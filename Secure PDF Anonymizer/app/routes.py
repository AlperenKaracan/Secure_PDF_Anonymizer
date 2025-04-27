import os
import uuid
import logging
import re
from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, send_file, flash
)
from werkzeug.utils import secure_filename
import fitz

from . import mongo
from .encryption import encrypt_file, decrypt_file
from .advanced_text_anonymizer import advanced_anonymize_text_pdf
from .advanced_image_anonymizer import advanced_anonymize_faces_in_pdf
from .extract_keywords_from_paper import extract_keywords_from_paper
from .reviewer_assignment import map_keywords_to_domains, get_detailed_reviewer_profiles
from .reviewers import REVIEWERS
main = Blueprint("main", __name__)
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "makale"
)
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
logger = logging.getLogger(__name__)

def add_article_log(article_id, message):
    logger.debug(f"add_article_log çağrıldı: {message}")
    log_entry = {
        "zaman": datetime.now().isoformat(),
        "mesaj": message
    }
    mongo.db.articles.update_one({"_id": article_id}, {"$push": {"logs": log_entry}})


def get_latest_pdf(article):
    logger.debug("get_latest_pdf fonksiyonu çalışıyor.")
    source_pdf = article.get("filepath")
    rev_history = article.get("revision_history", [])
    if rev_history:
        last_rev_info = rev_history[-1]
        enc_rev_path = last_rev_info.get("encrypted_filepath")
        ham_rev_path = last_rev_info.get("revision_filepath")

        if enc_rev_path and os.path.exists(enc_rev_path):
            try:
                decrypted_pdf = decrypt_file(enc_rev_path)
                source_pdf = os.path.abspath(decrypted_pdf)
                logger.info("Şifreli revize dosyası çözüldü.")
            except Exception as e:
                logger.error(f"Şifre çözme hatası: {e}")
                if ham_rev_path and os.path.exists(ham_rev_path):
                    source_pdf = os.path.abspath(ham_rev_path)
                else:
                    source_pdf = article["filepath"]
        elif ham_rev_path and os.path.exists(ham_rev_path):
            source_pdf = os.path.abspath(ham_rev_path)
        else:
            source_pdf = article["filepath"]
    return os.path.abspath(source_pdf)
def extract_sections_from_pdf(pdf_path):
    logger.debug(f"extract_sections_from_pdf fonksiyonu başlıyor: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc(simple=True)
        sections = []
        if toc:
            for item in toc:
                level, title, page = item
                if level == 1:
                    sections.append(title.strip())
            if not sections:
                sections = [item[1].strip() for item in toc]
        else:
            sections_set = set()
            section_pattern = re.compile(r'^(?:\d+\.\s*)?([A-Z][A-Z\s]{2,})$')
            common_keywords = {
                "INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION",
                "CONCLUSION", "ABSTRACT", "BACKGROUND"
            }
            for page in doc:
                text = page.get_text("text")
                for line in text.splitlines():
                    cleaned = line.strip().rstrip(":")
                    if not cleaned:
                        continue
                    if cleaned.isupper() and len(cleaned) < 60:
                        sections_set.add(cleaned)
                    else:
                        m = section_pattern.match(cleaned)
                        if m:
                            candidate = m.group(1).strip()
                            if candidate in common_keywords or len(candidate) < 60:
                                sections_set.add(candidate)
            sections = list(sections_set)
        doc.close()
        logger.debug(f"extract_sections_from_pdf tamamlandı. Bulunan bölümler: {sections}")
        return sections
    except Exception as e:
        logger.error(f"Bölüm çıkarma hatası: {e}")
        return []

@main.route("/")
def index():
    logger.debug("Anasayfa görüntülendi.")
    return render_template("index.html")

@main.route("/upload", methods=["GET", "POST"])
def upload():
    logger.debug("upload sayfası çağrıldı.")
    if request.method == "POST":
        logger.debug("upload: POST isteği alındı.")
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Lütfen bir PDF dosyası seçin!", "danger")
            logger.warning("upload: Kullanıcı PDF dosyası seçmedi.")
            return redirect(request.url)
        if not file.filename.lower().endswith(".pdf"):
            flash("Lütfen yalnızca PDF dosyası yükleyin!", "danger")
            logger.warning("upload: Kullanıcı PDF dışında dosya yüklemeye çalıştı.")
            return redirect(request.url)

        email = request.form.get("email")
        if not email:
            flash("E-posta adresi zorunludur!", "danger")
            logger.warning("upload: E-posta adresi girilmemiş.")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        auto_keywords = extract_keywords_from_paper(filepath)
        encrypted_path = encrypt_file(filepath)

        tracking_number = str(uuid.uuid4())
        article_data = {
            "tracking_number": tracking_number,
            "email": email,
            "filename": filename,
            "filepath": filepath,
            "encrypted_filepath": encrypted_path,
            "is_encrypted": True,
            "anonymized_filepath": None,
            "revision_history": [],
            "status": "uploaded",
            "keywords": ", ".join(auto_keywords),
            "logs": []
        }
        article_id = mongo.db.articles.insert_one(article_data).inserted_id

        add_article_log(article_id, f"Makale yüklendi, anahtar kelimeler: {auto_keywords}")
        logger.info(f"Makale yüklendi -> {tracking_number}, Anahtar Kelimeler: {auto_keywords}")

        flash(f"Makale başarıyla yüklendi! Takip Numarası: {tracking_number}", "success")
        return render_template("upload.html", success=True, tracking_number=tracking_number)

    return render_template("upload.html")

@main.route("/revision/<tracking_number>", methods=["GET", "POST"])
def revision(tracking_number):
    logger.debug(f"revision route: tracking_number={tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article:
        flash("Makale bulunamadı!", "danger")
        logger.warning("revision: Makale bulunamadı.")
        return redirect(url_for("main.status"))

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Lütfen bir PDF dosyası seçin!", "danger")
            logger.warning("revision: Dosya seçilmedi.")
            return redirect(request.url)
        if not file.filename.lower().endswith(".pdf"):
            flash("Lütfen yalnızca PDF dosyası yükleyin!", "danger")
            logger.warning("revision: PDF dışında dosya yüklendi.")
            return redirect(request.url)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(secure_filename(file.filename))[0]
        rev_filename = f"{base_name}_rev_{timestamp}.pdf"
        revision_filepath = os.path.join(UPLOAD_FOLDER, rev_filename)
        file.save(revision_filepath)
        encrypted_rev_path = encrypt_file(revision_filepath)

        revision_info = {
            "revision_filepath": revision_filepath,
            "encrypted_filepath": encrypted_rev_path,
            "timestamp": datetime.now().isoformat()
        }
        mongo.db.articles.update_one(
            {"_id": article["_id"]},
            {
                "$set": {"status": "revised", "new_revised_pdf": True},
                "$push": {"revision_history": revision_info}
            }
        )
        add_article_log(article["_id"], "Revize PDF yüklendi, durum 'revised' olarak güncellendi.")
        logger.info(f"Revize PDF yüklendi -> {tracking_number}")
        flash("Revize makale başarıyla yüklendi. Editör ve atanan hakem bilgilendirildi.", "success")
        return redirect(url_for("main.status"))

    return render_template("revision_upload.html", article=article)


@main.route("/status", methods=["GET", "POST"])
def status():
    logger.debug("status sayfası çağrıldı.")
    if request.method == "POST":
        tracking_number = request.form.get("tracking_number")
        email = request.form.get("email")
        article = mongo.db.articles.find_one({"tracking_number": tracking_number, "email": email})
        if not article:
            flash("Makale bulunamadı, takip numarası veya e-posta yanlış!", "danger")
            logger.warning("status: Makale bulunamadı.")
            return render_template("status.html", not_found=True)
        return render_template("status.html", article=article)
    return render_template("status.html")


@main.route("/download/<tracking_number>")
def download(tracking_number):
    logger.debug(f"download: tracking_number={tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article or not article.get("anonymized_filepath"):
        flash("Anonimleştirilmiş dosya bulunamadı!", "danger")
        logger.warning("download: Anonimleştirilmiş dosya yok.")
        return "Anonimleştirilmiş dosya yok", 404
    return send_file(article["anonymized_filepath"], as_attachment=True)


@main.route("/download_revised_pdf/<path:rev_path>")
def download_revised_pdf(rev_path):
    full_path = os.path.abspath(rev_path)
    logger.debug(f"download_revised_pdf: {full_path}")
    if not os.path.exists(full_path):
        flash("Revize dosya bulunamadı!", "danger")
        logger.warning("download_revised_pdf: Dosya yok.")
        return "Revize dosya yok", 404
    return send_file(full_path, as_attachment=True)


@main.route("/download_original/<tracking_number>")
def download_original(tracking_number):
    logger.debug(f"download_original: {tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article:
        flash("Makale bulunamadı!", "danger")
        logger.warning("download_original: Makale bulunamadı.")
        return redirect(url_for("main.editor_dashboard"))
    original_path = article.get("filepath")
    if not original_path or not os.path.exists(original_path):
        flash("Orijinal PDF dosyası bulunamadı!", "danger")
        logger.warning("download_original: PDF yok.")
        return "Orijinal PDF yok", 404
    return send_file(original_path, as_attachment=True)


@main.route("/editor")
def editor_dashboard():
    logger.debug("editor_dashboard görüntüleniyor.")
    articles = list(mongo.db.articles.find({}))
    reviews_dict = {}
    for art in articles:
        tnum = art.get("tracking_number")
        if tnum:
            review_data = mongo.db.reviews.find_one({"tracking_number": tnum})
            if review_data:
                reviews_dict[tnum] = review_data
    return render_template("editor_dashboard.html", articles=articles, reviews=reviews_dict)


@main.route("/editor/request_revision/<tracking_number>", methods=["GET", "POST"])
def request_revision(tracking_number):
    logger.debug(f"request_revision: {tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article:
        flash("Makale bulunamadı!", "danger")
        logger.warning("request_revision: Makale bulunamadı.")
        return redirect(url_for("main.editor_dashboard"))
    if request.method == "POST":
        instructions = request.form.get("instructions", "")
        mongo.db.articles.update_one(
            {"tracking_number": tracking_number},
            {"$set": {"status": "revision_required", "revision_instructions": instructions}}
        )
        add_article_log(article["_id"], "Editör revizyon talebi gönderdi, durum 'revision_required'")
        flash("Revizyon isteği gönderildi. Makale 'revision_required' durumuna alındı.", "success")
        logger.info(f"Revizyon talebi -> {tracking_number}")
        return redirect(url_for("main.editor_dashboard"))
    return render_template("request_revision.html", article=article)


@main.route("/editor/manual_assign/<tracking_number>", methods=["GET", "POST"])
def manual_assign(tracking_number):
    logger.debug(f"manual_assign: {tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article:
        flash("Makale bulunamadı!", "danger")
        logger.warning("manual_assign: Makale bulunamadı.")
        return redirect(url_for("main.editor_dashboard"))

    if request.method == "POST":
        selected_reviewer = request.form.get("reviewer")
        selected_sections = request.form.getlist("sections")
        if not selected_reviewer:
            flash("Lütfen bir hakem seçin!", "danger")
            logger.warning("manual_assign: Hakem seçilmedi.")
            return redirect(url_for("main.manual_assign", tracking_number=tracking_number))

        source_pdf = article["filepath"]
        rev_history = article.get("revision_history", [])
        if rev_history:
            last_rev_info = rev_history[-1]
            enc_rev_path = last_rev_info.get("encrypted_filepath")
            ham_rev_path = last_rev_info.get("revision_filepath")
            if enc_rev_path and os.path.exists(enc_rev_path):
                try:
                    decrypted_pdf = decrypt_file(enc_rev_path)
                    source_pdf = os.path.abspath(decrypted_pdf)
                    logger.debug(f"Şifreli revize dosyası çözüldü: {source_pdf}")
                except Exception as e:
                    logger.error(f"Şifre çözme hatası: {e}")
                    if ham_rev_path and os.path.exists(ham_rev_path):
                        source_pdf = os.path.abspath(ham_rev_path)
                    else:
                        source_pdf = article["filepath"]
            elif ham_rev_path and os.path.exists(ham_rev_path):
                source_pdf = os.path.abspath(ham_rev_path)

        try:
            text_anon_path = advanced_anonymize_text_pdf(source_pdf, exempt_sections=selected_sections)
            final_anon_path = advanced_anonymize_faces_in_pdf(text_anon_path)
        except Exception as e:
            flash(f"Anonimleştirme sırasında hata oluştu: {e}", "danger")
            logger.error(f"Anonimleştirme hatası: {e}")
            return redirect(url_for("main.editor_dashboard"))

        extracted_keywords = article.get("keywords", "")
        auto_keywords = [kw.strip() for kw in extracted_keywords.split(",") if kw.strip()]
        matched_domains = map_keywords_to_domains(auto_keywords)

        potential_reviewer_names = set()
        for domain, subfields in matched_domains.items():
            for r in REVIEWERS:
                for interest in r["interests"]:
                    norm_interest = interest.lower().strip()
                    for sf in subfields:
                        norm_sf = sf.lower().strip()
                        if norm_sf in norm_interest or norm_interest in norm_sf:
                            potential_reviewer_names.add(r["name"])
                            break
        if not potential_reviewer_names:
            potential_reviewer_names = {r["name"] for r in REVIEWERS}

        mongo.db.articles.update_one(
            {"_id": article["_id"]},
            {"$set": {
                "anonymized_filepath": final_anon_path,
                "status": "anonymized",
                "assigned_reviewers": [selected_reviewer]
            }}
        )
        add_article_log(article["_id"], "Makale anonimleştirildi ve hakeme atandı.")
        logger.info(f"Makale anonimleştirildi -> {tracking_number}, Atanan hakem: {selected_reviewer}")

        flash("Makale anonimleştirildi ve hakem atandı!", "success")
        return redirect(url_for("main.editor_dashboard"))

    else:
        extracted_keywords = article.get("keywords", "")
        auto_keywords = [kw.strip() for kw in extracted_keywords.split(",") if kw.strip()]
        matched_domains = map_keywords_to_domains(auto_keywords)
        potential_reviewer_names = set()
        for domain, subfields in matched_domains.items():
            for r in REVIEWERS:
                for interest in r["interests"]:
                    norm_interest = interest.lower().strip()
                    for sf in subfields:
                        norm_sf = sf.lower().strip()
                        if norm_sf in norm_interest or norm_interest in norm_sf:
                            potential_reviewer_names.add(r["name"])
                            break
        if not potential_reviewer_names:
            potential_reviewer_names = {r["name"] for r in REVIEWERS}

        source_pdf = get_latest_pdf(article)
        try:
            sections = extract_sections_from_pdf(source_pdf)
            if not sections:
                sections = ["INTRODUCTION", "METHOD", "RESULTS", "DISCUSSION", "REFERENCES"]
        except Exception as e:
            logger.error(f"PDF'den bölüm çıkarılırken hata: {e}")
            sections = ["INTRODUCTION", "METHOD", "RESULTS", "DISCUSSION", "REFERENCES"]

        potential_reviewers_details = get_detailed_reviewer_profiles(sorted(list(potential_reviewer_names)))

        return render_template(
            "manual_assign.html",
            article=article,
            potential_reviewer_names=sorted(list(potential_reviewer_names)),
            potential_reviewers=potential_reviewers_details,
            matched_domains=matched_domains,
            sections=sections
        )

@main.route("/hakem")
def hakem():
    logger.debug("Hakem dashboard görüntüleniyor.")
    reviewer = request.args.get("reviewer")
    query = {"status": {"$in": ["anonymized", "reviewed"]}}
    if reviewer:
        query["assigned_reviewers"] = {"$in": [reviewer]}
    articles = list(mongo.db.articles.find(query))
    return render_template("hakem_dashboard.html", articles=articles, reviewers=REVIEWERS)

@main.route("/review/<tracking_number>", methods=["GET", "POST"])
def review_article(tracking_number):
    logger.debug(f"review_article: {tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article:
        flash("Makale bulunamadı!", "danger")
        logger.warning("review_article: Makale bulunamadı.")
        return redirect(url_for("main.hakem"))

    if request.method == "POST":
        existing_review = mongo.db.reviews.find_one({"tracking_number": tracking_number})
        if existing_review:
            mongo.db.reviews.update_one(
                {"tracking_number": tracking_number},
                {"$set": {
                    "score": request.form.get("score"),
                    "detailed_comments": request.form.get("detailed_comments", ""),
                    "star_rating": request.form.get("star_rating"),
                    "updated_at": datetime.now().isoformat()
                }}
            )
            logger.info(f"review_article: Mevcut değerlendirme güncellendi -> {tracking_number}")
            flash("Mevcut değerlendirme güncellendi.", "success")
        else:
            score = request.form.get("score")
            detailed_comments = request.form.get("detailed_comments", "")
            star_rating = request.form.get("star_rating")
            mongo.db.reviews.insert_one({
                "tracking_number": tracking_number,
                "score": score,
                "detailed_comments": detailed_comments,
                "star_rating": star_rating,
                "created_at": datetime.now().isoformat()
            })
            logger.info(f"review_article: Yeni değerlendirme kaydedildi -> {tracking_number}")
            flash("Değerlendirme başarıyla kaydedildi.", "success")
        anonymized_pdf_path = article.get("anonymized_filepath")
        if anonymized_pdf_path:
            review_text = (
                "HAKEM DEGERLENDIRMESI\n"
                "-----------------------------\n"
                f"Puan: {request.form.get('score')}\n"
                f"Yildiz Degeri: {request.form.get('star_rating')}\n"
                f"Yorum:\n{request.form.get('detailed_comments', '').strip()}"
            )
            final_pdf = append_review_to_pdf(anonymized_pdf_path, review_text)
            mongo.db.articles.update_one(
                {"tracking_number": tracking_number},
                {"$set": {"anonymized_filepath": final_pdf}}
            )

        mongo.db.articles.update_one(
            {"tracking_number": tracking_number},
            {"$set": {"status": "reviewed"}}
        )
        add_article_log(article["_id"], "Hakem değerlendirmesi kaydedildi/güncellendi ve PDF'e eklendi.")
        logger.info(f"Hakem değerlendirmesi gönderildi -> {tracking_number}")

        return render_template("review.html", article=article, success=True)
    else:
        return render_template("review.html", article=article, success=False)


def append_review_to_pdf(pdf_path, review_text):
    logger.debug(f"append_review_to_pdf: {pdf_path}")
    doc = fitz.open(pdf_path)
    new_page = doc.new_page(width=doc[0].rect.width, height=doc[0].rect.height)
    text_rect = new_page.rect
    new_page.insert_textbox(text_rect, review_text, fontname="helv", fontsize=12, color=(0, 0, 0))
    new_pdf_path = pdf_path.replace(".pdf", "_reviewed.pdf")
    doc.save(new_pdf_path, deflate=True)
    doc.close()
    logger.debug(f"append_review_to_pdf: yeni PDF kaydedildi -> {new_pdf_path}")
    return new_pdf_path

@main.route("/editor/article_logs/<tracking_number>")
def article_logs(tracking_number):
    logger.debug(f"article_logs: {tracking_number}")
    article = mongo.db.articles.find_one({"tracking_number": tracking_number})
    if not article:
        flash("Makale bulunamadı!", "danger")
        return redirect(url_for("main.editor_dashboard"))
    logs = article.get("logs", [])
    logs.sort(key=lambda x: x["zaman"])
    return render_template("article_logs.html", article=article, logs=logs)

