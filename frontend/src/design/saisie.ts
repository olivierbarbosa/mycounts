/**
 * Conversion d'une saisie utilisateur en centimes.
 *
 * Miroir CLIENT de `domain/montants.parse_montant` — mais **le serveur reste seul juge** :
 * cette fonction sert uniquement à donner un retour immédiat pendant la frappe. Toute
 * valeur envoyée est revalidée côté serveur, qui rejette ce qu'il n'accepte pas.
 *
 * Ne jamais passer par un flottant : `Number('12,50')` puis `× 100` ferait rentrer
 * l'imprécision binaire par la porte du client.
 */

const SAISIE = /^(?<signe>[-+])?(?<entier>\d{1,15})(?:[.,](?<decimales>\d{1,2}))?$/

export class SaisieInvalide extends Error {}

export function enCentimes(saisie: string): number {
  const texte = saisie.replace(/[\s  ]/g, '').replace('€', '')
  if (!texte) throw new SaisieInvalide('Montant vide.')

  const trouve = SAISIE.exec(texte)
  if (!trouve?.groups) {
    throw new SaisieInvalide('Montant illisible. Exemple : 12,50')
  }

  const { signe, entier, decimales = '' } = trouve.groups
  const centimes = Number(entier) * 100 + Number(decimales.padEnd(2, '0') || '0')
  if (!Number.isSafeInteger(centimes)) {
    throw new SaisieInvalide('Montant trop grand.')
  }
  return signe === '-' ? -centimes : centimes
}
