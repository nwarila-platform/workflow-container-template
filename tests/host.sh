#!/usr/bin/env bash
# The container's host tests. ci.yaml runs this file; the container decides what it checks.
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -B -m unittest discover -s tests -v
