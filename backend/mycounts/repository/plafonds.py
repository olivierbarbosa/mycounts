"""Accès aux plafonds de catégorie."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from mycounts.domain.montants import Cents
from mycounts.domain.plafonds import OperationCategorisee
from mycounts.models.budget import Categorie, Compte, Operation, Plafond
from mycounts.repository.base import Principal, Vue
from mycounts.repository.budget import _comptes_autorises


def _plafonds_autorises(principal: Principal) -> ColumnElement[bool]:
    """Condition de visibilité d'un plafond. Auteur unique de la règle.

    La colonne `vue` existait depuis la migration `06db5cb0ed21` et **aucune requête ne la
    lisait** : en vue foyer, on voyait ses plafonds personnels, sur un écran qui annonce
    ne montrer que l'argent commun. Une colonne qu'aucune requête ne lit fait croire au
    modèle qu'une fonction existe (corrigé le 22 août 2026).

    Les deux vues n'ont pas la même règle de propriété, et ce n'est pas une inconséquence :
    l'unicité posée en base la dictait déjà.

    - **PERSONNELLE** — les siens. Voir le plafond de l'autre membre reviendrait à voir ses
      intentions de dépense. Unicité `(utilisateur_id, categorie_id, vue)`.
    - **FOYER** — ceux du foyer, quel qu'en soit l'auteur. Un plafond sur les dépenses
      communes est une décision commune : `uq_plafond_de_foyer_par_categorie` n'en admet
      qu'UN par catégorie, tous membres confondus. En faire un objet personnel
      contredirait cet index, et le second membre à en poser un recevrait un conflit
      qu'aucun écran ne saurait expliquer.
    """
    if not principal.mode_legacy:
        return Plafond.espace_id == principal.espace_id
    if principal.vue is Vue.FOYER:
        return Plafond.vue == Vue.FOYER
    return and_(
        Plafond.vue == Vue.PERSONNELLE,
        Plafond.utilisateur_id == principal.utilisateur_id,
    )


def plafonds_de(session: Session, principal: Principal) -> list[Plafond]:
    """Plafonds du périmètre courant. Voir `_plafonds_autorises`."""
    return list(
        session.execute(
            select(Plafond)
            .join(Categorie, Categorie.id == Plafond.categorie_id)
            .where(
                _plafonds_autorises(principal),
                (
                    Categorie.foyer_id == principal.foyer_id
                    if principal.mode_legacy
                    else Categorie.espace_id == principal.espace_id
                ),
            )
            .order_by(Categorie.nom)
        ).scalars()
    )


def plafond_visible(
    session: Session, principal: Principal, plafond_id: uuid.UUID
) -> Plafond | None:
    return session.execute(
        select(Plafond).where(Plafond.id == plafond_id, _plafonds_autorises(principal))
    ).scalar_one_or_none()


def plafond_pour_categorie(
    session: Session, principal: Principal, categorie_id: uuid.UUID
) -> Plafond | None:
    return session.execute(
        select(Plafond).where(
            _plafonds_autorises(principal),
            Plafond.categorie_id == categorie_id,
        )
    ).scalar_one_or_none()


def definir_plafond(
    session: Session,
    principal: Principal,
    *,
    categorie_id: uuid.UUID,
    montant_centimes: Cents,
) -> Plafond:
    """Crée le plafond du périmètre courant, ou met à jour celui qui existe déjà.

    Un seul plafond par catégorie et par vue : deux limites concurrentes sur la même
    catégorie n'auraient aucun sens et l'interface devrait en choisir une arbitrairement.
    En vue foyer, ce « déjà » vaut pour TOUT le foyer — l'index n'en admet qu'un, et
    modifier celui d'un autre membre est le comportement voulu : c'est une limite commune.
    """
    existant = plafond_pour_categorie(session, principal, categorie_id)
    if existant is not None:
        existant.montant_centimes = montant_centimes
        session.flush()
        return existant

    plafond = Plafond(
        espace_id=principal.espace_id,
        utilisateur_id=principal.utilisateur_id,
        # La vue est DÉDUITE du périmètre regardé, jamais demandée : c'est là que
        # l'utilisateur a déjà dit de quel argent il parle. La redemander dans le
        # formulaire permettrait de la contredire et de créer un plafond qui disparaît de
        # l'écran où on vient de le poser — la même faute que la case « compte joint ».
        vue=principal.vue,
        categorie_id=categorie_id,
        montant_centimes=montant_centimes,
    )
    session.add(plafond)
    session.flush()
    return plafond


def supprimer_plafond(session: Session, plafond: Plafond) -> None:
    session.delete(plafond)
    session.flush()


def operations_categorisees(
    session: Session, principal: Principal
) -> list[OperationCategorisee]:
    """Vue des opérations prête pour le calcul des plafonds.

    Sans borne de date : les agrégats appliquent eux-mêmes leurs bornes, et deux endroits
    qui filtreraient le temps finiraient par ne plus filtrer pareil.
    """
    lignes = session.execute(
        select(Operation)
        .join(Compte, Compte.id == Operation.compte_id)
        .where(_comptes_autorises(principal))
    ).scalars()

    return [
        OperationCategorisee(
            montant=Cents(o.montant_centimes),
            date_operation=o.date_operation,
            etat=o.etat,
            est_ouverture=o.est_ouverture,
            annulee=o.annulee,
            categorie_id=o.categorie_id,
        )
        for o in lignes
    ]
