import { Check, X } from 'lucide-react'
import { useState } from 'react'

import type { CategoriePublique, NatureCategorie, TeinteCategorie } from '../api/client'
import { ErreurApi, api } from '../api/client'
import styles from './ChoixCategorie.module.css'

/** Valeur sentinelle de l'option de création. Elle ne peut pas entrer en collision avec un
 *  identifiant : ceux-ci sont des UUID, et celle-ci n'en a pas la forme. */
const CREER = '#creer'

/** Les six teintes du domaine, dans l'ordre où elles sont proposées.
 *
 *  Recopiées depuis `TeinteCategorie`, faute de pouvoir énumérer un type TypeScript à
 *  l'exécution — le schéma est généré, il ne produit pas de tableau. Un test unitaire
 *  vérifie que cette liste et le type ne divergent pas : sans lui, ajouter une teinte au
 *  domaine la laisserait inutilisée ici sans que rien ne le signale. */
const TEINTES: readonly TeinteCategorie[] = ['violet', 'cyan', 'vert', 'ambre', 'rose', 'ardoise']

/**
 * Teinte attribuée à une catégorie créée à la volée : la MOINS employée jusqu'ici.
 *
 * Ce n'est pas un détail cosmétique. La pastille de couleur est ce qui permet de repérer
 * une catégorie dans la liste de l'accueil sans lire son nom ; en tirer une au hasard
 * produirait tôt ou tard deux voisines de la même teinte, ce qui retire à la pastille sa
 * seule utilité. À égalité, l'ordre de `TEINTES` tranche — le résultat est déterministe,
 * donc testable.
 */
export function teinteLaMoinsEmployee(categories: readonly CategoriePublique[]): TeinteCategorie {
  const emplois = new Map<TeinteCategorie, number>(TEINTES.map((teinte) => [teinte, 0]))
  for (const categorie of categories) {
    const teinte = categorie.teinte as TeinteCategorie
    if (emplois.has(teinte)) emplois.set(teinte, emplois.get(teinte)! + 1)
  }
  return TEINTES.reduce((meilleure, teinte) =>
    emplois.get(teinte)! < emplois.get(meilleure)! ? teinte : meilleure,
  )
}

type Props = {
  readonly categories: readonly CategoriePublique[]
  /** Seules les catégories de cette nature sont proposées, et c'est elle que prend une
   *  catégorie créée ici. La nature n'est pas modifiable après coup — c'est une règle du
   *  domaine — donc la deviner serait la seule décision irréversible de ce composant. */
  readonly nature: NatureCategorie
  readonly valeur: string
  readonly surChangement: (categorieId: string) => void
  /** Prévient l'application qu'une catégorie est née : à elle de relire ses référentiels.
   *  Le composant ne peut pas s'en charger — il ne détient pas la liste, il la reçoit. */
  readonly surCreation: (categorie: CategoriePublique) => void | Promise<void>
  readonly id?: string
  /** Étiquette accessible, quand aucun `<label>` extérieur ne pointe vers le champ. */
  readonly libelle?: string
  /** Identifiants à retirer de la liste — l'écran des budgets exclut ainsi les catégories
   *  déjà plafonnées. Le filtre vit chez l'appelant : lui seul sait pourquoi il exclut. */
  readonly exclure?: ReadonlySet<string>
  /** Texte de l'option neutre. `null` la retire : sur les budgets, « sans catégorie » ne
   *  veut rien dire — un plafond porte toujours sur une catégorie. */
  readonly optionNeutre?: string | null
}

/**
 * Choix d'une catégorie, avec création sur place.
 *
 * Ce qu'il résout : ajouter une catégorie manquante demandait de quitter sa saisie, d'aller
 * dans Paramètres → Catégories, de la créer, de revenir et de tout ressaisir. Le seul
 * moment où l'on découvre qu'une catégorie manque est précisément celui où l'on est en
 * train de s'en servir.
 *
 * Ce qu'il ne fait PAS : il ne demande ni teinte ni réglage. Une création à la volée doit
 * coûter un nom et une validation, sinon elle ne remplace pas l'écran des catégories —
 * elle le duplique. La teinte est attribuée par `teinteLaMoinsEmployee`, et reste
 * modifiable dans les paramètres, qui demeurent l'écran où l'on RANGE ses catégories.
 */
export function ChoixCategorie({
  categories,
  nature,
  valeur,
  surChangement,
  surCreation,
  id,
  libelle,
  exclure,
  optionNeutre = 'Sans catégorie',
}: Props) {
  const [enCreation, setEnCreation] = useState(false)
  const [nom, setNom] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  const proposees = categories.filter(
    (categorie) => categorie.nature === nature && !exclure?.has(categorie.id),
  )

  async function creer() {
    const propre = nom.trim()
    if (propre === '') {
      setErreur('Un nom est nécessaire.')
      return
    }
    setEnCours(true)
    setErreur(null)
    try {
      const creee = await api.creerCategorie(propre, nature, teinteLaMoinsEmployee(categories))
      // Sélectionnée dans la foulée : créer une catégorie pour devoir ensuite la choisir
      // dans la liste ferait deux gestes là où l'intention n'en portait qu'un.
      surChangement(creee.id)
      await surCreation(creee)
      setEnCreation(false)
      setNom('')
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  if (enCreation) {
    return (
      <div className={styles.creation}>
        <div className={styles.ligne}>
          <input
            className={styles.saisie}
            value={nom}
            onChange={(evenement) => setNom(evenement.target.value)}
            placeholder="Nom de la catégorie"
            aria-label="Nom de la nouvelle catégorie"
            autoFocus
            // Le formulaire de saisie qui entoure ce composant ne doit pas être soumis par
            // la touche Entrée d'un champ qui ne le concerne pas : la frappe est traitée
            // ici, et l'événement s'arrête là.
            onKeyDown={(evenement) => {
              if (evenement.key === 'Enter') {
                evenement.preventDefault()
                void creer()
              }
              if (evenement.key === 'Escape') setEnCreation(false)
            }}
          />
          <button
            type="button"
            className={styles.valider}
            onClick={() => void creer()}
            disabled={enCours}
            aria-label="Créer la catégorie"
          >
            <Check size={18} strokeWidth={2.4} aria-hidden />
          </button>
          <button
            type="button"
            className={styles.abandonner}
            onClick={() => {
              setEnCreation(false)
              setErreur(null)
            }}
            aria-label="Abandonner la création"
          >
            <X size={18} strokeWidth={2} aria-hidden />
          </button>
        </div>
        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}
      </div>
    )
  }

  return (
    <select
      id={id}
      className={styles.choix}
      value={valeur}
      aria-label={libelle}
      onChange={(evenement) => {
        if (evenement.target.value === CREER) {
          setEnCreation(true)
          return
        }
        surChangement(evenement.target.value)
      }}
    >
      {optionNeutre !== null && <option value="">{optionNeutre}</option>}
      {proposees.map((categorie) => (
        <option key={categorie.id} value={categorie.id}>
          {categorie.nom}
        </option>
      ))}
      {/* En dernier, et non en tête : la création est le cas rare, et une première ligne
          qui n'est pas une catégorie se choisit par erreur sur un sélecteur natif iOS, où
          le doigt part de la valeur courante. */}
      <option value={CREER}>+ Nouvelle catégorie…</option>
    </select>
  )
}
