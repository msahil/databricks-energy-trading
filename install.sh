#!/usr/bin/env bash
# Deploy the root Databricks Asset Bundle: demo-data Lakeflow job + Energy Trading Dash app.
# - Job runs notebooks 01→04 under modules/forecasting/notebooks/ (Unity Catalog Delta → energy_utilities.energy_trading2).
# - App resource syncs app/ (app.yaml, requirements.txt) for Databricks Apps deployment.
# Run from repository root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [databricks bundle deploy options]

Regenerates notebooks from templates, validates the bundle, and deploys to the workspace.

  databricks bundle deploy --auto-approve
  ./install.sh -t prod

After deploy:

  1) Seed demo Delta tables (job — run once or on schedule):

       databricks bundle run energy_trading_demo_data

  2) Publish / update the Databricks App (Dash UI):

       databricks bundle run energy_trading_app

     Open the app from Workspace → Apps, or follow the URL shown after the run.

Override cluster shape for the job (example):

  databricks bundle deploy --var="node_type_id=Standard_D4ds_v5"

Bundle resources (see resources/*.yml, databricks.yml):

  energy_trading_demo_data  — Lakeflow job (notebooks 01→04)
  energy_trading_app      — Databricks App asset (source app/)

See modules/forecasting/README.md and app/app.yaml.
EOF
  exit 1
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

echo "==> Regenerating notebooks from templates"
python3 modules/forecasting/notebooks/build_notebooks.py

echo "==> Validate & deploy bundle (repository root)"
databricks bundle validate "$@"
databricks bundle deploy "$@"

echo ""
echo "Deployed bundle resources:"
echo "  • energy_trading_demo_data — job (seed UC tables: databricks bundle run energy_trading_demo_data)"
echo "  • energy_trading_app       — Databricks App (Dash: databricks bundle run energy_trading_app)"
echo ""
echo "Typical order: run the job to materialise demo_* tables, then run the app and pick a SQL warehouse in the UI header."
