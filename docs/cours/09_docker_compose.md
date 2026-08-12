# 9. Docker et Docker Compose

## Le problème résolu : "ça marche chez moi"

Sans conteneurisation, faire tourner PostgreSQL nécessite de l'installer
sur chaque machine de développement, avec des versions potentiellement
différentes. Docker encapsule PostgreSQL (et sa configuration) dans une
image portable qui tourne identiquement partout.

## `docker-compose.yml` du projet

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: vil_user
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: vil
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

Décomposition :
- `image: postgres:16` : télécharge l'image officielle PostgreSQL version 16
- `environment` : configure la base au premier démarrage (utilisateur,
  mot de passe, nom de base) — via des variables d'environnement lues par
  l'image officielle
- `ports: "5432:5432"` : rend le port 5432 du conteneur accessible depuis
  la machine hôte au même port (format `hôte:conteneur`)
- `volumes: pgdata:...` : **sans ce volume, toutes les données seraient
  perdues à chaque `docker compose down`** — le volume persiste les
  fichiers de la base même quand le conteneur est supprimé et recréé

## Commandes essentielles

```bash
docker compose up -d      # démarre en arrière-plan (-d = detached)
docker compose ps         # liste les services et leur état
docker compose down       # arrête et supprime les conteneurs (pas les volumes)
docker compose logs db    # affiche les logs du service "db"
```

## Le devcontainer (`.devcontainer/devcontainer.json`)

```json
{
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "postCreateCommand": "pip install -r apps/api/requirements.txt"
}
```
Différent de `docker-compose.yml` : le devcontainer définit
l'**environnement de développement lui-même** (VS Code tourne à
l'intérieur d'un conteneur Python 3.11 pré-configuré), alors que
`docker-compose.yml` définit les **services dont l'app a besoin**
(ici, juste PostgreSQL — l'API elle-même tourne directement dans le
devcontainer, pas dans un conteneur Docker séparé, pour simplifier le
rechargement à chaud pendant le développement).

## Pourquoi ne PAS conteneuriser l'API elle-même pour l'instant

Une architecture plus "production-ready" conteneuriserait aussi l'API
(un `Dockerfile` dédié + un service `api` dans `docker-compose.yml`).
Ce choix est repoussé à une phase de déploiement (Phase 11) — pendant le
développement actif, lancer l'API directement avec `uvicorn --reload`
donne un rechargement à chaud plus rapide qu'un rebuild d'image Docker à
chaque modification.

## Pour aller plus loin
- Documentation Docker Compose : https://docs.docker.com/compose/
- Documentation devcontainers : https://containers.dev/
