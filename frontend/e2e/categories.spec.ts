import { expect, test } from '@playwright/test'

/** Cycle de vie d'une catégorie, dans le vrai navigateur. */

async function ouvrirReglages(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (!(await page.locator('nav').isVisible())) {
    await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
    await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
    await page.getByRole('button', { name: 'Se connecter' }).click()
  }
  await page.getByRole('button', { name: 'Réglages' }).click()
  await expect(page.getByRole('heading', { name: 'Réglages' })).toBeVisible()
}

test('créer une catégorie puis la retrouver dans la saisie', async ({ page }) => {
  const nom = `Essai ${Date.now()}`
  await ouvrirReglages(page)

  await page.getByLabel('Nom de la nouvelle catégorie').fill(nom)
  await page.getByRole('button', { name: 'Ajouter', exact: true }).click()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toHaveValue(nom)

  // La catégorie doit être proposée à la saisie : une catégorie invisible du formulaire
  // ne sert à rien, et c'est exactement le genre de lien qu'un test d'API ne voit pas.
  await page.getByRole('button', { name: 'Accueil' }).click()
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await expect(page.getByLabel('Catégorie')).toContainText(nom)
})

test('renommer une catégorie', async ({ page }) => {
  const nom = `Renommer ${Date.now()}`
  await ouvrirReglages(page)
  await page.getByLabel('Nom de la nouvelle catégorie').fill(nom)
  await page.getByRole('button', { name: 'Ajouter', exact: true }).click()

  const champ = page.getByLabel(`Nom de la catégorie ${nom}`)
  await champ.fill(`${nom} modifié`)
  await champ.blur()

  await expect(page.getByLabel(`Nom de la catégorie ${nom} modifié`)).toBeVisible()
})

test('supprimer une catégorie inutilisée', async ({ page }) => {
  const nom = `Jetable ${Date.now()}`
  await ouvrirReglages(page)
  await page.getByLabel('Nom de la nouvelle catégorie').fill(nom)
  await page.getByRole('button', { name: 'Ajouter', exact: true }).click()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()

  const ligne = page.locator('li', { has: page.getByLabel(`Nom de la catégorie ${nom}`) })
  await ligne.getByRole('button', { name: 'Supprimer' }).click()

  // Une suppression ne part jamais d'un seul geste : la confirmation doit apparaître,
  // et la catégorie doit encore être là tant qu'elle n'est pas validée.
  await expect(page.getByRole('alertdialog')).toBeVisible()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()

  await page.getByRole('alertdialog').getByRole('button', { name: 'Supprimer' }).click()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toHaveCount(0)
})

test('annuler une suppression laisse la catégorie en place', async ({ page }) => {
  const nom = `Annulee ${Date.now()}`
  await ouvrirReglages(page)
  await page.getByLabel('Nom de la nouvelle catégorie').fill(nom)
  await page.getByRole('button', { name: 'Ajouter', exact: true }).click()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()

  const ligne = page.locator('li', { has: page.getByLabel(`Nom de la catégorie ${nom}`) })
  await ligne.getByRole('button', { name: 'Supprimer' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Annuler' }).click()

  await expect(page.getByRole('alertdialog')).toHaveCount(0)
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()
})

test('supprimer une catégorie utilisée est refusé avec une explication', async ({ page }) => {
  // Le refus doit dire pourquoi ET rester visible : un message qui disparaît laisse
  // croire que l'action a fonctionné.
  const nom = `Utilisee ${Date.now()}`
  await ouvrirReglages(page)
  await page.getByLabel('Nom de la nouvelle catégorie').fill(nom)
  await page.getByRole('button', { name: 'Ajouter', exact: true }).click()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()

  await page.getByRole('button', { name: 'Accueil' }).click()
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant').fill('9,99')
  await page.getByLabel('Libellé').fill(`Op ${nom}`)
  await page.getByLabel('Catégorie').selectOption({ label: nom })
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByText(`Op ${nom}`)).toBeVisible()

  await page.getByRole('button', { name: 'Réglages' }).click()
  const ligne = page.locator('li', { has: page.getByLabel(`Nom de la catégorie ${nom}`) })
  await ligne.getByRole('button', { name: 'Supprimer' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Supprimer' }).click()

  await expect(page.getByRole('alert')).toContainText('archiver')
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()
})
