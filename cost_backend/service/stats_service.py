"""造价总览统计：预算 / 变更 / 结算聚合。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    CostBudgetItem,
    CostChangeOrder,
    CostProject,
    CostSettlement,
)


async def cost_overview(
    db: AsyncSession,
    project_ids: list[int] | None,
    project_id: int | None = None,
) -> dict:
    """汇总预算合价、变更金额、结算金额，并给出按项目/科目/状态分布。"""
    if not project_ids:
        return _empty()

    proj_filter = _build_proj_filter(project_ids, project_id)

    # 预算合价
    budget_rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(CostBudgetItem.total_price), 0),
                func.count(CostBudgetItem.id),
            ).where(proj_filter(CostBudgetItem.project_id))
        )
    ).one()
    budget_total = float(budget_rows[0] or 0)
    budget_count = int(budget_rows[1] or 0)

    # 预算按科目分布
    cat_rows = (
        await db.execute(
            select(
                CostBudgetItem.category,
                func.coalesce(func.sum(CostBudgetItem.total_price), 0),
            )
            .where(proj_filter(CostBudgetItem.project_id))
            .group_by(CostBudgetItem.category)
        )
    ).all()
    by_category = [
        {"category": c or "未分类", "total": float(t or 0)} for c, t in cat_rows
    ]

    # 预算按项目分布
    proj_rows = (
        await db.execute(
            select(
                CostBudgetItem.project_id,
                CostProject.project_name,
                func.coalesce(func.sum(CostBudgetItem.total_price), 0),
            )
            .outerjoin(CostProject, CostProject.id == CostBudgetItem.project_id)
            .where(proj_filter(CostBudgetItem.project_id))
            .group_by(CostBudgetItem.project_id, CostProject.project_name)
        )
    ).all()
    by_project = [
        {"project_id": pid, "project_name": pname or f"项目{pid}", "total": float(t or 0)}
        for pid, pname, t in proj_rows
    ]

    # 变更金额
    change_rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(CostChangeOrder.amount), 0),
                func.count(CostChangeOrder.id),
            ).where(proj_filter(CostChangeOrder.project_id))
        )
    ).one()
    change_total = float(change_rows[0] or 0)
    change_count = int(change_rows[1] or 0)

    # 变更 TOP（按金额降序，取前 10）
    top_rows = (
        await db.execute(
            select(
                CostChangeOrder.change_no,
                CostChangeOrder.change_name,
                CostChangeOrder.amount,
            )
            .where(proj_filter(CostChangeOrder.project_id))
            .order_by(CostChangeOrder.amount.desc())
            .limit(10)
        )
    ).all()
    change_top = [
        {"change_no": no or "", "name": nm or "", "amount": float(a or 0)}
        for no, nm, a in top_rows
    ]

    # 结算金额
    settle_rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(CostSettlement.total_amount), 0),
                func.count(CostSettlement.id),
            ).where(proj_filter(CostSettlement.project_id))
        )
    ).one()
    settlement_total = float(settle_rows[0] or 0)
    settlement_count = int(settle_rows[1] or 0)

    # 结算按状态
    settle_status_rows = (
        await db.execute(
            select(
                CostSettlement.status,
                func.coalesce(func.sum(CostSettlement.total_amount), 0),
            )
            .where(proj_filter(CostSettlement.project_id))
            .group_by(CostSettlement.status)
        )
    ).all()
    by_settlement_status = [
        {"status": s or "未知", "total": float(t or 0)} for s, t in settle_status_rows
    ]

    return {
        "budget_total": budget_total,
        "budget_count": budget_count,
        "by_category": by_category,
        "by_project": by_project,
        "change_total": change_total,
        "change_count": change_count,
        "change_top": change_top,
        "settlement_total": settlement_total,
        "settlement_count": settlement_count,
        "by_settlement_status": by_settlement_status,
    }


def _build_proj_filter(project_ids: list[int] | None, project_id: int | None):
    """返回一个函数 col -> 条件，便于对各表复用项目权限过滤。"""
    if project_id is not None:
        if project_ids is not None and project_id not in project_ids:
            allowed = []
        else:
            allowed = [project_id]
    else:
        allowed = project_ids or []

    def _f(col):
        if not allowed:
            return col.in_([])  # 无权限
        return col.in_(allowed)

    return _f


def _empty() -> dict:
    return {
        "budget_total": 0,
        "budget_count": 0,
        "by_category": [],
        "by_project": [],
        "change_total": 0,
        "change_count": 0,
        "change_top": [],
        "settlement_total": 0,
        "settlement_count": 0,
        "by_settlement_status": [],
    }
