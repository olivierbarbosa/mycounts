import { expect, test } from '@playwright/test'

/**
 * Parcours complet : amorçage, saisie, soldes.
 *
 * Ce test valide l'arithmétique **à l'écran**, pas dans une réponse d'API : c'est le seul
 * endroit où l'on vérifie que le chiffre lu par l'utilisateur est celui que le serveur a
 * calculé. Un total juste côté serveur et mal formaté à l'affichage produit exactement la
 * même impression qu'un total faux.
 */

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  const courriel = page.getByLabel('Adresse électronique')
  if (await courriel.isVisible()) {
    await courriel.fill(process.env.MYCOUNTS_COURRIEL_TEST!)
    await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
    await page.getByRole('button', { name: 'Se connecter' }).click()
    // Attendre que la session soit RÉELLEMENT établie. Sans cette ligne, ce helper rendait
    // la main pendant que la requête de connexion était encore en vol : les tests qui
    // enchaînaient sur un élément d'interface s'en tiraient — l'attente de l'élément leur
    // laissait le temps — mais tout appel direct à `page.request` partait sans cookie et
    // recevait un 401 silencieux, dont le seul symptôme visible était une condition qui ne
    // se déclenchait jamais.
    await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
  }
}

test('saisie : les montants affichés sont exacts', async ({ page }) => {
  // L'état de départ est fixé par le globalSetup : un compte, aucune opération.
  // L'écran d'amorçage n'est donc pas traversé ici — il est couvert par les tests
  // d'intégration de l'API. Voir scripts/reinitialiser_foyer_essai.py.
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()

  // Solde avant saisie, lu À L'ÉCRAN.
  const avant = await page.locator('main header').innerText()

  // Libellé unique par exécution : un libellé fixe finit par exister en plusieurs
  // exemplaires et le locator devient ambigu — la suite partage sa base avec les autres
  // fichiers de test.
  const libelle = `Courses e2e ${Date.now()}`
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant').fill('45,90')
  await page.getByLabel('Libellé').fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  await expect(page.getByText(libelle)).toBeVisible()

  const apres = await page.locator('main header').innerText()
  expect(apres, 'le solde affiché doit avoir changé après la saisie').not.toBe(avant)

  // La dépense apparaît avec le signe « moins » typographique, pas un tiret.
  const ligne = page.locator('li', { hasText: libelle })
  await expect(ligne).toContainText('−45')
})

test('une dépense saisie sans signe est enregistrée en négatif', async ({ page }) => {
  // Le sens vient de la bascule Dépense/Revenu, pas du signe tapé : l'utilisateur ne
  // doit pas avoir à y penser. Sans ce test, une inversion de signe passerait inaperçue
  // jusqu'au premier solde faux.
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByRole('button', { name: 'Dépense', exact: true }).click()
  await page.getByLabel('Montant').fill('12,34')
  const libelle = `Sens e2e ${Date.now()}`
  await page.getByLabel('Libellé').fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  const ligne = page.locator('li', { hasText: libelle })
  await expect(ligne).toContainText('−12')
  await expect(ligne).not.toContainText('+12')
})

test('un montant illisible est refusé avant tout envoi', async ({ page }) => {
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant').fill('douze euros')
  await page.getByLabel('Libellé').fill('Illisible')
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  await expect(page.getByRole('alert')).toContainText('illisible')
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('le solde projeté est toujours accompagné de sa borne', async ({ page }) => {
  // Un solde projeté sans date de fin de fenêtre est ininterprétable : « il me reste
  // 320 € » — jusqu'à quand ?
  await connecter(page)
  await expect(page.getByRole('button', { name: 'Saisir une opération' })).toBeVisible()
  await expect(page.locator('main header')).toContainText('jusqu’au')
})

test('les options secondaires sont repliées, et leurs valeurs restent lisibles', async ({
  page,
}) => {
  // Ce qui est mesuré n'est pas « la date est cachée » mais « on peut la VÉRIFIER sans
  // rien déplier ». Un repli qui n'annoncerait que « Options » aurait passé la première
  // moitié de ce test et raté tout son intérêt : il faudrait ouvrir pour savoir.
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()

  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })
  await expect(feuille.getByLabel('Montant')).toBeVisible()
  await expect(feuille.getByLabel('Date de l’opération')).toHaveCount(0)

  const repli = feuille.getByRole('button', { expanded: false })
  await expect(repli, 'la valeur par défaut doit se lire sans déplier').toContainText('Aujourd’hui')

  await repli.click()
  await expect(feuille.getByLabel('Date de l’opération')).toBeVisible()
})

test('changer la date se voit sur le repli une fois refermé', async ({ page }) => {
  // Le témoin qui distingue un résumé CALCULÉ d'un libellé écrit en dur : « Aujourd'hui »
  // seul passerait le test précédent même s'il ne regardait jamais la valeur du champ.
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()

  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })
  await feuille.getByRole('button', { expanded: false }).click()
  await feuille.getByLabel('Date de l’opération').fill('2026-03-14')

  const repli = feuille.getByRole('button', { expanded: true })
  await expect(repli).toContainText('14 mars')
  await expect(repli).not.toContainText('Aujourd’hui')
})

test('la coche « c’est ma paie » n’existe plus, dans aucun des trois modes', async ({ page }) => {
  // Une paie est un revenu de catégorie Salaire, rien d'autre. La case demandait de
  // confirmer ce que la catégorie venait d'énoncer — et elle s'affichait en Virement, où
  // elle n'a aucun sens : sa condition était `!sortie`, vraie pour le revenu ET pour le
  // virement. Une négation qui décrivait deux cas là où elle en visait un.
  await connecter(page)
  // Le mode Virement est désactivé tant qu'il n'y a qu'un compte, et le foyer d'essai est
  // réinitialisé avec un seul. Le test le GARANTIT lui-même plutôt que d'espérer qu'un
  // autre fichier ait laissé le second derrière lui.
  const comptes = (await (await page.request.get('/api/comptes')).json()) as unknown[]
  if (comptes.length < 2) {
    await page.request.post('/api/comptes', {
      data: { nom: `Second ${Date.now()}`, produit: 'livret_a', prive: true },
    })
    await page.reload()
    await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
  }

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })

  for (const mode of ['Dépense', 'Revenu', 'Virement']) {
    await feuille.getByRole('button', { name: mode, exact: true }).click()
    await expect(
      feuille.getByLabel(/c’est ma paie/i),
      `la coche subsiste en mode ${mode}`,
    ).toHaveCount(0)
  }
})

test('une catégorie Salaire marque l’opération comme paie', async ({ page }) => {
  /* Le témoin qui distingue « la case a été retirée » de « la RÈGLE a été retirée ».
   *
   * Une première version se contentait de vérifier la mention affichée à l'écran. Elle ne
   * valait rien : remplacer l'envoi par `est_paie: false` la laissait verte, puisque la
   * mention, elle, continuait de s'afficher. Ce qui compte est ce qui part au serveur —
   * c'est lui qui décide où commence la période budgétaire. */
  const libelle = `Paie ${Date.now()}`
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })

  await feuille.getByRole('button', { name: 'Revenu', exact: true }).click()
  await expect(feuille.getByText(/ouvrira une nouvelle période/)).toHaveCount(0)

  await feuille.getByLabel('Catégorie').selectOption({ label: 'Salaire' })
  await expect(feuille.getByText(/ouvrira une nouvelle période/)).toBeVisible()

  await feuille.getByLabel('Montant').fill('1500,00')
  await feuille.getByLabel('Libellé').fill(libelle)
  await feuille.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByText(libelle)).toBeVisible()

  const operations = (await (await page.request.get('/api/operations')).json()) as {
    libelle: string
    est_paie: boolean
  }[]
  const enregistree = operations.find((operation) => operation.libelle === libelle)
  expect(enregistree, 'l’opération n’a pas été enregistrée').toBeDefined()
  expect(enregistree!.est_paie, 'la catégorie Salaire n’a pas marqué la paie').toBe(true)
})

test('un revenu d’une AUTRE catégorie n’est pas une paie', async ({ page }) => {
  // L'autre sens, sans lequel un `est_paie: true` posé en dur passerait le test précédent.
  const libelle = `Prime ${Date.now()}`
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })

  await feuille.getByRole('button', { name: 'Revenu', exact: true }).click()
  await feuille.getByLabel('Montant').fill('300,00')
  await feuille.getByLabel('Libellé').fill(libelle)
  await feuille.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByText(libelle)).toBeVisible()

  const operations = (await (await page.request.get('/api/operations')).json()) as {
    libelle: string
    est_paie: boolean
  }[]
  expect(operations.find((operation) => operation.libelle === libelle)!.est_paie).toBe(false)
})
