# Competition requirements traceability — ITU UAE Hackathon 2026
Last checked 27 Oct 2026. Source: https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/

**Do not invent official percentage weighting or a jury score.** “Implemented” refers to our offline simulated scope only.

| Published requirement | Evidence in v0.4 | Honest status | Mandatory next step |
|---|---|---|---|
| Country-specific, structured, retrievable knowledge base | `kb/sources.json`, `kb/claims.json`, metadata search, ingest module, 8-case summary retrieval benchmark | PARTIAL: 10 links/12 **high-level summaries**; no full verified legal texts | Import licensed/official full national material; verify section/page, effective date, jurisdiction, amendment; human review |
| Domain-specific AI application use case | Three-site shortage scenario, `optimizer.py`, safe independent gate, synthetic measurements | IMPLEMENTED in simulation | Define one specific product category with pharmacist review; avoid any clinical recommendation |
| Institutional agents with distinct mandates and uneven access | 10 role specs, `agents.observe`, `council.run_council`, typed restricted messages | OFFLINE STRUCTURAL DEMO; live generative role calls not verified | Validate authorized live calls with trace-scoped testing |
| Sequenced, chunked information / error events | `scenarios.flagship`: private Supplier alert and later Coordinator disclosure | IMPLEMENTED FOR ONE CASE ONLY | Add at least 4 structurally different scenarios with independent expected outcomes |
| Applied laws and institutional responsibilities | `policy.py` research questions, default-deny legal gate | PARTIAL: policy applicability NOT determined | Expert-check binding law and institutional mandates |
| Cross-national best practices and sectoral policy gaps | WHO + EMA EU/EEA comparator; `policy_matrix` distinguishes evidence gap from legal gap | PARTIAL: research questions, **zero confirmed gaps** | Compare two jurisdictions with precise jurisdictional differences, independently review hypotheses |
| Auditability: observations, outcomes, sources | Hashed audit, bounded role traces, source IDs, receipt verifier | IMPLEMENTED FOR STRUCTURAL DEMO | Per-section excerpt citations; replay tests, signed evidence or trusted storage for authenticity |
| Y.3172 pipeline / MLFO / ML sandbox mapping | `reports/LLM_AGENT_ARCHITECTURE_SPRINT1.md` + architectural correspondence | DOCUMENTED ANALOGY, not compliance certification | Add interface-level implementation tests and a figure in the formal report |
| AI Readiness 2.0 | Data, infrastructure, skills, ecosystem, policy analysis in existing docs | TEXTUAL MAPPING | Use measured constraints and stakeholder interview/review |
| Five-page report | Historical v0.3 `reports/technical_report.pdf` | DRAFT, not final | Update report to organizer template + attach evaluated v0.4 facts and team details |
| GitHub repo + KB | Local source and ZIP | NOT PUBLISHED | User/team to publish with appropriate code/attribution/license decisions |
| Demo video <=7 min | `reports/demo_script_en.md` | SCRIPT ONLY | Record reproducible steps with both failure and recovery and clearly marked synthetic data |
| 10 Nov deadline | Organizer timeline | CONFIRMED AS OF 27 OCT | Submit before deadline (registration status confirmed separately by participant) |

**Priority ranking for actual jury alignment:** (1) full national KB + applicable law extraction, (2) technically real/institutional agent evaluations, (3) verified sectoral policy gaps with international examples, (4) auditable interactions. This ranking is a development judgment, NOT disclosed jury weights.

**Official notes:** Organizers say prototype accuracy is not a stand-alone scoring criterion; the sectoral policy/standards gap analysis and *relevance/accuracy of global examples* are especially important. They expect progressive disclosure of incomplete facts. Success on synthetic logistics allocation alone does not satisfy the policy mission.
