import shutil

import pytest

BLENDER_AVAILABLE = shutil.which("blender") is not None


def _get_token(client, email="motorgen@vil.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    return r.json()["access_token"]


def _create_asset_with_nameplate(client, headers, power_kw=1.5, poles=4, rated_speed_rpm=1450.0):
    r = client.post(
        "/api/assets",
        json={
            "name": "Moteur test",
            "manufacturer": "Générique",
            "electrical_properties": {
                "rated_power_kw": power_kw,
                "frequency_hz": 50.0,
                "rated_voltage_v": 400.0,
                "rated_current_a": 3.2,
            },
            "mechanical_properties": {
                "poles": poles,
                "rated_speed_rpm": rated_speed_rpm,
            },
        },
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_motor_physics_requires_nameplate_data(client):
    token = _get_token(client, "physics1@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/assets", json={"name": "Asset sans plaque"}, headers=headers)
    asset_id = r.json()["id"]

    r = client.get(f"/api/assets/{asset_id}/motor-physics", headers=headers)
    assert r.status_code == 422


def test_motor_physics_computed_from_real_nameplate(client):
    token = _get_token(client, "physics2@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset_id = _create_asset_with_nameplate(client, headers, power_kw=1.5, poles=4, rated_speed_rpm=1450.0)

    r = client.get(f"/api/assets/{asset_id}/motor-physics", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["synchronous_speed_rpm"] == pytest.approx(1500.0)
    assert data["rated_speed_rpm"] == pytest.approx(1450.0)
    assert data["rated_slip_source"] == "mesurée (vitesse plaque)"
    assert data["rated_torque_nm"] > 0
    assert data["breakdown_torque_nm"] > data["rated_torque_nm"]


def test_motor_physics_estimated_slip_when_speed_missing(client):
    token = _get_token(client, "physics3@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/assets",
        json={
            "name": "Moteur sans vitesse plaque",
            "electrical_properties": {"rated_power_kw": 2.2},
            "mechanical_properties": {"poles": 4},
        },
        headers=headers,
    )
    asset_id = r.json()["id"]

    r = client.get(f"/api/assets/{asset_id}/motor-physics", headers=headers)
    assert r.status_code == 200
    assert r.json()["rated_slip_source"] == "estimée (valeur typique)"


def test_frame_dimensions_estimated_from_power(client):
    token = _get_token(client, "frame1@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset_id = _create_asset_with_nameplate(client, headers, power_kw=1.5)

    r = client.get(f"/api/assets/{asset_id}/frame-dimensions", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["frame_designation"] == "90S"
    assert data["body_diameter_mm"] > 0


def test_frame_dimensions_uses_real_geometry_when_provided(client):
    token = _get_token(client, "frame2@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/assets",
        json={
            "name": "Moteur avec cotes constructeur réelles",
            "electrical_properties": {"rated_power_kw": 1.5},
            "mechanical_properties": {"poles": 4},
            "geometry": {
                "frame_designation": "90S-RealManufacturerXYZ",
                "shaft_height_mm": 91.5,  # cote réelle légèrement différente de la norme
                "body_diameter_mm": 152.0,
                "body_length_mm": 228.0,
                "shaft_diameter_mm": 24.0,
                "shaft_length_mm": 50.0,
            },
        },
        headers=headers,
    )
    asset_id = r.json()["id"]

    r = client.get(f"/api/assets/{asset_id}/frame-dimensions", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["frame_designation"] == "90S-RealManufacturerXYZ"
    assert data["body_diameter_mm"] == 152.0  # cote réelle utilisée, pas l'estimation IEC


@pytest.mark.skipif(not BLENDER_AVAILABLE, reason="Blender non installé sur cette machine")
def test_generate_and_download_3d_model_end_to_end(client):
    """
    Test de bout en bout réel : crée un Asset, déclenche la génération
    Blender via l'API, télécharge le GLB produit, vérifie qu'il est
    structurellement valide.
    """
    from pygltflib import GLTF2

    token = _get_token(client, "gen3d@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset_id = _create_asset_with_nameplate(client, headers, power_kw=1.5, poles=4, rated_speed_rpm=1450.0)

    r = client.post(f"/api/assets/{asset_id}/generate-3d-model", headers=headers)
    assert r.status_code == 200
    assert r.json()["file_size_bytes"] > 1000

    r = client.get(f"/api/assets/{asset_id}/3d-model", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "model/gltf-binary"

    import io
    # FileResponse via TestClient : le contenu binaire est dans r.content
    gltf = GLTF2().load_from_bytes(r.content)
    assert len(gltf.meshes) > 0
    node_names = {n.name for n in gltf.nodes}
    assert "MotorBody" in node_names


def test_3d_model_download_404_before_generation(client):
    token = _get_token(client, "gen3d_404@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset_id = _create_asset_with_nameplate(client, headers)

    r = client.get(f"/api/assets/{asset_id}/3d-model", headers=headers)
    assert r.status_code == 404
