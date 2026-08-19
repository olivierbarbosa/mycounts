import { useEffect, useState } from 'react'

import styles from './ReglageTransparence.module.css'

/**
 * Réglage de transparence du verre, repris d'iOS 27 où Apple a dû l'introduire après
 * les retours sur la lisibilité. Trois positions plutôt qu'un interrupteur : « opaque »
 * doit rester atteignable sans passer par les réglages du système.
 */
const POSITIONS = [
  { cle: 'claire', libelle: 'Clair', variable: 'var(--verre-opacite-claire)' },
  { cle: 'moyenne', libelle: 'Moyen', variable: 'var(--verre-opacite-moyenne)' },
  { cle: 'opaque', libelle: 'Opaque', variable: 'var(--verre-opacite-opaque)' },
] as const

type Position = (typeof POSITIONS)[number]['cle']

const CLE_STOCKAGE = 'mycounts.transparence'

export function ReglageTransparence() {
  const [position, setPosition] = useState<Position>(() => {
    const enregistre = localStorage.getItem(CLE_STOCKAGE)
    return POSITIONS.some((p) => p.cle === enregistre) ? (enregistre as Position) : 'moyenne'
  })

  useEffect(() => {
    const choisie = POSITIONS.find((p) => p.cle === position) ?? POSITIONS[1]
    document.documentElement.style.setProperty('--verre-opacite', choisie.variable)
    localStorage.setItem(CLE_STOCKAGE, position)
  }, [position])

  return (
    <div className={styles.groupe} role="group" aria-label="Transparence de l'interface">
      {POSITIONS.map((option) => (
        <button
          key={option.cle}
          type="button"
          className={styles.option}
          aria-pressed={option.cle === position}
          onClick={() => setPosition(option.cle)}
        >
          {option.libelle}
        </button>
      ))}
    </div>
  )
}
