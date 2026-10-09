#!/usr/bin/env bash
# Deploy a Godot web build to S3 + CloudFront (play.munro.games).
#
# Usage:  tools/deploy-game.sh <game-id> <local-build-dir>
# Example: tools/deploy-game.sh apprentice-arena "M:/Git/munro-games-site/play/apprentice-arena"
#
# The build dir is a Godot "Web" export output (index.html + index.pck + index.wasm + ...).
# Game builds do NOT live in this git repo; they live in S3 and are served over CloudFront.
set -euo pipefail

ID="${1:?game id required (folder name, e.g. apprentice-arena)}"
SRC="${2:?local build dir required (the Godot web export output)}"

PROFILE="munro-personal"
BUCKET="munro-games-play"
DIST_ID="E6DDPBBVEY1XE"

[ -f "$SRC/index.html" ] || { echo "No index.html in $SRC — is that a Godot web export?" >&2; exit 1; }

echo "Uploading $ID to s3://$BUCKET/$ID/ ..."
aws s3 sync "$SRC" "s3://$BUCKET/$ID/" --profile "$PROFILE" --delete --no-progress

# Godot streaming-compiles the wasm; it must be served as application/wasm (the CLI guesses wrong).
aws s3 cp "$SRC/index.wasm" "s3://$BUCKET/$ID/index.wasm" \
  --content-type application/wasm --profile "$PROFILE" --no-progress >/dev/null

echo "Invalidating CloudFront cache for /$ID/* ..."
aws cloudfront create-invalidation --distribution-id "$DIST_ID" \
  --paths "/$ID/*" --profile "$PROFILE" --query "Invalidation.Status" --output text

echo "Done -> https://play.munro.games/$ID/index.html"
