#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo."; exit 1; fi
systemctl disable --now sanket-relay.service 2>/dev/null || true
rm -f /etc/systemd/system/sanket-relay.service
systemctl daemon-reload
rm -rf /opt/sanket-relay
# Keep /etc/sanket-relay and /var/lib/sanket-relay so configuration/data are not silently destroyed.
echo "Sanket Relay service and program files removed. Config/data retained in /etc/sanket-relay and /var/lib/sanket-relay."
