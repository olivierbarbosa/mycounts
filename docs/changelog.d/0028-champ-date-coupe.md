# Le champ de date ne déborde plus de l'écran sur iPhone

Montant et date partageaient une ligne. Sur un vrai iPhone, le champ de date sortait par
la droite : iOS affiche « 5 août 2026 » là où Chromium affiche « 08/05/2026 », et refuse
de descendre sous cette largeur intrinsèque.

Sous 400 px les deux champs s'empilent — la contrainte est supprimée, pas bordée. Au-delà,
`minmax(0, 1fr)` autorise une colonne à passer sous sa largeur intrinsèque plutôt que de
déborder de la grille.

La ligne regagnée est payée par un espacement resserré sous 400 px et une note ramenée à
une ligne.

Le garde-fou gagne la mesure horizontale qui lui manquait, et surtout la mention de son
angle mort : **Chromium, WebKit de bureau et l'émulation iPhone de Playwright déclaraient
tous les trois cette mise en page conforme**. Aucun ne rend le widget de date d'iOS.
