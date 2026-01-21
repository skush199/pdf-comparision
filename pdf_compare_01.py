"""
PDF Document Comparison Tool (TEXT + OCR)

- Compares two PDFs with identical structure
- Extracts numbers from:
    1) Text layer (PyMuPDF)
    2) Image-based text (Google Vision OCR)
- Highlights numeric differences
- Outputs JSON report

Usage:
python pdf_compare_with_ocr.py old.pdf new.pdf output.pdf
"""

import sys
import re
import json
import fitz
import io
import os
import pdfplumber

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

from google.cloud import vision
from google.oauth2 import service_account


# ============================================================================
# OCR PROCESSOR (UNCHANGED – YOUR CLASS)
# ============================================================================

class GoogleVisionOCRProcessor():

    def looks_like_cid_encoded(self, text):
        return "(cid:" in text.lower()

    def ocr_image_bytes(self, image_bytes, client, language_hints=None):
        if language_hints is None:
            language_hints = ["ja", "en"]
        image = vision.Image(content=image_bytes)
        image_context = vision.ImageContext(language_hints=language_hints)
        response = client.document_text_detection(image=image, image_context=image_context)
        if response.error.message:
            print(f"⚠️ OCR error: {response.error.message}")
            return ""
        if response.full_text_annotation and response.full_text_annotation.text:
            return response.full_text_annotation.text.strip()
        return ""

    def clamp_bbox_to_page(self, bbox, page_bbox):
        x0, top, x1, bottom = bbox
        px0, pt, px1, pb = page_bbox
        x0 = max(px0, min(x0, px1))
        x1 = max(px0, min(x1, px1))
        top = max(pt, min(top, pb))
        bottom = max(pt, min(bottom, pb))
        if x0 >= x1 or top >= bottom:
            return None
        return (x0, top, x1, bottom)

    def extract_text_from_pdf(self, pdf_path, user_type="org"):
        if user_type == "org":
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            creds = service_account.Credentials.from_service_account_file(cred_path)
            client = vision.ImageAnnotatorClient(credentials=creds)
        else:
            client = vision.ImageAnnotatorClient()

        pages_text = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                parts = []
                text = (page.extract_text() or "").strip()
                if text and self.looks_like_cid_encoded(text):
                    text = ""

                if text:
                    parts.append(text)
                    if page.images:
                        page_bbox = (0, 0, page.width, page.height)
                        for img in page.images:
                            bbox = self.clamp_bbox_to_page(
                                (img["x0"], img["top"], img["x1"], img["bottom"]),
                                page_bbox
                            )
                            if not bbox:
                                continue
                            crop = page.crop(bbox).to_image(resolution=400)
                            buf = io.BytesIO()
                            crop.save(buf, format="PNG")
                            ocr_text = self.ocr_image_bytes(buf.getvalue(), client)
                            if ocr_text:
                                parts.append(ocr_text)
                else:
                    img = page.to_image(resolution=400)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    ocr_text = self.ocr_image_bytes(buf.getvalue(), client)
                    if ocr_text:
                        parts.append(ocr_text)

                pages_text.append("\n".join(parts))

        return pages_text


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class NumberMatch:
    value: str
    numeric_value: float
    page: int
    rect: fitz.Rect
    line_number: int


@dataclass
class Difference:
    page: int
    line: int
    old_value: str
    new_value: str
    old_rect: fitz.Rect
    new_rect: fitz.Rect


# ============================================================================
# NUMBER EXTRACTION (TEXT LAYER)
# ============================================================================

NUMBER_PATTERN = re.compile(r"-?[\d,]+\.?\d*")

def extract_numbers_from_page(page: fitz.Page, page_num: int) -> List[NumberMatch]:
    results = []
    blocks = page.get_text("dict")["blocks"]
    line_no = 0

    for block in blocks:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            line_no += 1
            for span in line["spans"]:
                text = span["text"]
                rect = fitz.Rect(span["bbox"])
                for m in NUMBER_PATTERN.finditer(text):
                    raw = m.group()
                    try:
                        val = float(raw.replace(",", ""))
                    except:
                        continue
                    char_w = rect.width / max(len(text), 1)
                    x0 = rect.x0 + m.start() * char_w
                    x1 = rect.x0 + m.end() * char_w
                    results.append(NumberMatch(
                        value=raw,
                        numeric_value=val,
                        page=page_num,
                        rect=fitz.Rect(x0, rect.y0, x1, rect.y1),
                        line_number=line_no
                    ))
    return results


# ============================================================================
# OCR NUMBER EXTRACTION
# ============================================================================

def extract_numbers_from_ocr_text(text, page_num, page_rect):
    results = []
    for m in NUMBER_PATTERN.finditer(text):
        raw = m.group()
        try:
            val = float(raw.replace(",", ""))
        except:
            continue
        results.append(NumberMatch(
            value=raw,
            numeric_value=val,
            page=page_num,
            rect=page_rect,
            line_number=-1
        ))
    return results


# ============================================================================
# UNIFIED NUMBER EXTRACTION
# ============================================================================

def extract_all_numbers(pdf_path):
    ocr = GoogleVisionOCRProcessor()
    doc = fitz.open(pdf_path)
    ocr_pages = ocr.extract_text_from_pdf(pdf_path)

    all_numbers = []

    for i, page in enumerate(doc):
        all_numbers.extend(extract_numbers_from_page(page, i))
        if i < len(ocr_pages):
            all_numbers.extend(
                extract_numbers_from_ocr_text(
                    ocr_pages[i],
                    i,
                    page.rect
                )
            )

    doc.close()
    return all_numbers


# ============================================================================
# COMPARISON
# ============================================================================

def compare_numbers(nums1, nums2, tol=0.0001):
    diffs = []
    for i in range(min(len(nums1), len(nums2))):
        if abs(nums1[i].numeric_value - nums2[i].numeric_value) > tol:
            diffs.append(Difference(
                page=nums1[i].page,
                line=nums1[i].line_number,
                old_value=nums1[i].value,
                new_value=nums2[i].value,
                old_rect=nums1[i].rect,
                new_rect=nums2[i].rect
            ))
    return diffs


# ============================================================================
# HIGHLIGHT OUTPUT
# ============================================================================

def create_highlighted_pdf(old_pdf, new_pdf, diffs, out_pdf):
    d1 = fitz.open(old_pdf)
    d2 = fitz.open(new_pdf)
    out = fitz.open()

    for i in range(max(len(d1), len(d2))):
        p1 = d1[i]
        p2 = d2[i]
        w = p1.rect.width + p2.rect.width + 20
        h = max(p1.rect.height, p2.rect.height)
        p = out.new_page(width=w, height=h)

        p.show_pdf_page(p1.rect, d1, i)
        p.show_pdf_page(
            fitz.Rect(p1.rect.width + 20, 0, w, h),
            d2, i
        )

        for d in diffs:
            if d.page == i:
                p.draw_rect(d.old_rect, color=(1,0,0), width=2)
                r = d.new_rect + fitz.Rect(p1.rect.width + 20,0,p1.rect.width + 20,0)
                p.draw_rect(r, color=(1,0,0), width=2)

    out.save(out_pdf)


# ============================================================================
# MAIN
# ============================================================================

def main(old_pdf, new_pdf, out_pdf):
    nums1 = extract_all_numbers(old_pdf)
    nums2 = extract_all_numbers(new_pdf)
    diffs = compare_numbers(nums1, nums2)
    create_highlighted_pdf(old_pdf, new_pdf, diffs, out_pdf)

    report = {
        "differences": len(diffs),
        "details": [
            {
                "page": d.page + 1,
                "old": d.old_value,
                "new": d.new_value
            } for d in diffs
        ]
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pdf_compare_with_ocr.py old.pdf new.pdf output.pdf")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
