import { Copy, ShieldCheck, ShieldOff } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { EnrolementPropose } from '../api/client'
import { ErreurApi, api } from '../api/client'
import styles from './SecondFacteur.module.css'

/** Où l'on en est de l'enrôlement. Un état explicite plutôt que trois booléens : les
 *  combinaisons impossibles — « en train de scanner ET déjà activé » — n'existent pas. */
type Etape = 'inconnu' | 'inactif' | 'scan' | 'codes' | 'actif'

/**
 * Activation et retrait du second facteur.
 *
 * **Trois écrans successifs, jamais simultanés.** Scanner, confirmer, noter ses codes : les
 * montrer ensemble laisserait croire qu'on peut sauter la confirmation, or c'est
 * précisément elle qui empêche de verrouiller le compte — sans un premier code vérifié,
 * une heure fausse sur le téléphone rendrait l'application inaccessible pour toujours.
 *
 * **Les codes de secours ne s'affichent qu'UNE fois.** Le serveur ne les garde que hachés ;
 * les redemander est impossible, pas seulement interdit. L'écran doit donc insister, et
 * exiger une confirmation explicite avant de les faire disparaître.
 */
export function SecondFacteur() {
  const [etape, setEtape] = useState<Etape>('inconnu')
  const [restants, setRestants] = useState(0)
  const [propose, setPropose] = useState<EnrolementPropose | null>(null)
  const [codes, setCodes] = useState<readonly string[]>([])
  const [code, setCode] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [occupe, setOccupe] = useState(false)
  const [notes, setNotes] = useState(false)

  const relire = useCallback(async () => {
    const etat = await api.etatSecondFacteur()
    setRestants(etat.codes_de_secours_restants)
    setEtape(etat.actif ? 'actif' : 'inactif')
  }, [])

  useEffect(() => {
    void relire().catch(() => setEtape('inactif'))
  }, [relire])

  async function tenter(action: () => Promise<void>) {
    setErreur(null)
    setOccupe(true)
    try {
      await action()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setOccupe(false)
    }
  }

  if (etape === 'inconnu') {
    // « Pas encore reçu » n'est pas « inactif » : afficher le second par défaut ferait
    // proposer d'activer ce qui l'est peut-être déjà.
    return <p className={styles.note}>Chargement…</p>
  }

  return (
    <div className={styles.bloc}>
      <h2 className={styles.titre}>Vérification en deux étapes</h2>

      {erreur !== null && (
        <p className={styles.erreur} role="alert">
          {erreur}
        </p>
      )}

      {etape === 'inactif' && (
        <>
          <p className={styles.note}>
            Un code à six chiffres, en plus du mot de passe, à chaque connexion. Il vous
            faudra une application d’authentification sur votre téléphone.
          </p>
          <button
            type="button"
            className={styles.principal}
            disabled={occupe}
            onClick={() =>
              void tenter(async () => {
                setPropose(await api.preparerSecondFacteur())
                setEtape('scan')
              })
            }
          >
            <ShieldCheck size={16} strokeWidth={2} aria-hidden />
            Activer
          </button>
        </>
      )}

      {etape === 'scan' && propose !== null && (
        <form
          className={styles.etape}
          onSubmit={(evenement: FormEvent) => {
            evenement.preventDefault()
            void tenter(async () => {
              const active = await api.activerSecondFacteur(code)
              setCodes(active.codes_de_secours)
              setCode('')
              setNotes(false)
              setEtape('codes')
            })
          }}
        >
          <p className={styles.note}>
            Scannez ce carré avec votre application d’authentification, puis tapez le code
            qu’elle affiche.
          </p>
          {/* Le SVG vient du serveur. `dangerouslySetInnerHTML` est ici sans danger au sens
              propre : la chaîne est produite par notre propre code à partir d'un URI que
              nous fabriquons, elle ne contient aucune donnée saisie par qui que ce soit. */}
          <div
            className={styles.qr}
            aria-label="Code à scanner"
            dangerouslySetInnerHTML={{ __html: propose.qr_svg }}
          />

          {/* La saisie manuelle n'est pas un repli de second ordre : un ordinateur de
              bureau n'a pas de caméra, et certaines applications n'acceptent que la clé. */}
          <details className={styles.repli}>
            <summary>Impossible de scanner ?</summary>
            <p className={styles.note}>Entrez cette clé dans votre application :</p>
            <code className={styles.secret}>{propose.secret}</code>
            <button
              type="button"
              className={styles.secondaire}
              onClick={() => void navigator.clipboard?.writeText(propose.secret)}
            >
              <Copy size={14} strokeWidth={2} aria-hidden />
              Copier la clé
            </button>
          </details>

          <label className={styles.etiquette} htmlFor="totp-code">
            Code affiché par l’application
          </label>
          <input
            id="totp-code"
            className={styles.champ}
            value={code}
            onChange={(evenement) => setCode(evenement.target.value)}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
          />
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.secondaire}
              onClick={() => {
                setEtape('inactif')
                setCode('')
                setErreur(null)
              }}
            >
              Annuler
            </button>
            <button
              type="submit"
              className={styles.principal}
              disabled={occupe || code.trim().length < 6}
            >
              Vérifier et activer
            </button>
          </div>
        </form>
      )}

      {etape === 'codes' && (
        <div className={styles.etape}>
          <p className={styles.avertissement}>
            Notez ces dix codes et rangez-les hors de votre téléphone. Ils sont la SEULE
            façon d’entrer si vous le perdez, chacun ne sert qu’une fois, et ils ne
            s’afficheront plus jamais.
          </p>
          <ul className={styles.codes}>
            {codes.map((secours) => (
              <li key={secours}>
                <code>{secours}</code>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className={styles.secondaire}
            onClick={() => void navigator.clipboard?.writeText(codes.join('\n'))}
          >
            <Copy size={14} strokeWidth={2} aria-hidden />
            Tout copier
          </button>
          {/* Une case à cocher plutôt qu'un simple « Fermer » : le geste doit être
              délibéré, parce qu'il est irréversible et que rien ne le dira ensuite. */}
          <label className={styles.confirmation}>
            <input
              type="checkbox"
              checked={notes}
              onChange={(evenement) => setNotes(evenement.target.checked)}
            />{' '}
            Je les ai notés
          </label>
          <button
            type="button"
            className={styles.principal}
            disabled={!notes}
            onClick={() => void relire()}
          >
            Terminer
          </button>
        </div>
      )}

      {etape === 'actif' && (
        <>
          <p className={styles.note}>
            <ShieldCheck size={16} strokeWidth={2} aria-hidden /> Active. Il vous reste{' '}
            <strong>{restants}</strong> code{restants > 1 ? 's' : ''} de secours.
          </p>
          {restants === 0 && (
            <p className={styles.avertissement}>
              Plus aucun code de secours. Si vous perdez votre téléphone, il n’existera
              aucun moyen de revenir. Désactivez puis réactivez pour en obtenir dix neufs.
            </p>
          )}
          <form
            className={styles.etape}
            onSubmit={(evenement: FormEvent) => {
              evenement.preventDefault()
              void tenter(async () => {
                await api.desactiverSecondFacteur(code)
                setCode('')
                await relire()
              })
            }}
          >
            <label className={styles.etiquette} htmlFor="totp-retrait">
              Pour désactiver, entrez un code en cours
            </label>
            <input
              id="totp-retrait"
              className={styles.champ}
              value={code}
              onChange={(evenement) => setCode(evenement.target.value)}
              inputMode="numeric"
              autoComplete="one-time-code"
            />
            <button
              type="submit"
              className={styles.destructif}
              disabled={occupe || code.trim() === ''}
            >
              <ShieldOff size={16} strokeWidth={2} aria-hidden />
              Désactiver
            </button>
          </form>
        </>
      )}
    </div>
  )
}
