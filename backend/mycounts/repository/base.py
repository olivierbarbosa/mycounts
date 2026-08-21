"""Session de base de données et périmètre de l'appelant."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from mycounts.config import charger_configuration


class Vue(StrEnum):
    """Sur quel argent on travaille.

    Deux mondes ÉTANCHES, décidé par Olivier le 21 août 2026 : on répond à « combien j'ai »
    ou à « combien on a », jamais aux deux mélangés. Un solde qui additionnerait le compte
    joint et le livret personnel ferait croire à une aisance qui n'appartient à personne.

    La vue n'est pas un filtre d'affichage : elle fait partie du PÉRIMÈTRE, au même titre
    que le foyer. C'est pourquoi elle vit dans le `Principal` et non dans un paramètre de
    route — une fonction qui l'oublierait rendrait des comptes qui ne sont pas les siens,
    et le seul moyen d'empêcher cet oubli est qu'elle ne puisse pas être omise.
    """

    PERSONNELLE = "personnelle"
    """Les comptes privés de la personne connectée."""

    FOYER = "foyer"
    """Les comptes joints du foyer, ceux que tous les membres voient."""


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
