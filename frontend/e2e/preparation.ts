import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { type APIResponse, request } from '@playwright/test'

/** Origine servie par Vite pendant les tests. L'API est jointe À TRAVERS son proxy `/api`,
 *  jamais sur son propre port : le cookie de session doit être posé sur l'hôte que le
 *  navigateur visitera, sans quoi il ne serait jamais renvoyé. */
export const ORIGINE = 'http://127.0.0.1:5189'

/** Session du compte de démonstration : écrite ici par `preparation()`, lue par
 *  `playwright.config.ts` (`use.storageState`). Ignorée par git — c'est un cookie. */
export const CHEMIN_ETAT_SESSION = resolve(import.meta.dirname, '.session-demo.json')

/**
 * Crée le compte de démonstration, l'enrôle au second facteur et ouvre sa session.
 *
 * Il ne suffit pas de le créer une fois à la main : les tests d'intégration vident les
 * tables, donc le compte disparaît entre deux exécutions. Une suite qui dépend d'un
 * geste extérieur n'est pas reproductible — c'est la leçon d'ERREURS.md #006, appliquée
 * ici aux données et non plus aux migrations.
 *
 * **La session est ouverte ICI, une fois, et partagée par tous les tests.** Le second
 * facteur est obligatoire : se connecter par l'écran dans chaque test exigerait un code
 * TOTP à chaque fois, et l'anti-rejeu refuse un code déjà consommé dans sa fenêtre de
 * 30 s — deux tests consécutifs se seraient disputé le même code. Les helpers `connecter`
 * des fichiers de tests voient la barre de navigation et n'ont plus rien à faire.
 */
export default async function preparation() {
  const racine = resolve(import.meta.dirname, '../..')
  const courriel = process.env.MYCOUNTS_COURRIEL_TEST
  const motDePasse = process.env.MYCOUNTS_MOT_DE_PASSE_TEST
  if (!courriel || !motDePasse) {
    throw new Error(
      'MYCOUNTS_COURRIEL_TEST et MYCOUNTS_MOT_DE_PASSE_TEST sont requis — utiliser « make tests-e2e ».',
    )
  }

  const python = resolve(racine, '.venv/bin/python')
  const environnement = { ...process.env, MYCOUNTS_MOT_DE_PASSE_INITIAL: motDePasse }

  execFileSync(
    python,
    [
      '-m',
      'scripts.creer_premier_compte',
      "Foyer d'essai",
      courriel,
      'Essai',
      '--ignorer-si-existe',
    ],
    { cwd: racine, env: environnement, stdio: 'inherit' },
  )

  // Les comptes et opérations du foyer de démonstration sont effacés — et le second
  // facteur retiré : sans cela, chaque exécution mesure un état cumulé et un locator qui
  // attend une ligne en trouve trois.
  execFileSync(python, ['-m', 'scripts.reinitialiser_foyer_essai'], {
    cwd: racine,
    env: environnement,
    stdio: 'inherit',
  })

  await enrolerEtOuvrirLaSession(python, racine, courriel, motDePasse)
}

async function enrolerEtOuvrirLaSession(
  python: string,
  racine: string,
  courriel: string,
  motDePasse: string,
) {
  const api = await request.newContext({ baseURL: ORIGINE })
  try {
    const connexion = await api.post('/api/auth/connexion', {
      data: { courriel, mot_de_passe: motDePasse },
    })
    await exiger(connexion, 'connexion du compte de démonstration')

    // Le vrai parcours d'enrôlement, pas un secret posé en base : c'est lui que les
    // utilisateurs suivent, et c'est donc lui que la suite doit savoir traverser.
    const preparation = await api.post('/api/auth/moi/second-facteur/preparer')
    await exiger(preparation, 'préparation du second facteur')
    const { secret } = (await preparation.json()) as { secret: string }

    // pyotp est déjà l'auteur du calcul côté serveur et côté tests d'intégration : un
    // second calculateur en JavaScript serait une seconde règle. Le secret passe par
    // l'entrée standard, jamais en argument — un argument est lisible dans `ps`.
    const code = execFileSync(
      python,
      ['-c', 'import pyotp, sys; print(pyotp.TOTP(sys.stdin.read().strip()).now())'],
      { cwd: racine, input: secret, encoding: 'utf8' },
    ).trim()

    const activation = await api.post('/api/auth/moi/second-facteur/activer', {
      data: { code, faire_confiance: false },
    })
    await exiger(activation, 'activation du second facteur')

    const etat = await api.storageState()
    writeFileSync(
      CHEMIN_ETAT_SESSION,
      JSON.stringify(
        {
          cookies: etat.cookies,
          /* Chaque test part de la vue PERSONNELLE, le défaut de l'application.
           *
           * La vue est conservée dans `localStorage` (voir `design/vue.ts`) : elle survit
           * d'un test à l'autre. Depuis qu'un périmètre sans compte n'affiche plus que
           * son invitation, un test laissé en vue foyer fait échouer le suivant. Poser
           * l'état ici plutôt que dans les vingt fichiers de tests : une valeur par
           * défaut a un auteur. `vue-foyer.spec.ts` bascule explicitement, c'est son
           * sujet. */
          origins: [
            { origin: ORIGINE, localStorage: [{ name: 'mycounts.vue', value: 'personnelle' }] },
          ],
        },
        null,
        2,
      ),
    )
  } finally {
    await api.dispose()
  }
}

async function exiger(reponse: APIResponse, etape: string) {
  if (reponse.ok()) return
  throw new Error(`${etape} : ${reponse.status()} ${await reponse.text()}`)
}
