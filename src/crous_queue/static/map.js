'use strict';
(() => {
  const root=document.querySelector('.map-page');if(!root)return;
  const form=document.querySelector('#map-search'),list=document.querySelector('#map-list');
  const error=document.querySelector('#map-error'),status=document.querySelector('#location-status');
  const queues={student:'File étudiante',staff:'File personnel',unspecified:'File non précisée'};
  let items=[],received=0,serverNow=0,loc=null,map=null,groups=[],rows=new Map();
  function node(tag,text,className) {const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e;}
  function band(value) {return value.minutes===undefined?'unknown':value.minutes===0?'zero':value.minutes<=5?'low':value.minutes<=10?'medium':value.minutes<=20?'high':'busy';}
  function value(v) {return navigator.onLine?currentState(v.waits,serverNow+performance.now()-received):{text:'Hors ligne · attente non vérifiée',detail:'Reconnectez-vous pour actualiser.',kind:'unknown'};}
  function hoursText(v) {
    const h=v.hours,now=serverNow+performance.now()-received;
    if(!navigator.onLine || (h.expires_at && Date.parse(h.expires_at)<=now))return 'Ouverture aujourd’hui non vérifiée';
    return `${h.today==='open'?'Ouvert aujourd’hui':h.today==='closed'?'Fermé aujourd’hui':'Ouverture aujourd’hui inconnue'} · ${frDate(h.local_date)} · ${h.intervals.join(' / ') || 'horaires non renseignés'}${h.freshness==='stale'?' (anciens, non vérifiés)':h.freshness==='conflict'?' (sources divergentes)':''} · ${h.timezone || 'fuseau inconnu'} · dernier relevé ${h.checked_at ? frDate(h.checked_at) : 'inconnu'}. ${h.caveat}`;
  }
  function distance(v) {if(!v.has_coordinates)return ' · coordonnées indisponibles';if(!loc)return '';return ` · environ ${number(L.latLng(loc).distanceTo([v.latitude,v.longitude])/1000)} km`;}
  function card(v) {
    const article=node('article','', 'venue-card');article.dataset.mapVenue=v.id;
    const a=node('a',v.name,'venue-link');a.href=`/v/${encodeURIComponent(v.id)}`;
    article.append(node('span',v.venue_type,'type-pill'),a,node('p',queues[v.queue_kind],'queue-label'),node('p','','map-wait'),node('p','','micro map-age'),node('p','','map-hours'));
    const source=node('a','Source officielle ↗');source.href=v.hours.official_url;source.rel='noreferrer';article.append(source);
    if(map && v.has_coordinates){const center=node('button','Voir le repère','text-button');center.addEventListener('click',()=>{map.setView([v.latitude,v.longitude],16);const g=groups.find(g=>g.items.some(item=>item.id===v.id));g?.marker.openPopup();});article.append(center);}
    return article;
  }
  function update() {
    for(const v of items){const row=rows.get(v.id);if(!row)continue;const val=value(v),wait=row.querySelector('.map-wait');wait.className=`map-wait crowd-${band(val)}`;wait.textContent=val.text+distance(v);row.querySelector('.map-age').textContent=val.detail;row.querySelector('.map-hours').textContent=hoursText(v);}
    for(const g of groups){popupText(g);paint(g);}
  }
  function label(val){return val.minutes===undefined?'?':number(val.minutes);}
  function paint(g){
    const values=g.items.map(value),element=g.marker.getElement();if(!element)return;
    // Fresh observations stay on top of overlapping unknown markers.
    const known=values.some(v=>v.minutes!==undefined);if(g.raised!==known){g.raised=known;g.marker.setZIndexOffset(known?1000:0);}
    element.setAttribute('aria-label',g.items.map((v,i)=>`${v.name}, ${values[i].text}`).join(' ; '));
    if(values.length===1){const b=band(values[0]);element.className=`leaflet-marker-icon crowd-marker crowd-${b} leaflet-zoom-animated leaflet-interactive`;element.dataset.band=b;element.textContent=label(values[0]);return;}
    // One segment per venue at a shared address: distinct identities are never pooled.
    element.className='leaflet-marker-icon crowd-marker crowd-shared leaflet-zoom-animated leaflet-interactive';delete element.dataset.band;
    const order=values.map((_,i)=>i).sort((a,b)=>(values[a].minutes===undefined)-(values[b].minutes===undefined));
    const shown=order.length>4?3:order.length;
    const parts=order.slice(0,shown).map(i=>{const s=node('span',label(values[i]),`crowd-segment crowd-${band(values[i])}`);s.dataset.segmentVenue=g.items[i].id;return s;});
    if(order.length>shown)parts.push(node('span',`+${order.length-shown}`,'crowd-segment crowd-unknown'));
    const signature=parts.map(p=>`${p.dataset.segmentVenue}:${p.className}:${p.textContent}`).join('|');
    if(element.dataset.segments!==signature){element.dataset.segments=signature;element.replaceChildren(...parts);}
  }
  function renderList(){
    const visible=items.filter(v=>!v.has_coordinates || !map || map.getBounds().contains([v.latitude,v.longitude]));
    const ids=visible.map(v=>v.id).join(',');
    if(list.dataset.ids!==ids){list.dataset.ids=ids;list.replaceChildren();rows=new Map();for(const v of visible){const el=card(v);rows.set(v.id,el);list.append(el);}}
    document.querySelector('#map-count').textContent=`${visible.length} lieu${visible.length===1?'':'x'}`;
    error.textContent=visible.length?'':'Aucun lieu dans cette zone. Déplacez la carte ou cherchez une ville.';update();
  }
  function popupText(g){if(!g.popup)return;for(const v of g.items){const row=[...g.popup.children].find(el=>el.dataset?.popupVenue===v.id);if(row){row.querySelector('.popup-wait').textContent=`${queues[v.queue_kind]} · ${value(v).text}`;row.querySelector('.popup-hours').textContent=hoursText(v);}}}
  function markers(){
    if(!map)return;
    for(const g of groups)g.marker.remove();groups=[];
    const grouped=new Map();for(const v of items.filter(v=>v.has_coordinates)){const key=`${v.latitude},${v.longitude}`;if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(v);}
    for(const venues of grouped.values()){
      const first=venues[0],segments=venues.length>1?Math.min(venues.length,4):0,size=segments?[segments*28+4,34]:[38,38];
      const marker=L.marker([first.latitude,first.longitude],{icon:L.divIcon({className:'crowd-marker crowd-unknown',html:'?',iconSize:size,iconAnchor:[size[0]/2,size[1]/2]}),keyboard:true}).addTo(map);
      const group={items:venues,marker,popup:null};
      marker.bindPopup(()=>{const panel=node('div','','map-popup');for(const v of venues){const row=node('div','');row.dataset.popupVenue=v.id;const a=node('a',`${v.name} → voir / signaler`);a.href=`/v/${encodeURIComponent(v.id)}`;row.append(a,node('p','','popup-wait'),node('p','','micro popup-hours'));panel.append(row);}group.popup=panel;popupText(group);return panel;},{maxWidth:230,minWidth:160,maxHeight:200,autoPanPadding:[30,30]});
      groups.push(group);
    }
  }
  async function load(fit=false){
    error.textContent='Chargement…';
    try{const params=new URLSearchParams(new FormData(form));const data=await api(`/map-data?${params}`);items=data.items;received=performance.now();serverNow=Date.parse(data.server_now);list.dataset.ids='';markers();
      if(map && fit && items.some(v=>v.has_coordinates))map.fitBounds(items.filter(v=>v.has_coordinates).map(v=>[v.latitude,v.longitude]),{padding:[35,35],maxZoom:15});
      renderList();if(data.truncated)error.textContent='Résultats limités à 2 000 lieux. Précisez la région.';
    }catch{error.textContent='Données indisponibles. Réessayez ou ouvrez l’annuaire.';items=[];markers();list.replaceChildren();rows.clear();}
  }
  if(typeof L!=='undefined'){
    map=L.map('venue-map',{scrollWheelZoom:false}).setView([48.846,2.35],14);
    if(root.dataset.tiles==='osm'){
      const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,referrerPolicy:'strict-origin-when-cross-origin',attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});
      tiles.on('tileerror',()=>{document.querySelector('#tile-status').textContent='Fond de carte indisponible. Les repères et la liste restent utilisables.';});tiles.addTo(map);
    }else document.querySelector('#tile-status').textContent='Fond externe désactivé. Repères et liste disponibles.';
    map.on('moveend',renderList);
    new ResizeObserver(()=>{map.invalidateSize();}).observe(document.querySelector('#venue-map'));
  }else document.querySelector('#tile-status').textContent='Carte indisponible. Tous les lieux restent accessibles dans la liste.';
  form.addEventListener('submit',event=>{event.preventDefault();load(true);});
  document.querySelector('#map-refresh').addEventListener('click',()=>load(false));
  document.querySelector('#locate').addEventListener('click',()=>{
    if(!map || !navigator.geolocation){status.textContent='Localisation indisponible. Recherchez une ville ou déplacez la carte.';return;}
    status.textContent='Localisation en cours…';
    navigator.geolocation.getCurrentPosition(position=>{
      // Round immediately. Never send or persist the precise browser coordinate.
      loc=[Math.round(position.coords.latitude*100)/100,Math.round(position.coords.longitude*100)/100];
      map.setView(loc,14);status.textContent='Carte centrée approximativement. Position non conservée.';renderList();
    },()=>{status.textContent='Localisation refusée ou indisponible. Recherchez une ville ou déplacez la carte.';},{enableHighAccuracy:false,timeout:8000,maximumAge:60000});
  });
  const initial=new URLSearchParams(location.search);for(const name of ['q','region','type'])if(initial.has(name))form.elements[name].value=initial.get(name);
  load(Boolean(initial.toString()));setInterval(update,1000);window.addEventListener('offline',update);
})();
