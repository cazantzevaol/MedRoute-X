# MedRoute X — six-minute judge demonstration

Rehearse on the packaged version with browser translation disabled. Run `run_demo.bat`, open the local dashboard and choose **Restore built-in example**. Use only synthetic data. Record the actual screen and outcomes; do not substitute expected results for failures.

**0:00–0:35 — Purpose and setup**

“MedRoute X tests how medicine supply proposals fail when institutions receive different information. This is a local research sandbox with invented inventories, demand and supplier messages. It neither contacts real suppliers nor executes transfers.” Briefly show the computer/software setup and local address.

**0:35–1:10 — Baseline proposal**

Show **Supply network**, unmet-demand metrics and **Independent safety gate**. “These are modeled packs, not patient outcomes. A technically valid proposal still requires human authorization.” Explain inventory reserves, travel time, temperature and capacity constraints. Read current values from the dashboard.

**1:10–2:10 — Private disruption and role value**

Click **Release next event →** once. The built-in supplier receives a private capacity reduction. Show the blocked operational check. Click **Run selected agents** in the main controls. Results reveal actual completed roles, notices and independent check status. Point to Supplier **Input → Finding → Next review action** and its formal-disclosure request; contrast the Coordinator's limited information and Auditor's independent check.

“The roles make information boundaries and responsibilities inspectable. They run deterministic local checks and exchange bounded notices. Running them does not change the plan or grant approval.”

**2:10–2:55 — Disclosure changes the plan**

Click **Release next event →** again. Explain that this event formally shares the update with the coordinator and triggers replanning. Show the new proposal, remaining shortage and operational result. Run the selected agents again and compare their inputs. “Disclosure changes the available facts; the human authorization boundary remains.” Do not claim the agents autonomously negotiated or purchased stock.

**2:55–3:40 — A useful next step**

In **Supply review**, show the proposed redistribution, any additional-supply requests, **Compare all three proposals**, and **Review tasks and evidence**. “Requests are unconfirmed suggestions for a responsible human, not available supplier stock.” Point to highlighted facility shortages. Download the **review packet**. Explain that **Useful proposal / Does not fit** stores bounded local preference feedback for equally effective valid options; it does not train a medical model or relax safety checks.

**3:40–4:20 — Editable scenario**

Click **Edit scenario**, change one invented stock value, and click **Calculate plan**. Compare the displayed input and resulting shortage. **Save as JSON** allows reuse through **Scenario file options → Load synthetic JSON**. Facility identifiers are numbered in this editor. For a longer demonstration, use **Test route disruption**, **Report disruption**, then **Confirm and share with coordinator** to repeat the disclosure experiment with custom inputs.

**4:20–5:10 — Evidence and evaluation**

Open **Agents, policy evidence and audit**. Show references, audit events and explicit unresolved review questions. “An international policy example is a comparison, not permission in the UAE. Missing material in our small knowledge base does not establish a legal gap.” Click **Run 30-case benchmark** and read the actual metrics. Distinguish total unmet packs from weighted unmet demand; do not claim superiority on a metric that ties. These seeded cases are separate from the edited scenario and do not establish clinical effectiveness.

**5:10–6:00 — Limits and reproducibility**

Download **evidence JSON** and show the packaged launch/test instructions. Explain that the national source coverage, expert policy review and generative-agent evaluation remain limited. The optional **AI briefing (local)** requires a separately installed local model; it is not part of this demonstrated deterministic council. On the preparation machine, Ollama was absent from PATH and its usual per-user install location on 9 November 2026; a successful local-model run has not been verified. Skip this button during the core demonstration unless a real installation has subsequently passed a rehearsal.

Close: “The contribution is a reproducible coordination experiment: expose who knows what, detect an unsafe proposal, demonstrate the effect of formal disclosure, and provide reviewable next steps without automated authorization.”

## Before recording

- Rehearse the complete sequence after a fresh extraction; record the exact release tested.
- Keep labels and narration in English and show readable text at normal zoom.
- Capture failures honestly; stop and fix unexpected behavior before recording a final take.
- Keep the video below seven minutes. Its first-round status and source are documented in [Submission checklist](SUBMISSION_CHECKLIST.md).
- No patient data, real supplier availability claims, paid API calls or automatic legal decisions.
