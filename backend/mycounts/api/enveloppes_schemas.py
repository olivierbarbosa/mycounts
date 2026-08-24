"""Schémas des enveloppes.

Aucun de ces schémas ne porte de solde à écrire : le solde se recalcule depuis le journal.
Ce qui entre, ce sont des MOUVEMENTS.
"""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from mycounts.domain.enveloppes import Rollover, TypeMouvement, UsageEnveloppe


class DemandeEnveloppe(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    categorie_id: uuid.UUID | None = None
    compte_prefere_id: uuid.UUID | None = None
    cible_centimes: int | None = Field(default=None, gt=0)
    date_cible: dt.date | None = None

    allocation_initiale_centimes: int = Field(
        default=0,
        ge=0,
        description=(
            "Somme réservée d'emblée. Enregistrée comme un MOUVEMENT du journal, jamais "
            "comme un solde de départ : sinon ce serait la seule valeur que l'historique "
            "ignore."
        ),
    )
    type_allocation_initiale: TypeMouvement = TypeMouvement.ALLOCATION
    usage: UsageEnveloppe = UsageEnveloppe.FONCTIONNEMENT
    rollover: Rollover = Rollover.REPORT
    priorite: int = Field(default=0, ge=0)
    contribution_mensuelle_centimes: int | None = Field(default=None, gt=0)


class ModificationEnveloppe(BaseModel):
    """Champs absents = inchangés.

    `null` retire une catégorie ou un compte préféré : ces deux liens sont facultatifs et
    le formulaire propose explicitement « aucun ». Une cible, elle, ne peut pas être
    retirée ici : cela ferait cesser toute recommandation mensuelle et mérite un parcours
    explicite plutôt qu'un champ vidé par mégarde.
    """

    nom: str | None = Field(default=None, min_length=1, max_length=80)
    categorie_id: uuid.UUID | None = None
    compte_prefere_id: uuid.UUID | None = None
    cible_centimes: int | None = Field(default=None, gt=0)
    date_cible: dt.date | None = None
    archive: bool | None = None
    usage: UsageEnveloppe | None = None
    rollover: Rollover | None = None
    priorite: int | None = Field(default=None, ge=0)
    contribution_mensuelle_centimes: int | None = Field(default=None, gt=0)


class DemandeMouvement(BaseModel):
    type: TypeMouvement
    montant_centimes: int = Field(
        gt=0,
        description=(
            "TOUJOURS positif : c'est le type qui dit le sens. Un montant signé rendrait "
            "possible une allocation négative, c'est-à-dire une reprise déguisée."
        ),
    )
    date_mouvement: dt.date | None = None
    libelle: str = Field(default="", max_length=140)


class MouvementPublic(BaseModel):
    id: uuid.UUID
    type: TypeMouvement
    montant_centimes: int
    date_mouvement: dt.date
    libelle: str


class EnveloppePublique(BaseModel):
    id: uuid.UUID
    nom: str
    categorie_id: uuid.UUID | None
    categorie_nom: str | None
    compte_prefere_id: uuid.UUID | None
    cible_centimes: int | None
    date_cible: dt.date | None
    solde_centimes: int
    """Peut être NÉGATIF : une dépense réelle n'est jamais bloquée par une enveloppe
    mal financée."""

    place_centimes: int | None
    """Ce qu'il manque pour atteindre la cible. `None` s'il n'y a pas de cible — et non
    zéro, qui se lirait comme « enveloppe pleine »."""

    contribution_theorique_centimes: int | None = None
    """Ce qu'il faudrait y mettre CHAQUE MOIS pour tenir l'échéance.

    `None` sans objectif ou sans date : les deux sont nécessaires. Une cible sans échéance
    est un plancher — « au moins 5 000 € pour les travaux » — qu'aucun rythme ne presse.

    Indicative, et rendue séparément de ce que la préparation recommande : les deux
    diffèrent dès que l'épargne disponible ne suffit pas, et c'est précisément l'écart
    qu'il faut pouvoir lire — « il faudrait 143 € par mois, je ne peux en mettre que 90 »
    est un renseignement, « 90 » tout seul n'en est pas un."""

    part: int
    archive: bool
    usage: UsageEnveloppe
    rollover: Rollover
    priorite: int
    contribution_mensuelle_centimes: int | None


class RepartitionPublique(BaseModel):
    """L'épargne découpée, et ce qui reste libre."""

    epargne_totale_centimes: int
    reserve_centimes: int
    """Somme des soldes POSITIFS seulement : une enveloppe dans le rouge ne rogne pas ce
    que les autres promettent."""

    non_affecte_centimes: int
    """Peut être négatif : l'argent a fondu sous ce qui était réservé."""

    decouvert: bool
    enveloppes: list[EnveloppePublique]


class LignePreparationPublique(BaseModel):
    """Une ligne de la proposition. Rien n'est écrit tant qu'elle n'est pas validée."""

    enveloppe_id: uuid.UUID
    nom: str
    a_liberer_centimes: int
    demande_un_choix: bool
    recommande_centimes: int
    place_centimes: int | None
    limitee_par_le_disponible: bool
    """Vrai quand l'argent a manqué pour servir cette enveloppe entièrement. Exposé plutôt
    que déduit à l'écran : « 40 € » et « 40 € parce qu'il ne restait que ça » ne disent pas
    la même chose, et seul le calcul sait laquelle des deux est vraie."""


class PreparationPublique(BaseModel):
    lignes: list[LignePreparationPublique]
    disponible_avant_centimes: int
    disponible_apres_centimes: int
    total_recommande_centimes: int
    total_libere_centimes: int
    attend_des_choix: bool

    capacite_epargne_centimes: int
    """Ce qu'on peut mettre de côté ce mois-ci : le solde PROJETÉ du quotidien.

    Projeté et non réel : ce qui reste aujourd'hui n'est pas ce qui restera après les
    prélèvements de la fin du mois. Placer le réel viderait le compte courant juste avant
    l'échéance du loyer — la mesure la plus dangereuse serait ici la plus optimiste.

    Jamais négatif : un mois déficitaire ne propose pas de placer une somme négative, il
    ne propose rien. Zéro dit « rien à placer », ce qui est exact.

    Répond à « chaque mois, l'application doit calculer combien je peux théoriquement
    mettre de côté » — demandé le 22 août 2026. Le montant n'est PAS déduit du disponible
    des enveloppes : celui-ci découpe l'épargne déjà là, celui-là dit ce qui pourrait la
    rejoindre. Les additionner promettrait deux fois le même argent."""

    compte_courant_suggere_id: uuid.UUID | None = None
    """D'où partirait le virement. `None` dès qu'il y a plusieurs comptes courants.

    Même règle que pour la destination : un seul candidat est une réponse, plusieurs n'en
    sont pas une. Le bouton ne s'affiche alors pas — proposer une action dont on ne connaît
    pas la moitié des termes reviendrait à choisir un compte au hasard pour l'utilisateur,
    et à déplacer son argent d'un endroit qu'il n'a pas désigné."""

    compte_epargne_suggere_id: uuid.UUID | None = None
    """Vers quel compte proposer le virement. `None` s'il n'y a aucun compte d'épargne.

    Choisi parmi les `compte_prefere_id` des enveloppes quand elles s'accordent, sinon le
    premier compte d'épargne. Une préférence de couverture n'a jamais déclenché de
    mouvement automatique et n'en déclenche toujours pas : elle ne fait que pré-remplir un
    formulaire que l'utilisateur valide."""


class ChoixDeLigne(BaseModel):
    """Ce que l'utilisateur retient d'une ligne, après l'avoir vue."""

    enveloppe_id: uuid.UUID
    allouer_centimes: int = Field(
        default=0,
        ge=0,
        description=(
            "Montant réellement alloué. Peut différer de la recommandation : c'est une "
            "proposition, pas un ordre."
        ),
    )
    liberer_centimes: int = Field(
        default=0,
        ge=0,
        description=(
            "Reliquat réellement libéré. Pour une enveloppe en mode « demander », zéro "
            "signifie que l'utilisateur a répondu « garder »."
        ),
    )


class DemandePreparation(BaseModel):
    """Application de la préparation. SEULE écriture du passage de période.

    Les lignes absentes ne sont pas appliquées : ne rien envoyer n'écrit rien. C'est ce
    qui permet de valider une partie de la proposition et de revenir plus tard sur le
    reste, sans que le calcul ait à se souvenir de quoi que ce soit.
    """

    lignes: list[ChoixDeLigne]
