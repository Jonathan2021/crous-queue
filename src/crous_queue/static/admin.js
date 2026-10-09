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
      const h=document.createElement('h2');h.textContent=`${report.venue_id} · ${report.minutes===null?"Observation sans attente":report.minutes+" min"}`;
      const p=document.createElement('p');p.textContent=`${report.kind} · ${report.queue_kind} · réseau ${report.network_label || 'inconnu'} · ${report.flag_count} abus · ${report.visibility} · ${report.received_at}`;
      const history=document.createElement('p');history.className='muted';history.textContent=report.history.map(h=>`${h.action} : ${h.rationale}`).join(' / ');
      const input=document.createElement('input');input.placeholder='Motif (sans donnée personnelle)';input.minLength=8;input.maxLength=500;input.setAttribute('aria-label','Motif de modération');
      const button=document.createElement('button');button.className='secondary';button.textContent='Masquer';button.disabled=report.visibility==='hidden';
      button.addEventListener('click',async()=>{try{await adminApi(`/admin/reports/${report.id}/hide`,{rationale:input.value,expected_version:report.version});status.textContent='Signalement masqué, historique enregistré.';await loadAdmin(true);}catch(error){status.textContent=error.message;}});
      const comment=document.createElement('p');comment.className='admin-comment';comment.textContent=`Commentaire (${report.comment_status || 'none'}) : ${report.comment || 'aucun'}`;
      const dimensions=document.createElement('p');dimensions.textContent=Object.entries(report.availability || {}).filter(([,v])=>v!==null).map(([k,v])=>`${k}: ${v}`).join(' · ');
      const bulk=document.createElement('button');bulk.className='secondary';bulk.textContent='Masquer ce réseau (2 h)';bulk.disabled=!report.network_label;
      bulk.title='Masque tous les retours visibles de ce réseau approximatif reçus depuis 2 heures, y compris des voisins légitimes (NAT).';
      bulk.addEventListener('click',async()=>{try{const result=await adminApi(`/admin/reports/${report.id}/hide-network`,{rationale:input.value});status.textContent=`${result.hidden} retour(s) masqué(s) pour ce réseau, historique enregistré.`;await loadAdmin(true);}catch(error){status.textContent=error.message;}});
      card.append(h,p,dimensions,comment,history,input,button,bulk);
      if(report.comment)for(const [action,label] of [['approve','Approuver le commentaire'],['hide','Masquer le commentaire'],['delete','Supprimer le texte']]){
        if(report.visibility==='hidden' && action!=='delete')continue;
        const control=document.createElement('button');control.className='secondary';control.textContent=label;
        control.addEventListener('click',async()=>{try{await adminApi(`/admin/reports/${report.id}/comment`,{action,rationale:input.value,expected_version:report.version});status.textContent='Modération du commentaire enregistrée.';await loadAdmin(true);}catch(error){status.textContent=error.message;}});card.append(control);
      }document.querySelector('#admin-list').append(card);
    }
    offset=data.next_offset;document.querySelector('#admin-more').hidden=offset===null;
    const metrics=await adminApi('/admin/metrics');document.querySelector('#admin-metrics').textContent=`${metrics.reports_total} retours conservés · ${metrics.fresh_venue_queues} files avec retour récent · ${metrics.returning_devices_7d} appareils revenus sur plusieurs jours`;
  }catch(error){status.textContent=error.message;}
}
document.querySelector('#admin-login').addEventListener('submit',event=>{event.preventDefault();adminKey=document.querySelector('#admin-key').value;document.querySelector('#admin-key').value='';loadAdmin(true);});
document.querySelector('#admin-more').addEventListener('click',()=>loadAdmin());
