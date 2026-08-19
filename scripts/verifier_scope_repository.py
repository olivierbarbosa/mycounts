"""Garde-fou n°7 — toute lecture de la base passe par le repository.

Le risque principal d'une application de foyer est une requête qui oublie son périmètre
et renvoie les données d'un autre. Contre-mesure : `backend/mycounts/repository/` est le
seul endroit autorisé à construire une requête, et chacune de ses fonctions applique le
périmètre de l'appelant. Le contournement par distraction devient impossible.

Détecte hors de `repository/` : `select(...)`, `.query(...)`, `session.execute(...)`,
`text(...)`.

CE QUI N'EST PAS COUVERT : ce contrôle prouve qu'aucune requête n'est écrite ailleurs, il
ne prouve PAS que celles du repository appliquent correctement leur périmètre. C'est le
rôle du test d'intégration par route — les deux sont nécessaires, aucun ne suffit.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from scripts.commun import RACINE, afficher_chemin

BACKEND = RACINE / "backend" / "mycounts"
AUTORISE = BACKEND / "repository"
INTERDITS = frozenset({"select", "text", "query", "execute", "scalars", "scalar"})


def nom_appele(noeud: ast.Call) -> str | None:
    if isinstance(noeud.func, ast.Name):
        return noeud.func.id
    if isinstance(noeud.func, ast.Attribute):
        return noeud.func.attr
    return None


def infractions(chemin: Path) -> list[str]:
    arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
    relatif = afficher_chemin(chemin)
    return [
        f"{relatif}:{noeud.lineno} appel « {nom} » hors du repository"
        for noeud in ast.walk(arbre)
        if isinstance(noeud, ast.Call) and (nom := nom_appele(noeud)) in INTERDITS
    ]


def main() -> int:
    fichiers = [
        f for f in sorted(BACKEND.rglob("*.py"))
        if AUTORISE not in f.parents and "migrations" not in f.parts
    ]
    trouvailles = [t for f in fichiers for t in infractions(f)]

    if trouvailles:
        print("REQUÊTE ÉCRITE HORS DU REPOSITORY :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print(
            "\nDéplacer la requête dans backend/mycounts/repository/, où elle recevra le "
            "périmètre de l'appelant.",
            file=sys.stderr,
        )
        return 1

    print(f"Garde-fou n°7 : {len(fichiers)} fichiers analysés, aucune requête hors repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
