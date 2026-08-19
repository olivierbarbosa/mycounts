/**
 * Auteur UNIQUE des couleurs, rayons, espacements et graisses du projet.
 *
 * Aucun autre fichier n'écrit de valeur littérale : le garde-fou n°9
 * (`scripts/verifier_couleurs.py`) refuse tout `#hex` ou `rgb()` ailleurs.
 *
 * Direction artistique : **néon et Liquid Glass**, sur la palette Stripe —
 * `#635bff` primaire, `#0a2540` bleu nuit, `#f6f9fc` surface claire, `#00d4ff` accent.
 * Fond en dégradé bleu nuit, surfaces en verre laiteux, montants en display avec les
 * centimes réduits.
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
  // Bleu nuit de la palette Stripe. Un fond doit rester un fond : assez présent pour
  // porter la DA, assez discret pour que l'œil aille aux montants.
  fond: '#0A2540',
  fondHaut: '#143A5C',
  fondBas: '#061726',

  /** Surfaces en verre : très peu opaques, c'est le flou qui fait le matériau. */
  surface: 'rgba(255, 255, 255, 0.07)',
  surfaceHaute: 'rgba(255, 255, 255, 0.12)',
  bordure: 'rgba(255, 255, 255, 0.14)',
  /** Repli opaque quand la transparence est désactivée ou non supportée. */
  surfaceOpaque: '#123253',

  texte: '#FFFFFF',
  // Ces deux opacités ne sont pas choisies à l'œil : ce sont les plus basses qui
  // passent encore 4,5:1 sur le dégradé de fond, avec une marge. Mesuré, pas supposé.
  texteAttenue: 'rgba(255, 255, 255, 0.80)',
  texteFaible: 'rgba(255, 255, 255, 0.62)',

  /** Primaire Stripe. Il porte du texte blanc : mesuré à 4,68:1, il passe le seuil AA
   *  de justesse et constitue donc la limite basse — l'éclaircir casserait le contraste. */
  accent: '#635BFF',
  accentClair: '#A5A0FF',
  accentContraste: '#FFFFFF',
  /** Accent cyan Stripe. Trop lumineux pour porter du texte : réservé aux lueurs, aux
   *  liserés et aux pastilles, jamais à un libellé. */
  neon: '#00D4FF',

  credit: '#34D399',
  debit: '#FB7185',
  alerte: '#FBBF24',

  verreTeinte: 'rgba(255, 255, 255, 0.09)',
  verreBordSombre: 'rgba(3, 16, 30, 0.55)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.42)',
  verreOpaque: '#123253',

  /** Lueurs néon. Décoratives : jamais le seul porteur d'une information. */
  lueurAccent: 'rgba(99, 91, 255, 0.45)',
  lueurNeon: 'rgba(0, 212, 255, 0.32)',

  /** Halos de fond. Ils passent DERRIÈRE le contenu et ne portent jamais de texte :
   *  c'est ce qui permet de les rendre francs sans dégrader la lisibilité. */
  haloHaut: 'rgba(99, 91, 255, 0.30)',
  haloBas: 'rgba(0, 212, 255, 0.14)',
  /** Liseré lumineux sur les surfaces en verre. */
  lueurBordure: 'rgba(165, 160, 255, 0.32)',
} as const

/** Palette claire. Mêmes rôles, mêmes noms : un composant ne connaît que les rôles. */
export const couleursClaires = {
  fond: '#F6F9FC',
  fondHaut: '#EDF3FA',
  fondBas: '#FFFFFF',

  surface: 'rgba(255, 255, 255, 0.72)',
  surfaceHaute: 'rgba(255, 255, 255, 0.88)',
  bordure: 'rgba(10, 37, 64, 0.14)',
  surfaceOpaque: '#FFFFFF',

  texte: '#0A2540',
  texteAttenue: 'rgba(10, 37, 64, 0.82)',
  texteFaible: 'rgba(10, 37, 64, 0.66)',

  // Assombri par rapport au #635BFF de la palette : sur fond clair, le primaire tel quel
  // ne tient pas le seuil AA avec du texte blanc.
  accent: '#4B45C6',
  accentClair: '#635BFF',
  accentContraste: '#FFFFFF',
  neon: '#0284A8',

  credit: '#047857',
  debit: '#BE123C',
  alerte: '#B45309',

  verreTeinte: 'rgba(255, 255, 255, 0.62)',
  verreBordSombre: 'rgba(10, 37, 64, 0.16)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.95)',
  verreOpaque: '#FFFFFF',

  lueurAccent: 'rgba(99, 91, 255, 0.22)',
  lueurNeon: 'rgba(0, 212, 255, 0.18)',

  haloHaut: 'rgba(99, 91, 255, 0.16)',
  haloBas: 'rgba(0, 212, 255, 0.10)',
  lueurBordure: 'rgba(75, 69, 198, 0.18)',
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
  familleTexte:
    "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif",
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
  --cible-tactile: ${cibleTactileMinimale};
  --verre-opacite: var(--verre-opacite-moyenne);
  color-scheme: light dark;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme='clair']) {
${enVariables('couleur', couleursSombres)}
  }
}

:root[data-theme='sombre'] {
${enVariables('couleur', couleursSombres)}
}
`
