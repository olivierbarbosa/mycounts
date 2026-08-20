/**
 * Auteur UNIQUE des couleurs, rayons, espacements et graisses du projet.
 *
 * Aucun autre fichier n'écrit de valeur littérale : le garde-fou n°9
 * (`scripts/verifier_couleurs.py`) refuse tout `#hex` ou `rgb()` ailleurs.
 *
 * Direction artistique : **bleu ardoise et Liquid Glass**, sur la palette choisie par
 * Olivier le 20 août 2026 — `#334155` ardoise, `#0EA5E9` ciel, `#7DD3FC` ciel clair,
 * `#E0F2FE` brume, `#F1F5F9` neige. Elle remplace la palette lavande d'origine.
 *
 * Contrainte mesurée AVANT d'écrire une ligne, et c'est elle qui commande la répartition
 * des rôles : `#0EA5E9` avec du texte blanc ne donne que **2,77:1** là où AA en demande
 * 4,5. Il ne peut donc porter aucun texte. Il va aux liserés, aux lueurs et aux jauges du
 * thème SOMBRE, où il mesure 6,44:1 sur le fond. En thème clair il tombe à 2,53:1 même
 * comme aplat graphique — sous le seuil de 3:1 des composants non textuels — et s'y
 * assombrit donc en `#0284C7` (3,74:1), puis en `#0369A1` (5,42:1) dès qu'il porte du
 * texte. Le violet suivait déjà exactement cette règle.
 *
 * Les boutons pleins ne montent jamais plus clair que `#0369A1`, mesuré à 5,93:1 avec du
 * blanc : leur volume vient de l'assombrissement vers le bas, jamais d'un éclaircissement
 * vers le haut.
 *
 * Contrepartie non négociable de cette DA : sur du verre, le contraste dépend de ce qui
 * défile dessous. Toutes les paires texte/fond définies ici sont donc vérifiées
 * automatiquement (`frontend/e2e/contraste.spec.ts`) dans les trois positions du réglage
 * de transparence. Une teinte plus jolie mais moins lisible fait échouer la CI.
 */

/** Palette sombre — dérivée de la même famille que la claire, et non d'une seconde DA :
 *  l'ardoise `#334155` y devient le fond en descendant à `#0F172A`, et le ciel `#0EA5E9`
 *  y prend enfin la place d'accent pleinement lisible que le thème clair lui refuse. */
export const couleursSombres = {
  /** Le fond n'est pas un aplat : trois arrêts, de l'ardoise au presque noir bleuté.
   *  Le premier sert aussi de couleur de repli. */
  fond: '#0F172A',
  fondHaut: '#1E293B',
  fondBas: '#020617',

  /** Surfaces en verre : très peu opaques, c'est le flou qui fait le matériau. */
  surface: 'rgba(255, 255, 255, 0.07)',
  surfaceHaute: 'rgba(255, 255, 255, 0.12)',
  bordure: 'rgba(255, 255, 255, 0.14)',
  /** Repli opaque quand la transparence est désactivée ou non supportée. */
  surfaceOpaque: '#1E293B',

  /** L'encre n'est pas du blanc pur mais la neige de la palette : sur un fond bleuté,
   *  du #FFFFFF franc paraît plus dur que le reste de l'interface. 16,3:1 sur le fond. */
  texte: '#F1F5F9',
  // Ces deux opacités ne sont pas choisies à l'œil : ce sont les plus basses qui
  // passent encore 4,5:1 sur le dégradé de fond, avec une marge. Mesuré, pas supposé.
  texteAttenue: 'rgba(241, 245, 249, 0.80)',
  texteFaible: 'rgba(241, 245, 249, 0.62)',

  /** Ciel de la palette, à sa valeur pure. Sur ce fond il mesure 6,44:1 : c'est le seul
   *  des deux thèmes où `#0EA5E9` peut être employé tel quel. */
  accent: '#0EA5E9',
  /** Ciel clair. Pour les BORDURES, les lueurs et les indicateurs — et, ici seulement,
   *  pour du texte : 10,7:1 sur le fond. La règle reste que le texte coloré se mesure
   *  avant d'être posé, jamais qu'une teinte est « pour le texte » par nature. */
  accentClair: '#7DD3FC',
  accentContraste: '#FFFFFF',
  /** Même ciel clair en rôle de néon : lueurs et liserés. */
  neon: '#7DD3FC',
  /** Brume de la palette. Accent froid et pâle, jamais de fond de libellé. */
  chaud: '#E0F2FE',

  credit: '#34D399',
  /* Le rouge d'origine, conservé sur décision explicite d'Olivier — la SECONDE fois, après
   *  avoir vu le chiffre. Sous le halo bleu il mesure 3,51:1 là où AA en demande 4,5.
   *  `#FDA4AF` le faisait passer à 5,00:1, au prix d'un rose nettement plus pâle.
   *
   *  Attention au chiffre que l'on cite : sur le fond NU `#0F172A`, ce rouge mesure
   *  6,63:1, et j'ai d'abord conclu de là que la dérogation de la palette lavande était
   *  devenue inutile. C'est faux — les montants ne sont jamais posés sur le fond nu mais
   *  sur le halo, qui l'éclaircit. La sonde de `contraste.spec.ts` mesure le rendu réel et
   *  a rendu le bon verdict ; mon calcul sur aplat mesurait autre chose que le sujet.
   *
   *  La dérogation n'est donc pas une exemption : son plancher vaut la valeur MESURÉE, si
   *  bien que toute dégradation supplémentaire de ce rouge — un halo plus clair, une
   *  opacité plus basse — fera rougir le test. */
  debit: '#FB7185',
  alerte: '#FBBF24',

  verreTeinte: 'rgba(255, 255, 255, 0.09)',
  verreBordSombre: 'rgba(2, 6, 23, 0.55)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.42)',
  verreOpaque: '#1E293B',

  /** Lueurs. Décoratives : jamais le seul porteur d'une information. */
  lueurAccent: 'rgba(14, 165, 233, 0.48)',
  /* Lueurs des deux sens, pour le halo qui éclaire le solde de l'accueil. Elles ne portent
   *  aucun texte : le chiffre est posé PAR-DESSUS en couleur pleine, et c'est lui que la
   *  sonde de contraste mesure. */
  lueurDebit: 'rgba(251, 113, 133, 0.34)',
  lueurCredit: 'rgba(52, 211, 153, 0.30)',
  lueurNeon: 'rgba(125, 211, 252, 0.28)',

  /** Halos de fond. Ils passent DERRIÈRE le contenu et ne portent jamais de texte :
   *  c'est ce qui permet de les rendre francs sans dégrader la lisibilité. */
  haloHaut: 'rgba(14, 165, 233, 0.26)',
  haloBas: 'rgba(125, 211, 252, 0.13)',
  /** Liseré lumineux sur les surfaces en verre. */
  lueurBordure: 'rgba(125, 211, 252, 0.30)',

  /** Habillage des boutons d'action. Auteur unique : chaque écran s'y réfère, aucun ne
   *  recompose son propre dégradé — deux boutons voisins aux dégradés légèrement
   *  différents se remarquent immédiatement. */
  /** L'arrêt le plus CLAIR ne peut pas dépasser #0369A1 : mesuré, il donne 5,93:1 avec du
   *  blanc. Partir du #0EA5E9 de la palette tomberait à 2,77:1 — le contraste arbitre,
   *  pas l'esthétique. Le volume vient donc de l'assombrissement vers le bas. */
  degradeAccent: 'linear-gradient(180deg, #0369A1 0%, #075985 55%, #0C4A6E 100%)',
  degradeAccentSurvol: 'linear-gradient(180deg, #0A7BB8 0%, #0369A1 55%, #075985 100%)',
  /** Liseré interne, jamais externe : un contour extérieur agrandirait la cible et
   *  décalerait l'alignement d'une rangée de boutons. */
  contourClair: 'rgba(255, 255, 255, 0.22)',
  contourSombre: 'rgba(2, 6, 23, 0.35)',
} as const

/** Force du grain posé sur le fond, par thème.
 *
 *  Le grain n'a pas de teinte : c'est du bruit achromatique généré par le filtre SVG de
 *  `global.css`, donc il ne consomme aucune couleur de la palette. Seule son intensité
 *  se règle ici, et elle diffère par thème : sur un fond sombre le bruit se voit à moitié
 *  moins qu'un même bruit sur un fond clair, où il vire vite au sale.
 *
 *  Deux rôles, au-delà du grain de la matière : il casse les bandes du dégradé radial,
 *  qui se voient sur les écrans OLED des téléphones, et il donne au verre quelque chose à
 *  flouter — un flou sur un aplat parfait ne se distingue pas d'un aplat.
 */
/** Grandeurs de disposition partagées par plusieurs écrans.
 *
 *  La largeur du rail était recopiée dans trois feuilles de style : celle de la barre qui
 *  le dessine, et celles des écrans qui décalent leur contenu pour ne pas passer dessous.
 *  Trois auteurs pour une même mesure, dont deux qui n'auraient appris un changement que
 *  par un chevauchement à l'écran.
 */
/**
 * Échelle d'empilement. AUTEUR UNIQUE des `z-index` du projet.
 *
 * Elle est née d'un défaut mesurable : les écrans poussés depuis une bulle — calendrier,
 * détail d'épargne, paramètres — étaient au plan 30, et les feuilles modales au plan 20.
 * Toute feuille ouverte DEPUIS l'un de ces écrans s'affichait donc derrière lui : le
 * formulaire existait, était focalisable, recevait la frappe, et restait invisible. Il
 * fallait fermer l'écran pour découvrir ce qu'on venait de saisir.
 *
 * Aucun des deux nombres n'était faux en lui-même ; ils avaient simplement été choisis
 * dans deux fichiers différents, à deux moments différents, sans que personne ne tienne la
 * liste. C'est précisément ce qu'une donnée à auteur unique empêche.
 *
 * L'ordre se lit de bas en haut, et un composant ne choisit jamais un nombre : il choisit
 * un RÔLE. Ajouter un plan intermédiaire se fait ici, une fois.
 */
export const plans = {
  /** Halos et grain du fond, sous le contenu. */
  fond: '-1',
  /** Poignée de glissement de retour, au-dessus du contenu de son écran. */
  poignee: '5',
  /** Barre d'onglets et rail latéral. */
  navigation: '10',
  /** Bulles du haut. Au-dessus de la navigation : elles se recouvrent au format bureau. */
  bulle: '15',
  /** Écran plein poussé par une bulle. Couvre navigation et bulles — il les remplace. */
  ecran: '30',
  /** Feuille modale. AU-DESSUS des écrans pleins, sans quoi elle ouvre dans le vide. */
  feuille: '40',
  /** Confirmation posée dans une feuille : le dernier mot revient à elle. */
  confirmation: '50',
} as const

export const disposition = {
  /** Largeur du rail latéral, au-delà de 1024 px. */
  largeurRail: '232px',
  /** Place réservée en haut de chaque écran pour la bulle d'avatar, qui est fixe et ne
   *  pousse donc rien : sans cette réserve, elle recouvrirait le premier titre. */
  reserveBulle: '56px',
}

export const textureSombre = {
  grainOpacite: '0.055',
}

export const textureClaire = {
  grainOpacite: '0.03',
}

/** Palette claire. Mêmes rôles, mêmes noms : un composant ne connaît que les rôles. */
export const couleursClaires = {
  fond: '#F1F5F9',
  fondHaut: '#E0F2FE',
  /** Seul ton dérivé hors des cinq choisis : le dégradé a besoin de s'éclaircir vers le
   *  bas, et reprendre `#F1F5F9` y aurait produit un aplat sur la moitié de la hauteur. */
  fondBas: '#F8FAFC',

  surface: 'rgba(255, 255, 255, 0.72)',
  surfaceHaute: 'rgba(255, 255, 255, 0.88)',
  bordure: 'rgba(51, 65, 85, 0.14)',
  surfaceOpaque: '#FFFFFF',

  /** L'ardoise de la palette. 9,45:1 sur le fond, 10,4:1 sur une surface blanche. */
  texte: '#334155',
  /* Ces deux opacités ne sont pas reprises du thème sombre ni choisies à l'œil : elles ont
   *  été MESURÉES contre le plus sombre des trois arrêts du dégradé de fond, `#E0F2FE`.
   *
   *  Les valeurs héritées de la palette lavande (0,82 et 0,66) ne tiennent plus ici, et
   *  `e2e/contraste.spec.ts` l'a dit avant moi : le violet `#2B144A` était nettement plus
   *  foncé que l'ardoise `#334155`, si bien qu'à 0,66 le texte faible tombait à 3,45:1
   *  pour un seuil à 4,5. À 0,78 il mesure 4,97:1 sur le pire fond.
   *
   *  Le texte atténué monte à 0,92 pour la même raison, et pour une seconde : à 0,82 il ne
   *  se serait plus distingué d'un texte faible remonté à 0,78, et deux rôles qui rendent
   *  la même chose à l'écran n'en font plus qu'un. */
  texteAttenue: 'rgba(51, 65, 85, 0.92)',
  texteFaible: 'rgba(51, 65, 85, 0.78)',

  // Assombri par rapport au #0EA5E9 de la palette, comme le violet l'était avant lui : le
  // ciel pur ne fait que 2,53:1 sur ce fond — sous les 3:1 exigés d'un composant
  // graphique, donc inutilisable même pour une barre de jauge. #0284C7 donne 3,74:1.
  accent: '#0284C7',
  /** Ici l'accent clair est plus SOMBRE que l'accent : le rôle est « la teinte qui peut
   *  porter du texte », pas « la teinte la plus lumineuse ». 5,42:1 sur le fond. */
  accentClair: '#0369A1',
  accentContraste: '#FFFFFF',
  neon: '#0EA5E9',
  chaud: '#7DD3FC',

  credit: '#047857',
  debit: '#BE123C',
  alerte: '#B45309',

  verreTeinte: 'rgba(255, 255, 255, 0.62)',
  verreBordSombre: 'rgba(51, 65, 85, 0.16)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.95)',
  verreOpaque: '#FFFFFF',

  lueurAccent: 'rgba(14, 165, 233, 0.22)',
  lueurDebit: 'rgba(190, 18, 60, 0.16)',
  lueurCredit: 'rgba(4, 120, 87, 0.16)',
  lueurNeon: 'rgba(125, 211, 252, 0.20)',

  haloHaut: 'rgba(14, 165, 233, 0.18)',
  haloBas: 'rgba(125, 211, 252, 0.22)',
  lueurBordure: 'rgba(3, 105, 161, 0.18)',

  degradeAccent: 'linear-gradient(180deg, #0369A1 0%, #075985 55%, #0C4A6E 100%)',
  degradeAccentSurvol: 'linear-gradient(180deg, #0A7BB8 0%, #0369A1 55%, #075985 100%)',
  contourClair: 'rgba(255, 255, 255, 0.28)',
  contourSombre: 'rgba(51, 65, 85, 0.20)',
} as const

/**
 * Rayons concentriques : le rayon d'un élément imbriqué se DÉDUIT de son parent,
 * il ne se choisit pas.
 */
export const rayons = {
  petit: '12px',
  moyen: '18px',
  grand: '26px',
  pilule: '999px',
} as const

export const espacements = {
  xs: '4px',
  s: '8px',
  m: '12px',
  l: '16px',
  xl: '24px',
  xxl: '32px',
} as const

export const typographie = {
  familleTexte: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif",
  familleChiffres:
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif",
  grasNormal: '400',
  grasMoyen: '600',
  grasFort: '700',
  grasDisplay: '800',
} as const

/**
 * Recette du Liquid Glass, telle qu'affinée dans iOS 27 : flou et saturation, plus un
 * bord assombri et un reflet spéculaire qui rendent la couche lisible sur un contenu
 * complexe. Pas de réfraction : `backdrop-filter` floute, il ne dévie pas la lumière.
 */
export const verre = {
  flou: '28px',
  saturation: '190%',
  /** Trois positions du réglage utilisateur, reprises d'iOS 27. */
  opaciteClaire: '0.35',
  opaciteMoyenne: '0.7',
  opaciteOpaque: '1',
} as const

/**
 * Points de rupture. UNIQUEMENT en `min-width` : l'application est écrite pour mobile
 * d'abord, le bureau est une mise en page à part entière (rail latéral), pas un
 * étirement.
 */
export const ruptures = {
  tablette: '600px',
  bureau: '1024px',
} as const

/** Cible tactile minimale (Apple HIG). Vérifiée par le garde-fou n°10. */
export const cibleTactileMinimale = '44px'

type Dictionnaire = Record<string, string>

const enKebab = (nom: string): string => nom.replace(/[A-Z]/g, (l) => `-${l.toLowerCase()}`)

const enVariables = (prefixe: string, valeurs: Dictionnaire): string =>
  Object.entries(valeurs)
    .map(([nom, valeur]) => `  --${prefixe}-${enKebab(nom)}: ${valeur};`)
    .join('\n')

/**
 * Produit la feuille de variables CSS consommée par les composants.
 *
 * Les composants n'écrivent que `var(--couleur-accent)` : ils ignorent la valeur, donc
 * changer la palette ne touche aucun composant.
 */
export const feuilleDeTokens = (): string => `
:root {
${enVariables('couleur', couleursClaires)}
${enVariables('rayon', rayons)}
${enVariables('espace', espacements)}
${enVariables('typo', typographie)}
${enVariables('verre', verre)}
${enVariables('texture', textureClaire)}
${enVariables('disposition', disposition)}
${enVariables('plan', plans)}
  --cible-tactile: ${cibleTactileMinimale};
  --verre-opacite: var(--verre-opacite-moyenne);
  color-scheme: light dark;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme='clair']) {
${enVariables('couleur', couleursSombres)}
${enVariables('texture', textureSombre)}
  }
}

:root[data-theme='sombre'] {
${enVariables('couleur', couleursSombres)}
${enVariables('texture', textureSombre)}
}
`
