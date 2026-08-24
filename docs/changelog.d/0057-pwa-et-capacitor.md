# PWA installable et frontière native

- MyCounts possède désormais un manifest, des icônes standard et maskable, les métadonnées
  iOS ainsi qu'un écran d'installation guidé dans les paramètres.
- Le service worker conserve uniquement le shell versionné. Toute route `/api` ou
  `/health` reste réseau seul avec `cache: no-store` ; hors ligne, aucun montant ni relevé
  n'est ressorti d'un cache persistant.
- Une mise à jour attend la validation de l'utilisateur avant de remplacer la version en
  cours. L'état hors ligne explique clairement pourquoi les comptes ne sont pas affichés.
- La couche de plateforme isole réseau, installation, notifications, fichiers, liens,
  cycle de vie et session. Le web utilise le cookie `httponly`; le futur natif exige un
  trousseau et ne replie jamais un jeton vers `localStorage`.
- Capacitor, ses scripts iOS/Android et son fichier de configuration sont prêts, sans
  générer prématurément les lourds projets natifs.
