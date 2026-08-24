import { Bell, Check, Download, Share } from 'lucide-react'
import { useEffect, useState } from 'react'

import { plateforme, type EtatInstallation, type EtatNotification } from '../plateforme'
import styles from './ApplicationAppareil.module.css'

const CLE_PREFERENCES = 'mycounts.notifications.appareil.v1'
const ALERTES = [
  { cle: 'budget', libelle: 'Budget presque épuisé' },
  { cle: 'charge', libelle: 'Charge bientôt prélevée' },
  { cle: 'epargne', libelle: 'Proposition d’épargne prête' },
  { cle: 'foyer', libelle: 'Changement important du foyer' },
] as const

type CleAlerte = (typeof ALERTES)[number]['cle']
type Preferences = Record<CleAlerte, boolean>

const PREFERENCES_INITIALES: Preferences = {
  budget: true,
  charge: true,
  epargne: true,
  foyer: true,
}

function lirePreferences(): Preferences {
  try {
    const lues = JSON.parse(localStorage.getItem(CLE_PREFERENCES) ?? '') as Partial<Preferences>
    return { ...PREFERENCES_INITIALES, ...lues }
  } catch {
    return PREFERENCES_INITIALES
  }
}

export function ApplicationAppareil() {
  const [installation, setInstallation] = useState<EtatInstallation>(() =>
    plateforme.installation.etat(),
  )
  const [notification, setNotification] = useState<EtatNotification>(() =>
    plateforme.notifications.etat(),
  )
  const [preferences, setPreferences] = useState<Preferences>(lirePreferences)

  useEffect(() => plateforme.installation.ecouter(setInstallation), [])

  function basculer(cle: CleAlerte) {
    const suivantes = { ...preferences, [cle]: !preferences[cle] }
    setPreferences(suivantes)
    localStorage.setItem(CLE_PREFERENCES, JSON.stringify(suivantes))
  }

  const notificationPossibleSurIos = !plateforme.estIos || installation === 'installee'

  return (
    <div className={styles.contenu}>
      <section className={styles.carte} aria-labelledby="installation-application">
        <div className={styles.entete}>
          <span className={styles.icone} aria-hidden>
            <Download size={21} strokeWidth={2} />
          </span>
          <div>
            <h2 id="installation-application" className={styles.titre}>
              Sur l’écran d’accueil
            </h2>
            <p className={styles.note}>MyCounts s’ouvre ensuite comme une application.</p>
          </div>
        </div>

        {installation === 'installee' ? (
          <p className={styles.succes}>
            <Check size={18} strokeWidth={2} aria-hidden />
            L’application est installée sur cet appareil.
          </p>
        ) : installation === 'installable' ? (
          <button
            type="button"
            className={styles.primaire}
            onClick={() => void plateforme.installation.demander()}
          >
            Installer MyCounts
          </button>
        ) : installation === 'instructions-ios' ? (
          <ol className={styles.etapes}>
            <li>
              Touchez <Share size={17} strokeWidth={2} aria-label="Partager" /> dans Safari.
            </li>
            <li>Choisissez « Sur l’écran d’accueil », puis « Ajouter ».</li>
          </ol>
        ) : (
          <p className={styles.note}>
            Ouvrez le menu de votre navigateur puis choisissez « Installer l’application ».
          </p>
        )}
      </section>

      <section className={styles.carte} aria-labelledby="notifications-application">
        <div className={styles.entete}>
          <span className={styles.icone} aria-hidden>
            <Bell size={21} strokeWidth={2} />
          </span>
          <div>
            <h2 id="notifications-application" className={styles.titre}>
              Notifications discrètes
            </h2>
            <p className={styles.note}>Aucun montant n’apparaît sur l’écran verrouillé.</p>
          </div>
        </div>

        {notification === 'granted' ? (
          <p className={styles.succes}>
            <Check size={18} strokeWidth={2} aria-hidden />
            Autorisées sur cet appareil
          </p>
        ) : notification === 'denied' ? (
          <p className={styles.note} role="status">
            Les notifications sont bloquées. Vous pouvez les réactiver dans les réglages du
            téléphone ou du navigateur.
          </p>
        ) : notification === 'indisponible' ? (
          <p className={styles.note}>Ce navigateur ne prend pas en charge les notifications.</p>
        ) : notificationPossibleSurIos ? (
          <button
            type="button"
            className={styles.primaire}
            onClick={() => void plateforme.notifications.demanderAutorisation().then(setNotification)}
          >
            Autoriser les notifications
          </button>
        ) : (
          <p className={styles.note}>
            Sur iPhone, installez d’abord MyCounts sur l’écran d’accueil. L’autorisation sera
            demandée ensuite, au bon moment.
          </p>
        )}

        <fieldset className={styles.preferences} disabled={notification !== 'granted'}>
          <legend>Me prévenir pour</legend>
          {ALERTES.map(({ cle, libelle }) => (
            <label key={cle} className={styles.preference}>
              <span>{libelle}</span>
              <input
                type="checkbox"
                checked={preferences[cle]}
                onChange={() => basculer(cle)}
              />
            </label>
          ))}
        </fieldset>
      </section>
    </div>
  )
}
