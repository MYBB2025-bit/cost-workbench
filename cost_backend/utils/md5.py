"""MD5 工具：发布补丁/附件前校验完整性。"""
import hashlib


def calc_md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def calc_md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()
