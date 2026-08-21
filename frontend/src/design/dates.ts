/**
 * Lecture des dates civiles envoyées par le serveur.
 *
 * Extrait d'`Accueil.tsx` le 22 août 2026, quand l'écran des enveloppes a eu besoin de la
 * même chose : une seconde copie de `dateCivile` aurait été une seconde occasion
 * d'oublier le piège du fuseau, et rien n'aurait signalé la divergence.
 */

/** Parse une date ISO en date LOCALE, sans passer par UTC.
 *
 *  `new Date('2026-08-19')` est interprété en UTC et peut afficher le 18 selon le fuseau
 *  du navigateur. Le serveur envoie une date civile : elle doit rester telle quelle. */
export function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

const MOIS_ET_ANNEE = new Intl.DateTimeFormat('fr-FR', { month: 'long', year: 'numeric' })

/** « novembre 2026 ». L'échéance d'un projet se dit au mois, jamais au jour : personne ne
 *  vise le 30 novembre pour un voyage, et afficher un jour précis donnerait à une
 *  approximation l'air d'un engagement. */
export function moisEtAnnee(iso: string): string {
  return MOIS_ET_ANNEE.format(dateCivile(iso))
}
