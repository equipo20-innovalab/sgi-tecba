#!/usr/bin/env bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")"
exec .venv-py311/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
