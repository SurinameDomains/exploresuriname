/* Search modal UI (search v2, 25 Oct 2026). Uses window.ESR_SEARCH from
   search_engine.js. Keeps the v1 globals openSearch / closeSearch / runSearch /
   searchKey (nav button, hero search and "/" shortcut call them).
   UI words are hand-written per language here (build_i18n does not touch JS);
   concept names come from /data/search-vocab.json.
   GA4: "search" {search_term, search_results, search_state, search_concepts}
   once the person pauses typing (1.5 s) or leaves the box; "search_click"
   {search_term, search_position, search_item, search_rel}; "search_cta"
   when the "add your business" card is used. */
(function () {
  var S = window.ESR_SEARCH;
  var LANG = (document.documentElement.lang || 'en').slice(0, 2);
  var LP = (location.pathname.match(/^\/(nl|es|zh|fr|pt)\//) || [])[1];
  var BASE = '/' + (LP ? LP + '/' : '');
  var NB = ' ';
  var TX = {
    en: {n: '{n} results', n1: '1 result', ph: 'Search places or what you need\u2026', fix: 'Showing results for “{x}”', also: 'Also relevant: {x}',
         gap1: 'No listings for “{x}” yet.', gap2: 'Know one, or is it your business? Listing is free and takes a few minutes.',
         gapBtn: 'Add a business for free', pmiss: 'Nothing in {p} yet. Showing all of Suriname.',
         none: 'No results for “{q}”', tryx: 'Try one of these:', miss: 'Missing a business? Add it for free',
         more: 'Show all {n} results', load: 'Loading…', sug: 'Search for', start: 'For example:',
         ex: ['air conditioning', 'birthday cake', 'barber', 'roti', 'hotel by the river', 'car rental']},
    nl: {n: '{n} resultaten', n1: '1 resultaat', ph: 'Zoek een zaak of wat je nodig hebt\u2026', fix: 'Resultaten voor “{x}”', also: 'Ook relevant: {x}',
         gap1: 'Nog geen vermeldingen voor “{x}”.', gap2: 'Ken je er een, of is het jouw zaak? Aanmelden is gratis en kost een paar minuten.',
         gapBtn: 'Zet je bedrijf er gratis op', pmiss: 'Nog niets in {p}. Je ziet heel Suriname.',
         none: 'Geen resultaten voor “{q}”', tryx: 'Probeer bijvoorbeeld:', miss: 'Mis je een bedrijf? Zet het er gratis op',
         more: 'Toon alle {n} resultaten', load: 'Laden…', sug: 'Zoek naar', start: 'Bijvoorbeeld:',
         ex: ['aircoman', 'taart bestellen', 'kapper Lelydorp', 'roti', 'nagelstudio', 'autoverhuur']},
    es: {n: '{n} resultados', n1: '1 resultado', ph: 'Busque un lugar o lo que necesita\u2026', fix: 'Resultados para «{x}»', also: 'También relevante: {x}',
         gap1: 'Aún no hay negocios en «{x}».', gap2: '¿Conoce uno o es su negocio? Publicarlo es gratis y lleva unos minutos.',
         gapBtn: 'Añadir un negocio gratis', pmiss: 'Aún nada en {p}. Mostrando todo Surinam.',
         none: 'Sin resultados para «{q}»', tryx: 'Pruebe con:', miss: '¿Falta un negocio? Añádalo gratis',
         more: 'Ver los {n} resultados', load: 'Cargando…', sug: 'Buscar', start: 'Por ejemplo:',
         ex: ['restaurante', 'hotel', 'farmacia', 'peluquería', 'alquiler de autos', 'tours']},
    zh: {n: '{n} 个结果', n1: '1 个结果', ph: '搜索商家或需求…', fix: '显示“{x}”的结果', also: '相关：{x}',
         gap1: '“{x}”暂时还没有商家。', gap2: '认识这样的商家，或者这就是您的生意？免费登记，只需几分钟。',
         gapBtn: '免费添加商家', pmiss: '{p}暂无结果，显示苏里南全部结果。',
         none: '没有找到“{q}”的结果', tryx: '试试：', miss: '缺少某个商家？免费添加',
         more: '显示全部 {n} 个结果', load: '加载中…', sug: '搜索', start: '例如：',
         ex: ['餐厅', '酒店', '中餐', '药店', '租车', '旅游']},
    fr: {n: '{n} résultats', n1: '1 résultat', ph: 'Cherchez un lieu ou un besoin…', fix: 'Résultats pour «' + NB + '{x}' + NB + '»', also: 'Également pertinent' + NB + ': {x}',
         gap1: 'Aucune adresse pour «' + NB + '{x}' + NB + '» pour l’instant.', gap2: 'Vous en connaissez une, ou c’est votre entreprise' + NB + '? L’inscription est gratuite et ne prend que quelques minutes.',
         gapBtn: 'Ajouter une entreprise gratuitement', pmiss: 'Rien à {p} pour l’instant. Résultats pour tout le Suriname.',
         none: 'Aucun résultat pour «' + NB + '{q}' + NB + '»', tryx: 'Essayez' + NB + ':', miss: 'Une entreprise manque' + NB + '? Ajoutez-la gratuitement',
         more: 'Afficher les {n} résultats', load: 'Chargement…', sug: 'Rechercher', start: 'Par exemple' + NB + ':',
         ex: ['restaurant', 'hôtel', 'pharmacie', 'coiffeur', 'location de voitures', 'excursions']},
    pt: {n: '{n} resultados', n1: '1 resultado', ph: 'Busque um lugar ou o que precisa\u2026', fix: 'Resultados para “{x}”', also: 'Também relevante: {x}',
         gap1: 'Ainda não há negócios em “{x}”.', gap2: 'Conhece um ou é o seu negócio? O cadastro é gratuito e leva poucos minutos.',
         gapBtn: 'Adicionar um negócio grátis', pmiss: 'Ainda nada em {p}. Mostrando todo o Suriname.',
         none: 'Nenhum resultado para “{q}”', tryx: 'Experimente:', miss: 'Falta algum negócio? Adicione grátis',
         more: 'Ver todos os {n} resultados', load: 'Carregando…', sug: 'Buscar', start: 'Por exemplo:',
         ex: ['restaurante', 'hotel', 'farmácia', 'cabeleireiro', 'aluguel de carros', 'passeios']}
  };
  var T = TX[LANG] || TX.en;
  var loading = false, waiters = [], sel = -1, last = null, showAll = false, forced = null;
  var gaTimer = null, gaSent = '', gaPending = null;
  var IC = '<svg class="sr-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path stroke-linecap="round" d="m20 20-3.5-3.5"/></svg>';

  function esc(x) { return String(x == null ? '' : x).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function fmt(s, o) { return s.replace(/\{(\w)\}/g, function (m, k) { return o[k] != null ? o[k] : m; }); }
  function href(u) { u = String(u || ''); return /^(https?:)?\//.test(u) ? u : BASE + u; }
  function box() { return document.getElementById('search-results'); }
  function input() { return document.getElementById('search-input'); }
  function title(w) { return String(w || '').replace(/\b[a-z]/g, function (c) { return c.toUpperCase(); }); }

  function load(cb) {
    if (S.ready()) { cb(); return; }
    waiters.push(cb);
    if (loading) return;
    loading = true;
    var a = null, b = null;
    function done() { if (a && b) { S.init(a, b); waiters.splice(0).forEach(function (f) { f(); }); } }
    fetch(BASE + 'search-index.json').then(function (r) { return r.json(); })
      .then(function (d) { a = d; done(); }).catch(function () { a = []; done(); });
    fetch('/data/search-vocab.json').then(function (r) { return r.json(); })
      .then(function (d) { b = d; done(); }).catch(function () { b = {c: [], p: {}, f: [], h: []}; done(); });
  }

  /* ── GA4 ─────────────────────────────────────────────────────────────── */
  function ga(name, params) {
    try {
      window.dataLayer = window.dataLayer || [];
      if (!window.gtag) { window.gtag = function () { window.dataLayer.push(arguments); }; }
      window.gtag('event', name, params);
    } catch (e) {}
  }
  function gaFlush() {
    clearTimeout(gaTimer);
    var p = gaPending; gaPending = null;
    if (!p || p.q === gaSent) return;
    gaSent = p.q;
    ga('search', {search_term: p.q, search_results: p.n, search_state: p.st,
                  search_concepts: p.c.slice(0, 100)});
  }
  function gaQueue(q, res) {
    q = q.trim().toLowerCase().slice(0, 100);
    clearTimeout(gaTimer);
    if (q.length < 2) { gaPending = null; return; }
    gaPending = {q: q, n: res.results.length, st: res.state || 'ok',
                 c: res.concepts.map(function (z) { return z.id; }).join(',')};
    gaTimer = setTimeout(gaFlush, 1500);
  }

  /* ── rendering ───────────────────────────────────────────────────────── */
  function hint(html) { box().innerHTML = '<div class="sr-empty">' + html + '</div>'; sel = -1; }
  function chips(list) {
    return '<div class="sr-chips">' + list.map(function (q) {
      return '<button type="button" class="sr-chip" data-q="' + esc(q) + '">' + esc(q) + '</button>';
    }).join('') + '</div>';
  }
  function startState() {
    hint('<p>' + esc(T.start) + '</p>' + chips(T.ex));
  }
  function mark(name, res) {
    var words = res.units.filter(function (u) { return u.k !== 'f' && u.typed && u.typed.length > 1; })
      .map(function (u) { return u.typed; });
    var out = esc(name);
    if (!words.length) return out;
    var rx = new RegExp('(' + words.map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')', 'gi');
    return out.replace(rx, '<mark>$1</mark>');
  }
  function item(x, i, res) {
    var e = x.e, col = (window._CAT_C || {})[e.c] || '#6b7280';
    return '<a href="' + esc(href(e.u)) + '" class="sr-it' + (i === 0 ? ' sr-active' : '') + '" data-i="' + i + '"' +
      (x.rel != null ? ' data-rel="1"' : '') + '>' +
      '<span class="sr-badge" style="background:' + col + '">' + esc(e.c) + '</span>' +
      '<span class="sr-name">' + mark(e.n, res) + '</span>' +
      (e.a ? '<span class="sr-area">' + esc(e.a) + '</span>' : '') + '</a>';
  }
  function addLink() {
    return '<a class="sr-add" href="' + esc(BASE + 'submit-business') + '" data-cta="1">' + esc(T.miss) + ' →</a>';
  }
  function render(res) {
    last = res;
    var h = [], n = 0, i;
    var prim = res.items.filter(function (x) { return x.rel == null; });
    var rel = res.items.filter(function (x) { return x.rel != null; });
    if (res.suggest.length) {
      h.push('<div class="sr-sugs">');
      res.suggest.forEach(function (s) {
        h.push('<button type="button" class="sr-sug" data-c="' + s.c + '">' + IC + '<span>' + esc(S.label(s.c, LANG)) +
          '</span><span class="sr-cnt">' + s.n + '</span></button>');
      });
      h.push('</div>');
    }
    if (res.state === 'gap') {
      var gl = res.concepts.filter(function (z) { return !z.n; }).map(function (z) { return S.label(z.c, LANG); }).join(', ');
      h.push('<div class="sr-gap"><p class="sr-gap1">' + esc(fmt(T.gap1, {x: gl})) + '</p><p class="sr-gap2">' + esc(T.gap2) +
        '</p><a class="sr-gapbtn" href="' + esc(BASE + 'submit-business') + '" data-cta="1">' + esc(T.gapBtn) + '</a></div>');
    } else if (res.state === 'none') {
      h.push('<div class="sr-empty"><p>' + esc(fmt(T.none, {q: res.q.trim()})) + '</p><p class="sr-try">' + esc(T.tryx) + '</p>' +
        chips(T.ex) + '</div>' + addLink());
    }
    if (prim.length) {
      var cs = res.concepts.filter(function (z) { return z.n; });
      if (cs.length && !forced) {
        var lab = cs.map(function (z) { return S.label(z.c, LANG); }).join(' + ');
        var fixed = cs.some(function (z) { return z.how === 'fuzzy'; });
        h.push('<div class="sr-head">' + esc(fixed ? fmt(T.fix, {x: lab}) : lab) +
          '<span>' + esc(prim.length === 1 ? T.n1 : fmt(T.n, {n: prim.length})) + '</span></div>');
      }
      if (res.state === 'place-miss' && res.place) h.push('<p class="sr-note">' + esc(fmt(T.pmiss, {p: title(res.place.typed || res.place.w)})) + '</p>');
      var cap = showAll ? 60 : 12;
      for (i = 0; i < prim.length && i < cap; i++) h.push(item(prim[i], n++, res));
      if (prim.length > cap) h.push('<button type="button" class="sr-more">' + esc(fmt(T.more, {n: Math.min(prim.length, 60)})) + '</button>');
    }
    var lastRel = null;
    rel.forEach(function (x) {
      if (x.rel !== lastRel) { lastRel = x.rel; h.push('<div class="sr-head sr-rel">' + esc(fmt(T.also, {x: S.label(x.rel, LANG)})) + '</div>'); }
      h.push(item(x, n++, res));
    });
    if (res.state === 'place-miss' || (res.state === 'gap' && rel.length)) h.push(addLink());
    box().innerHTML = h.join('');
    sel = n ? 0 : -1;
  }

  function doSearch(q) {
    var opts = forced && input() && input().value === forced.label ? {concept: forced.c} : null;
    if (!opts) forced = null;
    var res = S.search(opts ? forced.q : q, opts);
    render(res);
    gaQueue(opts ? forced.label : q, res);
  }

  window.runSearch = function (q) {
    q = String(q == null ? '' : q);
    showAll = false;
    if (!q.trim()) { forced = null; startState(); return; }
    if (!S.ready()) {
      hint('<p>' + esc(T.load) + '</p>');
      load(function () { var v = input() ? input().value : q; if (v.trim()) doSearch(v); });
      return;
    }
    doSearch(q);
  };
  window.openSearch = function () {
    document.getElementById('search-modal').style.display = 'block';
    if (input() && T.ph) input().setAttribute('placeholder', T.ph);
    setTimeout(function () { var el = input(); if (el) el.focus(); }, 50);
    if (!input().value.trim()) startState();
    load(function () {});
  };
  window.closeSearch = function () {
    gaFlush();
    document.getElementById('search-modal').style.display = 'none';
    input().value = '';
    forced = null;
    startState();
  };
  function focusables() { return box().querySelectorAll('a.sr-it, .sr-sug'); }
  window.searchKey = function (e) {
    var items = focusables();
    if (e.key === 'Escape') { window.closeSearch(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(sel + 1, items.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(sel - 1, 0); }
    else if (e.key === 'Enter') { if (items[sel]) { e.preventDefault(); items[sel].click(); } else gaFlush(); return; }
    else return;
    Array.prototype.forEach.call(items, function (el, k) { el.classList.toggle('sr-active', k === sel); });
    if (items[sel]) items[sel].scrollIntoView({block: 'nearest'});
  };

  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target : null;
    if (!t || !t.closest('#search-results')) return;
    var sug = t.closest('.sr-sug'), chip = t.closest('.sr-chip'), more = t.closest('.sr-more');
    var a = t.closest('a.sr-it'), cta = t.closest('[data-cta]');
    if (sug) {
      var c = +sug.getAttribute('data-c'), lab = S.label(c, LANG);
      forced = {c: c, label: lab, q: input().value};
      input().value = lab; input().focus();
      doSearch(lab);
      return;
    }
    if (chip) { forced = null; input().value = chip.getAttribute('data-q'); input().focus(); window.runSearch(input().value); return; }
    if (more) { showAll = true; render(last); return; }
    if (a || cta) {
      gaFlush();
      var term = (gaSent || input().value || '').slice(0, 100);
      if (a) ga('search_click', {search_term: term, search_position: (+a.getAttribute('data-i') || 0) + 1,
        search_item: (a.getAttribute('href') || '').replace(/^\/(nl|es|zh|fr|pt)\//, '/').slice(0, 100),
        search_rel: a.getAttribute('data-rel') ? 1 : 0});
      else ga('search_cta', {search_term: term,
        search_concepts: last ? last.concepts.map(function (z) { return z.id; }).join(',').slice(0, 100) : ''});
    }
  });
  window.addEventListener('pagehide', gaFlush);
  document.addEventListener('keydown', function (e) {
    var ae = document.activeElement || {};
    if (e.key === '/' && ae.tagName !== 'INPUT' && ae.tagName !== 'TEXTAREA' && !ae.isContentEditable) {
      e.preventDefault(); window.openSearch();
    }
  });
})();
