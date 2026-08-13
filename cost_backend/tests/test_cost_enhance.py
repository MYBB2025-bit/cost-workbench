"""造价前端增强相关后端接口测试：预算导入 / 台账导出 / 统计总览。"""
from io import BytesIO

from openpyxl import Workbook


def _login(client, username="admin", password="admin123"):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return r.json()["access_token"]


def _make_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.append(["编号", "名称", "规格", "单位", "工程量", "单价", "分类", "父级编号"])
    ws.append(["A", "土建工程", "", "", "", "", "分部分项", ""])
    ws.append(["A-1", "混凝土C30", "C30", "m3", 100, 500, "混凝土", "A"])
    ws.append(["A-2", "钢筋", "HRB400", "t", 10, 4000, "钢材", "A"])
    ws.append(["B", "安装工程", "", "", "", "", "分部分项", ""])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_budget_import_and_stats(client, seed_data):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    pid = seed_data["project_id"]

    # 导入预算
    xlsx = _make_xlsx()
    r = client.post(
        "/api/v1/budget/import",
        data={"project_id": str(pid)},
        files={"file": ("budget.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=H,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] == 4
    assert body["skipped"] == 0

    # 统计总览
    r2 = client.get(f"/api/v1/stats/cost-overview?project_id={pid}", headers=H)
    assert r2.status_code == 200, r2.text
    ov = r2.json()
    # 混凝土 100*500 + 钢筋 10*4000 = 50000 + 40000 = 90000
    assert abs(ov["budget_total"] - 90000) < 1e-6
    assert ov["budget_count"] == 4
    assert len(ov["by_project"]) >= 1
    assert len(ov["by_category"]) >= 2


def test_ledger_export(client, seed_data):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    pid = seed_data["project_id"]

    r = client.get(f"/api/v1/ledger/export?project_id={pid}", headers=H)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    # 带 BOM 头
    assert r.content[:3] == b"\xef\xbb\xbf"


def test_stats_overview_empty_forbidden(client):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    # 无数据权限的项目（用一个不存在的 id）
    r = client.get("/api/v1/stats/cost-overview?project_id=99999", headers=H)
    assert r.status_code == 403
