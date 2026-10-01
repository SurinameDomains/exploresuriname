
const _CAT_C = {"Eat & Drink": "#CA4E2F", "Stay": "#A56822", "Nature": "#35825C", "Activities": "#1C809C", "Shopping": "#B85185", "Services": "#4676B9", "Guides": "#677889", "Sightseeing": "#35825C"};
/* The hint is read from the page, so the Dutch and Spanish trees reuse their
   translated text when the box is cleared (build_i18n does not touch JS). */
const _HINT0 = (document.getElementById('search-hint') || {}).textContent || 'Start typing to search listings…';
let _SI = null;
let _SI_loading = false;
let _sel = -1;

function _loadSI(cb) {
  if (_SI) { cb(); return; }
  if (_SI_loading) { setTimeout(() => _loadSI(cb), 50); return; }
  _SI_loading = true;
  const depth = window.location.pathname.split('/').length > 3 ? '../../' : '';
  fetch(depth + 'search-index.json')
    .then(r => r.json())
    .then(data => { _SI = data; cb(); })
    .catch(() => { _SI = []; cb(); });
}
function openSearch() {
  document.getElementById('search-modal').style.display = 'block';
  setTimeout(() => document.getElementById('search-input').focus(), 50);
  _loadSI(() => {});
}
function closeSearch() {
  document.getElementById('search-modal').style.display = 'none';
  document.getElementById('search-input').value = '';
  document.getElementById('search-results').innerHTML = '<p id="search-hint" style="text-align:center;color:var(--ink-soft);font-size:.85rem;padding:32px 0"></p>';
  document.getElementById('search-hint').textContent = _HINT0;
  _sel = -1;
}
/* ── Search matching ─────────────────────────────────────────────────────
   Tokenised AND matching over name + keyword blob (which now includes the
   listing description), with diacritic folding, EN/NL + cuisine synonyms and
   relevance ranking. Replaces the old single-substring filter, which missed
   "sushi" for Norrii Zushii and broke on any multi-word query. */
const _SYN = {
  sushi:['sushi','zushi','sashimi','japanese','japans'],
  japanese:['japanese','japans','sushi','zushi','teppanyaki','ramen'],
  thai:['thai','thais','thaise'],
  chinese:['chinese','chinees','chinees','dimsum'],
  indian:['indian','indiaas','indiase','tandoori','curry'],
  roti:['roti','indian','indiaas'],
  javanese:['javanese','javaans','javaanse','warung','saoto','bami'],
  creole:['creole','creoolse','creools','surinamese','surinaamse'],
  surinamese:['surinamese','surinaamse','creole','creoolse','local'],
  pizza:['pizza','pizzas','italian','italiaans','italiaanse'],
  italian:['italian','italiaans','italiaanse','pizza','pasta'],
  burger:['burger','burgers','hamburger'],
  bbq:['bbq','barbecue','grill','grilled'],
  coffee:['coffee','koffie','cafe','espresso','cappuccino','barista'],
  cafe:['cafe','coffee','koffie','lunchroom'],
  bakery:['bakery','bakkerij','patisserie','pastry','pastries','bread','brood'],
  cake:['cake','cakes','taart','patisserie','pastry'],
  icecream:['icecream','ice','ijs','gelato'],
  vegan:['vegan','vegetarian','vegetarisch','plantbased'],
  vegetarian:['vegetarian','vegetarisch','vegan'],
  seafood:['seafood','fish','vis','shrimp'],
  bar:['bar','lounge','pub','drinks','cocktails','borrel'],
  restaurant:['restaurant','restaurants','eten','dining','eetcafe','food'],
  eten:['eten','food','restaurant','dining'],
  hotel:['hotel','hotels','accommodation','verblijf','overnachten','slapen','guesthouse'],
  lodge:['lodge','lodges','resort','ecolodge','jungle'],
  resort:['resort','resorts','lodge','vakantie'],
  pharmacy:['pharmacy','apotheek','drogisterij','drugstore'],
  apotheek:['apotheek','pharmacy','drogisterij','drugstore'],
  salon:['salon','kapper','barber','hairdresser','hair','beauty','nails'],
  kapper:['kapper','barber','salon','hair','hairstudio'],
  barber:['barber','kapper','barbershop','salon'],
  gym:['gym','fitness','sportschool','workout','crossfit'],
  fitness:['fitness','gym','sportschool','pilates','yoga'],
  spa:['spa','massage','wellness','sauna'],
  massage:['massage','spa','wellness','masseur'],
  bank:['bank','banking','banken','geldzaken'],
  atm:['atm','geldautomaat','pinautomaat','pinnen','cash','bank'],
  supermarket:['supermarket','supermarkt','grocery','groceries','boodschappen','market'],
  supermarkt:['supermarkt','supermarket','grocery','boodschappen'],
  butcher:['butcher','slagerij','slager','meat','vlees'],
  laundry:['laundry','wasserij','drycleaning','stomerij'],
  carrental:['carrental','rental','huurauto','autoverhuur','rentacar'],
  rental:['rental','rentals','huur','verhuur','huurauto'],
  garage:['garage','automotive','autobedrijf','monteur','repair'],
  insurance:['insurance','verzekering','verzekeringen','assurantie'],
  notary:['notary','notaris','notariaat'],
  school:['school','scholen','education','onderwijs','academy'],
  vet:['vet','veterinary','dierenarts','dierenkliniek'],
  livestock:['livestock','vee','veevoer','pluimvee','poultry','landbouw','farm','boer'],
  landbouw:['landbouw','agriculture','farming','farm','livestock','vee','boer'],
  dierenarts:['dierenarts','veterinary','vet','dierenkliniek'],
  telecom:['telecom','internet','mobile','simcard','simkaart','prepaid'],
  realestate:['realestate','vastgoed','makelaar','makelaardij','property','huis'],
  vastgoed:['vastgoed','realestate','makelaar','makelaardij','property'],
  tour:['tour','tours','excursie','excursies','trip','uitstapje','guide'],
  tours:['tours','tour','excursies','trips','reizen'],
  beach:['beach','strand','coast','kust'],
  river:['river','rivier','kreek','creek','water'],
  jungle:['jungle','rainforest','oerwous','oerwoud','forest','bos','regenwoud'],
  nature:['nature','natuur','park','reserve','wildlife'],
  wifi:['wifi','internet','telecom'],
  casino:['casino','gambling','gokken','slots'],
  museum:['museum','musea','history','geschiedenis','gallery'],
  tattoo:['tattoo','tattoos','tatoeage','piercing'],
  security:['security','beveiliging','bewaking'],
  cleaning:['cleaning','schoonmaak','cleaningservice','poetsen'],
  parking:['parking','parkeren'],
  wedding:['wedding','bruiloft','trouwen','events','feest'],
  party:['party','feest','events','evenementen'],
  kids:['kids','children','kinderen','family','familie'],
  halal:['halal'],
  delivery:['delivery','bezorging','takeaway','afhalen','bezorgen'],
  north:['north','noord','noordelijk','geyersvlijt','kwatta'],
  south:['south','zuid','zuidelijk','latour'],
  centre:['centre','center','centrum','city','downtown'],
  paramaribo:['paramaribo','pbm','city']
};
/* The table above is written one-way; mirror it so "koffie" finds the "coffee"
   row and vice versa. One hop only, no transitive chains. */
const _SYN_X = (function () {
  const m = {};
  const add = (a, b) => { (m[a] = m[a] || []).push(b); };
  for (const key in _SYN) {
    const row = _SYN[key];
    for (let i = 0; i < row.length; i++) {
      for (let j = 0; j < row.length; j++) if (i !== j) add(row[i], row[j]);
      if (row[i] !== key) { add(row[i], key); add(key, row[i]); }
    }
  }
  for (const k in m) m[k] = m[k].filter((v, i, a) => v !== k && a.indexOf(v) === i);
  return m;
})();
function _sFold(x) {
  return (x || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}
/* Filler words are dropped from the query, otherwise strict AND matching kills
   natural-language searches like "where to eat roti in Paramaribo" (which the
   hero placeholder actively invites people to type). */
const _QSTOP = new Set(['the','and','for','with','from','into','that','this','all','any','some',
 'where','what','when','how','who','why','best','top','good','cheap','near','nearby','around',
 'are','was','you','your','can','have','has','its','but','out','let','get','place','places',
 'in','on','at','to','of','is','it','my','me','we','us','or','an','as','by','be','do','if',
 'de','het','een','van','voor','met','naar','aan','bij','over','waar','hoe','wat','welke',
 'beste','goede','dichtbij','zijn','ook','deze','dat','die','dit','niet','uit','ligt','plek',
 'kan','ik','wil','zoek','zoeken','vind','vinden','ben','hebben','doen','gaan','iets',
 'find','need','want','looking','show','give','there','here','something','anything']);
function _sTokens(q) {
  /* Keep single characters: the first keystroke of every search is one letter,
     and it must still be a valid prefix query. */
  const raw = _sFold(q).split(/[^a-z0-9]+/).filter(t => t.length > 0);
  const kept = raw.filter(t => !_QSTOP.has(t));
  return kept.length ? kept : raw;          /* never return an empty query */
}
function _sEsc(x) {
  return (x || '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function _sRxEsc(x) {
  return x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
/* A token matches itself, its singular form, or a known synonym. Synonym and
   plural hits score lower so exact wording always ranks first. */
function _sTerms(tok) {
  /* [term, weight, wholeWordOnly]. What the user actually typed may match as a
     prefix (so "restau" finds restaurants); short synonyms must match a whole
     word, otherwise "maki" hits "making" and drags junk into a sushi search. */
  const out = [[tok, 1, false]];
  if (tok.length > 4 && tok.slice(-1) === 's') out.push([tok.slice(0, -1), 0.9, false]);
  const syn = _SYN_X[tok];
  if (syn) for (let i = 0; i < syn.length; i++) out.push([syn[i], 0.5, syn[i].length < 5]);
  return out;
}
function _sScore(rec, toks, loose) {
  if (!rec._n) {
    rec._n = _sFold(rec.n);
    rec._k = _sFold([rec.n, rec.k || '', rec.a || '', rec.c || ''].join(' '));
  }
  const n = rec._n, k = rec._k;
  let total = 0, matched = 0, strongest = 0;
  for (let i = 0; i < toks.length; i++) {
    const terms = _sTerms(toks[i]);
    let best = 0;
    for (let j = 0; j < terms.length; j++) {
      const t = terms[j][0], w = terms[j][1];
      const wb = new RegExp('\\b' + _sRxEsc(t) + (terms[j][2] ? '\\b' : ''));
      let s = 0;
      if (n === t)             s = 1000;
      else if (n.indexOf(t) === 0) s = 600;
      else if (wb.test(n))     s = 420;
      else if (wb.test(k))     s = 130;
      /* Mid-word hits only for the literal token, and cheap: they are what made
         "hot pot" rank Hotel Peperpot above the actual hot pot restaurants. */
      else if (w === 1 && t.length > 3 && n.indexOf(t) >= 0) s = 90;
      s = s * w;
      if (s > best) best = s;
    }
    if (best) { total += best; matched++; if (best > strongest) strongest = best; }
    else if (!loose) return 0;    /* strict pass: every token must match */
  }
  if (!matched) return 0;
  if (total > 0 && rec.p) total += 250;   /* category browse pages outrank a
                                             single listing on generic queries */
  /* Loose pass ranks by how many query words matched, then by score, and needs
     at least one solid hit so leftover words can't drag in noise. */
  if (loose) {
    if (strongest < 130 || matched < Math.min(2, toks.length)) return 0;
    return matched * 100000 + Math.min(Math.round(total), 99999);
  }
  return total;
}
/* Highlight each matching token (and its matching synonym) in the name. */
function _sMark(name, toks) {
  const pats = [];
  const nf = _sFold(name);
  for (let i = 0; i < toks.length; i++) {
    const terms = _sTerms(toks[i]);
    for (let j = 0; j < terms.length; j++) {
      if (nf.indexOf(terms[j][0]) >= 0) { pats.push(_sRxEsc(terms[j][0])); break; }
    }
  }
  let out = _sEsc(name);
  if (!pats.length) return out;
  return out.replace(new RegExp('(' + pats.join('|') + ')', 'gi'), '<mark>$1</mark>');
}
function _sHint(box, msg) {
  box.innerHTML = '<p id="search-hint" style="text-align:center;color:var(--ink-soft);'
    + 'font-size:.85rem;padding:32px 0">' + msg + '</p>';
}
function runSearch(q) {
  const box = document.getElementById('search-results');
  q = q.trim();
  if (!q) { _sHint(box, _HINT0); _sel = -1; return; }
  if (!_SI) {
    _loadSI(() => runSearch(q));
    box.innerHTML = '<p style="text-align:center;color:var(--ink-soft);font-size:.85rem;padding:32px 0">Loading…</p>';
    return;
  }
  const toks = _sTokens(q);
  if (!toks.length) { _sHint(box, _HINT0); _sel = -1; return; }
  let scored = [];
  for (let pass = 0; pass < 2; pass++) {
    const loose = pass === 1;
    for (let i = 0; i < _SI.length; i++) {
      const sc = _sScore(_SI[i], toks, loose);
      if (sc > 0) scored.push([sc, _SI[i]]);
    }
    if (scored.length || toks.length < 2) break;   /* only fall back if AND found nothing */
  }
  scored.sort((a, b) => b[0] - a[0] || a[1].n.length - b[1].n.length);
  if (scored.length) {
    const floor = scored[0][0] * 0.2;
    scored = scored.filter(p => p[0] >= floor);
  }
  const hits = scored.slice(0, 12).map(p => p[1]);
  if (!hits.length) { box.innerHTML = '<p style="text-align:center;color:var(--ink-soft);font-size:.85rem;padding:32px 0">No results for "' + _sEsc(q) + '"</p>'; return; }
  const depth = window.location.pathname.split('/').length > 3 ? '../../' : '';
  box.innerHTML = hits.map((h, i) => {
    const hi = _sMark(h.n, toks);
    const col = _CAT_C[h.c] || '#6b7280';
    return '<a href="' + depth + h.u + '" class="' + (i===0?'sr-active':'') + '">'
      + '<span class="sr-badge" style="background:' + col + '">' + h.c + '</span>'
      + '<span class="sr-name">' + hi + '</span>'
      + (h.a ? '<span class="sr-area">' + h.a + '</span>' : '')
      + '</a>';
  }).join('');
  _sel = 0;
}
function searchKey(e) {
  const items = document.querySelectorAll('#search-results a');
  if (e.key === 'Escape') { closeSearch(); return; }
  if (e.key === 'ArrowDown') { e.preventDefault(); _sel = Math.min(_sel+1, items.length-1); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); _sel = Math.max(_sel-1, 0); }
  else if (e.key === 'Enter') { if(items[_sel]) window.location = items[_sel].href; return; }
  else return;
  items.forEach((el,i) => el.classList.toggle('sr-active', i===_sel));
  if(items[_sel]) items[_sel].scrollIntoView({block:'nearest'});
}
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault(); openSearch();
  }
});
