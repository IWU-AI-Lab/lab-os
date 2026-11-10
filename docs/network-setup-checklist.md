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
1. **Test the lab Wi-Fi with what's already on it.** The desktops and the Pis are on it. Do the Step 0 test above between the desktop and a Pi. Replies → no client isolation: Pi screens can open the brain's address directly, and option 2 works. No replies → skip to 3.
2. **The Newline through a Pi** (your idea): Newline → Ethernet cable → a Pi that's already on the lab Wi-Fi. Set the Pi's wired connection to "Shared to other computers"; it gives the Newline an address and passes on internet and the way to the brain. Only works if test 1 replied. (If the Newline is already on a university network itself, try opening the brain's address from it first.)
3. **A cable from the brain's computer to the Newline.**
   - *HDMI + the Newline's USB touch cable:* the Newline becomes that computer's screen; the hub runs at `http://localhost` (a secure page, so voice works). No network at all. Only if the Newline is close to that computer.
   - *An Ethernet cable straight between them:* set the brain's wired connection to "Shared to other computers" (Ubuntu: Settings → Network → the wired connection → IPv4); the Newline opens the brain's Ethernet address. Needs a free Ethernet port on the brain (the desktops use Wi-Fi) and a long enough cable.
   - *Long HDMI:* passive HDMI cables get unreliable past ~10 m (4K: ~5 m); an active/optical HDMI cable (~15–30 m) and a USB extension for touch reach further. USB-C (video + touch in one cable) if both ends have it with video support. With HDMI the Newline is simply another monitor of the brain's computer: pages go there with "Show on another screen" (`docs/hub.md` → "Other monitors").
   - *The brain's own Wi-Fi hotspot* (added 2026-11-10): only if the desktop is on the network by its Ethernet port, so its Wi-Fi card is free: Ubuntu Settings → Wi-Fi → ⋮ → "Turn On Wi-Fi Hotspot"; the Newline joins it and opens the brain's hotspot address (usually `http://10.42.0.1:8080`). No cable to the Newline, no extra hardware. **Ask IT first**: campus networks often forbid running your own access point (the same question as the router).
4. **A phone hotspot as a stand-in router.** Every device joins the phone's Wi-Fi; phones normally let their clients reach each other. Limits: ~5–10 devices, the phone stays there and charged, addresses change, the internet uses the phone's data (chat is light).
5. **The lab router (GL.iNet Beryl AX)** solves all of it: devices reach each other, fixed addresses, a local DNS entry for `hub.indwesailab.com`, the Quest over Wi-Fi, no IT registration per device. Waiting on the professor's OK.

---

## Step 1 — List every device
| Name (unique, lowercase) | Device | Wi-Fi MAC address | How I got into it | Notes |
|---|---|---|---|---|
| raspbot1 | Yahboom Raspbot v2 | 88:a2:9e:5b:01:c8 | own hotspot + SSH | Order of the two MACs as given 2026-10-27; check `ip link` on raspbot1 if unsure. |
| raspbot2 | Yahboom Raspbot v2 | 88:a2:9e:5b:01:3f | own hotspot + SSH | |
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
Details: `current-focus.md` → "Step 7, concretely".
- **Fixed address for the brain:** a DHCP reservation in the lab router, so `hub.indwesailab.com` keeps pointing to the right computer. (Before the router: the desktop's university address may change; check it before relying on the name.)
- **Local DNS entry in the router:** `hub.indwesailab.com` → the brain's address, so the name works without internet. On the GL.iNet (OpenWrt) this is a custom DNS / hosts entry.
- **DNS rebinding protection:** routers and some networks block public names that point to private addresses (like `192.168.x.x`). If the name doesn't resolve on the lab network, allow the domain in the router's rebind protection, or rely on the local DNS entry.
- **Can the screens reach the brain?** University networks often block devices from talking to each other. Before the router: open the brain's address from the Newline once to check.

## Gotchas found so far
- Wi-Fi MAC ≠ Ethernet MAC.
- Pi 5 = micro-HDMI; Jetson Orin Nano dev kit = DisplayPort.
- Phones/Quests may use randomized MACs.
- Duplicate factory hostnames on identical robots.
- Raspbot ships in hotspot mode; needs WLAN country set.
- Possible client isolation on managed Wi-Fi.
- Lab wall Ethernet port works (tested with a Raspbot sharing internet via hotspot) — don't leave a router/hotspot on it without the professor's OK.
