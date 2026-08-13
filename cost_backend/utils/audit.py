"""审计日志写入工具。"""

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SysAuditLog


async def write_audit(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    operate_type: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    content: dict | None = None,
    ip: str | None = None,
) -> None:
    row = SysAuditLog(
        user_id=user_id,
        operate_type=operate_type,
        resource_type=resource_type,
        resource_id=resource_id,
        content=content,
        ip=ip,
    )
    db.add(row)
    # 审计日志异步提交，调用方可自行决定何时 flush
    await db.flush()
