# Palette Stripe et corrections UX

**Lot** : 3 | **Date** : 2026-08-19

## Palette

Reprise de la palette Stripe : `#635bff` primaire, `#0a2540` bleu nuit, `#f6f9fc` surface
claire, `#00d4ff` accent. Le fond passe du violet au bleu nuit.

Deux contraintes de contraste ont dicté des écarts par rapport à la palette brute :
`#635bff` sur blanc donne 4,68:1 — il passe le seuil AA de justesse et devient donc la
limite basse, l'éclaircir le casserait. En thème clair, il a fallu l'assombrir à `#4b45c6`.
Le cyan `#00d4ff` ne porte jamais de texte : il reste aux lueurs et aux liserés.

## UX

Audit contre le playbook de ui-skills.com (47 règles). Déjà respectées : cibles 44 px,
`tabular-nums`, rayons concentriques, `focus-visible`, jamais la couleur seule, labels
visibles, contraste mesuré, une seule couleur d'accent par vue.

Ajoutées :

- **confirmation avant suppression** d'une catégorie — la règle la plus importante ici,
  et elle manquait ;
- retour visuel à l'appui (`:active`, échelle 0.97) : sur mobile, sans lui on ne sait pas
  si le geste a été pris et on appuie deux fois ;
- état vide avec une **action**, pas seulement une explication ;
- interligne resserré sur les grands titres, largeur de ligne limitée à 70 caractères.

`docs/UX.md` consigne ce qui vaut spécifiquement pour une application d'argent, et une
règle du playbook que le projet enfreint sciemment (le glow sur les boutons primaires).

## Isolation de la démonstration

Les tests de bout en bout écrivaient dans la base de démonstration : Playwright réutilise
le serveur existant, et c'était celui de la démo. Base **et ports** sont désormais
distincts (5190 / 8011 contre 5189 / 8010).
