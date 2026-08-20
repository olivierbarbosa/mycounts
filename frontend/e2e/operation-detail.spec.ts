import { expect, test } from '@playwright/test'

/**
 * Détail, correction et retrait d'une opération.
 *
 * Le test central est `retirer une échéance de prélèvement ne la fait pas revenir` :
 * une suppression sèche paraîtrait juste jusqu'au prochain calcul, où la ligne
 * réapparaîtrait sans explication.
 */

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

/**
 * Ouvre le calendrier depuis sa bulle.
 *
 * `dispatchEvent` et non `click`, pour une raison précise : depuis que l'écran monte sa
 * coquille SANS attendre le réseau — c'était le but, il ne s'affichait avant qu'après
 * quatre allers-retours — il recouvre la bulle dans la milliseconde qui suit l'appui.
 * Playwright vérifie l'actionnabilité de sa cible APRÈS avoir cliqué, constate qu'elle est
 * désormais couverte par l'écran qu'elle vient d'ouvrir, et réessaie jusqu'au délai.
 *
 * La bulle est pourtant bien cliquable AU MOMENT du clic, et l'interception qui suit est
 * le résultat attendu du geste, pas un obstacle à celui-ci. L'assertion sur le dialogue
 * garde donc toute sa valeur : si le clic ne portait pas, elle échouerait.
 */
async function ouvrirCalendrier(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: 'Calendrier' }).dispatchEvent('click')
  await expect(page.getByRole('dialog', { name: 'Calendrier' })).toBeVisible()
}

async function saisir(page: import('@playwright/test').Page, libelle: string, montant: string) {
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant', { exact: true }).fill(montant)
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}

test('ouvrir le détail d’une opération depuis la liste', async ({ page }) => {
  const libelle = `Detail ${Date.now()}`
  await connecter(page)
  await saisir(page, libelle, '45,90')

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()

  const feuille = page.getByRole('dialog', { name: 'Détail de l’opération' })
  await expect(feuille).toBeVisible()
  await expect(feuille).toContainText('Saisie manuelle')
  await expect(feuille).toContainText('Confirmée')
  await expect(feuille.getByLabel('Montant')).toHaveValue('45,90')
})

test('corriger un montant met à jour le solde affiché', async ({ page }) => {
  const libelle = `Corrige ${Date.now()}`
  await connecter(page)
  await saisir(page, libelle, '45,90')

  const avant = await page.locator('main header').innerText()

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  await page.getByLabel('Montant', { exact: true }).fill('10,00')
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const ligne = page.locator('li', { hasText: libelle }).first()
  await expect(ligne).toContainText('−10')
  await expect(page.locator('main header')).not.toHaveText(avant)
})

test('corriger ne change pas le sens de l’opération', async ({ page }) => {
  // Une dépense reste une dépense : la faire basculer par un signe tapé serait une
  // inversion silencieuse, invisible jusqu'au solde suivant.
  const libelle = `Sens ${Date.now()}`
  await connecter(page)
  await saisir(page, libelle, '30,00')

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  await page.getByLabel('Montant', { exact: true }).fill('50,00')
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  const ligne = page.locator('li', { hasText: libelle }).first()
  await expect(ligne).toContainText('−50')
  await expect(ligne).not.toContainText('+50')
})

test('supprimer demande confirmation et retire l’opération', async ({ page }) => {
  const libelle = `Jetable ${Date.now()}`
  await connecter(page)
  await saisir(page, libelle, '12,00')

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  await page.getByRole('button', { name: 'Supprimer', exact: true }).click()

  // La confirmation apparaît, et l'opération est toujours là tant qu'on n'a pas validé.
  await expect(page.getByRole('alertdialog')).toBeVisible()

  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Supprimer', exact: true })
    .click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('button', { name: `Détail de ${libelle}` })).toHaveCount(0)
})

test('annuler la confirmation laisse l’opération en place', async ({ page }) => {
  const libelle = `Garde ${Date.now()}`
  await connecter(page)
  await saisir(page, libelle, '8,00')

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  await page.getByRole('button', { name: 'Supprimer', exact: true }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Annuler', exact: true }).click()
  await expect(page.getByRole('alertdialog')).toHaveCount(0)

  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
  await expect(page.getByRole('button', { name: `Détail de ${libelle}` })).toBeVisible()
})

test('retirer une échéance de prélèvement ne la fait pas revenir', async ({ page }) => {
  // Le contrôle qui distingue une annulation d'une suppression sèche : celle-ci
  // paraîtrait juste jusqu'au prochain calcul, où la ligne réapparaîtrait.
  const libelle = `Echeance ${Date.now()}`
  const hier = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10)

  await connecter(page)
  await ouvrirCalendrier(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  await page.getByLabel('Montant', { exact: true }).fill('7,50')
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Première échéance').fill(hier)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  // La FEUILLE nommément : le calendrier qui l'a ouverte est lui-même un dialogue modal
  // et reste ouvert derrière elle.
  await expect(page.getByRole('dialog', { name: /prélèvement/ })).toHaveCount(0)

  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
  await page.getByRole('button', { name: 'Accueil' }).click()
  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  await expect(page.getByRole('dialog')).toContainText('Prélèvement automatique')
  await page.getByRole('button', { name: 'Supprimer', exact: true }).click()
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Supprimer', exact: true })
    .click()

  // Le calcul se rejoue à chaque ouverture du calendrier : trois passages suffisent
  // largement à faire réapparaître une ligne simplement supprimée.
  for (let tour = 0; tour < 3; tour++) {
    await ouvrirCalendrier(page)
    // Fermer l'écran, et non cliquer sur l'onglet « Accueil » : la barre d'onglets est
    // RECOUVERTE par le calendrier, qui est un dialogue modal. Le tour de boucle ne
    // rouvrait donc rien, et le test ne rejouait pas le calcul qu'il prétend éprouver.
    // Celui DU CALENDRIER : le détail de l'opération, ouvert derrière, en porte un autre.
    await page
      .getByRole('dialog', { name: 'Calendrier' })
      .getByRole('button', { name: 'Fermer', exact: true })
      .click()
    await expect(page.getByRole('dialog', { name: 'Calendrier' })).toHaveCount(0)
  }

  await expect(page.getByRole('button', { name: `Détail de ${libelle}` })).toHaveCount(0)
})
