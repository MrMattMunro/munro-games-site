# munro-games-site

Static GitHub Pages site for **[munro.games](https://munro.games)** — a living showcase of
Matt Munro's Godot game prototypes, playable in-browser (Godot HTML5 exports).

## How it's built

Plain static site, mirroring `rivethold-website`. No build step. `index.html` is self-contained
(inline CSS, Google Fonts) and renders its card grid from a `GAMES` array in an inline `<script>`.

## Adding a game

Full checklist: **`ADDING_A_GAME.md`**. In short:

1. Export a **thread-off** Godot Web build locally into `play/<id>/` (gitignored scratch).
2. **Deploy the build to S3:** `tools/deploy-game.sh <id> "M:/Git/munro-games-site/play/<id>"` — it is served at `https://play.munro.games/<id>/index.html` (NOT from this repo).
3. Drop a 16:10 thumbnail at `assets/<id>.png`.
4. Add one entry to the `GAMES` array in `index.html`, with `play:'https://play.munro.games/<id>/index.html'`.
5. Commit + push the card + thumbnail only — GitHub Pages redeploys automatically. **The build is not committed.**

Prototypes and already-released titles (e.g. Floodline) ship as full playable demos. The plan's
"trimmed vertical-slice for unreleased commercial titles" rule was set aside for Apprentice Arena
(Matt, 2026-10-09 — it's free/beta, nothing to undercut).

## Hosting

Two tiers (split 2026-10-09 — Godot builds exceed GitHub's 100 MB/file limit):

- **This site** (`munro.games`): GitHub Pages, deploy from `main` / root, `CNAME` → `munro.games`. Holds only `index.html` + `assets/` + `icons/`. `play/` is gitignored.
- **Game builds** (`play.munro.games`): private S3 bucket `munro-games-play` (us-east-1) behind CloudFront `E6DDPBBVEY1XE`. Deploy via `tools/deploy-game.sh`.
- DNS in Route 53 (AWS profile `munro-personal`, acct `554605724969`), zone `Z0668111H5Y70SCGTI3T`.
- Email on Fastmail (`matt@munro.games`).

Plan of record: `claude-assistant/plans/munro-games/2026-10-07-prototype-showcase-page.md`.
