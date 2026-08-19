"""Application FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from mycounts.api.auth import routeur as routeur_auth
from mycounts.api.budget import routeur as routeur_budget

app = FastAPI(title="mycounts", version="0.0.0")
app.include_router(routeur_auth)
app.include_router(routeur_budget)


@app.get("/health")
def health() -> dict[str, str]:
    return {"statut": "ok"}
