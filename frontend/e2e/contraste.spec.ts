import { expect, test } from "@playwright/test";

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

const SEUIL_AA = 4.5;
const SEUIL_AA_GRAND = 3; // ≥ 24 px, ou ≥ 18,66 px en gras

const POSITIONS = ["claire", "moyenne", "opaque"] as const;

/** Les deux thèmes sont testés explicitement. Playwright force « light » par défaut :
 *  sans cette boucle, la moitié de la palette n'aurait jamais été mesurée — et je
 *  n'aurais même pas su laquelle. */
const THEMES = ["light", "dark"] as const;

async function connecter(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.locator("nav, form").first().waitFor({ state: "visible" });
  if (await page.locator("nav").isVisible()) return;
  await page
    .getByLabel("Adresse électronique")
    .fill(process.env.MYCOUNTS_COURRIEL_TEST!);
  await page
    .getByLabel("Mot de passe")
    .fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.locator("nav")).toBeVisible();
}

const MESURE = ([seuilNormal, seuilGrand]: [number, number]) => {
  const canal = (v: number) =>
    v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;

  /** Lit rgb()/rgba() ET color(srgb …), dont les composantes vont de 0 à 1.
   *
   *  Sans ce second cas, toute surface produite par `color-mix()` était lue comme un
   *  quasi-noir : la sonde annonçait des rapports de 1,5 là où le contraste réel était
   *  de 10. Une sonde fausse est pire qu'une sonde absente — elle fait corriger ce qui
   *  n'est pas cassé. */
  const lire = (couleur: string): [number, number, number, number] => {
    const nombres = couleur.match(/[\d.]+/g)?.map(Number) ?? [];
    if (nombres.length < 3) return [0, 0, 0, 0];
    const echelle = couleur.startsWith("color(") ? 255 : 1;
    return [
      nombres[0] * echelle,
      nombres[1] * echelle,
      nombres[2] * echelle,
      nombres.length > 3 ? nombres[3] : 1,
    ];
  };

  const luminance = ([r, v, b]: number[]) =>
    0.2126 * canal(r / 255) + 0.7152 * canal(v / 255) + 0.0722 * canal(b / 255);

  /** Compose les calques translucides jusqu'à trouver un fond opaque. */
  const fondEffectif = (element: Element): [number, number, number] => {
    const calques: [number, number, number, number][] = [];
    let courant: Element | null = element;
    while (courant) {
      const [r, v, b, a] = lire(getComputedStyle(courant).backgroundColor);
      if (a > 0) calques.push([r, v, b, a]);
      if (a >= 1) break;
      courant = courant.parentElement;
    }
    // Fond ultime du navigateur si aucun calque opaque n'est trouvé.
    let [r, v, b] = [255, 255, 255];
    for (let i = calques.length - 1; i >= 0; i--) {
      const [cr, cv, cb, ca] = calques[i];
      r = cr * ca + r * (1 - ca);
      v = cv * ca + v * (1 - ca);
      b = cb * ca + b * (1 - ca);
    }
    return [r, v, b];
  };

  const resultats: { texte: string; rapport: number; seuil: number }[] = [];
  for (const element of document.querySelectorAll(
    "h1, h2, p, span, label, button, a, input",
  )) {
    const texte = (element.textContent ?? "").trim();
    if (!texte || element.children.length > 0) continue;
    const boite = element.getBoundingClientRect();
    if (boite.width === 0 || boite.height === 0) continue;

    const style = getComputedStyle(element);
    if (style.visibility === "hidden" || style.opacity === "0") continue;

    const [tr, tv, tb, ta] = lire(style.color);
    const [fr, fv, fb] = fondEffectif(element);
    // Un texte lui-même translucide se compose sur son fond avant comparaison.
    const avant = [
      tr * ta + fr * (1 - ta),
      tv * ta + fv * (1 - ta),
      tb * ta + fb * (1 - ta),
    ];

    const l1 = luminance(avant);
    const l2 = luminance([fr, fv, fb]);
    const rapport = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);

    const taille = Number.parseFloat(style.fontSize);
    const gras = Number.parseInt(style.fontWeight, 10) >= 700;
    const grand = taille >= 24 || (gras && taille >= 18.66);
    resultats.push({
      texte: texte.slice(0, 40),
      rapport: Math.round(rapport * 100) / 100,
      seuil: grand ? seuilGrand : seuilNormal,
    });
  }
  return resultats;
};

for (const theme of THEMES) {
  for (const position of POSITIONS) {
    test(`contraste AA — thème ${theme}, transparence « ${position} »`, async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: theme });
      await connecter(page);
      await page.evaluate(
        (p) => localStorage.setItem("mycounts.transparence", p),
        position,
      );
      await page.reload();
      await expect(page.locator("nav")).toBeVisible();

      const mesures = await page.evaluate(MESURE, [SEUIL_AA, SEUIL_AA_GRAND]);
      expect(
        mesures.length,
        "aucun texte mesuré : la sonde est cassée",
      ).toBeGreaterThan(5);

      const insuffisants = mesures.filter((m) => m.rapport < m.seuil);
      expect(
        insuffisants,
        `textes sous le seuil — thème ${theme}, transparence « ${position} »`,
      ).toEqual([]);
    });
  }
}

test("témoin : la sonde de contraste sait détecter un texte illisible", async ({
  page,
}) => {
  // Sans ce témoin, une sonde qui renverrait toujours un rapport élevé passerait les
  // trois tests ci-dessus sans rien vérifier.
  await connecter(page);
  await page.evaluate(() => {
    const cobaye = document.createElement("p");
    cobaye.textContent = "texte volontairement illisible";
    // Gris moyen sur gris moyen : rapport proche de 1.
    cobaye.style.color = "rgb(130, 130, 130)";
    cobaye.style.backgroundColor = "rgb(140, 140, 140)";
    document.body.append(cobaye);
  });
  const mesures = await page.evaluate(MESURE, [4.5, 3]);
  const cobaye = mesures.find((m) =>
    m.texte.startsWith("texte volontairement"),
  );
  expect(cobaye, "le cobaye n’a pas été mesuré").toBeDefined();
  expect(cobaye!.rapport).toBeLessThan(2);
});
