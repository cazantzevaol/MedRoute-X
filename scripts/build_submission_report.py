"""Rebuild the 2026-11-09 ITU submission draft (exactly five pages, no network).

Run from repo root: python scripts/build_submission_report.py
Authoring dependency: reportlab. This is a *draft*, not a submitted application.
"""
from __future__ import annotations
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'technical_report.pdf'
benchmark = json.loads((ROOT / 'reports' / 'benchmark_summary.json').read_text(encoding='utf-8'))
NAVY = colors.HexColor('#13263C')
TEAL = colors.HexColor('#087C85')
PALE = colors.HexColor('#EDF5F6')
INK = colors.HexColor('#29384A')
GREY = colors.HexColor('#657587')
WHITE = colors.white
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='MRKicker', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=TEAL, spaceAfter=9))
styles.add(ParagraphStyle(name='MRHero', fontName='Helvetica-Bold', fontSize=22, leading=27, textColor=NAVY, spaceAfter=8))
styles.add(ParagraphStyle(name='MRSub', fontName='Helvetica', fontSize=11, leading=15, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name='MRH', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=NAVY, spaceAfter=9))
styles.add(ParagraphStyle(name='MRH2', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=TEAL, spaceBefore=9, spaceAfter=5))
styles.add(ParagraphStyle(name='MRP', fontName='Helvetica', fontSize=9.0, leading=13, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name='MRSmall', fontName='Helvetica', fontSize=7.8, leading=11, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name='MRNote', fontName='Helvetica-Oblique', fontSize=8.2, leading=11.5, textColor=GREY, spaceAfter=8))
styles.add(ParagraphStyle(name='MRCell', fontName='Helvetica', fontSize=8.0, leading=11, textColor=INK))
styles.add(ParagraphStyle(name='MRHead', fontName='Helvetica-Bold', fontSize=8.0, leading=11, textColor=WHITE))


def p(t, kind='MRP'):
    return Paragraph(t, styles[kind])


def heading(title):
    return p(title, 'MRH2')


def table(headers, rows, widths):
    data = [[p(str(v), 'MRHead') for v in headers]] + [[p(str(v), 'MRCell') for v in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, PALE]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, -1), (-1, -1), .5, colors.HexColor('#CFDEE2')),
    ]))
    return t


def box(text):
    t = Table([[p(text, 'MRP')]], colWidths=[502])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PALE),
        ('BOX', (0, 0), (-1, -1), .6, colors.HexColor('#C7DDE0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def page(c, doc):
    c.saveState()
    w, h = A4
    c.setStrokeColor(colors.HexColor('#D8E5E8'))
    c.line(45, h - 43, w - 45, h - 43)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(TEAL)
    c.drawString(45, h - 34, 'MEDROUTE X  /  UAE AI FOR GOOD LAB  /  v0.10')
    c.setFont('Helvetica', 7.5)
    c.setFillColor(GREY)
    c.drawString(45, 30, 'Synthetic-only research  |  Not a clinical or regulatory authorization  |  09 Nov 2026')
    c.drawRightString(w - 45, 30, f'{doc.page} / 5')
    c.restoreState()

story = []
# Page 1: problem, scope, why this prototype exists.
story += [Spacer(1, 13), p('TECHNICAL REPORT  /  ITU UAE HACKATHON 2026', 'MRKicker'),
          p('MedRoute X', 'MRHero'),
          p('Evidence-grounded multi-agent coordination for synthetic medicine continuity', 'MRSub'),
          box('<b>Release:</b> v0.10.0 (09 November 2026). <b>Submission:</b> draft only; team registration, identity and GitHub URL must be completed by the entrant. <b>System:</b> offline deterministic ten-role prototype; optional live LLM adapter has NOT been evaluated.'),
          heading('1. Problem statement and intended use'),
          p('Shortages can create a coordination problem between healthcare facilities, stock holders, suppliers, logistics and regulators. Actors may receive conflicting or delayed information. MedRoute X studies whether bounded role-specific information, progressive disclosure, independent operational validation and source-linked policy context can improve <b>synthetic</b> decision processes.'),
          p('The prototype does <b>not</b> manage real inventory, process patient records, select treatment, authorize controlled-medicine movement, or implement UAE regulator decisions. Candidate transfers are simulations and always remain pending human authority.'),
          heading('2. Evaluation scenario: sequential incomplete information'),
          table(['Step', 'Information released', 'Expected observable outcome'], [
              ('0', 'Hospital A has simulated unmet demand; Hospital B has simulated surplus.', 'Optimizer proposes candidates; independent validation; no legal approval.'),
              ('1', 'Supplier privately receives a reduced route-capacity update.', 'Coordinator remains stale; validator blocks unsafe candidate.'),
              ('2', 'Supplier formally discloses the update to coordinator.', 'Plan recomputed within known capacity; approval still pending.'),
              ('3', 'Controlled-medicine emergency case explicitly declared.', 'EDE-specific review pathway indicated; no automated authorization.'),
          ], [39, 224, 239]),
          Spacer(1, 10),
          p('All identities, quantities, routes and urgency weights are invented. The workflow measures protocol correctness and optimization metrics, not patient outcomes.', 'MRNote'),
          PageBreak()]

# Page 2: architecture and standards mapping.
story += [p('ARCHITECTURE AND STANDARDS', 'MRKicker'),
          p('3. Multi-agent coordination and boundaries', 'MRH'),
          p('Ten role-specific offline assessors: Coordinator, Hospital, Inventory, Demand, Supplier, Logistics, Regulator, GlobalPolicy, Equity and Auditor. Each receives a bounded view; handoffs are typed and auditable. The independent operational validator checks stock reserve, route capacity, temperature and timing. Policy retrieval supplies research context, not permission. Role findings quantify visible shortages, reserve-protected surplus, demand and route constraints; private supplier details are withheld until formal disclosure.'),
          box('<b>Human authorization:</b> neither an offline assessor nor an optional LLM response can issue a regulatory permit. Human authorization is always required. The browser demo runs on loopback; it has no user authentication and is not a deployed medical service.'),
          heading('4. Mapping to ITU-T Y.3172 (architectural analogy)'),
          table(['Y.3172-oriented element', 'MedRoute X analogue', 'Limit'], [
              ('Data collection / preparation', 'Synthetic inventory, route and event fixtures; scoped observations.', 'No live healthcare data pipeline.'),
              ('Model and pipeline functions', 'Optimization, retrieval, role evaluation, deterministic policy gate.', 'Not an ITU-certified implementation.'),
              ('Orchestration and sandbox', 'Sequenced events, typed handoffs, replayable tests.', 'Offline prototype; no network orchestration.'),
              ('Monitoring and outputs', 'Audit hash chain, evidence references, regression checks.', 'Hash chain is not tamper-proof against a full rewrite.'),
          ], [136, 232, 134]),
          heading('5. Mapping to ITU AI Readiness Framework 2.0'),
          table(['Dimension', 'Implemented signal / identified need'], [
              ('Data governance and sovereignty', 'No patient data; public source metadata; future expert-reviewed national corpus needed.'),
              ('Human oversight and accountability', 'Human approval gate; role-specific audit; no delegated legal decisions.'),
              ('Digital infrastructure and skills', 'Local Python demo, reproducible tests; trained operators and secure hosting not yet available.'),
              ('Inclusion and contextualization', 'Synthetic priority-weighted allocation; fairness and local applicability unvalidated.'),
          ], [161, 341]),
          p('The standards mappings are qualitative design interpretations, not conformity assessments.', 'MRNote'),
          PageBreak()]

# Page 3: regulatory evidence.
story += [p('POLICY EVIDENCE AND HUMAN AUTHORITY', 'MRKicker'),
          p('6. Local policy mapping (UAE)', 'MRH'),
          p('The curated knowledge base has 14 source pointers and 18 short claims. These are manually summarized metadata and selected official excerpts, <b>not</b> a complete national legislative corpus. Every candidate medicine movement is marked HUMAN_REVIEW_REQUIRED.'),
          table(['Official source / reference', 'Relevant scope', 'Prototype response'], [
              ('EDE emergency transfer service [R1]', 'Request for approval of emergency transfers of narcotic, psychotropic and semi-controlled medicines between eligible facilities.', 'Explicit controlled + emergency scenario -> EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED; no permit.'),
              ('UAE Federal Law 2/2019, Arts 4 and 16 [R2]', 'Confidentiality and conditions/exceptions concerning health information.', 'Only synthetic data; no patient-specific document ingestion.'),
              ('UAE Federal Law 2/2019, Art 13 [R2]', 'Conditions restricting certain offshore health-data processing/transfers.', 'No claim that this sandbox is approved for real health data.'),
              ('UAE Federal Decree-Law 38/2024 [R3]', 'Medical products and pharmaceutical establishments (official legislation metadata).', 'Product/facility authorization requires qualified review.'),
              ('EDE supply-chain announcement, 24 Feb 2026 [R7]', 'Multiple authorized agents per medical product; supply continuity policy context.', 'Research context only; not a facility-to-facility transfer permit.'),
              ('EMA shortage solidarity example [R4]', 'Cross-border EU/EEA shortage coordination (comparative context).', 'Research comparator only; no UAE legal force.'),
          ], [159, 181, 162]),
          Spacer(1, 11),
          box('<b>Critical distinction:</b> the EDE service lists patient-related supporting documents for certain applications. Those records belong only in the competent authorized channel, never in MedRoute X. Screening of public document ingestion is heuristic and does not guarantee de-identification.'),
          heading('7. Evidence status and interpretation'),
          p('English excerpts of Federal Law 2/2019 Articles 4, 13 and 16 were checked against the official UAE legislation portal. The authoritative Arabic wording, implementing rules, scope, current amendments and institution-specific procedures require independent expert verification. A missing source is an <b>evidence gap</b>, not a proven defect in UAE law.'),
          PageBreak()]

# Page 4: measurable results and limitations.
s = benchmark['stats']
story += [p('EVALUATION AND REPRODUCIBILITY', 'MRKicker'),
          p('8. Results on 30 seeded synthetic cases', 'MRH'),
          p('Reproducible offline benchmark (seed 2026). Lower values are better. The urgency weights are synthetic institutional preferences and must not be interpreted as medical triage or patient harm reduction.'),
          table(['Method', 'Mean unmet packs', 'Priority-weighted unmet', 'Operational validity'], [
              ('No coordination', f"{s['local_only']['mean_unmet_units']:.2f}", f"{s['local_only']['mean_priority_weighted_unmet']:.2f}", '100%'),
              ('Greedy allocation', f"{s['greedy']['mean_unmet_units']:.2f}", f"{s['greedy']['mean_priority_weighted_unmet']:.2f}", '100%'),
              ('Two-stage optimizer', f"{s['optimized']['mean_unmet_units']:.2f}", f"{s['optimized']['mean_priority_weighted_unmet']:.2f}", '100%'),
          ], [138, 109, 141, 114]),
          Spacer(1, 10),
          box(f"<b>Measured outcome:</b> the optimizer reduces synthetic priority-weighted unmet demand by {benchmark['priority_weighted_reduction_vs_greedy_percent']:.2f}% versus greedy. <b>Total unmet packs are unchanged</b> versus greedy. No patient outcomes or real regulatory compliance were measured."),
          heading('9. Verification and auditability'),
          p('Offline regression suite: 376 tests in the 09 November 2026 local release suite. Protocol acceptance: 30 synthetic scenarios, 300 role assessments, valid hash-chain checks and zero autonomous legal approvals in the previous v0.9 acceptance run. A hash chain detects inconsistent local records; it is not an external trust anchor.'),
          p('New release gate inspects PDF page count and version, mandatory ITU topics, local knowledge-base integrity, benchmark and demo artifacts. It explicitly refuses to infer team registration, GitHub accessibility or formal submission from local files.'),
          heading('10. Decision support and limitations'),
          p('A review packet compares keep-stock, greedy and priority-aware proposals, excludes operationally invalid options and identifies remaining supply requests and human review tasks. Local feedback only breaks ties between equally effective valid options in the same scenario context; it does not retrain a model or override safety gates.'),
          p('The ten offline roles are deterministic rule-based prototypes, <b>not ten independent LLMs</b>. Optional model-backed code is unvalidated and never used in these results. No live supplier integration or trained adaptive model is claimed. There is no independent legal annotation gold set, multilingual corpus, clinical validation, real data, secure user authentication, or approved production deployment.'),
          PageBreak()]

# Page 5: gaps, submission and official references.
story += [p('POLICY GAPS, REFERENCES AND NEXT STEPS', 'MRKicker'),
          p('11. Policy and standards gaps (research hypotheses)', 'MRH'),
          p('<b>G1: Institutional escalation.</b> Under incomplete information, which verified legal and operational actors should receive shortage alerts, and in what order? Need: authoritative role and process documentation plus pharmacy/regulator review.'),
          p('<b>G2: Machine-readable permissions.</b> How can a policy knowledge base encode jurisdiction, source version, exceptions, responsible authority and review status without mistaking retrieval for permission? Need: legal expert gold set and source provenance verification.'),
          p('<b>G3: Cross-border comparators.</b> Which EMA/WHO coordination practices could inform future policy design while remaining clearly nonbinding in the UAE? Need: domain-specific gap analysis and international comparison, not automatic importation of foreign rules.'),
          heading('12. Submission readiness (as of 09 November 2026)'),
          table(['Item', 'Current status'], [
              ('Technical report', 'Five-page v0.10 draft with Y.3172/readiness/policy/evaluation mappings.'),
              ('Knowledge base', '14 source pointers, 18 curated claims; not a complete or legally validated corpus.'),
              ('GitHub repository', 'Not uploaded or confirmed accessible to judges.'),
              ('Team registration', 'Not verified; published registration window ended 5 Nov 2026.'),
              ('Submission', 'NOT submitted; official deadline 10 November 2026.'),
              ('Demo video', 'Optional at first round (up to 7 minutes), required if shortlisted; no recording claimed.'),
          ], [145, 357]),
          heading('13. Reproduction and references'),
          p('Commands: <font name="Courier">python -m pip install -r requirements.txt</font>; <font name="Courier">python -m pytest -q</font>; <font name="Courier">python scripts/submission_gate.py --version 0.10</font>; <font name="Courier">python -m medroute.server</font>. No API key needed for offline runs.', 'MRSmall'),
          p('[R1] Emirates Drug Establishment, emergency transfer service: <link href="https://ede.gov.ae/en/w/approve-emergency-drugs-and-psychotropic-materials" color="#087C85">ede.gov.ae / emergency drugs service</link>.<br/>'
            '[R2] UAE legislation portal, Federal Law 2/2019: <link href="https://uaelegislation.gov.ae/en/legislations/1209/download" color="#087C85">official PDF (Arts 4, 13, 16)</link>.<br/>'
            '[R3] UAE legislation portal, Federal Decree-Law 38/2024: <link href="https://uaelegislation.gov.ae/en/legislations/2751" color="#087C85">official metadata</link>.<br/>'
            '[R4] European Medicines Agency: <link href="https://www.ema.europa.eu/en/about-us/who-we-are/executive-steering-group-shortages-medicinal-products" color="#087C85">shortages steering group</link>.<br/>'
            '[R5] ITU: <link href="https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/" color="#087C85">hackathon requirements, FAQ and deadline</link>.<br/>'
            '[R6] ITU-T: <link href="https://www.itu.int/ITU-T/recommendations/rec.aspx?id=13894" color="#087C85">Y.3172</link>.<br/>'
            '[R7] EDE (24 Feb 2026): <link href="https://www.ede.gov.ae/en/w/emirates-drug-establishment-breaks-the-monopoly-of-medical-products-in-the-country" color="#087C85">supply-chain announcement</link>.', 'MRSmall'),
          p('Team name, member identities and repository link must be supplied by the entrant. This document does not represent organizer acceptance or regulator endorsement.', 'MRNote')]


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=46, rightMargin=46,
                            topMargin=60, bottomMargin=53, title='MedRoute X v0.10 - ITU UAE Technical Report',
                            author='MedRoute X - draft for entrant review')
    doc.build(story, onFirstPage=page, onLaterPages=page)
    print(f'Built {OUT}')


if __name__ == '__main__':
    build()
