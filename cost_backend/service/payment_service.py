"""进度款 WBS 递归统计（移植原 paymentStats，修复 bug②）。
原缺陷：totalEstimate = ownEst || childEst —— 父节点自带值会吞掉子节点汇总。
修复：total = 本级值 + Σ(子节点汇总值)，父/子不再互斥。
输入为扁平节点列表（含 parent_id），内部构建树后递归聚合。
"""


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def build_payment_tree(nodes: list) -> list[dict]:
    """nodes: 含 id / parent_id / name / estimate / applied / audited / status 的对象（ORM 或 dict）。"""
    entries = {}
    for n in nodes:
        nid = getattr(n, "id", None) if not isinstance(n, dict) else n.get("id")
        name = getattr(n, "name", None) if not isinstance(n, dict) else n.get("name")
        est = _num(getattr(n, "estimate", 0) if not isinstance(n, dict) else n.get("estimate", 0))
        app = _num(getattr(n, "applied", 0) if not isinstance(n, dict) else n.get("applied", 0))
        aud = _num(getattr(n, "audited", 0) if not isinstance(n, dict) else n.get("audited", 0))
        status = getattr(n, "status", None) if not isinstance(n, dict) else n.get("status")
        entries[nid] = {
            "id": nid, "name": name, "status": status,
            "own_estimate": est, "own_applied": app, "own_audited": aud,
            "children": [],
        }

    roots = []
    for nid, entry in entries.items():
        # 找到父节点
        parent_id = _find_parent(nodes, nid)
        if parent_id is not None and parent_id in entries:
            entries[parent_id]["children"].append(entry)
        else:
            roots.append(entry)
    return [_aggregate(r) for r in roots]


def _find_parent(nodes, nid):
    for n in nodes:
        if (getattr(n, "id", None) if not isinstance(n, dict) else n.get("id")) == nid:
            return getattr(n, "parent_id", None) if not isinstance(n, dict) else n.get("parent_id")
    return None


def _aggregate(entry: dict) -> dict:
    child_results = [_aggregate(c) for c in entry["children"]]
    child_est = sum(c["total_estimate"] for c in child_results)
    child_app = sum(c["total_applied"] for c in child_results)
    child_aud = sum(c["total_audited"] for c in child_results)
    total_est = entry["own_estimate"] + child_est
    total_app = entry["own_applied"] + child_app
    total_aud = entry["own_audited"] + child_aud
    return {
        "id": entry["id"],
        "name": entry["name"],
        "status": entry["status"],
        "own_estimate": round(entry["own_estimate"], 4),
        "own_applied": round(entry["own_applied"], 4),
        "own_audited": round(entry["own_audited"], 4),
        "total_estimate": round(total_est, 4),
        "total_applied": round(total_app, 4),
        "total_audited": round(total_aud, 4),
        "children": child_results,
    }


def compute_payment_stats(nodes: list) -> dict:
    """对外聚合入口：返回根节点列表与汇总。"""
    tree = build_payment_tree(nodes)
    total_estimate = sum(r["total_estimate"] for r in tree)
    total_applied = sum(r["total_applied"] for r in tree)
    total_audited = sum(r["total_audited"] for r in tree)
    return {
        "tree": tree,
        "summary": {
            "total_estimate": round(total_estimate, 4),
            "total_applied": round(total_applied, 4),
            "total_audited": round(total_audited, 4),
        },
    }
