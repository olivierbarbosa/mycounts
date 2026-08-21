import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

type Props = {
  readonly children: ReactNode
}

/**
 * Rend son contenu directement dans `<body>`, hors de l'arbre DOM où il est écrit.
 *
 * **Pourquoi une modale en a besoin.** Un `z-index` n'est comparable qu'entre frères du
 * même contexte d'empilement. Or les écrans d'onglet portent une animation d'entrée dont
 * l'état final est conservé (`animation-fill-mode: both`) : le `transform` reste posé
 * indéfiniment, fût-il l'identité, et tout `transform` non-`none` crée un contexte. Une
 * feuille écrite DANS un écran d'onglet voyait donc son plan 40 confiné dans un conteneur
 * à `z-index: auto`, et passait sous la barre de navigation, qui est au plan 10.
 *
 * Mesuré le 22 août 2026 : `document.elementFromPoint` au centre de la barre rendait une
 * icône de la barre, feuille ouverte par-dessus (ERREURS.md #049).
 *
 * **Pourquoi ici et non dans les écrans.** Corriger le contexte fautif — retirer le
 * `both`, ou poser un `z-index` sur le conteneur d'onglet — réglerait CE cas et laisserait
 * le suivant intact : la prochaine animation, le prochain `filter`, le prochain
 * `will-change` recréeraient un contexte, et la feuille disparaîtrait à nouveau sans que
 * personne n'ait touché à la feuille. Une modale ne doit pas dépendre de l'endroit du DOM
 * où on l'écrit.
 *
 * Le contexte React, lui, traverse le portail : les composants portés gardent leurs
 * fournisseurs, seul le point d'attache DOM change.
 */
export function Portail({ children }: Props) {
  return createPortal(children, document.body)
}
