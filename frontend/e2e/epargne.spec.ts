import { expect, test, type Page } from '@playwright/test'

/**
 * Virements et page Épargne, validés à l'écran.
 *
 * Le test central est `virer vers l'épargne ne crée aucune dépense` : c'est la mesure qui
 * peut rendre la réponse inverse. Deux grandeurs doivent bouger en sens OPPOSÉS — le
 * solde du quotidien baisse, l'épargne monte — pendant qu'une troisième ne bouge pas du
 * tout. Si « dépensé sur la période » suivait, mettre de l'argent de côté ferait sauter
 * tous les plafonds du mois.
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

/** Crée un compte d'épargne depuis les Réglages, comme le ferait l'utilisateur. */
async function creerEpargne(page: Page, nom: string, ouverture: string) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Comptes bancaires' }).click()
  await page.getByRole('button', { name: 'Ajouter un compte' }).click()
  await page.getByLabel('Nom du compte').fill(nom)
  // Le PRODUIT, pas le comportement : c'est le catalogue qui traduit « Livret A » en
  // « mis de côté ». Le test suit le même chemin que l'utilisateur.
  await page.getByLabel('Type de compte').selectOption('livret_a')
  await page.getByLabel('Solde actuel (facultatif)').fill(ouverture)
  await page.getByRole('button', { name: 'Créer le compte' }).click()
  await expect(page.getByRole('button', { name: 'Ajouter un compte' })).toBeVisible()
  await page.getByRole('button', { name: 'Retour', exact: true }).click()
  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
}

test('la page Épargne n’est jamais muette', async ({ page }) => {
  // Une page vide qui n'explique pas comment la remplir est une impasse ; une page pleine
  // qui prétendrait être vide serait pire.
  //
  // L'emptiness ne peut pas être garantie ici : la suite partage une base, et tout fichier
  // qui passe avant celui-ci peut créer un livret — `comptes.spec.ts` le fait. Plutôt que
  // de dépendre d'un ordre alphabétique qui a déjà cassé ce test trois fois, on vérifie
  // l'invariant dans les deux états.
  await connecter(page)

  // L'état attendu se lit par l'API, pas en comptant des éléments d'un DOM encore en
  // cours de rendu : la première version lisait zéro pendant le chargement et exigeait
  // alors le message de page vide sur une page qui allait afficher deux livrets.
  const epargne = (await (await page.request.get('/api/epargne')).json()) as {
    comptes: unknown[]
  }

  await page.getByRole('button', { name: 'Épargne' }).click()
  const principal = page.locator('main')
  await expect(principal).toContainText('Épargne totale')

  if (epargne.comptes.length === 0) {
    await expect(principal).toContainText('Aucun compte d’épargne')
  } else {
    await expect(
      principal,
      'des livrets sont affichés : la page ne peut pas dire qu’il n’y en a aucun',
    ).not.toContainText('Aucun compte d’épargne')
  }
})

test('virer vers l’épargne ne crée aucune dépense', async ({ page }) => {
  await connecter(page)
  const livret = `Livret ${Date.now()}`
  await creerEpargne(page, livret, '0')

  // Les grandeurs se lisent par l'API, pas en comparant des chaînes d'en-tête : le texte
  // entier change dès qu'une autre échéance se matérialise, et le test échouait alors
  // pour une raison étrangère à ce qu'il vérifie. Le geste, lui, reste celui de
  // l'utilisateur — le virement passe par la feuille de saisie.
  const lire = async () => {
    const resume = (await (await page.request.get('/api/resume')).json()) as {
      solde_projete: number
      depenses_de_periode: number
    }
    const epargne = (await (await page.request.get('/api/epargne')).json()) as {
      total_centimes: number
    }
    return { ...resume, epargne: epargne.total_centimes }
  }

  const avant = await lire()

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByRole('button', { name: 'Virement', exact: true }).click()
  await page.getByLabel('Montant', { exact: true }).fill('200,00')
  await page.getByLabel('Libellé', { exact: true }).fill('Mise de côté')
  // La destination se choisit par SON NOM. Un index supposait l'ordre et le nombre des
  // comptes, deux choses que les autres tests font varier — le virement partait alors
  // vers un compte au hasard et le livret restait à zéro.
  await page.getByLabel('Vers le compte').selectOption({ label: livret })
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  const apres = await lire()

  // Celle qui ne doit PAS bouger. C'est tout l'enjeu.
  expect(
    apres.depenses_de_periode,
    'un virement compté en dépense ferait sauter les plafonds',
  ).toBe(avant.depenses_de_periode)

  // Celles qui bougent, en sens contraires et du même montant.
  expect(apres.solde_projete - avant.solde_projete).toBe(-20_000)
  expect(apres.epargne - avant.epargne).toBe(20_000)

  await page.getByRole('button', { name: 'Épargne' }).click()
  // L'assertion porte sur la LIGNE du livret et non sur le total : la suite partage sa
  // base, et un total absolu dépendrait des livrets créés par les autres tests.
  await expect(page.locator('li', { hasText: livret })).toContainText('200')
})

test('l’épargne ne gonfle pas le solde du quotidien', async ({ page }) => {
  // Créer un livret avec de l'argent dessus ne doit rien changer à l'accueil : sinon
  // l'écran annoncerait une aisance qui n'existe pas.
  await connecter(page)

  // Grandeurs exactes, pas comparaison de texte : l'en-tête entier change dès qu'une
  // échéance sans rapport se matérialise entre les deux lectures, et le test échouait
  // alors pour une raison étrangère à ce qu'il vérifie.
  const soldeCourant = async () =>
    ((await (await page.request.get('/api/resume')).json()) as { solde_reel: number }).solde_reel

  const avant = await soldeCourant()

  const livret = `Livret bis ${Date.now()}`
  await creerEpargne(page, livret, '500,00')

  expect(await soldeCourant(), 'un livret ne doit rien ajouter au solde du quotidien').toBe(avant)

  await page.getByRole('button', { name: 'Épargne' }).click()
  await expect(page.locator('main li', { hasText: livret })).toContainText('500')
})

test('virer depuis l’Épargne ne propose ni dépense ni revenu', async ({ page }) => {
  // Depuis un écran d'épargne, « Dépense » et « Revenu » sont deux options hors sujet dans
  // une bascule à trois positions : elles coûtent une lecture à chaque ouverture.
  await connecter(page)
  await page.getByRole('button', { name: 'Épargne' }).click()
  await page.getByRole('button', { name: 'Virer de l’argent' }).click()

  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })
  await expect(feuille.getByRole('heading', { name: 'Virement' })).toBeVisible()
  await expect(feuille.getByRole('button', { name: 'Dépense', exact: true })).toHaveCount(0)
  await expect(feuille.getByRole('button', { name: 'Revenu', exact: true })).toHaveCount(0)

  // Le formulaire est bien celui d'un virement : deux comptes, aucune catégorie.
  await expect(feuille.getByLabel('Du compte')).toBeVisible()
  await expect(feuille.getByLabel('Vers le compte')).toBeVisible()
})

test('le + de la barre rend la bascule après un passage par l’Épargne', async ({ page }) => {
  // Le sens imposé est un état de l'application, pas de la feuille : sans remise à zéro à
  // chaque ouverture, le `+` de la barre resterait verrouillé sur Virement pour le reste
  // de la session. C'est le témoin qui distingue « imposé quand il faut » de « imposé ».
  await connecter(page)
  await page.getByRole('button', { name: 'Épargne' }).click()
  await page.getByRole('button', { name: 'Virer de l’argent' }).click()
  await page
    .getByRole('dialog', { name: 'Saisir une opération' })
    .getByRole('button', { name: 'Annuler', exact: true })
    .click()

  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  const feuille = page.getByRole('dialog', { name: 'Saisir une opération' })
  await expect(feuille.getByRole('button', { name: 'Dépense', exact: true })).toBeVisible()
})
