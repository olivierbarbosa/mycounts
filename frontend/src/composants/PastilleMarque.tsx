import styles from './PastilleMarque.module.css'

/**
 * Pastille identifiant un service par ses initiales et une teinte stable.
 *
 * Pourquoi pas de vrais logos : aucune bibliothèque libre ne couvre les marques
 * d'abonnement françaises. `simple-icons`, la plus complète, n'en contient que 7 sur 18
 * pour 25 Mo — Free, SFR, EDF, Canal+ et Amazon Prime en sont absents. Une pastille
 * générée a l'avantage décisif d'être **toujours** présente : pas de trous au milieu
 * d'un calendrier.
 *
 * La teinte est dérivée du nom, donc **stable** : « Netflix » aura toujours la même
 * couleur, sur tous les écrans et à toutes les sessions. Une couleur aléatoire changerait
 * à chaque rendu et détruirait la reconnaissance visuelle, qui est tout l'intérêt.
 */

type Props = {
  readonly nom: string
  readonly taille?: 'petite' | 'moyenne' | 'grande'
}

/** Teintes disponibles, prises dans les tokens : la pastille ne fabrique aucune couleur. */
const TEINTES = [
  'var(--couleur-accent-clair)',
  'var(--couleur-neon)',
  'var(--couleur-credit)',
  'var(--couleur-alerte)',
  'var(--couleur-debit)',
  'var(--couleur-accent)',
] as const

/** Hachage entier déterministe. Pas de flottant, pas d'aléatoire : le même nom doit
 *  toujours donner la même teinte. */
export function teintePour(nom: string): string {
  let empreinte = 0
  for (const caractere of nom.trim().toLowerCase()) {
    empreinte = (empreinte * 31 + caractere.codePointAt(0)!) % 100_000
  }
  return TEINTES[empreinte % TEINTES.length]
}

/** Une ou deux lettres : « Canal+ » → « C », « Basic Fit » → « BF ». */
export function initiales(nom: string): string {
  const mots = nom
    .trim()
    .split(/[\s-]+/)
    .filter((mot) => /\p{L}|\p{N}/u.test(mot))
  if (mots.length === 0) return '?'
  if (mots.length === 1) return mots[0].slice(0, 1).toUpperCase()
  return (mots[0].slice(0, 1) + mots[1].slice(0, 1)).toUpperCase()
}

export function PastilleMarque({ nom, taille = 'moyenne' }: Props) {
  return (
    <span
      className={`${styles.pastille} ${styles[taille]}`}
      style={{ ['--teinte-marque' as string]: teintePour(nom) }}
      aria-hidden="true"
    >
      {initiales(nom)}
    </span>
  )
}
