import { expect, test, type Page } from '@playwright/test'

/**
 * Ce que les animations ont le droit d'animer, et qu'elles existent.
 *
 * Deux défauts sont arrivés le même jour et aucun test ne pouvait les voir :
 *
 * 1. Les sous-menus n'avaient AUCUNE animation. Un module CSS renomme les
 *    `animation-name` qu'il rencontre : en déplaçant les images clés vers `global.css`,
 *    les modules pointaient vers un nom inexistant. Le code décrivait le mouvement, le
 *    navigateur ne le jouait pas.
 * 2. Le panneau animait `clip-path`, que le compositeur ne sait pas jouer : chaque image
 *    forçait une repeinte plein écran, à 33,3 ms l'image — trente par seconde.
 *
 * Ce test ne chronomètre rien : une mesure de temps serait instable en intégration
 * continue. Il vérifie les deux causes, qui elles sont déterministes.
 */

/** Propriétés que le compositeur joue sans repeindre. Tout le reste coûte une repeinte
 *  par image, ce qui se voit dès qu'un fond flouté est à l'écran. */
const COMPOSITABLES = new Set(['transform', 'scale', 'rotate', 'translate', 'opacity', 'offset'])

/** Clés techniques présentes dans toute image clé, sans rapport avec ce qui est animé. */
const TECHNIQUES = new Set(['offset', 'computedOffset', 'easing', 'composite'])

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

/** Propriétés réellement animées sur un élément, hors clés techniques. */
async function proprietesAnimees(page: Page, selecteur: string) {
  return page.evaluate(
    ({ sel, techniques }) => {
      const element = document.querySelector(sel)
      if (element === null) return null
      const vues = new Set<string>()
      for (const animation of element.getAnimations()) {
        for (const image of animation.effect?.getKeyframes() ?? []) {
          for (const cle of Object.keys(image)) {
            if (!techniques.includes(cle)) vues.add(cle)
          }
        }
      }
      return [...vues].sort()
    },
    { sel: selecteur, techniques: [...TECHNIQUES] },
  )
}

test('le panneau n’anime que des propriétés que le compositeur sait jouer', async ({ page }) => {
  await connecter(page)
  await page.getByRole('button', { name: /^Paramètres de / }).click()

  const animees = await proprietesAnimees(page, '[class*="panneau"]')
  expect(animees, 'le panneau ne joue aucune animation').not.toBeNull()
  expect(animees!.length, 'le panneau ne joue aucune animation').toBeGreaterThan(0)
  for (const propriete of animees!) {
    expect(COMPOSITABLES.has(propriete), `« ${propriete} » force une repeinte par image`).toBe(true)
  }
})

test('l’avatar migre depuis la bulle, et non depuis sa place d’arrivée', async ({ page }) => {
  await connecter(page)
  const bulle = await page.getByRole('button', { name: /^Paramètres de / }).boundingBox()
  await page.getByRole('button', { name: /^Paramètres de / }).click()

  // La première image clé porte le transform qui ramène l'avatar sur la bulle. S'il est
  // nul, l'effet existe dans le code et nulle part à l'écran — c'est exactement ce qui
  // s'était produit, deux animations se superposant et la nulle l'emportant.
  const depart = await page.evaluate(() => {
    const avatar = document.querySelector('[class*="avatar"]')
    const animations = avatar?.getAnimations() ?? []
    return {
      nombre: animations.length,
      transform: String(animations[0]?.effect?.getKeyframes()[0]?.transform ?? ''),
    }
  })

  expect(depart.nombre, 'une seule animation, sinon la dernière écrase les autres').toBe(1)
  expect(depart.transform).toMatch(/translate\(-?\d+/)
  // Le déplacement doit être du même ordre que la distance bulle → avatar, pas nul.
  const [dx] = depart.transform.match(/-?\d+(\.\d+)?/g)!.map(Number)
  expect(Math.abs(dx), 'l’avatar ne part pas de la bulle').toBeGreaterThan(bulle!.width)
})

test('le sous-menu entre bien par la droite', async ({ page }) => {
  await connecter(page)
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Catégories' }).click()

  const animees = await proprietesAnimees(page, '[class*="sousPage"]')
  expect(animees, 'le sous-menu ne joue aucune animation').not.toBeNull()
  expect(animees, 'le sous-menu doit glisser, donc translater').toContain('transform')
  for (const propriete of animees!) {
    expect(COMPOSITABLES.has(propriete), `« ${propriete} » force une repeinte par image`).toBe(true)
  }
})

test('revenir d’un sous-menu le fait repartir vers la droite', async ({ page }) => {
  // Le sens porte du sens : la page était venue de la droite, elle y retourne. Une sortie
  // vers la gauche dirait « on avance encore » au moment où l'on recule.
  await connecter(page)
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await page.getByRole('button', { name: 'Catégories' }).click()
  await expect(page.getByRole('heading', { name: 'Catégories' })).toBeVisible()

  await page.getByRole('button', { name: 'Retour' }).click()

  const trajet = await page.evaluate(() => {
    const sousPage = document.querySelector('[class*="sousPage"]')
    if (sousPage === null) return null
    const images = sousPage.getAnimations()[0]?.effect?.getKeyframes() ?? []
    return {
      debut: String(images[0]?.transform ?? ''),
      fin: String(images[images.length - 1]?.transform ?? ''),
    }
  })

  expect(trajet, 'la sous-page disparaît sans sortir').not.toBeNull()
  expect(trajet!.debut).toBe('translateX(0px)')
  expect(trajet!.fin, 'elle doit repartir vers la droite, d’où elle venait').toBe(
    'translateX(100%)',
  )

  // Et elle finit par quitter le DOM : une page qui s'attarde bloquerait les clics.
  await expect(page.locator('[class*="sousPage"]')).toHaveCount(0)
})
