import { afterEach, describe, expect, it, vi } from 'vitest'

import { changerEspace } from '../../design/espace'
import { api, lireDetailErreur } from '../client'

afterEach(() => {
  changerEspace(null)
  vi.unstubAllGlobals()
})

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

describe('périmètre HTTP', () => {
  it('pose X-Mycounts-Espace sur chaque requête après une bascule', async () => {
    const requete = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', requete)
    changerEspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1')

    await api.deconnexion()

    expect(requete).toHaveBeenCalledOnce()
    const options = requete.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(options.headers).get('X-Mycounts-Espace')).toBe(
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1',
    )
  })

  it('omet seulement l’espace pour relire les appartenances après une révocation', async () => {
    const requete = vi
      .fn()
      .mockResolvedValue(
        new Response('[]', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    vi.stubGlobal('fetch', requete)
    changerEspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1')

    await api.espaces()

    const options = requete.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(options.headers).has('X-Mycounts-Espace')).toBe(false)
  })

  it('crée une invitation ciblée dans le foyer actif, jamais un code legacy', async () => {
    const requete = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ jeton: 'jeton-cible', expire_le: '2026-08-31T00:00:00Z' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', requete)
    changerEspace('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2')

    await api.inviterDansEspace('membre@essai.fr', 'administrateur')

    expect(requete.mock.calls[0]?.[0]).toBe('/api/espaces/invitations')
    const options = requete.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(options.body))).toEqual({
      courriel: 'membre@essai.fr',
      role: 'administrateur',
    })
  })
})
