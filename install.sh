#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"

echo "==> Checking Python >=3.8..."
python3 -c "import sys
if sys.version_info < (3,8):
    raise SystemExit('Python >= 3.8 required')"

if [ -d "$VENV_DIR" ]; then
  echo "Virtualenv già presente in $VENV_DIR — attivando e aggiornando pip..."
else
  echo "==> Creazione virtualenv in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

# Attiva venv (POSIX)
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Aggiorna pip/ruoli base
python -m pip install --upgrade pip setuptools wheel

# Installa dipendenze
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "Attenzione: requirements.txt non trovato. Installo pwntools globalmente nel venv..."
  pip install pwntools
fi

echo "==> Installazione completata. Per attivare: source $VENV_DIR/bin/activate"

