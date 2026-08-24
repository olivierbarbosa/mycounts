import { describe, expect, it } from 'vitest'

import { cheminNotification, contenuNotification } from '../notifications'

describe('notifications discrètes', () => {
  it('ignore tout texte libre et ne rend qu’un message générique connu', () => {
    expect(contenuNotification('budget').corps).toBe('Un budget demande votre attention.')
    expect(contenuNotification({ montant: '12 345 €' }).corps).toBe(
      'Une information vous attend dans l’application.',
    )
  })

  it('refuse qu’une notification ouvre un autre site', () => {
    expect(cheminNotification('/budget?mois=8', 'https://mycounts.app')).toBe('/budget?mois=8')
    expect(cheminNotification('https://piege.example/vol', 'https://mycounts.app')).toBe('/')
    expect(cheminNotification('pas une url', 'https://mycounts.app')).toBe('/pas%20une%20url')
  })
})
