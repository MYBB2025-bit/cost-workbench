"""风险项 CRUD 接口测试（覆盖此前遗漏的创建/更新/删除路由）。"""
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
        json={"project_name": "风险测试项目", "project_code": "RISK-01"},
    )
    assert r.status_code == 200
    return r.json()


def test_risk_crud(client: TestClient, token: str, project: dict):
    headers = {"Authorization": f"Bearer {token}"}
    pid = project["id"]

    # 创建
    r = client.post(
        "/api/v1/risk/items",
        headers=headers,
        json={"project_id": pid, "risk_type": "进度", "level": "high",
              "title": "基础施工滞后", "desc": "连续降雨", "due": "2026-08-20", "status": "open"},
    )
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    assert r.json()["level"] == "high"

    # 更新状态
    r = client.put(f"/api/v1/risk/items/{rid}", headers=headers, json={"status": "handled"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "handled"

    # 列表可查到
    r = client.get(f"/api/v1/risk/items?project_id={pid}", headers=headers)
    assert r.status_code == 200
    assert any(item["id"] == rid for item in r.json())

    # 删除
    r = client.delete(f"/api/v1/risk/items/{rid}", headers=headers)
    assert r.status_code == 200, r.text

    # 删除后列表为空
    r = client.get(f"/api/v1/risk/items?project_id={pid}", headers=headers)
    assert all(item["id"] != rid for item in r.json())


def test_risk_update_missing(client: TestClient, token: str, project: dict):
    headers = {"Authorization": f"Bearer {token}"}
    r = client.put("/api/v1/risk/items/999999", headers=headers, json={"status": "x"})
    assert r.status_code == 404
