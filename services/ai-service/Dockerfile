FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/ai-service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY packages/shared-utils /app/packages/shared_utils
COPY packages/shared-types /app/packages/shared_types
COPY services/ai-service /app/services/ai_service
COPY data/knowledge-base /app/data/knowledge-base
RUN printf '' > /app/packages/__init__.py && printf '' > /app/services/__init__.py

ENV PYTHONPATH=/app
EXPOSE 8003
CMD ["uvicorn", "services.ai_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
