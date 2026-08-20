import type { CSSProperties, ReactNode } from 'react'

import styles from './Bulle.module.css'
import type { Origine } from './EcranDeBulle'

type Props = {
  readonly libelle: string
  /** Bord auquel la bulle s'accroche. L'avatar tient le coin gauche, les actions le droit. */
  readonly cote: 'gauche' | 'droite'
  /** Rang dans sa rangée, la plus proche du bord étant 0.
   *
   *  Un rang et non une position libre : plusieurs bulles côte à côte doivent s'aligner
   *  sans que chaque appelant recalcule un décalage. Le jour où il en faudrait une
   *  quatrième, ce paramètre refusera de compiler — ce qui vaut mieux qu'un en-tête qui
   *  déborde en silence. */
  readonly rang: 0 | 1 | 2
  readonly children: ReactNode
  readonly surOuverture: (origine: Origine) => void
}

/** Deux lettres au plus : au-delà, la bulle devient un pavé de texte illisible à 44 px.
 *
 *  Nommée ainsi et non `initiales` tout court : `PastilleMarque` en expose une autre, qui
 *  n'a ni les mêmes séparateurs ni le même nombre de lettres parce qu'elle abrège un
 *  créancier et non une personne. Deux fonctions homonymes aux règles différentes dans le
 *  même dossier est un piège qu'un import distrait suffit à déclencher. */
export function initialesDeLUtilisateur(nom: string): string {
  const mots = nom.trim().split(/\s+/).filter(Boolean)
  if (mots.length === 0) return '?'
  if (mots.length === 1) return mots[0].slice(0, 2).toUpperCase()
  return (mots[0][0] + mots[mots.length - 1][0]).toUpperCase()
}

/**
 * Bulle fixe en haut de l'écran — avatar à gauche, actions à droite.
 *
 * AUTEUR UNIQUE de l'objet. L'avatar et les actions étaient deux composants avec deux
 * feuilles de style recopiées l'une sur l'autre : elles se ressemblaient tant qu'on
 * pensait à modifier les deux. Ce qu'Olivier a demandé le 20 août 2026 — que toutes les
 * bulles ouvrent leur écran de la même façon avec le même effet — ne peut pas tenir sur
 * deux composants jumeaux, seulement sur un seul.
 *
 * Elle est `position: fixed` et ne pousse donc rien : la place qu'elle occupe est
 * réservée par `--disposition-reserve-bulle` sur chaque écran. Une bulle qui participerait
 * au flux décalerait le contenu d'un écran sur deux selon qu'il a un titre ou non — c'est
 * la faute que la classe Verre a commise deux fois (ERREURS #008 et #020).
 */
export function Bulle({ libelle, cote, rang, children, surOuverture }: Props) {
  return (
    <button
      type="button"
      className={cote === 'gauche' ? styles.bulleGauche : styles.bulleDroite}
      style={{ '--rang': rang } as CSSProperties}
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
      aria-label={libelle}
    >
      {children}
    </button>
  )
}
