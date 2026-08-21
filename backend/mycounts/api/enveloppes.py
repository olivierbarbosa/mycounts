"""Routes des enveloppes.

**La règle qui commande tout ce fichier** :

    Une allocation vers une enveloppe ne crée JAMAIS de mouvement bancaire.

Aucune route d'ici n'écrit dans `operation`. Le compte dit où l'argent EST, l'enveloppe à
quoi il est PROMIS. Les confondre ferait apparaître de l'argent qui n'existe pas.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status

from mycounts.api.budget import resume_de_la_periode
from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.api.enveloppes_schemas import (
    DemandeEnveloppe,
    DemandeMouvement,
    DemandePreparation,
    EnveloppePublique,
    LignePreparationPublique,
    ModificationEnveloppe,
    MouvementPublic,
    PreparationPublique,
    RepartitionPublique,
)
from mycounts.domain.agregats import Agregat, calculer
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.comptes import TypeCompte
from mycounts.domain.enveloppes import Enveloppe as EnveloppeCalcul
from mycounts.domain.enveloppes import (
    Mouvement,
    TypeMouvement,
    contribution_theorique,
    preparer_la_periode,
    repartir,
)
from mycounts.domain.montants import Cents
from mycounts.models.budget import Enveloppe
from mycounts.repository import budget as depot_budget
from mycounts.repository import enveloppes as depot
from mycounts.repository import plafonds as depot_plafonds

routeur = APIRouter(tags=["enveloppes"])


def _en_calcul(enveloppe: Enveloppe) -> EnveloppeCalcul:
    return EnveloppeCalcul(
        nom=enveloppe.nom,
        mouvements=tuple(
            Mouvement(type=m.type, montant=Cents(m.montant_centimes))
            for m in enveloppe.mouvements
        ),
        cible=None if enveloppe.cible_centimes is None else Cents(enveloppe.cible_centimes),
        date_cible=enveloppe.date_cible,
        usage=enveloppe.usage,
        rollover=enveloppe.rollover,
        priorite=enveloppe.priorite,
        contribution_mensuelle=(
            None
            if enveloppe.contribution_mensuelle_centimes is None
            else Cents(enveloppe.contribution_mensuelle_centimes)
        ),
    )


def _capacite_epargne(session: SessionBase, principal: PrincipalCourant) -> int:
    """Ce qu'on peut mettre de côté : le solde PROJETÉ du quotidien, jamais négatif.

    Projeté et non réel — ce qui reste aujourd'hui n'est pas ce qui restera après les
    prélèvements de la fin du mois. Placer le réel viderait le compte courant juste avant
    l'échéance du loyer.

    Le calcul est celui de l'accueil, pas un second : deux définitions de « ce qu'il me
    reste » finiraient par ne plus donner le même chiffre, et l'utilisateur croirait à une
    erreur de l'une des deux pages.
    """
    return max(0, resume_de_la_periode(session, principal).solde_projete)


def _seul_compte(
    session: SessionBase, principal: PrincipalCourant, type_compte: TypeCompte
) -> uuid.UUID | None:
    """L'unique compte de ce type, ou `None` s'il y en a zéro ou plusieurs.

    « Plusieurs » rend `None` volontairement : en choisir un ferait partir l'argent d'un
    endroit que l'utilisateur n'a pas désigné, et l'écran n'aurait rien dit.
    """
    comptes = depot_budget.ids_des_comptes(session, principal, type_compte=type_compte)
    return comptes[0] if len(comptes) == 1 else None


def _compte_epargne_suggere(
    session: SessionBase, principal: PrincipalCourant, enveloppes: Sequence[Enveloppe]
) -> uuid.UUID | None:
    """Vers quel compte proposer le virement.

    La préférence des enveloppes d'abord, et seulement si elles s'ACCORDENT : deux
    enveloppes qui visent deux livrets différents ne désignent aucun gagnant, et en
    choisir un au hasard poserait un défaut que l'utilisateur ne saurait pas d'où il vient.
    À défaut, le premier compte d'épargne — un seul candidat est une réponse, pas une
    supposition.

    Une préférence de couverture ne déclenche AUCUN mouvement automatique : elle
    pré-remplit un formulaire, que l'utilisateur valide.
    """
    prefers = {e.compte_prefere_id for e in enveloppes if e.compte_prefere_id is not None}
    if len(prefers) == 1:
        return prefers.pop()
    epargnes = depot_budget.ids_des_comptes(session, principal, type_compte=TypeCompte.EPARGNE)
    return epargnes[0] if epargnes else None


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
    """L'état actuel des enveloppes — et « actuel » est ici une promesse, pas une figure
    de style.

    `session.expire_all()` d'abord, parce que les sessions du projet sont créées avec
    `expire_on_commit=False` : après une écriture, les objets déjà chargés gardent l'état
    qu'ils avaient AVANT. Une route qui ajoutait un mouvement puis renvoyait cette
    répartition annonçait donc le solde d'avant son propre travail — mesuré le 20 août
    2026 : allouer 200 € renvoyait un solde de 0, et l'écran l'affichait tel quel jusqu'au
    rechargement suivant.

    Le défaut existait depuis le lot E1 et aucun test ne le voyait : tous relisaient l'état
    par un second appel, c'est-à-dire précisément par le chemin qui contourne le cache.
    """
    session.expire_all()
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
                contribution_theorique_centimes=(
                    None
                    if (theorique := contribution_theorique(calcul, aujourd_hui())) is None
                    else int(theorique)
                ),
                part=etat.part(calcul),
                archive=modele.archive,
                usage=modele.usage,
                rollover=modele.rollover,
                priorite=modele.priorite,
                contribution_mensuelle_centimes=modele.contribution_mensuelle_centimes,
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
        usage=demande.usage,
        rollover=demande.rollover,
        priorite=demande.priorite,
        contribution_mensuelle_centimes=demande.contribution_mensuelle_centimes,
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
        usage=demande.usage,
        rollover=demande.rollover,
        priorite=demande.priorite,
        contribution_mensuelle_centimes=demande.contribution_mensuelle_centimes,
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


def _plafonds_par_enveloppe(
    session: SessionBase, principal: PrincipalCourant, enveloppes: list[Enveloppe]
) -> dict[str, Cents]:
    """Le plafond de la catégorie de chaque enveloppe, indexé par NOM d'enveloppe.

    Par nom et non par identifiant de catégorie : le domaine ne connaît pas les
    identifiants de la base, et lui en passer ferait entrer un détail de persistance dans
    une fonction de calcul. Le nom d'enveloppe est unique par foyer — une contrainte
    d'unicité le garantit.
    """
    par_enveloppe: dict[str, Cents] = {}
    for enveloppe in enveloppes:
        if enveloppe.categorie_id is None:
            continue
        plafond = depot_plafonds.plafond_pour_categorie(session, principal, enveloppe.categorie_id)
        if plafond is not None:
            par_enveloppe[enveloppe.nom] = Cents(plafond.montant_centimes)
    return par_enveloppe


@routeur.get("/enveloppes/preparation", response_model=PreparationPublique)
def preparation(session: SessionBase, principal: PrincipalCourant) -> PreparationPublique:
    """Ce que la période qui s'ouvre propose de faire. N'ÉCRIT RIEN.

    Olivier a choisi que le passage de période ne touche à l'argent qu'après validation
    explicite : cette route calcule, `POST` applique. La séparation n'est pas une politesse
    — elle est ce qui permet de voir avant que ça bouge.

    Rejouer cette route est sans effet, et rejouer le `POST` qui la suit ne double rien
    non plus : le calcul part de l'état réel des enveloppes, si bien qu'une préparation
    déjà appliquée produit une proposition vide.
    """
    enveloppes = depot.enveloppes_du_foyer(session, principal)
    calculs = [_en_calcul(e) for e in enveloppes]
    etat = repartir(_epargne_totale(session, principal), calculs)

    proposition = preparer_la_periode(
        etat.non_affecte,
        calculs,
        _plafonds_par_enveloppe(session, principal, enveloppes),
        # Passé TOUJOURS depuis l'API : sans lui, une enveloppe qui ne porte qu'un objectif
        # et une échéance ne reçoit aucune recommandation, alors qu'elle contient tout ce
        # qu'il faut pour en calculer une.
        aujourd_hui(),
    )
    par_nom = {e.nom: e.id for e in enveloppes}

    return PreparationPublique(
        lignes=[
            LignePreparationPublique(
                enveloppe_id=par_nom[ligne.nom],
                nom=ligne.nom,
                a_liberer_centimes=int(ligne.a_liberer),
                demande_un_choix=ligne.demande_un_choix,
                recommande_centimes=int(ligne.recommande),
                place_centimes=None if ligne.place is None else int(ligne.place),
                limitee_par_le_disponible=ligne.limitee_par_le_disponible,
            )
            for ligne in proposition.lignes
        ],
        capacite_epargne_centimes=_capacite_epargne(session, principal),
        compte_courant_suggere_id=_seul_compte(session, principal, TypeCompte.COURANT),
        compte_epargne_suggere_id=_compte_epargne_suggere(session, principal, enveloppes),
        disponible_avant_centimes=int(proposition.disponible_avant),
        disponible_apres_centimes=int(proposition.disponible_apres),
        total_recommande_centimes=int(proposition.total_recommande),
        total_libere_centimes=int(proposition.total_libere),
        attend_des_choix=proposition.attend_des_choix,
    )


@routeur.post("/enveloppes/preparation", response_model=RepartitionPublique)
def appliquer_la_preparation(
    demande: DemandePreparation, session: SessionBase, principal: PrincipalCourant
) -> RepartitionPublique:
    """Applique les lignes retenues. SEULE écriture du passage de période.

    Les montants viennent de la demande et non d'un recalcul côté serveur : la proposition
    est une proposition, et l'utilisateur peut en retenir d'autres chiffres. Recalculer ici
    reviendrait à lui reprendre la décision qu'on vient de lui donner.

    La libération est écrite AVANT l'allocation, pour la même raison qu'elle la précède
    dans le calcul : sur une enveloppe qui libère puis reçoit, l'ordre inverse produirait
    un solde intermédiaire faux dans le journal — lisible six mois plus tard comme une
    erreur qui n'a jamais eu lieu.
    """
    for choix in demande.lignes:
        enveloppe = depot.enveloppe_visible(session, principal, choix.enveloppe_id)
        if enveloppe is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Enveloppe introuvable."
            )

        if choix.liberer_centimes > 0:
            depot.ajouter_mouvement(
                session,
                enveloppe,
                type=TypeMouvement.LIBERATION,
                montant_centimes=Cents(choix.liberer_centimes),
                date_mouvement=aujourd_hui(),
                libelle="Fin de période",
            )
        if choix.allouer_centimes > 0:
            depot.ajouter_mouvement(
                session,
                enveloppe,
                type=TypeMouvement.ALLOCATION,
                montant_centimes=Cents(choix.allouer_centimes),
                date_mouvement=aujourd_hui(),
                libelle="Préparation du mois",
            )

    session.commit()
    return _repartition(session, principal)
