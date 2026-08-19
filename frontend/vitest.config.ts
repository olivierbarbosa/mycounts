import { defineConfig } from 'vitest/config'

/** Vitest ne couvre que les fonctions pures du frontend. Les fichiers `e2e/` relèvent de
 *  Playwright : sans cette exclusion, Vitest tente de les exécuter et échoue sur
 *  `test.describe` qu'il ne connaît pas. */
export default defineConfig({
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
