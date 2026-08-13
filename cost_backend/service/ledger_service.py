"""最终资料台账采集（移植原 collectFinalLedger，台账聚合并行加兜底）。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostLedgerDoc, CostProject


async def collect_final_ledger(
    db: AsyncSession, project_ids: list[int] | None, project_id: int | None = None
) -> list[dict]:
    if project_ids == []:
        return []
    stmt = select(CostLedgerDoc)
    if project_id is not None:
        if project_ids is not None and project_id not in project_ids:
            return []
        stmt = stmt.where(CostLedgerDoc.project_id == project_id)
    elif project_ids is not None:
        stmt = stmt.where(CostLedgerDoc.project_id.in_(project_ids))
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "category": r.category,
            "name": r.name,
            "owner": r.owner,
            "due": r.due,
            "status": r.status,
            "finished_at": r.finished_at,
        }
        for r in rows
    ]


async def export_ledger(
    db: AsyncSession, project_ids: list[int] | None, project_id: int | None = None
) -> list[dict]:
    """导出台账为行列表（带项目名称），支持按项目过滤。

    project_ids 为 None 表示超级管理员可访问全部项目（不过滤）；
    为空列表 [] 表示无权访问任何项目，返回空。
    """
    if project_ids == []:
        return []
    stmt = select(CostLedgerDoc, CostProject.project_name).outerjoin(
        CostProject, CostProject.id == CostLedgerDoc.project_id
    )
    if project_id is not None:
        if project_ids is not None and project_id not in project_ids:
            return []
        stmt = stmt.where(CostLedgerDoc.project_id == project_id)
    elif project_ids is not None:
        stmt = stmt.where(CostLedgerDoc.project_id.in_(project_ids))
    res = await db.execute(stmt)
    out = []
    for r, pname in res.all():
        out.append(
            {
                "project_name": pname or "",
                "category": r.category or "",
                "name": r.name or "",
                "owner": r.owner or "",
                "due": r.due or "",
                "status": r.status or "",
                "finished_at": r.finished_at or "",
            }
        )
    return out

