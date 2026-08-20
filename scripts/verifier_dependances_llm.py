"""Garde-fou n°3 — ce qui part vers un modèle de langage, et rien d'autre.

Ce garde-fou a changé de nature le 21 août 2026. Il interdisait toute dépendance à un
client LLM, faute d'appel à surveiller ; sa propre docstring annonçait la suite :

    « Le jour où une catégorisation assistée arrive, elle apporte dans LE MÊME COMMIT
      l'analyse statique des sources vérifiant que les libellés sont anonymisés et
      qu'aucun identifiant de compte ne part. »

Ce jour est arrivé. Olivier a demandé une catégorisation assistée le 20 août 2026 et
accepté, après qu'on lui a montré ce que contiendraient les libellés — y compris ceux qui
trahissent un rendez-vous médical — que ceux-ci sortent du foyer.

Le contrôle porte donc désormais sur TROIS choses, toutes vérifiables par lecture des
sources :

1. **un seul fichier** parle à un service externe. Un projet qui envoie des données
   bancaires doit pouvoir répondre « ce fichier, et lui seul » ;
2. **ce fichier ne mentionne aucun champ sensible** — montant, solde, IBAN, identifiant de
   compte, date d'opération. Ce n'est pas une preuve absolue, et la limite est écrite plus
   bas, mais aucune de ces notions n'a de raison d'apparaître là où l'on n'envoie que des
   libellés ;
3. **aucun client LLM n'entre dans les dépendances.** L'appel se fait en HTTP simple : un
   SDK apporterait des chemins d'envoi que ce garde-fou ne saurait pas lire.

**Ce qu'il ne détecte PAS**, et il faut le savoir avant de lui faire confiance :

- une donnée sensible passée sous un nom qui n'est pas dans la liste ci-dessous. Le
  contrôle est lexical, pas sémantique ;
- une fuite par un service tiers appelé indirectement — un client HTTP enveloppé dans une
  fonction utilitaire d'un autre module, par exemple ;
- ce que le service distant fait des libellés une fois reçus. Cela ne se vérifie pas depuis
  ce dépôt, et c'est le prix accepté en connaissance de cause.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Final

from scripts.commun import RACINE

CLIENTS_LLM: Final = frozenset(
    {"anthropic", "openai", "google-generativeai", "google-genai", "mistralai", "cohere",
     "ollama", "litellm", "langchain", "langchain-openai", "llama-index", "transformers",
     "@anthropic-ai/sdk", "@google/generative-ai", "@mistralai/mistralai"}
)

FICHIERS_DE_DEPENDANCES: Final = ("pyproject.toml", "requirements.txt",
                                  "requirements-dev.txt", "frontend/package.json")

"""Le SEUL fichier autorisé à parler à un service externe."""
PORTE_DE_SORTIE: Final = Path("backend/mycounts/services/categorisation_ia.py")

"""Hôtes tiers auxquels le projet s'adresse. Toute mention ailleurs que dans la porte de
sortie fait échouer ce contrôle."""
HOTES_EXTERNES: Final = ("openrouter.ai", "api.openai.com", "api.anthropic.com",
                         "generativelanguage.googleapis.com", "api.mistral.ai")

"""Champs qui ne doivent JAMAIS apparaître dans la porte de sortie.

Aucun n'a de raison d'y figurer : ce fichier reçoit des listes de chaînes et n'a accès à
rien d'autre. Leur présence signalerait qu'on a commencé à lui passer des objets riches.
"""
CHAMPS_SENSIBLES: Final = ("montant", "solde", "iban", "compte_id", "date_operation",
                           "foyer_id", "utilisateur_id", "reference", "cle_import")


def _champs_sensibles_dans_le_code(porte: Path) -> list[str]:
    """Cherche les champs interdits dans le CODE, jamais dans la documentation.

    Par l'arbre syntaxique et non par une expression régulière : la docstring de ce
    fichier-là nomme précisément les champs qui ne doivent pas sortir, pour dire qu'ils ne
    sortent pas. Un contrôle lexical échouait donc sur sa propre documentation — c'est
    arrivé à la première version, et un garde-fou qui rougit devant un texte correct finit
    par être désactivé.

    Sont inspectés : les noms de variables, les attributs, les mots-clés d'appel et les
    chaînes littérales qui ne sont pas des docstrings. C'est-à-dire tout ce par quoi une
    donnée pourrait effectivement passer.
    """
    arbre = ast.parse(porte.read_text(encoding="utf-8"))

    porteurs = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    docstrings = {
        id(noeud.body[0].value)
        for noeud in ast.walk(arbre)
        if isinstance(noeud, porteurs)
        and noeud.body
        and isinstance(noeud.body[0], ast.Expr)
        and isinstance(noeud.body[0].value, ast.Constant)
        and isinstance(noeud.body[0].value.value, str)
    }

    mots: set[str] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Name):
            mots.add(noeud.id)
        elif isinstance(noeud, ast.Attribute):
            mots.add(noeud.attr)
        elif isinstance(noeud, ast.arg):  # noqa: SIM114 — voir juste en dessous
            mots.add(noeud.arg)
        # Deux branches distinctes malgré l'apparence : `ast.arg.arg` est toujours une
        # chaîne, `ast.keyword.arg` peut valoir None (cas de `**kwargs`). Les fusionner
        # avec un `or` — ce qu'un formateur propose volontiers — fait passer un `None` à
        # `add`, et le typage le refuse à juste titre.
        elif isinstance(noeud, ast.keyword) and noeud.arg is not None:
            mots.add(noeud.arg)
        elif (
            isinstance(noeud, ast.Constant)
            and isinstance(noeud.value, str)
            and id(noeud) not in docstrings
        ):
            mots.update(re.findall(r"\w+", noeud.value.lower()))

    return [
        f"{PORTE_DE_SORTIE} : le code mentionne « {champ} ». Ce fichier ne reçoit que des "
        "libellés ; un champ bancaire n'y a rien à faire."
        for champ in CHAMPS_SENSIBLES
        if any(champ in mot.lower() for mot in mots)
    ]


def _sources() -> list[Path]:
    racine = RACINE / "backend"
    return [
        chemin
        for chemin in racine.rglob("*.py")
        if "__pycache__" not in chemin.parts and "migrations" not in chemin.parts
    ]


def main() -> int:
    trouvailles: list[str] = []

    for nom in FICHIERS_DE_DEPENDANCES:
        chemin = RACINE / nom
        if not chemin.exists():
            continue
        contenu = chemin.read_text(encoding="utf-8")
        for client in CLIENTS_LLM:
            motif = rf'["\']?{re.escape(client)}["\']?\s*[:=><~"\'\],]'
            if re.search(motif, contenu):
                trouvailles.append(
                    f"{nom} : dépendance « {client} » — l'appel doit rester en HTTP simple, "
                    "un SDK ouvrirait des chemins d'envoi que ce contrôle ne sait pas lire."
                )

    porte = RACINE / PORTE_DE_SORTIE
    for source in _sources():
        contenu = source.read_text(encoding="utf-8")
        relatif = source.relative_to(RACINE)
        for hote in HOTES_EXTERNES:
            if hote in contenu and source != porte:
                trouvailles.append(
                    f"{relatif} : appelle « {hote} ». Un seul fichier a le droit de parler "
                    f"à un tiers, et c'est {PORTE_DE_SORTIE}."
                )

    if porte.exists():
        trouvailles.extend(_champs_sensibles_dans_le_code(porte))

    if trouvailles:
        print("SORTIE DE DONNÉES NON CONFORME :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        return 1

    print(
        f"Garde-fou n°3 : une seule porte de sortie ({PORTE_DE_SORTIE.name}), "
        "aucun champ bancaire dedans, aucun client LLM en dépendance."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
