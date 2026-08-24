"""Accès aux enveloppes et à leur journal.

Chaque lecture prend un `Principal` : le périmètre n'est jamais implicite.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mycounts.domain.enveloppes import Rollover, TypeMouvement, UsageEnveloppe
from mycounts.domain.montants import Cents
from mycounts.models.budget import Enveloppe, MouvementEnveloppe
from mycounts.repository.base import Principal


def enveloppes_du_foyer(
    session: Session, principal: Principal, *, archivees: bool = False
) -> list[Enveloppe]:
    """Enveloppes visibles, journal chargé d'avance.

    `selectinload` et non un chargement paresseux : le solde de chaque enveloppe se
    recalcule depuis ses mouvements, donc les afficher toutes déclencherait une requête
    par enveloppe — le nombre de requêtes grandirait avec le nombre d'enveloppes.
    """
    # `vue` existait depuis `06db5cb0ed21` et aucune requête ne la lisait : les
    # enveloppes personnelles apparaissaient dans la vue foyer, sur un écran qui annonce
    # ne montrer que l'argent commun. Une enveloppe découpe une ÉPARGNE, et les deux
    # épargnes sont étanches ; les mélanger donnait un découpage dont la somme dépassait
    # ce qu'il découpe.
    conditions = [
        Enveloppe.foyer_id == principal.foyer_id,
        Enveloppe.vue == principal.vue,
    ]
    if not archivees:
        conditions.append(Enveloppe.archive.is_(False))
    return list(
        session.execute(
            select(Enveloppe)
            .where(*conditions)
            .options(selectinload(Enveloppe.mouvements))
            .order_by(Enveloppe.cree_le)
        ).scalars()
    )


def enveloppe_visible(
    session: Session, principal: Principal, enveloppe_id: uuid.UUID
) -> Enveloppe | None:
    return session.execute(
        select(Enveloppe)
        .where(
            Enveloppe.id == enveloppe_id,
            Enveloppe.foyer_id == principal.foyer_id,
            Enveloppe.vue == principal.vue,
        )
        .options(selectinload(Enveloppe.mouvements))
    ).scalar_one_or_none()


def creer_enveloppe(
    session: Session,
    principal: Principal,
    *,
    nom: str,
    categorie_id: uuid.UUID | None = None,
    compte_prefere_id: uuid.UUID | None = None,
    cible_centimes: int | None = None,
    date_cible: dt.date | None = None,
    usage: UsageEnveloppe = UsageEnveloppe.FONCTIONNEMENT,
    rollover: Rollover = Rollover.REPORT,
    priorite: int = 0,
    contribution_mensuelle_centimes: int | None = None,
) -> Enveloppe:
    enveloppe = Enveloppe(
        foyer_id=principal.foyer_id,
        cree_par_id=principal.utilisateur_id,
        # Déduite du périmètre regardé, jamais demandée : c'est là que l'utilisateur a
        # déjà dit de quelle épargne il parle. La redemander dans le formulaire
        # permettrait de la contredire et de créer une enveloppe qui disparaît de l'écran
        # où on vient de la poser.
        vue=principal.vue,
        nom=nom,
        categorie_id=categorie_id,
        compte_prefere_id=compte_prefere_id,
        cible_centimes=cible_centimes,
        date_cible=date_cible,
        usage=usage,
        rollover=rollover,
        priorite=priorite,
        contribution_mensuelle_centimes=contribution_mensuelle_centimes,
    )
    session.add(enveloppe)
    session.flush()
    return enveloppe


def modifier_enveloppe(
    session: Session,
    enveloppe: Enveloppe,
    *,
    nom: str | None = None,
    categorie_id: uuid.UUID | None = None,
    categorie_fournie: bool = False,
    compte_prefere_id: uuid.UUID | None = None,
    compte_prefere_fourni: bool = False,
    cible_centimes: int | None = None,
    date_cible: dt.date | None = None,
    archive: bool | None = None,
    usage: UsageEnveloppe | None = None,
    rollover: Rollover | None = None,
    priorite: int | None = None,
    contribution_mensuelle_centimes: int | None = None,
) -> Enveloppe:
    """Les champs laissés à `None` ne sont pas touchés.

    Conséquence assumée : on ne peut pas RETIRER une cible par cette fonction, seulement
    la changer. Retirer une cible est un geste rare et lourd de sens — la préparation
    mensuelle cesse alors de recommander quoi que ce soit — il aura sa propre route.
    """
    if nom is not None:
        enveloppe.nom = nom
    if categorie_fournie:
        enveloppe.categorie_id = categorie_id
    if compte_prefere_fourni:
        enveloppe.compte_prefere_id = compte_prefere_id
    if cible_centimes is not None:
        enveloppe.cible_centimes = cible_centimes
    if date_cible is not None:
        enveloppe.date_cible = date_cible
    if archive is not None:
        enveloppe.archive = archive
    if usage is not None:
        enveloppe.usage = usage
    if rollover is not None:
        enveloppe.rollover = rollover
    if priorite is not None:
        enveloppe.priorite = priorite
    if contribution_mensuelle_centimes is not None:
        enveloppe.contribution_mensuelle_centimes = contribution_mensuelle_centimes
    session.flush()
    return enveloppe


def supprimer_enveloppe(session: Session, enveloppe: Enveloppe) -> None:
    """Supprime l'enveloppe ET son journal.

    Aucun argent ne bouge : une enveloppe ne détient rien, elle nomme une part de ce qui
    est déjà en banque. Supprimer la dernière enveloppe rend simplement tout l'argent
    « non affecté ».
    """
    session.delete(enveloppe)
    session.flush()


def ajouter_mouvement(
    session: Session,
    enveloppe: Enveloppe,
    *,
    type: TypeMouvement,
    montant_centimes: Cents,
    date_mouvement: dt.date,
    libelle: str = "",
    operation_id: uuid.UUID | None = None,
) -> MouvementEnveloppe:
    """Ajoute une ligne au journal. Ne modifie jamais une ligne existante.

    Corriger une enveloppe consiste à ajouter un mouvement d'ajustement, pas à réécrire
    l'histoire : six mois plus tard, c'est la seule façon de comprendre un écart.
    """
    mouvement = MouvementEnveloppe(
        enveloppe_id=enveloppe.id,
        type=type,
        montant_centimes=int(montant_centimes),
        date_mouvement=date_mouvement,
        libelle=libelle,
        operation_id=operation_id,
    )
    session.add(mouvement)
    session.flush()
    return mouvement
