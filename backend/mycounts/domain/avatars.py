"""Transformation d'une image reçue en avatar servable.

Une seule fonction publique, `normaliser`, et une règle : **rien de ce qui entre ne
ressort tel quel**. L'image est décodée, réorientée, recadrée, puis RÉENCODÉE. Ce
réencodage n'est pas un confort d'affichage, il porte trois garanties que le contrôle du
type déclaré ne donne pas :

1. **C'est bien une image.** Un fichier téléversé annonce son type lui-même ; le décoder
   est la seule façon de le vérifier. Servir tel quel ce qui prétendait être un PNG
   revient à héberger le fichier de n'importe qui sous son propre domaine.
2. **Les métadonnées partent.** Une photo d'iPhone transporte la position GPS de l'endroit
   où elle a été prise, l'appareil, la date. Un avatar est vu par les autres membres du
   foyer : y laisser les coordonnées de son domicile serait une fuite silencieuse, faite
   par quelqu'un qui croyait n'envoyer qu'un portrait.
3. **La taille est bornée pour de bon.** Une image de 20 000 pixels de côté tient en peu
   d'octets une fois compressée et en occupe un gigaoctet une fois décodée. La borne porte
   donc sur les DIMENSIONS avant décodage complet, pas seulement sur le poids du fichier.

L'orientation EXIF est appliquée avant tout : les photos prises au téléphone sont
enregistrées dans le sens du capteur et redressées par une étiquette. La retirer sans
l'appliquer — ce que fait tout réencodage naïf — couche le portrait.
"""

from __future__ import annotations

import io
from typing import Final

from PIL import Image, ImageOps, UnidentifiedImageError

# Poids maximal accepté en entrée. Une photo d'iPhone récente pèse 2 à 5 Mo ; huit laisse
# de la marge sans permettre d'occuper la base avec un seul envoi.
POIDS_MAXIMAL_OCTETS: Final = 8 * 1024 * 1024

# Dimensions maximales en entrée, vérifiées AVANT le décodage complet. Une « bombe de
# décompression » est une image légère qui explose en mémoire une fois développée.
COTE_MAXIMAL_ENTREE: Final = 12_000

# Côté de l'avatar produit. 512 suffit pour un affichage à 128 px sur un écran à trois
# fois la densité, ce qui est le plus grand usage qu'en fasse l'application.
COTE: Final = 512

TYPE_MIME: Final = "image/webp"

# WebP : accepté par Safari depuis la version 14, et deux fois plus léger que JPEG à
# qualité égale. Le format de SORTIE est unique — servir tantôt du PNG tantôt du JPEG
# obligerait à retenir lequel, pour un gain nul.
_QUALITE: Final = 82


class ImageRefusee(Exception):
    """Motif lisible par un humain, destiné à être affiché tel quel."""


def normaliser(donnees: bytes) -> bytes:
    """Rend un WebP carré de `COTE` pixels, sans métadonnées.

    Lève `ImageRefusee` avec un message montrable. Toute erreur de décodage est traitée
    comme un refus et jamais propagée : un fichier illisible est une saisie invalide, pas
    une panne du serveur, et un 500 enverrait chercher un incident inexistant.
    """
    if not donnees:
        raise ImageRefusee("Le fichier est vide.")
    if len(donnees) > POIDS_MAXIMAL_OCTETS:
        raise ImageRefusee(
            f"L’image dépasse {POIDS_MAXIMAL_OCTETS // (1024 * 1024)} Mo. "
            "Choisissez-en une plus légère."
        )

    try:
        # Première ouverture : l'en-tête seul est lu, les dimensions sont connues sans que
        # les pixels soient développés en mémoire. C'est là que se refuse une bombe.
        with Image.open(io.BytesIO(donnees)) as sonde:
            largeur, hauteur = sonde.size
    except UnidentifiedImageError:
        raise ImageRefusee(
            "Ce fichier n’est pas une image reconnue. Le format HEIC de l’iPhone n’est "
            "pas accepté : choisissez « Plus compatible » dans Réglages → Appareil "
            "photo → Formats, ou envoyez une capture d’écran."
        ) from None
    except Exception:
        raise ImageRefusee("Ce fichier n’a pas pu être lu comme une image.") from None

    if largeur > COTE_MAXIMAL_ENTREE or hauteur > COTE_MAXIMAL_ENTREE:
        raise ImageRefusee(
            f"L’image dépasse {COTE_MAXIMAL_ENTREE} pixels de côté."
        )
    if largeur == 0 or hauteur == 0:
        raise ImageRefusee("Cette image n’a aucune dimension.")

    try:
        with Image.open(io.BytesIO(donnees)) as image:
            # Redressée AVANT tout recadrage : appliquer l'étiquette d'orientation après
            # avoir coupé reviendrait à couper dans le mauvais sens.
            redressee = ImageOps.exif_transpose(image) or image
            # `fit` recadre au centre puis met à l'échelle : une photo en portrait donne
            # un carré pris au milieu plutôt qu'un visage écrasé.
            carre = ImageOps.fit(
                redressee.convert("RGB"), (COTE, COTE), method=Image.Resampling.LANCZOS
            )
            sortie = io.BytesIO()
            # Ni `exif=`, ni `icc_profile=` : ce qui n'est pas recopié ne survit pas. C'est
            # ainsi que la position GPS disparaît — par omission, sans liste de champs à
            # tenir à jour, qui aurait vieilli au premier format nouveau.
            carre.save(sortie, format="WEBP", quality=_QUALITE, method=4)
    except ImageRefusee:
        raise
    except Exception:
        raise ImageRefusee("Cette image n’a pas pu être convertie.") from None

    return sortie.getvalue()
