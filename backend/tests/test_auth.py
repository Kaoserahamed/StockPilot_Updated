"""Authentication: registration, login, token lifecycle and password reset."""

from fastapi.testclient import TestClient

from tests import factories

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def _register(client: TestClient, **overrides) -> dict:
    payload = {
        "owner_name": "Owner",
        "email": "new@test.com",
        "password": factories.DEFAULT_PASSWORD,
        "business_name": "New Shop",
        **overrides,
    }
    resp = client.post(REGISTER, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #
def test_register_creates_owner_and_business(client: TestClient) -> None:
    body = _register(client)
    assert body["email"] == "new@test.com"
    assert body["name"] == "Owner"
    assert body["is_active"] is True
    assert "hashed_password" not in body  # the hash must never be exposed

    headers = factories.login(client, "new@test.com")
    business = client.get("/api/v1/businesses/me", headers=headers)
    assert business.status_code == 200
    assert business.json()["name"] == "New Shop"


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        REGISTER,
        json={
            "owner_name": "Other",
            "email": "new@test.com",
            "password": factories.DEFAULT_PASSWORD,
            "business_name": "Other Shop",
        },
    )
    assert resp.status_code == 409


def test_register_requires_email_or_phone(client: TestClient) -> None:
    resp = client.post(
        REGISTER,
        json={
            "owner_name": "Nobody",
            "password": factories.DEFAULT_PASSWORD,
            "business_name": "No Contact",
        },
    )
    assert resp.status_code == 422


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post(
        REGISTER,
        json={
            "owner_name": "Owner",
            "email": "short@test.com",
            "password": "abc",
            "business_name": "Shop",
        },
    )
    assert resp.status_code == 422
    assert "6 characters" in resp.text


def test_register_accepts_phone_only_owner(client: TestClient) -> None:
    resp = client.post(
        REGISTER,
        json={
            "owner_name": "Phone Owner",
            "phone": "01700000000",
            "password": factories.DEFAULT_PASSWORD,
            "business_name": "Phone Shop",
        },
    )
    assert resp.status_code == 201, resp.text
    headers = factories.login(client, "01700000000")
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def test_login_returns_both_tokens(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        LOGIN, json={"username": "new@test.com", "password": factories.DEFAULT_PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"].lower() == "bearer"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    _register(client)
    resp = client.post(LOGIN, json={"username": "new@test.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_rejects_unknown_user(client: TestClient) -> None:
    resp = client.post(LOGIN, json={"username": "ghost@test.com", "password": "whatever1"})
    assert resp.status_code == 401


def test_deactivated_user_cannot_use_their_credentials(client: TestClient) -> None:
    headers = factories.register_owner(client, email="owner-d@test.com")
    employee = factories.create_employee(client, headers, email="emp-d@test.com")

    deactivated = client.post(
        f"/api/v1/employees/{employee['membership_id']}/deactivate", headers=headers
    )
    assert deactivated.status_code == 200

    resp = client.post(
        LOGIN, json={"username": "emp-d@test.com", "password": factories.DEFAULT_PASSWORD}
    )
    assert resp.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #
def test_me_requires_a_bearer_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_refresh_token_mints_a_usable_new_pair(client: TestClient) -> None:
    _register(client)
    tokens = client.post(
        LOGIN, json={"username": "new@test.com", "password": factories.DEFAULT_PASSWORD}
    ).json()

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200, resp.text
    refreshed = resp.json()
    assert refreshed["access_token"]

    headers = {"Authorization": f"Bearer {refreshed['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_access_token_cannot_be_replayed_as_a_refresh_token(client: TestClient) -> None:
    """The token `type` claim is enforced, so an access token cannot extend itself."""
    _register(client)
    tokens = client.post(
        LOGIN, json={"username": "new@test.com", "password": factories.DEFAULT_PASSWORD}
    ).json()

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401


def test_refresh_requires_the_token_field(client: TestClient) -> None:
    assert client.post("/api/v1/auth/refresh", json={}).status_code == 422


def test_refresh_rejects_an_invalid_token(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "nope"})
    assert resp.status_code == 401


def test_logout_is_stateless_and_acknowledged(client: TestClient) -> None:
    headers = factories.register_owner(client, email="logout@test.com")
    resp = client.post("/api/v1/auth/logout", headers=headers)
    assert resp.status_code == 200
    assert "message" in resp.json()


# --------------------------------------------------------------------------- #
# Password reset
# --------------------------------------------------------------------------- #
def test_forgot_password_does_not_leak_account_existence(client: TestClient) -> None:
    """Both branches must return the same message to prevent enumeration."""
    _register(client)
    known = client.post("/api/v1/auth/forgot-password", json={"username": "new@test.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"username": "ghost@test.com"})

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]


def test_password_reset_flow_changes_the_password(client: TestClient) -> None:
    _register(client)
    issued = client.post("/api/v1/auth/forgot-password", json={"username": "new@test.com"}).json()

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": issued["dev_token"], "new_password": "brand-new-pass"},
    )
    assert reset.status_code == 200, reset.text

    old = client.post(
        LOGIN, json={"username": "new@test.com", "password": factories.DEFAULT_PASSWORD}
    )
    new = client.post(LOGIN, json={"username": "new@test.com", "password": "brand-new-pass"})
    assert old.status_code == 401
    assert new.status_code == 200


def test_reset_token_is_single_use(client: TestClient) -> None:
    _register(client)
    token = client.post("/api/v1/auth/forgot-password", json={"username": "new@test.com"}).json()[
        "dev_token"
    ]

    first = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "first-pass-1"}
    )
    assert first.status_code == 200

    again = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "second-pass-2"}
    )
    assert again.status_code == 400


def test_reset_rejects_an_unknown_token(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/reset-password", json={"token": "made-up", "new_password": "whatever1"}
    )
    assert resp.status_code == 400
