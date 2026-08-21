import { expect, test, type Page } from '@playwright/test'

/**
 * Correction du solde depuis l'accueil.
 *
 * Un solde est une SOMME d'opérations, jamais une valeur qu'on écrit : la correction
 * devient une opération de plus, qui porte l'écart. Le test central vérifie qu'elle
 * n'entre pas dans les dépenses — réparer une erreur de saisie de 20 € n'est pas avoir
 * dépensé 20 €, et l'y compter ferait sauter un plafond pour une erreur qu'on vient
 * précisément de réparer.
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

const lire = async (page: Page) =>
  (await (await page.request.get('/api/resume')).json()) as {
    solde_reel: number
    depenses_de_periode: number
  }

test('corriger le solde depuis l’accueil ne crée pas de dépense', async ({ page }) => {
  await connecter(page)
  const avant = await lire(page)
  const vise = avant.solde_reel - 4_321

  await page.getByRole('button', { name: 'Corriger le solde réel' }).click()
  await expect(page.getByRole('dialog', { name: 'Corriger le solde' })).toBeVisible()

  // Le premier compte de la liste est celui que l'accueil totalise : le foyer d'essai
  // n'en a qu'un de courant.
  await page.getByLabel('Solde affiché par votre banque').fill(String(vise / 100).replace('.', ','))
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const apres = await lire(page)
  expect(apres.solde_reel, 'le solde doit rejoindre la valeur saisie').toBe(vise)
  expect(
    apres.depenses_de_periode,
    'un ajustement compté en dépense ferait sauter les plafonds',
  ).toBe(avant.depenses_de_periode)
})

test('l’écart est TRACÉ, même s’il ne figure plus dans le journal', async ({ page }) => {
  /* Ce test a changé de sujet le 22 août 2026, sans rien perdre de son intention.
   *
   * Il vérifiait que « Ajustement de solde » s'affichait sur l'accueil, au motif qu'une
   * correction invisible serait une valeur posée d'autorité. Olivier a demandé que les
   * ajustements quittent la liste des dépenses récentes — voir « −13,40 € » sous ce titre
   * fait chercher un achat qui n'existe pas.
   *
   * L'intention d'origine tient toujours, et c'est elle qui est mesurée ici : la ligne
   * EXISTE, datée et libellée. Ce qui a changé, c'est l'endroit où on la lit.
   *
   * Ce que ce déplacement COÛTE, et qui est assumé : l'accueil étant le seul écran qui
   * liste les opérations, un ajustement n'est plus consultable depuis l'interface. Il
   * reste corrigeable — en refaire un ramène le solde à la valeur voulue, l'écart étant
   * recalculé par le serveur à chaque fois.
   */
  await connecter(page)
  const avant = await lire(page)

  await page.getByRole('button', { name: 'Corriger le solde réel' }).click()
  const vise = avant.solde_reel + 1_500
  await page.getByLabel('Solde affiché par votre banque').fill(String(vise / 100).replace('.', ','))
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const operations = (await (await page.request.get('/api/operations')).json()) as {
    libelle: string
    est_ajustement: boolean
  }[]
  const trace = operations.filter((operation) => operation.est_ajustement)
  expect(trace.length, 'la correction doit laisser une trace').toBeGreaterThan(0)

  // Et elle ne se lit plus parmi les achats.
  await expect(page.locator('main')).not.toContainText('Ajustement de solde')
})

test('corriger vers le solde déjà affiché ne fait rien', async ({ page }) => {
  // Écrire un ajustement de zéro remplirait l'historique de lignes qui ne disent rien.
  await connecter(page)
  const avant = await lire(page)
  const lignes = await (await page.request.get('/api/operations?periode_courante=false')).json()

  await page.getByRole('button', { name: 'Corriger le solde réel' }).click()
  await page
    .getByLabel('Solde affiché par votre banque')
    .fill(String(avant.solde_reel / 100).replace('.', ','))
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const apres = await (await page.request.get('/api/operations?periode_courante=false')).json()
  expect(apres.length, 'aucune ligne ne doit être ajoutée').toBe(lignes.length)
})

test('un ajustement n’apparaît pas dans le journal des dépenses', async ({ page }) => {
  /* Demandé par Olivier le 22 août 2026 : voir « −13,40 € » sous « Dépenses récentes »
   * fait chercher un achat qui n'existe pas.
   *
   * Les DEUX moitiés comptent, et la seconde davantage : l'ajustement disparaît de la
   * liste mais continue de compter dans le solde réel. Ne vérifier que la disparition
   * laisserait passer un code qui l'aurait purement et simplement cessé d'écrire — ce qui
   * ferait diverger l'application de la banque, exactement l'inverse du but.
   */
  await connecter(page)
  const comptes = (await (await page.request.get('/api/comptes')).json()) as { id: string }[]

  const avant = await lire(page)
  const vise = avant.solde_reel - 1_340
  const fait = await page.request.post(`/api/comptes/${comptes[0].id}/ajustement`, {
    data: { solde_reel_centimes: vise },
  })
  expect(fait.status(), await fait.text()).toBe(200)
  await page.reload()

  // Ce qui DOIT changer : le solde suit la banque.
  const apres = await lire(page)
  expect(apres.solde_reel, 'l’ajustement doit compter dans le solde').toBe(vise)

  // Ce qui ne doit PAS apparaître : la ligne, dans le journal de ce qu'on a acheté.
  await expect(
    page.locator('main'),
    'un ajustement n’est pas une dépense',
  ).not.toContainText('Ajustement de solde')
})
