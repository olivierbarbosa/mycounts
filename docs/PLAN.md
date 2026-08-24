# Plan de mycounts — page par page

Ce document fige **ce que fait chaque écran, et ce qu'il ne fait pas**. Il existe parce
que trois écrans ont été refaits deux ou trois fois faute d'avoir écrit leur périmètre
avant de coder : l'agenda (liste → calendrier → charges seulement), les catégories (par
défaut → libres → par défaut modifiables), la palette (Revolut → Stripe → lavande).

Règle de lecture : **la colonne « ne fait pas » compte autant que l'autre.** C'est elle qui
évite les reprises.

---

## Principes qui valent pour tous les écrans

- **Smartphone d'abord.** Un écran conçu pour 1280 px et rétréci ensuite est toujours
  mauvais sur 390. L'inverse marche.
- **Simple et rapide.** L'action fréquente doit être atteignable en un geste. Une saisie
  de dépense qui demande cinq champs ne sera pas faite.
- **Aucun montant fictif**, jamais, même pour « habiller » un écran vide.
- **Un chiffre ne s'affiche pas sans dire ce qu'il mesure** : borne de période, mention
  « estimé » quand elle est déduite.
- **Confirmation avant toute suppression.**

---

## 1. Connexion — `ecrans/Connexion.tsx`

| | |
|---|---|
| **Sert à** | Entrer dans l'application. Rien d'autre. |
| **Ne fait pas** | Pas d'inscription libre tant que `MYCOUNTS_INSCRIPTIONS_OUVERTES` est faux. Le mot de passe oublié passe par un lien envoyé par courriel (livré le 24 août 2026). |
| **État** | ✅ Terminé. |

---

## 2. Amorçage du premier compte — `ecrans/PremierCompte.tsx`

| | |
|---|---|
| **Sert à** | Créer le compte bancaire et saisir son solde actuel, une seule fois. |
| **Ne fait pas** | Pas de gestion multi-comptes ici : un seul compte au démarrage. |
| **État** | ✅ Terminé. Le solde devient une opération d'ouverture, jamais une colonne. |
| **Manque** | Ajouter d'autres comptes ensuite (aucun écran ne le permet aujourd'hui). |

---

## 3. Accueil — `ecrans/Accueil.tsx`

**Sert à** répondre à une seule question : *combien me reste-t-il, et où est parti
l'argent ce mois-ci ?*

| Fait | Ne fait pas |
|---|---|
| Solde projeté en grand, avec sa borne de période | N'affiche pas de graphique |
| Réel, à confirmer, dépensé de la période | Ne montre pas les prélèvements à venir (c'est le Calendrier) |
| Liste des opérations de la période | Ne gère pas les plafonds (c'est Budget) |
| Saisie rapide d'une dépense ou d'un revenu | |

**Manque, par ordre d'importance :**

1. **Modifier une opération** — l'API n'a pas de `PATCH /operations/{id}`.
2. **Supprimer une opération**, avec confirmation — pas de `DELETE` non plus.
3. **Voir le détail d'une opération** : date de valeur, compte, catégorie, provenance
   (saisie manuelle ou prélèvement matérialisé).
4. Filtrer par catégorie ou par compte.

---

## 4. Calendrier — `ecrans/Calendrier.tsx`

**Sert à** trois choses, et rien de plus :

1. ajouter un prélèvement pour connaître ses charges ;
2. voir d'un coup d'œil **qui** prélève et **quand** ;
3. couvrir tous les rythmes — mensuel, trimestriel, annuel, et le reste.

| Fait | Ne fait pas |
|---|---|
| Grille mensuelle sur toutes les tailles | **Aucun revenu** : un salaire se saisit à l'accueil |
| Points sous 600 px + détail du jour au tap | Pas de vue semaine ni de vue liste annuelle |
| Ajouter, modifier, arrêter un prélèvement | Ne modifie jamais les prélèvements déjà passés |
| Rythmes nommés | |
| File « à confirmer » | |
| Pastilles de marque | Pas de vrais logos (voir ci-dessous) |
| « À venir » borné au mois civil, borne donnée par le serveur | Pas une fenêtre glissante : ce qui reste à payer ce mois-ci |

**Manque :**

1. **Logo récupéré en ligne**, sur le modèle de KeePassXC : déclenché par une **action
   explicite**, jamais automatiquement ; requête faite par le serveur puis mise en cache ;
   `<link rel="icon">` du site, repli sur `/favicon.ico`, puis sur le service DuckDuckGo ;
   repli final sur la pastille.
2. Total annuel des charges — « mes abonnements me coûtent X € par an » est l'information
   qui fait résilier.

---

## 5. Budget — écran à construire

**Sert à** savoir si l'on tient ses plafonds, et à être prévenu avant de les dépasser.

| Fera | Ne fera pas |
|---|---|
| Un plafond par catégorie, sur la période de paie à paie | Pas d'enveloppes à la YNAB |
| Jauge, consommé, restant | Ne mélange jamais consommé et à-venir |
| Alerte quand les échéances à venir feront dépasser | Pas de plafond partagé (lot 5) |

**État** : backend terminé et testé, écran à écrire.

---

## 6. Réglages — `ecrans/Reglages.tsx`

| Fait | Manque |
|---|---|
| Compte, transparence, invitation | Nombre de paies par cycle (`paies_par_cycle`) |
| Catégories : créer, renommer, retinter, supprimer | Gestion des comptes bancaires |
| Déconnexion | Archiver une catégorie (l'API le permet, pas l'écran) |

---

## Ordre d'exécution proposé

1. **Accueil : modifier, supprimer, voir le détail d'une opération** — c'est l'action la
   plus fréquente, et elle est aujourd'hui à sens unique.
2. **Calendrier : « à venir » sur le mois en cours** — correction rapide, demandée.
3. **Écran Budget** — le backend attend.
4. **Logos en ligne**, façon KeePassXC.
5. **Réglages : paies par cycle et comptes.**
6. **Lot 5** : comptes joints et partage. **Lot 6** : déploiement VPS.

---

## Ce qui reste à trancher

- Un compte supplémentaire : depuis les Réglages, ou depuis l'accueil ?
- Les plafonds du foyer, quand les comptes joints arriveront : quelle période commune,
  puisque chaque membre a la sienne ?
- ~~Mot de passe oublié : script, ou envoi de courriel ?~~ — **TRANCHÉ le 24 août 2026** : courriel, par une boîte d'envoi en base et un worker SMTP séparé (`scripts/traiter_courriels.py`).
