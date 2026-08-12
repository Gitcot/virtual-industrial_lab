# 8. Tests automatisés (pytest)

## Pourquoi tester, concrètement (pas en théorie)

Ce projet a eu **5 bugs réels** trouvés uniquement parce que des tests ont
été exécutés — pas parce que le code "avait l'air correct" :
1. Types Postgres-only (`JSONB`, `UUID`) cassaient sur SQLite
2. Version de `bcrypt` incompatible avec `passlib`
3. Imports manquants dans les migrations Alembic générées
4. Courant resté basé sur l'état précédent après une transition
5. Constante thermique irréaliste (le moteur "grillait" en 4 secondes)

Aucun de ces bugs n'était visible à la simple lecture du code — chacun
n'est apparu qu'à l'exécution des tests.

## Fixtures — préparer un contexte de test réutilisable

```python
@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
```

Cette fixture (dans `conftest.py`) :
1. Crée toutes les tables sur une base SQLite en mémoire
2. Remplace la dépendance `get_db` de l'API par une version pointant vers
   cette base de test (au lieu de la vraie base Postgres)
3. Fournit un `TestClient` (simule des requêtes HTTP sans vrai serveur)
4. Nettoie tout après le test

Chaque fonction de test qui prend `client` en paramètre reçoit
automatiquement cet environnement isolé — **aucun test ne pollue les
autres**.

## `StaticPool` — un piège SQLite spécifique

```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```
Sans `StaticPool`, chaque connexion à `sqlite:///:memory:` créerait une
base **différente et vide** — les données écrites dans un test
"disparaîtraient" pour la requête suivante. `StaticPool` force toutes les
connexions à réutiliser la même connexion sous-jacente. **C'est un bug
réel rencontré pendant le développement** de ce projet.

## Tester les cas d'erreur, pas seulement les cas de succès

```python
def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "wrongpw@vil.com", "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": "wrongpw@vil.com", "password": "bad"})
    assert r.status_code == 401
```
Un test qui ne vérifie que les cas heureux donne une fausse confiance. La
suite de ce projet teste systématiquement : doublons, tokens absents,
transitions d'état interdites, isolation entre utilisateurs.

## Tests purs vs tests d'intégration

- `simulation/tests/test_motor_engine.py` : teste `MotorSimulator` en
  isolation totale (aucune DB, aucune API) — rapide, précis sur la
  logique physique
- `apps/api/tests/test_simulation.py` : teste le comportement à travers
  toute la pile (HTTP → auth → DB → moteur) — plus lent, vérifie que
  l'assemblage fonctionne

Les deux sont nécessaires et complémentaires : le premier isole les bugs
de logique, le second isole les bugs d'intégration (comme le calcul
`parents[N]` erroné mentionné au cours 1, invisible dans un test pur).

## Pour aller plus loin
- Documentation pytest : https://docs.pytest.org/
- FastAPI + tests : https://fastapi.tiangolo.com/tutorial/testing/
