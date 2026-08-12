import pytest

from simulation.frame_dimensions import frame_for_power


def test_small_motor_gets_small_frame():
    dims = frame_for_power(1.5)
    assert dims.frame_designation == "90S"


def test_frame_dimensions_increase_with_power():
    """Test de cohérence: plus la puissance demandée est grande, plus la carcasse doit être grande ou égale."""
    powers = [0.5, 1.5, 4.0, 11.0, 30.0, 75.0]
    dims_list = [frame_for_power(p) for p in powers]
    diameters = [d.body_diameter_mm for d in dims_list]
    assert diameters == sorted(diameters), "les diamètres doivent croître avec la puissance"


def test_exact_boundary_power_matches_table_entry():
    dims = frame_for_power(0.75)
    assert dims.frame_designation == "80"


def test_extrapolation_beyond_table_is_flagged():
    dims = frame_for_power(500.0)  # bien au-delà de la table
    assert "extrapolé" in dims.frame_designation


def test_negative_power_rejected():
    with pytest.raises(ValueError):
        frame_for_power(-1.0)


def test_zero_power_rejected():
    with pytest.raises(ValueError):
        frame_for_power(0.0)


def test_all_dimensions_positive():
    for p in [0.37, 1.5, 7.5, 30.0, 110.0]:
        dims = frame_for_power(p)
        assert dims.shaft_height_mm > 0
        assert dims.body_diameter_mm > 0
        assert dims.body_length_mm > 0
        assert dims.shaft_diameter_mm > 0
        assert dims.shaft_length_mm > 0
