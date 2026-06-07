#!/usr/bin/env bash
# Deploy the root Databricks Asset Bundle: demo-data workflow job + Energy Trading Dash app.
# Run from repository root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [databricks bundle deploy options]

Validates the bundle and deploys to the workspace.

  databricks bundle deploy --auto-approve
  ./install.sh -t prod

After deploy:

  1) Seed demo Delta tables (workflow job — drops schema and reloads fresh each run):

       databricks bundle run energy_trading_demo_data

  2) Publish / update the Databricks App (Dash UI):

       databricks bundle run energy_trading_app

Open the app from Workspace → Apps, or follow the URL shown after the run.

The demo-data job uses serverless compute (no cluster variables).

See resources/*.yml and databricks.yml.
EOF
  exit 1
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

echo "==> Validate & deploy bundle (repository root)"
databricks bundle validate "$@"
databricks bundle deploy "$@"

echo ""
echo "Deployed bundle resources:"
echo "  • energy_trading_demo_data — workflow job (seed UC: databricks bundle run energy_trading_demo_data)"
echo "  • energy_trading_app       — Databricks App (Dash: databricks bundle run energy_trading_app)"
echo ""
echo "Typical order: run the job to materialise demo tables, then run the app."
echo ""
