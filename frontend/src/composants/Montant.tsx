import styles from './Montant.module.css'

/**
 * Auteur UNIQUE de l'affichage d'un montant.
 *
 * Aucun autre composant ne formate de centimes : une seconde implémentation finirait par
 * arrondir, séparer ou signer différemment, et deux écrans montreraient deux chiffres
 * pour la même donnée.
 *
 * Le signe est TOUJOURS écrit en toutes lettres (« − » ou « + »), jamais porté par la
 * seule couleur : un daltonien, un écran en plein soleil ou une capture en noir et blanc
 * doivent rester lisibles.
 */

export type TailleMontant = 'display' | 'titre' | 'ligne'

type Props = {
  readonly centimes: number
  readonly taille?: TailleMontant
  /** Force la neutralité chromatique : utile quand le signe seul suffit (un solde). */
  readonly neutre?: boolean
  /** Masque le signe « + » sur les valeurs positives (soldes, où il est du bruit). */
  readonly signeExplicitePositif?: boolean
}

const ESPACE_INSECABLE = ' '
const MOINS = '−'

/** Intl produit déjà une espace FINE insécable (U+202F) pour les milliers en français —
 *  vérifié, pas supposé. On ne la remplace donc pas : la seule chose à garantir est
 *  qu'aucune espace ordinaire ne s'y glisse, sinon un montant peut se couper en deux
 *  lignes au milieu. */
const ESPACES_INSECABLES = /[\u202f\u00a0]/

export const contientEspaceInsecable = (texte: string): boolean => ESPACES_INSECABLES.test(texte)

/** Découpe des centimes en parties affichables, sans jamais passer par un flottant. */
export function decouper(centimes: number): {
  signe: string
  euros: string
  centimes: string
} {
  const negatif = centimes < 0
  const absolu = Math.abs(centimes)
  // Division entière et modulo : `absolu / 100` produirait un flottant, et 0.1 + 0.2
  // resterait le bug le plus cher de l'informatique de gestion.
  const euros = Math.trunc(absolu / 100)
  const reste = absolu % 100

  return {
    signe: negatif ? MOINS : '+',
    euros: euros.toLocaleString('fr-FR').replace(/ /g, ESPACE_INSECABLE),
    centimes: String(reste).padStart(2, '0'),
  }
}

export function Montant({
  centimes,
  taille = 'ligne',
  neutre = false,
  signeExplicitePositif = true,
}: Props) {
  const { signe, euros, centimes: decimales } = decouper(centimes)
  // Zéro n'est ni un crédit ni un débit : le colorer en vert avec un « + » laisse croire
  // à une entrée d'argent qui n'existe pas.
  const couleur =
    neutre || centimes === 0 ? styles.neutre : centimes < 0 ? styles.debit : styles.credit
  const signeAffiche = centimes < 0 ? signe : centimes > 0 && signeExplicitePositif ? signe : ''

  return (
    <span
      className={`${styles.montant} ${styles[taille]} ${couleur}`}
      // Lecture vocale : « moins quarante-cinq euros quatre-vingt-dix » plutôt que les
      // fragments visuels séparés.
      aria-label={`${centimes < 0 ? 'moins ' : ''}${euros} euros ${decimales}`}
    >
      <span aria-hidden="true">
        {signeAffiche}
        {euros}
        <span className={styles.centimes}>,{decimales}&nbsp;€</span>
      </span>
    </span>
  )
}
