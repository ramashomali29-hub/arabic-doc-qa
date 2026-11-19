import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from rag import add_pdf, ask
import tempfile
from convert import pdf_to_word

app = FastAPI(title="Arabic Document Q&A")
os.makedirs("uploads", exist_ok=True)
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    if not data.startswith(b"%PDF") or len(data) > MAX_SIZE:
        raise HTTPException(400, "Only PDF files under 10 MB are allowed")
    safe_name = os.path.basename(file.filename)
    path = os.path.join("uploads", safe_name)
    with open(path, "wb") as f:
        f.write(data)
    return {"file": safe_name, "chunks": add_pdf(path)}


class Citation(BaseModel):
    file: str
    page: int
    score: float
    ocr: bool = False


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[Citation]
    sources: list[str]


@app.post("/ask", response_model=AskResponse)
def ask_question(q: Question):
    result = ask(q.question)
    # "sources" keeps the original human-readable format for existing clients
    result["sources"] = [f"{c['file']} - page {c['page']}" for c in result["citations"]]
    return result


@app.post("/convert")
async def convert_pdf_to_word(file: UploadFile = File(...)):
    # read the uploaded file
    data = await file.read()

    if len(data) > MAX_SIZE:
        return {"error": "File too large (max 10 MB)."}

    # basic validation: must be a real PDF
    if not data.startswith(b"%PDF"):
        return {"error": "The uploaded file is not a valid PDF."}

    # save the PDF to a temp file
    tmp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmp_dir, "input.pdf")
    with open(pdf_path, "wb") as f:
        f.write(data)

    # convert
    docx_path = os.path.join(tmp_dir, "output.docx")
    broken = pdf_to_word(pdf_path, docx_path)

    # the downloaded file keeps the original name but with .docx
    out_name = os.path.splitext(file.filename)[0] + ".docx"

    headers = {}
    if broken:
        headers["X-Warning"] = "Arabic text may be broken; this PDF likely needs OCR."

    return FileResponse(
        docx_path,
        filename=out_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )