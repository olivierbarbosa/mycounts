/**
 * Formulation d'une cadence en toutes lettres.
 *
 * Auteur unique : « tous les 3 mois » doit s'écrire pareil dans l'agenda, la feuille de
 * saisie et la liste des récurrences. Trois formulations pour la même donnée, et
 * l'utilisateur croit à trois choses différentes.
 */

export type UniteCadence = 'jour' | 'semaine' | 'mois' | 'an'

const SINGULIERS: Record<UniteCadence, string> = {
  jour: 'tous les jours',
  semaine: 'toutes les semaines',
  mois: 'tous les mois',
  an: 'tous les ans',
}

const PLURIELS: Record<UniteCadence, string> = {
  jour: 'jours',
  semaine: 'semaines',
  mois: 'mois',
  an: 'ans',
}

const FEMININ: ReadonlySet<UniteCadence> = new Set<UniteCadence>(['semaine'])

export function frequenceEnToutesLettres(unite: UniteCadence, intervalle: number): string {
  if (intervalle <= 1) return SINGULIERS[unite]
  const article = FEMININ.has(unite) ? 'toutes les' : 'tous les'
  return `${article} ${intervalle} ${PLURIELS[unite]}`
}

/** Forme courte pour les espaces contraints d'un calendrier. */
export function frequenceCourte(unite: UniteCadence, intervalle: number): string {
  const abreviations: Record<UniteCadence, string> = {
    jour: 'j',
    semaine: 'sem',
    mois: 'mois',
    an: 'an',
  }
  return intervalle <= 1 ? `/${abreviations[unite]}` : `/${intervalle}${abreviations[unite]}`
}
