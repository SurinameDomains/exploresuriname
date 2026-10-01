
(function(){
  var E = window.BizEngine;
  var L = (document.documentElement.lang || 'en').slice(0,2);
  var R = JSON.parse(document.getElementById('bzR').textContent);
  var H = JSON.parse(document.getElementById('bzH').textContent);
  function $(id){ return document.getElementById(id); }
  function T(k, v){
    var e = document.querySelector('#bzT [data-k="'+k+'"]');
    var s = e ? e.textContent : k;
    if (v) for (var x in v) s = s.split('{'+x+'}').join(v[x]);
    return s;
  }
  function money(c){ return E.fmt(c, L); }
  function fmtIn(c){ return new Intl.NumberFormat((L==='en'||L==='zh')?'en-US':'nl-NL', {minimumFractionDigits: c%100?2:0, maximumFractionDigits:2}).format(c/100); }
  function srd(c){ return 'SRD ' + E.fmt(c, L); }
  function amt(id){ var el = $(id); if(!el) return null; var v = el.value.trim(); if(v===''){ el.removeAttribute('aria-invalid'); return null; }
    var c = E.parseAmount(v, L); if(c===null){ el.setAttribute('aria-invalid','true'); } else el.removeAttribute('aria-invalid'); return c; }
  function num(id){ var el = $(id); if(!el) return null; var v = el.value.trim(); if(v===''){ el.removeAttribute('aria-invalid'); return null; }
    var n = E.parseNum(v, L); if(n===null){ el.setAttribute('aria-invalid','true'); } else el.removeAttribute('aria-invalid'); return n; }
  function today(){ var d = new Date(Date.now() - 3*3600*1000); return d.toISOString().slice(0,10); } // Suriname date (UTC-3)
  function fmtDate(iso){ if(!iso) return ''; var p = iso.split('-'); var d = new Date(Date.UTC(+p[0], +p[1]-1, +p[2]));
    return d.toLocaleDateString(L==='en'?'en-GB':(L==='es'?'es-ES':(L==='zh'?'zh-CN':'nl-NL')), {weekday:'short', day:'numeric', month:'long', year:'numeric', timeZone:'UTC'}); }
  function fmtDay(iso){ if(!iso) return ''; var p = iso.split('-'); var d = new Date(Date.UTC(+p[0], +p[1]-1, +p[2]));
    return d.toLocaleDateString(L==='en'?'en-GB':(L==='es'?'es-ES':(L==='zh'?'zh-CN':'nl-NL')), {day:'numeric', month:'long', year:'numeric', timeZone:'UTC'}); }
  function seg(id, cb){ var box = $(id); if(!box) return; box.addEventListener('click', function(ev){ var b = ev.target.closest('button[data-v]'); if(!b) return;
      [].forEach.call(box.querySelectorAll('button'), function(x){ x.setAttribute('aria-pressed', x===b?'true':'false'); }); if(cb) cb(b.getAttribute('data-v')); }); }
  function segVal(id){ var b = document.querySelector('#'+id+' button[aria-pressed=true]'); return b ? b.getAttribute('data-v') : null; }
  function segSet(id, v){ [].forEach.call(document.querySelectorAll('#'+id+' button'), function(x){ x.setAttribute('aria-pressed', x.getAttribute('data-v')===v?'true':'false'); }); }
  function toast(msg){ var t = $('bzToast'); if(!t){ t = document.createElement('div'); t.id='bzToast'; t.className='bz-toast'; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('on'); clearTimeout(t._h); t._h = setTimeout(function(){ t.classList.remove('on'); }, 2200); }
  function copy(text){ if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(function(){ toast(T('copied')); }, function(){ fallback(); }); } else fallback();
    function fallback(){ var ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); toast(T('copied')); }catch(e){} document.body.removeChild(ta); } }
  function wa(text){ window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank', 'noopener'); }
  // shareable state: ?a=1&b=2 (only the listed input ids)
  // Only put inputs in the address bar after the visitor changed something, so a
  // freshly opened tool keeps its clean URL (/btw-calculator, not ?amt=...).
  var touched = false; ['input','change','click'].forEach(function(ev){ document.addEventListener(ev, function(e){ if(e.isTrusted && e.target && e.target.closest && e.target.closest('main')) touched = true; }, true); });
  function saveUrl(ids){ if(!touched) return; try{ var q = new URLSearchParams(); ids.forEach(function(id){ var el=$(id); if(!el) return;
      var v = el.type==='checkbox' ? (el.checked?'1':'') : (el.getAttribute('role')==='group' ? segVal(id) : el.value); if(v) q.set(id, v); });
      var s = q.toString(); history.replaceState(null, '', location.pathname + (s ? '?' + s : '')); }catch(e){} }
  function loadUrl(ids){ try{ var q = new URLSearchParams(location.search); ids.forEach(function(id){ if(!q.has(id)) return; var el=$(id); if(!el) return;
      if(el.type==='checkbox') el.checked = q.get(id)==='1'; else if(el.getAttribute('role')==='group') segSet(id, q.get(id)); else el.value = q.get(id); }); return q.toString() !== ''; }catch(e){ return false; } }
  function store(k, v){ try{ if(v===undefined){ var s = localStorage.getItem('bz.'+k); return s ? JSON.parse(s) : null; } localStorage.setItem('bz.'+k, JSON.stringify(v)); return true; }catch(e){ return null; } }
  function download(name, blob){ var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; document.body.appendChild(a); a.click(); setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1500); }
  function loadScript(src){ return new Promise(function(res, rej){ if(document.querySelector('script[src="'+src+'"]')) return res(); var s=document.createElement('script'); s.src=src; s.onload=res; s.onerror=function(){ rej(new Error('load '+src)); }; document.head.appendChild(s); }); }
  function on(ids, ev, fn){ ids.forEach(function(id){ var el=$(id); if(el) el.addEventListener(ev, fn); }); }
  function esc(s){ return String(s===null||s===undefined?'':s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function rows(list){ return list.map(function(r){ return '<tr'+(r[2]?' class="'+r[2]+'"':'')+'><td>'+esc(r[0])+'</td><td class="n">'+r[1]+'</td></tr>'; }).join(''); }
  // Show default values in the reader's number format (1.000,50 in NL/ES, 1,000.50 in EN).
  // Runs before the page script, so values from a shared link (loadUrl) still win.
  [].forEach.call(document.querySelectorAll('input.bz-num[value]'), function(el){
    var v = el.value.trim(); if(!v) return;
    if(el.getAttribute('data-kind')==='m'){ var c = E.parseAmount(v); if(c===null) return;
      el.value = new Intl.NumberFormat((L==='en'||L==='zh')?'en-US':'nl-NL', {minimumFractionDigits: c%100?2:0, maximumFractionDigits:2}).format(c/100); }
    else { var n = E.parseNum(v); if(n===null) return; el.value = new Intl.NumberFormat((L==='en'||L==='zh')?'en-US':'nl-NL', {useGrouping:false, maximumFractionDigits:4}).format(n); }
  });
  // share/print buttons present on most tools
  document.addEventListener('click', function(ev){
    var b = ev.target.closest('[data-bz]'); if(!b) return;
    var a = b.getAttribute('data-bz');
    if(a==='link') copy(location.href);
    else if(a==='print') window.print();
    else if(a==='wa' && window.BZ && BZ.shareText) wa(BZ.shareText() + '\n' + location.href);
    else if(a==='copy' && window.BZ && BZ.shareText) copy(BZ.shareText());
  });
  window.BZ = {E:E, L:L, R:R, H:H, $:$, T:T, money:money, fmtIn:fmtIn, srd:srd, amt:amt, num:num, today:today, fmtDate:fmtDate, fmtDay:fmtDay, seg:seg, segVal:segVal, segSet:segSet,
    toast:toast, copy:copy, wa:wa, saveUrl:saveUrl, loadUrl:loadUrl, store:store, download:download, loadScript:loadScript, on:on, esc:esc, rows:rows, shareText:null};
})();
/* Mobile tables: see .bz-stack in KIT_CSS. Separate block so a failure here
   can never break the tools above. */
(function(){
  if(!document.querySelectorAll) return;
  var tables = [].slice.call(document.querySelectorAll('.bz-scroll > table.bz-tbl'));
  function label(t){
    var h = t.tHead && t.tHead.rows[0]; if(!h) return;
    var names = [].map.call(h.cells, function(c){ return c.textContent.trim(); });
    var long = false;
    [].forEach.call(t.tBodies, function(b){ [].forEach.call(b.rows, function(r){
      var i = 0;
      [].forEach.call(r.cells, function(c, j){
        c.setAttribute('data-label', names[i] || '');
        if(j > 0 && c.textContent.trim().length > 30) long = true;
        i += c.colSpan || 1;
      });
    }); });
    if(long) t.classList.add('bz-one');
  }
  function decide(){
    tables.forEach(function(t){
      if(!t.tHead || t.classList.contains('bz-nostack')) return;
      t.classList.remove('bz-stack');
      var w = t.parentNode;
      if(w.clientWidth > 0 && w.scrollWidth > w.clientWidth + 2) t.classList.add('bz-stack');
    });
  }
  tables.forEach(function(t){
    label(t);
    if(window.MutationObserver) [].forEach.call(t.tBodies, function(b){
      new MutationObserver(function(){ label(t); }).observe(b, {childList:true});
    });
  });
  decide();
  // Tables inside a hidden tab measure 0 wide at load: re-decide when a
  // wrapper's width changes (tab shown, rotation). Width only, so the height
  // change from stacking can never retrigger it.
  if(window.ResizeObserver) tables.forEach(function(t){
    var w = t.parentNode, last = w.clientWidth;
    new ResizeObserver(function(){ if(w.clientWidth !== last){ last = w.clientWidth; decide(); } }).observe(w);
  });
})();
