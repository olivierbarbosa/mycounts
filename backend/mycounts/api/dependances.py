"""Dépendances FastAPI : session de base et utilisateur authentifié."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from mycounts.domain.securite import empreinte_jeton, maintenant
from mycounts.repository import auth as depot
from mycounts.repository import espaces as depot_espaces
from mycounts.repository.base import Principal, Vue, obtenir_session

NOM_COOKIE = "mycounts_session"

SessionBase = Annotated[Session, Depends(obtenir_session)]


"""En-tête par lequel le client annonce le périmètre qu'il regarde."""
EN_TETE_VUE = "X-Mycounts-Vue"
EN_TETE_ESPACE = "X-Mycounts-Espace"


def principal_courant(
    session: SessionBase,
    mycounts_session: Annotated[str | None, Cookie(alias=NOM_COOKIE)] = None,
    vue_demandee: Annotated[str | None, Header(alias=EN_TETE_VUE)] = None,
    espace_demande: Annotated[str | None, Header(alias=EN_TETE_ESPACE)] = None,
) -> Principal:
    """Utilisateur authentifié, sur le périmètre demandé, ou 401.

    Le message est identique quel que soit le motif (cookie absent, session inconnue,
    session expirée) : distinguer ces cas renseignerait un attaquant sur l'existence
    d'un compte ou la validité d'un jeton volé.

    **L'espace arrive par un en-tête, pas par le cookie de session.** Son UUID n'est pas
    une autorisation : l'appartenance active est relue en base et verrouillée pour toute
    la requête. Le garder hors de la session évite de recréer l'authentification à chaque
    bascule d'affichage.

    Seule l'absence d'en-tête choisit l'espace personnel. Un UUID mal formé, inconnu ou
    non autorisé reçoit le même 404 neutre : l'en-tête ne devient ni une fuite ni un
    oracle, et une écriture destinée à un foyer révoqué ne change jamais de périmètre.
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

    identifiant_espace: uuid.UUID | None = None
    if espace_demande is not None:
        try:
            identifiant_espace = uuid.UUID(espace_demande.strip())
        except ValueError:
            # Même réponse qu'un UUID inexistant ou appartenant à autrui : aucun oracle,
            # et surtout aucune écriture destinée à un foyer ne retombe en personnel.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espace indisponible.",
            ) from None

    principal = depot_espaces.principal_pour(
        session,
        utilisateur_id=utilisateur.id,
        espace_id=identifiant_espace,
    )
    if principal is not None:
        return principal
    if espace_demande is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espace indisponible.",
        )

    # Les bases antérieures à la migration n'ont pas encore d'espace personnel. Ce
    # repli disparaîtra avec les colonnes legacy ; il ne peut viser que le foyer déjà
    # lié à l'identité authentifiée.
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
