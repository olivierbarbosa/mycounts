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
export type ComptePublic = components['schemas']['ComptePublic']
export type CategoriePublique = components['schemas']['CategoriePublique']
export type OperationPublique = components['schemas']['OperationPublique']
export type ResumePublic = components['schemas']['ResumePublic']
export type NatureCategorie = components['schemas']['NatureCategorie']
export type TeinteCategorie = components['schemas']['TeinteCategorie']

export type SaisieOperation = {
  compte_id: string
  libelle: string
  montant_centimes: number
  date_operation: string
  categorie_id?: string | null
  est_paie?: boolean
}

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

/** Toute l'API vit sous /api, sur la même origine que le front. Un seul préfixe : le
 *  proxy de développement n'a qu'une entrée à connaître, et aucune liste de chemins ne
 *  peut diverger (ERREURS.md #015). */
const BASE = '/api'

async function appeler<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  const reponse = await fetch(`${BASE}${chemin}`, {
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

  comptes: () => appeler<ComptePublic[]>('/comptes'),

  creerCompte: (nom: string, soldeOuvertureCentimes: number) =>
    appeler<ComptePublic>('/comptes', {
      method: 'POST',
      body: JSON.stringify({
        nom,
        prive: true,
        solde_ouverture_centimes: soldeOuvertureCentimes,
      }),
    }),

  categories: () => appeler<CategoriePublique[]>('/categories'),

  creerCategorie: (nom: string, nature: NatureCategorie, teinte: TeinteCategorie) =>
    appeler<CategoriePublique>('/categories', {
      method: 'POST',
      body: JSON.stringify({ nom, nature, teinte }),
    }),

  operations: () => appeler<OperationPublique[]>('/operations'),

  creerOperation: (saisie: SaisieOperation) =>
    appeler<OperationPublique>('/operations', {
      method: 'POST',
      body: JSON.stringify(saisie),
    }),

  resume: () => appeler<ResumePublic>('/resume'),
}
