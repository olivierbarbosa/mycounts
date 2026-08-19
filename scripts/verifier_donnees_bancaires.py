"""Garde-fou n°1 — aucune donnée bancaire réelle dans le dépôt.

CE QUI EST DÉTECTÉ
  - IBAN dont le **checksum mod-97 est valide** (un IBAN inventé au hasard a 1 chance
    sur 97 de passer, donc quasi aucun faux positif) ;
  - numéros de carte de 13 à 19 chiffres dont le **checksum de Luhn est valide**.

CE QUI N'EST PAS DÉTECTÉ — limites assumées, écrites ici pour qu'on ne s'y fie pas :
  - les « soldes plausibles » : un montant n'a aucune signature qui le distingue d'un
    nombre quelconque. Un tel contrôle produirait surtout du bruit, on cesserait de le
    lire, et il finirait désactivé. Il n'est donc pas tenté ;
  - le contenu des images : une capture d'écran de relevé passe au travers ;
  - les libellés d'opérations réelles (« VIR SEPA DUPONT ») ;
  - l'historique git : seul l'arbre de travail est analysé.
"""

from __future__ import annotations

import re
import sys
from typing import Final

from scripts.commun import RACINE, fichiers_du_depot, texte_de

_IBAN: Final = re.compile(r"\b[A-Z]{2}\d{2}[ ]?(?:[A-Z0-9]{4}[ ]?){2,7}[A-Z0-9]{1,4}\b")
_CARTE: Final = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def iban_valide(candidat: str) -> bool:
    """Validation mod-97 (ISO 13616)."""
    brut = candidat.replace(" ", "").upper()
    if not 15 <= len(brut) <= 34:
        return False
    reordonne = brut[4:] + brut[:4]
    try:
        numerique = "".join(str(int(c, 36)) for c in reordonne)
    except ValueError:
        return False
    return int(numerique) % 97 == 1


def luhn_valide(candidat: str) -> bool:
    chiffres = [int(c) for c in candidat if c.isdigit()]
    if not 13 <= len(chiffres) <= 19:
        return False
    if len(set(chiffres)) == 1:  # 0000000000000 : remplissage, pas un PAN
        return False
    total = 0
    for position, chiffre in enumerate(reversed(chiffres)):
        if position % 2 == 1:
            chiffre *= 2
            if chiffre > 9:
                chiffre -= 9
        total += chiffre
    return total % 10 == 0


def main() -> int:
    trouvailles: list[str] = []
    moi = __file__

    for chemin in fichiers_du_depot():
        if str(chemin) == moi:
            continue
        contenu = texte_de(chemin)
        if contenu is None:
            continue
        relatif = chemin.relative_to(RACINE)
        for numero, ligne in enumerate(contenu.splitlines(), 1):
            for correspondance in _IBAN.finditer(ligne):
                if iban_valide(correspondance.group()):
                    trouvailles.append(f"{relatif}:{numero} IBAN de checksum valide")
            for correspondance in _CARTE.finditer(ligne):
                if luhn_valide(correspondance.group()):
                    trouvailles.append(f"{relatif}:{numero} numéro de carte (Luhn valide)")

    if trouvailles:
        print("DONNÉE BANCAIRE DÉTECTÉE — la CI échoue :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print(
            "\nAucune donnée bancaire réelle ne doit entrer dans le dépôt. Pour une "
            "fixture, utiliser un IBAN au checksum délibérément faux.",
            file=sys.stderr,
        )
        return 1

    print("Garde-fou n°1 : aucune donnée bancaire détectée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
