# L'API refuse de démarrer sur une base qui n'est pas à jour

La suppression d'une opération rendait « Not Found » sur la démonstration : le serveur
tournait sur le code d'avant la route. Une fois redémarré, elle rendait 500 — la base de
démonstration n'avait pas la colonne `annulee`.

- `api/app.py` compare au démarrage la révision de la base à la tête Alembic et refuse de
  démarrer si elles diffèrent, en nommant la commande à lancer.
- `Makefile` : la démonstration lance uvicorn avec `--reload`, comme le frontend.
- Témoin `tests/integration/test_garde_migrations.py`, vérifié par mutation.
