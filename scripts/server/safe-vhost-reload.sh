#!/usr/bin/env bash
# Safe domain-scoped vhost reload — never restarts global stack unless nginx -t fails.
# Usage: safe-vhost-reload.sh <domain>
# Installed at /opt/siber/scripts/server/safe-vhost-reload.sh

set -euo pipefail

DOMAIN="${1:?domain required}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

reconfigure_domain_safe "$DOMAIN"

code=$(http_code "https://${SERVER_IP}/" "$DOMAIN")
log "Post-reload ${DOMAIN} -> ${code}"

if [ "$code" = "000" ] || [ "$code" = "502" ]; then
  log "WARN: ${DOMAIN} still bad after reload"
  exit 1
fi

exit 0
