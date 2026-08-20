import { expect, test, type Page } from '@playwright/test'

/**
 * Correction du solde depuis l'accueil.
 *
 * Un solde est une SOMME d'opérations, jamais une valeur qu'on écrit : la correction
 * devient une opération de plus, qui porte l'écart. Le test central vérifie qu'elle
 * n'entre pas dans les dépenses — réparer une erreur de saisie de 20 € n'est pas avoir
 * dépensé 20 €, et l'y compter ferait sauter un plafond pour une erreur qu'on vient
 * précisément de réparer.
 */

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

const lire = async (page: Page) =>
  (await (await page.request.get('/api/resume')).json()) as {
    solde_reel: number
    depenses_de_periode: number
  }

test('corriger le solde depuis l’accueil ne crée pas de dépense', async ({ page }) => {
  await connecter(page)
  const avant = await lire(page)
  const vise = avant.solde_reel - 4_321

  await page.getByRole('button', { name: /Réel aujourd’hui/ }).click()
  await expect(page.getByRole('dialog', { name: 'Corriger le solde' })).toBeVisible()

  // Le premier compte de la liste est celui que l'accueil totalise : le foyer d'essai
  // n'en a qu'un de courant.
  await page.getByLabel('Solde affiché par votre banque').fill(String(vise / 100).replace('.', ','))
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const apres = await lire(page)
  expect(apres.solde_reel, 'le solde doit rejoindre la valeur saisie').toBe(vise)
  expect(
    apres.depenses_de_periode,
    'un ajustement compté en dépense ferait sauter les plafonds',
  ).toBe(avant.depenses_de_periode)
})

test('l’écart apparaît dans l’historique', async ({ page }) => {
  // Une correction invisible serait une valeur posée d'autorité : trois mois plus tard,
  // rien ne permettrait de comprendre l'écart.
  await connecter(page)
  const avant = await lire(page)

  await page.getByRole('button', { name: /Réel aujourd’hui/ }).click()
  const vise = avant.solde_reel + 1_500
  await page.getByLabel('Solde affiché par votre banque').fill(String(vise / 100).replace('.', ','))
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await expect(page.locator('main')).toContainText('Ajustement de solde')
})

test('corriger vers le solde déjà affiché ne fait rien', async ({ page }) => {
  // Écrire un ajustement de zéro remplirait l'historique de lignes qui ne disent rien.
  await connecter(page)
  const avant = await lire(page)
  const lignes = await (await page.request.get('/api/operations?periode_courante=false')).json()

  await page.getByRole('button', { name: /Réel aujourd’hui/ }).click()
  await page
    .getByLabel('Solde affiché par votre banque')
    .fill(String(avant.solde_reel / 100).replace('.', ','))
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const apres = await (await page.request.get('/api/operations?periode_courante=false')).json()
  expect(apres.length, 'aucune ligne ne doit être ajoutée').toBe(lignes.length)
})
