import re
import spacy
import pytesseract
from pytesseract import Output
from PIL import Image
import cv2
import numpy as np
import io
import logging
from datetime import datetime
import fitz
nlp = spacy.load("en_core_web_trf")

EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
PHONE_REGEX = r'\b(?:\+?\d{1,3}[-.\s])?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'
INSTITUTION_REGEX = r'\b(?:University|College|Institute|Laboratory|Hospital|School|Fakülte|Üniversitesi|Laboratuvarı|Okulu|Merkezi|Araştırma Merkezi|Inc\.?|LLC|Ltd\.?|Corporation|Company)\b'


def advanced_preprocess_image(img: Image.Image):
    image_np = np.array(img)
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )
    return thresh


def get_ocr_data_advanced(page):

    pix = page.get_pixmap(dpi=400)
    pil_img = Image.open(io.BytesIO(pix.tobytes()))
    processed_img = advanced_preprocess_image(pil_img)
    data = pytesseract.image_to_data(processed_img, lang='eng', output_type=Output.DICT)
    return data, pix


def extract_full_text_from_pdf(filepath):

    doc = fitz.open(filepath)
    full_text = []
    max_pages = min(2, len(doc))
    for i in range(max_pages):
        page = doc[i]
        text = page.get_text()
        if not text or len(text.strip()) < 20:
            text = pytesseract.image_to_string(
                Image.open(io.BytesIO(page.get_pixmap(dpi=300).tobytes())), lang='eng'
            )
        full_text.append(text)
    doc.close()
    return "\n".join(full_text)


def extract_sensitive_entities(text):

    entities = set()
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "ORG", "GPE"]:
            entities.add(ent.text.strip())

    emails = re.findall(EMAIL_REGEX, text, flags=re.IGNORECASE)
    phones = re.findall(PHONE_REGEX, text, flags=re.IGNORECASE)
    institutions = re.findall(INSTITUTION_REGEX, text, flags=re.IGNORECASE)

    for e in emails:
        entities.add(e.strip())
    for p in phones:
        entities.add(p.strip())
    for inst in institutions:
        entities.add(inst.strip())

    multiword_names = re.findall(r'\b(?:Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    for name in multiword_names:
        entities.add(name.strip())

    return entities


def extract_sections_from_pdf(filepath):
    doc = fitz.open(filepath)
    all_text = ""
    for page in doc:
        all_text += page.get_text() + "\n"
    doc.close()

    sections = []
    for line in all_text.splitlines():
        cleaned = line.strip().rstrip(":")
        if len(cleaned) >= 3 and cleaned[0].isupper():
            sections.append(cleaned)
    return list(dict.fromkeys(sections))


def is_exempt_page(text, exempt_sections):
    lines = text.splitlines()
    for line in lines:
        stripped_line = line.strip().rstrip(":")
        for section in exempt_sections:
            if stripped_line.lower() == section.lower():
                return True
    return False


def advanced_anonymize_text_pdf(filepath, exempt_sections=None):

    if exempt_sections is None:
        exempt_sections = extract_sections_from_pdf(filepath)
        logging.info(f"Dinamİk olarak tespit edilen bölümler: {exempt_sections}")

    doc = fitz.open(filepath)
    logging.info(f"Gelişmiş metin anonimleştirme başladı: {filepath}")

    if len(doc) > 0:
        first_page = doc[0]
        ocr_data, _ = get_ocr_data_advanced(first_page)
        full_text = " ".join(ocr_data['text'])
        sensitive_entities = extract_sensitive_entities(full_text)
        logging.info(f"Tespit edilen hassas bilgiler: {sensitive_entities}")
    else:
        sensitive_entities = set()
        logging.info("PDF'de sayfa yok; varlık çıkarımı atlanıyor.")

    for page_index, page in enumerate(doc):
        ocr_data, pix = get_ocr_data_advanced(page)
        page_text = " ".join(ocr_data['text'])

        if is_exempt_page(page_text, exempt_sections):
            logging.info(f"Sayfa {page_index} için redaksiyon atlandı.")
            continue

        positions = list(zip(ocr_data['left'], ocr_data['top'], ocr_data['width'], ocr_data['height']))
        scale_x = page.rect.width / pix.width
        scale_y = page.rect.height / pix.height

        for idx, word in enumerate(ocr_data['text']):
            clean_word = word.strip()
            if not clean_word:
                continue
            for entity in sensitive_entities:
                if clean_word.lower() == entity.lower():
                    x, y, w, h = positions[idx]
                    rect = fitz.Rect(x * scale_x, y * scale_y, (x + w) * scale_x, (y + h) * scale_y)
                    page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filepath = filepath.replace(".pdf", f"_anon_{timestamp}.pdf")
    doc.save(new_filepath, garbage=4, clean=True, deflate=True)
    doc.close()

    logging.info(f"Gelişmiş metin anonimleştirme tamamlandı: {new_filepath}")
    return new_filepath
