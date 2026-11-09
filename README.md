# MedRoute X

A local, synthetic medicine-continuity sandbox for the ITU AI for Good Lab Hackathon UAE 2026.

**Start here:** [Judge quick start](START_HERE.md). **Submission materials:** [checklist](reports/SUBMISSION_CHECKLIST.md), [technical report](reports/technical_report.pdf), [demo script](reports/demo_script_en.md).

## Run

Requires Python 3.10+. On Windows, double-click `run_demo.bat`. The launcher creates a local virtual environment and installs SciPy if needed; first setup requires internet access. It opens http://127.0.0.1:8765/. Keep the server running during the demonstration.

Manual setup on any supported platform:

```sh
python -m pip install -r requirements.txt
python -m medroute.server
```

## What the demonstration proves

A coordinator initially proposes transfers using disclosed inventory, demand and route facts. A synthetic supplier event changes a route before the coordinator receives that update. An independent operational checker blocks the stale plan. Formal disclosure triggers recalculation. Operational validity never grants legal permission.

Ten selectable roles report scoped inputs, numerical findings and next review actions. The default council is deterministic. Optional local Ollama briefing prioritizes a verified fact; it is not required for the demo. No live supplier is connected, and no paid model is called by default.

The dashboard supports a numeric scenario editor, strict synthetic JSON import/export, custom route disruptions, comparison of three proposals, additional supply requests and evidence export. Local reviewer preferences only break ties between equally effective valid proposals. They do not train a language model.

## Verify

```sh
python -m pytest -q
node --check web/app.js
node tests/test_ui_regressions.cjs
python scripts/submission_gate.py --expected-tests 376 --expected-sources 14 --expected-claims 18
python scripts/agent_review.py --cases 30
```

Node.js is needed only for JavaScript checks. Current results and limitations are in [verification_current.json](reports/verification_current.json). The submission gate checks local artifacts; it cannot confirm registration, repository access or legal approval.

## Project layout

- `medroute/`: optimizer, scenario state, scoped roles, independent checks, evidence and loopback server.
- `web/`: English dashboard.
- `kb/`: policy source pointers, claims and review status.
- `tests/` and `benchmarks/`: regression checks and synthetic evaluation fixtures.
- `reports/`: judge materials, architecture and reproducible evidence.
- `scripts/`: launcher, evaluation, artifact generation and local preflight tools.

Source references are evidence pointers, not verified legal advice. Missing material is an evidence gap, not proof that no law applies. All movements require qualified human review. Use synthetic data only; the importer rejects free-text patient records.

## Packaging and local data

`SHA256SUMS.txt` records release file hashes. The release ZIP excludes `.venv`, caches and `runtime/`. Local feedback, if used, stays in `runtime/review_preferences.sqlite3`. Historical development materials are outside this project in the workspace Archive and are not part of the judge package.

Nothing is published or submitted by the launcher or local preflight commands.
