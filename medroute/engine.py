"""Stepwise exercise with asymmetric information and an independent safety gate."""
from copy import copy, deepcopy
from uuid import uuid4
from .scenarios import flagship
from .optimizer import optimize, validate_operational
from .agents import findings
from .audit import append as audit_append, verify as verify_audit
from .knowledge import search_claims, catalog
from .policy import policy_matrix
from .disclosure import public_report, pending_private_supplier_reports


class DisruptionError(ValueError):
    """Invalid operation in the synthetic disclosure workflow."""


class Sandbox:
    def __init__(self, scenario=None):
        self.reset(scenario or flagship())

    def reset(self, scenario=None):
        staged = copy(self)
        staged._reset(scenario)
        return self._commit(staged)

    def _commit(self, staged):
        snapshot = staged.state()
        self.__dict__.update(vars(staged))
        return snapshot

    def _reset(self, scenario):
        self.base = deepcopy(scenario or self.base)
        if self.base['id'] == 'CUSTOM':
            self.base['events'] = []
        self.world = deepcopy(self.base)  # Actual test conditions (scorer only)
        self.known = deepcopy(self.base)  # Validated facts coordinator knows
        self.step_number = 0
        self.reports = []
        self.audit = []
        self._record("START", "Scenario loaded; no medicine transferred.")
        self._snapshot = self._compute_state()

    def _record(self, kind, detail):
        audit_append(self.audit, self.step_number, kind, detail)

    def advance(self):
        if self.step_number >= len(self.base["events"]):
            return self.state()
        # Compute against a private candidate so failures leave the event retryable.
        staged = copy(self)
        staged.world = deepcopy(self.world)
        staged.known = deepcopy(self.known)
        staged.reports = self.reports.copy()
        staged.audit = self.audit.copy()
        staged._advance()
        return self._commit(staged)

    def _pending_disruption(self):
        if self.base['id'] == 'CUSTOM' and self.reports:
            return self.reports[-1].get('change')
        return None

    def report_disruption(self, route_id, capacity):
        if self.base['id'] != 'CUSTOM':
            raise DisruptionError('Load a custom scenario first.')
        if self._pending_disruption():
            raise DisruptionError('Confirm the pending disruption before reporting another.')
        if self.step_number >= 40:
            raise DisruptionError('Reset the scenario before reporting more disruptions.')
        route = next((item for item in self.world['routes'] if item['id'] == route_id), None)
        if route is None or type(capacity) is not int or not 0 <= capacity < route['capacity']:
            raise DisruptionError('Choose a route and enter an integer below its current capacity.')
        return self._append_event({
            'change': {'route_id': route_id, 'capacity': capacity},
            'disruption_id': uuid4().hex,
            'visible_to': ['Supplier'],
            'message': 'Supplier reports a capacity reduction.',
        })

    def confirm_disruption(self, disruption_id):
        pending = self._pending_disruption()
        if not pending:
            raise DisruptionError('No disruption is awaiting confirmation.')
        if disruption_id != self.base['events'][self.step_number - 1]['disruption_id']:
            raise DisruptionError('The pending report changed. Refresh the scenario and review it again.')
        return self._append_event({
            'reveal': [pending['route_id']],
            'visible_to': ['Coordinator', 'Logistics', 'Auditor'],
            'message': 'Demo operator confirmed and shared the route update.',
        })

    def _append_event(self, event):
        staged = copy(self)
        staged.base = {**self.base, 'events': [*self.base['events'], event]}
        staged.advance()
        return self._commit(staged)

    def _advance(self):
        self.step_number += 1
        event = self.base["events"][self.step_number-1]
        if event.get("change"):
            change = event["change"]
            for route in self.world["routes"]:
                if route["id"] == change["route_id"]:
                    route["capacity"] = change["capacity"]
        self.reports.append({"step": self.step_number, "visible_to": event["visible_to"],
                             "change": event.get("change"), "message": event["message"],
                             "revealed_routes": list(event.get("reveal", []))})
        # Only update coordinator facts when a formally disclosed route change arrives.
        for route_id in event.get("reveal", []):
            actual = next(r for r in self.world["routes"] if r["id"] == route_id)
            current = next(r for r in self.known["routes"] if r["id"] == route_id)
            current.update(actual)
        self._record("INFORMATION_EVENT",
                     "Formal institutional disclosure (details withheld)." if
                     "Coordinator" in event["visible_to"] else
                     "Restricted institutional event (details withheld).")
        self._record("INFORMATION_RECIPIENTS", ", ".join(event["visible_to"]))
        if self.base['id'] == 'CUSTOM' and event.get('reveal'):
            route_id = event['reveal'][0]
            capacity = next(route['capacity'] for route in self.known['routes']
                            if route['id'] == route_id)
            self._record('DEMO_OPERATOR_CONFIRMATION', f'{route_id}: capacity {capacity} packs shared.')
        self._snapshot = self._compute_state()

    def _compute_state(self):
        proposed = optimize(self.known)
        operational = validate_operational(self.world, proposed)
        category = self.base.get('product_category', 'unspecified')
        emergency = self.base.get('emergency_declared', False)
        report = findings(self.known, proposed, self.reports, self.step_number, category, emergency)
        gate = report["legal_gate"]
        if not operational["passes"]:
            status = "BLOCKED_OPERATIONAL"
        elif gate["status"] == "HUMAN_REVIEW_REQUIRED":
            status = "PENDING_AUTHORIZATION"
        else:
            status = "NO_ACTION"
        # The audit records rationales and input references rather than private hidden CoT.
        self._record('PLAN_PROPOSAL',
                     f'candidate transfers={len(proposed["transfers"])}; units={proposed["baseline_unmet"]-proposed["unmet_total"]}; '
                     f'weighted unmet={proposed["priority_weighted_unmet"]}')
        for item in report['messages']:
            self._record('AGENT_ASSESSMENT',
                         f'{item["agent"]}: {item["summary"][:260]} | claims={",".join(item["references"])}')
        self._record('INDEPENDENT_OPERATIONAL_CHECK',
                     f'passes={operational["passes"]}; issues={operational["issues"]}')
        self._record('LEGAL_GATE', f'status={gate["status"]}; no autonomous permissions')
        matrix = policy_matrix(proposed, self.reports, self.step_number, category, emergency)
        self._record('POLICY_QUESTIONS',
                     f'expert-review questions={matrix["questions_requiring_expert_review"]}; confirmed legal gaps=0')
        return {"scenario": {"id": self.base["id"], "title": self.base["title"],
                             "product": self.base["product"], "product_category": category, "emergency_declared": emergency, "sites": self.base["sites"],
                             "routes_known": self.known["routes"],
                             "horizon_days": self.known["horizon_days"],
                             "note": self.base["notes"]},
                "step": self.step_number, "steps_total": len(self.base["events"]),
                "disruption_pending": self._pending_disruption() is not None,
                "pending_supplier_disclosure": bool(pending_private_supplier_reports(self.reports)),
                "disruption_id": (self.base['events'][self.step_number - 1]['disruption_id']
                                  if self._pending_disruption() else None),
                "event": None if self.step_number == 0 else (
                    "Formal institutional disclosure" if
                    "Coordinator" in self.base["events"][self.step_number-1]["visible_to"] else
                    "Restricted institutional event"),
                "plan": proposed, "operational_check": operational, "legal_check": gate,
                "release_status": status, "agents": report["messages"],
                "policy_gap_hypothesis": report["gap_hypothesis"],
                "policy_matrix": matrix,
                "audit": list(self.audit), "audit_verification": verify_audit(self.audit),
                "evidence": search_claims("UAE essential medicines supply policy shortage authorization international", limit=6),
                "knowledge_source_count": len(catalog()),
                "reports": [public_report(r) for r in self.reports],
                "no_patient_data": True, "simulation_only": True,
                "implementation_mode": "deterministic_role_prototypes_no_llm"}

    def state(self):
        """Pure read; repeated dashboard refreshes never change the audit chain."""
        return deepcopy(self._snapshot)
