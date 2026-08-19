import { expect, test } from '@playwright/test'

/**
 * Agenda et confirmation, dans le vrai navigateur.
 *
 * Le test central est `confirmer ne déplace pas le solde projeté` : c'est l'invariant le
 * plus important du projet, et c'est ici qu'il est vérifié tel que l'utilisateur le voit
 * — pas dans une réponse d'API.
 */

const HIER = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10)

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

async function ouvrirAgenda(page: import('@playwright/test').Page) {
  await connecter(page)
  await page.getByRole('button', { name: 'Agenda' }).click()
  await expect(page.getByRole('heading', { name: 'Agenda' })).toBeVisible()
}

async function creerRecurrence(
  page: import('@playwright/test').Page,
  libelle: string,
  montant: string,
  ancre: string,
) {
  await page.getByRole('button', { name: 'Ajouter une échéance récurrente' }).click()
  await page.getByLabel('Montant', { exact: true }).fill(montant)
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Première échéance').fill(ancre)
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}

test('créer une échéance récurrente et la voir dans l’agenda', async ({ page }) => {
  const libelle = `Abonnement ${Date.now()}`
  await ouvrirAgenda(page)
  const dans10 = new Date(Date.now() + 10 * 86_400_000).toISOString().slice(0, 10)

  await creerRecurrence(page, libelle, '10,99', dans10)

  const ligne = page.locator('li', { hasText: libelle }).first()
  await expect(ligne).toBeVisible()
  await expect(ligne).toContainText('−10')
})

test('une échéance échue remonte dans « à confirmer » sans job manuel', async ({ page }) => {
  // Le trou d'ERREURS.md #018 : entre l'échéance et le passage du job, elle
  // n'apparaissait nulle part. La seule ouverture de l'agenda doit suffire.
  const libelle = `Echue ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '7,50', HIER)

  await expect(page.getByText('À confirmer', { exact: false })).toBeVisible()
  const ligne = page.locator('li', { hasText: libelle }).first()
  await expect(ligne.getByRole('button', { name: 'Confirmer' })).toBeVisible()
})

test('confirmer ne déplace pas le solde projeté', async ({ page }) => {
  // L'invariant central du projet, mesuré tel que l'utilisateur le voit. Trois grandeurs,
  // dont deux qui doivent varier en sens OPPOSÉS : si les trois bougeaient ensemble, ce
  // serait la sonde qui est fausse ; si le projeté bougeait, il y aurait double comptage.
  const libelle = `Temoin ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '12,34', HIER)

  const lire = async () => {
    const reponse = await page.request.get('/api/resume')
    return (await reponse.json()) as {
      solde_projete: number
      solde_reel: number
      solde_a_confirmer: number
    }
  }

  const avant = await lire()
  const ligne = page.locator('li', { hasText: libelle }).first()
  await ligne.getByRole('button', { name: 'Confirmer' }).click()
  await expect(ligne.getByRole('button', { name: 'Confirmer' })).toHaveCount(0)
  const apres = await lire()

  expect(apres.solde_projete, 'double comptage à la confirmation').toBe(avant.solde_projete)
  expect(apres.solde_reel).toBeLessThan(avant.solde_reel)
  expect(apres.solde_a_confirmer).toBeGreaterThan(avant.solde_a_confirmer)
  expect(apres.solde_reel - avant.solde_reel).toBe(
    -(apres.solde_a_confirmer - avant.solde_a_confirmer),
  )
})

test('le total de l’agenda est la somme de ses lignes', async ({ page }) => {
  // Un total affiché qui ne serait pas la somme de ce qu'on voit est indétectable à
  // l'œil dès qu'il y a plus de trois lignes.
  await ouvrirAgenda(page)
  const dans5 = new Date(Date.now() + 5 * 86_400_000).toISOString().slice(0, 10)
  await creerRecurrence(page, `Somme ${Date.now()}`, '25,00', dans5)

  const echeances = await page.request.get('/api/agenda?jours=60')
  const lignes = (await echeances.json()) as { montant_centimes: number }[]
  const attendu = lignes.reduce((s, e) => s + e.montant_centimes, 0)

  const total = page.locator('main').getByText('Total des 60 prochains jours')
  await expect(total).toBeVisible()

  const euros = Math.trunc(Math.abs(attendu) / 100).toLocaleString('fr-FR')
  await expect(total.locator('..')).toContainText(euros)
})
