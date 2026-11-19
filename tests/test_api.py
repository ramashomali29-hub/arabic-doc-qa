import sys
import types

fake_rag = types.ModuleType("rag")
fake_rag.add_pdf = lambda path: 5
fake_rag.ask = lambda question: {
    "answer": "test answer",
    "grounded": True,
    "citations": [{"file": "doc.pdf", "page": 1, "score": 0.81, "ocr": False}],
}
sys.modules["rag"] = fake_rag

# convert.py needs Tesseract/Poppler, which CI does not have
fake_convert = types.ModuleType("convert")
fake_convert.pdf_to_word = lambda pdf_path, docx_path: False
sys.modules["convert"] = fake_convert

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)


def test_ask_returns_answer_and_sources():
    r = client.post("/ask", json={"question": "ما هي نسبة الضريبة؟"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "test answer"
    assert body["grounded"] is True
    assert body["citations"][0] == {"file": "doc.pdf", "page": 1, "score": 0.81, "ocr": False}
    assert body["sources"] == ["doc.pdf - page 1"]


def test_empty_question_rejected():
    r = client.post("/ask", json={"question": ""})
    assert r.status_code == 422


def test_too_long_question_rejected():
    r = client.post("/ask", json={"question": "a" * 501})
    assert r.status_code == 422


def test_upload_valid_pdf():
    files = {"file": ("law.pdf", b"%PDF-1.4 test content", "application/pdf")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200
    assert r.json()["chunks"] == 5


def test_upload_rejects_non_pdf():
    files = {"file": ("fake.pdf", b"not a real pdf", "application/pdf")}
    r = client.post("/upload", files=files)
    assert r.status_code == 400


def test_upload_rejects_large_file():
    big = b"%PDF" + b"0" * (10 * 1024 * 1024)
    files = {"file": ("big.pdf", big, "application/pdf")}
    r = client.post("/upload", files=files)
    assert r.status_code == 400


def test_upload_blocks_path_traversal():
    files = {"file": ("../../evil.pdf", b"%PDF-1.4", "application/pdf")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200
    assert r.json()["file"] == "evil.pdf"