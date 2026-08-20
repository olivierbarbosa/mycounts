import { expect, test, type Page } from '@playwright/test'

/**
 * Choix du thème, et son autorité sur celui du système.
 *
 * L'application a longtemps suivi `prefers-color-scheme` sans recours possible : un
 * iPhone réglé sur « automatique » la faisait passer en clair au lever du jour, sans
 * qu'aucun écran ne permette de s'y opposer.
 *
 * La mesure porte sur les DEUX sens. Vérifier seulement « système clair + choix sombre →
 * fond sombre » ne distinguerait pas un réglage qui fonctionne d'un réglage cassé qui
 * afficherait toujours du sombre.
 */

const FOND_SOMBRE = 'rgb(27, 15, 51)'
const FOND_CLAIR = 'rgb(251, 247, 255)'

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

/** Ouvre le panneau puis sa page Apparence. Le panneau est modal : une fois ouvert, il
 *  recouvre la bulle, donc il ne faut pas chercher à le rouvrir entre deux choix. */
async function ouvrirApparence(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Apparence' }).click()
  await expect(page.getByRole('group', { name: 'Thème de l’interface' })).toBeVisible()
}

async function choisirTheme(page: Page, libelle: string) {
  await page
    .getByRole('group', { name: 'Thème de l’interface' })
    .getByRole('button', { name: libelle })
    .click()
}

const fond = (page: Page) => page.evaluate(() => getComputedStyle(document.body).backgroundColor)

test('le thème choisi l’emporte sur celui du téléphone, dans les deux sens', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await connecter(page)
  expect(await fond(page), 'sans choix, l’app suit le téléphone').toBe(FOND_CLAIR)

  await ouvrirApparence(page)
  await choisirTheme(page, 'Sombre')
  expect(await fond(page), 'le choix sombre doit primer sur un téléphone en clair').toBe(
    FOND_SOMBRE,
  )

  // L'autre sens, sur un téléphone en sombre : c'est ce qui distingue un réglage qui
  // fonctionne d'un réglage bloqué sur une seule valeur.
  await page.emulateMedia({ colorScheme: 'dark' })
  await choisirTheme(page, 'Clair')
  expect(await fond(page), 'le choix clair doit primer sur un téléphone en sombre').toBe(FOND_CLAIR)

  // Et « Système » rend la main.
  await choisirTheme(page, 'Système')
  expect(await fond(page), 'Système doit rendre la main au téléphone').toBe(FOND_SOMBRE)
})

test('le thème choisi survit au rechargement', async ({ page }) => {
  // Un réglage qui se perd au rechargement est pire que pas de réglage : il donne
  // l'impression d'avoir été ignoré.
  await page.emulateMedia({ colorScheme: 'light' })
  await connecter(page)
  await ouvrirApparence(page)
  await choisirTheme(page, 'Sombre')

  await page.reload()
  await expect(page.locator('nav')).toBeVisible()
  expect(await fond(page)).toBe(FOND_SOMBRE)

  // Remettre « Système » : les tests suivants partagent ce navigateur et son stockage.
  await ouvrirApparence(page)
  await choisirTheme(page, 'Système')
})
