#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"

if [ -d "$VENV_DIR" ]; then
  echo "Rimuovo $VENV_DIR..."
  rm -rf "$VENV_DIR"
  echo "OK"
else
  echo "Nessun virtualenv trovato in $VENV_DIR"
fi

