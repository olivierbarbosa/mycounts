import { type FormEvent, useState } from 'react'

import type { ComptePublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import styles from './ComptesBancaires.module.css'
import { SaisieInvalide, enCentimes } from '../design/saisie'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly surChangement: () => void
}

const LIBELLES = { courant: 'Compte courant', epargne: 'Épargne' } as const

/**
 * Liste et création des comptes bancaires du foyer.
 *
 * Le type se choisit à la CRÉATION et n'est pas modifiable ensuite : basculer un compte
 * courant en épargne retirerait son argent du solde du quotidien sans qu'aucune opération
 * n'ait bougé, et l'écart avec la banque deviendrait inexplicable.
 */
export function ComptesBancaires({ comptes, surChangement }: Props) {
  const [ouvert, setOuvert] = useState(false)
  const [nom, setNom] = useState('')
  const [type, setType] = useState<'courant' | 'epargne'>('courant')
  const [ouverture, setOuverture] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)

  async function creer(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let centimes = 0
    if (ouverture.trim() !== '') {
      try {
        centimes = enCentimes(ouverture)
      } catch (cause) {
        setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
        return
      }
    }

    try {
      await api.creerCompte({
        nom: nom.trim(),
        prive: true,
        type_compte: type,
        solde_ouverture_centimes: centimes,
      })
      setNom('')
      setOuverture('')
      setType('courant')
      setOuvert(false)
      surChangement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  return (
    <div className={styles.bloc}>
      <ul className={styles.liste}>
        {comptes.map((compte) => (
          <li key={compte.id} className={styles.ligne}>
            <span className={styles.nom}>{compte.nom}</span>
            <span className={styles.type}>{LIBELLES[compte.type_compte]}</span>
          </li>
        ))}
      </ul>

      {ouvert ? (
        <form className={styles.formulaire} onSubmit={creer} noValidate>
          <label className={styles.etiquette} htmlFor="compte-nom">
            Nom du compte
          </label>
          <input
            id="compte-nom"
            className={styles.saisie}
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            maxLength={80}
            placeholder="Livret A"
            required
          />

          <label className={styles.etiquette} htmlFor="compte-type">
            Nature
          </label>
          <select
            id="compte-type"
            className={styles.saisie}
            value={type}
            onChange={(e) => setType(e.target.value as 'courant' | 'epargne')}
          >
            <option value="courant">Compte courant</option>
            <option value="epargne">Épargne</option>
          </select>
          <p className={styles.note}>
            L’épargne ne compte pas dans le solde du quotidien : elle a son propre total, sur sa
            page. La nature ne se change plus ensuite.
          </p>

          <label className={styles.etiquette} htmlFor="compte-ouverture">
            Solde actuel (facultatif)
          </label>
          <input
            id="compte-ouverture"
            className={styles.saisie}
            value={ouverture}
            onChange={(e) => setOuverture(e.target.value)}
            inputMode="decimal"
            placeholder="0,00"
            autoComplete="off"
          />

          {erreur !== null && (
            <p className={styles.erreur} role="alert">
              {erreur}
            </p>
          )}

          <div className={styles.actions}>
            <button type="button" className={styles.secondaire} onClick={() => setOuvert(false)}>
              Annuler
            </button>
            <button type="submit" className={styles.principal}>
              Créer le compte
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className={styles.secondaire} onClick={() => setOuvert(true)}>
          Ajouter un compte
        </button>
      )}
    </div>
  )
}
