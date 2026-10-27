#!/usr/bin/env bash
# Fetch fresh GitHub stats and re-render every SVG except the portrait.
set -euo pipefail
cd "$(dirname "$0")"

python3 fetch_stats.py
python3 render_stats.py
python3 render_projects.py
python3 render_links.py
python3 render_farm.py
