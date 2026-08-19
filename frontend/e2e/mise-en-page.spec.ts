import { expect, test } from '@playwright/test'

import { VIEWPORTS } from '../playwright.config'

const CIBLE_MINIMALE = 44

/**
 * Garde-fou n°10 — mise en page sur téléphone, tablette et bureau.
 *
 * Ces tests tournent contre l'application RÉELLE servie par Vite, pas contre un rendu de
 * composant isolé : c'est la seule façon de voir un débordement, qui naît toujours de la
 * combinaison des règles, jamais d'un composant seul.
 */
for (const vue of VIEWPORTS) {
  test.describe(`${vue.nom} (${vue.width}×${vue.height})`, () => {
    test.use({ viewport: { width: vue.width, height: vue.height } })

    test('la page de connexion ne déborde pas horizontalement', async ({ page }) => {
      await page.goto('/')
      await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()

      const debordement = await page.evaluate(
        () => document.body.scrollWidth > document.body.clientWidth,
      )
      expect(debordement, 'le corps de la page défile horizontalement').toBe(false)
    })

    test('toutes les cibles tactiles atteignent 44 px', async ({ page }) => {
      await page.goto('/')
      const trop_petites = await page.evaluate((minimum) => {
        return [...document.querySelectorAll('button, a[role="button"]')]
          .map((element) => {
            const boite = element.getBoundingClientRect()
            return { texte: element.textContent?.trim() ?? '', h: boite.height, l: boite.width }
          })
          .filter((c) => c.h > 0 && (c.h < minimum || c.l < minimum))
      }, CIBLE_MINIMALE)
      expect(trop_petites, 'cibles sous 44 px').toEqual([])
    })

    test('les champs de saisie font au moins 16 px', async ({ page }) => {
      // En dessous de 16 px, iOS Safari zoome automatiquement à la mise au point du
      // champ et l'utilisateur se retrouve avec une page décalée.
      await page.goto('/')
      // L'application n'affiche rien tant que /auth/moi n'a pas répondu : évaluer le DOM
      // sans cette attente mesurait une page vide, et le test « passait » sur zéro champ.
      await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()
      const tailles = await page.evaluate(() =>
        [...document.querySelectorAll('input')].map((i) =>
          Number.parseFloat(getComputedStyle(i).fontSize),
        ),
      )
      expect(tailles.length).toBeGreaterThan(0)
      for (const taille of tailles) expect(taille).toBeGreaterThanOrEqual(16)
    })
  })
}

test.describe('navigation selon la taille', () => {
  test('téléphone : la navigation est en bas', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await connecter(page)
    const nav = page.locator('nav')
    const boite = (await nav.boundingBox())!
    expect(boite.width, 'la barre doit être plus large que haute').toBeGreaterThan(boite.height)
    expect(boite.y, 'la barre doit être dans la moitié basse').toBeGreaterThan(844 / 2)
  })

  test('bureau : la navigation est un rail latéral, pas une barre basse', async ({ page }) => {
    // Sans ce contrôle, le bureau resterait un mobile étiré : une pilule au centre d'un
    // écran de 1280 px, et 1000 px de vide autour.
    await page.setViewportSize({ width: 1280, height: 800 })
    await connecter(page)
    const boite = (await page.locator('nav').boundingBox())!
    expect(boite.height, 'le rail doit être plus haut que large').toBeGreaterThan(boite.width)
    expect(boite.x, 'le rail doit être collé à gauche').toBeLessThan(100)
  })

  test('la navigation reste entièrement dans la fenêtre', async ({ page }) => {
    // Régression : la tab bar dépassait de 41 px sous le bord, ses boutons étaient
    // partiellement inatteignables. Voir ERREURS.md #008.
    for (const vue of VIEWPORTS) {
      await page.setViewportSize({ width: vue.width, height: vue.height })
      await connecter(page)
      const boite = (await page.locator('nav').boundingBox())!
      expect(boite.y + boite.height, `${vue.nom} : la nav dépasse en bas`).toBeLessThanOrEqual(
        vue.height,
      )
      expect(boite.x, `${vue.nom} : la nav déborde à gauche`).toBeGreaterThanOrEqual(0)
      expect(boite.x + boite.width, `${vue.nom} : la nav déborde à droite`).toBeLessThanOrEqual(
        vue.width,
      )
    }
  })
})

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  // Attendre que l'application ait tranché entre « connecté » et « pas connecté ».
  // Sans cette attente, la garde ci-dessous lisait une page encore vide, concluait
  // « pas connecté » et tentait de remplir un formulaire absent.
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}
