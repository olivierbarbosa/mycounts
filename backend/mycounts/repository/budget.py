"""Accès aux comptes, catégories et opérations.

Chaque lecture prend un `Principal` et applique son périmètre. Deux règles s'y
superposent :

1. **le foyer** — on ne voit jamais les données d'un autre foyer ;
2. **la confidentialité** — un compte marqué privé n'est visible que de son propriétaire.

Le périmètre des opérations passe par une jointure sur `compte`, jamais par une colonne
`foyer_id` recopiée sur `operation` : une copie dériverait le jour où une opération
change de compte.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from mycounts.domain.agregats import EtatOperation, OperationCalcul
from mycounts.domain.categories import CATEGORIES_INITIALES
from mycounts.domain.comptes import TypeCompte
from mycounts.domain.import_releve import Correspondance, GenreCorrespondance
from mycounts.domain.montants import Cents
from mycounts.models.budget import (
    Categorie,
    Compte,
    CorrespondanceImport,
    NatureCategorie,
    Operation,
    TeinteCategorie,
)
from mycounts.repository.base import Principal, Vue


def _comptes_autorises(principal: Principal) -> ColumnElement[bool]:
    """Condition de visibilité d'un compte. Auteur unique de la règle de confidentialité.

    L'écrire une seconde fois dans une requête voisine est la façon la plus sûre de créer
    une fuite : les deux versions divergeront, et la plus permissive ne préviendra pas.
    """
    if principal.vue is Vue.FOYER:
        # Les comptes JOINTS, et eux seuls. Y ajouter les comptes privés de l'appelant
        # ferait un total que personne ne pourrait interpréter — ni « ce que nous avons »,
        # ni « ce que j'ai » — et ferait apparaître ses opérations personnelles dans un
        # écran que son conjoint regarde aussi.
        return and_(Compte.foyer_id == principal.foyer_id, Compte.prive.is_(False))

    # Vue personnelle : ses propres comptes privés. Les comptes joints en sont exclus, pour
    # la même raison en sens inverse — « combien j'ai » ne comprend pas la moitié du compte
    # commun, dont la répartition n'appartient pas à cette application.
    return and_(
        Compte.foyer_id == principal.foyer_id,
        Compte.prive.is_(True),
        Compte.proprietaire_id == principal.utilisateur_id,
    )


def creer_compte(
    session: Session,
    principal: Principal,
    *,
    nom: str,
    prive: bool = True,
    type_compte: TypeCompte = TypeCompte.COURANT,
    produit: str = "compte_courant",
) -> Compte:
    compte = Compte(
        foyer_id=principal.foyer_id,
        proprietaire_id=principal.utilisateur_id,
        nom=nom,
        prive=prive,
        type_compte=type_compte,
        produit=produit,
    )
    session.add(compte)
    session.flush()
    return compte


def modifier_compte(
    session: Session,
    compte: Compte,
    *,
    nom: str | None = None,
    produit: str | None = None,
    type_compte: TypeCompte | None = None,
    archive: bool | None = None,
) -> Compte:
    """Corrige un compte. Les champs laissés à `None` ne sont pas touchés.

    `None` et non une valeur par défaut : sans cette distinction, renommer un compte
    remettrait silencieusement son produit à celui du catalogue par défaut.
    """
    if nom is not None:
        compte.nom = nom
    if produit is not None:
        compte.produit = produit
    if type_compte is not None:
        compte.type_compte = type_compte
    if archive is not None:
        compte.archive = archive
    session.flush()
    return compte


def compte_a_des_operations(session: Session, compte_id: uuid.UUID) -> bool:
    """Y compris les opérations ANNULÉES, mais PAS le solde d'ouverture.

    Les annulées comptent : une annulée reste une ligne en base, et c'est elle qui empêche
    la matérialisation de recréer l'échéance. Supprimer le compte l'emporterait, et le
    prélèvement reviendrait au passage suivant du job.

    L'ouverture ne compte PAS, et c'est une correction du 21 août 2026. Olivier a créé un
    compte joint avec son solde de départ, puis n'a plus pu le supprimer : la règle
    protège les mois clos, mais un compte qui ne porte que son amorçage n'a jamais servi à
    clore quoi que ce soit. Refuser sa suppression rendait irréversible la seule erreur
    qu'on fait vraiment — se tromper en créant un compte.

    Les lignes d'ouverture partent alors avec le compte, ce qui est exact : un solde de
    départ ne décrit rien d'autre que ce compte-là.
    """
    return (
        session.execute(
            select(Operation.id)
            .where(Operation.compte_id == compte_id, Operation.est_ouverture.is_(False))
            .limit(1)
        ).first()
        is not None
    )


def supprimer_compte(session: Session, compte: Compte) -> None:
    session.delete(compte)
    session.flush()


def comptes_visibles(
    session: Session,
    principal: Principal,
    *,
    type_compte: TypeCompte | None = None,
    inclure_archives: bool = False,
) -> list[Compte]:
    """Comptes que l'appelant peut voir, éventuellement d'un seul type.

    Le filtre est posé en SQL et non sur les objets rendus : la colonne est un `String`,
    donc l'attribut vaut une chaîne à l'exécution et non un membre de `TypeCompte`. Un
    `is` sur cette valeur est faux pour TOUS les comptes, silencieusement — c'est ce qui
    a d'abord rendu une épargne vide.

    `inclure_archives` sert à l'écran de GESTION, et à lui seul. Le défaut les écarte :
    un compte archivé ne doit plus être proposé à la saisie ni compté dans un total. Mais
    l'écran qui propose l'archivage doit continuer de montrer ce qu'il a rangé, sinon
    l'action présentée comme réversible est sans retour (ERREURS.md #043).
    """
    conditions: list[ColumnElement[bool]] = [_comptes_autorises(principal)]
    if not inclure_archives:
        conditions.append(Compte.archive.is_(False))
    if type_compte is not None:
        conditions.append(Compte.type_compte == type_compte)
    return list(
        session.execute(
            select(Compte)
            .where(*conditions)
            .order_by(Compte.cree_le)
        ).scalars()
    )


def compte_visible(session: Session, principal: Principal, compte_id: uuid.UUID) -> Compte | None:
    return session.execute(
        select(Compte).where(Compte.id == compte_id, _comptes_autorises(principal))
    ).scalar_one_or_none()


def _comptes_administrables(principal: Principal) -> ColumnElement[bool]:
    """Les deux périmètres RÉUNIS, pour AGIR sur un compte déjà désigné.

    N'élargit aucun droit, et c'est la seule raison pour laquelle cette condition a le
    droit d'exister : elle réunit ce que l'appelant voit déjà en basculant de vue, jamais
    les comptes privés de quelqu'un d'autre. Elle est dérivée de `_comptes_autorises`
    plutôt que réécrite — une seconde version de la règle de confidentialité divergerait
    de la première, et c'est la plus permissive des deux qui ne préviendrait pas.

    Depuis le 22 août 2026, l'écran de gestion ne LISTE plus qu'un périmètre à la fois :
    il suit la vue, comme le reste de l'application. Cette condition reste néanmoins plus
    large que la vue courante, et volontairement — c'est un filet. Une action part avec
    l'en-tête de vue du moment où l'on clique ; refuser dès que celui-ci ne concorde plus
    avec la liste affichée produirait un « Compte introuvable » à propos de quelque chose
    qui est à l'écran. Ce message-là envoie chercher une panne qui n'existe pas, et c'est
    exactement ce qui s'est produit (ERREURS.md #043).
    """
    return or_(*(_comptes_autorises(replace(principal, vue=vue)) for vue in Vue))


def compte_administrable(
    session: Session, principal: Principal, compte_id: uuid.UUID
) -> Compte | None:
    """Un compte désigné pour être renommé, archivé ou supprimé.

    À utiliser partout où l'écran de gestion agit sur un compte qu'il vient de LISTER.
    Voir `_comptes_administrables` pour ce que cette largeur protège.

    Les écrans qui CALCULENT — ajustement de solde, détail d'épargne — gardent
    `compte_visible` : leur chiffre appartient à un seul des deux mondes.
    """
    return session.execute(
        select(Compte).where(Compte.id == compte_id, _comptes_administrables(principal))
    ).scalar_one_or_none()


def creer_categories_initiales(session: Session, foyer_id: uuid.UUID) -> list[Categorie]:
    """Amorce le foyer avec la liste par défaut.

    Un écran vide au premier lancement décourage la saisie : on crée une catégorie avant
    de pouvoir enregistrer une dépense, et c'est le moment où l'on remet à plus tard.
    Toutes sont renommables, retintables, archivables et supprimables tant qu'elles ne
    servent à aucune opération.
    """
    creees = [
        Categorie(foyer_id=foyer_id, nom=modele.nom, nature=modele.nature, teinte=modele.teinte)
        for modele in CATEGORIES_INITIALES
    ]
    session.add_all(creees)
    session.flush()
    return creees


def modifier_categorie(
    session: Session,
    categorie: Categorie,
    *,
    nom: str | None = None,
    teinte: TeinteCategorie | None = None,
    archivee: bool | None = None,
) -> Categorie:
    """La `nature` n'est volontairement PAS modifiable.

    Basculer une catégorie de dépense en revenu changerait le signe attendu de toutes les
    opérations déjà classées dessous, et donc les totaux de mois déjà clos.
    """
    if nom is not None:
        categorie.nom = nom
    if teinte is not None:
        categorie.teinte = teinte
    if archivee is not None:
        categorie.archivee = archivee
    session.flush()
    return categorie


def categorie_est_utilisee(session: Session, categorie_id: uuid.UUID) -> bool:
    return (
        session.execute(
            select(Operation.id).where(Operation.categorie_id == categorie_id).limit(1)
        ).first()
        is not None
    )


def supprimer_categorie(session: Session, categorie: Categorie) -> None:
    """Suppression définitive. L'appelant doit avoir vérifié qu'elle n'est pas utilisée :
    la base refuserait de toute façon (`ondelete=RESTRICT`)."""
    session.delete(categorie)
    session.flush()


def categories(
    session: Session, principal: Principal, *, inclure_archivees: bool = False
) -> list[Categorie]:
    conditions: list[ColumnElement[bool]] = [Categorie.foyer_id == principal.foyer_id]
    if not inclure_archivees:
        conditions.append(Categorie.archivee.is_(False))
    return list(
        session.execute(
            select(Categorie).where(*conditions).order_by(Categorie.nature, Categorie.nom)
        ).scalars()
    )


def categorie_visible(
    session: Session, principal: Principal, categorie_id: uuid.UUID
) -> Categorie | None:
    return session.execute(
        select(Categorie).where(
            Categorie.id == categorie_id, Categorie.foyer_id == principal.foyer_id
        )
    ).scalar_one_or_none()


def creer_categorie(
    session: Session,
    principal: Principal,
    *,
    nom: str,
    nature: NatureCategorie,
    teinte: TeinteCategorie,
) -> Categorie:
    categorie = Categorie(foyer_id=principal.foyer_id, nom=nom, nature=nature, teinte=teinte)
    session.add(categorie)
    session.flush()
    return categorie


def creer_operation(
    session: Session,
    principal: Principal,
    *,
    compte_id: uuid.UUID,
    libelle: str,
    montant_centimes: Cents,
    date_operation: dt.date,
    categorie_id: uuid.UUID | None = None,
    etat: EtatOperation = EtatOperation.CONFIRMEE,
    est_paie: bool = False,
    est_ouverture: bool = False,
    est_ajustement: bool = False,
    cle_import: str | None = None,
) -> Operation:
    operation = Operation(
        compte_id=compte_id,
        categorie_id=categorie_id,
        cree_par_id=principal.utilisateur_id,
        libelle=libelle,
        montant_centimes=montant_centimes,
        date_operation=date_operation,
        etat=etat,
        est_paie=est_paie,
        est_ouverture=est_ouverture,
        est_ajustement=est_ajustement,
        cle_import=cle_import,
    )
    session.add(operation)
    session.flush()
    return operation


def creer_virement(
    session: Session,
    principal: Principal,
    *,
    compte_source_id: uuid.UUID,
    compte_destination_id: uuid.UUID,
    montant_centimes: Cents,
    date_operation: dt.date,
    libelle: str,
    cle_import: str | None = None,
    compte_du_releve_id: uuid.UUID | None = None,
) -> tuple[Operation, Operation]:
    """Crée les deux moitiés d'un virement, liées par un même identifiant.

    `montant_centimes` est POSITIF : c'est la somme déplacée. Le signe est décidé ici et
    nulle part ailleurs — laisser l'appelant fournir −200 d'un côté et +200 de l'autre
    ouvrirait la porte à deux moitiés de montants différents, c'est-à-dire à de l'argent
    créé ou détruit par une faute de saisie.

    Aucune catégorie : un virement n'est ni une dépense ni un revenu, il n'a donc rien à
    classer. Lui en donner une le ferait apparaître dans un plafond.

    Les deux lignes sont ajoutées dans la même transaction. Une moitié sans l'autre serait
    pire que pas de virement du tout : de l'argent disparu d'un compte sans être arrivé
    nulle part.
    """
    virement_id = uuid.uuid4()
    # La clé d'import ne va que sur la moitié correspondant à la LIGNE DU RELEVÉ, celle du
    # compte importé. La poser sur les deux ferait deux lignes prétendant venir de la même
    # ligne de fichier ; n'en marquer aucune rendrait le réimport non idempotent, et le
    # virement serait recréé à chaque fois.
    moities = [
        Operation(
            compte_id=compte,
            cree_par_id=principal.utilisateur_id,
            libelle=libelle,
            montant_centimes=Cents(signe * int(montant_centimes)),
            date_operation=date_operation,
            etat=EtatOperation.CONFIRMEE,
            virement_id=virement_id,
            cle_import=cle_import if compte == compte_du_releve_id else None,
        )
        for compte, signe in ((compte_source_id, -1), (compte_destination_id, 1))
    ]
    session.add_all(moities)
    session.flush()
    return moities[0], moities[1]


def operations_du_virement(
    session: Session, principal: Principal, virement_id: uuid.UUID
) -> list[Operation]:
    """Les deux moitiés d'un virement, sous réserve que le foyer y ait accès.

    Sert à supprimer un virement d'un bloc : retirer une seule moitié laisserait de
    l'argent créé ou détruit.
    """
    return list(
        session.execute(
            select(Operation)
            .join(Compte, Compte.id == Operation.compte_id)
            .where(Operation.virement_id == virement_id, _comptes_autorises(principal))
        ).scalars()
    )


def operation_visible(
    session: Session, principal: Principal, operation_id: uuid.UUID
) -> Operation | None:
    return session.execute(
        select(Operation)
        .join(Compte, Compte.id == Operation.compte_id)
        .where(Operation.id == operation_id, _comptes_autorises(principal))
    ).scalar_one_or_none()


def modifier_operation(
    session: Session,
    operation: Operation,
    *,
    libelle: str | None = None,
    montant_centimes: Cents | None = None,
    date_operation: dt.date | None = None,
    categorie_id: uuid.UUID | None = None,
    categorie_fournie: bool = False,
) -> Operation:
    """Corrige une opération.

    `est_paie` n'est pas modifiable : basculer une opération en paie déplacerait les
    bornes de toutes les périodes suivantes, et donc les totaux de mois déjà consultés.
    Pour corriger une paie mal saisie, on la supprime et on la ressaisit.
    """
    if libelle is not None:
        operation.libelle = libelle
    if montant_centimes is not None:
        operation.montant_centimes = montant_centimes
    if date_operation is not None:
        operation.date_operation = date_operation
    if categorie_fournie:
        operation.categorie_id = categorie_id
    session.flush()
    return operation


def retirer_operation(session: Session, operation: Operation) -> str:
    """Retire une opération des écrans, et renvoie ce qui a été fait.

    Deux cas, et l'appelant n'a pas à les distinguer :

    - **saisie manuelle** : suppression définitive, la ligne n'a aucune raison de rester ;
    - **issue d'une récurrence** : marquée annulée et CONSERVÉE. La supprimer serait
      inutile — le job de matérialisation la recréerait au passage suivant, puisque sa
      clé d'idempotence ne la verrait plus. La garder annulée est ce qui rend le retrait
      définitif.
    """
    if operation.recurrence_id is None:
        session.delete(operation)
        session.flush()
        return "supprimee"

    operation.annulee = True
    session.flush()
    return "annulee"


def operations_visibles(
    session: Session,
    principal: Principal,
    *,
    depuis: dt.date | None = None,
    jusqu_a: dt.date | None = None,
    comptes: Sequence[uuid.UUID] | None = None,
) -> list[Operation]:
    """Opérations des comptes que l'appelant a le droit de voir.

    Les bornes de date sont **incluses** des deux côtés, comme les périodes budgétaires.
    """
    # Les opérations annulées ne remontent jamais : elles n'existent en base que pour
    # empêcher le job de les recréer.
    conditions: list[ColumnElement[bool]] = [
        _comptes_autorises(principal),
        Operation.annulee.is_(False),
    ]
    if depuis is not None:
        conditions.append(Operation.date_operation >= depuis)
    if jusqu_a is not None:
        conditions.append(Operation.date_operation <= jusqu_a)
    if comptes is not None:
        conditions.append(Operation.compte_id.in_(comptes))

    return list(
        session.execute(
            select(Operation)
            .join(Compte, Compte.id == Operation.compte_id)
            .where(*conditions)
            .order_by(Operation.date_operation.desc(), Operation.cree_le.desc())
        ).scalars()
    )


def ids_des_comptes(
    session: Session, principal: Principal, *, type_compte: TypeCompte
) -> list[uuid.UUID]:
    """Identifiants des comptes du foyer d'un type donné, archivés compris.

    Les archivés sont inclus à dessein : leur argent existe toujours, et les exclure ici
    ferait varier le solde du foyer au moment d'archiver un compte — un changement de
    présentation qui déplacerait un chiffre. `comptes_visibles` les écarte parce qu'elle
    sert à PROPOSER des comptes, ce qui est une autre question.
    """
    return list(
        session.execute(
            select(Compte.id).where(
                _comptes_autorises(principal), Compte.type_compte == type_compte
            )
        ).scalars()
    )


def total_verse_par_virement(
    session: Session,
    principal: Principal,
    *,
    comptes: Sequence[uuid.UUID],
    debut: dt.date,
    fin: dt.date,
) -> Cents:
    """Somme des virements ENTRANTS sur ces comptes, entre deux dates incluses.

    Seulement les virements, et seulement les entrées. Un intérêt versé par la banque ou
    une saisie manuelle sur le livret ne sont pas « ce que j'ai mis de côté ce mois-ci » —
    les compter gonflerait un chiffre dont l'utilisateur se sert pour juger son effort.

    Ce n'est volontairement pas un agrégat de `domain/agregats.py` : les agrégats
    répondent à « ce solde vaut combien », celui-ci à « d'où vient l'argent ». Lui donner
    une ligne dans la table obligerait les quatre autres à déclarer un axe qui ne les
    concerne pas.
    """
    if not comptes:
        return Cents(0)
    total = session.execute(
        # La jointure n'est pas décorative : `_comptes_autorises` porte sur `Compte`, et
        # sans elle PostgreSQL ajoute la table au FROM en produit cartésien. La somme est
        # alors multipliée par le nombre de comptes du foyer — un chiffre d'argent faux,
        # et faux d'un facteur qui change avec le nombre de comptes.
        select(func.coalesce(func.sum(Operation.montant_centimes), 0))
        .select_from(Operation)
        .join(Compte, Compte.id == Operation.compte_id)
        .where(
            _comptes_autorises(principal),
            Operation.compte_id.in_(comptes),
            Operation.virement_id.is_not(None),
            Operation.montant_centimes > 0,
            Operation.annulee.is_(False),
            Operation.date_operation >= debut,
            Operation.date_operation <= fin,
        )
    ).scalar_one()
    return Cents(int(total))


def operations_pour_calcul(
    session: Session, principal: Principal, *, comptes: Sequence[uuid.UUID] | None = None
) -> list[OperationCalcul]:
    """Vue minimale des opérations, prête pour `domain.agregats.calculer`.

    Sans borne de date : les agrégats appliquent eux-mêmes leurs bornes, et deux endroits
    qui filtreraient le temps finiraient par ne plus filtrer pareil.
    """
    return [
        OperationCalcul(
            montant=Cents(operation.montant_centimes),
            date_operation=operation.date_operation,
            etat=operation.etat,
            est_ouverture=operation.est_ouverture,
            annulee=operation.annulee,
            # Sans cette ligne, la règle écrite dans le domaine ne s'appliquerait jamais :
            # toute opération arriverait avec `est_virement=False`, et les virements
            # entreraient dans les dépenses malgré la table qui dit le contraire.
            est_virement=operation.virement_id is not None,
            est_ajustement=operation.est_ajustement,
        )
        for operation in operations_visibles(session, principal, comptes=comptes)
    ]


def dates_de_paie(
    session: Session, principal: Principal, *, comptes: Sequence[uuid.UUID] | None = None
) -> list[dt.date]:
    """Dates des paies, qui ouvrent les périodes budgétaires.

    Les opérations seulement PRÉVUES sont exclues : une paie qui n'a pas eu lieu ne peut
    pas ouvrir une période, sinon le budget démarrerait sur un revenu imaginaire.
    """
    conditions: list[ColumnElement[bool]] = [
        _comptes_autorises(principal),
        Operation.est_paie.is_(True),
        Operation.etat != EtatOperation.PREVUE,
        Operation.annulee.is_(False),
    ]
    if comptes is not None:
        conditions.append(Operation.compte_id.in_(comptes))

    return list(
        session.execute(
            select(Operation.date_operation)
            .join(Compte, Compte.id == Operation.compte_id)
            .where(*conditions)
            .order_by(Operation.date_operation)
        ).scalars()
    )


def cles_deja_importees(session: Session, principal: Principal) -> set[str]:
    """Les clés des lignes de relevé déjà importées, pour le périmètre de l'appelant.

    Un `set` plutôt qu'une liste : l'import compare chaque ligne du fichier à cet ensemble,
    et un fichier de deux cents lignes contre un historique de plusieurs milliers ferait
    autant de parcours linéaires.
    """
    lignes = session.execute(
        select(Operation.cle_import)
        .join(Compte, Compte.id == Operation.compte_id)
        .where(Compte.foyer_id == principal.foyer_id, Operation.cle_import.is_not(None))
    ).scalars()
    return {cle for cle in lignes if cle is not None}


def correspondances_du_foyer(session: Session, principal: Principal) -> list[Correspondance]:
    """Ce que le foyer a retenu des imports précédents, dans la forme du domaine.

    Converties ici plutôt que dans la route : le domaine ne doit pas connaître les modèles
    SQLAlchemy, et la route n'a pas à savoir comment ils sont faits.
    """
    lignes = session.execute(
        select(CorrespondanceImport).where(CorrespondanceImport.foyer_id == principal.foyer_id)
    ).scalars()
    return [
        Correspondance(
            # Converti EXPLICITEMENT : la colonne est un `String`, et SQLAlchemy en rend
            # une chaîne brute, pas un membre de l'énumération. Le domaine compare ses
            # genres avec `is`, qui est le bon opérateur pour un enum et qui rendrait
            # silencieusement `False` sur une chaîne — la correspondance ne serait jamais
            # retrouvée, sans qu'aucune erreur ne se produise nulle part.
            genre=GenreCorrespondance(ligne.genre),
            valeur=ligne.valeur,
            categorie_id=str(ligne.categorie_id),
        )
        for ligne in lignes
    ]


def retenir_la_correspondance(
    session: Session,
    principal: Principal,
    *,
    genre: GenreCorrespondance,
    valeur: str,
    categorie_id: uuid.UUID,
) -> None:
    """Retient un rangement, ou remplace celui qui existait.

    Remplacer et non ignorer : si l'utilisateur range Intermarché ailleurs qu'avant, c'est
    qu'il a changé d'avis, et le prochain import doit suivre son dernier choix — pas le
    premier qu'il ait fait.
    """
    if not valeur.strip():
        return
    existante = session.execute(
        select(CorrespondanceImport).where(
            CorrespondanceImport.foyer_id == principal.foyer_id,
            CorrespondanceImport.genre == genre,
            CorrespondanceImport.valeur == valeur,
        )
    ).scalar_one_or_none()
    if existante is not None:
        existante.categorie_id = categorie_id
        session.flush()
        return
    session.add(
        CorrespondanceImport(
            foyer_id=principal.foyer_id,
            genre=genre,
            valeur=valeur,
            categorie_id=categorie_id,
        )
    )
    session.flush()
