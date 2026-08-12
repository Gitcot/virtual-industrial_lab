import pytest

from simulation.motor_engine import (
    FaultType,
    InvalidTransitionError,
    MotorSimulator,
    MotorState,
    StartMode,
)


def test_initial_state_is_stopped():
    m = MotorSimulator()
    assert m.state == MotorState.STOPPED
    assert m.current_a == 0.0


def _run_ticks(motor: MotorSimulator, total_seconds: float, dt: float = 0.5) -> None:
    """Avance la simulation par petits pas, comme le ferait un client UI réel."""
    remaining = total_seconds
    while remaining > 1e-9:
        step = min(dt, remaining)
        motor.tick(step)
        remaining -= step


def test_direct_start_sets_high_current_then_running():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    assert m.state == MotorState.STARTING_DIRECT

    m.tick(0.5)
    assert m.current_a == pytest.approx(m.params.rated_current_a * m.params.starting_current_ratio)
    assert m.state == MotorState.STARTING_DIRECT

    _run_ticks(m, m.DIRECT_STARTUP_DURATION_S + 1.0, dt=0.5)
    assert m.state == MotorState.RUNNING
    assert m.current_a == pytest.approx(m.params.rated_current_a)


def test_star_delta_start_reduces_inrush_current():
    m = MotorSimulator()
    m.start(StartMode.STAR_DELTA)
    assert m.state == MotorState.STARTING_STAR

    m.tick(0.5)
    expected_star_current = (
        m.params.rated_current_a * m.params.starting_current_ratio * m.params.star_current_ratio_factor
    )
    assert m.current_a == pytest.approx(expected_star_current)

    # avance jusqu'à bascule delta
    _run_ticks(m, m.STAR_PHASE_DURATION_S, dt=0.5)
    assert m.state == MotorState.STARTING_DELTA

    # avance jusqu'à running
    _run_ticks(m, m.DIRECT_STARTUP_DURATION_S + 1.0, dt=0.5)
    assert m.state == MotorState.RUNNING


def test_star_delta_inrush_lower_than_direct():
    """Le point pédagogique clé : Y/D réduit l'appel de courant vs direct."""
    direct = MotorSimulator()
    direct.start(StartMode.DIRECT)
    direct.tick(0.5)

    star = MotorSimulator()
    star.start(StartMode.STAR_DELTA)
    star.tick(0.5)

    assert star.current_a < direct.current_a


def test_cannot_start_twice():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    with pytest.raises(InvalidTransitionError):
        m.start(StartMode.DIRECT)


def test_stop_from_running_returns_to_stopped():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    _run_ticks(m, m.DIRECT_STARTUP_DURATION_S + 2.0, dt=0.5)
    assert m.state == MotorState.RUNNING
    m.stop()
    assert m.state == MotorState.STOPPED
    assert m.current_a == 0.0


def test_electrical_fault_injection():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    _run_ticks(m, m.DIRECT_STARTUP_DURATION_S + 2.0, dt=0.5)
    m.inject_fault(FaultType.PHASE_LOSS)
    assert m.state == MotorState.FAULT_ELECTRICAL
    assert m.current_a == 0.0


def test_cannot_inject_fault_when_stopped():
    m = MotorSimulator()
    with pytest.raises(InvalidTransitionError):
        m.inject_fault(FaultType.PHASE_LOSS)


def test_thermal_trip_occurs_under_sustained_high_current():
    """
    Simule un défaut de surcharge : on force un courant élevé prolongé et on
    vérifie que la protection thermique se déclenche automatiquement.
    """
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    # reste en régime de démarrage (courant élevé) largement au-delà de la
    # durée normale, en avançant par petits pas pour laisser le modèle
    # thermique intégrer l'échauffement
    m.DIRECT_STARTUP_DURATION_S = 999999  # empêche la bascule vers RUNNING pour ce test
    tripped = False
    for _ in range(200):
        m.tick(1.0)
        if m.state == MotorState.FAULT_THERMAL:
            tripped = True
            break
    assert tripped, "La protection thermique aurait dû se déclencher sous courant de démarrage prolongé"


def test_reset_refused_while_still_hot():
    m = MotorSimulator()
    m.inject_fault_for_test = None  # no-op, juste lisibilité
    m.start(StartMode.DIRECT)
    m.DIRECT_STARTUP_DURATION_S = 999999
    for _ in range(200):
        m.tick(1.0)
        if m.state == MotorState.FAULT_THERMAL:
            break
    assert m.state == MotorState.FAULT_THERMAL

    with pytest.raises(InvalidTransitionError):
        m.reset()


def test_reset_succeeds_after_cooldown():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    m.DIRECT_STARTUP_DURATION_S = 999999
    for _ in range(200):
        m.tick(1.0)
        if m.state == MotorState.FAULT_THERMAL:
            break
    assert m.state == MotorState.FAULT_THERMAL

    # laisse refroidir : courant nul pendant longtemps -> température redescend
    for _ in range(500):
        m.tick(1.0)

    m.reset()
    assert m.state == MotorState.TRIPPED
    m.acknowledge_and_stop()
    assert m.state == MotorState.STOPPED


def test_cannot_stop_directly_from_fault_requires_reset():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    _run_ticks(m, m.DIRECT_STARTUP_DURATION_S + 2.0, dt=0.5)
    m.inject_fault(FaultType.PHASE_LOSS)
    with pytest.raises(InvalidTransitionError):
        m.stop()


def test_read_measurements_shape():
    m = MotorSimulator()
    m.start(StartMode.DIRECT)
    m.tick(1.0)
    data = m.read_measurements()
    assert set(data.keys()) == {"state", "voltage_v", "current_a", "simulated_temp_c", "fault_active"}
    assert data["state"] == "starting_direct"
    assert data["fault_active"] is None


def test_tick_rejects_non_positive_dt():
    m = MotorSimulator()
    with pytest.raises(ValueError):
        m.tick(0)
    with pytest.raises(ValueError):
        m.tick(-1)
