"""Routes du budget : comptes, catégories, opérations, résumé de période."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from mycounts.api.budget_schemas import (
    CategoriePublique,
    ComptePublic,
    DemandeCategorie,
    DemandeCompte,
    DemandeOperation,
    ModificationCategorie,
    OperationPublique,
    PeriodePublique,
    ResumePublic,
)
from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.montants import Cents
from mycounts.domain.resume import ResumePeriode, resumer
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot

routeur = APIRouter(tags=["budget"])


def _en_compte(compte: object) -> ComptePublic:
    return ComptePublic.model_validate(compte, from_attributes=True)


@routeur.get("/comptes", response_model=list[ComptePublic])
def lister_comptes(session: SessionBase, principal: PrincipalCourant) -> list[ComptePublic]:
    return [_en_compte(c) for c in depot.comptes_visibles(session, principal)]


@routeur.post("/comptes", response_model=ComptePublic, status_code=status.HTTP_201_CREATED)
def creer_compte(
    demande: DemandeCompte, session: SessionBase, principal: PrincipalCourant
) -> ComptePublic:
    compte = depot.creer_compte(session, principal, nom=demande.nom, prive=demande.prive)
    if demande.solde_ouverture_centimes != 0:
        # Le solde de départ est une opération, jamais une colonne : sinon le solde
        # cesserait d'être une somme et deviendrait une valeur à réconcilier.
        depot.creer_operation(
            session,
            principal,
            compte_id=compte.id,
            libelle="Solde d'ouverture",
            montant_centimes=Cents(demande.solde_ouverture_centimes),
            date_operation=aujourd_hui(),
            est_ouverture=True,
        )
    session.commit()
    return _en_compte(compte)


@routeur.get("/categories", response_model=list[CategoriePublique])
def lister_categories(
    session: SessionBase, principal: PrincipalCourant
) -> list[CategoriePublique]:
    return [
        CategoriePublique.model_validate(c, from_attributes=True)
        for c in depot.categories(session, principal)
    ]


@routeur.post(
    "/categories", response_model=CategoriePublique, status_code=status.HTTP_201_CREATED
)
def creer_categorie(
    demande: DemandeCategorie, session: SessionBase, principal: PrincipalCourant
) -> CategoriePublique:
    categorie = depot.creer_categorie(
        session, principal, nom=demande.nom, nature=demande.nature, teinte=demande.teinte
    )
    session.commit()
    return CategoriePublique.model_validate(categorie, from_attributes=True)


@routeur.patch("/categories/{categorie_id}", response_model=CategoriePublique)
def modifier_categorie(
    categorie_id: uuid.UUID,
    demande: ModificationCategorie,
    session: SessionBase,
    principal: PrincipalCourant,
) -> CategoriePublique:
    categorie = depot.categorie_visible(session, principal, categorie_id)
    if categorie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")
    depot.modifier_categorie(
        session, categorie, nom=demande.nom, teinte=demande.teinte, archivee=demande.archivee
    )
    session.commit()
    return CategoriePublique.model_validate(categorie, from_attributes=True)


@routeur.delete("/categories/{categorie_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_categorie(
    categorie_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> None:
    """Suppression définitive, refusée si la catégorie sert à une opération.

    Le message propose l'archivage : supprimer une catégorie utilisée changerait
    rétroactivement les totaux d'un mois déjà clos.
    """
    categorie = depot.categorie_visible(session, principal, categorie_id)
    if categorie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")
    if depot.categorie_est_utilisee(session, categorie_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cette catégorie est utilisée par des opérations. L'archiver la retire des "
                "listes sans réécrire l'historique."
            ),
        )
    depot.supprimer_categorie(session, categorie)
    session.commit()


@routeur.get("/operations", response_model=list[OperationPublique])
def lister_operations(
    session: SessionBase,
    principal: PrincipalCourant,
    periode_courante: bool = Query(
        default=True, description="Restreindre à la période budgétaire en cours."
    ),
) -> list[OperationPublique]:
    depuis = jusqu_a = None
    if periode_courante:
        resume = _resumer(session, principal)
        depuis, jusqu_a = resume.periode.debut, resume.periode.fin

    return [
        OperationPublique.model_validate(o, from_attributes=True)
        for o in depot.operations_visibles(session, principal, depuis=depuis, jusqu_a=jusqu_a)
    ]


@routeur.post(
    "/operations", response_model=OperationPublique, status_code=status.HTTP_201_CREATED
)
def creer_operation(
    demande: DemandeOperation, session: SessionBase, principal: PrincipalCourant
) -> OperationPublique:
    """Saisit une opération.

    Le compte et la catégorie sont revérifiés à travers le périmètre de l'appelant :
    un identifiant valide chez quelqu'un d'autre doit être refusé exactement comme un
    identifiant inexistant, sans distinction observable.
    """
    if demande.montant_centimes == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Un montant nul ne décrit aucune opération.",
        )
    if demande.est_paie and demande.montant_centimes <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Une paie ouvre une période budgétaire : son montant doit être positif.",
        )

    if depot.compte_visible(session, principal, demande.compte_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    if demande.categorie_id is not None and (
        depot.categorie_visible(session, principal, demande.categorie_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    operation = depot.creer_operation(
        session,
        principal,
        compte_id=demande.compte_id,
        libelle=demande.libelle,
        montant_centimes=Cents(demande.montant_centimes),
        date_operation=demande.date_operation,
        categorie_id=demande.categorie_id,
        est_paie=demande.est_paie,
    )
    session.commit()
    return OperationPublique.model_validate(operation, from_attributes=True)


def _resumer(session: SessionBase, principal: PrincipalCourant) -> ResumePeriode:
    utilisateur = depot_auth.utilisateur_par_id(session, principal.utilisateur_id)
    paies_par_cycle = utilisateur.paies_par_cycle if utilisateur else 1
    return resumer(
        depot.operations_pour_calcul(session, principal),
        depot.dates_de_paie(session, principal),
        aujourd_hui=aujourd_hui(),
        paies_par_cycle=paies_par_cycle,
    )


@routeur.get("/resume", response_model=ResumePublic)
def resume(session: SessionBase, principal: PrincipalCourant) -> ResumePublic:
    r = _resumer(session, principal)
    return ResumePublic(
        periode=PeriodePublique(
            debut=r.periode.debut, fin=r.periode.fin, fin_estimee=r.periode.fin_estimee
        ),
        solde_projete=r.solde_projete,
        solde_reel=r.solde_reel,
        solde_a_confirmer=r.solde_a_confirmer,
        depenses_de_periode=r.depenses_de_periode,
    )
