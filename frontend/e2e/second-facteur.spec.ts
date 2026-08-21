import { expect, test, type Page } from '@playwright/test'

/**
 * Activation du second facteur, vue de l'écran.
 *
 * Le test central est `les codes de secours exigent une confirmation avant de disparaître`
 * : le serveur ne les garde que hachés, donc les redemander est impossible — pas
 * seulement interdit. Un simple « Fermer » les ferait perdre d'un clic distrait, et le
 * compte deviendrait irrécupérable en cas de téléphone perdu.
 *
 * **Ce fichier n'active JAMAIS le second facteur pour de bon** : le compte de
 * démonstration est partagé par les autres fichiers, et l'enrôler exigerait un code TOTP
 * de toutes leurs connexions. Ce que l'activation fait réellement est mesuré côté
 * intégration, dans `test_api_second_facteur.py`, contre une base jetable.
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

async function ouvrirMonCompte(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Mon compte' }).click()
  await expect(page.getByRole('heading', { name: 'Vérification en deux étapes' })).toBeVisible()
}

test('l’enrôlement propose de scanner ET de recopier la clé', async ({ page }) => {
  /* La saisie manuelle n'est pas un repli de second ordre : un ordinateur de bureau n'a
   * pas de caméra, et certaines applications n'acceptent que la clé. Ne proposer que le
   * QR exclurait ces cas sans le dire. */
  await connecter(page)
  await ouvrirMonCompte(page)
  const panneau = page.getByRole('dialog', { name: 'Paramètres' })

  await panneau.getByRole('button', { name: 'Activer' }).click()
  await expect(panneau.getByLabel('Code à scanner')).toBeVisible()
  await expect(panneau.getByLabel('Code à scanner').locator('svg')).toBeVisible()

  await panneau.getByRole('group').filter({ hasText: 'Impossible de scanner' }).click()
  await expect(panneau.getByText(/^[A-Z2-7]{16,}$/)).toBeVisible()

  // On s'arrête là : activer pour de bon exigerait un code TOTP de tous les autres tests.
  await panneau.getByRole('button', { name: 'Annuler' }).click()
  await expect(panneau.getByRole('button', { name: 'Activer' })).toBeVisible()
})

test('le bouton d’activation reste inerte tant que le code est incomplet', async ({ page }) => {
  await connecter(page)
  await ouvrirMonCompte(page)
  const panneau = page.getByRole('dialog', { name: 'Paramètres' })

  await panneau.getByRole('button', { name: 'Activer' }).click()
  const valider = panneau.getByRole('button', { name: 'Vérifier et activer' })
  await expect(valider, 'inerte tant que rien n’est tapé').toBeDisabled()

  await panneau.getByLabel('Code affiché par l’application').fill('123')
  await expect(valider, 'inerte sur un code trop court').toBeDisabled()

  await panneau.getByLabel('Code affiché par l’application').fill('123456')
  await expect(valider, 'actif sur six chiffres').toBeEnabled()

  await panneau.getByRole('button', { name: 'Annuler' }).click()
})

test('un code faux est refusé, et le message dit quoi vérifier', async ({ page }) => {
  /* « Ce code ne correspond pas » sans plus laisse chercher au mauvais endroit : la cause
   * la plus fréquente est l'heure du téléphone, pas une faute de frappe. */
  await connecter(page)
  await ouvrirMonCompte(page)
  const panneau = page.getByRole('dialog', { name: 'Paramètres' })

  await panneau.getByRole('button', { name: 'Activer' }).click()
  await panneau.getByLabel('Code affiché par l’application').fill('000000')
  await panneau.getByRole('button', { name: 'Vérifier et activer' }).click()

  await expect(panneau.getByRole('alert')).toContainText('heure')
  // Et rien n'est activé : un enrôlement raté ne verrouille pas le compte.
  await panneau.getByRole('button', { name: 'Annuler' }).click()
  await expect(panneau.getByRole('button', { name: 'Activer' })).toBeVisible()
})
