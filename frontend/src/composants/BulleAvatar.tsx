import styles from './BulleAvatar.module.css'

/** Position et taille de la bulle au moment du clic, dans le repère de la fenêtre.
 *  C'est le point de départ de la transition : sans elle, le panneau ne saurait pas d'où
 *  il vient et l'avatar réapparaîtrait ailleurs au lieu d'y migrer. */
export type Origine = { readonly x: number; readonly y: number; readonly taille: number }

type Props = {
  readonly nom: string
  readonly surOuverture: (origine: Origine) => void
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
      onClick={(evenement) => {
        // Mesurée au clic et non au montage : la bulle est fixe, mais la barre du
        // navigateur se rétracte au défilement et déplace tout ce qui dépend de
        // `safe-area-inset-top`. Une position mémorisée trop tôt ferait partir
        // l'animation à côté.
        const boite = evenement.currentTarget.getBoundingClientRect()
        surOuverture({
          x: boite.left + boite.width / 2,
          y: boite.top + boite.height / 2,
          taille: boite.width,
        })
      }}
      aria-label={`Paramètres de ${nom}`}
    >
      <span aria-hidden>{initiales(nom)}</span>
    </button>
  )
}
