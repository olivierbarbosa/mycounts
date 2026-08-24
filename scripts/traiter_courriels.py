"""Worker de boîte d'envoi SMTP, à lancer comme service séparé."""

from __future__ import annotations

import logging
import time

from mycounts.config import charger_configuration
from mycounts.domain.securite import maintenant
from mycounts.repository import identite as depot
from mycounts.repository.base import fabrique_de_sessions
from mycounts.services.courriels import envoyer, rendre

journal = logging.getLogger("mycounts.courriels")


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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        if not traiter_un():
            time.sleep(5)


if __name__ == "__main__":
    main()
