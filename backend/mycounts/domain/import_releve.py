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


class GenreCorrespondance(StrEnum):
    """Sur quoi porte une correspondance apprise."""

    LIBELLE = "libelle"
    """Le commerçant, normalisé. « intermarche » → Courses."""

    CATEGORIE_BANQUE = "categorie_banque"
    """La catégorie que la banque a posée. « Alimentation » → Courses."""


@dataclass(frozen=True)
class Correspondance:
    """Ce qu'on a retenu d'un rangement précédent.

    Deux genres, et leur ordre de priorité n'est pas indifférent — voir
    `categorie_proposee`.
    """

    genre: GenreCorrespondance
    valeur: str
    categorie_id: str


def normaliser_pour_correspondance(libelle: str) -> str:
    """Ramène un libellé à sa forme comparable.

    Volontairement identique à la normalisation des statistiques — mêmes accents, même
    casse, même ponctuation — pour qu'un commerçant reconnu dans un écran le soit dans
    l'autre. Deux normalisations différentes feraient de « Carrefour City » deux
    commerçants selon l'endroit d'où on le regarde.
    """
    from mycounts.domain.statistiques import normaliser_libelle

    return normaliser_libelle(libelle)


def categorie_proposee(
    ligne: LigneImportee, correspondances: Sequence[Correspondance]
) -> str | None:
    """La catégorie à proposer pour cette ligne, ou `None` si on ne sait pas.

    **Le particulier l'emporte sur le général.** Une correspondance apprise sur le
    COMMERÇANT passe avant une correspondance sur la catégorie de la banque : « Alimentation
    → Courses » est une règle large, « intermarche → Courses » est une décision prise pour
    ce commerçant-là. La même hiérarchie que pour le budget mensuel d'une enveloppe.

    `None` et non une catégorie par défaut : ranger de travers est pire que ne pas ranger.
    Une opération sans catégorie se voit dans les statistiques — c'est même la ligne la
    plus visible — alors qu'une opération mal rangée disparaît dans un total juste en
    apparence.
    """
    par_libelle = normaliser_pour_correspondance(ligne.libelle)
    for correspondance in correspondances:
        if (
            correspondance.genre is GenreCorrespondance.LIBELLE
            and correspondance.valeur == par_libelle
        ):
            return correspondance.categorie_id

    for correspondance in correspondances:
        if (
            correspondance.genre is GenreCorrespondance.CATEGORIE_BANQUE
            and correspondance.valeur == ligne.categorie_banque
            and ligne.categorie_banque != ""
        ):
            return correspondance.categorie_id

    return None


"""Écart de dates toléré pour rapprocher une ligne importée d'une opération existante.

Trois jours : un prélèvement se présente rarement au jour dit, et le relevé porte lui-même
deux dates qui diffèrent une fois sur deux. Au-delà, on rapprocherait des opérations qui
n'ont en commun que leur montant.
"""
JOURS_DE_TOLERANCE: Final[int] = 3


@dataclass(frozen=True)
class OperationExistante:
    """Vue minimale d'une opération déjà en base, pour la recherche de doublons."""

    date_operation: dt.date
    montant: Cents
    libelle: str


def ressemble_a_une_operation_existante(
    ligne: LigneImportee, existantes: Iterable[OperationExistante]
) -> OperationExistante | None:
    """Cherche une opération déjà enregistrée que cette ligne dupliquerait.

    Le cas visé est précis : un prélèvement saisi comme récurrence a déjà produit son
    opération, et le relevé la contient aussi. Sans ce rapprochement, l'abonnement compte
    deux fois — dans le solde, dans les budgets et dans les statistiques.

    **Le critère est le MONTANT exact et une date proche**, pas le libellé. Une récurrence
    s'appelle « Netflix » chez son propriétaire et « PRLV NETFLIX INTERNATIONAL BV » sur le
    relevé : exiger que les libellés se ressemblent ferait rater précisément les cas qu'on
    cherche.

    **Ce rapprochement ne décide RIEN.** Il signale une ressemblance à l'écran de revue,
    qui décoche la ligne et dit pourquoi. Deux dépenses du même montant à trois jours
    d'intervalle existent — un plein d'essence hebdomadaire, deux fois le même abonnement —
    et seule la personne qui les a faites peut trancher. Fusionner d'office ferait perdre
    une opération réelle sans que rien ne le dise.
    """
    for existante in existantes:
        if int(existante.montant) != int(ligne.montant):
            continue
        if abs((existante.date_operation - ligne.date_operation).days) > JOURS_DE_TOLERANCE:
            continue
        return existante
    return None


"""Seuils de détection d'un prélèvement récurrent.

Calibrés sur un export réel de 198 opérations, et corrigés par ce calibrage — la première
version exigeait trois occurrences et n'en proposait **aucune**. La raison tient en une
ligne : l'export couvrait 55 jours, où un prélèvement mensuel ne peut apparaître que deux
fois. Un seuil fixe demandait donc l'impossible, et se serait tu pour toujours sans jamais
signaler qu'il ne trouvait rien faute de pouvoir chercher.

Le seuil est désormais RELATIF à ce que la fenêtre permet d'observer : on exige trois
occurrences quand le relevé est assez long pour en contenir trois, deux quand il ne peut
pas. Sur 55 jours, le seuil retombe à deux et douze abonnements réels apparaissent ;
sur six mois, il remonte à trois et écarte les coïncidences.

Le critère d'acceptation reste le même : ne proposer QUE des prélèvements réels, quitte à
en rater. Une suggestion fausse coûte plus cher qu'une suggestion manquée — elle transforme
un écran d'aide en écran à trier, et un écran à trier ne se lit plus.

- un montant IDENTIQUE au centime : un prélèvement dont le montant varie — l'électricité,
  l'eau — n'est pas détectable ainsi, et prétendre le contraire produirait du bruit ;
- des intervalles réguliers à cinq jours près, un prélèvement mensuel ne tombant pas au
  jour dit ;
- des sorties seulement : un salaire est récurrent lui aussi, mais l'utilisateur n'a pas
  besoin qu'on le lui apprenne.
"""
OCCURRENCES_SOUHAITEES: Final[int] = 3
OCCURRENCES_MINIMALES_ABSOLUES: Final[int] = 2
"""Deux, jamais moins. Une seule occurrence n'est pas une récurrence, c'est une dépense."""
ECART_TOLERE_EN_JOURS: Final[int] = 5
INTERVALLES_CONNUS: Final[tuple[tuple[int, str], ...]] = (
    (7, "semaine"),
    (14, "quinzaine"),
    (30, "mois"),
    (91, "trimestre"),
    (365, "an"),
)


@dataclass(frozen=True)
class RecurrenceCandidate:
    """Un prélèvement qui revient, et qu'aucune récurrence enregistrée ne couvre encore."""

    libelle: str
    montant: Cents
    cadence: str
    occurrences: int
    derniere: dt.date


def detecter_les_recurrences(
    lignes: Sequence[LigneImportee], deja_connues: Iterable[Cents] = ()
) -> tuple[RecurrenceCandidate, ...]:
    """Repère les prélèvements réguliers que le relevé contient.

    **Elle ne crée rien.** Elle propose, comme tout le reste de cet import — un écran qui
    ajouterait des récurrences tout seul remplirait le calendrier de prélèvements que
    personne n'a validés, et il faudrait ensuite les défaire un par un.

    `deja_connues` contient les montants des récurrences déjà enregistrées : les
    reproposer serait exactement le bruit qu'on cherche à éviter. Le rapprochement se fait
    sur le montant seul, pour la même raison qu'ailleurs — le libellé d'une récurrence
    saisie à la main ne ressemble pas à celui du relevé.

    Ce qu'elle ne détecte PAS, et il vaut mieux le savoir : un prélèvement dont le montant
    varie d'un mois à l'autre. L'électricité, l'eau, une carte de crédit. Les repérer
    demanderait une tolérance sur le montant, qui rapprocherait aussi des dépenses sans
    aucun rapport — et le prix serait payé en suggestions fausses.
    """
    montants_connus = {int(m) for m in deja_connues}

    par_commercant: dict[tuple[str, int], list[dt.date]] = {}
    for ligne in lignes:
        if int(ligne.montant) >= 0:
            continue
        if int(ligne.montant) in montants_connus:
            continue
        cle = (normaliser_pour_correspondance(ligne.libelle), int(ligne.montant))
        par_commercant.setdefault(cle, []).append(ligne.date_operation)

    # La fenêtre du relevé décide de ce qu'on peut espérer voir.
    toutes_les_dates = [ligne.date_operation for ligne in lignes]
    fenetre = (
        (max(toutes_les_dates) - min(toutes_les_dates)).days if toutes_les_dates else 0
    )

    candidates: list[RecurrenceCandidate] = []
    for (libelle, montant), dates in par_commercant.items():
        if len(dates) < OCCURRENCES_MINIMALES_ABSOLUES:
            continue
        ordonnees = sorted(dates)
        ecarts = [
            (suivante - precedente).days
            for precedente, suivante in zip(ordonnees, ordonnees[1:], strict=False)
        ]
        moyen = sum(ecarts) / len(ecarts)

        cadence = next(
            (
                nom
                for jours, nom in INTERVALLES_CONNUS
                if abs(moyen - jours) <= ECART_TOLERE_EN_JOURS
            ),
            None,
        )
        if cadence is None:
            continue
        # Régulier ne veut pas dire « en moyenne régulier » : trois dépenses les 1er, 2 et
        # 60 ont une moyenne mensuelle et ne sont pas un abonnement.
        if any(abs(ecart - moyen) > ECART_TOLERE_EN_JOURS for ecart in ecarts):
            continue

        # Le seuil, enfin, RELATIF à la cadence trouvée : exiger trois occurrences d'un
        # prélèvement annuel sur un relevé de deux mois est une exigence qu'aucun fichier
        # ne peut satisfaire, et un seuil qu'on ne peut pas atteindre est un seuil qui se
        # tait pour toujours.
        jours_de_la_cadence = next(j for j, nom in INTERVALLES_CONNUS if nom == cadence)
        observables = fenetre // jours_de_la_cadence + 1
        exigees = max(
            OCCURRENCES_MINIMALES_ABSOLUES, min(OCCURRENCES_SOUHAITEES, observables)
        )
        if len(ordonnees) < exigees:
            continue

        candidates.append(
            RecurrenceCandidate(
                libelle=libelle,
                montant=Cents(montant),
                cadence=cadence,
                occurrences=len(ordonnees),
                derniere=ordonnees[-1],
            )
        )

    return tuple(sorted(candidates, key=lambda c: (int(c.montant), c.libelle)))


"""Correspondances par défaut entre les catégories des banques françaises et celles du
foyer, par NOM.

Elles évitent le pire cas de l'import : un premier relevé de deux cents lignes toutes
« sans catégorie », qui rend muets les statistiques et les budgets, et qu'il faudrait
ranger à la main avant que l'apprentissage n'ait quoi que ce soit à apprendre.

Par NOM et non par identifiant : le domaine ne connaît pas la base. L'appelant cherche la
catégorie du foyer qui porte ce nom, et ne propose rien s'il ne la trouve pas — un foyer
qui a renommé « Courses » en « Alimentation » ne doit pas se voir imposer une catégorie
inventée.

Ce tableau ne couvre PAS tout, volontairement. « Banque et assurances », « Juridique et
administratif » ou « À catégoriser » n'ont pas d'équivalent évident, et deviner y ferait
plus de mal que de bien : une ligne mal rangée disparaît dans un total juste en apparence,
là où une ligne non rangée se voit.
"""
CORRESPONDANCES_PAR_DEFAUT: Final[dict[str, tuple[str, ...]]] = {
    # Chaque catégorie de banque propose plusieurs noms possibles, du plus précis au plus
    # général : le foyer garde ses propres mots, et le premier nom qu'il possède gagne.
    "Alimentation": ("Courses", "Alimentation"),
    "Transports": ("Transport", "Transports"),
    "Sante": ("Santé", "Sante"),
    "Santé": ("Santé", "Sante"),
    "Logement - maison": ("Logement", "Loyer"),
    "Loisirs et vacances": ("Restaurants et sorties", "Sorties", "Loisirs"),
    "Shopping et services": ("Achats divers", "Shopping"),
    "Revenus et rentrees d'argent": ("Autres revenus", "Salaire"),
    "Remboursements de soins": ("Remboursement", "Santé"),
}


def categorie_par_defaut(
    ligne: LigneImportee, noms_du_foyer: Sequence[str]
) -> str | None:
    """Le nom de catégorie du foyer qui correspond à celle de la banque, s'il existe.

    Rend un NOM, que l'appelant convertit en identifiant. Rien quand le foyer ne possède
    aucun des noms proposés : mieux vaut une ligne non rangée qu'une catégorie inventée.
    """
    propositions = CORRESPONDANCES_PAR_DEFAUT.get(ligne.categorie_banque.strip())
    if propositions is None:
        return None
    disponibles = {nom.strip().lower(): nom for nom in noms_du_foyer}
    for propose in propositions:
        trouve = disponibles.get(propose.lower())
        if trouve is not None:
            return trouve
    return None
