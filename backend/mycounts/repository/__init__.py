"""Seul package autorisé à interroger la base.

Toute lecture passe par ici et applique le périmètre de l'appelant. Le garde-fou
`scripts/verifier_scope_repository.py` refuse tout `select(...)` écrit ailleurs.
"""
