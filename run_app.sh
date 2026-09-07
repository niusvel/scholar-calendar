#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creando el entorno virtual..."
    python3 -m venv .venv
fi

if [ ! -x ".venv/bin/scholar-calendar" ] ||
    ! .venv/bin/python -c 'import scholar_calendar; import reportlab' >/dev/null 2>&1; then
    echo "Instalando dependencias..."
    .venv/bin/python -m pip install -e .
fi

exec .venv/bin/scholar-calendar
