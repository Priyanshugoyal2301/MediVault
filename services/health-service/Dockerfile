FROM python:3.11-slim
WORKDIR /app

COPY services/health-service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY packages/shared-utils /app/packages/shared_utils
COPY packages/shared-types /app/packages/shared_types
COPY services/health-service /app/services/health_service
COPY services/ai-service /app/services/ai_service
RUN printf '' > /app/packages/__init__.py && printf '' > /app/services/__init__.py

ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["uvicorn", "services.health_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
