import { describe, expect, it } from 'vitest'

import { frequenceCourte, frequenceEnToutesLettres } from '../frequence'

describe('frequenceEnToutesLettres', () => {
  it.each([
    ['mois', 1, 'tous les mois'],
    ['mois', 3, 'tous les 3 mois'],
    ['an', 1, 'tous les ans'],
    ['an', 2, 'tous les 2 ans'],
    ['semaine', 1, 'toutes les semaines'],
    ['semaine', 2, 'toutes les 2 semaines'],
    ['jour', 1, 'tous les jours'],
    ['jour', 10, 'tous les 10 jours'],
  ] as const)('%s × %i → %o', (unite, intervalle, attendu) => {
    expect(frequenceEnToutesLettres(unite, intervalle)).toBe(attendu)
  })

  it('accorde l’article au genre de l’unité', () => {
    // « tous les semaines » se remarque immédiatement et fait amateur.
    expect(frequenceEnToutesLettres('semaine', 2)).toContain('toutes les')
    expect(frequenceEnToutesLettres('mois', 2)).toContain('tous les')
  })

  it('traite un intervalle absurde comme un intervalle simple', () => {
    expect(frequenceEnToutesLettres('mois', 0)).toBe('tous les mois')
    expect(frequenceEnToutesLettres('mois', -3)).toBe('tous les mois')
  })
})

describe('frequenceCourte', () => {
  it.each([
    ['mois', 1, '/mois'],
    ['mois', 3, '/3mois'],
    ['an', 1, '/an'],
    ['semaine', 2, '/2sem'],
  ] as const)('%s × %i → %o', (unite, intervalle, attendu) => {
    expect(frequenceCourte(unite, intervalle)).toBe(attendu)
  })
})
