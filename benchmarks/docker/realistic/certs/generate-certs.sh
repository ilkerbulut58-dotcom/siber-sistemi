#!/usr/bin/env sh
# Regenerate committed benchmark TLS certificates (requires Python cryptography).
set -eu
cd "$(dirname "$0")"
python3 generate-certs.py
