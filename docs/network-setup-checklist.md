# Network Setup Checklist — getting every device onto the network

> **Note (2026-10-23):** the plan changed. Instead of registering every device with campus IT, the lab will use **its own travel router** (plugged into the lab's wall Ethernet port, with the professor's OK) — see the "Network plan" in lab-jarvis-log.md. With the router, devices join the router's Wi-Fi with a password, so **Steps 1–3 and 5 below only apply if you end up registering devices individually.** **Steps 0, 2 (finding Wi-Fi hardware), 4 and 6 still apply.** The teleop fast track needs none of this (it uses USB).

Goal: every robot/device joins the network, has a unique name, and can be reached from the Linux "brain" desktop with `ssh <name>` — so Claude Code can do the rest.

---

## Step 0 — 2-minute test: can devices on the network talk to each other?
Some managed Wi-Fi networks use **"client isolation"**: devices can reach the internet but *not each other*.

On one Linux desktop:
```
ip addr        # note this machine's address (looks like 10.x.x.x or 192.168.x.x)
```
On the other Linux desktop:
```
ping -c 4 <first desktop's address>
```
- Replies → good, devices can talk to each other.
- "Destination unreachable" / timeouts → probably client isolation. (With the lab's own router this doesn't apply — you control that network.)

---

## Networks before the router (2026-11-09)
lab-os needs the screens to reach the brain (the hub on the Newline, modules on other screens). **New devices can't join the lab Wi-Fi without campus IT, and that's slow** (the Raspbots have waited two weeks), so nothing here adds a device to it. Options, best first:
1. **Test the lab Wi-Fi with what's already on it.** The desktops and the Pis are on it. Do the Step 0 test above between the desktop and a Pi. Replies → no client isolation: Pi screens can open the brain's address directly, and option 2 works. No replies → skip to 3. **Replied (2026-11-10)** between `pi01` and the lab desktop, both ways.
2. **The Newline through a Pi** (your idea): Newline → Ethernet cable → a Pi that's already on the lab Wi-Fi. Set the Pi's wired connection to "Shared to other computers"; it gives the Newline an address and passes on internet and the way to the brain. Only works if test 1 replied. (If the Newline is already on a university network itself, try opening the brain's address from it first.)
   **Works (2026-11-10)** with `pi01` (`pi01.iwu.ai.lab`, user `ai-comp-lab-rp-01`, Debian 13 / NetworkManager; the lab desktop's SSH key is on it). On the Pi, once:
   ```bash
   sudo nmcli con add type ethernet ifname eth0 con-name newline-share ipv4.method shared ipv6.method disabled connection.autoconnect-priority 10
   sudo nmcli con up newline-share        # comes back by itself after a reboot; undo: sudo nmcli con delete newline-share
   ```
   The cable goes into the Newline's **LAN in** port; the Newline has no Ethernet settings of its own, it just takes an address (`10.42.0.x`; it was `10.42.0.103`). After the sharing is switched on, re-plug the cable once so the Newline asks again. Then the Newline's Chrome opens `http://192.168.7.72:8080/design` (the desktop's Wi-Fi address; `hostname -I` there if it changed; the name didn't work from the Pi). Test 1 replied the same day between `pi01` and the lab desktop (`ai-comp-lab-ubuntu-76358`, 192.168.7.72) in both directions: no client isolation between them.
3. **A cable from the brain's computer to the Newline.**
   - *HDMI + the Newline's USB touch cable:* the Newline becomes that computer's screen; the hub runs at `http://localhost` (a secure page, so voice works). No network at all. Only if the Newline is close to that computer.
   - *An Ethernet cable straight between them:* set the brain's wired connection to "Shared to other computers" (Ubuntu: Settings → Network → the wired connection → IPv4); the Newline opens the brain's Ethernet address. Needs a free Ethernet port on the brain (the desktops use Wi-Fi) and a long enough cable.
   - *Long HDMI:* passive HDMI cables get unreliable past ~10 m (4K: ~5 m); an active/optical HDMI cable (~15–30 m) and a USB extension for touch reach further. USB-C (video + touch in one cable) if both ends have it with video support. With HDMI the Newline is simply another monitor of the brain's computer: pages go there with "Show on another screen" (`docs/hub.md` → "Other monitors").
   - *The brain's own Wi-Fi hotspot* (added 2026-11-10): only if the desktop is on the network by its Ethernet port, so its Wi-Fi card is free: Ubuntu Settings → Wi-Fi → ⋮ → "Turn On Wi-Fi Hotspot"; the Newline joins it and opens the brain's hotspot address (usually `http://10.42.0.1:8080`). No cable to the Newline, no extra hardware. **Ask IT first**: campus networks often forbid running your own access point (the same question as the router).
4. **A phone hotspot as a stand-in router.** Every device joins the phone's Wi-Fi; phones normally let their clients reach each other. Limits: ~5–10 devices, the phone stays there and charged, addresses change, the internet uses the phone's data (chat is light).
5. **The lab router (GL.iNet Beryl AX)** solves all of it: devices reach each other, fixed addresses, a local DNS entry for `hub.indwesailab.com`, the Quest over Wi-Fi, no IT registration per device. Waiting on the professor's OK.

### The ThinkCentres at the front of the room (2026-11-11)
The ~7 ThinkCentres sit at the front, far from the wall Ethernet ports (at the back, with the rest of the setup). They have no Wi-Fi. There's a network switch next to them but no access point (one was apparently planned; nobody knows what happened to it). Options, cheapest first:
1. **Ask first:** is there a wall port at the front that's just not switched on (IT can activate one), and what happened to the planned access point?
2. **A Pi as the bridge** (the same trick as the Newline through `pi01`, option 2 above): a Pi that's on the lab Wi-Fi, its Ethernet into the switch, set to "Shared to other computers". Every ThinkCentre on the switch gets an address and internet. Free and already proven. Limits: the Pi's Wi-Fi speed is shared by all of them, and other computers can't reach the ThinkCentres directly (they're behind the Pi), only through it.
3. **With the lab router:** a second small router at the front (e.g. a GL.iNet Opal, ~$40) joins the main router's Wi-Fi and feeds the switch by cable ("repeater" or "WDS" mode). Then the ThinkCentres are on the lab network like everything else.
4. **Powerline adapters** (~$50 a pair): Ethernet through the room's power wiring, one plug at the back, one at the front. Usually fine within one room; ask IT, some campuses don't allow them.
5. **A USB Wi-Fi adapter per ThinkCentre** (~$15 each): pick one whose chip Linux supports out of the box (e.g. MediaTek MT7612U / MT7921AU). Each still needs IT registration for the lab Wi-Fi, or the lab router's password.
6. **One long cable, made tidy:** a single cable from the back to the switch is enough (the switch shares it). Flat Ethernet cable along the wall or under the carpet edge, or in a cable cover, looks much less messy than loose cables.

---

## Step 1 — List every device
| Name (unique, lowercase) | Device | Wi-Fi MAC address | How I got into it | Notes |
|---|---|---|---|---|
| raspbot1 | Yahboom Raspbot v2 (Raspberry Pi 5) | 88:a2:9e:5b:01:3f | own hotspot + SSH, or Ethernet cable (Step 2) | Checked with `ip link` 2026-11-10. Ethernet (eth0) MAC `88:a2:9e:5b:01:3e`. Hostname still `yahboom`, user `pi`. Can't join IWU-AI-LAB yet (Step 5). |
| raspbot2 | Yahboom Raspbot v2 | 88:a2:9e:5b:01:c8 | own hotspot + SSH | |
| pi5-1 … | Raspberry Pi 5 (bridges for arms, spares) | | | |
| jetson1 … jetson5 | Jetson Orin Nano | | | |
| quest1 … quest3 | Meta Quest 3 | | | |
| (later) picar1–3 | PiCar Pro (unbuilt) | | | |

Notes:
- The **xArm**, **SO-101** arms and **TonyBot v1** (Arduino) connect over USB/Bluetooth, so they don't join the network themselves — the Pi 5 (or other computer) they plug into does.

---

## Step 2 — Check each device's Wi-Fi hardware (and MAC address)
⚠️ Devices often have two MAC addresses — one for the Ethernet port and one for Wi-Fi.

### Getting into a device
- **Raspbot:** connect to its own hotspot ("Raspbot") and SSH in (IP shown on its little screen).
- **Raspbot by Ethernet cable** (worked for raspbot1, 2026-11-10; no Wi-Fi needed): cable from a desktop's Ethernet port to the Raspbot (it was done on the lab's **other** Ubuntu desktop, not `ai-comp-lab-ubuntu-76358`: that one's "Wired connection 1" is set to share since, so don't plug it into a wall socket). On the desktop, set "Wired connection 1" to share (once; Ubuntu Settings → Network → the wired connection → IPv4 → "Shared to other computers", or `nmcli con modify "Wired connection 1" ipv4.method shared`, then `nmcli con up "Wired connection 1"`). The desktop becomes `10.42.0.1` and gives the Raspbot a `10.42.0.x` address. Find it with `ip neigh` (raspbot1 was `10.42.0.84`), then `ssh pi@10.42.0.x`.
- **Raspberry Pi 5:** monitor + keyboard. ⚠️ The Pi 5 uses **micro-HDMI** — you need a micro-HDMI → HDMI cable or adapter.
- **Jetson Orin Nano:** monitor + keyboard. ⚠️ The dev kit's video port is **DisplayPort**, not HDMI.

### Command (Pi, Jetson, any Linux device)
```
ip link
```
Find the entry whose name starts with **`wl`** (e.g. `wlan0`, or `wlP1p1s0` on a Jetson). The MAC is the `link/ether xx:xx:xx:xx:xx:xx` under it.
- **No entry starting with `wl`?** → no Wi-Fi hardware. It'll need a USB Wi-Fi adapter or an Ethernet cable.

### Quest 3 / phones
⚠️ Turn **off** "private / randomized MAC address" for the network if you're registering them.

---

## Step 3 — (Only if registering individually) Ask campus IT
Via the professor. Questions: can the lab register devices itself? reserved IP addresses? can devices talk to each other? network name and sign-in?

---

## Step 4 — Rename each device & change default passwords
Two Raspbots with the same factory name will confuse everything.
```
sudo hostnamectl set-hostname raspbot1     # use the name from your table
```
Robots often ship with **well-known default passwords**. Change them:
```
passwd
```
Write the new passwords somewhere safe (not in the code repository).

---

## Step 5 — Join the Wi-Fi (lab router or lab network)
On each Pi / Jetson (NetworkManager):
```
sudo nmcli dev wifi connect "<network name>" password "<password>"
```
- Set the **Wi-Fi country** first if needed (`sudo raspi-config` → Localisation → WLAN Country).
- **Raspbots start in hotspot mode** — they may need Yahboom's own steps to switch to joining a normal network.
- **IWU-AI-LAB is an "Enhanced Open" (OWE) network, and the Pi's Wi-Fi chip (brcmfmac) can't do OWE.** Make the saved profile plain open: `sudo nmcli con modify IWU-AI-LAB remove 802-11-wireless-security`. That worked on `pi01`.
- **raspbot1 still can't join IWU-AI-LAB** (2026-11-10), even with the open profile and both MACs registered by IT: every try ends `ASSOC-REJECT status_code=16`. Suspected cause: its old software (kernel 6.6.31, Wi-Fi firmware 7.45.234 from 2021, NetworkManager 1.42.4); `pi01` joins with kernel 6.18, firmware 7.45.265, NetworkManager 1.52. Untested next step: `sudo apt install firmware-brcm80211` on raspbot1 (the offered version may still not have 7.45.265). Details: `GOTCHAS.md` (2026-11-10, raspbot1 Wi-Fi).
- **In plain words (for the professor):** IWU-AI-LAB has no password, but it's encrypted with a newer method ("Enhanced Open"). The Raspbot's Wi-Fi chip doesn't know that method, so it's set to join the network's plain "open" side instead; that works for `pi01`. On raspbot1 even that fails at the very first step, before the network has answered: its own Wi-Fi software gives up (status 16, a time-out). The MAC registration doesn't look like the problem (IT registered both addresses). The likely cause is the old software Yahboom shipped on it (Wi-Fi firmware from 2021): `pi01`, the same kind of computer with newer software, joins fine. Likely, not proven.
- **Would the lab's own router fix it? Very likely, for this problem.** The router's Wi-Fi uses an ordinary password (WPA2), which Pis have handled for years, and needs no IT registration. raspbot1's own hotspot uses the same kind of password and works, and it has saved Yahboom networks of that kind. What the router doesn't fix: the Newline's lag (that's the screen itself), the Raspbot's old software otherwise, and range (about one room). **Test before buying:** have raspbot1 join a phone hotspot set to WPA2 (`lab-checklist.md`, part 6). If it joins, the router will very likely work too.
- Check it worked: `ip addr` should show an address on the `wl…` entry.

---

## Step 6 — From the Linux desktop: SSH keys + nicknames
Once, on the desktop:
```
ssh-keygen -t ed25519          # press Enter through the questions
```
For each device (once):
```
ssh-copy-id <user>@<device address or name.local>
```
Then add a nickname for each device to `~/.ssh/config`:
```
Host raspbot1
    HostName <address or raspbot1.local>
    User pi
```
Test:
```
ssh raspbot1 hostname         # should print "raspbot1" with no password prompt
```
From here on, Claude Code (on the desktop) can reach every device by name.

---

## Step 7 — The brain's secure address (for voice on every screen)
**Deferred (decision 2026-11-10):** voice is built first on `localhost` and with Chrome's flag; this section is for later. Details: `current-focus.md` → "Step 7, concretely".
- **Fixed address for the brain:** a DHCP reservation in the lab router, so `hub.indwesailab.com` keeps pointing to the right computer. (Before the router: the desktop's university address may change; check it before relying on the name.)
- **Local DNS entry in the router:** `hub.indwesailab.com` → the brain's address, so the name works without internet. On the GL.iNet (OpenWrt) this is a custom DNS / hosts entry.
- **DNS rebinding protection:** routers and some networks block public names that point to private addresses (like `192.168.x.x`). If the name doesn't resolve on the lab network, allow the domain in the router's rebind protection, or rely on the local DNS entry.
- **Can the screens reach the brain?** University networks often block devices from talking to each other. Before the router it works on the lab Wi-Fi between `pi01` and the desktop, and from the Newline through `pi01` (2026-11-10, "Networks before the router" → options 1–2).

## Gotchas found so far
- Wi-Fi MAC ≠ Ethernet MAC.
- Pi 5 = micro-HDMI; Jetson Orin Nano dev kit = DisplayPort.
- Phones/Quests may use randomized MACs.
- Duplicate factory hostnames on identical robots.
- Raspbot ships in hotspot mode; needs WLAN country set.
- Possible client isolation on managed Wi-Fi.
- The Pi's Wi-Fi can't do OWE ("Enhanced Open"); save open networks as plain open.
- raspbot1's clock is set to China time (Asia/Shanghai, UTC+8): its logs look 13 h ahead of the desktop. The clock itself is right.
- Lab wall Ethernet port works (tested with a Raspbot sharing internet via hotspot) — don't leave a router/hotspot on it without the professor's OK.
