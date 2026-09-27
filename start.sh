#!/usr/bin/env bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
	if [[ -n "${FRONTEND_PID:-}" ]]; then
		kill "${FRONTEND_PID}" 2>/dev/null || true
	fi
}

trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

PYTHON_CMD=""
for candidate in python3 python python.exe; do
	if command -v "${candidate}" >/dev/null 2>&1 && "${candidate}" -m pip --version >/dev/null 2>&1; then
		PYTHON_CMD="${candidate}"
		break
	fi
done

if [[ -z "${PYTHON_CMD}" ]]; then
	echo "Python 3 is required but was not found."
	exit 1
fi

echo "Installing ASTRAEA backend dependencies"
${PYTHON_CMD} -m pip install fastapi uvicorn pydantic pydantic-settings pycryptodome reedsolo opencv-python pytest

echo "Installing ASTRAEA frontend dependencies"
(
	cd "${ROOT_DIR}/astraea-frontend"
	npm ci
)

echo "Starting ASTRAEA frontend on http://localhost:5173"
(
	cd "${ROOT_DIR}/astraea-frontend"
	npm run dev
) &
FRONTEND_PID=$!

echo "Starting ASTRAEA backend on http://localhost:8000"
${PYTHON_CMD} -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
