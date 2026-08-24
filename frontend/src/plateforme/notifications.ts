export type TypeNotification =
  | 'budget'
  | 'charge'
  | 'seuil-securite'
  | 'epargne'
  | 'invitation'
  | 'foyer'
  | 'securite'

const CONTENUS: Record<TypeNotification, { corps: string; etiquette: string }> = {
  budget: { corps: 'Un budget demande votre attention.', etiquette: 'budget' },
  charge: { corps: 'Une charge arrive bientôt.', etiquette: 'charge' },
  'seuil-securite': {
    corps: 'Votre solde projeté demande votre attention.',
    etiquette: 'seuil-securite',
  },
  epargne: { corps: 'Votre proposition d’épargne est prête.', etiquette: 'epargne' },
  invitation: { corps: 'Vous avez reçu une invitation.', etiquette: 'invitation' },
  foyer: { corps: 'Un changement important concerne votre foyer.', etiquette: 'foyer' },
  securite: { corps: 'Vérifiez une activité de sécurité récente.', etiquette: 'securite' },
}

export function contenuNotification(type: unknown) {
  return typeof type === 'string' && type in CONTENUS
    ? CONTENUS[type as TypeNotification]
    : { corps: 'Une information vous attend dans l’application.', etiquette: 'information' }
}

/** Une notification ne peut ouvrir qu'un chemin de MyCounts. Une URL externe ou
 * malformée retombe sur l'accueil, même si le serveur envoyait un payload compromis. */
export function cheminNotification(destination: unknown, origine: string) {
  if (typeof destination !== 'string') return '/'
  try {
    const url = new URL(destination, origine)
    return url.origin === origine ? `${url.pathname}${url.search}${url.hash}` : '/'
  } catch {
    return '/'
  }
}
