import { RefreshCw, X } from 'lucide-react'
import { useRegisterSW } from 'virtual:pwa-register/react'

import styles from './MiseAJourPwa.module.css'

export function MiseAJourPwa() {
  const {
    offlineReady: [preteHorsLigne, masquerPrete],
    needRefresh: [miseAJourDisponible, masquerMiseAJour],
    updateServiceWorker,
  } = useRegisterSW({
    immediate: true,
    onRegisteredSW(_url, enregistrement) {
      // La navigation seule ne suffit pas sur une PWA laissée ouverte plusieurs jours.
      // Une vérification légère ne télécharge la nouvelle version que si le script a
      // changé ; l'utilisateur garde ensuite le dernier mot via le bouton ci-dessous.
      if (enregistrement !== undefined) {
        window.setInterval(() => void enregistrement.update(), 60 * 60 * 1000)
      }
    },
  })

  if (!preteHorsLigne && !miseAJourDisponible) return null

  return (
    <aside className={styles.message} aria-live="polite" aria-label="Mise à jour de l’application">
      <p className={styles.texte}>
        {miseAJourDisponible
          ? 'Une nouvelle version de MyCounts est prête.'
          : 'L’application pourra maintenant s’ouvrir sans réseau.'}
      </p>
      {miseAJourDisponible && (
        <button
          type="button"
          className={styles.action}
          onClick={() => void updateServiceWorker(true)}
        >
          <RefreshCw size={17} strokeWidth={2} aria-hidden />
          Mettre à jour
        </button>
      )}
      <button
        type="button"
        className={styles.fermer}
        aria-label="Fermer le message"
        onClick={() => {
          masquerPrete(false)
          masquerMiseAJour(false)
        }}
      >
        <X size={18} strokeWidth={2} aria-hidden />
      </button>
    </aside>
  )
}
