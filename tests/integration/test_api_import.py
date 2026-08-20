"""Import d'un relevé, contre PostgreSQL.

**Toutes les données de ce fichier sont inventées** : elles reproduisent la forme d'un
export bancaire réel sans en reprendre aucun contenu.

Le test central est `réimporter le même fichier n'écrit rien` — c'est la contrainte que
`BOUCLE.md` posait comme non négociable : sans elle, réimporter un mois qui chevauche le
précédent duplique l'argent, et l'erreur ne se voit qu'en comparant son solde à celui de
sa banque.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import session_ouverte

ENTETE = (
    "Date de comptabilisation;Libelle simplifie;Libelle operation;Reference;"
    "Informations complementaires;Type operation;Categorie;Sous categorie;"
    "Debit;Credit;Date operation;Date de valeur;Pointage operation"
)


def releve(*lignes: str) -> bytes:
    return ("\r\n".join((ENTETE, *lignes)) + "\r\n").encode("iso-8859-1")


def ligne(
    libelle: str = "INTERMARCHE",
    debit: str = "-46,80",
    reference: str = "ref-1",
    credit: str = "",
    categorie: str = "Alimentation",
    date: str = "17/08/2026",
) -> str:
    return (
        f"19/08/2026;{libelle};CB {libelle};{reference};;Carte bancaire;{categorie};"
        f"Sous;{debit};{credit};{date};{date};0"
    )


def creer_compte(client: TestClient) -> str:
    reponse = client.post("/api/comptes", json={"nom": "Courant", "prive": True})
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def analyser(client: TestClient, contenu: bytes) -> dict:  # type: ignore[type-arg]
    reponse = client.post(
        "/api/import/analyse", files={"fichier": ("releve.csv", contenu, "text/csv")}
    )
    assert reponse.status_code == 200, reponse.text
    return dict(reponse.json())


def test_lanalyse_nECRIT_rien(client: TestClient, session_bd: Session) -> None:
    """La règle du module : rien ne s'écrit sans revue."""
    session_ouverte(client, session_bd)
    creer_compte(client)

    avant = len(client.get("/api/operations?periode_courante=false").json())
    revue = analyser(client, releve(ligne()))
    apres = len(client.get("/api/operations?periode_courante=false").json())

    assert revue["nouvelles"] == 1
    assert apres == avant


def test_valider_ecrit_les_lignes_retenues(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte = creer_compte(client)
    revue = analyser(client, releve(ligne(), ligne(libelle="TOTAL", debit="-40,00")))

    # L'utilisateur n'en retient qu'une : c'est une proposition, pas un ordre.
    retenue = revue["lignes"][0]
    reponse = client.post(
        "/api/import/valider",
        json={
            "compte_id": compte,
            "lignes": [
                {
                    "cle": retenue["cle"],
                    "date_operation": retenue["date_operation"],
                    "libelle": retenue["libelle"],
                    "montant_centimes": retenue["montant_centimes"],
                }
            ],
        },
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["ecrites"] == 1

    operations = client.get("/api/operations?periode_courante=false").json()
    assert len(operations) == 1


def _valider_tout(client: TestClient, compte: str, revue: dict) -> dict:  # type: ignore[type-arg]
    reponse = client.post(
        "/api/import/valider",
        json={
            "compte_id": compte,
            "lignes": [
                {
                    "cle": ligne["cle"],
                    "date_operation": ligne["date_operation"],
                    "libelle": ligne["libelle"],
                    "montant_centimes": ligne["montant_centimes"],
                }
                for ligne in revue["lignes"]
                if not ligne["deja_importee"]
            ],
        },
    )
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def test_reimporter_le_meme_fichier_nECRIT_rien(
    client: TestClient, session_bd: Session
) -> None:
    """La contrainte non négociable : réimporter ne duplique pas l'argent."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client)
    contenu = releve(ligne(), ligne(libelle="TOTAL", debit="-40,00"))

    _valider_tout(client, compte, analyser(client, contenu))
    apres_premier = len(client.get("/api/operations?periode_courante=false").json())

    seconde_revue = analyser(client, contenu)
    assert seconde_revue["nouvelles"] == 0
    assert seconde_revue["deja_importees"] == 2

    _valider_tout(client, compte, seconde_revue)
    assert len(client.get("/api/operations?periode_courante=false").json()) == apres_premier


def test_un_import_qui_chevauche_najoute_que_le_nouveau(
    client: TestClient, session_bd: Session
) -> None:
    """Le cas réel : on réimporte un mois entier pour rattraper deux oublis."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client)

    _valider_tout(client, compte, analyser(client, releve(ligne())))
    revue = analyser(client, releve(ligne(), ligne(libelle="TOTAL", debit="-40,00")))

    assert revue["nouvelles"] == 1
    assert revue["deja_importees"] == 1
    resultat = _valider_tout(client, compte, revue)
    assert resultat["ecrites"] == 1
    assert len(client.get("/api/operations?periode_courante=false").json()) == 2


def test_deux_operations_identiques_du_meme_jour_sont_TOUTES_importees(
    client: TestClient, session_bd: Session
) -> None:
    """Trois remboursements de 2 € le même jour existent dans un relevé réel.

    Dédupliquer par le contenu en supprimerait deux, et l'erreur ne se verrait qu'en
    comparant son solde à celui de sa banque.
    """
    session_ouverte(client, session_bd)
    compte = creer_compte(client)
    contenu = releve(
        ligne(libelle="REMB", reference="", debit="", credit="+2,00"),
        ligne(libelle="REMB", reference="", debit="", credit="+2,00"),
        ligne(libelle="REMB", reference="", debit="", credit="+2,00"),
    )

    revue = analyser(client, contenu)
    assert revue["nouvelles"] == 3
    _valider_tout(client, compte, revue)
    assert len(client.get("/api/operations?periode_courante=false").json()) == 3

    # Et le réimport reste idempotent malgré les identiques.
    assert analyser(client, contenu)["nouvelles"] == 0


def test_un_virement_interne_est_signale_comme_tel(
    client: TestClient, session_bd: Session
) -> None:
    """La banque marque elle-même ses mouvements internes ; les compter en revenu
    gonflerait les rentrées de chaque mise de côté."""
    session_ouverte(client, session_bd)
    creer_compte(client)
    revue = analyser(
        client,
        releve(
            ligne(
                libelle="VIR. VERS CPT DEPOT",
                debit="",
                credit="+200,00",
                categorie="Transaction exclue",
            )
        ),
    )
    assert revue["lignes"][0]["sens"] == "virement"


def test_un_fichier_illisible_est_refuse_avec_un_message_utile(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/import/analyse",
        files={"fichier": ("bidon.csv", b"un;deux\r\n1;2\r\n", "text/csv")},
    )
    assert reponse.status_code == 422
    # Le message nomme la colonne manquante : c'est la seule information qui permet d'agir.
    assert "Debit" in reponse.json()["detail"]


def test_un_compte_inconnu_est_refuse(client: TestClient, session_bd: Session) -> None:
    """Un identifiant valide chez quelqu'un d'autre doit être refusé exactement comme un
    identifiant inexistant."""
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/import/valider",
        json={"compte_id": "00000000-0000-0000-0000-000000000000", "lignes": []},
    )
    assert reponse.status_code == 404


def creer_categorie(client: TestClient, nom: str) -> str:
    reponse = client.post(
        "/api/categories", json={"nom": nom, "nature": "depense", "teinte": "vert"}
    )
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def test_le_rangement_sAPPREND_dun_import_a_lautre(
    client: TestClient, session_bd: Session
) -> None:
    """Sans mémoire, 198 lignes seraient à ranger à la main à chaque import — et personne
    ne le fait deux fois.

    La catégorie bancaire choisie ici — « Banque et assurances » — est délibérément une de
    celles que le tableau par défaut NE couvre pas : sans cela, la première analyse
    proposerait déjà quelque chose et le test mesurerait ce tableau au lieu de mesurer
    l'apprentissage.
    """
    session_ouverte(client, session_bd)
    compte = creer_compte(client)
    courses = creer_categorie(client, "Courses")

    revue = analyser(
        client, releve(ligne("INTERMARCHE", "-46,80", "r1", categorie="Banque et assurances"))
    )
    assert revue["lignes"][0]["categorie_proposee_id"] is None

    premiere = revue["lignes"][0]
    client.post(
        "/api/import/valider",
        json={
            "compte_id": compte,
            "lignes": [
                {
                    "cle": premiere["cle"],
                    "date_operation": premiere["date_operation"],
                    "libelle": premiere["libelle"],
                    "montant_centimes": premiere["montant_centimes"],
                    "categorie_id": courses,
                    "categorie_banque": premiere["categorie_banque"],
                }
            ],
        },
    )

    # Second relevé, même commerçant, autre montant et autre référence.
    seconde = analyser(
        client, releve(ligne("INTERMARCHE", "-31,20", "r2", categorie="Banque et assurances"))
    )
    assert seconde["lignes"][0]["categorie_proposee_id"] == courses


def test_la_categorie_de_la_banque_sert_aussi_pour_un_commercant_INCONNU(
    client: TestClient, session_bd: Session
) -> None:
    """Le rangement appris sur « Alimentation » couvre tous les commerçants de cette
    catégorie, y compris ceux qu'on n'a jamais vus."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client)
    courses = creer_categorie(client, "Courses")

    revue = analyser(client, releve(ligne("INTERMARCHE", "-46,80", "r1")))
    premiere = revue["lignes"][0]
    client.post(
        "/api/import/valider",
        json={
            "compte_id": compte,
            "lignes": [
                {
                    "cle": premiere["cle"],
                    "date_operation": premiere["date_operation"],
                    "libelle": premiere["libelle"],
                    "montant_centimes": premiere["montant_centimes"],
                    "categorie_id": courses,
                    "categorie_banque": "Alimentation",
                }
            ],
        },
    )

    # Un commerçant jamais vu, mais la même catégorie bancaire.
    autre = analyser(client, releve(ligne("CARREFOUR", "-22,00", "r9")))
    assert autre["lignes"][0]["categorie_proposee_id"] == courses


def test_un_prelevement_deja_enregistre_est_signale_comme_doublon(
    client: TestClient, session_bd: Session
) -> None:
    """Le cas visé : un abonnement saisi comme récurrence, et présent au relevé. Sans ce
    signalement, il compterait deux fois — dans le solde, les budgets et les statistiques."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client)
    client.post(
        "/api/operations",
        json={
            "compte_id": compte,
            "libelle": "Netflix",
            "montant_centimes": -1_599,
            "date_operation": "2026-08-16",
        },
    )

    revue = analyser(client, releve(ligne("PRLV NETFLIX INTERNATIONAL", "-15,99", "r5")))
    # Le libellé n'a pas besoin de se ressembler : c'est le montant et la date qui parlent.
    assert revue["lignes"][0]["doublon_probable"] is not None
    assert "Netflix" in revue["lignes"][0]["doublon_probable"]


def test_les_recurrences_du_releve_sont_PROPOSEES_jamais_creees(
    client: TestClient, session_bd: Session
) -> None:
    """Un écran qui ajouterait des récurrences tout seul remplirait le calendrier de
    prélèvements que personne n'a validés."""
    session_ouverte(client, session_bd)
    creer_compte(client)
    avant = len(client.get("/api/recurrences").json())

    revue = analyser(
        client,
        releve(
            ligne("ORANGE", "-25,89", "r1", date="05/07/2026"),
            ligne("ORANGE", "-25,89", "r2", date="05/08/2026"),
        ),
    )
    assert len(revue["recurrences_proposees"]) == 1
    assert revue["recurrences_proposees"][0]["cadence"] == "mois"
    # Rien n'a été créé.
    assert len(client.get("/api/recurrences").json()) == avant


def test_une_ligne_reclassee_en_virement_ne_compte_PAS_comme_un_revenu(
    client: TestClient, session_bd: Session
) -> None:
    """Le cas d'Olivier : un +200 € qui vient de son LEP, pas de l'extérieur.

    La banque marque ses mouvements internes, mais pas toujours. Sans reclassement, la
    somme entre dans les revenus et gonfle d'un argent qui n'est jamais entré dans le
    foyer — 31 lignes sur 198 dans son export réel.
    """
    session_ouverte(client, session_bd)
    cheques = creer_compte(client)
    lep = client.post(
        "/api/comptes", json={"nom": "LEP", "prive": True, "produit": "lep"}
    )
    assert lep.status_code == 201, lep.text
    lep_id = lep.json()["id"]

    revue = analyser(client, releve(ligne("VIR RECU", "", "v1", credit="+200,00")))
    proposee = revue["lignes"][0]

    reponse = client.post(
        "/api/import/valider",
        json={
            "compte_id": cheques,
            "lignes": [
                {
                    "cle": proposee["cle"],
                    "date_operation": proposee["date_operation"],
                    "libelle": proposee["libelle"],
                    "montant_centimes": proposee["montant_centimes"],
                    "sens": "virement",
                    "contrepartie_id": lep_id,
                }
            ],
        },
    )
    assert reponse.status_code == 201, reponse.text

    operations = client.get("/api/operations?periode_courante=false").json()
    # Deux moitiés, liées, de signes opposés : l'argent a changé de poche sans entrer.
    assert len(operations) == 2
    assert sum(operation["montant_centimes"] for operation in operations) == 0
    assert all(operation["virement_id"] is not None for operation in operations)


def test_le_sens_du_virement_se_deduit_du_SIGNE(
    client: TestClient, session_bd: Session
) -> None:
    """Un débit sur le compte importé va VERS l'autre compte, un crédit en vient. Le
    fichier contient déjà la réponse : la demander serait une question de trop."""
    session_ouverte(client, session_bd)
    cheques = creer_compte(client)
    lep_id = client.post(
        "/api/comptes", json={"nom": "LEP", "prive": True, "produit": "lep"}
    ).json()["id"]

    revue = analyser(client, releve(ligne("VIR EMIS", "-150,00", "v2")))
    proposee = revue["lignes"][0]
    client.post(
        "/api/import/valider",
        json={
            "compte_id": cheques,
            "lignes": [
                {
                    "cle": proposee["cle"],
                    "date_operation": proposee["date_operation"],
                    "libelle": proposee["libelle"],
                    "montant_centimes": proposee["montant_centimes"],
                    "sens": "virement",
                    "contrepartie_id": lep_id,
                }
            ],
        },
    )

    operations = client.get("/api/operations?periode_courante=false").json()
    sortie = next(o for o in operations if o["montant_centimes"] < 0)
    entree = next(o for o in operations if o["montant_centimes"] > 0)
    assert sortie["compte_id"] == cheques
    assert entree["compte_id"] == lep_id


def test_un_virement_importe_ne_se_reimporte_pas(
    client: TestClient, session_bd: Session
) -> None:
    """Un virement crée DEUX opérations ; si aucune ne portait la clé, il serait recréé à
    chaque import."""
    session_ouverte(client, session_bd)
    cheques = creer_compte(client)
    lep_id = client.post(
        "/api/comptes", json={"nom": "LEP", "prive": True, "produit": "lep"}
    ).json()["id"]
    contenu = releve(ligne("VIR RECU", "", "v3", credit="+200,00"))

    proposee = analyser(client, contenu)["lignes"][0]
    client.post(
        "/api/import/valider",
        json={
            "compte_id": cheques,
            "lignes": [
                {
                    "cle": proposee["cle"],
                    "date_operation": proposee["date_operation"],
                    "libelle": proposee["libelle"],
                    "montant_centimes": proposee["montant_centimes"],
                    "sens": "virement",
                    "contrepartie_id": lep_id,
                }
            ],
        },
    )
    assert analyser(client, contenu)["nouvelles"] == 0


def test_importer_depuis_une_date_ecarte_ce_qui_precede(
    client: TestClient, session_bd: Session
) -> None:
    """Le cas d'Olivier : n'importer que depuis sa dernière paie, pour ne pas faire
    doublon avec ce qu'il a déjà saisi à la main."""
    session_ouverte(client, session_bd)
    creer_compte(client)
    contenu = releve(
        ligne("ANCIEN", "-10,00", "a1", date="01/07/2026"),
        ligne("RECENT", "-20,00", "a2", date="18/08/2026"),
    )

    reponse = client.post(
        "/api/import/analyse?depuis=2026-08-01",
        files={"fichier": ("releve.csv", contenu, "text/csv")},
    )
    assert reponse.status_code == 200, reponse.text
    revue = reponse.json()
    assert revue["total"] == 1
    assert revue["lignes"][0]["libelle"] == "RECENT"


def test_le_tableau_par_defaut_range_des_le_PREMIER_import(
    client: TestClient, session_bd: Session
) -> None:
    """Le pire cas de l'import est un premier relevé tout « sans catégorie ».

    Mesuré sur un export réel : le tableau par défaut range 99 lignes sur 198, dont 90 des
    135 dépenses, sans qu'aucun libellé ne sorte du foyer ni qu'on ait rien appris.
    """
    session_ouverte(client, session_bd)
    creer_compte(client)
    courses = creer_categorie(client, "Courses")

    revue = analyser(client, releve(ligne("INTERMARCHE", "-46,80", "r1")))
    assert revue["lignes"][0]["categorie_proposee_id"] == courses


def test_une_categorie_bancaire_sans_equivalent_ne_propose_RIEN(
    client: TestClient, session_bd: Session
) -> None:
    """Deviner ferait plus de mal que de bien : une ligne mal rangée disparaît dans un
    total juste en apparence, là où une ligne non rangée se voit."""
    session_ouverte(client, session_bd)
    creer_compte(client)
    creer_categorie(client, "Courses")

    revue = analyser(
        client,
        releve(
            ligne("MAITRE DUPONT", "-300,00", "r7", categorie="Juridique et administratif")
        ),
    )
    assert revue["lignes"][0]["categorie_proposee_id"] is None
