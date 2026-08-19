"""Accès aux données d'authentification.

Seul endroit du projet autorisé à construire une requête. Chaque lecture porteuse de
données de foyer prend un `Principal` et applique son périmètre.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.orm import Session

from mycounts.models.auth import Foyer, Invitation, SessionWeb, Utilisateur
from mycounts.repository.base import Principal


def creer_foyer(session: Session, nom: str) -> Foyer:
    foyer = Foyer(nom=nom)
    session.add(foyer)
    session.flush()
    return foyer


def creer_utilisateur(
    session: Session,
    *,
    foyer_id: uuid.UUID,
    courriel: str,
    nom_affichage: str,
    empreinte_mot_de_passe: str,
) -> Utilisateur:
    utilisateur = Utilisateur(
        foyer_id=foyer_id,
        courriel=courriel,
        nom_affichage=nom_affichage,
        empreinte_mot_de_passe=empreinte_mot_de_passe,
    )
    session.add(utilisateur)
    session.flush()
    return utilisateur


def utilisateur_par_courriel(session: Session, courriel: str) -> Utilisateur | None:
    """Recherche par adresse — sans périmètre, car c'est le point d'entrée de la connexion.

    Le courriel reçu doit avoir été normalisé par l'appelant : cette fonction ne le fait
    pas, pour que la normalisation ait un auteur unique (domain/securite.py).
    """
    return session.execute(
        select(Utilisateur).where(Utilisateur.courriel == courriel, Utilisateur.actif.is_(True))
    ).scalar_one_or_none()


def utilisateur_par_id(session: Session, utilisateur_id: uuid.UUID) -> Utilisateur | None:
    return session.execute(
        select(Utilisateur).where(Utilisateur.id == utilisateur_id, Utilisateur.actif.is_(True))
    ).scalar_one_or_none()


def enregistrer_session_web(
    session: Session, *, utilisateur_id: uuid.UUID, empreinte: str, expire_le: dt.datetime
) -> SessionWeb:
    session_web = SessionWeb(
        utilisateur_id=utilisateur_id, empreinte_jeton=empreinte, expire_le=expire_le
    )
    session.add(session_web)
    session.flush()
    return session_web


def session_web_active(
    session: Session, *, empreinte: str, a_l_instant: dt.datetime
) -> tuple[SessionWeb, Utilisateur] | None:
    """Session non expirée et son utilisateur, ou None.

    L'expiration est filtrée en SQL : une session périmée ne doit jamais remonter jusqu'à
    l'appelant, où quelqu'un pourrait oublier de la vérifier.
    """
    ligne = session.execute(
        select(SessionWeb, Utilisateur)
        .join(Utilisateur, Utilisateur.id == SessionWeb.utilisateur_id)
        .where(
            SessionWeb.empreinte_jeton == empreinte,
            SessionWeb.expire_le > a_l_instant,
            Utilisateur.actif.is_(True),
        )
    ).one_or_none()
    if ligne is None:
        return None
    return ligne[0], ligne[1]


def supprimer_session_web(session: Session, *, empreinte: str) -> int:
    """Supprime la session et renvoie le nombre de lignes touchées (0 ou 1)."""
    # `Session.execute` est typé `Result`, mais un DELETE renvoie toujours un
    # `CursorResult`, seul porteur de `rowcount`. Le cast documente ce fait au lieu de
    # le taire par un « type: ignore » nu, que le garde-fou n°5 refuse.
    resultat = cast(
        "CursorResult[Any]",
        session.execute(delete(SessionWeb).where(SessionWeb.empreinte_jeton == empreinte)),
    )
    return resultat.rowcount


def purger_sessions_expirees(session: Session, *, a_l_instant: dt.datetime) -> int:
    """Supprime les sessions expirées. Renvoie le nombre supprimé."""
    resultat = cast(
        "CursorResult[Any]",
        session.execute(delete(SessionWeb).where(SessionWeb.expire_le <= a_l_instant)),
    )
    return resultat.rowcount


def creer_invitation(
    session: Session,
    *,
    foyer_id: uuid.UUID,
    creee_par_id: uuid.UUID,
    empreinte_code: str,
    expire_le: dt.datetime,
) -> Invitation:
    invitation = Invitation(
        foyer_id=foyer_id,
        creee_par_id=creee_par_id,
        empreinte_code=empreinte_code,
        expire_le=expire_le,
    )
    session.add(invitation)
    session.flush()
    return invitation


def invitation_utilisable(
    session: Session, *, empreinte_code: str, a_l_instant: dt.datetime
) -> Invitation | None:
    """Invitation ni expirée ni déjà consommée.

    Les deux conditions sont en SQL pour la même raison que l'expiration de session :
    une invitation inutilisable ne doit pas pouvoir arriver jusqu'à un appelant distrait.
    """
    return session.execute(
        select(Invitation).where(
            Invitation.empreinte_code == empreinte_code,
            Invitation.expire_le > a_l_instant,
            Invitation.utilisee_le.is_(None),
        )
    ).scalar_one_or_none()


def marquer_invitation_utilisee(
    session: Session, *, invitation: Invitation, a_l_instant: dt.datetime
) -> None:
    invitation.utilisee_le = a_l_instant
    session.flush()


def membres_du_foyer(session: Session, principal: Principal) -> list[Utilisateur]:
    """Membres du foyer de l'appelant. Périmètre appliqué, jamais optionnel."""
    foyer_id = principal.foyer_id
    return list(
        session.execute(
            select(Utilisateur)
            .where(Utilisateur.foyer_id == foyer_id, Utilisateur.actif.is_(True))
            .order_by(Utilisateur.cree_le)
        ).scalars()
    )
