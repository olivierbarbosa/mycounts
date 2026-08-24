import { describe, expect, it } from 'vitest'

import { estApiOuDonneeSensible } from '../politiqueCache'

describe('politique de cache PWA', () => {
  it.each([
    '/api',
    '/api/comptes',
    '/api/imports/releve',
    '/api/coach/conversations',
    '/health',
  ])('interdit tout cache persistant pour %s', (chemin) => {
    expect(estApiOuDonneeSensible(new URL(chemin, 'https://mycounts.app'))).toBe(true)
  })

  it.each(['/', '/index.html', '/assets/application.js', '/pwa/icon-192.png'])(
    'autorise le shell statique pour %s',
    (chemin) => {
      expect(estApiOuDonneeSensible(new URL(chemin, 'https://mycounts.app'))).toBe(false)
    },
  )
})
