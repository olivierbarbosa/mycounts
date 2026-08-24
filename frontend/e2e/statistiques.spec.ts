import { expect, test, type Page } from '@playwright/test'

/**
 * Statistiques et constats, à l'écran.
 *
 * Le test qui compte est `un virement n'apparaît pas dans les dépenses` : c'est la règle
 * du projet appliquée ici, et la seule dont une violation gonflerait le total d'un montant
 * que l'utilisateur n'a jamais dépensé.
 */

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
}

/** `dispatchEvent` et non `click` : l'écran monte sa coquille sans attendre le réseau et
 *  recouvre la bulle dans la milliseconde, si bien que Playwright refuse de valider un
 *  clic dont l'interception qui suit est justement le résultat attendu. */
async function ouvrirStatistiques(page: Page) {
  await page.getByRole('button', { name: 'Statistiques' }).dispatchEvent('click')
  await expect(page.getByRole('dialog', { name: 'Statistiques' })).toBeVisible()
}

async function saisir(page: Page, libelle: string, montant: string) {
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant').fill(montant)
  await page.getByLabel('Libellé').fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByText(libelle).first()).toBeVisible()
}

test('la bulle Statistiques ouvre l’écran, à gauche du calendrier', async ({ page }) => {
  await connecter(page)

  // La rangée se compte depuis son bord : le calendrier est le plus à droite.
  const stats = page.getByRole('button', { name: 'Statistiques' })
  const calendrier = page.getByRole('button', { name: 'Calendrier' })
  const boiteStats = (await stats.boundingBox())!
  const boiteCalendrier = (await calendrier.boundingBox())!
  expect(boiteStats.x).toBeLessThan(boiteCalendrier.x)

  await ouvrirStatistiques(page)
  await expect(
    page.getByRole('dialog', { name: 'Statistiques' }).getByRole('heading', {
      name: 'Statistiques',
    }),
  ).toBeVisible()
})

test('les dépenses se répartissent par catégorie, sans catégorie comprise', async ({ page }) => {
  const libelle = `Stat ${Date.now()}`
  await connecter(page)
  await saisir(page, libelle, '42,00')

  await ouvrirStatistiques(page)
  const ecran = page.getByRole('dialog', { name: 'Statistiques' })
  await expect(ecran.getByText('Où va l’argent')).toBeVisible()
  // Jamais masqué : c'est souvent la plus grosse ligne, et la cacher fausserait tout.
  await expect(ecran.getByText('Sans catégorie').first()).toBeVisible()
})

test('un virement n’apparaît pas dans les dépenses', async ({ page }) => {
  /* La règle du projet : l'argent n'a pas quitté le foyer. Le compter ferait apparaître
   * une dépense à chaque mise de côté. Deux grandeurs sont lues, et une seule doit bouger. */
  await connecter(page)

  // Un second compte, sans quoi le mode Virement reste désactivé.
  const comptes = (await (await page.request.get('/api/comptes')).json()) as { id: string }[]
  if (comptes.length < 2) {
    await page.request.post('/api/comptes', {
      data: { nom: `Livret ${Date.now()}`, produit: 'livret_a', prive: true },
    })
    await page.reload()
    await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
  }

  const avant = (await (await page.request.get('/api/statistiques')).json()) as {
    total_centimes: number
    nombre_de_depenses: number
  }

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })
  await feuille.getByRole('button', { name: 'Virement', exact: true }).click()
  await feuille.getByLabel('Montant').fill('150,00')
  await feuille.getByLabel('Libellé').fill(`Virement ${Date.now()}`)
  await feuille.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(feuille).toHaveCount(0)

  const apres = (await (await page.request.get('/api/statistiques')).json()) as {
    total_centimes: number
    nombre_de_depenses: number
  }
  expect(apres.total_centimes, 'un virement a été compté comme une dépense').toBe(
    avant.total_centimes,
  )
  expect(apres.nombre_de_depenses).toBe(avant.nombre_de_depenses)
})

test('le goutte-à-goutte se lit avec sa raison, pas comme un reproche', async ({ page }) => {
  // La phrase explique POURQUOI la ligne s'affiche. C'est la seule façon de ne pas la lire
  // comme un jugement — l'écran ne dit jamais qu'une dépense est inutile.
  const libelle = `Cafe ${Date.now()}`
  await connecter(page)
  for (let tour = 0; tour < 3; tour++) await saisir(page, libelle, '25,00')

  await ouvrirStatistiques(page)
  const ecran = page.getByRole('dialog', { name: 'Statistiques' })
  await expect(ecran.getByText('À regarder')).toBeVisible()
  await expect(ecran.getByText(libelle).first()).toBeVisible()
  await expect(ecran.getByText(/3 dépenses ce mois-ci/)).toBeVisible()
  await expect(ecran.getByText('75,00 €').first()).toBeVisible()
})
