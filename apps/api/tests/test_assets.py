def _get_token(client, email="asset-user@vil.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    return r.json()["access_token"]


def test_create_and_list_asset(client):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/assets",
        json={
            "name": "Moteur asynchrone 1.5kW",
            "manufacturer": "Leroy Somer",
            "electrical_properties": {"voltage_v": 400, "current_a": 3.2},
        },
        headers=headers,
    )
    assert r.status_code == 201
    asset_id = r.json()["id"]

    r = client.get("/api/assets", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/api/assets/{asset_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["electrical_properties"]["voltage_v"] == 400


def test_get_unknown_asset_404(client):
    token = _get_token(client, "asset-user2@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/assets/00000000-0000-0000-0000-000000000000", headers=headers)
    assert r.status_code == 404


def test_assets_require_auth(client):
    r = client.get("/api/assets")
    assert r.status_code == 401
