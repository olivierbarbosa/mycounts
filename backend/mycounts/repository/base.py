"""Session de base de données et périmètre de l'appelant.

`Vue` est réexportée depuis `domain.perimetre` : elle appartient au domaine, mais tout le
code qui manipule un `Principal` la cherche naturellement ici.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from mycounts.config import charger_configuration
from mycounts.domain.perimetre import Vue


@dataclass(frozen=True)
class Principal:
    """Qui agit, dans quel foyer, et sur quel argent.

    Toute fonction de lecture du repository prend un `Principal` : le périmètre n'est
    jamais implicite, et une fonction qui l'oublierait se verrait à la signature.

    La vue vaut PERSONNELLE par défaut, et ce défaut est un choix de sûreté : un appelant
    qui oublierait de la transmettre verrait ses propres comptes, jamais ceux du foyer.
    L'inverse ferait fuiter par omission.
    """

    utilisateur_id: uuid.UUID
    foyer_id: uuid.UUID
    vue: Vue = Vue.PERSONNELLE


@lru_cache(maxsize=1)
def moteur() -> Engine:
    return create_engine(charger_configuration().database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def fabrique_de_sessions() -> sessionmaker[Session]:
    return sessionmaker(bind=moteur(), expire_on_commit=False)


def obtenir_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête, fermée à la fin."""
    session = fabrique_de_sessions()()
    try:
        yield session
    finally:
        session.close()


__all__ = ["Principal", "Vue", "fabrique_de_sessions", "moteur", "obtenir_session"]
