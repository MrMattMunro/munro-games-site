# munro-games-site

Static GitHub Pages site for **[munro.games](https://munro.games)** — a living showcase of
Matt Munro's Godot game prototypes, playable in-browser (Godot HTML5 exports).

## How it's built

Plain static site, mirroring `rivethold-website`. No build step. `index.html` is self-contained
(inline CSS, Google Fonts) and renders its card grid from a `GAMES` array in an inline `<script>`.

## Adding a game

1. Export a **thread-off** Godot Web build into `play/<id>/`.
2. Drop a 16:10 screenshot at `assets/<id>.png`.
3. Add one entry to the `GAMES` array in `index.html` (see the comment block there).
4. Commit and push — GitHub Pages redeploys automatically.

Unreleased commercial titles ship as a **trimmed vertical-slice** build plus a `store` link, not the
full game. Already-released titles (e.g. Floodline) and prototypes can ship as full playable demos.

## Hosting

- GitHub Pages, deploy from `main` / root. `CNAME` → `munro.games`.
- DNS in Route 53 (AWS profile `munro-personal`), zone `Z0668111H5Y70SCGTI3T`.
- Email on Fastmail (`matt@munro.games`).

Plan of record: `claude-assistant/plans/munro-games/2026-10-07-prototype-showcase-page.md`.
