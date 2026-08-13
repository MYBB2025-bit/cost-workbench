"""系统管理 API 测试：用户/角色/权限/灰度发布 CRUD 与绑定。"""

API = "/api/v1"


def _login(client, username, password):
    r = client.post(f"{API}/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_system_admin_flow(client):
    admin = _login(client, "admin", "admin123")
    h = {"Authorization": f"Bearer {admin}"}

    # 1) 创建权限
    r = client.post(f"{API}/system/permissions", json={
        "perm_code": "test:resource:action",
        "perm_name": "测试权限",
        "resource": "test",
        "action": "action",
    }, headers=h)
    assert r.status_code == 200, r.text
    perm_id = r.json()["id"]

    # 2) 创建角色并绑定权限
    r = client.post(f"{API}/system/roles", json={
        "role_code": "test_role",
        "role_name": "测试角色",
        "perm_ids": [perm_id],
    }, headers=h)
    assert r.status_code == 200, r.text
    role_id = r.json()["id"]

    r = client.get(f"{API}/system/roles", headers=h)
    role = next(x for x in r.json() if x["id"] == role_id)
    assert any(p["perm_code"] == "test:resource:action" for p in role["perms"])

    # 3) 创建用户并绑定角色
    r = client.post(f"{API}/system/users", json={
        "username": "tester",
        "real_name": "测试员",
        "password": "test123",
        "role_ids": [role_id],
    }, headers=h)
    assert r.status_code == 200, r.text
    user_id = r.json()["id"]

    r = client.get(f"{API}/system/users", headers=h)
    user = next(x for x in r.json() if x["id"] == user_id)
    assert any(r["role_code"] == "test_role" for r in user["roles"])

    # 4) 编辑用户状态
    r = client.put(f"{API}/system/users/{user_id}", json={"status": 0}, headers=h)
    assert r.status_code == 200, r.text

    # 5) 灰度发布 CRUD
    r = client.post(f"{API}/system/gray-releases", json={
        "version_code": "v9.9.9",
        "enable": 1,
        "user_filter": {"user_ids": [user_id]},
    }, headers=h)
    assert r.status_code == 200, r.text
    gray_id = r.json()["id"]

    r = client.get(f"{API}/system/gray-releases", headers=h)
    assert any(g["version_code"] == "v9.9.9" for g in r.json())

    r = client.put(f"{API}/system/gray-releases/{gray_id}", json={"enable": 0}, headers=h)
    assert r.status_code == 200, r.text

    # 6) 删除
    r = client.delete(f"{API}/system/gray-releases/{gray_id}", headers=h)
    assert r.status_code == 200, r.text
    r = client.delete(f"{API}/system/users/{user_id}", headers=h)
    assert r.status_code == 200, r.text
    r = client.delete(f"{API}/system/roles/{role_id}", headers=h)
    assert r.status_code == 200, r.text
    r = client.delete(f"{API}/system/permissions/{perm_id}", headers=h)
    assert r.status_code == 200, r.text
