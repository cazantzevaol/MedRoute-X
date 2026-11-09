// Run with: node tests/test_ui_regressions.cjs (no browser dependencies).
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
function cut(start, end) {
  const offset = source.indexOf(start);
  assert.ok(offset >= 0, start);
  const finish = source.indexOf(end, offset);
  assert.ok(finish > offset, end);
  return source.slice(offset, finish);
}
function dom() {
  const nodes = {};
  const node = () => ({append() {}, replaceChildren() {}, scrollIntoView() {},
    querySelector() { return node(); }});
  return {el: id => nodes[id] ??= node(), document: {createElement: node}};
}
async function main() {
  {
    let resolve, calls = 0;
    const context = vm.createContext({...dom(), request: () => {
      calls++; return new Promise(r => resolve = r);
    }, render() {}, renderDisruption() {}, loadReviewPacket() {},
    updateControls() {}, runSelectedAgents() {}, setAgentRunStatus() {}});
    vm.runInContext('let state; let simulationBusy=false;' +
      cut('async function updateSimulation', "el('advance').onclick"), context);
    const first = context.updateSimulation('/first');
    assert.equal(await context.updateSimulation('/second'), false);
    assert.equal(calls, 1);
    resolve({});
    assert.equal(await first, true);
    assert.equal(vm.runInContext('simulationBusy', context), false);
    console.log('PASS mutation overlap guard');
  }
  {
    const context = vm.createContext({...dom(), state: {scenario: {
      horizon_days: 9, sites: [{id: 'Facility 19', stock: 42},
        {id: 'Facility 55', stock: 100}],
      routes_known: [{id: 'R', from: 'Facility 55', to: 'Facility 19', capacity: 5}]
    }}, downloadJSON() {}});
    vm.runInContext(cut('const editor=el', "el('benchmark').onclick"), context);
    await context.el('edit-scenario').onclick();
    const draft = vm.runInContext('draft', context);
    assert.equal(draft.horizon_days, 9);
    assert.equal(draft.sites[0].stock, 42);
    assert.equal(draft.routes[0].from, 2);
    assert.equal(draft.routes[0].to, 1);
    context.state = {scenario: {...context.state.scenario, horizon_days: 12}};
    await context.el('edit-scenario').onclick();
    assert.equal(vm.runInContext('draft.horizon_days', context), 12);
    context.state={scenario:{...context.state.scenario,id:'CUSTOM'}};
    await context.el('edit-scenario').onclick();
    assert.equal(vm.runInContext('draft.sites[0].id',context),19);
    assert.equal(vm.runInContext('draft.routes[0].from',context),55);
    assert.equal(vm.runInContext('draft.routes[0].to',context),19);
    console.log('PASS current scenario editor and endpoint mapping');
  }
  {
    let saved, posted;
    const context = vm.createContext({...dom(), state: {scenario: {
      horizon_days: 5, sites: [1,2,3].map(id => ({id,stock:10,daily_demand:2,reserve_days:1,priority:1})), routes_known: []
    }, plan: {baseline_unmet:0,unmet_total:0}, operational_check:{passes:true}},
    fmt: String, downloadJSON: value => saved=JSON.parse(JSON.stringify(value)),
    updateSimulation: async (url,method,body) => {posted=JSON.parse(body);return true;}});
    vm.runInContext(cut('const editor=el', "el('benchmark').onclick"), context);
    await context.el('edit-scenario').onclick();
    context.el('add-facility').onclick();
    assert.equal(vm.runInContext('draft.sites.length',context),4);
    vm.runInContext('draft.sites[3].daily_demand=17; draft.sites[0].stock=123;',context);
    context.el('add-route').onclick();
    assert.equal(vm.runInContext('draft.routes[0].to',context),4);
    assert.equal(vm.runInContext('draft.sites[0].stock',context),123);
    context.el('scenario-form').reportValidity=()=>true;
    context.el('save-scenario').onclick();
    await context.el('scenario-form').onsubmit({preventDefault(){}});
    assert.deepEqual(saved,posted);
    assert.equal(posted.sites[3].daily_demand,17);
    for(let i=0;i<25;i++)context.el('add-facility').onclick();
    for(let i=0;i<65;i++)context.el('add-route').onclick();
    assert.equal(vm.runInContext('draft.sites.length',context),20);
    assert.equal(vm.runInContext('draft.routes.length',context),60);
    assert.equal(vm.runInContext('new Set(draft.sites.map(s=>s.id)).size',context),20);
    assert.equal(context.el('add-facility').disabled,true);
    assert.equal(context.el('add-route').disabled,true);
    const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
    assert.ok(html.includes('<details class="panel" open><summary>Agents, policy evidence and audit'));
    const originalRoutes=vm.runInContext('JSON.stringify(draft.routes)',context);
    context.moveDraftFacility(1,1);
    assert.equal(vm.runInContext('draft.sites[1].id',context),1);
    assert.equal(vm.runInContext('JSON.stringify(draft.routes)',context),originalRoutes);
    context.moveDraftFacility(2,-1);
    assert.equal(vm.runInContext('draft.sites[0].id',context),2);
    context.confirm=()=>false;
    context.removeDraftFacility(1);
    assert.equal(vm.runInContext('draft.sites.length',context),20);
    context.confirm=()=>true;
    context.removeDraftFacility(1);
    assert.equal(vm.runInContext('draft.sites.length',context),19);
    assert.equal(vm.runInContext('draft.routes.some(r=>r.from===1||r.to===1)',context),false);
    context.el('add-route').onclick();
    const routeId=vm.runInContext('draft.routes[0].id',context);
    context.removeDraftRoute(routeId);
    assert.equal(vm.runInContext('draft.routes.some(r=>r.id==='+routeId+')',context),false);
    vm.runInContext('draft.sites=draft.sites.slice(0,1);draft.routes=[];',context);
    context.removeDraftFacility(vm.runInContext('draft.sites[0].id',context));
    assert.equal(vm.runInContext('draft.sites.length',context),1);
    console.log('PASS facility/route add, move, removal, cancellation, limits and save/submit parity');
  }
  {
    const rejects = [];
    const context = vm.createContext({...dom(), state: {},
      request: () => new Promise((resolve, reject) => rejects.push(reject))});
    vm.runInContext(cut('let currentReview;', "el('download-review').onclick"), context);
    const old = context.loadReviewPacket(context.state);
    const fresh = context.loadReviewPacket(context.state);
    rejects[0](new Error('old'));
    await old;
    assert.equal(context.el('decision-status').textContent, 'Preparing the review\u2026');
    rejects[1](new Error('new'));
    await fresh;
    assert.match(context.el('decision-status').textContent, /new/);
    console.log('PASS stale review failure ignored');
  }
  {
    let finish, refreshes = 0;
    const context = vm.createContext({...dom(), state: {},
      currentReview: {audit_head: 'a', recommendation: {method: 'm'}},
      request: () => new Promise(resolve => finish = resolve),
      loadReviewPacket: () => refreshes++});
    vm.runInContext(cut('async function rateProposal', "el('feedback-useful').onclick"), context);
    const pending = context.rateProposal(true);
    context.state = {}; context.currentReview = null;
    finish({}); await pending;
    assert.equal(refreshes, 0);
    console.log('PASS stale feedback ignored');
  }
  {
    const result = {trace: [{role: 'Supplier', summary: 'Capacity reduced',
      observation_keys: ['routes'], private_reports_visible: 1, incoming_handoffs: [],
      outgoing_handoff: {intent: 'REQUEST_FORMAL_DISCLOSURE'}, mode: 'offline',
      cited_claim_ids: []}], handoffs: [{}],
      operational_check_from_independent_engine: {passes: false}};
    const context = vm.createContext({...dom(), state: {step: 1},
      selectedAgents: new Set(['Supplier']), agentRunVersion: 0,
      request: async () => result, roleLabels: {}, inputLabels: {routes: 'known routes'},
      escapeHTML: value => String(value).replaceAll('<', '&lt;')});
    vm.runInContext(cut('function setAgentRunStatus', "el('run-agents').onclick"), context);
    await context.runSelectedAgents();
    assert.match(context.el('councillist').innerHTML, /Input/);
    assert.match(context.el('councillist').innerHTML, /Capacity reduced/);
    assert.match(context.el('councillist').innerHTML, /Request formal disclosure/);
    for (const id of ['agent-run-status', 'agent-hero-status', 'council-status']) {
      assert.match(context.el(id).textContent, /1 roles completed \u00b7 1 structured notices/);
      assert.match(context.el(id).textContent, /blocked/);
    }
    const detail=context.sourceEvidenceHTML({source_details:[{id:'C-TEST',source_title:'Official source',source_url:'https://example.org',claim:'A curated statement',jurisdiction:'UAE',source_review_status:'pending',legal_applicability:'UNVERIFIED'}]});
    assert.match(detail,/href="https:\/\/example.org"/);
    assert.match(detail,/Human check/);
    assert.match(detail,/UNVERIFIED/);
    assert.ok(!context.sourceEvidenceHTML({source_details:[{source_url:'javascript:alert(1)'}]}).includes('href='));
    context.request = async () => { throw new Error('network unavailable'); };
    await context.runSelectedAgents();
    assert.match(context.el('agent-hero-status').textContent, /network unavailable/);
    console.log('PASS agent inputs, findings, action, visible summary and errors');
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
