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
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
