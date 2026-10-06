FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root system user and group
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "Honeychecker App User" appuser

# Install honeychecker dependencies
COPY honeychecker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy honeychecker application source and shared backend/honeycore module
COPY honeychecker/ /app/
COPY backend/honeycore/ /app/honeycore/
COPY backend/honeycore/ /app/backend/honeycore/

# Ensure PYTHONPATH includes both /app and /app/backend
ENV PYTHONPATH="/app:/app/backend"

# Assign ownership to appuser
RUN chown -R appuser:appuser /app

# Run as non-root user
USER appuser

EXPOSE 8001

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
