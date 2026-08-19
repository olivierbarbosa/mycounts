# Récurrences et matérialisation (lot 3, socle)

**Lot** : 3 | **Date** : 2026-08-19

## Le piège du 31

`domain/recurrence.py` calcule chaque échéance **depuis la date d'ancrage**, jamais depuis
l'échéance précédente. Une récurrence au 31 glisse au 28 en février puis **revient au 31**
en mars. Un calcul partant de la date précédente resterait bloqué au 28 pour toujours : le
prélèvement réel, lui, retomberait au 31, et l'écart ne se verrait qu'après plusieurs mois
d'agenda faux.

Témoin exécuté : en calculant depuis l'échéance précédente, trois tests rougissent.

## Idempotence, portée par la base

Clé explicite : `UNIQUE (recurrence_id, date_operation)`, index partiel
`uq_operation_par_echeance`. Ce n'est **pas** un contrôle applicatif — deux exécutions
simultanées pourraient toutes deux constater l'absence puis toutes deux insérer.

Le job est réellement rejoué trois fois dans les tests. Les deux compteurs varient en sens
opposés : la première passe crée 3 et ignore 0, les suivantes créent 0 et ignorent 3.

## Un downgrade impossible, corrigé

`alembic revision --autogenerate` a produit une clé étrangère **anonyme** : la migration
s'appliquait, mais son `downgrade` appelait `drop_constraint(None, …)` et échouait. Une
migration qui ne sait pas revenir en arrière n'est utilisable qu'une fois.

Corrigé par une convention de nommage sur `MetaData`, et vérifié sur une base neuve :
montée complète, descente d'un cran, remontée, descente jusqu'à `base`, remontée.

## Accès depuis un autre appareil

`make demo` lance l'application, joignable via Tailscale. Le backend n'écoute que sur
`127.0.0.1` : seul le proxy l'atteint, il n'est exposé à aucun réseau — vérifié.
