"""预算清单业务层。"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostBudgetItem
from repository import budget_repo


async def _filter_project(
    project_id: int, project_ids: list[int] | None
) -> CostBudgetItem | None:
    if project_ids is not None and project_id not in project_ids:
        return None
    return None  # only used for side-effect check


async def list_items(
    db: AsyncSession,
    project_ids: list[int] | None,
    project_id: int | None = None,
) -> list[CostBudgetItem]:
    if project_id is not None and project_ids is not None and project_id not in project_ids:
        return []
    return await budget_repo.list_items(db, project_ids=project_ids, project_id=project_id)


async def get_item(
    db: AsyncSession, item_id: int, project_ids: list[int] | None
) -> CostBudgetItem | None:
    row = await budget_repo.get_item(db, item_id)
    if not row:
        return None
    if project_ids is not None and row.project_id not in project_ids:
        return None
    return row


async def create_item(db: AsyncSession, data: dict, user_id: int) -> CostBudgetItem:
    data = dict(data)
    data["total_price"] = float(data.get("qty", 0) or 0) * float(
        data.get("unit_price", 0) or 0
    )
    return await budget_repo.create_item(db, data)


async def update_item(
    db: AsyncSession, item_id: int, data: dict, project_ids: list[int] | None
) -> CostBudgetItem | None:
    row = await get_item(db, item_id, project_ids)
    if not row:
        return None
    return await budget_repo.update_item(db, row, data)


async def delete_item(
    db: AsyncSession, item_id: int, project_ids: list[int] | None
) -> bool:
    row = await get_item(db, item_id, project_ids)
    if not row:
        return False
    await budget_repo.delete_item(db, row)
    return True


def build_tree(rows: list[CostBudgetItem]) -> list[dict[str, Any]]:
    """把扁平清单项构建成树。"""
    node_map: dict[int, dict[str, Any]] = {}
    for r in rows:
        node = {
            "id": r.id,
            "project_id": r.project_id,
            "parent_id": r.parent_id,
            "item_no": r.item_no,
            "name": r.name,
            "spec": r.spec,
            "unit": r.unit,
            "qty": float(r.qty or 0),
            "unit_price": float(r.unit_price or 0),
            "total_price": float(r.total_price or 0),
            "category": r.category,
            "work_type": r.work_type,
            "sort_order": r.sort_order,
            "children": [],
        }
        node_map[r.id] = node
    roots = []
    for r in rows:
        node = node_map[r.id]
        if r.parent_id and r.parent_id in node_map:
            node_map[r.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


async def bulk_import(
    db: AsyncSession, project_id: int, rows: list[dict], user_id: int
) -> dict[str, Any]:
    """批量导入预算清单（来自 xlsx 解析结果）。返回导入统计。"""
    created = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    nodes: list[tuple] = []  # (item_no, parent_no, orm)

    for i, r in enumerate(rows, start=2):  # 第 1 行为表头
        name = str(r.get("name") or "").strip()
        if not name:
            skipped += 1
            errors.append({"row": i, "reason": "缺少名称"})
            continue
        try:
            qty = float(r.get("qty") or 0)
            unit_price = float(r.get("unit_price") or 0)
        except (TypeError, ValueError):
            qty, unit_price = 0.0, 0.0
        item_no = str(r.get("item_no") or "").strip() or None
        obj = CostBudgetItem(
            project_id=project_id,
            item_no=item_no,
            name=name,
            spec=str(r.get("spec") or "").strip() or None,
            unit=str(r.get("unit") or "").strip() or None,
            qty=qty,
            unit_price=unit_price,
            total_price=qty * unit_price,
            category=str(r.get("category") or "").strip() or None,
        )
        nodes.append((item_no, str(r.get("parent_no") or "").strip(), obj))
        created += 1

    orm_list = [n[2] for n in nodes]
    await budget_repo.bulk_create(db, orm_list)
    by_no = {no: obj for no, pno, obj in nodes if no}
    for _no, pno, obj in nodes:
        if pno and pno in by_no:
            obj.parent_id = by_no[pno].id
    await db.commit()
    return {"created": created, "skipped": skipped, "errors": errors, "imported_by": user_id}

