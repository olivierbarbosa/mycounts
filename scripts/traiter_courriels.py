"""Worker de boîte d'envoi SMTP, à lancer comme service séparé."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from mycounts.config import charger_configuration
from mycounts.domain.securite import maintenant
from mycounts.repository import identite as depot
from mycounts.repository.base import fabrique_de_sessions
from mycounts.services.courriels import envoyer, rendre

journal = logging.getLogger("mycounts.courriels")

# Même chemin que la sonde du compose (infra/docker-compose.vps.yml) : /tmp est le seul
# répertoire où l'utilisateur sans privilège de l'image peut écrire.
BATTEMENT = "/tmp/mycounts-courriels-vivant"


def traiter_un() -> bool:
    configuration = charger_configuration()
    # Une installation privée peut démarrer avant que le mot de passe SMTP soit posé.
    # Dans ce cas, surtout ne pas consommer les huit essais de chaque message : la file
    # doit rester intacte et repartir après configuration puis redémarrage du worker.
    if not configuration.smtp_configure:
        return False
    session = fabrique_de_sessions()()
    try:
        instant = maintenant()
        courriel = depot.prochain_courriel(session, a_l_instant=instant)
        if courriel is None:
            session.rollback()
            return False
        try:
            rendu = rendre(
                courriel.modele,
                courriel.donnees,
                support=configuration.courriel_support,
            )
            envoyer(configuration, destinataire=courriel.destinataire, courriel=rendu)
        except Exception as erreur:  # noqa: BLE001 — le worker doit survivre au transport
            # Ni destinataire, ni contenu, ni jeton dans les logs.
            journal.warning("Échec d'un courriel sortant: %s", erreur.__class__.__name__)
            depot.reporter_courriel(
                session, courriel, a_l_instant=instant, erreur=erreur.__class__.__name__
            )
        else:
            depot.marquer_envoye(session, courriel, a_l_instant=instant)
        session.commit()
        return True
    finally:
        session.close()


def battre() -> None:
    """Écrit le battement de cœur que la sonde Docker relit.

    Un worker sans port n'a rien d'autre à montrer qu'« encore en boucle ». La sonde
    héritée de l'image interrogeait un port HTTP que ce processus n'ouvre pas, et l'a
    déclaré malade pendant six jours sans rien mesurer de lui (ERREURS.md #054).
    """
    Path(BATTEMENT).touch()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    configuration = charger_configuration()
    # Dire au démarrage ce qui va se passer : « SMTP absent » se lisait jusqu'ici
    # comme « rien à envoyer », et un mot de passe oublié a attendu sept jours en file.
    if configuration.smtp_configure:
        journal.info("Worker de courriels démarré, SMTP configuré.")
    else:
        journal.warning("SMTP NON configuré : la file restera intacte, rien ne partira.")
    while True:
        battre()
        if not traiter_un():
            time.sleep(5)


if __name__ == "__main__":
    main()
