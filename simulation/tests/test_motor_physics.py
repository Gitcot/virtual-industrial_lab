import math

import pytest

from simulation.motor_physics import InductionMotorModel, NameplateData


def test_synchronous_speed_4_poles_50hz():
    """Valeur de référence connue: moteur 4 pôles / 50Hz -> Ns = 1500 tr/min (fait établi)."""
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, frequency_hz=50.0))
    assert m.synchronous_speed_rpm == pytest.approx(1500.0)


def test_synchronous_speed_2_poles_50hz():
    """2 pôles / 50Hz -> Ns = 3000 tr/min (fait établi)."""
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=2, frequency_hz=50.0))
    assert m.synchronous_speed_rpm == pytest.approx(3000.0)


def test_synchronous_speed_4_poles_60hz():
    """4 pôles / 60Hz (réseau US) -> Ns = 1800 tr/min (fait établi)."""
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, frequency_hz=60.0))
    assert m.synchronous_speed_rpm == pytest.approx(1800.0)


def test_rated_slip_from_real_nameplate_speed():
    """
    Cas réel: plaque indiquant 1450 tr/min pour un moteur 4 pôles/50Hz
    (Ns=1500). Glissement exact attendu: (1500-1450)/1500 = 0.0333...
    """
    m = InductionMotorModel(
        NameplateData(rated_power_kw=1.5, poles=4, frequency_hz=50.0, rated_speed_rpm=1450.0)
    )
    assert m.rated_slip == pytest.approx((1500 - 1450) / 1500)
    assert m.rated_speed_rpm == pytest.approx(1450.0)
    assert m.describe()["rated_slip_source"] == "mesurée (vitesse plaque)"


def test_rated_slip_estimated_when_speed_unknown():
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4))
    assert m.rated_slip == pytest.approx(0.04)  # DEFAULT_RATED_SLIP
    assert m.describe()["rated_slip_source"] == "estimée (valeur typique)"


def test_rated_torque_matches_power_speed_relation():
    """
    Vérification croisée par une seconde méthode (cf. master prompt §5 -
    "vérifier le résultat par une deuxième méthode"): P = T * omega, donc
    T = P / omega. Pour P=1500W et N=1450tr/min:
    omega = 1450 * 2*pi/60 = 151.84 rad/s
    T = 1500 / 151.84 = 9.878 N.m
    """
    m = InductionMotorModel(
        NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0)
    )
    omega = 1450.0 * 2 * math.pi / 60.0
    expected_torque = 1500.0 / omega
    assert m.rated_torque_nm == pytest.approx(expected_torque, rel=1e-6)


def test_torque_zero_at_synchronous_speed():
    """Fait théorique: à la vitesse de synchronisme (s=0), le couple est nul."""
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0))
    assert m.torque_at_speed(m.synchronous_speed_rpm) == 0.0


def test_torque_at_rated_slip_approximately_equals_rated_torque():
    """
    Test de cohérence interne: la formule de Kloss, évaluée au glissement
    nominal, doit redonner (approximativement) le couple nominal calculé
    indépendamment via P/omega. Une divergence significative indiquerait
    une incohérence entre les deux méthodes de calcul du modèle.
    """
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0))
    torque_from_kloss = m.torque_at_slip(m.rated_slip)
    # Kloss est une approximation autour du point nominal, pas une identité
    # exacte -> tolérance large mais qui doit rester dans un ordre de
    # grandeur cohérent (même signe, même ordre de grandeur)
    assert torque_from_kloss == pytest.approx(m.rated_torque_nm, rel=0.15)


def test_starting_torque_is_lower_than_breakdown_torque():
    """
    Fait théorique pour un moteur à cage standard: le couple de démarrage
    (s=1) est généralement inférieur au couple de décrochage (proche de
    s_max), car s=1 est loin du glissement optimal s_max.
    """
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0))
    assert m.starting_torque_nm() < m.breakdown_torque_nm


def test_starting_torque_ratio_reasonable_order_of_magnitude():
    """
    Pour un moteur standard, le rapport couple démarrage/nominal est
    typiquement entre 0.5 et 3 (ordre de grandeur usuel selon la classe de
    conception NEMA/IEC) - test de plausibilité, pas de valeur exacte.
    """
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0))
    ratio = m.starting_torque_ratio()
    assert 0.3 < ratio < 4.0


def test_invalid_power_rejected():
    with pytest.raises(ValueError):
        InductionMotorModel(NameplateData(rated_power_kw=-1, poles=4))


def test_invalid_poles_rejected():
    with pytest.raises(ValueError):
        InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=3))  # nombre impair invalide
    with pytest.raises(ValueError):
        InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=0))


def test_torque_at_slip_out_of_range_rejected():
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0))
    with pytest.raises(ValueError):
        m.torque_at_slip(2.0)
    with pytest.raises(ValueError):
        m.torque_at_slip(-0.5)


def test_describe_returns_traceable_summary():
    m = InductionMotorModel(NameplateData(rated_power_kw=1.5, poles=4, rated_speed_rpm=1450.0))
    summary = m.describe()
    assert set(summary.keys()) == {
        "synchronous_speed_rpm", "rated_speed_rpm", "rated_slip", "rated_slip_source",
        "rated_torque_nm", "breakdown_torque_nm", "breakdown_torque_ratio",
        "starting_torque_nm", "starting_torque_ratio",
    }


def test_larger_motor_different_nameplate():
    """Second cas réel indépendant, pour éviter de valider uniquement un seul jeu de valeurs."""
    m = InductionMotorModel(
        NameplateData(rated_power_kw=7.5, poles=2, frequency_hz=50.0, rated_speed_rpm=2900.0)
    )
    assert m.synchronous_speed_rpm == pytest.approx(3000.0)
    assert m.rated_slip == pytest.approx((3000 - 2900) / 3000)
    omega = 2900.0 * 2 * math.pi / 60.0
    assert m.rated_torque_nm == pytest.approx(7500.0 / omega, rel=1e-6)
