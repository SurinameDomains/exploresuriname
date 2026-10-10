"""Shared menu contents (Oct 2026): keep the published site under the GitHub
Pages 1 GB limit.

Every page carried the full menu (the six desktop dropdowns and the six mobile
accordion groups, ~16 KB) in its own HTML: about 160 MB across the site. This
step moves the CONTENTS of those twelve containers into one small shared
script per language, /assets/n-<hash>.js, and leaves the empty containers in
the page. The script tag sits directly after </nav>, so it runs while the page
is still being parsed, before anything after the menu exists, and fills the
containers. Everything after that point sees the same menu DOM as before.

Why this cannot change what a page does:
  * Only the inner HTML of #dd-*-menu and #mg-* is moved. The top bar, the
    buttons, the language links, the util rail and every attribute of the
    containers themselves stay in the page, untouched.
  * Links are stored as root-relative paths ("/nl/restaurants.html"), which
    resolve to exactly the URL the page's relative link resolved to.
  * The highlighted "you are here" link differs per page. Its class and style
    are kept on the container (data-na) and put back by the script, so the
    menu DOM is the same as the inline version.
  * The script runs at the spot the menu HTML used to be parsed. If it ever
    failed to load, so would the existing /assets/ menu script (open/close),
    which the menu already depends on: no new failure mode.
  * A page is only changed when all twelve containers are found and every link
    in them is of a known kind. Anything unexpected: the page stays inline.
  * offline.html and 404.html keep everything inline (they must work alone).
  * File names are content hashes (no stale cache; the service worker's
    cache-first rule for .js is right for them). A file is only deleted when
    no page anywhere references it and it has been unused for KEEP_DAYS.

Runs at the end of build_i18n.py, after every language tree is written.
"""
import datetime as _dt
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets"
MANIFEST = OUT / "nav-manifest.json"
NAME_RE = re.compile(r"^n-[0-9a-f]{12}\.js$")
REF_RE = re.compile(r'/assets/(n-[0-9a-f]{12}\.js)')
KEEP_DAYS = 30
SKIP = {"offline.html", "404.html"}
SKIP_DIRS = {".git", "node_modules", "assets", "vendor", "fonts", "icons", "images",
             "data", "__pycache__", ".github", "scripts", "tests"}

IDS = ("dd-expl-menu", "dd-plan-menu", "dd-live-menu", "dd-learn-menu", "dd-games-menu",
       "dd-biz-menu", "mg-expl", "mg-plan", "mg-live", "mg-learn", "mg-games", "mg-biz")
# the class every NOT-highlighted link in that container has (generate.py nav_html)
INACTIVE = {"dd-expl-menu": "nvm text-gray-700 rounded-lg"}
for _i in IDS:
    INACTIVE.setdefault(_i, "nvb text-gray-600 rounded-lg" if _i.startswith("mg-")
                        else "nva text-gray-700 rounded-lg")
ACTIVE_STYLE = "color:var(--forest);background:var(--mint)"

OPEN_RE = {i: re.compile(r'<div\b[^>]*\bid="' + re.escape(i) + r'"[^>]*>') for i in IDS}
DIV_TAG_RE = re.compile(r"<(/?)div\b[^>]*>", re.I)
A_TAG_RE = re.compile(r"<a\b[^>]*>", re.I)
ATTR_RE = re.compile(r'\s([a-zA-Z_:][-a-zA-Z0-9_:.]*)="([^"]*)"')

JS_TMPL = ('(function(){var d=document,F=%s;for(var k in F){var e=d.getElementById(k);'
           'if(!e||!e.hasAttribute("data-nf"))continue;e.removeAttribute("data-nf");'
           'e.innerHTML=F[k];var a=e.getAttribute("data-na");if(!a)continue;'
           'e.removeAttribute("data-na");var L=e.getElementsByTagName("a"),A=JSON.parse(a);'
           'for(var i=0;i<A.length;i++){var x=L[A[i][0]];if(!x)continue;x.className=A[i][1];'
           'if(A[i][2])x.setAttribute("style",A[i][2]);else x.removeAttribute("style");}}})();')


class Skip(Exception):
    pass


def _page_url(rel):
    """URL the page is served at, as a base for its relative links. A file
    x.html is served at /x (same directory), index.html at its folder."""
    return "/" + rel.replace("\\", "/")


def _body_span(h, start_tag_end):
    """End index of the inner HTML of the <div> whose open tag ends at
    start_tag_end (balanced <div> counting)."""
    depth = 1
    for m in DIV_TAG_RE.finditer(h, start_tag_end):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.start()
    raise Skip("unbalanced div")


def _norm_body(body, cid, base):
    """Return (shared_body, active_list). shared_body has root-relative hrefs and
    every link in its not-highlighted form."""
    acts = []
    out = []
    pos = 0
    idx = 0
    for m in A_TAG_RE.finditer(body):
        tag = m.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cls = attrs.get("class", "")
        sty = attrs.get("style")
        href = attrs.get("href")
        if href is None:
            raise Skip("link without href")
        new = tag
        if cls != INACTIVE[cid] or sty is not None:
            # highlighted link: only the known highlight markup is accepted
            if sty != ACTIVE_STYLE or "font-semibold" not in cls.split():
                raise Skip("unknown link markup in " + cid)
            acts.append([idx, cls, sty])
            new = new.replace(f'class="{cls}"', f'class="{INACTIVE[cid]}"', 1)
            new = re.sub(r'\sstyle="[^"]*"', "", new, count=1)
        if not re.match(r"^(?:[a-z][a-z0-9+.-]*:|/|#)", href, re.I):
            absu = urljoin(base, html.unescape(href))
            if not absu.startswith("/"):
                raise Skip("href did not resolve")
            new = new.replace(f'href="{href}"', f'href="{html.escape(absu, quote=True)}"', 1)
        out.append(body[pos:m.start()])
        out.append(new)
        pos = m.end()
        idx += 1
    out.append(body[pos:])
    return "".join(out), acts


def _extract(h, rel):
    """Return (new_page_without_script, fragment_dict, insert_at) or raise Skip."""
    if 'data-nf=""' in h or "data-nf " in h or REF_RE.search(h):
        raise Skip("already done")
    base = _page_url(rel)
    spans = []
    for cid in IDS:
        ms = list(OPEN_RE[cid].finditer(h))
        if len(ms) != 1:
            raise Skip("container count " + cid)
        m = ms[0]
        end = _body_span(h, m.end())
        spans.append((cid, m, end))
    frag = {}
    pieces = []
    pos = 0
    for cid, m, end in sorted(spans, key=lambda s: s[1].start()):
        if m.start() < pos:
            raise Skip("nested containers")
        body = h[m.end():end]
        shared, acts = _norm_body(body, cid, base)
        frag[cid] = shared
        open_tag = m.group(0)
        extra = ' data-nf=""'
        if acts:
            extra += ' data-na="' + html.escape(json.dumps(acts, ensure_ascii=False,
                                                           separators=(",", ":")), quote=True) + '"'
        new_open = open_tag[:-1] + extra + ">"
        pieces.append(h[pos:m.start()])
        pieces.append(new_open)
        pos = end
    pieces.append(h[pos:])
    new = "".join(pieces)
    last = max(new.find(f'id="{cid}"') for cid in IDS)
    close = new.find("</nav>", last)
    if close < 0 or "<nav" in new[last:close]:
        raise Skip("menu not inside the main <nav>")
    return new, frag, close + len("</nav>")


SCRIPT_RE = re.compile(r'\n?<script src="/assets/(n-[0-9a-f]{12}\.js)"></script>')
FRAG_RE = re.compile(r"F=(\{.*\});for\(var k in F\)", re.S)


def _rel_href(target, base):
    """Inverse of the root-relative rewrite: the link as generate.py wrote it
    relative to the page (e.g. /restaurants.html -> ../../restaurants.html)."""
    import posixpath
    path, sep, rest = target.partition("#")
    q = ""
    if "?" in path:
        path, q = path.split("?", 1)
        q = "?" + q
    frag = sep + rest
    base_dir = posixpath.dirname(base) or "/"
    r = posixpath.relpath(path, base_dir) if path else ""
    if path.endswith("/") and r and not r.endswith("/"):
        r += "/"
    if r == ".":
        r = "./"
    return r + q + frag


def inline(h, rel):
    """Put the shared menu back into a page that nav_extract.run() changed, so
    build_i18n can treat it like a fresh generate.py page (e.g. a business page
    kept from the previous build when its engine tests fail). Returns h
    unchanged when the page is not extracted. Raises if it cannot restore."""
    if 'data-nf=""' not in h:
        return h
    m = SCRIPT_RE.search(h)
    if not m:
        raise RuntimeError("extracted page without its menu script: " + rel)
    js = (OUT / m.group(1)).read_text(encoding="utf-8")
    fm = FRAG_RE.search(js)
    frag = json.loads(fm.group(1).replace("<\\/", "</"))
    h = h[:m.start()] + h[m.end():]
    base = _page_url(rel)
    for cid in IDS:
        om = re.search(r'<div\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*>', h)
        if not om or 'data-nf=""' not in om.group(0):
            raise RuntimeError("container missing: " + cid)
        tag = om.group(0)
        acts = []
        am = re.search(r' data-na="([^"]*)"', tag)
        if am:
            acts = json.loads(html.unescape(am.group(1)))
        clean = tag.replace(' data-nf=""', "", 1)
        if am:
            clean = clean.replace(am.group(0), "", 1)
        body = frag[cid]
        act = {a[0]: a for a in acts}
        out = []
        pos = 0
        for idx, a in enumerate(A_TAG_RE.finditer(body)):
            t = a.group(0)
            hm = re.search(r'href="([^"]*)"', t)
            href = hm.group(1)
            if href.startswith("/") and not href.startswith("//"):
                t = t.replace(hm.group(0), 'href="' + html.escape(_rel_href(html.unescape(href), base), quote=True) + '"', 1)
            if idx in act:
                _, cls, sty = act[idx]
                t = t.replace(f'class="{INACTIVE[cid]}"', f'class="{cls}"', 1)
                if sty:
                    t = t[:-1] + f' style="{sty}">'
            out.append(body[pos:a.start()])
            out.append(t)
            pos = a.end()
        out.append(body[pos:])
        end = om.end()
        if not h.startswith("</div>", end):
            raise RuntimeError("container not empty: " + cid)
        h = h[:om.start()] + clean + "".join(out) + h[end:]
    return h


def _walk():
    for p in ROOT.rglob("*.html"):
        rel = p.relative_to(ROOT).as_posix()
        if rel.split("/")[0] in SKIP_DIRS or p.name in SKIP:
            continue
        yield p, rel


def run(today=None, cleanup=True):
    today = today or _dt.date.today().isoformat()
    OUT.mkdir(exist_ok=True)
    written = {}
    changed = saved = skipped = 0
    referenced = set()
    reasons = {}
    for p, rel in _walk():
        try:
            h = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if 'id="dd-expl-menu"' not in h:
            continue
        try:
            new, frag, at = _extract(h, rel)
        except Skip as e:
            r = str(e)
            if r != "already done":
                skipped += 1
                reasons[r] = reasons.get(r, 0) + 1
            referenced.update(REF_RE.findall(h))
            continue
        js = JS_TMPL % json.dumps(frag, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
        name = "n-" + hashlib.md5(js.encode("utf-8")).hexdigest()[:12] + ".js"
        if name not in written:
            f = OUT / name
            # the file must exist with exactly these bytes before any page points at it
            if not f.exists() or f.read_text(encoding="utf-8") != js:
                with open(f, "w", encoding="utf-8", newline="") as fh:
                    fh.write(js)
            if f.read_text(encoding="utf-8") != js:
                raise RuntimeError("nav fragment write check failed: " + name)
            written[name] = True
        new = new[:at] + f'\n<script src="/assets/{name}"></script>' + new[at:]
        p.write_text(new, encoding="utf-8")
        referenced.add(name)
        changed += 1
        saved += len(h.encode("utf-8")) - len(new.encode("utf-8"))

    removed = 0
    if cleanup:
        try:
            seen = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            seen = {}
        for name in referenced:
            seen[name] = today
        cutoff = (_dt.date.fromisoformat(today) - _dt.timedelta(days=KEEP_DAYS)).isoformat()
        for f in OUT.iterdir():
            if not NAME_RE.match(f.name) or f.name in referenced:
                continue
            last = seen.get(f.name)
            if last is None:
                seen[f.name] = today
            elif last < cutoff:
                f.unlink()
                seen.pop(f.name, None)
                removed += 1
        seen = {k: v for k, v in seen.items() if (OUT / k).exists()}
        new_manifest = json.dumps(seen, indent=1, sort_keys=True) + "\n"
        if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != new_manifest:
            MANIFEST.write_text(new_manifest, encoding="utf-8")
    why = (" (kept inline: " + ", ".join(f"{k} x{v}" for k, v in reasons.items()) + ")") if reasons else ""
    return (f"nav: {len(written)} shared menu files, {changed} pages updated, "
            f"{saved / 1e6:.1f} MB less HTML, {skipped} pages kept inline{why}, {removed} old files removed")


if __name__ == "__main__":
    print(run())
