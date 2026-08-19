"""Application FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from mycounts.api.auth import routeur as routeur_auth

app = FastAPI(title="mycounts", version="0.0.0")
app.include_router(routeur_auth)


@app.get("/health")
def health() -> dict[str, str]:
    return {"statut": "ok"}
