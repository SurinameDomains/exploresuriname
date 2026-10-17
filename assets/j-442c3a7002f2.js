
(function(){
  var D = document, W = window;
  var I = {"en":{"noneOpen":"Nothing here is open right now.","open":"Open","until":"until {t}","h24":"Open 24 hours","soon":"Closes soon","closed":"Closed","opens":"opens {t}","opensTom":"opens tomorrow {t}","opensDay":"opens {d} {t}","hol":"Public holiday: hours may differ","openNow":"Open now","near":"Near me","finding":"Finding you…","denied":"Location is off. Allow it in your browser settings to sort by distance.","failed":"Could not get your location. Try again.","sorted":"sorted by distance","noLoc":"{n} without location last","noHours":"{n} without hours not shown","away":"{d} away"},"nl":{"noneOpen":"Hier is nu niets open.","open":"Open","until":"tot {t}","h24":"24 uur open","soon":"Sluit binnenkort","closed":"Gesloten","opens":"opent om {t}","opensTom":"opent morgen om {t}","opensDay":"opent {d} om {t}","hol":"Feestdag: openingstijden kunnen afwijken","openNow":"Nu open","near":"Bij mij in de buurt","finding":"Locatie zoeken…","denied":"Locatie staat uit. Sta het toe in je browserinstellingen om op afstand te sorteren.","failed":"Je locatie kon niet worden bepaald. Probeer het opnieuw.","sorted":"gesorteerd op afstand","noLoc":"{n} zonder locatie onderaan","noHours":"{n} zonder openingstijden niet getoond","away":"{d} hiervandaan"},"es":{"noneOpen":"Ahora no hay nada abierto aquí.","open":"Abierto","until":"hasta las {t}","h24":"Abierto 24 horas","soon":"Cierra pronto","closed":"Cerrado","opens":"abre a las {t}","opensTom":"abre mañana a las {t}","opensDay":"abre el {d} a las {t}","hol":"Día festivo: el horario puede variar","openNow":"Abierto ahora","near":"Cerca de mí","finding":"Buscando tu ubicación…","denied":"La ubicación está desactivada. Actívala en tu navegador para ordenar por distancia.","failed":"No se pudo obtener tu ubicación. Inténtalo de nuevo.","sorted":"ordenado por distancia","noLoc":"{n} sin ubicación al final","noHours":"{n} sin horario no se muestran","away":"a {d}"},"zh":{"noneOpen":"此类别目前没有营业的商家。","open":"营业中","until":"至 {t}","h24":"24 小时营业","soon":"即将打烊","closed":"已打烊","opens":"{t} 开门","opensTom":"明天 {t} 开门","opensDay":"{d} {t} 开门","hol":"公共假日：营业时间可能不同","openNow":"正在营业","near":"附近","finding":"正在定位…","denied":"定位已关闭。请在浏览器设置中允许定位，以按距离排序。","failed":"无法获取您的位置，请重试。","sorted":"按距离排序","noLoc":"{n} 家无位置信息的排在最后","noHours":"{n} 家无营业时间的未显示","away":"距离 {d}"},"fr":{"noneOpen":"Rien n’est ouvert ici pour le moment.","open":"Ouvert","until":"jusqu’à {t}","h24":"Ouvert 24 h/24","soon":"Ferme bientôt","closed":"Fermé","opens":"ouvre à {t}","opensTom":"ouvre demain à {t}","opensDay":"ouvre {d} à {t}","hol":"Jour férié : les horaires peuvent varier","openNow":"Ouvert maintenant","near":"Autour de moi","finding":"Recherche de votre position…","denied":"La localisation est désactivée. Autorisez-la dans les réglages de votre navigateur pour trier par distance.","failed":"Impossible d’obtenir votre position. Veuillez réessayer.","sorted":"triés par distance","noLoc":"{n} sans position en fin de liste","noHours":"{n} sans horaires non affichées","away":"à {d}"},"pt":{"noneOpen":"Nada aqui está aberto agora.","open":"Aberto","until":"até {t}","h24":"Aberto 24 horas","soon":"Fecha em breve","closed":"Fechado","opens":"abre às {t}","opensTom":"abre amanhã às {t}","opensDay":"abre {d} às {t}","hol":"Feriado: o horário pode variar","openNow":"Aberto agora","near":"Perto de mim","finding":"Buscando sua localização…","denied":"A localização está desativada. Permita no navegador para ordenar por distância.","failed":"Não foi possível obter sua localização. Tente de novo.","sorted":"ordenado por distância","noLoc":"{n} sem localização no final","noHours":"{n} sem horário não exibidos","away":"a {d}"}}, HOL = ["2026-01-01", "2026-02-17", "2026-03-04", "2026-03-20", "2026-04-03", "2026-04-05", "2026-04-06", "2026-05-01", "2026-05-27", "2026-06-16", "2026-07-01", "2026-08-09", "2026-10-10", "2026-11-08", "2026-11-25", "2026-12-25", "2026-12-26", "2027-01-01", "2027-02-06", "2027-03-10", "2027-03-22", "2027-03-26", "2027-03-28", "2027-03-29", "2027-05-01", "2027-05-17", "2027-07-01", "2027-08-09", "2027-10-10", "2027-11-25", "2027-12-25", "2027-12-26"];
  var L = I[(D.documentElement.lang || 'en').slice(0, 2).toLowerCase()] || I.en;
  function fmt(s, o){ return s.replace(/\{(\w)\}/g, function(_, k){ return o[k]; }); }
  function hm(m){ m = ((m % 1440) + 1440) % 1440; return ('0' + Math.floor(m / 60)).slice(-2) + ':' + ('0' + (m % 60)).slice(-2); }
  var dayFmt = null;
  try { dayFmt = new Intl.DateTimeFormat(D.documentElement.lang || 'en', {weekday: 'short', timeZone: 'UTC'}); } catch (e) {}
  function dayName(d){ /* d: 0 = Monday */ return dayFmt ? dayFmt.format(new Date(Date.UTC(2024, 0, 1 + d))) : ['Mo','Tu','We','Th','Fr','Sa','Su'][d]; }
  /* Suriname is UTC-3 all year (no daylight saving) */
  function nowSR(){
    var n = new Date(Date.now() - 3 * 3600e3);
    return {mow: ((n.getUTCDay() + 6) % 7) * 1440 + n.getUTCHours() * 60 + n.getUTCMinutes(),
            day: n.toISOString().slice(0, 10)};
  }
  function parse(s){ return (s || '').split(',').map(function(p){ var x = p.split('-'); return [+x[0], +x[1]]; }).filter(function(r){ return r[1] > r[0]; }); }
  function status(rs, chain){
    if (!rs.length) return null;
    var now = nowSR(), t = now.mow, hol = HOL.indexOf(now.day) >= 0;
    if (rs.length === 1 && rs[0][0] <= 0 && rs[0][1] >= 10080) return {k: 'open', txt: L.h24};
    for (var i = 0; i < rs.length; i++){
      var a = rs[i][0], b = rs[i][1];
      var tt = (a <= t && t < b) ? t : ((a <= t + 10080 && t + 10080 < b) ? t + 10080 : -1);
      if (tt < 0) continue;
      if (hol) return {k: 'hol', txt: L.hol, open: true};
      var left = b - tt;
      if (left <= 60) return {k: 'soon', txt: L.soon, sub: chain ? '' : hm(b), open: true};
      return {k: 'open', txt: L.open, sub: chain ? '' : fmt(L.until, {t: hm(b)}), open: true};
    }
    if (hol) return {k: 'hol', txt: L.hol};
    /* closed: next opening */
    var best = null;
    rs.forEach(function(r){ var a = r[0] > t ? r[0] : r[0] + 10080; if (best === null || a < best) best = a; });
    var dd = Math.floor(best / 1440) - Math.floor(t / 1440), sub;
    var dow = Math.floor(best / 1440) % 7;
    if (dd === 0) sub = fmt(L.opens, {t: hm(best)});
    else if (dd === 1) sub = fmt(L.opensTom, {t: hm(best)});
    else sub = fmt(L.opensDay, {d: dayName(dow), t: hm(best)});
    return {k: 'closed', txt: L.closed, sub: sub};
  }
  function km(d){ return d < 1 ? (Math.max(50, Math.round(d * 20) * 50)) + ' m' : (d < 10 ? d.toFixed(1) : Math.round(d)) + ' km'; }
  function hav(a, b){
    var r = Math.PI / 180, dl = (b[0] - a[0]) * r, dn = (b[1] - a[1]) * r;
    var h = Math.sin(dl / 2) * Math.sin(dl / 2) + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dn / 2) * Math.sin(dn / 2);
    return 12742 * Math.asin(Math.sqrt(h));
  }
  var cards = [], openOn = false, nearOn = false, me = null, nHours = 0, nPins = 0;
  function lineOf(c){
    var l = c.querySelector('.oh-line');
    if (!l){ l = D.createElement('p'); l.className = 'oh-line';
      var h = c.querySelector('.listing-name, h3'); if (h && h.parentNode) h.parentNode.insertBefore(l, h.nextSibling); else c.appendChild(l); }
    return l;
  }
  function paint(c){
    var st = c._ohS, l = null, html = '';
    if (st) html += '<span class="oh-st oh-' + st.k + '">' + st.txt + (st.sub ? ' <span class="oh-sub">· ' + st.sub + '</span>' : '') + '</span>';
    if (nearOn && c._km != null) html += '<span class="oh-km">' + km(c._km) + '</span>';
    if (html || c.querySelector('.oh-line')){ l = lineOf(c); if (l.innerHTML !== html) l.innerHTML = html; }
  }
  function tick(){
    cards.forEach(function(c){ c._ohS = c._ohR.length ? status(c._ohR, c.hasAttribute('data-hc')) : null; paint(c); });
    D.querySelectorAll('.oh-live[data-h]').forEach(function(el){
      var s = status(parse(el.getAttribute('data-h')), false);
      el.innerHTML = s ? '<span class="oh-st oh-' + s.k + '">' + s.txt + (s.sub ? ' <span class="oh-sub">· ' + s.sub + '</span>' : '') + '</span>' : '';
    });
    if (openOn && W.gfApply) W.gfApply(true);
  }
  function ga(n, on){ try { if (typeof gtag === 'function') gtag('event', 'gf_toggle', {name: n, on: on}); } catch (e) {} }
  function msg(t){
    var bar = D.querySelector('.gf-row'); if (!bar) return;
    var m = D.getElementById('oh-msg');
    if (!m){ m = D.createElement('p'); m.id = 'oh-msg'; m.className = 'oh-msg'; bar.parentNode.insertBefore(m, bar.nextSibling); }
    m.textContent = t || ''; m.hidden = !t;
  }
  function init(){
    cards = Array.prototype.slice.call(D.querySelectorAll('.listing-card'));
    cards.forEach(function(c){
      c._ohR = parse(c.getAttribute('data-h'));
      if (c._ohR.length) nHours++;
      var ll = (c.getAttribute('data-ll') || '').split(';').filter(Boolean).map(function(p){ var x = p.split(','); return [+x[0], +x[1]]; });
      c._ohP = ll; if (ll.length) nPins++;
    });
    tick(); setInterval(tick, 60000);
    var bo = D.getElementById('oh-open'), bn = D.getElementById('oh-near');
    if (bo && nHours >= 5){
      bo.querySelector('span').textContent = L.openNow; bo.hidden = false;
      bo.addEventListener('click', function(){
        openOn = !openOn; bo.setAttribute('aria-pressed', openOn ? 'true' : 'false'); bo.classList.toggle('chip-active', openOn); ga('open_now', openOn);
        if (W.gfApply) W.gfApply();
      });
    }
    if (bn && nPins >= 8 && navigator.geolocation){
      bn.querySelector('span').textContent = L.near; bn.hidden = false;
      bn.addEventListener('click', function(){
        if (nearOn){ nearOn = false; bn.setAttribute('aria-pressed', 'false'); bn.classList.remove('chip-active'); msg(''); cards.forEach(paint); ga('near_me', false); if (W.gfApply) W.gfApply(); return; }
        bn.classList.add('oh-busy'); bn.querySelector('span').textContent = L.finding;
        navigator.geolocation.getCurrentPosition(function(p){
          me = [p.coords.latitude, p.coords.longitude];
          cards.forEach(function(c){ c._km = c._ohP.length ? Math.min.apply(null, c._ohP.map(function(q){ return hav(me, q); })) : null; });
          nearOn = true; bn.classList.remove('oh-busy'); bn.querySelector('span').textContent = L.near;
          bn.setAttribute('aria-pressed', 'true'); bn.classList.add('chip-active'); msg(''); cards.forEach(paint); ga('near_me', true);
          if (W.gfApply) W.gfApply();
        }, function(err){
          bn.classList.remove('oh-busy'); bn.querySelector('span').textContent = L.near;
          msg(err && err.code === 1 ? L.denied : L.failed); ga('near_me_error', err ? err.code : 0);
        }, {enableHighAccuracy: false, timeout: 12000, maximumAge: 300000});
      });
    }
    /* hooks used by the filter bar (_GF_JS) */
    var hid = 0;
    W.gfBegin = function(){ hid = 0; };
    W.gfOk = function(c){ if (!openOn) return true; if (!c._ohR.length){ hid++; return false; } return !!(c._ohS && c._ohS.open); };
    W.gfSort = function(list){
      if (!nearOn) return null;
      return list.map(function(c, k){ return [c, k]; }).sort(function(x, y){
        var a = x[0]._km, b = y[0]._km;
        if (a == null && b == null) return x[1] - y[1]; if (a == null) return 1; if (b == null) return -1;
        return a - b;
      }).map(function(x){ return x[0]; });
    };
    W.gfNote = function(vis){
      var out = [], em = D.querySelector('.gf-empty');
      if (em){ if (em.dataset.t0 == null) em.dataset.t0 = em.textContent; em.textContent = (openOn && !vis) ? L.noneOpen : em.dataset.t0; }
      if (openOn && hid) out.push(fmt(L.noHours, {n: hid}));
      if (nearOn){ out.push(L.sorted); var nl = cards.filter(function(c){ return c._gfOk && c._km == null; }).length; if (nl) out.push(fmt(L.noLoc, {n: nl})); }
      return out.length ? ' · ' + out.join(' · ') : '';
    };
  }
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', init); else init();
})();
