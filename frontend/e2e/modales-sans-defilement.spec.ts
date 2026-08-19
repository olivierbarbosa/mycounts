import { expect, test, type Page } from '@playwright/test'

/**
 * Sur téléphone, aucune modale ne doit demander de défilement.
 *
 * La règle est plus forte qu'un confort de mise en page : une feuille dont les actions
 * tombent sous la ligne de flottaison se présente comme terminée alors qu'elle ne l'est
 * pas. La capture qui a motivé ce test montrait un détail d'opération dont « Enregistrer »
 * et « Supprimer » n'existaient tout simplement pas à l'écran.
 *
 * Ce que ce test ne détecte PAS : un clavier logiciel ouvert réduit la hauteur utile de
 * moitié sur iOS, et aucun navigateur sans interface ne le simule. Les feuilles à champ de
 * saisie restent donc à vérifier à la main sur un vrai téléphone.
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
  return feuille.evaluate((boite: HTMLElement, hauteurEcran: number) => {
    // La feuille elle-même, ou son unique enfant quand le rôle porte le voile.
    const defilante = boite.scrollHeight > boite.clientHeight ? boite : (boite.firstElementChild as HTMLElement) ?? boite
    const boutonsHorsEcran = [...boite.querySelectorAll('button')]
      .filter((b) => {
        const r = b.getBoundingClientRect()
        return r.height > 0 && (r.bottom > hauteurEcran + 1 || r.top < -1)
      })
      .map((b) => (b.getAttribute('aria-label') ?? b.textContent ?? '').trim())
    return {
      hauteurEnTrop: Math.max(0, defilante.scrollHeight - defilante.clientHeight),
      boutonsHorsEcran,
    }
  }, TELEPHONE.height)
}

test.use({ viewport: TELEPHONE })

test('la feuille de saisie tient dans l’écran d’un téléphone', async ({ page }) => {
  await connecter(page)
  await page.getByRole('button', { name: 'Saisir une opération' }).click()
  expect(await defautsDe(page, 'Saisir une opération')).toEqual({
    hauteurEnTrop: 0,
    boutonsHorsEcran: [],
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
    boutonsHorsEcran: [],
  })
})

test('l’ajout d’un prélèvement tient dans l’écran d’un téléphone', async ({ page }) => {
  await connecter(page)
  await page.getByRole('button', { name: 'Calendrier' }).click()
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  expect(await defautsDe(page, 'Ajouter un prélèvement')).toEqual({
    hauteurEnTrop: 0,
    boutonsHorsEcran: [],
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
    boutonsHorsEcran: [],
  })
})
