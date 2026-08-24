import { expect, test } from '@playwright/test'

test('la connexion passe au MFA sans perdre les identifiants', async ({ page }) => {
  const corpsConnexion: unknown[] = []

  await page.route('*://*/api/**', async (route) => {
    const requete = route.request()
    if (requete.url().endsWith('/api/auth/connexion')) {
      const corps = requete.postDataJSON()
      corpsConnexion.push(corps)
      const avecCode = typeof corps.code === 'string'
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: avecCode
            ? { motif: 'second_facteur_invalide', message: 'Ce code n’est pas valable.' }
            : {
                motif: 'second_facteur_requis',
                message: 'Entrez le code de votre application.',
              },
        }),
      })
      return
    }
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Authentification requise.' }),
    })
  })

  await page.goto('/')
  await page.getByLabel('Adresse électronique').fill('personne@essai.fr')
  await page.getByLabel('Mot de passe').fill('correct cheval batterie agrafe')
  await page.getByRole('button', { name: 'Se connecter' }).click()

  await expect(
    page.getByRole('heading', { name: 'Vérifions que c’est bien vous.' }),
  ).toBeVisible()
  await page.getByLabel('Code de vérification').fill('000000')
  await page.getByRole('button', { name: 'Continuer' }).click()
  await expect(page.getByRole('alert')).toHaveText('Ce code n’est pas valable.')

  // `faire_confiance` est faux tant que la case n'est pas cochée : le seul appareil qui
  // devient fiable est celui qu'on a explicitement désigné.
  expect(corpsConnexion).toEqual([
    {
      courriel: 'personne@essai.fr',
      mot_de_passe: 'correct cheval batterie agrafe',
      faire_confiance: false,
    },
    {
      courriel: 'personne@essai.fr',
      mot_de_passe: 'correct cheval batterie agrafe',
      code: '000000',
      faire_confiance: false,
    },
  ])

  await page.getByRole('button', { name: 'Revenir' }).click()
  await expect(page.getByLabel('Adresse électronique')).toHaveValue('personne@essai.fr')
  await expect(page.getByLabel('Mot de passe')).toHaveValue('correct cheval batterie agrafe')
})

test('le login tient dans un petit écran sans défiler', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 700 })
  await page.route('*://*/api/**', (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Authentification requise.' }),
    }),
  )
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()

  const dimensions = await page.evaluate(() => ({
    contenu: document.documentElement.scrollHeight,
    fenetre: document.documentElement.clientHeight,
  }))
  expect(dimensions.contenu).toBeLessThanOrEqual(dimensions.fenetre)
})
