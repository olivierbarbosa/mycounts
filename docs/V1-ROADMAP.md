# MyCounts V1 — feuille de route

Cette feuille de route privilégie la justesse et l'isolation avant les fonctions visibles.
« Terminé » signifie testé, migrable, observable et documenté, pas seulement affiché.

Chaque lot visible respecte en même temps la direction actuelle et le contrat UX de
`V1-PRODUIT.md` : mobile d'abord, minimum de gestes, une action principale par étape et
aucune modale à faire défiler. Ce contrôle n'est jamais reporté au lot de finition.

## Lot 0 — Figer la V1 et mesurer l'existant

Durée indicative : 2 à 4 jours.

- Adopter `V1-PRODUIT.md` et `V1-ARCHITECTURE.md` comme références.
- Transformer les décisions en scénarios d'acceptation.
- Produire quatre fichiers d'import anonymisés : CSV et PDF pour Revolut et Caisse
  d'Épargne.
- Inventorier le schéma et les endpoints touchés par le passage aux espaces.
- Capturer les invariants et sommes de la base actuelle pour la migration.
- Inventorier les composants et tokens existants à réutiliser ; définir le gabarit unique
  des modales sans défilement et des parcours multi-étapes.

Sortie : périmètre figé, fixtures représentatives et aucune question métier bloquante.

## Lot 1 — Fiabilité et sécurité du socle

Durée indicative : 1 à 2 semaines.

- Corriger les PATCH nullable et ajouter les tests de régression.
- Faire vérifier PostgreSQL par `/health`.
- Ajouter rate limiting pour connexion, MFA, récupération et invitations.
- Empêcher la réutilisation TOTP et durcir les sessions.
- Ajouter monitoring, erreurs frontend/backend et alertes d'exploitation sans données
  financières dans les logs.
- Sauvegarde hors serveur, test réel de restauration et procédure de rollback.
- Faire dépendre le déploiement du succès de la CI ; ajouter lint frontend, contrats et
  smoke test de l'image de production.

Sortie : incident détectable, sauvegarde restaurable et déploiement réversible.

## Lot 2 — Espaces financiers et migration

Durée indicative : 2 à 3 semaines.

- Ajouter `Espace`, `Appartenance`, rôles et invitations ciblées.
- Porter le périmètre explicite dans les repositories et l'API.
- Ajouter le sélecteur d'espace atomique au frontend.
- Migrer sans perte les comptes privés et joints existants.
- Implémenter création, arrivée, départ, transfert de propriété et suppression d'un foyer.
- Ajouter tests d'autorisation croisés et tests de propriétés d'isolation.

Sortie : un utilisateur peut avoir plusieurs foyers et aucune donnée ne traverse un
espace sans autorisation.

## Lot 3 — Identité publique et emails

Durée indicative : 1 à 2 semaines.

- Inscription, vérification d'adresse et mot de passe oublié.
- Faire évoluer l'écran d'entrée mobile déjà livré : identifiants en un geste, puis MFA
  seulement lorsque nécessaire, sans carte de login générique ni modale défilante, avec
  autofill et gestionnaires de mots de passe correctement déclarés.
- TOTP obligatoire, codes de récupération et appareils de confiance révocables.
- Définir dès ce lot les deux transports de session : cookie web/PWA et jetons courts
  renouvelables pour le futur conteneur natif.
- Procédure de récupération manuelle documentée.
- SMTP OVH/Zimbra via boîte d'envoi transactionnelle et worker.
- SPF, DKIM, DMARC et tests Gmail/Outlook.
- Emails d'invitation et de sécurité.

Sortie : un inconnu peut créer et récupérer son compte sans intervention serveur ; la
phase privée peut rester sur invitations jusqu'à la décision d'ouverture.

## Lot 4 — Cycles fiables et nouveau tableau de bord

Durée indicative : 1 à 2 semaines.

- Persister les cycles réels et leur ouverture explicite.
- Rendre les cycles clos immuables hors correction auditée.
- Séparer prochaine paie estimée et bornes réelles.
- Refaire le calcul du reste disponible : charges, budgets, sécurité et épargne.
- Distinguer budgets réinitialisés et enveloppes cumulatives.
- Tester revenus multiples, retard de paie, période initiale, découvert et correction
  historique.
- Tester qu'une opération rétroactive modifie au besoin les agrégats du cycle explicitement
  choisi sans jamais en déplacer les bornes.

Sortie : ajouter ou supprimer une ancienne paie ne déplace jamais silencieusement une
période close.

## Lot 5 — Onboarding et import multibanque

Durée indicative : 2 à 4 semaines selon les PDF reçus.

- Onboarding MFA, comptes, soldes, seuil de sécurité, prochaine paie et imports.
- Découper l'onboarding et la revue d'import en étapes courtes reprenables, sans modale
  défilante ni double saisie.
- Pipeline temporaire et suppression garantie des fichiers.
- Profils certifiés Revolut et Caisse d'Épargne en CSV et PDF officiel.
- Parseur générique expérimental avec seuil de confiance et refus sûr.
- Rapport, aperçu, idempotence et gestion des lignes ignorées.
- Détection des récurrences présentes dans les trois relevés et validation utilisateur.
- Matérialisation automatique, rapprochement manuel et totaux mensuel/annuel.

Sortie : le même fichier peut être importé deux fois sans changer le solde ; aucun PDF
incertain ne devient silencieusement de l'argent réel.

## Lot 6 — Épargne, enveloppes et moteur d'aide

Durée indicative : 2 à 3 semaines.

- Agréger les comptes d'épargne stables en réserve réelle.
- Mettre en œuvre les deux types d'enveloppes et leur journal d'affectation.
- Garantir la couverture des enveloppes par l'épargne réelle.
- Garantir les affectations en centimes exacts et la désaffectation déterministe sur tous
  les chemins qui réduisent l'épargne.
- Gérer le virement manuel confirmé et le retrait inverse.
- Construire le moteur déterministe prudent/recommandé/ambitieux.
- Apprendre des cycles terminés et isoler les dépenses exceptionnelles confirmées.
- Modal de paie et validation propriétaire/admin dans un foyer.
- Garantir que la paie puis la répartition d'épargne se valident avec les valeurs utiles
  visibles, sans défilement et sans recharger un autre écran entre chaque étape.

Sortie : chaque euro affecté existe réellement dans l'épargne et chaque recommandation
est reproductible sans IA.

## Lot 7 — Coach IA avec consentement

Durée indicative : 1 à 2 semaines.

- Consentements par utilisateur et espace, agrégé puis détaillé.
- Unanimité des membres actifs pour un foyer.
- Constructeur de contexte minimal et isolé.
- OpenRouter ZDR, collecte interdite, allowlist, plafond de coût et arrêt sûr.
- Suggestions de capacité et de répartition expliquées.
- Chat libre privé par membre, recommandations appliquées partagées.
- Révocation et suppression de l'historique.
- Tests prouvant que l'application reste complète sans OpenRouter.

Sortie : aucune donnée n'est envoyée sans consentement et aucune réponse IA ne contourne
le moteur financier.

## Lot 8 — PWA, push, droits et finition de la bêta

Durée indicative : 1 à 2 semaines.

- Manifest, icônes, installation et stratégie de cache sûre.
- Abonnements Web Push, centre interne et préférences.
- Alertes budget, charge, seuil de sécurité, coach et foyer.
- Export portable et suppression/anonymisation.
- Mentions légales, confidentialité, CGU et information OpenRouter.
- Accessibilité, performance et E2E sur les parcours critiques.
- E2E de chaque état de modale avec libellés longs, erreurs, clavier mobile et action
  principale toujours visible.
- Guide support et traitement des retours de la famille et des amis.

Sortie : bêta privée installable et exploitable sans accès direct au serveur.

## Lot 9 — Passage de privé à public

Durée : dictée par les retours, pas par une date arbitraire.

- Corriger tous les défauts de justesse ou d'isolation de la bêta.
- Tester une restauration récente en préproduction.
- Vérifier délivrabilité email et capacité SMTP.
- Revue sécurité et confidentialité externe ou contradictoire.
- Monitoring et procédure d'incident opérationnels.
- Ouvrir progressivement l'inscription et mesurer le support nécessaire.

## Lot 10 — Applications iPhone et Android

Durée indicative : 2 à 4 semaines après stabilisation de la V1 web, hors délai de revue
des boutiques.

- Ajouter Capacitor et les projets natifs iOS/Android.
- Brancher les adaptateurs natifs : push, stockage sécurisé, biométrie, fichiers et liens
  universels/app links.
- Tester clavier, zones sûres, retour Android, cycle de vie, réseau dégradé et reprise.
- Préparer icônes, écrans de lancement, politique de confidentialité et fiches boutiques.
- Fournir un compte de démonstration complet aux équipes de revue.
- Distribuer d'abord via TestFlight et une piste de test Google Play.

Sortie : les deux applications apportent des fonctions natives utiles et partagent le
même comportement financier que la PWA.

## Ordre critique

`socle fiable → espaces → identité → cycles → imports → épargne → IA → PWA → public → natif`

Les lots visibles ne doivent pas devancer leurs invariants. En particulier, le coach ne
doit jamais devenir l'auteur des calculs et le parseur PDF ne doit jamais contourner
l'aperçu utilisateur.

## Estimation

- Première alpha familiale utile après les lots 0 à 5 : environ **8 à 12 semaines** de
  travail solo, selon la diversité réelle des relevés PDF.
- V1 privée complète avec enveloppes, IA et push : environ **12 à 18 semaines**.
- Ouverture publique : après une période de bêta mesurée et sans incident de justesse,
  pas sur la seule base d'un calendrier.

Ces estimations excluent la synchronisation bancaire, les virements réels et l'OCR.
La conversion native est estimée séparément dans le lot 10.

## Définition de terminé avant ouverture publique

- inscription, récupération et MFA testés de bout en bout ;
- isolation inter-espace testée sur chaque famille d'objet ;
- cycles clos immuables et projections explicables ;
- imports certifiés idempotents et imports expérimentaux refusés en cas de doute ;
- enveloppes toujours couvertes par l'épargne réelle ;
- désactivation d'OpenRouter sans perte de fonction financière ;
- consentements, export et suppression opérationnels ;
- sauvegarde restaurée et rollback répété ;
- PWA installable, push révocable et secrets absents du client ;
- aucune nouvelle modale défilante et aucun parcours principal inutilement dupliqué ;
- un nouvel utilisateur atteint seul un tableau de bord juste à partir de ses relevés.
