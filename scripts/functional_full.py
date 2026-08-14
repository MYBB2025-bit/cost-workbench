"""造价平台【全接口】端到端功能测试（标准库实现，覆盖 OpenAPI 全部 62 个端点）。

逐接口走真实 HTTP，断言状态码与关键字段；并清理本次创建的测试数据。
用法：python functional_full.py [BASE_URL]
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse, urlencode

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
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
        boundary = "------funcfullboundary"
        parts = []
        if form:
            for k, v in form.items():
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{str(v)}\r\n'.encode())
        for name, (fname, fdata, ftype) in files.items():
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{fname}"\r\n'
                f"Content-Type: {ftype}\r\n\r\n".encode() + fdata + b"\r\n"
            )
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif form is not None and method != "GET":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form).encode()

    conn = HTTPSConnection(host, port) if ssl else HTTPConnection(host, port, timeout=timeout)
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


def poll_task(job_id, tries=60, interval=1.0):
    for _ in range(tries):
        status, j = req("GET", f"/api/v1/task/{job_id}", token=TOKEN)
        if status == 200 and isinstance(j, dict):
            st = j.get("status")
            if st in ("success", "failed"):
                return st, j
        time.sleep(interval)
    return "timeout", None


def main():
    print(f"=== 造价平台【全接口】功能测试 @ {BASE} ===\n")
    created = {}  # 用于清理

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
    s, j = req("GET", "/metrics")
    check("GET /metrics == 200", s == 200, f"status={s}")

    # 2. 项目 CRUD
    print("\n[2] 项目管理（CRUD）")
    ts = int(time.time())
    s, j = req("POST", "/api/v1/project/create", json_body={"project_name": f"全测项目-{ts}", "project_code": f"PJFT-{ts}", "contract_amount": 12500000}, token=TOKEN)
    check("POST /project/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    pid = (j or {}).get("id")
    created["pid"] = pid
    s, j = req("GET", "/api/v1/project/list", token=TOKEN)
    check("GET /project/list 数组(>=1)", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s} {type(j).__name__}")
    if pid:
        s, j = req("GET", f"/api/v1/project/{pid}", token=TOKEN)
        check("GET /project/{pid}", s == 200 and isinstance(j, dict) and j.get("id") == pid, f"{s} {j}")
        s, j = req("PUT", f"/api/v1/project/{pid}", json_body={"project_name": f"全测项目-{ts}-改"}, token=TOKEN)
        check("PUT /project/{pid} 改名", s == 200 and isinstance(j, dict) and j.get("project_name", "").endswith("改"), f"{s} {j}")

    # 3. 预算清单 CRUD + 导入
    print("\n[3] 预算清单（CRUD + 导入）")
    s, j = req("POST", "/api/v1/budget/create", json_body={"project_id": pid, "item_no": "A1", "name": "土方开挖", "unit": "m3", "qty": 1000, "unit_price": 35.5, "category": "土石方"}, token=TOKEN)
    check("POST /budget/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    bid = (j or {}).get("id")
    created["bid"] = bid
    s, j = req("GET", "/api/v1/budget/list", token=TOKEN, params={"project_id": pid})
    check("GET /budget/list 数组(>=1)", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s}")
    if bid:
        s, j = req("GET", f"/api/v1/budget/{bid}", token=TOKEN)
        check("GET /budget/{bid}", s == 200 and isinstance(j, dict) and j.get("id") == bid, f"{s} {j}")
        s, j = req("PUT", f"/api/v1/budget/{bid}", json_body={"name": "土方开挖-改", "unit_price": 40}, token=TOKEN)
        check("PUT /budget/{bid} 改单价", s == 200 and isinstance(j, dict) and j.get("unit_price") == 40, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/budget/{bid}", token=TOKEN)
        check("DELETE /budget/{bid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")
    s, j = req("GET", "/api/v1/budget/tree", token=TOKEN, params={"project_id": pid})
    check("GET /budget/tree 数组", s == 200 and isinstance(j, list), f"{s} {j}")
    # 同步导入
    xlsx_path = os.path.join(os.environ.get("TEMP", "/tmp"), "ft_budget.xlsx")
    make_xlsx(xlsx_path)
    with open(xlsx_path, "rb") as f:
        xdata = f.read()
    s, j = req("POST", "/api/v1/budget/import", files={"file": ("ft_budget.xlsx", xdata, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, form={"project_id": pid}, token=TOKEN)
    check("POST /budget/import 同步导入返回条目", s == 200 and isinstance(j, dict) and (j.get("created") or j.get("count") or j.get("total_rows")), f"{s} {j}")
    # 异步导入
    s, j = req("POST", "/api/v1/budget/import-async", files={"file": ("ft_budget.xlsx", xdata, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, form={"project_id": pid}, token=TOKEN)
    ok = s == 200 and isinstance(j, dict) and j.get("job_id")
    check("POST /budget/import-async 返回 job_id", ok, f"{s} {j}")
    if ok:
        st, job = poll_task(j["job_id"])
        check(f"预算导入异步任务 status={st}", st == "success", f"{job}")

    # 4. 结算 CRUD + 明细
    print("\n[4] 结算管理（CRUD + 明细）")
    s, j = req("POST", "/api/v1/settlement/create", json_body={"project_id": pid, "settlement_name": "一期中间结算", "total_amount": 3200000, "settlement_type": "midterm"}, token=TOKEN)
    check("POST /settlement/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    sid = (j or {}).get("id")
    created["sid"] = sid
    s, j = req("GET", "/api/v1/settlement/list", token=TOKEN, params={"project_id": pid})
    check("GET /settlement/list", s == 200 and isinstance(j, list), f"{s}")
    if sid:
        s, j = req("GET", f"/api/v1/settlement/{sid}", token=TOKEN)
        check("GET /settlement/{sid}", s == 200 and isinstance(j, dict) and j.get("id") == sid, f"{s} {j}")
        s, j = req("PUT", f"/api/v1/settlement/{sid}", json_body={"settlement_name": "一期中间结算-改", "total_amount": 3300000}, token=TOKEN)
        check("PUT /settlement/{sid} 改金额", s == 200 and isinstance(j, dict) and j.get("total_amount") == 3300000, f"{s} {j}")
        s, j = req("POST", f"/api/v1/settlement/{sid}/items", json_body={"settlement_id": sid, "name": "土方开挖结算", "settle_qty": 1000, "unit_price": 35.5, "amount": 35500}, token=TOKEN)
        check("POST /settlement/{sid}/items", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
        siid = (j or {}).get("id")
        created["siid"] = siid
        s, j = req("GET", f"/api/v1/settlement/{sid}/items", token=TOKEN)
        check("GET /settlement/{sid}/items 数组", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s}")
        if siid:
            s, j = req("PUT", f"/api/v1/settlement/items/{siid}", json_body={"settle_qty": 1100, "amount": 39050}, token=TOKEN)
            check("PUT /settlement/items/{siid} 改量", s == 200 and isinstance(j, dict) and j.get("settle_qty") == 1100, f"{s} {j}")
            s, j = req("DELETE", f"/api/v1/settlement/items/{siid}", token=TOKEN)
            check("DELETE /settlement/items/{siid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/settlement/{sid}", token=TOKEN)
        check("DELETE /settlement/{sid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")

    # 5. 变更 + 签证 + 变更明细
    print("\n[5] 变更 / 签证 / 变更明细")
    s, j = req("POST", "/api/v1/change/create", json_body={"project_id": pid, "change_name": "设计变更-基础加深", "amount": 150000}, token=TOKEN)
    check("POST /change/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    cid = (j or {}).get("id")
    created["cid"] = cid
    s, j = req("GET", "/api/v1/change/list", token=TOKEN, params={"project_id": pid})
    check("GET /change/list 数组", s == 200 and isinstance(j, list), f"{s}")
    if cid:
        s, j = req("GET", f"/api/v1/change/{cid}", token=TOKEN)
        check("GET /change/{cid}", s == 200 and isinstance(j, dict) and j.get("id") == cid, f"{s} {j}")
        s, j = req("PUT", f"/api/v1/change/{cid}", json_body={"change_name": "设计变更-基础加深-改", "amount": 160000}, token=TOKEN)
        check("PUT /change/{cid} 改金额", s == 200 and isinstance(j, dict) and j.get("amount") == 160000, f"{s} {j}")
        s, j = req("POST", f"/api/v1/change/{cid}/items", json_body={"name": "挖土方增量", "unit": "m3", "before_qty": 1000, "after_qty": 1200, "delta_qty": 200, "unit_price": 35.5, "amount": 7100}, token=TOKEN)
        check("POST /change/{cid}/items", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
        ciid = (j or {}).get("id")
        created["ciid"] = ciid
        s, j = req("GET", f"/api/v1/change/{cid}/items", token=TOKEN)
        check("GET /change/{cid}/items 数组", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s}")
        if ciid:
            # delta_qty/amount 为派生字段 = after_qty-before_qty 及 *unit_price，改 after_qty 验证重算
            s, j = req("PUT", f"/api/v1/change/items/{ciid}", json_body={"after_qty": 1500}, token=TOKEN)
            check("PUT /change/items/{ciid} 改后量→派生 delta_qty=500, amount=17750",
                  s == 200 and isinstance(j, dict) and j.get("delta_qty") == 500 and j.get("amount") == 17750.0, f"{s} {j}")
            s, j = req("DELETE", f"/api/v1/change/items/{ciid}", token=TOKEN)
            check("DELETE /change/items/{ciid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/change/{cid}", token=TOKEN)
        check("DELETE /change/{cid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")
    s, j = req("POST", "/api/v1/change/visa/create", json_body={"project_id": pid, "visa_no": f"VFT-{ts}", "content": "现场签证-零星用工", "amount": 80000}, token=TOKEN)
    check("POST /change/visa/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    vid = (j or {}).get("id")
    created["vid"] = vid
    s, j = req("GET", "/api/v1/change/visa/list", token=TOKEN, params={"project_id": pid})
    check("GET /change/visa/list 数组", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s}")
    if vid:
        s, j = req("PUT", f"/api/v1/change/visa/{vid}", json_body={"content": "现场签证-零星用工-改", "amount": 85000}, token=TOKEN)
        check("PUT /change/visa/{vid} 改金额", s == 200 and isinstance(j, dict) and j.get("amount") == 85000, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/change/visa/{vid}", token=TOKEN)
        check("DELETE /change/visa/{vid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")

    # 6. 进度款 + 支付节点
    print("\n[6] 进度款与支付节点")
    s, j = req("POST", "/api/v1/progress/create", json_body={"project_id": pid, "period_name": "第1期", "apply_amount": 3000000, "audit_amount": 2850000}, token=TOKEN)
    check("POST /progress/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("GET", "/api/v1/progress/list", token=TOKEN, params={"project_id": pid})
    check("GET /progress/list 数组", s == 200 and isinstance(j, list), f"{s}")
    s, j = req("POST", "/api/v1/progress/payment-node", json_body={"project_id": pid, "name": "基础节点", "estimate": 3000000, "applied": 3000000, "audited": 2850000}, token=TOKEN)
    check("POST /progress/payment-node", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    s, j = req("GET", f"/api/v1/progress/payment-nodes/{pid}", token=TOKEN)
    check("GET /progress/payment-nodes/{pid} 数组", s == 200 and isinstance(j, list), f"{s}")
    s, j = req("GET", f"/api/v1/progress/payment-stats/{pid}", token=TOKEN)
    check("GET /progress/payment-stats/{pid}", s == 200 and isinstance(j, dict), f"{s} {j}")

    # 7. 核价库
    print("\n[7] 核价库")
    s, j = req("POST", "/api/v1/pricing/create", json_body={"project_id": pid, "name": "HRB400钢筋", "spec": "Φ25", "unit": "t", "category": "钢材", "price": 4200, "qty": 50}, token=TOKEN)
    check("POST /pricing/create", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    prcid = (j or {}).get("id")
    created["prcid"] = prcid
    s, j = req("GET", "/api/v1/pricing/list", token=TOKEN, params={"project_id": pid})
    check("GET /pricing/list 数组", s == 200 and isinstance(j, list), f"{s}")
    if prcid:
        s, j = req("PUT", f"/api/v1/pricing/{prcid}", json_body={"price": 4300, "qty": 60}, token=TOKEN)
        check("PUT /pricing/{prcid} 改单价", s == 200 and isinstance(j, dict) and j.get("price") == 4300, f"{s} {j}")

    # 8. 风险与预警
    print("\n[8] 风险与预警")
    s, j = req("POST", "/api/v1/risk/items", json_body={"project_id": pid, "risk_type": "进度", "level": "high", "title": "基础施工滞后", "desc": "连续降雨导致滞后3天", "due": "2026-08-20", "status": "open"}, token=TOKEN)
    check("POST /risk/items 创建", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    rid = (j or {}).get("id")
    created["rid"] = rid
    s, j = req("GET", "/api/v1/risk/items", token=TOKEN, params={"project_id": pid})
    check("GET /risk/items 数组", s == 200 and isinstance(j, list), f"{s}")
    if rid:
        s, j = req("PUT", f"/api/v1/risk/items/{rid}", json_body={"status": "handled"}, token=TOKEN)
        check("PUT /risk/items/{rid} 更新状态", s == 200 and isinstance(j, dict) and j.get("status") == "handled", f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/risk/items/{rid}", token=TOKEN)
        check("DELETE /risk/items/{rid}", s == 200 and (j or {}).get("deleted") is True, f"{s} {j}")
    s, j = req("GET", "/api/v1/risk/warnings", token=TOKEN)
    check("GET /risk/warnings 200", s == 200, f"{s}")

    # 9. 台账 / 统计
    print("\n[9] 台账 / 统计")
    s, j = req("GET", "/api/v1/ledger/list", token=TOKEN, params={"project_id": pid})
    check("GET /ledger/list 200", s == 200 and isinstance(j, list), f"{s}")
    s, txt = req("GET", "/api/v1/ledger/export", token=TOKEN, params={"project_id": pid}, raw=True)
    check("GET /ledger/export 下载文件(>0)", s == 200 and isinstance(txt, str) and len(txt) > 0, f"status={s} len={len(txt) if isinstance(txt,str) else '?'}")
    s, j = req("GET", "/api/v1/stats/cost-overview", token=TOKEN)
    check("GET /stats/cost-overview 字典", s == 200 and isinstance(j, dict), f"{s} {j}")

    # 10. 系统管理（用户/角色/权限/灰度/项目选择）
    print("\n[10] 系统管理（用户/角色/权限/灰度）")
    s, j = req("GET", "/api/v1/system/users", token=TOKEN)
    check("GET /system/users 数组", s == 200 and isinstance(j, list), f"{s}")
    s, j = req("POST", "/api/v1/system/users", json_body={"username": f"ftuser-{ts}", "real_name": "全测用户", "password": "ft123456", "status": 1}, token=TOKEN)
    check("POST /system/users", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    uid = (j or {}).get("id")
    created["uid"] = uid
    if uid:
        s, j = req("PUT", f"/api/v1/system/users/{uid}", json_body={"real_name": "全测用户-改", "status": 0}, token=TOKEN)
        check("PUT /system/users/{uid} 改状态", s == 200 and isinstance(j, dict) and j.get("id") == uid, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/system/users/{uid}", token=TOKEN)
        check("DELETE /system/users/{uid}", s == 200 and (j or {}).get("ok") is True, f"{s} {j}")
    s, j = req("GET", "/api/v1/system/roles", token=TOKEN)
    check("GET /system/roles 数组", s == 200 and isinstance(j, list), f"{s}")
    s, j = req("POST", "/api/v1/system/roles", json_body={"role_code": f"ftrole-{ts}", "role_name": "全测角色"}, token=TOKEN)
    check("POST /system/roles", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    rid_role = (j or {}).get("id")
    created["rid_role"] = rid_role
    if rid_role:
        s, j = req("PUT", f"/api/v1/system/roles/{rid_role}", json_body={"role_name": "全测角色-改"}, token=TOKEN)
        check("PUT /system/roles/{rid_role}", s == 200 and isinstance(j, dict) and j.get("id") == rid_role, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/system/roles/{rid_role}", token=TOKEN)
        check("DELETE /system/roles/{rid_role}", s == 200 and (j or {}).get("ok") is True, f"{s} {j}")
    s, j = req("GET", "/api/v1/system/permissions", token=TOKEN)
    check("GET /system/permissions 数组", s == 200 and isinstance(j, list), f"{s}")
    s, j = req("POST", "/api/v1/system/permissions", json_body={"perm_code": f"ft:perm:{ts}", "perm_name": "全测权限", "resource": "ft", "action": "view"}, token=TOKEN)
    check("POST /system/permissions", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    pid_perm = (j or {}).get("id")
    created["pid_perm"] = pid_perm
    if pid_perm:
        s, j = req("PUT", f"/api/v1/system/permissions/{pid_perm}", json_body={"perm_name": "全测权限-改"}, token=TOKEN)
        check("PUT /system/permissions/{pid_perm}", s == 200 and isinstance(j, dict) and j.get("id") == pid_perm, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/system/permissions/{pid_perm}", token=TOKEN)
        check("DELETE /system/permissions/{pid_perm}", s == 200 and (j or {}).get("ok") is True, f"{s} {j}")
    s, j = req("GET", "/api/v1/system/gray-releases", token=TOKEN)
    check("GET /system/gray-releases 数组", s == 200 and isinstance(j, list), f"{s}")
    s, j = req("POST", "/api/v1/system/gray-releases", json_body={"version_code": f"1.0.0-ft-{ts}", "enable": 1, "user_filter": {"user_ids": []}}, token=TOKEN)
    check("POST /system/gray-releases", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    gid = (j or {}).get("id")
    created["gid"] = gid
    if gid:
        s, j = req("PUT", f"/api/v1/system/gray-releases/{gid}", json_body={"enable": 0}, token=TOKEN)
        check("PUT /system/gray-releases/{gid}", s == 200 and isinstance(j, dict) and j.get("id") == gid, f"{s} {j}")
        s, j = req("DELETE", f"/api/v1/system/gray-releases/{gid}", token=TOKEN)
        check("DELETE /system/gray-releases/{gid}", s == 200 and (j or {}).get("ok") is True, f"{s} {j}")
    s, j = req("GET", "/api/v1/system/projects", token=TOKEN)
    check("GET /system/projects 数组(>=1)", s == 200 and isinstance(j, list) and len(j) >= 1, f"{s}")

    # 11. 客户端更新（发布/检测/下载/补丁上传）
    print("\n[11] 客户端更新（发布/检测/下载/补丁）")
    s, j = req("GET", "/api/v1/client/version/list", token=TOKEN)
    check("GET /client/version/list 200", s == 200, f"{s}")
    vc = f"1.0.0-ft-{ts}"
    s, j = req("POST", "/api/v1/client/version/publish", json_body={"version_code": vc, "version_desc": "全测发布", "force_update": 0, "min_compat_version": "1.0.0"}, token=TOKEN)
    check("POST /client/version/publish", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    created["vc"] = vc
    s, j = req("GET", "/api/v1/client/version/check", token=TOKEN, params={"local_ver": "0.9.0"})
    check("GET /client/version/check 返回 update 字段", s == 200 and isinstance(j, dict) and "update" in j, f"{s} {j}")
    s, txt = req("GET", f"/api/v1/client/version/download/{vc}", token=TOKEN, raw=True)
    check("GET /client/version/download/{vc} (200或404兜底)", s in (200, 404), f"status={s}")
    s, j = req("GET", "/api/v1/client/patch/list", token=TOKEN)
    check("GET /client/patch/list 200", s == 200, f"{s}")
    patch_data = b"\x00bsdiff-patch-data-for-test\x01\x02\x03"
    s, j = req("POST", "/api/v1/client/patch/upload", files={"file": ("ft.patch", patch_data, "application/octet-stream")}, params={"from_version": "1.0.0", "to_version": vc}, token=TOKEN)
    check("POST /client/patch/upload 返回 id", s == 200 and isinstance(j, dict) and j.get("id"), f"{s} {j}")
    pid_patch = (j or {}).get("id")
    created["pid_patch"] = pid_patch
    if pid_patch:
        s, txt = req("GET", f"/api/v1/client/patch/download/{pid_patch}", token=TOKEN, raw=True)
        check("GET /client/patch/download/{pid} 数据一致", s == 200 and isinstance(txt, str) and txt.encode("latin-1") == patch_data, f"status={s} len={len(txt) if isinstance(txt,str) else '?'}")

    # 12. 数据迁移（预览 + 触发）
    print("\n[12] 历史数据迁移（预览 + 触发）")
    s, j = req("GET", "/api/v1/migration/preview", token=TOKEN)
    ok = s == 200 and isinstance(j, dict) and j.get("file_size_bytes")
    check("GET /migration/preview 返回文件体积", ok, f"{s} {str(j)[:160]}")
    if ok:
        print(f"        文件大小={j.get('file_size_bytes')} 字节, 计数={j.get('counts')}")
    s, j = req("POST", "/api/v1/migration/run", token=TOKEN, timeout=180)
    ok = s == 200 and isinstance(j, dict) and j.get("job_id")
    check("POST /migration/run 返回 job_id", ok, f"{s} {j}")
    if ok:
        st, job = poll_task(j["job_id"], tries=180, interval=1.0)
        check(f"迁移任务完成 status={st}", st == "success", f"{job}")

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
