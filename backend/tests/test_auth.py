def test_health_check(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "Cloud4Green Nexus with Apache Guacamole" in data["brand"]["product"]

def test_login_success(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@nexus.test",
        "password": "admin-secure-password-123"
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "admin@nexus.test"
    assert data["user"]["role"] == "admin"

def test_login_invalid_password(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@nexus.test",
        "password": "wrong-password"
    })
    assert r.status_code == 401
    assert "Invalid email, username, or password" in r.json()["detail"]

def test_auth_me(client, user1_headers):
    r = client.get("/api/v1/auth/me", headers=user1_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "user1@nexus.test"
    assert r.json()["role"] == "user"

def test_unauthorized_access(client):
    r = client.get("/api/v1/vms")
    assert r.status_code == 401
