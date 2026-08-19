"""Utilitaires partagés par les garde-fous.

Auteur unique de la liste des chemins exclus : la recopier dans chaque script
garantirait qu'un jour l'un d'eux analyse `node_modules` et l'autre non.
"""

from __future__ import annotations

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
    """Tous les fichiers versionnables du dépôt, hors répertoires d'outillage."""
    for chemin in racine.rglob("*"):
        if not chemin.is_file():
            continue
        if EXCLUS & set(chemin.relative_to(racine).parts):
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
