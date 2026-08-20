import { PiggyBank } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type { EpargnePublique } from '../api/client'
import { api } from '../api/client'
import { Montant } from '../composants/Montant'
import styles from './Epargne.module.css'

type Props = {
  readonly rafraichissement: number
  readonly surVirement: () => void
}

const DATE_COURTE = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' })

function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

/**
 * Ce que le foyer a mis de côté.
 *
 * Le total est SÉPARÉ de celui de l'accueil, et ce n'est pas un choix de mise en page :
 * additionner un livret au compte courant fait croire à une aisance qui n'existe pas, et
 * la décision de dépenser se prendrait sur un chiffre faux.
 *
 * Ce que cette page ne fait PAS : d'objectifs chiffrés. Ils n'ont de sens qu'une fois les
 * comptes alimentés, et réserver une part d'un compte à un projet serait un second
 * système comptable à tenir d'accord avec le premier.
 */
export function Epargne({ rafraichissement, surVirement }: Props) {
  const [epargne, setEpargne] = useState<EpargnePublique | null>(null)

  const charger = useCallback(async () => {
    setEpargne(await api.epargne())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  if (epargne === null) return null

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <p className={styles.libelle}>Épargne totale</p>
        <Montant
          centimes={epargne.total_centimes}
          taille="display"
          neutre
          signeExplicitePositif={false}
        />
        <p className={styles.borne}>
          {/* Le versé s'accompagne toujours de sa période : « 200 € versés » ne se lit
              pas sans savoir depuis quand. */}
          <Montant
            centimes={epargne.verse_sur_la_periode_centimes}
            taille="ligne"
            neutre
            signeExplicitePositif={false}
          />{' '}
          versés depuis le {DATE_COURTE.format(dateCivile(epargne.periode.debut))}
        </p>
      </header>

      {epargne.comptes.length === 0 ? (
        <div className={styles.vide}>
          <PiggyBank size={28} strokeWidth={1.5} aria-hidden />
          <p>
            Aucun compte d’épargne. Créez-en un dans les Réglages, puis alimentez-le par virement
            depuis votre compte courant.
          </p>
        </div>
      ) : (
        <>
          <h2 className={styles.titreListe}>Mes comptes</h2>
          <ul className={styles.liste}>
            {epargne.comptes.map((compte) => (
              <li key={compte.id} className={styles.ligne}>
                <span className={styles.nom}>{compte.nom}</span>
                <Montant
                  centimes={compte.solde_centimes}
                  taille="titre"
                  neutre
                  signeExplicitePositif={false}
                />
              </li>
            ))}
          </ul>

          <button type="button" className={styles.action} onClick={surVirement}>
            Virer de l’argent
          </button>
        </>
      )}
    </main>
  )
}
