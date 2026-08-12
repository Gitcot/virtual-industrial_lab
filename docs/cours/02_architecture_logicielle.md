# 2. Architecture logicielle du projet

## Le principe central : découplage du moteur de simulation

Le master prompt exige que le "SimulationEngine" soit testable seul, sans
dépendre de FastAPI ni de la base de données. C'est le principe
d'**architecture en couches** (layered architecture) :

```
simulation/motor_engine.py     <- logique métier PURE (aucun import FastAPI/DB)
        ↑ utilisé par
apps/api/app/services/motor_simulation.py   <- pont/adaptateur
        ↑ utilisé par
apps/api/app/api/routes/simulation.py       <- couche HTTP (FastAPI)
```

**Pourquoi ce découpage ?** Trois raisons concrètes vécues dans ce projet :
1. **Testabilité** : les 14 tests de `simulation/tests/test_motor_engine.py`
   s'exécutent en 0.05s, sans base de données, sans serveur HTTP. Un test
   qui dépendrait de l'API entière serait plus lent et plus fragile.
2. **Réutilisabilité** : le même moteur pourra un jour tourner côté client
   (offline-first, Phase 8) sans réécriture, puisqu'il n'a aucune
   dépendance à un serveur.
3. **Localisation des bugs** : quand un test échouait (température qui
   explose), on savait immédiatement que le problème était dans la
   physique du modèle, pas dans la couche HTTP ou la base de données.

## Le pattern "Adapter" (services/motor_simulation.py)

```python
def simulator_from_session(session: MotorSession) -> MotorSimulator:
    """Reconstruit un MotorSimulator à partir de l'état persisté en DB."""
    ...

def apply_simulator_to_session(sim: MotorSimulator, session: MotorSession) -> None:
    """Recopie l'état du simulateur (après une action) dans la ligne DB."""
    ...
```

Ce fichier ne contient aucune logique métier — il fait uniquement la
conversion entre deux représentations du même état (objet Python pur ↔
ligne de base de données). C'est le rôle d'un **adaptateur** : isoler le
reste du code des détails de persistance.

## Séparation Modèles / Schémas

Deux notions qu'on pourrait confondre :
- **Modèle** (`app/models/motor_session.py`, SQLAlchemy) : décrit une table
  de base de données.
- **Schéma** (`app/schemas/motor_session.py`, Pydantic) : décrit la forme
  des données échangées via l'API (JSON entrant/sortant).

Ils se ressemblent souvent mais ont des rôles différents : un modèle a des
colonnes internes (comme `owner_id`) qu'on ne veut jamais exposer
publiquement, alors que le schéma de sortie (`MotorSessionOut`) choisit
précisément quels champs sont visibles.

## Pourquoi une architecture Client (offline-first) / API / DB ?

Le master prompt impose l'offline-first (les Labs essentiels doivent
fonctionner sans réseau). Ça oriente des choix dès maintenant :
- Le moteur de simulation ne connaît pas la notion de "session HTTP" — il
  avance dans le temps via `tick(dt_seconds)`, appelable aussi bien par un
  serveur que par un client local plus tard.
- Les types de données (`PortableUUID`, `PortableJSON` dans
  `app/core/types.py`) fonctionnent aussi bien avec PostgreSQL (serveur)
  qu'avec SQLite (client local futur) — décision prise dès la Phase 2 pour
  ne pas devoir tout réécrire en Phase 8.

## Modularité Core + Labs

Le Core (auth, assets, moteur de simulation générique) est distinct des
Labs (contenu pédagogique spécifique : "laboratoire moteur électrique").
Dans le code actuel, `simulation/motor_engine.py` EST le premier Lab —
mais il est rangé dans un dossier séparé (`simulation/`, pas
`apps/api/app/labs/moteur/`) pour préfigurer la Phase 9 (Labs distribués
en packages versionnés, téléchargeables indépendamment).

## Pour aller plus loin
- "Clean Architecture", Robert C. Martin
- Pattern Adapter (Gang of Four) : https://refactoring.guru/design-patterns/adapter
