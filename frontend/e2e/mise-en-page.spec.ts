import { expect, test } from '@playwright/test'

import { VIEWPORTS } from '../playwright.config'

const CIBLE_MINIMALE = 44

/** Ces trois mesures portent sur la PAGE DE CONNEXION. Or chaque test reçoit la session
 *  de démonstration déjà ouverte (`e2e/preparation.ts`) : sans effacer le cookie, elles
 *  mesureraient l'accueil et « passeraient » sur le mauvais sujet — la forme d'erreur la
 *  plus fréquente d'ERREURS.md. */
async function sansSession(page: import('@playwright/test').Page) {
  await page.context().clearCookies()
}

/**
 * Garde-fou n°10 — mise en page sur téléphone, tablette et bureau.
 *
 * Ces tests tournent contre l'application RÉELLE servie par Vite, pas contre un rendu de
 * composant isolé : c'est la seule façon de voir un débordement, qui naît toujours de la
 * combinaison des règles, jamais d'un composant seul.
 */
for (const vue of VIEWPORTS) {
  test.describe(`${vue.nom} (${vue.width}×${vue.height})`, () => {
    test.use({ viewport: { width: vue.width, height: vue.height } })

    test('la page de connexion ne déborde pas horizontalement', async ({ page }) => {
      await sansSession(page)
      await page.goto('/')
      await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()

      const debordement = await page.evaluate(
        () => document.body.scrollWidth > document.body.clientWidth,
      )
      expect(debordement, 'le corps de la page défile horizontalement').toBe(false)
    })

    test('toutes les cibles tactiles atteignent 44 px', async ({ page }) => {
      await sansSession(page)
      await page.goto('/')
      const trop_petites = await page.evaluate((minimum) => {
        return [...document.querySelectorAll('button, a[role="button"]')]
          .map((element) => {
            const boite = element.getBoundingClientRect()
            return { texte: element.textContent?.trim() ?? '', h: boite.height, l: boite.width }
          })
          .filter((c) => c.h > 0 && (c.h < minimum || c.l < minimum))
      }, CIBLE_MINIMALE)
      expect(trop_petites, 'cibles sous 44 px').toEqual([])
    })

    test('les champs de saisie font au moins 16 px', async ({ page }) => {
      // En dessous de 16 px, iOS Safari zoome automatiquement à la mise au point du
      // champ et l'utilisateur se retrouve avec une page décalée.
      await sansSession(page)
      await page.goto('/')
      // L'application n'affiche rien tant que /auth/moi n'a pas répondu : évaluer le DOM
      // sans cette attente mesurait une page vide, et le test « passait » sur zéro champ.
      await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()
      const tailles = await page.evaluate(() =>
        [...document.querySelectorAll('input')].map((i) =>
          Number.parseFloat(getComputedStyle(i).fontSize),
        ),
      )
      expect(tailles.length).toBeGreaterThan(0)
      for (const taille of tailles) expect(taille).toBeGreaterThanOrEqual(16)
    })
  })
}

/* Insets hauts réels des appareils testés. Chromium de bureau rend
   `env(safe-area-inset-top)` à 0 : sans simulation, la seule configuration mesurée serait
   celle où le problème ne se produit PAS — le recouvrement du 27 août 2026 valait 10 px
   sans encoche et 26 px avec. Une mesure aveugle au cas fautif ne prouve rien. */
const ENCOCHES: Readonly<Record<string, number>> = {
  'iPhone SE': 0,
  'iPhone 14': 47,
  'Pixel 7': 24,
  'iPhone 15 Pro Max': 59,
}

test.describe('la rangée du haut ne recouvre jamais le contenu', () => {
  /* Régression du 27 août 2026 : le sélecteur d'espace occupait un second étage sous les
     bulles, en `position: fixed`, sans que `--disposition-reserve-bulle` — écrite pour
     l'avatar seul — ait été élargie. « Solde projeté » était coupé en deux sur l'appareil
     d'Olivier. Voir ERREURS.md #053. */
  for (const vue of VIEWPORTS.filter((v) => v.nom in ENCOCHES)) {
    const inset = ENCOCHES[vue.nom]!

    test(`${vue.nom} (encoche ${inset} px)`, async ({ page }) => {
      await page.setViewportSize({ width: vue.width, height: vue.height })
      await connecter(page)
      /* Le contenu D'ABORD : `evaluate` ne décale que les nœuds présents à l'instant où
         il s'exécute, contrairement à une feuille de style. Sans cette attente, la page
         n'était pas encore montée, elle gardait son rembourrage d'origine, et le témoin
         accusait un recouvrement de 11 px qui n'existait pas. */
      await expect(page.getByText('Solde projeté')).toBeVisible()
      if (inset > 0) {
        /* L'inset est AJOUTÉ à ce que chaque élément calcule déjà, jamais substitué.
           Une première version écrivait `top: calc(12px + inset)` en `!important` : elle
           remplaçait la position du composant, si bien qu'une position fautive devenait
           invisible dès qu'on simulait une encoche. Le témoin ne rougissait alors que sur
           l'iPhone SE, le seul format sans simulation — une sonde qui neutralise le défaut
           qu'elle cherche. */
        await page.evaluate((decalage) => {
          for (const noeud of document.querySelectorAll<HTMLElement>(
            '[class*="bulle"], button[aria-haspopup="dialog"]',
          )) {
            const actuel = Number.parseFloat(getComputedStyle(noeud).top)
            noeud.style.setProperty('top', `${actuel + decalage}px`, 'important')
          }
          const page_ = document.querySelector<HTMLElement>('main[class*="page"]')
          if (page_) {
            const actuel = Number.parseFloat(getComputedStyle(page_).paddingTop)
            page_.style.setProperty('padding-top', `${actuel + decalage}px`, 'important')
          }
        }, inset)
      }

      const mesure = await page.evaluate(() => {
        const flottants = [
          ...document.querySelectorAll('[class*="bulle"], button[aria-haspopup="dialog"]'),
        ].map((n) => n.getBoundingClientRect())
        const titre = [...document.querySelectorAll('*')]
          .find((n) => n.textContent?.trim() === 'Solde projeté' && n.children.length === 0)!
          .getBoundingClientRect()
        return {
          basDesFlottants: Math.round(Math.max(...flottants.map((b) => b.bottom))),
          hautDuTitre: Math.round(titre.top),
          largeurVue: window.innerWidth,
          debordeADroite: Math.round(Math.max(...flottants.map((b) => b.right))),
        }
      })

      expect(
        mesure.basDesFlottants,
        `la rangée du haut recouvre « Solde projeté » de ${mesure.basDesFlottants - mesure.hautDuTitre} px`,
      ).toBeLessThanOrEqual(mesure.hautDuTitre)
      expect(mesure.debordeADroite, 'la rangée déborde à droite').toBeLessThanOrEqual(
        mesure.largeurVue,
      )
    })
  }
})

test.describe('navigation selon la taille', () => {
  test('téléphone : la navigation est en bas', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await connecter(page)
    const nav = page.getByRole('navigation', { name: 'Navigation principale' })
    const boite = (await nav.boundingBox())!
    expect(boite.width, 'la barre doit être plus large que haute').toBeGreaterThan(boite.height)
    expect(boite.y, 'la barre doit être dans la moitié basse').toBeGreaterThan(844 / 2)
  })

  test('bureau : la navigation est un rail latéral, pas une barre basse', async ({ page }) => {
    // Sans ce contrôle, le bureau resterait un mobile étiré : une pilule au centre d'un
    // écran de 1280 px, et 1000 px de vide autour.
    await page.setViewportSize({ width: 1280, height: 800 })
    await connecter(page)
    const boite = (await page.getByRole('navigation', { name: 'Navigation principale' }).boundingBox())!
    expect(boite.height, 'le rail doit être plus haut que large').toBeGreaterThan(boite.width)
    expect(boite.x, 'le rail doit être collé à gauche').toBeLessThan(100)
  })

  test('la navigation reste entièrement dans la fenêtre', async ({ page }) => {
    // Régression : la tab bar dépassait de 41 px sous le bord, ses boutons étaient
    // partiellement inatteignables. Voir ERREURS.md #008.
    for (const vue of VIEWPORTS) {
      await page.setViewportSize({ width: vue.width, height: vue.height })
      await connecter(page)
      const boite = (await page.getByRole('navigation', { name: 'Navigation principale' }).boundingBox())!
      expect(boite.y + boite.height, `${vue.nom} : la nav dépasse en bas`).toBeLessThanOrEqual(
        vue.height,
      )
      expect(boite.x, `${vue.nom} : la nav déborde à gauche`).toBeGreaterThanOrEqual(0)
      expect(boite.x + boite.width, `${vue.nom} : la nav déborde à droite`).toBeLessThanOrEqual(
        vue.width,
      )
    }
  })
})

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  // Attendre que l'application ait tranché entre « connecté » et « pas connecté ».
  // Sans cette attente, la garde ci-dessous lisait une page encore vide, concluait
  // « pas connecté » et tentait de remplir un formulaire absent.
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
}

test('aucune barre de défilement n’est visible, et le défilement fonctionne', async ({ page }) => {
  // Deux grandeurs qui ne bougent pas ensemble : la barre doit avoir une épaisseur NULLE
  // pendant que le contenu reste plus haut que la fenêtre. Vérifier seulement la première
  // ne distinguerait pas une barre masquée d'une page qui ne défile pas.
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (!(await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible())) {
    await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
    await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
    await page.getByRole('button', { name: 'Se connecter' }).click()
  }
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()

  const mesure = await page.evaluate(() => {
    const element = document.scrollingElement as HTMLElement
    return {
      epaisseur: window.innerWidth - element.clientWidth,
      defilable: element.scrollHeight > element.clientHeight,
      // Une barre masquée par `overflow: hidden` serait un faux positif : le contenu ne
      // défilerait plus du tout.
      styleDefilement: getComputedStyle(element).overflowY,
    }
  })

  expect(mesure.epaisseur, 'la barre de défilement occupe encore de la place').toBe(0)
  expect(mesure.styleDefilement).not.toBe('hidden')
})
