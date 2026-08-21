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
from mycounts.models.budget import (
    Categorie,
    Compte,
    CorrespondanceImport,
    Enveloppe,
    MouvementEnveloppe,
    Operation,
    Plafond,
    Recurrence,
)
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
    est_proprietaire: bool = False,
) -> Utilisateur:
    utilisateur = Utilisateur(
        foyer_id=foyer_id,
        courriel=courriel,
        nom_affichage=nom_affichage,
        empreinte_mot_de_passe=empreinte_mot_de_passe,
        est_proprietaire=est_proprietaire,
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


def foyer_de(session: Session, principal: Principal) -> Foyer:
    """Le foyer de l'appelant. Il existe forcément : un utilisateur sans foyer n'est pas
    un état que le schéma autorise."""
    return session.execute(
        select(Foyer).where(Foyer.id == principal.foyer_id)
    ).scalar_one()


def est_le_proprietaire(session: Session, principal: Principal) -> bool:
    """Le foyer appartient-il à l'appelant ?

    Auteur unique du droit d'administrer : la gestion des membres et la destruction du
    foyer passent toutes deux par ici, et deux implémentations de « est-ce l'admin ? »
    finiraient par diverger sur exactement le cas qui compte.
    """
    return bool(
        session.execute(
            select(Utilisateur.est_proprietaire).where(
                Utilisateur.id == principal.utilisateur_id,
                Utilisateur.foyer_id == principal.foyer_id,
            )
        ).scalar_one_or_none()
    )


def supprimer_le_foyer(session: Session, principal: Principal) -> None:
    """Efface le foyer et TOUT ce qu'il contient. Sans retour possible.

    Aucune sauvegarde, aucune corbeille, aucun délai de grâce : ce que cette fonction
    supprime a disparu. L'appelant est seul responsable d'avoir obtenu une confirmation —
    voir `DELETE /api/auth/foyer`, qui exige que le nom du foyer soit retapé.

    L'ordre suit les dépendances, des feuilles vers la racine. Il n'est pas confié aux
    `ON DELETE` : la plupart des clés du projet sont en RESTRICT, précisément pour qu'une
    suppression accidentelle bute au lieu de se propager. Cette fonction est le seul
    endroit qui a le droit de tout défaire, et elle le fait explicitement.

    Ce qui protège cette liste d'être incomplète est
    `test_la_suppression_ne_laisse_AUCUNE_ligne`, avec une portée mesurée : une table
    oubliée ici le fait rougir SI sa clé vers le foyer est en RESTRICT — la suppression
    bute alors sur la contrainte. Une table en CASCADE oubliée ne le fait PAS rougir,
    parce que PostgreSQL la nettoie de lui-même ; la ligne explicite est redondante dans
    ce cas, et son absence sans conséquence. Vérifié dans les deux sens le 21 août 2026 :
    retirer `Invitation` (CASCADE) laisse le test vert, retirer `Enveloppe` (RESTRICT) le
    fait échouer.
    """
    foyer_id = principal.foyer_id

    utilisateurs = select(Utilisateur.id).where(Utilisateur.foyer_id == foyer_id)
    comptes = select(Compte.id).where(Compte.foyer_id == foyer_id)
    categories = select(Categorie.id).where(Categorie.foyer_id == foyer_id)
    enveloppes = select(Enveloppe.id).where(Enveloppe.foyer_id == foyer_id)

    session.execute(
        delete(MouvementEnveloppe).where(MouvementEnveloppe.enveloppe_id.in_(enveloppes))
    )
    session.execute(delete(Enveloppe).where(Enveloppe.foyer_id == foyer_id))
    session.execute(delete(Operation).where(Operation.compte_id.in_(comptes)))
    session.execute(delete(Recurrence).where(Recurrence.compte_id.in_(comptes)))
    session.execute(delete(Plafond).where(Plafond.utilisateur_id.in_(utilisateurs)))
    # Un plafond de foyer n'appartient à personne en particulier : le retirer par son
    # utilisateur en laisserait derrière si un membre l'avait posé puis quitté le foyer.
    session.execute(delete(Plafond).where(Plafond.categorie_id.in_(categories)))
    session.execute(
        delete(CorrespondanceImport).where(CorrespondanceImport.foyer_id == foyer_id)
    )
    session.execute(delete(Compte).where(Compte.foyer_id == foyer_id))
    session.execute(delete(Categorie).where(Categorie.foyer_id == foyer_id))
    session.execute(delete(Invitation).where(Invitation.foyer_id == foyer_id))
    session.execute(delete(SessionWeb).where(SessionWeb.utilisateur_id.in_(utilisateurs)))
    session.execute(delete(Utilisateur).where(Utilisateur.foyer_id == foyer_id))
    session.execute(delete(Foyer).where(Foyer.id == foyer_id))
    session.flush()

def comptes_joints(session: Session, principal: Principal) -> list[Compte]:
    """Les comptes joints du foyer, archivés compris.

    Sans filtre sur l'archivage : la dissolution doit emporter TOUT le partage, et un
    compte archivé reste un compte partagé — il porte de l'argent et une histoire.
    """
    return list(
        session.execute(
            select(Compte).where(
                Compte.foyer_id == principal.foyer_id, Compte.prive.is_(False)
            ).order_by(Compte.nom)
        ).scalars()
    )


def dissoudre_le_partage(session: Session, principal: Principal) -> int:
    """Supprime les comptes JOINTS du foyer. Ne touche à personne ni à rien d'autre.

    C'est la correction du 21 août 2026 : « supprimer le foyer » effaçait aussi les
    comptes PERSONNELS et les utilisateurs, donc déconnectait celui qui voulait seulement
    arrêter de partager. Le foyer est le conteneur racine de tout en base — mais c'est un
    fait de schéma, pas une intention de l'utilisateur, et l'interface n'a pas à le lui
    faire payer (ERREURS.md #044).

    Les membres RESTENT membres, avec leur compte, leurs comptes personnels, leurs
    catégories et leurs enveloppes. Ce qui disparaît est exactement ce que la vue
    « comptes joints » montre — cette vue étant un filtre sur `Compte.prive`, la dissoudre
    n'est rien d'autre que supprimer ces comptes-là.

    L'appelant vérifie AVANT d'appeler qu'aucun de ces comptes ne porte de vraie
    opération : ici on ne refuse rien, on exécute. Voir `DELETE /api/auth/foyer/partage`.
    """
    joints = select(Compte.id).where(
        Compte.foyer_id == principal.foyer_id, Compte.prive.is_(False)
    )

    session.execute(delete(Operation).where(Operation.compte_id.in_(joints)))
    session.execute(delete(Recurrence).where(Recurrence.compte_id.in_(joints)))
    # Même cast que `supprimer_session_web` : un DELETE renvoie toujours un
    # `CursorResult`, seul porteur de `rowcount`, que `Session.execute` type en `Result`.
    efface = cast(
        "CursorResult[Any]",
        session.execute(
            delete(Compte).where(
                Compte.foyer_id == principal.foyer_id, Compte.prive.is_(False)
            )
        ),
    )
    session.flush()
    return efface.rowcount


def supprimer_mon_compte(session: Session, principal: Principal) -> None:
    """Efface l'appelant et ce qui n'appartient qu'à lui. Sans retour possible.

    Distincte de `supprimer_le_foyer`, et c'est tout l'objet du lot : arrêter de partager
    et disparaître sont deux intentions différentes, et les confondre faisait perdre son
    compte à qui voulait seulement la première.

    DERNIER MEMBRE : le foyer part avec lui. Le laisser derrière créerait un foyer que
    personne ne peut plus atteindre — ni pour le vider, ni pour le détruire —, et ses
    comptes joints survivraient à tous leurs propriétaires.

    Ce qui suit l'appelant : ses comptes PRIVÉS et leurs opérations, ses plafonds, ses
    sessions. Ce qui reste au foyer : les comptes joints, les catégories et les enveloppes
    — elles sont partagées, et les emporter viderait l'écran des autres membres. Les
    comptes joints qu'il avait ouverts restent aussi : l'argent est celui du foyer, pas le
    sien. Le prix est que `proprietaire_id` pointe alors vers un utilisateur effacé, ce
    qui empêche de les supprimer ; c'est pourquoi la route refuse de laisser partir le
    propriétaire tant qu'il reste des membres.
    """
    if len(membres_du_foyer(session, principal)) == 1:
        supprimer_le_foyer(session, principal)
        return

    moi = principal.utilisateur_id
    mes_comptes = select(Compte.id).where(
        Compte.foyer_id == principal.foyer_id,
        Compte.prive.is_(True),
        Compte.proprietaire_id == moi,
    )

    session.execute(delete(Operation).where(Operation.compte_id.in_(mes_comptes)))
    session.execute(delete(Recurrence).where(Recurrence.compte_id.in_(mes_comptes)))
    session.execute(delete(Plafond).where(Plafond.utilisateur_id == moi))
    session.execute(
        delete(Compte).where(
            Compte.foyer_id == principal.foyer_id,
            Compte.prive.is_(True),
            Compte.proprietaire_id == moi,
        )
    )
    session.execute(delete(SessionWeb).where(SessionWeb.utilisateur_id == moi))
    session.execute(delete(Utilisateur).where(Utilisateur.id == moi))
    session.flush()
