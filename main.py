import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from rag import add_pdf, ask

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


@app.post("/ask")
def ask_question(q: Question):
    answer, sources = ask(q.question)
    return {"answer": answer, "sources": sources}