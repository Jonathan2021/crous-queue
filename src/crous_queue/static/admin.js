'use strict';
let adminKey='',offset=0;
const status=document.querySelector('#admin-status');
async function adminApi(url,payload) {
  const response=await fetch(url,{method:payload?'POST':'GET',headers:{'Authorization':'Bearer '+adminKey,...(payload?{'Content-Type':'application/json','X-CQ-Request':'1'}:{})},body:payload?JSON.stringify(payload):undefined});
  const data=await response.json();if(!response.ok)throw new Error(data.detail?.message || 'Action indisponible.');return data;
}
async function loadAdmin(reset=false) {
  try {
    if(reset){offset=0;document.querySelector('#admin-list').replaceChildren();}
    const data=await adminApi(`/admin/reports?offset=${offset}`);
    for(const report of data.items){
      const card=document.createElement('article');card.className='venue-card';
      const h=document.createElement('h2');h.textContent=`${report.venue_id} · ${report.minutes} min`;
      const p=document.createElement('p');p.textContent=`${report.kind} · ${report.queue_kind} · ${report.flag_count} abus · ${report.visibility} · ${report.received_at}`;
      const history=document.createElement('p');history.className='muted';history.textContent=report.history.map(h=>`${h.action} : ${h.rationale}`).join(' / ');
      const input=document.createElement('input');input.placeholder='Motif (sans donnée personnelle)';input.minLength=8;input.maxLength=500;input.setAttribute('aria-label','Motif de modération');
      const button=document.createElement('button');button.className='secondary';button.textContent='Masquer';button.disabled=report.visibility==='hidden';
      button.addEventListener('click',async()=>{try{await adminApi(`/admin/reports/${report.id}/hide`,{rationale:input.value,expected_version:report.version});status.textContent='Signalement masqué, historique enregistré.';await loadAdmin(true);}catch(error){status.textContent=error.message;}});
      card.append(h,p,history,input,button);document.querySelector('#admin-list').append(card);
    }
    offset=data.next_offset;document.querySelector('#admin-more').hidden=offset===null;
    const metrics=await adminApi('/admin/metrics');document.querySelector('#admin-metrics').textContent=`${metrics.reports_total} retours conservés · ${metrics.fresh_venue_queues} files avec retour récent · ${metrics.returning_devices_7d} appareils revenus sur plusieurs jours`;
  }catch(error){status.textContent=error.message;}
}
document.querySelector('#admin-login').addEventListener('submit',event=>{event.preventDefault();adminKey=document.querySelector('#admin-key').value;document.querySelector('#admin-key').value='';loadAdmin(true);});
document.querySelector('#admin-more').addEventListener('click',()=>loadAdmin());
