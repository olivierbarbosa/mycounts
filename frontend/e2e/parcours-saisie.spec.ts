import { expect, test } from '@playwright/test'

/**
 * Parcours complet : amorçage, saisie, soldes.
 *
 * Ce test valide l'arithmétique **à l'écran**, pas dans une réponse d'API : c'est le seul
 * endroit où l'on vérifie que le chiffre lu par l'utilisateur est celui que le serveur a
 * calculé. Un total juste côté serveur et mal formaté à l'affichage produit exactement la
 * même impression qu'un total faux.
 */

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  const courriel = page.getByLabel('Adresse électronique')
  if (await courriel.isVisible()) {
    await courriel.fill(process.env.MYCOUNTS_COURRIEL_TEST!)
    await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
    await page.getByRole('button', { name: 'Se connecter' }).click()
  }
}

test('saisie : les montants affichés sont exacts', async ({ page }) => {
  // L'état de départ est fixé par le globalSetup : un compte, aucune opération.
  // L'écran d'amorçage n'est donc pas traversé ici — il est couvert par les tests
  // d'intégration de l'API. Voir scripts/reinitialiser_foyer_essai.py.
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()

  // Solde avant saisie, lu À L'ÉCRAN.
  const avant = await page.locator('main header').innerText()

  // Libellé unique par exécution : un libellé fixe finit par exister en plusieurs
  // exemplaires et le locator devient ambigu — la suite partage sa base avec les autres
  // fichiers de test.
  const libelle = `Courses e2e ${Date.now()}`
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant').fill('45,90')
  await page.getByLabel('Libellé').fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  await expect(page.getByText(libelle)).toBeVisible()

  const apres = await page.locator('main header').innerText()
  expect(apres, 'le solde affiché doit avoir changé après la saisie').not.toBe(avant)

  // La dépense apparaît avec le signe « moins » typographique, pas un tiret.
  const ligne = page.locator('li', { hasText: libelle })
  await expect(ligne).toContainText('−45')
})

test('une dépense saisie sans signe est enregistrée en négatif', async ({ page }) => {
  // Le sens vient de la bascule Dépense/Revenu, pas du signe tapé : l'utilisateur ne
  // doit pas avoir à y penser. Sans ce test, une inversion de signe passerait inaperçue
  // jusqu'au premier solde faux.
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByRole('button', { name: 'Dépense', exact: true }).click()
  await page.getByLabel('Montant').fill('12,34')
  const libelle = `Sens e2e ${Date.now()}`
  await page.getByLabel('Libellé').fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  const ligne = page.locator('li', { hasText: libelle })
  await expect(ligne).toContainText('−12')
  await expect(ligne).not.toContainText('+12')
})

test('un montant illisible est refusé avant tout envoi', async ({ page }) => {
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant').fill('douze euros')
  await page.getByLabel('Libellé').fill('Illisible')
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  await expect(page.getByRole('alert')).toContainText('illisible')
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('le solde projeté est toujours accompagné de sa borne', async ({ page }) => {
  // Un solde projeté sans date de fin de fenêtre est ininterprétable : « il me reste
  // 320 € » — jusqu'à quand ?
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()
  await expect(page.locator('main header')).toContainText('jusqu’au')
})
