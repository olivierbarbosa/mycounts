"""Rendu et transport SMTP des seuls courriels d'identité de MyCounts."""

from __future__ import annotations

import html
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Final

from mycounts.config import Configuration


@dataclass(frozen=True)
class CourrielRendu:
    sujet: str
    texte: str
    html: str


SUJETS: Final[dict[str, str]] = {
    "verification_courriel": "Vérifiez votre adresse MyCounts",
    "reinitialisation_mot_de_passe": "Réinitialisez votre accès MyCounts",
    "alerte_securite": "Sécurité de votre compte MyCounts",
}


def rendre(modele: str, donnees: dict[str, str], *, support: str) -> CourrielRendu:
    """Rend un modèle fermé; aucune chaîne arbitraire ne devient un sujet ou du HTML."""
    if modele not in SUJETS:
        raise ValueError("Modèle de courriel inconnu.")
    nom = donnees.get("nom", "").strip() or "Bonjour"
    lien = donnees.get("lien", "").strip()
    if modele == "verification_courriel":
        action = "Vérifier mon adresse"
        explication = "Ce lien est valable 24 heures et ne peut servir qu’une fois."
    elif modele == "reinitialisation_mot_de_passe":
        action = "Choisir un nouveau mot de passe"
        explication = "Ce lien est valable 30 minutes et ne peut servir qu’une fois."
    else:
        action = "Ouvrir MyCounts"
        explication = donnees.get("message", "Un changement de sécurité a eu lieu.")

    texte = (
        f"{nom},\n\n{action} : {lien}\n\n{explication}\n\n"
        f"Si vous n’êtes pas à l’origine de cette demande, contactez {support}."
    )
    nom_html = html.escape(nom)
    lien_html = html.escape(lien, quote=True)
    explication_html = html.escape(explication)
    support_html = html.escape(support)
    corps_html = (
        '<div style="font-family:system-ui,sans-serif;max-width:560px;margin:auto;'
        'color:#18243b"><h1 style="font-size:24px">MyCounts</h1>'
        f"<p>{nom_html},</p>"
        f'<p><a href="{lien_html}" style="display:inline-block;padding:12px 18px;'
        f'border-radius:14px;background:#3558d4;color:#fff;text-decoration:none">{action}</a></p>'
        f"<p>{explication_html}</p><p>Si vous n’êtes pas à l’origine de cette demande, "
        f"contactez {support_html}.</p></div>"
    )
    return CourrielRendu(sujet=SUJETS[modele], texte=texte, html=corps_html)


def envoyer(
    configuration: Configuration, *, destinataire: str, courriel: CourrielRendu
) -> None:
    """Envoie par SSL direct ou STARTTLS; le mot de passe ne quitte jamais la config."""
    if not configuration.smtp_configure:
        raise RuntimeError("SMTP non configuré")

    message = EmailMessage()
    message["Subject"] = courriel.sujet
    message["From"] = configuration.courriel_expediteur
    message["To"] = destinataire
    message.set_content(courriel.texte)
    message.add_alternative(courriel.html, subtype="html")

    contexte = ssl.create_default_context()
    if configuration.smtp_ssl:
        with smtplib.SMTP_SSL(
            configuration.smtp_hote,
            configuration.smtp_port,
            context=contexte,
            timeout=15,
        ) as serveur:
            serveur.login(configuration.smtp_utilisateur, configuration.smtp_mot_de_passe)
            serveur.send_message(message)
        return

    with smtplib.SMTP(configuration.smtp_hote, configuration.smtp_port, timeout=15) as serveur:
        if configuration.smtp_starttls:
            serveur.starttls(context=contexte)
        serveur.login(configuration.smtp_utilisateur, configuration.smtp_mot_de_passe)
        serveur.send_message(message)
