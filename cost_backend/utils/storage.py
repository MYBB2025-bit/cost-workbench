"""对象存储抽象：MinIO 为主，本地文件系统降级。
- 全栈：补丁/附件存 MinIO（大文件下载交给对象存储+Nginx，不占 FastAPI 算力）
- 降级：存本地 ./patches、./uploads 目录
对外统一暴露：put_object / get_object_stream / exists
"""
import os
from typing import BinaryIO

from core.config import settings


class Storage:
    def __init__(self):
        self.use_local = settings.USE_LOCAL_STORAGE
        self._client = None
        if not self.use_local:
            try:
                from minio import Minio

                self._client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE,
                )
                # 确保桶存在
                for b in (settings.MINIO_BUCKET_PATCH, settings.MINIO_BUCKET_ATTACH):
                    if not self._client.bucket_exists(b):
                        self._client.make_bucket(b)
            except Exception:
                # MinIO 不可用时自动降级本地
                self.use_local = True

    # ---- 本地路径 ----
    def _local_dir(self, bucket: str) -> str:
        base = settings.LOCAL_PATCH_DIR if bucket == settings.MINIO_BUCKET_PATCH else settings.LOCAL_UPLOAD_DIR
        os.makedirs(base, exist_ok=True)
        return base

    def put_object(self, bucket: str, key: str, data: BinaryIO, length: int) -> None:
        if self.use_local or self._client is None:
            path = os.path.join(self._local_dir(bucket), key)
            # key 可能含多级目录（如 visa/1/xxx.pdf），需确保父目录存在
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "wb") as f:
                f.write(data.read())
            return
        self._client.put_object(bucket, key, data, length=length)

    def get_object_stream(self, bucket: str, key: str):
        """返回 (stream_iterator, size)。stream_iterator 每次 yield 一个 bytes 块。"""
        if self.use_local or self._client is None:
            path = os.path.join(self._local_dir(bucket), key)
            if not os.path.exists(path):
                raise FileNotFoundError(key)
            size = os.path.getsize(path)

            def local_iter():
                with open(path, "rb") as f:
                    while chunk := f.read(1024 * 1024):
                        yield chunk

            return local_iter(), size
        obj = self._client.get_object(bucket, key)
        return obj.stream(1024 * 1024), obj.getheader("content-length")

    def exists(self, bucket: str, key: str) -> bool:
        if self.use_local or self._client is None:
            return os.path.exists(os.path.join(self._local_dir(bucket), key))
        try:
            self._client.stat_object(bucket, key)
            return True
        except Exception:
            return False


storage = Storage()
