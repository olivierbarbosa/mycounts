/// <reference lib="webworker" />

import { cleanupOutdatedCaches, matchPrecache, precacheAndRoute } from 'workbox-precaching'
import { registerRoute } from 'workbox-routing'
import { NetworkOnly } from 'workbox-strategies'

import { estApiOuDonneeSensible } from '../src/plateforme/politiqueCache'
import { cheminNotification, contenuNotification } from '../src/plateforme/notifications'

declare const self: ServiceWorkerGlobalScope & {
  readonly __WB_MANIFEST: Array<{ url: string; revision?: string | null }>
}

// Seuls le shell et les fichiers compilés passent dans le précache injecté au build.
// Aucun JSON métier ne figure dans ce manifeste généré depuis `dist`.
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// Cette route vient avant le repli de navigation. `NetworkOnly` et `cache: no-store`
// empêchent le service worker ET le cache HTTP du navigateur de conserver une réponse
// financière. Les fichiers importés et le coach empruntent tous `/api`.
registerRoute(
  ({ url }) => url.origin === self.location.origin && estApiOuDonneeSensible(url),
  new NetworkOnly({ fetchOptions: { cache: 'no-store', credentials: 'include' } }),
)

// Hors ligne, seule la coquille HTML est rendue. React affiche ensuite un état réseau
// dédié sans inventer une session ni ressortir des montants d'un stockage persistant.
registerRoute(
  ({ request, url }) =>
    request.mode === 'navigate' &&
    url.origin === self.location.origin &&
    !estApiOuDonneeSensible(url),
  async ({ event }) => {
    try {
      return await fetch(event.request, { cache: 'no-store' })
    } catch {
      return (await matchPrecache('/index.html')) ?? Response.error()
    }
  },
)

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') void self.skipWaiting()
})

self.addEventListener('push', (event) => {
  let chargeUtile: { type?: unknown; destination?: unknown } = {}
  try {
    chargeUtile = event.data?.json() ?? {}
  } catch {
    // Un payload illisible devient une notification générique ; son contenu brut n'est
    // jamais affiché et ne peut donc pas faire fuiter un libellé bancaire.
  }
  const contenu = contenuNotification(chargeUtile.type)
  const destination = cheminNotification(chargeUtile.destination, self.location.origin)

  event.waitUntil(
    self.registration.showNotification('MyCounts', {
      body: contenu.corps,
      tag: `mycounts-${contenu.etiquette}`,
      icon: '/pwa/icon-192.png',
      badge: '/pwa/icon-192.png',
      data: { destination },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const destination = cheminNotification(
    (event.notification.data as { destination?: unknown } | undefined)?.destination,
    self.location.origin,
  )

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (clients) => {
      const existant = clients.find((client) => new URL(client.url).origin === self.location.origin)
      if (existant !== undefined) {
        await existant.navigate(destination)
        return existant.focus()
      }
      return self.clients.openWindow(destination)
    }),
  )
})
