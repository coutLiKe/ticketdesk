from fastapi import FastAPI

from app.config import settings

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: answers 'is the process up?' Used by Docker and CI."""
    return {"status": "ok"}
