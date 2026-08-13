"""预算清单接口测试。"""
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
        json={"project_name": "预算测试项目", "project_code": "BUDGET-01"},
    )
    assert r.status_code == 200
    return r.json()


def test_budget_crud(client: TestClient, token: str, project: dict):
    pid = project["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # create
    r = client.post(
        "/api/v1/budget/create",
        headers=headers,
        json={
            "project_id": pid,
            "item_no": "001",
            "name": "土方开挖",
            "unit": "m3",
            "qty": 100,
            "unit_price": 50,
            "category": "分部分项",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_price"] == 5000
    item_id = data["id"]

    # list
    r = client.get(f"/api/v1/budget/list?project_id={pid}", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # tree
    r = client.get(f"/api/v1/budget/tree?project_id={pid}", headers=headers)
    assert r.status_code == 200
    tree = r.json()
    assert len(tree) == 1
    assert tree[0]["total_price"] == 5000

    # update
    r = client.put(
        f"/api/v1/budget/{item_id}",
        headers=headers,
        json={"qty": 200},
    )
    assert r.status_code == 200
    assert r.json()["total_price"] == 10000

    # delete
    r = client.delete(f"/api/v1/budget/{item_id}", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/budget/list?project_id={pid}", headers=headers)
    assert len(r.json()) == 0
