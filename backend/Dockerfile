# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./backend/app/
COPY ingestion/ ./backend/ingestion/

# Copy the SQLite database — build fails explicitly if this file is absent.
# Run `python -m backend.ingestion.ingest` locally before building the image.
COPY data/wind_data.db ./backend/data/wind_data.db

# Environment variable defaults (override at runtime)
ENV WIND_DB_PATH=/app/backend/data/wind_data.db
ENV FRONTEND_ORIGIN=http://localhost:5173
ENV DECISION_CUTOFF_TIME=09:20

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
