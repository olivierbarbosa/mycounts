"""Compteurs PostgreSQL des échecs de connexion."""

from __future__ import annotations

import datetime as dt
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mycounts.domain.limitation_auth import Portee
from mycounts.models.auth import TentativeConnexion


def nombre_echecs(
    session: Session,
    *,
    empreinte: str,
    portee: Portee,
    fenetre_debut: dt.datetime,
) -> int:
    return int(
        session.execute(
            select(TentativeConnexion.echecs).where(
                TentativeConnexion.empreinte == empreinte,
                TentativeConnexion.portee == portee.value,
                TentativeConnexion.fenetre_debut == fenetre_debut,
            )
        ).scalar_one_or_none()
        or 0
    )


def compter_un_echec(
    session: Session,
    *,
    empreinte: str,
    portee: Portee,
    fenetre_debut: dt.datetime,
) -> int:
    """Incrémente atomiquement et rend la nouvelle valeur."""
    insertion = insert(TentativeConnexion).values(
        empreinte=empreinte,
        portee=portee.value,
        fenetre_debut=fenetre_debut,
        echecs=1,
    )
    requete = insertion.on_conflict_do_update(
        index_elements=[
            TentativeConnexion.empreinte,
            TentativeConnexion.portee,
            TentativeConnexion.fenetre_debut,
        ],
        set_={"echecs": TentativeConnexion.echecs + 1},
    ).returning(TentativeConnexion.echecs)
    return int(session.execute(requete).scalar_one())


def oublier(
    session: Session, *, empreinte: str, portee: Portee
) -> int:
    resultat = cast(
        "CursorResult[Any]",
        session.execute(
            delete(TentativeConnexion).where(
                TentativeConnexion.empreinte == empreinte,
                TentativeConnexion.portee == portee.value,
            )
        ),
    )
    return resultat.rowcount


def purger_avant(session: Session, *, avant: dt.datetime) -> int:
    resultat = cast(
        "CursorResult[Any]",
        session.execute(
            delete(TentativeConnexion).where(TentativeConnexion.fenetre_debut < avant)
        ),
    )
    return resultat.rowcount
