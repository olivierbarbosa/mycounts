# Ce que les vrais relevés d'Olivier ont appris

Analyse d'un export réel de la Caisse d'Épargne — 198 opérations, du 29/06 au 20/08/2026 —
et de trois relevés PDF mensuels. **Aucune de ces données n'est entrée dans le dépôt** : le
garde-fou nº 1 refuse un IBAN valide, et les fixtures de test sont inventées de bout en
bout. Ce fichier ne conserve que des CONSTATS de forme, jamais de contenu.

## Le format CSV

Treize colonnes, séparateur `;`, **encodage ISO-8859-1**, fins de ligne CRLF.

L'encodage n'est pas un détail : lu en UTF-8, le fichier lève une erreur de décodage. Et
l'inverse est pire — un fichier UTF-8 lu en Latin-1 ne lève RIEN, il produit des « Ã© ». On
tente donc l'UTF-8 en premier, parce que c'est celui qui sait échouer bruyamment.

## Il n'existe aucune clé naturellement unique

C'est le constat qui a décidé de toute la conception de l'import, et il n'était pas
prévisible sans les vraies données :

| Constat | Mesure |
|---|---|
| Référence bancaire vide | **31 lignes sur 198** (16 %) |
| Même référence pour deux opérations DIFFÉRENTES | 1 cas — deux achats du même jour, 31,98 € et 15,50 € |
| Doublons sur (date + libellé + montant + référence) | **3 groupes** |
| Doublons sans la référence | 6 groupes |

Et ces doublons sont de VRAIES opérations distinctes : trois remboursements de 2,00 € le
même jour, deux virements internes de 100 € le même jour. Dédupliquer par le contenu
supprimerait donc de l'argent réel.

D'où la clé retenue : `date · libellé · montant · référence · rang d'occurrence`. Vérifiée
sur le fichier complet — **0 collision, réimport parfaitement idempotent**.

## Les autres surprises

- **Deux dates, différentes une fois sur deux.** 94 lignes sur 198 ont une date de
  comptabilisation distincte de la date d'opération, parfois de plusieurs jours. Un achat
  du 30 comptabilisé le 2 tomberait dans la mauvaise période budgétaire, faussant les deux
  mois à la fois. L'import retient la date d'OPÉRATION.
- **La banque marque elle-même ses virements internes** : catégorie « Transaction exclue »,
  31 lignes. S'en servir évite de compter chaque mise de côté comme un revenu.
- **Débit et crédit sont dans deux colonnes séparées**, jamais remplies ensemble.
- **La banque fournit ses propres catégories** (13 valeurs distinctes). Elles sont
  affichées pendant la revue comme indice, jamais appliquées : ce ne sont pas celles du
  foyer, et se tromper silencieusement de rangement est pire que de ne rien ranger.
- **La colonne « Pointage » vaut 0 partout** : inexploitable.

## Les PDF

Trois relevés mensuels, ~170 ko chacun. Le texte est extractible — 250 dates et 133
montants dans celui d'août — mais **positionné, pas structuré** : l'association d'une date,
d'un libellé et d'un montant dépend des coordonnées à l'écran, pas de l'ordre dans le
fichier. Le flux contient en outre des codes techniques de mainframe (de l'EBCDIC affiché
en Latin-1) mêlés au texte utile.

Surtout : **le CSV contient tout ce que le PDF contient, et davantage** — références,
catégories, seconde date. Le PDF n'apporterait que l'historique antérieur à ce que la
banque laisse exporter en CSV.

Recommandation : ne pas faire du PDF un import de premier rang. Si le besoin d'historique
ancien se confirme, en faire un lot à part, avec un taux d'erreur MESURÉ sur ces trois
fichiers avant de livrer quoi que ce soit — une ligne mal lue devient de l'argent faux.

## Ce que l'app ne sait toujours pas faire

Constaté en confrontant le modèle à ces relevés :

1. **Rapprocher un virement importé avec son compte de destination.** Le relevé dit qu'un
   virement interne est sorti, pas où il est allé. L'import le marque comme virement mais
   ne peut pas créer les deux jambes.
2. **Catégoriser automatiquement.** La banque propose une catégorie ; rien ne relie encore
   ses 13 valeurs aux catégories du foyer. Un tableau de correspondance apprenable — « la
   prochaine fois, range Intermarché dans Courses » — serait le prolongement naturel.
3. **Pointer une opération.** La banque a la notion, l'app n'a que « à confirmer » pour les
   récurrences. Utile pour rapprocher un mois entier ligne à ligne.
4. **Détecter qu'un prélèvement récurrent connu correspond à une ligne importée.** Sans
   cela, un abonnement déjà saisi comme récurrence sera importé une seconde fois.
