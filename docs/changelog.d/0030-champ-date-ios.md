# Le champ de date ne dépasse plus sur iOS

Empiler les champs n'avait pas suffi : à pleine largeur, le champ de date sortait encore
de l'écran. La cause se lit dans les chiffres d'une capture d'un iPhone de 430 px — la
feuille laisse 398 px utiles, le champ Libellé en occupe 398, le champ de date 432, soit
exactement `398 + 2 × 16 px de padding + 2 × 1 px de bordure`.

**iOS ignore `box-sizing: border-box` sur `input[type="date"]`** alors qu'il l'honore sur
les champs texte. Le champ traite sa largeur comme du contenu et ajoute le reste par-dessus.

Correction dans `@supports (-webkit-touch-callout: none)`, donc iOS seulement : `appearance:
none` rend au champ le comportement d'une boîte ordinaire, et le padding horizontal retiré
fait tomber la largeur à 398 px **que `box-sizing` soit honoré ou non**. Elle tient donc
dans les deux cas plutôt que de parier sur celui qui n'est pas observable ici.

Ni Chromium, ni WebKit de bureau, ni l'émulation iPhone de Playwright ne reproduisent ce
comportement : cette règle repose sur un calcul, pas sur une mesure locale.
