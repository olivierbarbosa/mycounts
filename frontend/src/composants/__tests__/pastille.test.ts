import { describe, expect, it } from 'vitest'

import { initiales, teintePour } from '../PastilleMarque'

describe('initiales', () => {
  it.each([
    ['Netflix', 'N'],
    ['Canal+', 'C'],
    ['Basic Fit', 'BF'],
    ['Assurance habitation', 'AH'],
    ['EDF', 'E'],
    ['  spotify  ', 'S'],
    ['', '?'],
    ['   ', '?'],
    ['+++', '?'],
  ])('%o → %o', (nom, attendu) => {
    expect(initiales(nom)).toBe(attendu)
  })
})

describe('teintePour', () => {
  it('donne toujours la même teinte pour le même nom', () => {
    // C'est TOUT l'intérêt : une couleur aléatoire changerait à chaque rendu et
    // détruirait la reconnaissance visuelle.
    expect(teintePour('Netflix')).toBe(teintePour('Netflix'))
    expect(teintePour('Netflix')).toBe(teintePour('netflix'))
    expect(teintePour('Netflix')).toBe(teintePour('  Netflix '))
  })

  it('témoin : des noms différents ne reçoivent pas tous la même teinte', () => {
    // Sans ce volet, une fonction qui renverrait une constante passerait le test
    // précédent sans difficulté.
    const noms = ['Netflix', 'Spotify', 'EDF', 'Free', 'Canal+', 'Loyer', 'Assurance']
    const teintes = new Set(noms.map(teintePour))
    expect(teintes.size).toBeGreaterThan(1)
  })

  it('ne renvoie que des variables de la palette, jamais une couleur fabriquée', () => {
    // Le garde-fou n°9 interdit les couleurs en dur ; une teinte calculée en HSL
    // contournerait cette règle par la porte du JavaScript.
    for (const nom of ['Netflix', 'Free', 'EDF', 'Zzz', '']) {
      expect(teintePour(nom)).toMatch(/^var\(--couleur-[a-z-]+\)$/)
    }
  })
})
