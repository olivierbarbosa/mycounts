# MyCounts V1 — architecture cible

Ce document traduit `V1-PRODUIT.md` en invariants techniques. Il ne décrit pas encore le
schéma SQL final colonne par colonne ; chaque lot devra produire sa migration et ses tests
avant modification de la production.

## 1. Périmètre comme primitive de sécurité

### Entités principales

- `Utilisateur` : identité, MFA, sessions et profil.
- `Espace` : `PERSONNEL` ou `FOYER`, nom, état et paramètres financiers.
- `Appartenance` : `utilisateur_id`, `espace_id`, rôle, état et dates.
- `InvitationEspace` : destinataire, rôle proposé, expiration, jeton haché et état.

Chaque utilisateur reçoit exactement un espace personnel et une appartenance propriétaire
non révocable tant que l'identité existe. Il peut avoir plusieurs appartenances à des
foyers. `Utilisateur.foyer_id`, `Utilisateur.est_proprietaire` et la vue binaire actuelle
deviennent obsolètes.

Toutes les entités financières portent directement un `espace_id`, ou appartiennent à un
parent qui le porte avec une contrainte empêchant les liens inter-espace. Une requête API
résout un `Principal` composé de l'utilisateur, de l'espace actif et de son rôle. Aucune
méthode de repository financier n'accepte un espace brut sans appartenance vérifiée.

L'espace actif est un UUID explicite dans l'URL ou un en-tête dédié. Le défaut est l'espace
personnel. Le changement d'espace est atomique côté interface : ancien libellé et anciennes
données disparaissent ensemble.

## 2. Modèle financier

### Comptes et opérations

`Compte` appartient à un espace et possède un type `COURANT`, `EPARGNE_STABLE`
(`epargne` en base) ou `PLACEMENT` — ce dernier hors quotidien et hors réserve. Les comptes en devise non EUR sont refusés en V1.

`Operation` conserve : compte, espace, montant en centimes, date civile, catégorie,
créateur, source, référence d'import, récurrence éventuelle et nature spéciale éventuelle
(ouverture, ajustement, transfert, contribution). L'espace de l'opération, du compte, de
la catégorie, du cycle et de la récurrence doit concorder en base.

Une contribution entre espace personnel et foyer produit deux écritures indépendantes,
sans identifiant partagé ni clé étrangère croisée.

### Cycles persistants

`CycleBudgetaire` devient une entité persistante : espace, opération d'ouverture, date de
début réelle, opération de clôture éventuelle, date de fin réelle éventuelle, état et
version de correction.

- Une opération n'ouvre un cycle que si `ouvre_cycle` a été confirmé.
- La création de la paie suivante clôt le cycle ouvert dans la même transaction SQL.
- Une date estimée de paie vit dans les paramètres de projection, pas dans la borne réelle.
- Les cycles clos ne sont jamais redécoupés par le rang des opérations.
- Une correction manuelle écrit un événement d'audit et recalcule explicitement les
  agrégats concernés.

`Operation.cycle_id` est fixé à l'écriture et n'est jamais redéduit silencieusement de sa
date. Ajouter, modifier ou supprimer une opération dans un cycle clos passe par une
correction explicite et auditée : les agrégats de ce cycle sont recalculés, mais ses bornes
ne changent pas.

### Budgets

Les budgets sont rattachés à un cycle et une catégorie de consommation. Leur reliquat ne
crée aucune écriture et n'est pas reporté au cycle suivant.

### Réserve d'épargne et enveloppes

La réserve réelle d'un espace est la somme des soldes de ses comptes `EPARGNE_STABLE`.
Les enveloppes ne sont liées à aucun compte particulier.

`Enveloppe` porte un type `PREVENTION` ou `OBJECTIF`, une importance utilisateur, un solde
affecté, et selon son type une réserve suffisante validée ou un montant/date cible.

Invariants :

- somme des soldes d'enveloppes <= réserve d'épargne réelle ;
- aucun solde d'enveloppe négatif ;
- toute variation est écrite dans un journal d'affectation ;
- un retrait d'épargne doit désaffecter exactement le même montant ;
- un intérêt ou ajustement crée de l'épargne non affectée tant qu'aucun plan n'est validé.

Toute écriture, correction, suppression ou import qui diminue la réserve déclenche une
désaffectation déterministe sans dépendre de l'IA : argent non affecté d'abord, puis
enveloppes par importance croissante, puis par taux de couverture décroissant et enfin par
identifiant stable. La désaffectation est journalisée et notifiée ; l'écriture bancaire
n'est jamais refusée pour préserver une affectation virtuelle.

`PlanEpargneCycle` conserve les entrées du calcul déterministe, les trois capacités, le
montant choisi, la proposition de répartition, son auteur, son état et la confirmation du
virement manuel. La proposition IA n'est jamais elle-même le grand livre.

La répartition est convertie en centimes avant validation. La somme des affectations doit
être exactement égale au montant du virement confirmé. Les restes d'arrondi sont attribués
de manière déterministe à l'enveloppe la plus prioritaire, puis par identifiant stable.

## 3. Imports

L'import suit deux phases : analyse temporaire puis validation atomique.

- `ProfilImportBanque` versionne les règles d'un format certifié.
- Un parseur générique peut seulement produire un aperçu expérimental.
- Un fichier est stocké dans un emplacement temporaire isolé, borné en taille et supprimé
  après succès ou expiration.
- Les PDF sont analysés localement ; leur contenu brut n'est pas transmis à OpenRouter.
- La détection de banque et de format est explicite.
- Chaque profil possède sa propre clé d'idempotence.
- Revolut ignore les états non finalisés et les devises non EUR.
- La validation vérifie les totaux, les dates, les signes, le compte et l'espace.
- Le rapport d'import et les empreintes restent ; le fichier disparaît.

Une récurrence candidate doit être observée dans chacun des trois relevés. Le rapprochement
utilise un libellé normalisé, une cadence compatible et une tolérance de montant. La
création reste soumise à validation.

`OccurrenceRecurrence` garantit une matérialisation idempotente par récurrence et date.
Une opération manuelle peut être rapprochée d'une occurrence avant sa matérialisation.

## 4. Moteur de capacité d'épargne

Le calcul est pur, déterministe, versionné et reproductible. Il reçoit au minimum : solde
actuel daté, revenus, charges récurrentes avant la paie estimée, budgets du cycle, dépenses
habituelles, dépenses exceptionnelles confirmées, solde de sécurité et épargne existante.

Il produit trois capacités bornées à zéro : prudente, recommandée et ambitieuse. La
formule exacte et la fenêtre statistique seront figées par des exemples métier avant le
code. Un historique court diminue l'indice de confiance affiché, pas les garanties
d'intégrité.

Le coach peut proposer un montant ou une ventilation, mais l'API valide toutes les
contraintes sans lui faire confiance.

## 5. IA et consentements

`ConsentementIA` est rattaché à un utilisateur et un espace, avec niveau `AGREGE` ou
`DETAILLE`, version du texte accepté et dates d'activation/révocation. Dans un foyer, une
requête n'est autorisée que si tous les membres actifs ont un consentement compatible.

Le constructeur de contexte applique une liste positive de champs : agrégats, objectifs,
enveloppes et, au niveau détaillé, seuls les libellés/montants nécessaires. Email, nom,
identifiants bancaires, fichier importé et données des autres espaces sont exclus.

OpenRouter est appelé avec collecte interdite et ZDR obligatoire. Le fournisseur et le
modèle sont allowlistés ; les replis ne peuvent pas affaiblir la politique. Une clé serveur
distincte possède un plafond de coût. Prompts, réponses brutes et secrets ne vont pas dans
les logs.

Le chat est stocké par MyCounts, par membre et par espace. Les recommandations appliquées
sont copiées comme décisions financières partagées, sans exposer la conversation privée.
La révocation empêche tout nouvel appel et permet la suppression de l'historique.

## 6. Messages asynchrones

Une boîte d'envoi transactionnelle en base alimente deux workers indépendants :

- email SMTP OVH/Zimbra pour identité, invitations et sécurité ;
- Web Push pour les notifications budgétaires PWA.

Création du jeton et de l'événement d'envoi sont atomiques. Les workers gèrent
idempotence, tentatives, expiration et suivi d'échec. Les jetons sont hachés, à usage
unique et absents des logs.

## 7. Migration de l'existant

Migration non destructive recommandée :

1. créer un espace personnel par utilisateur existant ;
2. créer un espace foyer par foyer actuel ;
3. migrer les comptes privés vers leur espace personnel ;
4. migrer les comptes joints vers l'espace foyer ;
5. dupliquer les catégories personnelles par utilisateur et remapper leurs opérations ;
6. conserver une copie commune des catégories et objets partagés dans le foyer ;
7. remapper récurrences, plafonds, enveloppes et imports ;
8. construire ou valider les cycles historiques sans modifier leurs sommes ;
9. créer les appartenances et rôles ;
10. seulement ensuite supprimer l'ancien périmètre `foyer_id/vue`.

La migration est répétée sur une copie de production. Contrôles obligatoires avant/après :
nombre d'opérations, somme par compte, solde de chaque compte, nombre de catégories liées,
absence de clé étrangère inter-espace, un espace personnel par utilisateur et un
propriétaire par foyer.

## 8. Menaces à tester explicitement

- accès à l'UUID d'un espace ou objet d'un autre membre ;
- changement d'espace pendant une requête ou un chargement frontend ;
- réimport créant un doublon ou une paie ouvrant un cycle sans validation ;
- ajout/suppression d'une ancienne paie déplaçant un cycle clos ;
- concurrence entre matérialisation d'une récurrence et saisie manuelle ;
- enveloppes supérieures à l'épargne réelle ;
- réponse IA contenant un montant hors des bornes déterministes ;
- révocation d'un consentement ou d'une appartenance pendant un appel ;
- vol d'un cookie d'appareil de confiance ;
- fuite de jeton, libellé bancaire ou conversation dans les logs.

## 9. Architecture frontend et densité des parcours

Les nouvelles fonctions réutilisent les tokens et primitives actuels. Les composants de
modal, feuille, champ, montant, navigation, espace vide et confirmation ne sont pas
dupliqués par fonctionnalité.

Un parcours complexe est représenté par une machine d'états explicite et persistable,
notamment pour l'onboarding, l'import, la paie et le plan d'épargne. Chaque étape possède
une entrée, une action principale et une sortie déterministes. Fermer puis reprendre ne
doit ni perdre une validation déjà acquise ni créer une écriture deux fois.

Une modale est un conteneur sans défilement. Avant implémentation, chaque état doit tenir
avec le contenu français maximal, les erreurs visibles, les zones sûres et le clavier
mobile. Si ce contrat ne tient pas, l'état est scindé ou déplacé vers un écran dédié ; un
`overflow-y: auto` dans la modale n'est pas une solution admise.

Les tests E2E vérifient au minimum : absence de débordement, action principale visible,
cible tactile de 44 px, retour arrière sans perte, réouverture idempotente, contraste et
absence d'ancien montant après changement d'espace.

## 10. Portabilité PWA, iOS et Android

Le métier et les composants d'écran ne dépendent pas directement des API du navigateur.
Une couche de capacités expose au minimum :

- notifications push et ouverture depuis une notification ;
- stockage sécurisé de la session et des secrets locaux ;
- biométrie comme déverrouillage local, jamais comme remplacement du MFA serveur ;
- sélection et partage de fichiers ;
- liens profonds pour invitation, vérification et récupération ;
- état réseau et reprise d'une action idempotente ;
- informations de zones sûres, clavier et cycle de vie de l'application.

Chaque capacité possède une implémentation web/PWA et pourra recevoir une implémentation
Capacitor iOS/Android. Le serveur reste l'auteur des autorisations et de l'intégrité :
aucune confiance supplémentaire n'est accordée au conteneur natif.

Le transport de session fait partie de cette couche. Le web/PWA conserve le cookie
`httponly`, `secure`, `samesite=lax` sur le même hôte. Le conteneur natif utilisera un
jeton d'accès court stocké dans le trousseau, renouvelé par un secret rotatif et révocable
côté serveur ; son origine est explicitement autorisée. Le contrat est conçu dans le lot
identité afin qu'aucun endpoint métier ne dépende directement de la présence d'un cookie.

Le cache hors ligne ne contient pas de relevé importé, conversation IA ou réponse API
financière persistante. La V1 peut afficher un shell hors ligne, mais toute écriture exige
une reprise réseau explicite et idempotente.

### Appareil de confiance

Un appareil de confiance possède un secret aléatoire haché côté serveur et peut être
révoqué individuellement. Changer le mot de passe, ajouter ou retirer un facteur révoque
tous les appareils sauf le courant. La confiance peut éviter le TOTP à la connexion, mais
jamais pour changer l'adresse ou le mot de passe, désactiver le MFA, transférer la
propriété ou supprimer un compte ou un foyer.

### Mesure des modales

Le contrat sans défilement utilise le viewport visuel, clavier ouvert, avec une référence
minimale de 390 x 340 px, le libellé français le plus long et un message d'erreur. Le test
échoue si le contenu dépasse son conteneur ou si l'action principale sort du viewport. Un
parcours qui ne tient pas est scindé en étapes supplémentaires.
