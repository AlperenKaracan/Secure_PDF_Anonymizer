import fitz
import cv2
import numpy as np
from PIL import Image
import io
import logging
from mtcnn import MTCNN

def advanced_anonymize_faces_in_pdf(filepath):

    try:
        doc = fitz.open(filepath)
        logging.info(f"Gelişmiş görüntü anonimleştirme başlad: {filepath}")
        detector = MTCNN()

        for page in doc:
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                open_cv_image = np.array(pil_img)
                results = detector.detect_faces(open_cv_image)

                for face in results:
                    x, y, w, h = face['box']
                    k = max(3, int(min(w, h) / 3))
                    if k % 2 == 0:
                        k += 1
                    face_region = open_cv_image[y:y+h, x:x+w]
                    blurred = cv2.GaussianBlur(face_region, (k, k), 0)
                    open_cv_image[y:y+h, x:x+w] = blurred

                    logging.info(f"Face blurred: {(x, y, w, h)}")

                pil_img = Image.fromarray(open_cv_image)

                img_buffer = io.BytesIO()
                pil_img.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                page.replace_image(xref, stream=img_buffer.getvalue())

        new_filepath = filepath.replace(".pdf", "_faces_anon.pdf")
        doc.save(new_filepath, deflate=True)
        doc.close()
        logging.info(f"Gelişmiş görüntü anonimleştirme bitti: {new_filepath}")
        return new_filepath

    except Exception as e:
        logging.error(f"Görüntü anonimleştirme sorunu: {e}")
        raise
