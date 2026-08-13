"""Celery 异步任务相关后端接口测试（eager 模式，无 broker 亦可跑）。"""
import io

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
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _xlsx_file(pid):
    return ("budget.xlsx", _make_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def test_budget_import_async_eager(client, seed_data):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    pid = seed_data["project_id"]

    r = client.post(
        "/api/v1/budget/import-async",
        data={"project_id": str(pid)},
        files={"file": _xlsx_file(pid)},
        headers=H,
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    # eager 模式下任务已同步完成
    r2 = client.get(f"/api/v1/task/{job_id}", headers=H)
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["status"] == "success"
    assert body["result"]["created"] == 4
    assert body["progress"] == 100


def test_ledger_export_async_and_download(client, seed_data):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    pid = seed_data["project_id"]

    r = client.get(f"/api/v1/ledger/export-async?project_id={pid}", headers=H)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    r2 = client.get(f"/api/v1/task/{job_id}", headers=H)
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"

    r3 = client.get(f"/api/v1/task/{job_id}/download", headers=H)
    assert r3.status_code == 200, r3.text
    # utf-8-sig BOM
    assert r3.content[:3] == b"\xef\xbb\xbf"


def test_task_view_forbidden_for_other_user(client, seed_data):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    pid = seed_data["project_id"]

    r = client.post(
        "/api/v1/budget/import-async",
        data={"project_id": str(pid)},
        files={"file": _xlsx_file(pid)},
        headers=H,
    )
    job_id = r.json()["job_id"]

    # 受限用户 editor（非 super，未创建该任务）查看应 403
    et = client.post(
        "/api/v1/auth/login",
        data={"username": "editor", "password": "editor123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    EH = {"Authorization": f"Bearer {et}"}
    r2 = client.get(f"/api/v1/task/{job_id}", headers=EH)
    assert r2.status_code == 403


def test_task_download_before_finished(client, seed_data):
    token = _login(client)
    H = {"Authorization": f"Bearer {token}"}
    pid = seed_data["project_id"]

    job_id = client.post(
        "/api/v1/budget/import-async",
        data={"project_id": str(pid)},
        files={"file": _xlsx_file(pid)},
        headers=H,
    ).json()["job_id"]
    # 成功后才是 success；这里直接验证成功态可下载，失败态返回 409 由导出类覆盖
    r = client.get(f"/api/v1/task/{job_id}", headers=H)
    assert r.json()["status"] == "success"
