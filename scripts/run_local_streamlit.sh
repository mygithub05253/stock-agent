#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8501}"
HOST="${HOST:-127.0.0.1}"

if [[ ! -x ".venv/bin/streamlit" ]]; then
  echo "Streamlit executable not found at .venv/bin/streamlit"
  echo "Run these commands first:"
  echo "  python -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements-dev.txt"
  exit 1
fi

export GLM_BASE_URL="${GLM_BASE_URL:-https://api.z.ai/api/paas/v4}"
export GLM_MODEL="${GLM_MODEL:-glm-4.5-flash}"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS="${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}"

echo "Starting Streamlit at http://${HOST}:${PORT}"
if [[ -n "${GLM_API_KEY:-}" ]]; then
  echo "GLM enabled with model ${GLM_MODEL}"
else
  echo "GLM_API_KEY is not set. InvestmentAnalyst Agent will use fallback behavior."
fi

exec .venv/bin/streamlit run streamlit_app.py \
  --server.port "$PORT" \
  --server.address "$HOST"
