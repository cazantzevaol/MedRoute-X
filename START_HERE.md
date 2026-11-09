# MedRoute X — Judge quick start

1. Extract the ZIP. On Windows, double-click **run_demo.bat**. Python 3.10 or later is required. The first setup needs internet access to install SciPy. On macOS or Linux, install the dependencies with `python -m pip install -r requirements.txt` and run `python -m medroute.server`.
2. Open http://127.0.0.1:8765/ if the browser does not open automatically. Keep the server window open.
3. Click **Release next event**. The independent operational check blocks the stale plan after a route capacity loss. Click it again to share the update with the coordinator and recalculate.
4. Click **Run selected agents**. Results open automatically and show each role's inputs, numerical findings and next review action. Transfer authorization requires human review.
5. To try your own synthetic values, click **Edit scenario**, change the inputs and click **Calculate plan**. Use **Save as JSON** and **Load synthetic JSON** to reuse values later. Use **Restore built-in example** to return to the event sequence.

The demo runs locally with synthetic data. The competition materials are in [the technical report](reports/technical_report.pdf), [the knowledge base](kb/) and [the demo script](reports/demo_script_en.md). See the [README](README.md) for test and agent-review commands.

## Live disruption in a custom scenario

Click **Edit scenario → Calculate plan**, then choose a route and a lower capacity in **Test a route disruption**. Use **Report disruption** to send a supplier-only update. The independent check may block the existing plan. Click **Confirm and share with coordinator** to disclose the update and recalculate. This confirmation is a simulated information handoff. Transfer authorization remains with qualified humans.

## Optional local AI briefing

Run Ollama with a local model already installed. In PowerShell, set
`$env:MEDROUTE_LOCAL_MODEL = 'your-local-model-tag'`, then run
`.\run_demo.bat`. Click **AI briefing (local)** to prioritize one verified
scenario fact. The model receives only a short summary of synthetic facts and
returns an allowed category. The dashboard uses its own factual wording.
Use a local-only Ollama setup. The AI briefing leaves routing checks and human
authorization in place.

## Enable agent checks

Select roles using the checkboxes on their cards, then click **Run selected agents**.
Enable **Run after scenario changes** to rerun selected checks when this page updates the scenario.
Clear the toggle to stop automatic runs. Completed dialogue appears below the cards.
These checks use the offline protocol provider. **AI briefing (local)** requires a configured local model.

Hospital identifies facility shortages; Inventory measures donor stock above reserves;
Demand estimates horizon requirements; Logistics checks route constraints; Equity compares
unmet-demand shares. Coordinator requests missing disclosures, while Auditor reports the
independent operational result. Running these checks does not change the plan. Formal
disclosure of updated route facts to the coordinator triggers replanning.

These are deterministic role checks, not ten autonomous language models. There is no
live supplier connection in this release. Supplier events are synthetic demonstrations.

## Current verification

See `reports/verification_current.json` for the latest executable checks and limitations.
The five-page technical PDF and submission checklist describe this release and
the remaining owner actions before publication and submission.

## Supply review

The **Supply review** panel compares three proposals using the same coordinator-visible
facts. Operational validation checks each against the actual synthetic conditions.
A blocked option remains visible so reviewers can see why its shortfall estimate
cannot be relied on for execution. The next-action card identifies the responsible
role and unresolved task. **Download review packet** exports the comparison,
tasks, policy questions and evidence for human review. Agent details are in the
expandable **Agents, policy evidence and audit** section.

## Proposal feedback

**Useful proposal** and **Does not fit** save a local preference for the current
scenario conditions. Feedback breaks ties only between operationally valid
options with the same modeled shortfall and weighted shortfall. It does not train
a language model or confirm real-world outcomes. Preferences persist in
`runtime/review_preferences.sqlite3` on this computer and are excluded from the release ZIP.

## Add more facilities

Open **Edit scenario**, then click **+ Add facility**. Enter synthetic stock, daily
 demand, reserve days and priority. Up to 20 facilities are supported. New facilities
start with zero stock and demand; replace these values for your scenario.

Use **+ Add route**, choose different **From facility** and **To facility**, and
set capacity and travel days. Up to 60 routes are supported. A new route starts
with zero capacity and requires human review. Routes are directed: add a separate
route for the reverse direction if needed. Click **Calculate plan** to apply the
network, or **Save as JSON** to save it. An unconnected facility still contributes
to demand and shortage calculations. Agent details are expanded by default.

Human authorization means qualified approval outside this prototype. **Confirm and
share with coordinator** only discloses synthetic data; it does not authorize a transfer.

## Remove and rearrange facilities

Use **Remove facility** inside its editor card. A confirmation lists connected routes
that will also be removed. At least one facility must remain. **Remove route** removes
only that route. **Move up / Move down** reorder facility cards while preserving their
identifiers and route connections. These changes affect the draft; click **Calculate
plan** to apply them, or **Save as JSON** to export the edited draft.

## Inspect source references

After running agents, expand **Source-reference checks**. Inspect the linked source,
curated statement, jurisdiction and applicability status. Reference allowlisting and
hash integrity are automatic checks; semantic support and legal applicability remain
unverified. Open the source and compare its actual text against the finding. Synthetic
inventory numbers originate from scenario inputs, not policy documents.
