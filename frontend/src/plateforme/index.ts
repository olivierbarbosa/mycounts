import { Capacitor } from '@capacitor/core'

import type { Plateforme } from './contrat'
import { creerPlateformeNative } from './native'
import { creerPlateformeWeb } from './web'

export type { EtatInstallation, EtatNotification, Plateforme } from './contrat'

export const plateforme: Plateforme =
  typeof window !== 'undefined' && Capacitor.isNativePlatform()
  ? creerPlateformeNative()
  : creerPlateformeWeb()
