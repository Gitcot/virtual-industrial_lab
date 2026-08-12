# Cours — Technologies du projet Virtual Industrial Lab

Ce dossier explique, thème par thème, les technologies réellement utilisées
dans le code livré (Phases 1-5). Chaque fichier s'appuie sur de vrais
extraits du projet, pas des exemples génériques déconnectés.

## Sommaire

| # | Fichier | Thème |
|---|---|---|
| 1 | `01_python_fondamentaux.md` | Python appliqué au backend |
| 2 | `02_architecture_logicielle.md` | Principes d'architecture du projet |
| 3 | `03_fastapi.md` | Framework API web |
| 4 | `04_pydantic_validation.md` | Validation de données |
| 5 | `05_sqlalchemy_orm.md` | ORM et modèles de base de données |
| 6 | `06_alembic_migrations.md` | Migrations de schéma |
| 7 | `07_authentification_jwt.md` | Sécurité, hashing, JWT |
| 8 | `08_tests_pytest.md` | Tests automatisés backend |
| 9 | `09_docker_compose.md` | Conteneurisation |
| 10 | `10_git_devcontainer.md` | Git, GitHub Codespaces, environnement reproductible |
| 11 | `11_javascript_moderne.md` | JS ES modules, async/await, fetch |
| 12 | `12_threejs_3d_web.md` | Rendu 3D dans le navigateur |
| 13 | `13_api_rest_design.md` | Conception d'API REST |
| 14 | `14_machines_a_etats.md` | Modélisation par état (le cœur du moteur de simulation) |
| 15 | `15_theorie_moteur_asynchrone.md` | Théorie électromagnétique (circuit équivalent, glissement, Kloss) |
| 16 | `16_blender_python_api.md` | API Python de Blender (bpy) — génération 3D procédurale |

## Comment lire ce cours

Chaque fichier suit la même structure : **concept** → **pourquoi on
l'utilise ici** → **extrait de code réel du projet** → **points de
vigilance / erreurs fréquentes** → **pour aller plus loin**.

Ce n'est pas un cours généraliste sur chaque technologie (des ressources
bien meilleures existent : documentation officielle, cours dédiés) — c'est
un cours **contextualisé** : pourquoi CE choix a été fait ICI, et comment le
code livré illustre le concept.
