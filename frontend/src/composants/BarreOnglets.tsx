import styles from './BarreOnglets.module.css'
import verre from './Verre.module.css'

export type Onglet = {
  readonly cle: string
  readonly libelle: string
  readonly icone: string
}

type Props = {
  readonly onglets: readonly Onglet[]
  readonly actif: string
  readonly surChangement: (cle: string) => void
}

/** Navigation principale, en bas de l'écran et en Liquid Glass. */
export function BarreOnglets({ onglets, actif, surChangement }: Props) {
  return (
    <nav className={`${styles.barre} ${verre.verre}`} aria-label="Navigation principale">
      {onglets.map((onglet) => (
        <button
          key={onglet.cle}
          type="button"
          className={styles.onglet}
          aria-current={onglet.cle === actif ? 'page' : undefined}
          onClick={() => surChangement(onglet.cle)}
        >
          <span className={styles.icone} aria-hidden="true">
            {onglet.icone}
          </span>
          {onglet.libelle}
        </button>
      ))}
    </nav>
  )
}
