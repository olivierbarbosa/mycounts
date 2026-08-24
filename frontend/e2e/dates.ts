/**
 * Dates civiles pour les tests, en heure de PARIS — celle du serveur.
 *
 * `new Date().toISOString().slice(0, 10)` est un piège que ce dépôt connaît déjà côté
 * serveur — « les dates civiles sont en Europe/Paris, jamais un `::date` nu » — et qui
 * existe à l'identique en JavaScript : `toISOString()` bascule en UTC.
 *
 * Le défaut ne se voit qu'entre minuit et deux heures du matin, quand Paris a changé de
 * jour mais pas UTC. Un test qui plaçait une échéance « demain » obtenait alors la date
 * d'AUJOURD'HUI, l'échéance était matérialisée, et l'assertion sur l'à-venir échouait en
 * annonçant un dépassement déjà réalisé. Vérifié le 21 août 2026 à 00h21 : `toISOString()`
 * rendait le 21 pour « demain », `sv-SE` local rendait le 22.
 *
 * `sv-SE` n'est pas un caprice : c'est la locale dont le format court EST `AAAA-MM-JJ`,
 * ce qui évite d'assembler soi-même les morceaux et de se tromper de zéro initial.
 *
 * Et `timeZone: 'Europe/Paris'` explicitement, pas « local » : le VPS et les runners de
 * la CI vivent en UTC. Entre 22 h et minuit UTC, leur « demain » est déjà l'aujourd'hui
 * de Paris — le serveur matérialisait l'échéance et le même test rougissait de nouveau,
 * mesuré le 24 août 2026 à 22 h 11 UTC. La date civile a UN fuseau, celui du serveur.
 */
export function jourLocal(decalageEnJours = 0): string {
  const date = new Date()
  date.setDate(date.getDate() + decalageEnJours)
  return date.toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' })
}
