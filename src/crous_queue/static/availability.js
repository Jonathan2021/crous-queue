'use strict';
(() => {
  const form=document.querySelector('#availability-form');if(!form)return;
  const root=document.querySelector('[data-venue]'),venue=root.dataset.venue,queue=root.dataset.queue;
  const status=document.querySelector('#availability-status'),button=document.querySelector('#availability-submit'),discard=document.querySelector('#availability-discard');
  const key=`cq-availability-pending-${venue}`;
  let pending=read(sessionStorage,key,null),data=null,now=0,received=0,signature='';
  const names={available:'Disponible',unavailable:'Temporairement indisponible',not_offered:'Non proposé ici',unknown:'Inconnu',conflicting:'Avis divergents'};
  function render(){
    if(!data)return;const instant=now+performance.now()-received;
    for(const [dimension,value] of Object.entries(data.dimensions)){
      const box=document.querySelector(`[data-dimension="${dimension}"]`);
      const fresh=value.observations.filter(o=>Date.parse(o.expires_at)>instant);
      const newest=Math.max(...fresh.map(o=>Date.parse(o.observed_at)));
      const cohort=fresh.filter(o=>Date.parse(o.observed_at)>=newest-120000),values=new Set(cohort.map(o=>o.value));
      const kind=!navigator.onLine || !cohort.length?'unknown':values.size>1?'conflicting':[...values][0];
      box.querySelector('.dimension-value').textContent=names[kind];box.dataset.state=kind;
      box.querySelector('.dimension-age').textContent=!navigator.onLine?'Hors ligne · non vérifié':!cohort.length?'Aucune observation récente':`${cohort.length} observation${cohort.length>1?'s':''} · il y a ${Math.max(0,Math.floor((instant-newest)/60000))} min · valable ${dimension==='seating'?5:10} min`;
    }
    const comments=navigator.onLine?data.comments.filter(c=>Date.parse(c.expires_at)>instant):[];
    const next=comments.map(c=>c.id).join(',');const list=document.querySelector('#comments');
    if(next===signature && list.dataset.loaded)return;signature=next;list.dataset.loaded='yes';list.replaceChildren();
    if(!comments.length){const p=document.createElement('p');p.textContent='Aucun commentaire récent approuvé.';list.append(p);}
    for(const comment of comments){const row=document.createElement('article');row.className='observation';const text=document.createElement('p');text.textContent=comment.text;const age=document.createElement('small');age.textContent=`Observation à ${stamp(comment.observed_at)} · expire une heure après l’observation`;const flag=document.createElement('button');flag.className='text-button';flag.textContent='Signaler ce commentaire';flag.addEventListener('click',async()=>{try{await api(`/reports/${comment.id}/flags`,{reason:'suspected_false'});status.textContent='Signalement transmis à la modération.';}catch(e){status.textContent=e.message;}});row.append(text,age,flag);list.append(row);}
  }
  function display(value){data=value;now=Date.parse(value.server_now);received=performance.now();render();}
  async function load(){try{display(await api(`/venues/${encodeURIComponent(venue)}/availability?queue_kind=${queue}`));}catch{data=null;document.querySelector('#comments').textContent='Commentaires non vérifiés. Actualisez après reconnexion.';document.querySelectorAll('[data-dimension] .dimension-value').forEach(el=>el.textContent='Non vérifié');status.textContent='Observations indisponibles. Reconnectez-vous et actualisez.';}}
  function controls(){button.textContent=pending?'Réessayer ces observations':'Partager ces observations';discard.hidden=!pending;for(const field of form.querySelectorAll('select,textarea'))field.disabled=Boolean(pending);}
  controls();
  if(pending){status.textContent='Une tentative attend votre action. La date originale sera conservée.';for(const [name,value] of Object.entries(pending))if(form.elements[name])form.elements[name].value=value;}
  discard.addEventListener('click',()=>{pending=null;sessionStorage.removeItem(key);controls();status.textContent='Tentative abandonnée. Elle a pu être reçue : actualisez avant un nouveau signalement.';load();});
  form.addEventListener('submit',async event=>{
    event.preventDefault();button.disabled=true;
    try{
      if(!navigator.onLine)throw new Error('Hors ligne : aucun envoi différé. Reconnectez-vous.');
      if(!pending){const fields=Object.fromEntries(new FormData(form));const payload={kind:'availability',queue_kind:queue,observed_at:new Date().toISOString(),idempotency_key:crypto.randomUUID()};for(const [name,value] of Object.entries(fields))if(value.trim())payload[name]=value.trim();pending=payload;store(sessionStorage,key,pending);}
      const result=await api(`/venues/${encodeURIComponent(venue)}/reports`,pending);
      pending=null;sessionStorage.removeItem(key);form.reset();display(result.availability);
      status.textContent=result.report.comment_status==='pending'?'Observations reçues. Votre commentaire attend la modération.':'Observations reçues. Leur date de constat est conservée.';
    }catch(error){status.textContent=error.message;if(error.status && error.status<500 && error.status!==429){pending=null;sessionStorage.removeItem(key);}}
    finally{button.disabled=false;controls();}
  });
  document.querySelector('#availability-refresh').addEventListener('click',load);
  setInterval(render,1000);window.addEventListener('offline',render);window.addEventListener('online',load);load();
})();
