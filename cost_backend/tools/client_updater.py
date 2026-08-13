"""造价平台客户端（exe）自更新器。

部署在最终用户机器上的 exe 旁，用于：
  检测更新（带鉴权 + 服务端灰度过滤） → 断点续传下载 bsdiff 补丁/整包
  → MD5 校验 → 安全打补丁（失败自动回滚） → 替换自身并重启动（带启动自愈守卫）。

依赖（需打包进客户端，非服务端）：requests、bsdiff4
    pip install requests bsdiff4

典型用法
--------
1) 作为库，在 PyWebView 应用启动后静默检测（传入已登录用户的 token）：

    from tools.client_updater import ClientUpdater
    updater = ClientUpdater(
        api_base="https://update.example.com/api/v1",
        token=user_token,            # 来自应用登录态
        exe_path=sys.executable,     # 当前 exe 自身
    )
    result = updater.run(local_ver="v1.0.0", silent=True)
    # 若检测到更新，run() 会派生更新助手进程完成替换并重启；
    # 应用应在启动时调用 updater.clear_guard() 清除更新守卫标记。

2) 命令行（无 GUI 场景 / CI）：

    python client_updater.py --current v1.0.0 --exe cost_workbench.exe \
        --api-base https://update.example.com/api/v1 \
        --username alice --password ***
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger("client_updater")

# 更新助手进程的源码（运行时写出到工作目录，确保冻结成 exe 后也能独立运行）
HELPER_SOURCE = '''"""自更新辅助进程（由 client_updater 派生，独立运行）。"""
import json
import os
import subprocess
import sys
import time


def _rollback(exe, backup):
    try:
        if os.path.exists(exe):
            try:
                os.remove(exe)
            except OSError:
                pass
        if os.path.exists(backup):
            os.rename(backup, exe)
            subprocess.Popen([exe])
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        cfg = json.load(f)
    exe = cfg["exe"]
    new = cfg["new"]
    backup = cfg["backup"]
    guard = cfg["guard"]
    time.sleep(1.5)
    try:
        if os.path.exists(backup):
            try:
                os.remove(backup)
            except OSError:
                pass
        if os.path.exists(exe):
            os.rename(exe, backup)
        import shutil
        shutil.move(new, exe)
        with open(guard, "w", encoding="utf-8") as g:
            g.write(str(time.time()))
        p = subprocess.Popen([exe])
    except Exception:
        _rollback(exe, backup)
        sys.exit(1)
    try:
        for _ in range(50):
            time.sleep(0.1)
            if p.poll() is not None:
                raise RuntimeError("new process exited immediately")
        time.sleep(3)
        if p.poll() is not None:
            raise RuntimeError("new process crashed after start")
    except Exception:
        _rollback(exe, backup)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# 数据契约（与后端 /api/v1/client/* 对齐）
# ---------------------------------------------------------------------------
class PatchInfo:
    def __init__(self, patch_id, md5, size):
        self.patch_id = patch_id
        self.md5 = md5 or ""
        self.size = size or 0

    @classmethod
    def from_dict(cls, d):
        if not d:
            return None
        return cls(d.get("patch_id"), d.get("md5", ""), d.get("size", 0))


class UpdateInfo:
    def __init__(self, raw: dict):
        self.raw = raw
        self.update = bool(raw.get("update", False))
        self.latest_version = raw.get("latest_version")
        self.force_update = bool(raw.get("force_update", False))
        self.min_compat_version = raw.get("min_compat_version")
        self.version_desc = raw.get("version_desc", "")
        self.patch = PatchInfo.from_dict(raw.get("patch"))
        # 整包更新地址（当无差分补丁时由服务端返回，相对 api_base 的路径）
        self.download_url = raw.get("download_url")
        self.full_md5 = raw.get("full_md5", "")

    @property
    def need_full(self) -> bool:
        """需要走整包更新：服务端声明有更新，但未提供差分补丁。"""
        return self.update and self.patch is None


class UpdateError(Exception):
    pass


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def file_md5(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _lazy_requests():
    try:
        import requests
        return requests
    except ImportError as e:
        raise UpdateError("缺少依赖 requests，请 pip install requests") from e


def _lazy_bsdiff4():
    try:
        import bsdiff4
        return bsdiff4
    except ImportError as e:
        raise UpdateError("缺少依赖 bsdiff4，请 pip install bsdiff4") from e


def parse_range_header(header: str, total: int):
    """解析 HTTP Range 头，返回 (start, end) 或 None。"""
    if not header or not header.lower().startswith("bytes="):
        return None
    spec = header[len("bytes="):].strip()
    parts = spec.split("-")
    if len(parts) != 2:
        return None
    start_s, end_s = parts
    if not start_s:
        # 后缀形式 bytes=-N：取最后 N 字节
        if not end_s:
            return None
        suffix = int(end_s)
        start = max(0, total - suffix)
        end = total - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else total - 1
    if end >= total:
        end = total - 1
    if start < 0 or start > end:
        return None
    return start, end


def _slice_stream(stream_iter, start: int, end: int):
    """从流中跳过前 start 字节，并最多产出 (end - start + 1) 字节。"""
    remaining_skip = start
    while remaining_skip > 0:
        chunk = next(stream_iter, b"")
        if not chunk:
            return
        if len(chunk) <= remaining_skip:
            remaining_skip -= len(chunk)
            continue
        chunk = chunk[remaining_skip:]
        remaining_skip = 0
        yield chunk
    budget = end - start + 1
    for chunk in stream_iter:
        if not chunk:
            break
        if len(chunk) <= budget:
            budget -= len(chunk)
            yield chunk
        else:
            yield chunk[:budget]
            return


# ---------------------------------------------------------------------------
# 主更新器
# ---------------------------------------------------------------------------
class ClientUpdater:
    def __init__(
        self,
        api_base: str = "http://127.0.0.1:8000/api/v1",
        token: str = None,
        username: str = None,
        password: str = None,
        exe_path: str = None,
        workdir: str = None,
        timeout: int = 60,
    ):
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.username = username
        self.password = password
        self.exe_path = exe_path or sys.argv[0]
        self.workdir = workdir or os.path.dirname(os.path.abspath(self.exe_path))
        self.timeout = timeout
        self.backup_path = self.exe_path + ".bak"
        self.guard_path = os.path.join(self.workdir, ".update_guard")

    # ---- 鉴权 ----------------------------------------------------------
    def _ensure_token(self) -> str:
        if self.token:
            return self.token
        if not self.username or not self.password:
            raise UpdateError("未提供 token，也未提供 username/password 用于登录")
        requests = _lazy_requests()
        r = requests.post(
            f"{self.api_base}/auth/login",
            data={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        r.raise_for_status()
        self.token = r.json().get("access_token")
        if not self.token:
            raise UpdateError("登录失败：服务端未返回 access_token")
        return self.token

    # ---- 检测更新 ------------------------------------------------------
    def check(self, local_ver: str) -> UpdateInfo:
        requests = _lazy_requests()
        token = self._ensure_token()
        r = requests.get(
            f"{self.api_base}/client/version/check",
            params={"local_ver": local_ver},
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return UpdateInfo(r.json())

    # ---- 下载（断点续传 + MD5 校验）----------------------------------
    def _download(self, url: str, expect_md5: str, dest: str, auth: str = None) -> str:
        requests = _lazy_requests()
        tmp = dest + ".part"
        exist = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        headers = {}
        if exist:
            headers["Range"] = f"bytes={exist}-"
        if auth:
            headers["Authorization"] = f"Bearer {auth}"
        resp = requests.get(url, headers=headers, stream=True, timeout=self.timeout)
        resp.raise_for_status()
        if resp.status_code == 206:
            mode = "ab"
        else:
            # 服务端不支持续传，从头写
            mode = "wb"
            if os.path.exists(tmp):
                os.remove(tmp)
        with open(tmp, mode) as f:
            for chunk in resp.iter_content(1 << 16):
                if chunk:
                    f.write(chunk)
        if expect_md5 and file_md5(tmp) != expect_md5:
            os.remove(tmp)
            raise UpdateError("下载文件 MD5 校验失败，可能已损坏或被篡改")
        shutil.move(tmp, dest)
        return dest

    def download_patch(self, patch: PatchInfo, dest: str = None) -> str:
        """下载差分补丁（该端点免鉴权）。"""
        dest = dest or os.path.join(self.workdir, f"patch_{patch.patch_id}.bsdiff")
        url = f"{self.api_base}/client/patch/download/{patch.patch_id}"
        return self._download(url, patch.md5, dest, auth=None)

    def download_full(self, download_url: str, expect_md5: str = "", dest: str = None) -> str:
        """下载整包（无差分补丁时的兜底方案）。"""
        dest = dest or os.path.join(self.workdir, "update_full.exe")
        url = self.api_base + download_url if download_url.startswith("/") else download_url
        return self._download(url, expect_md5, dest, auth=self.token)

    # ---- 应用补丁 ------------------------------------------------------
    def apply_bsdiff(self, old_path: str, patch_path: str, new_path: str) -> None:
        bsdiff4 = _lazy_bsdiff4()
        try:
            bsdiff4.file_patch(old_path, new_path, patch_path)
        except Exception as e:
            raise UpdateError(f"补丁应用失败: {e}") from e
        if not os.path.exists(new_path) or os.path.getsize(new_path) == 0:
            raise UpdateError("补丁应用后生成文件为空，疑似补丁与目标版本不匹配")

    # ---- 替换 + 重启（派生独立助手进程）------------------------------
    def _spawn_helper(self, new_exe_path: str) -> None:
        helper_path = os.path.join(self.workdir, "_update_helper.py")
        with open(helper_path, "w", encoding="utf-8") as f:
            f.write(HELPER_SOURCE)
        args_path = os.path.join(self.workdir, "_update_helper_args.json")
        with open(args_path, "w", encoding="utf-8") as f:
            json.dump(
                {"exe": self.exe_path, "new": new_exe_path,
                 "backup": self.backup_path, "guard": self.guard_path},
                f,
            )
        flags = 0x00000200 if sys.platform == "win32" else 0  # DETACHED_PROCESS
        subprocess.Popen(
            [sys.executable, helper_path, args_path],
            creationflags=flags,
            close_fds=True,
        )

    # ---- 启动守卫（自愈）---------------------------------------------
    def clear_guard(self) -> None:
        """应用成功启动后调用，清除更新守卫标记。"""
        if os.path.exists(self.guard_path):
            try:
                os.remove(self.guard_path)
            except OSError:
                pass

    def maybe_rollback_on_startup(self) -> bool:
        """应用启动时调用：若上次更新失败（守卫仍在且新 exe 缺失），自动回滚。"""
        if not os.path.exists(self.guard_path):
            return False
        if os.path.exists(self.exe_path) and os.path.exists(self.backup_path):
            # 新 exe 已就位且守卫未清 → 视为成功，清守卫即可
            self.clear_guard()
            return False
        # 新 exe 缺失但备份在 → 回滚
        if os.path.exists(self.backup_path):
            try:
                if os.path.exists(self.exe_path):
                    os.remove(self.exe_path)
                os.rename(self.backup_path, self.exe_path)
                subprocess.Popen([self.exe_path])
            except Exception:
                pass
        try:
            os.remove(self.guard_path)
        except OSError:
            pass
        return True

    # ---- 编排 ----------------------------------------------------------
    def run(self, local_ver: str, silent: bool = True, relaunch: bool = True) -> dict:
        info = self.check(local_ver)
        if not info.update:
            logger.info("已是最新版本 %s", local_ver)
            return {"updated": False, "reason": "latest"}

        work = os.path.join(self.workdir, "update")
        os.makedirs(work, exist_ok=True)

        if info.patch:
            logger.info("发现差分补丁：%s → %s", local_ver, info.latest_version)
            patch_path = self.download_patch(
                info.patch, os.path.join(work, f"patch_{info.patch.patch_id}.bsdiff")
            )
            new_exe = os.path.join(work, "new.exe")
            self.apply_bsdiff(self.exe_path, patch_path, new_exe)
            action = "patch"
        elif info.need_full and info.download_url:
            logger.info("无差分补丁，走整包更新到 %s", info.latest_version)
            new_exe = self.download_full(
                info.download_url, info.full_md5, os.path.join(work, "full.exe")
            )
            action = "full"
        else:
            raise UpdateError("服务端未提供差分补丁或整包下载地址，无法自动更新")

        if not relaunch:
            return {"updated": True, "relaunched": False, "new_exe": new_exe, "action": action}

        self._spawn_helper(new_exe)
        logger.info("已派生更新助手，将替换并重启应用")
        sys.exit(0)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="造价平台客户端自更新")
    ap.add_argument("--current", required=True, help="当前版本号，如 v1.0.0")
    ap.add_argument("--exe", default=sys.argv[0], help="exe 文件路径（默认当前进程）")
    ap.add_argument("--api-base", default="http://127.0.0.1:8000/api/v1")
    ap.add_argument("--username", default=os.getenv("COST_CLIENT_USER"))
    ap.add_argument("--password", default=os.getenv("COST_CLIENT_PASSWORD"))
    ap.add_argument("--token", default=os.getenv("COST_CLIENT_TOKEN"))
    ap.add_argument("--workdir", default=None, help="工作/下载目录（默认 exe 同目录）")
    ap.add_argument("--check-only", action="store_true", help="仅检测并打印结果")
    args = ap.parse_args()

    updater = ClientUpdater(
        api_base=args.api_base,
        token=args.token,
        username=args.username,
        password=args.password,
        exe_path=args.exe,
        workdir=args.workdir,
    )

    if args.check_only:
        info = updater.check(args.current)
        print(json.dumps(
            {"update": info.update, "latest_version": info.latest_version,
             "force_update": info.force_update, "version_desc": info.version_desc,
             "has_patch": info.patch is not None, "need_full": info.need_full},
            ensure_ascii=False, indent=2,
        ))
        return

    updater.run(args.current)


if __name__ == "__main__":
    main()
