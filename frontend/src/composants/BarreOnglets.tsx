import type { LucideIcon } from 'lucide-react'
import { Plus } from 'lucide-react'
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
  /** Action d'ajout, dans sa PROPRE capsule à droite de la barre. `null` la retire :
   *  un périmètre sans aucun compte n'a nulle part où écrire, et le bouton ouvrirait une
   *  feuille de saisie sans compte à proposer. Retirer vaut mieux que griser — un bouton
   *  grisé sans explication se lit comme une panne. */
  readonly surAjout: (() => void) | null
}

/** Navigation principale, en bas de l'écran et en Liquid Glass.
 *
 *  Deux capsules distinctes, sur le modèle d'Apple Music : les onglets dans une pilule,
 *  l'ajout seul dans un disque posé à sa droite. La version précédente logeait le `+` au
 *  MILIEU de la pilule, à un emplacement d'onglet — il fallait alors décaler l'index de
 *  la pastille glissante pour qu'elle saute par-dessus, et le bouton n'en restait pas
 *  moins lu comme une destination puisqu'il occupait la place d'une destination.
 *
 *  Le séparer règle les deux : la forme dit qu'il n'est pas du même ordre que ses
 *  voisins, et la pastille compte à nouveau de simples onglets. */
export function BarreOnglets({ onglets, actif, surChangement, surAjout }: Props) {
  const emplacementActif = Math.max(
    0,
    onglets.findIndex((o) => o.cle === actif),
  )

  return (
    <nav className={styles.barre} aria-label="Navigation principale">
      <div
        className={styles.pilule}
        style={
          {
            '--emplacements': onglets.length,
            '--actif': emplacementActif,
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
              {/* Le rebond se rejoue à chaque changement sans qu'on ait à remonter
                  l'élément : une animation CSS démarre dès que son `animation-name`
                  s'applique, et la classe change ici d'un onglet à l'autre. Une clé de
                  remontage a été essayée puis retirée — le témoin restait vert sans elle. */}
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
      </div>

      {surAjout !== null && (
        <button
          type="button"
          className={styles.ajouter}
          onClick={surAjout}
          aria-label="Saisir une opération"
        >
          <Plus size={24} strokeWidth={2.5} aria-hidden />
        </button>
      )}
    </nav>
  )
}
