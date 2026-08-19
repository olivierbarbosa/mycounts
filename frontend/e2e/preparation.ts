import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

/**
 * Crée le compte de démonstration avant la suite de tests.
 *
 * Il ne suffit pas de le créer une fois à la main : les tests d'intégration vident les
 * tables, donc le compte disparaît entre deux exécutions. Une suite qui dépend d'un
 * geste extérieur n'est pas reproductible — c'est la leçon d'ERREURS.md #006, appliquée
 * ici aux données et non plus aux migrations.
 */
export default function preparation() {
  const racine = resolve(import.meta.dirname, '../..')
  const courriel = process.env.MYCOUNTS_COURRIEL_TEST
  const motDePasse = process.env.MYCOUNTS_MOT_DE_PASSE_TEST
  if (!courriel || !motDePasse) {
    throw new Error(
      'MYCOUNTS_COURRIEL_TEST et MYCOUNTS_MOT_DE_PASSE_TEST sont requis — utiliser « make tests-e2e ».',
    )
  }

  execFileSync(
    resolve(racine, '.venv/bin/python'),
    ['-m', 'scripts.creer_premier_compte', "Foyer d'essai", courriel, 'Essai', '--ignorer-si-existe'],
    {
      cwd: racine,
      env: { ...process.env, MYCOUNTS_MOT_DE_PASSE_INITIAL: motDePasse },
      stdio: 'inherit',
    },
  )
}
