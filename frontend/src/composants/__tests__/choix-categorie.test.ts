import { describe, expect, it } from 'vitest'

import type { CategoriePublique, TeinteCategorie } from '../../api/client'
import { teinteLaMoinsEmployee } from '../ChoixCategorie'

/** Fabrique une catégorie réduite à ce que la fonction lit. Le reste du type ne l'intéresse
 *  pas, et le remplir donnerait à croire qu'il compte. */
const avecTeintes = (teintes: readonly string[]): readonly CategoriePublique[] =>
  teintes.map((teinte, rang) => ({ teinte, id: String(rang) }) as unknown as CategoriePublique)

describe('teinteLaMoinsEmployee', () => {
  it('rend la première teinte quand aucune catégorie n’existe', () => {
    expect(teinteLaMoinsEmployee([])).toBe('violet')
  })

  it('évite les teintes déjà prises', () => {
    // Cinq des six sont employées : la seule libre est la seule réponse acceptable.
    expect(teinteLaMoinsEmployee(avecTeintes(['violet', 'cyan', 'vert', 'ambre', 'rose']))).toBe(
      'ardoise',
    )
  })

  it('choisit la MOINS employée, et non simplement une inemployée', () => {
    // Toutes sont employées au moins une fois : une fonction qui ne saurait qu'écarter les
    // teintes déjà vues n'aurait ici plus rien à répondre. Celle-ci compte les emplois.
    const beaucoupDeViolet = avecTeintes([
      'violet',
      'violet',
      'violet',
      'cyan',
      'cyan',
      'vert',
      'ambre',
      'rose',
      'ardoise',
    ])
    expect(teinteLaMoinsEmployee(beaucoupDeViolet)).toBe('vert')
  })

  it('ignore une teinte inconnue du domaine plutôt que de la compter', () => {
    // Une teinte retirée du domaine mais restée en base ne doit pas fausser le décompte —
    // ni faire renvoyer une valeur que le domaine refuserait.
    expect(teinteLaMoinsEmployee(avecTeintes(['fuchsia', 'violet']))).toBe('cyan')
  })
})

/**
 * Garde-fou de divergence : `ChoixCategorie` porte la liste des teintes en dur, faute de
 * pouvoir énumérer un type TypeScript à l'exécution.
 *
 * Ce `Record` cesse de compiler si `TeinteCategorie` gagne une valeur — c'est la
 * vérification qui compte, et elle est faite par `tsc`, pas par vitest. L'assertion
 * ci-dessous couvre l'autre sens : une teinte retirée du type mais laissée dans la liste.
 */
const TOUTES: Record<TeinteCategorie, true> = {
  violet: true,
  cyan: true,
  vert: true,
  ambre: true,
  rose: true,
  ardoise: true,
}

describe('liste des teintes', () => {
  it('propose exactement les teintes du domaine', () => {
    // Chaque teinte du domaine doit pouvoir SORTIR de la fonction : on sature les cinq
    // autres et l'on vérifie que c'est bien celle qui reste qui est rendue. Une teinte
    // absente de la liste de `ChoixCategorie` fait échouer ce tour de boucle.
    for (const teinte of Object.keys(TOUTES) as TeinteCategorie[]) {
      const autres = (Object.keys(TOUTES) as TeinteCategorie[]).filter((t) => t !== teinte)
      expect(teinteLaMoinsEmployee(avecTeintes(autres))).toBe(teinte)
    }
  })
})
