import { CloudOff, RefreshCw } from 'lucide-react'

import styles from './EtatHorsLigne.module.css'

export function EtatHorsLigne() {
  return (
    <main className={styles.page} aria-labelledby="titre-hors-ligne">
      <div className={styles.carte}>
        <span className={styles.icone} aria-hidden>
          <CloudOff size={30} strokeWidth={1.8} />
        </span>
        <h1 id="titre-hors-ligne" className={styles.titre}>
          Vous êtes hors ligne
        </h1>
        <p className={styles.texte}>
          Vos montants ne sont pas enregistrés sur ce téléphone. Reconnectez-vous pour retrouver
          vos comptes et effectuer une opération.
        </p>
        <button type="button" className={styles.bouton} onClick={() => window.location.reload()}>
          <RefreshCw size={18} strokeWidth={2} aria-hidden />
          Réessayer
        </button>
      </div>
    </main>
  )
}
