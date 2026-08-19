import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/** Chemins servis par l'API. En développement ils sont relayés vers uvicorn ; en
 *  production le reverse proxy du VPS les sert depuis la MÊME origine que le front.
 *  Même origine des deux côtés : le cookie de session part sans configuration CORS et
 *  « samesite=lax » reste pleinement efficace. */
const CHEMINS_API = ['/auth', '/health']

export default defineConfig({
  plugins: [react()],
  server: {
    // Explicitement IPv4 : par défaut Vite n'écoute qu'en IPv6 ([::1]), et le backend
    // écoute en IPv4. Deux piles différentes des deux côtés du proxy, c'est une heure
    // perdue à chercher une panne qui n'existe pas.
    host: '127.0.0.1',
    port: 5189,
    // Sans « strictPort », Vite bascule EN SILENCE sur le port suivant quand le sien est
    // pris. Un autre projet occupait 5175 et j'ai validé contre SON application sans
    // m'en apercevoir : le navigateur affichait un back-office qui n'est pas le nôtre.
    // Mieux vaut un démarrage qui échoue qu'une vérification qui ment (ERREURS.md #007).
    strictPort: true,
    proxy: Object.fromEntries(
      CHEMINS_API.map((chemin) => [
        chemin,
        { target: 'http://127.0.0.1:8010', changeOrigin: false },
      ]),
    ),
  },
})
