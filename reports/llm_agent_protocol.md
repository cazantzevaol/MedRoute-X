# MedRoute X v0.3 — inter-agent protocol and safe LLM mode

## What is actually implemented

- `medroute.council` executes **ten role-specific assessment calls**, with a structured handoff from each specialist to Coordinator and independent Auditor. Roles have separate mandate and observation fields; only Supplier sees a new supplier report prior to formal disclosure. A typed handoff can request disclosure, but it **does not include the private capacity figure**.
- Offline mode uses **scripted deterministic assessments**. It is useful for unit tests and demos, but is NOT ten generative agents.
- Opt-in `OpenAIProvider` makes **live external model API calls** (normally one per role). It can produce separate role assessments, with evidence retrieval scoped to the role. **The API has not been live validated by the authoring assistant, no key is provided, and generated statements are untrusted until reviewed.**
- The only data sent to external API in the intended demonstration: simulated inventory, publicly sourced policy summaries and constrained protocol messages. Never add real patients, protected stock/contract details or secrets.
- Every generated citation ID is checked against retrieved, documented claim IDs, but semantic support/entailment is **not verified** by that mechanical check.
- Inbound model prose is **not forwarded** to another agent to reduce prompt-injection propagation. Instead, the protocol sends allowlisted fields (`from`, `intent`, `legal_clearance=false`, `evidence_ids`, `has_private_information`, `content_policy`).
- The mathematical inventory optimizer, independent operational check and conservative authorization gate are **outside the LLM provider**; even a malicious model cannot grant a transfer by setting a JSON flag.

## Run (offline)

```bash
python -m medroute council
python -m medroute.council --provider offline --step 1 --output reports/council_step1_offline.json
python -m medroute.council --provider offline --step 2 --output reports/council_step2_offline.json
```

## Run real model calls only if YOU explicitly choose to

Set the API key in your own local environment, never in code or a GitHub commit:

```bash
export OPENAI_API_KEY='your-key-set-locally'
export OPENAI_MODEL='gpt-4.1-mini'       # Example only: verify model availability in your account
python -m medroute.council --provider openai --step 1 --roles Supplier Regulator Coordinator Auditor
```

This test costs tokens and uses an external model provider. First review payload and data-handling rules. No live requests are executed by offline tests or the web demo. API errors, usage limits or model availability can still prevent a live run.

## Threat model / acceptance checks

1. **Asymmetric facts:** Supplier can see a route update before Coordinator; Coordinator must not infer the numeric change until formal disclosure.
2. **Prompt injection:** arbitrary model-generated summaries are not copied into another agent's context; inputs from retrieved materials are clearly marked non-instructional.
3. **Invented legal claims:** unknown citation IDs are removed, but semantically incorrect use of real IDs needs expert review.
4. **Malicious approvals:** any model-provided permission flag is ignored. Regulated movements remain non-executable, requiring real institutional approvals.
5. **Audit integrity:** every role assessment contains input SHA-256 and structured receipt; hash chaining detects subsequent modification of stored logs (but is not digital signing).
6. **No patient data:** all cases use synthetic sites/demand/stock; no substitution, diagnosis or treatment recommendations.

## What to verify before entering the final round

- Test live API calls in a private isolated sandbox; manually inspect all ten role outputs on 3+ varying scenarios.
- Obtain informed written review from a UAE licensed pharmacist / competent regulatory professional and an appropriately qualified legal/privacy specialist.
- Convert source-page summaries to a versioned, properly licensed, permissioned, **full national text corpus** with exact section-level citations and historical update checks.
- Benchmark policy applicability and retrieval against manually labeled ground truth, including false positives/negatives and cases where no evidence supports a recommendation.
