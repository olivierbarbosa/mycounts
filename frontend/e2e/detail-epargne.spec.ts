import { expect, test, type Page } from '@playwright/test'

/**
 * Détail d'un livret : versé, repris, et le signal de l'aller-retour.
 *
 * Le test central est `un aller-retour se voit à l'écran` : c'est la mesure qui peut
 * rendre la réponse inverse. Un mois où l'on verse 500 € puis en reprend 200 doit se
 * distinguer d'un mois calme — sous un solde net, les deux se ressembleraient.
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

/** Crée un livret et y fait circuler de l'argent, par l'API : ce test porte sur ce que
 *  l'écran AFFICHE, pas sur la façon dont les virements se saisissent. */
async function livretAvecMouvements(page: Page, nom: string, verse: number, repris: number) {
  const comptes = (await (await page.request.get('/api/comptes')).json()) as {
    id: string
    type_compte: string
  }[]
  const courant = comptes.find((c) => c.type_compte === 'courant')!

  const livret = (await (
    await page.request.post('/api/comptes', {
      data: { nom, prive: true, produit: 'livret_a' },
    })
  ).json()) as { id: string }

  const jour = new Date().toISOString().slice(0, 10)
  await page.request.post('/api/virements', {
    data: {
      compte_source_id: courant.id,
      compte_destination_id: livret.id,
      montant_centimes: verse,
      date_operation: jour,
    },
  })
  if (repris > 0) {
    await page.request.post('/api/virements', {
      data: {
        compte_source_id: livret.id,
        compte_destination_id: courant.id,
        montant_centimes: repris,
        date_operation: jour,
      },
    })
  }
  return livret.id
}

test('un aller-retour se voit à l’écran', async ({ page }) => {
  await connecter(page)
  const nom = `Livret AR ${Date.now()}`
  await livretAvecMouvements(page, nom, 50_000, 20_000)

  await page.getByRole('button', { name: 'Épargne' }).click()
  await page.getByRole('button', { name: `Détail de ${nom}` }).click()

  const detail = page.getByRole('dialog', { name: `Détail de ${nom}` })
  await expect(detail).toBeVisible()

  // Le signal, écrit en toutes lettres : un chiffre qu'il faut déduire d'un dessin n'est
  // pas un chiffre qu'on lit.
  await expect(detail).toContainText('versé puis repris')
  await expect(detail).toContainText('aller-retour')

  // Les deux montants restent distincts : 500 versés et 200 repris, jamais 300 nets.
  await expect(detail).toContainText('500')
  await expect(detail).toContainText('200')
})

test('un livret sans reprise ne déclenche aucun signal', async ({ page }) => {
  // Le témoin du test précédent : sans lui, un écran qui crierait à l'aller-retour en
  // toutes circonstances passerait aussi bien.
  await connecter(page)
  const nom = `Livret calme ${Date.now()}`
  await livretAvecMouvements(page, nom, 30_000, 0)

  await page.getByRole('button', { name: 'Épargne' }).click()
  await page.getByRole('button', { name: `Détail de ${nom}` }).click()

  const detail = page.getByRole('dialog', { name: `Détail de ${nom}` })
  await expect(detail).toContainText('Le rythme tient')
  await expect(detail).not.toContainText('aller-retour')
})

test('le détail se referme et rend la main à la liste', async ({ page }) => {
  await connecter(page)
  const nom = `Livret ferme ${Date.now()}`
  await livretAvecMouvements(page, nom, 10_000, 0)

  await page.getByRole('button', { name: 'Épargne' }).click()
  await page.getByRole('button', { name: `Détail de ${nom}` }).click()
  await expect(page.getByRole('dialog', { name: `Détail de ${nom}` })).toBeVisible()

  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
  await expect(page.getByRole('dialog', { name: `Détail de ${nom}` })).toHaveCount(0)
  await expect(page.getByRole('button', { name: `Détail de ${nom}` })).toBeVisible()
})
