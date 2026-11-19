import pdfplumber
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# OCR tools
import pytesseract
from pdf2image import convert_from_path

# --- paths to the installed programs (change if you installed them elsewhere) ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Users\Rama\OneDrive\Desktop\Poppler\Release-26.09.0-0\poppler-26.09.0\Library\bin"


def _is_arabic(text):
    """True if the text contains any Arabic letter."""
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _looks_broken(text):
    """
    True if the extracted Arabic looks broken: it contains isolated
    presentation-form letters (U+FB50–U+FEFF) that appear when the PDF
    stored the text wrongly.
    """
    return any("\uFB50" <= ch <= "\uFEFF" for ch in text)


def _add_paragraph(doc, text):
    """Add one paragraph, right-to-left if it is Arabic."""
    p = doc.add_paragraph(text)
    if _is_arabic(text):
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.right_to_left = True
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return p


def _add_table(doc, table_rows):
    """Add a real Word table from a list of rows."""
    rows = [r for r in table_rows if r]
    if not rows:
        return
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in rows:
        cells = table.add_row().cells
        for i in range(cols):
            value = row[i] if i < len(row) and row[i] else ""
            cells[i].text = value
            for p in cells[i].paragraphs:
                if _is_arabic(value):
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p.paragraph_format.right_to_left = True


def _extract_direct(pdf_path, doc):
    """
    Try to read the PDF text directly (fast, keeps tables).
    Returns True if it succeeded, False if the Arabic looked broken.
    """
    broken_pages = 0
    total_pages = 0
    blocks = []   # collect first, write only if not broken

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            tables = page.extract_tables()
            text = page.extract_text() or ""
            if _is_arabic(text) and _looks_broken(text):
                broken_pages += 1
            blocks.append((tables, text))

    # if more than a third of the pages look broken, fall back to OCR
    if total_pages and broken_pages > total_pages / 3:
        return False

    for page_number, (tables, text) in enumerate(blocks, start=1):
        for table in tables:
            _add_table(doc, table)
            doc.add_paragraph("")
        for line in text.splitlines():
            line = line.strip()
            if line:
                _add_paragraph(doc, line)
        if page_number < len(blocks):
            doc.add_page_break()
    return True


def _extract_ocr(pdf_path, doc):
    """
    Read the PDF with OCR (slower, no tables, but fixes broken Arabic).
    Reads each page as an image, in Arabic + English.
    """
    images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    for page_number, image in enumerate(images, start=1):
        text = pytesseract.image_to_string(image, lang="ara+eng")
        for line in text.splitlines():
            line = line.strip()
            if line:
                _add_paragraph(doc, line)
        if page_number < len(images):
            doc.add_page_break()


def pdf_to_word(pdf_path, docx_path):
    """
    Convert a PDF to Word.
    If the PDF has Arabic text, use OCR (most reliable for Arabic PDFs).
    If it is English-only, use direct extraction (fast, keeps tables).
    """
    # peek at the text to decide
    sample = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:3]:          # first 3 pages are enough to tell
            sample += page.extract_text() or ""

    doc = Document()
    if _is_arabic(sample):
        print(">>> Arabic detected — using OCR", flush=True)
        _extract_ocr(pdf_path, doc)
    else:
        print(">>> English only — using direct extraction", flush=True)
        _extract_direct(pdf_path, doc)
    doc.save(docx_path)
    return False