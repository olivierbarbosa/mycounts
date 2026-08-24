import { expect, test, type Page } from '@playwright/test'

import {
  EN_TETE_ESPACE,
  basculerVers,
  creerCompteDans,
  foyerDeDemonstration,
  selecteurEspace,
} from './espaces-aide'

/**
 * Bascule entre son argent et celui du foyer, sur le modèle des ESPACES.
 *
 * Deux mondes ÉTANCHES, décidé par Olivier le 21 août 2026 : on répond à « combien j'ai »
 * ou à « combien on a », jamais aux deux mélangés. Depuis les espaces multiples, la
 * bascule est le sélecteur en haut de l'écran, et le périmètre voyage dans
 * `X-Mycounts-Espace` — l'ancienne capsule « Périmètre » des paramètres n'existe plus.
 *
 * Le test central est `un compte du foyer n'apparaît PAS dans l'espace personnel` et son
 * pendant : c'est l'étanchéité qui donne son sens à la bascule, et une fuite dans un sens
 * ou dans l'autre la rendrait inutile — voire indiscrète.
 */

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
}

const lireNoms = async (page: Page, espaceId?: string) =>
  ((await (
    await page.request.get('/api/comptes', {
      headers: espaceId === undefined ? {} : { [EN_TETE_ESPACE]: espaceId },
    })
  ).json()) as { nom: string }[]).map((compte) => compte.nom)

test('le sélecteur marque l’espace actif, et la bascule revient', async ({ page }) => {
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)
  const moi = selecteurEspace(page).getByRole('button', { name: 'Moi', exact: true })
  const maison = selecteurEspace(page).getByRole('button', { name: foyer.nom, exact: true })

  await expect(moi, 'l’application ouvre sur le personnel').toHaveAttribute('aria-current', 'page')
  await expect(maison).not.toHaveAttribute('aria-current', 'page')

  await basculerVers(page, foyer.nom)
  await expect(moi, 'un seul espace actif à la fois').not.toHaveAttribute('aria-current', 'page')

  await basculerVers(page, 'Moi')
  await expect(moi).toHaveAttribute('aria-current', 'page')
})

test('un compte du foyer n’apparaît PAS dans l’espace personnel', async ({ page }) => {
  const marque = Date.now()
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)
  await creerCompteDans(page, foyer, `Joint ${marque}`)
  await creerCompteDans(page, null, `Perso ${marque}`)

  const noms = await lireNoms(page)
  expect(noms).toContain(`Perso ${marque}`)
  expect(noms, 'un compte du foyer fuit dans le personnel').not.toContain(`Joint ${marque}`)
})

test('un compte personnel n’apparaît PAS dans le foyer', async ({ page }) => {
  /* L'étanchéité dans l'autre sens, et c'est celui qui protège : les opérations
   * personnelles ne doivent pas apparaître dans un écran que le conjoint regarde. */
  const marque = Date.now()
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)
  await creerCompteDans(page, foyer, `Joint ${marque}`)
  await creerCompteDans(page, null, `Perso ${marque}`)

  const noms = await lireNoms(page, foyer.id)
  expect(noms).toContain(`Joint ${marque}`)
  expect(noms, 'un compte personnel fuit dans le foyer').not.toContain(`Perso ${marque}`)
})

test('le solde de l’accueil change avec l’espace', async ({ page }) => {
  /* Ce que la bascule doit produire pour valoir quelque chose : deux réponses différentes
   * à « combien ». Un écran qui afficherait le même total dans les deux espaces
   * signalerait que le périmètre n'a pas suivi. Mesuré sur l'ÉCRAN, pas seulement sur
   * l'API : c'est le libellé et le chiffre ensemble qui doivent changer (ERREURS.md #045). */
  await connecter(page)
  const foyer = await foyerDeDemonstration(page)
  // 8 765,00 € : un montant qu'aucun autre test ne pose, reconnaissable à l'écran.
  await creerCompteDans(page, foyer, `Joint solde ${Date.now()}`, 876_500)

  const enFoyer = (await (
    await page.request.get('/api/resume', { headers: { [EN_TETE_ESPACE]: foyer.id } })
  ).json()) as { solde_reel: number }
  const enPerso = (await (await page.request.get('/api/resume')).json()) as {
    solde_reel: number
  }
  expect(enFoyer.solde_reel).not.toBe(enPerso.solde_reel)

  // Le séparateur de milliers est une espace fine insécable, et les centimes sont un
  // enfant du même élément : le motif accepte toute espace et lit « 8 765,00 » d'un bloc.
  const montant = /^8[\s\u202f\u00a0]765,00/
  await expect(page.getByText(montant)).toHaveCount(0)
  await basculerVers(page, foyer.nom)
  await expect(page.getByText(montant).first()).toBeVisible()
  await basculerVers(page, 'Moi')
  await expect(page.getByText(montant)).toHaveCount(0)
})

test('un identifiant d’espace inconnu ne donne accès à rien', async ({ page }) => {
  /* Pas de repli sur le personnel : un UUID inconnu reçoit un 404 neutre, sinon une
   * écriture destinée à un foyer révoqué changerait de périmètre en silence. */
  await connecter(page)
  const inconnue = await page.request.get('/api/comptes', {
    headers: { [EN_TETE_ESPACE]: '11111111-2222-4333-8444-555555555555' },
  })
  expect(inconnue.status()).toBe(404)
  const malformee = await page.request.get('/api/comptes', {
    headers: { [EN_TETE_ESPACE]: 'nimportequoi' },
  })
  expect(malformee.status(), 'un en-tête mal formé n’est pas « absent »').toBe(404)
})
