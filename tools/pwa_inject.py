#!/usr/bin/env python3
"""Make a Godot web build installable as its own standalone PWA.

Run against a game's build dir (the Godot "Web" export output) BEFORE deploying
it to S3. Adds, idempotently:
  - pwa-icon-192 / -512 / -maskable.png  (from the build's index.icon.png)
  - manifest.webmanifest                 (scope "./"  -> /<id>/ , display standalone)
  - sw.js                                (minimal fetch handler = installability)
  - a <head> block in index.html         (manifest link, metas, SW register, Install button)

All games sit on the one play.munro.games origin at /<id>/, so each manifest's
relative scope/start_url + a per-folder service worker makes each game a separate
installable app that launches standalone (no browser address bar).

Usage: pwa_inject.py <build-dir> <game-id> [name] [orientation] [theme-color]
"""
import sys, os, json, re, hashlib
from PIL import Image

build = sys.argv[1]
gid = sys.argv[2]
name = sys.argv[3] if len(sys.argv) > 3 else gid.replace('-', ' ').title()
orientation = sys.argv[4] if len(sys.argv) > 4 else 'any'
theme = sys.argv[5] if len(sys.argv) > 5 else '#0d0d0d'
# overlay "off" when the game has its own in-menu Install button (calls window.pwaInstall()).
overlay = (len(sys.argv) <= 6) or (sys.argv[6].lower() != 'off')

idx_path = os.path.join(build, 'index.html')
if not os.path.exists(idx_path):
    sys.exit(f"pwa_inject: no index.html in {build}")

# ---- icons (from the Godot-exported project icon) ----
src = os.path.join(build, 'index.icon.png')
if not os.path.exists(src):
    sys.exit(f"pwa_inject: no index.icon.png in {build}")
base = Image.open(src).convert('RGBA')
base.resize((512, 512), Image.LANCZOS).convert('RGB').save(os.path.join(build, 'pwa-icon-512.png'))
base.resize((192, 192), Image.LANCZOS).convert('RGB').save(os.path.join(build, 'pwa-icon-192.png'))

# Maskable: icon at 80% on a background sampled from its own corners, so no
# launcher mask ever shows a white border.
def corner_bg(im):
    px = im.convert('RGB').load()
    w, h = im.size
    cs = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    return tuple(sum(c[i] for c in cs) // 4 for i in range(3))

bg = Image.new('RGBA', (512, 512), corner_bg(base) + (255,))
side = round(512 * 0.80)
bg.alpha_composite(base.resize((side, side), Image.LANCZOS), ((512 - side) // 2, (512 - side) // 2))
bg.convert('RGB').save(os.path.join(build, 'pwa-icon-maskable.png'))

# ---- manifest ----
manifest = {
    "id": f"/{gid}/",
    "name": name,
    "short_name": name[:24],
    "start_url": "./index.html",
    "scope": "./",
    "display": "standalone",
    "orientation": orientation,
    "background_color": "#000000",
    "theme_color": theme,
    "icons": [
        {"src": "pwa-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "pwa-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "pwa-icon-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}
with open(os.path.join(build, 'manifest.webmanifest'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(manifest, f, indent=2)

# ---- head injection (idempotent, between markers) ----
# Always expose a small install API the game (or the overlay) can call:
#   window.pwaCanInstall  bool   - a native install prompt is ready
#   window.pwaIsIOS       bool   - iOS Safari (manual Share -> Add to Home Screen)
#   window.pwaStandalone  bool   - already launched as an installed app
#   window.pwaInstall()   -> 'prompt' | 'ios' | 'none'
api = """<!-- pwa:start (tools/pwa_inject.py) -->
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="%THEME%">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="%NAME%">
<link rel="apple-touch-icon" href="pwa-icon-192.png">
<script>(function(){
/* Pause audio when the page is hidden or unfocused (returning to the home
screen etc.). Godot's game loop freezes when hidden, but its Web Audio context
keeps playing, so we suspend it. Wrap AudioContext to track the engine's one. */
var AC=window.AudioContext||window.webkitAudioContext;
if(AC){
var ctxs=[];
function W(){var c=Reflect.construct(AC,arguments,W);ctxs.push(c);return c;}
W.prototype=AC.prototype;
window.AudioContext=W;if(window.webkitAudioContext)window.webkitAudioContext=W;
function setSusp(s){ctxs.forEach(function(c){try{if(s){c.suspend();}else{c.resume();}}catch(e){}});}
document.addEventListener('visibilitychange',function(){setSusp(document.hidden);});
window.addEventListener('blur',function(){setSusp(true);});
window.addEventListener('focus',function(){if(!document.hidden){setSusp(false);}});
}
})();</script>
<script>(function(){
if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}
window.pwaStandalone=(window.matchMedia&&matchMedia('(display-mode: standalone)').matches)||navigator.standalone===true;
window.pwaIsIOS=/iP(hone|od|ad)/.test(navigator.platform)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1)||/iPhone|iPad|iPod/.test(navigator.userAgent);
window.pwaCanInstall=false;
var dp=null;
window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();dp=e;window.pwaCanInstall=true;});
window.addEventListener('appinstalled',function(){dp=null;window.pwaCanInstall=false;});
window.pwaInstall=function(){
if(dp){dp.prompt();dp.userChoice.then(function(){dp=null;window.pwaCanInstall=false;});return 'prompt';}
if(window.pwaIsIOS){return 'ios';}
return 'none';
};
})();</script>
"""

# Optional floating overlay button (default on). Off when the game supplies its
# own in-menu Install button that calls window.pwaInstall().
overlay_block = """<style>#pwaInstall{position:fixed;left:12px;bottom:12px;z-index:9999;display:none;padding:9px 15px;border:0;border-radius:999px;background:rgba(247,148,29,.95);color:#111;font:600 14px sans-serif;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.4)}</style>
<script>(function(){
if(window.pwaStandalone)return;
var b=document.createElement('button');b.id='pwaInstall';b.type='button';b.textContent='\\u2193 Install app';
function add(){if(document.body)document.body.appendChild(b);}
if(document.readyState!=='loading')add();else document.addEventListener('DOMContentLoaded',add);
var hideT=null;function show(){b.style.display='block';clearTimeout(hideT);hideT=setTimeout(function(){b.style.display='none';},9000);}
window.addEventListener('beforeinstallprompt',function(){show();});
if(window.pwaIsIOS)show();
b.addEventListener('click',function(){var r=window.pwaInstall();if(r==='ios')alert('To install: tap the Share button in Safari, then "Add to Home Screen".');else b.style.display='none';});
})();</script>
"""

block = (api + (overlay_block if overlay else '') + "<!-- pwa:end -->\n").replace('%THEME%', theme).replace('%NAME%', name)

# ---- service worker: offline-capable, cache-first, versioned per build ----
# The cache name is stamped from the injected head + the .pck size, so any build
# or injector change makes a new worker that clears the old cache on activate
# (so a redeploy updates clients on their next online visit). After one online
# load the game plays offline. Same-origin only -> leaves fonts/other origins alone.
pck = os.path.join(build, 'index.pck')
pck_size = os.path.getsize(pck) if os.path.exists(pck) else 0
stamp = hashlib.md5((block + str(pck_size)).encode('utf-8')).hexdigest()[:10]
sw = """// Auto-injected per-game PWA service worker (tools/pwa_inject.py).
// Offline-capable: caches the game's files on first load, then serves them from
// cache so the installed app opens and plays without a connection.
var CACHE = '%CACHE%';
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;  // don't touch other origins
  e.respondWith(caches.match(req).then(function (hit) {
    if (hit) return hit;
    return fetch(req).then(function (res) {
      if (res && res.status === 200 && res.type === 'basic') {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
      }
      return res;
    }).catch(function () {
      if (req.mode === 'navigate') return caches.match('index.html');
      return undefined;
    });
  }));
});
""".replace('%CACHE%', gid + '-' + stamp)
with open(os.path.join(build, 'sw.js'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(sw)

with open(idx_path, 'r', encoding='utf-8') as f:
    html = f.read()
html = re.sub(r'<!-- pwa:start.*?<!-- pwa:end -->\s*', '', html, flags=re.DOTALL)
html = html.replace('</head>', block + '</head>', 1)
with open(idx_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(html)

print(f"pwa_inject: {gid} -> installable PWA ({name}, {orientation})")
