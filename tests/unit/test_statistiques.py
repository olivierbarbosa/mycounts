"""Statistiques et constats.

Deux exigences guident ces tests :

- la répartition doit rester JUSTE quand les catégories se ressemblent — un tri instable
  ou un total mal rapporté ne se voit pas à l'œil, il se voit ici ;
- un constat ne doit se déclencher que quand il apprend quelque chose. Chaque seuil a donc
  son test juste en dessous et juste au-dessus : un seuil qu'on ne franchit jamais dans les
  deux sens est un seuil qu'on n'a pas vérifié.
"""

from __future__ import annotations

import pytest
from mycounts.domain.montants import Cents
from mycounts.domain.statistiques import (
    Constat,
    DepenseCalcul,
    Motif,
    PosteDeDepense,
    constats,
    normaliser_libelle,
    repartition,
)


def _depense(libelle: str, montant: int, categorie: str | None = None) -> DepenseCalcul:
    return DepenseCalcul(libelle=libelle, montant=Cents(montant), categorie=categorie)


class TestNormaliserLibelle:
    @pytest.mark.parametrize(
        ("saisi", "attendu"),
        [
            ("Carrefour City", "carrefour city"),
            ("CARREFOUR CITY", "carrefour city"),
            ("Carrefour-City", "carrefour city"),
            ("  Carrefour   City  ", "carrefour city"),
            ("Café Crème", "cafe creme"),
            ("MONOPRIX_92", "monoprix 92"),
        ],
    )
    def test_les_ecritures_dun_meme_endroit_se_rejoignent(self, saisi: str, attendu: str) -> None:
        assert normaliser_libelle(saisi) == attendu

    def test_deux_endroits_DIFFERENTS_restent_distincts(self) -> None:
        """Une correspondance approximative ferait des regroupements que l'utilisateur n'a
        pas demandés et ne pourrait pas défaire."""
        assert normaliser_libelle("Carrefour") != normaliser_libelle("Carrefour City")


class TestRepartition:
    def test_les_postes_sont_tries_du_plus_gros_au_plus_petit(self) -> None:
        postes = repartition(
            [_depense("a", 1_000, "Courses"), _depense("b", 5_000, "Loyer")]
        )
        assert [p.categorie for p in postes] == ["Loyer", "Courses"]

    def test_a_egalite_le_nom_tranche(self) -> None:
        """Sans quoi l'ordre viendrait du dictionnaire, donc des lignes en base : un
        classement qu'on ne peut pas prévoir se relit différemment à chaque ouverture."""
        postes = repartition([_depense("a", 1_000, "Zorro"), _depense("b", 1_000, "Alpha")])
        assert [p.categorie for p in postes] == ["Alpha", "Zorro"]

    def test_la_part_se_rapporte_au_TOTAL(self) -> None:
        postes = repartition(
            [_depense("a", 7_500, "Loyer"), _depense("b", 2_500, "Courses")]
        )
        assert {p.categorie: p.part for p in postes} == {"Loyer": 75, "Courses": 25}

    def test_sans_categorie_est_un_poste_comme_les_autres(self) -> None:
        """Jamais masqué : c'est souvent la plus grosse ligne, et la cacher donnerait une
        répartition fausse."""
        postes = repartition([_depense("a", 9_000), _depense("b", 1_000, "Courses")])
        assert postes[0].categorie is None
        assert postes[0].part == 90

    def test_la_variation_compare_a_la_periode_precedente(self) -> None:
        postes = repartition(
            [_depense("a", 12_000, "Courses")], [_depense("a", 10_000, "Courses")]
        )
        assert postes[0].variation == 20

    def test_un_poste_NOUVEAU_na_pas_de_variation(self) -> None:
        """« Nouveau » et « +∞ % » ne veulent pas dire la même chose, et le second ferait
        passer un fait clair pour une aberration."""
        postes = repartition([_depense("a", 5_000, "Ski")], [_depense("b", 1_000, "Courses")])
        ski = next(p for p in postes if p.categorie == "Ski")
        assert ski.montant_precedent is None
        assert ski.variation is None

    def test_aucune_depense_ne_produit_aucune_division_par_zero(self) -> None:
        assert repartition([]) == ()


class TestGoutteAGoutte:
    """Plusieurs petites dépenses au même endroit, dont le total surprend."""

    def test_trois_passages_au_meme_endroit_sont_signales(self) -> None:
        depenses = [_depense("Sushi Shop", 2_000) for _ in range(3)]
        (constat,) = constats(depenses)
        assert constat.motif is Motif.GOUTTE_A_GOUTTE
        assert constat.montant == Cents(6_000)
        assert constat.detail == 3

    def test_deux_passages_ne_suffisent_PAS(self) -> None:
        """Deux est une coïncidence. Le test qui borne le seuil par en dessous."""
        assert constats([_depense("Sushi Shop", 5_000) for _ in range(2)]) == ()

    def test_un_petit_total_ne_fait_pas_un_constat(self) -> None:
        """Dix passages à 1 € font 10 € : exact, et sans intérêt."""
        assert constats([_depense("Boulangerie", 100) for _ in range(10)]) == ()

    def test_les_ecritures_differentes_du_meme_endroit_se_regroupent(self) -> None:
        depenses = [
            _depense("Uber Eats", 2_000),
            _depense("UBER EATS", 2_000),
            _depense("uber-eats", 2_000),
        ]
        (constat,) = constats(depenses)
        assert constat.detail == 3
        # Le libellé ORIGINAL, celui que l'utilisateur reconnaîtra dans sa liste.
        assert constat.sujet == "Uber Eats"

    def test_des_endroits_differents_ne_se_melangent_pas(self) -> None:
        depenses = [_depense("Boulangerie", 3_000), _depense("Boucherie", 3_000)]
        assert constats(depenses) == ()


class TestPosteEnHausse:
    def test_une_hausse_franche_est_signalee(self) -> None:
        postes = [
            PosteDeDepense(
                categorie="Sorties",
                montant=Cents(10_000),
                part=50,
                montant_precedent=Cents(5_000),
            )
        ]
        (constat,) = constats([], postes)
        assert constat.motif is Motif.POSTE_EN_HAUSSE
        assert constat.detail == 100

    def test_une_hausse_sur_de_petits_montants_est_TUE(self) -> None:
        """Passer de 4 € à 6 € fait un « +50 % » parfaitement exact et parfaitement inutile."""
        postes = [
            PosteDeDepense(
                categorie="Timbres", montant=Cents(600), part=1, montant_precedent=Cents(400)
            )
        ]
        assert constats([], postes) == ()

    def test_une_hausse_faible_nest_pas_signalee(self) -> None:
        postes = [
            PosteDeDepense(
                categorie="Courses",
                montant=Cents(10_500),
                part=50,
                montant_precedent=Cents(10_000),
            )
        ]
        assert constats([], postes) == ()

    def test_une_BAISSE_nest_jamais_signalee(self) -> None:
        """Le témoin qui distingue « hausse » d'« écart » : une valeur absolue mal placée
        ferait féliciter l'utilisateur d'avoir dépensé moins, sous forme d'alerte."""
        postes = [
            PosteDeDepense(
                categorie="Courses",
                montant=Cents(5_000),
                part=50,
                montant_precedent=Cents(20_000),
            )
        ]
        assert constats([], postes) == ()


class TestAbonnements:
    def test_le_cout_annuel_est_signale(self) -> None:
        (constat,) = constats([], [], cout_annuel_des_abonnements=Cents(48_000))
        assert constat.motif is Motif.ABONNEMENTS
        assert constat.montant == Cents(48_000)

    def test_aucun_abonnement_ne_produit_aucun_constat(self) -> None:
        assert constats([], [], cout_annuel_des_abonnements=Cents(0)) == ()
        assert constats([], [], cout_annuel_des_abonnements=None) == ()


class TestOrdreDesConstats:
    def test_le_plus_gros_montant_passe_devant(self) -> None:
        """Ce qu'on lit en premier doit être ce qui pèse le plus."""
        resultats: tuple[Constat, ...] = constats(
            [_depense("Cafe", 2_000) for _ in range(3)],
            [],
            cout_annuel_des_abonnements=Cents(48_000),
        )
        assert [c.motif for c in resultats] == [Motif.ABONNEMENTS, Motif.GOUTTE_A_GOUTTE]
