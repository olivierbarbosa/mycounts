"""Les courriels d'identité restent fermés, neutres et sans donnée financière."""

from __future__ import annotations

import pytest
from mycounts.services.courriels import rendre


@pytest.mark.parametrize(
    ("modele", "duree"),
    [
        ("verification_courriel", "24 heures"),
        ("reinitialisation_mot_de_passe", "30 minutes"),
        ("invitation_espace", "sept jours"),
    ],
)
def test_les_liens_identite_annoncent_leur_duree(modele: str, duree: str) -> None:
    courriel = rendre(
        modele,
        {"nom": "Olivier", "lien": "https://mycounts.app/?preuve=opaque"},
        support="support@mycounts.app",
    )

    assert duree in courriel.texte
    assert "https://mycounts.app/?preuve=opaque" in courriel.texte
    assert "support@mycounts.app" in courriel.texte
    assert "€" not in courriel.texte


def test_le_html_echappe_toutes_les_donnees_variables() -> None:
    courriel = rendre(
        "verification_courriel",
        {
            "nom": '<img src=x onerror="alert(1)">',
            "lien": 'https://mycounts.app/?x="><script>alert(1)</script>',
        },
        support="support+<privé>@mycounts.app",
    )

    assert "<script>" not in courriel.html
    assert "<img src=x" not in courriel.html
    assert "&lt;script&gt;" in courriel.html
    assert "&lt;privé&gt;" in courriel.html


def test_un_modele_non_prevus_ne_peut_pas_devenir_un_courriel_arbitraire() -> None:
    with pytest.raises(ValueError, match="inconnu"):
        rendre(
            "sujet-fourni-par-un-client",
            {"nom": "A", "lien": "https://example.test"},
            support="support@mycounts.app",
        )
