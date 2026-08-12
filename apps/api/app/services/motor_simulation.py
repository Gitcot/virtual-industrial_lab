"""
Pont entre la persistance (MotorSession, DB) et le moteur de simulation pur
(MotorSimulator, simulation/motor_engine.py). Garde le moteur physique
totalement indépendant de FastAPI/SQLAlchemy, comme l'exige le principe
d'architecture "Learning Engine testable seul".
"""
import sys
from pathlib import Path

# Le module simulation/ vit à la racine du repo, hors de apps/api/. On
# l'ajoute au sys.path pour l'importer sans dupliquer le code du moteur.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation.motor_engine import (  # noqa: E402
    FaultType,
    MotorParameters,
    MotorSimulator,
    MotorState,
    StartMode,
)

from app.models.motor_session import MotorSession  # noqa: E402


def simulator_from_session(session: MotorSession) -> MotorSimulator:
    """Reconstruit un MotorSimulator à partir de l'état persisté en DB."""
    params_dict = session.motor_parameters or {}
    params = MotorParameters(**params_dict) if params_dict else MotorParameters()

    sim = MotorSimulator(params=params)
    sim.state = MotorState(session.state)
    sim.elapsed_in_state_s = session.elapsed_in_state_s
    sim.simulated_temp_c = session.simulated_temp_c
    sim.current_a = session.current_a
    sim.voltage_v = session.voltage_v
    sim.fault_active = FaultType(session.fault_active) if session.fault_active else None
    return sim


def apply_simulator_to_session(sim: MotorSimulator, session: MotorSession) -> None:
    """Recopie l'état du simulateur (après une action) dans la ligne DB."""
    session.state = sim.state.value
    session.elapsed_in_state_s = sim.elapsed_in_state_s
    session.simulated_temp_c = sim.simulated_temp_c
    session.current_a = sim.current_a
    session.voltage_v = sim.voltage_v
    session.fault_active = sim.fault_active.value if sim.fault_active else None
