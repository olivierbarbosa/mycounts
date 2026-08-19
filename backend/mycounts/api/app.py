"""Application FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from mycounts.api.agenda import routeur as routeur_agenda
from mycounts.api.auth import routeur as routeur_auth
from mycounts.api.budget import routeur as routeur_budget
from mycounts.api.plafonds import routeur as routeur_plafonds

app = FastAPI(title="mycounts", version="0.0.0")

# UN seul point de montage pour l'API. La liste des chemins à relayer vivait auparavant
# dans vite.config.ts : c'était une seconde source de vérité, et elle a divergé dès la
# première route ajoutée — /comptes renvoyait la page HTML au lieu du JSON.
# Voir ERREURS.md #015.
PREFIXE_API = "/api"
app.include_router(routeur_auth, prefix=PREFIXE_API)
app.include_router(routeur_budget, prefix=PREFIXE_API)
app.include_router(routeur_agenda, prefix=PREFIXE_API)
app.include_router(routeur_plafonds, prefix=PREFIXE_API)


@app.get("/health")
def health() -> dict[str, str]:
    return {"statut": "ok"}
