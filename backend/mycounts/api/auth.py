"""Routes d'authentification.

Aucune inscription publique : on entre par un code d'invitation, ou pas du tout.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from mycounts.api.dependances import NOM_COOKIE, PrincipalCourant, SessionBase
from mycounts.api.schemas import (
    DemandeAdhesion,
    DemandeConnexion,
    InvitationCreee,
    UtilisateurPublic,
)
from mycounts.config import charger_configuration
from mycounts.domain.securite import (
    DUREE_SESSION,
    empreinte_jeton,
    engendrer_jeton,
    expiration_invitation,
    expiration_session,
    hacher_mot_de_passe,
    maintenant,
    verifier_mot_de_passe,
)
from mycounts.repository import auth as depot

routeur = APIRouter(prefix="/auth", tags=["authentification"])

# Empreinte d'un mot de passe qui n'est celui de personne. Sert à faire travailler Argon2
# même quand le compte n'existe pas : sans ça, une connexion sur adresse inconnue
# répondrait en 1 ms et une adresse connue en 60 ms, ce qui révèle quelles adresses ont
# un compte. La valeur est calculée une fois au démarrage.
_EMPREINTE_LEURRE = hacher_mot_de_passe("mot de passe leurre, sans usage reel")


def _pose_le_cookie(reponse: Response, jeton: str) -> None:
    configuration = charger_configuration()
    reponse.set_cookie(
        key=NOM_COOKIE,
        value=jeton,
        httponly=True,  # inaccessible au JavaScript : un XSS ne peut pas voler la session
        samesite="lax",  # bloque l'envoi depuis un site tiers (CSRF)
        secure=configuration.environnement != "developpement",  # HTTPS seul en production
        max_age=int(DUREE_SESSION.total_seconds()),
        path="/",
    )


@routeur.post("/connexion", response_model=UtilisateurPublic)
def connexion(
    demande: DemandeConnexion, reponse: Response, session: SessionBase
) -> UtilisateurPublic:
    """Ouvre une session.

    La réponse est identique que l'adresse soit inconnue ou le mot de passe faux :
    distinguer les deux permettrait d'énumérer les comptes existants.
    """
    refus = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects."
    )

    # `demande.courriel` est déjà validé ET normalisé par le schéma, qui délègue au
    # domaine. Re-normaliser ici donnerait l'impression d'un second auteur de la règle.
    utilisateur = depot.utilisateur_par_courriel(session, demande.courriel)
    empreinte = utilisateur.empreinte_mot_de_passe if utilisateur else _EMPREINTE_LEURRE
    mot_de_passe_correct = verifier_mot_de_passe(empreinte, demande.mot_de_passe)

    if utilisateur is None or not mot_de_passe_correct:
        raise refus

    jeton = engendrer_jeton()
    depot.enregistrer_session_web(
        session,
        utilisateur_id=utilisateur.id,
        empreinte=empreinte_jeton(jeton),
        expire_le=expiration_session(),
    )
    session.commit()
    _pose_le_cookie(reponse, jeton)

    return UtilisateurPublic(
        id=utilisateur.id,
        courriel=utilisateur.courriel,
        nom_affichage=utilisateur.nom_affichage,
        foyer_id=utilisateur.foyer_id,
    )


@routeur.post("/deconnexion", status_code=status.HTTP_204_NO_CONTENT)
def deconnexion(reponse: Response, session: SessionBase, principal: PrincipalCourant) -> None:
    """Ferme la session courante côté serveur ET côté navigateur.

    Effacer le seul cookie ne suffirait pas : le jeton resterait valable pour quiconque
    l'aurait intercepté.
    """
    del principal  # l'authentification est exigée, mais l'identité n'est pas utilisée ici
    reponse.delete_cookie(NOM_COOKIE, path="/")


@routeur.get("/moi", response_model=UtilisateurPublic)
def moi(session: SessionBase, principal: PrincipalCourant) -> UtilisateurPublic:
    utilisateur = depot.utilisateur_par_id(session, principal.utilisateur_id)
    if utilisateur is None:  # pragma: no cover — le principal vient d'être validé
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide.")
    return UtilisateurPublic(
        id=utilisateur.id,
        courriel=utilisateur.courriel,
        nom_affichage=utilisateur.nom_affichage,
        foyer_id=utilisateur.foyer_id,
    )


@routeur.post("/invitations", response_model=InvitationCreee, status_code=status.HTTP_201_CREATED)
def creer_invitation(session: SessionBase, principal: PrincipalCourant) -> InvitationCreee:
    """Engendre un code d'invitation pour le foyer de l'appelant.

    Le code en clair n'est renvoyé qu'ici. Seule son empreinte est stockée.
    """
    code = engendrer_jeton()
    expire_le = expiration_invitation()
    depot.creer_invitation(
        session,
        foyer_id=principal.foyer_id,
        creee_par_id=principal.utilisateur_id,
        empreinte_code=empreinte_jeton(code),
        expire_le=expire_le,
    )
    session.commit()
    return InvitationCreee(code=code, expire_le=expire_le)


@routeur.post("/rejoindre", response_model=UtilisateurPublic, status_code=status.HTTP_201_CREATED)
def rejoindre(
    demande: DemandeAdhesion, reponse: Response, session: SessionBase
) -> UtilisateurPublic:
    """Crée un compte dans le foyer désigné par un code d'invitation valide."""
    instant = maintenant()
    invitation = depot.invitation_utilisable(
        session, empreinte_code=empreinte_jeton(demande.code), a_l_instant=instant
    )
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation inconnue, expirée ou déjà utilisée.",
        )

    courriel = demande.courriel
    if depot.utilisateur_par_courriel(session, courriel) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cette adresse a déjà un compte."
        )

    utilisateur = depot.creer_utilisateur(
        session,
        foyer_id=invitation.foyer_id,
        courriel=courriel,
        nom_affichage=demande.nom_affichage,
        empreinte_mot_de_passe=hacher_mot_de_passe(demande.mot_de_passe),
    )
    depot.marquer_invitation_utilisee(session, invitation=invitation, a_l_instant=instant)

    jeton = engendrer_jeton()
    depot.enregistrer_session_web(
        session,
        utilisateur_id=utilisateur.id,
        empreinte=empreinte_jeton(jeton),
        expire_le=expiration_session(),
    )
    session.commit()
    _pose_le_cookie(reponse, jeton)

    return UtilisateurPublic(
        id=utilisateur.id,
        courriel=utilisateur.courriel,
        nom_affichage=utilisateur.nom_affichage,
        foyer_id=utilisateur.foyer_id,
    )
