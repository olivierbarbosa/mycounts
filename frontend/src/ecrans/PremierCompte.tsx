import { type FormEvent, useState } from 'react'

import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './PremierCompte.module.css'

type Props = {
  readonly surCreation: () => void
}

/**
 * Amorçage : premier compte et solde actuel.
 *
 * Le solde saisi devient une **opération d'ouverture**, pas une valeur stockée à part.
 * L'écran le dit explicitement — c'est ce qui explique pourquoi elle apparaîtra ensuite
 * dans la liste des opérations.
 */
export function PremierCompte({ surCreation }: Props) {
  const [nom, setNom] = useState('Compte courant')
  const [solde, setSolde] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  async function soumettre(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let centimes = 0
    if (solde.trim() !== '') {
      try {
        centimes = enCentimes(solde)
      } catch (cause) {
        setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
        return
      }
    }

    setEnCours(true)
    try {
      await api.creerCompte({
        nom: nom.trim(),
        prive: true,
        // Le tout premier compte est celui du quotidien : c'est là que tombent la paie
        // et les prélèvements. Un livret se crée ensuite, dans les Réglages.
        type_compte: 'courant',
        solde_ouverture_centimes: centimes,
      })
      surCreation()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <main className={styles.page}>
      <div>
        <h1 className={styles.titre}>Votre premier compte</h1>
        <p className={styles.explication}>
          Indiquez le solde qu'il affiche en ce moment. Tout se calculera à partir de là.
        </p>
      </div>

      <form className={styles.carte} onSubmit={soumettre} noValidate>
        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="nom-compte">
            Nom du compte
          </label>
          <input
            id="nom-compte"
            className={styles.saisie}
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            maxLength={80}
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="solde-actuel">
            Solde actuel
          </label>
          <input
            id="solde-actuel"
            className={styles.saisie}
            value={solde}
            onChange={(e) => setSolde(e.target.value)}
            inputMode="decimal"
            placeholder="1 240,50"
            autoComplete="off"
          />
          <p className={styles.note}>
            Laissez vide si le compte est à zéro. Un montant négatif est accepté : c'est un
            découvert, pas une dépense du mois.
          </p>
        </div>

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}

        <button className={styles.bouton} type="submit" disabled={enCours || nom.trim() === ''}>
          {enCours ? 'Création…' : 'Créer le compte'}
        </button>
      </form>

      <p className={styles.note}>
        Ce solde est enregistré comme une opération d'ouverture : vous la verrez dans la liste.
        Votre solde reste ainsi la somme de vos opérations, jamais un chiffre à part.
      </p>
    </main>
  )
}
