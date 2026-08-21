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

test('un compte joint se crée depuis la VUE joints', async ({ page }) => {
  /* Sans cet écran, la vue foyer resterait vide pour toujours : aucun compte joint
   * n'était créable, `prive: true` étant écrit en dur.
   *
   * La case « Compte joint du foyer » a disparu le 22 août 2026 : c'est la VUE qui décide.
   * Depuis que l'écran ne liste que le périmètre courant, une case libre permettait de
   * créer, en vue joints, un compte personnel qui s'évaporait de la liste où on venait
   * de le créer. Un contrôle dont l'usage le plus naturel fait disparaître son résultat
   * ne se corrige pas par un avertissement.
   */
  const nom = `Commun ${Date.now()}`
  await connecter(page)
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page
    .getByRole('group', { name: 'Périmètre' })
    .getByRole('button', { name: 'Comptes joints' })
    .click()

  /* Tout est cadré sur le PANNEAU : l'accueil reste monté derrière lui et porte, quand
   * le foyer n'a aucun compte joint, un bouton « Créer un compte joint » du même nom. Un
   * sélecteur global attrape celui-là, que le panneau recouvre — le clic part alors sur
   * un élément intercepté et le test expire sans rien dire d'utile. */
  const panneau = page.getByRole('dialog', { name: 'Paramètres' })

  /* Deux chemins mènent à l'écran des comptes, selon ce que le foyer contient déjà :
   * l'invitation quand il est vide, la rubrique sinon. Le test accepte les deux — l'ordre
   * d'exécution des fichiers ne dit pas lequel s'appliquera, et un test qui n'en
   * connaîtrait qu'un échouerait selon son rang, la pire forme d'échec : intermittente. */
  const rubrique = panneau.getByRole('button', { name: 'Comptes du foyer' })
  const invitation = panneau.getByRole('button', { name: 'Créer un compte joint' })

  /* On ATTEND que l'un des deux existe avant de choisir. `isVisible()` répond tout de
     suite, sans attendre : interrogé pendant que la bascule recharge, il dit « non » sur
     les deux et le test part sur une branche qui n'apparaîtra jamais. Une question posée
     trop tôt reçoit une réponse fausse, pas une erreur. */
  await expect(rubrique.or(invitation).first()).toBeVisible()
  if (await rubrique.isVisible()) await rubrique.click()
  else await invitation.click()
  await expect(panneau.getByRole('heading', { name: 'Comptes bancaires' })).toBeVisible()

  /* `.last()` : le sous-écran est POSÉ sur la racine du panneau, qui reste montée —
     l'invitation des paramètres est donc encore dans le DOM, avec le même libellé. Le
     dernier des deux est celui de l'écran qu'on regarde. */
  await panneau
    .getByRole('button', { name: /Créer un compte joint|Ajouter un compte/ })
    .last()
    .click()
  await panneau.getByLabel('Nom du compte').fill(nom)
  await expect(panneau.getByText(/Ce compte sera JOINT/)).toBeVisible()
  await panneau.getByRole('button', { name: 'Créer le compte' }).click()

  /* On attend le RÉSULTAT, pas le titre de l'écran : celui-ci reste affiché pendant que
     le formulaire est ouvert, si bien que l'attendre passait immédiatement et le test
     interrogeait l'API avant que la création n'ait abouti. Une attente qui est déjà
     satisfaite au moment où on la pose ne synchronise rien. */
  await expect(panneau.getByText(nom)).toBeVisible()

  const joints = (await (
    await page.request.get('/api/comptes', {
      headers: { 'X-Mycounts-Vue': 'foyer' },
    })
  ).json()) as { nom: string }[]
  expect(joints.map((compte) => compte.nom)).toContain(nom)
})
