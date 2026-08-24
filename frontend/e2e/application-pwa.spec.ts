import { expect, test, type Page } from '@playwright/test'

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
}

test.describe('installation sur iPhone', () => {
  test.use({
    viewport: { width: 390, height: 700 },
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1',
  })

  test('explique l’ajout avant de demander les notifications, sans débordement', async ({
    page,
  }) => {
    // L'explication n'apparaît que tant que rien n'a été décidé : un Chromium headless
    // répond « denied » d'office, et l'écran dirait alors « bloquées » — le test
    // mesurerait le navigateur de test, pas l'écran. L'état est figé à « default ».
    await page.addInitScript(() => {
      if ('Notification' in window) {
        Object.defineProperty(window.Notification, 'permission', {
          configurable: true,
          get: () => 'default',
        })
      }
    })
    await connecter(page)
    await page.getByRole('button', { name: /^Paramètres de / }).click()
    await page.getByRole('button', { name: 'Application' }).click()

    await expect(page.getByRole('heading', { name: 'Sur l’écran d’accueil' })).toBeVisible()
    await expect(page.getByText('Touchez', { exact: false })).toBeVisible()
    await expect(page.getByText('installez d’abord MyCounts', { exact: false })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Autoriser les notifications' })).toHaveCount(0)

    const disposition = await page.evaluate(() => ({
      largeurPage: document.documentElement.scrollWidth,
      largeurViewport: document.documentElement.clientWidth,
      hauteurRetour: document.querySelector<HTMLButtonElement>('button[aria-label="Retour"]')
        ?.getBoundingClientRect().height,
    }))
    expect(disposition.largeurPage).toBeLessThanOrEqual(disposition.largeurViewport)
    expect(disposition.hauteurRetour).toBeGreaterThanOrEqual(44)
  })
})
