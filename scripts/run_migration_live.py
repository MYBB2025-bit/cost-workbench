"""实跑 183MB 历史数据迁移到运行中的后端，并轮询 TaskJob 直到完成。"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method, path, token=None, data=None, as_form=False):
    url = BASE + path
    headers = {}
    body = None
    if as_form and data is not None:
        # application/x-www-form-urlencoded
        body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in data.items()).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    # 1. 登录（OAuth2 表单）
    s, j = req("POST", "/api/v1/auth/login", data={"username": "admin", "password": "admin123"}, as_form=True)
    if s != 200:
        print(f"[FAIL] 登录失败 {s}: {j}")
        sys.exit(1)
    token = j["access_token"]
    print("[OK] 登录成功")

    # 2. 先预览，确认文件可读
    s, prev = req("GET", "/api/v1/migration/preview", token=token)
    if s != 200:
        print(f"[FAIL] 预览失败 {s}: {prev}")
        sys.exit(1)
    size = prev.get("file_size_bytes") or prev.get("size")
    print(f"[OK] 预览成功 文件大小={size} 字节 结构计数={prev.get('counts') or prev}")

    # 3. 触发迁移
    s, run = req("POST", "/api/v1/migration/run", token=token)
    if s != 200:
        print(f"[FAIL] 触发迁移失败 {s}: {run}")
        sys.exit(1)
    job_id = run["job_id"]
    print(f"[OK] 迁移已触发 job_id={job_id} 初始状态={run['status']}")

    # 4. 轮询
    for i in range(120):
        s, job = req("GET", f"/api/v1/task/{job_id}", token=token)
        if s != 200:
            print(f"[FAIL] 轮询失败 {s}: {job}")
            sys.exit(1)
        status = job.get("status")
        prog = job.get("progress")
        total = job.get("total")
        print(f"  轮询#{i+1} status={status} progress={prog}/{total}")
        if status in ("success", "failed"):
            break
        time.sleep(1)

    if status == "success":
        result = job.get("result")
        try:
            result = json.loads(result) if isinstance(result, str) else result
        except Exception:
            pass
        print("\n========== 迁移完成 ==========")
        print(f"job_id      : {job_id}")
        print(f"status      : {status}")
        print(f"result(stats): {json.dumps(result, ensure_ascii=False)}")
        # 校验落库：用各列表接口计数
        print("\n--- 落库校验 ---")
        for name, path in [
            ("项目", "/api/v1/project/list"),
            ("结算", "/api/v1/settlement/list"),
            ("签证", "/api/v1/change/visa/list"),
            ("进度款", "/api/v1/progress/list"),
            ("风险", "/api/v1/risk/items"),
            ("台账", "/api/v1/ledger/list"),
        ]:
            ss, dd = req("GET", path, token=token)
            n = len(dd) if isinstance(dd, list) else (dd.get("total") or "?")
            print(f"  {name}: HTTP {ss} 计数={n}")
    else:
        print(f"\n[FAIL] 迁移失败: {job.get('error')}")


if __name__ == "__main__":
    main()
