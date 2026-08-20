# Les comptes deviennent des cartes, avec un catalogue de produits français

Une carte par compte : son nom, ce qu'il y a dessus, et ce qu'il est. On peut le
**modifier**, le **supprimer** et l'**ajouter** — la ligne unique de la version précédente
obligeait à tout tasser sur 390 px et les actions n'y tenaient pas.

## Le produit et le comportement sont deux choses

Le **produit** est ce qui existe chez les banques — Livret A, LDDS, LEP, Livret Jeune, PEL,
CEL, compte à terme, PEA, PEA-PME, compte-titres, assurance vie, PER, compte joint,
espèces. Le **comportement** est binaire : l'argent compte-t-il dans le solde du quotidien
ou dans l'épargne. C'est le seul que les agrégats lisent.

Le comportement est **déduit** du produit et n'est jamais envoyé par le client : deux
façons de dire la même chose finiraient par se contredire. D'où deux entrées « Autre »
plutôt qu'une avec un réglage à part.

Le catalogue vit dans le domaine et est servi par le serveur : c'est lui qui décide qu'un
PEA ne compte pas dans le solde du quotidien, et cette règle n'appartient pas à l'écran.
Un produit inconnu est **refusé** plutôt que ramené à un défaut — deviner le comportement
d'un compte reviendrait à déplacer de l'argent d'une colonne à l'autre sans qu'on l'ait
demandé.

## Ce que la suppression refuse

Un compte qui porte des opérations n'est pas supprimé : ses lignes disparaîtraient des
totaux passés et un mois déjà clos changerait de montant. Le refus dit pourquoi **et**
propose l'archivage — un message qui dirait seulement « impossible » laisserait chercher.

Le solde d'ouverture étant une opération, un compte créé avec un montant n'est jamais vide :
c'est cohérent, et le témoin le vérifie.
