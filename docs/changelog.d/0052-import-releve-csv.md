# Lot F — import d'un relevé CSV

Conçu sur de vrais relevés de la Caisse d'Épargne fournis par Olivier. L'analyse complète
est dans `docs/analyse-releves-caisse-epargne.md` ; **aucune de ces données n'est entrée
dans le dépôt**, et les fixtures de test sont inventées de bout en bout.

## Rien ne s'écrit sans revue

Deux routes : `POST /import/analyse` lit le fichier et rend ce qu'il propose,
`POST /import/valider` écrit les lignes qu'on lui redonne. Un import en une seule mettrait
dans les comptes des opérations que personne n'a lues, et le premier faux positif ferait
perdre confiance à tout le reste.

Le fichier n'est jamais conservé côté serveur : un relevé bancaire stocké serait une donnée
sensible de plus à protéger, pour un bénéfice nul.

## La clé d'unicité, et pourquoi elle est ce qu'elle est

`BOUCLE.md` l'exigeait « explicite et documentée ». Les vraies données ont montré que le
sujet était moins simple qu'il n'y paraissait — sur 198 opérations :

- la référence bancaire est **vide 31 fois** ;
- elle est **partagée par deux achats différents** du même jour ;
- même (date + libellé + montant + référence) laisse **3 groupes de doublons**, et ce sont
  de vraies opérations distinctes — trois remboursements de 2 € le même jour.

Dédupliquer par le contenu supprimerait donc de l'argent réel. La clé ajoute un **rang
d'occurrence** : la n-ième ligne identique du fichier. Vérifiée sur l'export complet — zéro
collision, réimport idempotent.

Son angle mort est écrit dans le module : un fichier partiel qui ne contiendrait que la
seconde de trois occurrences identiques lui donnerait le rang 1, et elle passerait pour
déjà importée.

## Ce que les vraies données ont imposé

- **ISO-8859-1**, pas UTF-8. L'UTF-8 est tenté en premier parce que c'est celui qui échoue
  bruyamment : l'inverse réussit toujours et produit des « Ã© ».
- **La date d'OPÉRATION**, pas celle de comptabilisation — elles diffèrent 94 fois sur 198,
  et un achat du 30 comptabilisé le 2 fausserait deux mois de budget à la fois.
- **Les virements internes sont reconnus** : la banque les marque elle-même, 31 lignes sur
  198. Les compter en revenu gonflerait les rentrées de chaque mise de côté.
- **Les montants ne passent JAMAIS par un flottant.** `int(float("0.29") * 100)` vaut 28.
- Les espaces de milliers, y compris insécables, ne cassent pas la lecture.

## L'écran

Les lignes déjà importées sont **montrées**, barrées et décochées : les taire ferait croire
à un fichier incomplet à qui réimporte un mois entier pour rattraper deux oublis. Tout ce
qui est nouveau est coché d'emblée — faire cocher deux cents lignes à la main serait une
corvée qui ferait renoncer.

La catégorie de la banque est affichée comme indice, jamais appliquée : ce ne sont pas les
catégories du foyer.

## Un défaut du client corrigé au passage

`appeler()` posait `Content-Type: application/json` sur TOUTES les requêtes. Un envoi de
fichier passe par un `FormData`, dont la frontière multipart est générée par le navigateur :
le type imposé produisait un corps que le serveur ne savait pas découper.

## Vérifié

21 tests unitaires, dont deux mutations : ignorer le rang dans la clé fait rougir le témoin
des opérations réellement identiques, retenir la date de comptabilisation fait rougir le
sien. 176 tests d'intégration, 110 de bout en bout — dont un qui dépose un fichier Latin-1
avec accents et vérifie qu'ils survivent.
