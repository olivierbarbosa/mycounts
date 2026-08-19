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
  use: {
    baseURL: 'http://127.0.0.1:5189',
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
