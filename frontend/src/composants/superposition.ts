import { useEffect } from 'react'

const ATTRIBUT = 'data-superpose'

/**
 * Signale qu'un écran couvre entièrement l'application.
 *
 * Sert à une seule chose, mesurée : arrêter le voyage des halos pendant qu'un panneau en
 * verre dépoli est ouvert. Un `backdrop-filter` plein écran doit refaire son flou à chaque
 * image tant que ce qu'il recouvre bouge — le débit tombait de 61 à 36 images par seconde
 * sur un écran de téléphone. Les halos étant cachés par le panneau, les figer ne retire
 * rien à ce qui est visible.
 *
 * L'attribut est compté plutôt que posé et retiré : deux écrans superposés — les budgets
 * ouverts sous les paramètres — se marcheraient sinon dessus, le premier fermé rendant le
 * mouvement au second qui est encore là.
 */
let ouverts = 0

export function useSuperposition() {
  useEffect(() => {
    ouverts += 1
    document.documentElement.setAttribute(ATTRIBUT, '')
    return () => {
      ouverts -= 1
      if (ouverts === 0) document.documentElement.removeAttribute(ATTRIBUT)
    }
  }, [])
}
