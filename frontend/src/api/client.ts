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
export type RecurrencePublique = components['schemas']['RecurrencePublique']
export type EcheanceAgenda = components['schemas']['EcheanceAgenda']
export type BornesDuMois = components['schemas']['BornesDuMois']
export type DemandeVirement = components['schemas']['DemandeVirement']
export type VirementCree = components['schemas']['VirementCree']
export type EpargnePublique = components['schemas']['EpargnePublique']
export type CompteEpargne = components['schemas']['CompteEpargne']
export type DetailEpargne = components['schemas']['DetailEpargne']
export type MoisDEpargne = components['schemas']['MoisDEpargnePublic']
export type RepartitionEnveloppes = components['schemas']['RepartitionPublique']
export type EnveloppePublique = components['schemas']['EnveloppePublique']
export type DemandeEnveloppe = components['schemas']['DemandeEnveloppe']
export type ModificationEnveloppe = components['schemas']['ModificationEnveloppe']
export type PreparationPublique = components['schemas']['PreparationPublique']
export type StatistiquesPubliques = components['schemas']['StatistiquesPubliques']
export type PosteDeDepense = components['schemas']['PostePublic']
export type Constat = components['schemas']['ConstatPublic']
export type LignePreparation = components['schemas']['LignePreparationPublique']
export type ChoixDeLigne = components['schemas']['ChoixDeLigne']
export type Rollover = components['schemas']['Rollover']
export type UsageEnveloppe = components['schemas']['UsageEnveloppe']
export type DemandeMouvementEnveloppe = components['schemas']['DemandeMouvement']
export type MouvementEnveloppe = components['schemas']['MouvementPublic']
export type DemandeCompte = components['schemas']['DemandeCompte']
export type ModificationCompte = components['schemas']['ModificationCompte']
export type ProduitPublic = components['schemas']['ProduitPublic']
export type SoldeDeCompte = components['schemas']['SoldeDeCompte']
export type DemandeAjustement = components['schemas']['DemandeAjustement']
export type AjustementFait = components['schemas']['AjustementFait']
export type UniteRecurrence = components['schemas']['UniteRecurrence']
export type PlafondPublic = components['schemas']['PlafondPublic']

export type SaisieRecurrence = {
  compte_id: string
  libelle: string
  montant_centimes: number
  ancre: string
  unite: UniteRecurrence
  intervalle?: number
  categorie_id?: string | null
  fin?: string | null
}
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

  /** Le corps entier est passé : la signature positionnelle précédente obligeait à
   *  ajouter un paramètre à chaque champ nouveau, et un appelant sur deux l'oubliait. */
  creerCompte: (demande: DemandeCompte) =>
    appeler<ComptePublic>('/comptes', { method: 'POST', body: JSON.stringify(demande) }),

  /** Produits bancaires proposés. Servis par le serveur : c'est le catalogue du domaine
   *  qui décide qu'un PEA ne compte pas dans le solde du quotidien, pas l'écran. */
  catalogueDesComptes: () => appeler<ProduitPublic[]>('/comptes/catalogue'),

  soldesDesComptes: () => appeler<SoldeDeCompte[]>('/comptes/soldes'),

  modifierCompte: (id: string, demande: ModificationCompte) =>
    appeler<ComptePublic>(`/comptes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(demande),
    }),

  supprimerCompte: (id: string) => appeler<void>(`/comptes/${id}`, { method: 'DELETE' }),

  /** Met le solde d'accord avec celui de la banque. On envoie le solde CONSTATÉ : le
   *  serveur calcule l'écart, lui seul connaissant le solde à l'instant où il écrit. */
  ajusterLeSolde: (compteId: string, demande: DemandeAjustement) =>
    appeler<AjustementFait>(`/comptes/${compteId}/ajustement`, {
      method: 'POST',
      body: JSON.stringify(demande),
    }),

  categories: () => appeler<CategoriePublique[]>('/categories'),

  creerCategorie: (nom: string, nature: NatureCategorie, teinte: TeinteCategorie) =>
    appeler<CategoriePublique>('/categories', {
      method: 'POST',
      body: JSON.stringify({ nom, nature, teinte }),
    }),

  modifierCategorie: (
    id: string,
    modifications: {
      nom?: string
      teinte?: TeinteCategorie
      archivee?: boolean
    },
  ) =>
    appeler<CategoriePublique>(`/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(modifications),
    }),

  supprimerCategorie: (id: string) => appeler<void>(`/categories/${id}`, { method: 'DELETE' }),

  operations: () => appeler<OperationPublique[]>('/operations'),

  creerOperation: (saisie: SaisieOperation) =>
    appeler<OperationPublique>('/operations', {
      method: 'POST',
      body: JSON.stringify(saisie),
    }),

  modifierOperation: (
    id: string,
    modifications: {
      libelle?: string
      montant_centimes?: number
      date_operation?: string
      categorie_id?: string | null
    },
  ) =>
    appeler<OperationPublique>(`/operations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(modifications),
    }),

  supprimerOperation: (id: string) => appeler<void>(`/operations/${id}`, { method: 'DELETE' }),

  resume: () => appeler<ResumePublic>('/resume'),

  /** Ce que le foyer a mis de côté. Distinct du résumé : les deux totaux répondent à des
   *  questions différentes, et les additionner ferait croire à une aisance qui n'existe pas. */
  epargne: () => appeler<EpargnePublique>('/epargne'),

  /** Rythme d'un livret : versé, repris et solde, mois par mois. */
  detailEpargne: (compteId: string) => appeler<DetailEpargne>(`/epargne/${compteId}`),

  /** Les enveloppes ET le non-affecté. Le second est rendu par le serveur et non déduit
   *  ici : le laisser calculer côté écran ouvrirait deux définitions de « disponible ». */
  enveloppes: () => appeler<RepartitionEnveloppes>('/enveloppes'),

  creerEnveloppe: (demande: DemandeEnveloppe) =>
    appeler<RepartitionEnveloppes>('/enveloppes', {
      method: 'POST',
      body: JSON.stringify(demande),
    }),

  /** Réglages d'une enveloppe. Les champs absents restent inchangés — conséquence
   *  assumée côté serveur : on ne peut pas RETIRER une cible ici, seulement la changer. */
  modifierEnveloppe: (id: string, demande: ModificationEnveloppe) =>
    appeler<RepartitionEnveloppes>(`/enveloppes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(demande),
    }),

  /** Ce que la période qui s'ouvre PROPOSE. N'écrit rien : c'est `appliquerPreparation`
   *  qui écrit, et seulement les lignes qu'on lui donne. */
  preparation: () => appeler<PreparationPublique>('/enveloppes/preparation'),

  /** Où va l'argent, et ce que l'addition mentale rate. Le serveur est seul auteur des
   *  seuils qui décident qu'un constat mérite d'être affiché. */
  statistiques: () => appeler<StatistiquesPubliques>('/statistiques'),

  appliquerPreparation: (lignes: readonly ChoixDeLigne[]) =>
    appeler<RepartitionEnveloppes>('/enveloppes/preparation', {
      method: 'POST',
      body: JSON.stringify({ lignes }),
    }),

  supprimerEnveloppe: (id: string) => appeler<void>(`/enveloppes/${id}`, { method: 'DELETE' }),

  /** Ajoute une ligne au journal. N'écrit AUCUNE opération bancaire. */
  mouvementEnveloppe: (id: string, demande: DemandeMouvementEnveloppe) =>
    appeler<RepartitionEnveloppes>(`/enveloppes/${id}/mouvements`, {
      method: 'POST',
      body: JSON.stringify(demande),
    }),

  journalEnveloppe: (id: string) => appeler<MouvementEnveloppe[]>(`/enveloppes/${id}/journal`),

  creerVirement: (demande: DemandeVirement) =>
    appeler<VirementCree>('/virements', { method: 'POST', body: JSON.stringify(demande) }),

  agenda: (jours = 60) => appeler<EcheanceAgenda[]>(`/agenda?jours=${jours}`),

  /** Bornes du mois CIVIL courant. Calculées par le serveur : « aujourd'hui » se lit dans
   *  le fuseau Europe/Paris, dont le domaine est l'auteur unique. */
  moisEnCours: () => appeler<BornesDuMois>('/agenda/mois-en-cours'),

  recurrences: () => appeler<RecurrencePublique[]>('/recurrences'),

  creerRecurrence: (saisie: SaisieRecurrence) =>
    appeler<RecurrencePublique>('/recurrences', {
      method: 'POST',
      body: JSON.stringify(saisie),
    }),

  modifierRecurrence: (id: string, modifications: Partial<SaisieRecurrence>) =>
    appeler<RecurrencePublique>(`/recurrences/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(modifications),
    }),

  arreterRecurrence: (id: string) => appeler<void>(`/recurrences/${id}`, { method: 'DELETE' }),

  aConfirmer: () => appeler<OperationPublique[]>('/operations/a-confirmer'),

  confirmer: (id: string) =>
    appeler<OperationPublique>(`/operations/${id}/confirmer`, {
      method: 'POST',
    }),

  plafonds: () => appeler<PlafondPublic[]>('/plafonds'),

  definirPlafond: (categorieId: string, montantCentimes: number) =>
    appeler<PlafondPublic[]>('/plafonds', {
      method: 'PUT',
      body: JSON.stringify({
        categorie_id: categorieId,
        montant_centimes: montantCentimes,
      }),
    }),

  supprimerPlafond: (id: string) => appeler<void>(`/plafonds/${id}`, { method: 'DELETE' }),
}
