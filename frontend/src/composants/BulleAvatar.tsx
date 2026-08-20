import styles from './BulleAvatar.module.css'

type Props = {
  readonly nom: string
  readonly surOuverture: () => void
}

/** Deux lettres au plus : au-delà, la bulle devient un pavé de texte illisible à 40 px. */
export function initiales(nom: string): string {
  const mots = nom.trim().split(/\s+/).filter(Boolean)
  if (mots.length === 0) return '?'
  if (mots.length === 1) return mots[0].slice(0, 2).toUpperCase()
  return (mots[0][0] + mots[mots.length - 1][0]).toUpperCase()
}

/**
 * Bulle d'avatar, fixe en haut à gauche de tous les écrans.
 *
 * Elle est `position: fixed` et ne pousse donc rien : la place qu'elle occupe est
 * réservée par `--disposition-reserve-bulle` sur chaque écran. Une bulle qui participerait
 * au flux décalerait le contenu d'un écran sur deux selon qu'il a un titre ou non — c'est
 * la faute que la classe Verre a commise deux fois (ERREURS #008 et #020).
 */
export function BulleAvatar({ nom, surOuverture }: Props) {
  return (
    <button
      type="button"
      className={styles.bulle}
      onClick={surOuverture}
      aria-label={`Paramètres de ${nom}`}
    >
      <span aria-hidden>{initiales(nom)}</span>
    </button>
  )
}
