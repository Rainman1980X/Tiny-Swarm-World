"""Bounded, value-free API acceptance for caller-selected effective-model routes."""

from __future__ import annotations

import secrets
from typing import TypedDict
from urllib.parse import urlsplit

import requests


class AuthenticationResult(TypedDict):
    authenticated_access_verified: bool
    invalid_rejected: bool
    redacted_failure_reason: str


def probe_authentication(
    route_name: str, base_url: str, username: str, password: str,
    verify: bool | str = True,
) -> AuthenticationResult:
    """Perform one invalid login, then a fresh valid login; never return values.

    Caller owns applicability, live consent, credentials, TLS trust, and evidence.
    For Infisical and Pulsar's admin API, identity evidence is a credential-
    authenticated protected read operation; these APIs do not echo the principal.
    For Pulsar's admin API, username labels the expected superuser role and
    password carries the managed bearer token.
    """
    if route_name not in {"jenkins", "nexus", "sonarqube", "portainer", "pulsar-manager",
                          "pulsar-admin-api", "infisical"}:
        return _result(False, False, "unsupported_route")
    try:
        parsed = urlsplit(base_url)
    except ValueError:
        return _result(False, False, "invalid_configuration")
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or not username or not password):
        return _result(False, False, "invalid_configuration")
    invalid_password = secrets.token_urlsafe(32)
    if invalid_password == password:
        invalid_password += "-invalid"
    try:
        _, rejected = _attempt(route_name, base_url.rstrip("/"), username, invalid_password, verify)
        identity, _ = _attempt(route_name, base_url.rstrip("/"), username, password, verify)
    except (ValueError, TypeError, KeyError):
        return _result(False, False, "invalid_response")
    except requests.RequestException:
        return _result(False, False, "transport_failure")
    reason = "" if identity and rejected else (
        "invalid_credentials_not_rejected" if not rejected else "identity_not_verified"
    )
    return _result(identity, rejected, reason)


def _result(identity: bool, rejected: bool, reason: str) -> AuthenticationResult:
    return {"authenticated_access_verified": identity, "invalid_rejected": rejected,
            "redacted_failure_reason": reason}


def _attempt(route: str, url: str, username: str, password: str,
             verify: bool | str) -> tuple[bool, bool]:
    with requests.Session() as session:
        # Prevent ambient netrc credentials or a previous attempt's cookies from
        # turning an intentionally invalid login into another user's session.
        session.trust_env = False
        session.verify = verify
        if route == "pulsar-admin-api":
            response = session.get(url + "/admin/v2/clusters",
                                   headers={"Authorization": "Bearer " + password},
                                   timeout=15, allow_redirects=False)
            if response.status_code in {401, 403}:
                return False, True
            if response.status_code != 200:
                return False, False
            clusters = response.json()
            return (isinstance(clusters, list) and bool(clusters)
                    and all(isinstance(cluster, str) and bool(cluster.strip()) for cluster in clusters)), False
        if route == "infisical":
            return _infisical_attempt(session, url, username, password)
        if route == "pulsar-manager":
            return _pulsar_attempt(session, url, username, password)
        if route == "portainer":
            login = session.post(url + "/api/auth", json={"Username": username, "Password": password},
                                 timeout=15, allow_redirects=False)
            if login.status_code in {401, 403}:
                return False, True
            if login.status_code == 422:
                error = login.json()
                return False, isinstance(error, dict) and error.get("message") == "Invalid credentials"
            if login.status_code != 200:
                return False, False
            body = login.json()
            token = body.get("jwt") if isinstance(body, dict) else None
            if not isinstance(token, str) or not token:
                return False, False
            response = session.get(url + "/api/users/me", headers={"Authorization": "Bearer " + token},
                                   timeout=15, allow_redirects=False)
        else:
            paths = {"jenkins": "/whoAmI/api/json", "nexus": "/service/rest/v1/security/users",
                     "sonarqube": "/api/users/current"}
            response = session.get(url + paths[route], auth=(username, password),
                                   timeout=15, allow_redirects=False)
        if response.status_code in {401, 403}:
            # A minted Portainer token means login accepted the credentials,
            # even if its later identity endpoint refuses access.
            return False, route != "portainer"
        if response.status_code != 200:
            return False, False
        body = response.json()
        if route == "nexus":
            return (isinstance(body, list) and any(isinstance(user, dict) and user.get("userId") == username
                    for user in body)), False
        if not isinstance(body, dict):
            return False, False
        if route == "jenkins":
            return body.get("authenticated") is True and body.get("name") == username, False
        if route == "sonarqube":
            return body.get("isLoggedIn") is True and body.get("login") == username, False
        key = "Username" if route == "portainer" else "login"
        return body.get(key) == username, False


def _infisical_attempt(session: requests.Session, url: str, username: str,
                       password: str) -> tuple[bool, bool]:
    # Reuse the existing live suite's login/organization contract, without
    # environment-coupled credentials, automatic retries, or organization writes.
    response = session.post(url + "/api/v3/auth/login",
                            json={"email": username, "password": password},
                            timeout=15, allow_redirects=False)
    if response.status_code in {401, 403}:
        return False, True
    if response.status_code == 400:
        error = response.json()
        return False, isinstance(error, dict) and error.get("message") == "Invalid username or email"
    if response.status_code != 200:
        return False, False
    body = response.json()
    token = body.get("accessToken") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        return False, False
    organizations = session.get(url + "/api/v1/organization",
                                headers={"Authorization": "Bearer " + token},
                                timeout=15, allow_redirects=False)
    if organizations.status_code != 200:
        # Successful login is never reclassified as invalid credential rejection
        # because the protected operation fails later.
        return False, False
    payload = organizations.json()
    items = payload.get("organizations") if isinstance(payload, dict) else None
    return (isinstance(items, list) and bool(items)
            and all(isinstance(item, dict) and isinstance(item.get("id"), str)
                    and bool(item["id"].strip()) for item in items)), False


def _pulsar_attempt(session: requests.Session, url: str, username: str,
                    password: str) -> tuple[bool, bool]:
    csrf = session.get(url + "/pulsar-manager/csrf-token", timeout=15, allow_redirects=False)
    if csrf.status_code != 200 or not csrf.text.strip():
        return False, False
    token = csrf.text.strip()
    session.cookies.set("XSRF-TOKEN", token)
    headers = {"X-XSRF-TOKEN": token}
    response = session.post(url + "/pulsar-manager/login", headers=headers,
                            json={"username": username, "password": password},
                            timeout=15, allow_redirects=False)
    if response.status_code in {401, 403}:
        return False, True
    if response.status_code != 200:
        return False, False
    body = response.json()
    if not isinstance(body, dict):
        return False, False
    if body.get("login") != "success":
        return False, body.get("error") in {
            "The user is not exist", "The user name or password not incorrect",
        }
    # Pulsar Manager 0.4 returns the authenticated principal and session token
    # in headers. Exercise its protected read API, not a landing-page marker.
    access_token = response.headers.get("token")
    if response.headers.get("username") != username or not access_token:
        return False, False
    headers.update({"token": access_token, "username": username})
    environments = session.get(url + "/pulsar-manager/environments", headers=headers,
                               timeout=15, allow_redirects=False)
    if environments.status_code != 200:
        return False, False
    data = environments.json()
    return (isinstance(data, dict) and isinstance(data.get("data"), list)
            and type(data.get("total")) is int and data["total"] >= 0
            and "error" not in data), False
