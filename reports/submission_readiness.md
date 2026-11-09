# MedRoute X — local pre-submission status (01 November 2026, v0.10)

The official ITU UAE 2026 hackathon lists a **10 November 2026** submission deadline and requires a technical report **no longer than 5 pages**, a GitHub repository and a policy/strategy/regulation knowledge base. An optional video (max 7 minutes) becomes required if shortlisted. The event page shows **registration until 5 November 2026** in its main text; search previews may show a conflicting `Applications closed` badge. The specific team's eligibility is **unverified**.

| Requirement | Status | Evidence |
|---|---|---|
| Five-page report | **LOCAL PASS, DRAFT** | `reports/technical_report.pdf` rebuilt for v0.10; five pages inspected with `pypdf` and rendered visually |
| ITU-T Y.3172 / AI Readiness mapping | **LOCAL PASS, NON-CERTIFIED** | Report pp. 2-3 and existing architecture documentation |
| Policy and standards gap hypotheses | **DOCUMENTED, NOT VALIDATED** | Report p. 5; no claim of proven UAE legal gap |
| National KB | **PARTIAL** | 13 source pointers / 17 claims; metadata and English excerpts, not full binding corpus |
| Offline simulation | **LOCAL PASS** | 172/172 tests; 30-case protocol acceptance; no autonomous permits |
| Real LLM agent performance | **NOT TESTED** | Offline scripted roles are not independent LLMs |
| Local artifact gate | **PASS** | `reports/sprint6_submission_gate.json`; only structural checks |
| Registration / team identity | **UNVERIFIED** | Must be confirmed by entrant; deadline shown as 5 November |
| GitHub accessible to judges | **UNVERIFIED / NOT PUBLISHED** | No code publication was authorized |
| Organizer submission | **NOT SUBMITTED** | No submission was authorized |
| Expert UAE legal and pharmacy review | **NOT PERFORMED** | Arabic original and applicability require specialists |

**Important:** `submission_ready=false` even if `local_preflight_passed=true`. The local gate is not a legal review, source authentication service, registration check, or submission action.

Reproduce locally: `python -m pytest -q && python scripts/submission_gate.py --version 0.10`.
