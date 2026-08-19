"""Tests des agrégats.

Le test central du projet est `test_temoin_confirmer_ne_change_pas_le_projete` : c'est
la mesure qui peut rendre la réponse inverse. Si confirmer une échéance déplaçait le
solde projeté, il y aurait double comptage — et l'écart ne se découvrirait que des
semaines plus tard, par un désaccord avec la banque.
"""

from __future__ import annotations

import datetime as dt
import itertools

import pytest
from mycounts.domain.agregats import (
    CONTRIBUTIONS,
    SIGNE_RETENU,
    Agregat,
    Borne,
    EtatOperation,
    OperationCalcul,
    calculer,
    contribue,
)
from mycounts.domain.montants import Cents

AUJOURD_HUI = dt.date(2026, 8, 19)
FIN_FENETRE = dt.date(2026, 9, 26)


def operation(
    montant: int, jour: dt.date = AUJOURD_HUI, etat: EtatOperation = EtatOperation.CONFIRMEE
) -> OperationCalcul:
    return OperationCalcul(montant=Cents(montant), date_operation=jour, etat=etat)


def somme(agregat: Agregat, operations: list[OperationCalcul]) -> int:
    return calculer(agregat, operations, aujourd_hui=AUJOURD_HUI, fin_de_fenetre=FIN_FENETRE)


def test_la_table_est_exhaustive() -> None:
    """Toute combinaison état × agrégat doit être déclarée explicitement.

    Ajouter un état ou un agrégat sans compléter la table fait échouer ce test. Sans lui,
    l'oubli produirait un total silencieusement faux — et rien, dans l'interface, ne
    permettrait de le voir.
    """
    for agregat, etat in itertools.product(Agregat, EtatOperation):
        assert etat in CONTRIBUTIONS[agregat], (
            f"« {etat} » n'est pas déclaré pour l'agrégat « {agregat} » : "
            "dire explicitement s'il contribue, ou pas."
        )


def test_aucun_agregat_ne_manque_dans_la_table() -> None:
    assert set(CONTRIBUTIONS) == set(Agregat)
    assert set(SIGNE_RETENU) == set(Agregat), "un agrégat sans signe retenu sommerait tout"


def test_les_depenses_ignorent_les_revenus() -> None:
    """Un agrégat nommé « dépenses » ne doit pas additionner les paies.

    Première version : il renvoyait +233 410 au lieu de −16 590 sur une période contenant
    un salaire. Un plafond alimenté par ce chiffre n'aurait jamais alerté.
    """
    operations = [operation(250000), operation(-4590), operation(-12000)]
    assert somme(Agregat.DEPENSES_DE_PERIODE, operations) == -16590
    assert somme(Agregat.SOLDE_REEL, operations) == 233410


def test_temoin_le_filtre_de_signe_est_actif() -> None:
    """Contrôle inverse : sur des données sans revenu, dépenses et solde coïncident.

    Sans lui, un filtre qui exclurait TOUT passerait le test précédent.
    """
    sorties_seules = [operation(-4590), operation(-12000)]
    assert somme(Agregat.DEPENSES_DE_PERIODE, sorties_seules) == somme(
        Agregat.SOLDE_REEL, sorties_seules
    )


def test_une_combinaison_inconnue_leve() -> None:
    """Le plantage est voulu : mieux vaut une erreur qu'un total faux."""
    with pytest.raises(KeyError):
        contribue(Agregat.SOLDE_REEL, "etat_inexistant")  # type: ignore[arg-type]


# --- Le témoin central -----------------------------------------------------------


def test_temoin_confirmer_ne_change_pas_le_projete() -> None:
    """Confirmer une échéance : réel et à-confirmer bougent en SENS OPPOSÉS, projeté fixe.

    Trois grandeurs mesurées, dont deux qui doivent diverger. Si les trois bougeaient
    dans le même sens, ce serait la sonde qui est fausse ; si le projeté bougeait, il y
    aurait double comptage.
    """
    avant = [operation(-4590, etat=EtatOperation.A_CONFIRMER), operation(200000)]
    apres = [operation(-4590, etat=EtatOperation.CONFIRMEE), operation(200000)]

    reel_avant = somme(Agregat.SOLDE_REEL, avant)
    reel_apres = somme(Agregat.SOLDE_REEL, apres)
    a_confirmer_avant = somme(Agregat.SOLDE_A_CONFIRMER, avant)
    a_confirmer_apres = somme(Agregat.SOLDE_A_CONFIRMER, apres)
    projete_avant = somme(Agregat.SOLDE_PROJETE, avant)
    projete_apres = somme(Agregat.SOLDE_PROJETE, apres)

    assert projete_avant == projete_apres, "le solde projeté a bougé : il y a double comptage"
    assert reel_apres < reel_avant, "le solde réel doit intégrer le débit confirmé"
    assert a_confirmer_apres > a_confirmer_avant, "la part à confirmer doit se vider"
    # Les deux variations doivent se compenser exactement, au centime près.
    assert (reel_apres - reel_avant) == -(a_confirmer_apres - a_confirmer_avant)


def test_temoin_les_trois_grandeurs_ne_sont_pas_confondues() -> None:
    """Contrôle inverse : sur un jeu où elles DOIVENT différer, elles diffèrent.

    Sans ce test, une implémentation qui renverrait la même somme pour les trois agrégats
    passerait le témoin ci-dessus sans difficulté.
    """
    operations = [
        operation(300000),
        operation(-4590, etat=EtatOperation.A_CONFIRMER),
        operation(-12000, jour=dt.date(2026, 9, 5), etat=EtatOperation.PREVUE),
    ]
    reel = somme(Agregat.SOLDE_REEL, operations)
    a_confirmer = somme(Agregat.SOLDE_A_CONFIRMER, operations)
    projete = somme(Agregat.SOLDE_PROJETE, operations)

    assert reel == 300000
    assert a_confirmer == -4590
    assert projete == 300000 - 4590 - 12000
    assert len({reel, a_confirmer, projete}) == 3


# --- Bornes temporelles ----------------------------------------------------------


def test_une_echeance_hors_fenetre_ne_compte_pas_dans_le_projete() -> None:
    """Un projeté sans borne de fenêtre ne veut rien dire : il inclurait l'année entière."""
    dans = operation(-5000, jour=FIN_FENETRE, etat=EtatOperation.PREVUE)
    dehors = operation(-5000, jour=FIN_FENETRE + dt.timedelta(days=1), etat=EtatOperation.PREVUE)

    assert somme(Agregat.SOLDE_PROJETE, [dans]) == -5000
    assert somme(Agregat.SOLDE_PROJETE, [dehors]) == 0


def test_une_operation_confirmee_future_compte_dans_le_projete_pas_dans_le_reel() -> None:
    """Le réel s'arrête à aujourd'hui ; le projeté regarde jusqu'à la fin de la fenêtre.

    Ce test a corrigé la table : elle bornait d'abord les opérations confirmées à
    aujourd'hui pour TOUS les agrégats, si bien qu'une dépense constatée et datée de
    demain n'apparaissait nulle part. Voir ERREURS.md #010.
    """
    future = operation(-5000, jour=AUJOURD_HUI + dt.timedelta(days=1))
    assert somme(Agregat.SOLDE_REEL, [future]) == 0
    assert somme(Agregat.SOLDE_PROJETE, [future]) == -5000


def test_aucune_operation_ne_disparait_de_tous_les_agregats() -> None:
    """Témoin structurel : toute opération datée dans la fenêtre doit apparaître dans au
    moins un agrégat, quel que soit son état et sa date.

    C'est le contrôle qui manquait : sans lui, une borne mal posée fait disparaître de
    l'argent sans qu'aucun total ne semble faux.
    """
    jours = [AUJOURD_HUI - dt.timedelta(days=1), AUJOURD_HUI, AUJOURD_HUI + dt.timedelta(days=1),
             FIN_FENETRE]
    for etat in EtatOperation:
        for jour in jours:
            une = [operation(-1234, jour=jour, etat=etat)]
            totaux = [somme(agregat, une) for agregat in Agregat]
            assert any(total != 0 for total in totaux), (
                f"une opération {etat} datée du {jour} n'apparaît dans AUCUN agrégat"
            )


def test_la_borne_du_jour_est_inclusive() -> None:
    assert somme(Agregat.SOLDE_REEL, [operation(-100, jour=AUJOURD_HUI)]) == -100


def test_une_fenetre_anterieure_au_jour_est_refusee() -> None:
    with pytest.raises(ValueError, match="fin de fenêtre"):
        calculer(
            Agregat.SOLDE_REEL, [], aujourd_hui=AUJOURD_HUI, fin_de_fenetre=AUJOURD_HUI
            - dt.timedelta(days=1)
        )


# --- Plafonds --------------------------------------------------------------------


def test_les_plafonds_ignorent_les_echeances_futures() -> None:
    """Sinon un plafond serait dépassé dès le premier jour de la période, par des
    dépenses qui n'ont pas encore eu lieu."""
    operations = [
        operation(-30000),
        operation(-12000, jour=dt.date(2026, 9, 5), etat=EtatOperation.PREVUE),
    ]
    assert somme(Agregat.DEPENSES_DE_PERIODE, operations) == -30000


def test_les_plafonds_comptent_les_operations_a_confirmer() -> None:
    """L'argent est parti : l'ignorer sous-estimerait la consommation du plafond."""
    partie = [operation(-4590, etat=EtatOperation.A_CONFIRMER)]
    assert somme(Agregat.DEPENSES_DE_PERIODE, partie) == -4590


# --- Cas dégénérés ---------------------------------------------------------------


@pytest.mark.parametrize("agregat", list(Agregat))
def test_aucune_operation_donne_zero(agregat: Agregat) -> None:
    assert somme(agregat, []) == 0


def test_le_resultat_reste_un_entier() -> None:
    total = somme(Agregat.SOLDE_PROJETE, [operation(1), operation(2)])
    assert isinstance(total, int)
    assert total == 3


def test_toutes_les_bornes_declarees_sont_utilisees() -> None:
    """Témoin de la table : une borne déclarée mais jamais employée signalerait une
    règle morte — du code qu'on croit actif et qui ne l'est pas."""
    employees = {b for etats in CONTRIBUTIONS.values() for b in etats.values() if b is not None}
    assert employees == set(Borne)
