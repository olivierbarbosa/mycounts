# « À venir » porte sur le mois en cours

Le calendrier listait 60 jours glissants. Il montre désormais ce qui reste à payer d'ici
la fin du mois **civil**, et l'intitulé du total le dit : « Charges restantes en août ».

La borne vient du serveur — nouvelle route `GET /api/agenda/mois-en-cours`, qui appelle
`bornes_du_mois()`. Le client ne la recalcule pas : « aujourd'hui » se lit dans le fuseau
Europe/Paris, dont le domaine est l'auteur unique, et un navigateur réglé ailleurs se
tromperait de mois les premier et dernier jours. Ce n'est pas la période budgétaire, qui
va de paie à paie.

Deux vides à distinguer, désormais : « aucun prélèvement enregistré » et « plus rien à
payer d'ici la fin du mois ». Les confondre faisait contredire à l'écran la liste des
prélèvements affichée juste au-dessus.

Le test du total gagne au passage un plafond qui lui manquait : il créait une échéance à
cinq jours, laquelle tombait le mois suivant passé le 26 — il aurait échoué quelques jours
par mois sans que rien n'ait changé.
