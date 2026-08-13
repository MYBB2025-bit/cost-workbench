"""造价平台端到端功能冒烟测试（标准库实现，不依赖第三方包）。

通过真实 HTTP 请求走通核心业务链路，输出 PASS/FAIL 报告。
用法：python functional_smoke.py [BASE_URL]
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse, urlencode

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TOKEN = None
PASS = []
FAIL = []


def parse_url(u):
    p = urlparse(u)
    return p.scheme == "https", p.hostname, p.port or (443 if p.scheme == "https" else 80)


def req(method, path, *, json_body=None, form=None, params=None, files=None, token=None, raw=False, timeout=30):
    ssl, host, port = parse_url(BASE)
    url_path = path if path.startswith("/") else "/" + path
    if params:
        url_path += ("?" + urlencode(params))
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")
    elif files is not None:
        boundary = "------funcsmokeboundary"
        parts = []
        if form:
            for k, v in form.items():
                parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{str(v)}\r\n".encode())
        for name, (fname, fdata, ftype) in files.items():
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{fname}\"\r\n"
                f"Content-Type: {ftype}\r\n\r\n".encode() + fdata + b"\r\n"
            )
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif form is not None and method != "GET":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form).encode()

    conn = HTTPSConnection(host, port) if ssl else HTTPConnection(host, port)
    try:
        conn.request(method, url_path, body=data, headers=headers)
        resp = conn.getresponse()
        body = resp.read()
        status = resp.status
    finally:
        conn.close()
    text = body.decode("utf-8", "replace")
    if raw:
        return status, text
    try:
        j = json.loads(text) if text else None
    except Exception:
        j = text
    return status, j


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"  [PASS] {name}")
    else:
        FAIL.append(name)
        print(f"  [FAIL] {name}  {detail}")


def login():
    global TOKEN
    status, j = req("POST", "/api/v1/auth/login", form={"username": "admin", "password": "admin123"})
    if status == 200 and isinstance(j, dict) and j.get("access_token"):
        TOKEN = j["access_token"]
        return True
    print("  login resp:", status, j)
    return False


def make_xlsx(path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "预算"
    ws.append(["编号", "名称", "规格", "单位", "工程量", "单价", "分类", "父级编号"])
    ws.append(["A1", "土方开挖", "三类土", "m3", 1000, 35.5, "土石方", ""])
    ws.append(["A1-1", "机械挖土", "", "m3", 800, 28.0, "土石方", "A1"])
    ws.append(["B1", "钢筋工程", "HRB400", "t", 50, 4200, "主体", ""])
    wb.save(path)


def poll_task(job_id, tries=30):
    for _ in range(tries):
        status, j = req("GET", f"/api/v1/task/{job_id}", token=TOKEN)
        if status == 200 and isinstance(j, dict):
            st = j.get("status")
            if st in ("success", "failed"):
                return st, j
        time.sleep(0.3)
    return "timeout", None


def main():
    print(f"=== 造价平台功能冒烟测试 @ {BASE} ===\n")

    # 1. 健康 & 鉴权
    print("[1] 系统健康 & 鉴权")
    s, j = req("GET", "/health")
    check("GET /health == 200", s == 200, f"status={s}")
    check("登录 admin/admin123", login())
    s, j = req("GET", "/api/v1/auth/me", token=TOKEN)
    check("GET /auth/me 含超级权限 *", s == 200 and isinstance(j, dict) and "*" in (j.get("perms") or []), f"{s} {j}")
    s, j = req("GET", "/api/v1/auth/menu", token=TOKEN)
    menus = (j.get("menus") if isinstance(j, dict) else (j if isinstance(j, list) else [])) or []
    check(f"GET /auth/menu 返回 {len(menus)} 个菜单(>=14)", s == 200 and len(menus) >= 14, f"{s} count={len(menus)}")

    # 2. 项目（每次用唯一编码，避免与历史脏数据唯一约束冲突）
    print("\n[2] 项目管理")
    ts = int(time.time())
    s, j = req("POST", "/api/v1/project/create", json_body={"project_name": f"测试项目-滨江大厦-{ts}", "project_code": f"PJ-{ts}", "contract_amount": 12500000}, token=TOKEN)
    check("POST /project/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    pid = (j or {}).get("id")
    s, j = req("GET", "/api/v1/project/list", token=TOKEN)
    check("GET /project/list 返回数组(>=1)", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s} {type(j).__name__}")

    # 3. 预算清单
    print("\n[3] 预算清单")
    s, j = req("POST", "/api/v1/budget/create", json_body={"project_id": pid, "item_no": "A1", "name": "土方开挖", "unit": "m3", "qty": 1000, "unit_price": 35.5, "category": "土石方"}, token=TOKEN)
    check("POST /budget/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("GET", "/api/v1/budget/list", token=TOKEN, params={"project_id": pid})
    check("GET /budget/list 返回数组(>=1)", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s} {type(j).__name__}")
    s, j = req("GET", "/api/v1/budget/tree", token=TOKEN, params={"project_id": pid})
    check("GET /budget/tree 返回数组", s == 200 and isinstance(j, list), f"{s} {j}")

    # 4. 结算
    print("\n[4] 结算管理")
    s, j = req("POST", "/api/v1/settlement/create", json_body={"project_id": pid, "settlement_name": "一期中间结算", "total_amount": 3200000, "settlement_type": "midterm"}, token=TOKEN)
    check("POST /settlement/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    sid = (j or {}).get("id")
    if sid:
        s, j = req("POST", f"/api/v1/settlement/{sid}/items", json_body={"settlement_id": sid, "name": "土方开挖结算", "settle_qty": 1000, "unit_price": 35.5, "amount": 35500}, token=TOKEN)
        check("POST /settlement/{id}/items", s == 200, f"{s} {j}")
    s, j = req("GET", "/api/v1/settlement/list", token=TOKEN, params={"project_id": pid})
    check("GET /settlement/list", s == 200, f"{s}")

    # 5. 变更签证
    print("\n[5] 变更与签证")
    s, j = req("POST", "/api/v1/change/create", json_body={"project_id": pid, "change_name": "设计变更-基础加深", "amount": 150000}, token=TOKEN)
    check("POST /change/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("POST", "/api/v1/change/visa/create", json_body={"project_id": pid, "visa_no": "V-001", "content": "现场签证-零星用工", "amount": 80000}, token=TOKEN)
    check("POST /change/visa/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("GET", "/api/v1/change/visa/list", token=TOKEN, params={"project_id": pid})
    check("GET /change/visa/list", s == 200, f"{s}")

    # 6. 进度款
    print("\n[6] 进度款与支付节点")
    s, j = req("POST", "/api/v1/progress/create", json_body={"project_id": pid, "period_name": "第1期", "apply_amount": 3000000, "audit_amount": 2850000}, token=TOKEN)
    check("POST /progress/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("POST", "/api/v1/progress/payment-node", json_body={"project_id": pid, "name": "基础节点", "estimate": 3000000, "applied": 3000000, "audited": 2850000}, token=TOKEN)
    check("POST /progress/payment-node", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("GET", f"/api/v1/progress/payment-nodes/{pid}", token=TOKEN)
    check("GET /progress/payment-nodes/{pid}", s == 200, f"{s}")
    s, j = req("GET", f"/api/v1/progress/payment-stats/{pid}", token=TOKEN)
    check("GET /progress/payment-stats/{pid}", s == 200, f"{s} {j}")

    # 7. 核价库
    print("\n[7] 核价库")
    s, j = req("POST", "/api/v1/pricing/create", json_body={"project_id": pid, "name": "HRB400钢筋", "spec": "Φ25", "unit": "t", "category": "钢材", "price": 4200, "qty": 50}, token=TOKEN)
    check("POST /pricing/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("GET", "/api/v1/pricing/list", token=TOKEN, params={"project_id": pid})
    check("GET /pricing/list", s == 200, f"{s}")

    # 8. 风险预警
    print("\n[8] 风险与预警（补创建接口）")
    s, j = req("POST", "/api/v1/risk/items", json_body={"project_id": pid, "risk_type": "进度", "level": "high", "title": "基础施工滞后", "desc": "连续降雨导致滞后3天", "due": "2026-08-20", "status": "open"}, token=TOKEN)
    check("POST /risk/items 创建成功", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    rid = (j or {}).get("id")
    if rid:
        s, j = req("PUT", f"/api/v1/risk/items/{rid}", json_body={"status": "handled"}, token=TOKEN)
        check("PUT /risk/items/{id} 更新状态", s == 200 and isinstance(j, dict) and j.get("status") == "handled", f"{s} {j}")
    s, j = req("GET", "/api/v1/risk/warnings", token=TOKEN)
    check("GET /risk/warnings", s == 200, f"{s}")
    s, j = req("GET", "/api/v1/risk/items", token=TOKEN, params={"project_id": pid})
    check("GET /risk/items", s == 200 and isinstance(j, list), f"{s}")

    # 9. 台账 / 统计 / 客户端升级
    print("\n[9] 台账 / 统计 / 客户端升级")
    s, j = req("GET", "/api/v1/ledger/list", token=TOKEN, params={"project_id": pid})
    check("GET /ledger/list", s == 200, f"{s}")
    s, j = req("GET", "/api/v1/stats/cost-overview", token=TOKEN)
    check("GET /stats/cost-overview", s == 200 and isinstance(j, dict), f"{s} {j}")
    s, j = req("GET", "/api/v1/client/version/list", token=TOKEN)
    check("GET /client/version/list", s == 200, f"{s}")

    # 10. 数据迁移预览（只读）
    print("\n[10] 183MB 数据迁移预览（只读）")
    s, j = req("GET", "/api/v1/migration/preview", token=TOKEN)
    ok = s == 200 and isinstance(j, dict) and j.get("file_size_bytes")
    check("GET /migration/preview", ok, f"{s} {str(j)[:120]}")
    if ok:
        print(f"        文件大小={j.get('file_size_bytes')} 字节, 结构计数={j.get('counts')}")

    # 11. 异步任务：预算导入 / 台账导出
    print("\n[11] 异步任务：预算导入 / 台账导出")
    xlsx_path = os.path.join(os.environ.get("TEMP", "/tmp"), "test_budget.xlsx")
    make_xlsx(xlsx_path)
    with open(xlsx_path, "rb") as f:
        xdata = f.read()
    s, j = req("POST", "/api/v1/budget/import-async", files={"file": ("test_budget.xlsx", xdata, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, form={"project_id": pid}, token=TOKEN)
    ok = s == 200 and isinstance(j, dict) and j.get("job_id")
    check("POST /budget/import-async 返回 job_id", ok, f"{s} {j}")
    if ok:
        job_id = j["job_id"]
        st, job = poll_task(job_id)
        check(f"预算导入任务完成 status={st}", st == "success", f"{job}")
        s2, j2 = req("GET", "/api/v1/budget/list", token=TOKEN, params={"project_id": pid})
        imported = (j2 if isinstance(j2, list) else []) or []
        check(f"导入后预算清单条目数={len(imported)} (>=3)", len(imported) >= 3, f"count={len(imported)}")

    s, j = req("GET", "/api/v1/ledger/export-async", token=TOKEN, params={"project_id": pid})
    ok = s == 200 and isinstance(j, dict) and j.get("job_id")
    check("GET /ledger/export-async 返回 job_id", ok, f"{s} {j}")
    if ok:
        job_id = j["job_id"]
        st, job = poll_task(job_id)
        check(f"台账导出任务完成 status={st}", st == "success", f"{job}")
        s2, txt = req("GET", f"/api/v1/task/{job_id}/download", token=TOKEN, raw=True)
        check("GET /task/{id}/download 下载到文件", s2 == 200 and isinstance(txt, str) and len(txt) > 0, f"status={s2} len={len(txt) if isinstance(txt,str) else '?'}")

    # 汇总
    print("\n" + "=" * 52)
    print(f"总计: {len(PASS)} 通过, {len(FAIL)} 失败")
    if FAIL:
        print("失败项:")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("全部通过 ✅")


if __name__ == "__main__":
    main()
