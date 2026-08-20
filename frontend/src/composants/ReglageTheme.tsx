import { useEffect, useState } from 'react'

import styles from './ReglageTransparence.module.css'

/**
 * Choix du thème : système, sombre ou clair.
 *
 * `tokens.ts` sait lire `data-theme` depuis le début, mais rien ne l'écrivait : l'app
 * suivait donc l'apparence du téléphone, sans recours. Un iPhone réglé sur « automatique »
 * bascule en clair au lever du jour, et l'application changeait de couleurs toute seule
 * sans qu'aucun écran ne permette de s'y opposer.
 *
 * « Système » reste le défaut, et pas seulement par habitude : c'est le seul choix qui
 * respecte un utilisateur ayant réglé son téléphone en clair pour une raison de confort
 * visuel.
 */
const THEMES = [
  { cle: 'systeme', libelle: 'Système' },
  { cle: 'sombre', libelle: 'Sombre' },
  { cle: 'clair', libelle: 'Clair' },
] as const

type Theme = (typeof THEMES)[number]['cle']

const CLE_STOCKAGE = 'mycounts.theme'

/** Applique le thème enregistré. Appelé au démarrage, AVANT le premier rendu de React :
 *  sans cela l'écran s'affiche une fraction de seconde dans le thème du système avant de
 *  basculer, et ce clignotement se voit d'autant plus que les deux thèmes s'opposent. */
export function appliquerThemeEnregistre() {
  const enregistre = localStorage.getItem(CLE_STOCKAGE)
  if (enregistre === 'sombre' || enregistre === 'clair') {
    document.documentElement.setAttribute('data-theme', enregistre)
  }
}

export function ReglageTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const enregistre = localStorage.getItem(CLE_STOCKAGE)
    return THEMES.some((t) => t.cle === enregistre) ? (enregistre as Theme) : 'systeme'
  })

  useEffect(() => {
    // « Système » retire l'attribut au lieu d'en écrire un troisième : c'est son ABSENCE
    // que la feuille de tokens interprète comme « suis le téléphone ».
    if (theme === 'systeme') document.documentElement.removeAttribute('data-theme')
    else document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(CLE_STOCKAGE, theme)
  }, [theme])

  return (
    <div className={styles.groupe} role="group" aria-label="Thème de l’interface">
      {THEMES.map((option) => (
        <button
          key={option.cle}
          type="button"
          className={styles.option}
          aria-pressed={option.cle === theme}
          onClick={() => setTheme(option.cle)}
        >
          {option.libelle}
        </button>
      ))}
    </div>
  )
}
