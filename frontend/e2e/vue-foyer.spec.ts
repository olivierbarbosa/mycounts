import { expect, test, type Page } from '@playwright/test'

/**
 * Bascule entre son argent et celui du foyer.
 *
 * Deux mondes ÉTANCHES, décidé par Olivier le 21 août 2026 : on répond à « combien j'ai »
 * ou à « combien on a », jamais aux deux mélangés.
 *
 * Le test central est `un compte joint n'apparaît pas dans la vue personnelle` et son
 * pendant : c'est l'étanchéité qui donne son sens à la bascule, et une fuite dans un sens
 * ou dans l'autre la rendrait inutile — voire indiscrète.
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
  await expect(page.getByRole('group', { name: 'Périmètre' })).toBeVisible()
}

async function basculerVers(page: Page, libelle: 'Compte personnel' | 'Comptes joints') {
  await ouvrirParametres(page)
  await page
    .getByRole('group', { name: 'Périmètre' })
    .getByRole('button', { name: libelle })
    .click()
  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
}

/** Crée un compte par l'API, joint ou personnel. Le nom porte une marque unique : la base
 *  est partagée entre tous les fichiers de test. */
async function creerCompte(page: Page, nom: string, joint: boolean) {
  const reponse = await page.request.post('/api/comptes', {
    data: { nom, prive: !joint, produit: 'compte_courant' },
  })
  expect(reponse.status(), await reponse.text()).toBe(201)
}

test('la bascule existe et dit ce que chaque vue EXCLUT', async ({ page }) => {
  // C'est l'absence qui surprend, jamais la présence : quelqu'un qui ne retrouve pas son
  // livret doit comprendre pourquoi sans avoir à chercher.
  await connecter(page)
  await ouvrirParametres(page)

  await expect(page.getByText(/Les comptes joints n’y figurent pas/)).toBeVisible()
  await page
    .getByRole('group', { name: 'Périmètre' })
    .getByRole('button', { name: 'Comptes joints' })
    .click()
  await expect(page.getByText(/Vos comptes personnels n’y figurent pas/)).toBeVisible()

  // Remettre la vue personnelle : les autres tests partagent ce navigateur.
  await page
    .getByRole('group', { name: 'Périmètre' })
    .getByRole('button', { name: 'Compte personnel' })
    .click()
})

test('un compte joint n’apparaît PAS dans la vue personnelle', async ({ page }) => {
  const marque = Date.now()
  await connecter(page)
  await creerCompte(page, `Joint ${marque}`, true)
  await creerCompte(page, `Perso ${marque}`, false)

  await basculerVers(page, 'Compte personnel')
  const comptes = (await (await page.request.get('/api/comptes')).json()) as { nom: string }[]
  const noms = comptes.map((compte) => compte.nom)
  expect(noms).toContain(`Perso ${marque}`)
  expect(noms, 'un compte joint fuit dans la vue personnelle').not.toContain(`Joint ${marque}`)
})

test('un compte personnel n’apparaît PAS dans la vue foyer', async ({ page }) => {
  /* L'étanchéité dans l'autre sens, et c'est celui qui protège : les opérations
   * personnelles ne doivent pas apparaître dans un écran que le conjoint regarde. */
  const marque = Date.now()
  await connecter(page)
  await creerCompte(page, `Joint ${marque}`, true)
  await creerCompte(page, `Perso ${marque}`, false)

  await basculerVers(page, 'Comptes joints')
  const comptes = (await (
    await page.request.get('/api/comptes', {
      headers: { 'X-Mycounts-Vue': 'foyer' },
    })
  ).json()) as { nom: string }[]
  const noms = comptes.map((compte) => compte.nom)
  expect(noms).toContain(`Joint ${marque}`)
  expect(noms, 'un compte personnel fuit dans la vue foyer').not.toContain(`Perso ${marque}`)

  await basculerVers(page, 'Compte personnel')
})

test('le solde de l’accueil change avec la vue', async ({ page }) => {
  /* Ce que la bascule doit produire pour valoir quelque chose : deux réponses différentes
   * à « combien ». Un écran qui afficherait le même total dans les deux vues signalerait
   * que le périmètre n'a pas suivi. */
  const marque = Date.now()
  await connecter(page)

  const joint = await page.request.post('/api/comptes', {
    data: {
      nom: `Joint solde ${marque}`,
      prive: false,
      produit: 'compte_courant',
      solde_ouverture_centimes: 123_400,
    },
  })
  expect(joint.status()).toBe(201)

  await basculerVers(page, 'Comptes joints')
  const enFoyer = (await (
    await page.request.get('/api/resume', {
      headers: { 'X-Mycounts-Vue': 'foyer' },
    })
  ).json()) as { solde_reel: number }
  const enPerso = (await (await page.request.get('/api/resume')).json()) as {
    solde_reel: number
  }

  expect(enFoyer.solde_reel).not.toBe(enPerso.solde_reel)
  await basculerVers(page, 'Compte personnel')
})

test('un en-tête de vue inconnu ne donne accès à rien de plus', async ({ page }) => {
  // Le défaut de sûreté : au pire on montre à quelqu'un ses propres comptes.
  const marque = Date.now()
  await connecter(page)
  await creerCompte(page, `Joint garde ${marque}`, true)

  const comptes = (await (
    await page.request.get('/api/comptes', {
      headers: { 'X-Mycounts-Vue': 'nimportequoi' },
    })
  ).json()) as { nom: string }[]
  expect(comptes.map((compte) => compte.nom)).not.toContain(`Joint garde ${marque}`)
})

test('un compte joint se crée depuis l’écran des comptes', async ({ page }) => {
  // Sans cet écran, la vue foyer resterait vide pour toujours : aucun compte joint
  // n'était créable, `prive: true` étant écrit en dur.
  const nom = `Commun ${Date.now()}`
  await connecter(page)
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Comptes bancaires' }).click()
  await page.getByRole('button', { name: 'Ajouter un compte' }).click()

  await page.getByLabel('Nom du compte').fill(nom)
  await page.getByLabel('Compte joint du foyer').check()
  await expect(page.getByText(/Visible par tous les membres du foyer/)).toBeVisible()
  await page.getByRole('button', { name: 'Créer le compte' }).click()
  await expect(page.getByRole('button', { name: 'Ajouter un compte' })).toBeVisible()

  const joints = (await (
    await page.request.get('/api/comptes', {
      headers: { 'X-Mycounts-Vue': 'foyer' },
    })
  ).json()) as { nom: string }[]
  expect(joints.map((compte) => compte.nom)).toContain(nom)
})
