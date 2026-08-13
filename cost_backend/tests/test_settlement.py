"""结算接口测试。"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def token(client: TestClient):
    r = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def project(client: TestClient, token: str):
    r = client.post(
        "/api/v1/project/create",
        headers={"Authorization": f"Bearer {token}"},
        json={"project_name": "结算测试项目", "project_code": "SETTLE-01"},
    )
    assert r.status_code == 200
    return r.json()


@pytest.fixture
def budget_item(client: TestClient, token: str, project: dict):
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/v1/budget/create",
        headers=headers,
        json={
            "project_id": project["id"],
            "item_no": "001",
            "name": "混凝土",
            "unit": "m3",
            "qty": 100,
            "unit_price": 500,
        },
    )
    assert r.status_code == 200
    return r.json()


def test_settlement_crud(client: TestClient, token: str, project: dict, budget_item: dict):
    pid = project["id"]
    bid = budget_item["id"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/v1/settlement/create",
        headers=headers,
        json={
            "project_id": pid,
            "settlement_no": "JS-001",
            "settlement_name": "期中结算",
            "settlement_type": "midterm",
            "total_amount": 50000,
        },
    )
    assert r.status_code == 200
    settlement_id = r.json()["id"]

    r = client.post(
        f"/api/v1/settlement/{settlement_id}/items",
        headers=headers,
        json={
            "budget_item_id": bid,
            "name": "混凝土",
            "unit": "m3",
            "settle_qty": 80,
            "unit_price": 500,
        },
    )
    assert r.status_code == 200
    assert r.json()["amount"] == 40000

    r = client.get(f"/api/v1/settlement/{settlement_id}", headers=headers)
    assert r.status_code == 200
    detail = r.json()
    assert detail["settlement_no"] == "JS-001"
    assert len(detail["items"]) == 1

    r = client.delete(f"/api/v1/settlement/{settlement_id}", headers=headers)
    assert r.status_code == 200
