import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import sharp from 'sharp'

const racine = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const source = resolve(racine, 'public/app-icon.svg')
const destination = resolve(racine, 'public/pwa')

await mkdir(destination, { recursive: true })

for (const taille of [180, 192, 512]) {
  const rendu = await sharp(source).resize(taille, taille).png().toBuffer()
  // Les icônes iOS ne doivent pas contenir de transparence : le système applique déjà
  // son propre masque et remplacerait sinon les coins par du noir.
  await sharp({
    create: { width: taille, height: taille, channels: 4, background: '#0F172A' },
  })
    .composite([{ input: rendu }])
    .png()
    .toFile(resolve(destination, `icon-${taille}.png`))
}

// L'icône maskable conserve une zone sûre de 80 % quel que soit le masque choisi par
// Android. Le fond reste plein bord ; seul le symbole est réduit et centré.
const symbole = await sharp(source).resize(410, 410).png().toBuffer()
await sharp({
  create: { width: 512, height: 512, channels: 4, background: '#0F172A' },
})
  .composite([{ input: symbole, left: 51, top: 51 }])
  .png()
  .toFile(resolve(destination, 'icon-maskable-512.png'))
