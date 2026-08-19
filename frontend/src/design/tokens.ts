/**
 * Auteur UNIQUE des couleurs, rayons, espacements et graisses du projet.
 *
 * Aucun autre fichier n'écrit de valeur littérale : le garde-fou n°9
 * (`scripts/verifier_couleurs.py`) refuse tout `#hex` ou `rgb()` ailleurs.
 *
 * Direction artistique : **néon et Liquid Glass**, sur une palette lavande —
 * `#8C56D4` primaire, `#DC95FF` mauve clair, `#FFBEFB` rose, `#FFF4BF` crème.
 * Fond en dégradé violet profond, surfaces en verre laiteux, montants en display avec
 * les centimes réduits.
 *
 * Contrainte mesurée avant d'écrire une ligne : `#8C56D4` donne 4,53:1 avec du blanc,
 * soit le seuil AA franchi de justesse. C'est donc le SEUL des quatre qui peut porter du
 * texte clair ; les trois autres vont aux lueurs, aux liserés et aux pastilles.
 *
 * Contrepartie non négociable de cette DA : sur du verre, le contraste dépend de ce qui
 * défile dessous. Toutes les paires texte/fond définies ici sont donc vérifiées
 * automatiquement (`frontend/e2e/contraste.spec.ts`) dans les trois positions du réglage
 * de transparence. Une teinte plus jolie mais moins lisible fait échouer la CI.
 */

/** Palette sombre — thème principal. */
export const couleursSombres = {
  /** Le fond n'est plus un aplat : deux arrêts de dégradé, du violet profond au presque
   *  noir violacé. Le premier sert aussi de couleur de repli. */
  // Violet profond dérivé du primaire. Un fond doit rester un fond : assez présent pour
  // porter la DA, assez discret pour que l'œil aille aux montants.
  fond: '#1B0F33',
  fondHaut: '#2E1A55',
  fondBas: '#120920',

  /** Surfaces en verre : très peu opaques, c'est le flou qui fait le matériau. */
  surface: 'rgba(255, 255, 255, 0.07)',
  surfaceHaute: 'rgba(255, 255, 255, 0.12)',
  bordure: 'rgba(255, 255, 255, 0.14)',
  /** Repli opaque quand la transparence est désactivée ou non supportée. */
  surfaceOpaque: '#251646',

  texte: '#FFFFFF',
  // Ces deux opacités ne sont pas choisies à l'œil : ce sont les plus basses qui
  // passent encore 4,5:1 sur le dégradé de fond, avec une marge. Mesuré, pas supposé.
  texteAttenue: 'rgba(255, 255, 255, 0.80)',
  texteFaible: 'rgba(255, 255, 255, 0.62)',

  /** Primaire de la palette. Mesuré à 4,53:1 avec du blanc : il passe AA de justesse et
   *  constitue la limite basse — l'éclaircir casserait le contraste. */
  accent: '#8C56D4',
  accentClair: '#DC95FF',
  accentContraste: '#FFFFFF',
  /** Rose de la palette. Trop lumineux pour porter du texte : lueurs et liserés. */
  neon: '#FFBEFB',
  /** Crème de la palette. Même règle : accent chaud, jamais de fond de libellé. */
  chaud: '#FFF4BF',

  credit: '#34D399',
  /* Éclairci de 31 % vers le blanc par rapport au #FB7185 d'origine : sous le halo, le
   *  rose initial tombait à 3,23:1. Ce défaut est antérieur à l'animation du halo — la
   *  sonde ne mesurait simplement pas le halo. */
  debit: '#FC9DAB',
  alerte: '#FBBF24',

  verreTeinte: 'rgba(255, 255, 255, 0.09)',
  verreBordSombre: 'rgba(12, 5, 26, 0.55)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.42)',
  verreOpaque: '#251646',

  /** Lueurs néon. Décoratives : jamais le seul porteur d'une information. */
  lueurAccent: 'rgba(140, 86, 212, 0.48)',
  lueurNeon: 'rgba(255, 190, 251, 0.28)',

  /** Halos de fond. Ils passent DERRIÈRE le contenu et ne portent jamais de texte :
   *  c'est ce qui permet de les rendre francs sans dégrader la lisibilité. */
  /* 0,20 et non 0,26 : au-delà, le halo éclaircit assez le fond pour faire tomber le
   *  rouge des débits sous 4,5:1, et colle le vert des crédits à 4,52:1 — sans marge pour
   *  la moindre retouche future. Mesuré par `e2e/contraste.spec.ts` une fois la sonde
   *  rendue capable de voir le halo, ce qu'elle ne savait pas faire. */
  haloHaut: 'rgba(220, 149, 255, 0.20)',
  haloBas: 'rgba(255, 190, 251, 0.13)',
  /** Liseré lumineux sur les surfaces en verre. */
  lueurBordure: 'rgba(220, 149, 255, 0.30)',

  /** Habillage des boutons d'action. Auteur unique : chaque écran s'y réfère, aucun ne
   *  recompose son propre dégradé — deux boutons voisins aux dégradés légèrement
   *  différents se remarquent immédiatement. */
  /** L'arrêt le plus CLAIR ne peut pas dépasser #635BFF : mesuré, il donne 4,68:1 avec
   *  du blanc et constitue déjà la limite basse du seuil AA. Un dégradé qui s'éclaircit
   *  vers le haut, comme la première version (#7A73FF), tombait à 3,67:1 — le contraste
   *  arbitre, pas l'esthétique. Le volume vient donc de l'assombrissement vers le bas. */
  degradeAccent: 'linear-gradient(180deg, #8C56D4 0%, #7F4CC4 55%, #6C3FAA 100%)',
  degradeAccentSurvol: 'linear-gradient(180deg, #9560DE 0%, #8752CE 55%, #7345B4 100%)',
  /** Liseré interne, jamais externe : un contour extérieur agrandirait la cible et
   *  décalerait l'alignement d'une rangée de boutons. */
  contourClair: 'rgba(255, 255, 255, 0.22)',
  contourSombre: 'rgba(12, 5, 26, 0.35)',
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
export const textureSombre = {
  grainOpacite: '0.055',
}

export const textureClaire = {
  grainOpacite: '0.03',
}

/** Palette claire. Mêmes rôles, mêmes noms : un composant ne connaît que les rôles. */
export const couleursClaires = {
  fond: '#FBF7FF',
  fondHaut: '#F6EDFF',
  fondBas: '#FFFDF5',

  surface: 'rgba(255, 255, 255, 0.72)',
  surfaceHaute: 'rgba(255, 255, 255, 0.88)',
  bordure: 'rgba(43, 20, 74, 0.14)',
  surfaceOpaque: '#FFFFFF',

  texte: '#2B144A',
  texteAttenue: 'rgba(43, 20, 74, 0.82)',
  texteFaible: 'rgba(43, 20, 74, 0.66)',

  // Assombri par rapport au #8C56D4 de la palette : sur fond clair, le primaire tel quel
  // ne tient pas le seuil AA avec du texte blanc.
  accent: '#6E3DAE',
  accentClair: '#8C56D4',
  accentContraste: '#FFFFFF',
  neon: '#A63C9E',
  chaud: '#8A6A12',

  credit: '#047857',
  debit: '#BE123C',
  alerte: '#B45309',

  verreTeinte: 'rgba(255, 255, 255, 0.62)',
  verreBordSombre: 'rgba(43, 20, 74, 0.16)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.95)',
  verreOpaque: '#FFFFFF',

  lueurAccent: 'rgba(140, 86, 212, 0.22)',
  lueurNeon: 'rgba(220, 149, 255, 0.20)',

  haloHaut: 'rgba(220, 149, 255, 0.18)',
  haloBas: 'rgba(255, 244, 191, 0.22)',
  lueurBordure: 'rgba(110, 61, 174, 0.18)',

  degradeAccent: 'linear-gradient(180deg, #7B47BE 0%, #6E3DAE 55%, #5D3193 100%)',
  degradeAccentSurvol: 'linear-gradient(180deg, #8951CC 0%, #7B47BE 55%, #6A3AA6 100%)',
  contourClair: 'rgba(255, 255, 255, 0.28)',
  contourSombre: 'rgba(43, 20, 74, 0.20)',
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
