import { expect, type Page } from '@playwright/test'

/**
 * Ce que les tests de bout en bout savent des ESPACES.
 *
 * Une identité a un espace personnel (« Moi ») et des foyers ; le sélecteur en haut de
 * l'application est l'unique auteur de la bascule, et l'API reçoit le périmètre par
 * `X-Mycounts-Espace`. Ce module est le seul endroit où les tests écrivent ces trois
 * faits : un test qui les recopierait deviendrait un second auteur, et vieillirait seul.
 */

export type EspacePublic = {
  readonly id: string
  readonly type: 'personnel' | 'foyer'
  readonly nom: string
}

export const EN_TETE_ESPACE = 'X-Mycounts-Espace'

/** Le foyer du compte de démonstration — `creer_premier_compte` en crée exactement un. */
export async function foyerDeDemonstration(page: Page): Promise<EspacePublic> {
  const espaces = (await (await page.request.get('/api/espaces')).json()) as EspacePublic[]
  const foyer = espaces.find((espace) => espace.type === 'foyer')
  if (foyer === undefined) throw new Error('le compte de démonstration n’a aucun foyer')
  return foyer
}

/** Crée un compte par l'API dans l'espace donné ; sans espace, dans le personnel. Le nom
 *  porte une marque unique : la base est partagée entre tous les fichiers de test. */
export async function creerCompteDans(
  page: Page,
  espace: EspacePublic | null,
  nom: string,
  soldeOuvertureCentimes?: number,
) {
  const reponse = await page.request.post('/api/comptes', {
    data: {
      nom,
      prive: espace === null || espace.type === 'personnel',
      produit: 'compte_courant',
      ...(soldeOuvertureCentimes === undefined
        ? {}
        : { solde_ouverture_centimes: soldeOuvertureCentimes }),
    },
    headers: espace === null ? {} : { [EN_TETE_ESPACE]: espace.id },
  })
  expect(reponse.status(), await reponse.text()).toBe(201)
  return (await reponse.json()) as { id: string }
}

export function selecteurEspace(page: Page) {
  return page.getByRole('navigation', { name: 'Changer d’espace' })
}

/** Bascule par le sélecteur, comme l'utilisateur, et attend que l'espace soit ACTIF —
 *  le libellé et les données changent ensemble, un clic ne suffit donc pas à conclure. */
export async function basculerVers(page: Page, libelle: string) {
  const bouton = selecteurEspace(page).getByRole('button', { name: libelle, exact: true })
  if ((await bouton.getAttribute('aria-current')) === 'page') return
  await bouton.click()
  await expect(bouton).toHaveAttribute('aria-current', 'page')
  await expect(selecteurEspace(page)).toHaveAttribute('aria-busy', 'false')
}

export async function ouvrirParametres(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await expect(page.getByRole('dialog', { name: 'Paramètres' })).toBeVisible()
  return page.getByRole('dialog', { name: 'Paramètres' })
}
