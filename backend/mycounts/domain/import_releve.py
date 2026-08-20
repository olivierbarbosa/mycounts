"""Import d'un relevé bancaire au format CSV.

**La règle qui commande tout le module** :

    Rien ne s'écrit sans revue.

L'import PROPOSE des lignes, l'utilisateur les valide. Un import qui écrirait directement
mettrait dans les comptes des opérations que personne n'a lues, et le premier faux
positif ferait perdre confiance à tout le reste.

## La clé d'unicité, et pourquoi elle est ce qu'elle est

Réimporter un mois qui chevauche le précédent ne doit pas dupliquer l'argent. Il faut donc
reconnaître qu'une ligne a déjà été importée — et les vrais relevés rendent cela moins
évident qu'il n'y paraît. Mesuré sur un export réel de 198 opérations :

- la référence bancaire est **vide 31 fois** (16 %) ;
- elle est **en double** pour deux opérations DIFFÉRENTES — deux achats du même jour chez
  le même commerçant, de 31,98 € et 15,50 €, partagent le même identifiant ;
- même (date + libellé + montant + référence) laisse **3 groupes de doublons**, et ce sont
  de VRAIES opérations distinctes : trois remboursements de 2,00 € le même jour, deux
  virements internes de 100 € le même jour.

Il n'existe donc aucune clé naturellement unique, et dédupliquer par le seul contenu
SUPPRIMERAIT de vraies opérations. La clé retenue ajoute donc un **rang d'occurrence** : la
n-ième ligne identique du fichier. Deux remboursements identiques du même jour sont deux
lignes de rangs 1 et 2, et se réimportent à l'identique.

**Ce que cette clé ne couvre PAS**, et il faut le savoir avant de s'y fier : un fichier
partiel qui ne contiendrait que la SECONDE des trois occurrences identiques lui donnerait
le rang 1, et elle passerait pour déjà importée. Le cas suppose un export tronqué au milieu
d'une journée, ce que les banques ne font pas — mais il est réel, et c'est ici qu'il est
écrit plutôt que nulle part.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from mycounts.domain.montants import Cents

"""Encodage des exports de la Caisse d'Épargne, et de la plupart des banques françaises.

`ISO-8859-1` et non UTF-8 : mesuré sur un export réel. Lire un tel fichier en UTF-8 lève
une erreur de décodage ou, pire selon l'implémentation, remplace silencieusement les
accents. « Intermarché » deviendrait « Intermarch? » dans les libellés, et le
regroupement par commerçant des statistiques ne s'en remettrait pas.

L'UTF-8 est tenté d'abord malgré tout : certaines banques ont migré, et un fichier UTF-8
lu en Latin-1 ne lève AUCUNE erreur — il produit des « Ã© » à la place des « é ». Le sens
de la tentative compte donc : l'UTF-8 échoue bruyamment sur du Latin-1, l'inverse échoue
en silence.
"""
ENCODAGES: Final[tuple[str, ...]] = ("utf-8-sig", "iso-8859-1")

SEPARATEUR: Final[str] = ";"

"""Colonnes attendues. Le fichier en porte treize ; six suffisent, et exiger les autres
ferait échouer l'import d'une banque qui n'en fournit que l'essentiel."""
COLONNE_DATE_OPERATION: Final[str] = "Date operation"
COLONNE_DATE_COMPTABILISATION: Final[str] = "Date de comptabilisation"
COLONNE_LIBELLE: Final[str] = "Libelle simplifie"
COLONNE_LIBELLE_BRUT: Final[str] = "Libelle operation"
COLONNE_REFERENCE: Final[str] = "Reference"
COLONNE_DEBIT: Final[str] = "Debit"
COLONNE_CREDIT: Final[str] = "Credit"
COLONNE_CATEGORIE: Final[str] = "Categorie"
COLONNE_TYPE: Final[str] = "Type operation"

"""Catégorie dont la banque marque elle-même les mouvements internes.

Un virement d'un compte à l'autre n'est ni une dépense ni un revenu : l'argent n'a pas
quitté le foyer. La banque le sait et le dit — 31 lignes sur 198 dans l'export mesuré.
S'en servir évite de gonfler les revenus de chaque mise de côté.
"""
CATEGORIE_EXCLUE: Final[str] = "Transaction exclue"


class SensImporte(StrEnum):
    """Ce que la ligne fera si elle est retenue."""

    DEPENSE = "depense"
    REVENU = "revenu"
    VIREMENT = "virement"
    """Marqué comme interne par la banque. Ne comptera ni dans les dépenses ni dans les
    revenus — reste à savoir vers quel compte, ce que le fichier ne dit pas."""


class ReleveIllisible(Exception):
    """Le fichier n'est pas un relevé exploitable.

    Levée avec un message destiné à l'utilisateur, pas au journal : « colonne Debit
    absente » lui dit quoi faire, « KeyError » ne lui dit rien.
    """


@dataclass(frozen=True)
class LigneImportee:
    """Une ligne du fichier, telle qu'on la propose. Rien n'est écrit à ce stade."""

    date_operation: dt.date
    libelle: str
    montant: Cents
    """SIGNÉ : négatif pour une dépense. Le fichier sépare débit et crédit en deux
    colonnes ; les fusionner ici évite que chaque lecteur ait à se souvenir de le faire."""

    sens: SensImporte
    reference: str
    categorie_banque: str
    rang: int
    """Occurrence de cette ligne parmi ses identiques dans le fichier. Voir la clé
    d'unicité en tête de module."""

    @property
    def cle(self) -> str:
        """Ce qui identifie la ligne d'un import à l'autre.

        Une CHAÎNE et non un tuple : c'est sous cette forme qu'elle est conservée en base,
        et rendre ici un tuple obligerait chaque appelant à refaire la même conversion —
        donc à s'accorder sur un séparateur, ailleurs, autant de fois qu'il y a
        d'appelants.

        Le séparateur est `\x1f`, le caractère de séparation d'unités : contrairement à un
        `|` ou un `;`, il ne peut pas figurer dans un libellé bancaire, si bien qu'aucune
        échappée n'est nécessaire et qu'aucun libellé ne peut fabriquer la clé d'un autre.

        Le LIBELLÉ BRUT n'y figure pas : il contient parfois la date de facturation
        (« CB INTERMARCHE FACT 170826 »), ce qui suffirait à distinguer deux lignes que
        la banque a corrigées entre deux exports.
        """
        return "\x1f".join(
            (
                self.date_operation.isoformat(),
                self.libelle,
                str(int(self.montant)),
                self.reference,
                str(self.rang),
            )
        )


def _decoder(contenu: bytes) -> str:
    """Décode le fichier, en essayant l'UTF-8 AVANT le Latin-1.

    L'ordre n'est pas indifférent : un fichier Latin-1 lu en UTF-8 lève une erreur nette,
    tandis qu'un fichier UTF-8 lu en Latin-1 réussit toujours et produit des « Ã© ». On
    essaie donc d'abord celui qui sait échouer.
    """
    for encodage in ENCODAGES:
        try:
            return contenu.decode(encodage)
        except UnicodeDecodeError:
            continue
    raise ReleveIllisible(
        "Impossible de lire ce fichier : son encodage n'est ni UTF-8 ni ISO-8859-1."
    )


def _en_centimes(texte: str) -> int | None:
    """Lit « -46,80 », « +200,00 », « 1 234,56 ». Rend `None` sur une case vide.

    Les espaces de milliers incluent l'espace INSÉCABLE et l'espace fine insécable, que
    les exports bancaires emploient et qu'un `strip()` ordinaire laisse passer.
    """
    propre = texte.strip().replace(" ", "").replace(" ", "").replace(" ", "")
    if not propre:
        return None
    propre = propre.replace(",", ".")
    try:
        # Par la chaîne et non par `float` : `int(float("0.29") * 100)` vaut 28. Le projet
        # interdit d'ailleurs les flottants dans le domaine, et c'est précisément pour ça.
        signe = -1 if propre.startswith("-") else 1
        propre = propre.lstrip("+-")
        entier, _, decimales = propre.partition(".")
        decimales = (decimales + "00")[:2]
        return signe * (int(entier or "0") * 100 + int(decimales))
    except ValueError as cause:
        raise ReleveIllisible(f"Montant illisible dans le relevé : « {texte.strip()} ».") from cause


def _en_date(texte: str) -> dt.date:
    propre = texte.strip()
    for format_ in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(propre, format_).date()
        except ValueError:
            continue
    raise ReleveIllisible(f"Date illisible dans le relevé : « {propre} ».")


def analyser(contenu: bytes) -> tuple[LigneImportee, ...]:
    """Lit le relevé et rend les lignes proposées, de la plus récente à la plus ancienne.

    La date retenue est celle de l'OPÉRATION, pas celle de comptabilisation. Elles diffèrent
    dans 94 cas sur 198 dans l'export mesuré, parfois de plusieurs jours : un achat du 30
    du mois comptabilisé le 2 tomberait dans la mauvaise période budgétaire, et le budget
    du mois s'en trouverait faux des deux côtés à la fois.
    """
    texte = _decoder(contenu)
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=SEPARATEUR)

    entetes = set(lecteur.fieldnames or [])
    if not entetes:
        raise ReleveIllisible("Ce fichier est vide.")
    manquantes = {COLONNE_LIBELLE, COLONNE_DEBIT, COLONNE_CREDIT} - entetes
    if manquantes:
        raise ReleveIllisible(
            "Ce relevé n'a pas les colonnes attendues : "
            + ", ".join(sorted(manquantes))
            + ". Exportez-le au format CSV depuis votre banque."
        )

    vues: dict[tuple[str, str, int, str], int] = {}
    lignes: list[LigneImportee] = []

    for brut in lecteur:
        debit = _en_centimes(brut.get(COLONNE_DEBIT, ""))
        credit = _en_centimes(brut.get(COLONNE_CREDIT, ""))
        if debit is None and credit is None:
            # Ligne sans montant : un pied de page, un total, une ligne vide. On l'ignore
            # plutôt que de refuser tout le fichier pour elle.
            continue
        montant = Cents(debit if debit is not None else credit or 0)

        colonne_date = (
            COLONNE_DATE_OPERATION
            if brut.get(COLONNE_DATE_OPERATION, "").strip()
            else COLONNE_DATE_COMPTABILISATION
        )
        date_operation = _en_date(brut.get(colonne_date, ""))

        libelle = (brut.get(COLONNE_LIBELLE) or brut.get(COLONNE_LIBELLE_BRUT) or "").strip()
        reference = (brut.get(COLONNE_REFERENCE) or "").strip()
        categorie = (brut.get(COLONNE_CATEGORIE) or "").strip()

        if categorie == CATEGORIE_EXCLUE:
            sens = SensImporte.VIREMENT
        elif int(montant) < 0:
            sens = SensImporte.DEPENSE
        else:
            sens = SensImporte.REVENU

        empreinte = (date_operation.isoformat(), libelle, int(montant), reference)
        rang = vues.get(empreinte, 0) + 1
        vues[empreinte] = rang

        lignes.append(
            LigneImportee(
                date_operation=date_operation,
                libelle=libelle,
                montant=montant,
                sens=sens,
                reference=reference,
                categorie_banque=categorie,
                rang=rang,
            )
        )

    return tuple(lignes)


def ecarter_les_deja_importees(
    lignes: Sequence[LigneImportee], deja: Iterable[str]
) -> tuple[tuple[LigneImportee, ...], tuple[LigneImportee, ...]]:
    """Sépare ce qui est nouveau de ce qui a déjà été importé.

    Les deux sont RENDUS, et l'écran montre les deux : cacher les lignes ignorées ferait
    croire à un fichier incomplet, et l'utilisateur qui réimporte un mois entier pour deux
    oublis a besoin de voir que les autres n'ont pas disparu — elles sont juste déjà là.
    """
    connues = set(deja)
    nouvelles = tuple(ligne for ligne in lignes if ligne.cle not in connues)
    ignorees = tuple(ligne for ligne in lignes if ligne.cle in connues)
    return nouvelles, ignorees
