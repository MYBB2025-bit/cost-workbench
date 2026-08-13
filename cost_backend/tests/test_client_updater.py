"""客户端自更新器（tools/client_updater）单元测试 + 与后端更新接口的契约测试。"""
import hashlib
import os
import sys

import bsdiff4
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.client_updater import (  # noqa: E402
    ClientUpdater,
    UpdateError,
    UpdateInfo,
    file_md5,
    parse_range_header,
)


# ============================ 纯函数 / 单元 ============================
def test_file_md5(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"hello world")
    assert file_md5(str(p)) == hashlib.md5(b"hello world").hexdigest()


@pytest.mark.parametrize("header,total,expect", [
    ("bytes=0-99", 1000, (0, 99)),
    ("bytes=500-", 1000, (500, 999)),
    ("bytes=-100", 1000, (900, 999)),
    (None, 1000, None),
    ("bytes=10-5", 1000, None),
])
def test_parse_range_header(header, total, expect):
    assert parse_range_header(header, total) == expect


def test_apply_bsdiff_roundtrip(tmp_path):
    old = tmp_path / "old.bin"
    new = tmp_path / "new.bin"
    patch = tmp_path / "p.bsdiff"
    out = tmp_path / "out.bin"
    old.write_bytes(b"A" * 1000 + b"BASELINE" + b"B" * 500)
    new.write_bytes(b"A" * 1000 + b"PATCHED_CONTENT" + b"B" * 500)
    bsdiff4.file_diff(str(old), str(new), str(patch))
    u = ClientUpdater(exe_path=str(old))
    u.apply_bsdiff(str(old), str(patch), str(out))
    assert out.read_bytes() == new.read_bytes()


def test_update_info_parse():
    info = UpdateInfo({"update": True, "latest_version": "v2", "force_update": 1,
                       "patch": {"patch_id": 7, "md5": "abc", "size": 10}})
    assert info.update and info.force_update
    assert info.patch.patch_id == 7 and info.patch.md5 == "abc"
    assert not info.need_full

    info2 = UpdateInfo({"update": True, "latest_version": "v2",
                        "download_url": "/client/version/download/v2", "full_md5": "ff"})
    assert info2.need_full
    assert info2.download_url == "/client/version/download/v2"


# ====================== 下载逻辑（mock requests）======================
class FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def iter_content(self, n=1):
        for i in range(0, len(self._data), n):
            yield self._data[i:i + n]


class FakeRequests:
    def __init__(self, data, status=200):
        self._resp = FakeResp(data, status)
        self.last_headers = None

    def get(self, url, headers=None, stream=False, timeout=None):
        self.last_headers = headers
        return self._resp


def test_download_full_200(tmp_path, monkeypatch):
    data = b"X" * 2048
    monkeypatch.setattr("tools.client_updater._lazy_requests", lambda: FakeRequests(data, 200))
    u = ClientUpdater(workdir=str(tmp_path))
    dest = u._download("http://x/full.exe", hashlib.md5(data).hexdigest(), str(tmp_path / "out.exe"))
    assert open(dest, "rb").read() == data


def test_download_resume_206(tmp_path, monkeypatch):
    data = b"Y" * 3000
    (tmp_path / "out.exe.part").write_bytes(data[:1000])
    monkeypatch.setattr("tools.client_updater._lazy_requests", lambda: FakeRequests(data[1000:], 206))
    u = ClientUpdater(workdir=str(tmp_path))
    dest = u._download("http://x/p.bin", hashlib.md5(data).hexdigest(), str(tmp_path / "out.exe"))
    assert open(dest, "rb").read() == data


def test_download_200_ignores_range_restart(tmp_path, monkeypatch):
    data = b"W" * 1500
    (tmp_path / "out.exe.part").write_bytes(b"stale")
    monkeypatch.setattr("tools.client_updater._lazy_requests", lambda: FakeRequests(data, 200))
    u = ClientUpdater(workdir=str(tmp_path))
    dest = u._download("http://x/f.exe", hashlib.md5(data).hexdigest(), str(tmp_path / "out.exe"))
    assert open(dest, "rb").read() == data


def test_download_md5_fail(tmp_path, monkeypatch):
    data = b"Z" * 1024
    monkeypatch.setattr("tools.client_updater._lazy_requests", lambda: FakeRequests(data, 200))
    u = ClientUpdater(workdir=str(tmp_path))
    with pytest.raises(UpdateError):
        u._download("http://x/f.exe", "deadbeef", str(tmp_path / "out.exe"))
    assert not (tmp_path / "out.exe.part").exists()


# ================ 后端更新接口契约（TestClient + 真实 patch）===============
def _seed(client):
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/v1/client/version/publish",
        json={"version_code": "v1.0.1", "version_desc": "test"}, headers=H,
    )
    old = b"A" * 2000 + b"OLD_BUILD" + b"B" * 1000
    new = b"A" * 2000 + b"NEW_BUILD_X" + b"B" * 1000
    patch = bsdiff4.diff(old, new)
    files = {"file": ("v1.0.0__to__v1.0.1.bsdiff", patch, "application/octet-stream")}
    r = client.post(
        "/api/v1/client/patch/upload",
        files=files,
        params={"from_version": "v1.0.0", "to_version": "v1.0.1"},
        headers=H,
    )
    assert r.status_code == 200, r.text
    return token, r.json()["id"], patch


def test_check_returns_patch(client):
    token, patch_id, patch = _seed(client)
    H = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/client/version/check?local_ver=v1.0.0", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["update"] is True
    assert body["patch"]["patch_id"] == patch_id
    assert body["patch"]["md5"] == hashlib.md5(patch).hexdigest()


def test_patch_download_200_and_206(client):
    token, patch_id, patch = _seed(client)
    url = f"/api/v1/client/patch/download/{patch_id}"
    r = client.get(url)
    assert r.status_code == 200
    assert r.content == patch
    assert r.headers.get("Accept-Ranges") == "bytes"
    # 断点续传：Range 应返回 206
    r2 = client.get(url, headers={"Range": "bytes=0-9"})
    assert r2.status_code == 206
    assert r2.headers["Content-Range"] == f"bytes 0-9/{len(patch)}"
    assert r2.content == patch[:10]


def test_full_download_404_when_missing(client):
    _seed(client)
    r = client.get("/api/v1/client/version/download/v1.0.1")
    assert r.status_code == 404
