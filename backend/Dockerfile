FROM python:3.12-slim

# Don't write .pyc files; flush logs immediately so `docker compose logs` is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Copy requirements first so Docker caches the (slow) install layer
# until the requirements actually change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user: if the app is compromised, the attacker has fewer rights.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# Apply pending migrations, then start the server. `exec` lets uvicorn receive stop signals.
# Hosts like Render tell us which port to use through $PORT; locally we default to 8000.
# --proxy-headers makes uvicorn read the real client IP from X-Forwarded-For (needed for
# per-client login limits when running behind a hosting proxy).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
