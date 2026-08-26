# La rangée du haut, allégée et réparée

- Le sélecteur d'espace devient une pilule dans la rangée des bulles, à côté de l'avatar :
  il occupait un second étage qui recouvrait le premier titre de chaque écran, de 10 px
  sans encoche et de 26 px avec.
- Sa feuille de style utilisait onze noms de jetons inexistants sur dix-neuf : elle
  s'affichait sans fond, sans bordure et sans distinction entre l'espace actif et les
  autres. Le garde-fou n°12 refuse désormais tout `var(--…)` inconnu.
- La liste des espaces s'ouvre au doigt au lieu de tenir une ligne en permanence, et passe
  par `Portail` comme toute modale.
- « Importer un relevé » quitte la rangée pour les paramètres : cinq objets ne tenaient pas
  dans les 351 px utiles d'un iPhone SE. La pilule y gagne 52 px.
- Les tests de mise en page couvrent quatre téléphones — 375, 390, 412 et 430 px — avec
  leurs encoches simulées, au lieu d'une seule largeur sans inset.
