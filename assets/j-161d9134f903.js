
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
