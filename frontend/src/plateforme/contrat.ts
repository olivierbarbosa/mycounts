export type Execution = 'web' | 'pwa' | 'native'
export type EtatInstallation = 'installee' | 'installable' | 'instructions-ios' | 'navigateur'
export type EtatNotification = NotificationPermission | 'indisponible'
export type CycleDeVie = 'active' | 'arriere-plan'
export type EtatAffichage = {
  readonly hauteurClavier: number
  readonly clavierOuvert: boolean
}

export interface CoffreNatif {
  lire(cle: string): Promise<string | null>
  ecrire(cle: string, valeur: string): Promise<void>
  supprimer(cle: string): Promise<void>
}

export interface Plateforme {
  readonly execution: Execution
  readonly estIos: boolean
  readonly session: {
    /** Le web ne lit jamais le cookie : il est `httponly`. Le natif utilisera un jeton
     * court dans le trousseau, une fois le transport serveur livré. */
    readonly transport: 'cookie-httponly' | 'jeton-court-trousseau'
    lireJetonAcces(): Promise<string | null>
    enregistrerJetonAcces(jeton: string): Promise<void>
    oublierJetonAcces(): Promise<void>
  }
  readonly reseau: {
    estEnLigne(): boolean
    ecouter(aLaModification: (enLigne: boolean) => void): () => void
  }
  readonly installation: {
    etat(): EtatInstallation
    ecouter(aLaModification: (etat: EtatInstallation) => void): () => void
    demander(): Promise<'acceptee' | 'refusee' | 'indisponible'>
  }
  readonly notifications: {
    etat(): EtatNotification
    demanderAutorisation(): Promise<EtatNotification>
    abonner(clePublique: string): Promise<PushSubscriptionJSON>
    desabonner(): Promise<boolean>
  }
  readonly fichiers: {
    choisir(options: { accepte: string; multiple?: boolean }): Promise<readonly File[]>
  }
  readonly liens: {
    ouvrir(url: string): void
    ecouter(aLaModification: (url: string) => void): () => void
  }
  readonly cycleDeVie: {
    ecouter(aLaModification: (etat: CycleDeVie) => void): () => void
  }
  readonly affichage: {
    etat(): EtatAffichage
    ecouter(aLaModification: (etat: EtatAffichage) => void): () => void
  }
  readonly biometrie: {
    disponible(): Promise<boolean>
    deverrouiller(raison: string): Promise<boolean>
  }
}
