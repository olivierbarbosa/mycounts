import { expect, test, type Page } from '@playwright/test'

/**
 * Fiabilité de la PWA — ce qui distingue une application installée d'un onglet.
 *
 * Trois mesures, toutes contre l'application RÉELLE servie par Vite :
 *
 *  1. **aucune erreur de console** sur les écrans principaux, à quatre largeurs de
 *     téléphone et une de tablette. Une erreur de console en PWA n'a aucun lecteur : pas
 *     d'outils de développement sur un téléphone, et personne ne la signale ;
 *  2. **une coupure réseau ne vide pas la saisie en cours.** iOS émet `offline` en passant
 *     du Wi-Fi au cellulaire ; remplacer tout l'écran à cet instant jetait le montant
 *     tapé. L'écran reste, un bandeau dit l'état, et la saisie se termine au retour ;
 *  3. **le bandeau se pose AU-DESSUS de la barre d'onglets**, jamais dessus : un message
 *     qui recouvre la navigation supprime la seule sortie de l'écran.
 *
 * Ce que ce fichier ne mesure PAS : la coquille hors ligne servie par le service worker.
 * Vite ne l'enregistre pas en développement ; elle se vérifie sur le `dist` construit,
 * que `scripts/verifier-pwa.mjs` contrôle à chaque build.
 */

const LARGEURS = [
  { nom: 'iPhone SE', width: 375, height: 667 },
  { nom: 'iPhone 14', width: 390, height: 844 },
  { nom: 'iPhone 15 Pro Max', width: 430, height: 932 },
  { nom: 'tablette', width: 820, height: 1180 },
] as const

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
}

/** Erreurs de console et exceptions non rattrapées, collectées dès AVANT la navigation :
 *  brancher l'écoute après `goto` raterait celles du premier rendu. */
function ecouterLesErreurs(page: Page) {
  const erreurs: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') erreurs.push(message.text())
  })
  page.on('pageerror', (erreur) => erreurs.push(erreur.message))
  return erreurs
}

for (const vue of LARGEURS) {
  test(`${vue.nom} (${vue.width} px) : aucune erreur de console sur les écrans principaux`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: vue.width, height: vue.height })
    const erreurs = ecouterLesErreurs(page)
    await connecter(page)
    await expect(page.getByText('Solde projeté')).toBeVisible()

    for (const onglet of ['Budget', 'Enveloppe', 'Épargne', 'Accueil']) {
      await page.getByRole('navigation', { name: 'Navigation principale' }).getByRole('button', { name: onglet }).click()
    }
    await page.getByRole('button', { name: 'Calendrier' }).click()
    const calendrier = page.getByRole('dialog', { name: 'Calendrier' })
    await expect(calendrier.getByRole('button', { name: 'Fermer' })).toBeVisible()
    await calendrier.getByRole('button', { name: 'Fermer' }).click()
    await page.getByRole('button', { name: /^Paramètres de / }).click()
    await page.getByRole('button', { name: 'Application' }).click()
    await expect(page.getByRole('heading', { name: 'Sur l’écran d’accueil' })).toBeVisible()

    expect(erreurs, 'erreurs de console').toEqual([])
  })
}

test.describe('coupure réseau en cours de session', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('la saisie en cours survit à une coupure, et le bandeau ne couvre pas la navigation', async ({
    page,
    context,
  }) => {
    await connecter(page)
    await page.getByRole('button', { name: 'Saisir une opération' }).click()
    await page.getByLabel('Montant').fill('45,90')

    await context.setOffline(true)
    const bandeau = page.getByRole('status', { name: 'État du réseau' })
    await expect(bandeau).toBeVisible()
    await expect(bandeau).toContainText('hors ligne')
    // Le montant tapé est toujours là : l'écran n'a pas été remplacé.
    await expect(page.getByLabel('Montant')).toHaveValue('45,90')

    await context.setOffline(false)
    await expect(bandeau).toHaveCount(0)
    await expect(page.getByLabel('Montant')).toHaveValue('45,90')
  })

  for (const vue of LARGEURS) {
    test(`${vue.nom} : le bandeau se pose au-dessus de la barre d’onglets`, async ({
      page,
      context,
    }) => {
      await page.setViewportSize({ width: vue.width, height: vue.height })
      await connecter(page)
      await context.setOffline(true)
      const bandeau = page.getByRole('status', { name: 'État du réseau' })
      await expect(bandeau).toBeVisible()

      const boiteBandeau = (await bandeau.boundingBox())!
      const boiteNav = (await page
        .getByRole('navigation', { name: 'Navigation principale' })
        .boundingBox())!
      expect(
        boiteBandeau.y + boiteBandeau.height,
        `le bandeau recouvre la navigation de ${Math.round(boiteBandeau.y + boiteBandeau.height - boiteNav.y)} px`,
      ).toBeLessThanOrEqual(boiteNav.y)
      expect(boiteBandeau.x, 'le bandeau déborde à gauche').toBeGreaterThanOrEqual(0)
      expect(boiteBandeau.x + boiteBandeau.width, 'le bandeau déborde à droite').toBeLessThanOrEqual(
        vue.width,
      )
      await context.setOffline(false)
    })
  }

  test('sans données chargées, la coupure affiche l’écran hors ligne entier', async ({
    page,
  }) => {
    // Rien n'est encore à l'écran : il n'y a rien à préserver, et l'écran dédié évite
    // de montrer une connexion qui ferait retaper un mot de passe pour rien. Le navigateur
    // est déclaré hors ligne AVANT le premier rendu, pas coupé après.
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => false })
    })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Vous êtes hors ligne' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Réessayer' })).toBeVisible()
    await expect(page.getByRole('status', { name: 'État du réseau' })).toHaveCount(0)
  })
})
