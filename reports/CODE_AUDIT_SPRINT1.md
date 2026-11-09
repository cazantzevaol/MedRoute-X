# Independent code audit — MedRoute X 0.3 → 0.4
Date: 27 October 2026. Scope: source code in `medroute/`, CLI, the local demo server, tests and documented API behavior. This is a code review and controlled test suite, **not** a licensed healthcare, penetration or legal audit.

## Findings and executed remediation

| Priority | Source / issue in 0.3 | Risk | Remediation in 0.4 | Evidence |
|---|---|---|---|---|
| HIGH | `llm_json_request` read `OPENAI_API_URL` without destination validation | A misconfigured environment could send an API credential to an arbitrary host | `authorized_endpoint` now defaults to exact official HTTPS path; any custom HTTPS endpoint needs explicit `MEDROUTE_ALLOW_CUSTOM_API_ENDPOINT=I_ACCEPT_RISK`; automatic HTTP redirects blocked | `tests/test_sprint1_security.py` malicious host and redirect tests |
| HIGH | Council audit anchored the role *request* but not the role *output* | Edited exported role summaries/citations might leave the original hash-chain verification green | Every trace record has `record_sha256`, included in chained audit event; `verify_council_artifact` recomputes it and checks handoff consistency | Trace alteration, citation and handoff tampering tests |
| MEDIUM | LLM result accepted nonstring summary converted into text and free-shaped question values | Unpredictable output type or excessive content may be misrepresented as expert recommendation | Strict summary and question type/size requirements, citation allowlist and permanently false autonomous approval flag | Invalid-output tests, adversarial provider test |
| MEDIUM | API response decoded with no explicit maximum | Oversized remote response could consume excessive process memory | 256 KiB bound, response shape validation, 30-second request timeout | Size-bound and mocked transport tests |
| MEDIUM | Local `POST` accepted arbitrary Origin and negative `Content-Length` | Browser origin interference and invalid request handling | Reject cross-origin state changes; reject invalid/negative length | Source review (not a real-browser security audit) |
| LOW | Audit `verify` raised on malformed entries | A corrupted saved log could crash verification | Invalid log returns `{valid:false}` | Malformed log test |
| EVIDENCE GAP | 0.3 retrieval had no fixed gold-query regression | Cannot meaningfully report even narrow query retrieval reproducibility | Added **8 editorially labeled** source-summary queries and executable Hit@1/MRR@3 evaluator | `benchmarks/policy_retrieval_gold.json`, `medroute/retrieval_eval.py` |

## Results

- Baseline from unchanged v0.3: **45 tests passed**.
- Current v0.4 offline suite: **68 tests passed**. Tests include mock LLM responses, not a live API integration.
- Three state transitions verified; 10 offline role assessments per state; independent check blocks undisclosed reduced capacity before authorized disclosure; no agent has an execution permission.
- Source-summary retrieval **Hit@1 = 8/8** for the deliberately small, close-to-source test set. **This is not a legal KB accuracy score**. Full statutes are absent.

## Residual risks (must not claim solved)

1. A person who can rewrite both an artifact and its hash-chain can recompute the hashes: this is *tamper-evidence within one saved artifact*, not a cryptographically signed authenticity service.
2. A real LLM could cite an existing claim while misinterpreting it: claim-ID validation is not semantic entailment. Bindings/amendments must be validated independently.
3. LLM live calls and any customer-specific data-handling are **not tested**. Real clinical or inventory systems are explicitly out of scope.
4. Current role messages are scripted in offline mode; no outcome advantage of 10 independent language models has been demonstrated.
5. Initial official report `reports/technical_report.pdf` remains a historical v0.3 draft. The changes in this audit must be folded into a submission-specific 5-page report.

## How to reproduce

```bash
python -m pytest -q
PYTHONPATH=. python scripts/sprint1_acceptance.py
python -m medroute.retrieval_eval
python -m medroute.council --provider offline --step 1 --output reports/council_step1_v04.json
```
