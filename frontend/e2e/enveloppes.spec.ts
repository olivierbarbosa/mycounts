import { expect, test, type Page } from '@playwright/test'

/**
 * Enveloppes, validées à l'écran.
 *
 * Le test central est `réserver ne déplace aucun argent` : c'est la règle qui commande
 * tout le module, et la seule dont une violation ne se verrait pas tout de suite — un
 * utilisateur qui croirait avoir viré de l'argent se retrouverait à découvert sans
 * comprendre pourquoi. La mesure porte donc sur DEUX grandeurs qui doivent bouger en sens
 * opposés (le réservé monte, le non-affecté baisse) pendant qu'une troisième ne bouge pas
 * du tout : le solde réel des comptes.
 *
 * L'écran n'avait aucun test de bout en bout jusqu'au lot B.
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

/** Garantit qu'il y a de l'épargne à découper. Sans livret, toute enveloppe met la
 *  répartition en découvert et l'écran ne dit plus la même chose. */
async function garantirDeLEpargne(page: Page) {
  const comptes = (await (await page.request.get('/api/comptes')).json()) as {
    id: string
    type: string
  }[]
  if (comptes.some((compte) => compte.type === 'epargne')) return

  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Comptes bancaires' }).click()
  await page.getByRole('button', { name: 'Ajouter un compte' }).click()
  await page.getByLabel('Nom du compte').fill(`Livret ${Date.now()}`)
  await page.getByLabel('Type de compte').selectOption('livret_a')
  await page.getByLabel('Solde actuel (facultatif)').fill('5000,00')
  await page.getByRole('button', { name: 'Créer le compte' }).click()
  await expect(page.getByRole('button', { name: 'Ajouter un compte' })).toBeVisible()
  await page.getByRole('button', { name: 'Retour', exact: true }).click()
  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
}

/** Repart d'une répartition vide.
 *
 *  La suite partage sa base : sans ce nettoyage, chaque exécution laissait derrière elle
 *  les enveloppes des précédentes, jusqu'à ce que leur total dépasse l'épargne et mette la
 *  répartition en découvert. Or le total réservé ne compte QUE les soldes positifs — une
 *  enveloppe dans le rouge ne doit pas rogner ce que les autres promettent — si bien que
 *  les écarts mesurés cessaient de correspondre aux montants saisis.
 *
 *  Le symptôme était un test qui passait seul et échouait en groupe, une exécution sur
 *  deux. Un test dont le verdict dépend de ce que d'autres ont laissé ne prouve rien, ni
 *  quand il rougit ni quand il passe. */
async function repartirDeZero(page: Page) {
  const repartition = (await (await page.request.get('/api/enveloppes')).json()) as {
    enveloppes: { id: string }[]
  }
  for (const enveloppe of repartition.enveloppes) {
    await page.request.delete(`/api/enveloppes/${enveloppe.id}`)
  }
}

async function ouvrirEnveloppes(page: Page) {
  await connecter(page)
  await garantirDeLEpargne(page)
  await repartirDeZero(page)
  await page.getByRole('button', { name: 'Enveloppe' }).click()
  await expect(page.getByText('Non affecté')).toBeVisible()
}

/** Ce que le serveur calcule, pour comparer à ce que l'écran montre. */
const lire = async (page: Page) => {
  const repartition = (await (await page.request.get('/api/enveloppes')).json()) as {
    reserve_centimes: number
    non_affecte_centimes: number
  }
  const resume = (await (await page.request.get('/api/resume')).json()) as {
    solde_reel: number
  }
  return { ...repartition, solde_reel: resume.solde_reel }
}

async function creerEnveloppe(page: Page, nom: string, montant: string) {
  await page.getByRole('button', { name: 'Nouvelle enveloppe' }).click()
  await page.getByLabel('Nom de l’enveloppe').fill(nom)
  await page.getByLabel('À réserver maintenant').fill(montant)
  await page.getByRole('button', { name: 'Créer l’enveloppe' }).click()
  await expect(page.getByText(nom)).toBeVisible()
}

test('réserver ne déplace aucun argent', async ({ page }) => {
  await ouvrirEnveloppes(page)
  const avant = await lire(page)

  await creerEnveloppe(page, `Vacances ${Date.now()}`, '200,00')
  const apres = await lire(page)

  // Les deux grandeurs qui doivent bouger, en sens OPPOSÉS.
  expect(apres.reserve_centimes - avant.reserve_centimes).toBe(20_000)
  expect(apres.non_affecte_centimes - avant.non_affecte_centimes).toBe(-20_000)

  // Celle qui ne doit PAS bouger, et c'est tout l'objet du module : l'argent n'a pas
  // quitté les comptes, il a seulement reçu un nom.
  expect(apres.solde_reel, 'réserver a déplacé de l’argent').toBe(avant.solde_reel)
})

test('la création ne demande qu’un nom et une somme', async ({ page }) => {
  // « Le moins d'interactions possible » : catégorie et objectif se remplissent une fois
  // sur trois et allongeaient le formulaire de deux lignes à chaque création.
  await ouvrirEnveloppes(page)
  await page.getByRole('button', { name: 'Nouvelle enveloppe' }).click()

  await expect(page.getByLabel('Nom de l’enveloppe')).toBeVisible()
  await expect(page.getByLabel('À réserver maintenant')).toBeVisible()
  await expect(page.getByLabel('Objectif')).toHaveCount(0)

  await page.getByRole('button', { name: /Catégorie et objectif/ }).click()
  await expect(page.getByLabel('Objectif')).toBeVisible()
})

test('ajuster une enveloppe vers un montant plus élevé alloue la différence', async ({ page }) => {
  const nom = `Ajust ${Date.now()}`
  await ouvrirEnveloppes(page)
  await creerEnveloppe(page, nom, '100,00')

  const ligne = page.locator('li', { hasText: nom }).first()
  await ligne.getByRole('button', { name: `Ajuster l’enveloppe ${nom}` }).click()

  const champ = page.getByLabel(`Montant réservé pour ${nom}`)
  // Pré-rempli : on vient AJUSTER, pas ressaisir de zéro.
  await expect(champ).toHaveValue('100,00')

  const avant = await lire(page)
  await champ.fill('150,00')
  await page.getByRole('button', { name: 'Enregistrer' }).click()

  // Attendre que le formulaire se referme, et non lire l'API dans la foulée du clic :
  // le champ ne disparaît qu'une fois l'écriture ACQUITTÉE. Sans cette attente, le test
  // lisait l'état d'avant une exécution sur deux — une course, pas un défaut du code.
  await expect(champ).toHaveCount(0)

  const apres = await lire(page)
  expect(apres.reserve_centimes - avant.reserve_centimes).toBe(5_000)
  expect(apres.solde_reel, 'un ajustement a déplacé de l’argent').toBe(avant.solde_reel)
})

test('ajuster vers un montant plus BAS reprend la différence', async ({ page }) => {
  // L'autre sens. Sans lui, une implémentation qui n'écrirait que des allocations —
  // en prenant la valeur absolue de l'écart — passerait le test précédent.
  const nom = `Reprise ${Date.now()}`
  await ouvrirEnveloppes(page)
  await creerEnveloppe(page, nom, '300,00')

  const ligne = page.locator('li', { hasText: nom }).first()
  await ligne.getByRole('button', { name: `Ajuster l’enveloppe ${nom}` }).click()

  const avant = await lire(page)
  const champ = page.getByLabel(`Montant réservé pour ${nom}`)
  await champ.fill('120,00')
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(champ).toHaveCount(0)

  const apres = await lire(page)
  expect(apres.reserve_centimes - avant.reserve_centimes).toBe(-18_000)
  expect(apres.non_affecte_centimes - avant.non_affecte_centimes).toBe(18_000)
})

test('le retrait n’est proposé que dans l’édition', async ({ page }) => {
  // C'est l'action la plus rare et la seule irréversible de l'écran : elle occupait une
  // ligne sur chaque enveloppe.
  const nom = `Retrait ${Date.now()}`
  await ouvrirEnveloppes(page)
  await creerEnveloppe(page, nom, '50,00')

  const ligne = page.locator('li', { hasText: nom }).first()
  const supprimer = ligne.getByRole('button', { name: `Supprimer l’enveloppe ${nom}` })
  await expect(supprimer).toHaveCount(0)

  await ligne.getByRole('button', { name: `Ajuster l’enveloppe ${nom}` }).click()
  await supprimer.click()
  await expect(page.locator('li', { hasText: nom })).toHaveCount(0)
})
