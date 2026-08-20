"""Routes d'import d'un relevé bancaire.

**La règle qui commande ce fichier** :

    Rien ne s'écrit sans revue.

`POST /import/analyse` lit le fichier et rend ce qu'il PROPOSE ; `POST /import/valider`
écrit les lignes qu'on lui redonne. Deux routes, parce qu'un import en une seule mettrait
dans les comptes des opérations que personne n'a lues.

Le fichier n'est jamais stocké. Il est lu en mémoire, analysé, et oublié : un relevé
bancaire conservé sur le serveur serait une donnée sensible de plus à protéger, pour un
bénéfice nul — la revue se fait dans la foulée, et la validation renvoie les lignes.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.api.import_schemas import (
    CategorieManquante,
    DemandeValidationImport,
    LigneImportPublique,
    RecurrenceProposee,
    RevueImport,
)
from mycounts.domain.import_releve import (
    GenreCorrespondance,
    LigneImportee,
    OperationExistante,
    ReleveIllisible,
    SensImporte,
    analyser,
    categorie_par_defaut,
    categorie_proposee,
    detecter_les_recurrences,
    ecarter_les_deja_importees,
    normaliser_pour_correspondance,
    ressemble_a_une_operation_existante,
)
from mycounts.domain.montants import Cents
from mycounts.repository import budget as depot
from mycounts.repository import recurrences as depot_recurrences
from mycounts.services.categorisation_ia import (
    proposer_des_categories,
    proposer_des_categories_manquantes,
)

routeur = APIRouter(tags=["import"])

"""Taille maximale acceptée, en octets.

Un relevé de deux cents opérations pèse 40 ko ; 5 Mo laissent une marge de deux ordres de
grandeur. La borne existe parce que le fichier est lu ENTIÈREMENT en mémoire : sans elle,
un envoi de plusieurs gigaoctets ferait tomber le serveur pour tout le foyer.
"""
TAILLE_MAXIMALE: int = 5 * 1024 * 1024


def _en_public(
    ligne: LigneImportee,
    deja_importee: bool,
    categorie_id: str | None = None,
    doublon: OperationExistante | None = None,
) -> LigneImportPublique:
    return LigneImportPublique(
        cle=ligne.cle,
        categorie_proposee_id=None if categorie_id is None else uuid.UUID(categorie_id),
        doublon_probable=(
            None
            if doublon is None
            else f"{doublon.libelle} du {doublon.date_operation.strftime('%d/%m')}"
        ),
        date_operation=ligne.date_operation,
        libelle=ligne.libelle,
        montant_centimes=int(ligne.montant),
        sens=ligne.sens,
        categorie_banque=ligne.categorie_banque,
        deja_importee=deja_importee,
    )


@routeur.post("/import/analyse", response_model=RevueImport)
async def analyser_un_releve(
    session: SessionBase,
    principal: PrincipalCourant,
    fichier: Annotated[
        UploadFile, File(description="Relevé au format CSV, exporté depuis la banque.")
    ],
    depuis: dt.date | None = None,
) -> RevueImport:
    """Lit le relevé et rend ce qu'il propose. **N'écrit rien.**

    Les lignes déjà importées sont rendues elles aussi, marquées comme telles : les taire
    ferait croire à un fichier incomplet à qui réimporte un mois entier pour deux oublis.
    """
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAXIMALE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Ce fichier dépasse 5 Mo. Un relevé mensuel en pèse quelques dizaines de ko.",
        )

    try:
        lignes = analyser(contenu)
        if depuis is not None:
            # Filtré APRÈS l'analyse et non pendant : les rangs d'occurrence se calculent
            # sur le fichier ENTIER, sinon écarter une première occurrence donnerait le
            # rang 1 à la seconde, qui passerait alors pour déjà importée.
            lignes = tuple(ligne for ligne in lignes if ligne.date_operation >= depuis)
    except ReleveIllisible as cause:
        # Le message du domaine est écrit POUR l'utilisateur : il nomme la colonne
        # manquante ou la valeur illisible. Le remplacer par un texte générique lui
        # retirerait la seule information qui lui permet d'agir.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(cause)
        ) from cause

    nouvelles, ignorees = ecarter_les_deja_importees(
        lignes, depot.cles_deja_importees(session, principal)
    )

    # Ce que le foyer a retenu des imports précédents, et ce qu'il a déjà en base.
    correspondances = depot.correspondances_du_foyer(session, principal)
    existantes = [
        OperationExistante(
            date_operation=operation.date_operation,
            montant=Cents(operation.montant_centimes),
            libelle=operation.libelle,
        )
        for operation in depot.operations_visibles(session, principal)
    ]
    montants_recurrents = [
        Cents(recurrence.montant_centimes)
        for recurrence in depot_recurrences.recurrences_visibles(session, principal)
    ]

    # Quatre niveaux, du moins coûteux au plus coûteux, et chacun ne voit que ce que le
    # précédent n'a pas su ranger. L'ordre n'est pas une optimisation : chaque niveau
    # franchi est un libellé de moins qui sort du foyer.
    categories_du_foyer = depot.categories(session, principal)
    par_nom = {categorie.nom: categorie.id for categorie in categories_du_foyer}
    proposees: dict[str, str] = {}
    for ligne in nouvelles:
        #  1. ce que le foyer a explicitement rangé ainsi ;
        apprise = categorie_proposee(ligne, correspondances)
        if apprise is not None:
            proposees[ligne.cle] = apprise
            continue
        #  2. le tableau par défaut des catégories bancaires.
        nom = categorie_par_defaut(ligne, list(par_nom))
        if nom is not None:
            proposees[ligne.cle] = str(par_nom[nom])

    #  3. l'assistance externe, pour ce qui reste — et pour cela SEULEMENT. Les libellés
    #     déjà rangés ne sortent pas. Voir `services/categorisation_ia.py` : c'est le seul
    #     fichier du projet qui parle à un tiers, et il n'envoie que des libellés.
    #
    #     Les dépenses et les revenus sont demandés SÉPARÉMENT, chacun avec les seules
    #     catégories de sa nature. Une première version envoyait tout ensemble et recevait
    #     « Revolut → Autres revenus », « BPCE Vie → Autres revenus » : privé du signe, le
    #     modèle rangeait des dépenses en recettes. Le corriger ne demande pas d'envoyer
    #     davantage — il suffit de ne pas proposer une catégorie que la nature interdit.
    restants = [
        ligne
        for ligne in nouvelles
        if ligne.cle not in proposees and ligne.sens is not SensImporte.VIREMENT
    ]
    for nature, sens_attendu in (("depense", SensImporte.DEPENSE), ("revenu", SensImporte.REVENU)):
        de_cette_nature = [ligne for ligne in restants if ligne.sens is sens_attendu]
        if not de_cette_nature:
            continue
        noms_permis = [
            categorie.nom for categorie in categories_du_foyer if categorie.nature == nature
        ]
        if not noms_permis:
            continue
        suggestions = proposer_des_categories(
            [ligne.libelle for ligne in de_cette_nature], noms_permis
        )
        for ligne in de_cette_nature:
            nom_suggere = suggestions.get(ligne.libelle)
            if nom_suggere is not None:
                proposees[ligne.cle] = str(par_nom[nom_suggere])

    #  4. et ce que personne ne peut ranger : une catégorie qui manque. Elle n'est
    #     proposée que si PLUSIEURS libellés l'appellent — sans quoi chaque commerçant
    #     inconnu produirait la sienne, et l'écran offrirait d'en créer trente.
    orphelins = [
        ligne
        for ligne in nouvelles
        if ligne.cle not in proposees and ligne.sens is SensImporte.DEPENSE
    ]
    manquantes = (
        proposer_des_categories_manquantes(
            [ligne.libelle for ligne in orphelins],
            [categorie.nom for categorie in categories_du_foyer],
        )
        if orphelins
        else {}
    )

    return RevueImport(
        total=len(lignes),
        nouvelles=len(nouvelles),
        deja_importees=len(ignorees),
        lignes=[
            _en_public(
                ligne,
                False,
                proposees.get(ligne.cle),
                ressemble_a_une_operation_existante(ligne, existantes),
            )
            for ligne in nouvelles
        ]
        + [_en_public(ligne, True) for ligne in ignorees],
        categories_manquantes=[
            CategorieManquante(nom=nom, libelles=couverts)
            for nom, couverts in manquantes.items()
        ],
        recurrences_proposees=[
            RecurrenceProposee(
                libelle=candidate.libelle,
                montant_centimes=int(candidate.montant),
                cadence=candidate.cadence,
                occurrences=candidate.occurrences,
                derniere=candidate.derniere,
            )
            for candidate in detecter_les_recurrences(nouvelles, montants_recurrents)
        ],
    )


@routeur.post("/import/valider", status_code=status.HTTP_201_CREATED)
def valider_un_import(
    demande: DemandeValidationImport, session: SessionBase, principal: PrincipalCourant
) -> dict[str, int]:
    """Écrit les lignes retenues. **Seule écriture de l'import.**

    Les lignes viennent de la demande et non d'une relecture du fichier : l'utilisateur a
    pu en écarter, et relire le fichier ici lui reprendrait la décision qu'on vient de lui
    donner. Le fichier n'est d'ailleurs plus là — il n'est jamais conservé.

    La clé est revérifiée contre la base au moment d'écrire : entre l'analyse et la
    validation, un autre appareil a pu importer le même relevé.
    """
    if depot.compte_visible(session, principal, demande.compte_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")

    connues = depot.cles_deja_importees(session, principal)
    ecrites = 0
    for ligne in demande.lignes:
        if ligne.cle in connues:
            continue
        if ligne.sens is SensImporte.VIREMENT and ligne.contrepartie_id is not None:
            # Le SIGNE du relevé décide du sens : un crédit sur le compte importé vient de
            # l'autre compte, un débit y va. Le déduire évite de poser à l'utilisateur une
            # question dont le fichier contient déjà la réponse.
            if ligne.montant_centimes >= 0:
                source, destination = ligne.contrepartie_id, demande.compte_id
            else:
                source, destination = demande.compte_id, ligne.contrepartie_id
            depot.creer_virement(
                session,
                principal,
                compte_source_id=source,
                compte_destination_id=destination,
                montant_centimes=Cents(abs(ligne.montant_centimes)),
                date_operation=ligne.date_operation,
                libelle=ligne.libelle,
                cle_import=ligne.cle,
                compte_du_releve_id=demande.compte_id,
            )
        else:
            depot.creer_operation(
                session,
                principal,
                compte_id=demande.compte_id,
                libelle=ligne.libelle,
                montant_centimes=Cents(ligne.montant_centimes),
                date_operation=ligne.date_operation,
                categorie_id=ligne.categorie_id,
                cle_import=ligne.cle,
            )

        # Le rangement s'APPREND. Sans cela, le choix de l'utilisateur ne servirait qu'à
        # cette ligne-ci, et deux cents lignes seraient à ranger de nouveau au prochain
        # import — ce que personne ne fait deux fois.
        if ligne.categorie_id is not None and ligne.sens is not SensImporte.VIREMENT:
            depot.retenir_la_correspondance(
                session,
                principal,
                genre=GenreCorrespondance.LIBELLE,
                valeur=normaliser_pour_correspondance(ligne.libelle),
                categorie_id=ligne.categorie_id,
            )
            if ligne.categorie_banque:
                depot.retenir_la_correspondance(
                    session,
                    principal,
                    genre=GenreCorrespondance.CATEGORIE_BANQUE,
                    valeur=ligne.categorie_banque,
                    categorie_id=ligne.categorie_id,
                )

        connues.add(ligne.cle)
        ecrites += 1

    session.commit()
    return {"ecrites": ecrites, "ignorees": len(demande.lignes) - ecrites}
