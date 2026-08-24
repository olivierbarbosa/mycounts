import type { CoffreNatif, Plateforme } from './contrat'

/** Prépare le contrat du conteneur sans simuler une sécurité inexistante. Tant qu'un
 * plugin de trousseau iOS/Keystore Android n'est pas injecté, toute lecture de jeton
 * échoue explicitement : aucun repli vers `localStorage` n'est autorisé. */
export function creerPlateformeNative(coffre?: CoffreNatif): Plateforme {
  const coffreObligatoire = () => {
    if (coffre === undefined) {
      throw new Error('Le trousseau natif doit être branché avant d’activer la session native.')
    }
    return coffre
  }

  return {
    execution: 'native',
    estIos: typeof navigator !== 'undefined' && /iPad|iPhone|iPod/.test(navigator.userAgent),
    session: {
      transport: 'jeton-court-trousseau',
      async lireJetonAcces() {
        return coffreObligatoire().lire('session.acces')
      },
      async enregistrerJetonAcces(jeton) {
        await coffreObligatoire().ecrire('session.acces', jeton)
      },
      async oublierJetonAcces() {
        await coffreObligatoire().supprimer('session.acces')
      },
    },
    // Ces capacités restent fonctionnelles dans la WebView ; les plugins natifs pourront
    // remplacer l'adaptateur sans toucher aux écrans.
    reseau: {
      estEnLigne: () => navigator.onLine,
      ecouter(aLaModification) {
        const enLigne = () => aLaModification(true)
        const horsLigne = () => aLaModification(false)
        window.addEventListener('online', enLigne)
        window.addEventListener('offline', horsLigne)
        return () => {
          window.removeEventListener('online', enLigne)
          window.removeEventListener('offline', horsLigne)
        }
      },
    },
    installation: {
      etat: () => 'installee',
      ecouter: () => () => undefined,
      demander: async () => 'indisponible',
    },
    notifications: {
      etat: () => 'indisponible',
      demanderAutorisation: async () => 'indisponible',
      abonner: async () => {
        throw new Error('Les notifications natives ne sont pas encore branchées.')
      },
      desabonner: async () => false,
    },
    fichiers: {
      choisir: async () => {
        throw new Error('Le sélecteur de fichiers natif n’est pas encore branché.')
      },
    },
    liens: {
      ouvrir: (url) => window.location.assign(url),
      ecouter(aLaModification) {
        const annoncer = () => aLaModification(window.location.href)
        window.addEventListener('popstate', annoncer)
        return () => window.removeEventListener('popstate', annoncer)
      },
    },
    cycleDeVie: {
      ecouter(aLaModification) {
        const annoncer = () =>
          aLaModification(document.visibilityState === 'visible' ? 'active' : 'arriere-plan')
        document.addEventListener('visibilitychange', annoncer)
        return () => document.removeEventListener('visibilitychange', annoncer)
      },
    },
    affichage: {
      etat() {
        const visuel = window.visualViewport
        const hauteurClavier =
          visuel === null
            ? 0
            : Math.max(0, Math.round(window.innerHeight - visuel.height - visuel.offsetTop))
        return { hauteurClavier, clavierOuvert: hauteurClavier > 120 }
      },
      ecouter(aLaModification) {
        const visuel = window.visualViewport
        if (visuel === null) return () => undefined
        const annoncer = () => aLaModification(this.etat())
        visuel.addEventListener('resize', annoncer)
        return () => visuel.removeEventListener('resize', annoncer)
      },
    },
    biometrie: {
      disponible: async () => false,
      deverrouiller: async () => {
        throw new Error('Le plugin biométrique natif n’est pas encore branché.')
      },
    },
  }
}
