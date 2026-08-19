import { describe, expect, it } from 'vitest'

import { contientEspaceInsecable, decouper } from '../Montant'

/**
 * Miroir exact de `test_montants.py` côté serveur : ces tests ont été calibrés contre
 * l'implémentation fautive, pas supposés. Le piège est le même — une division par 100
 * en flottant semble juste sur les cas qu'on essaie spontanément.
 */

describe('decouper', () => {
  it.each([
    [0, '+', '0', '00'],
    [1, '+', '0', '01'],
    [10, '+', '0', '10'],
    [1250, '+', '12', '50'],
    [-4590, '−', '45', '90'],
    [-1, '−', '0', '01'],
    [100000, '+', '1 000', '00'],
    [123456789, '+', '1 234 567', '89'],
  ])('%i centimes', (centimes, signe, euros, decimales) => {
    expect(decouper(centimes)).toEqual({ signe, euros, centimes: decimales })
  })

  it('balayage exhaustif de 0,00 à 199,99', () => {
    // Ce test ne rejette PAS une implémentation par `toFixed(2)` : mesuré, les deux
    // coïncident sur tout le domaine représentable en JavaScript. Il vérifie
    // l'exactitude, pas le choix d'implémentation — voir ERREURS.md #014.
    for (let euros = 0; euros < 200; euros++) {
      for (let centimes = 0; centimes < 100; centimes++) {
        const total = euros * 100 + centimes
        const decoupe = decouper(total)
        expect(Number(decoupe.euros.replace(/ /g, ''))).toBe(euros)
        expect(decoupe.centimes).toBe(String(centimes).padStart(2, '0'))
      }
    }
  })

  it('reste exact jusqu’à la limite des entiers sûrs de JavaScript', () => {
    // MAX_SAFE_INTEGER = 9 007 199 254 740 991 centimes, soit 90 071 992 547 409,91 €.
    // Au-delà, ce n'est pas le formatage qui se trompe : c'est le `number` lui-même qui
    // ne représente plus l'entier reçu du serveur, où la colonne est un BIGINT.
    const limite = Number.MAX_SAFE_INTEGER
    const decoupe = decouper(limite)
    expect(decoupe.centimes).toBe('91')
    expect(Number(decoupe.euros.replace(/[\u202f\u00a0]/g, ''))).toBe(Math.trunc(limite / 100))
  })

  it('documente la limite réelle du client : au-delà, le nombre est déjà faux', () => {
    // Constat mesuré, pas une protection : ce test existe pour que la limite soit écrite
    // quelque part. Un montant de cette taille est irréaliste pour un budget de foyer,
    // mais la frontière BIGINT / number est réelle et doit être connue.
    const trop_grand = Number.MAX_SAFE_INTEGER + 2
    expect(Number.isSafeInteger(trop_grand)).toBe(false)
  })

  it('le signe est un caractère « moins » typographique, pas un tiret ASCII', () => {
    // Le tiret ASCII se confond avec un trait d'union dans une liste d'opérations.
    expect(decouper(-100).signe).toBe('−')
    expect(decouper(-100).signe).not.toBe('-')
  })

  it('les milliers sont séparés par une espace insécable, jamais ordinaire', () => {
    // Une espace ordinaire permettrait un retour à la ligne au milieu d'un montant.
    // Intl utilise U+202F (fine) et non U+00A0 : constat mesuré, le test accepte les deux.
    const euros = decouper(100000).euros
    expect(contientEspaceInsecable(euros)).toBe(true)
    expect(euros).not.toContain('\u0020')
  })
})
