# Ce qu'on tire encore du document du collègue

Le document `reference-enveloppes-collegue.md` a déjà servi à trancher le découpage E1→E4
de `BOUCLE.md` et à construire le lot E1. Cette note fait le tri de ce qu'il reste à en
prendre — et dit ce qu'il vaut mieux ne PAS en prendre, avec la raison.

## Déjà repris, et bien repris

- **Ledger sans solde stocké.** `MouvementEnveloppe` est la seule source ; aucun
  `current_balance`. C'était déjà la règle du projet pour les comptes.
- **Le compte préféré est une simple préférence de couverture** — aucun mouvement bancaire.
- **Cible et date cible** sur l'enveloppe.
- **Montant toujours positif, le type porte le sens.** Le document ne l'exige pas ; nous
  l'avons ajouté parce qu'un montant signé rendrait possible une reprise déguisée en
  allocation négative, invisible dans un journal filtré par type.
- **La règle fondamentale** : une allocation ne crée jamais de transaction bancaire.

## À prendre, par ordre d'urgence

### 1. `rollover_mode` — le vrai trou

C'est la seule question du document que nous n'avons pas tranchée, et elle se posera **au
premier changement de période**, sans qu'aucun code n'ait de réponse : que devient le
contenu d'une enveloppe « Courses » quand la paie tombe ? Il reste ? Il est repris ? Il est
plafonné à la cible ?

Tant que ce n'est pas décidé, E3 (préparation mensuelle) ne peut pas être écrit
correctement : `place = max(0, cible − actuel)` suppose déjà une réponse.

### 2. `purpose` : `operating` contre `reserve`

Change le calcul du disponible. Une enveloppe de fonctionnement se vide tous les mois par
construction ; une réserve s'accumule. Les additionner dans un même total « réservé »
donne un chiffre qui ne veut rien dire.

### 3. `priorite` et `contribution_mensuelle`

Nécessaires à E3 : sans priorité, un disponible insuffisant se répartit dans un ordre
arbitraire — c'est-à-dire dans l'ordre d'insertion en base.

### 4. `statut` : `active` / `pause` / `atteint` / `abandonne`

Un objectif atteint doit pouvoir se clore sans être supprimé, sinon son historique part
avec lui.

### 5. Le workflow de confirmation en cinq états

`à préparer → préparation calculée → allocations validées → virement déclaré → confirmé`.
Il s'articule directement avec l'import de relevé : c'est l'import qui fournit enfin la
cinquième étape, aujourd'hui impossible autrement que par la correction manuelle du solde.

## À NE PAS prendre

### La table `Project` séparée

Le document impose deux contraintes qui, mises côte à côte, se contredisent presque : un
projet doit **toujours** être adossé à une enveloppe de réserve, et une enveloppe ne peut
porter **qu'un seul** projet. C'est une relation un-à-un. Une relation un-à-un entre deux
tables est presque toujours une seule table déguisée en deux.

Notre `Enveloppe` porte déjà `cible_centimes` et `date_cible` — l'essentiel de ce qu'est un
projet. Lui ajouter `priorite`, `statut` et `contribution_mensuelle` donne la totalité de
la valeur décrite aux sections 6 à 10, sans seconde table, sans jointure obligatoire et
sans le cas « projet sans enveloppe » que le document doit lui-même rattraper en créant
l'enveloppe à la volée.

**Ce qu'on perd en refusant :** rien de fonctionnel repéré. Un jour où plusieurs projets
devraient partager une même enveloppe, il faudra revenir dessus — mais le document
l'interdit explicitement, donc ce jour n'est pas prévu par lui non plus.

### Le second ledger `ProjectLedgerEntry`

Deux journaux pour le même argent, c'est deux sources de vérité pour un même solde. Le
projet entier est construit contre ça : un solde est une somme de mouvements, écrite à un
seul endroit. Si les projets deviennent des enveloppes, la question ne se pose plus.

### `type` d'enveloppe (`household` / `personal` / `child`)

À reporter jusqu'à l'onglet Foyer. Aujourd'hui aucun écran ne pourrait remplir cette
colonne autrement qu'en la laissant à sa valeur par défaut — et une colonne que personne
ne peut renseigner ment sur ce que le modèle sait.

## Sur l'import de relevé

`BOUCLE.md` a tranché le CSV avec écran de revue. La demande d'y ajouter le **PDF** mérite
d'être posée à part : un CSV a des colonnes, un PDF a une mise en page. L'extraction y est
faillible par nature, et une ligne mal lue devient une opération fausse dans les soldes.
Si le PDF est retenu, la revue avant écriture n'est plus une précaution mais la seule
barrière — et le taux d'erreur doit être mesuré sur de vrais relevés avant de livrer.
