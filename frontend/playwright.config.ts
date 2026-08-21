import { defineConfig } from '@playwright/test'

/** Trois tailles réelles : téléphone, tablette, bureau. Le garde-fou n°10 vérifie sur
 *  chacune qu'aucun débordement horizontal n'apparaît et que toute cible tactile atteint
 *  44 px — la mesure échoue immédiatement sur une grille figée en pixels. */
export const VIEWPORTS = [
  { nom: 'mobile', width: 390, height: 844 },
  { nom: 'tablette', width: 820, height: 1180 },
  { nom: 'bureau', width: 1280, height: 800 },
] as const

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  /* Le compte de démonstration est (re)créé avant la suite : les tests d'intégration
     vident les tables, donc il ne survit pas d'une exécution à l'autre. */
  globalSetup: './e2e/preparation.ts',
  use: {
    baseURL: 'http://127.0.0.1:5189',
    /* Chaque test part de la vue PERSONNELLE, le défaut de l'application.
     *
     * La vue est conservée dans `localStorage` (voir `design/vue.ts`) : elle survit d'un
     * test à l'autre. Tant que les deux vues affichaient la même chose, l'oubli était
     * sans conséquence ; depuis qu'un périmètre sans compte n'affiche plus que son
     * invitation, un test laissé en vue foyer fait échouer le suivant — qui cherche un
     * écran que sa propre exécution n'a pas rendu vide. Poser l'état ici plutôt que dans
     * les dix-huit fichiers de tests : une valeur par défaut a un auteur, pas dix-huit.
     *
     * `vue-foyer.spec.ts` bascule explicitement, c'est son sujet. */
    storageState: {
      cookies: [],
      origins: [
        {
          origin: 'http://127.0.0.1:5189',
          localStorage: [{ name: 'mycounts.vue', value: 'personnelle' }],
        },
      ],
    },
  },
  /* Playwright démarre lui-même les deux serveurs : les tests ne dépendent donc d'aucun
     processus lancé à la main. C'est exactement la leçon d'ERREURS.md #006 — une
     vérification dont le périmètre inclut le shell de l'opérateur ne prouve rien. */
  webServer: [
    {
      command:
        'cd .. && .venv/bin/python -m uvicorn mycounts.api.app:app --app-dir backend --port 8010 --host 127.0.0.1',
      url: 'http://127.0.0.1:8010/health',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5189',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
