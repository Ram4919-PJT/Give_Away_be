"""End-to-end API test for item donation workflow."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = "Test@1234"

USERS = {
    "donor": "ananya.donor@gmail.com",
    "admin": "admin@giveaway.org",
    "receiver": "ramesh.receiver@gmail.com",
}


def login(client: httpx.Client, email: str) -> str:
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    steps: list[str] = []
    with httpx.Client(timeout=60.0) as client:
        donor_token = login(client, USERS["donor"])
        admin_token = login(client, USERS["admin"])
        receiver_token = login(client, USERS["receiver"])
        steps.append("login ok")

        # Donor verification status
        r = client.get(f"{BASE}/core/donors/me/item-donations/verification-status", headers=auth_headers(donor_token))
        r.raise_for_status()
        assert r.json().get("verified") is True, "Donor must be verified for test"
        steps.append("donor verified")

        # Categories
        r = client.get(f"{BASE}/core/item-categories", headers=auth_headers(donor_token))
        r.raise_for_status()
        categories = r.json()
        cat_id = categories[0]["category_id"] if categories else 1

        # Create draft
        payload = {
            "item_name": "E2E Test Blankets",
            "category_id": cat_id,
            "description": "Warm blankets for testing workflow",
            "quantity": 5,
            "condition": "GOOD",
            "pickup_line1": "123 Test St",
            "pickup_city": "Mumbai",
            "pickup_state": "Maharashtra",
            "pickup_pincode": "400001",
            "display_city": "Mumbai",
            "display_state": "Maharashtra",
        }
        r = client.post(f"{BASE}/core/donors/me/item-donations", json=payload, headers=auth_headers(donor_token))
        r.raise_for_status()
        item = r.json()
        item_id = item["item_donation_id"]
        steps.append(f"created item {item_id}")

        # Submit (needs at least one photo in real flow - check if required)
        r = client.post(f"{BASE}/core/donors/me/item-donations/{item_id}/submit", headers=auth_headers(donor_token))
        if r.status_code >= 400:
            # upload minimal placeholder if photo required
            img = Path(__file__).resolve().parent.parent / "uploads"
            img.mkdir(exist_ok=True)
            test_file = img / "e2e_test.png"
            if not test_file.exists():
                test_file.write_bytes(
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
                )
            with test_file.open("rb") as f:
                r = client.post(
                    f"{BASE}/core/donors/me/item-donations/{item_id}/documents",
                    headers=auth_headers(donor_token),
                    files={"file": ("e2e_test.png", f, "image/png")},
                    data={"document_type": "ITEM_PHOTO"},
                )
                r.raise_for_status()
            r = client.post(f"{BASE}/core/donors/me/item-donations/{item_id}/submit", headers=auth_headers(donor_token))
        r.raise_for_status()
        assert r.json()["status"] in ("PENDING_VERIFICATION", "SUBMITTED")
        steps.append("submitted for verification")

        # Admin queue
        r = client.get(f"{BASE}/core/admin/item-donations/queue", headers=auth_headers(admin_token))
        r.raise_for_status()
        queue = r.json()
        assert any(i["item_donation_id"] == item_id for i in queue), "Item not in admin queue"
        steps.append("admin queue")

        # Approve
        r = client.post(
            f"{BASE}/core/admin/item-donations/{item_id}/review",
            json={"action": "approve", "comment": "E2E approved"},
            headers=auth_headers(admin_token),
        )
        r.raise_for_status()
        assert r.json()["status"] in ("APPROVED", "AVAILABLE")
        steps.append("approved")

        # Catalog
        r = client.get(f"{BASE}/core/catalog/items", headers=auth_headers(receiver_token))
        r.raise_for_status()
        catalog = r.json()
        items = catalog.get("items", catalog) if isinstance(catalog, dict) else catalog
        assert any(i.get("item_donation_id") == item_id for i in items), "Not in catalog"
        steps.append("catalog visible")

        # Request
        r = client.post(
            f"{BASE}/core/receivers/me/item-requests?item_donation_id={item_id}",
            json={"quantity_requested": 2, "message": "Need for family", "preferred_fulfillment": "PICKUP"},
            headers=auth_headers(receiver_token),
        )
        r.raise_for_status()
        req_id = r.json()["request_id"]
        steps.append(f"request {req_id}")

        # Donor accept
        r = client.post(
            f"{BASE}/core/donors/me/item-requests/{req_id}/respond",
            json={"action": "accept"},
            headers=auth_headers(donor_token),
        )
        r.raise_for_status()
        assert r.json()["status"] == "ACCEPTED"
        steps.append("accepted")

        # Complete
        r = client.post(f"{BASE}/core/donors/me/item-requests/{req_id}/complete", headers=auth_headers(donor_token))
        r.raise_for_status()
        assert r.json()["status"] == "COMPLETED"
        steps.append("completed")

    print("PASS:", " -> ".join(steps))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("FAIL:", e, file=sys.stderr)
        raise SystemExit(1)
