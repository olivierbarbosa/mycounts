import { expect, test, type Page } from '@playwright/test'

import { jourLocal } from './dates'

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
  if (await page.getByRole('navigation', { name: 'Navigation principale' }).isVisible()) return
  await page.getByLabel('Adresse électronique').fill(process.env.MYCOUNTS_COURRIEL_TEST!)
  await page.getByLabel('Mot de passe').fill(process.env.MYCOUNTS_MOT_DE_PASSE_TEST!)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()
}

/** `dispatchEvent` : l'écran monte sa coquille sans attendre le réseau et recouvre la
 *  bulle dans la milliseconde, si bien que Playwright refuse de valider un clic dont
 *  l'interception qui suit est justement le résultat attendu. */
async function ouvrirImport(page: Page) {
  await page.getByRole('button', { name: 'Importer un relevé' }).dispatchEvent('click')
  await expect(page.getByRole('dialog', { name: 'Importer un relevé' })).toBeVisible()
}

/** Déplie le bloc des lignes prêtes.
 *
 *  Elles sont repliées par défaut, et c'est tout le principe de l'écran : une ligne qui
 *  n'attend aucune décision ne doit pas occuper de place. Les tests qui veulent lire un
 *  libellé ordinaire doivent donc l'ouvrir, comme un humain le ferait. */
async function deplierLesPretes(page: Page) {
  // Sur `aria-expanded` et non sur la simple visibilité : le bouton est là dans les deux
  // états, et cliquer sans regarder REPLIERAIT un bloc déjà ouvert. Le helper doit pouvoir
  // être appelé deux fois de suite sans rien casser.
  const repli = page
    .getByRole('dialog', { name: 'Importer un relevé' })
    .getByRole('button', { name: /prêtes? à importer/, expanded: false })
  if (await repli.count()) await repli.click()
}

async function deposer(page: Page, contenu: Buffer, nom = 'releve.csv') {
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await ecran
    .getByLabel('Relevé au format CSV')
    .setInputFiles({ name: nom, mimeType: 'text/csv', buffer: contenu })
  // Attendre que l'analyse ait rendu sa revue. `setInputFiles` rend la main dès le fichier
  // choisi, avant l'aller-retour serveur : sans cette attente, tout ce qui suit s'exécute
  // sur un écran encore vide, et l'échec ressemble à un défaut d'affichage.
  await expect(
    ecran.getByText(/lignes? lues?|ligne lue/).or(ecran.getByRole('alert')),
  ).toBeVisible()
}

test('déposer un relevé montre ce qu’il contient SANS rien écrire', async ({ page }) => {
  const libelle = `Boulangerie ${Date.now()}`
  await connecter(page)

  const avant = (await (await page.request.get('/api/operations?periode_courante=false')).json())
    .length

  await ouvrirImport(page)
  await deposer(page, releve(ligne(libelle, '-12,40', `r-${Date.now()}`)))

  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await expect(ecran.getByText(/1 à importer/)).toBeVisible()
  await deplierLesPretes(page)
  await expect(ecran.getByText(libelle)).toBeVisible()

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
  await ecran.getByRole('button', { name: /^Importer 1$/ }).click()
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
  await ecran.getByRole('button', { name: /^Importer 1$/ }).click()
  await expect(ecran.getByText(/1 opération importée/)).toBeVisible()

  // Second dépôt du MÊME fichier.
  await deposer(page, contenu)
  // La ligne n'est pas tue : l'écran dit qu'elle a déjà été importée.
  await expect(ecran.getByText(/déjà été importée/)).toBeVisible()
  await expect(ecran.getByRole('button', { name: /^Importer 0$/ })).toBeDisabled()
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

  await deplierLesPretes(page)
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

  await ecran.getByRole('button', { name: /prête à importer/ }).click()
  await ecran.getByRole('button', { name: `Régler ${commercant}` }).click()
  const feuille = page.getByRole('dialog', { name: `Réglages de ${commercant}` })
  await feuille.getByLabel('Catégorie').selectOption(depense.id)
  await feuille.getByRole('button', { name: 'Terminé' }).click()
  await ecran.getByRole('button', { name: /^Importer 1$/ }).click()
  await expect(ecran.getByText(/1 opération importée/)).toBeVisible()

  /* Second relevé, même commerçant, autre montant : la catégorie est PRÉ-REMPLIE.
   *
   * L'assertion porte sur la valeur du champ et non sur le texte de la ligne : c'est le
   * pré-remplissage qui est le sujet, et le lire dans le champ le prouve sans dépendre de
   * la façon dont la ligne résume son contenu. */
  await deposer(page, releve(ligne(commercant, '-24,50', `b-${Date.now()}`)))
  await deplierLesPretes(page)
  await ecran.getByRole('button', { name: `Régler ${commercant}` }).click()
  const relue = page.getByRole('dialog', { name: `Réglages de ${commercant}` })
  await expect(relue.getByLabel('Catégorie')).toHaveValue(depense.id)
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
  await expect(ecran.getByRole('button', { name: /^Importer 0$/ })).toBeDisabled()
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
  await expect(page.getByRole('navigation', { name: 'Navigation principale' })).toBeVisible()

  const libelle = `VIR RECU ${marque}`
  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(
    page,
    releve(
      `19/08/2026;${libelle};VIR;v-${marque};;Virement recu;Divers;Sous;;+173,47;19/08/2026;19/08/2026;0`,
    ),
  )

  await ecran.getByRole('button', { name: /prête à importer/ }).click()
  await ecran.getByRole('button', { name: `Régler ${libelle}` }).click()
  const feuille = page.getByRole('dialog', { name: `Réglages de ${libelle}` })
  await feuille.getByRole('button', { name: 'Virement', exact: true }).click()
  await feuille.getByLabel('De quel compte').selectOption({ label: nomDeLaContrepartie })
  await feuille.getByRole('button', { name: 'Terminé' }).click()
  await ecran.getByRole('button', { name: /^Importer 1$/ }).click()
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

  await deplierLesPretes(page)
  await expect(ecran.getByText(`RECENT ${marque}`)).toBeVisible()
  await expect(ecran.getByText(`ANCIEN ${marque}`)).toHaveCount(0)
})

test('seules les EXCEPTIONS sont dépliées, le reste est replié', async ({ page }) => {
  /* Le principe qui gouverne tout l'écran, et il vient d'un échec : la première version
   * affichait les deux cents lignes à l'identique, chacune avec deux menus déroulants.
   * Olivier l'a essayée sur son téléphone et l'a trouvée illisible.
   *
   * Une ligne ordinaire ne doit donc rien demander : elle est repliée. Seule celle qui
   * changerait le résultat — ici un doublon probable — est mise en avant. */
  const marque = Date.now()
  await connecter(page)

  const comptes = (await (await page.request.get('/api/comptes')).json()) as { id: string }[]
  await page.request.post('/api/operations', {
    data: {
      compte_id: comptes[0].id,
      libelle: `Deja la ${marque}`,
      montant_centimes: -8_137,
      date_operation: jourLocal(),
    },
  })

  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(
    page,
    releve(
      ligne(`Ordinaire A ${marque}`, '-12,00', `oa-${marque}`),
      ligne(`Ordinaire B ${marque}`, '-13,00', `ob-${marque}`),
      ligne(`Suspecte ${marque}`, '-81,37', `su-${marque}`, jourLocal()),
    ),
  )

  // L'exception est visible d'emblée, avec sa raison.
  await expect(ecran.getByText('À vérifier (1)')).toBeVisible()
  await expect(ecran.getByText(/ressemble à/)).toBeVisible()

  // Les ordinaires sont repliées : leur libellé n'est pas affiché tant qu'on n'ouvre pas.
  await expect(ecran.getByText(`Ordinaire A ${marque}`)).toHaveCount(0)
  await expect(ecran.getByRole('button', { name: /2 prêtes à importer/ })).toBeVisible()

  await ecran.getByRole('button', { name: /2 prêtes à importer/ }).click()
  await expect(ecran.getByText(`Ordinaire A ${marque}`)).toBeVisible()

  // Le doublon est décoché : seules les deux ordinaires partent.
  await expect(ecran.getByRole('button', { name: /^Importer 2$/ })).toBeVisible()
})

test('toucher une ligne ouvre sa feuille de réglages', async ({ page }) => {
  // Une ligne MONTRE, elle ne demande rien. Qui veut la corriger la touche : c'est ce qui
  // permet d'en aligner deux cents sans les rendre illisibles.
  const libelle = `Reglage ${Date.now()}`
  await connecter(page)
  await ouvrirImport(page)
  const ecran = page.getByRole('dialog', { name: 'Importer un relevé' })
  await deposer(page, releve(ligne(libelle, '-9,99', `rg-${Date.now()}`)))

  await ecran.getByRole('button', { name: /prête à importer/ }).click()
  await ecran.getByRole('button', { name: `Régler ${libelle}` }).click()

  const feuille = page.getByRole('dialog', { name: `Réglages de ${libelle}` })
  await expect(feuille).toBeVisible()
  await expect(feuille.getByRole('button', { name: 'Dépense' })).toBeVisible()
  await expect(feuille.getByLabel('Catégorie')).toBeVisible()

  // « Ne pas importer » écarte la ligne sans la faire disparaître.
  await feuille.getByRole('button', { name: 'Ne pas importer' }).click()
  await expect(feuille).toHaveCount(0)
  await expect(ecran.getByRole('button', { name: /^Importer 0$/ })).toBeDisabled()
})
