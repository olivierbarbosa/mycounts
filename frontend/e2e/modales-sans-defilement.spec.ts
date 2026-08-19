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

/* Deux téléphones, et non un seul : la première version de ce garde-fou ne mesurait que
   390 px. J'ai empilé deux champs sous un seuil de 400 px et conclu que c'était réglé.
   L'appareil réel faisait 430 px — au-dessus du seuil — et le défaut y était intact. Une
   mise en page qui tient à une largeur ne dit rien de la suivante.

   Les hauteurs ne sont pas celles des fiches techniques : sur 390, la barre du navigateur
   prend environ 120 px ; sur 430 en web app installée, il n'y a plus de barre mais restent
   la barre d'état et l'indicateur d'accueil. */
const TELEPHONES = [
  { nom: 'téléphone compact dans Safari', width: 390, height: 664 },
  { nom: 'grand téléphone en web app', width: 430, height: 839 },
] as const

type Ecran = { width: number; height: number }

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

async function saisir(page: Page, libelle: string, montant: string) {
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  await page.getByLabel('Montant', { exact: true }).fill(montant)
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByRole('button', { name: 'Enregistrer' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}

/** Mesure ce qui dépasse : la hauteur de trop, la largeur de trop, ce qui sort du cadre. */
async function defautsDe(page: Page, nom: string, ecran: Ecran) {
  const feuille = page.getByRole('dialog', { name: nom })
  await expect(feuille).toBeVisible()
  return feuille.evaluate((boite: HTMLElement, e: Ecran) => {
    // La feuille elle-même, ou son unique enfant quand le rôle porte le voile.
    const defilante =
      boite.scrollHeight > boite.clientHeight
        ? boite
        : ((boite.firstElementChild as HTMLElement) ?? boite)

    const hors = (r: DOMRect) =>
      r.bottom > e.height + 1 || r.top < -1 || r.right > e.width + 1 || r.left < -1

    const boutonsHorsEcran = [...boite.querySelectorAll('button')]
      .filter((b) => b.getBoundingClientRect().height > 0 && hors(b.getBoundingClientRect()))
      .map((b) => (b.getAttribute('aria-label') ?? b.textContent ?? '').trim())

    // La largeur compte autant que la hauteur, et se contrôle moins bien : un champ natif
    // a une largeur intrinsèque propre au moteur, qu'aucune règle de la feuille ne fixe.
    // Un premier jet de ce garde-fou ne regardait que la verticale.
    const debordent = [...boite.querySelectorAll('input, select, p, label')]
      .filter((el) => el.getBoundingClientRect().height > 0 && hors(el.getBoundingClientRect()))
      .map((el) => (el.getAttribute('id') ?? el.tagName).toLowerCase())

    return {
      hauteurEnTrop: Math.max(0, defilante.scrollHeight - defilante.clientHeight),
      largeurEnTrop: Math.max(0, defilante.scrollWidth - defilante.clientWidth),
      boutonsHorsEcran,
      debordent,
    }
  }, ecran)
}

const CONFORME = {
  hauteurEnTrop: 0,
  largeurEnTrop: 0,
  boutonsHorsEcran: [],
  debordent: [],
}

for (const telephone of TELEPHONES) {
  test.describe(telephone.nom, () => {
    const ecran = { width: telephone.width, height: telephone.height }
    test.use({ viewport: ecran })

    test('la feuille de saisie tient dans l’écran', async ({ page }) => {
      await connecter(page)
      await page.getByRole('button', { name: 'Saisir une opération' }).click()
      expect(await defautsDe(page, 'Saisir une opération', ecran)).toEqual(CONFORME)
    })

    test('le détail d’une opération tient dans l’écran', async ({ page }) => {
      const libelle = `Tenue ${Date.now()}`
      await connecter(page)
      await saisir(page, libelle, '45,90')
      await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
      expect(await defautsDe(page, 'Détail de l’opération', ecran)).toEqual(CONFORME)
    })

    test('l’ajout d’un prélèvement tient dans l’écran', async ({ page }) => {
      await connecter(page)
      await page.getByRole('button', { name: 'Calendrier' }).click()
      await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
      expect(await defautsDe(page, 'Ajouter un prélèvement', ecran)).toEqual(CONFORME)
    })

    test('la confirmation de suppression reste entièrement visible', async ({ page }) => {
      const libelle = `Confirme ${Date.now()}`
      await connecter(page)
      await saisir(page, libelle, '12,00')
      await page.getByRole('button', { name: `Détail de ${libelle}` }).click()
      // L'état le plus haut de la feuille : la demande de confirmation s'ajoute au reste.
      await page.getByRole('button', { name: 'Supprimer' }).click()
      await expect(page.getByRole('alertdialog')).toBeVisible()
      expect(await defautsDe(page, 'Détail de l’opération', ecran)).toEqual(CONFORME)
    })
  })
}
