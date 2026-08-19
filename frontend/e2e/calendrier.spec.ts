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
  await page.getByRole('button', { name: 'Calendrier' }).click()
  await expect(page.getByRole('heading', { name: 'Calendrier' })).toBeVisible()
}

async function creerRecurrence(
  page: import('@playwright/test').Page,
  libelle: string,
  montant: string,
  ancre: string,
) {
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  await page.getByLabel('Montant', { exact: true }).fill(montant)
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Première échéance').fill(ancre)
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}

test('créer un prélèvement et le voir dans le calendrier', async ({ page }) => {
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

test('le total des charges est la somme des lignes affichées', async ({ page }) => {
  // Un total affiché qui ne serait pas la somme de ce qu'on voit est indétectable à
  // l'œil dès qu'il y a plus de trois lignes. Le total ne porte QUE sur les charges :
  // un revenu récurrent, s'il en existait un, ne doit pas y entrer.
  await ouvrirAgenda(page)
  const dans5 = new Date(Date.now() + 5 * 86_400_000).toISOString().slice(0, 10)
  await creerRecurrence(page, `Somme ${Date.now()}`, '25,00', dans5)

  const echeances = await page.request.get('/api/agenda?jours=60')
  const lignes = (await echeances.json()) as { montant_centimes: number }[]
  const attendu = lignes
    .filter((e) => e.montant_centimes < 0)
    .reduce((s, e) => s + e.montant_centimes, 0)

  const total = page.locator('main').getByText('Charges des 60 prochains jours')
  await expect(total).toBeVisible()

  const euros = Math.trunc(Math.abs(attendu) / 100).toLocaleString('fr-FR')
  await expect(total.locator('..')).toContainText(euros)
})


test('la feuille ne propose que des prélèvements, jamais de revenu', async ({ page }) => {
  // Le calendrier est une page de charges : proposer « Revenu » ici brouillerait la
  // lecture « combien je paie », qui est sa seule raison d'être.
  await ouvrirAgenda(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()

  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Revenu' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Nouveau prélèvement' })).toBeVisible()
})

test('les rythmes sont nommés, pas exprimés en intervalle', async ({ page }) => {
  // « Tous les 3 mois » se choisit d'un coup ; « intervalle 3, unité mois » se traduit
  // mentalement, et une hésitation à la saisie finit en prélèvement mal daté.
  await ouvrirAgenda(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()

  const frequence = page.getByLabel('Fréquence')
  await expect(frequence).toContainText('Tous les mois')
  await expect(frequence).toContainText('Tous les 3 mois')
  await expect(frequence).toContainText('Tous les ans')
})

test('un prélèvement saisi sans signe est enregistré en négatif', async ({ page }) => {
  const libelle = `Charge ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '24,99', new Date(Date.now() + 5 * 86_400_000)
    .toISOString()
    .slice(0, 10))

  const ligne = page.locator('li', { hasText: libelle }).first()
  await expect(ligne).toContainText('−24')
})

test('modifier un prélèvement conserve son rythme à la réouverture', async ({ page }) => {
  // Rouvrir un prélèvement trimestriel en affichant « Tous les mois » le ferait basculer
  // au mensuel dès la première validation — une modification qu'on n'a pas demandée est
  // pire qu'un champ vide.
  const libelle = `Trimestre ${Date.now()}`
  await ouvrirAgenda(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  await page.getByLabel('Montant', { exact: true }).fill('45,00')
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Fréquence').selectOption({ label: 'Tous les 3 mois' })
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.getByRole('button', { name: `Modifier le prélèvement ${libelle}` }).click()
  await expect(page.getByRole('heading', { name: 'Modifier le prélèvement' })).toBeVisible()
  await expect(page.getByLabel('Fréquence')).toHaveValue('trimestriel')
  await expect(page.getByLabel('Montant', { exact: true })).toHaveValue('45,00')
})

test('modifier le montant d’un prélèvement met à jour le calendrier', async ({ page }) => {
  const libelle = `Modif ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(
    page,
    libelle,
    '12,00',
    new Date(Date.now() + 6 * 86_400_000).toISOString().slice(0, 10),
  )

  await page.getByRole('button', { name: `Modifier le prélèvement ${libelle}` }).click()
  await page.getByLabel('Montant', { exact: true }).fill('30,00')
  await page.getByRole('dialog').getByRole('button', { name: 'Modifier', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const ligne = page.locator('li', { hasText: libelle }).first()
  await expect(ligne).toContainText('−30')
})

test('arrêter un prélèvement demande confirmation', async ({ page }) => {
  const libelle = `Arret ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(
    page,
    libelle,
    '9,99',
    new Date(Date.now() + 4 * 86_400_000).toISOString().slice(0, 10),
  )

  await page.getByRole('button', { name: `Arrêter le prélèvement ${libelle}` }).click()
  await expect(page.getByRole('alertdialog')).toBeVisible()
  await expect(page.getByText(libelle).first()).toBeVisible()

  await page.getByRole('alertdialog').getByRole('button', { name: 'Arrêter' }).click()
  await expect(page.getByRole('alertdialog')).toHaveCount(0)
  await expect(
    page.getByRole('button', { name: `Arrêter le prélèvement ${libelle}` }),
  ).toHaveCount(0)
})
