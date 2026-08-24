# MyCounts V1 — spécification produit

Statut : **décisions validées avec le fondateur le 24 août 2026**.

Ce document décrit la cible V1. Il remplace les anciennes décisions produit de
`docs/PLAN.md` et `CLAUDE.md` lorsqu'elles concernent l'inscription publique, le nombre
de foyers, l'import PDF, les cycles de paie, les enveloppes ou le coach IA. Ces deux
documents continuent de décrire l'état actuellement livré jusqu'à sa migration.

## 1. Promesse

MyCounts remplace le tableur de comptes par une vision claire et accompagnée de son
argent. L'application aide à comprendre où part l'argent, réduire les dépenses inutiles,
préparer les charges, préserver son train de vie et répartir rationnellement son épargne.

MyCounts est une aide à la gestion. Il ne se connecte pas aux banques, n'initie aucun
virement et ne vend ni ne recommande de produit financier.

## 2. Public et lancement

- V1 en français, pour la France, en euros et en fuseau `Europe/Paris`.
- Cible initiale : une personne seule ou des adultes gérant un compte joint.
- Produit gratuit. Des fonctions IA plus avancées pourront devenir premium plus tard.
- Première diffusion privée et gratuite auprès de la famille et des amis.
- Inscription publique seulement après validation de la justesse des montants, des
  sauvegardes et des parcours sans assistance.

Hors V1 : synchronisation bancaire, initiation de paiement, multidevise, placements à
valorisation variable, crédits, cartes à débit différé, OCR de scans ou de photos et
application mobile native.

## 3. Identité et espaces financiers

Le compte utilisateur est l'identité permanente : adresse électronique, mot de passe,
MFA, sessions, profil et préférences de confidentialité.

Chaque utilisateur possède un espace personnel et peut créer ou rejoindre plusieurs
foyers. Chaque espace constitue une gestion financière indépendante : comptes bancaires,
catégories, opérations, cycles, budgets, récurrences, enveloppes et réglages propres.

- Aucun compte ni mouvement financier n'est partagé automatiquement entre deux espaces.
- Aucun transfert d'opération d'un espace vers un autre.
- La création ou l'arrivée dans un foyer commence avec des données financières vierges
  et des catégories françaises par défaut.
- L'espace actif est toujours visible dans l'interface.
- Un invité peut rejoindre un foyer immédiatement et terminer plus tard l'onboarding de
  son espace personnel.

### Rôles d'un foyer

- **Propriétaire** : tous les droits, gestion des membres, transfert de propriété et
  suppression du foyer.
- **Administrateur** : finances, réglages, invitations et gestion des membres, sauf le
  propriétaire et la suppression du foyer.
- **Membre** : consultation et gestion des comptes, opérations, budgets et enveloppes,
  sans gestion des membres ni réglages structurants.

Toutes les opérations du foyer sont modifiables par ses membres. L'auteur et l'historique
des modifications restent consultables. Un membre qui part perd immédiatement l'accès ;
ses écritures restent. Le propriétaire doit transférer son rôle avant de partir. À la
suppression définitive d'une identité, son attribution devient « ancien membre ».

Ouvrir un cycle, corriger un cycle clos et valider un plan d'épargne commun ne sont pas
des modifications ordinaires : ces actions sont réservées au propriétaire et aux
administrateurs.

### Contribution entre espace personnel et foyer

Les deux côtés ne sont jamais liés techniquement. Une sortie personnelle peut être
classée « contribution au foyer » et l'entrée commune « contribution d'un membre ».
Elles affectent leurs soldes respectifs mais sont isolées des dépenses de consommation et
des salaires dans les statistiques.

## 4. Inscription et première connexion

La connexion est un écran d'entrée d'application mobile plein écran, pas une carte de
formulaire héritée d'un site web. Elle reprend la direction visuelle de MyCounts, respecte
les zones sûres et le clavier, prend en charge les gestionnaires de mots de passe et
découpe le mot de passe puis le MFA en étapes progressives. L'action principale, la
récupération et le retour restent visibles sans défilement.

1. Création du compte utilisateur.
2. Vérification de l'adresse électronique.
3. Enrôlement TOTP obligatoire avant toute donnée financière.
4. Affichage unique de codes de récupération.
5. Possibilité de faire confiance à un appareil pendant 30 jours, avec révocation dans
   les réglages.
6. Création automatique de l'espace personnel.
7. Saisie du premier compte courant, de son solde bancaire connu et de la date de ce
   solde.
8. Saisie d'un solde de sécurité à préserver ; MyCounts peut en proposer un.
9. Ajout des comptes d'épargne à capital stable : Livret A, LEP et équivalents.
10. Import guidé des trois derniers relevés.
11. Validation des opérations, récurrences et revenus détectés.
12. Choix du revenu qui ouvre le cycle et saisie de la date estimée de la prochaine paie.
13. Présentation du tableau de bord.
14. Création ou arrivée dans un foyer, facultative.

La récupération du compte passe par `no-reply@mycounts.app`. La perte simultanée du
second facteur et des codes suit une procédure manuelle via `support@mycounts.app`.

## 5. Import d'initialisation

L'import sert principalement à initialiser le compte. Après cela, l'utilisateur saisit
ses opérations manuellement. Un import ultérieur reste possible mais n'est pas une
synchronisation.

### Formats

- CSV et relevés PDF officiels téléchargés depuis la banque.
- Aucun scan, photographie ou OCR en V1.
- Profils certifiés au lancement : Revolut et Caisse d'Épargne, après tests sur de vrais
  fichiers anonymisés.
- Autres banques : détection générique en « compatibilité expérimentale », aperçu
  obligatoire et refus si les dates, montants ou totaux ne sont pas assez fiables.
- Opérations Revolut non finalisées et opérations non libellées en euros ignorées avec
  une explication.

Les fichiers originaux sont temporaires et supprimés après le traitement. Sont conservés
les opérations normalisées, les empreintes anti-doublons et le rapport d'import.

Chaque import affiche : opérations ajoutées, déjà présentes, ignorées et en erreur. Un
réimport est idempotent. Aucune proposition ne devient une écriture réelle sans l'aperçu
et la validation de l'utilisateur.

### Détection des récurrences

Une récurrence n'est proposée que si un libellé suffisamment similaire apparaît dans
chacun des trois relevés. Le montant peut varier. La détection couvre les sorties et les
entrées, par exemple un remboursement régulier de mutuelle.

Une récurrence validée alimente le calendrier. Une sortie contribue aux charges
mensuelles et annuelles ; une entrée ne compte pas comme charge. À son échéance,
l'opération est créée automatiquement. L'utilisateur peut modifier son montant ou la
supprimer. Une opération manuelle correspondante est rapprochée pour éviter un doublon.

Si le montant change, MyCounts demande s'il devient la nouvelle référence ou s'il est
exceptionnel. L'absence d'une récurrence n'émet pas d'alerte : l'import n'a pas vocation à
être répété continuellement.

## 6. Cycles de paie

Un cycle commence avec une opération de revenu que l'utilisateur marque explicitement
« ouvre un nouveau cycle ». Ni sa catégorie, ni une date prévue, ni l'IA ne peuvent le
faire seules.

- Plusieurs revenus sont permis, mais un seul revenu de référence ouvre chaque cycle.
- Dans un foyer, un seul revenu de référence est choisi pour l'espace commun.
- Aucune date mensuelle n'est imposée.
- Le cycle reste ouvert tant que la prochaine paie réelle n'a pas été enregistrée.
- La nouvelle paie clôt le cycle précédent à sa date réelle et ouvre le suivant.
- Un cycle clos garde des bornes immuables, sauf correction manuelle explicite et auditée.
- La date estimée de prochaine paie sert uniquement à la projection des charges ; elle ne
  clôture jamais un cycle.
- Sans paie historique validée, une période d'initialisation est visible mais exclue des
  comparaisons statistiques.

## 7. Tableau de bord et budgets

Le chiffre central est le **reste réellement disponible jusqu'à la prochaine paie**, pas
le seul solde bancaire. Le tableau de bord distingue au minimum :

1. solde bancaire actuel ;
2. solde projeté après les charges fixes à venir avant la paie estimée ;
3. reste disponible après les budgets de consommation ;
4. capacité d'épargne proposée puis validée ;
5. reste réellement disponible après cette épargne.

Les budgets de consommation couvrent notamment courses, carburant et restaurants. Ils
réduisent le disponible et repartent de zéro à chaque cycle réel, sans reporter leur
reliquat. Un dépassement reste visible mais n'est pas reporté comme dette budgétaire.

Les soldes négatifs sont autorisés et clairement signalés. Aucune épargne n'est proposée
si le solde projeté reste sous le solde de sécurité.

Le solde de sécurité est un plancher du compte courant. Il ne fait jamais partie de la
réserve d'épargne : une enveloppe de prévention protège un risque futur, tandis que ce
plancher évite de mettre le quotidien en difficulté avant la prochaine paie.

## 8. Épargne et enveloppes

Tous les comptes d'épargne à capital stable d'un espace forment une réserve commune. Une
enveloppe est une affectation virtuelle de cette épargne réelle et n'est pas liée à un
livret précis. La somme affectée aux enveloppes ne peut pas dépasser l'épargne constatée.

Deux types existent :

- **prévention** : réserve permanente pour voiture, maison, enfants ou imprévus ;
- **objectif court terme** : montant cible à atteindre, avec une date cible.

Le solde d'une enveloppe est conservé entre les cycles. Son importance est définie par
l'utilisateur. Pour une réserve préventive, le coach peut proposer un niveau de sécurité,
mais l'utilisateur doit le valider.

### Rituel à chaque paie

1. L'utilisateur enregistre la paie réelle et ouvre le cycle.
2. Le moteur calcule trois capacités d'épargne : prudente, recommandée et ambitieuse.
3. L'utilisateur choisit et valide le montant.
4. Le coach propose une répartition entre les enveloppes ; les pourcentages ne sont qu'un
   affichage, les montants validés restent des centimes exacts.
5. La proposition tient compte des soldes existants, de l'importance, de l'historique,
   des objectifs et des dates. Une enveloppe suffisamment couverte peut recevoir 0 €.
6. L'utilisateur valide.
7. Il effectue lui-même le virement dans son application bancaire et le confirme dans
   MyCounts ; les enveloppes sont alors créditées.

Dans le sens inverse, un retrait de l'épargne vers le compte courant diminue la réserve
et les enveloppes. L'argent non affecté est consommé d'abord. Pour un besoin précis,
l'utilisateur choisit l'enveloppe ; sinon le coach propose de réduire les enveloppes les
moins prioritaires ou les mieux couvertes. Le transfert n'est ni un revenu ni une dépense.
Si une correction ou un import révèle une réserve plus faible sans passer par ce parcours,
MyCounts rétablit automatiquement la couverture selon la même règle déterministe et
explique les désaffectations réalisées.

## 9. Moteur d'aide et coach IA

Le moteur financier, déterministe et testable, calcule les montants. Le coach IA explique
les résultats, détecte des habitudes, propose des arbitrages et permet un dialogue libre.
Il ne modifie jamais une donnée financière sans validation.

La capacité d'épargne tient compte du solde, des revenus, des charges à venir, des budgets,
du train de vie observé et du solde de sécurité. Elle s'affine à chaque cycle clos. Une
dépense exceptionnelle est conservée dans l'historique mais peut être exclue du train de
vie après confirmation. Les suggestions sur des dépenses inutiles restent neutres,
masquables et sans jugement.

Le coach intervient lors d'une paie, de la répartition d'épargne et du bilan de cycle. Un
chat libre est également disponible. Il peut répondre à des questions générales mais ne
pousse aucun placement, crédit, assurance ou produit financier.

### Confidentialité IA

- OpenRouter est appelé depuis le serveur avec la clé de MyCounts, jamais depuis le
  navigateur.
- Consentement explicite, désactivé par défaut et révocable à tout moment.
- Niveau agrégé par défaut ; consentement distinct pour envoyer certains libellés et
  montants détaillés.
- Contexte limité à l'espace actif ; aucun mélange entre espace personnel et foyers.
- Dans un foyer, activation seulement après le consentement individuel de tous les
  membres adultes.
- Conversations privées par membre ; seules les recommandations appliquées deviennent
  visibles dans le foyer.
- Routage OpenRouter `data_collection: deny`, ZDR obligatoire et journalisation des
  contenus désactivée.
- Historique du chat conservé par MyCounts, supprimable par l'utilisateur.
- Si le service IA est indisponible ou le plafond de coût atteint, tous les calculs et
  parcours financiers continuent de fonctionner.

## 10. Notifications

La V1 comprend des notifications push PWA sur téléphone et un centre interne. Sur iOS,
l'application explique l'ajout à l'écran d'accueil avant de demander l'autorisation.

Notifications initiales : budget presque épuisé ou dépassé, charge prochaine, solde
projeté sous le seuil de sécurité, proposition d'épargne prête, invitation et changement
important du foyer. Elles restent discrètes sur l'écran verrouillé.

Les courriels sont réservés à la vérification d'adresse, la récupération, les invitations
et les alertes de sécurité. `no-reply@mycounts.app` envoie ; `support@mycounts.app` reçoit.

## 11. Données et droits

- Export complet dans un format lisible et portable.
- Suppression du compte et de l'espace personnel.
- Transfert obligatoire de propriété avant de quitter un foyer.
- Anonymisation de l'auteur dans les foyers après suppression définitive de l'identité.
- Politique de confidentialité, mentions légales, CGU et information sur OpenRouter avant
  toute ouverture publique.
- Sauvegardes hors serveur et restauration réellement testée.

## 12. Critère de réussite

Une personne qui ne connaît pas MyCounts peut, sans assistance : sécuriser son compte,
saisir ses soldes, importer trois relevés, valider ses charges et sa paie, comprendre son
reste à vivre, obtenir une proposition d'épargne explicable, la répartir entre ses
enveloppes et retrouver exactement les montants qu'elle a validés.

## 13. UX et direction visuelle non négociables

Toutes les fonctions V1 prolongent l'interface actuelle. Elles ne créent ni second design
system, ni esthétique « assistant IA » séparée. Les tokens, composants, mouvements et la
direction Liquid Glass bleu ardoise restent les auteurs visuels uniques.

- Smartphone d'abord ; bureau comme extension, jamais comme point de départ.
- L'action fréquente se fait en un minimum de gestes et, autant que possible, en un clic
  depuis l'écran où le besoin apparaît.
- Une seule décision principale par écran ou étape ; les valeurs sûres sont préremplies.
- Les termes métier sont traduits en conséquences concrètes pour l'utilisateur.
- Les détails avancés sont révélés progressivement, sans encombrer le parcours principal.
- Une modale ne défile jamais verticalement. Si son contenu ne tient pas entièrement dans
  le viewport, le parcours est découpé en plusieurs étapes courtes ou devient un écran
  dédié. Réduire ou masquer le contenu pour le faire tenir est interdit.
- Le clavier mobile, les zones sûres et les messages d'erreur ne doivent ni cacher
  l'action principale ni provoquer un défilement de modale.
- Le changement d'espace, les montants réels/projetés et toute action IA conservent les
  règles de lisibilité et de mouvement déjà définies dans `docs/UX.md`.
- Chaque nouvelle modale est testée au minimum sur les largeurs mobiles et tablettes déjà
  couvertes par le projet, avec son contenu réel le plus long et ses états d'erreur.

## 14. Évolution vers les applications iPhone et Android

La V1 web est conçue pour devenir une application distribuée sur l'App Store et Google
Play sans réécriture du métier. React, les écrans et l'API restent communs ; une couche
native apportera ensuite notifications, biométrie, stockage sécurisé, partage de fichiers,
liens universels et intégration au cycle de vie du téléphone.

La première étape est une PWA réellement installable. La seconde utilise un runtime natif
tel que Capacitor et ajoute les projets iOS/Android. L'application publiée devra offrir
une expérience « app » complète, pas seulement afficher le site dans un conteneur.

L'application native reste hors du périmètre de livraison V1, mais aucune fonctionnalité
V1 ne doit rendre sa conversion inutilement coûteuse.
