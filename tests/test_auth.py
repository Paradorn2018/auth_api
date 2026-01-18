# tests/test_auth.py
import secrets


BASE = "/api/v1/auth"


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def test_register_login_me(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    password = "1234"

    # register
    r = client.post(f"{BASE}/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == email
    assert body["is_active"] is True

    # login
    r = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev1"})
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # view-profile
    r = client.get(f"{BASE}/view-profile", headers=_auth_headers(tokens["access_token"]))
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["email"] == email


def test_edit_profile(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    password = "1234"

    client.post(f"{BASE}/register", json={"email": email, "password": password})
    tokens = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev1"}).json()

    r = client.patch(
        f"{BASE}/edit-profile",
        json={"full_name": "Paradorn", "phone": "0812345678"},
        headers=_auth_headers(tokens["access_token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["full_name"] == "Paradorn"
    assert body["phone"] == "0812345678"


def test_change_password_revokes_sessions(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    old = "1234"
    new = "abcd1234"

    client.post(f"{BASE}/register", json={"email": email, "password": old})
    tokens1 = client.post(f"{BASE}/login", json={"email": email, "password": old, "device_id": "dev1"}).json()

    r = client.post(
        f"{BASE}/change-password",
        json={"old_password": old, "new_password": new},
        headers=_auth_headers(tokens1["access_token"]),
    )
    assert r.status_code == 200, r.text

    # old password should fail login
    r = client.post(f"{BASE}/login", json={"email": email, "password": old, "device_id": "dev2"})
    assert r.status_code == 401, r.text

    # new password should work
    tokens2 = client.post(f"{BASE}/login", json={"email": email, "password": new, "device_id": "dev2"}).json()
    assert "access_token" in tokens2

    # refresh with old refresh token should fail because sessions revoked
    r = client.post(f"{BASE}/refresh-access-token", json={"refresh_token": tokens1["refresh_token"]})
    assert r.status_code == 401, r.text


def test_refresh_rotation(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    password = "1234"

    client.post(f"{BASE}/register", json={"email": email, "password": password})
    tokens = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev1"}).json()

    # refresh once -> ok
    r = client.post(f"{BASE}/refresh-access-token", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, r.text
    new_tokens = r.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # refresh with old token again -> should fail (rotated/revoked)
    r = client.post(f"{BASE}/refresh-access-token", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401, r.text


def test_logout_makes_refresh_invalid(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    password = "1234"

    client.post(f"{BASE}/register", json={"email": email, "password": password})
    tokens = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev1"}).json()

    r = client.post(f"{BASE}/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, r.text

    # refresh after logout -> should fail
    r = client.post(f"{BASE}/refresh-access-token", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401, r.text


def test_logout_all(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    password = "1234"

    client.post(f"{BASE}/register", json={"email": email, "password": password})
    t1 = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev1"}).json()
    t2 = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev2"}).json()

    r = client.post(f"{BASE}/logout-all", headers=_auth_headers(t1["access_token"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["revoked"] >= 1

    # both refresh tokens should now fail
    r = client.post(f"{BASE}/refresh-access-token", json={"refresh_token": t1["refresh_token"]})
    assert r.status_code == 401, r.text
    r = client.post(f"{BASE}/refresh-access-token", json={"refresh_token": t2["refresh_token"]})
    assert r.status_code == 401, r.text


def test_forgot_and_reset_password(client):
    email = f"u_{secrets.token_hex(4)}@a.com"
    password = "1234"
    new_password = "9999aaaa"

    client.post(f"{BASE}/register", json={"email": email, "password": password})

    # forgot password (DEV mode should return reset_token)
    r = client.post(f"{BASE}/forgot-password", json={"email": email})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "ok"
    assert "reset_token" in data  # ต้องมีใน ENV=dev
    reset_token = data["reset_token"]

    # reset
    r = client.post(f"{BASE}/reset-password", json={"token": reset_token, "new_password": new_password})
    assert r.status_code == 200, r.text

    # login with old -> fail
    r = client.post(f"{BASE}/login", json={"email": email, "password": password, "device_id": "dev1"})
    assert r.status_code == 401, r.text

    # login with new -> ok
    r = client.post(f"{BASE}/login", json={"email": email, "password": new_password, "device_id": "dev1"})
    assert r.status_code == 200, r.text
