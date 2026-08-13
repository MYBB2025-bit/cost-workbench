"""领域逻辑单测（纯函数，无需数据库）。"""
from service.payment_service import compute_payment_stats
from service.pricing_service import calc_total


class _Node:
    def __init__(self, id, parent_id, name, estimate=0, applied=0, audited=0, status=None):
        self.id = id
        self.parent_id = parent_id
        self.name = name
        self.estimate = estimate
        self.applied = applied
        self.audited = audited
        self.status = status


def test_calc_total_basic():
    assert calc_total(10, 5) == 50
    assert calc_total(0, 100) == 0
    assert calc_total(None, 3) == 0


def test_payment_stats_parent_plus_children():
    """修复 bug②：父节点自带值 + 子节点汇总，二者相加而非互斥。"""
    nodes = [
        _Node(1, None, "总包", estimate=100),      # 本级 100
        _Node(2, 1, "子项A", estimate=30),         # 子 30
        _Node(3, 1, "子项B", estimate=20),         # 子 20
    ]
    res = compute_payment_stats(nodes)
    root = res["tree"][0]
    # 父 total = 100 + 30 + 20 = 150（旧逻辑会漏算子节点，得 100）
    assert root["own_estimate"] == 100
    assert root["total_estimate"] == 150
    assert res["summary"]["total_estimate"] == 150


def test_payment_stats_deep_nesting():
    nodes = [
        _Node(1, None, "L1", estimate=10),
        _Node(2, 1, "L2", estimate=5),
        _Node(3, 2, "L3", estimate=2),
    ]
    res = compute_payment_stats(nodes)
    assert res["summary"]["total_estimate"] == 17  # 10+5+2


def test_payment_stats_empty():
    res = compute_payment_stats([])
    assert res["tree"] == []
    assert res["summary"]["total_estimate"] == 0
