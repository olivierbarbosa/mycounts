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

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.api.import_schemas import (
    DemandeValidationImport,
    LigneImportPublique,
    RevueImport,
)
from mycounts.domain.import_releve import (
    LigneImportee,
    ReleveIllisible,
    analyser,
    ecarter_les_deja_importees,
)
from mycounts.domain.montants import Cents
from mycounts.repository import budget as depot

routeur = APIRouter(tags=["import"])

"""Taille maximale acceptée, en octets.

Un relevé de deux cents opérations pèse 40 ko ; 5 Mo laissent une marge de deux ordres de
grandeur. La borne existe parce que le fichier est lu ENTIÈREMENT en mémoire : sans elle,
un envoi de plusieurs gigaoctets ferait tomber le serveur pour tout le foyer.
"""
TAILLE_MAXIMALE: int = 5 * 1024 * 1024


def _en_public(ligne: LigneImportee, deja_importee: bool) -> LigneImportPublique:
    return LigneImportPublique(
        cle=ligne.cle,
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

    return RevueImport(
        total=len(lignes),
        nouvelles=len(nouvelles),
        deja_importees=len(ignorees),
        lignes=[_en_public(ligne, False) for ligne in nouvelles]
        + [_en_public(ligne, True) for ligne in ignorees],
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
        connues.add(ligne.cle)
        ecrites += 1

    session.commit()
    return {"ecrites": ecrites, "ignorees": len(demande.lignes) - ecrites}
