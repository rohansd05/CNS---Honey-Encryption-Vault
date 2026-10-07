FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root system user and group
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "HoneyVault App User" appuser

# Install backend dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application source tree
COPY backend/ /app/

# Assign ownership to appuser
RUN chown -R appuser:appuser /app

# Run as non-root user
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && if [ \"${DEMO_MODE}\" = \"true\" ] && [ -f scripts/seed_demo.py ]; then python -m scripts.seed_demo --if-missing; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
