import { expect, test, type Page } from '@playwright/test'

/**
 * Les deux zones de danger, et le fait qu'elles soient DEUX.
 *
 * Le test central est `arrêter de partager et disparaître sont deux écrans` : c'est la
 * correction du 21 août 2026. Un seul bouton « Supprimer le foyer » faisait les deux, si
 * bien qu'Olivier perdait son compte et sa session en voulant seulement cesser de
 * partager — le foyer étant, en base, le conteneur racine de ses comptes personnels
 * (ERREURS.md #044). Les refondre en une seule zone ferait revenir le défaut sans qu'aucun
 * autre test ne s'en aperçoive.
 *
 * Ce fichier ne va JAMAIS jusqu'au bout, ni pour l'une ni pour l'autre :
 * — « Tout effacer » détruirait le compte de démonstration et les autres tests avec lui ;
 * — « Supprimer les comptes joints » emporterait ceux que `vue-foyer.spec.ts` vient de
 *   créer, et les tests partagent un même foyer : la dissolution déplacerait le sol sous
 *   les autres exactement comme une paie mal placée le ferait.
 * Ce que ces deux actions font réellement est prouvé côté intégration, contre une base
 * jetable, dans `test_suppression_foyer.py` et `test_dissolution_partage.py`.
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

async function ouvrirParametres(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
}

async function ouvrirFoyer(page: Page) {
  await ouvrirParametres(page)
  await page.getByRole('button', { name: 'Foyer' }).click()
  await expect(page.getByRole('heading', { name: 'Membres' })).toBeVisible()
}

async function ouvrirMonCompte(page: Page) {
  await ouvrirParametres(page)
  await page.getByRole('button', { name: 'Mon compte' }).click()
  await expect(page.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
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

test('arrêter de partager et disparaître sont deux écrans', async ({ page }) => {
  /* La séparation elle-même, mesurée dans les deux sens : chaque écran porte SON action
   * et pas celle de l'autre. Une assertion sur la seule présence des deux boutons
   * passerait encore s'ils étaient tous deux revenus sur l'écran du foyer. */
  await connecter(page)
  await ouvrirFoyer(page)
  await expect(page.getByRole('heading', { name: 'Dissoudre le partage' })).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Supprimer mon compte' }),
    'effacer son compte n’a rien à faire sur l’écran du foyer',
  ).toHaveCount(0)

  await page.getByRole('button', { name: 'Retour', exact: true }).click()
  await page.getByRole('button', { name: 'Mon compte' }).click()
  await expect(page.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Dissoudre le partage' }),
    'le partage ne se dissout pas depuis son compte',
  ).toHaveCount(0)
})

test('dissoudre annonce ce qu’il NE touche pas', async ({ page }) => {
  /* L'ancienne zone disait « personnels comme joints » — elle était honnête, l'action
   * était brutale. Celle-ci doit dire l'inverse, et le dire explicitement : c'est la
   * seule chose qui distingue les deux boutons aux yeux de qui les lit. */
  await connecter(page)
  await ouvrirFoyer(page)

  const zone = page.getByText(/Supprime les comptes joints/)
  await expect(zone).toContainText('comptes personnels')
  await expect(zone, 'la promesse qui manquait').toContainText('restez connecté')
})

test('le bouton reste inerte tant que l’adresse n’est pas exacte', async ({ page }) => {
  /* La seule barrière entre un doigt qui glisse et une perte définitive — et celle qu'un
   * remaniement de l'écran ferait sauter sans bruit : la suppression continuerait de
   * fonctionner, seule la protection disparaîtrait.
   *
   * C'est l'ADRESSE et non le nom du foyer depuis le 21 août 2026 : ce qu'on détruit ici
   * est son compte, et faire retaper le nom du foyer désignait la mauvaise chose. */
  await connecter(page)
  await ouvrirMonCompte(page)

  await page.getByRole('button', { name: 'Supprimer mon compte' }).click()
  const effacer = page.getByRole('button', { name: 'Tout effacer' })
  await expect(effacer, 'inerte tant que rien n’est tapé').toBeDisabled()

  const champ = page.getByRole('textbox')
  await champ.fill('quelquun@ailleurs.fr')
  await expect(effacer, 'inerte sur une adresse fausse').toBeDisabled()

  // L'adresse est affichée juste au-dessus : le test la lit là où l'utilisateur la lit,
  // plutôt que de la coder en dur — sinon il mesurerait sa propre constante.
  const adresse = (await page.locator('strong').last().textContent())!
  await champ.fill(adresse)
  await expect(effacer, 'actif sur l’adresse exacte').toBeEnabled()

  // On s'arrête ici. Voir l'en-tête du fichier.
  await page.getByRole('button', { name: 'Annuler' }).click()
  await expect(page.getByRole('button', { name: 'Tout effacer' })).toHaveCount(0)
})

test('supprimer son compte dit ce qu’il détruit avant de le détruire', async ({ page }) => {
  await connecter(page)
  await ouvrirMonCompte(page)

  const zone = page.getByText(/Efface définitivement votre compte/)
  await expect(zone).toContainText('comptes personnels')
  await expect(zone).toContainText('Aucune sauvegarde')
})
