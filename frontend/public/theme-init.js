// public/theme-init.js - runs before first paint (no flash); external file so a strict CSP can stay `script-src 'self'`.
;(function () {
  var pref = 'system'
  try {
    pref = localStorage.getItem('synapse.theme') || 'system'
  } catch (e) {}
  var dark =
    pref === 'dark' ||
    (pref === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', dark)
  var meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', dark ? '#243341' : '#F0F2F5')
})()
