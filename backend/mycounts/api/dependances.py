"""Dépendances FastAPI : session de base et utilisateur authentifié."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from mycounts.domain.securite import empreinte_jeton, maintenant
from mycounts.repository import auth as depot
from mycounts.repository.base import Principal, Vue, obtenir_session

NOM_COOKIE = "mycounts_session"

SessionBase = Annotated[Session, Depends(obtenir_session)]


"""En-tête par lequel le client annonce le périmètre qu'il regarde."""
EN_TETE_VUE = "X-Mycounts-Vue"


def principal_courant(
    session: SessionBase,
    mycounts_session: Annotated[str | None, Cookie(alias=NOM_COOKIE)] = None,
    vue_demandee: Annotated[str | None, Header(alias=EN_TETE_VUE)] = None,
) -> Principal:
    """Utilisateur authentifié, sur le périmètre demandé, ou 401.

    Le message est identique quel que soit le motif (cookie absent, session inconnue,
    session expirée) : distinguer ces cas renseignerait un attaquant sur l'existence
    d'un compte ou la validité d'un jeton volé.

    **La vue arrive par un en-tête, pas par le cookie de session.** Elle n'est pas un
    secret et ne donne accès à rien de plus : le foyer et l'utilisateur viennent de la
    session, et la vue ne fait que choisir LEQUEL de leurs deux périmètres regarder. La
    mettre dans la session obligerait à réécrire un cookie à chaque bascule, donc à
    invalider et recréer l'authentification pour un changement d'affichage.

    Une valeur inconnue ou absente retombe sur la vue PERSONNELLE. Le défaut est un choix
    de sûreté : au pire, on montre à quelqu'un ses propres comptes. L'inverse ferait fuiter
    par simple faute de frappe dans un en-tête.
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
    return Principal(
        utilisateur_id=utilisateur.id,
        foyer_id=utilisateur.foyer_id,
        vue=_vue_ou_personnelle(vue_demandee),
    )


def _vue_ou_personnelle(demandee: str | None) -> Vue:
    """Traduit l'en-tête en vue, sans jamais lever.

    Une valeur inconnue ne produit PAS une erreur 400 : ce serait transformer une faute
    d'affichage en panne. Elle retombe sur la vue personnelle, qui ne montre à l'appelant
    que ce qui lui appartient déjà.
    """
    if demandee is None:
        return Vue.PERSONNELLE
    try:
        return Vue(demandee.strip().lower())
    except ValueError:
        return Vue.PERSONNELLE


PrincipalCourant = Annotated[Principal, Depends(principal_courant)]
