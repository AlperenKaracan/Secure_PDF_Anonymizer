# Güvenli Belge Anonimleştirici (Secure PDF Anonymizer)

## Açıklama

Bu proje, akademik makalelerin (PDF formatında) güvenli bir şekilde anonimleştirilmesi için geliştirilmiş bir Flask web uygulamasıdır. Gelişmiş OCR ve NLP teknikleri kullanarak metinlerdeki hassas bilgileri (kişi isimleri, kurumlar, e-postalar, telefon numaraları vb.) tespit edip redakte eder ve belgelerdeki görsellerde bulunan yüzleri bulanıklaştırır. Ayrıca, makalelerden otomatik anahtar kelime çıkarma, çıkarılan anahtar kelimelere göre ilgili araştırma alanlarını belirleme ve bu alanlardaki uzman hakemleri atama yeteneklerine sahiptir. Proje, makale gönderimi, revizyon süreçleri ve hakem değerlendirmeleri için bir iş akışı sunar.

## Özellikler

* **PDF Yükleme ve Takip:** Kullanıcıların PDF makalelerini yüklemesine ve benzersiz bir takip numarası ile süreçlerini takip etmesine olanak tanır.
* **Gelişmiş Metin Anonimleştirme:**
    * Spacy kullanarak metin içindeki Kişi (PERSON), Organizasyon (ORG), Yer (GPE) gibi özel isimleri tanır.
    * Regex kullanarak e-posta adreslerini ve telefon numaralarını bulur.
    * Belirli başlıkları (örn. GİRİŞ, YÖNTEM) anonimleştirme dışında tutma seçeneği sunar.
    * Gerektiğinde PDF içindeki görsellerden metin okumak için PyTesseract OCR kullanır.
* **Gelişmiş Görüntü Anonimleştirme:**
    * PDF içindeki görsellerde MTCNN ile yüzleri tespit eder.
    * OpenCV kullanarak tespit edilen yüzleri Gaussian Blur ile bulanıklaştırır.
* **Dosya Şifreleme:** Yüklenen orijinal ve revize edilmiş dosyaları `cryptography` kütüphanesi kullanarak şifreler ve güvenli bir şekilde saklar.
* **Anahtar Kelime Çıkarma:**
    * PDF metninden ve OCR ile elde edilen metinden Spacy (NER ve noun chunks) kullanarak otomatik anahtar kelimeler çıkarır.
    * Metin içinde geçen "Keywords", "Index Terms" gibi explicit anahtar kelimeleri ayrıştırır.
* **Alan Eşleştirme ve Hakem Atama:**
    * Çıkarılan anahtar kelimeleri, önceden tanımlanmış araştırma alanları ve alt alanlarla eşleştirir.
    * Eşleşen alanlara göre, ilgi alanları uyan hakemleri önerir ve atanmasını sağlar. Eşleştirmede `fuzzywuzzy` kullanılır.
* **İş Akışı Yönetimi:**
    * **Editör Paneli:** Yüklenen makaleleri listeler, durumlarını gösterir, hakem ataması yapar, revizyon talep eder ve işlem loglarını görüntüler.
    * **Hakem Paneli:** Atanan makaleleri listeler, anonimleştirilmiş PDF'i indirir ve değerlendirme (puan, yıldız, yorum) gönderir.
    * **Yazar Alanı:** Makale yükleme, takip numarası ile durum kontrolü ve revizyon yükleme imkanı sunar.
* **Loglama:** Tüm önemli işlemler (dosya yükleme, anonimleştirme, atama, revizyon, değerlendirme) hem bir log dosyasına hem de MongoDB veritabanına kaydedilir.

## Teknolojiler

* **Backend:** Python, Flask
* **Veritabanı:** MongoDB (PyMongo ile)
* **NLP & OCR:** Spacy (`en_core_web_trf`), PyTesseract
* **Görüntü İşleme:** OpenCV, MTCNN, Pillow (PIL)
* **PDF İşleme:** PyMuPDF (fitz)
* **Şifreleme:** Cryptography (Fernet)
* **Metin Eşleştirme:** FuzzyWuzzy
* **Frontend:** HTML, CSS, JavaScript, Bootstrap, jQuery, DataTables

## Kullanım

1.  **Yazar:**
    * Ana sayfadan "Makalenizi Yükleyin" veya "Yükle" menüsüne gidin.
    * PDF dosyasını ve e-posta adresinizi girerek makaleyi yükleyin.
    * Verilen takip numarasını not alın.
    * "Durum" menüsünden takip numarası ve e-posta ile makalenizin durumunu kontrol edin.
    * Eğer revizyon istenmişse ("Revizyon Gerekiyor" durumu), "Revize Edilmiş PDF Yükle" seçeneği ile güncellenmiş dosyayı yükleyin.
2.  **Editör:**
    * "Editör" menüsüne gidin.
    * Yüklenen makaleleri, durumlarını ve varsa hakem değerlendirmelerini görüntüleyin.
    * "Hakemi Ata" butonu ile makale için hakem atama sayfasına gidin.
        * Otomatik çıkarılan anahtar kelimeleri ve eşleşen alanları inceleyin.
        * Anonimleştirmeden hariç tutulacak bölümleri seçin.
        * Önerilen hakem listesinden birini seçin ve atayın. Bu işlem aynı zamanda belgeyi seçilen ayarlarla anonimleştirir.
    * Gerekiyorsa "Revize İste" butonu ile yazardan revizyon talep edin.
    * Orijinal, revize edilmiş (varsa) ve anonimleştirilmiş PDF'leri indirin.
    * "Makale Logları" ile ilgili makalenin işlem geçmişini inceleyin.
3.  **Hakem:**
    * "Hakem" menüsüne gidin.
    * İsterseniz kendi isminizi seçerek sadece size atanmış makaleleri filtreleyin.
    * "İncele" butonu ile değerlendirme sayfasına gidin.
    * "İndir" butonu ile anonimleştirilmiş makaleyi indirin.
    * Makaleyi inceledikten sonra puan (1-10), yıldız (1-5) ve detaylı yorumlarınızı girerek gönderin.
