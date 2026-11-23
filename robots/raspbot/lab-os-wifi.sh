#!/bin/sh
# lab-os on the Raspbot: at start, join the router's Wi-Fi if it is there, else start the
# Raspbot's own hotspot (so it can still be reached). Run once at start by lab-os-wifi.service.
# The hotspot's profile has autoconnect off (install-wifi.sh), so NetworkManager does not start
# it first: a Wi-Fi in hotspot mode does not look for other networks.
ROUTER="${ROUTER:-GL-B7-5G}"   # the profile's name, and its Wi-Fi name
HOTSPOT="${HOTSPOT:-Raspbot}"  # the hotspot's profile
WAIT_S="${WAIT_S:-60}"         # look for the router this long
STEP_S="${STEP_S:-5}"

active() { nmcli -t -f NAME connection show --active | grep -qxF "$1"; }

waited=0
while [ "$waited" -lt "$WAIT_S" ]; do
    if active "$ROUTER"; then
        echo "on $ROUTER"
        exit 0
    fi
    if nmcli -t -f SSID device wifi list --rescan yes 2>/dev/null | grep -qxF "$ROUTER"; then
        if nmcli connection up "$ROUTER"; then
            echo "joined $ROUTER"
            exit 0
        fi
    fi
    sleep "$STEP_S"
    waited=$((waited + STEP_S))
done
echo "$ROUTER not found in $WAIT_S s: starting the hotspot $HOTSPOT"
nmcli connection up "$HOTSPOT"
