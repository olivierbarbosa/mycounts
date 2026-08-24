"""Remet le foyer de démonstration dans un état connu avant la suite de bout en bout.

État garanti à la sortie : **un seul compte courant, dans l'espace PERSONNEL, aucune
opération, aucune récurrence, aucun second facteur** — et « un seul » est vérifié par
`tests/integration/test_reinitialisation.py`, parce que la version précédente de ce fichier
promettait déjà cet état sans le tenir. Sans cela, chaque exécution laisse ses données
derrière elle et les tests mesurent un état cumulé — un locator qui attend une ligne en
trouve trois.

L'espace personnel, parce que c'est lui que l'application ouvre par défaut : le compte
était créé dans le foyer historique de l'identité, et la suite entière tombait sur l'écran
d'amorçage « Votre premier compte » — un état que ce script promettait justement d'éviter.
Mesuré le 24 août 2026, à la première exécution des tests de bout en bout sur le modèle
des espaces multiples.

Le second facteur est retiré parce qu'il est OBLIGATOIRE : sans lui, les routes financières
répondent 403 et aucun test ne voit l'application. Or Playwright ne connaît pas le secret
TOTP d'une exécution précédente. La suite repart donc d'un compte À ENRÔLER, et c'est
`frontend/e2e/preparation.ts` qui refait l'enrôlement par l'API — il détient le secret le
temps d'un code, puis écrit la session ouverte pour tous les tests.

Le compte est conservé (ou recréé) et non supprimé : sinon toute la suite retomberait sur
l'écran d'amorçage, qui n'a pas de barre de navigation. Conséquence assumée et écrite
ici : **l'écran d'amorçage n'est pas couvert par les tests de bout en bout**. Il l'est par
les tests d'intégration de l'API (solde d'ouverture) et par une vérification manuelle au
navigateur.

**Garde-fou** : ce script refuse de s'exécuter si l'adresse visée ne correspond pas au
compte de démonstration attendu. Une commande qui vide des tables doit être incapable de
viser autre chose que ce pour quoi elle a été écrite.
"""

from __future__ import annotations

import os
import sys

from mycounts.domain.securite import normaliser_courriel
from mycounts.models.auth import SessionWeb
from mycounts.models.budget import Compte, Operation, Recurrence
from mycounts.repository import auth as depot
from mycounts.repository import budget as depot_budget
from mycounts.repository import espaces as depot_espaces
from mycounts.repository import identite as depot_identite
from mycounts.repository.base import Principal, fabrique_de_sessions
from sqlalchemy import delete, or_, select

SUFFIXE_AUTORISE = "@mycounts-demo.fr"


def main() -> int:
    courriel_brut = os.environ.get("MYCOUNTS_COURRIEL_TEST", "")
    if not courriel_brut:
        print("MYCOUNTS_COURRIEL_TEST est requis.", file=sys.stderr)
        return 1

    courriel = normaliser_courriel(courriel_brut)
    if not courriel.endswith(SUFFIXE_AUTORISE):
        print(
            f"Refus : « {courriel} » n'est pas un compte de démonstration "
            f"(suffixe attendu : {SUFFIXE_AUTORISE}).",
            file=sys.stderr,
        )
        return 1

    session = fabrique_de_sessions()()
    try:
        utilisateur = depot.utilisateur_par_courriel(session, courriel)
        if utilisateur is None:
            print(f"Aucun compte {courriel} : rien à réinitialiser.")
            return 0

        # Tous les espaces de l'identité, foyer historique compris : un compte laissé dans
        # un espace que la suite ne regarde pas resterait invisible, jusqu'au test qui y
        # bascule et en trouve un de trop.
        perimetres = [espace.id for espace, _ in depot_espaces.espaces_de(session, utilisateur.id)]
        perimetres.append(utilisateur.foyer_id)
        comptes = list(
            session.execute(
                select(Compte.id).where(
                    or_(Compte.espace_id.in_(perimetres), Compte.foyer_id.in_(perimetres))
                )
            ).scalars()
        )
        if comptes:
            # Les opérations d'abord : elles référencent les récurrences. Sans les
            # récurrences, une exécution suivante les rematérialiserait aussitôt et les
            # tests repartiraient d'un état différent du précédent.
            session.execute(delete(Operation).where(Operation.compte_id.in_(comptes)))
            session.execute(delete(Recurrence).where(Recurrence.compte_id.in_(comptes)))
            # Puis les comptes eux-mêmes. Cette ligne manquait : le script annonçait « un
            # compte » et en laissait autant que les exécutions précédentes en avaient
            # créé. Tant qu'aucun test n'en créait, l'écart ne se voyait pas — les tests
            # d'épargne, eux, en créent un par cas, et la page en affichait quatre.
            session.execute(delete(Compte).where(Compte.id.in_(comptes)))
        principal = depot_espaces.principal_pour(
            session, utilisateur_id=utilisateur.id, espace_id=None
        )
        if principal is None:
            # Identité antérieure au lot espaces, sans espace personnel : son foyer
            # historique reste son seul périmètre.
            principal = Principal(utilisateur_id=utilisateur.id, foyer_id=utilisateur.foyer_id)
        depot_budget.creer_compte(session, principal, nom="Compte courant")
        # Le facteur, ses codes de secours, les appareils fiables ET les sessions : une
        # session « MFA satisfait » d'une exécution précédente survivrait sinon au retrait
        # du secret, et un cookie périmé pourrait encore ouvrir les finances.
        depot.desactiver_le_second_facteur(session, utilisateur)
        depot_identite.revoquer_tous_les_appareils(session, utilisateur.id)
        session.execute(delete(SessionWeb).where(SessionWeb.utilisateur_id == utilisateur.id))
        session.commit()
        print(
            "Foyer de démonstration prêt : un compte dans l'espace personnel, aucune "
            "opération, aucune récurrence, aucun second facteur."
        )
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
