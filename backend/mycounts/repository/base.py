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
from mycounts.domain.espaces import RoleEspace, TypeEspace
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
    espace_id: uuid.UUID = uuid.UUID(int=0)
    role: RoleEspace = RoleEspace.PROPRIETAIRE
    type_espace: TypeEspace = TypeEspace.PERSONNEL
    # Compatibilité temporaire des appels internes et tests antérieurs au lot espaces.
    # Le code V1 ne doit plus utiliser ce champ pour autoriser une lecture.
    foyer_id: uuid.UUID = uuid.UUID(int=0)
    vue: Vue = Vue.PERSONNELLE
    mode_legacy: bool = False

    def __post_init__(self) -> None:
        if self.espace_id.int == 0 and self.foyer_id.int != 0:
            object.__setattr__(self, "mode_legacy", True)
        identifiant = (
            self.espace_id
            if self.espace_id.int != 0
            else (self.foyer_id if self.foyer_id.int != 0 else None)
        )
        if identifiant is None:
            raise ValueError("Un principal doit désigner un espace.")
        object.__setattr__(self, "espace_id", identifiant)
        if self.foyer_id.int == 0:
            object.__setattr__(self, "foyer_id", identifiant)
        if self.vue is Vue.FOYER and self.type_espace is TypeEspace.PERSONNEL:
            object.__setattr__(self, "type_espace", TypeEspace.FOYER)

    @property
    def est_personnel(self) -> bool:
        return self.type_espace is TypeEspace.PERSONNEL


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
