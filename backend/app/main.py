from fastapi import FastAPI

from app.config import settings
from app.routers import assets, auth, comments, ticket_assets, tickets, users

app = FastAPI(title=settings.app_name)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(comments.router)
app.include_router(assets.router)
app.include_router(ticket_assets.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: answers 'is the process up?' Used by Docker and CI."""
    return {"status": "ok"}
