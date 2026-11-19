"""Quick manual check: turn 2 pages of the tax law into a scanned (image-only) PDF and OCR it with Azure."""
import fitz  # PyMuPDF

from ocr import ocr_enabled, ocr_pdf, page_needs_ocr

SRC = "uploads/income_tax_law_2014.pdf"
SCAN = "uploads/scanned_sample.pdf"

# 1) build an image-only PDF from the first 2 pages (like a scanner would)
src = fitz.open(SRC)
scan = fitz.open()
for i in range(2):
    pix = src[i].get_pixmap(dpi=150)
    page = scan.new_page(width=src[i].rect.width, height=src[i].rect.height)
    # JPEG keeps the file small (the free tier accepts files up to 4 MB)
    page.insert_image(page.rect, stream=pix.tobytes("jpeg", jpg_quality=80))
scan.save(SCAN, garbage=4, deflate=True)
import os
print("Created", SCAN, f"({os.path.getsize(SCAN) / 1e6:.1f} MB)")

# 2) normal text extraction finds nothing on a scanned page
text = fitz.open(SCAN)[0].get_text()
print("Text without OCR:", repr(text[:50]), "| needs OCR:", page_needs_ocr(text))

# 3) Azure OCR reads it
print("OCR enabled:", ocr_enabled())
for p in ocr_pdf(SCAN):
    print(f"\n--- page {p['page']} ---")
    print(p["text"][:400])
