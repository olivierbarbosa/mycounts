"""Catalogue des produits, modification et suppression d'un compte.

Le test central est `supprimer un compte qui porte des opérations est refusé` : sans ce
refus, les lignes disparaîtraient des soldes et des totaux passés, et un mois déjà clos
changerait de montant après coup.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.comptes import CATALOGUE, TypeCompte
from mycounts.domain.securite import hacher_mot_de_passe, normaliser_courriel
from mycounts.repository import auth as depot_auth
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE
from tests.integration.test_api_budget import connecter_avec_mfa, session_ouverte


def creer(client: TestClient, nom: str, produit: str = "compte_courant") -> dict:  # type: ignore[type-arg]
    reponse = client.post(
        "/api/comptes", json={"nom": nom, "prive": True, "produit": produit}
    )
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def test_le_catalogue_traduit_chaque_produit_en_comportement(
    client: TestClient, session_bd: Session
) -> None:
    """Un produit qui n'annoncerait pas son comportement laisserait l'écran le deviner."""
    session_ouverte(client, session_bd)
    produits = client.get("/api/comptes/catalogue").json()

    assert len(produits) == len(CATALOGUE)
    assert {p["type_compte"] for p in produits} == {TypeCompte.COURANT, TypeCompte.EPARGNE}
    par_cle = {p["cle"]: p for p in produits}
    assert par_cle["livret_a"]["type_compte"] == TypeCompte.EPARGNE
    assert par_cle["compte_courant"]["type_compte"] == TypeCompte.COURANT


def test_le_comportement_est_deduit_du_produit(client: TestClient, session_bd: Session) -> None:
    """Demander « un Livret A » suffit : le client n'envoie jamais le comportement.

    Le témoin oppose deux produits qui ne doivent PAS donner le même résultat — sans le
    second, un code qui renverrait toujours « épargne » passerait le test.
    """
    session_ouverte(client, session_bd)
    assert creer(client, "Livret", "livret_a")["type_compte"] == TypeCompte.EPARGNE
    assert creer(client, "Courant", "compte_courant")["type_compte"] == TypeCompte.COURANT


def test_un_produit_inconnu_est_refuse(client: TestClient, session_bd: Session) -> None:
    """Plutôt que de retomber sur un produit par défaut : deviner le comportement d'un
    compte reviendrait à déplacer de l'argent d'une colonne à l'autre sans qu'on l'ait
    demandé."""
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/comptes", json={"nom": "Bizarre", "prive": True, "produit": "livret_martien"}
    )
    assert reponse.status_code == 422, reponse.text


def test_changer_de_produit_change_le_comportement(
    client: TestClient, session_bd: Session
) -> None:
    """C'est le seul moyen de corriger une création faite trop vite."""
    session_ouverte(client, session_bd)
    compte = creer(client, "Mal nommé", "compte_courant")

    reponse = client.patch(
        f"/api/comptes/{compte['id']}", json={"nom": "Livret A", "produit": "livret_a"}
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["nom"] == "Livret A"
    assert reponse.json()["type_compte"] == TypeCompte.EPARGNE
    assert reponse.json()["produit_libelle"] == "Livret A"


def test_renommer_ne_reinitialise_pas_le_produit(
    client: TestClient, session_bd: Session
) -> None:
    """Les champs absents restent inchangés. Sans cette distinction, renommer un livret le
    remettrait en compte courant et sortirait son argent de la page Épargne."""
    session_ouverte(client, session_bd)
    compte = creer(client, "Livret", "livret_a")

    reponse = client.patch(f"/api/comptes/{compte['id']}", json={"nom": "Livret bleu"})
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["produit"] == "livret_a"
    assert reponse.json()["type_compte"] == TypeCompte.EPARGNE


def test_supprimer_un_compte_vide(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte = creer(client, "À jeter")

    assert client.delete(f"/api/comptes/{compte['id']}").status_code == 204
    assert [c["nom"] for c in client.get("/api/comptes").json()] == []


def test_supprimer_un_compte_qui_porte_des_operations_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte = creer(client, "Utilisé")
    client.post(
        "/api/operations",
        json={
            "compte_id": compte["id"],
            "libelle": "Courses",
            "montant_centimes": -1_000,
            "date_operation": aujourd_hui().isoformat(),
        },
    )

    reponse = client.delete(f"/api/comptes/{compte['id']}")
    assert reponse.status_code == 409, reponse.text
    assert "Archivez" in reponse.json()["detail"], "le refus doit dire quoi faire à la place"
    # Et le compte est toujours là : un refus qui supprimerait quand même serait pire.
    assert [c["nom"] for c in client.get("/api/comptes").json()] == ["Utilisé"]


def test_les_soldes_sont_rendus_par_compte(client: TestClient, session_bd: Session) -> None:
    """Le solde RÉEL, pas le projeté : une carte répond à « combien y a-t-il dessus »."""
    session_ouverte(client, session_bd)
    def avec_solde(nom: str, produit: str, ouverture: int) -> dict:  # type: ignore[type-arg]
        return dict(
            client.post(
                "/api/comptes",
                json={
                    "nom": nom,
                    "prive": True,
                    "produit": produit,
                    "solde_ouverture_centimes": ouverture,
                },
            ).json()
        )

    a = avec_solde("A", "compte_courant", 30_000)
    b = avec_solde("B", "livret_a", 12_000)

    rendus = client.get("/api/comptes/soldes").json()
    soldes = {s["compte_id"]: s["solde_centimes"] for s in rendus}
    assert soldes[a["id"]] == 30_000
    assert soldes[b["id"]] == 12_000


def solde_de(client: TestClient, compte_id: str) -> int:
    rendus = client.get("/api/comptes/soldes").json()
    return int(next(s["solde_centimes"] for s in rendus if s["compte_id"] == compte_id))


def test_ajuster_le_solde_enregistre_lecart_sans_creer_de_depense(
    client: TestClient, session_bd: Session
) -> None:
    """Corriger un solde n'est pas dépenser.

    Trois grandeurs : le solde doit rejoindre EXACTEMENT la valeur demandée, l'écart doit
    être celui qu'on attend, et les dépenses de période ne doivent pas bouger d'un
    centime. Sans la troisième, une correction de 20 € ferait sauter un plafond de 20 €.
    """
    session_ouverte(client, session_bd)
    compte = creer(client, "Courant")
    client.post(
        "/api/operations",
        json={
            "compte_id": compte["id"],
            "libelle": "Courses",
            "montant_centimes": -3_000,
            "date_operation": aujourd_hui().isoformat(),
        },
    )
    depenses_avant = int(client.get("/api/resume").json()["depenses_de_periode"])
    assert solde_de(client, compte["id"]) == -3_000

    reponse = client.post(
        f"/api/comptes/{compte['id']}/ajustement", json={"solde_reel_centimes": -5_000}
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["ecart_centimes"] == -2_000
    assert reponse.json()["solde_centimes"] == -5_000

    assert solde_de(client, compte["id"]) == -5_000, "le solde doit valoir ce qui a été demandé"
    assert (
        int(client.get("/api/resume").json()["depenses_de_periode"]) == depenses_avant
    ), "un ajustement compté en dépense ferait sauter les plafonds"


def test_ajuster_un_solde_deja_juste_ne_cree_rien(
    client: TestClient, session_bd: Session
) -> None:
    """Écrire un ajustement de zéro remplirait l'historique de lignes qui ne disent rien."""
    session_ouverte(client, session_bd)
    compte = creer(client, "Courant")

    avant = len(client.get("/api/operations?periode_courante=false").json())
    reponse = client.post(
        f"/api/comptes/{compte['id']}/ajustement", json={"solde_reel_centimes": 0}
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["ecart_centimes"] == 0
    assert len(client.get("/api/operations?periode_courante=false").json()) == avant


def test_lecart_est_calcule_par_le_serveur_pas_recu(
    client: TestClient, session_bd: Session
) -> None:
    """Deux corrections successives ne se doublent pas.

    Le client envoie le solde CONSTATÉ, jamais l'écart : s'il envoyait l'écart, la seconde
    demande le calculerait sur une valeur déjà périmée et l'ajouterait une seconde fois.
    Rejouer la même demande doit donc être sans effet.
    """
    session_ouverte(client, session_bd)
    compte = creer(client, "Courant")

    for _ in range(3):
        client.post(
            f"/api/comptes/{compte['id']}/ajustement", json={"solde_reel_centimes": 12_345}
        )

    assert solde_de(client, compte["id"]) == 12_345


def test_un_membre_ne_peut_pas_supprimer_le_compte_joint_dun_autre(
    client: TestClient, session_bd: Session
) -> None:
    """Un compte joint est visible de tous les membres, mais n'appartient qu'à celui qui
    l'a ouvert. La visibilité ne vaut pas permission — ce qui n'est vrai d'aucun objet
    partagé, et l'était pourtant ici avant cette garde.

    Le refus est un 403 et non un 404 : le compte existe et l'appelant le voit ; lui dire
    « introuvable » l'enverrait chercher une panne qui n'existe pas.
    """
    alice = session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/comptes", json={"nom": "Compte joint", "prive": False, "produit": "compte_courant"}
    )
    assert reponse.status_code == 201, reponse.text
    compte_id = reponse.json()["id"]

    # Un second membre du MÊME foyer, connecté à son tour. Le helper habituel crée un
    # foyer neuf à chaque appel : ici il faut partager celui d'Alice, sans quoi Bruno ne
    # verrait tout simplement pas le compte et le test mesurerait la visibilité au lieu
    # de la permission.
    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        courriel_verifie=True,
    )
    session_bd.commit()
    connecter_avec_mfa(client, session_bd, "bruno@essai.fr")

    refus = client.request(
        "DELETE", f"/api/comptes/{compte_id}", headers={"X-Mycounts-Vue": "foyer"}
    )
    assert refus.status_code == 403, refus.text
    assert "peut le supprimer" in refus.json()["detail"]

    # Et le compte est toujours là pour tout le monde.
    comptes = client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json()
    assert [c["nom"] for c in comptes] == ["Compte joint"]


def test_le_proprietaire_supprime_son_compte_joint(
    client: TestClient, session_bd: Session
) -> None:
    """L'autre sens, sans lequel une règle qui refuserait TOUJOURS passerait le test
    précédent."""
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/comptes", json={"nom": "A moi", "prive": False, "produit": "compte_courant"}
    )
    compte_id = reponse.json()["id"]

    suppression = client.request(
        "DELETE", f"/api/comptes/{compte_id}", headers={"X-Mycounts-Vue": "foyer"}
    )
    assert suppression.status_code == 204, suppression.text
    assert client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json() == []


def test_un_compte_qui_ne_porte_QUE_son_ouverture_se_supprime(
    client: TestClient, session_bd: Session
) -> None:
    """Le cas d'Olivier : un compte joint créé avec son solde de départ, impossible à
    supprimer ensuite.

    La règle protège les mois clos, mais un compte qui ne porte que son amorçage n'a jamais
    servi à clore quoi que ce soit. La refuser rendait irréversible la seule erreur qu'on
    fait vraiment — se tromper en créant un compte.
    """
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/comptes",
        json={
            "nom": "Avec ouverture",
            "prive": False,
            "produit": "compte_courant",
            "solde_ouverture_centimes": 50_000,
        },
    )
    assert reponse.status_code == 201, reponse.text

    suppression = client.request(
        "DELETE", f"/api/comptes/{reponse.json()['id']}", headers={"X-Mycounts-Vue": "foyer"}
    )
    assert suppression.status_code == 204, suppression.text


def test_un_compte_qui_porte_une_VRAIE_operation_reste_protege(
    client: TestClient, session_bd: Session
) -> None:
    """L'autre sens, sans lequel la correction précédente ouvrirait la porte à la
    disparition de mois déjà clos."""
    session_ouverte(client, session_bd)
    compte_id = client.post(
        "/api/comptes", json={"nom": "Avec dépense", "prive": True, "produit": "compte_courant"}
    ).json()["id"]
    client.post(
        "/api/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Un achat",
            "montant_centimes": -1_000,
            "date_operation": aujourd_hui().isoformat(),
        },
    )

    refus = client.request("DELETE", f"/api/comptes/{compte_id}")
    assert refus.status_code == 409, refus.text
    assert "Archivez-le" in refus.json()["detail"]


def test_lecran_de_gestion_suit_la_vue(client: TestClient, session_bd: Session) -> None:
    """Le sens de ce test s'est INVERSÉ le 22 août 2026.

    Il exigeait auparavant que l'écran de gestion réunisse les deux périmètres, au motif
    que l'étanchéité ne porte que sur les soldes. Olivier a tranché l'inverse : chaque vue
    montre son monde, ici comme partout. Deux écrans qui répondent différemment à la même
    bascule s'apprennent deux fois.

    Ce que cette décision NE défait pas : agir sur un compte reste possible depuis les
    deux vues — voir `test_un_compte_joint_se_gere_depuis_la_vue_personnelle`. La liste
    s'est resserrée, pas les permissions.
    """
    session_ouverte(client, session_bd)
    client.post(
        "/api/comptes", json={"nom": "Mon perso", "prive": True, "produit": "compte_courant"}
    )
    client.post(
        "/api/comptes", json={"nom": "Le joint", "prive": False, "produit": "compte_courant"}
    )

    for vue, attendu in [("personnelle", ["Mon perso"]), ("foyer", ["Le joint"])]:
        gestion = client.get(
            "/api/comptes?inclure_archives=true", headers={"X-Mycounts-Vue": vue}
        ).json()
        assert [c["nom"] for c in gestion] == attendu, f"vue {vue}"


def test_un_compte_joint_se_gere_depuis_la_vue_personnelle(
    client: TestClient, session_bd: Session
) -> None:
    """L'écran de gestion liste les deux périmètres ; il doit pouvoir AGIR sur les deux.

    Lister sans pouvoir agir est le pire des deux états : le compte s'affiche sous le
    doigt et le serveur répond « Compte introuvable ». Olivier l'a rencontré sur son
    compte joint, et la réponse l'envoyait chercher une panne qui n'existait pas.
    """
    session_ouverte(client, session_bd)
    joint = client.post(
        "/api/comptes",
        json={"nom": "Le joint", "prive": False, "produit": "compte_courant"},
        headers={"X-Mycounts-Vue": "foyer"},
    ).json()

    # Tout ce qui suit se fait en vue PERSONNELLE, sur un compte JOINT.
    renomme = client.patch(
        f"/api/comptes/{joint['id']}",
        json={"nom": "Renomme", "produit": "compte_courant", "archive": False},
    )
    assert renomme.status_code == 200, renomme.text
    assert renomme.json()["nom"] == "Renomme"

    efface = client.delete(f"/api/comptes/{joint['id']}")
    assert efface.status_code == 204, efface.text
    assert client.get("/api/comptes?inclure_archives=true").json() == []


def test_un_compte_archive_reste_atteignable_dans_lecran_de_gestion(
    client: TestClient, session_bd: Session
) -> None:
    """L'archivage est proposé comme l'alternative DOUCE à une suppression refusée.

    La liste filtrait `archive = false` : le compte disparaissait de l'écran même qui
    venait de le proposer, sans moyen de le désarchiver ni de le supprimer. Une action
    présentée comme réversible était sans retour.
    """
    session_ouverte(client, session_bd)
    compte = creer(client, "A ranger")

    archive = client.patch(
        f"/api/comptes/{compte['id']}",
        json={"nom": "A ranger", "produit": "compte_courant", "archive": True},
    )
    assert archive.status_code == 200, archive.text

    # Il quitte les écrans qui proposent des comptes…
    assert client.get("/api/comptes").json() == []
    # …mais reste dans celui qui les gère, marqué comme tel.
    gestion = client.get("/api/comptes?inclure_archives=true").json()
    assert [(c["nom"], c["archive"]) for c in gestion] == [("A ranger", True)]

    # Et le chemin du retour existe.
    retour = client.patch(
        f"/api/comptes/{compte['id']}",
        json={"nom": "A ranger", "produit": "compte_courant", "archive": False},
    )
    assert retour.status_code == 200, retour.text
    assert [c["nom"] for c in client.get("/api/comptes").json()] == ["A ranger"]


def test_le_solde_dun_compte_archive_est_rendu_a_lecran_de_gestion(
    client: TestClient, session_bd: Session
) -> None:
    """« Archivés compris » était FAUX : la docstring l'annonçait, la boucle les excluait.

    Une carte archivée sans montant se lit comme un compte vide — pas comme un compte
    rangé. La phrase a survécu des semaines parce que rien ne pouvait la contredire.

    L'autre bord est mesuré dans le même test : le défaut écarte toujours les archivés,
    sans quoi ils reviendraient dans les totaux qu'ils avaient quittés.
    """
    session_ouverte(client, session_bd)
    compte = client.post(
        "/api/comptes",
        json={
            "nom": "Range",
            "prive": True,
            "produit": "compte_courant",
            "solde_ouverture_centimes": 1234,
        },
    ).json()
    client.patch(
        f"/api/comptes/{compte['id']}",
        json={"nom": "Range", "produit": "compte_courant", "archive": True},
    )

    soldes = {
        s["compte_id"]: s["solde_centimes"]
        for s in client.get("/api/comptes/soldes?inclure_archives=true").json()
    }
    assert soldes.get(compte["id"]) == 1234

    # Le défaut reste étanche : un écran qui totalise n'a jamais vu ce compte.
    assert client.get("/api/comptes/soldes").json() == []


def test_le_compte_prive_dun_autre_membre_reste_intouchable(
    client: TestClient, session_bd: Session
) -> None:
    """La non-régression qui compte : élargir la GESTION aux deux vues n'ouvre pas la
    porte aux comptes privés d'autrui.

    `toutes_vues` réunit les deux périmètres que l'appelant peut déjà consulter, jamais
    un troisième. Sans ce test, une condition trop permissive — « tous les comptes du
    foyer » au lieu de « les miens et les joints » — passerait tous les autres tests de
    ce fichier en silence, et c'est la plus permissive des deux versions qui ne prévient
    jamais.
    """
    alice = session_ouverte(client, session_bd)
    secret = creer(client, "Le carnet d'Alice")

    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        courriel_verifie=True,
    )
    session_bd.commit()
    connecter_avec_mfa(client, session_bd, "bruno@essai.fr")

    # Bruno ne le voit pas, même dans l'écran qui réunit les deux périmètres.
    assert client.get("/api/comptes?inclure_archives=true").json() == []
    assert client.get("/api/comptes/soldes?toutes_vues=true").json() == []

    # Et il ne peut ni le renommer ni le supprimer. Un 404 et non un 403 : ici le compte
    # n'est pas « visible mais interdit », il est hors de son monde — le lui nommer
    # apprendrait déjà son existence.
    renommage = client.patch(
        f"/api/comptes/{secret['id']}",
        json={"nom": "Vole", "produit": "compte_courant", "archive": False},
    )
    assert renommage.status_code == 404, renommage.text
    assert client.delete(f"/api/comptes/{secret['id']}").status_code == 404


def test_les_corrections_de_solde_restent_consultables(
    client: TestClient, session_bd: Session
) -> None:
    """Elles ont quitté le journal de l'accueil ; il leur fallait un autre endroit.

    Sans cette route, une correction posée devenait invisible : impossible de relire trois
    mois plus tard pourquoi le solde avait bougé de 13,40 €. Une valeur posée d'autorité,
    exactement ce que l'ajustement cherche à ne pas être.

    Les deux moitiés sont mesurées : la correction figure ici, et n'est PAS une opération
    ordinaire du journal.
    """
    session_ouverte(client, session_bd)
    compte = creer(client, "Courant")
    client.post(
        "/api/operations",
        json={
            "compte_id": compte["id"],
            "libelle": "Un vrai achat",
            "montant_centimes": -1_000,
            "date_operation": aujourd_hui().isoformat(),
        },
    )
    fait = client.post(
        f"/api/comptes/{compte['id']}/ajustement", json={"solde_reel_centimes": -2_340}
    )
    assert fait.status_code == 200, fait.text

    corrections = client.get(f"/api/comptes/{compte['id']}/ajustements").json()
    assert len(corrections) == 1, corrections
    assert corrections[0]["est_ajustement"] is True
    assert corrections[0]["montant_centimes"] == -1_340

    # L'achat, lui, n'est pas une correction : la route ne mélange pas les deux.
    assert all(c["libelle"] != "Un vrai achat" for c in corrections)


def test_deux_corrections_du_meme_jour_sortent_de_la_plus_recente(
    client: TestClient, session_bd: Session
) -> None:
    """Corriger deux fois le même jour est le cas ordinaire : on rectifie, on se ravise.

    L'ordre appartient à `operations_visibles`, qui départage par `cree_le`. Ce témoin
    existe parce que la route a d'abord retrié la liste elle-même, sur `date_operation`
    seule : un second auteur, moins juste que le premier, et invisible — le bon résultat
    arrivait quand même du repository. Muter la route ne fait donc rien rougir ; muter le
    `order_by` du repository fait rougir ce test.
    """
    session_ouverte(client, session_bd)
    compte = creer(client, "Courant")

    premiere = client.post(
        f"/api/comptes/{compte['id']}/ajustement", json={"solde_reel_centimes": -1_000}
    )
    assert premiere.status_code == 200, premiere.text
    seconde = client.post(
        f"/api/comptes/{compte['id']}/ajustement", json={"solde_reel_centimes": -2_500}
    )
    assert seconde.status_code == 200, seconde.text

    corrections = client.get(f"/api/comptes/{compte['id']}/ajustements").json()
    assert len(corrections) == 2, corrections
    assert [c["date_operation"] for c in corrections] == [
        corrections[0]["date_operation"],
        corrections[0]["date_operation"],
    ], "les deux doivent bien porter la MÊME date, sans quoi le tri ne prouve rien"
    # La seconde amène le solde de -1000 à -2500, soit -1500 ; elle vient en tête.
    assert corrections[0]["montant_centimes"] == -1_500
    assert corrections[1]["montant_centimes"] == -1_000


def test_lhistorique_des_corrections_respecte_le_perimetre(
    client: TestClient, session_bd: Session
) -> None:
    """Un identifiant de compte inconnu ne dit pas s'il existe ailleurs."""
    session_ouverte(client, session_bd)
    autre = uuid.uuid4()
    assert client.get(f"/api/comptes/{autre}/ajustements").status_code == 404
