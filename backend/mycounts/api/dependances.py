"""Dépendances FastAPI : session de base et utilisateur authentifié."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mycounts.domain.securite import empreinte_jeton, maintenant
from mycounts.repository import auth as depot
from mycounts.repository.base import Principal, obtenir_session

NOM_COOKIE = "mycounts_session"

SessionBase = Annotated[Session, Depends(obtenir_session)]


def principal_courant(
    session: SessionBase,
    mycounts_session: Annotated[str | None, Cookie(alias=NOM_COOKIE)] = None,
) -> Principal:
    """Utilisateur authentifié, ou 401.

    Le message est identique quel que soit le motif (cookie absent, session inconnue,
    session expirée) : distinguer ces cas renseignerait un attaquant sur l'existence
    d'un compte ou la validité d'un jeton volé.
    """
    refus = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise."
    )
    if not mycounts_session:
        raise refus

    trouve = depot.session_web_active(
        session, empreinte=empreinte_jeton(mycounts_session), a_l_instant=maintenant()
    )
    if trouve is None:
        raise refus

    _, utilisateur = trouve
    return Principal(utilisateur_id=utilisateur.id, foyer_id=utilisateur.foyer_id)


PrincipalCourant = Annotated[Principal, Depends(principal_courant)]
