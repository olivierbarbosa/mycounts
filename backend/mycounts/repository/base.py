"""Session de base de données et périmètre de l'appelant."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from mycounts.config import charger_configuration


@dataclass(frozen=True)
class Principal:
    """Qui agit, et dans quel foyer.

    Toute fonction de lecture du repository prend un `Principal` : le périmètre n'est
    jamais implicite, et une fonction qui l'oublierait se verrait à la signature.
    """

    utilisateur_id: uuid.UUID
    foyer_id: uuid.UUID


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
