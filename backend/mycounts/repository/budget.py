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

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import Session

from mycounts.domain.agregats import EtatOperation, OperationCalcul
from mycounts.domain.categories import CATEGORIES_INITIALES
from mycounts.domain.montants import Cents
from mycounts.models.budget import Categorie, Compte, NatureCategorie, Operation, TeinteCategorie
from mycounts.repository.base import Principal


def _comptes_autorises(principal: Principal) -> ColumnElement[bool]:
    """Condition de visibilité d'un compte. Auteur unique de la règle de confidentialité.

    L'écrire une seconde fois dans une requête voisine est la façon la plus sûre de créer
    une fuite : les deux versions divergeront, et la plus permissive ne préviendra pas.
    """
    return and_(
        Compte.foyer_id == principal.foyer_id,
        or_(Compte.prive.is_(False), Compte.proprietaire_id == principal.utilisateur_id),
    )


def creer_compte(
    session: Session, principal: Principal, *, nom: str, prive: bool = True
) -> Compte:
    compte = Compte(
        foyer_id=principal.foyer_id,
        proprietaire_id=principal.utilisateur_id,
        nom=nom,
        prive=prive,
    )
    session.add(compte)
    session.flush()
    return compte


def comptes_visibles(session: Session, principal: Principal) -> list[Compte]:
    return list(
        session.execute(
            select(Compte)
            .where(_comptes_autorises(principal), Compte.archive.is_(False))
            .order_by(Compte.cree_le)
        ).scalars()
    )


def compte_visible(session: Session, principal: Principal, compte_id: uuid.UUID) -> Compte | None:
    return session.execute(
        select(Compte).where(Compte.id == compte_id, _comptes_autorises(principal))
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
    )
    session.add(operation)
    session.flush()
    return operation


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
    if categorie_id is not None:
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
