#!/usr/bin/env bash
# Sets up the Movement Project backend (Python venv) and frontend (Node/npm).
# Run this from Terminal on your Mac: bash setup.sh
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$PROJECT_ROOT/backend"
FRONTEND="$PROJECT_ROOT/frontend"

echo "== Backend: Python venv =="
# scikit-learn 1.4.2 / numpy 1.26.4 / pandas 2.2.2 (pinned in requirements.txt)
# have no prebuilt wheels for Python 3.13, which is why pip tried to build
# scikit-learn from source and failed. Use Python 3.11 or 3.12 instead.
PY=""
for cand in python3.12 python3.11; do
  if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done

if [ -z "$PY" ]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
  echo "Installing python@3.12 via Homebrew..."
  brew install python@3.12
  PY="$(brew --prefix python@3.12)/bin/python3.12"
fi

echo "Using $PY ($($PY --version))"

rm -rf "$BACKEND/venv"
"$PY" -m venv "$BACKEND/venv"
source "$BACKEND/venv/bin/activate"
pip install --upgrade pip
pip install -r "$BACKEND/requirements.txt"
deactivate
echo "Backend venv ready at $BACKEND/venv"

echo ""
echo "== Frontend: Node & npm =="
if ! command -v node >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
  echo "Installing node via Homebrew..."
  brew install node
fi
echo "Node $(node -v), npm $(npm -v)"

cd "$FRONTEND"
npm install

echo ""
echo "All set. To run the project:"
echo "  Backend:  cd \"$BACKEND\" && source venv/bin/activate && uvicorn main:app --reload"
echo "  Frontend (new tab): cd \"$FRONTEND\" && npm run dev"
