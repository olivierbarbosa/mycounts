import type { LucideIcon } from 'lucide-react'
import type { CSSProperties } from 'react'

import styles from './BarreOnglets.module.css'

export type Onglet = {
  readonly cle: string
  readonly libelle: string
  /** Composant d'icône, pas un caractère : un glyphe Unicode change de dessin selon la
   *  police du système et ne s'aligne jamais deux fois pareil. */
  readonly Icone: LucideIcon
}

type Props = {
  readonly onglets: readonly Onglet[]
  readonly actif: string
  readonly surChangement: (cle: string) => void
}

/** Navigation principale, en bas de l'écran et en Liquid Glass. */
export function BarreOnglets({ onglets, actif, surChangement }: Props) {
  return (
    <nav
      className={styles.barre}
      aria-label="Navigation principale"
      style={
        {
          '--onglets': onglets.length,
          '--actif': Math.max(
            0,
            onglets.findIndex((o) => o.cle === actif),
          ),
        } as CSSProperties
      }
    >
      {/* La pastille est UN seul élément qui glisse, et non un fond qui s'allume sur
          l'onglet d'arrivée : le déplacement dit d'où l'on vient. Elle est décorative et
          traversable — l'état accessible reste porté par `aria-current`. */}
      <span className={styles.pastille} aria-hidden />
      {/* La marque n'apparaît qu'au format bureau : sur mobile, elle prendrait la place
          d'un onglet dans la zone du pouce. */}
      <span className={styles.marque}>mycounts</span>
      {onglets.map((onglet) => {
        const actifCourant = onglet.cle === actif
        return (
          <button
            key={onglet.cle}
            type="button"
            className={styles.onglet}
            aria-current={actifCourant ? 'page' : undefined}
            onClick={() => surChangement(onglet.cle)}
          >
            {/* Le rebond se rejoue à chaque changement sans qu'on ait à remonter l'élément :
                une animation CSS démarre dès que son `animation-name` s'applique, et la
                classe change ici d'un onglet à l'autre. Une clé de remontage a été
                essayée puis retirée — le témoin restait vert sans elle. */}
            <onglet.Icone
              className={actifCourant ? styles.iconeActive : styles.icone}
              size={20}
              strokeWidth={2}
              aria-hidden
            />
            {onglet.libelle}
          </button>
        )
      })}
    </nav>
  )
}
