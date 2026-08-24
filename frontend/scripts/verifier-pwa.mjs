import { access, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const racine = resolve(import.meta.dirname, '..')
const manifeste = JSON.parse(await readFile(resolve(racine, 'dist/manifest.webmanifest'), 'utf8'))
const serviceWorker = await readFile(resolve(racine, 'dist/service-worker.js'), 'utf8')

function exiger(condition, message) {
  if (!condition) throw new Error(`PWA invalide : ${message}`)
}

exiger(manifeste.display === 'standalone', 'le manifest ne demande pas le mode standalone')
exiger(manifeste.start_url === '/', 'le point de départ doit rester sur la même origine')
exiger(
  manifeste.icons.some((icone) => icone.sizes === '512x512' && icone.purpose === 'maskable'),
  'l’icône maskable 512 px manque',
)

for (const icone of manifeste.icons) {
  await access(resolve(racine, 'dist', icone.src.replace(/^\//, '')))
}

// Le bundle est minifié, mais ces constantes de politique restent littérales. Leur
// absence signifie que le garde-fou réseau seul a disparu du build réellement livré.
exiger(serviceWorker.includes('/api/'), 'la frontière /api n’est pas reconnue')
exiger(serviceWorker.includes('no-store'), 'les requêtes sensibles ne forcent plus no-store')
exiger(serviceWorker.includes('credentials:`include`'), 'la session cookie ne suit plus les requêtes')
exiger(!serviceWorker.includes('url":"api/'), 'une route API a glissé dans le précache')

console.log('Manifest, icônes et politique de cache PWA vérifiés.')
