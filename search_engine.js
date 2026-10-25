/* Explore Suriname site search v2 (25 Oct 2026). Source of truth for the
   search modal; generate.py inlines this file into every page.
   Data: /search-index.json (per language tree) + /search-vocab.json (shared,
   built from search_vocab.py). Pipeline per query:
   1. tokens -> units: concept phrases (longest match, also glued: "nagel studio"
      = "nagelstudio"), places (district / neighbourhood), filler words (never
      required), Dutch plural/diminutive forms, compounds ("verjaardagstaart",
      "nagelstylist"), literal words, typo fixes (1 edit from 4 letters, 2 from 8,
      same first letter), and an as-you-type prefix for the last word.
   2. every concept / text unit is required; places and filler only add score.
      Place matches rank first ("kapper lelydorp"). If nothing matches all units,
      brand words alone are required, then a loose pass ranks by units matched.
   3. a recognised need with no listing gives a "not listed yet" state (the
      "Jouw zaak?" card) plus related types, never a dead end.
   Node: module.exports = {init, search} for tests (website-tests / harness). */
(function (root) {
  'use strict';
  var IDX = null, VOC = null, P = null;
  /* other names for a whole district (a neighbourhood only boosts its own street) */
  var DIST_ALIAS = {'parbo': 1, 'pbo': 1, '\u5e15\u62c9\u9a6c\u91cc\u535a': 1};

  function fold(x) {
    return String(x || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }
  /* Latin words, plus runs of Chinese characters (the /zh/ tree) */
  function toks(x) { return fold(x).match(/[a-z0-9]+|[\u3400-\u9fff]+/g) || []; }
  function isCJK(w) { return /[\u3400-\u9fff]/.test(w); }
  function pad(x) { return ' ' + toks(x).join(' ') + ' '; }
  function hasW(padded, term) { return padded.indexOf(' ' + term + ' ') >= 0; }
  function hasPre(padded, term) { return padded.indexOf(' ' + term) >= 0; }

  /* Damerau-Levenshtein with an early exit above max. */
  function dl(a, b, max) {
    var la = a.length, lb = b.length;
    if (Math.abs(la - lb) > max) return max + 1;
    var d = [], i, j;
    for (i = 0; i <= la; i++) { d[i] = [i]; }
    for (j = 0; j <= lb; j++) { d[0][j] = j; }
    for (i = 1; i <= la; i++) {
      var rowMin = max + 1;
      for (j = 1; j <= lb; j++) {
        var c = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
        var v = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
        if (i > 1 && j > 1 && a.charCodeAt(i - 1) === b.charCodeAt(j - 2) && a.charCodeAt(i - 2) === b.charCodeAt(j - 1))
          v = Math.min(v, d[i - 2][j - 2] + 1);
        d[i][j] = v;
        if (v < rowMin) rowMin = v;
      }
      if (rowMin > max) return max + 1;
    }
    return d[la][lb];
  }

  /* Dutch / English inflection: plural, diminutive, -e. Only used to look a
     word up in the vocabulary, never to match free text, so over-stemming
     cannot create junk matches. */
  function variants(w) {
    var out = [], add = function (x) { if (x.length >= 3 && x !== w && out.indexOf(x) < 0) out.push(x); };
    if (/tjes$/.test(w)) add(w.slice(0, -4));
    if (/jes$/.test(w)) add(w.slice(0, -3));
    if (/tje$/.test(w)) add(w.slice(0, -3));
    if (/je$/.test(w)) add(w.slice(0, -2));
    if (/ies$/.test(w)) add(w.slice(0, -3) + 'y');
    if (/en$/.test(w)) { add(w.slice(0, -2)); if (/(.)\1en$/.test(w)) add(w.slice(0, -3)); }
    if (/s$/.test(w)) add(w.slice(0, -1));
    if (/e$/.test(w)) add(w.slice(0, -1));
    if (/es$/.test(w)) add(w.slice(0, -2));
    return out;
  }

  function prepare() {
    var C = VOC.c, i, j, t;
    var term = new Map(), maxN = 1, single = [], cid = {}, cjk = [];
    for (i = 0; i < C.length; i++) {
      cid[C[i].i] = i;
      for (j = 0; j < C[i].t.length; j++) {
        t = C[i].t[j];
        if (!term.has(t)) term.set(t, []);
        if (term.get(t).indexOf(i) < 0) term.get(t).push(i);
        var n = t.split(' ').length;
        if (n > maxN) maxN = n;
        if (n === 1 && !isCJK(t)) single.push(t);
        if (isCJK(t)) cjk.push(t);
      }
    }
    /* umbrella concepts ("party" = rental + supplies + catering ...) */
    var inc = C.map(function (c) { return (c.x || []).map(function (x) { return cid[x]; }).filter(function (x) { return x != null; }); });
    var rel = C.map(function (c) { return (c.r || []).map(function (x) { return cid[x]; }).filter(function (x) { return x != null; }); });
    var place = new Map(Object.keys(VOC.p).map(function (k) { return [k, VOC.p[k]]; }));
    Object.keys(VOC.p).forEach(function (k) { var n = k.split(' ').length; if (n > maxN) maxN = n; });
    var dist = {};
    Object.keys(VOC.p).forEach(function (k) { dist[fold(VOC.p[k])] = VOC.p[k]; });
    var filler = new Set(VOC.f), heads = new Set(VOC.h);
    var words = new Map(), members = C.map(function () { return 0; }), nameWords = new Set();
    for (i = 0; i < IDX.length; i++) {
      var e = IDX[i];
      e._n = fold(e.n);
      e._ns = pad(e.n);
      e._ng = e._ns.replace(/ /g, '');
      e._as = e.s ? pad(e.s) : ' ';
      e._ks = pad([e.k || '', e.a || '', e.s || ''].join(' '));
      /* kind from the URL, never from "c": the category label is translated
         in the /nl/ /es/ /zh/ /fr/ /pt/ copies of the index */
      var u0 = String(e.u || ''), isFlora = u0.indexOf('flora-fauna') === 0 || !!e.ffu;
      e._kind = isFlora ? (e.ffu ? 'flora' : 'florahub') : e.p ? 'page'
        : (e.t || e.s || u0.indexOf('listing/') === 0 ? 'listing' : 'guide');
      e._game = e._kind === 'guide' && / (game|spel)\b|puzzle|quiz|crossword/.test(e._ks);
      e._t = new Set();
      (e.t || []).forEach(function (x) { if (cid[x] != null) { e._t.add(cid[x]); members[cid[x]]++; } });
      (e._ns + e._ks).split(' ').forEach(function (w) { if (w.length > 1) words.set(w, (words.get(w) || 0) + 1); });
      if (e._kind === 'listing') e._ns.split(' ').forEach(function (w) { if (w.length > 3) nameWords.add(w); });
    }
    /* a word that only appears in the vocabulary still counts as "known" */
    P = {term: term, cjk: cjk, maxN: Math.min(maxN, 4), single: single, cid: cid, inc: inc, rel: rel, place: place, dist: dist,
         filler: filler, heads: heads, words: words, members: members, nameWords: nameWords,
         rw: new Set(VOC.rw || []), fx: C.map(function (c) { return c.fx != null && cid[c.fx] != null ? cid[c.fx] : null; })};
    /* concepts a listing's NAME says it is ("Pizza Hut", "Apotheek Soma"):
       ranked above listings that only offer it */
    for (i = 0; i < IDX.length; i++) {
      var nt = IDX[i]._ns.trim().split(' '), nc = new Set(), a, z;
      for (a = 0; a < nt.length; a++) for (z = 1; z <= 3 && a + z <= nt.length; z++) {
        var g = nt.slice(a, a + z).join(' '), hit = term.get(g);
        if (!hit && z === 1) { var vv = variants(g); for (var q = 0; q < vv.length && !hit; q++) hit = term.get(vv[q]); }
        if (hit) hit.forEach(function (c) { nc.add(c); });
      }
      IDX[i]._nc = nc;
    }
  }

  function conceptOf(w) { return P.term.get(w) || null; }
  function stemConcept(w) {
    var v = variants(w);
    for (var i = 0; i < v.length; i++) { var c = conceptOf(v[i]); if (c) return {c: c, w: v[i]}; }
    return null;
  }
  function anyConcept(w) { return conceptOf(w) ? {c: conceptOf(w), w: w} : stemConcept(w); }
  /* Dutch compounds put the head last: "verjaardagstaart" -> taart. A generic
     head ("studio", "man", "monteur") hands the meaning to the first part:
     "nagelstudio" -> nagel, "aircomonteur" -> airco. */
  function splitConcept(w) {
    if (w.length < 6 || (P.nameWords && P.nameWords.has(w))) return null;
    var k, a, b, hit;
    for (k = w.length - 3; k >= 3; k--) {
      a = w.slice(0, k); b = w.slice(k);
      if (P.heads.has(b) || P.heads.has(b.replace(/s$/, ''))) {
        hit = anyConcept(a) || (a.length > 4 && /s$/.test(a) ? anyConcept(a.slice(0, -1)) : null);
        if (hit) return {c: hit.c, w: hit.w, how: 'split'};
      }
    }
    for (k = 3; k <= w.length - 3; k++) {
      b = w.slice(k);
      hit = anyConcept(b);
      if (hit && b.length >= 4) return {c: hit.c, w: hit.w, how: 'split'};
    }
    return null;
  }
  function lcp(a, b) { var i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++; return i; }
  function fuzzyConcept(w) {
    if (w.length < 4) return null;
    var max = w.length >= 8 ? 2 : 1, best = max + 1, bestL = -1, out = null, i, t, d, l;
    for (i = 0; i < P.single.length; i++) {
      t = P.single[i];
      if (t.charCodeAt(0) !== w.charCodeAt(0) || t.length < 4) continue;
      d = dl(w, t, max);
      if (d > max) continue;
      l = lcp(w, t);
      if (d < best || (d === best && l > bestL)) { best = d; bestL = l; out = {c: conceptOf(t).slice(), w: t}; }
      else if (d === best && l === bestL) { conceptOf(t).forEach(function (x) { if (out.c.indexOf(x) < 0) out.c.push(x); }); }
    }
    return out;
  }
  function fuzzyPlace(w) {
    if (w.length < 5) return null;
    var max = w.length >= 8 ? 2 : 1, best = max + 1, out = null;
    P.place.forEach(function (d, t) {
      if (t.indexOf(' ') >= 0 || t.charCodeAt(0) !== w.charCodeAt(0)) return;
      var x = dl(w, t, max); if (x < best) { best = x; out = t; }
    });
    return best <= max ? out : null;
  }
  function fuzzyWord(w) {
    if (w.length < 5) return null;
    var max = w.length >= 8 ? 2 : 1, best = max + 1, out = null, bestN = 0;
    P.words.forEach(function (n, t) {
      if (t.charCodeAt(0) !== w.charCodeAt(0) || Math.abs(t.length - w.length) > max) return;
      var x = dl(w, t, max);
      if (x < best || (x === best && n > bestN)) { best = x; out = t; bestN = n; }
    });
    return best <= max ? out : null;
  }
  /* concepts with a term that starts with w, shortest completion first
     ("elekt" -> elektra/elektricien before elektronica) */
  function prefixConcepts(w) {
    var best = {}, out = [];
    if (w.length < 3) return out;
    P.term.forEach(function (cs, t) {
      if (t.indexOf(w) !== 0 || t === w) return;
      cs.forEach(function (c) { if (best[c] == null || t.length < best[c]) best[c] = t.length; });
    });
    out = Object.keys(best).map(Number);
    out.sort(function (a, b) { return best[a] - best[b] || P.members[b] - P.members[a]; });
    return out;
  }

  /* Chinese has no spaces: find concept labels and place names inside the run */
  function cjkUnits(w) {
    var out = [], cs = [], best = '';
    P.cjk.forEach(function (t) {
      if (w.indexOf(t) >= 0 || (w.length >= 2 && t.indexOf(w) >= 0)) {
        conceptOf(t).forEach(function (c) { if (cs.indexOf(c) < 0) cs.push(c); });
        if (t.length > best.length) best = t;
      }
    });
    P.place.forEach(function (d, t) { if (isCJK(t) && w.indexOf(t) >= 0) out.push({k: 'p', d: d, w: t, typed: t}); });
    if (P.filler.has(w)) out.push({k: 'f', w: w, typed: w});
    else if (cs.length) out.unshift({k: 'c', c: cs, w: best, how: 'exact', typed: w});
    else if (!out.length) out.push({k: 't', w: w, typed: w, pre: true});
    return out;
  }

  /* known as it stands; compounds ("suppermarkt") are checked for a typo
     before they are split, or "markt" would win over "supermarkt" */
  function known(w) {
    return conceptOf(w) || P.place.has(w) || P.filler.has(w) || P.words.has(w) || isCJK(w) || stemConcept(w);
  }
  function parse(q) {
    var T = toks(q), typing = !/\s$/.test(q), U = [], i = 0, n, s1, s2, hit, w, fixed = {};
    /* typos are fixed before phrases are read, so "chineese winkel" still
       becomes the phrase "chinees winkel" */
    /* tokens inside a known phrase ("salao de beleza") are left alone */
    var covered = {}, j0, n0;
    for (j0 = 0; j0 < T.length; j0++) for (n0 = 2; n0 <= Math.min(P.maxN, T.length - j0); n0++) {
      var ph = T.slice(j0, j0 + n0);
      if (conceptOf(ph.join(' ')) || conceptOf(ph.join('')) || P.place.has(ph.join(' '))) for (var c0 = j0; c0 < j0 + n0; c0++) covered[c0] = 1;
    }
    for (i = 0; i < T.length; i++) {
      if (covered[i]) continue;
      if (!conceptOf(T[i]) && !P.place.has(T[i]) && !P.filler.has(T[i])) {
        var st = stemConcept(T[i]); if (st) { T[i] = st.w; continue; }
      }
      if ((i === T.length - 1 && typing) || T[i].length < 4 || known(T[i])) continue;
      var fc = fuzzyConcept(T[i]), fp = fc ? null : fuzzyPlace(T[i]);
      if (fc) { fixed[i] = T[i]; T[i] = fc.w; } else if (fp) { fixed[i] = T[i]; T[i] = fp; }
    }
    i = 0;
    while (i < T.length) {
      hit = null;
      for (n = Math.min(P.maxN, T.length - i); n >= 1 && !hit; n--) {
        s1 = T.slice(i, i + n).join(' ');
        s2 = T.slice(i, i + n).join('');
        /* "mijn" (my / mine), "die", "can": a filler word only means the
           concept when it is the whole query */
        if (n === 1 && T.length > 1 && P.filler.has(s1)) continue;
        if (conceptOf(s1)) hit = {k: 'c', c: conceptOf(s1), w: s1, how: 'exact', n: n};
        else if (n > 1 && conceptOf(s2)) hit = {k: 'c', c: conceptOf(s2), w: s2, how: 'exact', n: n};
        else if (n > 1 && P.place.has(s1)) hit = {k: 'p', d: P.place.get(s1), w: s1, n: n};
      }
      if (hit) {
        hit.typed = T.slice(i, i + hit.n).join(' ');
        for (var f = i; f < i + hit.n; f++) if (fixed[f]) { hit.how = 'fuzzy'; hit.typed = hit.typed.replace(T[f], fixed[f]); }
        U.push(hit); i += hit.n; continue;
      }
      w = T[i];
      var last = i === T.length - 1, isTyping = last && typing;
      if (isCJK(w)) { cjkUnits(w).forEach(function (u) { U.push(u); }); i++; continue; }
      if (P.place.has(w)) U.push({k: 'p', d: P.place.get(w), w: w, typed: w});
      else if (P.filler.has(w)) U.push({k: 'f', w: w, typed: w});
      else if (w.length <= 2 && T.length > 1 && !/^[0-9]+$/.test(w)) U.push({k: 'f', w: w, typed: w, pre: isTyping});
      else if ((hit = stemConcept(w))) U.push({k: 'c', c: hit.c, w: hit.w, how: 'stem', typed: w});
      else if (isTyping && w.length >= 3 && prefixConcepts(w).length) U.push({k: 'x', c: prefixConcepts(w), w: w, typed: w});
      else if ((hit = splitConcept(w))) U.push({k: 'c', c: hit.c, w: hit.w, how: 'split', typed: w});
      else if (P.words.has(w) || (isTyping && w.length < 4)) U.push({k: 't', w: w, typed: w, pre: true});
      else if ((hit = fuzzyConcept(w))) U.push({k: 'c', c: hit.c, w: hit.w, how: 'fuzzy', typed: w});
      else if ((hit = fuzzyPlace(w))) U.push({k: 'p', d: P.place.get(hit), w: hit, typed: w, how: 'fuzzy'});
      else if ((hit = fuzzyWord(w))) U.push({k: 't', w: hit, typed: w, how: 'fuzzy'});
      else U.push({k: 't', w: w, typed: w, pre: isTyping});
      i++;
    }
    /* "telefoon laten repareren" asks for a repair shop, not a phone shop */
    if (U.some(function (u) { return P.rw.has(u.w) || P.rw.has(u.typed); })) {
      U.forEach(function (u) {
        if (u.k !== 'c') { if (P.rw.has(u.w)) u.k = 'f'; return; }
        u.c = u.c.map(function (c) { return P.fx[c] != null ? P.fx[c] : c; }).filter(function (c, k, a) { return a.indexOf(c) === k; });
      });
    }
    /* a query of only filler words ("open", "service") searches them literally */
    if (!U.some(function (u) { return u.k !== 'f'; })) U.forEach(function (u) { if (u.w.length > 1) u.k = 't'; u.pre = true; });
    return U;
  }

  function withInc(cs) {
    var out = cs.slice();
    cs.forEach(function (c) { P.inc[c].forEach(function (x) { if (out.indexOf(x) < 0) out.push(x); }); });
    return out;
  }

  /* how well entry e satisfies a concept unit (0 = not at all) */
  function cScore(e, u) {
    var cs = u.cx || (u.cx = withInc(u.c)), i, j, terms;
    if (e._kind === 'listing') {
      for (i = 0; i < cs.length; i++) if (e._t.has(cs[i])) {
        for (j = 0; j < cs.length; j++) if (e._nc.has(cs[j])) return 650;
        return 500;
      }
      /* untagged listings fall back on their name ("Garage de Paarl" is a
         taxi firm: its tags win over the word in its name) */
      if (!e._t.size) {
        if (u.w.length > 2 && hasW(e._ns, u.w)) return 450;
        for (i = 0; i < cs.length; i++) if (e._nc.has(cs[i])) return 420;
      }
      if (u.w.length > 2 && hasW(e._as, u.w)) return 300;
      return 0;
    }
    /* guides, category pages, Flora & Fauna: only the words the person typed
       (all synonyms would drag in every page that mentions "tools" or "tax") */
    var ws = u.ws || (u.ws = [u.w, u.typed].filter(function (x, k, a) { return x && a.indexOf(x) === k; }));
    var hit = false;
    for (i = 0; i < ws.length && !hit; i++) {
      hit = hasW(e._ns, ws[i]) || hasW(e._ks, ws[i]);
      /* "money exchange": every word of the phrase on the page counts too */
      if (!hit && ws[i].indexOf(' ') > 0) {
        var parts = ws[i].split(' ').filter(function (x) { return x.length > 2 && !P.filler.has(x); });
        hit = parts.length > 1 && parts.every(function (x) { return hasW(e._ns, x) || hasW(e._ks, x); });
      }
    }
    if (!hit) return 0;
    if (e._kind === 'page') return 700;
    /* site tools answer the need first; games only match by name */
    if (e._kind === 'guide') return e._game ? 200 : 700;
    return 90;
  }
  /* literal word: same weights as the v1 matcher (name beats keywords) */
  function tScore(e, w, pre) {
    if (e._n === w) return 1000;
    if (w.length > 3 && e._ng.indexOf(w) === 0) return 560;   /* "remax" -> "Re Max" */
    if (e._n.indexOf(w) === 0) return 600;
    if (pre ? hasPre(e._ns, w) : hasW(e._ns, w)) return 420;
    if (hasW(e._ns, w)) return 420;
    if (hasW(e._ks, w) || (pre && w.length > 2 && hasPre(e._ks, w))) return e._kind === 'guide' || e._kind === 'page' ? 300 : 130;
    if (w.length > 3 && e._n.indexOf(w) >= 0) return 90;
    return 0;
  }
  function pScore(e, u) {
    if (hasW(e._ns, u.w) || hasW(e._as, u.w)) return 2;
    if (u.w.length > 3 && (hasPre(e._ns, u.w) || hasPre(e._as, u.w))) return 2;   /* Latour -> Latourweg */
    if (hasW(e._ks, u.w)) return 1.5;
    var d = u.d, isDistrict = fold(d) === u.w || DIST_ALIAS[u.w] === 1;
    if (e.a === d && (isDistrict || d !== 'Paramaribo')) return 1;
    return 0;
  }
  function uScore(e, u) {
    if (u.k === 'c') return cScore(e, u);
    if (u.k === 't') return tScore(e, u.w, u.pre) * (u.how === 'fuzzy' ? 0.8 : 1);
    if (u.k === 'x') {
      var s = tScore(e, u.w, true);
      if (e._kind === 'listing') for (var i = 0; i < u.c.length; i++) if (e._t.has(u.c[i])) { s = Math.max(s, 320 - Math.min(i, 4) * 15); break; }
      return s;
    }
    return 0;
  }

  /* the exact words typed still count inside a concept: "bird watching",
     "eco lodge", "moksi alesi" rank the places that say so above the rest
     of the type */
  function typedBonus(e, u) {
    var ws = u.tw || (u.tw = String(u.typed || '').split(' ').filter(function (x) { return x.length > 2 && !P.filler.has(x); })), b = 0;
    for (var i = 0; i < ws.length; i++) {
      if (hasPre(e._ns, ws[i])) b += 120;
      else if (hasW(e._ks, ws[i])) b += 40;
    }
    return b;
  }

  function run(U, mode) {
    var req = U.filter(function (u) { return u.k === 'c' || u.k === 't' || u.k === 'x'; });
    var places = U.filter(function (u) { return u.k === 'p'; });
    var opt = U.filter(function (u) { return u.k === 'f' || (mode === 'brand' && u.k === 'c') || (mode === 'concepts' && u.k === 't'); });
    if (mode === 'brand') req = req.filter(function (u) { return u.k !== 'c'; });
    if (mode === 'concepts') req = req.filter(function (u) { return u.k !== 't'; });
    var placeOnly = !req.length && places.length;
    /* a whole district ("in paramaribo") still lets a guide page lead; a
       neighbourhood or a name ("hotel peperpot") puts the local hits first */
    var wide = places.every(function (u) { return fold(u.d) === u.w || DIST_ALIAS[u.w] === 1; });
    var out = [];
    for (var i = 0; i < IDX.length; i++) {
      var e = IDX[i], total = 0, matched = 0, strongest = 0, j, s;
      for (j = 0; j < req.length; j++) {
        s = uScore(e, req[j]);
        if (mode === 'brand' && req[j].k === 't' && s < 420) s = 0;   /* a brand word must hit the name */
        if (s && req[j].k !== 't') s += typedBonus(e, req[j]);
        if (mode === 'concepts' && j > 0) s *= 0.5;                    /* the first need typed leads */
        if (s) { total += s; matched++; if (s > strongest) strongest = s; }
        else if (mode !== 'loose' && mode !== 'concepts') { total = -1; break; }
      }
      if (total < 0) continue;
      var pl = 0;
      for (j = 0; j < places.length; j++) pl = Math.max(pl, pScore(e, places[j]));
      if (placeOnly) { if (!pl) continue; total += 200 * pl; matched = 1; strongest = 200; }
      else if (!matched) continue;
      for (j = 0; j < opt.length; j++) {
        s = opt[j].k === 'c' ? Math.max(cScore(e, opt[j]), typedBonus(e, opt[j])) : tScore(e, opt[j].w, opt[j].pre);
        if (s) total += s * 0.25;
      }
      if (e.p) total += 250;
      if (mode === 'loose') {
        if (strongest < 130 || matched < Math.min(2, req.length)) continue;
        total += matched * 100000;
      }
      if (mode === 'concepts') total += matched * 1000;
      /* a site tool or category page that answers the need ranks with the
         local results, not after them ("things to do in paramaribo") */
      out.push({e: e, s: total, pl: pl, g: wide && (e._kind === 'guide' || e._kind === 'page') && strongest >= 520});
    }
    return out;
  }

  function rank(list, havePlace) {
    list.sort(function (a, b) {
      if (havePlace && (a.pl >= 1 || a.g) !== (b.pl >= 1 || b.g)) return a.pl >= 1 || a.g ? -1 : 1;
      /* ties: the better documented listing first (longer keyword blob) */
      return b.s - a.s || (b.pl - a.pl) || b.e._ks.length - a.e._ks.length || a.e.n.length - b.e.n.length;
    });
    if (list.length) {
      var floor = list[0].s * 0.2;
      list = list.filter(function (x, i) { return i < 3 || x.s >= floor || (havePlace && x.pl >= 1); });
    }
    return list;
  }

  /* opts.concept: a picked suggestion (concept index); the places typed in
     the query still apply ("kapp lelydorp" -> Hairdressers in Lelydorp) */
  function search(q, opts) {
    var res = {q: q, units: [], items: [], results: [], concepts: [], suggest: [], gap: [], state: '', place: null};
    if (!IDX || !VOC) return res;
    if (!P) prepare();
    q = String(q || '');
    if (!q.trim()) return res;
    var U = parse(q);
    if (opts && opts.concept != null && VOC.c[opts.concept]) {
      U = [{k: 'c', c: [opts.concept], w: VOC.c[opts.concept].t[0], how: 'exact', typed: ''}]
        .concat(U.filter(function (u) { return u.k === 'p'; }));
    }
    res.units = U;
    var places = U.filter(function (u) { return u.k === 'p'; });
    res.place = places.length ? places[0] : null;
    var cu = U.filter(function (u) { return u.k === 'c'; });
    var tu = U.filter(function (u) { return u.k === 't'; });
    var list = run(U, 'strict'), mode = 'strict';
    /* words that occur nowhere on the site ("done", "please") stop blocking */
    var unknown = tu.filter(function (u) { return (u.how === 'fuzzy' || !P.words.has(u.w)) && !u.pre; })
      .concat(U.filter(function (u) { return u.k === 'x' && U.length > 1; }));
    if (!list.length && unknown.length && unknown.length < U.length) {
      var U2 = U.map(function (u) { return unknown.indexOf(u) >= 0 ? {k: 'f', w: u.w, typed: u.typed} : u; });
      list = run(U2, 'strict'); if (list.length) { mode = 'drop'; U = U2; tu = tu.filter(function (u) { return unknown.indexOf(u) < 0; }); }
    }
    if (!list.length && cu.length && tu.length) { list = run(U, 'brand'); mode = 'brand'; }
    /* needs first: "taxi bellen", "apotheek open zondag", "verzekering auto" */
    if (cu.length && (cu.length > 1 || tu.length) && list.filter(function (x) { return x.e._kind === 'listing'; }).length < 3) {
      var more = run(U, 'concepts'), seen = new Set(list.map(function (x) { return x.e; }));
      more = rank(more, !!places.length).filter(function (x) { return !seen.has(x.e); });
      if (more.length) { list = rank(list, !!places.length).concat(more); mode = list.length > more.length ? mode + '+concepts' : 'concepts'; }
    }
    if (!list.length && U.filter(function (u) { return u.k !== 'f' && u.k !== 'p'; }).length > 1) { list = run(U, 'loose'); mode = 'loose'; }
    if (mode.indexOf('concepts') < 0) list = rank(list, !!places.length);
    var items = list.map(function (x) { return {e: x.e, pl: x.pl >= 1}; });
    /* recognised needs, with how many listings offer them */
    cu.forEach(function (u) {
      u.c.forEach(function (c) {
        var cs = withInc([c]), n = 0;
        cs.forEach(function (x) { n += P.members[x]; });
        if (!res.concepts.some(function (z) { return z.c === c; })) res.concepts.push({c: c, id: VOC.c[c].i, n: n, how: u.how});
      });
    });
    U.filter(function (u) { return u.k === 'x'; }).forEach(function (u) {
      u.c.slice(0, 6).forEach(function (c) {
        var n = 0; withInc([c]).forEach(function (x) { n += P.members[x]; });
        if (n) res.suggest.push({c: c, id: VOC.c[c].i, n: n});
      });
      res.suggest = res.suggest.slice(0, 4);   /* prefixConcepts order: shortest completion first */
    });
    /* "nothing listed yet": a recognised need that no listing offers */
    var listingHits = items.filter(function (x) { return x.e._kind === 'listing'; }).length;
    var single = cu.length === 1 && !tu.length && !U.some(function (u) { return u.k === 'x'; });
    if (cu.length && mode !== 'brand') {
      var toolHit = items.some(function (x) { return x.e._kind === 'guide' || x.e._kind === 'page'; });
      res.concepts.forEach(function (z) { if (!z.n && !toolHit) res.gap.push(z.id); });
      if (res.gap.length) res.state = 'gap';
    }
    if (places.length && items.length && !items.some(function (x) { return x.pl; })) res.state = res.state || 'place-miss';
    /* fewer than 3 real hits for a single need: add related types */
    if (single && listingHits < 3) {
      var have = new Set(items.map(function (x) { return x.e; }));
      var relC = [];
      cu[0].c.forEach(function (c) { P.rel[c].forEach(function (r) { if (relC.indexOf(r) < 0 && cu[0].c.indexOf(r) < 0) relC.push(r); }); });
      relC.slice(0, 3).forEach(function (r) {
        var ru = {k: 'c', c: [r], w: VOC.c[r].t[0]}, add = [];
        for (var i = 0; i < IDX.length; i++) {
          var e = IDX[i];
          if (have.has(e) || e._kind !== 'listing' || !cScore(e, ru)) continue;
          var pl = 0; places.forEach(function (p) { pl = Math.max(pl, pScore(e, p)); });
          add.push({e: e, s: cScore(e, ru) + pl * 100, pl: pl});
        }
        add.sort(function (a, b) { return (b.pl >= 1) - (a.pl >= 1) || b.s - a.s; });
        add.slice(0, 6).forEach(function (x) { have.add(x.e); items.push({e: x.e, pl: x.pl >= 1, rel: r}); });
      });
    }
    if (!items.length && !res.state) res.state = 'none';
    res.mode = mode;
    res.items = items;
    res.results = items.map(function (x) { return x.e.u; });
    return res;
  }

  function init(idx, voc) { IDX = idx; VOC = voc; P = null; }
  function ready() { return !!(IDX && VOC); }
  function label(c, lang) { var l = VOC && VOC.c[c] && VOC.c[c].l; return l ? (l[lang] || l.en) : ''; }
  function conceptIndex(id) { if (!P) prepare(); return P.cid[id]; }

  var api = {init: init, ready: ready, search: search, label: label, conceptIndex: conceptIndex, fold: fold};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ESR_SEARCH = api;
})(this);
