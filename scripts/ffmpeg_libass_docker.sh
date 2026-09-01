#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
workspace_root=$(dirname -- "$script_dir")
cjk_font_source=${NARRATOPRO_CJK_FONT_PATH:-/System/Library/Fonts/STHeiti Medium.ttc}
cjk_font_dir=/private/tmp/narratopro-fonts
media_root=${NARRATOPRO_MEDIA_ROOT:-}

if [ ! -r "$cjk_font_source" ]; then
  echo "CJK subtitle font unavailable: $cjk_font_source" >&2
  exit 78
fi

mkdir -p "$cjk_font_dir"
cp "$cjk_font_source" "$cjk_font_dir/STHeiti-Medium.ttc"

if [ -n "$media_root" ]; then
  if [ ! -d "$media_root" ]; then
    echo "Media root unavailable: $media_root" >&2
    exit 78
  fi
  exec docker run --rm \
    --entrypoint ffmpeg \
    --volume "$workspace_root:$workspace_root" \
    --volume "$media_root:$media_root:ro" \
    --volume "$cjk_font_dir:/usr/share/fonts/truetype/narratopro:ro" \
    --workdir "$workspace_root" \
    narratoai:latest "$@"
fi

exec docker run --rm \
  --entrypoint ffmpeg \
  --volume "$workspace_root:$workspace_root" \
  --volume "$cjk_font_dir:/usr/share/fonts/truetype/narratopro:ro" \
  --workdir "$workspace_root" \
  narratoai:latest "$@"
