'use strict';
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const networkStatus = $('#network-status');
const number = value => new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(value);
const stamp = date => new Intl.DateTimeFormat('fr-FR',{timeZone:document.querySelector('[data-timezone]')?.dataset.timezone || 'UTC',hour:'2-digit',minute:'2-digit'}).format(new Date(date));
const read = (storage,key,fallback) => {try {return JSON.parse(storage.getItem(key)) ?? fallback;} catch {return fallback;}};
const store = (storage,key,value) => {try {storage.setItem(key,JSON.stringify(value));} catch { /* Private browsing can disable storage. */ }};
let favorites = read(localStorage,'cq-favorites',[]);
if (!Array.isArray(favorites)) favorites=[];
favorites = favorites.filter(id=>typeof id==='string').slice(0,50);
function favoriteButtons() {
  $$('[data-favorite]').forEach(button=>{
    const yes=favorites.includes(button.dataset.favorite);
    button.setAttribute('aria-pressed',String(yes));button.textContent=yes?'♥':'♡';
    if (button.hasAttribute('data-detail-favorite')) button.setAttribute('aria-label',yes?'Retirer des favoris':'Ajouter aux favoris');
  });
}
async function favoriteList() {
  const list=$('#favorite-list'); if (!list) return;
  list.replaceChildren(); $('#favorites').hidden=favorites.length===0;
  for (const id of favorites) {
    try {
      const response=await fetch(`/venues/${encodeURIComponent(id)}`);if(!response.ok)continue;
      const venue=await response.json();
      const article=document.createElement('article');article.className='venue-card';
      const a=document.createElement('a');a.className='venue-link';a.href=`/v/${encodeURIComponent(id)}`;a.textContent=venue.name;
      const p=document.createElement('p');p.className='location';p.textContent=venue.zone || venue.region;
      article.append(a,p);list.append(article);
    } catch {break;}
  }
}
$$('[data-favorite]').forEach(button=>button.addEventListener('click',()=>{
  const id=button.dataset.favorite;
  favorites=favorites.includes(id)?favorites.filter(value=>value!==id):[...favorites,id].slice(-50);
  store(localStorage,'cq-favorites',favorites);favoriteButtons();favoriteList();
}));
favoriteButtons();favoriteList();

async function api(url,payload) {
  if (!navigator.onLine) throw new Error('Hors ligne : reconnectez-vous pour contribuer. Aucun envoi différé.');
  let response;
  try {
    response=await fetch(url,{method:payload===undefined?'GET':'POST',credentials:'same-origin',headers:payload===undefined?{}:{'Content-Type':'application/json','X-CQ-Request':'1'},body:payload===undefined?undefined:JSON.stringify(payload)});
  } catch {throw new Error('Connexion interrompue. Réessayer avec la même contribution.');}
  const data=await response.json();
  if (!response.ok) { const error=new Error(data.detail?.message || 'Action indisponible. Réessayez.'); error.status=response.status; throw error; }
  return data;
}
function currentState(state,now) {
  const estimates=state.estimates.filter(r=>Math.min(Date.parse(r.observed_at),Date.parse(r.received_at))+900000>now);
  if (!estimates.length) return {text:'Aucun signalement récent',detail:'L’attente est inconnue. Vous êtes sur place ? Partagez votre estimation.',kind:'unknown'};
  const values=estimates.map(r=>r.minutes).sort((a,b)=>a-b);
  const low=values[0],high=values.at(-1),count=values.length;
  const newest=Math.max(...estimates.map(r=>Math.min(Date.parse(r.observed_at),Date.parse(r.received_at))));
  const age=Math.max(0,Math.floor((now-newest)/60000));
  const remaining=Math.max(1,Math.ceil((Math.min(...estimates.map(r=>Math.min(Date.parse(r.observed_at),Date.parse(r.received_at))))+900000-now)/60000));
  // Counts devices, not people; a network (≈ same Wi-Fi/NAT) counts at most a few.
  const sources=new Set(estimates.map(r=>r.source)).size;
  const origin=count===1?'1 appareil · non confirmé':`${count} appareils · ${sources===1?'1 seul réseau':sources+' réseaux'}`;
  const others=(state.excluded_observed || []).filter(t=>Date.parse(t)+900000>now).length;
  const excluded=others?` · ${others} autre${others>1?'s':''} du même réseau non compté${others>1?'s':''}`:'';
  const detail=`${origin}${excluded} · dernier il y a ${age} min · actualisé au plus tard dans ${remaining} min`;
  if (high-low>15) return {text:`${low}–${high} min · avis divergents`,detail,kind:'conflicting'};
  const middle=count%2?values[Math.floor(count/2)]:(values[count/2-1]+values[count/2])/2;
  return {text:`${number(middle)} min`,detail,kind:count===1?'single':'recent',minutes:middle};
}
const cardStates=[];
$$('[data-card-wait]').forEach(async box=>{
  try {
    const state=await api(`/venues/${encodeURIComponent(box.dataset.cardWait)}/waits`);
    cardStates.push({box,state,received:performance.now(),now:Date.parse(state.server_now)});renderCards();
  } catch {box.lastElementChild.textContent='Attente non vérifiée';}
});
function renderCards() {
  cardStates.forEach(({box,state,received,now})=>{const v=currentState(state,now+performance.now()-received);box.lastElementChild.textContent=navigator.onLine?v.text:'Hors ligne · attente non vérifiée';});
}
let liveState=null,liveReceived=0,liveNow=0;
const page=$('[data-venue]');
const venue=page?.dataset.venue,queue=page?.dataset.queue;
const pendingKey=`cq-pending-${venue}`;
let pending=read(sessionStorage,pendingKey,null);
function displayState(state) {
  liveState=state;liveReceived=performance.now();liveNow=Date.parse(state.server_now);
  renderWait();renderObservations();
}
function renderWait() {
  if (!liveState || !page) return;
  const state=currentState(liveState,liveNow+performance.now()-liveReceived);
  $('#wait-value').textContent=navigator.onLine?state.text:'Attente non vérifiée';
  $('#wait-detail').textContent=navigator.onLine?state.detail:'Hors ligne : les signalements ne sont plus vérifiés. Reconnectez-vous pour actualiser.';
  $('#wait-box').dataset.state=navigator.onLine?state.kind:'unknown';
}
let observationSignature="";
function renderObservations() {
  const container=$('#observations');if (!container || !liveState) return;
  const now=liveNow+performance.now()-liveReceived;
  const reports=[...liveState.estimates.filter(r=>Math.min(Date.parse(r.observed_at),Date.parse(r.received_at))+900000>now),...liveState.completed.filter(r=>Math.min(Date.parse(r.observed_at),Date.parse(r.received_at))+3600000>now)];
  const signature=reports.map(r=>r.id).join(',');
  if (signature===observationSignature && container.dataset.loaded) return;
  observationSignature=signature;container.dataset.loaded='yes';container.replaceChildren();
  if (!reports.length) {const p=document.createElement('p');p.className='muted';p.textContent='Aucun retour récent.';container.append(p);return;}
  for (const report of reports) {
    const row=document.createElement('div');row.className='observation';
    const summary=document.createElement('div');summary.textContent=`${report.kind==='estimate'?'Estimation':'Attente personnelle terminée'} · ${report.minutes} min`;
    const small=document.createElement('small');small.textContent=`${report.kind==='completed'?'Terminée':'Observée'} à ${stamp(report.observed_at)}${report.source_window_start?' · début à '+stamp(report.source_window_start):''}${report.kind==='completed'?' · ne décrit pas la file actuelle':''}`;summary.append(small);
    const button=document.createElement('button');button.className='text-button';button.textContent='Signaler un abus';
    button.addEventListener('click',async()=>{try {await api(`/reports/${report.id}/flags`,{reason:'suspected_false'});$('#flag-status').textContent='Signalement transmis à la modération.';button.disabled=true;} catch(error) {$('#flag-status').textContent=error.message;}});
    row.append(summary,button);container.append(row);
  }
}
let activeTimer=null,startKey=read(sessionStorage,'cq-timer-key',null);
async function loadTimers() {
  try {const result=await api('/timers/active');activeTimer=result.items.find(t=>t.venue_id===venue) || null;renderTimer();} catch {$('#timer-status').textContent='Chronomètre non vérifié : reconnectez-vous.';}
}
function renderTimer() {
  if (!page) return;
  $('#timer-action').textContent=activeTimer?'Terminer mon attente':'Démarrer mon chronomètre';
  if (activeTimer) $('#timer-status').textContent=`Début à ${stamp(activeTimer.started_at)}. Cette durée sera publiée comme attente terminée.`;
}
if (page) {
  api(`/venues/${encodeURIComponent(venue)}/waits?queue_kind=${queue}`).then(displayState).catch(error=>{$('#wait-detail').textContent=error.message;});loadTimers();
  $('#open-report').addEventListener('click',()=>{$('#report-panel').hidden=false;$('#open-report').hidden=true;$('#report-panel').scrollIntoView({block:'nearest',behavior:'smooth'});if(pending){$('#minutes').value=pending.minutes;$('#confirm-report').textContent='Réessayer';}});
  $('#cancel-report').addEventListener('click',()=>{$('#report-panel').hidden=true;$('#open-report').hidden=false;});
  $$('[data-minutes]').forEach(button=>button.addEventListener('click',()=>{if(pending)return;$('#minutes').value=button.dataset.minutes;$$('[data-minutes]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));}));
  $$('input[name=kind]').forEach(input=>input.addEventListener('change',()=>{$('#report-question').textContent=input.value==='completed'?'Combien de minutes avez-vous personnellement attendu ? (Votre attente vient de se terminer.)':'Combien de temps attendrait quelqu’un qui rejoint la file maintenant ?';}));
  $('#report-form').addEventListener('submit',async event=>{
    event.preventDefault();const button=$('#confirm-report');button.disabled=true;$('#form-status').textContent='';
    try {
      if(!navigator.onLine) throw new Error('Hors ligne : reconnectez-vous pour contribuer. Aucun envoi différé.');
      if(!pending) {pending={kind:$('input[name=kind]:checked').value,minutes:Number($('#minutes').value),observed_at:new Date().toISOString(),queue_kind:queue,idempotency_key:crypto.randomUUID()};store(sessionStorage,pendingKey,pending);}
      const result=await api(`/venues/${encodeURIComponent(venue)}/reports`,pending);
      pending=null;sessionStorage.removeItem(pendingKey);displayState(result.waits);$('#report-panel').hidden=true;$('#open-report').hidden=false;button.textContent='Confirmer';
    } catch(error) {$('#form-status').textContent=error.message; if(error.status && error.status<500 && error.status!==429){pending=null;sessionStorage.removeItem(pendingKey);button.textContent='Confirmer';} else if(pending)button.textContent='Réessayer';}
    finally {button.disabled=false;}
  });
  $('#timer-action').addEventListener('click',async()=>{
    const button=$('#timer-action');button.disabled=true;
    try {
      if(activeTimer){const result=await api(`/timers/${activeTimer.id}/finish`,{});activeTimer=null;displayState(result.waits);$('#timer-status').textContent='Votre attente terminée a été enregistrée séparément.';}
      else {if(!startKey){startKey=crypto.randomUUID();store(sessionStorage,'cq-timer-key',startKey);}activeTimer=await api('/timers/start',{venue_id:venue,queue_kind:queue,idempotency_key:startKey});sessionStorage.removeItem('cq-timer-key');startKey=null;}
      renderTimer();
    } catch(error) {$('#timer-status').textContent=error.message;}
    finally {button.disabled=false;}
  });
}
function network() {networkStatus.hidden=navigator.onLine;renderWait();renderCards();}
window.addEventListener('offline',network);
window.addEventListener('online',()=>{network();if(page){api(`/venues/${encodeURIComponent(venue)}/waits?queue_kind=${queue}`).then(displayState).catch(()=>{});loadTimers();}});
setInterval(()=>{renderWait();renderCards();renderObservations();},1000);network();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
// Official hours use their own clock/source; no queue state can imply closure.
async function refreshHours() {
  for (const box of $$('[data-hours]')) {
    try {
      const h=await api(`/venues/${encodeURIComponent(box.dataset.hours)}/hours`);
      box.dataset.expiry=h.expires_at || '';
      box.querySelector('.hours-status').textContent=`${h.today==='open'?'Ouvert aujourd’hui':h.today==='closed'?'Fermé aujourd’hui':'Ouverture aujourd’hui inconnue'} · ${h.local_date} · ${h.timezone || 'Fuseau inconnu'}`;
      box.querySelector('.hours-now').textContent=h.now==='open'?'Ouvert maintenant':h.now==='closed'?'Fermé maintenant':'Ouverture maintenant non vérifiée';
      const intervals=box.querySelector('.hours-intervals');
      intervals.hidden=!h.intervals.length;
      intervals.textContent=`Service : ${h.intervals.join(' / ')}${h.freshness==='fresh'?'':' (horaire historique)'}`;
      box.querySelector('.hours-checked').textContent=h.checked_at?`Dernier relevé : ${new Date(h.checked_at).toLocaleString('fr-FR',{timeZone:'UTC',dateStyle:'short',timeStyle:'short'})} UTC · `:'';
      box.querySelector('a').href=h.official_url;
      box.querySelector('.hours-caveat').textContent=h.caveat;
    } catch {
      box.querySelector('.hours-status').textContent='Ouverture aujourd’hui non vérifiée';
      box.querySelector('.hours-now').textContent='Ouverture maintenant non vérifiée';
    }
  }
}
window.addEventListener('offline',refreshHours);
window.addEventListener('online',refreshHours);
setInterval(refreshHours,60000);
