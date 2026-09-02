import { CloudOff } from 'lucide-react'

import styles from './BandeauReseau.module.css'

/**
 * Coupure réseau EN COURS de session : l'écran reste, le bandeau dit l'état.
 *
 * Avant lui, `offline` remplaçait toute l'application par `EtatHorsLigne`. Or iOS émet cet
 * événement en passant du Wi-Fi au cellulaire, et le remplacement démontait la feuille de
 * saisie avec le montant qu'on venait d'y taper. L'écran plein reste réservé au démarrage
 * sans réseau, quand il n'y a rien à préserver (`App.tsx`).
 *
 * Ce bandeau n'annonce rien d'autre que l'état : il ne met aucune saisie en attente, et
 * n'enregistre rien localement — les montants ne vivent pas sur le téléphone.
 */
export function BandeauReseau() {
  return (
    <div className={styles.bandeau} role="status" aria-label="État du réseau">
      <span className={styles.icone} aria-hidden>
        <CloudOff size={20} strokeWidth={2} />
      </span>
      <p className={styles.texte}>
        Vous êtes hors ligne. Ce qui est affiché reste, et vos actions attendront le retour
        du réseau.
      </p>
    </div>
  )
}
