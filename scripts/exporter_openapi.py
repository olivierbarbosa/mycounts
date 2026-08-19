"""Écrit le schéma OpenAPI sur la sortie standard.

Le serveur fait foi : le client génère ses types depuis ce fichier et n'en écrit aucun à
la main. Inventer un contrat côté client est l'anti-pattern n°1 du projet — le jour où le
serveur change, rien ne signale la divergence.
"""

from __future__ import annotations

import json
import sys

from mycounts.api.app import app


def main() -> int:
    json.dump(app.openapi(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
