"""变更签证接口测试。"""
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
        json={"project_name": "变更测试项目", "project_code": "CHANGE-01"},
    )
    assert r.status_code == 200
    return r.json()


def test_change_order_and_visa(client: TestClient, token: str, project: dict):
    pid = project["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # create change order
    r = client.post(
        "/api/v1/change/create",
        headers=headers,
        json={
            "project_id": pid,
            "change_no": "BG-001",
            "change_name": "设计变更一",
            "change_type": "设计变更",
            "amount": 5000,
        },
    )
    assert r.status_code == 200
    change_id = r.json()["id"]

    # create change item
    r = client.post(
        f"/api/v1/change/{change_id}/items",
        headers=headers,
        json={
            "name": "钢筋增量",
            "unit": "t",
            "before_qty": 10,
            "after_qty": 12,
            "unit_price": 4000,
        },
    )
    assert r.status_code == 200
    item = r.json()
    assert item["delta_qty"] == 2
    assert item["amount"] == 8000

    # detail with items
    r = client.get(f"/api/v1/change/{change_id}", headers=headers)
    assert r.status_code == 200
    detail = r.json()
    assert detail["change_no"] == "BG-001"
    assert len(detail["items"]) == 1

    # visa create
    r = client.post(
        "/api/v1/change/visa/create",
        headers=headers,
        json={
            "project_id": pid,
            "visa_no": "QZ-001",
            "visa_date": "2026-08-01",
            "content": "现场零星挖土",
            "amount": 1200,
        },
    )
    assert r.status_code == 200
    visa_id = r.json()["id"]

    r = client.get(f"/api/v1/change/visa/list?project_id={pid}", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # delete
    r = client.delete(f"/api/v1/change/visa/{visa_id}", headers=headers)
    assert r.status_code == 200
    r = client.delete(f"/api/v1/change/{change_id}", headers=headers)
    assert r.status_code == 200
