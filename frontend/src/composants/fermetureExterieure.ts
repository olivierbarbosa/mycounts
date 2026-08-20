import type { MouseEvent } from 'react'

/**
 * Ferme une feuille modale quand l'appui a lieu EN DEHORS d'elle, sur le voile.
 *
 * Écrit une fois et non dans chacune des quatre feuilles, pour une raison qui tient dans
 * la condition ci-dessous : `evenement.target !== evenement.currentTarget` est facile à
 * oublier, et sans elle la feuille se ferme aussi quand on relâche un bouton à
 * l'intérieur — le clic remonte jusqu'au voile. Le défaut ne se voit pas au premier essai,
 * seulement sur les gestes qui traversent une bordure.
 *
 * Ce que ce comportement ne fait PAS : demander confirmation quand un formulaire est
 * entamé. Un appui hors de la feuille est le geste natif d'iOS pour abandonner, et
 * l'interrompre par une question ferait perdre à ce geste ce qui le rend rapide. Ce qui
 * est saisi et non validé est donc perdu — la contrepartie assumée d'une fermeture en un
 * geste.
 */
export function fermetureExterieure(surFermeture: () => void) {
  return (evenement: MouseEvent<HTMLElement>) => {
    if (evenement.target !== evenement.currentTarget) return
    surFermeture()
  }
}
