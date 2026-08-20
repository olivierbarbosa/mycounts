"""Import d'un relevé CSV.

**Toutes les données de ce fichier sont inventées.** Elles reproduisent la FORME d'un
export réel — colonnes, encodage, séparateur, doubles dates, débit et crédit en deux
colonnes — sans en reprendre aucun contenu. Le garde-fou nº 1 refuse d'ailleurs qu'un IBAN
valide entre dans le dépôt, et il a raison de le faire.

Le test central est `la clé distingue deux opérations réellement identiques` : sans lui,
une déduplication par le contenu supprimerait de vraies lignes, et l'erreur ne se verrait
qu'en comparant son solde à celui de sa banque.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.import_releve import (
    ReleveIllisible,
    SensImporte,
    analyser,
    ecarter_les_deja_importees,
)
from mycounts.domain.montants import Cents

ENTETE = (
    "Date de comptabilisation;Libelle simplifie;Libelle operation;Reference;"
    "Informations complementaires;Type operation;Categorie;Sous categorie;"
    "Debit;Credit;Date operation;Date de valeur;Pointage operation"
)


def _releve(*lignes: str, encodage: str = "iso-8859-1") -> bytes:
    return ("\r\n".join((ENTETE, *lignes)) + "\r\n").encode(encodage)


def _ligne(
    *,
    comptabilisation: str = "19/08/2026",
    libelle: str = "INTERMARCHE",
    reference: str = "ref-1",
    categorie: str = "Alimentation",
    debit: str = "-46,80",
    credit: str = "",
    operation: str = "17/08/2026",
) -> str:
    return (
        f"{comptabilisation};{libelle};CB {libelle} FACT;{reference};;Carte bancaire;"
        f"{categorie};Sous;{debit};{credit};{operation};{operation};0"
    )


class TestLecture:
    def test_une_depense_est_lue_en_negatif(self) -> None:
        (ligne,) = analyser(_releve(_ligne()))
        assert ligne.montant == Cents(-4_680)
        assert ligne.sens is SensImporte.DEPENSE

    def test_un_credit_est_lu_en_positif(self) -> None:
        (ligne,) = analyser(_releve(_ligne(debit="", credit="+200,00")))
        assert ligne.montant == Cents(20_000)
        assert ligne.sens is SensImporte.REVENU

    def test_la_date_retenue_est_celle_de_lOPERATION(self) -> None:
        """Et non celle de comptabilisation. Elles diffèrent une fois sur deux dans un
        export réel : un achat du 30 comptabilisé le 2 tomberait dans la mauvaise période
        budgétaire, faussant le budget des deux mois à la fois."""
        (ligne,) = analyser(
            _releve(_ligne(comptabilisation="02/09/2026", operation="30/08/2026"))
        )
        assert ligne.date_operation == dt.date(2026, 8, 30)

    def test_a_defaut_de_date_doperation_la_comptabilisation_sert(self) -> None:
        (ligne,) = analyser(_releve(_ligne(operation="")))
        assert ligne.date_operation == dt.date(2026, 8, 19)

    def test_un_virement_interne_est_reconnu_comme_tel(self) -> None:
        """La banque marque elle-même ses mouvements internes. S'en servir évite de
        gonfler les revenus de chaque mise de côté."""
        (ligne,) = analyser(
            _releve(
                _ligne(
                    libelle="VIR. VERS CPT DEPOT",
                    categorie="Transaction exclue",
                    debit="",
                    credit="+200,00",
                )
            )
        )
        assert ligne.sens is SensImporte.VIREMENT

    @pytest.mark.parametrize(
        ("espace", "encodage"),
        [
            (" ", "iso-8859-1"),
            ("\u00a0", "iso-8859-1"),
            # L'espace FINE insécable n'existe pas en ISO-8859-1 : un relevé qui en
            # contient est forcément en UTF-8, et le test le produit donc ainsi. Écrire ce
            # cas en Latin-1 faisait échouer le test à l'encodage, pas le code à la
            # lecture — la mesure aurait porté sur le mauvais sujet.
            ("\u202f", "utf-8"),
        ],
    )
    def test_les_espaces_de_milliers_ne_cassent_pas_le_montant(
        self, espace: str, encodage: str
    ) -> None:
        (ligne,) = analyser(_releve(_ligne(debit=f"-1{espace}234,56"), encodage=encodage))
        assert ligne.montant == Cents(-123_456)

    def test_les_centimes_ne_passent_JAMAIS_par_un_flottant(self) -> None:
        """`int(float("0.29") * 100)` vaut 28. C'est la raison d'être de la règle du projet,
        et le genre d'erreur qui ne se voit que sur un total de fin de mois."""
        (ligne,) = analyser(_releve(_ligne(debit="-0,29")))
        assert ligne.montant == Cents(-29)

    def test_une_ligne_sans_montant_est_ignoree_sans_faire_echouer_le_fichier(self) -> None:
        """Un pied de page ou un total ne doit pas faire perdre les 197 autres lignes."""
        lignes = analyser(_releve(_ligne(), _ligne(debit="", credit="")))
        assert len(lignes) == 1


class TestEncodage:
    def test_un_fichier_latin1_garde_ses_accents(self) -> None:
        """La plupart des banques françaises exportent en ISO-8859-1. Lu en UTF-8, le
        fichier lève une erreur ; lu de travers, il remplace les accents."""
        (ligne,) = analyser(_releve(_ligne(libelle="Café Crème"), encodage="iso-8859-1"))
        assert ligne.libelle == "Café Crème"

    def test_un_fichier_utf8_garde_aussi_ses_accents(self) -> None:
        """L'ordre des tentatives compte : un fichier UTF-8 lu en Latin-1 ne lève AUCUNE
        erreur, il produit des « Ã© ». On essaie donc d'abord celui qui sait échouer."""
        (ligne,) = analyser(_releve(_ligne(libelle="Café Crème"), encodage="utf-8"))
        assert ligne.libelle == "Café Crème"


class TestCleDUnicite:
    def test_la_cle_distingue_deux_operations_reellement_identiques(self) -> None:
        """LE test du module.

        Trois remboursements de 2 € le même jour existent dans un export réel. Dédupliquer
        par le contenu en supprimerait deux — et l'erreur ne se verrait qu'en comparant son
        solde à celui de sa banque, des semaines plus tard.
        """
        lignes = analyser(
            _releve(
                _ligne(libelle="REMB", reference="", debit="", credit="+2,00"),
                _ligne(libelle="REMB", reference="", debit="", credit="+2,00"),
                _ligne(libelle="REMB", reference="", debit="", credit="+2,00"),
            )
        )
        assert [ligne.rang for ligne in lignes] == [1, 2, 3]
        assert len({ligne.cle for ligne in lignes}) == 3

    def test_deux_operations_differentes_partageant_une_reference_restent_distinctes(
        self,
    ) -> None:
        """Mesuré sur un export réel : deux achats du même jour chez le même commerçant
        partagent le même identifiant bancaire. La référence seule ne peut donc pas être
        la clé."""
        lignes = analyser(
            _releve(
                _ligne(libelle="VERTBAUDET", reference="meme-ref", debit="-31,98"),
                _ligne(libelle="VERTBAUDET", reference="meme-ref", debit="-15,50"),
            )
        )
        assert len({ligne.cle for ligne in lignes}) == 2

    def test_reimporter_le_meme_fichier_ne_propose_plus_rien(self) -> None:
        """L'idempotence, qui est toute la raison d'être de la clé."""
        lignes = analyser(_releve(_ligne(), _ligne(libelle="TOTAL", debit="-40,00")))
        nouvelles, ignorees = ecarter_les_deja_importees(lignes, [ligne.cle for ligne in lignes])
        assert nouvelles == ()
        assert len(ignorees) == 2

    def test_un_import_qui_chevauche_ne_garde_que_le_nouveau(self) -> None:
        premier = analyser(_releve(_ligne()))
        second = analyser(_releve(_ligne(), _ligne(libelle="TOTAL", debit="-40,00")))
        nouvelles, ignorees = ecarter_les_deja_importees(second, [ligne.cle for ligne in premier])
        assert [ligne.libelle for ligne in nouvelles] == ["TOTAL"]
        assert [ligne.libelle for ligne in ignorees] == ["INTERMARCHE"]

    def test_les_lignes_ignorees_sont_RENDUES_et_non_tues(self) -> None:
        """L'écran les montre : les cacher ferait croire à un fichier incomplet à qui
        réimporte un mois entier pour deux oublis."""
        lignes = analyser(_releve(_ligne()))
        _, ignorees = ecarter_les_deja_importees(lignes, [ligne.cle for ligne in lignes])
        assert len(ignorees) == 1


class TestFichiersRefuses:
    def test_un_fichier_sans_les_colonnes_attendues_est_refuse_avec_un_message_utile(
        self,
    ) -> None:
        with pytest.raises(ReleveIllisible) as erreur:
            analyser(b"un;deux;trois\r\n1;2;3\r\n")
        # Le message nomme ce qui manque : « KeyError » ne dirait rien à personne.
        assert "Debit" in str(erreur.value)

    def test_un_fichier_vide_est_refuse(self) -> None:
        with pytest.raises(ReleveIllisible):
            analyser(b"")

    def test_un_montant_illisible_est_refuse_en_nommant_la_valeur(self) -> None:
        with pytest.raises(ReleveIllisible) as erreur:
            analyser(_releve(_ligne(debit="quarante euros")))
        assert "quarante euros" in str(erreur.value)

    def test_une_date_illisible_est_refusee_en_nommant_la_valeur(self) -> None:
        with pytest.raises(ReleveIllisible) as erreur:
            analyser(_releve(_ligne(operation="hier", comptabilisation="hier")))
        assert "hier" in str(erreur.value)
