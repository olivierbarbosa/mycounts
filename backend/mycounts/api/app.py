"""Application FastAPI."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from mycounts.api.agenda import routeur as routeur_agenda
from mycounts.api.auth import routeur as routeur_auth
from mycounts.api.budget import routeur as routeur_budget
from mycounts.api.dependances import SessionBase
from mycounts.api.enveloppes import routeur as routeur_enveloppes
from mycounts.api.espaces import routeur as routeur_espaces
from mycounts.api.import_releve import routeur as routeur_import
from mycounts.api.plafonds import routeur as routeur_plafonds
from mycounts.api.statistiques import routeur as routeur_statistiques
from mycounts.domain import limitation_auth
from mycounts.domain.securite import maintenant
from mycounts.repository import limitation_auth as depot_limitation
from mycounts.repository import sante as depot_sante

_journal = logging.getLogger("mycounts")


class BaseNonMigree(RuntimeError):
    """La base ne correspond pas aux migrations du code en cours d'exécution."""


def verifier_migrations_appliquees() -> None:
    """Refuse de démarrer si la base n'est pas à la dernière migration.

    Sans ce contrôle, l'application démarre normalement et échoue plus tard, à la
    première requête touchant une colonne absente — avec une erreur 500 opaque, loin de
    sa cause. C'est arrivé sur la base de démonstration : une colonne ajoutée le matin,
    la migration jamais appliquée là, et un « Not Found » incompréhensible à l'écran le
    soir. Voir ERREURS.md #022.

    Une base vierge est acceptée : c'est le cas des tests, qui migrent ensuite.
    """
    from mycounts.repository.base import moteur

    racine = Path(__file__).resolve().parents[3]
    attendue = ScriptDirectory.from_config(Config(str(racine / "alembic.ini"))).get_current_head()
    if attendue is None:
        return

    with moteur().connect() as connexion:
        if not inspect(connexion).has_table("alembic_version"):
            return
        appliquee = MigrationContext.configure(connexion).get_current_revision()

    if appliquee != attendue:
        raise BaseNonMigree(
            f"La base est en révision {appliquee!r}, le code attend {attendue!r}. "
            f"Lancer « make migrer » (ou « make demo-migrer » pour la démonstration)."
        )


@asynccontextmanager
async def cycle_de_vie(_: FastAPI) -> AsyncIterator[None]:
    verifier_migrations_appliquees()
    yield


app = FastAPI(title="mycounts", version="0.0.0", lifespan=cycle_de_vie)

# UN seul point de montage pour l'API. La liste des chemins à relayer vivait auparavant
# dans vite.config.ts : c'était une seconde source de vérité, et elle a divergé dès la
# première route ajoutée — /comptes renvoyait la page HTML au lieu du JSON.
# Voir ERREURS.md #015.
PREFIXE_API = "/api"
app.include_router(routeur_auth, prefix=PREFIXE_API)
app.include_router(routeur_budget, prefix=PREFIXE_API)
app.include_router(routeur_agenda, prefix=PREFIXE_API)
app.include_router(routeur_plafonds, prefix=PREFIXE_API)
app.include_router(routeur_enveloppes, prefix=PREFIXE_API)
app.include_router(routeur_statistiques, prefix=PREFIXE_API)
app.include_router(routeur_import, prefix=PREFIXE_API)
app.include_router(routeur_espaces, prefix=PREFIXE_API)


@app.get("/health")
def health(session: SessionBase) -> dict[str, str]:
    """Confirme que l'API peut réellement joindre PostgreSQL.

    Un processus HTTP vivant devant une base coupée n'est pas sain : Traefik et Docker
    doivent cesser de lui envoyer du trafic au lieu d'attendre la première route métier
    en erreur 500.
    """
    try:
        depot_sante.verifier_base(session)
        depot_limitation.purger_avant(
            session,
            avant=limitation_auth.debut_de_fenetre(maintenant()),
        )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        _journal.exception("Sonde de santé PostgreSQL en échec")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données indisponible.",
        ) from None
    return {"statut": "ok"}
