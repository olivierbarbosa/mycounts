"""Routes du budget : comptes, catégories, opérations, résumé de période."""

from __future__ import annotations

import uuid
from typing import Final

from fastapi import APIRouter, HTTPException, Query, status

from mycounts.api.budget_schemas import (
    AjustementFait,
    CategoriePublique,
    CompteEpargne,
    ComptePublic,
    DemandeAjustement,
    DemandeCategorie,
    DemandeCompte,
    DemandeOperation,
    DemandeVirement,
    DetailEpargne,
    EpargnePublique,
    ModificationCategorie,
    ModificationCompte,
    ModificationOperation,
    MoisDEpargnePublic,
    OperationPublique,
    PeriodePublique,
    ProduitPublic,
    ResumePublic,
    SoldeDeCompte,
    VirementCree,
)
from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.domain import comptes as domaine_comptes
from mycounts.domain.agregats import Agregat, EtatOperation, OperationCalcul, calculer
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.comptes import TypeCompte
from mycounts.domain.epargne import MouvementEpargne, mois_precedents, repartir_par_mois
from mycounts.domain.montants import Cents
from mycounts.domain.resume import ResumePeriode, resumer
from mycounts.jobs.materialisation import materialiser
from mycounts.models.budget import Compte
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot
from mycounts.repository import recurrences as depot_recurrences

routeur = APIRouter(tags=["budget"])


def _en_compte(compte: Compte) -> ComptePublic:
    return ComptePublic(
        id=compte.id,
        nom=compte.nom,
        prive=compte.prive,
        type_compte=compte.type_compte,
        produit=compte.produit,
        # Le libellé vient du catalogue et n'est jamais stocké : le figer en base
        # obligerait à réécrire toutes les lignes le jour où un produit change de nom.
        produit_libelle=domaine_comptes.produit(compte.produit).libelle,
        archive=compte.archive,
    )


@routeur.get("/comptes", response_model=list[ComptePublic])
def lister_comptes(
    session: SessionBase,
    principal: PrincipalCourant,
    inclure_archives: bool = Query(
        default=False,
        description=(
            "Rendre aussi les comptes archivés. Réservé à l'écran de GESTION : les "
            "écrans qui proposent ou totalisent des comptes ne doivent pas les voir."
        ),
    ),
) -> list[ComptePublic]:
    """Les comptes du périmètre courant.

    Le périmètre suit la VUE, ici comme partout ailleurs. Un paramètre `toutes_vues` a
    brièvement existé, qui réunissait les deux mondes dans l'écran de gestion ; il est
    retiré le 22 août 2026 au profit d'une règle unique — chaque vue montre son monde, et
    l'on bascule pour voir l'autre. Deux écrans qui répondent différemment à la même
    bascule s'apprennent deux fois.

    `inclure_archives` reste, lui, indispensable : l'écran qui propose l'archivage doit
    continuer de montrer ce qu'il a rangé, sinon l'action est sans retour
    (ERREURS.md #043).
    """
    return [
        _en_compte(c)
        for c in depot.comptes_visibles(session, principal, inclure_archives=inclure_archives)
    ]


@routeur.post("/comptes", response_model=ComptePublic, status_code=status.HTTP_201_CREATED)
def creer_compte(
    demande: DemandeCompte, session: SessionBase, principal: PrincipalCourant
) -> ComptePublic:
    produit = _produit_ou_400(demande.produit)
    compte = depot.creer_compte(
        session,
        principal,
        nom=demande.nom,
        prive=demande.prive,
        produit=produit.cle,
        # Déduit, jamais reçu : le catalogue est seul auteur de ce qu'un produit fait
        # dans les calculs.
        type_compte=produit.type_compte,
    )
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


def _produit_ou_400(cle: str) -> domaine_comptes.ProduitBancaire:
    try:
        return domaine_comptes.produit(cle)
    except ValueError as cause:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(cause)
        ) from cause


@routeur.get("/comptes/catalogue", response_model=list[ProduitPublic])
def catalogue_des_comptes(principal: PrincipalCourant) -> list[ProduitPublic]:
    """Produits bancaires proposés à la création d'un compte.

    Servi par le serveur et non écrit dans l'interface : c'est le catalogue qui décide
    qu'un PEA ne compte pas dans le solde du quotidien, et cette règle appartient au
    domaine. Une liste recopiée côté client en ferait un second auteur.
    """
    del principal
    return [
        ProduitPublic(cle=p.cle, libelle=p.libelle, type_compte=p.type_compte)
        for p in domaine_comptes.CATALOGUE
    ]


@routeur.get("/comptes/soldes", response_model=list[SoldeDeCompte])
def soldes_des_comptes(
    session: SessionBase,
    principal: PrincipalCourant,
    inclure_archives: bool = Query(
        default=False,
        description="Rendre aussi les soldes des comptes archivés, comme `GET /comptes`.",
    ),
) -> list[SoldeDeCompte]:
    """Solde RÉEL de chaque compte du périmètre courant.

    Le réel et non le projeté : une carte de compte répond à « combien y a-t-il dessus »,
    pas à « combien restera-t-il ». Y projeter des échéances ferait diverger le chiffre de
    ce que la banque affiche, qui est la seule référence pour un rapprochement.

    La docstring annonçait « archivés compris » alors que la boucle les excluait, et cette
    phrase a survécu des semaines parce que rien ne pouvait la contredire (ERREURS.md
    #043). Ils le sont maintenant, mais seulement sur demande : une carte archivée sans
    montant se lit comme un compte vide.
    """
    jour = aujourd_hui()
    return [
        SoldeDeCompte(
            compte_id=compte.id,
            solde_centimes=int(
                calculer(
                    Agregat.SOLDE_REEL,
                    depot.operations_pour_calcul(session, principal, comptes=[compte.id]),
                    aujourd_hui=jour,
                    fin_de_fenetre=jour,
                )
            ),
        )
        for compte in depot.comptes_visibles(
            session, principal, inclure_archives=inclure_archives
        )
    ]


@routeur.patch("/comptes/{compte_id}", response_model=ComptePublic)
def modifier_compte(
    compte_id: uuid.UUID,
    demande: ModificationCompte,
    session: SessionBase,
    principal: PrincipalCourant,
) -> ComptePublic:
    """Renomme un compte, change son produit, ou l'archive.

    Changer de produit peut faire passer un compte du quotidien à l'épargne — c'est
    voulu : c'est le seul moyen de corriger une création faite trop vite. L'argent ne
    bouge pas, seul l'écran qui le totalise change.
    """
    compte = depot.compte_administrable(session, principal, compte_id)
    if compte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    produit = None if demande.produit is None else _produit_ou_400(demande.produit)
    depot.modifier_compte(
        session,
        compte,
        nom=demande.nom,
        produit=None if produit is None else produit.cle,
        type_compte=None if produit is None else produit.type_compte,
        archive=demande.archive,
    )
    session.commit()
    return _en_compte(compte)


@routeur.delete("/comptes/{compte_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_compte(
    compte_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> None:
    """Supprime un compte VIDE.

    Un compte qui porte des opérations n'est pas supprimé : ses lignes disparaîtraient
    des soldes et des totaux passés, et un mois clos changerait de montant après coup.
    L'archivage existe pour cela — il retire le compte des propositions sans toucher à
    son histoire.
    """
    compte = depot.compte_administrable(session, principal, compte_id)
    if compte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    # Un compte JOINT est visible de tous les membres, mais n'appartient qu'à celui qui
    # l'a ouvert. Sans cette garde, n'importe quel membre du foyer pouvait supprimer
    # l'espace commun — la visibilité valait permission, ce qui n'est vrai d'aucun objet
    # partagé. Un 403 et non un 404 : le compte existe, l'appelant le voit, et lui dire
    # « introuvable » l'enverrait chercher une panne qui n'existe pas.
    if compte.proprietaire_id != principal.utilisateur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seule la personne qui a ouvert ce compte peut le supprimer.",
        )

    if depot.compte_a_des_operations(session, compte_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ce compte porte des opérations : le supprimer changerait des mois déjà "
                "clos. Archivez-le pour le retirer des propositions."
            ),
        )

    depot.supprimer_compte(session, compte)
    session.commit()


@routeur.get("/comptes/{compte_id}/ajustements", response_model=list[OperationPublique])
def historique_des_corrections(
    compte_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> list[OperationPublique]:
    """Les corrections de solde d'un compte, la plus récente d'abord.

    Elles ont quitté le journal de l'accueil le 22 août 2026 — un ajustement n'est pas un
    achat, et le voir sous « Dépenses récentes » fait chercher une dépense qui n'existe
    pas. Mais l'accueil étant le seul écran qui listait les opérations, elles étaient
    devenues invisibles : une correction posée d'autorité, impossible à relire trois mois
    plus tard. Cette route leur rend un endroit, celui où on les fait.
    """
    if depot.compte_visible(session, principal, compte_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    # L'ordre vient du repository — `date_operation DESC, cree_le DESC` — et n'est pas
    # refait ici. Un second tri ferait un second auteur pour la même donnée, et celui-ci
    # était en plus MOINS juste : il ignorait `cree_le`, alors que corriger deux fois le
    # même jour est le cas ordinaire. Un tri qui recopie mal ce qu'il recopie ne se voit
    # pas, parce que le bon résultat arrive quand même de l'autre auteur.
    corrections = depot.operations_visibles(
        session, principal, comptes=[compte_id], seulement_ajustements=True
    )
    return [OperationPublique.model_validate(o, from_attributes=True) for o in corrections]


@routeur.post("/comptes/{compte_id}/ajustement", response_model=AjustementFait)
def ajuster_le_solde(
    compte_id: uuid.UUID,
    demande: DemandeAjustement,
    session: SessionBase,
    principal: PrincipalCourant,
) -> AjustementFait:
    """Met le solde d'un compte d'accord avec celui de la banque.

    Un solde est une SOMME d'opérations, jamais une valeur qu'on écrit : la mise d'accord
    passe donc par une opération de plus, qui porte l'écart. Elle compte dans les soldes —
    c'est son objet — et jamais dans les dépenses, sans quoi réparer une erreur de saisie
    de 20 € ferait sauter un plafond de 20 €.

    L'écart est calculé ICI et non par le client : seul le serveur connaît le solde à
    l'instant où il écrit. Un écart calculé par le client le serait sur une valeur déjà
    périmée, et deux corrections concurrentes se doubleraient.

    Concordance parfaite : aucune opération. Écrire un ajustement de zéro remplirait
    l'historique de lignes qui ne disent rien.
    """
    compte = depot.compte_visible(session, principal, compte_id)
    if compte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    jour = demande.date_operation or aujourd_hui()
    actuel = int(
        calculer(
            Agregat.SOLDE_REEL,
            depot.operations_pour_calcul(session, principal, comptes=[compte_id]),
            aujourd_hui=jour,
            fin_de_fenetre=jour,
        )
    )
    ecart = demande.solde_reel_centimes - actuel

    if ecart != 0:
        depot.creer_operation(
            session,
            principal,
            compte_id=compte_id,
            libelle="Ajustement de solde",
            montant_centimes=Cents(ecart),
            date_operation=jour,
            est_ajustement=True,
        )
        session.commit()

    return AjustementFait(ecart_centimes=ecart, solde_centimes=actuel + ecart)


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


@routeur.post(
    "/virements", response_model=VirementCree, status_code=status.HTTP_201_CREATED
)
def creer_virement(
    demande: DemandeVirement, session: SessionBase, principal: PrincipalCourant
) -> VirementCree:
    """Déplace de l'argent d'un compte du foyer vers un autre.

    Ce n'est ni une dépense ni un revenu : l'argent ne quitte pas le foyer. Les deux
    lignes créées restent dans les soldes de leurs comptes et sortent des dépenses de
    période — voir `INCLUT_VIREMENTS` dans `domain/agregats.py`.

    Les deux comptes sont vérifiés séparément : sans quoi un identifiant appartenant à un
    autre foyer permettrait d'y déposer de l'argent, ou d'en constater le solde par
    l'échec ou le succès de l'appel.
    """
    connus = {compte.id for compte in depot.comptes_visibles(session, principal)}
    for compte_id in (demande.compte_source_id, demande.compte_destination_id):
        if compte_id not in connus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable."
            )

    sortie, entree = depot.creer_virement(
        session,
        principal,
        compte_source_id=demande.compte_source_id,
        compte_destination_id=demande.compte_destination_id,
        montant_centimes=Cents(demande.montant_centimes),
        date_operation=demande.date_operation,
        libelle=demande.libelle,
    )
    session.commit()
    return VirementCree(
        virement_id=sortie.virement_id,  # type: ignore[arg-type]
        sortie=OperationPublique.model_validate(sortie, from_attributes=True),
        entree=OperationPublique.model_validate(entree, from_attributes=True),
    )


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
        resume = resume_de_la_periode(session, principal)
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


@routeur.patch("/operations/{operation_id}", response_model=OperationPublique)
def modifier_operation(
    operation_id: uuid.UUID,
    demande: ModificationOperation,
    session: SessionBase,
    principal: PrincipalCourant,
) -> OperationPublique:
    """Corrige une opération déjà saisie."""
    categorie_fournie = "categorie_id" in demande.model_fields_set
    operation = depot.operation_visible(session, principal, operation_id)
    if operation is None or operation.annulee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opération introuvable.")
    if demande.montant_centimes is not None and demande.montant_centimes == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Un montant nul ne décrit aucune opération.",
        )
    if (
        operation.est_paie
        and demande.montant_centimes is not None
        and demande.montant_centimes <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Une paie ouvre une période budgétaire : son montant doit rester positif.",
        )
    if demande.categorie_id is not None and (
        depot.categorie_visible(session, principal, demande.categorie_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    depot.modifier_operation(
        session,
        operation,
        libelle=demande.libelle,
        montant_centimes=Cents(demande.montant_centimes)
        if demande.montant_centimes is not None
        else None,
        date_operation=demande.date_operation,
        categorie_id=demande.categorie_id,
        categorie_fournie=categorie_fournie,
    )
    session.commit()
    return OperationPublique.model_validate(operation, from_attributes=True)


@routeur.delete("/operations/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_operation(
    operation_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> None:
    """Retire une opération.

    Une saisie manuelle est supprimée ; une opération issue d'un prélèvement est annulée
    et conservée, faute de quoi le job la recréerait au passage suivant. La distinction
    est faite par le repository — l'appelant demande simplement le retrait.
    """
    operation = depot.operation_visible(session, principal, operation_id)
    if operation is None or operation.annulee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opération introuvable.")
    depot.retirer_operation(session, operation)
    session.commit()


def resume_de_la_periode(
    session: SessionBase, principal: PrincipalCourant
) -> ResumePeriode:
    """Les quatre grandeurs de la période, sur les comptes COURANTS.

    Public depuis le 22 août 2026 : la préparation des enveloppes a besoin du solde
    projeté pour dire ce qu'on peut mettre de côté. Elle importe donc ce calcul-ci plutôt
    que d'en écrire un second — deux définitions de « ce qu'il me reste » finiraient par
    ne plus donner le même chiffre, et l'écart passerait pour une panne de l'une des deux
    pages.
    """
    # Même rattrapage que pour l'agenda : une échéance échue non matérialisée serait
    # absente du solde réel comme de la part à confirmer. Idempotent.
    materialiser(session, espace_id=principal.espace_id)
    utilisateur = depot_auth.utilisateur_par_id(session, principal.utilisateur_id)
    paies_par_cycle = utilisateur.paies_par_cycle if utilisateur else 1
    # Le résumé de l'accueil ne porte que sur les comptes COURANTS. Mélanger un livret
    # au compte courant fait croire à une aisance qui n'existe pas : l'écran annoncerait
    # 4 000 € alors que 3 500 sont mis de côté, et la décision de dépenser se prendrait
    # sur un chiffre faux. L'épargne a son propre total, sur sa propre page.
    courants = depot.ids_des_comptes(session, principal, type_compte=TypeCompte.COURANT)
    operations = depot.operations_pour_calcul(session, principal, comptes=courants)
    paies = depot.dates_de_paie(session, principal, comptes=courants)
    jour = aujourd_hui()
    sans_echeances_futures = resumer(
        operations,
        paies,
        aujourd_hui=jour,
        paies_par_cycle=paies_par_cycle,
    )

    # Les récurrences futures n'existent volontairement pas dans `operation` : l'agenda
    # les projette à la volée et le job ne les matérialise qu'à leur date. Le résumé doit
    # faire la même projection, sinon une charge pourtant visible au calendrier ne réduit
    # ni le solde projeté ni la capacité d'épargne proposée au début du cycle.
    comptes_courants = set(courants)
    operations.extend(
        OperationCalcul(
            montant=Cents(recurrence.montant_centimes),
            date_operation=date_echeance,
            etat=EtatOperation.PREVUE,
        )
        for recurrence, date_echeance in depot_recurrences.echeances_projetees(
            session,
            principal,
            depuis=jour,
            jusqu_a=sans_echeances_futures.periode.fin,
        )
        if recurrence.compte_id in comptes_courants
    )
    return resumer(
        operations,
        paies,
        aujourd_hui=jour,
        paies_par_cycle=paies_par_cycle,
    )


@routeur.get("/epargne", response_model=EpargnePublique)
def epargne(session: SessionBase, principal: PrincipalCourant) -> EpargnePublique:
    """Total épargné, solde de chaque livret, et ce qui y a été versé sur la période.

    Le solde retenu est le solde RÉEL. Un livret n'a ni échéance à confirmer ni
    prélèvement à venir : y projeter quoi que ce soit inventerait un argent qui n'arrive
    de nulle part.
    """
    comptes_epargne = depot.ids_des_comptes(session, principal, type_compte=TypeCompte.EPARGNE)
    periode = resume_de_la_periode(session, principal).periode
    aujourd_hui_ = aujourd_hui()

    par_compte: list[CompteEpargne] = []
    for compte in depot.comptes_visibles(session, principal, type_compte=TypeCompte.EPARGNE):
        solde = calculer(
            Agregat.SOLDE_REEL,
            depot.operations_pour_calcul(session, principal, comptes=[compte.id]),
            aujourd_hui=aujourd_hui_,
            fin_de_fenetre=max(aujourd_hui_, periode.fin),
        )
        par_compte.append(
            CompteEpargne(id=compte.id, nom=compte.nom, solde_centimes=int(solde))
        )

    return EpargnePublique(
        total_centimes=sum(c.solde_centimes for c in par_compte),
        verse_sur_la_periode_centimes=int(
            depot.total_verse_par_virement(
                session,
                principal,
                comptes=comptes_epargne,
                debut=periode.debut,
                fin=periode.fin,
            )
        ),
        periode=PeriodePublique(
            debut=periode.debut, fin=periode.fin, fin_estimee=periode.fin_estimee
        ),
        comptes=par_compte,
    )


MOIS_AFFICHES: Final = 6
"""Six mois et non douze.

Sur un écran de 390 px, douze groupes de deux barres tombent sous trois pixels chacune :
le graphique cesse d'être lisible avant d'être complet. Six mois suffisent à voir un
rythme s'installer, et c'est la fenêtre que l'écran annonce.
"""


@routeur.get("/epargne/{compte_id}", response_model=DetailEpargne)
def detail_epargne(
    compte_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> DetailEpargne:
    """Rythme d'un compte d'épargne : versé, repris et solde, mois par mois.

    Seuls les VIREMENTS alimentent `verse` et `repris` : eux seuls disent ce qu'on a
    délibérément placé ou repris. Un intérêt versé par la banque change le solde sans rien
    dire de l'effort. Le solde de fin de mois, lui, compte tout.
    """
    compte = depot.compte_visible(session, principal, compte_id)
    if compte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    jour = aujourd_hui()
    operations = depot.operations_visibles(session, principal, comptes=[compte_id])
    solde = int(
        calculer(
            Agregat.SOLDE_REEL,
            depot.operations_pour_calcul(session, principal, comptes=[compte_id]),
            aujourd_hui=jour,
            fin_de_fenetre=jour,
        )
    )

    virements = [
        MouvementEpargne(montant=Cents(o.montant_centimes), date_operation=o.date_operation)
        for o in operations
        if o.virement_id is not None
    ]
    tous = [
        MouvementEpargne(montant=Cents(o.montant_centimes), date_operation=o.date_operation)
        for o in operations
    ]

    mois = repartir_par_mois(
        virements,
        solde_final=Cents(solde),
        mois=mois_precedents(jour, MOIS_AFFICHES),
        tous_les_mouvements=tous,
    )

    return DetailEpargne(
        compte=_en_compte(compte),
        solde_centimes=solde,
        mois=[
            MoisDEpargnePublic(
                premier_jour=m.premier_jour,
                verse_centimes=int(m.verse),
                repris_centimes=int(m.repris),
                net_centimes=int(m.net),
                solde_fin_centimes=int(m.solde_fin),
                aller_retour=m.aller_retour,
            )
            for m in mois
        ],
        mois_avec_aller_retour=sum(1 for m in mois if m.aller_retour),
    )


@routeur.get("/resume", response_model=ResumePublic)
def resume(session: SessionBase, principal: PrincipalCourant) -> ResumePublic:
    r = resume_de_la_periode(session, principal)
    return ResumePublic(
        periode=PeriodePublique(
            debut=r.periode.debut, fin=r.periode.fin, fin_estimee=r.periode.fin_estimee
        ),
        solde_projete=r.solde_projete,
        solde_reel=r.solde_reel,
        solde_a_confirmer=r.solde_a_confirmer,
        depenses_de_periode=r.depenses_de_periode,
    )
