"""Routes des enveloppes.

**La règle qui commande tout ce fichier** :

    Une allocation vers une enveloppe ne crée JAMAIS de mouvement bancaire.

Aucune route d'ici n'écrit dans `operation`. Le compte dit où l'argent EST, l'enveloppe à
quoi il est PROMIS. Les confondre ferait apparaître de l'argent qui n'existe pas.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.api.enveloppes_schemas import (
    DemandeEnveloppe,
    DemandeMouvement,
    EnveloppePublique,
    ModificationEnveloppe,
    MouvementPublic,
    RepartitionPublique,
)
from mycounts.domain.agregats import Agregat, calculer
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.comptes import TypeCompte
from mycounts.domain.enveloppes import Enveloppe as EnveloppeCalcul
from mycounts.domain.enveloppes import Mouvement, repartir
from mycounts.domain.montants import Cents
from mycounts.models.budget import Enveloppe
from mycounts.repository import budget as depot_budget
from mycounts.repository import enveloppes as depot

routeur = APIRouter(tags=["enveloppes"])


def _en_calcul(enveloppe: Enveloppe) -> EnveloppeCalcul:
    return EnveloppeCalcul(
        nom=enveloppe.nom,
        mouvements=tuple(
            Mouvement(type=m.type, montant=Cents(m.montant_centimes))
            for m in enveloppe.mouvements
        ),
        cible=None if enveloppe.cible_centimes is None else Cents(enveloppe.cible_centimes),
    )


def _epargne_totale(session: SessionBase, principal: PrincipalCourant) -> Cents:
    """Somme des soldes réels des comptes d'ÉPARGNE.

    C'est cette somme que les enveloppes découpent — pas le solde du quotidien. Une
    enveloppe promet de l'argent mis de côté ; la rapporter au compte courant ferait
    croire qu'on peut réserver ce qui sert à vivre le mois.
    """
    jour = aujourd_hui()
    comptes = depot_budget.ids_des_comptes(session, principal, type_compte=TypeCompte.EPARGNE)
    if not comptes:
        return Cents(0)
    return calculer(
        Agregat.SOLDE_REEL,
        depot_budget.operations_pour_calcul(session, principal, comptes=comptes),
        aujourd_hui=jour,
        fin_de_fenetre=jour,
    )


def _repartition(session: SessionBase, principal: PrincipalCourant) -> RepartitionPublique:
    enveloppes = depot.enveloppes_du_foyer(session, principal)
    calculs = [_en_calcul(e) for e in enveloppes]
    etat = repartir(_epargne_totale(session, principal), calculs)

    return RepartitionPublique(
        epargne_totale_centimes=int(etat.epargne_totale),
        reserve_centimes=int(etat.reserve),
        non_affecte_centimes=int(etat.non_affecte),
        decouvert=etat.decouvert,
        enveloppes=[
            EnveloppePublique(
                id=modele.id,
                nom=modele.nom,
                categorie_id=modele.categorie_id,
                categorie_nom=modele.categorie.nom if modele.categorie else None,
                compte_prefere_id=modele.compte_prefere_id,
                cible_centimes=modele.cible_centimes,
                date_cible=modele.date_cible,
                solde_centimes=int(calcul.solde),
                place_centimes=None if calcul.place is None else int(calcul.place),
                part=etat.part(calcul),
                archive=modele.archive,
            )
            for modele, calcul in zip(enveloppes, calculs, strict=True)
        ],
    )


@routeur.get("/enveloppes", response_model=RepartitionPublique)
def lister(session: SessionBase, principal: PrincipalCourant) -> RepartitionPublique:
    """Toutes les enveloppes, avec ce qui reste non affecté.

    Le non-affecté est rendu au même niveau que les enveloppes, et non déduit par le
    client : c'est la grandeur qui dit ce qu'on peut encore réserver, et la laisser
    calculer ailleurs ouvrirait la porte à deux définitions du mot « disponible ».
    """
    return _repartition(session, principal)


@routeur.post(
    "/enveloppes", response_model=RepartitionPublique, status_code=status.HTTP_201_CREATED
)
def creer(
    demande: DemandeEnveloppe, session: SessionBase, principal: PrincipalCourant
) -> RepartitionPublique:
    if demande.categorie_id is not None and (
        depot_budget.categorie_visible(session, principal, demande.categorie_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")
    if demande.compte_prefere_id is not None and (
        depot_budget.compte_visible(session, principal, demande.compte_prefere_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    enveloppe = depot.creer_enveloppe(
        session,
        principal,
        nom=demande.nom,
        categorie_id=demande.categorie_id,
        compte_prefere_id=demande.compte_prefere_id,
        cible_centimes=demande.cible_centimes,
        date_cible=demande.date_cible,
    )
    # Une allocation initiale reste un MOUVEMENT : elle entre dans le journal comme les
    # autres, sinon le solde de départ serait la seule valeur que l'historique ignore.
    if demande.allocation_initiale_centimes > 0:
        depot.ajouter_mouvement(
            session,
            enveloppe,
            type=demande.type_allocation_initiale,
            montant_centimes=Cents(demande.allocation_initiale_centimes),
            date_mouvement=aujourd_hui(),
            libelle="Allocation initiale",
        )
    session.commit()
    return _repartition(session, principal)


@routeur.patch("/enveloppes/{enveloppe_id}", response_model=RepartitionPublique)
def modifier(
    enveloppe_id: uuid.UUID,
    demande: ModificationEnveloppe,
    session: SessionBase,
    principal: PrincipalCourant,
) -> RepartitionPublique:
    enveloppe = depot.enveloppe_visible(session, principal, enveloppe_id)
    if enveloppe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enveloppe introuvable."
        )

    depot.modifier_enveloppe(
        session,
        enveloppe,
        nom=demande.nom,
        categorie_id=demande.categorie_id,
        compte_prefere_id=demande.compte_prefere_id,
        cible_centimes=demande.cible_centimes,
        date_cible=demande.date_cible,
        archive=demande.archive,
    )
    session.commit()
    return _repartition(session, principal)


@routeur.delete("/enveloppes/{enveloppe_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    enveloppe_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> None:
    """Supprime l'enveloppe et son journal. Aucun argent ne bouge.

    Une enveloppe ne détient rien : elle nomme une part de ce qui est déjà en banque.
    La supprimer rend simplement cette part « non affectée ». C'est pourquoi il n'y a pas
    de refus ici, contrairement aux comptes — il n'y a rien à perdre.
    """
    enveloppe = depot.enveloppe_visible(session, principal, enveloppe_id)
    if enveloppe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enveloppe introuvable."
        )
    depot.supprimer_enveloppe(session, enveloppe)
    session.commit()


@routeur.post(
    "/enveloppes/{enveloppe_id}/mouvements",
    response_model=RepartitionPublique,
    status_code=status.HTTP_201_CREATED,
)
def ajouter_mouvement(
    enveloppe_id: uuid.UUID,
    demande: DemandeMouvement,
    session: SessionBase,
    principal: PrincipalCourant,
) -> RepartitionPublique:
    """Ajoute une ligne au journal. **N'écrit aucune opération bancaire.**

    Réserver 200 € pour les vacances ne déplace pas 200 € : cela dit que 200 € des
    livrets sont promis aux vacances. L'argent était déjà là.
    """
    enveloppe = depot.enveloppe_visible(session, principal, enveloppe_id)
    if enveloppe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enveloppe introuvable."
        )

    depot.ajouter_mouvement(
        session,
        enveloppe,
        type=demande.type,
        montant_centimes=Cents(demande.montant_centimes),
        date_mouvement=demande.date_mouvement or aujourd_hui(),
        libelle=demande.libelle,
    )
    session.commit()
    return _repartition(session, principal)


@routeur.get("/enveloppes/{enveloppe_id}/journal", response_model=list[MouvementPublic])
def journal(
    enveloppe_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> list[MouvementPublic]:
    enveloppe = depot.enveloppe_visible(session, principal, enveloppe_id)
    if enveloppe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enveloppe introuvable."
        )
    return [
        MouvementPublic(
            id=m.id,
            type=m.type,
            montant_centimes=m.montant_centimes,
            date_mouvement=m.date_mouvement,
            libelle=m.libelle,
        )
        for m in sorted(enveloppe.mouvements, key=lambda m: (m.date_mouvement, m.cree_le))
    ]
