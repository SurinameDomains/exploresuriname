
/* ── Dropdown (desktop) ─────────────────────────────────────────────────── */
var _openDd = null;
var _ddTimer = null;
function openDd(id) {
  if (_ddTimer) { clearTimeout(_ddTimer); _ddTimer = null; }
  if (_openDd && _openDd !== id) closeDd(_openDd);
  var menu = document.getElementById(id + '-menu');
  var chev = document.getElementById(id) ? document.getElementById(id).querySelector('.dd-chevron') : null;
  if (menu) menu.classList.remove('hidden');
  if (chev) chev.style.transform = 'rotate(180deg)';
  _openDd = id;
}
function closeDd(id) {
  _ddTimer = setTimeout(function() {
    var menu = document.getElementById(id + '-menu');
    var chev = document.getElementById(id) ? document.getElementById(id).querySelector('.dd-chevron') : null;
    if (menu) menu.classList.add('hidden');
    if (chev) chev.style.transform = '';
    if (_openDd === id) _openDd = null;
    _ddTimer = null;
  }, 80);
}
function toggleDd(id) {
  var menu = document.getElementById(id + '-menu');
  var btn  = document.getElementById(id);
  var chev = btn ? btn.querySelector('.dd-chevron') : null;
  if (_openDd && _openDd !== id) {
    var prev = document.getElementById(_openDd + '-menu');
    var prevBtn = document.getElementById(_openDd);
    if (prev)    prev.classList.add('hidden');
    if (prevBtn) { var c = prevBtn.querySelector('.dd-chevron'); if(c) c.style.transform=''; }
    _openDd = null;
  }
  if (!menu) return;
  var isOpen = !menu.classList.contains('hidden');
  if (isOpen) {
    menu.classList.add('hidden');
    if (chev) chev.style.transform = '';
    _openDd = null;
  } else {
    menu.classList.remove('hidden');
    if (chev) chev.style.transform = 'rotate(180deg)';
    _openDd = id;
  }
}
document.addEventListener('click', function(e) {
  if (_openDd && !document.getElementById(_openDd).contains(e.target)) {
    var menu = document.getElementById(_openDd + '-menu');
    var btn  = document.getElementById(_openDd);
    if (menu) menu.classList.add('hidden');
    if (btn)  { var c = btn.querySelector('.dd-chevron'); if(c) c.style.transform=''; }
    _openDd = null;
  }
});
/* ── Mobile accordion ───────────────────────────────────────────────────── */
function toggleMobileMenu() {
  var mm = document.getElementById('mm');
  mm.classList.toggle('hidden');
}
function toggleMobGroup(id) {
  var body = document.getElementById(id);
  var btn  = body ? body.previousElementSibling : null;
  var chev = btn  ? btn.querySelector('.mob-chevron') : null;
  if (!body) return;
  var isOpen = !body.classList.contains('hidden');
  body.classList.toggle('hidden', isOpen);
  if (chev) chev.style.transform = isOpen ? '' : 'rotate(180deg)';
}
/* GA4 nav_click (21 Oct 2026): where a menu click came from (tile = phone shortcut
   row, mob_menu, desk_top, desk_menu, rail) and where it went (path without
   language prefix or .html), so the menu order can be checked against use.
   Window/bubble like the outbound-click handler, i.e. after the gtag loader. */
window.addEventListener('click', function(e) {
  try {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var l = a.closest('#mg-quick') ? 'tile' : a.closest('#mm') ? 'mob_menu' :
            a.closest('.util-rail') ? 'rail' : a.closest('.dd-menu') ? 'desk_menu' :
            a.closest('.navlinks') ? 'desk_top' : '';
    if (!l) return;
    var p = new URL(a.href, location.href).pathname
              .replace(/^[/](nl|es|zh|fr|pt)[/]/, '/').replace(/[.]html$/, '').replace(/[/]index$/, '/');
    window.dataLayer = window.dataLayer || [];
    if (!window.gtag) { window.gtag = function() { window.dataLayer.push(arguments); }; }
    window.gtag('event', 'nav_click', {nav_loc: l, nav_item: p.slice(0, 60)});
  } catch (x) {}
});
