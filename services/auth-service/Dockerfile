FROM python:3.11-slim
WORKDIR /app

COPY services/auth-service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Underscore package names so `services.auth_service` / `packages.shared_utils` import cleanly
COPY packages/shared-utils /app/packages/shared_utils
COPY packages/shared-types /app/packages/shared_types
COPY services/auth-service /app/services/auth_service
RUN printf '' > /app/packages/__init__.py && printf '' > /app/services/__init__.py

ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["uvicorn", "services.auth_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
