#!/bin/sh
# Run once on the Raspbot with sudo: sudo sh ~/lab-os/install-wifi.sh (docs/guides/raspbot.md).
# Installs lab-os-wifi.service and turns off the hotspot's own autoconnect. Undo:
#   sudo systemctl disable lab-os-wifi; sudo nmcli connection modify Raspbot connection.autoconnect yes
set -e
here="$(dirname "$0")"
install -D -m 644 "$here/lab-os-wifi.sh" /usr/local/lib/lab-os/lab-os-wifi.sh
install -m 644 "$here/lab-os-wifi.service" /etc/systemd/system/lab-os-wifi.service
nmcli connection modify GL-B7-5G connection.autoconnect yes connection.autoconnect-priority 10
nmcli connection modify Raspbot connection.autoconnect no
systemctl daemon-reload
systemctl enable lab-os-wifi.service
echo "Done. At the next start, raspbot1 joins GL-B7-5G, else it starts the Raspbot hotspot."
