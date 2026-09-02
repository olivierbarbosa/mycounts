# PWA : une coupure réseau ne vide plus la saisie, et les messages du bas laissent la barre

**Lot** : V1-PWA-01 | **Date** : 2026-09-02

Audit mesuré sur 375, 390, 430 et 820 px, dans un vrai navigateur, avant de toucher quoi
que ce soit. Aucune erreur de console sur les écrans principaux ; la rangée du haut, les
zones sûres et les cibles tactiles tenaient déjà. Trois défauts prouvés, corrigés :

- **Une coupure réseau remplaçait tout l'écran.** iOS émet `offline` au passage du Wi-Fi
  au cellulaire ; l'application démontait alors la feuille de saisie et le montant tapé
  disparaissait. Désormais l'écran reste, un bandeau `role="status"` dit l'état, et la
  saisie se termine au retour du réseau. L'écran plein « Vous êtes hors ligne » ne vaut
  plus qu'au démarrage sans réseau, quand rien n'est à préserver. Aucune donnée n'est mise
  en attente ni stockée localement : les montants ne vivent pas sur le téléphone.
- **Le message « nouvelle version prête » se posait SUR la barre d'onglets** — à 12 px du
  bord, là où la barre flottante commence 63 px plus haut (mesuré à 375 px). La position
  des messages du bas a maintenant un auteur unique, `BandeauBas.module.css`, dans une
  réserve `--disposition-reserve-navigation` déclarée dans `tokens.ts` ; au-delà de
  1024 px, le rail est à gauche et la réserve ne s'applique plus.
- **Le manifest verrouillait le portrait et demandait `window-controls-overlay`.** Le
  premier interdisait le paysage jusque sur tablette, où le rail latéral est fait pour
  lui ; le second pose les boutons de fenêtre par-dessus la rangée du haut sans qu'aucune
  feuille ne réserve `env(titlebar-area-*)`. Les deux sont retirés.

Et une amélioration de fiabilité : la recherche de mise à jour, jusqu'ici horaire, se fait
aussi au retour au premier plan — une PWA endormie voit ses minuteries gelées, l'heure ne
s'écoulait pas pendant qu'elle dormait.

Vérifié par `frontend/e2e/pwa-fiabilite.spec.ts` : erreurs de console sur quatre largeurs,
survie du montant tapé à une coupure, bandeau au-dessus de la barre sur chaque largeur
(le test rougit à 63 px de recouvrement quand on remet l'ancienne position), écran plein
au démarrage hors ligne. Ce qu'il ne mesure PAS : la coquille servie par le service worker,
que Vite n'enregistre pas en développement — `scripts/verifier-pwa.mjs` la contrôle sur le
`dist` à chaque build.

Pas d'étape native dans ce lot : le transport Capacitor reste inactif tant que le
trousseau et les jetons courts serveur ne sont pas livrés. Une PWA qui ne survit pas à un
changement de réseau n'a rien à gagner à être emballée dans une application.
