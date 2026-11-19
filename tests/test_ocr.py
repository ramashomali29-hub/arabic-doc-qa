from types import SimpleNamespace

import ocr


def test_page_needs_ocr_for_empty_page():
    assert ocr.page_needs_ocr("")
    assert ocr.page_needs_ocr("   ")


def test_page_needs_ocr_for_broken_arabic():
    # isolated presentation-form letters = badly encoded Arabic
    assert ocr.page_needs_ocr("\ufee3\ufe8e\ufea9\ufe93 " * 10)


def test_clean_arabic_page_does_not_need_ocr():
    assert not ocr.page_needs_ocr("تفرض الضريبة على دخل الشخص الطبيعي وفق الشرائح التالية")


def test_ocr_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("AZURE_DI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_DI_KEY", raising=False)
    assert not ocr.ocr_enabled()


def test_ocr_pdf_returns_text_per_page(tmp_path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    line = lambda c: SimpleNamespace(content=c)
    result = SimpleNamespace(pages=[
        SimpleNamespace(page_number=1, lines=[line("المادة 1"), line("نص المادة")]),
        SimpleNamespace(page_number=2, lines=None),
    ])

    class FakeClient:
        def begin_analyze_document(self, model_id, body):
            assert model_id == "prebuilt-read"
            return SimpleNamespace(result=lambda: result)

    pages = ocr.ocr_pdf(str(pdf), client=FakeClient())
    assert pages == [{"page": 1, "text": "المادة 1\nنص المادة"}, {"page": 2, "text": ""}]
