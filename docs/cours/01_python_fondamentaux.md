# 1. Python fondamentaux appliqués au backend

## Pourquoi Python ici
Le master prompt du projet a retenu Python + FastAPI pour le backend :
écosystème scientifique riche (utile pour la simulation physique et,
plus tard, l'IA), lisibilité, typage optionnel qui aide à la maintenabilité
d'un projet appelé à grossir sur plusieurs années.

## Dataclasses — structurer des données sans boilerplate

Le moteur de simulation (`simulation/motor_engine.py`) utilise
`@dataclass` plutôt qu'une classe classique avec `__init__` écrit à la main :

```python
from dataclasses import dataclass, field

@dataclass
class MotorParameters:
    rated_voltage_v: float = 400.0
    rated_current_a: float = 3.2
    thermal_time_constant_s: float = 300.0
```

Sans `@dataclass`, il faudrait écrire manuellement `__init__`,
`__repr__`, `__eq__`. Le décorateur les génère automatiquement à partir
des annotations de type.

**Point de vigilance** : les valeurs par défaut mutables (listes, dicts)
ne doivent jamais être écrites directement (`champ: list = []`) — Python
partagerait la même liste entre toutes les instances. Utiliser
`field(default_factory=list)` à la place, comme dans :
```python
simulated_temp_c: float = field(init=False)
```

## Enum — représenter un ensemble fini d'états

```python
class MotorState(str, enum.Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    FAULT_THERMAL = "fault_thermal"
```

Hériter aussi de `str` (pas seulement `enum.Enum`) permet à la valeur
d'être directement sérialisable en JSON et comparable à une chaîne — utile
puisque l'état est stocké tel quel dans la base de données
(`session.state = sim.state.value`).

## Type hints et `from __future__ import annotations`

En haut de `motor_engine.py` :
```python
from __future__ import annotations
```
Ceci permet d'utiliser des types plus modernes (`FaultType | None` au lieu
de `Optional[FaultType]`) même sur des versions de Python qui ne les
supportent pas nativement dans les annotations. Les type hints ne sont pas
vérifiés à l'exécution par Python lui-même — ce sont des outils externes
(mypy, l'IDE, Pydantic) qui les exploitent.

## Exceptions personnalisées

```python
class InvalidTransitionError(Exception):
    """Levée quand une action est demandée dans un état qui ne l'autorise pas."""
```

Créer ses propres exceptions (plutôt que d'utiliser `Exception` brut ou
`ValueError` partout) permet au code appelant de distinguer précisément
les cas d'erreur :
```python
try:
    sim.start(mode)
except InvalidTransitionError as e:
    raise HTTPException(status_code=409, detail=str(e))
```
C'est ce qui permet à l'API de traduire une erreur métier (409 Conflict)
différemment d'une erreur de validation (422).

## Erreurs fréquentes observées pendant le développement de ce projet

1. **Confondre `parents[N]`** (pathlib) : `Path(__file__).resolve().parents[N]`
   remonte de N niveaux dans l'arborescence. Une erreur de comptage a
   cassé un import (`app/services/motor_simulation.py` vs
   `app/api/routes/simulation.py` ne sont pas à la même profondeur).
   **Toujours vérifier avec un test d'import** avant de continuer.

2. **Valeurs mutables par défaut** — voir plus haut.

## Pour aller plus loin
- Documentation officielle Python : https://docs.python.org/3/
- PEP 557 (dataclasses) : https://peps.python.org/pep-0557/
