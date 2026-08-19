# Montant et date empilés sur toute largeur de téléphone

Le seuil d'empilement était à 400 px ; l'appareil qui montrait le défaut fait 430 px de
large. Le champ de date y débordait toujours.

Le seuil passe à 600 px : aucune largeur de téléphone ne partage plus cette ligne. C'est
un choix par construction et non par mesure — aucun moteur disponible localement ne rend
le widget de date d'iOS, donc aucune valeur intermédiaire ne serait vérifiable.

Le garde-fou tourne maintenant sur **deux largeurs** (390 × 664 dans Safari, 430 × 839 en
web app installée) au lieu d'une seule, et mesure la largeur en plus de la hauteur.
