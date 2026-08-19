"""Garde-fou n°3 — aucune donnée bancaire envoyée à un LLM.

À ce stade le projet ne fait AUCUN appel à un modèle de langage. Le contrôle réellement
vérifiable est donc l'absence de tout client LLM dans les dépendances : il n'y a aucun
prompt à analyser, et prétendre analyser des prompts inexistants serait un garde-fou
décoratif.

Le jour où une catégorisation assistée arrive, elle apporte dans LE MÊME COMMIT l'analyse
statique des sources vérifiant que les libellés sont anonymisés et qu'aucun identifiant de
compte ne part — et jamais un prompt lu depuis la base, qui y serait invisible.
"""

from __future__ import annotations

import re
import sys
from typing import Final

from scripts.commun import RACINE

CLIENTS_LLM: Final = frozenset(
    {"anthropic", "openai", "google-generativeai", "google-genai", "mistralai", "cohere",
     "ollama", "litellm", "langchain", "langchain-openai", "llama-index", "transformers",
     "@anthropic-ai/sdk", "@google/generative-ai", "@mistralai/mistralai"}
)

FICHIERS: Final = ("pyproject.toml", "requirements.txt", "requirements-dev.txt",
                   "frontend/package.json")


def main() -> int:
    trouvailles: list[str] = []
    for nom in FICHIERS:
        chemin = RACINE / nom
        if not chemin.exists():
            continue
        contenu = chemin.read_text(encoding="utf-8")
        for client in CLIENTS_LLM:
            motif = rf'["\']?{re.escape(client)}["\']?\s*[:=><~"\'\],]'
            if re.search(motif, contenu):
                trouvailles.append(f"{nom} : dépendance « {client} »")

    if trouvailles:
        print("CLIENT LLM DÉTECTÉ dans les dépendances :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print(
            "\nAjouter un client LLM impose d'ajouter, dans le même commit, l'analyse "
            "statique vérifiant qu'aucune donnée bancaire ne part vers lui — puis de "
            "remplacer ce garde-fou.",
            file=sys.stderr,
        )
        return 1

    print("Garde-fou n°3 : aucun client LLM dans les dépendances.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
