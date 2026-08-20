"""Utilitaires partagés par les garde-fous.

Auteur unique de la liste des chemins exclus : la recopier dans chaque script
garantirait qu'un jour l'un d'eux analyse `node_modules` et l'autre non.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Final

RACINE: Final = Path(__file__).resolve().parent.parent

EXCLUS: Final = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
     ".pytest_cache", ".ruff_cache", "dist", ".vite", "playwright-report", "test-results"}
)

BINAIRES: Final = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ico", ".woff", ".woff2",
     ".ttf", ".zip", ".gz", ".db", ".sqlite", ".mp4", ".webm"}
)


def fichiers_du_depot(racine: Path = RACINE) -> Iterator[Path]:
    """Tous les fichiers qui peuvent PARTIR dans un commit, hors outillage.

    Demandé à git plutôt que parcouru sur le disque, et la nuance n'est pas théorique :
    `.env` existe sur toute machine de développement et contient des secrets — c'est sa
    raison d'être. Un balayage du disque le trouvait et faisait rougir le garde-fou des
    secrets sur un fichier que `.gitignore` empêche justement de partir. Un contrôle qui
    rougit devant une situation correcte finit par être désactivé, et c'est alors le vrai
    cas qui passe.

    Sont rendus les fichiers SUIVIS et les fichiers non suivis mais non ignorés — ces
    derniers comptent, car ce sont précisément ceux qu'un `git add .` distrait emporterait.

    Repli sur le disque quand git est absent : mieux vaut un contrôle trop large qu'aucun.
    """
    try:
        listés = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=racine,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        for chemin in racine.rglob("*"):
            if chemin.is_file() and not (EXCLUS & set(chemin.relative_to(racine).parts)):
                yield chemin
        return

    for relatif in listés.split("\0"):
        if not relatif:
            continue
        chemin = racine / relatif
        if not chemin.is_file():
            continue
        if EXCLUS & set(Path(relatif).parts):
            continue
        yield chemin


def texte_de(chemin: Path) -> str | None:
    """Contenu texte d'un fichier, ou None s'il est binaire ou illisible.

    Les images sont ignorées : une capture d'écran contenant un relevé ne serait PAS
    détectée par ce garde-fou. C'est une limite assumée — il faudrait de l'OCR.
    """
    if chemin.suffix.lower() in BINAIRES:
        return None
    try:
        return chemin.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def afficher_chemin(chemin: Path, racine: Path = RACINE) -> str:
    """Chemin relatif au dépôt s'il en fait partie, absolu sinon.

    `relative_to` lève une exception pour un fichier extérieur ; les témoins des
    garde-fous analysent justement des fichiers temporaires hors du dépôt.
    """
    try:
        return str(chemin.relative_to(racine))
    except ValueError:
        return str(chemin)
