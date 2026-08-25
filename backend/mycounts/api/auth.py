"""Routes d'authentification.

Aucune inscription publique : on entre par un code d'invitation, ou pas du tout.
"""

from __future__ import annotations

import datetime as dt
import io
import uuid
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlencode

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError

from mycounts.api.dependances import (
    NOM_COOKIE,
    PrincipalCourant,
    PrincipalIdentite,
    SessionBase,
)
from mycounts.api.schemas import (
    AccuseIdentite,
    AppareilPublic,
    DemandeActivationSecondFacteur,
    DemandeAdhesion,
    DemandeChangementCourriel,
    DemandeChangementMotDePasse,
    DemandeConnexion,
    DemandeInscription,
    DemandeJetonIdentite,
    DemandeRecuperation,
    DemandeReinitialisation,
    DemandeRenommage,
    DemandeSuppressionCompte,
    EnrolementPropose,
    EtatSecondFacteur,
    InvitationCreee,
    MembrePublic,
    SecondFacteurActive,
    UtilisateurPublic,
)
from mycounts.config import charger_configuration
from mycounts.domain import limitation_auth
from mycounts.domain.avatars import TYPE_MIME as TYPE_MIME_AVATAR
from mycounts.domain.avatars import ImageRefusee, normaliser
from mycounts.domain.limitation_auth import Portee
from mycounts.domain.second_facteur import (
    code_de_secours_correspond,
    compteur_du_code_valide,
    engendrer_codes_de_secours,
    engendrer_secret,
    hacher_code_de_secours,
    uri_denrolement,
)
from mycounts.domain.securite import (
    DUREE_SESSION,
    empreinte_jeton,
    engendrer_jeton,
    expiration_appareil_confiance,
    expiration_invitation,
    expiration_reinitialisation,
    expiration_session,
    expiration_verification_courriel,
    hacher_mot_de_passe,
    maintenant,
    normaliser_courriel,
    verifier_mot_de_passe,
)
from mycounts.models.auth import AppareilConfiance, Utilisateur
from mycounts.repository import auth as depot
from mycounts.repository import budget as depot_budget
from mycounts.repository import espaces as depot_espaces
from mycounts.repository import identite as depot_identite
from mycounts.repository import limitation_auth as depot_limitation

routeur = APIRouter(prefix="/auth", tags=["authentification"])

NOM_COOKIE_APPAREIL = "mycounts_appareil"
USAGE_VERIFICATION = "verification_courriel"
USAGE_REINITIALISATION = "reinitialisation_mot_de_passe"

# Empreinte d'un mot de passe qui n'est celui de personne. Sert à faire travailler Argon2
# même quand le compte n'existe pas : sans ça, une connexion sur adresse inconnue
# répondrait en 1 ms et une adresse connue en 60 ms, ce qui révèle quelles adresses ont
# un compte. La valeur est calculée une fois au démarrage.
_EMPREINTE_LEURRE = hacher_mot_de_passe("mot de passe leurre, sans usage reel")
@dataclass(frozen=True)
class _SeauLimitation:
    empreinte: str
    portee: Portee


def _seaux_de_connexion(requete: Request, courriel: str) -> tuple[_SeauLimitation, ...]:
    configuration = charger_configuration()
    cle = configuration.cle_hmac_effective
    origine_brute = requete.client.host if requete.client is not None else "origine-inconnue"
    origine = limitation_auth.origine_normalisee(origine_brute)
    return (
        _SeauLimitation(
            empreinte=limitation_auth.empreinte_hmac(
                f"{courriel}\0{origine}", cle=cle
            ),
            portee=Portee.COUPLE,
        ),
        _SeauLimitation(
            empreinte=limitation_auth.empreinte_hmac(origine, cle=cle),
            portee=Portee.ORIGINE,
        ),
    )


def _seau_action_sensible(
    requete: Request,
    utilisateur_id: uuid.UUID,
    *,
    action: str,
) -> tuple[_SeauLimitation, ...]:
    """Isole le compteur d'une action de ceux de la connexion et des autres actions."""
    configuration = charger_configuration()
    origine_brute = requete.client.host if requete.client is not None else "origine-inconnue"
    origine = limitation_auth.origine_normalisee(origine_brute)
    return (
        _SeauLimitation(
            empreinte=limitation_auth.empreinte_hmac(
                f"{utilisateur_id}\0{origine}\0{action}",
                cle=configuration.cle_hmac_effective,
            ),
            portee=Portee.ACTION,
        ),
    )


def _oublier_les_seaux(
    session: SessionBase, seaux: tuple[_SeauLimitation, ...]
) -> None:
    for seau in seaux:
        depot_limitation.oublier(
            session,
            empreinte=seau.empreinte,
            portee=seau.portee,
        )


def _refuser_si_limite_atteinte(
    session: SessionBase,
    seaux: tuple[_SeauLimitation, ...],
    *,
    instant: dt.datetime,
) -> None:
    debut = limitation_auth.debut_de_fenetre(instant)
    for seau in seaux:
        echecs = depot_limitation.nombre_echecs(
            session,
            empreinte=seau.empreinte,
            portee=seau.portee,
            fenetre_debut=debut,
        )
        if echecs >= limitation_auth.maximum_echecs(seau.portee):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez plus tard.",
                headers={"Retry-After": str(limitation_auth.secondes_avant_reessai(instant))},
            )


def _compter_un_echec(
    session: SessionBase,
    seaux: tuple[_SeauLimitation, ...],
    *,
    instant: dt.datetime,
) -> None:
    debut = limitation_auth.debut_de_fenetre(instant)
    limite_depassee = False
    for seau in seaux:
        nouveau_total = depot_limitation.compter_un_echec(
            session,
            empreinte=seau.empreinte,
            portee=seau.portee,
            fenetre_debut=debut,
        )
        if nouveau_total > limitation_auth.maximum_echecs(seau.portee):
            limite_depassee = True
    depot_limitation.purger_avant(session, avant=debut)
    # Le 401 qui suit ne doit pas annuler le compteur.
    session.commit()
    if limite_depassee:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez plus tard.",
            headers={"Retry-After": str(limitation_auth.secondes_avant_reessai(instant))},
        )


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


def _pose_le_cookie_appareil(reponse: Response, secret: str) -> None:
    configuration = charger_configuration()
    reponse.set_cookie(
        key=NOM_COOKIE_APPAREIL,
        value=secret,
        httponly=True,
        samesite="strict",
        secure=configuration.environnement != "developpement",
        max_age=int((expiration_appareil_confiance() - maintenant()).total_seconds()),
        path="/api/auth",
    )


def _mettre_lien_identite_en_file(
    session: SessionBase,
    *,
    utilisateur: Utilisateur,
    usage: str,
) -> None:
    """Crée preuve et message dans la même transaction, sans journaliser le jeton."""
    jeton = engendrer_jeton()
    expire_le = (
        expiration_verification_courriel()
        if usage == USAGE_VERIFICATION
        else expiration_reinitialisation()
    )
    preuve = depot_identite.creer_jeton(
        session,
        utilisateur_id=utilisateur.id,
        usage=usage,
        empreinte=empreinte_jeton(jeton),
        expire_le=expire_le,
    )
    configuration = charger_configuration()
    chemin = "verification" if usage == USAGE_VERIFICATION else "recuperation"
    lien = (
        f"{configuration.url_publique.rstrip('/')}/?"
        + urlencode({chemin: jeton})
    )
    depot_identite.mettre_en_file(
        session,
        utilisateur_id=utilisateur.id,
        cle_idempotence=f"{usage}:{preuve.id}",
        destinataire=utilisateur.courriel,
        modele=usage,
        donnees={"nom": utilisateur.nom_affichage, "lien": lien},
    )


def _appareil_valide(
    session: SessionBase, requete: Request, utilisateur: Utilisateur, *, instant: dt.datetime
) -> AppareilConfiance | None:
    secret = requete.cookies.get(NOM_COOKIE_APPAREIL)
    if not secret:
        return None
    return depot_identite.appareil_actif(
        session,
        utilisateur_id=utilisateur.id,
        empreinte_secret=empreinte_jeton(secret),
        a_l_instant=instant,
    )


def _tourner_appareil(
    session: SessionBase,
    reponse: Response,
    appareil: AppareilConfiance,
) -> None:
    secret = engendrer_jeton()
    depot_identite.tourner_secret_appareil(
        session,
        appareil,
        empreinte_secret=empreinte_jeton(secret),
        expire_le=expiration_appareil_confiance(),
    )
    _pose_le_cookie_appareil(reponse, secret)


def _faire_confiance_a_lappareil(
    session: SessionBase,
    requete: Request,
    reponse: Response,
    utilisateur: Utilisateur,
    *,
    nom_demande: str | None,
) -> None:
    secret = engendrer_jeton()
    nom = (nom_demande or requete.headers.get("user-agent") or "Appareil").strip()
    depot_identite.creer_appareil(
        session,
        utilisateur_id=utilisateur.id,
        empreinte_secret=empreinte_jeton(secret),
        nom=nom,
        expire_le=expiration_appareil_confiance(),
    )
    _pose_le_cookie_appareil(reponse, secret)


def _version_avatar(session: SessionBase, utilisateur_id: uuid.UUID) -> str | None:
    return depot.versions_des_avatars(session, [utilisateur_id]).get(utilisateur_id)


def _qr_en_svg(uri: str) -> str:
    """Le QR d'enrôlement en SVG inline.

    SVG et non PNG : il reste net quelle que soit la taille d'écran, pèse moins, et évite
    de faire transiter le secret par une seconde requête d'image — qui atterrirait dans
    l'historique du navigateur et dans les journaux du serveur.
    """
    tampon = io.BytesIO()
    qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(tampon)
    return tampon.getvalue().decode()


def _utilisateur_courant(session: SessionBase, principal: PrincipalIdentite) -> Utilisateur:
    """L'utilisateur derrière la session.

    Le 404 n'arrive qu'entre une suppression de compte et la fin d'une requête déjà
    partie : la dépendance qui fabrique le `Principal` a déjà validé la session. Le lever
    quand même vaut mieux qu'un `assert`, qui disparaîtrait sous `python -O`.
    """
    utilisateur = depot.utilisateur_par_id(session, principal.utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    return utilisateur


def _vue_publique(utilisateur: Utilisateur, *, version_avatar: str | None) -> UtilisateurPublic:
    """Ce que le client apprend de lui-même. Auteur unique de cette traduction.

    Trois routes la renvoyaient chacune à sa façon ; ajouter un champ obligeait à le poser
    trois fois, et l'oublier une seule aurait donné à l'écran un état correct après
    connexion et incomplet après rechargement.
    """
    return UtilisateurPublic(
        id=utilisateur.id,
        courriel=utilisateur.courriel,
        nom_affichage=utilisateur.nom_affichage,
        foyer_id=utilisateur.foyer_id,
        foyer_nom=utilisateur.foyer.nom,
        est_proprietaire=utilisateur.est_proprietaire,
        a_un_avatar=version_avatar is not None,
        avatar_version=version_avatar,
        courriel_verifie=utilisateur.courriel_verifie_le is not None,
        second_facteur_actif=utilisateur.totp_actif,
        enrolement_requis=not utilisateur.totp_actif or utilisateur.secret_totp is None,
    )


@routeur.post(
    "/inscription",
    response_model=AccuseIdentite,
    status_code=status.HTTP_202_ACCEPTED,
)
def inscription(
    demande: DemandeInscription, requete: Request, session: SessionBase
) -> AccuseIdentite:
    """Crée une identité non vérifiée; la bêta reste fermée par configuration."""
    instant = maintenant()
    invitation_espace = None
    if demande.invitation is not None:
        invitation_espace = depot_espaces.invitation_utilisable(
            session,
            empreinte_jeton=empreinte_jeton(demande.invitation),
            courriel=demande.courriel,
            a_l_instant=instant,
        )
        if invitation_espace is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cette invitation est inconnue, expirée ou destinée à une autre adresse.",
            )
    if not charger_configuration().inscriptions_ouvertes and invitation_espace is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les inscriptions sont actuellement sur invitation.",
        )
    seaux = _seaux_de_connexion(requete, demande.courriel)
    _refuser_si_limite_atteinte(session, seaux, instant=instant)
    _compter_un_echec(session, seaux, instant=instant)

    existant = depot.utilisateur_par_courriel(session, demande.courriel)
    if existant is not None:
        # Même réponse : l'inscription ne devient pas un annuaire d'adresses.
        return AccuseIdentite(
            message="Si cette adresse peut être utilisée, un lien vient d’être envoyé."
        )

    try:
        utilisateur, espace_personnel = depot.creer_identite_personnelle(
            session,
            courriel=demande.courriel,
            nom_affichage=demande.nom_affichage.strip(),
            empreinte_mot_de_passe=hacher_mot_de_passe(demande.mot_de_passe),
            courriel_verifie=False,
        )
        depot_budget.creer_categories_initiales(session, espace_personnel.id)
        if invitation_espace is not None:
            depot_espaces.accepter_invitation(
                session,
                invitation_espace,
                utilisateur_id=utilisateur.id,
                a_l_instant=instant,
            )
        _mettre_lien_identite_en_file(
            session, utilisateur=utilisateur, usage=USAGE_VERIFICATION
        )
        session.commit()
    except IntegrityError:
        session.rollback()
    return AccuseIdentite(
        message="Si cette adresse peut être utilisée, un lien vient d’être envoyé."
    )


@routeur.post("/verification", response_model=AccuseIdentite)
def verifier_le_courriel(
    demande: DemandeJetonIdentite, session: SessionBase
) -> AccuseIdentite:
    instant = maintenant()
    trouve = depot_identite.consommer_jeton(
        session,
        empreinte=empreinte_jeton(demande.jeton),
        usage=USAGE_VERIFICATION,
        a_l_instant=instant,
    )
    if trouve is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien est inconnu, expiré ou déjà utilisé.",
        )
    _, utilisateur = trouve
    depot_identite.marquer_courriel_verifie(session, utilisateur, a_l_instant=instant)
    session.commit()
    return AccuseIdentite(message="Votre adresse est vérifiée. Vous pouvez vous connecter.")


@routeur.post(
    "/verification/renvoyer",
    response_model=AccuseIdentite,
    status_code=status.HTTP_202_ACCEPTED,
)
def renvoyer_la_verification(
    demande: DemandeRecuperation, requete: Request, session: SessionBase
) -> AccuseIdentite:
    instant = maintenant()
    seaux = _seaux_de_connexion(requete, demande.courriel)
    _refuser_si_limite_atteinte(session, seaux, instant=instant)
    _compter_un_echec(session, seaux, instant=instant)
    utilisateur = depot.utilisateur_par_courriel(session, demande.courriel)
    if utilisateur is not None and utilisateur.courriel_verifie_le is None:
        _mettre_lien_identite_en_file(
            session, utilisateur=utilisateur, usage=USAGE_VERIFICATION
        )
        session.commit()
    return AccuseIdentite(
        message="Si cette adresse attend une vérification, un lien vient d’être envoyé."
    )


@routeur.post(
    "/mot-de-passe-oublie",
    response_model=AccuseIdentite,
    status_code=status.HTTP_202_ACCEPTED,
)
def demander_une_reinitialisation(
    demande: DemandeRecuperation, requete: Request, session: SessionBase
) -> AccuseIdentite:
    instant = maintenant()
    seaux = _seaux_de_connexion(requete, demande.courriel)
    _refuser_si_limite_atteinte(session, seaux, instant=instant)
    _compter_un_echec(session, seaux, instant=instant)
    utilisateur = depot.utilisateur_par_courriel(session, demande.courriel)
    if utilisateur is not None and utilisateur.courriel_verifie_le is not None:
        _mettre_lien_identite_en_file(
            session, utilisateur=utilisateur, usage=USAGE_REINITIALISATION
        )
        session.commit()
    return AccuseIdentite(
        message="Si cette adresse possède un compte, un lien vient d’être envoyé."
    )


@routeur.post("/reinitialisation", response_model=AccuseIdentite)
def reinitialiser_le_mot_de_passe(
    demande: DemandeReinitialisation, session: SessionBase
) -> AccuseIdentite:
    trouve = depot_identite.consommer_jeton(
        session,
        empreinte=empreinte_jeton(demande.jeton),
        usage=USAGE_REINITIALISATION,
        a_l_instant=maintenant(),
    )
    if trouve is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien est inconnu, expiré ou déjà utilisé.",
        )
    _, utilisateur = trouve
    if utilisateur.totp_actif:
        _exiger_le_second_facteur(session, utilisateur, demande.code)
    depot.reinitialiser_le_mot_de_passe(
        session,
        utilisateur,
        empreinte=hacher_mot_de_passe(demande.nouveau_mot_de_passe),
    )
    depot_identite.revoquer_tous_les_appareils(session, utilisateur.id)
    session.commit()
    return AccuseIdentite(message="Votre mot de passe a été remplacé.")


@routeur.post("/connexion", response_model=UtilisateurPublic)
def connexion(
    demande: DemandeConnexion,
    requete: Request,
    reponse: Response,
    session: SessionBase,
) -> UtilisateurPublic:
    """Ouvre une session.

    La réponse est identique que l'adresse soit inconnue ou le mot de passe faux :
    distinguer les deux permettrait d'énumérer les comptes existants.
    """
    refus = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects."
    )

    instant = maintenant()
    seaux = _seaux_de_connexion(requete, demande.courriel)
    _refuser_si_limite_atteinte(session, seaux, instant=instant)

    # `demande.courriel` est déjà validé ET normalisé par le schéma, qui délègue au
    # domaine. Re-normaliser ici donnerait l'impression d'un second auteur de la règle.
    utilisateur = depot.utilisateur_par_courriel(session, demande.courriel)
    empreinte = utilisateur.empreinte_mot_de_passe if utilisateur else _EMPREINTE_LEURRE
    mot_de_passe_correct = verifier_mot_de_passe(empreinte, demande.mot_de_passe)

    if utilisateur is None or not mot_de_passe_correct:
        _compter_un_echec(session, seaux, instant=instant)
        raise refus

    if utilisateur.courriel_verifie_le is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "motif": "courriel_non_verifie",
                "message": "Vérifiez votre adresse avant de vous connecter.",
            },
        )

    appareil_deja_fiable: AppareilConfiance | None = None
    preuve_mfa_directe = False
    if utilisateur.totp_actif and utilisateur.secret_totp is not None:
        appareil_deja_fiable = _appareil_valide(
            session, requete, utilisateur, instant=instant
        )
        if not appareil_deja_fiable:
            preuve_mfa_directe = demande.code is not None and demande.code.strip() != ""
            try:
                _exiger_le_second_facteur(session, utilisateur, demande.code)
            except HTTPException as erreur:
                detail = erreur.detail
                if isinstance(detail, dict) and detail.get("motif") == "second_facteur_invalide":
                    _compter_un_echec(session, seaux, instant=instant)
                raise

    second_facteur_satisfait = utilisateur.totp_actif and (
        appareil_deja_fiable is not None or preuve_mfa_directe
    )
    if appareil_deja_fiable is not None:
        _tourner_appareil(session, reponse, appareil_deja_fiable)
    if demande.faire_confiance and preuve_mfa_directe:
        _faire_confiance_a_lappareil(
            session,
            requete,
            reponse,
            utilisateur,
            nom_demande=demande.nom_appareil,
        )

    jeton = engendrer_jeton()
    depot.enregistrer_session_web(
        session,
        utilisateur_id=utilisateur.id,
        empreinte=empreinte_jeton(jeton),
        expire_le=expiration_session(),
        second_facteur_satisfait=second_facteur_satisfait,
    )
    _oublier_les_seaux(
        session, tuple(seau for seau in seaux if seau.portee is Portee.COUPLE)
    )
    session.commit()
    _pose_le_cookie(reponse, jeton)

    return _vue_publique(utilisateur, version_avatar=_version_avatar(session, utilisateur.id))


def _exiger_le_second_facteur(
    session: SessionBase, utilisateur: Utilisateur, code: str | None
) -> None:
    """Vérifie le code, ou consomme un code de secours. Lève 401 sinon.

    **Le motif est machine-lisible** — `detail` est un objet et non une phrase — parce que
    l'écran doit distinguer deux situations que rien ne sépare autrement : « il faut
    maintenant un code » et « ce code est faux ». Les confondre afficherait « code
    incorrect » à quelqu'un qui n'en a encore saisi aucun.

    **TOTP d'abord, code de secours ensuite.** Un seul champ pour les deux : celui qui a
    perdu son téléphone tape son code de secours là où il tapait ses six chiffres, sans
    chercher un second formulaire. Les formats ne se confondent pas.

    **Un code de secours est consommé même si la session échouait ensuite.** C'est voulu :
    un code rejouable ne serait plus à usage unique, et l'usage est justement ce qu'on veut
    tracer.
    """
    if code is None or code.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "motif": "second_facteur_requis",
                "message": "Entrez le code de votre application.",
            },
        )

    assert utilisateur.secret_totp is not None
    compteur = compteur_du_code_valide(utilisateur.secret_totp, code)
    if compteur is not None:
        if depot.consommer_compteur_totp(session, utilisateur.id, compteur=compteur):
            # Comme un code de secours, un TOTP accepté est consommé même si la création
            # de session échoue ensuite. Sinon une panne après cette ligne le rendrait
            # rejouable pendant le reste de sa fenêtre.
            session.commit()
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "motif": "second_facteur_invalide",
                "message": "Ce code n’est pas valable.",
            },
        )

    for candidat in depot.codes_de_secours_valides(session, utilisateur.id):
        if code_de_secours_correspond(candidat.empreinte, code):
            depot.consommer_le_code_de_secours(session, candidat, a_l_instant=maintenant())
            session.commit()
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"motif": "second_facteur_invalide", "message": "Ce code n’est pas valable."},
    )


@routeur.post("/deconnexion", status_code=status.HTTP_204_NO_CONTENT)
def deconnexion(
    requete: Request,
    reponse: Response,
    session: SessionBase,
    principal: PrincipalIdentite,
) -> None:
    """Ferme la session courante côté serveur ET côté navigateur.

    Effacer le seul cookie ne suffirait pas : le jeton resterait valable pour quiconque
    l'aurait intercepté.
    """
    del principal  # la dépendance exige une session active avant d'autoriser sa révocation
    jeton = requete.cookies.get(NOM_COOKIE)
    if jeton is not None:
        depot.supprimer_session_web(session, empreinte=empreinte_jeton(jeton))
        session.commit()
    reponse.delete_cookie(NOM_COOKIE, path="/")


@routeur.get("/moi", response_model=UtilisateurPublic)
def moi(session: SessionBase, principal: PrincipalIdentite) -> UtilisateurPublic:
    utilisateur = depot.utilisateur_par_id(session, principal.utilisateur_id)
    if utilisateur is None:  # pragma: no cover — le principal vient d'être validé
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide.")
    return _vue_publique(utilisateur, version_avatar=_version_avatar(session, utilisateur.id))


@routeur.post("/invitations", response_model=InvitationCreee, status_code=status.HTTP_201_CREATED)
def creer_invitation(session: SessionBase, principal: PrincipalCourant) -> InvitationCreee:
    """Engendre un code d'invitation pour le foyer de l'appelant.

    Le code en clair n'est renvoyé qu'ici. Seule son empreinte est stockée.
    """
    if not principal.mode_legacy:
        # Ce code historique n'est ni ciblé sur une adresse ni rattaché aux nouveaux
        # rôles. Surtout, depuis que l'espace personnel est le défaut, le laisser utiliser
        # `foyer_id` créerait une invitation vers son conteneur de compatibilité. Les
        # nouveaux clients passent exclusivement par `/espaces/invitations`.
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Utilisez l’invitation ciblée du foyer actif.",
        )
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
        courriel_verifie=False,
    )
    _mettre_lien_identite_en_file(
        session, utilisateur=utilisateur, usage=USAGE_VERIFICATION
    )
    espace_personnel, _ = depot_espaces.creer_espace_personnel(session, utilisateur)
    depot_budget.creer_categories_initiales(session, espace_personnel.id)
    depot.marquer_invitation_utilisee(session, invitation=invitation, a_l_instant=instant)

    jeton = engendrer_jeton()
    depot.enregistrer_session_web(
        session,
        utilisateur_id=utilisateur.id,
        empreinte=empreinte_jeton(jeton),
        expire_le=expiration_session(),
        second_facteur_satisfait=False,
    )
    session.commit()
    _pose_le_cookie(reponse, jeton)

    return _vue_publique(utilisateur, version_avatar=_version_avatar(session, utilisateur.id))


@routeur.get("/foyer/membres", response_model=list[MembrePublic])
def membres_du_foyer(session: SessionBase, principal: PrincipalCourant) -> list[MembrePublic]:
    """Qui compose le foyer.

    Aucune donnée sensible : un nom, une adresse, une date d'arrivée. Pas de mot de passe,
    pas de session, pas de solde — savoir avec qui l'on partage un compte joint ne donne
    aucun droit sur l'argent de l'autre.
    """
    membres = depot.membres_du_foyer(session, principal)
    # Une seule requête pour tout le monde : un appel par membre ferait autant
    # d'allers-retours que le foyer compte de personnes, pour un booléen chacun.
    versions = depot.versions_des_avatars(session, [m.id for m in membres])
    return [
        MembrePublic(
            id=membre.id,
            nom_affichage=membre.nom_affichage,
            courriel=membre.courriel,
            cree_le=membre.cree_le,
            est_vous=membre.id == principal.utilisateur_id,
            est_proprietaire=membre.est_proprietaire,
            a_un_avatar=membre.id in versions,
            avatar_version=versions.get(membre.id),
        )
        for membre in membres
    ]


@routeur.patch("/moi", response_model=UtilisateurPublic)
def renommer(
    demande: DemandeRenommage, session: SessionBase, principal: PrincipalCourant
) -> UtilisateurPublic:
    """Change le nom affiché. Aucun mot de passe exigé : rien de sensible ne se joue ici.

    Le nom alimente aussi les initiales de la bulle, faute d'avatar : le laisser vide
    donnerait un disque muet, d'où la longueur minimale portée par le schéma.
    """
    utilisateur = _utilisateur_courant(session, principal)
    depot.renommer_utilisateur(session, utilisateur, nom=demande.nom_affichage.strip())
    session.commit()
    return _vue_publique(utilisateur, version_avatar=_version_avatar(session, utilisateur.id))


@routeur.post("/moi/mot-de-passe", status_code=status.HTTP_204_NO_CONTENT)
def changer_le_mot_de_passe(
    demande: DemandeChangementMotDePasse,
    requete: Request,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    """Change le mot de passe et ferme les AUTRES sessions.

    L'ancien est vérifié avec la même fonction que la connexion : une seconde comparaison
    écrite ici pourrait diverger, et c'est la plus permissive qui ne préviendrait pas.

    La longueur minimale du nouveau est celle du domaine, levée en `ValueError` par
    `hacher_mot_de_passe`. On la traduit en 400 plutôt que de la recopier : deux endroits
    qui déclarent la même borne finissent par ne plus déclarer la même.
    """
    utilisateur = _utilisateur_courant(session, principal)
    if not verifier_mot_de_passe(utilisateur.empreinte_mot_de_passe, demande.ancien):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe actuel est incorrect.",
        )
    try:
        empreinte = hacher_mot_de_passe(demande.nouveau)
    except ValueError as cause:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(cause)
        ) from cause

    depot.changer_le_mot_de_passe(
        session,
        utilisateur,
        empreinte=empreinte,
        # La session qui demande survit : la fermer renverrait vers l'écran de connexion
        # juste après avoir annoncé un succès, ce qui se lit comme un échec.
        sauf_empreinte_jeton=empreinte_jeton(requete.cookies.get(NOM_COOKIE, "")),
    )
    depot_identite.revoquer_tous_les_appareils(session, utilisateur.id)
    session.commit()


@routeur.post("/moi/courriel", response_model=UtilisateurPublic)
def changer_le_courriel(
    demande: DemandeChangementCourriel, session: SessionBase, principal: PrincipalCourant
) -> UtilisateurPublic:
    """Change l'adresse de connexion. Le mot de passe est exigé.

    Le conflit d'unicité est rendu en 409 avec un message neutre — « cette adresse ne peut
    pas être utilisée » — et non « elle existe déjà » : cette seconde formulation
    permettrait de savoir, depuis un compte quelconque, qui d'autre a un compte ici.
    """
    utilisateur = _utilisateur_courant(session, principal)
    if not verifier_mot_de_passe(utilisateur.empreinte_mot_de_passe, demande.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le mot de passe est incorrect."
        )

    try:
        depot.changer_le_courriel(session, utilisateur, courriel=demande.courriel)
        utilisateur.courriel_verifie_le = None
        depot_identite.revoquer_tous_les_appareils(session, utilisateur.id)
        _mettre_lien_identite_en_file(
            session, utilisateur=utilisateur, usage=USAGE_VERIFICATION
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette adresse ne peut pas être utilisée.",
        ) from None
    return _vue_publique(utilisateur, version_avatar=_version_avatar(session, utilisateur.id))


@routeur.put("/moi/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def envoyer_son_avatar(
    session: SessionBase,
    principal: PrincipalCourant,
    fichier: Annotated[UploadFile, File(description="Image de profil.")],
) -> None:
    """Reçoit une image, la normalise, la remplace.

    Rien de ce qui arrive n'est stocké tel quel : `normaliser` décode, redresse, recadre et
    réencode. C'est ce qui garantit qu'on sert bien une image — un fichier téléversé
    annonce son type lui-même — et c'est aussi ce qui efface les métadonnées, dont la
    position GPS que transporte toute photo de téléphone.

    Le poids est vérifié APRÈS lecture, pas par un en-tête : `Content-Length` est déclaré
    par l'appelant et ne contraint rien.
    """
    donnees = await fichier.read()
    try:
        normalisee = normaliser(donnees)
    except ImageRefusee as cause:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(cause)
        ) from cause

    depot.enregistrer_avatar(
        session, principal.utilisateur_id, contenu=normalisee, type_mime=TYPE_MIME_AVATAR
    )
    session.commit()


@routeur.get("/moi/second-facteur", response_model=EtatSecondFacteur)
def etat_du_second_facteur(
    session: SessionBase, principal: PrincipalIdentite
) -> EtatSecondFacteur:
    utilisateur = _utilisateur_courant(session, principal)
    return EtatSecondFacteur(
        actif=utilisateur.totp_actif,
        codes_de_secours_restants=len(depot.codes_de_secours_valides(session, utilisateur.id)),
    )


@routeur.get("/moi/appareils", response_model=list[AppareilPublic])
def lister_les_appareils(
    session: SessionBase, principal: PrincipalCourant
) -> list[AppareilPublic]:
    return [
        AppareilPublic(
            id=appareil.id,
            nom=appareil.nom,
            cree_le=appareil.cree_le,
            vu_le=appareil.vu_le,
            expire_le=appareil.expire_le,
        )
        for appareil in depot_identite.appareils_de(session, principal.utilisateur_id)
        if appareil.expire_le > maintenant()
    ]


@routeur.delete("/moi/appareils/{appareil_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoquer_un_appareil(
    appareil_id: uuid.UUID,
    reponse: Response,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    if not depot_identite.revoquer_appareil(
        session, utilisateur_id=principal.utilisateur_id, appareil_id=appareil_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appareil introuvable.")
    session.commit()
    # Si c'était cet appareil, le cookie devient inutilisable; le retirer évite un essai
    # silencieux à la prochaine connexion. Pour un autre appareil, c'est sans conséquence.
    reponse.delete_cookie(NOM_COOKIE_APPAREIL, path="/api/auth")


@routeur.post("/moi/second-facteur/preparer", response_model=EnrolementPropose)
def preparer_le_second_facteur(
    session: SessionBase, principal: PrincipalIdentite
) -> EnrolementPropose:
    """Engendre un secret et rend de quoi le configurer. **N'active rien.**

    Rappeler cette route AVANT l'activation engendre un NOUVEAU secret, et c'est voulu :
    on la rappelle quand la première tentative a échoué — QR mal scanné, application
    refermée — et réutiliser le secret d'un enrôlement raté laisserait la moitié du travail
    faite avec une application dont on ne sait plus ce qu'elle contient.

    Une fois le second facteur ACTIF, elle est refusée : régénérer un secret depuis une
    session ouverte permettrait de remplacer le facteur sans posséder l'ancien, ce qui le
    viderait de son sens.
    """
    utilisateur = _utilisateur_courant(session, principal)
    if utilisateur.totp_actif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le second facteur est déjà actif. Désactivez-le d’abord.",
        )

    secret = engendrer_secret()
    depot.preparer_lenrolement(session, utilisateur, secret=secret)
    session.commit()

    uri = uri_denrolement(secret, utilisateur.courriel)
    return EnrolementPropose(secret=secret, uri=uri, qr_svg=_qr_en_svg(uri))


@routeur.post("/moi/second-facteur/activer", response_model=SecondFacteurActive)
def activer_le_second_facteur(
    demande: DemandeActivationSecondFacteur,
    requete: Request,
    reponse: Response,
    session: SessionBase,
    principal: PrincipalIdentite,
) -> SecondFacteurActive:
    """Vérifie un PREMIER code, puis active. Rend les dix codes de secours, une seule fois.

    L'activation exige une preuve que l'application est correctement configurée. Sans elle,
    une heure fausse sur le téléphone ou un QR scanné à moitié verrouillerait le compte :
    le serveur croirait l'enrôlement fait, et aucun code ne fonctionnerait plus.
    """
    utilisateur = _utilisateur_courant(session, principal)
    instant = maintenant()
    seaux = _seau_action_sensible(
        requete, utilisateur.id, action="activation-second-facteur"
    )
    _refuser_si_limite_atteinte(session, seaux, instant=instant)
    if utilisateur.secret_totp is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Commencez par préparer l’enrôlement.",
        )
    compteur = compteur_du_code_valide(utilisateur.secret_totp, demande.code)
    if compteur is None:
        _compter_un_echec(session, seaux, instant=instant)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce code ne correspond pas. Vérifiez l’heure de votre téléphone.",
        )
    if not depot.consommer_compteur_totp(session, utilisateur.id, compteur=compteur):
        _compter_un_echec(session, seaux, instant=instant)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce code vient déjà d’être utilisé. Attendez le suivant.",
        )

    codes = engendrer_codes_de_secours()
    depot.activer_le_second_facteur(
        session,
        utilisateur,
        empreintes_de_secours=[hacher_code_de_secours(c) for c in codes],
    )
    depot_identite.revoquer_tous_les_appareils(session, utilisateur.id)
    jeton_session = requete.cookies.get(NOM_COOKIE)
    if jeton_session is not None:
        depot.marquer_session_mfa(session, empreinte=empreinte_jeton(jeton_session))
    if demande.faire_confiance:
        _faire_confiance_a_lappareil(
            session,
            requete,
            reponse,
            utilisateur,
            nom_demande=demande.nom_appareil,
        )
    _oublier_les_seaux(session, seaux)
    session.commit()
    return SecondFacteurActive(codes_de_secours=codes)


@routeur.delete("/moi/second-facteur", status_code=status.HTTP_204_NO_CONTENT)
def desactiver_le_second_facteur(
    demande: DemandeActivationSecondFacteur,
    requete: Request,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    """Retire le second facteur. Un code EN COURS est exigé.

    Une session ouverte ne suffit pas : c'est précisément contre l'usage d'une session
    volée que le second facteur existe, et le retirer sans preuve de possession annulerait
    la protection depuis l'endroit même qu'elle protège.
    """
    utilisateur = _utilisateur_courant(session, principal)
    if not utilisateur.totp_actif or utilisateur.secret_totp is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Le second facteur n’est pas actif."
        )
    instant = maintenant()
    seaux = _seau_action_sensible(
        requete, utilisateur.id, action="desactivation-second-facteur"
    )
    _refuser_si_limite_atteinte(session, seaux, instant=instant)
    try:
        _exiger_le_second_facteur(session, utilisateur, demande.code)
    except HTTPException:
        _compter_un_echec(session, seaux, instant=instant)
        raise

    depot.desactiver_le_second_facteur(session, utilisateur)
    depot_identite.revoquer_tous_les_appareils(session, utilisateur.id)
    _oublier_les_seaux(session, seaux)
    session.commit()


@routeur.delete("/moi/avatar", status_code=status.HTTP_204_NO_CONTENT)
def retirer_son_avatar(session: SessionBase, principal: PrincipalCourant) -> None:
    """Retire l'avatar. 404 s'il n'y en avait pas.

    « Retiré » et « il n'y en avait pas » sont deux réponses différentes : les confondre
    ferait afficher un succès à qui clique deux fois, et douter du premier clic.
    """
    if not depot.supprimer_avatar(session, principal.utilisateur_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun avatar à retirer."
        )
    session.commit()


@routeur.get(
    "/utilisateurs/{utilisateur_id}/avatar",
    responses={200: {"content": {"image/webp": {}}}, 404: {}},
)
def avatar_dune_personne(
    utilisateur_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> Response:
    """Sert l'image d'un membre du foyer.

    Restreint au foyer de l'appelant : une image de profil n'est pas publique, et un
    identifiant se devine assez mal pour être un secret mais assez bien pour ne pas en
    être un. Hors du foyer, 404 et non 403 — dire « interdit » confirmerait l'existence du
    compte.

    `ETag` sur la date de modification, et `private` : l'image est nominative, un cache
    partagé n'a pas à la garder.
    """
    cible = depot.utilisateur_par_id(session, utilisateur_id)
    meme_espace = depot_espaces.appartenance_active(
        session,
        utilisateur_id=utilisateur_id,
        espace_id=principal.espace_id,
    )
    if cible is None or meme_espace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun avatar.")

    avatar = depot.avatar_de(session, utilisateur_id)
    if avatar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun avatar.")

    return Response(
        content=avatar.contenu,
        media_type=avatar.type_mime,
        headers={
            "Cache-Control": "private, max-age=0, must-revalidate",
            "ETag": f'"{avatar.modifie_le.timestamp()}"',
        },
    )


@routeur.delete("/foyer/partage", status_code=status.HTTP_204_NO_CONTENT)
def dissoudre_le_partage(
    session: SessionBase, principal: PrincipalCourant
) -> None:
    """Arrête le partage : supprime les comptes JOINTS, et rien d'autre.

    Ni déconnexion, ni perte de compte, ni perte des comptes personnels. C'était le
    défaut : « supprimer le foyer » emportait l'identité de celui qui voulait seulement
    cesser de partager, parce que le foyer est le conteneur racine de tout en base. Ce
    fait de schéma n'a pas à être payé par l'utilisateur (ERREURS.md #044).

    Le refus porte sur les OPÉRATIONS RÉELLES, exactement comme pour un compte seul : un
    compte joint qui ne porte que son amorçage n'a clos aucun mois, et l'emporter ne
    change aucun total passé. La liste des comptes qui bloquent est rendue dans le
    message : « c'est refusé » sans dire par quoi oblige à essayer un par un.

    Réservé au propriétaire. Un compte joint contient l'argent des DEUX membres, et la
    visibilité ne vaut pas permission.
    """
    if not depot.est_le_proprietaire(session, principal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le propriétaire du foyer peut dissoudre le partage.",
        )

    joints = depot.comptes_joints(session, principal)
    if not joints:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Il n’y a aucun compte joint à dissoudre.",
        )

    occupes = [
        compte.nom
        for compte in joints
        if depot_budget.compte_a_des_operations(session, compte.id)
    ]
    if occupes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ces comptes joints portent des opérations : "
                + ", ".join(occupes)
                + ". Les supprimer changerait des mois déjà clos. Videz-les ou "
                "archivez-les avant de dissoudre le partage."
            ),
        )

    depot.dissoudre_le_partage(session, principal)
    session.commit()


@routeur.delete("/moi", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_mon_compte(
    demande: DemandeSuppressionCompte,
    reponse: Response,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    """Efface son compte et ses données personnelles. Définitivement.

    Trois verrous, chacun pour une erreur différente :

    - **adresse retapée** — contre le geste réflexe. Voir `DemandeSuppressionCompte`.
    - **propriétaire entouré** — celui qui a créé le foyer ne peut pas partir tant qu'il
      reste des membres : `Compte.proprietaire_id` pointerait vers un utilisateur effacé
      sur les comptes joints qu'il a ouverts, et plus personne ne pourrait les supprimer.
      Transférer la propriété est un lot à part ; refuser franchement vaut mieux que
      laisser un foyer dans un état dont on ne sort plus.
    - **session fermée** — le cookie pointerait sur un utilisateur qui n'existe plus.
      L'effacer ici évite un écran d'erreur là où il faut un écran d'accueil.

    Dernier membre : le foyer part avec lui, comptes joints compris. C'est le seul cas où
    cette route détruit plus que l'appelant — et le seul où plus personne ne resterait
    pour le faire.

    Aucune sauvegarde n'est prise. Il n'y a rien à restaurer après cet appel.
    """
    utilisateur = depot.utilisateur_par_id(session, principal.utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    # Comparaison sur l'adresse normalisée : c'est la forme sous laquelle elle est stockée
    # et affichée. La casse ne prouve rien ici — une adresse n'en a pas — alors que le nom
    # du foyer, lui, en a une que l'écran montre.
    if normaliser_courriel(demande.courriel) != utilisateur.courriel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L’adresse saisie ne correspond pas à celle de ce compte.",
        )

    autres = len(depot.membres_du_foyer(session, principal)) - 1
    if utilisateur.est_proprietaire and autres > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Vous avez créé ce foyer et il compte encore "
                f"{autres} autre{'s' if autres > 1 else ''} membre"
                f"{'s' if autres > 1 else ''}. Retirez-les avant de supprimer votre compte."
            ),
        )

    depot.supprimer_mon_compte(session, principal)
    session.commit()
    reponse.delete_cookie(NOM_COOKIE, path="/")
