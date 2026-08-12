def _get_token(client, email="motor-user@vil.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    return r.json()["access_token"]


def test_create_session_defaults_to_stopped(client):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/simulation/sessions", json={}, headers=headers)
    assert r.status_code == 201
    assert r.json()["state"] == "stopped"
    assert r.json()["current_a"] == 0.0


def test_start_direct_then_tick_shows_high_current(client):
    token = _get_token(client, "motor2@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    session_id = client.post("/api/simulation/sessions", json={}, headers=headers).json()["id"]

    r = client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "direct"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["state"] == "starting_direct"

    r = client.post(f"/api/simulation/sessions/{session_id}/tick", json={"dt_seconds": 0.5}, headers=headers)
    assert r.status_code == 200
    assert r.json()["current_a"] > r.json()["voltage_v"] * 0  # sanity: current > 0
    assert r.json()["current_a"] > 10  # inrush attendu nettement au-dessus du nominal (~3.2A)


def test_full_start_sequence_reaches_running(client):
    token = _get_token(client, "motor3@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    session_id = client.post("/api/simulation/sessions", json={}, headers=headers).json()["id"]
    client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "direct"}, headers=headers)

    state = None
    for _ in range(20):
        r = client.post(f"/api/simulation/sessions/{session_id}/tick", json={"dt_seconds": 0.5}, headers=headers)
        state = r.json()["state"]
        if state == "running":
            break
    assert state == "running"


def test_cannot_start_twice_returns_409(client):
    token = _get_token(client, "motor4@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    session_id = client.post("/api/simulation/sessions", json={}, headers=headers).json()["id"]
    client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "direct"}, headers=headers)
    r = client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "direct"}, headers=headers)
    assert r.status_code == 409


def test_invalid_start_mode_returns_422(client):
    token = _get_token(client, "motor5@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    session_id = client.post("/api/simulation/sessions", json={}, headers=headers).json()["id"]
    r = client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "warp_speed"}, headers=headers)
    assert r.status_code == 422


def test_fault_injection_and_reset_flow(client):
    token = _get_token(client, "motor6@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    session_id = client.post("/api/simulation/sessions", json={}, headers=headers).json()["id"]
    client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "direct"}, headers=headers)
    client.post(f"/api/simulation/sessions/{session_id}/tick", json={"dt_seconds": 1.0}, headers=headers)

    r = client.post(
        f"/api/simulation/sessions/{session_id}/fault",
        json={"fault_type": "phase_loss"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["state"] == "fault_electrical"

    # reset devrait fonctionner immédiatement pour un défaut électrique (pas de contrainte thermique)
    r = client.post(f"/api/simulation/sessions/{session_id}/reset", headers=headers)
    assert r.status_code == 200
    assert r.json()["state"] == "tripped"

    r = client.post(f"/api/simulation/sessions/{session_id}/acknowledge", headers=headers)
    assert r.status_code == 200
    assert r.json()["state"] == "stopped"


def test_sessions_are_isolated_per_user(client):
    token1 = _get_token(client, "motor7a@vil.com")
    token2 = _get_token(client, "motor7b@vil.com")
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    session_id = client.post("/api/simulation/sessions", json={}, headers=headers1).json()["id"]

    # user2 ne doit pas pouvoir accéder à la session de user1
    r = client.get(f"/api/simulation/sessions/{session_id}", headers=headers2)
    assert r.status_code == 404


def test_sessions_require_auth(client):
    r = client.post("/api/simulation/sessions", json={})
    assert r.status_code == 401


def test_custom_rated_parameters_are_used(client):
    token = _get_token(client, "motor8@vil.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/simulation/sessions",
        json={"rated_current_a": 10.0, "rated_voltage_v": 230.0},
        headers=headers,
    )
    session_id = r.json()["id"]
    client.post(f"/api/simulation/sessions/{session_id}/start", json={"mode": "direct"}, headers=headers)
    r = client.post(f"/api/simulation/sessions/{session_id}/tick", json={"dt_seconds": 0.5}, headers=headers)
    # courant d'appel attendu ~ 6.5 x 10A = 65A (vs ~20.8A avec les valeurs par défaut 3.2A)
    assert r.json()["current_a"] > 50
