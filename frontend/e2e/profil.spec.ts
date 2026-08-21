import { expect, test, type Page } from '@playwright/test'

/**
 * Photo de profil et nom affiché, vus de l'écran.
 *
 * Le test central est `la photo envoyée remplace les initiales partout` : l'avatar est
 * rendu par un composant unique posé à trois endroits — la bulle, l'en-tête des
 * paramètres, la liste des membres. Une version qui n'en câblerait qu'un donnerait un
 * visage à un endroit et des lettres à l'autre, sur le même écran.
 *
 * **Ce que ce fichier ne fait PAS** : changer le mot de passe ni l'adresse. Les tests
 * partagent un compte ; en modifier l'identifiant de connexion ferait échouer les cent
 * trente autres, et un test qui déplace le sol sous les autres coûte plus cher que ce
 * qu'il prouve. Les deux sont mesurés côté intégration, contre une base jetable, dans
 * `test_api_profil.py`.
 */

/** Un PNG 2×2 valide, écrit à la main : le plus petit décor qui soit vraiment une image.
 *  Le serveur DÉCODE ce qu'il reçoit — un fichier bidon serait refusé, et le test
 *  mesurerait le refus au lieu de l'envoi. */
const PNG_MINUSCULE = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGP8z4AATAxkcAGCAAA' +
    'wCAGFYA4/AAAAAElFTkSuQmCC',
  'base64',
)

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

async function ouvrirMonCompte(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Mon compte' }).click()
  await expect(page.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
}

/** Retire l'avatar s'il y en a un. Appelé en `finally` : un test qui échoue ne doit pas
 *  laisser une photo derrière lui, sinon le suivant mesure un décor qu'il n'a pas posé. */
async function nettoyer(page: Page) {
  await page.request.delete('/api/auth/moi/avatar')
}

test('la photo envoyée remplace les initiales partout', async ({ page }) => {
  await connecter(page)
  try {
    await ouvrirMonCompte(page)
    const panneau = page.getByRole('dialog', { name: 'Paramètres' })

    // Les initiales d'abord : sans cette moitié, un test qui trouverait une image ne
    // saurait pas dire si elle vient d'être posée ou si elle était déjà là.
    await expect(panneau.locator('img'), 'aucune photo au départ').toHaveCount(0)

    // Le champ est masqué par conception — il reste focalisable pour le clavier — et
    // `setInputFiles` n'exige pas qu'il soit visible.
    await panneau
      .locator('input[type="file"]')
      .setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: PNG_MINUSCULE })

    await expect(panneau.getByText('Photo mise à jour.')).toBeVisible()
    // Le portrait de l'écran ET la bulle qui l'a ouvert : c'est le même composant, et
    // c'est ce que ce test protège.
    await expect(
      panneau.locator('img'),
      'l’en-tête du panneau ET le profil portent le portrait',
    ).toHaveCount(2)
    await expect(page.getByRole('button', { name: /^Paramètres de / }).locator('img')).toBeVisible()

    // Servie par l'API, et bien comme une image.
    const source = await panneau.locator('img').first().getAttribute('src')
    const servie = await page.request.get(source!)
    expect(servie.status()).toBe(200)
    expect(servie.headers()['content-type']).toBe('image/webp')
  } finally {
    await nettoyer(page)
  }
})

test('retirer sa photo ramène les initiales', async ({ page }) => {
  await connecter(page)
  try {
    await page.request.put('/api/auth/moi/avatar', {
      multipart: {
        fichier: { name: 'p.png', mimeType: 'image/png', buffer: PNG_MINUSCULE },
      },
    })
    // Rechargement après le décor : l'application tient l'utilisateur en état, et une
    // photo posée par l'API après le chargement lui reste inconnue.
    await page.reload()
    await ouvrirMonCompte(page)
    const panneau = page.getByRole('dialog', { name: 'Paramètres' })
    await expect(panneau.locator('img')).toHaveCount(2)

    await panneau.getByRole('button', { name: 'Retirer' }).click()
    await expect(panneau.getByText('Photo retirée.')).toBeVisible()
    await expect(panneau.locator('img'), 'la photo doit avoir disparu').toHaveCount(0)
  } finally {
    await nettoyer(page)
  }
})

test('un fichier qui n’est pas une image est refusé, et le dit', async ({ page }) => {
  /* Un fichier téléversé annonce son type LUI-MÊME : celui-ci se présente en PNG et n'en
   * est pas un. Seul le décodage côté serveur peut le dire, et le message doit revenir
   * jusqu'à l'écran — un refus muet se lit comme une panne. */
  await connecter(page)
  try {
    await ouvrirMonCompte(page)
    const panneau = page.getByRole('dialog', { name: 'Paramètres' })
    await panneau.locator('input[type="file"]').setInputFiles({
      name: 'faux.png',
      mimeType: 'image/png',
      buffer: Buffer.from('ceci n’est pas une image'),
    })

    await expect(panneau.getByRole('alert')).toContainText('image')
    await expect(panneau.locator('img'), 'rien ne doit avoir été posé').toHaveCount(0)
  } finally {
    await nettoyer(page)
  }
})

test('le nom affiché se change et se voit aussitôt', async ({ page }) => {
  const nom = `Essai ${Date.now() % 100000}`
  await connecter(page)
  try {
    await ouvrirMonCompte(page)
    const panneau = page.getByRole('dialog', { name: 'Paramètres' })

    await panneau.getByRole('button', { name: /^Nom affiché/ }).click()
    await panneau.getByLabel('Nouveau nom').fill(nom)
    await panneau.getByRole('button', { name: 'Enregistrer' }).click()

    await expect(panneau.getByText('Nom modifié.')).toBeVisible()
    // Le nom vit à trois endroits — le titre du panneau, la ligne, l'étiquette de la
    // bulle. Le voir revenir sur la bulle prouve que le rechargement a traversé toute
    // l'application, pas seulement le formulaire.
    await expect(page.getByRole('button', { name: `Paramètres de ${nom}` })).toBeVisible()
  } finally {
    // Le compte est partagé par les autres fichiers : on lui rend son nom.
    await page.request.patch('/api/auth/moi', { data: { nom_affichage: 'Essai' } })
  }
})

test('le portrait remplit exactement son disque, aux trois endroits', async ({ page }) => {
  /* Mesuré, pas regardé.
   *
   * La bulle est un `<button>`, dont le navigateur remplit le padding par défaut à
   * `1px 6px`. Invisible tant qu'elle ne portait que deux lettres centrées ; le jour où
   * elle a contenu une image devant remplir le disque, celle-ci est sortie à 30 × 40 dans
   * un rond de 44 — un ovale décalé, signalé par Olivier depuis son téléphone. Un style
   * hérité de l'agent utilisateur ne se voit que quand le contenu change de nature, et
   * aucun test d'alors ne mesurait de géométrie.
   *
   * Le critère est le CARRÉ, pas une taille : les trois disques ont des mesures
   * différentes et légitimes. Ce qui ne l'est jamais, c'est une image plus large que haute
   * dans un rond — `border-radius: 50%` en fait alors une ellipse.
   */
  await connecter(page)
  try {
    await page.request.put('/api/auth/moi/avatar', {
      multipart: { fichier: { name: 'p.png', mimeType: 'image/png', buffer: PNG_MINUSCULE } },
    })
    await page.reload()

    const bulle = page.getByRole('button', { name: /^Paramètres de / })
    await expect(bulle.locator('img')).toBeVisible()
    const carreeDansLaBulle = await bulle.locator('img').evaluate((img) => {
      const image = img.getBoundingClientRect()
      const disque = img.closest('button')!.getBoundingClientRect()
      return {
        carree: Math.abs(image.width - image.height) < 1,
        // Deux pixels de tolérance : la bordure du disque, qui n'appartient pas à l'image.
        remplit: disque.width - image.width <= 2 && disque.height - image.height <= 2,
      }
    })
    expect(carreeDansLaBulle, 'le portrait de la bulle doit remplir son disque').toEqual({
      carree: true,
      remplit: true,
    })

    await bulle.click()
    const panneau = page.getByRole('dialog', { name: 'Paramètres' })
    await panneau.getByRole('button', { name: 'Mon compte' }).click()
    await expect(panneau.getByRole('heading', { name: 'Supprimer mon compte' })).toBeVisible()
    // L'éclosion du panneau est une transformation : mesurer pendant fausserait les tailles.
    await page.waitForTimeout(700)

    const formes = await panneau.evaluate((noeud) =>
      [...noeud.querySelectorAll('img')].map((img) => {
        const r = img.getBoundingClientRect()
        return { carree: Math.abs(r.width - r.height) < 1, cote: Math.round(r.width) }
      }),
    )
    expect(formes.length, 'l’en-tête et le profil portent chacun un portrait').toBe(2)
    for (const forme of formes) {
      expect(forme.carree, `portrait de ${forme.cote} px déformé`).toBe(true)
      expect(forme.cote, 'un portrait réduit à rien passerait le test du carré').toBeGreaterThan(30)
    }
  } finally {
    await nettoyer(page)
  }
})
