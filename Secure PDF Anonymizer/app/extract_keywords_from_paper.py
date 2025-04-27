import fitz
import io
import re
from PIL import Image
import cv2
import numpy as np
import pytesseract
import logging
import spacy

nlp = spacy.load("en_core_web_trf")

def preprocess_for_ocr(img: Image.Image):
    image_np = np.array(img)
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return thresh

def ocr_page(page):
    pix = page.get_pixmap(dpi=300)
    pil_img = Image.open(io.BytesIO(pix.tobytes()))
    processed_img = preprocess_for_ocr(pil_img)
    text = pytesseract.image_to_string(processed_img, lang='eng')
    return text

def extract_keywords_from_text_spacy(text):
    doc = nlp(text)
    kw = set()
    for ent in doc.ents:
        kw.add(ent.text.strip())
    for chunk in doc.noun_chunks:
        kw.add(chunk.text.strip())
    return list(kw)

def parse_keywords_line(line):
    line_clean = re.sub(r'(?i)keywords?:?', '', line)
    line_clean = re.sub(r'(?i)index terms?:?', '', line_clean)
    parts = re.split(r'[;,]', line_clean)
    return [p.strip() for p in parts if p.strip()]

def extract_keywords_from_paper(filepath):
    doc = fitz.open(filepath)
    all_keywords = set()
    max_pages_to_check = min(2, len(doc))
    found_explicit_keywords = False

    for page_index in range(max_pages_to_check):
        page = doc[page_index]
        text = page.get_text()
        if not text or len(text.strip()) < 20:
            text = ocr_page(page)
        lines = text.split('\n')
        for line in lines:
            if re.search(r'(?i)(keywords|index terms)', line):
                parsed = parse_keywords_line(line)
                if parsed:
                    for p in parsed:
                        all_keywords.add(p)
                    found_explicit_keywords = True
        if not found_explicit_keywords:
            spacy_kws = extract_keywords_from_text_spacy(text)
            for skw in spacy_kws:
                all_keywords.add(skw)
    doc.close()
    return list(all_keywords)
