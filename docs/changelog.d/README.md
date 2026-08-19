# Journal des changements

Un fichier par changement : `<numéro>-<slug>.md`. Jamais de `CHANGELOG.md` unique — un
fichier partagé met toutes les branches en conflit.

Format :

```markdown
# <titre court>

**Lot** : 0 | **Date** : AAAA-MM-JJ

Ce qui change, et pourquoi. Si le changement touche un invariant ou un garde-fou, dire
lequel et comment il a été vérifié.
```

La doc part dans le **même commit** que le code, jamais après.
