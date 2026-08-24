"""Accès aux données d'authentification.

Seul endroit du projet autorisé à construire une requête. Chaque lecture porteuse de
données de foyer prend un `Principal` et applique son périmètre.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, delete, or_, select, update
from sqlalchemy.orm import Session

from mycounts.domain.espaces import RoleEspace, TypeEspace
from mycounts.models.auth import (
    Appartenance,
    Avatar,
    CodeDeSecours,
    Espace,
    Foyer,
    Invitation,
    InvitationEspace,
    SessionWeb,
    Utilisateur,
)
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
    # Compatibilité de création pendant la migration : le foyer historique et le nouvel
    # espace partagent leur UUID. Les nouveaux parcours passent par repository.espaces.
    session.add(Espace(id=foyer.id, type=TypeEspace.FOYER, nom=nom))
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
    espace = session.get(Espace, foyer_id)
    if espace is not None and TypeEspace(espace.type) is TypeEspace.PERSONNEL:
        # La table Foyer subsiste comme support de FK durant la migration. Elle ne doit
        # jamais transformer ce conteneur technique en espace personnel partagé.
        raise ValueError("Un espace personnel ne peut recevoir aucun autre membre.")
    utilisateur = Utilisateur(
        foyer_id=foyer_id,
        courriel=courriel,
        nom_affichage=nom_affichage,
        empreinte_mot_de_passe=empreinte_mot_de_passe,
        est_proprietaire=est_proprietaire,
    )
    session.add(utilisateur)
    session.flush()
    # Les scripts/tests historiques créent encore l'identité dans un foyer. Leur
    # appartenance est matérialisée dès maintenant pour que l'en-tête d'espace puisse
    # autoriser les mêmes données durant la transition.
    session.add(
        Appartenance(
            utilisateur_id=utilisateur.id,
            espace_id=foyer_id,
            role=(RoleEspace.PROPRIETAIRE if est_proprietaire else RoleEspace.MEMBRE),
        )
    )
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
    session.execute(delete(InvitationEspace).where(InvitationEspace.espace_id == foyer_id))
    session.execute(delete(SessionWeb).where(SessionWeb.utilisateur_id.in_(utilisateurs)))
    session.execute(delete(Utilisateur).where(Utilisateur.foyer_id == foyer_id))
    session.execute(delete(Espace).where(Espace.id == foyer_id))
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


def avatar_de(session: Session, utilisateur_id: uuid.UUID) -> Avatar | None:
    """L'avatar d'une personne, ou None.

    Sans `Principal` : une image de profil n'est pas une donnée de foyer. Elle est vue par
    tous ceux qui voient la personne, et la route qui l'expose exige d'être connecté —
    c'est la seule barrière utile ici. Lui appliquer le périmètre des comptes ferait
    disparaître le portrait d'un membre selon la vue en cours, ce qui n'a aucun sens.
    """
    return session.get(Avatar, utilisateur_id)


def enregistrer_avatar(
    session: Session, utilisateur_id: uuid.UUID, *, contenu: bytes, type_mime: str
) -> Avatar:
    """Pose ou remplace l'avatar. Le contenu est déjà normalisé par le domaine.

    Remplacement en place plutôt que suppression puis insertion : la clé primaire est
    l'identifiant de la personne, et deux lignes ne peuvent pas coexister. `modifie_le`
    est repoussé par `onupdate`, ce qui suffit à faire changer l'`ETag` — sans quoi le
    navigateur continuerait d'afficher l'ancienne image et l'on croirait l'envoi perdu.
    """
    existant = session.get(Avatar, utilisateur_id)
    if existant is None:
        existant = Avatar(utilisateur_id=utilisateur_id, contenu=contenu, type_mime=type_mime)
        session.add(existant)
    else:
        existant.contenu = contenu
        existant.type_mime = type_mime
    session.flush()
    return existant


def supprimer_avatar(session: Session, utilisateur_id: uuid.UUID) -> bool:
    """Retire l'avatar. Rend `False` s'il n'y en avait pas.

    La distinction sert la route : « retiré » et « il n'y en avait pas » sont deux
    réponses différentes, et les confondre ferait afficher un succès à qui vient de
    cliquer deux fois — donc douter du premier clic.
    """
    existant = session.get(Avatar, utilisateur_id)
    if existant is None:
        return False
    session.delete(existant)
    session.flush()
    return True


def renommer_utilisateur(session: Session, utilisateur: Utilisateur, *, nom: str) -> Utilisateur:
    utilisateur.nom_affichage = nom
    session.flush()
    return utilisateur


def changer_le_courriel(
    session: Session, utilisateur: Utilisateur, *, courriel: str
) -> Utilisateur:
    """Change l'adresse de connexion. Déjà normalisée par l'appelant.

    L'unicité est tenue par la base (`uq_utilisateur_courriel`) : la vérifier ici en plus
    créerait une seconde règle, et une fenêtre entre la lecture et l'écriture où deux
    demandes concurrentes passeraient toutes les deux.
    """
    utilisateur.courriel = courriel
    session.flush()
    return utilisateur


def changer_le_mot_de_passe(
    session: Session, utilisateur: Utilisateur, *, empreinte: str, sauf_empreinte_jeton: str
) -> int:
    """Change le mot de passe et ferme les AUTRES sessions. Rend le nombre de fermetures.

    Fermer les autres est le point : on change son mot de passe le plus souvent parce que
    quelqu'un d'autre pourrait l'avoir. Le laisser connecté ailleurs viderait la mesure de
    son sens — l'ancienne session continuerait de fonctionner avec l'ancien secret.

    Celle qui a fait la demande survit, sinon l'écran renverrait vers la connexion juste
    après avoir annoncé un succès, ce qui se lit comme un échec.
    """
    utilisateur.empreinte_mot_de_passe = empreinte
    fermees = cast(
        "CursorResult[Any]",
        session.execute(
            delete(SessionWeb).where(
                SessionWeb.utilisateur_id == utilisateur.id,
                SessionWeb.empreinte_jeton != sauf_empreinte_jeton,
            )
        ),
    )
    session.flush()
    return fermees.rowcount


def versions_des_avatars(
    session: Session, utilisateur_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Qui, parmi ceux-là, a un avatar, et depuis quand. UNE requête, quel que soit le nombre.

    Un `avatar_de` par membre serait plus court à écrire et ferait autant d'allers-retours
    que le foyer compte de personnes, pour ne rendre qu'un booléen chacun. La liste des
    membres est courte aujourd'hui ; la forme qui ne dégénère pas ne coûte pas plus cher à
    écrire une fois.

    Seules la clé et la date sont lues, jamais `contenu` : rapporter les images pour
    répondre « oui, il y en a une » chargerait plusieurs centaines de kilo-octets par appel.

    La date sert de version d'URL côté client. Un entier de secondes suffit — deux envois
    dans la même seconde par la même personne ne se produisent pas, et si cela arrivait la
    seconde image porterait la même URL une seconde de trop.
    """
    if not utilisateur_ids:
        return {}
    lignes = session.execute(
        select(Avatar.utilisateur_id, Avatar.modifie_le).where(
            Avatar.utilisateur_id.in_(utilisateur_ids)
        )
    ).all()
    return {identifiant: str(int(date.timestamp())) for identifiant, date in lignes}


def preparer_lenrolement(session: Session, utilisateur: Utilisateur, *, secret: str) -> None:
    """Écrit le secret SANS activer le second facteur.

    Les deux sont distincts, et c'est ce qui évite de verrouiller un compte : entre le
    moment où l'on montre le QR et celui où l'application le lit correctement, tout peut
    échouer — mauvaise heure sur le téléphone, code scanné à moitié, application refermée.
    Activer d'emblée ferait croire au serveur que l'enrôlement a réussi, et plus aucun code
    ne fonctionnerait.
    """
    utilisateur.secret_totp = secret
    utilisateur.totp_actif = False
    utilisateur.dernier_compteur_totp = None
    session.flush()


def consommer_compteur_totp(
    session: Session, utilisateur_id: uuid.UUID, *, compteur: int
) -> bool:
    """Consomme un compteur TOTP une seule fois, même sous deux requêtes concurrentes.

    Le `UPDATE ... WHERE ancien < nouveau` porte l'arbitrage dans PostgreSQL. Une lecture
    suivie d'une écriture laisserait deux transactions lire la même ancienne valeur puis
    accepter toutes les deux le même code.
    """
    resultat = cast(
        "CursorResult[Any]",
        session.execute(
            update(Utilisateur)
            .where(
                Utilisateur.id == utilisateur_id,
                or_(
                    Utilisateur.dernier_compteur_totp.is_(None),
                    Utilisateur.dernier_compteur_totp < compteur,
                ),
            )
            .values(dernier_compteur_totp=compteur)
        ),
    )
    return resultat.rowcount == 1


def activer_le_second_facteur(
    session: Session, utilisateur: Utilisateur, *, empreintes_de_secours: Sequence[str]
) -> None:
    """Active le TOTP et remplace les codes de secours.

    Remplace, et non ajoute : réactiver le second facteur repart de dix codes neufs, et
    laisser vivre les anciens laisserait des portes dont on aurait oublié l'existence.
    """
    utilisateur.totp_actif = True
    session.execute(
        delete(CodeDeSecours).where(CodeDeSecours.utilisateur_id == utilisateur.id)
    )
    session.add_all(
        CodeDeSecours(utilisateur_id=utilisateur.id, empreinte=empreinte)
        for empreinte in empreintes_de_secours
    )
    session.flush()


def desactiver_le_second_facteur(session: Session, utilisateur: Utilisateur) -> None:
    """Retire le secret ET les codes. Laisser le secret derrière permettrait de réactiver
    sans repasser par un QR, donc avec une application dont on ne sait plus si elle est
    encore installée sur le bon téléphone."""
    utilisateur.secret_totp = None
    utilisateur.totp_actif = False
    utilisateur.dernier_compteur_totp = None
    session.execute(
        delete(CodeDeSecours).where(CodeDeSecours.utilisateur_id == utilisateur.id)
    )
    session.flush()


def codes_de_secours_valides(session: Session, utilisateur_id: uuid.UUID) -> list[CodeDeSecours]:
    """Les codes non encore consommés."""
    return list(
        session.execute(
            select(CodeDeSecours).where(
                CodeDeSecours.utilisateur_id == utilisateur_id,
                CodeDeSecours.utilise_le.is_(None),
            )
        ).scalars()
    )


def consommer_le_code_de_secours(
    session: Session, code: CodeDeSecours, *, a_l_instant: dt.datetime
) -> None:
    """Marque le code comme utilisé. La ligne RESTE.

    Savoir qu'un code de secours a servi, et quand, est exactement la trace qu'on cherche
    après coup — une ligne effacée ne raconte rien.
    """
    code.utilise_le = a_l_instant
    session.flush()
