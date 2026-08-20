"""Avertit quand la base de DÉMONSTRATION est en retard sur les migrations.

**Ce qu'il détecte.** Une migration écrite et appliquée à la base de développement, mais
pas à celle de la démonstration. L'API de démonstration refuse alors de démarrer, et
l'application n'affiche plus rien du tout : le fond, et c'est tout.

**Pourquoi il existe.** Le piège était déjà écrit dans `BOUCLE.md` — « la base de
DÉMONSTRATION se migre séparément » — et il a quand même été payé le 20 août 2026, au lot C.
Une consigne qu'on relit ne remplace pas un contrôle qui la vérifie : c'est exactement ce
que ce projet reproche aux garde-fous absents, et il n'y avait aucune raison d'en excepter
celui-ci.

**Ce qu'il ne détecte PAS**, et c'est délibéré :

- il n'AVERTIT que, il ne bloque pas. La base de démonstration est une commodité locale ;
  faire échouer la vérification d'un poste qui n'en a pas serait un contrôle qui punit ceux
  qui ne sont pas concernés ;
- il se tait si la base est injoignable ou n'existe pas — même raison ;
- il ne dit rien de la base de PRODUCTION, qu'il ne connaît pas et n'a pas à connaître.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

URL_DEMO = "postgresql+psycopg://mycounts:mycounts@localhost:5434/mycounts_demo"


def main() -> int:
    racine = Path(__file__).resolve().parents[1]
    attendue = ScriptDirectory.from_config(Config(str(racine / "alembic.ini"))).get_current_head()
    if attendue is None:
        print("Garde-fou nº 11 : aucune migration déclarée, rien à comparer.")
        return 0

    url = os.environ.get("MYCOUNTS_URL_DEMO", URL_DEMO)
    try:
        with create_engine(url).connect() as connexion:
            if not inspect(connexion).has_table("alembic_version"):
                print("Garde-fou nº 11 : base de démonstration absente, rien à vérifier.")
                return 0
            appliquee = MigrationContext.configure(connexion).get_current_revision()
    except Exception:
        # Injoignable : ni une faute ni une information. Ce contrôle sert celui qui a une
        # démonstration en route, il n'a rien à dire aux autres.
        print("Garde-fou nº 11 : base de démonstration injoignable, rien à vérifier.")
        return 0

    if appliquee != attendue:
        print(
            f"Garde-fou nº 11 : ATTENTION, la démonstration est en révision {appliquee!r} "
            f"alors que le code attend {attendue!r}.\n"
            f"  Son API refusera de démarrer et l'application n'affichera plus rien.\n"
            f"  Lancer « make demo-migrer »."
        )
        return 0

    print("Garde-fou nº 11 : la base de démonstration est à jour.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
