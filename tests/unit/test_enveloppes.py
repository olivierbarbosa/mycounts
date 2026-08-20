"""Enveloppes : le solde vient du journal, jamais d'une valeur écrite.

Deux tests centraux, tous deux capables de rendre la réponse inverse :

- `le reserve ne compte que les soldes positifs` : une enveloppe dans le rouge ne doit pas
  rogner ce que les autres promettent ;
- `le non affecte devient negatif quand l'argent fond` : le forcer à zéro cacherait
  exactement ce qu'il faut voir.
"""

from __future__ import annotations

import itertools

import pytest
from mycounts.domain.enveloppes import (
    CREDITE,
    Enveloppe,
    Mouvement,
    Repartition,
    Rollover,
    TypeMouvement,
    UsageEnveloppe,
    ordre_de_service,
    reliquat_au_changement_de_periode,
    repartir,
    solde_de,
)
from mycounts.domain.montants import Cents


def m(type_: TypeMouvement, montant: int) -> Mouvement:
    return Mouvement(type=type_, montant=Cents(montant))


def enveloppe(nom: str, *mouvements: Mouvement, cible: int | None = None) -> Enveloppe:
    return Enveloppe(
        nom=nom, mouvements=mouvements, cible=None if cible is None else Cents(cible)
    )


def test_chaque_type_a_un_sens_declare() -> None:
    """Ajouter un type sans décider de son sens doit faire échouer ce test.

    Sans lui, un type nouveau tomberait par défaut du côté « débite » — silencieusement,
    et sur de l'argent.
    """
    for type_ in TypeMouvement:
        credite = type_ in CREDITE
        assert isinstance(credite, bool)
    # Les types crédités sont ceux qu'on a explicitement listés, ni plus ni moins.
    assert {
        TypeMouvement.ALLOCATION,
        TypeMouvement.REMBOURSEMENT,
        TypeMouvement.AJUSTEMENT_PLUS,
    } == CREDITE


def test_le_solde_se_recalcule_depuis_le_journal() -> None:
    solde = solde_de(
        [
            m(TypeMouvement.ALLOCATION, 90_000),
            m(TypeMouvement.DEPENSE, 12_000),
            m(TypeMouvement.REMBOURSEMENT, 2_000),
        ]
    )
    assert solde == 80_000


def test_le_montant_est_toujours_positif_le_sens_vient_du_type() -> None:
    """Deux mouvements de MÊME montant et de sens opposés s'annulent.

    C'est ce qui rend un montant signé inutile — et dangereux : une allocation négative
    serait une reprise déguisée, invisible dans un journal filtré par type.
    """
    assert solde_de([m(TypeMouvement.ALLOCATION, 5_000), m(TypeMouvement.REPRISE, 5_000)]) == 0


def test_une_enveloppe_peut_passer_en_negatif() -> None:
    """Une dépense réelle ne se bloque pas parce que l'enveloppe est mal financée."""
    vacances = enveloppe(
        "Vacances", m(TypeMouvement.ALLOCATION, 10_000), m(TypeMouvement.DEPENSE, 13_000)
    )
    assert vacances.solde == -3_000


def test_le_reserve_ne_compte_que_les_soldes_positifs() -> None:
    """Une enveloppe dans le rouge ne rogne pas ce que les autres promettent.

    Le témoin oppose deux répartitions dont seule la seconde a une enveloppe négative :
    le réservé doit être IDENTIQUE, alors qu'une somme naïve le ferait baisser de 5 000.
    """
    impots = enveloppe("Impôts", m(TypeMouvement.ALLOCATION, 90_000))
    vacances_rouge = enveloppe("Vacances", m(TypeMouvement.DEPENSE, 5_000))

    sans = repartir(Cents(300_000), [impots])
    avec = repartir(Cents(300_000), [impots, vacances_rouge])

    assert sans.reserve == 90_000
    assert avec.reserve == 90_000, "une enveloppe négative ne diminue pas le réservé"
    assert avec.non_affecte == 210_000


def test_le_non_affecte_devient_negatif_quand_largent_fond() -> None:
    """Le témoin : mêmes enveloppes, seule l'épargne change."""
    enveloppes = [
        enveloppe("Impôts", m(TypeMouvement.ALLOCATION, 90_000)),
        enveloppe("Vacances", m(TypeMouvement.ALLOCATION, 80_000)),
    ]

    confortable = repartir(Cents(300_000), enveloppes)
    entame = repartir(Cents(120_000), enveloppes)

    assert confortable.non_affecte == 130_000
    assert confortable.decouvert is False
    assert entame.non_affecte == -50_000, "borner à zéro cacherait que les promesses sautent"
    assert entame.decouvert is True


def test_la_part_ne_depend_pas_des_voisines() -> None:
    impots = enveloppe("Impôts", m(TypeMouvement.ALLOCATION, 90_000))
    seule = repartir(Cents(300_000), [impots])
    accompagnee = repartir(
        Cents(300_000), [impots, enveloppe("Vacances", m(TypeMouvement.ALLOCATION, 80_000))]
    )

    assert seule.part(impots) == 30
    assert accompagnee.part(impots) == 30


def test_une_epargne_nulle_ne_divise_pas_par_zero() -> None:
    vide = repartir(Cents(0), [enveloppe("Impôts", m(TypeMouvement.ALLOCATION, 90_000))])
    assert vide.part(vide.enveloppes[0]) == 0
    assert vide.decouvert is True


def test_la_place_restante_vaut_none_sans_cible() -> None:
    """`None` et non zéro : sans cible, la préparation mensuelle ne doit RIEN recommander.

    Recommander zéro serait déjà une décision prise à la place de l'utilisateur.
    """
    sans_cible = enveloppe("Divers", m(TypeMouvement.ALLOCATION, 10_000))
    avec_cible = enveloppe("Ski", m(TypeMouvement.ALLOCATION, 10_000), cible=30_000)

    assert sans_cible.place is None
    assert avec_cible.place == 20_000


def test_la_place_ne_devient_jamais_negative() -> None:
    """Dépasser sa cible ne crée pas une place négative, qui se lirait comme une dette."""
    depassee = enveloppe("Ski", m(TypeMouvement.ALLOCATION, 40_000), cible=30_000)
    assert depassee.place == 0


def test_aucune_combinaison_de_types_ne_fait_planter_le_calcul() -> None:
    """Balayage du produit cartésien : deux mouvements de tous types possibles.

    Un test à trois exemples choisis ne prouve rien d'un calcul qui dépend d'un ensemble
    de types — il prouve que ces trois-là marchent.
    """
    for a, b in itertools.product(TypeMouvement, repeat=2):
        attendu = (100 if a in CREDITE else -100) + (200 if b in CREDITE else -200)
        assert solde_de([m(a, 100), m(b, 200)]) == attendu


def test_une_repartition_sans_enveloppe_laisse_tout_disponible() -> None:
    vide = Repartition(epargne_totale=Cents(50_000), enveloppes=())
    assert vide.reserve == 0
    assert vide.non_affecte == 50_000


class TestReliquatAuChangementDePeriode:
    """Ce que le passage de période fait au solde, avant qu'aucune écriture n'ait lieu."""

    @staticmethod
    def _avec(solde: int, rollover: Rollover) -> Enveloppe:
        """Une enveloppe dont le solde vaut exactement `solde`, quel qu'en soit le signe."""
        type_ = TypeMouvement.ALLOCATION if solde >= 0 else TypeMouvement.REPRISE
        return Enveloppe(
            nom="Courses",
            mouvements=(Mouvement(type=type_, montant=Cents(abs(solde))),),
            rollover=rollover,
        )

    def test_le_report_ne_libere_rien(self) -> None:
        reliquat = reliquat_au_changement_de_periode(self._avec(12_000, Rollover.REPORT))
        assert reliquat.a_liberer == Cents(0)
        assert reliquat.demande_un_choix is False

    def test_la_liberation_rend_tout_le_solde(self) -> None:
        reliquat = reliquat_au_changement_de_periode(self._avec(12_000, Rollover.LIBERATION))
        assert reliquat.a_liberer == Cents(12_000)
        assert reliquat.demande_un_choix is False

    def test_demander_propose_le_solde_mais_attend_un_choix(self) -> None:
        """La différence avec la libération n'est PAS le montant, c'est le drapeau.

        Une implémentation qui traiterait « demander » comme « libérer » proposerait le bon
        chiffre et l'écrirait sans rien demander : le test doit donc porter sur les deux.
        """
        reliquat = reliquat_au_changement_de_periode(self._avec(12_000, Rollover.DEMANDER))
        assert reliquat.a_liberer == Cents(12_000)
        assert reliquat.demande_un_choix is True

    @pytest.mark.parametrize("rollover", list(Rollover))
    def test_un_solde_negatif_ne_libere_jamais_rien(self, rollover: Rollover) -> None:
        """Quel que soit le mode. Libérer un découvert ferait apparaître de l'argent.

        Paramétré sur TOUS les modes : un mode ajouté plus tard sans traiter ce cas fera
        échouer ce test au lieu de laisser passer un découvert converti en disponible.
        """
        reliquat = reliquat_au_changement_de_periode(self._avec(-5_000, rollover))
        assert reliquat.a_liberer == Cents(0)
        assert reliquat.demande_un_choix is False

    @pytest.mark.parametrize("rollover", list(Rollover))
    def test_un_solde_nul_ne_libere_jamais_rien(self, rollover: Rollover) -> None:
        reliquat = reliquat_au_changement_de_periode(
            Enveloppe(nom="Vide", rollover=rollover)
        )
        assert reliquat.a_liberer == Cents(0)
        assert reliquat.demande_un_choix is False

    def test_chaque_mode_est_traite(self) -> None:
        """Un mode ajouté à l'énumération sans être traité fait échouer ce test.

        `match` sans branche par défaut lèverait déjà, mais seulement si quelqu'un exécute
        ce chemin. Ici la boucle le garantit.
        """
        for rollover in Rollover:
            reliquat = reliquat_au_changement_de_periode(self._avec(1_000, rollover))
            assert isinstance(reliquat.a_liberer, int)


class TestOrdreDeService:
    """Qui est servi en premier quand le disponible ne suffit pas."""

    def test_la_plus_petite_priorite_passe_devant(self) -> None:
        tard = Enveloppe(nom="Vacances", priorite=5)
        tot = Enveloppe(nom="Impots", priorite=1)
        assert ordre_de_service([tard, tot]) == (tot, tard)

    def test_a_egalite_le_nom_tranche(self) -> None:
        """Et non l'ordre d'insertion en base, qu'aucun utilisateur ne peut prévoir.

        Le test présente les deux enveloppes dans l'ordre INVERSE de celui attendu : une
        implémentation qui se contenterait de préserver l'ordre reçu échouerait ici.
        """
        zorro = Enveloppe(nom="Zorro", priorite=0)
        alpha = Enveloppe(nom="Alpha", priorite=0)
        assert ordre_de_service([zorro, alpha]) == (alpha, zorro)

    def test_la_priorite_prime_sur_le_nom(self) -> None:
        alpha = Enveloppe(nom="Alpha", priorite=9)
        zorro = Enveloppe(nom="Zorro", priorite=1)
        assert ordre_de_service([alpha, zorro]) == (zorro, alpha)


class TestValeursParDefaut:
    """Ce qu'une enveloppe vaut quand on ne règle rien."""

    def test_le_defaut_est_le_report_et_le_fonctionnement(self) -> None:
        """Le report parce qu'il est NON DESTRUCTIF : rien ne disparaît sans geste."""
        enveloppe = Enveloppe(nom="Neuve")
        assert enveloppe.rollover is Rollover.REPORT
        assert enveloppe.usage is UsageEnveloppe.FONCTIONNEMENT
        assert enveloppe.priorite == 0
        assert enveloppe.contribution_mensuelle is None
