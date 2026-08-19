/**
 * Client HTTP de l'API.
 *
 * Les types viennent de `schema.ts`, GÉNÉRÉ depuis l'OpenAPI du serveur. Aucun type de
 * réponse n'est écrit à la main ici : le serveur fait foi, et une divergence doit casser
 * la compilation plutôt que de se découvrir à l'exécution.
 */
import type { components } from './schema'

export type UtilisateurPublic = components['schemas']['UtilisateurPublic']
export type InvitationCreee = components['schemas']['InvitationCreee']

/** Erreur portant le statut HTTP, pour distinguer « mauvais identifiants » du reste. */
export class ErreurApi extends Error {
  // Champ déclaré puis affecté, plutôt qu'un paramètre-propriété : ce dernier n'est pas
  // effaçable par le seul retrait des types, ce que la configuration TypeScript de Vite
  // (`erasableSyntaxOnly`) interdit.
  readonly statut: number

  constructor(statut: number, message: string) {
    super(message)
    this.statut = statut
    this.name = 'ErreurApi'
  }
}

/** L'API vit à la racine de la même origine que le front — pas de préfixe /api, donc
 *  pas de réécriture de chemin à maintenir des deux côtés. */
async function appeler<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  const reponse = await fetch(chemin, {
    ...options,
    // Indispensable : la session vit dans un cookie httpOnly, jamais en localStorage.
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })

  if (!reponse.ok) {
    const detail = await reponse
      .json()
      .then((corps: { detail?: string }) => corps.detail)
      .catch(() => undefined)
    throw new ErreurApi(reponse.status, detail ?? 'Le serveur a refusé la demande.')
  }

  if (reponse.status === 204) return undefined as T
  return (await reponse.json()) as T
}

export const api = {
  connexion: (courriel: string, motDePasse: string) =>
    appeler<UtilisateurPublic>('/auth/connexion', {
      method: 'POST',
      body: JSON.stringify({ courriel, mot_de_passe: motDePasse }),
    }),

  deconnexion: () => appeler<void>('/auth/deconnexion', { method: 'POST' }),

  moi: () => appeler<UtilisateurPublic>('/auth/moi'),

  creerInvitation: () => appeler<InvitationCreee>('/auth/invitations', { method: 'POST' }),
}
