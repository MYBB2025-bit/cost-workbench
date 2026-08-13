"""API 冒烟测试：认证、数据权限、客户端更新全链路。"""
import io

API = "/api/v1"


def _login(client, username, password):
    r = client.post(f"{API}/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_me(client):
    token = _login(client, "admin", "admin123")
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert "*" in body["perms"]  # 超级管理员


def test_data_permission_isolation(client, seed_data):
    """受限用户仅可见授权项目；admin 可见全部。"""
    token = _login(client, "editor", "editor123")
    r = client.get(f"{API}/project/list", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    names = [p["project_name"] for p in r.json()]
    assert "示范项目A" in names
    assert len(names) == 1


def test_project_crud_admin(client):
    token = _login(client, "admin", "admin123")
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(f"{API}/project/create", json={"project_name": "新工程", "project_code": "P-X", "contract_amount": 500000}, headers=h)
    assert r.status_code == 200
    pid = r.json()["id"]
    r = client.get(f"{API}/project/list", headers=h)
    assert any(p["id"] == pid for p in r.json())


def test_client_version_flow(client, seed_data):
    admin = _login(client, "admin", "admin123")
    ha = {"Authorization": f"Bearer {admin}"}
    editor = _login(client, "editor", "editor123")
    he = {"Authorization": f"Bearer {editor}"}

    # 1) 无版本时检测不更新
    r = client.get(f"{API}/client/version/check?local_ver=v1.0.0", headers=he)
    assert r.status_code == 200 and r.json()["update"] is False

    # 2) 发布新版本
    r = client.post(f"{API}/client/version/publish", json={"version_code": "v2.0.0", "version_desc": "测试版"}, headers=ha)
    assert r.status_code == 200

    # 3) 再次检测（editor 本地 v1.0.0）→ 需要更新，无补丁
    r = client.get(f"{API}/client/version/check?local_ver=v1.0.0", headers=he)
    body = r.json()
    assert body["update"] is True
    assert body["latest_version"] == "v2.0.0"
    assert body["patch"] is None

    # 4) 上传补丁（v1.0.0 -> v2.0.0）
    content = b"\x00bsdiff-binary-content\x01\x02\x03"
    files = {"file": ("patch.bsdiff", io.BytesIO(content), "application/octet-stream")}
    r = client.post(f"{API}/client/patch/upload?from_version=v1.0.0&to_version=v2.0.0",
                    files=files, headers=ha)
    assert r.status_code == 200, r.text
    patch_id = r.json()["id"]

    # 5) 检测应包含补丁
    r = client.get(f"{API}/client/version/check?local_ver=v1.0.0", headers=he)
    assert r.json()["patch"]["patch_id"] == patch_id

    # 6) 下载补丁内容一致
    r = client.get(f"{API}/client/patch/download/{patch_id}")
    assert r.status_code == 200
    assert r.content == content


def test_payment_stats_api(client, seed_data):
    admin = _login(client, "admin", "admin123")
    h = {"Authorization": f"Bearer {admin}"}
    pid = seed_data["project_id"]
    # 建 WBS 节点：父(100) + 两子(30,20)
    for body in [
        {"project_id": pid, "name": "总包", "estimate": 100, "parent_id": None},
        {"project_id": pid, "name": "子A", "estimate": 30, "parent_id": 1},
        {"project_id": pid, "name": "子B", "estimate": 20, "parent_id": 1},
    ]:
        r = client.post(f"{API}/progress/payment-node", json=body, headers=h)
        assert r.status_code == 200
    # 父节点 id 需已知：第一条 upsert 返回 id=1（自增从1）
    r = client.get(f"{API}/progress/payment-stats/{pid}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_estimate"] == 150  # 100+30+20（修复后）
