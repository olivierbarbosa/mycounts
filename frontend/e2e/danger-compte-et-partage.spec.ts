import { expect, test, type Page } from '@playwright/test'

import { basculerVers, foyerDeDemonstration, ouvrirParametres } from './espaces-aide'

/**
 * Les deux zones de danger, et le fait qu'elles soient DEUX.
 *
 * Le test central est `arrêter de partager et disparaître sont deux écrans` : c'est la
 * correction du 21 août 2026. Un seul bouton « Supprimer le foyer » faisait les deux, si
 * bien qu'Olivier perdait son compte et sa session en voulant seulement cesser de
 * partager — le foyer étant, en base, le conteneur racine de ses comptes personnels
 * (ERREURS.md #044). Les refondre en une seule zone ferait revenir le défaut sans qu'aucun
 * autre test ne s'en aperçoive.
 *
 * Ce fichier ne va JAMAIS jusqu'au bout, ni pour l'une ni pour l'autre :
 * — « Tout effacer » détruirait le compte de démonstration et les autres tests avec lui ;
 * — « Supprimer définitivement » le foyer emporterait celui que `foyer-espace.spec.ts`
 *   utilise, et les tests partagent un même foyer : sa disparition déplacerait le sol
 *   sous les autres exactement comme une paie mal placée le ferait.
 * Ce que ces deux actions font réellement est prouvé côté intégration, contre une base
 * jetable, dans `test_suppression_foyer.py` et `test_espaces_multiples.py`.
 *
 * Depuis les espaces multiples (24 août 2026), « arrêter de partager » vit dans la
 * rubrique « Foyer » d'un espace foyer — quitter, ou supprimer le foyer — et « disparaître »
 * dans « Mon compte », qui n'existe que dans l'espace personnel. La capsule « Périmètre »
 * des paramètres n'existe plus : c'est le sélecteur d'espace qui choisit le monde.
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

async function ouvrirFoyer(page: Page) {
  // « Foyer » ne vit que dans un espace foyer : c'est le monde qu'il décrit.
  const foyer = await foyerDeDemonstration(page)
  await basculerVers(page, foyer.nom)
  const panneau = await ouvrirParametres(page)
  await panneau.getByRole('button', { name: 'Foyer', exact: true }).click()
  // « Partage » quand on est seul, « Membres » dès qu'on est plusieurs : le titre dit
  // lequel des deux est vrai, et le helper accepte les deux pour ne pas présumer.
  await expect(
    panneau
      .getByRole('heading', { name: 'Partage', exact: true })
      .or(panneau.getByRole('heading', { name: 'Membres', exact: true })),
  ).toBeVisible()
  return panneau
}

async function ouvrirMonCompte(page: Page) {
  // « Mon compte » ne vit que dans l'espace personnel : c'est son identité, pas le foyer.
  await basculerVers(page, 'Moi')
  const panneau = await ouvrirParametres(page)
  await panneau.getByRole('button', { name: 'Mon compte' }).click()
  await expect(panneau.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
  return panneau
}

test('la liste des membres s’affiche au lieu de charger sans fin', async ({ page }) => {
  /* Le bug d'Olivier, dans le sens où il s'est produit : le client demandait
   * `/foyer/membres` quand la route est `/auth/foyer/membres`, et l'écran affichait
   * « Chargement… » pour toujours — parce qu'une liste vide et une liste pas encore
   * arrivée y étaient le même état.
   *
   * Ce test rougit aussi bien si le chemin casse que si les deux états refusionnent. */
  await connecter(page)
  const panneau = await ouvrirFoyer(page)

  /* Ce que ce test mesure est l'ARRIVÉE d'un état, quel qu'il soit : la liste des
     membres quand on est plusieurs, la phrase « pas encore partagé » quand on est seul.
     Ce qu'il refuse, c'est le troisième — « Chargement… » qui ne finit jamais. */
  await expect(panneau.getByText('Chargement…')).toHaveCount(0)
  await expect(
    panneau
      .getByText(/n’avez encore partagé avec personne/)
      .or(panneau.getByRole('listitem'))
      .first(),
  ).toBeVisible()
})

test('arrêter de partager et disparaître sont deux écrans', async ({ page }) => {
  /* La séparation elle-même, mesurée dans les deux sens : chaque écran porte SON action
   * et pas celle de l'autre. Une assertion sur la seule présence des deux boutons
   * passerait encore s'ils étaient tous deux revenus sur l'écran du foyer. */
  await connecter(page)
  const foyer = await ouvrirFoyer(page)
  await expect(foyer.getByRole('heading', { name: 'Supprimer le foyer' })).toBeVisible()
  await expect(
    foyer.getByRole('heading', { name: 'Supprimer mon compte' }),
    'effacer son compte n’a rien à faire sur l’écran du foyer',
  ).toHaveCount(0)
  // Retour à la racine du panneau, puis fermeture : « Fermer » ne vit qu'à la racine.
  await foyer.getByRole('button', { name: 'Retour', exact: true }).click()
  await foyer.getByRole('button', { name: 'Fermer', exact: true }).click()

  const compte = await ouvrirMonCompte(page)
  await expect(
    compte.getByRole('heading', { name: 'Supprimer le foyer' }),
    'le foyer ne se supprime pas depuis son compte',
  ).toHaveCount(0)
})

test('le foyer annonce ce qu’il NE touche pas', async ({ page }) => {
  /* L'ancienne zone disait « personnels comme joints » — elle était honnête, l'action
   * était brutale. L'écran du foyer doit dire l'inverse, et le dire explicitement :
   * c'est la seule chose qui distingue ce monde de « Mon compte » aux yeux de qui le lit. */
  await connecter(page)
  const panneau = await ouvrirFoyer(page)
  await expect(panneau.getByText(/comptes personnels rest/)).toBeVisible()
})

test('le bouton reste inerte tant que l’adresse n’est pas exacte', async ({ page }) => {
  /* La seule barrière entre un doigt qui glisse et une perte définitive — et celle qu'un
   * remaniement de l'écran ferait sauter sans bruit : la suppression continuerait de
   * fonctionner, seule la protection disparaîtrait.
   *
   * C'est l'ADRESSE et non le nom du foyer depuis le 21 août 2026 : ce qu'on détruit ici
   * est son compte, et faire retaper le nom du foyer désignait la mauvaise chose. */
  await connecter(page)
  const panneau = await ouvrirMonCompte(page)

  await panneau.getByRole('button', { name: 'Supprimer mon compte' }).click()
  const effacer = panneau.getByRole('button', { name: 'Tout effacer' })
  await expect(effacer, 'inerte tant que rien n’est tapé').toBeDisabled()

  // Le champ de CONFIRMATION, nommément : « Mon compte » porte aussi celui du retrait du
  // second facteur, et un `textbox` anonyme en attraperait deux.
  const champ = panneau.getByRole('textbox', { name: /^Tapez / })
  await champ.fill('quelquun@ailleurs.fr')
  await expect(effacer, 'inerte sur une adresse fausse').toBeDisabled()

  // L'adresse est affichée juste au-dessus : le test la lit là où l'utilisateur la lit,
  // plutôt que de la coder en dur — sinon il mesurerait sa propre constante.
  const adresse = (await panneau.locator('strong').last().textContent())!
  await champ.fill(adresse)
  await expect(effacer, 'actif sur l’adresse exacte').toBeEnabled()

  // On s'arrête ici. Voir l'en-tête du fichier.
  await panneau.getByRole('button', { name: 'Annuler' }).click()
  await expect(panneau.getByRole('button', { name: 'Tout effacer' })).toHaveCount(0)
})

test('supprimer son compte dit ce qu’il détruit avant de le détruire', async ({ page }) => {
  await connecter(page)
  const panneau = await ouvrirMonCompte(page)

  const zone = panneau.getByText(/Efface définitivement votre compte/)
  await expect(zone).toContainText('comptes personnels')
  await expect(zone).toContainText('Aucune sauvegarde')
})

test('seul dans son foyer, l’écran ne prétend pas à un groupe', async ({ page }) => {
  /* Tout compte reçoit un foyer d'office, si bien qu'une personne seule était annoncée
   * « Membres » avec une liste d'une ligne : elle-même. Un fait de schéma présenté comme
   * un fait social. Olivier : « pourquoi il me dit membre d'un foyer alors que non »
   * (ERREURS.md #046).
   *
   * Le foyer de démonstration n'a qu'un membre — `creer_premier_compte` en crée un seul,
   * et rien dans la suite n'en ajoute : les tests d'invitation lisent le code sans le
   * consommer. Si cela changeait, ce test rougirait plutôt que de mentir en silence.
   */
  await connecter(page)
  const panneau = await ouvrirFoyer(page)

  await expect(panneau.getByRole('heading', { name: 'Partage', exact: true })).toBeVisible()
  await expect(
    panneau.getByRole('heading', { name: 'Membres', exact: true }),
    'un groupe d’une personne n’est pas un groupe',
  ).toHaveCount(0)
  await expect(panneau.getByText(/n’avez encore partagé avec personne/)).toBeVisible()

  // Inviter reste proposé : c'est précisément ce qu'il faut faire depuis cet état.
  await expect(panneau.getByLabel('Adresse à inviter')).toBeVisible()
  await expect(panneau.getByRole('button', { name: 'Inviter cette personne' })).toBeVisible()
})

test('la rubrique Foyer n’existe que dans un foyer, Mon compte que chez soi', async ({
  page,
}) => {
  /* Tranché par Olivier le 22 août 2026 : « le bouton foyer ne devrait pas s'afficher si
   * aucun foyer n'a été créé ». Avec les espaces, la règle devient : chaque espace ne
   * propose que ce qu'il administre. Son identité ne se gère pas depuis un foyer, et un
   * foyer ne se gère pas depuis son espace personnel.
   *
   * Mesuré dans les DEUX sens, dans le même test : une assertion qui ne vaudrait que d'un
   * côté passerait aussi pour un code qui masque la rubrique toujours, ou jamais.
   */
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)

  await basculerVers(page, 'Moi')
  const chezMoi = await ouvrirParametres(page)
  await expect(chezMoi.getByRole('button', { name: 'Mon compte' })).toBeVisible()
  await expect(
    chezMoi.getByRole('button', { name: 'Foyer', exact: true }),
    'rien à administrer ici',
  ).toHaveCount(0)
  await chezMoi.getByRole('button', { name: 'Fermer', exact: true }).click()

  await basculerVers(page, foyer.nom)
  const enFoyer = await ouvrirParametres(page)
  await expect(enFoyer.getByRole('button', { name: 'Foyer', exact: true })).toBeVisible()
  await expect(
    enFoyer.getByRole('button', { name: 'Mon compte' }),
    'son identité ne se gère pas depuis le foyer',
  ).toHaveCount(0)
})
