/** Liste positive inversée : tout le métier vit sous `/api`, donc une route nouvelle y
 * est protégée sans qu'il faille penser à l'ajouter ici. `/health` reste réseau seul par
 * défense en profondeur, même s'il n'est pas exposé en production. */
export function estApiOuDonneeSensible(url: URL) {
  return (
    url.pathname === '/api' ||
    url.pathname.startsWith('/api/') ||
    url.pathname === '/health' ||
    url.pathname.startsWith('/health/')
  )
}
