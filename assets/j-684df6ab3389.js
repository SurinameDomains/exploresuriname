
(function(){
'use strict';
var D=document,W=window;
var LANG=(D.documentElement.lang||'en').slice(0,2).toLowerCase();
var I=W.FL_I18N||{},T=Object.assign({},I.en||{},I[LANG]||{});
var LOC={en:'en-GB',nl:'nl-NL',es:'es-ES',zh:'zh-CN',fr:'fr-FR',pt:'pt-BR'}[LANG]||'en-GB';
var CFG=W.FL_CFG||{},DATA=W.FL_DATA||{flights:[]};
var PFX=(LANG==='en'?'':'/'+LANG);
function tr(k,o){var s=(T[k]!=null?T[k]:k);if(o){for(var x in o){s=s.split('{'+x+'}').join(o[x]);}}return s;}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function now(){return Math.floor(Date.now()/1000);}
function pad(n){return(n<10?'0':'')+n;}
function hm(ts){if(!ts)return'';var d=new Date((ts-10800)*1000);return pad(d.getUTCHours())+':'+pad(d.getUTCMinutes());}
function hmz(ts,oz){if(oz==null)return hm(ts);var d=new Date((ts+oz)*1000);return pad(d.getUTCHours())+':'+pad(d.getUTCMinutes());}
function srDay(ts){return Math.floor((ts-10800)/86400);}
function lsGet(k,d){try{var v=localStorage.getItem(k);return v==null?d:JSON.parse(v);}catch(e){return d;}}
function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
function tval(r){return r.a||r.e||r.s;}
function shown(r,n){var st=r.st||'scheduled';if(r.d==='D'&&r.brd==='Open'&&(st==='scheduled'||st==='delayed'))return'boarding';if(st==='scheduled'&&r.e)return'ontime';if(st==='scheduled'&&tval(r)<n-1200)return'unknown';return st;}
function dur(sec){sec=Math.abs(sec);var h=Math.floor(sec/3600),m=Math.round((sec%3600)/60);if(m===60){h++;m=0;}
  if(h&&m)return h+tr('h')+' '+m+' '+tr('m');if(h)return h+tr('h');return Math.max(1,m)+' '+tr('m');}
function relT(ts,n){var d=ts-n;if(Math.abs(d)<60)return tr('now');return d>0?tr('in',{t:dur(d)}):tr('ago',{t:dur(d)});}
function dayLabel(ts,n){var d=srDay(ts)-srDay(n);if(d===0)return tr('today');if(d===1)return tr('tomorrow');if(d===-1)return tr('yesterday');
  try{return new Intl.DateTimeFormat(LOC,{weekday:'long',day:'numeric',month:'long',timeZone:'America/Paramaribo'}).format(new Date(ts*1000));}catch(e){return'';}}
function route(r){var me=(r.ap==='EAX'?'Paramaribo':'Paramaribo');return r.d==='A'?(r.on+' → '+me):(me+' → '+r.on);}
function pillTxt(r,n){var st=shown(r,n),t=tr(st);if(st==='delayed'&&r.dl)t+=' +'+r.dl+' '+tr('min');return t;}
function isFinal(r){return r.st==='landed'||r.st==='departed'||r.st==='cancelled'||r.st==='diverted';}
function pageUrl(r){return (CFG.pages||DATA.pages||[]).indexOf(r.sl)>=0?(PFX+'/'+r.sl):(PFX+'/flights#f='+encodeURIComponent(r.k));}
var tracked=lsGet('fl-track',[]);if(!Array.isArray(tracked))tracked=[];
var notifyOn=lsGet('fl-notify',false);
function isTracked(k){return tracked.indexOf(k)>=0;}
var toastT;function toast(msg){var t=D.getElementById('fl-toast');if(!t)return;t.textContent=msg;t.hidden=false;clearTimeout(toastT);toastT=setTimeout(function(){t.hidden=true;},3600);}
function ga(ev,p){try{if(W.gtag)W.gtag('event',ev,p||{});}catch(e){}}

/* ── row + details markup ── */
function rowHtml(r,n,open){var st=shown(r,n),t=tval(r),big=hm(t),small=Math.abs(t-r.s)>=300?hm(r.s):'';
  var p1=srDay(t)>srDay(n)+1?'':'';var cs=r.cs&&r.cs.length?' · '+r.cs.join(', '):'';
  var via=r.via&&r.via.length?'<span class="fr-sub">'+esc((r.vfirst?tr('alsoFrom'):tr('cont'))+' '+r.via.join(', '))+'</span>':'';
  var past=(isFinal(r)&&t<n-1800)?' past':'';
  return '<li class="fr'+past+'" data-k="'+esc(r.k)+'"><button class="fr-main" type="button" aria-expanded="'+(open?'true':'false')+'">'+
   '<span class="fr-time" translate="no"><b>'+big+p1+'</b>'+(small?'<s>'+small+'</s>':'')+'</span>'+
   '<span class="fr-mid"><span class="fr-city" translate="no">'+esc(r.on||r.oi)+'<small>'+esc(r.oi||'')+'</small></span>'+
   '<span class="fr-fn" translate="no">'+(isTracked(r.k)?'<span class="tk">★</span> ':'')+esc(r.fn)+' · '+esc(r.al||'')+esc(cs)+'</span>'+via+'</span>'+
   '<span class="fr-st"><span class="pill p-'+st+'">'+esc(pillTxt(r,n))+'</span>'+subLine(r,n)+'</span></button>'+
   '<div class="fr-det"'+(open?'':' hidden')+'>'+(open?detHtml(r,n):'')+'</div></li>';}
function subLine(r,n){var st=shown(r,n),t=tval(r);
  if(st==='landed'||st==='departed'){if(r.dl!=null&&Math.abs(r.dl)>=5)return'<span class="fr-sub">'+esc(r.dl>0?tr('late',{n:r.dl}):tr('early',{n:-r.dl}))+'</span>';return'';}
  if(st==='cancelled'||st==='unknown')return'';
  if(t>n&&t-n<6*3600)return'<span class="fr-sub">'+esc(relT(t,n))+'</span>';return'';}
function fact(k,v){return v?'<div><dt>'+esc(tr(k))+'</dt><dd translate="no">'+v+'</dd></div>':'';}
function detHtml(r,n){var me=r.ap, oth=r.oi;
  var depS=r.d==='D'?r.s:r.sd, arrS=r.d==='A'?r.s:r.sa;
  var g='<dl class="fd-grid">';
  g+=fact('sched',esc(hm(r.s)));
  if(r.e&&!r.a&&Math.abs(r.e-r.s)>=60)g+=fact('exp',esc(hm(r.e)));
  if(r.a)g+=fact('act',esc(hm(r.a)));
  if(r.sd&&r.sa&&r.sa>r.sd)g+=fact('dur',esc(dur(r.sa-r.sd)));
  if(r.belt&&r.d==='A')g+=fact('belt',esc(r.belt));
  if(r.ao)g+=fact(r.d==='A'?'tookoff':'landedAt2',esc(oth+' '+hmz(r.ao,r.oz))+' <small>'+esc(r.oz!=null?tr('local'):'SR')+'</small>');
  else if(r.d==='A'&&r.sd)g+=fact('dep',esc(oth+' '+hmz(r.sd,r.oz))+' <small>'+esc(r.oz!=null?tr('local'):'SR')+'</small>');
  else if(r.d==='D'&&r.sa)g+=fact('arr',esc(oth+' '+hmz(r.sa,r.oz))+' <small>'+esc(r.oz!=null?tr('local'):'SR')+'</small>');
  g+=fact('aircraft',esc(r.ac||''));g+=fact('reg',esc(r.rg||''));
  if(r.gate)g+=fact('gate',esc(r.gate));
  if(r.d==='D'&&r.chk&&!isFinal(r))g+=fact('checkin',esc(tr('cs_'+r.chk.toLowerCase().replace(/\s+/g,''))));
  if(r.d==='D'&&r.brd&&!isFinal(r))g+=fact('boardingL',esc(tr('cs_'+r.brd.toLowerCase().replace(/\s+/g,''))));
  if(r.cs&&r.cs.length)g+=fact('codeshare',esc(r.cs.join(', ')));
  g+='</dl>';
  if(r.why&&((r.dl||0)>=5||r.st==='cancelled'))g+='<p class="fd-why"><b>'+esc(tr('reason'))+(LANG==='fr'?'\u00a0:':':')+'</b> <span lang="en">'+esc(r.why)+'</span></p>';
  var on=isTracked(r.k);
  var a='<div class="fd-acts">'+
   '<button class="fbtn'+(on?' on':'')+'" data-act="track" type="button">★ '+esc(tr(on?'tracking':'track'))+'</button>'+
   (('Notification' in W)?'<button class="fbtn'+(notifyOn&&W.Notification.permission==='granted'?' on':'')+'" data-act="notify" type="button">'+esc(tr(notifyOn&&W.Notification.permission==='granted'?'notifyOn':'notify'))+'</button>':'')+
   '<button class="fbtn wa" data-act="share" type="button">'+esc(tr('share'))+'</button>'+
   '<a class="fbtn" data-act="cal" target="_blank" rel="noopener" href="'+esc(calUrl(r))+'">'+esc(tr('cal'))+'</a>'+
   (CFG.mode!=='flight'?'<a class="fbtn" href="'+esc(pageUrl(r))+'">'+esc(tr('page'))+' →</a>':'')+
   (r.site?'<a class="fbtn" target="_blank" rel="noopener" href="'+esc(r.site)+'">'+esc(tr('airline'))+' ↗</a>':'')+
   '</div>';
  return g+a+(r.d==='A'?pickupHtml(r,n):checkinHtml(r,n));}
function driveList(ap){return (CFG.drive||{})[ap]||[];}
function placeSel(ap,cls){var L=driveList(ap),cur=lsGet('fl-from-'+ap,L.length?L[0][0]:'');
  return '<select class="'+cls+'">'+L.map(function(x){return'<option value="'+x[0]+'"'+(x[0]===cur?' selected':'')+'>'+esc(tr('d_'+x[0]))+'</option>';}).join('')+'</select>';}
function driveMin(ap,id){var L=driveList(ap);for(var i=0;i<L.length;i++)if(L[i][0]===id)return L[i][2];return L.length?L[0][2]:50;}
function exitWin(r){var big=r.oi==='AMS'||/777|787|A330|A350|747|767|A340/.test(r.ac||'');if(r.ap==='EAX')return[10,25];return big?[30,60]:[20,40];}
function pickupHtml(r,n){if(r.st==='cancelled')return'';var L=driveList(r.ap);if(!L.length)return'';
  return '<div class="pk" data-pk="1"><h4>'+esc(tr('pkH'))+'</h4><label>'+esc(tr('pkFrom'))+' '+placeSel(r.ap,'pk-from')+'</label><p class="res" aria-live="polite">'+pickupRes(r,n)+'</p>'+
   '<p class="note">'+esc(tr('pkNote'))+'</p><p style="margin:.5rem 0 0"><a class="fbtn" target="_blank" rel="noopener" href="https://waze.com/ul?ll='+(CFG.coords||{})[r.ap]+'&navigate=yes">'+esc(tr('pkWaze'))+' ↗</a></p></div>';}
function pickupRes(r,n,from){var cur=from||lsGet('fl-from-'+r.ap,(driveList(r.ap)[0]||[''])[0]);var land=r.a||r.e||r.s,w=exitWin(r),dm=driveMin(r.ap,cur);
  var outA=land+w[0]*60,outB=land+w[1]*60,leave=outA-dm*60;
  var s='<span>'+esc(r.a?tr('pkLanded'):tr('pkLands'))+'</span> <b translate="no">'+hm(land)+'</b> · <span>'+esc(tr('pkOut'))+'</span> <b translate="no">'+hm(outA)+'–'+hm(outB)+'</b>';
  if(dm>0&&outB>n){s+='<br><span>'+esc(leave<=n?tr('pkLeaveNow'):tr('pkLeave'))+'</span>'+(leave<=n?'':' <b translate="no">'+hm(leave)+'</b>');}
  return s;}
function checkinHtml(r,n){if(r.st==='cancelled'||r.st==='departed'||r.ap!=='PBM')return'';
  var ci=(CFG.checkin||{})[r.oi]||(CFG.checkin||{})._||[3,2],open=r.s-ci[0]*3600,close=r.s-ci[1]*3600,be=close-1800;
  if(close<n)return'';
  return '<div class="pk" data-ci="1"><h4>'+esc(tr('ciH'))+'</h4><p class="res"><span>'+esc(tr('ciWin'))+'</span> <b translate="no">'+hm(open)+'–'+hm(close)+'</b> · <span>'+esc(tr('ciBe'))+'</span> <b translate="no">'+hm(be)+'</b></p>'+
   '<label>'+esc(tr('pkFrom'))+' '+placeSel(r.ap,'ci-from')+'</label><p class="res ci-leave">'+ciLeave(r,n,be)+'</p><p class="note">'+esc(tr('ciNote'))+'</p></div>';}
function ciLeave(r,n,be,from){var cur=from||lsGet('fl-from-'+r.ap,(driveList(r.ap)[0]||[''])[0]),dm=driveMin(r.ap,cur);if(dm<=0)return'';var lv=be-dm*60;
  return '<span>'+esc(lv<=n?tr('pkLeaveNow'):tr('pkLeave'))+'</span>'+(lv<=n?'':' <b translate="no">'+hm(lv)+'</b>');}
function gcal(ts){var d=new Date(ts*1000);return d.getUTCFullYear()+pad(d.getUTCMonth()+1)+pad(d.getUTCDate())+'T'+pad(d.getUTCHours())+pad(d.getUTCMinutes())+'00Z';}
function calUrl(r){var t=r.d==='A'?(r.e||r.s):r.s;var title=r.fn+' '+route(r);
  return 'https://calendar.google.com/calendar/render?action=TEMPLATE&text='+encodeURIComponent(title)+'&dates='+gcal(t-(r.d==='D'?3*3600:0))+'/'+gcal(t+(r.d==='A'?3600:0))+'&details='+encodeURIComponent(tr('seeLive')+': '+location.origin+pageUrl(r));}
function shareText(r,n){var st=shown(r,n),s=pillTxt(r,n);if(st==='landed')s=tr('landedAt',{t:hm(r.a||r.e||r.s)});else if(st==='departed')s=tr('departedAt',{t:hm(r.a||r.e||r.s)});else if(st!=='cancelled')s+=' · '+hm(tval(r))+' SR';
  return tr('shareText',{fn:r.fn,route:route(r),status:s});}

/* ── data helpers ── */
var SITES=CFG.sites||{};
function rows(){var L=(DATA.flights||[]);L.forEach(function(r){if(!r.site&&SITES[r.ai])r.site=SITES[r.ai];});return L;}
function byKey(k){var L=rows();for(var i=0;i<L.length;i++)if(L[i].k===k)return L[i];return null;}

/* ── live line ── */
function liveLine(){var el=D.getElementById('fl-live');if(!el)return;var n=now(),ap=CFG.mode==='flight'?(CFG.ap||'PBM'):state.ap;var a=(DATA.airports||{})[ap]||{};
  var asof=a.as_of||DATA.built,stale=!asof||(n-asof)>(DATA.stale_after_min||75)*60;
  el.className='fl-live'+(stale?' off':'');
  el.innerHTML='<span class="dot" aria-hidden="true"></span><b>'+esc(stale?tr('liveOld'):tr('liveOk'))+'</b><span>'+esc(tr('upd',{t:relT(asof||n,n)}))+'</span>';}

/* ── BOARD ── */
var state={ap:'PBM',d:'A',q:'',cg:false,earlier:false,open:null};
function initState(){var u=new URLSearchParams(location.search);var ap=(u.get('ap')||lsGet('fl-ap','PBM')+'').toUpperCase(),d=(u.get('d')||lsGet('fl-d','A')+'').toUpperCase();
  state.ap=(ap==='EAX'?'EAX':'PBM');state.d=(d==='D'||d==='DEP'?'D':'A');state.cg=!!lsGet('fl-cg',false);
  var h=/#f=([^&]+)/.exec(location.hash);if(h){var k=decodeURIComponent(h[1]),r=byKey(k);if(r){state.ap=r.ap;state.d=r.d;state.open=k;state.earlier=true;}}}
function filtered(){var n=now(),q=state.q.trim().toLowerCase();
  return rows().filter(function(r){if(r.ap!==state.ap||r.d!==state.d)return false;if(r.cg&&!state.cg&&!isTracked(r.k))return false;
    if(q){var hay=(r.fn+' '+(r.al||'')+' '+(r.on||'')+' '+(r.oi||'')+' '+(r.cs||[]).join(' ')+' '+(r.via||[]).join(' ')).toLowerCase();if(hay.indexOf(q)<0)return false;}
    return tval(r)>=n-12*3600;}).sort(function(a,b){return tval(a)-tval(b);});}
function renderBoard(){var box=D.getElementById('fl-board');if(!box)return;var n=now(),L=filtered();
  var early=L.filter(function(r){return (isFinal(r)||shown(r,n)==='unknown')&&tval(r)<n-1800&&r.k!==state.open;});
  var rest=L.filter(function(r){return early.indexOf(r)<0;});
  var h='';
  if(early.length){h+='<button class="fl-more" type="button" data-act="earlier">'+esc(state.earlier?tr('hideEarlier'):(early.length===1?tr('earlier1'):tr('earlier',{n:early.length})))+'</button>';
    if(state.earlier)h+=group(early,n);}
  h+=group(rest,n);
  if(!L.length){var apo=(DATA.airports||{})[state.ap]||{};h='<p class="fl-empty">'+esc(state.q?tr('none'):(apo.ok===false&&!rows().some(function(r){return r.ap===state.ap;})?tr('down'):tr('noneDay')))+'</p>';}
  box.innerHTML=h;
  D.querySelectorAll('[data-seg] button').forEach(function(b){var on=(b.getAttribute('data-v')===state.ap||b.getAttribute('data-v')===state.d);b.setAttribute('aria-pressed',on?'true':'false');});
  counts();}
function group(L,n){var h='',last=null;L.forEach(function(r){var dd=srDay(tval(r));if(dd!==last){if(last!==null)h+='</ul>';h+='<h3 class="fl-day">'+esc(dayLabel(tval(r),n))+'</h3><ul class="fl-list">';last=dd;}h+=rowHtml(r,n,r.k===state.open);});if(last!==null)h+='</ul>';return h;}
function counts(){var n=now();['A','D'].forEach(function(d){var c=rows().filter(function(r){return r.ap===state.ap&&r.d===d&&(!r.cg||state.cg)&&tval(r)>=n-1800&&srDay(tval(r))<=srDay(n)+1;}).length;
  var el=D.querySelector('[data-v="'+d+'"] .n');if(el)el.textContent=c?String(c):'';});}
function renderNext(){var box=D.getElementById('fl-next');if(!box)return;var n=now(),h='';
  tracked.forEach(function(k){var r=byKey(k);if(r&&tval(r)>=n-6*3600)h+=card(r,n,tr('yours'),true);});
  if(CFG.mode!=='flight'){['A','D'].forEach(function(d){var c=rows().filter(function(r){return r.ap===state.ap&&r.d===d&&!r.cg&&r.st!=='cancelled'&&!isFinal(r)&&tval(r)>=n-600&&!isTracked(r.k);}).sort(function(a,b){return tval(a)-tval(b);})[0];
    if(c)h+=card(c,n,tr(d==='A'?'nextArr':'nextDep'),false);});}
  box.innerHTML=h;box.hidden=!h;}
function card(r,n,label,trk){var t=tval(r);return '<button class="fl-card fl-nc'+(trk?' trk':'')+'" type="button" data-open="'+esc(r.k)+'"><span class="l">'+esc(label)+'</span>'+
  '<span class="big" translate="no">'+hm(t)+(Math.abs(t-r.s)>=300?'<small><s>'+hm(r.s)+'</s></small>':'')+'</span>'+
  '<span class="r" translate="no">'+esc(r.fn+' · '+(r.d==='A'?(r.on+' → '+r.ap):(r.ap+' → '+r.on)))+'</span>'+
  '<span class="c"><span class="pill p-'+shown(r,n)+'">'+esc(pillTxt(r,n))+'</span> '+esc(isFinal(r)?'':(Math.abs(t-n)>12*3600?dayLabel(t,n):relT(t,n)))+'</span></button>';}
function openRow(k){var r=byKey(k);if(!r)return;if(CFG.mode==='flight'){var el=D.getElementById('fp-status');if(el)el.scrollIntoView({behavior:'smooth',block:'start'});return;}
  state.ap=r.ap;state.d=r.d;state.open=k;state.earlier=true;renderAll();var li=D.querySelector('li[data-k="'+CSS.escape(k)+'"]');if(li)li.scrollIntoView({behavior:'smooth',block:'center'});}

/* ── FLIGHT PAGE ── */
function legsFor(){var fn=CFG.fn,n=now();var L=rows().filter(function(r){return r.fn===fn;});var out={};
  L.forEach(function(r){var key=r.d+r.ap;var cur=out[key];var score=function(x){var t=tval(x);return (isFinal(x)&&t<n-3*3600)?1e9+Math.abs(t-n):Math.abs(t-n);};if(!cur||score(r)<score(cur))out[key]=r;});
  return Object.keys(out).map(function(k){return out[k];}).sort(function(a,b){return a.s-b.s;});}
function renderFlight(){var box=D.getElementById('fp-status');if(!box)return;var n=now(),L=legsFor();if(!L.length)return;
  var h='';L.forEach(function(r){var t=tval(r),st=shown(r,n);
    h+='<div class="fl-card fp-status" data-k="'+esc(r.k)+'"><div class="row"><span class="when">'+esc(dayLabel(r.s,n))+' · '+esc(tr(r.d==='A'?'arr':'dep'))+' '+esc(r.ap)+'</span><span class="pill p-'+st+'">'+esc(pillTxt(r,n))+'</span></div>'+
      '<div class="big" translate="no">'+hm(t)+(Math.abs(t-r.s)>=300?'<s>'+hm(r.s)+'</s>':'')+'</div>'+
      '<p class="lbl" translate="no">'+esc(route(r))+(isFinal(r)||Math.abs(t-n)>12*3600?'':' · '+esc(relT(t,n)))+'</p>'+
      '<div class="fr-det">'+detHtml(r,n)+'</div></div>';});
  box.innerHTML=h;}

/* ── events ── */
D.addEventListener('click',function(e){var t=e.target.closest('[data-act],[data-open],.fr-main,[data-seg] button');if(!t)return;
  if(t.matches('[data-seg] button')){var v=t.getAttribute('data-v');if(v==='PBM'||v==='EAX'){state.ap=v;lsSet('fl-ap',v);}else{state.d=v;lsSet('fl-d',v);}state.open=null;state.earlier=false;renderAll();ga('fl_filter',{v:v});return;}
  if(t.hasAttribute('data-open')){openRow(t.getAttribute('data-open'));return;}
  if(t.classList.contains('fr-main')){var li=t.closest('li'),k=li.getAttribute('data-k');state.open=(state.open===k?null:k);
    var det=li.querySelector('.fr-det'),open=state.open===k;t.setAttribute('aria-expanded',open?'true':'false');
    if(open){D.querySelectorAll('.fr-det:not([hidden])').forEach(function(x){if(x!==det){x.hidden=true;var b=x.parentNode.querySelector('.fr-main');if(b)b.setAttribute('aria-expanded','false');}});det.innerHTML=detHtml(byKey(k),now());det.hidden=false;ga('fl_open',{fn:(byKey(k)||{}).fn});}
    else det.hidden=true;return;}
  var act=t.getAttribute('data-act'),host=t.closest('[data-k]'),r=host?byKey(host.getAttribute('data-k')):null;
  if(act==='earlier'){state.earlier=!state.earlier;renderBoard();return;}
  if(!r)return;
  if(act==='track'){var i=tracked.indexOf(r.k);if(i>=0){tracked.splice(i,1);toast(tr('untrackedToast',{fn:r.fn}));}else{tracked.push(r.k);toast(tr('trackedToast',{fn:r.fn}));snap[r.k]=sig(r);}
    tracked=tracked.slice(-8);lsSet('fl-track',tracked);ga('fl_track',{fn:r.fn});renderAll();return;}
  if(act==='notify'){if(!('Notification' in W))return;W.Notification.requestPermission().then(function(p){notifyOn=(p==='granted');lsSet('fl-notify',notifyOn);
      if(notifyOn){if(!isTracked(r.k)){tracked.push(r.k);lsSet('fl-track',tracked);snap[r.k]=sig(r);}toast(tr('alertsToast'));}else toast(tr('alertsDenied'));ga('fl_notify',{fn:r.fn,ok:notifyOn});renderAll();});return;}
  if(act==='share'){var txt=shareText(r,now()),url=location.origin+pageUrl(r);ga('fl_share',{fn:r.fn});
    if(navigator.share){navigator.share({text:txt,url:url}).catch(function(){});}else{W.open('https://wa.me/?text='+encodeURIComponent(txt+' '+url),'_blank','noopener');}return;}
  if(act==='cal'){ga('fl_cal',{fn:r.fn});return;}
});
D.addEventListener('change',function(e){var s=e.target;if(!s.matches('.pk-from,.ci-from'))return;var host=s.closest('[data-k]'),r=host?byKey(host.getAttribute('data-k')):null;if(!r)return;
  lsSet('fl-from-'+r.ap,s.value);var n=now();
  if(s.classList.contains('pk-from')){s.closest('.pk').querySelector('.res').innerHTML=pickupRes(r,n,s.value);}
  else{var ci=(CFG.checkin||{})[r.oi]||(CFG.checkin||{})._||[3,2];s.closest('.pk').querySelector('.ci-leave').innerHTML=ciLeave(r,n,r.s-ci[1]*3600-1800,s.value);}});
var qi=D.getElementById('fl-q');if(qi)qi.addEventListener('input',function(){state.q=qi.value;renderBoard();});
var cgi=D.getElementById('fl-cg');if(cgi){cgi.checked=state.cg;cgi.addEventListener('change',function(){state.cg=cgi.checked;lsSet('fl-cg',state.cg);renderBoard();});}

/* ── refresh + alerts ── */
var snap={};function sig(r){return (r.st||'')+'|'+Math.round(tval(r)/300);}
function snapAll(){tracked.forEach(function(k){var r=byKey(k);if(r)snap[k]=sig(r);});}
function alerts(){var n=now();tracked.forEach(function(k){var r=byKey(k);if(!r)return;var s=sig(r);if(snap[k]&&snap[k]!==s){var msg=shareText(r,n);toast(msg);
    if(notifyOn&&('Notification' in W)&&W.Notification.permission==='granted'){try{new W.Notification(tr('alertTitle',{fn:r.fn}),{body:msg,tag:r.k});}catch(e){}}}snap[k]=s;});}
function refresh(){if(D.hidden)return;fetch('/data/flights_live.json?t='+Math.floor(Date.now()/60000),{cache:'no-store'}).then(function(x){return x.ok?x.json():null;}).then(function(j){
  if(!j||!j.flights)return;if(j.built&&DATA.built&&j.built<DATA.built)return;DATA=j;alerts();renderAll();}).catch(function(){});}
function renderAll(){if(CFG.mode==='flight')renderFlight();else renderBoard();renderNext();liveLine();}
if(CFG.mode!=='flight')initState();
snapAll();renderAll();
setInterval(function(){if(!D.hidden){renderAll();}},45000);
setInterval(refresh,120000);
D.addEventListener('visibilitychange',function(){if(!D.hidden)refresh();});
setTimeout(refresh,4000);
})();
