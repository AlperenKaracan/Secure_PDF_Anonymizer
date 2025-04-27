import cv2
import numpy as np
from PIL import Image
import pytesseract
import logging

def preprocess_for_ocr(pil_image: Image.Image) -> np.ndarray:
    image = np.array(pil_image)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=30)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )
    return thresh

def perform_ocr(pil_image: Image.Image, lang: str = 'eng') -> str:
    processed_img = preprocess_for_ocr(pil_image)
    text = pytesseract.image_to_string(processed_img, lang=lang)
    logging.info("OCR completed.")
    return text

def extract_ocr_data(pil_image: Image.Image, lang: str = 'eng'):
    from pytesseract import Output
    processed_img = preprocess_for_ocr(pil_image)
    data = pytesseract.image_to_data(processed_img, lang=lang, output_type=Output.DICT)
    return data
