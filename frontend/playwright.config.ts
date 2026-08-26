import { defineConfig } from '@playwright/test'

import { CHEMIN_ETAT_SESSION } from './e2e/preparation'

/** Trois tailles réelles : téléphone, tablette, bureau. Le garde-fou n°10 vérifie sur
 *  chacune qu'aucun débordement horizontal n'apparaît et que toute cible tactile atteint
 *  44 px — la mesure échoue immédiatement sur une grille figée en pixels. */
/* Deux téléphones et non un seul, et l'un des deux sous Android : Olivier utilise
   l'application en web app sur iPhone, mais un `env(safe-area-inset-*)` oublié ou une
   largeur juste ne se voient qu'à la taille où ils cassent. 375 est le plus étroit encore
   en service, 430 le plus large — c'est entre ces deux bornes que la rangée du haut doit
   tenir. Le Pixel 7 y ajoute un inset haut différent de ceux d'iOS. */
export const VIEWPORTS = [
  { nom: 'iPhone SE', width: 375, height: 667 },
  { nom: 'iPhone 14', width: 390, height: 844 },
  { nom: 'Pixel 7', width: 412, height: 915 },
  { nom: 'iPhone 15 Pro Max', width: 430, height: 932 },
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
    /* La session du compte de démonstration, ouverte UNE fois par `e2e/preparation.ts`
       après l'enrôlement au second facteur — obligatoire depuis le lot identité. Chaque
       test la reçoit déjà ouverte, avec la vue personnelle posée dans `localStorage`. Les
       tests qui mesurent la page de connexion effacent d'abord leurs cookies. */
    storageState: CHEMIN_ETAT_SESSION,
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
