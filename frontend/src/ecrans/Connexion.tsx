import { type FormEvent, useState } from 'react'

import { ErreurApi, api, type UtilisateurPublic } from '../api/client'
import styles from './Connexion.module.css'

type Props = {
  readonly surConnexion: (utilisateur: UtilisateurPublic) => void
}

export function Connexion({ surConnexion }: Props) {
  const [courriel, setCourriel] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  async function soumettre(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      surConnexion(await api.connexion(courriel, motDePasse))
    } catch (cause) {
      // Le serveur renvoie déjà un message identique pour « adresse inconnue » et
      // « mot de passe faux » : le client ne doit surtout pas les distinguer non plus.
      setErreur(
        cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.',
      )
    } finally {
      setEnCours(false)
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <h1 className={styles.titre}>mycounts</h1>
        <p className={styles.sousTitre}>Suivez vos dépenses, gardez la main sur votre budget.</p>
      </header>

      <form className={styles.formulaire} onSubmit={soumettre} noValidate>
        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="courriel">
            Adresse électronique
          </label>
          <input
            id="courriel"
            className={styles.saisie}
            type="email"
            value={courriel}
            onChange={(e) => setCourriel(e.target.value)}
            autoComplete="username"
            inputMode="email"
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="mot-de-passe">
            Mot de passe
          </label>
          <input
            id="mot-de-passe"
            className={styles.saisie}
            type="password"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}

        <button className={styles.bouton} type="submit" disabled={enCours}>
          {enCours ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>

      <p className={styles.pied}>
        Il n'y a pas d'inscription libre : on entre par une invitation du foyer.
      </p>
    </main>
  )
}
