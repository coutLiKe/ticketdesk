from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors(app: FastAPI, origins_csv: str) -> None:
    """Allow the listed browser origins to call this API from another domain.

    Browsers block a page on one domain from reading responses from another unless the
    API opts in (CORS). We list exact origins (never "*"), and since we use bearer tokens
    rather than cookies, credentials are not allowed.
    """
    origins = [o.strip().rstrip("/") for o in origins_csv.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["Authorization", "Content-Type"],
        )
