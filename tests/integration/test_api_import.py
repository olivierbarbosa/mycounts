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
    credit: str = "",
    reference: str = "ref-1",
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
