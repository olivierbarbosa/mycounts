# Identité publique et MFA obligatoire

- ajout de l’inscription configurable, de la vérification d’adresse et de la récupération
  du mot de passe par jetons opaques à usage unique ;
- file d’envoi transactionnelle et worker SMTP OVH/Zimbra, sans donnée financière dans
  les messages ni les journaux ;
- accès aux données financières bloqué tant que l’adresse n’est pas vérifiée et le TOTP
  activé ;
- parcours mobile dédié au premier enrôlement, codes de récupération et confirmation de
  leur sauvegarde ;
- appareils fiables pendant trente jours avec rotation du secret, liste et révocation ;
- changement de mot de passe, d’adresse ou de facteur révoquant les appareils fiables et
  les sessions concernées ;
- page de connexion transformée en parcours d’application : identifiants, MFA,
  inscription, vérification et récupération tiennent chacun dans un écran sans
  défilement.
- intégration sur les espaces multiples : une inscription crée une identité dont le seul
  espace initial est PERSONNEL (`creer_identite_personnelle`), et `principal_identite`
  résout l’espace personnel sans exiger le second facteur ;
- tests de bout en bout sous MFA obligatoire : `reinitialiser_foyer_essai` retire le
  second facteur, `e2e/preparation.ts` refait l’enrôlement par l’API et écrit la session
  ouverte en `storageState` — aucun test ne se connecte plus par l’écran, l’anti-rejeu TOTP
  l’interdirait ; le spec du second facteur mesure désormais l’écran d’enrôlement.
