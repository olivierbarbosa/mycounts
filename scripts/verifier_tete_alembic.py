"""Garde-fou n°4 — les migrations n'ont qu'une seule tête.

Deux têtes signifient deux branches de migration fusionnées sans arbitrage : la base de
production suivra l'une des deux, et l'autre ne sera jamais appliquée — en silence.

Au lot 0 il n'existe encore aucune migration : le contrôle est donc « **au plus** une
tête », pas « exactement une ». Écrire « exactement » aurait produit un garde-fou rouge
dès le premier jour, qu'on aurait désactivé.
"""

from __future__ import annotations

import sys

from alembic.config import Config
from alembic.script import ScriptDirectory

from scripts.commun import RACINE


def main() -> int:
    script = ScriptDirectory.from_config(Config(str(RACINE / "alembic.ini")))
    tetes = script.get_heads()

    if len(tetes) > 1:
        print(f"{len(tetes)} TÊTES DE MIGRATION : {', '.join(tetes)}", file=sys.stderr)
        print("Fusionner avec « alembic merge » et arbitrer l'ordre.", file=sys.stderr)
        return 1

    print(f"Garde-fou n°4 : {len(tetes)} tête de migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
