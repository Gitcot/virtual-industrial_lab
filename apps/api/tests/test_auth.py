def test_register_creates_user(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "test@vil.com", "password": "secret123", "full_name": "Test User"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "test@vil.com"


def test_register_duplicate_email_rejected(client):
    client.post("/api/auth/register", json={"email": "dup@vil.com", "password": "secret123"})
    r = client.post("/api/auth/register", json={"email": "dup@vil.com", "password": "secret123"})
    assert r.status_code == 400


def test_login_success_returns_token(client):
    client.post("/api/auth/register", json={"email": "login@vil.com", "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": "login@vil.com", "password": "secret123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "wrongpw@vil.com", "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": "wrongpw@vil.com", "password": "bad"})
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_valid_token(client):
    client.post("/api/auth/register", json={"email": "me@vil.com", "password": "secret123"})
    login = client.post("/api/auth/login", json={"email": "me@vil.com", "password": "secret123"})
    token = login.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@vil.com"
