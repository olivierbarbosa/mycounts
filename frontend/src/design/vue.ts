/**
 * Périmètre regardé : ses propres comptes, ou ceux du foyer.
 *
 * Deux mondes ÉTANCHES, décidé par Olivier le 21 août 2026 : on répond à « combien j'ai »
 * ou à « combien on a », jamais aux deux mélangés.
 *
 * **La vue vit ici et non dans un état React** parce que `api/client.ts` doit la lire à
 * chaque requête, y compris depuis des appels que personne n'a passés en paramètre. Un
 * contexte React obligerait à traverser toute l'application pour une valeur que seul le
 * client HTTP consulte.
 *
 * **Elle est conservée dans `localStorage`**, contrairement à la session. La règle du
 * projet — « la session vit dans un cookie httpOnly, jamais en localStorage » — protège un
 * SECRET ; la vue n'en est pas un et ne donne accès à rien : le serveur décide du
 * périmètre à partir du cookie, la vue ne fait que choisir lequel de ses deux mondes
 * regarder. Un attaquant qui la modifierait verrait ses propres comptes.
 */

const CLE = 'mycounts.vue'

export type Vue = 'personnelle' | 'foyer'

/** En-tête attendu par le serveur. Écrit ici ET dans `api/dependances.py` : c'est un
 *  contrat entre deux programmes, et le seul endroit où le nom pouvait être unique serait
 *  un schéma généré — ce que FastAPI ne fait pas pour les en-têtes de dépendance. */
export const EN_TETE_VUE = 'X-Mycounts-Vue'

let courante: Vue = lire()

function lire(): Vue {
  try {
    return localStorage.getItem(CLE) === 'foyer' ? 'foyer' : 'personnelle'
  } catch {
    // Navigation privée, stockage refusé : on retombe sur le défaut sûr plutôt que de
    // faire échouer le démarrage de l'application pour un confort d'affichage.
    return 'personnelle'
  }
}

export function vueCourante(): Vue {
  return courante
}

export function changerDeVue(vue: Vue): void {
  courante = vue
  try {
    localStorage.setItem(CLE, vue)
  } catch {
    // Non conservée d'une session à l'autre, mais utilisable pendant celle-ci.
  }
}
