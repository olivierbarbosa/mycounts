import { expect, test, type Page } from '@playwright/test'

import { basculerVers, creerCompteDans, foyerDeDemonstration, ouvrirParametres } from './espaces-aide'

import { jourLocal } from './dates'

/**
 * Gestion des comptes, une carte par compte.
 *
 * Le test central est `supprimer un compte qui porte des opérations est refusé` : sans ce
 * refus, ses lignes disparaîtraient des totaux passés et un mois déjà clos changerait de
 * montant. Le refus doit dire pourquoi ET proposer l'archivage — un message qui dirait
 * seulement « impossible » laisserait chercher.
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

async function ouvrirComptes(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Comptes bancaires' }).click()
  await expect(page.getByRole('heading', { name: 'Comptes bancaires' })).toBeVisible()
}

async function fermer(page: Page) {
  await page.getByRole('button', { name: 'Retour', exact: true }).click()
  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Paramètres' })).toHaveCount(0)
}

/** Cartes DU PANNEAU. L'accueil reste monté derrière lui, et ses lignes d'opération
 *  portent le même nom de compte : un `li` non cadré en attrape deux. */
function carte(page: Page, nom: string) {
  return page.getByRole('dialog', { name: 'Paramètres' }).locator('li', { hasText: nom })
}

async function creer(page: Page, nom: string, produit: string, ouverture = '') {
  await page.getByRole('button', { name: 'Ajouter un compte' }).click()
  await page.getByLabel('Nom du compte').fill(nom)
  await page.getByLabel('Type de compte').selectOption(produit)
  if (ouverture !== '') await page.getByLabel('Solde actuel (facultatif)').fill(ouverture)
  await page.getByRole('button', { name: 'Créer le compte' }).click()
  await expect(page.getByRole('button', { name: 'Ajouter un compte' })).toBeVisible()
}

test('une carte porte le nom, le produit et ce qu’il y a dessus', async ({ page }) => {
  const nom = `Livret ${Date.now()}`
  await connecter(page)
  await ouvrirComptes(page)
  await creer(page, nom, 'pel', '1 250,00')

  await expect(carte(page, nom)).toContainText('PEL')
  await expect(carte(page, nom), 'le solde d’ouverture doit apparaître sur la carte').toContainText(
    '250',
  )
  await fermer(page)
})

test('changer le produit d’un compte le déplace vers l’épargne', async ({ page }) => {
  // Le comportement se déduit du produit : c'est le seul moyen de corriger une création
  // faite trop vite, et l'argent ne bouge pas — seul l'écran qui le totalise change.
  const nom = `Corrige ${Date.now()}`
  await connecter(page)
  await ouvrirComptes(page)
  await creer(page, nom, 'compte_courant', '300,00')

  await expect(carte(page, nom)).toContainText('Compte courant')

  await carte(page, nom)
    .getByRole('button', { name: `Modifier ${nom}` })
    .click()
  await page.getByLabel('Type de compte').selectOption('livret_a')
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()

  await expect(carte(page, nom)).toContainText('Livret A')
  await fermer(page)

  // Et l'argent a bien quitté le solde du quotidien pour l'épargne.
  await page.getByRole('button', { name: 'Épargne' }).click()
  await expect(page.locator('main li', { hasText: nom })).toContainText('300')
})

test('supprimer un compte vide', async ({ page }) => {
  const nom = `Jetable ${Date.now()}`
  await connecter(page)
  await ouvrirComptes(page)
  await creer(page, nom, 'compte_courant')

  await carte(page, nom)
    .getByRole('button', { name: `Supprimer ${nom}` })
    .click()
  await carte(page, nom)
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Supprimer', exact: true })
    .click()

  await expect(carte(page, nom)).toHaveCount(0)
  await fermer(page)
})

test('supprimer un compte qui porte des opérations est refusé, et l’archivage proposé', async ({
  page,
}) => {
  const nom = `Utilise ${Date.now()}`
  await connecter(page)
  await ouvrirComptes(page)
  await creer(page, nom, 'compte_courant', '500,00')
  await fermer(page)

  /* Une VRAIE dépense sur ce compte.
   *
   * Ce test exigeait auparavant que le seul solde d'ouverture suffise à bloquer la
   * suppression, au motif qu'il est une opération. Il l'est bien — mais un compte qui ne
   * porte QUE son amorçage n'a jamais servi à clore un mois, et le refuser rendait
   * irréversible la seule erreur qu'on fait vraiment : se tromper en créant un compte.
   * Signalé sur un compte joint, corrigé le 21 août 2026. Ce qu'il faut protéger, ce sont
   * les opérations réelles, et c'est ce que ce test mesure désormais.
   */
  const comptes = (await (await page.request.get('/api/comptes')).json()) as {
    id: string
    nom: string
  }[]
  const cible = comptes.find((compte) => compte.nom === nom)!
  await page.request.post('/api/operations', {
    data: {
      compte_id: cible.id,
      libelle: `Achat ${nom}`,
      montant_centimes: -1_200,
      date_operation: jourLocal(),
    },
  })
  // Le décor passe par l'API, le SUJET par l'écran : ce test porte sur le refus de
  // suppression, pas sur la saisie — qui a ses propres tests.

  await ouvrirComptes(page)
  await carte(page, nom)
    .getByRole('button', { name: `Supprimer ${nom}` })
    .click()
  await carte(page, nom)
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Supprimer', exact: true })
    .click()

  await expect(carte(page, nom).getByRole('alert')).toContainText('opérations')
  await expect(carte(page, nom).getByRole('alert'), 'le refus doit dire quoi faire').toContainText(
    'Archivez',
  )
  await expect(carte(page, nom), 'le compte doit rester').toHaveCount(1)

  /* Archivé, le compte RESTE dans l'écran qui gère les comptes.
   *
   * Ce test attendait auparavant `toHaveCount(0)` — il affirmait le défaut. L'archivage
   * est proposé deux lignes plus haut comme l'alternative douce à une suppression
   * refusée ; le faire disparaître de l'écran même qui vient de le proposer le rendait
   * ni désarchivable ni supprimable. Une action présentée comme réversible était sans
   * retour. C'est le deuxième test de ce fichier à verrouiller un bug en le décrivant
   * comme une intention (ERREURS.md #042 puis #043).
   */
  await carte(page, nom).getByRole('button', { name: 'Archiver' }).click()
  await expect(carte(page, nom)).toContainText('archivé')

  // Et il quitte bien les écrans qui PROPOSENT des comptes : c'est à cela qu'il sert.
  await fermer(page)
  const proposes = (await (await page.request.get('/api/comptes')).json()) as { nom: string }[]
  expect(proposes.map((compte) => compte.nom)).not.toContain(nom)

  // Le chemin du retour existe, et il ramène le compte parmi les propositions.
  await ouvrirComptes(page)
  await carte(page, nom)
    .getByRole('button', { name: `Désarchiver ${nom}` })
    .click()
  await expect(carte(page, nom)).not.toContainText('archivé')
  await fermer(page)
  const revenus = (await (await page.request.get('/api/comptes')).json()) as { nom: string }[]
  expect(revenus.map((compte) => compte.nom)).toContain(nom)
})

test('un compte joint se gère depuis le foyer', async ({ page }) => {
  /* Le sens de ce test a changé le 22 août 2026. Il vérifiait qu'un compte joint était
   * gérable depuis la vue PERSONNELLE, l'écran listant alors les deux mondes. Olivier a
   * tranché l'inverse : chaque monde montre le sien — et depuis les espaces multiples, le
   * monde est l'ESPACE choisi dans le sélecteur. Ce qui reste tenu ici, c'est qu'un
   * compte du foyer est bel et bien gérable — l'écran l'affiche avec son solde, et le
   * supprimer marche.
   */
  const nom = `Joint ${Date.now()}`
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)

  // Le décor passe par l'API : créer un compte joint depuis l'écran a son propre test.
  await creerCompteDans(page, foyer, nom, 1234)
  await basculerVers(page, foyer.nom)

  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Comptes du foyer' }).click()
  await expect(page.getByRole('heading', { name: 'Comptes bancaires' })).toBeVisible()

  await expect(carte(page, nom), 'le foyer montre ses comptes').toHaveCount(1)
  await expect(carte(page, nom), 'et leur solde').toContainText('12')

  await carte(page, nom)
    .getByRole('button', { name: `Supprimer ${nom}` })
    .click()
  await carte(page, nom)
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Supprimer', exact: true })
    .click()
  await expect(carte(page, nom), 'affiché donc supprimable').toHaveCount(0)
  await fermer(page)
})

test('un compte joint se crée depuis le foyer', async ({ page }) => {
  /* Sans cet écran, le foyer resterait vide pour toujours. La case « Compte joint du
   * foyer » a disparu le 22 août 2026 : c'est l'ESPACE qui décide. Un contrôle dont
   * l'usage le plus naturel fait disparaître son résultat ne se corrige pas par un
   * avertissement. */
  const nom = `Commun ${Date.now()}`
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)
  await basculerVers(page, foyer.nom)

  /* Tout est cadré sur le PANNEAU : l'accueil reste monté derrière lui et porte, quand
   * le foyer n'a aucun compte joint, un bouton « Créer un compte joint » du même nom. */
  const panneau = await ouvrirParametres(page)
  await panneau.getByRole('button', { name: 'Comptes du foyer' }).click()
  await expect(panneau.getByRole('heading', { name: 'Comptes bancaires' })).toBeVisible()

  await panneau.getByRole('button', { name: 'Créer un compte joint' }).last().click()
  await panneau.getByLabel('Nom du compte').fill(nom)
  await panneau.getByRole('button', { name: 'Créer le compte' }).click()
  await expect(carte(page, nom), 'créé dans le foyer, visible dans le foyer').toHaveCount(1)

  // Et il appartient bien au foyer, pas à l'espace personnel.
  const personnels = (await (await page.request.get('/api/comptes')).json()) as { nom: string }[]
  expect(personnels.map((compte) => compte.nom)).not.toContain(nom)
  await fermer(page)
})
