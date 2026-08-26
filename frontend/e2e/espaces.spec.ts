import { expect, test } from '@playwright/test'

import { listeDesEspaces, selecteurEspace } from './espaces-aide'

const PERSONNEL = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
const FOYER = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2'

async function simulerApi(page: import('@playwright/test').Page) {
  await page.route('*://*/api/**', async (route) => {
    const requete = route.request()
    const chemin = new URL(requete.url()).pathname
    if (chemin === '/api/espaces') {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify([
          { id: PERSONNEL, type: 'personnel', nom: 'Camille', role: 'proprietaire' },
          { id: FOYER, type: 'foyer', nom: 'Maison', role: 'administrateur' },
        ]),
      })
      return
    }
    if (chemin === '/api/auth/moi') {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
          courriel: 'camille@essai.fr',
          nom_affichage: 'Camille',
          foyer_id: FOYER,
          foyer_nom: 'Maison',
          est_proprietaire: false,
          a_un_avatar: false,
          avatar_version: null,
        }),
      })
      return
    }
    if (chemin === '/api/comptes') {
      if (requete.headers()['x-mycounts-espace'] === FOYER) {
        await new Promise((resolve) => setTimeout(resolve, 180))
      }
      await route.fulfill({ contentType: 'application/json', body: '[]' })
      return
    }
    if (chemin === '/api/categories') {
      await route.fulfill({ contentType: 'application/json', body: '[]' })
      return
    }
    await route.fulfill({ status: 404, contentType: 'application/json', body: '{}' })
  })
}

test('le libellé et les données changent atomiquement avec X-Mycounts-Espace', async ({
  page,
}) => {
  await simulerApi(page)
  await page.goto('/')
  const pilule = selecteurEspace(page)
  await expect(page.getByRole('heading', { name: 'Votre premier compte' })).toBeVisible()
  await expect(pilule).toHaveText('Moi')

  await pilule.click()
  await listeDesEspaces(page).getByRole('button', { name: 'Maison', exact: true }).click()

  /* La réponse du nouveau monde est volontairement retardée de 180 ms : l'ancien libellé
     reste associé à l'ancien contenu, jamais au contenu en cours de chargement. Cette
     assertion DISCRIMINE — une implémentation qui poserait le libellé avant les données
     afficherait déjà « Maison » ici, et `toHaveText('Moi')` échouerait. */
  await expect(pilule).toHaveText('Moi')
  await expect(page.getByRole('heading', { name: 'Votre premier compte' })).toBeVisible()

  await expect(pilule).toHaveText('Maison')
  await expect(page.getByRole('heading', { name: 'Aucun compte joint' })).toBeVisible()
})

test('la création ou adhésion tient sans défilement dans 390 x 340', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 340 })
  await simulerApi(page)
  await page.goto('/')
  // La création vit désormais DERRIÈRE la liste : deux gestes, comme pour l'utilisateur.
  await selecteurEspace(page).click()
  await listeDesEspaces(page).getByRole('button', { name: 'Créer ou rejoindre un foyer' }).click()
  const dialogue = page.getByRole('dialog', { name: 'Nouveau foyer' })
  await expect(dialogue).toBeVisible()
  await expect(dialogue.getByRole('button', { name: 'Créer le foyer' })).toBeVisible()

  const mesure = await dialogue.evaluate((element) => {
    const boite = element.getBoundingClientRect()
    return {
      deborde: element.scrollHeight > element.clientHeight,
      haut: boite.top,
      bas: boite.bottom,
      fenetre: window.innerHeight,
    }
  })
  expect(mesure.deborde).toBe(false)
  expect(mesure.haut).toBeGreaterThanOrEqual(0)
  expect(mesure.bas).toBeLessThanOrEqual(mesure.fenetre)

  const cibles = await page
    .locator('[role="dialog"] button, [role="dialog"] input')
    .evaluateAll((elements) =>
      elements.map((element) => {
        const boite = element.getBoundingClientRect()
        return { largeur: boite.width, hauteur: boite.height }
      }),
    )
  expect(cibles.length).toBeGreaterThan(0)
  for (const cible of cibles) {
    expect(cible.largeur).toBeGreaterThanOrEqual(44)
    expect(cible.hauteur).toBeGreaterThanOrEqual(44)
  }
})

test('un espace mémorisé puis révoqué revient au personnel', async ({ page }) => {
  await simulerApi(page)
  await page.addInitScript(() => {
    localStorage.setItem('mycounts.espace', 'cccccccc-cccc-4ccc-8ccc-ccccccccccc3')
  })

  await page.goto('/')

  await expect(selecteurEspace(page)).toHaveText('Moi')
  await expect(page.getByRole('heading', { name: 'Votre premier compte' })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('mycounts.espace'))).toBe(PERSONNEL)
})
