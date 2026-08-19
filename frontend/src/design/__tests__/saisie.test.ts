import { describe, expect, it } from 'vitest'

import { SaisieInvalide, enCentimes } from '../saisie'

describe('enCentimes', () => {
  it.each([
    ['0', 0],
    ['12', 1200],
    ['12,5', 1250],
    ['12,50', 1250],
    ['12.50', 1250],
    ['1 234,56', 123456],
    ['12,50 €', 1250],
    ['-45,90', -4590],
    ['0,01', 1],
  ])('%s → %i centimes', (saisie, attendu) => {
    expect(enCentimes(saisie as string)).toBe(attendu)
  })

  it.each(['', '   ', 'abc', '12,505', '12,,5', '1e3', '--5', '12-5'])('refuse %o', (saisie) => {
    expect(() => enCentimes(saisie)).toThrow(SaisieInvalide)
  })

  it('refuse plus de deux décimales plutôt que d’arrondir en silence', () => {
    // Un arrondi que l'utilisateur n'a pas demandé est un écart qu'il ne pourra pas
    // expliquer. Même choix que côté serveur.
    expect(() => enCentimes('12,505')).toThrow(SaisieInvalide)
  })

  it('accorde le même résultat que le serveur sur les cas de référence', () => {
    // Valeurs reprises de tests/unit/test_montants.py : les deux implémentations doivent
    // coïncider, sinon l'écran afficherait autre chose que ce qui est enregistré.
    expect(enCentimes('0,10') + enCentimes('0,20')).toBe(enCentimes('0,30'))
    expect(enCentimes('-1 234.5 €')).toBe(-123450)
  })

  it('accepte l’espace insécable des milliers, tel que collé depuis un relevé', () => {
    expect(enCentimes('1 234,56')).toBe(123456)
    expect(enCentimes('1 234,56')).toBe(123456)
  })
})
