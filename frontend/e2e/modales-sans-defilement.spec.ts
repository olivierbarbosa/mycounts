import { expect, test, type Page } from '@playwright/test'

/**
 * Sur téléphone, aucune modale ne doit demander de défilement.
 *
 * La règle est plus forte qu'un confort de mise en page : une feuille dont les actions
 * tombent sous la ligne de flottaison se présente comme terminée alors qu'elle ne l'est
 * pas. La capture qui a motivé ce test montrait un détail d'opération dont « Enregistrer »
 * et « Supprimer » n'existaient tout simplement pas à l'écran.
 *
 * Ce que ce test ne détecte PAS :
 *
 * - Le clavier logiciel. Ouvert, il ampute la hauteur utile de moitié sur iOS, et aucun
 *   navigateur sans interface ne le simule.
 * - La largeur intrinsèque des champs natifs. Un `input[type="date"]` se dimensionne
 *   d'après le texte que son moteur affiche : iOS écrit « 5 août 2026 » là où Chromium
 *   écrit « 08/05/2026 ». Un champ de date coupé par le bord de l'écran a été constaté sur
 *   un vrai iPhone alors que Chromium, WebKit de bureau ET l'émulation iPhone de Playwright
 *   le déclaraient tous les trois dans les clous. Aucun de ces trois moteurs ne rend le
 *   widget de date d'iOS ; leur verdict sur ce point ne vaut rien.
 *
 * Ces deux angles morts se vérifient à la main, sur l'appareil.
 */

/* 390 x 664, et non les 390 x 844 de la fiche technique de l'appareil : la barre d'état
   et celle du navigateur mangent environ 120 px, qu'aucune modale ne récupère jamais.
   Mesurer sur la hauteur nominale, c'est se donner 120 px qui n'existent pas — et c'est
   ce qui rendait une feuille « conforme » alors qu'elle demandait de défiler. */
const TELEPHONE = { width: 390, height: 664 }

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

/** Mesure ce qui dépasse : la hauteur de trop, et les boutons hors de l'écran. */
async function defautsDe(page: Page, nom: string) {
  const feuille = page.getByRole('dialog', { name: nom })
  await expect(feuille).toBeVisible()
  return feuille.evaluate((boite: HTMLElement, ecran: { width: number; height: number }) => {
    // La feuille elle-même, ou son unique enfant quand le rôle porte le voile.
    const defilante = boite.scrollHeight > boite.clientHeight ? boite : (boite.firstElementChild as HTMLElement) ?? boite
    const boutonsHorsEcran = [...boite.querySelectorAll('button')]
      .filter((b) => {
        const r = b.getBoundingClientRect()
        return r.height > 0 && (r.bottom > ecran.height + 1 || r.top < -1)
      })
      .map((b) => (b.getAttribute('aria-label') ?? b.textContent ?? '').trim())

    // La largeur compte autant que la hauteur, et se contrôle moins bien : un champ de
    // date ou un sélecteur natif a une largeur intrinsèque propre au moteur, qu'aucune
    // règle de la feuille ne fixe. Un premier jet de ce garde-fou ne regardait que la
    // verticale — et laissait passer un champ coupé par le bord de l'écran.
    const debordentADroite = [...boite.querySelectorAll('input, select, button, p, label')]
      .filter((e) => {
        const r = e.getBoundingClientRect()
        return r.height > 0 && (r.right > ecran.width + 1 || r.left < -1)
      })
      .map((e) => (e.getAttribute('id') ?? e.tagName).toLowerCase())

    return {
      hauteurEnTrop: Math.max(0, defilante.scrollHeight - defilante.clientHeight),
      largeurEnTrop: Math.max(0, defilante.scrollWidth - defilante.clientWidth),
      boutonsHorsEcran,
      debordentADroite,
    }
  }, TELEPHONE)
}

test.use({ viewport: TELEPHONE })

test('la feuille de saisie tient dans l’écran d’un téléphone', async ({ page }) => {
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  expect(await defautsDe(page, 'Saisir une opération')).toEqual({
    hauteurEnTrop: 0,
    largeurEnTrop: 0,
    boutonsHorsEcran: [],
    debordentADroite: [],
  })
})

test('le détail d’une opération tient dans l’écran d’un téléphone', async ({ page }) => {
  const libelle = `Tenue ${Date.now()}`
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant', { exact: true }).fill('45,90')
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  expect(await defautsDe(page, 'Détail de l’opération')).toEqual({
    hauteurEnTrop: 0,
    largeurEnTrop: 0,
    boutonsHorsEcran: [],
    debordentADroite: [],
  })
})

test('l’ajout d’un prélèvement tient dans l’écran d’un téléphone', async ({ page }) => {
  await connecter(page)
  await page.getByRole('button', { name: 'Calendrier' }).click()
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  expect(await defautsDe(page, 'Ajouter un prélèvement')).toEqual({
    hauteurEnTrop: 0,
    largeurEnTrop: 0,
    boutonsHorsEcran: [],
    debordentADroite: [],
  })
})

test('la confirmation de suppression reste entièrement visible', async ({ page }) => {
  const libelle = `Confirme ${Date.now()}`
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant', { exact: true }).fill('12,00')
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
  // L'état le plus haut de la feuille : la demande de confirmation s'ajoute au reste.
  await page.getByRole('button', { name: 'Supprimer' }).click()
  await expect(page.getByRole('alertdialog')).toBeVisible()
  expect(await defautsDe(page, 'Détail de l’opération')).toEqual({
    hauteurEnTrop: 0,
    largeurEnTrop: 0,
    boutonsHorsEcran: [],
    debordentADroite: [],
  })
})
