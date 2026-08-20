import { expect, test, type Page } from '@playwright/test'

/**
 * Plafonds par catégorie, vus de l'écran.
 *
 * Le test central est `l'à-venir ne s'additionne jamais au consommé` : c'est la mesure qui
 * peut rendre la réponse inverse. Deux grandeurs, dont une qui doit changer — l'alerte
 * apparaît — pendant que l'autre ne bouge pas — le consommé reste ce qui est réellement
 * sorti. Les fondre en un seul « dépensé » annoncerait 110 € partis alors que 50 sont
 * encore à venir, et c'est la confusion qui fait cesser de croire l'outil.
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

async function creerCategorie(page: Page, nom: string) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Catégories' }).click()
  await page.getByLabel('Nom de la nouvelle catégorie').fill(nom)
  await page.getByRole('button', { name: 'Ajouter', exact: true }).click()
  await expect(page.getByLabel(`Nom de la catégorie ${nom}`)).toBeVisible()
  await page.getByRole('button', { name: 'Retour' }).click()
  await page.getByRole('button', { name: 'Fermer' }).click()
  await expect(page.getByRole('dialog', { name: 'Paramètres' })).toHaveCount(0)
}

async function saisirDepense(page: Page, libelle: string, montant: string, categorie: string) {
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant', { exact: true }).fill(montant)
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Catégorie').selectOption({ label: categorie })
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}

async function ouvrirBudgets(page: Page) {
  // Le libellé du lien change selon qu'il existe déjà un plafond ou non : « Gérer » quand
  // il y en a, « Fixer un plafond » quand le bloc est vide. Les deux mènent au même écran.
  await page.getByRole('button', { name: /Gérer|Fixer un plafond/ }).click()
  await expect(page.getByRole('dialog', { name: 'Budgets' })).toBeVisible()
}

test('l’à-venir ne s’additionne jamais au consommé', async ({ page }) => {
  const categorie = `Budget ${Date.now()}`
  await connecter(page)
  await creerCategorie(page, categorie)
  await saisirDepense(page, `Achat ${Date.now()}`, '60,00', categorie)

  // Le plafond se fixe par l'API : l'écran des budgets n'est atteignable que lorsqu'au
  // moins un plafond existe, et ce test porte sur ce qu'il AFFICHE, pas sur sa création.
  const categories = (await (await page.request.get('/api/categories')).json()) as {
    id: string
    nom: string
  }[]
  const cible = categories.find((c) => c.nom === categorie)!
  await page.request.put('/api/plafonds', {
    data: { categorie_id: cible.id, montant_centimes: 10_000 },
  })
  await page.reload()

  // La jauge porte une étiquette d'accessibilité qui commence par le nom de la catégorie :
  // c'est le seul repère non ambigu, le nom apparaissant aussi dans la liste des
  // opérations. Remonter d'un cran donne la carte entière.
  const carte = (nom: string) =>
    page.getByRole('img', { name: new RegExp(`^${nom} :`) }).locator('..')
  const bloc = carte(categorie)
  await expect(bloc).toContainText('60')
  await expect(bloc).toContainText('100')
  await expect(bloc, 'aucune alerte tant que rien n’est prévu').not.toContainText('Sera dépassé')

  // Un prélèvement de 50 € dans la même catégorie, avant la fin de la période.
  const resume = (await (await page.request.get('/api/resume')).json()) as {
    periode: { fin: string }
  }
  const demain = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)
  const echeance = demain <= resume.periode.fin ? demain : resume.periode.fin
  const comptes = (await (await page.request.get('/api/comptes')).json()) as { id: string }[]
  await page.request.post('/api/recurrences', {
    data: {
      compte_id: comptes[0].id,
      libelle: `Prel ${categorie}`,
      montant_centimes: -5_000,
      ancre: echeance,
      unite: 'mois',
      categorie_id: cible.id,
    },
  })
  await page.reload()

  const apres = carte(categorie)
  // Ce qui DOIT changer : l'alerte apparaît.
  await expect(apres).toContainText('Sera dépassé')
  // Ce qui ne doit PAS changer : le consommé reste ce qui est réellement sorti.
  await expect(apres).toContainText('60')
  await expect(apres, 'consommé et à-venir fondus en un seul total').not.toContainText('110')
})

test('un plafond se fixe et se retire depuis l’écran des budgets', async ({ page }) => {
  const categorie = `Fixer ${Date.now()}`
  await connecter(page)
  await creerCategorie(page, categorie)

  // Il faut un plafond existant pour que le bloc « Budgets » — et donc « Gérer » —
  // apparaisse sur l'accueil. Les tests précédents en ont laissé.
  await ouvrirBudgets(page)

  await page.getByLabel('Catégorie à plafonner').selectOption({ label: categorie })
  await page.getByLabel('Montant du plafond').fill('250,00')
  await page.getByRole('button', { name: 'Fixer' }).click()

  const ligne = page.locator('li', { hasText: categorie })
  await expect(ligne).toContainText('250')

  await ligne.getByRole('button', { name: `Retirer le plafond de ${categorie}` }).click()
  await expect(page.locator('li', { hasText: categorie })).toHaveCount(0)
})

test('un plafond négatif est refusé avant tout envoi', async ({ page }) => {
  // Un plafond est une limite : accepter un négatif produirait une jauge pleine dès le
  // premier euro, sans que rien ne dise pourquoi.
  const categorie = `Negatif ${Date.now()}`
  await connecter(page)
  await creerCategorie(page, categorie)
  await ouvrirBudgets(page)

  await page.getByLabel('Catégorie à plafonner').selectOption({ label: categorie })
  await page.getByLabel('Montant du plafond').fill('-50,00')
  await page.getByRole('button', { name: 'Fixer' }).click()

  await expect(page.getByRole('alert')).toContainText('limite')
  await expect(page.locator('li', { hasText: categorie })).toHaveCount(0)
})

test('l’écran des budgets reste atteignable sans aucun plafond', async ({ page }) => {
  // Le bloc ne s'affichait qu'une fois un plafond posé : la seule porte vers l'écran qui
  // permet d'en poser un ne s'ouvrait donc qu'à ceux qui en avaient déjà. Une fonction
  // livrée que personne ne pouvait atteindre.
  await connecter(page)

  // On retire tous les plafonds pour retrouver l'état d'un foyer qui n'en a jamais eu.
  const plafonds = (await (await page.request.get('/api/plafonds')).json()) as { id: string }[]
  for (const plafond of plafonds) await page.request.delete(`/api/plafonds/${plafond.id}`)
  await page.reload()

  const bloc = page.getByRole('heading', { name: 'Budgets' }).locator('..')
  await expect(bloc, 'un bloc vide doit proposer l’action').toContainText('Fixer un plafond')

  await page.getByRole('button', { name: 'Fixer un plafond' }).click()
  await expect(page.getByRole('dialog', { name: 'Budgets' })).toBeVisible()
})
