"""Catégories fournies à la création d'un foyer.

Décision D1 (BOUCLE.md) : une liste est proposée d'emblée plutôt qu'un écran vide. Elle
est entièrement modifiable et supprimable — ce sont des données du foyer, pas une
configuration figée.

Auteur unique de cette liste : la recopier dans un script d'amorçage ou une fixture de
test créerait une seconde version qui dériverait à la première modification.
"""

from __future__ import annotations

from typing import Final, NamedTuple

from mycounts.models.budget import NatureCategorie, TeinteCategorie


class CategorieInitiale(NamedTuple):
    nom: str
    nature: NatureCategorie
    teinte: TeinteCategorie


CATEGORIES_INITIALES: Final[tuple[CategorieInitiale, ...]] = (
    CategorieInitiale("Courses", NatureCategorie.DEPENSE, TeinteCategorie.VERT),
    CategorieInitiale("Logement", NatureCategorie.DEPENSE, TeinteCategorie.VIOLET),
    CategorieInitiale("Transport", NatureCategorie.DEPENSE, TeinteCategorie.CYAN),
    CategorieInitiale("Abonnements", NatureCategorie.DEPENSE, TeinteCategorie.ROSE),
    CategorieInitiale("Restaurants et sorties", NatureCategorie.DEPENSE, TeinteCategorie.AMBRE),
    CategorieInitiale("Santé", NatureCategorie.DEPENSE, TeinteCategorie.CYAN),
    CategorieInitiale("Achats divers", NatureCategorie.DEPENSE, TeinteCategorie.ARDOISE),
    CategorieInitiale("Salaire", NatureCategorie.REVENU, TeinteCategorie.VERT),
    # Un remboursement n'est ni une paie ni un gain : c'est de l'argent qui revient. Le
    # ranger dans « Autres revenus » gonflait les revenus du mois d'une somme qui n'en est
    # pas un, et rendait illisible la question « combien ai-je réellement gagné ».
    CategorieInitiale("Remboursement", NatureCategorie.REVENU, TeinteCategorie.AMBRE),
    CategorieInitiale("Autres revenus", NatureCategorie.REVENU, TeinteCategorie.CYAN),
)
"""Volontairement courte.

Une taxonomie fine décourage la saisie : on hésite, on remet à plus tard, et l'outil ne
sert plus. Sept postes de dépense couvrent l'essentiel d'un budget de foyer ; les autres
s'ajoutent quand un besoin réel apparaît.
"""
