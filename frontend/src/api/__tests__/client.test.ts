import { describe, expect, it } from 'vitest'

import { lireDetailErreur } from '../client'

describe('lireDetailErreur', () => {
  it('conserve les erreurs ordinaires sans inventer de motif', () => {
    expect(lireDetailErreur('Identifiants incorrects.')).toEqual({
      message: 'Identifiants incorrects.',
    })
  })

  it('rend le motif MFA exploitable par le parcours de connexion', () => {
    expect(
      lireDetailErreur({
        motif: 'second_facteur_requis',
        message: 'Entrez le code de votre application.',
      }),
    ).toEqual({
      motif: 'second_facteur_requis',
      message: 'Entrez le code de votre application.',
    })
  })

  it('ne rend jamais un objet brut à React', () => {
    expect(lireDetailErreur({ detail_inattendu: true }).message).toBe(
      'Le serveur a refusé la demande.',
    )
  })
})
