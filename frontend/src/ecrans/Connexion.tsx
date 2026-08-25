import { ArrowLeft, LockKeyhole, ShieldCheck, UserPlus, WalletCards } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'

import { ErreurApi, api, type UtilisateurPublic } from '../api/client'
import styles from './Connexion.module.css'

type Props = {
  readonly surConnexion: (utilisateur: UtilisateurPublic) => void | Promise<void>
}

type Etape =
  | 'identifiants'
  | 'second-facteur'
  | 'inscription'
  | 'recuperation'
  | 'nouveau-mot-de-passe'
  | 'message'

export function Connexion({ surConnexion }: Props) {
  const [courriel, setCourriel] = useState('')
  const [nom, setNom] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [code, setCode] = useState('')
  const [faireConfiance, setFaireConfiance] = useState(false)
  const [etape, setEtape] = useState<Etape>('identifiants')
  const [message, setMessage] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)
  const [jetonRecuperation, setJetonRecuperation] = useState<string | null>(null)
  const [jetonInvitation] = useState(() =>
    new URLSearchParams(window.location.search).get('invitation'),
  )

  useEffect(() => {
    const parametres = new URLSearchParams(window.location.search)
    const verification = parametres.get('verification')
    const recuperation = parametres.get('recuperation')
    if (recuperation) {
      setJetonRecuperation(recuperation)
      setEtape('nouveau-mot-de-passe')
      window.history.replaceState({}, '', window.location.pathname)
      return
    }
    if (!verification) return
    setEnCours(true)
    void api
      .verifierCourriel(verification)
      .then((resultat) => {
        setMessage(resultat.message)
        setEtape('message')
        window.history.replaceState({}, '', window.location.pathname)
      })
      .catch((cause) => {
        setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
        setEtape('message')
      })
      .finally(() => setEnCours(false))
  }, [])

  function revenir() {
    setEtape('identifiants')
    setErreur(null)
    setMessage('')
    setCode('')
    setConfirmation('')
  }

  async function soumettre(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)
    setEnCours(true)
    try {
      if (etape === 'identifiants' || etape === 'second-facteur') {
        const utilisateur = await api.connexion(
          courriel,
          motDePasse,
          etape === 'second-facteur' ? code : undefined,
          etape === 'second-facteur' && faireConfiance,
        )
        await surConnexion(utilisateur)
        return
      }
      if (etape === 'inscription') {
        if (motDePasse !== confirmation) {
          setErreur('Les deux mots de passe ne correspondent pas.')
          return
        }
        const resultat = await api.inscription(
          courriel,
          nom,
          motDePasse,
          jetonInvitation ?? undefined,
        )
        if (jetonInvitation !== null) {
          window.history.replaceState({}, '', window.location.pathname)
        }
        setMessage(resultat.message)
        setEtape('message')
        return
      }
      if (etape === 'recuperation') {
        const resultat = await api.demanderReinitialisation(courriel)
        setMessage(resultat.message)
        setEtape('message')
        return
      }
      if (etape === 'nouveau-mot-de-passe' && jetonRecuperation !== null) {
        if (motDePasse !== confirmation) {
          setErreur('Les deux mots de passe ne correspondent pas.')
          return
        }
        const resultat = await api.reinitialiserMotDePasse(
          jetonRecuperation,
          motDePasse,
          code.trim() || undefined,
        )
        setMessage(resultat.message)
        setEtape('message')
      }
    } catch (cause) {
      if (cause instanceof ErreurApi && cause.motif === 'second_facteur_requis') {
        setEtape('second-facteur')
        setCode('')
        return
      }
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  const peutRevenir = etape !== 'identifiants'
  const titre = titreDe(etape)

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
          {peutRevenir && (
            <button type="button" className={styles.retour} aria-label="Revenir" onClick={revenir}>
              <ArrowLeft size={21} aria-hidden />
            </button>
          )}

          <div className={styles.introduction}>
            {etape !== 'identifiants' && (
              <span className={styles.temoinEtape} aria-hidden>
                {etape === 'inscription' ? (
                  <UserPlus size={24} strokeWidth={1.8} />
                ) : (
                  <ShieldCheck size={24} strokeWidth={1.8} />
                )}
              </span>
            )}
            <h1 className={styles.titre}>{titre}</h1>
            <p className={styles.sousTitre}>{descriptionDe(etape, message)}</p>
          </div>

          {etape !== 'message' && (
            <form className={styles.formulaire} onSubmit={soumettre} noValidate>
              {etape === 'inscription' && (
                <Champ id="nom" label="Votre prénom ou nom" value={nom} onChange={setNom} />
              )}
              {(etape === 'identifiants' ||
                etape === 'inscription' ||
                etape === 'recuperation') && (
                <Champ
                  id="courriel"
                  label="Adresse électronique"
                  value={courriel}
                  onChange={setCourriel}
                  type="email"
                  autoComplete="username"
                />
              )}
              {(etape === 'identifiants' ||
                etape === 'inscription' ||
                etape === 'nouveau-mot-de-passe') && (
                <Champ
                  id="mot-de-passe"
                  label={etape === 'identifiants' ? 'Mot de passe' : 'Nouveau mot de passe'}
                  value={motDePasse}
                  onChange={setMotDePasse}
                  type="password"
                  autoComplete={etape === 'identifiants' ? 'current-password' : 'new-password'}
                />
              )}
              {(etape === 'inscription' || etape === 'nouveau-mot-de-passe') && (
                <Champ
                  id="confirmation"
                  label="Confirmer le mot de passe"
                  value={confirmation}
                  onChange={setConfirmation}
                  type="password"
                  autoComplete="new-password"
                />
              )}
              {(etape === 'second-facteur' || etape === 'nouveau-mot-de-passe') && (
                <Champ
                  id="code-second-facteur"
                  label={
                    etape === 'second-facteur'
                      ? 'Code de vérification'
                      : 'Code MFA ou de secours si actif'
                  }
                  value={code}
                  onChange={setCode}
                  autoComplete="one-time-code"
                  classe={styles.code}
                  facultatif={etape === 'nouveau-mot-de-passe'}
                />
              )}
              {etape === 'second-facteur' && (
                <label className={styles.confiance}>
                  <input
                    type="checkbox"
                    checked={faireConfiance}
                    onChange={(e) => setFaireConfiance(e.target.checked)}
                  />
                  Faire confiance à ce téléphone pendant 30 jours
                </label>
              )}

              {erreur !== null && (
                <p className={styles.erreur} role="alert">
                  {erreur}
                </p>
              )}
              <button className={styles.bouton} type="submit" disabled={enCours}>
                {enCours ? 'Vérification…' : actionDe(etape)}
              </button>
            </form>
          )}

          {etape === 'identifiants' && (
            <nav className={styles.actionsSecondaires} aria-label="Accès au compte">
              <button type="button" onClick={() => setEtape('recuperation')}>
                Mot de passe oublié
              </button>
              <button type="button" onClick={() => setEtape('inscription')}>
                Créer un compte
              </button>
            </nav>
          )}
          {etape === 'message' && erreur !== null && (
            <p className={styles.erreur} role="alert">
              {erreur}
            </p>
          )}
        </section>

        <footer className={styles.pied}>
          <LockKeyhole size={15} aria-hidden />
          <span>Bêta privée sur invitation · connexion sécurisée</span>
        </footer>
      </div>
    </main>
  )
}

type ChampProps = {
  id: string
  label: string
  value: string
  onChange: (valeur: string) => void
  type?: 'text' | 'email' | 'password'
  autoComplete?: string
  classe?: string
  facultatif?: boolean
}

function Champ({
  id,
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  classe,
  facultatif = false,
}: ChampProps) {
  return (
    <div className={styles.champ}>
      <label className={styles.etiquette} htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className={`${styles.saisie} ${classe ?? ''}`}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        autoCapitalize={type === 'email' ? 'none' : undefined}
        spellCheck={false}
        inputMode={type === 'email' ? 'email' : undefined}
        required={!facultatif}
      />
    </div>
  )
}

function titreDe(etape: Etape): string {
  if (etape === 'identifiants') return 'Bonsoir.'
  if (etape === 'second-facteur') return 'Vérifions que c’est bien vous.'
  if (etape === 'inscription') return 'Votre espace commence ici.'
  if (etape === 'recuperation') return 'Retrouvons votre accès.'
  if (etape === 'nouveau-mot-de-passe') return 'Choisissez un nouvel accès.'
  return 'C’est presque terminé.'
}

function descriptionDe(etape: Etape, message: string): string {
  if (etape === 'identifiants')
    return 'Retrouvez votre argent, vos projets et votre prochain mois au même endroit.'
  if (etape === 'second-facteur')
    return 'Entrez le code de votre application ou un code de secours.'
  if (etape === 'inscription') return 'La bêta est privée ; une invitation peut être nécessaire.'
  if (etape === 'recuperation') return 'Nous enverrons un lien si cette adresse possède un compte.'
  if (etape === 'nouveau-mot-de-passe')
    return 'Votre code MFA reste demandé si votre compte en possède un.'
  return message || 'Vous pouvez revenir à la connexion.'
}

function actionDe(etape: Etape): string {
  if (etape === 'identifiants') return 'Se connecter'
  if (etape === 'second-facteur') return 'Continuer'
  if (etape === 'inscription') return 'Créer mon espace'
  if (etape === 'recuperation') return 'Recevoir le lien'
  return 'Remplacer le mot de passe'
}
