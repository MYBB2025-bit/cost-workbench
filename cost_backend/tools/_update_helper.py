"""自更新辅助进程（由 client_updater 在运行时生成并派生，独立运行）。

职责：
  1. 等待父进程退出，释放被占用的 exe 文件锁；
  2. 备份旧 exe；
  3. 将下载好的新 exe 替换到位；
  4. 启动新 exe 并验证其在 5 秒内保持存活；
  5. 若新 exe 启动失败，自动回滚到备份并重新拉起旧版。

仅使用标准库，以便冻结成 exe 后也能独立运行。
参数为一个 JSON 文件路径，内含：exe / new / backup / guard。
"""
import json
import os
import subprocess
import sys
import time


def _rollback(exe, backup):
    """回滚：删掉损坏的新 exe，恢复备份，并重拉旧版。"""
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
    with open(sys.argv[1], encoding="utf-8") as f:
        cfg = json.load(f)
    exe = cfg["exe"]
    new = cfg["new"]
    backup = cfg["backup"]
    guard = cfg["guard"]

    # 等待父进程退出，释放文件锁
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
        # 写入更新守卫：新 exe 成功启动后应清除它
        with open(guard, "w", encoding="utf-8") as g:
            g.write(str(time.time()))
        p = subprocess.Popen([exe])
    except Exception:
        _rollback(exe, backup)
        sys.exit(1)

    # 验证新进程在 5 秒内保持存活（崩溃的 exe 会被检测出来）
    try:
        for _ in range(50):
            time.sleep(0.1)
            if p.poll() is not None:
                raise RuntimeError("新进程启动后立即退出")
        time.sleep(3)
        if p.poll() is not None:
            raise RuntimeError("新进程启动后异常退出")
    except Exception:
        _rollback(exe, backup)
        sys.exit(1)


if __name__ == "__main__":
    main()
