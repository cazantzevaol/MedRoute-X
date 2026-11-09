const selectedAgents=new Set();

let agentSelectionInitialized=false;

const el = id => document.getElementById(id);

const escapeHTML = v => String(v).replace(/[&<>"']/g, x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));

const fmt = v => Number(v).toLocaleString('en-US');

const roleLabels={Equity:'Fairness of distribution',GlobalPolicy:'International policy'};

const inputLabels={

 sites:'facility inventory and demand',routes:'known routes',

 received_reports:'reports shared with this role',source_refs:'policy references',

 product_category:'product category',emergency_declared:'emergency declaration status'

};

async function request(path,method='GET', body='{}') {

 const options = {method};

 if(method==='POST') {

  options.headers={'Content-Type':'application/json','X-MedRoute-Request':'dashboard-v1'};

  options.body=body;

 }

 const res=await fetch(path,options);

 if(!res.ok) {

  if(path==='/api/agents/run'&&!res.headers.get('X-MedRoute-Agent-API')){

   throw new Error('The running server needs an update. Close the demo server, run run_demo.bat again, then refresh this page.');

  }

  const details=await res.json().catch(()=>null);

  throw new Error(details?.error||'Request failed ('+res.status+')');

 }

 return res.json();

}

function render(s) {

 el('status').textContent=s.release_status.replaceAll('_',' ');el('status').className='status '+(s.release_status.includes('BLOCKED')?'blocked':'');

 el('scenario-name').textContent=s.scenario.title;

 el('steps-total').textContent=s.steps_total;

 el('step').textContent=s.step;el('event').textContent=s.event||'Initial coordination — information shared is incomplete';

 el('before').textContent=fmt(s.plan.baseline_unmet);el('after').textContent=fmt(s.plan.unmet_total);

 el('covered').textContent=fmt(s.plan.baseline_unmet-s.plan.unmet_total);

 for(const id of ['before','after']){

  const count=id==='before'?s.plan.baseline_unmet:s.plan.unmet_total;

  el(id).closest('.metric').classList.toggle('has-shortfall',count>0);

 }

 el('shortfall-by-site').innerHTML=Object.entries(s.plan.unmet_by_site).map(([site,count])=>

  `<div class="shortfall-row ${count>0?'has-shortfall':''}">

  <strong>${escapeHTML(site)}</strong><span>${!s.operational_check.passes?'Awaiting a valid plan':count>0?fmt(count)+' packs unmet':'No modeled shortfall'}</span>

  <meter min="0" max="${Math.max(1,s.plan.baseline_unmet)}" value="${s.operational_check.passes?count:0}"

   aria-label="${escapeHTML(site)} unmet packs">${count}</meter></div>`).join('');

 el('shortfall-note').textContent=s.operational_check.passes?

  'Remaining shortfall under the proposed plan. Human authorization is required.':

  'Plan blocked. These estimates assume a plan that cannot currently be executed.';

 el('operational').textContent=s.operational_check.passes?'PASS':'FAIL';el('operational').className='check '+(s.operational_check.passes?'safe':'blocked');

 el('sites').innerHTML=s.scenario.sites.map(h=>`<div class="site"><strong>${escapeHTML(h.id)}</strong><b>${fmt(h.stock)}</b><small>stock packs · ${h.daily_demand}/day demand</small></div>`).join('');

 el('transfers').innerHTML=s.plan.transfers.length?s.plan.transfers.map(t=>`<div class="transfer"><span>${escapeHTML(t.from)} → ${escapeHTML(t.to)}</span><strong>${fmt(t.quantity)} packs</strong></div>`).join(''):'<div class="entry">No transfers proposed.</div>';

 el('gate').innerHTML=`<div class="gate"><strong>${escapeHTML(s.legal_check.status)}</strong><p>${escapeHTML(s.legal_check.message)}</p><small>References: ${escapeHTML(s.legal_check.evidence.join(', ')||'none')}</small></div>`;

 el('issues').innerHTML=s.operational_check.issues.length?s.operational_check.issues.map(x=>`<div class="issues">⚠ ${escapeHTML(x)}</div>`).join(''):'<div class="entry safe">✓ No operational constraint violations detected.</div>';

 el('gap').innerHTML=`<div class="gap"><em>${escapeHTML(s.policy_gap_hypothesis.classification)}</em><p>${escapeHTML(s.policy_gap_hypothesis.question)}</p><div>${escapeHTML(s.policy_gap_hypothesis.comparison)}</div></div>`;

 if(!agentSelectionInitialized){

  s.agents.forEach(agent=>selectedAgents.add(agent.agent));

  agentSelectionInitialized=true;

 }

 el('agents').innerHTML=s.agents.map(agent=>{

  const inputs=agent.observation_keys.map(key=>inputLabels[key]||key);

  return `<div class="agent">

   <label><input type="checkbox" data-agent="${escapeHTML(agent.agent)}" ${selectedAgents.has(agent.agent)?'checked':''}> <strong>${escapeHTML(roleLabels[agent.agent]||agent.agent)}</strong></label>

   <small>${escapeHTML(agent.mandate)}</small>

   <p>${escapeHTML(agent.summary)}</p>

   <small>Available inputs: ${escapeHTML(inputs.join(', ')||'None')}<br>

   Reports received: ${fmt(agent.messages_seen)}<br>

   Source references: ${escapeHTML(agent.references.join(', ')||'None')}</small>

  </div>`;

 }).join('');

 el('reports').innerHTML=s.reports.length?s.reports.map(r=>`<div class="entry"><small>EVENT ${r.step} · ${escapeHTML(r.visibility)}</small>Institutional report details withheld in public view.</div>`).join(''):'<div class="entry">No event released yet.</div>';

 el('policy').innerHTML=s.policy_matrix.rows.map(r=>`<div class="entry"><small>${escapeHTML(r.id)} · ${escapeHTML(r.jurisdiction)} · ${escapeHTML(r.status)}</small><strong>${escapeHTML(r.title)}</strong><p>${escapeHTML(r.question)}</p><small>Evidence: ${escapeHTML(r.references.join(', ')||'none')} · Confirmed legal gap: NO</small></div>`).join('');

 el('audit').innerHTML=s.audit.map(a=>`<div class="entry"><small>#${a.event_no} · STEP ${a.step} · ${escapeHTML(a.kind)}</small>${escapeHTML(a.detail)}</div>`).join('');

}

let state;

let simulationBusy=false;

function renderDisruption(s) {

 const panel=el('disruption-panel');

 panel.hidden=s.scenario.id!=='CUSTOM';

 const jump=el('jump-disruption');

 jump.hidden=panel.hidden;

 if(panel.hidden)return;

 const pending=s.disruption_pending;

 jump.textContent=pending?'Review supplier report':'Test route disruption';

 const routes=s.scenario.routes_known.filter(route=>route.capacity>0);

 el('disruption-form').hidden=pending||routes.length===0;

 el('confirm-disruption').hidden=!pending;

 const select=el('disruption-route');

 select.replaceChildren(...routes.map(route=>{

  const option=document.createElement('option');

  option.value=route.id;

  option.textContent=route.from+' → '+route.to+' ('+route.capacity+' packs)';

  option.dataset.capacity=route.capacity;

  return option;

 }));

 el('disruption-capacity').value='';

 updateCapacityLimit();

 el('disruption-status').textContent=pending?

  'Supplier report received. The coordinator still has the previous capacity. Operational check: '+

   (s.operational_check.passes?'passed.':'blocked.'):

  routes.length?'Report a reduction to test how the agents respond.':'No routes have capacity to reduce.';

}



function updateCapacityLimit() {

 const route=el('disruption-route').selectedOptions[0];

 el('disruption-capacity').max=route?Number(route.dataset.capacity)-1:0;

}



el('jump-disruption').onclick=()=>{

 el('disruption-panel').scrollIntoView({block:'start'});

 const target=state.disruption_pending?'confirm-disruption':'disruption-route';

 if(!el('disruption-form').hidden||state.disruption_pending)el(target).focus({preventScroll:true});

};

el('disruption-route').onchange=updateCapacityLimit;

el('disruption-form').onsubmit=async event=>{

 event.preventDefault();

 const body=JSON.stringify({route_id:el('disruption-route').value,

  capacity:el('disruption-capacity').valueAsNumber});

 if(!await updateSimulation('/api/scenario/disruption','POST',body)){

  el('disruption-status').textContent=el('simulation-error').textContent;

 } else {

  el('confirm-disruption').focus({preventScroll:true});

 }

};

el('confirm-disruption').onclick=async()=>{

 const previousShortfall=state.plan.unmet_total;

 const body=JSON.stringify({disruption_id:state.disruption_id});

 const ok=await updateSimulation('/api/scenario/confirm','POST',body);

 el('disruption-status').textContent=ok?

  'Update shared and plan recalculated. Estimated shortfall: '+fmt(previousShortfall)+

   ' → '+fmt(state.plan.unmet_total)+' packs. Human authorization is still required.':

  el('simulation-error').textContent;

};



function nextAction() {

 if (!state) return {label:'Load simulation', path:'/api/state', method:'GET'};

 if (state.scenario.id==='CUSTOM') {

  return {label:'Start built-in demo', path:'/api/scenario/example', method:'POST'};

 }

 if (state.step>=state.steps_total) {

  return {label:'Restart simulation', path:'/api/reset', method:'POST'};

 }

 return {label:'Release next event →', path:'/api/step', method:'POST'};

}

function updateControls(busy) {

 el('advance').disabled=busy;

 el('advance').textContent=busy?'Updating…':nextAction().label;

 for(const id of ['reset','example','scenario-file','report-disruption','confirm-disruption','edit-scenario']) el(id).disabled=busy;

 el('scenario-form').querySelector('[type="submit"]').disabled=busy;

}

async function updateSimulation(path,method='GET', body='{}') {

 if(simulationBusy)return false;

 simulationBusy=true;

 updateControls(true);

 const error=el('simulation-error');

 error.textContent='';

 try {

  state=await request(path,method,typeof body==='function'?await body():body);

  render(state);

  el('ai-briefing-status').textContent='';

  renderDisruption(state);

  void loadReviewPacket(state);

  el('councilpanel').hidden=true;

  setAgentRunStatus('Scenario updated. Agent results need a new run.');

  if(el('auto-agents').checked)void runSelectedAgents();

  return true;

 } catch(e) {

  error.textContent='Could not update the simulation. '+e.message;

 } finally {

  simulationBusy=false;

  updateControls(false);

 }

}

el('advance').onclick=()=>{

 const {path,method}=nextAction();

 return updateSimulation(path,method);

};

el('reset').onclick=()=>updateSimulation('/api/reset','POST');

el('example').onclick=()=>updateSimulation('/api/scenario/example','POST');

function downloadJSON(data,filename) {

 const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));

 const link=document.createElement('a');

 link.href=url;

 link.download=filename;

 link.click();

 setTimeout(()=>URL.revokeObjectURL(url),1000);

}



const fileStatus=el('scenario-file-status');

el('download-template').onclick=async event=>{

 const button=event.currentTarget;

 button.disabled=true;

 fileStatus.textContent='Preparing the JSON template…';

 try {

  const data=await request('/api/scenario/template');

  downloadJSON(data,'synthetic-scenario.json');

  fileStatus.textContent='Download requested. Check your browser downloads for synthetic-scenario.json.';

 } catch(error) {

  fileStatus.textContent='Could not download the template. '+error.message;

 } finally {

  button.disabled=false;

 }

};

el('scenario-file').onchange=async event=>{

 const file=event.target.files[0];

 event.target.value='';

 if(!file)return;

 fileStatus.textContent='Loading '+file.name+'…';

 const loaded=await updateSimulation('/api/scenario','POST',()=>{

  if(file.size>16384)throw new Error('Choose a JSON file up to 16 KB.');

  return file.text();

 });

 fileStatus.textContent=loaded?'Loaded '+file.name+'. See the updated plan below.':

  el('simulation-error').textContent;

};

const editor=el('scenario-editor');

const form=el('scenario-form');

const editorStatus=el('editor-status');

let draft;

let draftState;



function numberField(row,key,label,min,max) {

 const wrapper=document.createElement('label');

 const input=document.createElement('input');

 wrapper.textContent=label;

 input.type='number';

 input.min=min;

 input.max=max;

 input.step=1;

 input.required=true;

 input.value=row[key];

 input.oninput=()=>{row[key]=input.valueAsNumber};

 wrapper.append(input);

 return wrapper;

}



function editorGroup(title,fields) {

 const group=document.createElement('fieldset');

 const legend=document.createElement('legend');

 legend.textContent=title;

 group.append(legend,...fields);

 return group;

}



function endpointField(route,key,label) {

 const wrapper=document.createElement('label');

 wrapper.textContent=label;

 const select=document.createElement('select');

 for(const site of draft.sites){

  const option=document.createElement('option');

  option.value=site.id; option.textContent='Facility '+site.id; select.append(option);

 }

 select.value=route[key];

 select.onchange=()=>{

  const other=key==='from'?'to':'from';

  if(Number(select.value)===route[other]){

   select.value=route[key]; editorStatus.textContent='Choose two different facilities.'; return;

  }

  route[key]=Number(select.value); editorStatus.textContent='';

 };

 wrapper.append(select); return wrapper;

}

function nextEditorId(rows){

 const ids=new Set(rows.map(row=>row.id));

 let id=1; while(ids.has(id))id++;

 return id;

}

function removeDraftFacility(id){
 if(!draft||draft.sites.length<=1)return;
 const connected=draft.routes.filter(route=>route.from===id||route.to===id);
 const message='Remove Facility '+id+' from this draft?'+(connected.length?
  '\nAlso remove connected routes: '+connected.map(r=>'Route '+r.id+' ('+r.from+' -> '+r.to+')').join(', '):'');
 if(!confirm(message))return;
 draft.sites=draft.sites.filter(site=>site.id!==id);
 draft.routes=draft.routes.filter(route=>route.from!==id&&route.to!==id);
 renderEditor();
 editorStatus.textContent='Facility '+id+' and '+connected.length+' connected routes removed from the draft. Click Calculate plan to apply.';
}
function removeDraftRoute(id){
 if(!draft)return;
 draft.routes=draft.routes.filter(route=>route.id!==id);
 renderEditor();
 editorStatus.textContent='Route '+id+' removed from the draft. Click Calculate plan to apply.';
}
function editorButton(label,action,disabled=false){
 const button=document.createElement('button');
 button.type='button'; button.className='secondary'; button.textContent=label;
 button.disabled=disabled; button.onclick=action;
 return button;
}
function moveDraftFacility(id,offset){
 if(!draft||![-1,1].includes(offset))return;
 const index=draft.sites.findIndex(site=>site.id===id), target=index+offset;
 if(index<0||target<0||target>=draft.sites.length)return;
 [draft.sites[index],draft.sites[target]]=[draft.sites[target],draft.sites[index]];
 renderEditor();
 editorStatus.textContent='Facility '+id+' moved. Identifiers and route connections are unchanged.';
}
function renderEditor(){

  const groups=[editorGroup('Planning',[

   numberField(draft,'horizon_days','Planning days',1,30)

  ])];

  for(const site of draft.sites) {

   groups.push(editorGroup('Facility '+site.id,[

    numberField(site,'stock','Stock (packs)',0,10000),

    numberField(site,'daily_demand','Demand (packs/day)',0,10000),

    numberField(site,'reserve_days','Reserve (days)',0,30),

    numberField(site,'priority','Priority (1–5)',1,5),
    editorButton('Move up',()=>moveDraftFacility(site.id,-1),draft.sites[0]===site),
    editorButton('Move down',()=>moveDraftFacility(site.id,1),draft.sites[draft.sites.length-1]===site),
    editorButton('Remove facility',()=>removeDraftFacility(site.id),draft.sites.length<=1)

   ]));

  }

  for(const route of draft.routes) {

   groups.push(editorGroup('Route '+route.id,[

    endpointField(route,'from','From facility'),

    endpointField(route,'to','To facility'),

    numberField(route,'capacity','Capacity (packs)',0,10000),

    numberField(route,'days','Travel days',0,30),
    editorButton('Remove route',()=>removeDraftRoute(route.id))

   ]));

  }

  el('scenario-fields').replaceChildren(...groups);

  el('add-facility').disabled=draft.sites.length>=20;

  el('add-route').disabled=draft.sites.length<2||draft.routes.length>=60;

  el('editor-count').textContent=draft.sites.length+' / 20 facilities · '+draft.routes.length+' / 60 routes';

}

el('add-facility').onclick=()=>{

 if(!draft||draft.sites.length>=20)return;

 const id=nextEditorId(draft.sites);

 draft.sites.push({id,stock:0,daily_demand:0,reserve_days:2,priority:1});

 renderEditor();

 editorStatus.textContent='Facility '+id+' added. Enter synthetic stock and demand, then add a route if needed.';

};

el('add-route').onclick=()=>{

 if(!draft||draft.sites.length<2||draft.routes.length>=60)return;

 draft.routes.push({id:nextEditorId(draft.routes),from:draft.sites[0].id,

  to:draft.sites[draft.sites.length-1].id,capacity:0,days:1,temperature_ok:true,requires_approval:true});

 renderEditor();

 editorStatus.textContent='Route added with zero capacity. Choose its facilities and enter a synthetic capacity. Human review remains required.';

};



el('edit-scenario').onclick=async()=>{

 editor.hidden=false;

 editor.scrollIntoView({block:'start'});

 if(draft&&draftState===state)return;

 form.hidden=true;

 editorStatus.textContent='Loading current scenario values…';

 try {

  if(!state)throw new Error('Scenario is still loading.');

  const siteIds=new Map(state.scenario.sites.map((site,index)=>{
   const match=state.scenario.id==='CUSTOM'&&/^Facility (\d+)$/.exec(site.id);
   return [site.id,match?Number(match[1]):index+1];
  }));

  draft={

   horizon_days:state.scenario.horizon_days,

   sites:state.scenario.sites.map(site=>({...site,id:siteIds.get(site.id)})),

   routes:state.scenario.routes_known.map((route,index)=>({

    ...route,id:index+1,from:siteIds.get(route.from),to:siteIds.get(route.to)

   }))

  };

  draftState=state;

  renderEditor();

  form.hidden=false;

  editorStatus.textContent='';

 } catch {

  draft=null;

  editorStatus.textContent='Could not load current scenario values. Wait for the scenario to load, then click Edit scenario again.';

 }

};

el('close-scenario').onclick=()=>{editor.hidden=true};

form.onsubmit=async event=>{

 event.preventDefault();

 const submit=form.querySelector('[type="submit"]');

 submit.disabled=true;

 try {

  const saved=await updateSimulation('/api/scenario','POST',JSON.stringify(draft));

  editorStatus.textContent=saved?

   'Plan updated. Shortfall: '+fmt(state.plan.baseline_unmet)+' packs before the plan, '+

   fmt(state.plan.unmet_total)+' packs after. Operational check: '+

   (state.operational_check.passes?'passed.':'blocked.'):

   el('simulation-error').textContent;

 } finally {

  submit.disabled=false;

 }

};

el('save-scenario').onclick=()=>{

 if(!form.reportValidity())return;

 downloadJSON(draft,'synthetic-scenario.json');

};

el('benchmark').onclick=async()=>{

 el('benchmark').disabled=true;el('benchmark').textContent='Evaluating…';

 try{let b=await request('/api/evaluation');el('benchpanel').hidden=false;

 el('benchrows').innerHTML='<div class="benchgrid">'+Object.entries(b.stats).map(([m,v])=>`<div class="metric"><span>${escapeHTML(m)}</span><strong>${fmt(v.mean_unmet_units)}</strong><small>mean unmet units · weighted ${v.mean_priority_weighted_unmet} · valid rate ${Math.round(v.operational_valid_rate*100)}% · ${v.scenarios} cases</small></div>`).join('')+'</div>';

 el('benchpanel').scrollIntoView({behavior:'smooth'});}

 catch(error){el('simulation-error').textContent='Benchmark failed. '+error.message}

 finally{el('benchmark').disabled=false;el('benchmark').textContent='Run 30-case benchmark'}

};updateSimulation('/api/state');



el('download').onclick=async()=>{

 const button=el('download');

 button.disabled=true;

 try {

  downloadJSON(await request('/api/dossier'),'medroute_x_evidence_dossier.json');

 } catch(error) {

  el('simulation-error').textContent='Evidence download failed. '+error.message;

 } finally {

  button.disabled=false;

 }

};



let agentRunVersion=0;

el('agents').onchange=event=>{

 const role=event.target.dataset.agent;

 if(!role)return;

 if(event.target.checked)selectedAgents.add(role);else selectedAgents.delete(role);

 agentRunVersion++;

 el('councilpanel').hidden=true;

 setAgentRunStatus(selectedAgents.size+' roles selected. Run to update results.');

 if(el('auto-agents').checked)void runSelectedAgents();

};

function setAgentRunStatus(message){

 for(const id of ['agent-run-status','agent-hero-status','council-status'])el(id).textContent=message;

}

function sourceEvidenceHTML(agent){
 const sources=agent.source_details||[];
 if(!sources.length)return '<p>No inspectable source details returned. Run the agents again after restarting the server.</p>';
 return sources.map(source=>{
  const url=String(source.source_url||'');
  const safe=/^https:\/\/[^\s"<>]+$/.test(url);
  const title=escapeHTML(source.source_title||source.id);
  return '<div class="entry"><strong>'+escapeHTML(source.id)+'</strong><p>'+
   (safe?'<a href="'+escapeHTML(url)+'" target="_blank" rel="noopener noreferrer">'+title+'</a>':title+' (link unavailable)')+
   '</p><p>Curated source statement: '+escapeHTML(source.claim)+'</p><small>Jurisdiction: '+escapeHTML(source.jurisdiction)+
   '<br>Source review: '+escapeHTML(source.source_review_status)+
   '<br>Applicability: '+escapeHTML(source.legal_applicability)+
   '</small><p>Human check: open the source, locate the relevant section and check whether it supports this specific finding. Scenario quantities come from synthetic inputs, not this policy source.</p></div>';
 }).join('');
}
async function runSelectedAgents(){

 const version=++agentRunVersion;

 const snapshot=state;

 const status={set textContent(message){setAgentRunStatus(message)}};

 const roles=Array.from(selectedAgents);

 if(!roles.length){

  status.textContent='Select at least one role.';

  return;

 }

 status.textContent='Running '+roles.length+' local role checks on scenario step '+snapshot.step+'… Waiting for validated results.';

 el('councilpanel').hidden=true;

 try{

  const result=await request('/api/agents/run','POST',JSON.stringify({roles}));

  if(version!==agentRunVersion||snapshot!==state)return;

  el('councilpanel').hidden=false;

  el('councillist').innerHTML=result.trace.map(a=>

   `<div class="agent"><strong>${escapeHTML(roleLabels[a.role]||a.role)}</strong>

   <p><strong>Input</strong> · ${escapeHTML((a.observation_keys||[]).filter(key=>inputLabels[key]).map(key=>inputLabels[key]).join(', ')||'Role-scoped scenario')} · ${Number(a.private_reports_visible||0)} visible reports · ${a.incoming_handoffs.length} notices</p>

   <p><strong>Finding</strong> · ${escapeHTML(a.summary)}</p>

   <p><strong>Next review action</strong> · ${escapeHTML(a.outgoing_handoff?.intent==='REQUEST_FORMAL_DISCLOSURE'?'Request formal disclosure of the supplier update.':a.open_questions?.[0]||'Review this finding with the responsible specialist.')}</p>

   <small>Mode: ${escapeHTML(a.mode)} · Notices received: ${a.incoming_handoffs.length}<br>

   Source references: ${escapeHTML(a.cited_claim_ids.join(', ')||'None')}<br>

   Human authorization required</small>

   <details><summary>Source-reference checks</summary>

   <small>Integrity: ${escapeHTML(a.citation_integrity||'UNKNOWN')}<br>

   Unrecognized references: ${Number(a.unrecognized_reference_count||0)}<br>

   Flags: ${escapeHTML((a.safety_flags||[]).join(', ')||'None')}<br>

   Entailment NOT verified: source text has not been checked for support of this finding. Allowed references do not prove accuracy or legal permission.</small>${sourceEvidenceHTML(a)}</details></div>`).join('');

  const notices=result.handoffs?.length||0;

  const check=result.operational_check_from_independent_engine;

  status.textContent=result.trace.length+' roles completed · '+notices+' structured notices · Independent operational check: '+(check?.passes?'passed':'blocked')+'. Human authorization is still required.';

  el('councilpanel').scrollIntoView({block:'start',behavior:'smooth'});

 }catch(error){

  if(version===agentRunVersion&&snapshot===state)status.textContent='Agent run failed. '+error.message;

 }

}

el('run-agents').onclick=()=>runSelectedAgents();

el('councilrun').onclick=async()=>{

 await runSelectedAgents();

 if(!el('councilpanel').hidden)el('councilpanel').scrollIntoView({behavior:'smooth'});

};

el('councilrun').textContent='Run selected agents';

el('auto-agents').onchange=()=>{

 if(el('auto-agents').checked)void runSelectedAgents();

 else {

  agentRunVersion++;

  setAgentRunStatus('Automatic runs stopped. Use Run selected agents for a manual check.');

 }

};



el('ai-briefing').onclick=async()=>{

 const button=el('ai-briefing');

 const message=el('ai-briefing-status');

 const snapshot=state;

 button.disabled=true;

 message.textContent='Local AI is reviewing the scenario…';

 try {

  const result=await request('/api/ai/briefing','POST');

  if(state===snapshot)message.textContent='AI priority: '+result.finding;

 } catch(error) {

  if(state===snapshot)message.textContent=error.message;

 } finally {

  button.disabled=false;

 }

};



let currentReview;

let reviewRequestVersion=0;

async function loadReviewPacket(snapshot){

 const version=++reviewRequestVersion;

 currentReview=null;

 el('download-review').disabled=true;

 el('feedback-useful').disabled=true;

 el('feedback-unhelpful').disabled=true;

 el('decision-options').replaceChildren();

 el('decision-next').textContent='';

 el('review-recommendation').replaceChildren();

 el('decision-tasks').replaceChildren();

 el('decision-status').textContent='Preparing the review…';

 el('feedback-status').textContent='Local feedback helps select between equally effective valid options.';

 try{

  const packet=await request('/api/review-packet');

  if(state!==snapshot||version!==reviewRequestVersion)return;

  if(packet.audit_head!==snapshot.audit_verification.head){

   el('decision-status').textContent='Scenario changed in another session. Refresh to review the latest state.';

   return;

  }

  currentReview=packet;

  const proposal=packet.recommendation;

  el('review-recommendation').innerHTML=

   '<h3>Proposed resolution for human review</h3><p>'+escapeHTML(proposal.review_note)+'</p>'+

   '<strong>'+escapeHTML(proposal.title)+(proposal.provisional?' — provisional':'')+'</strong>'+

   (proposal.transfers.length?'<ul>'+proposal.transfers.map(move=>

    '<li>Propose '+fmt(move.quantity)+' packs from '+escapeHTML(move.from)+' to '+

    escapeHTML(move.to)+' via '+escapeHTML(move.route)+'.</li>').join('')+'</ul>':

    '<p>Keep stocks in place until a valid redistribution plan is available.</p>')+

   (proposal.additional_supply_requests.length?'<p>Request availability confirmation for additional supply:</p><ul>'+

    proposal.additional_supply_requests.map(item=>'<li>'+escapeHTML(item.facility)+': '+fmt(item.packs)+

     ' packs. Supplier availability is unconfirmed.</li>').join('')+'</ul>':'<p>No additional supply is required in this modeled proposal.</p>')+

   '<small>'+escapeHTML(proposal.reason)+'</small>';

  if(!snapshot.operational_check.passes){

   el('shortfall-note').textContent='Shortfall under the operationally valid proposal below. Human review is required.';

   el('shortfall-by-site').innerHTML=Object.entries(proposal.unmet_by_site).map(([site,count])=>

    `<div class="shortfall-row ${count>0?'has-shortfall':''}"><strong>${escapeHTML(site)}</strong>

    <span>${count>0?fmt(count)+' packs unmet':'No modeled shortfall'}</span>

    <meter min="0" max="${Math.max(1,snapshot.plan.baseline_unmet)}" value="${count}"

     aria-label="${escapeHTML(site)} unmet packs">${count}</meter></div>`).join('');

  }

  el('decision-status').textContent='Compare proposals on the same scenario. Human review is required.';

  el('decision-options').innerHTML=packet.alternatives.map(option=>

   `<div class="entry ${option.unmet_packs>0?'has-shortfall':''}"><strong>${escapeHTML(option.title)}</strong>

   <p>${fmt(option.unmet_packs)} packs unmet · Weighted shortfall ${fmt(option.weighted_unmet)}</p>

   <p>${option.operational_pass?'Operational check passed':'BLOCKED: '+escapeHTML(option.issues.join(' '))}</p>

   </div>`).join('');

  el('decision-next').textContent='Next: '+packet.next_action.action+' Owner: '+packet.next_action.owner;

  el('decision-tasks').innerHTML=packet.review_tasks.map(task=>

   `<div class="entry"><strong>${escapeHTML(task.owner)}</strong><p>${escapeHTML(task.action)}</p>

   <small>${escapeHTML(task.reason)}</small></div>`).join('');

  el('download-review').disabled=false;

  el('feedback-useful').disabled=false;

  el('feedback-unhelpful').disabled=false;

 }catch(error){

  if(state===snapshot&&version===reviewRequestVersion)el('decision-status').textContent='Review unavailable. '+error.message;

 }

}

el('download-review').onclick=()=>{

 if(currentReview)downloadJSON(currentReview,'medroute-review-packet.json');

};



async function rateProposal(useful){

 const packet=currentReview;

 const snapshot=state;

 if(!packet)return;

 el('feedback-useful').disabled=true;

 el('feedback-unhelpful').disabled=true;

 try{

  await request('/api/review-feedback','POST',JSON.stringify({

   audit_head:packet.audit_head,method:packet.recommendation.method,useful

  }));

  if(state!==snapshot||currentReview!==packet)return;

  el('feedback-status').textContent='Preference saved locally. It will help rank equally effective valid options for these conditions.';

  await loadReviewPacket(state);

 }catch(error){

  if(state!==snapshot||currentReview!==packet)return;

  el('feedback-status').textContent='Feedback not saved. '+error.message;

  el('feedback-useful').disabled=false;

  el('feedback-unhelpful').disabled=false;

 }

}

el('feedback-useful').onclick=()=>rateProposal(true);

el('feedback-unhelpful').onclick=()=>rateProposal(false);

