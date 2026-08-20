"""Catégorisation assistée — la porte de sortie du projet.

**Aucun test de ce fichier n'appelle le réseau.** Ce qui est vérifié n'est pas la qualité
des suggestions d'un modèle, qui n'est ni reproductible ni de notre ressort, mais les
garanties que ce module doit tenir quoi qu'il arrive :

- il se tait sans clé, et l'import continue ;
- il n'accepte que ce qu'il peut vérifier ;
- il ne fait jamais échouer son appelant.

Ces trois propriétés sont ce qui permet de brancher un service tiers sur un chemin qui
touche à de l'argent.
"""

from __future__ import annotations

import pytest
from mycounts.services.categorisation_ia import _lire_la_reponse, proposer_des_categories

CATEGORIES = ["Courses", "Transport", "Santé"]


class TestSansCle:
    def test_sans_cle_le_module_se_tait(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Et l'import fonctionne exactement comme avant. Une catégorisation est un
        confort ; en faire une dépendance rendrait l'import tributaire d'un tiers pour une
        tâche qu'il sait faire sans lui."""
        monkeypatch.delenv("MYCOUNTS_CLE_OPENROUTER", raising=False)
        assert proposer_des_categories(["INTERMARCHE"], CATEGORIES) == {}

    def test_une_cle_vide_vaut_pas_de_cle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Le cas d'un `.env` où la variable existe mais n'a pas été remplie — sans quoi
        on partirait appeler un service avec un jeton vide."""
        monkeypatch.setenv("MYCOUNTS_CLE_OPENROUTER", "   ")
        assert proposer_des_categories(["INTERMARCHE"], CATEGORIES) == {}

    def test_sans_libelle_ni_categorie_aucun_appel(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rien à classer, ou nulle part où le ranger : appeler serait payer pour rien."""
        monkeypatch.setenv("MYCOUNTS_CLE_OPENROUTER", "sk-factice")
        assert proposer_des_categories([], CATEGORIES) == {}
        assert proposer_des_categories(["INTERMARCHE"], []) == {}
        assert proposer_des_categories(["   "], CATEGORIES) == {}


class TestLectureDeLaReponse:
    """Ce qu'on accepte d'un modèle — c'est-à-dire uniquement ce qu'on peut vérifier."""

    def test_une_reponse_propre_est_lue(self) -> None:
        contenu = '{"INTERMARCHE": "Courses"}'
        assert _lire_la_reponse(contenu, ["INTERMARCHE"], CATEGORIES) == {
            "INTERMARCHE": "Courses"
        }

    def test_le_json_est_extrait_dun_texte_qui_lentoure(self) -> None:
        """Un modèle encadre volontiers son JSON de balises de code ou d'une phrase.
        L'exiger parfaitement propre ferait perdre des réponses utilisables."""
        contenu = 'Voici le résultat :\n```json\n{"TOTAL": "Transport"}\n```\nVoilà.'
        assert _lire_la_reponse(contenu, ["TOTAL"], CATEGORIES) == {"TOTAL": "Transport"}

    def test_une_categorie_INVENTEE_est_ecartee(self) -> None:
        """Un nom qui ne correspond à rien dans le foyer ne doit jamais remonter : il
        serait proposé à l'écran comme s'il existait."""
        contenu = '{"INTERMARCHE": "Alimentation biologique"}'
        assert _lire_la_reponse(contenu, ["INTERMARCHE"], CATEGORIES) == {}

    def test_un_libelle_QUON_NA_PAS_ENVOYE_est_ecarte(self) -> None:
        """Le témoin qui compte : sans lui, un modèle qui inventerait des lignes ferait
        apparaître des suggestions pour des opérations inexistantes."""
        contenu = '{"UNE LIGNE INVENTEE": "Courses"}'
        assert _lire_la_reponse(contenu, ["INTERMARCHE"], CATEGORIES) == {}

    def test_un_null_ne_range_rien(self) -> None:
        """« Je ne sais pas » est une réponse acceptable, et même souhaitable."""
        contenu = '{"ZZQX 447": null}'
        assert _lire_la_reponse(contenu, ["ZZQX 447"], CATEGORIES) == {}

    @pytest.mark.parametrize(
        "contenu",
        ["", "je ne sais pas", "[]", "{cassé", '{"a": }', "null"],
    )
    def test_une_reponse_illisible_ne_fait_pas_echouer(self, contenu: str) -> None:
        """Aucune de ces formes ne doit lever : l'appelant est un import qui doit aboutir
        même quand le service répond n'importe quoi."""
        assert _lire_la_reponse(contenu, ["INTERMARCHE"], CATEGORIES) == {}
