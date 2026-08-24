/** Espace financier actif, conservé sans jamais devenir une autorisation.
 *
 * Le serveur revérifie l'appartenance à chaque requête. La valeur locale ne sert qu'à
 * retrouver le dernier contexte ; si elle est périmée, l'API retombe sur le personnel.
 */

const CLE = 'mycounts.espace'

export const EN_TETE_ESPACE = 'X-Mycounts-Espace'

let courant: string | null = lire()

function lire(): string | null {
  try {
    return localStorage.getItem(CLE)
  } catch {
    return null
  }
}

export function espaceCourant(): string | null {
  return courant
}

export function changerEspace(espaceId: string | null): void {
  courant = espaceId
  try {
    if (espaceId === null) localStorage.removeItem(CLE)
    else localStorage.setItem(CLE, espaceId)
  } catch {
    // La bascule reste valable pour la session, même si le stockage est refusé.
  }
}

