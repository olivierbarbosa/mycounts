import { afterEach, describe, expect, it, vi } from 'vitest'

import { creerPlateformeNative } from '../native'
import { creerPlateformeWeb } from '../web'

afterEach(() => vi.unstubAllGlobals())

describe('transport de session par plateforme', () => {
  it('ne lit ni n’écrit jamais de jeton web dans localStorage', async () => {
    const stockage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    }
    vi.stubGlobal('localStorage', stockage)
    vi.stubGlobal('navigator', { userAgent: 'Mozilla/5.0', onLine: true })
    vi.stubGlobal('window', {
      matchMedia: () => ({ matches: false }),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })

    const session = creerPlateformeWeb().session

    expect(session.transport).toBe('cookie-httponly')
    await expect(session.lireJetonAcces()).resolves.toBeNull()
    await expect(session.enregistrerJetonAcces('secret')).rejects.toThrow('cookie httponly')
    await session.oublierJetonAcces()
    expect(stockage.getItem).not.toHaveBeenCalled()
    expect(stockage.setItem).not.toHaveBeenCalled()
    expect(stockage.removeItem).not.toHaveBeenCalled()
  })

  it('refuse le natif tant qu’un vrai trousseau n’est pas injecté', async () => {
    const session = creerPlateformeNative().session
    expect(session.transport).toBe('jeton-court-trousseau')
    await expect(session.lireJetonAcces()).rejects.toThrow('trousseau natif')
  })

  it('confie le jeton natif au trousseau injecté', async () => {
    const coffre = {
      lire: vi.fn(async () => 'jeton-court'),
      ecrire: vi.fn(async () => undefined),
      supprimer: vi.fn(async () => undefined),
    }
    const session = creerPlateformeNative(coffre).session

    await expect(session.lireJetonAcces()).resolves.toBe('jeton-court')
    await session.enregistrerJetonAcces('nouveau')
    await session.oublierJetonAcces()

    expect(coffre.lire).toHaveBeenCalledWith('session.acces')
    expect(coffre.ecrire).toHaveBeenCalledWith('session.acces', 'nouveau')
    expect(coffre.supprimer).toHaveBeenCalledWith('session.acces')
  })
})
