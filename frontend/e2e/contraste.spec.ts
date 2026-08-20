import { expect, test } from '@playwright/test'

/**
 * Contrepartie de la direction artistique néon + Liquid Glass (BOUCLE.md, décision D3).
 *
 * Sur du verre, le contraste d'un texte dépend de ce qui se trouve dessous. La règle du
 * lot 1 — « aucun montant sur du verre » — est donc remplacée par une contrainte
 * **mesurée** : tout texte visible doit atteindre le seuil AA de 4,5:1, dans les trois
 * positions du réglage de transparence.
 *
 * Le calcul est fait dans la page, sur les couleurs RÉELLEMENT rendues (`getComputedStyle`
 * et composition des calques translucides), et non sur les valeurs des tokens : c'est ce
 * que l'œil reçoit qui compte, pas ce que la palette annonce.
 */

const SEUIL_AA = 4.5
const SEUIL_AA_GRAND = 3 // ≥ 24 px, ou ≥ 18,66 px en gras

/* Dérogation, explicite et bornée, pour le rouge des débits du thème sombre.
 *
 * Olivier a choisi de conserver `#FB7185` après avoir vu le chiffre — la seconde fois, la
 * première portait sur la palette lavande. Sous le halo bleu, ce rouge mesure 3,51:1 là où
 * AA en demande 4,5. `#FDA4AF` le faisait passer à 5,00:1, au prix d'un rose nettement
 * plus pâle. C'est une décision prise en connaissance de cause le 20 août 2026.
 *
 * Ce n'est pas une exemption. Le seuil est abaissé à la valeur RÉELLEMENT MESURÉE : toute
 * dégradation supplémentaire de ce rouge — un halo plus clair, une opacité de texte plus
 * basse — repassera sous ce plancher et fera rougir ce test. Ce qu'il ne couvre plus, en
 * revanche, c'est l'écart entre 3,5 et 4,5, et cette ligne est le seul endroit où il est
 * écrit. Concrètement, ce sont les centimes des montants, en 10 px, qui en pâtissent.
 *
 * Une note sur la façon de mesurer, parce que je m'y suis trompé le jour même : sur le
 * fond NU `#0F172A`, ce même rouge donne 6,63:1, et j'en avais conclu que la dérogation
 * était devenue inutile. Les montants ne sont jamais posés sur le fond nu — le halo passe
 * dessous et l'éclaircit. Une mesure sur aplat ne dit rien du rendu.
 */
const DEBIT_SOMBRE = [251, 113, 133]
const PLANCHER_DEBIT = 3.5

const POSITIONS = ['claire', 'moyenne', 'opaque'] as const

/** Les deux thèmes sont testés explicitement. Playwright force « light » par défaut :
 *  sans cette boucle, la moitié de la palette n'aurait jamais été mesurée — et je
 *  n'aurais même pas su laquelle. */
const THEMES = ['light', 'dark'] as const

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

const MESURE = ([seuilNormal, seuilGrand, debit, plancherDebit]: [
  number,
  number,
  number[],
  number,
]) => {
  const canal = (v: number) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)

  /** Lit rgb()/rgba() ET color(srgb …), dont les composantes vont de 0 à 1.
   *
   *  Sans ce second cas, toute surface produite par `color-mix()` était lue comme un
   *  quasi-noir : la sonde annonçait des rapports de 1,5 là où le contraste réel était
   *  de 10. Une sonde fausse est pire qu'une sonde absente — elle fait corriger ce qui
   *  n'est pas cassé. */
  const lire = (couleur: string): [number, number, number, number] => {
    const nombres = couleur.match(/[\d.]+/g)?.map(Number) ?? []
    if (nombres.length < 3) return [0, 0, 0, 0]
    const echelle = couleur.startsWith('color(') ? 255 : 1
    return [
      nombres[0] * echelle,
      nombres[1] * echelle,
      nombres[2] * echelle,
      nombres.length > 3 ? nombres[3] : 1,
    ]
  }

  const luminance = ([r, v, b]: number[]) =>
    0.2126 * canal(r / 255) + 0.7152 * canal(v / 255) + 0.0722 * canal(b / 255)

  /** Couleurs d'arrêt d'un dégradé, s'il y en a un.
   *
   *  `getComputedStyle().backgroundColor` vaut `rgba(0,0,0,0)` quand le fond est un
   *  `linear-gradient` : la sonde composait alors sur le parent et annonçait 1,02:1 sur
   *  des boutons parfaitement lisibles. On extrait donc les arrêts pour tester le PIRE
   *  d'entre eux. Voir ERREURS.md #021. */
  const arretsDeDegrade = (element: Element): [number, number, number][] => {
    const image = getComputedStyle(element).backgroundImage
    if (!image || image === 'none') return []
    const trouves = image.match(/(?:rgba?|color)\([^)]+\)/g) ?? []
    return trouves
      .map(lire)
      .filter(([, , , a]) => a > 0)
      .map(([r, v, b]) => [r, v, b] as [number, number, number])
  }

  /** Arrêts translucides du halo dérivant, lus sur le pseudo-élément qui le porte.
   *
   *  Sans cette lecture, le halo échappe entièrement a la sonde : il vit dans un
   *  `background-image`, or la remontée des ancêtres ci-dessous ne lit que des
   *  `backgroundColor`. La sonde mesurait donc le fond nu et se déclarait verte pendant
   *  que le halo éclaircissait réellement le fond sous les textes. */
  const calquesDuHalo = (): [number, number, number, number][] => {
    const image = getComputedStyle(document.body, '::before').backgroundImage
    if (!image || image === 'none') return []
    return (image.match(/(?:rgba?|color)\([^)]+\)/g) ?? []).map(lire).filter(([, , , a]) => a > 0)
  }

  /** Compose les calques translucides jusqu'à trouver un fond opaque.
   *
   *  `halo` s'intercale juste au-dessus du corps de page, là où il se trouve réellement :
   *  au-dessus du fond, sous le verre. */
  const fondEffectif = (
    element: Element,
    halo: [number, number, number, number] | null,
  ): [number, number, number] => {
    const calques: [number, number, number, number][] = []
    let courant: Element | null = element
    let opaque: Element | null = null
    while (courant) {
      const [r, v, b, a] = lire(getComputedStyle(courant).backgroundColor)
      if (a > 0) {
        calques.push([r, v, b, a])
        opaque = courant
      }
      if (a >= 1) break
      courant = courant.parentElement
    }
    // Le halo ne compte que si l'opacité s'arrête sur le corps de page. Dès qu'une carte
    // opaque s'interpose, il passe derriere elle et n'éclaire plus rien.
    if (halo && opaque === document.body && calques.length > 0) {
      calques.splice(calques.length - 1, 0, halo)
    }
    // Fond ultime du navigateur si aucun calque opaque n'est trouvé.
    let [r, v, b] = [255, 255, 255]
    for (let i = calques.length - 1; i >= 0; i--) {
      const [cr, cv, cb, ca] = calques[i]
      r = cr * ca + r * (1 - ca)
      v = cv * ca + v * (1 - ca)
      b = cb * ca + b * (1 - ca)
    }
    return [r, v, b]
  }

  const resultats: { texte: string; rapport: number; seuil: number }[] = []
  for (const element of document.querySelectorAll('h1, h2, p, span, label, button, a, input')) {
    const texte = (element.textContent ?? '').trim()
    if (!texte || element.children.length > 0) continue
    const boite = element.getBoundingClientRect()
    if (boite.width === 0 || boite.height === 0) continue

    const style = getComputedStyle(element)
    if (style.visibility === 'hidden' || style.opacity === '0') continue

    const [tr, tv, tb, ta] = lire(style.color)

    // Fonds candidats. Quand un dégradé recouvre l'élément, ce sont SES arrêts qui font
    // foi : y ajouter le fond composé introduirait un candidat faux, et comme on retient
    // le pire rapport, ce faux candidat gagnerait toujours. Un candidat erroné n'est pas
    // un pire cas, c'est du bruit.
    //
    // Au fond nu s'ajoute une variante par teinte du halo. Ce n'est pas le faux candidat
    // de #021, et la différence se mesure au lieu de s'argumenter : les halos parcourent
    // 100 % de la largeur de l'écran et 90 % de sa hauteur — trajet relevé sur 390 px.
    // Tout texte passe donc réellement sous leur pic au cours du cycle, et ce candidat est
    // un vrai pire cas. Mesurer le fond immobile ne prouverait plus rien : la sonde lit un
    // instant, le fond, lui, bouge.
    const arrets = arretsDeDegrade(element)
    const candidats: [number, number, number][] =
      arrets.length > 0
        ? arrets
        : [
            fondEffectif(element, null),
            ...calquesDuHalo().map((halo) => fondEffectif(element, halo)),
          ]

    let rapport = Number.POSITIVE_INFINITY
    for (const [fr, fv, fb] of candidats) {
      // Un texte lui-même translucide se compose sur son fond avant comparaison.
      const avant = [tr * ta + fr * (1 - ta), tv * ta + fv * (1 - ta), tb * ta + fb * (1 - ta)]
      const l1 = luminance(avant)
      const l2 = luminance([fr, fv, fb])
      rapport = Math.min(rapport, (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05))
    }

    const taille = Number.parseFloat(style.fontSize)
    const gras = Number.parseInt(style.fontWeight, 10) >= 700
    const grand = taille >= 24 || (gras && taille >= 18.66)
    // Le rouge des débits porte son propre plancher, plus bas et documenté en tête de
    // fichier. La comparaison tolère un point d'écart par canal : un navigateur peut
    // rendre une couleur composée à l'unité près.
    const estDebit = [tr, tv, tb].every((v, i) => Math.abs(v - debit[i]) <= 1)
    resultats.push({
      texte: texte.slice(0, 40),
      rapport: Math.round(rapport * 100) / 100,
      seuil: estDebit ? plancherDebit : grand ? seuilGrand : seuilNormal,
    })
  }
  return resultats
}

/**
 * Garantit que l'accueil porte des montants des DEUX signes avant qu'on ne le mesure.
 *
 * Sans cela, ce fichier ne prouvait presque rien quand il tournait seul : le foyer d'essai
 * est réinitialisé vide, et une page sans opération n'affiche ni vert ni rouge — les deux
 * couleurs les plus difficiles à faire passer. Le défaut n'apparaissait qu'en suite
 * complète, après que d'autres tests avaient laissé des données derrière eux, ce qui
 * ressemblait à une interférence entre tests alors que c'était l'inverse : la mesure
 * isolée était la mesure aveugle.
 */
async function garantirDesMontants(page: import('@playwright/test').Page) {
  const comptes = (await (await page.request.get('/api/comptes')).json()) as { id: string }[]
  const compte_id = comptes[0].id
  const aujourdhui = new Date().toISOString().slice(0, 10)
  for (const montant_centimes of [-4299, 1250]) {
    await page.request.post('/api/operations', {
      data: {
        compte_id,
        libelle: `Contraste ${montant_centimes}`,
        montant_centimes,
        date_operation: aujourdhui,
      },
    })
  }
}

for (const theme of THEMES) {
  for (const position of POSITIONS) {
    test(`contraste AA — thème ${theme}, transparence « ${position} »`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: theme })
      await connecter(page)
      await garantirDesMontants(page)
      await page.evaluate((p) => localStorage.setItem('mycounts.transparence', p), position)
      await page.reload()
      // Attendre le CONTENU, pas seulement la navigation : celle-ci s'affiche pendant
      // que l'écran charge encore ses données, et la sonde mesurait alors une page vide.
      // En local le chargement était trop rapide pour que ça se voie ; la CI l'a révélé.
      await expect(page.locator('main')).toBeVisible()
      await expect(page.locator('main li, main header')).not.toHaveCount(0)

      const mesures = await page.evaluate(MESURE, [
        SEUIL_AA,
        SEUIL_AA_GRAND,
        DEBIT_SOMBRE,
        PLANCHER_DEBIT,
      ])
      expect(mesures.length, 'aucun texte mesuré : la sonde est cassée').toBeGreaterThan(5)

      const insuffisants = mesures.filter((m) => m.rapport < m.seuil)
      expect(
        insuffisants,
        `textes sous le seuil — thème ${theme}, transparence « ${position} »`,
      ).toEqual([])
    })
  }
}

test('témoin : la sonde de contraste sait détecter un texte illisible', async ({ page }) => {
  // Sans ce témoin, une sonde qui renverrait toujours un rapport élevé passerait les
  // trois tests ci-dessus sans rien vérifier.
  await connecter(page)
  await page.evaluate(() => {
    const cobaye = document.createElement('p')
    cobaye.textContent = 'texte volontairement illisible'
    // Gris moyen sur gris moyen : rapport proche de 1.
    cobaye.style.color = 'rgb(130, 130, 130)'
    cobaye.style.backgroundColor = 'rgb(140, 140, 140)'
    document.body.append(cobaye)
  })
  const mesures = await page.evaluate(MESURE, [4.5, 3, DEBIT_SOMBRE, PLANCHER_DEBIT])
  const cobaye = mesures.find((m) => m.texte.startsWith('texte volontairement'))
  expect(cobaye, 'le cobaye n’a pas été mesuré').toBeDefined()
  expect(cobaye!.rapport).toBeLessThan(2)
})

for (const theme of THEMES) {
  test(`contraste AA du panneau des paramètres — thème ${theme}`, async ({ page }) => {
    // Le panneau est un écran entier de texte que la sonde ne voyait pas : elle mesurait
    // l'accueil, où il n'est pas ouvert. Un écran neuf non mesuré est un écran où le
    // contraste n'est plus garanti par rien.
    await page.emulateMedia({ colorScheme: theme })
    await connecter(page)
    await page.getByRole('button', { name: /^Paramètres de / }).click()
    await expect(page.getByRole('dialog', { name: 'Paramètres' })).toBeVisible()

    const mesures = await page.evaluate(MESURE, [
      SEUIL_AA,
      SEUIL_AA_GRAND,
      DEBIT_SOMBRE,
      PLANCHER_DEBIT,
    ])
    expect(mesures.length, 'aucun texte mesuré : la sonde est cassée').toBeGreaterThan(5)
    expect(
      mesures.filter((m) => m.rapport < m.seuil),
      `textes sous le seuil dans les paramètres — thème ${theme}`,
    ).toEqual([])
  })
}
