import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

/** UN seul préfixe relayé vers uvicorn. Une liste de chemins ici serait une seconde
 *  source de vérité en face du routeur FastAPI — elle a divergé dès la première route
 *  ajoutée, et /comptes renvoyait la page HTML au lieu du JSON (ERREURS.md #015).
 *  Même origine des deux côtés : le cookie de session part sans configuration CORS et
 *  « samesite=lax » reste pleinement efficace. */
const CHEMINS_API = ['/api', '/health']

/** Ports paramétrables : la démonstration tourne sur d'autres ports que les tests, sinon
 *  Playwright (« reuseExistingServer ») se branche sur le serveur de démonstration et
 *  écrit dans sa base. */
const PORT_WEB = Number(process.env.MYCOUNTS_PORT_WEB ?? 5189)
const PORT_API = Number(process.env.MYCOUNTS_PORT_API ?? 8010)

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'pwa',
      filename: 'service-worker.ts',
      injectRegister: false,
      registerType: 'prompt',
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
      },
      manifest: {
        id: '/',
        name: 'MyCounts — Mon argent, clairement',
        short_name: 'MyCounts',
        description: 'Budgets, charges et épargne réunis dans une application simple.',
        lang: 'fr-FR',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        // Pas de « window-controls-overlay » : ce mode pose les boutons de la fenêtre
        // PAR-DESSUS la rangée du haut, et aucune feuille de style ne réserve
        // `env(titlebar-area-*)`. Pas d'`orientation` non plus : elle verrouillait le
        // portrait jusque sur tablette, là où le rail latéral est fait pour le paysage.
        display_override: ['standalone', 'minimal-ui'],
        background_color: '#0F172A',
        theme_color: '#0F172A',
        categories: ['finance', 'productivity'],
        icons: [
          { src: '/pwa/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa/icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: '/pwa/icon-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  server: {
    // 0.0.0.0 pour que l'application soit joignable depuis un autre appareil — en
    // pratique par Tailscale, dont le tunnel est chiffré de bout en bout. Le BACKEND,
    // lui, reste sur 127.0.0.1 : seul le proxy de Vite l'atteint, il n'est donc exposé
    // à aucun réseau.
    //
    // ATTENTION : ce serveur de développement ne fait PAS de HTTPS. Sur Tailscale le
    // trafic est chiffré par WireGuard, donc le mot de passe ne circule pas en clair.
    // Sur un Wi-Fi ordinaire, si. Ne pas y saisir de mot de passe réutilisé ailleurs.
    host: '0.0.0.0',
    // Vite refuse par défaut les hôtes qu'il ne connaît pas (protection anti-rebinding
    // DNS). On autorise les adresses du réseau Tailscale et le nom de la machine.
    allowedHosts: ['.ts.net', 'localhost', '127.0.0.1'],
    port: PORT_WEB,
    // Sans « strictPort », Vite bascule EN SILENCE sur le port suivant quand le sien est
    // pris. Un autre projet occupait 5175 et j'ai validé contre SON application sans
    // m'en apercevoir : le navigateur affichait un back-office qui n'est pas le nôtre.
    // Mieux vaut un démarrage qui échoue qu'une vérification qui ment (ERREURS.md #007).
    strictPort: true,
    proxy: Object.fromEntries(
      CHEMINS_API.map((chemin) => [
        chemin,
        { target: `http://127.0.0.1:${PORT_API}`, changeOrigin: false },
      ]),
    ),
  },
})
