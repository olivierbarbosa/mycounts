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

/* La mesure porte sur la LUMINANCE du fond, pas sur deux valeurs `rgb()` recopiées.
 *
 * Ces deux constantes tenaient les couleurs exactes de la palette. Elles en faisaient donc
 * un second auteur : changer la palette dans `tokens.ts` — seul auteur déclaré — faisait
 * rougir ce test, qui ne parle pourtant pas de couleurs mais de savoir QUI décide du
 * thème, du réglage ou du téléphone.
 *
 * Ce que la version par luminance perd : elle ne verrait pas une palette sombre virant au
 * brun. Ce n'est pas ce que ce fichier surveille, et `contraste.spec.ts` le verrait.
 * Ce qu'elle garde : les deux sens restent distingués, donc un réglage bloqué sur une
 * seule valeur la fait toujours rougir — vérifié en forçant `data-theme` à une constante.
 */
const luminance = (page: Page) =>
  page.evaluate(() => {
    const [r, v, b] = getComputedStyle(document.body)
      .backgroundColor.match(/[\d.]+/g)!
      .map(Number)
    const canal = (x: number) => {
      const n = x / 255
      return n <= 0.03928 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4
    }
    return 0.2126 * canal(r) + 0.7152 * canal(v) + 0.0722 * canal(b)
  })

/** Au-dessus : un fond clair. En dessous : un fond sombre. Les deux thèmes du projet
 *  mesurent 0,86 et 0,01 — la frontière est large, elle ne départage rien de limite. */
const FRONTIERE = 0.3

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
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

test('le thème choisi l’emporte sur celui du téléphone, dans les deux sens', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await connecter(page)
  expect(await luminance(page), 'sans choix, l’app suit le téléphone').toBeGreaterThan(FRONTIERE)

  await ouvrirApparence(page)
  await choisirTheme(page, 'Sombre')
  expect(
    await luminance(page),
    'le choix sombre doit primer sur un téléphone en clair',
  ).toBeLessThan(FRONTIERE)

  // L'autre sens, sur un téléphone en sombre : c'est ce qui distingue un réglage qui
  // fonctionne d'un réglage bloqué sur une seule valeur.
  await page.emulateMedia({ colorScheme: 'dark' })
  await choisirTheme(page, 'Clair')
  expect(
    await luminance(page),
    'le choix clair doit primer sur un téléphone en sombre',
  ).toBeGreaterThan(FRONTIERE)

  // Et « Système » rend la main.
  await choisirTheme(page, 'Système')
  expect(await luminance(page), 'Système doit rendre la main au téléphone').toBeLessThan(FRONTIERE)
})

test('le thème choisi survit au rechargement', async ({ page }) => {
  // Un réglage qui se perd au rechargement est pire que pas de réglage : il donne
  // l'impression d'avoir été ignoré.
  await page.emulateMedia({ colorScheme: 'light' })
  await connecter(page)
  await ouvrirApparence(page)
  await choisirTheme(page, 'Sombre')

  await page.reload()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
  expect(await luminance(page)).toBeLessThan(FRONTIERE)

  // Remettre « Système » : les tests suivants partagent ce navigateur et son stockage.
  await ouvrirApparence(page)
  await choisirTheme(page, 'Système')
})
