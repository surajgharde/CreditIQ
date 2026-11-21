"""
Every endpoint that touches borrower data requires a token.

Before, only the drafts and profile routers looked at a request's identity at
all, and both took it from an X-User-Email header that any caller could set.
Upload, analyze, results, fraud, CAM, EWS and history were open, and the admin
credentials were the literals admin@gmail.com / admin@123 in the source.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ADMIN_EMAIL = "pytest-admin@example.com"
ADMIN_PASSWORD = "pytest-password-not-a-default"

PROTECTED_GETS = [
    "/api/history",
    "/api/results/1",
    "/api/shap-chart/1",
    "/api/fraud/1",
    "/api/fraud/graph/1",
    "/api/ews/1",
    "/api/ews/all-loans",
    "/api/cam/preview/1",
    "/api/cam/download/1",
    "/api/analysis/latest",
    "/api/profile/telegram",
    "/api/profile/companies",
    "/api/health/live",
    "/api/status/1",
]

PROTECTED_POSTS = [
    "/api/upload",
    "/api/analyze/1",
    "/api/cam/generate/1",
    "/api/analysis/save",
    "/api/ews/acknowledge/1",
    "/api/chat",
]


@pytest.fixture(scope="module")
def client(monkeypatch_module=None):
    os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL
    os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD
    os.environ["JWT_SECRET"] = "pytest-jwt-secret"
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)


@pytest.fixture(scope="module")
def auth_header(client):
    response = client.post(
        "/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_get_requires_a_token(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", PROTECTED_POSTS)
def test_post_requires_a_token(client, path):
    assert client.post(path).status_code == 401


def test_a_garbage_token_is_rejected(client):
    response = client.get("/api/history", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_the_old_hardcoded_credentials_do_not_work(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@gmail.com", "password": "admin@123"},
    )
    assert response.status_code == 401


def test_the_configured_admin_can_sign_in_and_read(client, auth_header):
    assert client.get("/api/history", headers=auth_header).status_code == 200
    me = client.get("/api/auth/me", headers=auth_header)
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL


def test_the_liveness_probe_stays_public(client):
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_drafts_are_scoped_to_the_token_not_a_header(client, auth_header):
    """An X-User-Email header must not select whose draft is returned."""
    client.post(
        "/api/analysis/save",
        headers=auth_header,
        json={
            "company_name": "Token Owner Ltd",
            "cin_number": "U00000MH2020PTC000001",
            "gstin_number": "29AAAAA0000A1Z5",
            "pan_number": "AAAAA0000A",
            "loan_amount": 1_000_000,
        },
    )
    spoofed = client.get(
        "/api/analysis/latest",
        headers={**auth_header, "X-User-Email": "someone-else@example.com"},
    )
    assert spoofed.status_code == 200
    assert spoofed.json()["data"]["company_name"] == "Token Owner Ltd"


def test_websockets_require_the_token_in_the_query_string(client, auth_header):
    token = auth_header["Authorization"].split(" ", 1)[1]
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/analysis/1"):
            pass
    with client.websocket_connect(f"/ws/analysis/1?token={token}") as socket:
        assert socket is not None


def test_cors_does_not_allow_every_origin():
    from config import config
    assert "*" not in config.CORS_ORIGINS
    assert config.CORS_ORIGINS
