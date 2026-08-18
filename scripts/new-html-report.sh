#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: new-html-report.sh <name> <output-base-dir> [--charts] [--diagrams]

Creates <output-base-dir>/<name>/ with a self-contained Reader's Seat HTML
scaffold. Bundled fonts are copied automatically. Optional local JavaScript
libraries are copied only when requested.
EOF
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

NAME="$1"
BASE_DIR="$2"
shift 2

WITH_CHARTS=0
WITH_DIAGRAMS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --charts) WITH_CHARTS=1 ;;
    --diagrams) WITH_DIAGRAMS=1 ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "error: name must contain lowercase letters, digits, or hyphens" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$BASE_DIR" && pwd)"
OUT_DIR="$BASE_DIR/$NAME"

if [[ -e "$OUT_DIR" ]]; then
  echo "error: $OUT_DIR already exists" >&2
  exit 1
fi

mkdir -p "$OUT_DIR/assets" "$OUT_DIR/_shared/fonts" "$OUT_DIR/_shared/js" "$OUT_DIR/_shared/licenses"
cp "$SKILL_DIR/assets/html/fonts/WorkSans-Regular.ttf" "$OUT_DIR/_shared/fonts/"
cp "$SKILL_DIR/assets/html/fonts/WorkSans-Bold.ttf" "$OUT_DIR/_shared/fonts/"
cp "$SKILL_DIR/assets/html/fonts/RedHatMono-Regular.ttf" "$OUT_DIR/_shared/fonts/"
cp "$SKILL_DIR/assets/html/fonts/RedHatMono-Bold.ttf" "$OUT_DIR/_shared/fonts/"
cp "$SKILL_DIR/assets/html/THIRD_PARTY_NOTICES.md" "$OUT_DIR/_shared/licenses/"
cp "$SKILL_DIR/assets/html/fonts/WorkSans-OFL.txt" "$OUT_DIR/_shared/licenses/"
cp "$SKILL_DIR/assets/html/fonts/RedHatMono-OFL.txt" "$OUT_DIR/_shared/licenses/"

if [[ "$WITH_CHARTS" -eq 1 ]]; then
  cp "$SKILL_DIR/assets/html/js/echarts.min.js" "$OUT_DIR/_shared/js/"
fi
if [[ "$WITH_DIAGRAMS" -eq 1 ]]; then
  cp "$SKILL_DIR/assets/html/js/mermaid.min.js" "$OUT_DIR/_shared/js/"
fi

cp "$SKILL_DIR/assets/html/report-template.html" "$OUT_DIR/$NAME.html"

echo "Created: $OUT_DIR/$NAME.html"
echo "Created: $OUT_DIR/assets/"
echo "Copied: bundled Reader's Seat fonts"
echo "Copied: third-party notices"
if [[ "$WITH_CHARTS" -eq 1 ]]; then
  echo "Copied: ECharts"
fi
if [[ "$WITH_DIAGRAMS" -eq 1 ]]; then
  echo "Copied: Mermaid"
fi
