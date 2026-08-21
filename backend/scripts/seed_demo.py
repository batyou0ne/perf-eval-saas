"""Seeds the "Meridyen Yazilim" demo company over the real HTTP API.

Requires a running instance with the base dev seed already applied
(``docker compose exec backend python -m app.scripts.seed_dev_user``), since this script
logs in as the super admin that script creates rather than touching the database directly.

Usage:
    python backend/scripts/seed_demo.py [--base-url http://localhost:8001]
"""

import argparse
import sys

import httpx

SUPER_ADMIN_EMAIL = "superadmin@platform.io"
SUPER_ADMIN_PASSWORD = "devpassword123"

COMPANY_NAME = "Meridyen Yazilim"
DEMO_PASSWORD = "meridyen2026"

# (full_name, email, role, reports_to_email)
USERS = [
    ("Selin Aydin", "selin@meridyen.io", "company_admin", None),
    ("Burak Demir", "burak@meridyen.io", "hr", None),
    ("Elif Kaya", "elif@meridyen.io", "manager", "selin@meridyen.io"),
    ("Zeynep Arslan", "zeynep@meridyen.io", "manager", "selin@meridyen.io"),
    ("Deniz Yilmaz", "deniz@meridyen.io", "employee", "elif@meridyen.io"),
    ("Kerem Sahin", "kerem@meridyen.io", "employee", "elif@meridyen.io"),
    ("Mert Koc", "mert@meridyen.io", "employee", "zeynep@meridyen.io"),
]


def login(client: httpx.Client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def invite_and_accept(
    client: httpx.Client, inviter_token: str, *, email: str, role: str, full_name: str, company_id: str | None = None
) -> dict:
    body = {"email": email, "role": role}
    if company_id is not None:
        body["company_id"] = company_id

    resp = client.post("/api/v1/invites", json=body, headers=auth_headers(inviter_token))
    if resp.status_code == 400 and "already exists" in resp.text:
        print(f"  already exists, skipping invite: {email}")
        return {}
    resp.raise_for_status()
    invite = resp.json()

    token = invite["invite_link"].rsplit("/", 1)[-1]
    accept = client.post(
        f"/api/v1/invites/{token}/accept", json={"full_name": full_name, "password": DEMO_PASSWORD}
    )
    accept.raise_for_status()
    print(f"  created {role}: {email}")
    return accept.json()


def find_company_by_name(client: httpx.Client, token: str, name: str) -> str | None:
    resp = client.get("/api/v1/companies", params={"page_size": 100}, headers=auth_headers(token))
    resp.raise_for_status()
    for company in resp.json()["items"]:
        if company["name"] == name:
            return company["id"]
    return None


def get_user_id(client: httpx.Client, token: str, email: str) -> str | None:
    resp = client.get("/api/v1/users", params={"page_size": 100}, headers=auth_headers(token))
    resp.raise_for_status()
    for user in resp.json()["items"]:
        if user["email"] == email:
            return user["id"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        super_admin_token = login(client, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)

        company_id = find_company_by_name(client, super_admin_token, COMPANY_NAME)
        if company_id is None:
            resp = client.post(
                "/api/v1/companies", json={"name": COMPANY_NAME}, headers=auth_headers(super_admin_token)
            )
            resp.raise_for_status()
            company_id = resp.json()["id"]
            print(f"Created company {COMPANY_NAME} ({company_id})")
        else:
            print(f"Company {COMPANY_NAME} already exists ({company_id})")

        print("Inviting Selin Aydin (company admin)...")
        invite_and_accept(
            client,
            super_admin_token,
            email="selin@meridyen.io",
            role="company_admin",
            full_name="Selin Aydin",
            company_id=company_id,
        )

        admin_token = login(client, "selin@meridyen.io", DEMO_PASSWORD)

        print("Inviting the rest of the cast...")
        for full_name, email, role, _ in USERS[1:]:
            invite_and_accept(client, admin_token, email=email, role=role, full_name=full_name)

        print("Wiring up reporting lines...")
        for full_name, email, _, manager_email in USERS:
            if manager_email is None:
                continue
            user_id = get_user_id(client, admin_token, email)
            manager_id = get_user_id(client, admin_token, manager_email)
            if user_id is None or manager_id is None:
                print(f"  skipping {email}: could not resolve user or manager id")
                continue
            resp = client.post(
                f"/api/v1/users/{user_id}/manager",
                json={"manager_id": manager_id},
                headers=auth_headers(admin_token),
            )
            resp.raise_for_status()
            print(f"  {email} -> reports to {manager_email}")

    print("\nDone. Every seeded Meridyen user logs in with password: " + DEMO_PASSWORD)


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as exc:
        print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        sys.exit(1)
