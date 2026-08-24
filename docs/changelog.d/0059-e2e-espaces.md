# Tests de bout en bout respécifiés sur les espaces

- `vue-foyer.spec` devient `foyer-espace.spec` : la bascule est le sélecteur d’espace,
  le périmètre voyage dans `X-Mycounts-Espace`, et l’étanchéité est mesurée dans les deux
  sens plus sur l’écran (le solde de l’accueil change avec l’espace) ;
- `danger-compte-et-partage.spec` : « Quitter / Supprimer le foyer » vivent dans la
  rubrique « Foyer » d’un espace foyer, « Supprimer mon compte » dans « Mon compte » du
  personnel — chaque espace ne propose que ce qu’il administre ;
- `comptes.spec` : un compte joint se gère et se crée depuis le foyer ;
- `e2e/espaces-aide.ts` est l’unique auteur de la bascule et de la création de compte
  dans un espace ; `locator('nav')` désigne la navigation principale ;
- `make demo` ne se tue plus lui-même (`pkill -f "[p]ort …"`).
