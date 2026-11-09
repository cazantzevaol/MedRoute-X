"""Fully synthetic scenarios. Units are anonymized packs, not patients or doses."""
from copy import deepcopy
from random import Random


def flagship():
    return {
        "id": "CASE-001", "title": "Three facilities, one essential product",
        "product": "Synthetic essential medicine X (NOT a real product)",
        "product_category": "unspecified",
        "emergency_declared": False,
        "horizon_days": 5,
        "sites": [
            {"id": "Hospital A", "stock": 18, "daily_demand": 15, "reserve_days": 2, "priority": 4},
            {"id": "Hospital B", "stock": 150, "daily_demand": 12, "reserve_days": 5, "priority": 2},
            {"id": "Hospital C", "stock": 35, "daily_demand": 10, "reserve_days": 2, "priority": 3},
        ],
        "routes": [
            {"id": "B-A", "from": "Hospital B", "to": "Hospital A", "capacity": 70,
             "days": 1, "temperature_ok": True, "requires_approval": True},
            {"id": "B-C", "from": "Hospital B", "to": "Hospital C", "capacity": 25,
             "days": 1, "temperature_ok": True, "requires_approval": True},
            {"id": "C-A", "from": "Hospital C", "to": "Hospital A", "capacity": 12,
             "days": 2, "temperature_ok": True, "requires_approval": True},
        ],
        "events": [
            {"step": 1, "title": "A supplier reports reduced transport capacity",
             "change": {"route_id": "B-A", "capacity": 15},
             "visible_to": ["Supplier"],
             "message": "Route B-A capacity drops from 70 to 15. Only Supplier knows initially."},
            {"step": 2, "title": "Supplier information is shared across institutions",
             "change": None, "reveal": ["B-A"],
             "visible_to": ["Coordinator", "Logistics", "Auditor"],
             "message": "Coordinator receives verified route capacity and replans."},
        ],
        "notes": "Synthetic warehouses, transport capacities, and demand. No medical recommendations."
    }


def benchmark_scenarios(count=30, seed=2026):
    """Reproducible challenge set. Seed and generator are publicly inspectable."""
    rng = Random(seed)
    out = []
    for i in range(count):
        case = deepcopy(flagship())
        case["id"] = f"TEST-{i+1:03d}"
        case["title"] = f"Synthetic shortage case {i+1:03d}"
        for site in case["sites"]:
            site["stock"] = max(3, site["stock"] + rng.randint(-20, 20))
            site["daily_demand"] = max(2, site["daily_demand"] + rng.randint(-3, 3))
            # Synthetic, scenario-specific urgency ratings (NOT patient triage).
            site["priority"] = rng.randint(1, 5)
        # Generate both ample-supply and constrained-supply situations.
        case["sites"][1]["stock"] = rng.randint(75, 155)
        case["routes"][0]["capacity"] = rng.randint(20, 90)
        case["routes"][1]["capacity"] = rng.randint(15, 80)
        case["routes"][2]["capacity"] = rng.randint(0, 20)
        case["routes"][rng.randrange(3)]["temperature_ok"] = rng.random() > 0.12
        case["events"][0]["change"]["capacity"] = rng.randint(6, 65)
        out.append(case)
    return out


def multi_alert_disclosure():
    """Synthetic regression/demo: disclosure of one route cannot clear another alert."""
    case = deepcopy(flagship())
    case['id'] = 'CASE-002'
    case['title'] = 'Independent route alerts with separate formal disclosures'
    case['events'] = [
        {'title': 'Private B-A update', 'change': {'route_id': 'B-A', 'capacity': 15},
         'visible_to': ['Supplier'], 'message': 'Restricted B-A supplier alert'},
        {'title': 'B-A formally disclosed', 'reveal': ['B-A'],
         'visible_to': ['Coordinator', 'Auditor'], 'message': 'Formal B-A disclosure'},
        {'title': 'New private B-C update', 'change': {'route_id': 'B-C', 'capacity': 8},
         'visible_to': ['Supplier'], 'message': 'Restricted B-C supplier alert'},
        {'title': 'B-C formally disclosed', 'reveal': ['B-C'],
         'visible_to': ['Coordinator', 'Auditor'], 'message': 'Formal B-C disclosure'},
    ]
    return case


def controlled_emergency():
    """Synthetic category-only test of EDE emergency approval routing.

    Contains no named drug, patient, prescription or medical report. It does not
    model eligibility, clinical urgency or an actual application to the EDE.
    """
    case = deepcopy(flagship())
    case['id'] = 'CASE-003'
    case['title'] = 'Synthetic controlled-category emergency workflow review'
    case['product'] = 'Synthetic controlled-category product Z (NOT a real drug)'
    case['product_category'] = 'controlled_or_psychotropic'
    case['emergency_declared'] = True
    case['notes'] = 'Synthetic packs and fictional institutions; no patient data or approvals.'
    return case
