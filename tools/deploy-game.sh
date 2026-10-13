#!/usr/bin/env bash
# Deploy a Godot web build to S3 + CloudFront (play.munro.games) as an
# installable, standalone PWA.
#
# Usage:  tools/deploy-game.sh <game-id> <local-build-dir> [name] [orientation] [theme-color]
# Example: tools/deploy-game.sh floodline "M:/Git/munro-games-site/play/floodline" "Floodline" landscape
#
# The build dir is a Godot "Web" export output (index.html + index.pck + index.wasm + ...).
# Game builds do NOT live in this git repo; they live in S3 and are served over CloudFront.
# Each game is made its own installable PWA (manifest + service worker + icons + Install
# button) by tools/pwa_inject.py, run here so every deploy keeps it even after a re-export.
set -euo pipefail

ID="${1:?game id required (folder name, e.g. floodline)}"
SRC="${2:?local build dir required (the Godot web export output)}"
NAME="${3:-}"
ORIENT="${4:-any}"
THEME="${5:-#0d0d0d}"
OVERLAY="${6:-on}"   # "off" when the game has its own in-menu Install button

PROFILE="munro-personal"
BUCKET="munro-games-play"
DIST_ID="E6DDPBBVEY1XE"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ -f "$SRC/index.html" ] || { echo "No index.html in $SRC — is that a Godot web export?" >&2; exit 1; }

# Make the build an installable standalone PWA (idempotent; re-applied each deploy).
python "$HERE/pwa_inject.py" "$SRC" "$ID" "$NAME" "$ORIENT" "$THEME" "$OVERLAY"

echo "Uploading $ID to s3://$BUCKET/$ID/ ..."
aws s3 sync "$SRC" "s3://$BUCKET/$ID/" --profile "$PROFILE" --delete --no-progress

# Godot streaming-compiles the wasm; it must be served as application/wasm (the CLI guesses wrong).
aws s3 cp "$SRC/index.wasm" "s3://$BUCKET/$ID/index.wasm" \
  --content-type application/wasm --profile "$PROFILE" --no-progress >/dev/null

# The manifest + service worker must have the right content-types or the PWA won't install.
aws s3 cp "$SRC/manifest.webmanifest" "s3://$BUCKET/$ID/manifest.webmanifest" \
  --content-type application/manifest+json --profile "$PROFILE" --no-progress >/dev/null
aws s3 cp "$SRC/sw.js" "s3://$BUCKET/$ID/sw.js" \
  --content-type text/javascript --cache-control no-cache --profile "$PROFILE" --no-progress >/dev/null

echo "Invalidating CloudFront cache for /$ID/* ..."
aws cloudfront create-invalidation --distribution-id "$DIST_ID" \
  --paths "/$ID/*" --profile "$PROFILE" --query "Invalidation.Status" --output text

echo "Done -> https://play.munro.games/$ID/index.html"
