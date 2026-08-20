# Corriger le solde depuis l'accueil, et atteindre les budgets

## Le bloc Budgets était un cul-de-sac

Il ne s'affichait **qu'une fois un plafond posé** : la seule porte vers l'écran qui permet
d'en poser un ne s'ouvrait donc qu'à ceux qui en avaient déjà. Une fonction livrée que
personne ne pouvait atteindre. Le bloc est maintenant toujours là, et propose l'action
quand il est vide.

## Corriger le solde, sans jamais l'écrire

« Réel aujourd'hui » devient actionnable et demande **le solde affiché par votre banque** —
personne ne connaît son écart de tête, tout le monde lit le chiffre de son relevé.

Un solde est une **somme d'opérations**, jamais une valeur qu'on pose : la correction
devient une opération de plus, qui porte l'écart et reste visible dans l'historique. C'est
ce qui permet, trois mois plus tard, de comprendre d'où venait la différence.

L'écart est calculé **par le serveur**, jamais reçu : lui seul connaît le solde à l'instant
où il écrit. Un écart calculé par le client le serait sur une valeur déjà périmée, et deux
corrections concurrentes se doubleraient. Le témoin rejoue trois fois la même demande et
vérifie que le solde ne bouge qu'une.

Concordance parfaite : **aucune opération**. Écrire un ajustement de zéro remplirait
l'historique de lignes qui ne disent rien.

## Sixième dimension des agrégats

Un ajustement compte dans les trois soldes et **jamais dans les dépenses** : réparer une
erreur de saisie de 20 € n'est pas avoir dépensé 20 €, et l'y compter ferait sauter un
plafond pour une erreur qu'on vient précisément de réparer. La table `INCLUT_AJUSTEMENTS`
est exhaustive comme les cinq autres, et une contrainte en base refuse qu'un ajustement
soit en même temps une paie, une ouverture ou une moitié de virement.
