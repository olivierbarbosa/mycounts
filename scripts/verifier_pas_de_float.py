"""Garde-fou n°6 — aucun flottant dans le domaine.

`backend/mycounts/domain/` contient les règles de calcul monétaire. Un `float` y est
interdit sans exception : un montant est un entier de centimes.

Détecte, par analyse de l'arbre syntaxique (et non par recherche textuelle, qui se
laisserait tromper par un commentaire) :
  - tout littéral flottant (`0.1`, `1e3`) ;
  - tout usage du nom `float` (appel, annotation, isinstance).

CE QUI N'EST PAS COUVERT : le reste du backend. Une division flottante dans une route
API échappe à ce contrôle — c'est `Cents` et mypy qui l'attrapent là-bas, ce qui est
plus faible. Étendre le périmètre le jour où un calcul monétaire sortira du domaine.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from scripts.commun import RACINE, afficher_chemin

DOMAINE = RACINE / "backend" / "mycounts" / "domain"


def infractions(chemin: Path) -> list[str]:
    arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
    relatif = afficher_chemin(chemin)
    trouvailles: list[str] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Constant) and isinstance(noeud.value, float):
            trouvailles.append(f"{relatif}:{noeud.lineno} littéral flottant {noeud.value!r}")
        elif isinstance(noeud, ast.Name) and noeud.id == "float":
            trouvailles.append(f"{relatif}:{noeud.lineno} usage du type « float »")
    return trouvailles


def main() -> int:
    if not DOMAINE.is_dir():
        print(f"Répertoire du domaine introuvable : {DOMAINE}", file=sys.stderr)
        return 1

    trouvailles = [t for f in sorted(DOMAINE.rglob("*.py")) for t in infractions(f)]

    if trouvailles:
        print("FLOTTANT DANS LE DOMAINE :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print("\nUn montant est un entier de centimes (voir domain/montants.py).", file=sys.stderr)
        return 1

    print("Garde-fou n°6 : aucun flottant dans le domaine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
