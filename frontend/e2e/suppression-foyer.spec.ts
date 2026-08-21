import { expect, test, type Page } from '@playwright/test'

/**
 * La zone de danger de l'onglet Foyer.
 *
 * Le test central est `le bouton reste inerte tant que le nom n'est pas exact` : c'est la
 * seule barrière entre un doigt qui glisse et une perte définitive, et c'est aussi celle
 * qu'un remaniement de l'écran ferait sauter sans bruit — la suppression continuerait de
 * fonctionner, seule la protection disparaîtrait.
 *
 * Ce fichier ne va JAMAIS jusqu'au bout : cliquer « Tout effacer » détruirait le foyer de
 * démonstration et les cent vingt-trois autres tests avec lui. Ce que la suppression fait
 * réellement est prouvé côté intégration, dans `test_suppression_foyer.py`, contre une
 * base jetable.
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

async function ouvrirFoyer(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Foyer' }).click()
  await expect(page.getByRole('heading', { name: 'Membres' })).toBeVisible()
}

test('la liste des membres s’affiche au lieu de charger sans fin', async ({ page }) => {
  /* Le bug d'Olivier, dans le sens où il s'est produit : le client demandait
   * `/foyer/membres` quand la route est `/auth/foyer/membres`, et l'écran affichait
   * « Chargement… » pour toujours — parce qu'une liste vide et une liste pas encore
   * arrivée y étaient le même état.
   *
   * Ce test rougit aussi bien si le chemin casse que si les deux états refusionnent. */
  await connecter(page)
  await ouvrirFoyer(page)

  await expect(page.getByText('Chargement…')).toHaveCount(0)
  await expect(page.getByRole('listitem').first()).toBeVisible()
})

test('le bouton reste inerte tant que le nom n’est pas exact', async ({ page }) => {
  await connecter(page)
  await ouvrirFoyer(page)

  await page.getByRole('button', { name: 'Supprimer le foyer' }).click()
  const effacer = page.getByRole('button', { name: 'Tout effacer' })
  await expect(effacer, 'inerte tant que rien n’est tapé').toBeDisabled()

  const champ = page.getByRole('textbox')
  await champ.fill('n’importe quoi')
  await expect(effacer, 'inerte sur un nom faux').toBeDisabled()

  // Le nom du foyer est affiché juste au-dessus : le test le lit là où l'utilisateur le
  // lit, plutôt que de le coder en dur — sinon il mesurerait sa propre constante.
  const nomDuFoyer = (await page.locator('strong').first().textContent())!
  await champ.fill(nomDuFoyer.toLowerCase())
  await expect(effacer, 'la casse compte : c’est le signe qu’on a lu').toBeDisabled()

  await champ.fill(nomDuFoyer)
  await expect(effacer, 'actif sur le nom exact').toBeEnabled()

  // On s'arrête ici. Voir l'en-tête du fichier.
  await page.getByRole('button', { name: 'Annuler' }).click()
  await expect(page.getByRole('button', { name: 'Tout effacer' })).toHaveCount(0)
})

test('la zone de danger dit ce qu’elle détruit avant de le détruire', async ({ page }) => {
  // Un « Supprimer le foyer » sans inventaire laisserait croire qu'on ne perd que
  // l'espace partagé. Ce sont AUSSI les comptes personnels.
  await connecter(page)
  await ouvrirFoyer(page)

  const zone = page.getByText(/Efface définitivement/)
  await expect(zone).toContainText('personnels comme joints')
  await expect(zone).toContainText('Aucune sauvegarde')
})
