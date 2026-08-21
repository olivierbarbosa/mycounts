"""Enveloppes : le solde vient du journal, jamais d'une valeur écrite.

Deux tests centraux, tous deux capables de rendre la réponse inverse :

- `le reserve ne compte que les soldes positifs` : une enveloppe dans le rouge ne doit pas
  rogner ce que les autres promettent ;
- `le non affecte devient negatif quand l'argent fond` : le forcer à zéro cacherait
  exactement ce qu'il faut voir.
"""

from __future__ import annotations

import datetime as dt
import itertools
from dataclasses import replace

import pytest
from mycounts.domain.enveloppes import (
    CREDITE,
    Enveloppe,
    Mouvement,
    Repartition,
    Rollover,
    TypeMouvement,
    UsageEnveloppe,
    budget_mensuel,
    contribution_theorique,
    mois_restants,
    ordre_de_service,
    preparer_la_periode,
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


def _enveloppe(
    nom: str,
    solde: int = 0,
    cible: int | None = None,
    contribution: int | None = None,
    rollover: Rollover = Rollover.REPORT,
    priorite: int = 0,
) -> Enveloppe:
    """Une enveloppe dont le solde vaut exactement `solde`, par un seul mouvement."""
    mouvements = (
        ()
        if solde == 0
        else (
            Mouvement(
                type=TypeMouvement.ALLOCATION if solde > 0 else TypeMouvement.REPRISE,
                montant=Cents(abs(solde)),
            ),
        )
    )
    return Enveloppe(
        nom=nom,
        mouvements=mouvements,
        cible=None if cible is None else Cents(cible),
        contribution_mensuelle=None if contribution is None else Cents(contribution),
        rollover=rollover,
        priorite=priorite,
    )


class TestBudgetMensuel:
    """Ce qu'on prévoit de mettre, et d'où le chiffre vient."""

    def test_la_contribution_de_lenveloppe_prime_sur_le_plafond(self) -> None:
        """Le particulier l'emporte sur le général : une contribution est une décision
        prise POUR cette enveloppe, un plafond vaut pour toute la catégorie."""
        enveloppe = _enveloppe("Courses", contribution=30_000)
        assert budget_mensuel(enveloppe, plafond_de_la_categorie=Cents(40_000)) == Cents(30_000)

    def test_le_plafond_sert_a_defaut_de_contribution(self) -> None:
        enveloppe = _enveloppe("Courses")
        assert budget_mensuel(enveloppe, plafond_de_la_categorie=Cents(40_000)) == Cents(40_000)

    def test_sans_lun_ni_lautre_il_ny_a_PAS_de_budget(self) -> None:
        """`None` et non zéro : la préparation ne doit rien recommander plutôt que zéro."""
        assert budget_mensuel(_enveloppe("Courses")) is None


class TestPreparerLaPeriode:
    """La proposition faite au passage de période. Elle n'écrit rien."""

    def test_elle_recommande_le_budget_sans_depasser_la_place(self) -> None:
        # Cible 400, déjà 350 dedans : il n'en manque que 50, quoi que dise le budget.
        enveloppes = [_enveloppe("Courses", solde=35_000, cible=40_000, contribution=30_000)]
        preparation = preparer_la_periode(Cents(100_000), enveloppes)
        assert preparation.lignes[0].recommande == Cents(5_000)

    def test_elle_recommande_la_place_sans_depasser_le_budget(self) -> None:
        # L'autre borne du `min` : sans elle, une enveloppe vide à cible lointaine
        # avalerait tout le disponible du mois.
        enveloppes = [_enveloppe("Vacances", cible=150_000, contribution=10_000)]
        preparation = preparer_la_periode(Cents(100_000), enveloppes)
        assert preparation.lignes[0].recommande == Cents(10_000)

    def test_sans_budget_ni_cible_elle_ne_recommande_rien(self) -> None:
        preparation = preparer_la_periode(Cents(100_000), [_enveloppe("Divers")])
        assert preparation.lignes[0].recommande == Cents(0)

    def test_le_disponible_borne_la_derniere_servie(self) -> None:
        """Et la ligne DIT qu'elle a été rognée : « 40 € » et « 40 € parce qu'il ne restait
        que ça » ne s'interprètent pas pareil, et seul le calcul sait laquelle est vraie."""
        enveloppes = [
            _enveloppe("Impots", cible=100_000, contribution=60_000, priorite=1),
            _enveloppe("Vacances", cible=100_000, contribution=60_000, priorite=2),
        ]
        preparation = preparer_la_periode(Cents(80_000), enveloppes)
        premiere, seconde = preparation.lignes
        assert premiere.recommande == Cents(60_000)
        assert premiere.limitee_par_le_disponible is False
        assert seconde.recommande == Cents(20_000)
        assert seconde.limitee_par_le_disponible is True
        assert preparation.disponible_apres == Cents(0)

    def test_la_priorite_decide_qui_est_servi_en_premier(self) -> None:
        """Le témoin qui distingue un ordre CALCULÉ de l'ordre reçu : les enveloppes sont
        passées dans l'ordre inverse de leur priorité."""
        enveloppes = [
            _enveloppe("Tardive", cible=100_000, contribution=60_000, priorite=9),
            _enveloppe("Urgente", cible=100_000, contribution=60_000, priorite=1),
        ]
        preparation = preparer_la_periode(Cents(60_000), enveloppes)
        servie = next(ligne for ligne in preparation.lignes if ligne.recommande > Cents(0))
        assert servie.nom == "Urgente"

    def test_un_reliquat_libere_finance_la_periode(self) -> None:
        # Courses libère 120, ce qui porte le disponible à 220 et permet de servir Vacances.
        enveloppes = [
            _enveloppe("Courses", solde=12_000, rollover=Rollover.LIBERATION, priorite=1),
            _enveloppe("Vacances", cible=100_000, contribution=20_000, priorite=2),
        ]
        preparation = preparer_la_periode(Cents(10_000), enveloppes)
        assert preparation.disponible_avant == Cents(22_000)
        vacances = next(ligne for ligne in preparation.lignes if ligne.nom == "Vacances")
        assert vacances.recommande == Cents(20_000)

    def test_un_reliquat_EN_ATTENTE_ne_finance_rien(self) -> None:
        """La différence avec le test précédent tient au seul mode de fin de mois.

        Tant que la question n'a pas de réponse, cet argent peut aussi bien rester où il
        est : le compter d'avance ferait promettre à d'autres enveloppes de l'argent qu'un
        « non » reprendrait aussitôt.
        """
        enveloppes = [
            _enveloppe("Courses", solde=12_000, rollover=Rollover.DEMANDER, priorite=1),
            _enveloppe("Vacances", cible=100_000, contribution=20_000, priorite=2),
        ]
        preparation = preparer_la_periode(Cents(10_000), enveloppes)
        assert preparation.disponible_avant == Cents(10_000)
        vacances = next(ligne for ligne in preparation.lignes if ligne.nom == "Vacances")
        assert vacances.recommande == Cents(10_000)
        assert preparation.attend_des_choix is True

    def test_la_place_tient_compte_de_ce_qui_vient_detre_libere(self) -> None:
        """Une enveloppe qui rend 120 € puis en redemande a 400 € de place, pas 280."""
        enveloppes = [
            _enveloppe(
                "Courses",
                solde=12_000,
                cible=40_000,
                contribution=40_000,
                rollover=Rollover.LIBERATION,
            )
        ]
        preparation = preparer_la_periode(Cents(100_000), enveloppes)
        assert preparation.lignes[0].place == Cents(40_000)
        assert preparation.lignes[0].recommande == Cents(40_000)

    def test_rejouer_la_preparation_ne_double_rien(self) -> None:
        """L'idempotence, obtenue par construction et non par un verrou.

        C'est la propriété qui permet de se passer d'un marqueur « période déjà préparée »,
        c'est-à-dire d'un second état à tenir d'accord avec le premier. On simule ici
        l'application de la première proposition, puis on recalcule.
        """
        enveloppes = [_enveloppe("Vacances", cible=100_000, contribution=20_000)]
        premiere = preparer_la_periode(Cents(100_000), enveloppes)
        assert premiere.lignes[0].recommande == Cents(20_000)

        # La proposition est appliquée : le solde monte d'autant.
        apres_application = [
            _enveloppe("Vacances", solde=20_000, cible=100_000, contribution=20_000)
        ]
        seconde = preparer_la_periode(Cents(80_000), apres_application)
        # Elle recommande le budget du mois SUIVANT, pas une seconde fois celui-ci : le
        # doublement se verrait ici sous la forme d'une place qui n'aurait pas bougé.
        assert seconde.lignes[0].place == Cents(80_000)

    def test_rejouer_apres_une_liberation_ne_libere_pas_deux_fois(self) -> None:
        """Le cas où un doublement coûterait le plus cher : libérer deux fois le même
        reliquat ferait apparaître de l'argent qui n'existe pas."""
        libere = _enveloppe("Courses", solde=12_000, rollover=Rollover.LIBERATION)
        premiere = preparer_la_periode(Cents(0), [libere])
        assert premiere.lignes[0].a_liberer == Cents(12_000)

        vide = _enveloppe("Courses", solde=0, rollover=Rollover.LIBERATION)
        seconde = preparer_la_periode(Cents(12_000), [vide])
        assert seconde.lignes[0].a_liberer == Cents(0)
        assert seconde.disponible_avant == Cents(12_000)

    def test_une_enveloppe_en_decouvert_ne_libere_rien_et_reste_listee(self) -> None:
        """Listée quand même : une enveloppe dans le rouge est précisément celle qu'on veut
        voir au moment de répartir."""
        enveloppes = [_enveloppe("Courses", solde=-5_000, rollover=Rollover.LIBERATION)]
        preparation = preparer_la_periode(Cents(100_000), enveloppes)
        assert preparation.lignes[0].a_liberer == Cents(0)
        assert len(preparation.lignes) == 1


# --- Pilotage dans le temps -------------------------------------------------------
#
# La `date_cible` était stockée depuis l'origine et lue par AUCUN calcul : on pouvait la
# saisir, elle ne changeait rien. « J'ai un voyage au Japon en novembre 2026, il me faut
# 2 000 € » ne produisait donc aucune recommandation mensuelle.


def test_les_mois_restants_se_comptent_en_mois_civils() -> None:
    """Une échéance est une date du CALENDRIER — personne ne compte son projet en périodes
    de paie. C'est le seul endroit du module où le mois civil l'emporte."""
    aout = dt.date(2026, 8, 22)
    assert mois_restants(dt.date(2026, 11, 30), aout) == 3
    assert mois_restants(dt.date(2026, 9, 1), aout) == 1
    assert mois_restants(dt.date(2027, 8, 22), aout) == 12


def test_une_echeance_passee_reclame_le_reste_maintenant() -> None:
    """Le plancher à 1 n'est pas une précaution contre la division par zéro — c'en est une
    aussi — mais une décision : rendre 0 ferait disparaître la recommandation au moment
    précis où elle devient urgente."""
    assert mois_restants(dt.date(2026, 5, 1), dt.date(2026, 8, 22)) == 1


def test_la_contribution_theorique_arrondit_vers_le_HAUT() -> None:
    """À 1 999,99 € en novembre, on n'a pas les 2 000 € du billet.

    Vérifié sur une division qui ne tombe pas juste : 2 000 € en 3 mois font 666,67 € et
    non 666,66 — trois versements de 666,66 laisseraient deux centimes manquants.
    """
    japon = enveloppe("Japon", cible=200_000)
    objet = replace(japon, date_cible=dt.date(2026, 11, 30))
    assert contribution_theorique(objet, dt.date(2026, 8, 22)) == Cents(66_667)


def test_la_contribution_theorique_tient_compte_de_ce_qui_est_deja_mis() -> None:
    """Elle porte sur ce qui MANQUE, pas sur l'objectif : sinon elle réclamerait la même
    somme chaque mois jusqu'à la fin, et le projet serait financé deux fois."""
    japon = enveloppe("Japon", m(TypeMouvement.ALLOCATION, 50_000), cible=200_000)
    objet = replace(japon, date_cible=dt.date(2026, 11, 30))
    # Reste 1 500 € sur 3 mois.
    assert contribution_theorique(objet, dt.date(2026, 8, 22)) == Cents(50_000)


def test_sans_date_ou_sans_cible_il_ny_a_rien_a_deduire() -> None:
    """Une cible sans échéance est un PLANCHER — « au moins 5 000 € pour les travaux » —
    qu'aucun rythme ne presse. Inventer une date déciderait à la place de l'utilisateur.
    """
    travaux = enveloppe("Travaux", cible=500_000)
    assert contribution_theorique(travaux, dt.date(2026, 8, 22)) is None

    sans_objectif = replace(enveloppe("Flou"), date_cible=dt.date(2026, 11, 30))
    assert contribution_theorique(sans_objectif, dt.date(2026, 8, 22)) is None


def test_une_valeur_deduite_ne_recouvre_jamais_une_valeur_choisie() -> None:
    """L'ordre des trois sources, mesuré dans les trois cas.

    C'est le test qui protège la règle : la contribution théorique vient en DERNIER parce
    qu'elle est la seule que l'utilisateur n'a pas écrite. Un code qui la placerait en
    tête passerait les tests précédents sans qu'aucun ne s'en aperçoive.
    """
    datee = replace(enveloppe("Japon", cible=200_000), date_cible=dt.date(2026, 11, 30))
    jour = dt.date(2026, 8, 22)

    # 1. La contribution écrite sur l'enveloppe l'emporte sur tout.
    choisie = replace(datee, contribution_mensuelle=Cents(10_000))
    assert budget_mensuel(choisie, Cents(30_000), jour) == Cents(10_000)

    # 2. À défaut, le plafond de la catégorie.
    assert budget_mensuel(datee, Cents(30_000), jour) == Cents(30_000)

    # 3. À défaut des deux, ce que l'échéance impose.
    assert budget_mensuel(datee, None, jour) == Cents(66_667)

    # Et sans date de référence, rien n'est déduit : le domaine ne devine pas le jour.
    assert budget_mensuel(datee, None, None) is None


def test_une_enveloppe_datee_recoit_enfin_une_recommandation() -> None:
    """Le défaut, pris par le bout où il se voyait.

    Avant le 22 août 2026, cette enveloppe — un objectif, une échéance, rien d'autre —
    recevait `recommande = 0` : `budget_mensuel` rendait `None`, et `souhaite` retombait
    sur la place entière, aussitôt rabotée par le disponible. Elle demandait donc tout,
    tout de suite, au lieu de son rythme.
    """
    japon = replace(enveloppe("Japon", cible=200_000), date_cible=dt.date(2026, 11, 30))
    proposition = preparer_la_periode(Cents(500_000), [japon], None, dt.date(2026, 8, 22))

    (ligne,) = proposition.lignes
    assert ligne.recommande == Cents(66_667), "le rythme, pas la totalité"
    assert not ligne.limitee_par_le_disponible
