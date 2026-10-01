/* Flora & Fauna of Suriname — section script (flora_fauna_pages.py).
   window.FF_I18N (prepended at build time) holds every label in EN/NL/ES/ZH:
     k      : {key: {en, nl, es, zh}}   (keys match data-k attributes in the page)
     static : languages that have their own static species pages
     site   : [[path, label]] main-site links for the menu
   Jobs: ?lang= localization of English species pages, menus, search across all
   names in all languages, list filter/sort, district map and month chart. */
(function () {
  "use strict";
  var doc = document, html = doc.documentElement;
  var I18N = window.FF_I18N || {k: {}, static: [], site: []};
  var HREFLANG = {nl: "nl", es: "es", zh: "zh-Hans"};
  var LANG = (html.getAttribute("lang") || "en").slice(0, 2);

  function L(k, lg) { var v = I18N.k[k] || {}; return v[lg || LANG] || v.en || ""; }
  function norm(s) {
    return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[’'`]/g, "'");
  }
  function escH(s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  function prefix(lg) { return lg === "en" ? "" : "/" + lg; }

  /* ── ?lang=xx on an English page ───────────────────────
     Species pages exist as static pages only in some languages. For the others the
     English page is opened with ?lang=xx: go to the static page when there is one
     (hreflang link), otherwise localize the labels and the name in place. */
  var QL = null;
  try { QL = new URLSearchParams(location.search).get("lang"); } catch (e) {}
  if (LANG === "en" && QL && HREFLANG[QL]) {
    var alt = doc.querySelector('link[rel="alternate"][hreflang="' + HREFLANG[QL] + '"]');
    if (alt) { location.replace(alt.href + location.hash); return; }
    LANG = QL;
    html.setAttribute("lang", QL === "zh" ? "zh-Hans" : QL);
    doc.querySelectorAll("[data-k]").forEach(function (el) {
      var v = L(el.getAttribute("data-k"), QL); if (v) el.textContent = v;
    });
    var cell = doc.querySelector('td[data-lang="' + QL + '"]'), h1 = doc.querySelector(".ff-sp-head h1");
    if (cell && h1 && cell.textContent.trim() && cell.textContent.trim() !== "—") {
      var en = h1.textContent; h1.textContent = cell.textContent.trim();
      doc.title = doc.title.replace(en, h1.textContent);
      var cur = doc.querySelector(".ff-bc-cur"); if (cur) cur.textContent = h1.textContent;
      var im = doc.querySelector(".ff-photo img"); if (im) im.alt = h1.textContent;
    }
    var tpl = doc.querySelector('template[data-wlang="' + QL + '"]'), wt = doc.querySelector(".ff-wtext");
    if (tpl && wt) {
      wt.innerHTML = tpl.innerHTML;
      wt.setAttribute("lang", QL === "zh" ? "zh-Hans" : QL);
    }
    doc.querySelectorAll("a[href]").forEach(function (a) {
      var u; try { u = new URL(a.getAttribute("href"), location.href); } catch (e) { return; }
      if (u.origin !== location.origin || /[?&]lang=/.test(u.search) || /^\/(nl|es|zh)(\/|$)/.test(u.pathname)) return;
      if (a.closest(".ff-lmenu")) return;
      if (a.classList.contains("ff-card")) { u.search = "?lang=" + QL; }      /* another species: same treatment */
      else if (/\.(css|js|json|svg|png|jpe?g|webp)$/.test(u.pathname)) return;
      else { u.pathname = "/" + QL + u.pathname; }                          /* hub, groups, site pages exist in every tree */
      a.setAttribute("href", u.pathname + u.search + u.hash);
    });
  }
  var PREFIX = prefix(LANG);

  /* ── menus ─────────────────────────────────────────── */
  var mm = doc.querySelector(".ff-mmenu");
  if (mm && !mm.children.length) {
    mm.innerHTML = I18N.site.map(function (x) {
      var lab = x[1][LANG] || x[1].en;
      return '<a href="' + PREFIX + "/" + x[0] + '">' + escH(lab) + "</a>";
    }).join("");
  }
  function toggler(btnSel, menuSel) {
    var b = doc.querySelector(btnSel), m = doc.querySelector(menuSel);
    if (!b || !m) return;
    b.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var open = !m.classList.contains("open");
      doc.querySelectorAll(".ff-lmenu.open,.ff-mmenu.open").forEach(function (x) { x.classList.remove("open"); });
      if (open) m.classList.add("open");
      b.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
  toggler(".ff-lbtn", ".ff-lmenu");
  toggler(".ff-mbtn", ".ff-mmenu");
  doc.addEventListener("click", function () {
    doc.querySelectorAll(".ff-lmenu.open,.ff-mmenu.open").forEach(function (x) { x.classList.remove("open"); });
  });

  /* ── district map + month chart (drawn from data attributes) ── */
  var ORDER = ["Sipaliwini", "Brokopondo", "Marowijne", "Para", "Saramacca", "Coronie", "Nickerie", "Commewijne", "Wanica", "Paramaribo"];
  doc.querySelectorAll(".ff-map[data-d]").forEach(function (box) {
    var on = (box.getAttribute("data-d") || "").split(",");
    var svg = '<svg viewBox="0 0 300 307" role="img" aria-label="' + escH(L("u.where")) + '">' + ORDER.map(function (n) {
      return '<use href="/flora-fauna/assets/districts.svg#d-' + n + '" class="ff-d' + (on.indexOf(n) > -1 ? " on" : "") + '"/>';
    }).join("") + "</svg>";
    box.insertAdjacentHTML("afterbegin", svg);
  });
  doc.querySelectorAll(".ff-months[data-m]").forEach(function (box) {
    var m = box.getAttribute("data-m").split(",").map(Number), mx = Math.max.apply(null, m) || 1;
    box.setAttribute("role", "img"); box.setAttribute("aria-label", L("u.when"));
    box.innerHTML = m.map(function (v, i) {
      return '<div class="ff-mb"><span class="ff-mbar" style="height:' + Math.max(4, Math.round(100 * v / mx)) + '%" title="' + v + '"></span>'
        + '<span class="ff-ml">' + escH(L("m." + i)) + "</span></div>";
    }).join("");
  });

  /* ── search overlay (built here, so it costs nothing in the HTML) ── */
  var so = doc.createElement("div");
  so.className = "ff-so"; so.hidden = true;
  so.setAttribute("role", "dialog"); so.setAttribute("aria-modal", "true"); so.setAttribute("aria-label", L("u.search_btn"));
  so.innerHTML = '<div class="ff-so-box"><div class="ff-so-bar">'
    + '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
    + '<input type="search" class="ff-so-in" autocomplete="off" spellcheck="false" placeholder="' + escH(L("u.search_ph")) + '">'
    + '<button type="button" class="ff-so-x">' + escH(L("u.close")) + "</button></div>"
    + '<div class="ff-so-res"><p class="ff-so-hint">' + escH(L("u.search_hint")) + "</p></div></div>";
  doc.body.appendChild(so);
  var inp = so.querySelector(".ff-so-in"), res = so.querySelector(".ff-so-res");
  var IDX = null, loading = false, sel = -1;
  function load(cb) {
    if (IDX) return cb();
    if (loading) return;
    loading = true;
    res.innerHTML = '<p class="ff-so-hint">' + escH(L("u.loading")) + "</p>";
    fetch("/flora-fauna/assets/search.json", {cache: "force-cache"}).then(function (r) { return r.json(); }).then(function (rows) {
      IDX = rows.map(function (r) {
        return {u: r[0], l: r[1], n: {en: r[2], nl: r[3], es: r[4], zh: r[5]}, loc: r[6], g: r[7], p: r[8], o: r[9], s: r[10] || "",
                h: norm([r[1], r[2], r[3], r[4], r[5], r[6]].join(" | "))};
      });
      loading = false; cb();
    }).catch(function () { loading = false; });
  }
  function open() {
    so.hidden = false; doc.body.style.overflow = "hidden";
    setTimeout(function () { inp.focus(); }, 30);
    load(function () { run(); });
  }
  function close() { so.hidden = true; doc.body.style.overflow = ""; }
  doc.querySelectorAll("[data-ff-search]").forEach(function (b) { b.addEventListener("click", open); });
  so.addEventListener("click", function (ev) { if (ev.target === so) close(); });
  so.querySelector(".ff-so-x").addEventListener("click", close);
  doc.addEventListener("keydown", function (ev) {
    if (ev.key === "/" && so.hidden && !/input|textarea|select/i.test((ev.target.tagName || ""))) { ev.preventDefault(); open(); }
    if (so.hidden) return;
    var links = res.querySelectorAll("a");
    if (ev.key === "Escape") close();
    else if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      sel = Math.max(0, Math.min(links.length - 1, sel + (ev.key === "ArrowDown" ? 1 : -1)));
      links.forEach(function (a, i) { a.classList.toggle("sel", i === sel); });
      if (links[sel]) links[sel].scrollIntoView({block: "nearest"});
    } else if (ev.key === "Enter" && links.length) {
      ev.preventDefault(); location.href = (links[sel >= 0 ? sel : 0]).href;
    }
  });
  function score(e, q, words) {
    var best = 0, names = [e.n[LANG], e.n.en, e.l, e.loc, e.n.nl, e.n.es, e.n.zh];
    for (var i = 0; i < names.length; i++) {
      var v = norm(names[i]); if (!v) continue;
      if (v === q) best = Math.max(best, 100 - i);
      else if (v.indexOf(q) === 0) best = Math.max(best, 80 - i);
      else if ((" " + v).indexOf(" " + q) > -1) best = Math.max(best, 60 - i);
    }
    if (!best) {
      for (var j = 0; j < words.length; j++) if (e.h.indexOf(words[j]) < 0) return 0;
      best = 30;
    }
    return best + (e.p ? 8 : 0) + Math.min(6, Math.log(1 + e.o));
  }
  function url(e) {
    /* species page in this language? otherwise the English page localizes itself */
    if (LANG === "en") return "/flora-fauna/" + e.u;
    if (!e.p || e.s.indexOf(LANG) > -1) return PREFIX + "/flora-fauna/" + e.u;
    return "/flora-fauna/" + e.u + "?lang=" + LANG;
  }
  function run() {
    if (!IDX) return;
    var q = norm(inp.value.trim()); sel = -1;
    if (q.length < 2) { res.innerHTML = '<p class="ff-so-hint">' + escH(L("u.search_hint")) + "</p>"; return; }
    var words = q.split(/\s+/), out = [];
    for (var i = 0; i < IDX.length; i++) { var s = score(IDX[i], q, words); if (s) out.push([s, IDX[i]]); }
    out.sort(function (a, b) { return b[0] - a[0]; });
    out = out.slice(0, 40);
    if (!out.length) { res.innerHTML = '<p class="ff-so-hint">' + escH(L("u.no_results")) + "</p>"; return; }
    res.innerHTML = out.map(function (x) {
      var e = x[1], name = e.n[LANG] || e.n.en || e.l;
      var meta = (name !== e.l ? "<i>" + escH(e.l) + "</i>" : "") + (e.loc ? " &middot; " + escH(e.loc) : "");
      return '<a href="' + escH(url(e)) + '"><span class="ff-so-c">' + escH(L("g." + e.g)) + "</span>"
        + '<span class="ff-so-n">' + escH(name.charAt(0).toUpperCase() + name.slice(1)) + "</span>"
        + (meta ? '<span class="ff-so-m">' + meta + "</span>" : "") + "</a>";
    }).join("");
  }
  var tmr; inp.addEventListener("input", function () { clearTimeout(tmr); tmr = setTimeout(run, 90); });

  /* ── list filter + sort ────────────────────────────── */
  var filt = doc.querySelector(".ff-filter"), sort = doc.querySelector(".ff-sort");
  var lists = Array.prototype.slice.call(doc.querySelectorAll(".ff-list"));
  var none = doc.querySelector(".ff-none");
  function nameOf(el) {
    var n = el.querySelector(".ff-cn") || el.querySelector(".ff-rn") || el.querySelector(".ff-rl");
    return norm(n ? n.textContent : "");
  }
  function latinOf(el) {
    var n = el.querySelector(".ff-lat,.ff-rl") || el.querySelector(".ff-cn");
    return norm(n ? n.textContent : "");
  }
  function applyFilter() {
    var q = norm(filt.value.trim()), words = q ? q.split(/\s+/) : [], shown = 0;
    lists.forEach(function (ul) {
      Array.prototype.forEach.call(ul.children, function (el) {
        var h = norm(el.textContent), ok = true;
        for (var i = 0; i < words.length; i++) if (h.indexOf(words[i]) < 0) { ok = false; break; }
        el.hidden = !ok; if (ok) shown++;
      });
      var sec = ul.closest(".ff-check");
      if (sec) sec.hidden = !Array.prototype.some.call(ul.children, function (c) { return !c.hidden; });
    });
    if (none) none.hidden = shown > 0;
  }
  function applySort() {
    var mode = sort.value;
    lists.forEach(function (ul) {
      var items = Array.prototype.slice.call(ul.children);
      items.sort(function (a, b) {
        if (mode === "n") return nameOf(a).localeCompare(nameOf(b));
        if (mode === "l") return latinOf(a).localeCompare(latinOf(b));
        return (+b.getAttribute("data-o") - +a.getAttribute("data-o")) || (+b.getAttribute("data-r") - +a.getAttribute("data-r"));
      });
      items.forEach(function (el) { ul.appendChild(el); });
    });
  }
  if (filt) filt.addEventListener("input", applyFilter);
  if (sort) sort.addEventListener("change", applySort);
})();
