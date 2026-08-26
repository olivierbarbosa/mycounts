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

/** La pilule de la rangée du haut : elle dit l'espace COURANT et ouvre la liste.
 *
 *  Depuis le 27 août 2026 le sélecteur n'est plus une barre qui montre tous les espaces
 *  en permanence, mais un seul bouton dans la rangée des bulles. Son nom accessible finit
 *  par « Changer d'espace » et commence par l'espace courant, d'où l'ancre de fin. */
export function selecteurEspace(page: Page) {
  return page.getByRole('button', { name: /Changer d’espace$/ })
}

export function listeDesEspaces(page: Page) {
  return page.getByRole('dialog', { name: 'Changer d’espace' })
}

/** Bascule comme l'utilisateur — ouvrir, choisir — et attend que l'espace soit ACTIF.
 *  Le libellé et les données changent ensemble : un clic ne suffit pas à conclure. */
export async function basculerVers(page: Page, libelle: string) {
  const pilule = selecteurEspace(page)
  if ((await pilule.innerText()).trim() === libelle) return
  await pilule.click()
  await listeDesEspaces(page).getByRole('button', { name: libelle, exact: true }).click()
  await expect(pilule).toHaveText(libelle)
  await expect(pilule).toHaveAttribute('aria-busy', 'false')
}

export async function ouvrirParametres(page: Page) {
  await page.getByRole('button', { name: /^Paramètres de / }).click()
  await expect(page.getByRole('dialog', { name: 'Paramètres' })).toBeVisible()
  return page.getByRole('dialog', { name: 'Paramètres' })
}
