"""Garde-fou n°9 — aucune couleur ni rayon en dur hors des tokens.

`frontend/src/design/tokens.ts` est l'auteur unique de la palette. Partout ailleurs, on
n'écrit que `var(--couleur-…)`. Sans ce contrôle, une teinte recopiée « juste pour ce
composant » finit par diverger de la palette sans que rien ne le signale — et c'est la
couche où cette dérive s'installe le plus vite.

CE QUI EST DÉTECTÉ dans `frontend/src` (hors tokens.ts) :
  - notations `#rgb` / `#rrggbb` / `#rrggbbaa` ;
  - fonctions de couleur `rgb()`, `rgba()`, `hsl()`, `hsla()` ;
  - `border-radius` avec une valeur en pixels.

Les COMMENTAIRES sont retirés avant l'analyse : un hexadécimal dans un commentaire ne
colorie rien, et une référence comme « ERREURS.md #008 » déclenchait un faux positif. Les
sauts de ligne sont préservés pour que les numéros signalés restent justes.

CE QUI N'EST PAS DÉTECTÉ — limites assumées :
  - les couleurs nommées CSS (`red`, `tomato`) : le mot « red » apparaît dans trop de
    contextes légitimes pour être cherché sans bruit ;
  - `currentColor`, `transparent`, `inherit` : ils ne portent aucune valeur propre et
    sont explicitement autorisés ;
  - les images et polices embarquées.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

from scripts.commun import RACINE, afficher_chemin

SOURCE = RACINE / "frontend" / "src"
TOKENS = SOURCE / "design" / "tokens.ts"

MOTIFS: Final = (
    (re.compile(r"#[0-9a-fA-F]{3,8}\b"), "couleur hexadécimale en dur"),
    (re.compile(r"\b(?:rgba?|hsla?)\s*\("), "fonction de couleur en dur"),
    (re.compile(r"border-radius\s*:[^;]*\b\d+px"), "rayon en pixels en dur"),
)

EXTENSIONS: Final = frozenset({".css", ".ts", ".tsx"})

_BLOC_COMMENTAIRE: Final = re.compile(r"/\*.*?\*/", re.DOTALL)
_LIGNE_COMMENTAIRE: Final = re.compile(r"(?<!:)//.*$", re.MULTILINE)


def retirer_commentaires(texte: str) -> str:
    """Neutralise les commentaires en préservant le nombre de lignes.

    Le `(?<!:)` évite de tronquer « https:// » ; de toute façon aucune couleur ne se
    cache dans une URL.
    """
    sans_blocs = _BLOC_COMMENTAIRE.sub(lambda m: "\n" * m.group().count("\n"), texte)
    return _LIGNE_COMMENTAIRE.sub("", sans_blocs)


def infractions(chemin: Path) -> list[str]:
    trouvailles: list[str] = []
    relatif = afficher_chemin(chemin)
    contenu = retirer_commentaires(chemin.read_text(encoding="utf-8"))
    for numero, ligne in enumerate(contenu.splitlines(), 1):
        for motif, libelle in MOTIFS:
            if motif.search(ligne):
                trouvailles.append(f"{relatif}:{numero} {libelle} — utiliser var(--…)")
    return trouvailles


def main() -> int:
    if not SOURCE.is_dir():
        print(f"Sources frontend introuvables : {SOURCE}", file=sys.stderr)
        return 1

    fichiers = [
        f
        for f in sorted(SOURCE.rglob("*"))
        if f.is_file() and f.suffix in EXTENSIONS and f != TOKENS and "schema.ts" not in f.name
    ]
    trouvailles = [t for f in fichiers for t in infractions(f)]

    if trouvailles:
        print("COULEUR OU RAYON EN DUR hors des tokens :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print(
            f"\nLa palette a un seul auteur : {afficher_chemin(TOKENS)}.",
            file=sys.stderr,
        )
        return 1

    print(f"Garde-fou n°9 : {len(fichiers)} fichiers analysés, aucune couleur en dur.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
