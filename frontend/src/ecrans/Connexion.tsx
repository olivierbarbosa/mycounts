import { ArrowLeft, LockKeyhole, ShieldCheck, WalletCards } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { ErreurApi, api, type UtilisateurPublic } from '../api/client'
import styles from './Connexion.module.css'

type Props = {
  readonly surConnexion: (utilisateur: UtilisateurPublic) => void
}

export function Connexion({ surConnexion }: Props) {
  const [courriel, setCourriel] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [code, setCode] = useState('')
  const [etape, setEtape] = useState<'identifiants' | 'second-facteur'>('identifiants')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  async function soumettre(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      surConnexion(
        await api.connexion(
          courriel,
          motDePasse,
          etape === 'second-facteur' ? code : undefined,
        ),
      )
    } catch (cause) {
      if (cause instanceof ErreurApi && cause.motif === 'second_facteur_requis') {
        setEtape('second-facteur')
        setCode('')
        return
      }
      // Le serveur renvoie déjà un message identique pour « adresse inconnue » et
      // « mot de passe faux » : le client ne doit surtout pas les distinguer non plus.
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.coquille}>
        <header className={styles.marque}>
          <span className={styles.iconeApplication} aria-hidden>
            <WalletCards size={28} strokeWidth={1.8} />
          </span>
          <span className={styles.nomApplication}>mycounts</span>
        </header>

        <section className={styles.contenu} aria-live="polite">
          {etape === 'second-facteur' && (
            <button
              type="button"
              className={styles.retour}
              aria-label="Revenir aux identifiants"
              onClick={() => {
                setEtape('identifiants')
                setErreur(null)
              }}
            >
              <ArrowLeft size={21} aria-hidden />
            </button>
          )}

          <div className={styles.introduction}>
            {etape === 'second-facteur' && (
              <span className={styles.temoinEtape} aria-hidden>
                <ShieldCheck size={24} strokeWidth={1.8} />
              </span>
            )}
            <h1 className={styles.titre}>
              {etape === 'identifiants' ? 'Bonsoir.' : 'Vérifions que c’est bien vous.'}
            </h1>
            <p className={styles.sousTitre}>
              {etape === 'identifiants'
                ? 'Retrouvez votre argent, vos projets et votre prochain mois au même endroit.'
                : 'Entrez le code de votre application d’authentification ou un code de secours.'}
            </p>
          </div>

          <form className={styles.formulaire} onSubmit={soumettre} noValidate>
            {etape === 'identifiants' ? (
              <>
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
                    autoCapitalize="none"
                    spellCheck={false}
                    inputMode="email"
                    required
                    autoFocus
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
              </>
            ) : (
              <div className={styles.champ}>
                <label className={styles.etiquette} htmlFor="code-second-facteur">
                  Code de vérification
                </label>
                <input
                  id="code-second-facteur"
                  className={`${styles.saisie} ${styles.code}`}
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  autoComplete="one-time-code"
                  autoCapitalize="characters"
                  spellCheck={false}
                  placeholder="123 456 ou code de secours"
                  required
                  autoFocus
                />
              </div>
            )}

            {erreur !== null && (
              <p className={styles.erreur} role="alert">
                {erreur}
              </p>
            )}

            <button className={styles.bouton} type="submit" disabled={enCours}>
              {enCours
                ? 'Vérification…'
                : etape === 'identifiants'
                  ? 'Se connecter'
                  : 'Continuer'}
            </button>
          </form>
        </section>

        <footer className={styles.pied}>
          <LockKeyhole size={15} aria-hidden />
          <span>Bêta privée sur invitation · connexion sécurisée</span>
        </footer>
      </div>
    </main>
  )
}
