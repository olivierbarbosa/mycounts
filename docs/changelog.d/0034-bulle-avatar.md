# Les réglages passent derrière une bulle d'avatar

L'onglet Réglages disparaît de la barre : trois onglets se lisent d'un coup d'œil là où
quatre demandent de choisir, et le paramétrage n'est pas une destination qu'on visite
aussi souvent que ses dépenses.

À sa place, une **bulle d'avatar** fixe en haut à gauche de tous les écrans. Elle ouvre un
panneau à sous-menus — Mon compte, Comptes bancaires, Catégories, Apparence, Foyer — qui
entre par la droite, comme les écrans poussés d'iOS. L'avatar y grandit depuis son coin :
c'est ce qui relie la bulle à la page qui vient de s'ouvrir.

Tout le mouvement s'arrête sous `prefers-reduced-motion`, et n'est joué que par `transform`
et `opacity` — le compositeur s'en charge sans repeindre, ce qui compte sous des surfaces
en verre qui refont leur flou à chaque repeinte.

## Deux dettes soldées en chemin

- La **largeur du rail** (232 px) était recopiée dans cinq feuilles de style : celle qui le
  dessine et quatre écrans qui décalent leur contenu. Elle vit désormais dans `tokens.ts`.
- Le **dégradé de page** est nommé une fois et repris par le panneau : sans cela, ouvrir
  les réglages faisait disparaître le fond de l'application.

## Le garde-fou mesurait pendant l'animation

Le contrôle des modales déclarait tous les boutons du panneau hors écran. Il mesurait au
moment où le panneau était encore à droite, en train d'entrer. Il attend maintenant la fin
des animations — les infinies exceptées, dont la promesse ne se résout jamais. Un rouge
faux est pire qu'un vert faux : il apprend à ne plus croire son garde-fou.

Le panneau est un écran entier de texte : la sonde de contraste le mesure désormais dans
les deux thèmes, et sait rougir dessus — vérifié en abîmant une de ses couleurs.
