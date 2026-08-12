# 14. Machines à états — le cœur du moteur de simulation

## Le concept

Une machine à états finis modélise un système qui ne peut être que dans
UN état précis à la fois, parmi un ensemble fini, avec des règles claires
sur quelles transitions sont permises. C'est un des modèles les plus
adaptés pour représenter un équipement physique — un vrai moteur ne peut
pas être "à moitié démarré et à moitié en défaut" en même temps.

## Les états du moteur (extrait réel)

```python
class MotorState(str, enum.Enum):
    STOPPED = "stopped"
    STARTING_DIRECT = "starting_direct"
    STARTING_STAR = "starting_star"
    STARTING_DELTA = "starting_delta"
    RUNNING = "running"
    FAULT_THERMAL = "fault_thermal"
    FAULT_ELECTRICAL = "fault_electrical"
    TRIPPED = "tripped"
```

## Le diagramme de transitions (tel qu'implémenté)

```
STOPPED --start(direct)--> STARTING_DIRECT --(3s)--> RUNNING
STOPPED --start(star_delta)--> STARTING_STAR --(4s)--> STARTING_DELTA --(3s)--> RUNNING
RUNNING --stop()--> STOPPED
[STARTING_*, RUNNING] --inject_fault()--> FAULT_THERMAL | FAULT_ELECTRICAL
[FAULT_THERMAL, FAULT_ELECTRICAL] --reset()--> TRIPPED (si conditions OK)
TRIPPED --acknowledge_and_stop()--> STOPPED
```

## Pourquoi lever une exception plutôt que d'ignorer une action invalide

```python
def start(self, mode: StartMode) -> None:
    if self.state not in (MotorState.STOPPED,):
        raise InvalidTransitionError(
            f"Impossible de démarrer depuis l'état '{self.state.value}'. "
            "Le moteur doit être à l'arrêt (STOPPED)."
        )
```
Deux approches existaient : ignorer silencieusement une action invalide,
ou lever une exception explicite. Le choix fait ici (exception) a une
conséquence pédagogique directe : côté API, ça devient un code HTTP 409
avec un message clair — l'utilisateur du laboratoire comprend
immédiatement pourquoi son action a échoué, plutôt que de se demander
"pourquoi rien ne s'est passé".

## Séparer "déterminer la transition" et "calculer les valeurs"

C'est le bug le plus révélateur trouvé dans ce projet (voir cours 8) :

```python
def tick(self, dt_seconds: float) -> None:
    self.elapsed_in_state_s += dt_seconds
    self._process_state_transition()   # 1. d'abord : où en est-on ?
    self._update_current_and_voltage()  # 2. ensuite : quelles valeurs pour CET état ?
    self._update_thermal(dt_seconds)
    self._check_thermal_trip()
```
Version bugguée initiale : le courant était calculé AVANT de vérifier si
une transition d'état avait lieu — donc une mesure prise juste après une
transition reflétait encore l'ancien état. **Leçon générale** : dans une
machine à états, toujours déterminer l'état final AVANT de calculer les
valeurs qui en dépendent, jamais l'inverse.

## Modéliser le temps explicitement (`tick`), pas implicitement (timer)

```python
def tick(self, dt_seconds: float) -> None:
    ...
```
Plutôt qu'un timer réel (`setInterval`, thread avec `sleep`), le temps
avance uniquement quand `tick()` est appelé explicitement, avec une durée
choisie par l'appelant. **Pourquoi** : ça rend la simulation
déterministe et testable — un test peut simuler "200 secondes" en une
fraction de seconde réelle, en appelant `tick(1.0)` 200 fois dans une
boucle, sans jamais attendre.

## Où ce pattern peut se réutiliser dans le reste du projet

Toute future Lab (protections & mesures, automatisme/PLC, instrumentation)
suivra probablement le même pattern : un ensemble d'états finis, des
transitions explicites avec conditions vérifiées, un modèle physique
séparé de la représentation (DB ou 3D). Le moteur asynchrone est le
premier exemple concret, pas un cas isolé.

## Pour aller plus loin
- "State Pattern" (Gang of Four) : https://refactoring.guru/design-patterns/state
- Statecharts (David Harel) pour des machines à états plus complexes
  (états hiérarchiques, parallèles) si le besoin grandit
