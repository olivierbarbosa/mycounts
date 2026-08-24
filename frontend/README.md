# Interface MyCounts

Application React mobile d'abord, livrée sur le web sous forme de PWA installable.

## Développement

```bash
npm install
npm run dev
npm test
npm run lint
npm run build
```

Le build produit le manifest et le service worker, puis vérifie automatiquement que les
icônes existent et que `/api` reste réseau seul avec `cache: no-store`. Le service worker
ne persiste que `index.html`, les bundles versionnés et les ressources graphiques. Il ne
met jamais en cache une réponse financière, un relevé importé ou une conversation du
coach.

Les icônes PNG sont reproductibles depuis `public/app-icon.svg` :

```bash
npm run icons
```

## Préparation iOS et Android

Capacitor est configuré, sans projet natif généré dans le dépôt. Après stabilisation de
la PWA :

```bash
npm run native:add:ios
npm run native:add:android
npm run native:sync
```

La couche `src/plateforme/` sépare réseau, installation, notifications, fichiers, liens,
cycle de vie et transport de session. Sur le web, la session reste exclusivement dans le
cookie `httponly`. L'adaptateur natif refuse de démarrer son transport tant qu'un véritable
trousseau iOS/Keystore Android ne lui est pas injecté ; il n'existe aucun repli vers
`localStorage`.
