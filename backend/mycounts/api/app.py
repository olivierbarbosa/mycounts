"""Application FastAPI.

Au lot 0 elle n'expose qu'un contrôle de vie : il n'existe encore aucune donnée métier.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="mycounts", version="0.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"statut": "ok"}
