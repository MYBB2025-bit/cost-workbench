"""风险与预警采集（移植原 collectRiskItems / collectWarningItems，修复无兜底崩溃）。
原缺陷：直接 D.tasks.forEach 等，数组缺失即崩溃；现改为 DB 查询，天然安全（空结果=[]）。
"""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostLedgerDoc, CostRiskItem, CostWarningRule


async def collect_risk_items(db: AsyncSession, project_ids: list[int]) -> list[dict]:
    if not project_ids:
        return []
    res = await db.execute(select(CostRiskItem).where(CostRiskItem.project_id.in_(project_ids)))
    rows = res.scalars().all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "risk_type": r.risk_type,
            "level": r.level,
            "title": r.title,
            "desc": r.desc,
            "due": r.due,
            "status": r.status,
            "related_type": r.related_type,
            "related_id": r.related_id,
        }
        for r in rows
    ]


async def collect_warning_items(db: AsyncSession, project_ids: list[int]) -> list[dict]:
    """依据预警规则（默认 7 天）筛选临期且未完成的台账文档。"""
    if not project_ids:
        return []
    rule_res = await db.execute(select(CostWarningRule).where(CostWarningRule.enabled == 1))
    rules = rule_res.scalars().all()
    threshold = rules[0].threshold_days if rules else 7

    today = datetime.now().date()
    deadline = today + timedelta(days=threshold)
    res = await db.execute(
        select(CostLedgerDoc).where(
            CostLedgerDoc.project_id.in_(project_ids),
            CostLedgerDoc.status != "done",
        )
    )
    rows = res.scalars().all()
    warnings = []
    for r in rows:
        due = _parse_date(r.due)
        if due and today <= due <= deadline:
            warnings.append(
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "category": r.category,
                    "name": r.name,
                    "owner": r.owner,
                    "due": r.due,
                    "status": r.status,
                    "days_left": (due - today).days,
                }
            )
    return warnings


def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
