import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, lireDetailErreur } from '../client'

afterEach(() => vi.unstubAllGlobals())

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

describe('transport web', () => {
  it('envoie le cookie httpOnly sans inventer de jeton côté JavaScript', async () => {
    const requete = vi.fn(async (_entree: RequestInfo | URL, _options?: RequestInit) =>
      new Response(
        JSON.stringify({
          id: 'utilisateur',
          courriel: 'personne@example.test',
          nom_affichage: 'Personne',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    vi.stubGlobal('fetch', requete)

    await api.moi()

    expect(requete).toHaveBeenCalledOnce()
    const options = requete.mock.calls[0][1]
    expect(options?.credentials).toBe('include')
    expect(new Headers(options?.headers).has('Authorization')).toBe(false)
  })
})
