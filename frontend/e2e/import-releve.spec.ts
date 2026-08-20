import { expect, test, type Page } from '@playwright/test'

/**
 * Import d'un relevé, à l'écran.
 *
 * **Toutes les données de ce fichier sont inventées.** Elles reproduisent la forme d'un
 * export bancaire réel — encodage Latin-1, séparateur point-virgule, débit et crédit en
 * deux colonnes, deux dates — sans en reprendre aucun contenu.
 *
 * Le test central est `réimporter le même fichier ne propose plus rien` : c'est la
 * contrainte que BOUCLE.md posait comme non négociable, et la seule dont une violation
 * dupliquerait de l'argent sans que rien ne le signale.
 */

const ENTETE =
  'Date de comptabilisation;Libelle simplifie;Libelle operation;Reference;' +
  'Informations complementaires;Type operation;Categorie;Sous categorie;' +
  'Debit;Credit;Date operation;Date de valeur;Pointage operation'

function releve(...lignes: readonly string[]): Buffer {
  // Latin-1, comme les exports réels : c'est aussi ce que l'écran doit savoir lire.
  return Buffer.from([ENTETE, ...lignes].join('\r\n') + '\r\n', 'latin1')
}

function ligne(libelle: string, debit: string, reference = '', date = '17/08/2026'): string {
  return (
    `${date};${libelle};CB ${libelle};${reference};;Carte bancaire;Alimentation;` +
    `Sous;${debit};;${date};${date};0`
  )
}

async function connecter(page: Page) {
  await page.goto('/')
  await page.locator('nav, form').first().waitFor({ state: 'visible' })
  if (await page.locator('nav').isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.locator('nav')).toBeVisible()
}

/** `dispatchEvent` : l'écran monte sa coquille sans attendre le réseau et recouvre la
 *  bulle dans la milliseconde, si bien que Playwright refuse de valider un clic dont
 *  l'interception qui suit est justement le résultat attendu. */
async function ouvrirImport(page: Page) {
  await page.getByRole('button', { name: 'Importer un relevé' }).dispatchEvent('click')
  await expect(page.getByRole('dialog', { name: 'Importer un relevé' })).toBeVisible()
}

async function deposer(page: Page, contenu: Buffer, nom = 'releve.csv') {
  await page
    .getByRole('dialog', { name: 'Importer un relevé' })
    .getByLabel('Relevé au format CSV')
    .setInputFiles({ name: nom, mimeType: 'text/csv', buffer: contenu })
}

test('déposer un relevé montre ce qu’il contient SANS rien écrire', async ({ page }) => {
  const libelle = `Boulangerie ${Date.now()}`
  await connecter(page)

  const avant = (await (await page.request.get('/api/operations?periode_courante=false')).json())
    .length

  await ouvrirImport(page)
  await deposer(page, releve(ligne(libelle, '-12,40', `r-${Date.now()}`)))

  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await expect(ecran.getByText(libelle)).toBeVisible()
  await expect(ecran.getByText(/1 nouvelle/)).toBeVisible()

  // Rien n'a été écrit tant qu'on n'a pas validé.
  const apres = (await (await page.request.get('/api/operations?periode_courante=false')).json())
    .length
  expect(apres).toBe(avant)
})

test('valider écrit les lignes retenues, et elles apparaissent dans les comptes', async ({
  page,
}) => {
  const libelle = `Import ${Date.now()}`
  await connecter(page)
  await ouvrirImport(page)
  await deposer(page, releve(ligne(libelle, '-33,50', `r-${Date.now()}`)))

  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await ecran.getByRole('button', { name: /Importer 1 opération/ }).click()
  await expect(ecran.getByText(/1 opération importée/)).toBeVisible()

  const operations = (await (
    await page.request.get('/api/operations?periode_courante=false')
  ).json()) as { libelle: string; montant_centimes: number }[]
  const importee = operations.find((operation) => operation.libelle === libelle)
  expect(importee, 'l’opération n’a pas été écrite').toBeDefined()
  expect(importee!.montant_centimes).toBe(-3_350)
})

test('réimporter le même fichier ne propose plus rien', async ({ page }) => {
  /* La contrainte non négociable de BOUCLE.md. Sans elle, réimporter un mois qui chevauche
   * le précédent duplique l'argent — et l'erreur ne se voit qu'en comparant son solde à
   * celui de sa banque, des semaines plus tard. */
  const marque = Date.now()
  const contenu = releve(ligne(`Doublon ${marque}`, '-19,90', `r-${marque}`))
  await connecter(page)

  await ouvrirImport(page)
  await deposer(page, contenu)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await ecran.getByRole('button', { name: /Importer 1 opération/ }).click()
  await expect(ecran.getByText(/1 opération importée/)).toBeVisible()

  // Second dépôt du MÊME fichier.
  await deposer(page, contenu)
  await expect(ecran.getByText(/1 déjà importée/)).toBeVisible()
  // La ligne reste visible — la taire ferait croire à un fichier incomplet.
  await expect(ecran.getByText(`Doublon ${marque}`)).toBeVisible()
  await expect(ecran.getByRole('button', { name: /Importer 0 opération/ })).toBeDisabled()
})

test('un fichier illisible est refusé en disant ce qui manque', async ({ page }) => {
  await connecter(page)
  await ouvrirImport(page)
  await deposer(page, Buffer.from('un;deux\r\n1;2\r\n', 'latin1'), 'bidon.csv')

  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  // Le message nomme la colonne manquante : c'est la seule information qui permet d'agir.
  await expect(ecran.getByRole('alert')).toContainText('Debit')
})

test('les accents d’un relevé Latin-1 survivent à l’import', async ({ page }) => {
  // La plupart des banques françaises exportent en ISO-8859-1. Lu de travers, « Café »
  // deviendrait « Caf? » — et le regroupement par commerçant des statistiques ne s'en
  // remettrait pas.
  const libelle = `Café Crème ${Date.now()}`
  await connecter(page)
  await ouvrirImport(page)
  await deposer(page, releve(ligne(libelle, '-4,20', `r-${Date.now()}`)))

  await expect(
    page.getByRole('dialog', { name: 'Importer un relevé' }).getByText(libelle),
  ).toBeVisible()
})

test('le rangement s’apprend d’un import à l’autre', async ({ page }) => {
  /* Sans mémoire, deux cents lignes seraient à ranger à la main à chaque import — et
   * personne ne le fait deux fois. C'est ce qui rend l'import réellement utilisable. */
  const commercant = `Boucherie ${Date.now()}`
  await connecter(page)

  // Une catégorie de dépense, quelle qu'elle soit.
  const categories = (await (await page.request.get('/api/categories')).json()) as {
    id: string
    nom: string
    nature: string
  }[]
  const depense = categories.find((categorie) => categorie.nature === 'depense')!

  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(page, releve(ligne(commercant, '-18,00', `a-${Date.now()}`)))

  await ecran.getByLabel(`Catégorie de ${commercant}`).selectOption(depense.id)
  await ecran.getByRole('button', { name: /Importer 1 opération/ }).click()
  await expect(ecran.getByText(/1 opération importée/)).toBeVisible()

  // Second relevé, même commerçant, autre montant : la catégorie est proposée d'office.
  await deposer(page, releve(ligne(commercant, '-24,50', `b-${Date.now()}`)))
  await expect(ecran.getByLabel(`Catégorie de ${commercant}`)).toHaveValue(depense.id)
})

test('un prélèvement déjà enregistré est signalé et décoché', async ({ page }) => {
  /* Une opération en double fausse le solde, les budgets et les statistiques d'un coup,
   * alors qu'une ligne oubliée se rattrape en la recochant. */
  const marque = Date.now()
  await connecter(page)

  const comptes = (await (await page.request.get('/api/comptes')).json()) as { id: string }[]
  await page.request.post('/api/operations', {
    data: {
      compte_id: comptes[0].id,
      libelle: `Abonnement ${marque}`,
      montant_centimes: -1_799,
      date_operation: '2026-08-16',
    },
  })

  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(page, releve(ligne(`PRLV ABO ${marque}`, '-17,99', `c-${marque}`)))

  // Le libellé n'a pas besoin de se ressembler : c'est le montant et la date qui parlent.
  await expect(ecran.getByText(/ressemble à/)).toBeVisible()
  await expect(ecran.getByRole('button', { name: /Importer 0 opération/ })).toBeDisabled()
})

test('les prélèvements réguliers du relevé sont proposés, jamais créés', async ({ page }) => {
  const marque = Date.now()
  await connecter(page)
  const avant = ((await (await page.request.get('/api/recurrences')).json()) as unknown[]).length

  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(
    page,
    releve(
      `05/07/2026;ORANGE ${marque};PRLV ORANGE;o1-${marque};;Prelevement;Telecom;Sous;-25,89;;05/07/2026;05/07/2026;0`,
      `05/08/2026;ORANGE ${marque};PRLV ORANGE;o2-${marque};;Prelevement;Telecom;Sous;-25,89;;05/08/2026;05/08/2026;0`,
    ),
  )

  await expect(ecran.getByText('Prélèvements réguliers repérés')).toBeVisible()
  await expect(ecran.getByText(/par mois/)).toBeVisible()

  // Rien n'a été créé : l'écran propose, il ne remplit pas le calendrier tout seul.
  const apres = ((await (await page.request.get('/api/recurrences')).json()) as unknown[]).length
  expect(apres).toBe(avant)
})

test('une ligne peut être reclassée en virement entre comptes', async ({ page }) => {
  /* Le cas d'Olivier : un +200 € qui vient de son LEP, pas de l'extérieur. Sans
   * reclassement, la somme entre dans ses revenus et les gonfle d'un argent qui n'est
   * jamais entré dans le foyer. */
  const marque = Date.now()
  await connecter(page)

  /* Le test crée SON compte de contrepartie et le choisit par son NOM.
   *
   * Une première version réutilisait un compte existant quand il y en avait déjà deux, et
   * le sélectionnait par index. Elle passait seule et échouait dans la suite complète, où
   * dix-neuf comptes se sont accumulés — l'index ne désignait plus rien de prévisible. Un
   * test qui suppose un état sans le garantir lui-même finit toujours par mesurer autre
   * chose que son sujet. */
  const nomDeLaContrepartie = `LEP ${marque}`
  await page.request.post('/api/comptes', {
    data: { nom: nomDeLaContrepartie, produit: 'lep', prive: true },
  })
  await page.reload()
  await expect(page.locator('nav')).toBeVisible()

  const libelle = `VIR RECU ${marque}`
  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(
    page,
    releve(
      `19/08/2026;${libelle};VIR;v-${marque};;Virement recu;Divers;Sous;;+173,47;19/08/2026;19/08/2026;0`,
    ),
  )

  await ecran.getByLabel(`Nature de ${libelle}`).selectOption('virement')
  const autre = ecran.getByLabel(`Autre compte pour ${libelle}`)
  await expect(autre).toBeVisible()
  await autre.selectOption({ label: nomDeLaContrepartie })
  await ecran.getByRole('button', { name: /Importer 1 opération/ }).click()
  await expect(ecran.getByText(/1 opération importée/)).toBeVisible()

  // Deux moitiés de signes opposés : l'argent a changé de poche sans entrer dans le foyer.
  const operations = (await (
    await page.request.get('/api/operations?periode_courante=false')
  ).json()) as { libelle: string; montant_centimes: number; virement_id: string | null }[]
  const moities = operations.filter((operation) => operation.libelle === libelle)
  expect(moities).toHaveLength(2)
  expect(moities[0].montant_centimes + moities[1].montant_centimes).toBe(0)
  expect(moities.every((moitie) => moitie.virement_id !== null)).toBe(true)
})

test('on peut n’importer qu’à partir d’une date', async ({ page }) => {
  // Pour ne pas doubler ce qui a déjà été saisi à la main avant la dernière paie.
  const marque = Date.now()
  await connecter(page)
  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })

  await ecran.getByLabel('N’importer qu’à partir du').fill('2026-08-01')
  await deposer(
    page,
    releve(
      ligne(`ANCIEN ${marque}`, '-10,00', `x1-${marque}`, '01/07/2026'),
      ligne(`RECENT ${marque}`, '-20,00', `x2-${marque}`, '18/08/2026'),
    ),
  )

  await expect(ecran.getByText(`RECENT ${marque}`)).toBeVisible()
  await expect(ecran.getByText(`ANCIEN ${marque}`)).toHaveCount(0)
})
