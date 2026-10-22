FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# CPU-only PyTorch keeps the image several GB smaller
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py rag.py ./

# Run as a non-root user
RUN useradd --create-home appuser \
    && mkdir -p uploads chroma_db /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]