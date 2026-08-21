import { expect, test, type Page } from '@playwright/test'

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
 * — « Supprimer les comptes joints » emporterait ceux que `vue-foyer.spec.ts` vient de
 *   créer, et les tests partagent un même foyer : la dissolution déplacerait le sol sous
 *   les autres exactement comme une paie mal placée le ferait.
 * Ce que ces deux actions font réellement est prouvé côté intégration, contre une base
 * jetable, dans `test_suppression_foyer.py` et `test_dissolution_partage.py`.
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

/* La vue est PERSISTÉE dans `localStorage` : elle survit d'un test à l'autre et même
 * d'une exécution à l'autre. Chaque helper la pose donc explicitement, au lieu de
 * supposer celle qu'un test précédent a laissée. Un test qui dépend de son rang
 * d'exécution échoue par intermittence, ce qui est la pire forme d'échec — on finit par
 * le relancer au lieu de le lire. */
async function ouvrirParametres(page: Page, vue: 'personnelle' | 'foyer') {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  const capsule = vue === 'foyer' ? 'Comptes joints' : 'Compte personnel'
  await page
    .getByRole('group', { name: 'Périmètre' })
    .getByRole('button', { name: capsule })
    .click()
}

async function ouvrirFoyer(page: Page) {
  // « Foyer » ne vit que dans la vue joints : c'est le monde qu'il décrit.
  await ouvrirParametres(page, 'foyer')
  await page.getByRole('button', { name: 'Foyer', exact: true }).click()
  // « Partage » quand on est seul, « Membres » dès qu'on est plusieurs : le titre dit
  // lequel des deux est vrai, et le helper accepte les deux pour ne pas présumer.
  await expect(
    page
      .getByRole('heading', { name: 'Partage', exact: true })
      .or(page.getByRole('heading', { name: 'Membres', exact: true })),
  ).toBeVisible()
}

/** Pose un compte joint et rend de quoi le retirer.
 *
 *  La zone « Dissoudre le partage » n'existe que s'il y a quelque chose à dissoudre —
 *  c'est la règle même que `la dissolution n'est proposée que…` vérifie. Les tests qui
 *  portent sur son CONTENU doivent donc créer ce qu'ils vont lire, et le reprendre après :
 *  les tests partagent un foyer, et en laisser un derrière changerait ce que les suivants
 *  mesurent. */
async function avecCompteJoint(page: Page, nom: string) {
  const cree = await page.request.post('/api/comptes', {
    data: { nom, prive: false, produit: 'compte_courant' },
    headers: { 'X-Mycounts-Vue': 'foyer' },
  })
  const { id } = (await cree.json()) as { id: string }
  /* Rechargement obligatoire : `App` tient la liste des comptes en état, et un compte
     posé par l'API après le chargement lui reste inconnu. Basculer ne suffit pas — quand
     la vue demandée est déjà l'active, `basculerVers` sort sans relire. */
  await page.reload()
  return async () => {
    await page.request.delete(`/api/comptes/${id}`, { headers: { 'X-Mycounts-Vue': 'foyer' } })
  }
}

async function ouvrirMonCompte(page: Page) {
  // « Mon compte » ne vit que dans la vue personnelle : c'est son identité, pas le foyer.
  await ouvrirParametres(page, 'personnelle')
  await page.getByRole('button', { name: 'Mon compte' }).click()
  await expect(page.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
}

test('la liste des membres s’affiche au lieu de charger sans fin', async ({ page }) => {
  /* Le bug d'Olivier, dans le sens où il s'est produit : le client demandait
   * `/foyer/membres` quand la route est `/auth/foyer/membres`, et l'écran affichait
   * « Chargement… » pour toujours — parce qu'une liste vide et une liste pas encore
   * arrivée y étaient le même état.
   *
   * Ce test rougit aussi bien si le chemin casse que si les deux états refusionnent. */
  await connecter(page)
  const retirer = await avecCompteJoint(page, `Membres ${Date.now()}`)
  try {
    await ouvrirFoyer(page)

    /* Ce que ce test mesure est l'ARRIVÉE d'un état, quel qu'il soit : la liste des
     membres quand on est plusieurs, la phrase « pas encore partagé » quand on est seul.
     Ce qu'il refuse, c'est le troisième — « Chargement… » qui ne finit jamais. */
    await expect(page.getByText('Chargement…')).toHaveCount(0)
    // `.first()` sur la réunion : la racine du panneau reste montée sous le sous-écran et
    // porte ses propres `listitem`. Les deux branches peuvent donc matcher à la fois.
    await expect(
      page
        .getByText(/n’avez encore partagé avec personne/)
        .or(page.getByRole('listitem'))
        .first(),
    ).toBeVisible()
  } finally {
    await retirer()
  }
})

test('arrêter de partager et disparaître sont deux écrans', async ({ page }) => {
  /* La séparation elle-même, mesurée dans les deux sens : chaque écran porte SON action
   * et pas celle de l'autre. Une assertion sur la seule présence des deux boutons
   * passerait encore s'ils étaient tous deux revenus sur l'écran du foyer. */
  await connecter(page)
  const retirer = await avecCompteJoint(page, `Deux ecrans ${Date.now()}`)
  try {
    await ouvrirFoyer(page)
    await expect(page.getByRole('heading', { name: 'Dissoudre le partage' })).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Supprimer mon compte' }),
      'effacer son compte n’a rien à faire sur l’écran du foyer',
    ).toHaveCount(0)

    // Retour à la racine du panneau, puis l'autre monde. Le panneau reste ouvert : la
    // bulle qui le lance est dessous, la recliquer ne rouvrirait rien.
    await page.getByRole('button', { name: 'Retour', exact: true }).click()
    await page
      .getByRole('group', { name: 'Périmètre' })
      .getByRole('button', { name: 'Compte personnel' })
      .click()
    await page.getByRole('button', { name: 'Mon compte' }).click()
    await expect(page.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Dissoudre le partage' }),
      'le partage ne se dissout pas depuis son compte',
    ).toHaveCount(0)
  } finally {
    await retirer()
  }
})

test('dissoudre annonce ce qu’il NE touche pas', async ({ page }) => {
  /* L'ancienne zone disait « personnels comme joints » — elle était honnête, l'action
   * était brutale. Celle-ci doit dire l'inverse, et le dire explicitement : c'est la
   * seule chose qui distingue les deux boutons aux yeux de qui les lit. */
  await connecter(page)
  const retirer = await avecCompteJoint(page, `Annonce ${Date.now()}`)
  try {
    await ouvrirFoyer(page)
    const zone = page.getByText(/Supprime les comptes joints/)
    await expect(zone).toContainText('comptes personnels')
    await expect(zone, 'la promesse qui manquait').toContainText('restez connecté')
  } finally {
    await retirer()
  }
})

test('le bouton reste inerte tant que l’adresse n’est pas exacte', async ({ page }) => {
  /* La seule barrière entre un doigt qui glisse et une perte définitive — et celle qu'un
   * remaniement de l'écran ferait sauter sans bruit : la suppression continuerait de
   * fonctionner, seule la protection disparaîtrait.
   *
   * C'est l'ADRESSE et non le nom du foyer depuis le 21 août 2026 : ce qu'on détruit ici
   * est son compte, et faire retaper le nom du foyer désignait la mauvaise chose. */
  await connecter(page)
  await ouvrirMonCompte(page)

  await page.getByRole('button', { name: 'Supprimer mon compte' }).click()
  const effacer = page.getByRole('button', { name: 'Tout effacer' })
  await expect(effacer, 'inerte tant que rien n’est tapé').toBeDisabled()

  const champ = page.getByRole('textbox')
  await champ.fill('quelquun@ailleurs.fr')
  await expect(effacer, 'inerte sur une adresse fausse').toBeDisabled()

  // L'adresse est affichée juste au-dessus : le test la lit là où l'utilisateur la lit,
  // plutôt que de la coder en dur — sinon il mesurerait sa propre constante.
  const adresse = (await page.locator('strong').last().textContent())!
  await champ.fill(adresse)
  await expect(effacer, 'actif sur l’adresse exacte').toBeEnabled()

  // On s'arrête ici. Voir l'en-tête du fichier.
  await page.getByRole('button', { name: 'Annuler' }).click()
  await expect(page.getByRole('button', { name: 'Tout effacer' })).toHaveCount(0)
})

test('supprimer son compte dit ce qu’il détruit avant de le détruire', async ({ page }) => {
  await connecter(page)
  await ouvrirMonCompte(page)

  const zone = page.getByText(/Efface définitivement votre compte/)
  await expect(zone).toContainText('comptes personnels')
  await expect(zone).toContainText('Aucune sauvegarde')
})

test('seul dans son foyer, l’écran ne prétend pas à un groupe', async ({ page }) => {
  /* Tout compte reçoit un foyer d'office — `Utilisateur.foyer_id` est non nullable — si
   * bien qu'une personne seule était annoncée « Membres » avec une liste d'une ligne :
   * elle-même. Un fait de schéma présenté comme un fait social. Olivier : « pourquoi il
   * me dit membre d'un foyer alors que non » (ERREURS.md #046).
   *
   * Le foyer de démonstration n'a qu'un membre — `creer_premier_compte` en crée un seul,
   * et rien dans la suite n'en ajoute : les tests d'invitation lisent le code sans le
   * consommer. Si cela changeait, ce test rougirait plutôt que de mentir en silence.
   */
  await connecter(page)
  // Un compte joint pour ATTEINDRE l'écran, sans changer le nombre de membres — c'est
  // sur celui-ci que porte le test.
  const retirer = await avecCompteJoint(page, `Seul ${Date.now()}`)
  try {
    await ouvrirFoyer(page)

    await expect(page.getByRole('heading', { name: 'Partage', exact: true })).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Membres', exact: true }),
      'un groupe d’une personne n’est pas un groupe',
    ).toHaveCount(0)
    await expect(page.getByText(/n’avez encore partagé avec personne/)).toBeVisible()

    // Inviter reste proposé : c'est précisément ce qu'il faut faire depuis cet état.
    await expect(page.getByRole('button', { name: 'Inviter un membre' })).toBeVisible()
  } finally {
    await retirer()
  }
})

test('la rubrique Foyer n’existe qu’une fois le partage ouvert', async ({ page }) => {
  /* Tranché par Olivier le 22 août 2026 : « le bouton foyer ne devrait pas s'afficher si
   * aucun foyer n'a été créé ». L'espace commun naît de son premier compte joint ; avant
   * lui, il n'y a rien à administrer et la rubrique promettait un contenu vide.
   *
   * Mesuré dans les DEUX sens, dans le même test : une assertion qui ne vaudrait que d'un
   * côté passerait aussi pour un code qui masque la rubrique toujours, ou jamais.
   */
  await connecter(page)
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page
    .getByRole('group', { name: 'Périmètre' })
    .getByRole('button', { name: 'Comptes joints' })
    .click()

  /* Cadré sur le PANNEAU : l'accueil reste monté derrière lui et porte, dans le même
     état, un bouton « Créer un compte joint » du même nom. */
  const panneau = page.getByRole('dialog', { name: 'Paramètres' })
  const rubrique = panneau.getByRole('button', { name: 'Foyer', exact: true })
  await expect(panneau.getByRole('button', { name: 'Créer un compte joint' })).toBeVisible()
  await expect(rubrique, 'rien à partager : rien à administrer').toHaveCount(0)

  const retirer = await avecCompteJoint(page, `Ouvre ${Date.now()}`)
  try {
    await page.getByRole('button', { name: /^Paramètres de / }).click()
    await page
      .getByRole('group', { name: 'Périmètre' })
      .getByRole('button', { name: 'Comptes joints' })
      .click()
    await expect(rubrique, 'le partage ouvert, la rubrique apparaît').toBeVisible()
  } finally {
    await retirer()
  }
})
