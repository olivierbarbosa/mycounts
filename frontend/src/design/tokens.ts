/**
 * Auteur UNIQUE des couleurs, rayons, espacements et graisses du projet.
 *
 * Aucun autre fichier n'écrit de valeur littérale : le garde-fou n°9
 * (`scripts/verifier_couleurs.py`) refuse tout `#hex` ou `rgb(` ailleurs. C'est sur cette
 * couche que la dérive s'installe si on la laisse faire.
 *
 * Direction artistique : Revolut dominant — aplats denses, contraste fort, accent
 * électrique — avec le Liquid Glass réservé aux couches flottantes.
 */

/** Palette sombre, thème par défaut. */
export const couleursSombres = {
  fond: '#0A0A0F',
  surface: '#14141C',
  surfaceHaute: '#1E1E29',
  bordure: '#2A2A38',

  texte: '#F4F4F7',
  texteAttenue: '#9A9AAC',
  texteFaible: '#6B6B7E',

  accent: '#7A5CFF',
  accentClair: '#9B84FF',
  accentContraste: '#FFFFFF',

  credit: '#2FD98A',
  debit: '#FF6B6B',
  alerte: '#FFB020',

  /** Teinte du verre et de ses arêtes — voir `verre` plus bas. */
  verreTeinte: 'rgba(28, 28, 40, 0.62)',
  verreBordSombre: 'rgba(0, 0, 0, 0.55)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.16)',
  verreOpaque: '#161620',
} as const

/** Palette claire. Mêmes rôles, mêmes noms : un composant ne connaît que les rôles. */
export const couleursClaires = {
  fond: '#F5F5F8',
  surface: '#FFFFFF',
  surfaceHaute: '#FFFFFF',
  bordure: '#E2E2EA',

  texte: '#14141C',
  texteAttenue: '#5C5C70',
  texteFaible: '#8A8A9C',

  accent: '#5B3FE8',
  accentClair: '#7A5CFF',
  accentContraste: '#FFFFFF',

  credit: '#0F9D58',
  debit: '#D93636',
  alerte: '#B87400',

  verreTeinte: 'rgba(255, 255, 255, 0.68)',
  verreBordSombre: 'rgba(0, 0, 0, 0.14)',
  verreSpeculaire: 'rgba(255, 255, 255, 0.85)',
  verreOpaque: '#FFFFFF',
} as const

/**
 * Rayons concentriques : le rayon d'un élément imbriqué se DÉDUIT de son parent,
 * il ne se choisit pas. Deux rayons voisins choisis à la main finissent toujours par
 * diverger d'un pixel qui se voit.
 */
export const rayons = {
  petit: '10px',
  moyen: '16px',
  grand: '22px',
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
 * complexe. Pas de réfraction : `backdrop-filter` floute, il ne dévie pas la lumière —
 * un vrai lensing demanderait un filtre SVG de déplacement ou du WebGL, pour un coût
 * disproportionné ici.
 */
export const verre = {
  flou: '20px',
  saturation: '180%',
  /** Trois positions du réglage utilisateur, reprises d'iOS 27. */
  opaciteClaire: '0.45',
  opaciteMoyenne: '0.72',
  opaciteOpaque: '1',
} as const

/**
 * Points de rupture. UNIQUEMENT en `min-width` : l'application est écrite pour mobile
 * d'abord, le desktop est le cas dérivé. Une seule `max-width` dans le dépôt signalerait
 * que la base a été pensée à l'envers.
 */
export const ruptures = {
  tablette: '600px',
  bureau: '1024px',
} as const

/** Cible tactile minimale (Apple HIG). Vérifiée par le garde-fou n°10. */
export const cibleTactileMinimale = '44px'

type Dictionnaire = Record<string, string>

const enVariables = (prefixe: string, valeurs: Dictionnaire): string =>
  Object.entries(valeurs)
    .map(([nom, valeur]) => `  --${prefixe}-${enKebab(nom)}: ${valeur};`)
    .join('\n')

const enKebab = (nom: string): string => nom.replace(/[A-Z]/g, (l) => `-${l.toLowerCase()}`)

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
