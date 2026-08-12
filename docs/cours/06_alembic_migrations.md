# 6. Alembic — migrations de base de données

## Le problème que les migrations résolvent

Un modèle SQLAlchemy décrit la structure voulue en Python, mais la base de
données réelle a sa propre structure figée (tables déjà créées). Une
**migration** est un script versionné qui fait évoluer la base d'un état
vers un autre (ajouter une colonne, une table, un index...) de façon
traçable et réversible.

## Génération automatique

```bash
python -m alembic revision --autogenerate -m "initial schema"
```
Alembic compare les modèles Python (`Base.metadata`) à l'état actuel de la
base, et génère un script Python avec les différences :
```python
def upgrade() -> None:
    op.create_table('users', ...)
    op.create_table('assets', ...)
    op.create_table('motor_sessions', ...)

def downgrade() -> None:
    op.drop_table('motor_sessions')
    op.drop_table('assets')
    op.drop_table('users')
```
`upgrade()` applique le changement, `downgrade()` l'annule — utile pour
revenir en arrière si une migration pose problème en production.

## `env.py` — le point de configuration

```python
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```
Ce fichier connecte Alembic à la config de l'app (`settings.database_url`)
et à la liste des modèles enregistrés (`Base.metadata`, qui n'existe que
si tous les modèles ont été importés — d'où `from app import models` en
haut du fichier, sinon Alembic "ne verrait" pas les tables).

## Bug réel rencontré : types personnalisés et autogenerate

`render_item` a dû être ajouté dans `env.py` :
```python
def render_item(type_, obj, autogen_context):
    if isinstance(obj, PortableUUID):
        autogen_context.imports.add("from app.core.types import PortableUUID")
        return "PortableUUID()"
    ...
```
Par défaut, Alembic ne sait pas comment "écrire" du code Python valide
pour un type de colonne personnalisé (`PortableUUID`) — il générait du
code avec des imports manquants. `render_item` lui apprend explicitement
comment représenter ce type dans le fichier de migration généré. **Leçon
générale** : autogenerate est un excellent point de départ, mais son
résultat doit toujours être relu avant d'être appliqué.

## Appliquer une migration

```bash
python -m alembic upgrade head
```
`head` signifie "la dernière migration connue". Sur une base neuve, ça
crée toutes les tables d'un coup en rejouant l'historique des migrations
dans l'ordre.

## Pour aller plus loin
- Documentation Alembic : https://alembic.sqlalchemy.org/en/latest/
- Tutoriel autogenerate : https://alembic.sqlalchemy.org/en/latest/autogenerate.html
