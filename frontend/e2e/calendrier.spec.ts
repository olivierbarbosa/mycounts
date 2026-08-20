import { expect, test } from '@playwright/test'

import { jourLocal } from './dates'

/**
 * Agenda et confirmation, dans le vrai navigateur.
 *
 * Le test central est `confirmer ne déplace pas le solde projeté` : c'est l'invariant le
 * plus important du projet, et c'est ici qu'il est vérifié tel que l'utilisateur le voit
 * — pas dans une réponse d'API.
 */

const HIER = jourLocal(-1)

async function connecter(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

async function ouvrirAgenda(page: import('@playwright/test').Page) {
  await connecter(page)
  await page.getByRole('button', { name: 'Calendrier' }).click()
  await expect(page.getByRole('heading', { name: 'Calendrier' })).toBeVisible()
}

/** L'écran du calendrier, et lui seul.
 *
 *  Il RECOUVRE l'accueil, il ne le remplace pas : le DOM de l'accueil reste monté
 *  derrière, avec sa propre liste d'opérations. Un `page.locator('li', …)` cherche dans le
 *  document entier et tombait donc sur la ligne de l'accueil, où il n'y a évidemment aucun
 *  bouton « Confirmer ». Le test ne mesurait plus l'écran qu'il croyait mesurer — la forme
 *  d'erreur la plus fréquente de ce projet. */
const agenda = (page: import('@playwright/test').Page) =>
  page.getByRole('dialog', { name: 'Calendrier' })

async function creerRecurrence(
  page: import('@playwright/test').Page,
  libelle: string,
  montant: string,
  ancre: string,
) {
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  await page.getByLabel('Montant', { exact: true }).fill(montant)
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Première échéance').fill(ancre)
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  // La FEUILLE, nommément, et non « aucun dialogue » : le calendrier qui l'a ouverte est
  // lui-même un dialogue modal — comme les paramètres et le détail d'épargne — et il reste
  // ouvert derrière elle. Compter les dialogues faisait donc attendre la fermeture d'un
  // écran que ce helper n'a jamais eu l'intention de fermer.
  await expect(page.getByRole('dialog', { name: /prélèvement/ })).toHaveCount(0)
}

/* Placé en tête du fichier à dessein : les tests suivants créent des prélèvements
   du mois en cours, après quoi « À venir » n'est plus jamais vide et la branche
   vérifiée ici ne s'exécuterait plus. Un test qui ne peut plus atteindre son sujet
   passe sans rien prouver. */
test('« À venir » vide ne prétend pas que rien n’est enregistré', async ({ page }) => {
  // L'écran affiche « Mes prélèvements » juste au-dessus : annoncer « aucun prélèvement
  // enregistré » pendant qu'un prélèvement y figure ferait mentir la page. Ce cas se
  // produit dès que toutes les échéances du mois sont passées — de plus en plus souvent
  // à mesure qu'on avance dans le mois.
  await ouvrirAgenda(page)
  const mois = (await (await page.request.get('/api/agenda/mois-en-cours')).json()) as {
    fin: string
  }
  // Une échéance hors du mois en cours : elle peuple « Mes prélèvements » sans jamais
  // entrer dans « À venir ».
  // `T12:00:00` et non `T00:00:00` : c'est ce qui rend le `toISOString()` ci-dessous sûr.
  // À midi local, un décalage de deux heures ne change pas le jour, alors qu'à minuit il
  // le fait reculer d'un — c'est exactement le défaut qui a fait rougir budget.spec.ts le
  // 21 août 2026 à 00h21. Voir `dates.ts`.
  const moisSuivant = new Date(`${mois.fin}T12:00:00`)
  moisSuivant.setDate(moisSuivant.getDate() + 10)
  await creerRecurrence(
    page,
    `Hors mois ${Date.now()}`,
    '30,00',
    moisSuivant.toISOString().slice(0, 10),
  )

  const aVenir = page.getByRole('heading', { name: 'À venir' }).locator('..')

  // L'assertion qui tient TOUJOURS : tant qu'un prélèvement existe, l'écran ne peut pas
  // prétendre qu'il n'y en a aucun. C'est le défaut visé, et il est détectable quel que
  // soit l'état laissé par les autres fichiers de test.
  await expect(aVenir).not.toContainText('Aucun prélèvement enregistré')

  // La formulation positive ne s'affiche que si la section est réellement vide, ce que
  // seuls les prélèvements du MOIS EN COURS déterminent. D'autres fichiers en créent —
  // `budget.spec.ts` passe avant celui-ci dans l'ordre alphabétique. Cette branche est
  // donc vérifiée quand l'état le permet, et l'assertion ci-dessus couvre le reste.
  if ((await aVenir.getByRole('listitem').count()) === 0) {
    await expect(aVenir).toContainText('Plus rien à payer')
  }
})

test('créer un prélèvement et le voir dans le calendrier', async ({ page }) => {
  const libelle = `Abonnement ${Date.now()}`
  await ouvrirAgenda(page)
  const dans10 = jourLocal(10)

  await creerRecurrence(page, libelle, '10,99', dans10)

  const ligne = agenda(page).locator('li', { hasText: libelle }).first()
  await expect(ligne).toBeVisible()
  await expect(ligne).toContainText('−10')
})

test('une échéance échue remonte dans « à confirmer » sans job manuel', async ({ page }) => {
  // Le trou d'ERREURS.md #018 : entre l'échéance et le passage du job, elle
  // n'apparaissait nulle part. La seule ouverture de l'agenda doit suffire.
  const libelle = `Echue ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '7,50', HIER)

  await expect(agenda(page).getByText('À confirmer', { exact: false })).toBeVisible()
  const ligne = agenda(page).locator('li', { hasText: libelle }).first()
  await expect(ligne.getByRole('button', { name: 'Confirmer', exact: true })).toBeVisible()
})

test('confirmer ne déplace pas le solde projeté', async ({ page }) => {
  // L'invariant central du projet, mesuré tel que l'utilisateur le voit. Trois grandeurs,
  // dont deux qui doivent varier en sens OPPOSÉS : si les trois bougeaient ensemble, ce
  // serait la sonde qui est fausse ; si le projeté bougeait, il y aurait double comptage.
  const libelle = `Temoin ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '12,34', HIER)

  const lire = async () => {
    const reponse = await page.request.get('/api/resume')
    return (await reponse.json()) as {
      solde_projete: number
      solde_reel: number
      solde_a_confirmer: number
    }
  }

  const avant = await lire()
  const ligne = agenda(page).locator('li', { hasText: libelle }).first()
  await ligne.getByRole('button', { name: 'Confirmer', exact: true }).click()
  await expect(ligne.getByRole('button', { name: 'Confirmer', exact: true })).toHaveCount(0)
  const apres = await lire()

  expect(apres.solde_projete, 'double comptage à la confirmation').toBe(avant.solde_projete)
  expect(apres.solde_reel).toBeLessThan(avant.solde_reel)
  expect(apres.solde_a_confirmer).toBeGreaterThan(avant.solde_a_confirmer)
  expect(apres.solde_reel - avant.solde_reel).toBe(
    -(apres.solde_a_confirmer - avant.solde_a_confirmer),
  )
})

test('le total des charges est la somme des lignes affichées', async ({ page }) => {
  // Un total affiché qui ne serait pas la somme de ce qu'on voit est indétectable à
  // l'œil dès qu'il y a plus de trois lignes. Le total ne porte QUE sur les charges :
  // un revenu récurrent, s'il en existait un, ne doit pas y entrer.
  await ouvrirAgenda(page)

  // La borne vient du serveur, comme pour l'écran : la recalculer ici en ferait un second
  // auteur, et le test finirait par valider sa propre version du mois.
  const mois = (await (await page.request.get('/api/agenda/mois-en-cours')).json()) as {
    debut: string
    fin: string
  }
  // L'ancre est ramenée dans le mois. Sans ce plafond, le test créait une échéance à
  // cinq jours qui, passé le 26, tombait le mois suivant : elle n'entrait alors plus dans
  // le total, et le test échouait quelques jours par mois sans que rien n'ait changé.
  const dans5 = jourLocal(5)
  await creerRecurrence(page, `Somme ${Date.now()}`, '25,00', dans5 <= mois.fin ? dans5 : mois.fin)

  const echeances = await page.request.get('/api/agenda?jours=120')
  const lignes = (await echeances.json()) as {
    montant_centimes: number
    date_echeance: string
  }[]
  const attendu = lignes
    .filter((e) => e.montant_centimes < 0 && e.date_echeance <= mois.fin)
    .reduce((s, e) => s + e.montant_centimes, 0)

  const nomDuMois = new Intl.DateTimeFormat('fr-FR', { month: 'long' }).format(
    new Date(`${mois.debut}T12:00:00`),
  )
  const total = page.locator('main').getByText(`Charges restantes en ${nomDuMois}`)
  await expect(total).toBeVisible()

  const euros = Math.trunc(Math.abs(attendu) / 100).toLocaleString('fr-FR')
  await expect(total.locator('..')).toContainText(euros)
})

test('la feuille ne propose que des prélèvements, jamais de revenu', async ({ page }) => {
  // Le calendrier est une page de charges : proposer « Revenu » ici brouillerait la
  // lecture « combien je paie », qui est sa seule raison d'être.
  await ouvrirAgenda(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()

  await expect(page.getByRole('dialog', { name: /prélèvement/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Revenu', exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Nouveau prélèvement' })).toBeVisible()
})

test('les rythmes sont nommés, pas exprimés en intervalle', async ({ page }) => {
  // « Tous les 3 mois » se choisit d'un coup ; « intervalle 3, unité mois » se traduit
  // mentalement, et une hésitation à la saisie finit en prélèvement mal daté.
  await ouvrirAgenda(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()

  const frequence = page.getByLabel('Fréquence')
  await expect(frequence).toContainText('Tous les mois')
  await expect(frequence).toContainText('Tous les 3 mois')
  await expect(frequence).toContainText('Tous les ans')
})

test('un prélèvement saisi sans signe est enregistré en négatif', async ({ page }) => {
  const libelle = `Charge ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '24,99', jourLocal(5))

  const ligne = agenda(page).locator('li', { hasText: libelle }).first()
  await expect(ligne).toContainText('−24')
})

test('modifier un prélèvement conserve son rythme à la réouverture', async ({ page }) => {
  // Rouvrir un prélèvement trimestriel en affichant « Tous les mois » le ferait basculer
  // au mensuel dès la première validation — une modification qu'on n'a pas demandée est
  // pire qu'un champ vide.
  const libelle = `Trimestre ${Date.now()}`
  await ouvrirAgenda(page)
  await page.getByRole('button', { name: 'Ajouter un prélèvement' }).click()
  await page.getByLabel('Montant', { exact: true }).fill('45,00')
  await page.getByLabel('Libellé', { exact: true }).fill(libelle)
  await page.getByLabel('Fréquence').selectOption({ label: 'Tous les 3 mois' })
  await page.getByRole('button', { name: 'Enregistrer', exact: true }).click()
  await expect(page.getByRole('dialog', { name: /prélèvement/ })).toHaveCount(0)

  await page.getByRole('button', { name: `Modifier le prélèvement ${libelle}` }).click()
  await expect(page.getByRole('heading', { name: 'Modifier le prélèvement' })).toBeVisible()
  await expect(page.getByLabel('Fréquence')).toHaveValue('trimestriel')
  await expect(page.getByLabel('Montant', { exact: true })).toHaveValue('45,00')
})

test('modifier le montant d’un prélèvement met à jour le calendrier', async ({ page }) => {
  const libelle = `Modif ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '12,00', jourLocal(6))

  await page.getByRole('button', { name: `Modifier le prélèvement ${libelle}` }).click()
  await page.getByLabel('Montant', { exact: true }).fill('30,00')
  await page
    .getByRole('dialog', { name: /prélèvement/ })
    .getByRole('button', { name: 'Modifier', exact: true })
    .click()
  await expect(page.getByRole('dialog', { name: /prélèvement/ })).toHaveCount(0)

  const ligne = agenda(page).locator('li', { hasText: libelle }).first()
  await expect(ligne).toContainText('−30')
})

test('arrêter un prélèvement demande confirmation', async ({ page }) => {
  const libelle = `Arret ${Date.now()}`
  await ouvrirAgenda(page)
  await creerRecurrence(page, libelle, '9,99', jourLocal(4))

  await page.getByRole('button', { name: `Arrêter le prélèvement ${libelle}` }).click()
  await expect(page.getByRole('alertdialog')).toBeVisible()
  await expect(page.getByText(libelle).first()).toBeVisible()

  await page.getByRole('alertdialog').getByRole('button', { name: 'Arrêter' }).click()
  await expect(page.getByRole('alertdialog')).toHaveCount(0)
  await expect(page.getByRole('button', { name: `Arrêter le prélèvement ${libelle}` })).toHaveCount(
    0,
  )
})
