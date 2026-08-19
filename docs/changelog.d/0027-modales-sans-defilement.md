# Sur téléphone, aucune modale ne demande plus de défilement

Le détail d'une opération présentait « Enregistrer » et « Supprimer » sous la ligne de
flottaison : la feuille avait l'air terminée alors qu'elle ne l'était pas.

- Le doublon disparaît : la date figurait à la fois en fait non modifiable et en champ
  modifiable. Un seul auteur, le champ.
- Les faits (compte, état, origine) passent d'une colonne de trois lignes à une ligne qui
  se replie. Montant et date se partagent une ligne.
- Les feuilles sont serrées d'abord et ne retrouvent leur air qu'au-delà de 480 px.
- Pendant la confirmation de suppression, le formulaire s'efface : on ne demande pas de
  trancher en laissant sous les yeux quatre champs qu'on ne peut plus valider.

Garde-fou : `e2e/modales-sans-defilement.spec.ts` ouvre chaque modale sur **390 × 664** —
la hauteur réellement utile d'un téléphone, barre du navigateur déduite, et non les 844 px
de la fiche technique. Il échoue si une feuille déborde d'un seul pixel ou si un bouton
sort de l'écran, y compris dans l'état de confirmation.
