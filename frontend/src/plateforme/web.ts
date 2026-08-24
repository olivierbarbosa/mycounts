import type { EtatInstallation, EtatNotification, Plateforme } from './contrat'

type InvitationInstallation = Event & {
  prompt(): Promise<void>
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

type FenetrePwa = Window & {
  readonly MSStream?: unknown
}

type NavigateurPwa = Navigator & {
  readonly standalone?: boolean
}

function decoderClePublique(cle: string) {
  const completee = cle.padEnd(cle.length + ((4 - (cle.length % 4)) % 4), '=')
  const base64 = completee.replace(/-/g, '+').replace(/_/g, '/')
  return Uint8Array.from(atob(base64), (caractere) => caractere.charCodeAt(0))
}

function etatAffichage() {
  const visuel = window.visualViewport
  const hauteurClavier =
    visuel === null ? 0 : Math.max(0, Math.round(window.innerHeight - visuel.height - visuel.offsetTop))
  return { hauteurClavier, clavierOuvert: hauteurClavier > 120 }
}

function estPwaInstallee() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as NavigateurPwa).standalone === true
  )
}

function estIos() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false
  const appareilIos =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
  return appareilIos && !(window as FenetrePwa).MSStream
}

export function creerPlateformeWeb(): Plateforme {
  let invitation: InvitationInstallation | null = null
  const observateursInstallation = new Set<(etat: EtatInstallation) => void>()

  const etatInstallation = (): EtatInstallation => {
    if (estPwaInstallee()) return 'installee'
    if (invitation !== null) return 'installable'
    return estIos() ? 'instructions-ios' : 'navigateur'
  }

  const annoncerInstallation = () => {
    const etat = etatInstallation()
    observateursInstallation.forEach((observateur) => observateur(etat))
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('beforeinstallprompt', (evenement) => {
      evenement.preventDefault()
      invitation = evenement as InvitationInstallation
      annoncerInstallation()
    })
    window.addEventListener('appinstalled', () => {
      invitation = null
      annoncerInstallation()
    })
  }

  return {
    execution: estPwaInstallee() ? 'pwa' : 'web',
    estIos: estIos(),
    session: {
      transport: 'cookie-httponly',
      async lireJetonAcces() {
        // Le cookie de session est volontairement illisible depuis JavaScript.
        return null
      },
      async enregistrerJetonAcces() {
        throw new Error('Le web confie exclusivement la session au cookie httponly.')
      },
      async oublierJetonAcces() {
        // La révocation appartient à `/api/auth/deconnexion`, pas à un stockage client.
      },
    },
    reseau: {
      estEnLigne: () => (typeof navigator === 'undefined' ? true : navigator.onLine),
      ecouter(aLaModification) {
        if (typeof window === 'undefined') return () => undefined
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
      etat: etatInstallation,
      ecouter(aLaModification) {
        observateursInstallation.add(aLaModification)
        return () => observateursInstallation.delete(aLaModification)
      },
      async demander() {
        if (invitation === null) return 'indisponible'
        const courante = invitation
        await courante.prompt()
        const choix = await courante.userChoice
        invitation = null
        annoncerInstallation()
        return choix.outcome === 'accepted' ? 'acceptee' : 'refusee'
      },
    },
    notifications: {
      etat(): EtatNotification {
        return typeof window !== 'undefined' && 'Notification' in window
          ? Notification.permission
          : 'indisponible'
      },
      async demanderAutorisation(): Promise<EtatNotification> {
        if (typeof window === 'undefined' || !('Notification' in window)) return 'indisponible'
        return Notification.requestPermission()
      },
      async abonner(clePublique) {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
          throw new Error('Les notifications push ne sont pas disponibles sur cet appareil.')
        }
        const enregistrement = await navigator.serviceWorker.ready
        const existant = await enregistrement.pushManager.getSubscription()
        const abonnement =
          existant ??
          (await enregistrement.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: decoderClePublique(clePublique),
          }))
        return abonnement.toJSON()
      },
      async desabonner() {
        if (!('serviceWorker' in navigator)) return false
        const enregistrement = await navigator.serviceWorker.ready
        const abonnement = await enregistrement.pushManager.getSubscription()
        return abonnement === null ? false : abonnement.unsubscribe()
      },
    },
    fichiers: {
      choisir({ accepte, multiple = false }) {
        return new Promise((resoudre) => {
          const saisie = document.createElement('input')
          saisie.type = 'file'
          saisie.accept = accepte
          saisie.multiple = multiple
          saisie.addEventListener(
            'change',
            () => resoudre(saisie.files === null ? [] : Array.from(saisie.files)),
            { once: true },
          )
          saisie.click()
        })
      },
    },
    liens: {
      ouvrir(url) {
        window.location.assign(url)
      },
      ecouter(aLaModification) {
        const annoncer = () => aLaModification(window.location.href)
        window.addEventListener('popstate', annoncer)
        window.addEventListener('hashchange', annoncer)
        return () => {
          window.removeEventListener('popstate', annoncer)
          window.removeEventListener('hashchange', annoncer)
        }
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
      etat: etatAffichage,
      ecouter(aLaModification) {
        const visuel = window.visualViewport
        if (visuel === null) return () => undefined
        const annoncer = () => aLaModification(etatAffichage())
        visuel.addEventListener('resize', annoncer)
        visuel.addEventListener('scroll', annoncer)
        return () => {
          visuel.removeEventListener('resize', annoncer)
          visuel.removeEventListener('scroll', annoncer)
        }
      },
    },
    biometrie: {
      disponible: async () => false,
      deverrouiller: async () => {
        throw new Error('La biométrie appartient à l’application native.')
      },
    },
  }
}
