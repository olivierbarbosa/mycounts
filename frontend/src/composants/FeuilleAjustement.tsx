import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { ComptePublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import { Montant } from './Montant'
import { fermetureExterieure } from './fermetureExterieure'
import styles from './FeuilleSaisie.module.css'
import { Portail } from './Portail'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly surFermeture: () => void
  readonly surEnregistrement: () => void
}

/**
 * Met le solde d'un compte d'accord avec celui de la banque.
 *
 * On saisit le solde CONSTATÉ, pas l'écart : personne ne connaît son écart de tête, tout
 * le monde lit le chiffre affiché par sa banque. Le serveur fait la soustraction — lui
 * seul connaît le solde à l'instant où il écrit, et deux corrections concurrentes
 * calculées par le client se doubleraient.
 *
 * Ce que cet écran ne fait PAS : écrire le solde. Un solde est une somme d'opérations,
 * jamais une valeur qu'on pose. La correction devient une opération de plus, visible dans
 * l'historique — c'est ce qui permet, trois mois plus tard, de comprendre l'écart.
 */
export function FeuilleAjustement({ comptes, surFermeture, surEnregistrement }: Props) {
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  const [soldes, setSoldes] = useState<ReadonlyMap<string, number>>(new Map())
  const [saisie, setSaisie] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  const charger = useCallback(async () => {
    const montants = await api.soldesDesComptes()
    setSoldes(new Map(montants.map((s) => [s.compte_id, s.solde_centimes])))
  }, [])

  useEffect(() => {
    void charger()
  }, [charger])

  const actuel = soldes.get(compteId)

  async function soumettre(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let centimes: number
    try {
      centimes = enCentimes(saisie)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }

    setEnCours(true)
    try {
      await api.ajusterLeSolde(compteId, { solde_reel_centimes: centimes })
      surEnregistrement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <Portail>
      <div
        className={styles.voile}
        onClick={fermetureExterieure(surFermeture)}
        role="dialog"
        aria-modal="true"
        aria-label="Corriger le solde"
      >
        <form className={styles.feuille} onSubmit={soumettre} noValidate>
          <h2 className={styles.titre}>Corriger le solde</h2>

          {comptes.length > 1 && (
            <div className={styles.champ}>
              <label className={styles.etiquette} htmlFor="ajustement-compte">
                Compte
              </label>
              <select
                id="ajustement-compte"
                className={styles.choix}
                value={compteId}
                onChange={(e) => setCompteId(e.target.value)}
              >
                {comptes.map((compte) => (
                  <option key={compte.id} value={compte.id}>
                    {compte.nom}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className={styles.champ}>
            <label className={styles.etiquette} htmlFor="ajustement-solde">
              Solde affiché par votre banque
            </label>
            <input
              id="ajustement-solde"
              className={styles.saisie}
              value={saisie}
              onChange={(e) => setSaisie(e.target.value)}
              inputMode="decimal"
              placeholder="1 234,56"
              autoComplete="off"
              required
            />
            {actuel !== undefined && (
              <p className={styles.note}>
                L’application compte{' '}
                <Montant centimes={actuel} taille="ligne" neutre signeExplicitePositif={false} />.
                L’écart sera enregistré comme une opération, visible dans l’historique.
              </p>
            )}
          </div>

          {erreur !== null && (
            <p className={styles.erreur} role="alert">
              {erreur}
            </p>
          )}

          <div className={styles.actions}>
            <button type="button" className={styles.annuler} onClick={surFermeture}>
              Annuler
            </button>
            <button type="submit" className={styles.valider} disabled={enCours}>
              Corriger
            </button>
          </div>
        </form>
      </div>
    </Portail>
  )
}
