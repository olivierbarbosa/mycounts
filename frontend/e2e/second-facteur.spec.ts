import { expect, test, type Page } from '@playwright/test'

/**
 * Premier enrôlement au second facteur, vu de l'écran dédié.
 *
 * Le second facteur est OBLIGATOIRE depuis le lot identité : une session neuve ne voit
 * que cet écran tant qu'elle n'a pas activé le TOTP. Le test central est `les codes de
 * secours exigent une confirmation avant de disparaître` : le serveur ne les garde que
 * hachés, donc les redemander est impossible — pas seulement interdit. Un simple
 * « Continuer » les ferait perdre d'un clic distrait, et le compte deviendrait
 * irrécupérable en cas de téléphone perdu.
 *
 * **Ce fichier n'enrôle JAMAIS pour de bon** : l'API est simulée. Le compte de
 * démonstration a déjà été enrôlé par `preparation.ts`, et le refaire ici tournerait le
 * secret sous les pieds des autres fichiers. Ce que l'activation fait réellement est
 * mesuré côté intégration, dans `test_api_second_facteur.py`, contre une base jetable.
 */

const SECRET = 'JBSWY3DPEHPK3PXP'
const CODES = Array.from({ length: 10 }, (_, i) => `abcd-${String(1000 + i)}`)
const QR =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'

type Journal = { readonly chemins: string[] }

/** L'identité répond « enrôlement requis » jusqu'à ce que l'activation ait réussi. */
async function simulerApi(page: Page): Promise<Journal> {
  const journal: Journal = { chemins: [] }
  let enrole = false
  await page.route('*://*/api/**', async (route) => {
    const requete = route.request()
    const chemin = new URL(requete.url()).pathname
    journal.chemins.push(chemin)
    const json = (corps: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(corps) })

    if (chemin === '/api/auth/moi') {
      return json({
        id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        courriel: 'camille@essai.fr',
        nom_affichage: 'Camille',
        foyer_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        foyer_nom: 'Camille',
        est_proprietaire: true,
        a_un_avatar: false,
        avatar_version: null,
        courriel_verifie: true,
        second_facteur_actif: enrole,
        enrolement_requis: !enrole,
      })
    }
    if (chemin === '/api/auth/moi/second-facteur/preparer') {
      return json({ secret: SECRET, uri: `otpauth://totp/mycounts?secret=${SECRET}`, qr_svg: QR })
    }
    if (chemin === '/api/auth/moi/second-facteur/activer') {
      const { code } = requete.postDataJSON() as { code: string }
      if (code === '000000') {
        return json(
          { detail: 'Ce code ne correspond pas. Vérifiez l’heure de votre téléphone.' },
          400,
        )
      }
      enrole = true
      return json({ codes_de_secours: CODES })
    }
    if (chemin === '/api/espaces') {
      return json([
        {
          id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
          type: 'personnel',
          nom: 'Camille',
          role: 'proprietaire',
        },
      ])
    }
    return json([])
  })
  return journal
}

async function ouvrirLenrolement(page: Page) {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Protégez votre espace.' })).toBeVisible()
}

const champCode = (page: Page) => page.getByLabel('Code affiché par l’application')
const activer = (page: Page) => page.getByRole('button', { name: 'Activer et continuer' })

test('l’enrôlement propose de scanner ET de recopier la clé', async ({ page }) => {
  /* La saisie manuelle n'est pas un repli de second ordre : un ordinateur de bureau n'a
   * pas de caméra, et certaines applications n'acceptent que la clé. Ne proposer que le
   * QR exclurait ces cas sans le dire. */
  await simulerApi(page)
  await ouvrirLenrolement(page)

  await expect(page.getByLabel('Code à scanner')).toBeVisible()
  await expect(page.getByLabel('Code à scanner').locator('svg')).toBeVisible()
  await expect(page.getByText(SECRET)).toBeVisible()
})

test('le bouton d’activation reste inerte tant que le code est incomplet', async ({ page }) => {
  await simulerApi(page)
  await ouvrirLenrolement(page)

  await expect(activer(page), 'inerte tant que rien n’est tapé').toBeDisabled()
  await champCode(page).fill('123')
  await expect(activer(page), 'inerte sur un code trop court').toBeDisabled()
  await champCode(page).fill('123456')
  await expect(activer(page), 'actif sur six chiffres').toBeEnabled()
})

test('un code faux est refusé, et le message dit quoi vérifier', async ({ page }) => {
  /* « Ce code ne correspond pas » sans plus laisse chercher au mauvais endroit : la cause
   * la plus fréquente est l'heure du téléphone, pas une faute de frappe. */
  await simulerApi(page)
  await ouvrirLenrolement(page)

  await champCode(page).fill('000000')
  await activer(page).click()

  await expect(page.getByRole('alert')).toContainText('heure')
  // Et rien n'est activé : un enrôlement raté ne fait pas avancer le parcours.
  await expect(page.getByRole('heading', { name: 'Protégez votre espace.' })).toBeVisible()
  await expect(page.getByLabel('Code à scanner')).toBeVisible()
})

test('les codes de secours exigent une confirmation avant de disparaître', async ({ page }) => {
  const journal = await simulerApi(page)
  await ouvrirLenrolement(page)

  await champCode(page).fill('123456')
  await activer(page).click()

  await expect(page.getByRole('heading', { name: 'Gardez une porte de secours.' })).toBeVisible()
  await expect(page.getByRole('listitem')).toHaveCount(CODES.length)
  const terminer = page.getByRole('button', { name: 'Découvrir mon espace' })
  await expect(terminer, 'inerte tant que la sauvegarde n’est pas confirmée').toBeDisabled()

  await page.getByLabel('Je les ai conservés dans un endroit sûr').check()
  await expect(terminer).toBeEnabled()
  await terminer.click()

  // Deux grandeurs opposées : l'écran de secours part, et les finances sont demandées.
  await expect(page.getByRole('heading', { name: 'Gardez une porte de secours.' })).toBeHidden()
  await expect.poll(() => journal.chemins.includes('/api/espaces')).toBe(true)
})

test('l’enrôlement tient dans un petit écran sans défiler', async ({ page }) => {
  /* Un parcours d'accueil qui demande de faire défiler pour trouver son bouton principal
   * est un parcours qu'on abandonne. 700 px de haut : un iPhone avec sa barre d'adresse. */
  await page.setViewportSize({ width: 390, height: 700 })
  await simulerApi(page)
  await ouvrirLenrolement(page)
  await expect(page.getByLabel('Code à scanner').locator('svg')).toBeVisible()

  const mesurer = () =>
    page.evaluate(() => ({
      contenu: document.documentElement.scrollHeight,
      fenetre: document.documentElement.clientHeight,
    }))
  const scan = await mesurer()
  expect(scan.contenu, 'l’écran de scan déborde').toBeLessThanOrEqual(scan.fenetre)

  await champCode(page).fill('123456')
  await activer(page).click()
  await expect(page.getByRole('heading', { name: 'Gardez une porte de secours.' })).toBeVisible()
  const secours = await mesurer()
  expect(secours.contenu, 'l’écran des codes déborde').toBeLessThanOrEqual(secours.fenetre)
})
