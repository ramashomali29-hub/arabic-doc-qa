"""OCR for scanned or badly encoded Arabic PDFs using Azure AI Document Intelligence.

OCR is optional: it is enabled only when AZURE_DI_ENDPOINT and AZURE_DI_KEY are set.
Credentials are read from the environment and never logged.
"""
import logging
import os

try:  # load .env when running locally (Docker passes env vars directly)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Arabic presentation-form letters appear when a PDF stores Arabic text wrongly
_BROKEN_RANGE = ("\uFB50", "\uFEFF")
MIN_CHARS_PER_PAGE = 20
# Azure free tier (F0) accepts files up to 4 MB; paid tiers accept more
MAX_OCR_MB = float(os.getenv("AZURE_DI_MAX_MB", "4"))


def ocr_enabled():
    return bool(os.getenv("AZURE_DI_ENDPOINT") and os.getenv("AZURE_DI_KEY"))


def page_needs_ocr(text):
    """True if a page has almost no text (scanned) or broken Arabic."""
    text = (text or "").strip()
    if len(text) < MIN_CHARS_PER_PAGE:
        return True
    lo, hi = _BROKEN_RANGE
    return any(lo <= ch <= hi for ch in text)


def _client():
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    return DocumentIntelligenceClient(
        os.environ["AZURE_DI_ENDPOINT"],
        AzureKeyCredential(os.environ["AZURE_DI_KEY"]),
    )


def ocr_pdf(path, client=None):
    """Return a list of {"page": n, "text": "..."} (1-based pages) read with the prebuilt-read model."""
    size_mb = os.path.getsize(path) / 1e6
    if size_mb > MAX_OCR_MB:
        raise ValueError(f"File is {size_mb:.1f} MB; the OCR limit is {MAX_OCR_MB:g} MB")
    client = client or _client()
    with open(path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", body=f)
    result = poller.result()

    pages = []
    for page in result.pages or []:
        lines = [line.content for line in (page.lines or [])]
        pages.append({"page": page.page_number, "text": "\n".join(lines)})
    logger.info("OCR read %d pages from %s", len(pages), os.path.basename(path))
    return pages
