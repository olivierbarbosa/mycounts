# Écran d'agenda et file « à confirmer » (lot 3)

**Lot** : 3 | **Date** : 2026-08-19

Onglet Agenda : échéances des 60 prochains jours, total de la période, et file des
échéances arrivées à leur date en attente de confirmation.

## L'invariant central, vérifié à l'écran

Confirmer une échéance fait varier le solde réel et la part à confirmer en **sens
opposés**, et laisse le solde projeté **strictement identique**. Mesuré dans le vrai
navigateur : projeté 8 683 → 8 683, réel −1 099, à confirmer +1 099.

C'est désormais un test de bout en bout : si le projeté bougeait, il y aurait double
comptage — et l'écart ne se découvrirait qu'en constatant un désaccord avec la banque.

## Détails qui comptent

- L'agenda est **projeté à la volée**, jamais stocké : il suit toute modification d'une
  récurrence sans travail de mise à jour.
- Une échéance déjà matérialisée disparaît de l'agenda — l'y laisser la ferait compter
  deux fois à l'œil du lecteur.
- L'ouverture de l'agenda matérialise les échéances échues : sans ce rattrapage, une
  échéance d'hier n'apparaissait nulle part (ERREURS.md #018).
- Le total affiché est comparé à la somme des lignes réellement renvoyées : un total qui
  ne serait pas la somme de ce qu'on voit est indétectable à l'œil au-delà de trois lignes.
