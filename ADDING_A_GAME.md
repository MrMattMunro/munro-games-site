# Adding a game to munro.games

A checklist for putting one more Godot game on the showcase. Floodline (commit history +
`claude-assistant/plans/munro-games/2026-10-07-prototype-showcase-page.md`) is the worked example.

> ⚠️ **BUILDS LIVE IN S3 NOW, NOT IN THIS REPO (changed 2026-10-09).** GitHub rejects files over
> 100MB and the builds were blowing past it. Web builds are hosted in **S3** (`s3://munro-games-play/<id>/`,
> private, us-east-1) and served over **CloudFront** at **`https://play.munro.games/<id>/index.html`**
> (ACM cert, Route 53 alias, all on AWS account `554605724969` via `aws --profile munro-personal`;
> CloudFront distribution `E6DDPBBVEY1XE`). This repo keeps ONLY the lightweight showcase (index.html +
> thumbnails). `play/` is gitignored. **Deploy a build with `tools/deploy-game.sh <id> <build-dir>`**
> (syncs to S3, fixes the wasm content-type, invalidates the CloudFront cache). So the old "export into
> the site repo + git-commit the build + push" steps below (4, 7) are superseded: export locally, run
> deploy-game.sh, and the only thing you commit here is the card in index.html + the thumbnail. The
> card's `play:` is the full `https://play.munro.games/<id>/index.html` URL.

**Locations**
- Site repo: `M:\Git\munro-games-site` (SSH remote `MrMattMunro/munro-games-site`, GitHub Pages). **NOT** `C:\godot`. Holds the showcase only; builds are in S3 (see banner above).
- Game repos: `C:\godot\<name>` (own remote, often with CI — see step 7).
- Godot editors: `C:\godot\Godot_v4.6.1 / 4.6.3 / 4.7.1 / 4.7.2_...console.exe`. **Match the game's `project.godot` version** (web templates are version-specific).

---

## 1. Can it run on the web?
- Open `C:\godot\<name>\project.godot`. `rendering/renderer/rendering_method` **must be `gl_compatibility`** (Forward+/Mobile can't run on the web). If not, switch it and sanity-check the main scene still renders.
- **Web export templates** must be installed for that exact Godot version. Installed now: **4.6.1** and **4.7.2**. If missing for the version you need: download `Godot_v<ver>-stable_export_templates.tpz` from the GitHub release, and extract just the `web_*.zip` members into `%APPDATA%\Godot\export_templates\<ver>.stable\` (the `.tpz` is a zip; ~1.3 GB, delete after — see Floodline session).

## 2. Add a Web export preset (it's gitignored per game, so recreate it)
`export_presets.cfg` is gitignored in each game repo (holds signing ids), so the preset lives locally only. Add a **Web** preset with:
- **Thread Support = OFF** (`variant/thread_support=false`) — GitHub Pages can't set the COOP/COEP headers threads need.
- `html/canvas_resize_policy=2` (adaptive — canvas fills the window, reliably, across browsers/DPR).
- `html/head_include=...` — charcoal letterbox bg **plus a feature-detected fullscreen button** (bottom-right; hides itself on iOS Safari where element-fullscreen is blocked). The exact value is long and lives only in the gitignored preset, so **copy the `<style>…</style><script>…fsbtn…</script>` block verbatim from the `<head>` of an existing `play/<id>/index.html`** (e.g. Floodline). ⚠️ The cfg wraps `head_include` in double-quotes, so the value must contain **no `"` and no `\`** (the button script uses single quotes and a literal `⛶` glyph).

## 3. Landscape / fixed-aspect games: letterbox via the engine (not CSS)
If the game is a fixed 16:9 (or other) design and would otherwise show background gaps or squash in odd windows, add **web-only** letterboxing in the first scene that loads (Floodline: `splash.gd._ready()`):
```gdscript
if OS.has_feature("web"):
    get_window().content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
```
Guard it to web so the mobile/desktop build is untouched. ⚠️ Don't try to force the size with CSS in `head_include` — it fights the engine and shrinks a few seconds after load on some browsers/DPRs (that bug cost a lot of time).

## 4. Export locally, then deploy to S3 (builds do NOT go in git — see banner)
```
mkdir -p M:/Git/munro-games-site/play/<id>          # play/ is gitignored = local scratch
"C:/godot/Godot_v<ver>-stable_win64_console.exe" --headless --path "C:/godot/<name>" \
  --export-release "Web" "M:/Git/munro-games-site/play/<id>/index.html"
```
Test it locally first: `python -m http.server 8778 --directory M:/Git/munro-games-site`, open `http://localhost:8778/play/<id>/index.html`. **Verify in a FRESH browser (not a cached Chrome tab)** — stale cache made it look broken during the Floodline session.

Then deploy the build to S3 + CloudFront:
```
tools/deploy-game.sh <id> "M:/Git/munro-games-site/play/<id>" "<Display Name>" <orientation> "#0d0d0d" <overlay>
```
`<orientation>` = `landscape` | `portrait` | `any`. `<overlay>` = `off` when the game has its own in-menu Install button (§8), otherwise omit it (default `on` = a small auto-hiding floating Install button). This `aws s3 sync --delete`s the folder to `s3://munro-games-play/<id>/`, re-sets `index.wasm` to `application/wasm`, sets the `manifest.webmanifest` + `sw.js` content-types, invalidates CloudFront `/<id>/*`, and runs `tools/pwa_inject.py` — which makes the build an **installable, offline-capable PWA** (per-game manifest + versioned service worker + icons from the build's `index.icon.png`, plus a visibility-based audio pause). After one online load the installed game plays offline; a redeploy's new build stamp updates clients on their next online visit. It serves at `https://play.munro.games/<id>/index.html`. ⚠️ A bare `https://play.munro.games/<id>` (no `/index.html`) returns S3 `AccessDenied` — always link the full path. On iPad Safari, fully close + reopen the tab if you still see an old build after an invalidation.

## 5. Font check (pixel fonts often miss glyphs)
Grep the game's display strings for `·  ★  ◀  ▶  …  •` etc. Many pixel fonts lack them and render as boxes. Confirm with fontTools (`TTFont(font).getBestCmap()`) and swap for glyphs the font has (`/`, `>> <<`, `< >`, `:`). Fix in the game source (helps all platforms).

## 6. Card thumbnail + entry
- **Thumbnail** `assets/<id>.png`, 16:10 (960×600): composite the game's own title background + logo, **not** a menu screenshot. Floodline recipe: cover-crop `title_bg.png` + 35% dark scrim, alpha-composite the no-glow logo (solid letters), then full **additive** blend of the glow-only logo (neon halo). PIL `ImageChops.add`, premultiply the glow layer by its alpha.
- **Card**: add one entry to the `GAMES` array in `index.html`:
  ```js
  { id:'<id>', title:'...', genre:'...', blurb:'...', eng:'<engineering angle>',
    play:'https://play.munro.games/<id>/index.html',
    controls:['1-3 players', 'Touch', 'Controller'],
    store:{label:'Wishlist on Steam', url:'...'},  // optional
    ribbon:'Demo', group:'uncle-matt' }            // both optional
  ```
  ⛔ **No em-dashes** in card copy (Matt's house style — use commas/colons). `controls` is an array of short, **uniform** capability chips (players + input methods) shown on the card — keep them concise and standard (`1-3 players`, `Single player`, `Touch`, `Controller`, `Keyboard`, `Mouse`); the touch-vs-controller-per-mode nuance goes in the blurb, Steam-style. *(Replaced the old `platform:'ipad'|'desktop'` single tag, 2026-10-13.)*
- **Commercial & UNRELEASED titles** (Sword & Signet, Apprentice Arena): ship a **trimmed one-level slice + a store/wishlist link**, not the full game, so a free web build can't undercut the paid launch. Already-released (Floodline) and prototypes = full playable demo.

## 7. Commit
- **Site repo**: commit + push (`git -C M:/Git/munro-games-site ... ; git push`). One commit. ⚠️ **The build is NOT committed** — it went to S3 in step 4. The only new files here are the card entry in `index.html` and `assets/<id>.png`.
- **Game repo**: commit the game-side changes (renderer switch, font fixes, web-letterbox line) **in that game's own repo**. ⚠️ **Do NOT push if the repo has `codemagic.yaml`/CI** — a push can trigger a mobile build of the live game. Leave it for Matt to push.

## 8. Install-as-an-app button (in-menu, recommended)
`pwa_inject.py` exposes a tiny browser API on every game page that the game can call via `JavaScriptBridge`:
- `window.pwaCanInstall` (bool) — a native install prompt is ready
- `window.pwaIsIOS` / `window.pwaStandalone` (bool) — iOS Safari (manual Share → Add to Home Screen) / already installed
- `window.pwaInstall()` → `'prompt'` | `'ios'` | `'none'`

Add an **"INSTALL APP" button to the game's own main menu** (so nothing floats over gameplay), then deploy with `<overlay>` = `off`. Pattern (styled with the game's own button helper; Floodline uses a scene Button, the others build buttons in code):
```gdscript
func _setup_install() -> void:
    if not OS.has_feature("web"):
        return
    _install = <make a button the game's usual way>   # visible = false
    _install.pressed.connect(_do_install)
    <add it to the menu>
    var t := Timer.new(); t.wait_time = 1.0; t.timeout.connect(_refresh_install)
    add_child(t); t.start(); _refresh_install()        # the prompt can arrive after load

func _refresh_install() -> void:
    _install.visible = bool(JavaScriptBridge.eval(
        "(window.pwaStandalone!==true)&&((window.pwaCanInstall===true)||(window.pwaIsIOS===true))", true))

func _do_install() -> void:
    JavaScriptBridge.eval(
        "(function(){var r=window.pwaInstall&&window.pwaInstall();if(r==='ios'){alert('To install: tap the Share button in Safari, then Add to Home Screen.');}return r;})()", true)
```
⚠️ On a "press anything to start" title (Chop Hopper), give the button `focus_mode = FOCUS_NONE` so it doesn't hijack the start input; its default STOP mouse filter already stops a tap on it from also starting the game. If the game has NO menu (idle games like Drone Digger), host it on the Settings/Options panel. These are game-repo edits — compile-check, re-export, re-deploy; ⛔ don't push a game repo with CI.

## Gotchas worth remembering
- **`SendUserFile` is invisible in Matt's VSCode extension** — give file paths or a `localhost` URL instead.
- **Verify in a fresh browser** — cache lies.
- One `git` command per Bash call here (no `&&`); edit CRLF/data files in binary mode to preserve line endings.
- HTTPS on the Pages custom domain auto-provisions (can take >1 h on first setup); enable "Enforce HTTPS" once the cert exists.
