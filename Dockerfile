# Builds the backend (api/) when the build starts from the top of the repo.
# Same result as api/Dockerfile; kept so the deploy works whichever path Cloud Build uses.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app ./app

# Cloud Run tells the app which port to use through $PORT
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
