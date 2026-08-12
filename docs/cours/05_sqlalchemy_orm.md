# 5. SQLAlchemy — ORM et modèles de données

## Qu'est-ce qu'un ORM et pourquoi

Un ORM (Object-Relational Mapper) traduit entre objets Python et lignes de
table SQL, pour éviter d'écrire du SQL brut partout et — surtout du point
de vue sécurité — pour utiliser des **requêtes paramétrées** qui empêchent
les injections SQL par construction.

## Anatomie d'un modèle (extrait réel : `MotorSession`)

```python
class MotorSession(Base):
    __tablename__ = "motor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="stopped")
```

- `Mapped[uuid.UUID]` : syntaxe SQLAlchemy 2.0 (typée), remplace l'ancienne
  syntaxe `Column(UUID, ...)` sans annotation de type
- `ForeignKey("users.id")` : contrainte d'intégrité référentielle — la base
  de données elle-même refuse qu'une session pointe vers un utilisateur
  inexistant
- `default=uuid.uuid4` : génère un UUID aléatoire à la création si aucune
  valeur n'est fournie

## Types de colonnes portables — un choix d'architecture spécifique à ce projet

```python
class PortableUUID(TypeDecorator):
    """Stocke un UUID natif sur Postgres, une chaîne CHAR(36) sur SQLite."""
```

PostgreSQL a un type UUID natif ; SQLite non. Comme le projet doit
fonctionner à la fois côté serveur (Postgres) et, plus tard, côté client
offline (SQLite), un type "portable" a été créé pour que le même modèle
fonctionne des deux côtés sans dupliquer le code. **C'est un bug réel
rencontré et corrigé pendant le développement** : le code utilisait
initialement `sqlalchemy.dialects.postgresql.UUID` directement, ce qui
cassait tous les tests (qui utilisent SQLite en mémoire).

## Session et transactions

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
Une `Session` SQLAlchemy représente une transaction en cours. Rien n'est
écrit en base tant qu'on n'appelle pas `db.commit()` :
```python
db.add(session)
db.commit()      # écrit réellement en base
db.refresh(session)  # relit les valeurs générées par la DB (ex: id, created_at)
```
**Erreur fréquente** : oublier `db.commit()` et se demander pourquoi les
données "disparaissent" — elles n'ont jamais été écrites.

## Requêtes

```python
db.query(MotorSession).filter(
    MotorSession.id == session_id,
    MotorSession.owner_id == user.id,
).first()
```
Cette requête fait DEUX choses à la fois : trouver la session ET vérifier
qu'elle appartient bien à l'utilisateur courant. C'est un choix de
sécurité délibéré : plutôt que de récupérer la session puis vérifier la
propriété en Python, le filtre est dans la requête SQL elle-même — un
utilisateur ne peut littéralement pas récupérer la session d'un autre,
même par erreur de code ultérieure.

## Pour aller plus loin
- Documentation SQLAlchemy 2.0 : https://docs.sqlalchemy.org/en/20/
- Tutoriel ORM : https://docs.sqlalchemy.org/en/20/orm/quickstart.html
