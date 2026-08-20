import {
  type AnimationEvent,
  type CSSProperties,
  type ReactNode,
  type RefObject,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

import styles from './EcranDeBulle.module.css'
import { useSuperposition } from './superposition'

/** Position et taille de la bulle au moment du clic, dans le repère de la fenêtre.
 *
 *  C'est le point de départ de la transition : sans elle, l'écran ne saurait pas d'où il
 *  vient et jaillirait du centre quelle que soit la bulle touchée. AUTEUR UNIQUE du type —
 *  il vivait dans `BulleAvatar`, ce qui obligeait la bulle du calendrier à importer son
 *  vocabulaire à l'avatar alors qu'elles sont deux instances du même objet. */
export type Origine = { readonly x: number; readonly y: number; readonly taille: number }

/** Part de la largeur au-delà de laquelle le glissement ferme au relâchement.
 *  0,38 et non 0,5 : à la moitié, on tire le pouce jusqu'au bord opposé de l'écran pour
 *  un geste que le système natif valide bien avant. */
const PART_DE_VALIDATION = 0.38

/** Vitesse, en pixels par milliseconde, qui ferme quelle que soit la distance parcourue.
 *  C'est ce qui rend le geste rapide utilisable : un coup de pouce sec sur 60 px doit
 *  fermer, sinon le glissement paraît « lourd » comparé à celui d'iOS. */
const VITESSE_DE_VALIDATION = 0.5

/** Largeur de la zone de bord qui capte le geste, en pixels.
 *
 *  Un capteur de bord DÉDIÉ, et non un `touch-action` posé sur l'écran entier : le
 *  contenu de ces écrans défile — verticalement partout, horizontalement dans la grille du
 *  calendrier. Écouter le geste sur toute la surface obligerait à arbitrer à chaque
 *  `pointermove` entre défiler et revenir, arbitrage que ni l'un ni l'autre ne gagne
 *  proprement. Sur une bande de 24 px collée au bord, la question ne se pose pas. */
const BORD_PX = 24

type Retour = {
  /** À étaler sur l'élément racine de l'écran. */
  readonly proprietes: {
    readonly ref: RefObject<HTMLDivElement | null>
    readonly className: string
    readonly style: CSSProperties
    readonly onAnimationEnd: (evenement: AnimationEvent) => void
  }
  /** À rendre DANS l'élément racine : la bande de bord qui capte le glissement. */
  readonly poigneeDeRetour: ReactNode
  /** Ferme avec le mouvement de repli, puis démonte. */
  readonly fermer: () => void
  /** Vrai dès que le repli est engagé. Exposé parce qu'un écran peut avoir à distinguer
   *  la fin du mouvement d'ENTRÉE de celle du mouvement de SORTIE — les paramètres ne
   *  posent leur verre qu'après la première. */
  readonly ferme: boolean
}

/**
 * Mécanique commune à tous les écrans ouverts depuis une bulle du haut.
 *
 * Trois choses, tenues au même endroit parce qu'elles décrivent un seul comportement :
 *
 *  1. **le même effet pour toutes les bulles** — l'écran éclôt du point exact où le doigt
 *     a touché et s'y replie en partant. Le calendrier avait jusqu'ici sa propre glissade
 *     latérale : deux boutons identiques dans la même rangée ouvraient leur écran de deux
 *     façons différentes ;
 *  2. **le glissement de retour**, du bord gauche vers la droite, comme sur iOS. En PWA
 *     `standalone`, WebKit ne le fournit PAS — le geste natif de Safari disparaît dès que
 *     l'application quitte l'onglet. Il faut donc l'écrire, et c'est le seul endroit où il
 *     l'est ;
 *  3. la suspension des halos de fond pendant la superposition (`useSuperposition`).
 *
 * Ce que ce hook ne fait PAS : gérer une pile de plusieurs niveaux. Ces écrans sont plats
 * — une bulle ouvre une page, le geste la referme. Les sous-menus des paramètres gardent
 * leur propre mouvement latéral, qui dit autre chose : on descend d'un cran, on ne quitte
 * pas l'écran.
 */
export function useEcranDeBulle(origine: Origine, surFermeture: () => void): Retour {
  const racine = useRef<HTMLDivElement>(null)
  const [ferme, setFerme] = useState(false)
  useSuperposition()

  const fermer = useCallback(() => setFerme(true), [])

  /* Le démontage est commandé par la FIN du mouvement et non par un délai recopié depuis
     la feuille de style : deux durées à tenir d'accord finissent toujours par diverger, et
     l'écart se voit — un saut, ou une page qui s'attarde.

     Sauf quand il n'y a pas de mouvement du tout. Sous `prefers-reduced-motion`, les
     classes de `global.css` valent `animation: none` : aucun `animationend` n'est jamais
     émis, et un écran fermé par ce seul chemin resterait monté pour toujours. Le cas est
     traité ici plutôt que d'être laissé à chaque appelant. */
  useEffect(() => {
    if (!ferme) return
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    surFermeture()
  }, [ferme, surFermeture])

  const finDuMouvement = (evenement: AnimationEvent) => {
    if (evenement.target !== evenement.currentTarget) return
    if (ferme) surFermeture()
  }

  /* Le geste écrit DIRECTEMENT dans le style de l'élément, sans passer par un état React.
     Un `setState` par `pointermove` reconstruirait l'arbre soixante fois par seconde
     pendant que le doigt bouge, sous un panneau en verre qui doit refaire son flou : c'est
     la recette exacte des trente images par seconde mesurées ailleurs dans ce projet. */
  useEffect(() => {
    const element = racine.current
    if (element === null) return

    let depart: { x: number; t: number } | null = null
    let distance = 0

    const suivre = (x: number) => {
      // Jamais vers la gauche : un écran qu'on peut tirer hors de son bord opposé donne
      // l'impression que le geste a raté alors qu'il n'a simplement pas commencé.
      distance = Math.max(0, x - depart!.x)
      element.style.transform = `translateX(${distance}px)`
      element.style.opacity = `${1 - Math.min(distance / element.offsetWidth, 1) * 0.35}`
    }

    const relacher = () => {
      if (depart === null) return
      const duree = Math.max(1, performance.now() - depart.t)
      const vitesse = distance / duree
      depart = null
      element.style.transition = ''
      element.style.touchAction = ''

      if (distance > element.offsetWidth * PART_DE_VALIDATION || vitesse > VITESSE_DE_VALIDATION) {
        // Le repli reprend la main à partir de la position atteinte par le doigt : rendre
        // d'abord l'écran à sa place pour l'animer ensuite produirait un retour en arrière
        // visible juste avant la fermeture.
        element.style.transform = ''
        element.style.opacity = ''
        setFerme(true)
        return
      }

      // Geste abandonné : l'écran revient à sa place, et le dit en revenant lui-même.
      element.style.transition = 'transform 220ms cubic-bezier(0.2, 0, 0, 1), opacity 220ms'
      element.style.transform = ''
      element.style.opacity = ''
      window.setTimeout(() => {
        element.style.transition = ''
      }, 220)
    }

    const commencer = (evenement: PointerEvent) => {
      if (evenement.clientX > BORD_PX) return
      // Au format bureau il n'y a pas de bord d'écran à tirer, et les 24 premiers pixels
      // sont ceux du rail de navigation : y armer un geste de retour volerait ses clics.
      if (window.matchMedia('(min-width: 1024px)').matches) return
      depart = { x: evenement.clientX, t: performance.now() }
      distance = 0
      // Coupe l'animation d'éclosion si le geste part alors qu'elle joue encore : sans
      // cela, les deux transforms se disputent l'élément et l'écran tremble.
      element.getAnimations().forEach((animation) => animation.finish())
      element.style.transition = 'none'
      element.setPointerCapture(evenement.pointerId)
    }

    const bouger = (evenement: PointerEvent) => {
      if (depart === null) return
      evenement.preventDefault()
      suivre(evenement.clientX)
    }

    element.addEventListener('pointerdown', commencer)
    element.addEventListener('pointermove', bouger)
    element.addEventListener('pointerup', relacher)
    element.addEventListener('pointercancel', relacher)
    return () => {
      element.removeEventListener('pointerdown', commencer)
      element.removeEventListener('pointermove', bouger)
      element.removeEventListener('pointerup', relacher)
      element.removeEventListener('pointercancel', relacher)
    }
  }, [])

  return {
    proprietes: {
      ref: racine,
      className: ferme ? 'mouvement-repli' : 'mouvement-eclosion',
      style: {
        '--origine-x': `${origine.x}px`,
        '--origine-y': `${origine.y}px`,
        '--origine-rayon': `${origine.taille / 2}px`,
      } as CSSProperties,
      onAnimationEnd: finDuMouvement,
    },
    poigneeDeRetour: <span className={styles.poignee} aria-hidden />,
    fermer,
    ferme,
  }
}
