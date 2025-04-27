import os
from cryptography.fernet import Fernet
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_key():
    key = Fernet.generate_key()
    with open("fernet.key", "wb") as key_file:
        key_file.write(key)
    logging.info("Yeni şifreleme anahtarı oluşturuldu.")
    return key

def load_key():
    try:
        with open("fernet.key", "rb") as key_file:
            key = key_file.read()
        logging.info("Şifreleme anahtarı yüklendi.")
        return key
    except FileNotFoundError:
        logging.info("Şifreleme anahtarı bulunamadı, yeni anahtar oluşturuluyor.")
        return generate_key()

cipher_suite = Fernet(load_key())

def encrypt_file(filepath):
    try:
        enc_path = filepath + ".enc"

        with open(filepath, "rb") as f:
            file_data = f.read()

        encrypted_data = cipher_suite.encrypt(file_data)

        with open(enc_path, "wb") as f:
            f.write(encrypted_data)

        logging.info(f"Şifrelenmiş kopya oluşturuldu: {enc_path}")
        return enc_path

    except Exception as e:
        logging.error(f"Şifreleme hatası: {e}")
        raise

def decrypt_file(enc_path):
    try:
        base, ext = os.path.splitext(enc_path)
        dec_path = base + "_cozulmus.pdf"

        with open(enc_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = cipher_suite.decrypt(encrypted_data)

        with open(dec_path, "wb") as f:
            f.write(decrypted_data)

        logging.info(f"Dosya başarıyla çözüldü: {dec_path}")
        return dec_path

    except Exception as e:
        logging.error(f"Şifre çözme hatası: {e}")
        raise
