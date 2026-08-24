import { Copy, ShieldCheck, WalletCards } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'

import { ErreurApi, api, type EnrolementPropose, type UtilisateurPublic } from '../api/client'
import styles from './EnrolementMfa.module.css'

type Props = {
  readonly surTermine: (utilisateur: UtilisateurPublic) => void | Promise<void>
}

export function EnrolementMfa({ surTermine }: Props) {
  const [proposition, setProposition] = useState<EnrolementPropose | null>(null)
  const [code, setCode] = useState('')
  const [codes, setCodes] = useState<readonly string[]>([])
  const [faireConfiance, setFaireConfiance] = useState(true)
  const [notes, setNotes] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [occupe, setOccupe] = useState(false)

  useEffect(() => {
    void api
      .preparerSecondFacteur()
      .then(setProposition)
      .catch((cause) =>
        setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.'),
      )
  }, [])

  async function activer(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)
    setOccupe(true)
    try {
      const resultat = await api.activerSecondFacteur(code, faireConfiance)
      setCodes(resultat.codes_de_secours)
      setCode('')
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setOccupe(false)
    }
  }

  async function terminer() {
    setOccupe(true)
    try {
      await surTermine(await api.moi())
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setOccupe(false)
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.marque}>
        <WalletCards size={24} aria-hidden />
        <span>mycounts</span>
        <small>Sécurité · 1 sur 1</small>
      </header>

      {codes.length === 0 ? (
        <section className={styles.contenu}>
          <div className={styles.introduction}>
            <ShieldCheck size={28} aria-hidden />
            <h1>Protégez votre espace.</h1>
            <p>Scannez le carré, puis saisissez le code affiché sur votre téléphone.</p>
          </div>
          {proposition !== null && (
            <form className={styles.formulaire} onSubmit={activer}>
              <div
                className={styles.qr}
                aria-label="Code à scanner"
                dangerouslySetInnerHTML={{ __html: proposition.qr_svg }}
              />
              <div className={styles.saisieManuelle}>
                <code>{proposition.secret}</code>
                <button
                  type="button"
                  aria-label="Copier la clé"
                  onClick={() => void navigator.clipboard?.writeText(proposition.secret)}
                >
                  <Copy size={16} aria-hidden />
                </button>
              </div>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="123 456"
                maxLength={6}
                aria-label="Code affiché par l’application"
                autoFocus
              />
              <label className={styles.confiance}>
                <input
                  type="checkbox"
                  checked={faireConfiance}
                  onChange={(e) => setFaireConfiance(e.target.checked)}
                />
                Faire confiance à ce téléphone 30 jours
              </label>
              {erreur !== null && (
                <p className={styles.erreur} role="alert">
                  {erreur}
                </p>
              )}
              <button
                className={styles.principal}
                type="submit"
                disabled={occupe || code.trim().length < 6}
              >
                Activer et continuer
              </button>
            </form>
          )}
          {proposition === null && erreur === null && <p>Préparation…</p>}
        </section>
      ) : (
        <section className={styles.contenu}>
          <div className={styles.introduction}>
            <ShieldCheck size={28} aria-hidden />
            <h1>Gardez une porte de secours.</h1>
            <p>Copiez ces codes hors de votre téléphone. Ils ne seront plus affichés.</p>
          </div>
          <ul className={styles.codes}>
            {codes.map((secours) => (
              <li key={secours}>
                <code>{secours}</code>
              </li>
            ))}
          </ul>
          <button
            className={styles.copier}
            type="button"
            onClick={() => void navigator.clipboard?.writeText(codes.join('\n'))}
          >
            <Copy size={16} aria-hidden />
            Tout copier
          </button>
          <label className={styles.confiance}>
            <input type="checkbox" checked={notes} onChange={(e) => setNotes(e.target.checked)} />
            Je les ai conservés dans un endroit sûr
          </label>
          {erreur !== null && (
            <p className={styles.erreur} role="alert">
              {erreur}
            </p>
          )}
          <button
            className={styles.principal}
            type="button"
            disabled={!notes || occupe}
            onClick={() => void terminer()}
          >
            Découvrir mon espace
          </button>
        </section>
      )}
    </main>
  )
}
