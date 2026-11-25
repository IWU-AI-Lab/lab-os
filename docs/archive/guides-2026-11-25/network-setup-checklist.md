# Network setup checklist: get every device onto the network

> **The plan changed (2026-10-23).** The lab will not register every device with campus IT. It will use **its own travel router**, connected to the lab's wall Ethernet port, with the professor's OK (`docs/plan/log.md` → "Network plan"). With the router, devices join the router's Wi-Fi with a password. So **Steps 1, 3 and 5 apply only if you register devices one at a time.** **Steps 0, 2 (find the Wi-Fi hardware), 4 and 6 still apply.** Teleop needs none of this (it uses USB).

The goal: every robot and device joins the network, has its own name, and the Linux "brain" desktop can reach it with `ssh <name>`. Then Claude Code can do the rest.

---

## Step 0: a 2-minute test: can devices on the network talk to each other?
Some managed Wi-Fi networks use **"client isolation"**: devices can reach the internet, but *not each other*.

On one Linux desktop, run:
```
ip addr        # write down this computer's address (10.x.x.x or 192.168.x.x)
```
On the other Linux desktop, run:
```
ping -c 4 <first desktop's address>
```
- Replies: good, the devices can talk to each other.
- "Destination unreachable" or no reply: probably client isolation. (On the lab's own router this does not apply: the lab controls that network.)

---

## Networks before the router (2026-11-09)
lab-os needs the screens to reach the brain (the hub on the Newline, modules on other screens). **New devices cannot join the lab Wi-Fi without campus IT, and that is slow** (the Raspbots waited two weeks). So nothing here adds a device to it. The options, the best first:
1. **Test the lab Wi-Fi with the devices that are already on it.** The desktops and the Pis are on it. Do the Step 0 test between the desktop and a Pi. If you get replies, there is no client isolation: Pi screens can open the brain's address directly, and option 2 works. If not, go to option 3. **Result (2026-11-10): replies** between `pi01` and the lab desktop, in both directions.
2. **The Newline through a Pi:** connect the Newline with an Ethernet cable to a Pi that is already on the lab Wi-Fi. Set the Pi's wired connection to "Shared to other computers". The Pi gives the Newline an address, and passes on the internet and the way to the brain. This works only if test 1 had replies.
   **It works (2026-11-10)** with `pi01` (`pi01.iwu.ai.lab`, user `ai-comp-lab-rp-01`, Debian 13 with NetworkManager; the lab desktop's SSH key is on it). On the Pi, do this once:
   ```bash
   sudo nmcli con add type ethernet ifname eth0 con-name newline-share ipv4.method shared ipv6.method disabled connection.autoconnect-priority 10
   sudo nmcli con up newline-share        # it comes back by itself after a reboot; to undo: sudo nmcli con delete newline-share
   ```
   - Put the cable into the Newline's **LAN in** port. The Newline has no Ethernet settings of its own; it takes an address (`10.42.0.x`; it was `10.42.0.103`).
   - After you switch the sharing on, disconnect and connect the cable once, so that the Newline asks again.
   - Then open `http://192.168.7.72:8080/design` in the Newline's Chrome (the desktop's Wi-Fi address; run `hostname -I` on the desktop if it changed; the desktop's name did not work from the Pi).
3. **A cable from the brain's computer to the Newline:**
   - *HDMI and the Newline's USB touch cable:* the Newline becomes that computer's screen, and the hub runs at `http://localhost` (a secure page, so voice works). No network at all. Only if the Newline is near that computer.
   - *An Ethernet cable directly between them:* set the brain's wired connection to "Shared to other computers" (Ubuntu: Settings → Network → the wired connection → IPv4). The Newline opens the brain's Ethernet address. It needs a free Ethernet port on the brain (the desktops use Wi-Fi) and a cable that is long enough. **It works (2026-11-13)** from the lab desktop; the numbers are in `docs/dev/GOTCHAS.md`.
   - *A long HDMI cable:* passive HDMI cables become unreliable after about 10 m (4K: about 5 m). An active or optical HDMI cable (about 15 to 30 m) and a USB extension for touch reach further. USB-C (video and touch in one cable) works if both ends have it with video. With HDMI, the Newline is one more monitor of the brain's computer: pages go there with "Open on…" → "Another monitor of this computer" (`docs/archive/guides-2026-11-25/hub.md` → "Other monitors").
   - *The brain's own Wi-Fi hotspot:* only if the desktop is on the network through its Ethernet port, so that its Wi-Fi card is free. In Ubuntu Settings → Wi-Fi → ⋮, select "Turn On Wi-Fi Hotspot". The Newline joins it and opens the brain's hotspot address (usually `http://10.42.0.1:8080`). No cable to the Newline and no extra hardware. **Ask IT first:** campus networks often do not allow your own access point (the same question as for the router).
4. **A phone hotspot as a temporary router.** Every device joins the phone's Wi-Fi. Phones usually let their devices reach each other. The limits: about 5 to 10 devices, the phone must stay there and charged, the addresses change, and the internet uses the phone's data (chat uses little).
   - *The Linksys WRK54G from the closet* (found 2026-11-16): about 20 Mbps of Wi-Fi for everything (the internet through it measured 8 Mbps down, 2026-11-17). Enough for hub pages, chat, Quest teleop messages and the Raspbots, but not for several live camera videos (`docs/dev/GOTCHAS.md`). It needs a WPA2 password and IT's OK, like any router.
5. **The lab router** (a GL.iNet Beryl 7 travel router; it arrived on 2026-11-22, `docs/plan/current-focus.md` → "Waiting on others") solves all of it: devices reach each other, fixed addresses, a local DNS entry for `hub.indwesailab.com`, the Quest over Wi-Fi, and no IT registration for each device. The professor approved it, on the wall port too (2026-11-20). Setting it up: `docs/guides/lab-checklist.md` → part N.

### The ThinkCentres at the front of the room (2026-11-11)
The lab has 7 ThinkCentres, all unused now: 3 at the back (near the wall ports) and 4 at the front. The 4 at the front are on two separate desks, far from the wall Ethernet ports (at the back). The network switch is on one of the two desks, so a cable to the switch reaches only that desk; the other desk also needs a cable. The ThinkCentres have no Wi-Fi. There is no access point next to the switch (one was planned; nobody knows what happened to it). The options, the cheapest first:
1. **Ask first:** is there a wall port at the front that is not switched on (IT can switch one on), and what happened to the planned access point?
2. **A Pi as the bridge** (the same method as the Newline through `pi01`, option 2 above): a Pi on the lab Wi-Fi, with its Ethernet into the switch, set to "Shared to other computers". Every ThinkCentre on the switch gets an address and the internet. Free, and already proven. The limits: all of them share the Pi's Wi-Fi speed, and other computers can reach the ThinkCentres only through the Pi.
3. **With the lab router:** a second small router at the front (for example a GL.iNet Opal, about $40) joins the main router's Wi-Fi and feeds the switch by cable ("repeater" or "WDS" mode). Then the ThinkCentres are on the lab network like everything else.
4. **Powerline adapters** (about $50 a pair): Ethernet through the room's power wiring, one plug at the back, one at the front. Usually good within one room. Ask IT: some campuses do not allow them.
5. **A USB Wi-Fi adapter for each ThinkCentre** (about $15 each, 4 of them; no cables, which suits two desks): select one whose chip Linux supports without extra drivers (for example MediaTek MT7612U or MT7921AU). Each one still needs IT registration for the lab Wi-Fi, or the lab router's password.
6. **One long, tidy cable:** one cable from the back to the switch is enough (the switch shares it). A flat Ethernet cable along the wall, under the carpet edge, or in a cable cover looks much better than loose cables.

---

## Step 1: list every device
| Name (unique, lowercase) | Device | Wi-Fi MAC address | How to get into it | Notes |
|---|---|---|---|---|
| raspbot1 | Yahboom Raspbot v2 (Raspberry Pi 5) | 88:a2:9e:5b:01:3f | its own hotspot and SSH, or an Ethernet cable (Step 2) | Checked with `ip link` 2026-11-10. Ethernet (eth0) MAC `88:a2:9e:5b:01:3e`. Hostname still `yahboom`, user `pi`. Cannot join IWU-AI-LAB yet (Step 5). |
| raspbot2 | Yahboom Raspbot v2 | 88:a2:9e:5b:01:c8 | its own hotspot and SSH | |
| pi5-1 … | Raspberry Pi 5 (bridges for arms, spares) | | | |
| jetson1 … jetson5 | Jetson Orin Nano | | | |
| quest-a, quest-b, quest-c | Meta Quest 3 | | USB (adb) | Their serial numbers are in `config/devices.yaml`. |
| (later) picar1 to picar3 | PiCar Pro (not built) | | | |

The **xArm**, the **SO-101** arms and **TonyBot v1** (Arduino) connect over USB or Bluetooth, so they do not join the network themselves. The Pi 5 (or other computer) that they connect to does.

---

## Step 2: check each device's Wi-Fi hardware and MAC address
⚠️ Devices often have two MAC addresses: one for the Ethernet port and one for Wi-Fi.

### How to get into a device
- **Raspbot:** connect to its own hotspot ("Raspbot") and use SSH (its small screen shows the IP address).
- **Raspbot by Ethernet cable** (worked for raspbot1, 2026-11-10; no Wi-Fi needed):
  1. Connect a cable from a desktop's Ethernet port to the Raspbot. (This was done on the lab's **other** Ubuntu desktop, not on `ai-comp-lab-ubuntu-76358`. The other desktop's "Wired connection 1" is still set to share, so do not connect that one to a wall socket. `ai-comp-lab-ubuntu-76358`'s connection is normal, `ipv4.method auto`, checked 2026-11-11.)
  2. On the desktop, set "Wired connection 1" to share (once): Ubuntu Settings → Network → the wired connection → IPv4 → "Shared to other computers". Or run `nmcli con modify "Wired connection 1" ipv4.method shared`, then `nmcli con up "Wired connection 1"`. The desktop becomes `10.42.0.1` and gives the Raspbot a `10.42.0.x` address.
  3. Find the address with `ip neigh` (raspbot1 was `10.42.0.84`), then run `ssh pi@10.42.0.x`.
- **Raspberry Pi 5:** a monitor and a keyboard. ⚠️ The Pi 5 uses **micro-HDMI**: you need a micro-HDMI to HDMI cable or adapter.
- **Jetson Orin Nano:** a monitor and a keyboard. ⚠️ The dev kit's video port is **DisplayPort**, not HDMI.

### The command (Pi, Jetson, any Linux device)
```
ip link
```
Find the entry whose name starts with **`wl`** (for example `wlan0`, or `wlP1p1s0` on a Jetson). The MAC is the `link/ether xx:xx:xx:xx:xx:xx` under it.
- **No entry that starts with `wl`?** The device has no Wi-Fi hardware. It needs a USB Wi-Fi adapter or an Ethernet cable.

### Quest 3 and phones
⚠️ If you register them, switch **off** "private / randomized MAC address" for the network.

---

## Step 3: (only if you register devices one at a time) ask campus IT
Ask through the professor. The questions: can the lab register devices itself? Can it have reserved IP addresses? Can devices talk to each other? What are the network's name and sign-in?

---

## Step 4: rename each device and change the default passwords
Two Raspbots with the same factory name confuse everything:
```
sudo hostnamectl set-hostname raspbot1     # use the name from your table
```
Robots often come with **well-known default passwords**. Change them:
```
passwd
```
Write the new passwords in a safe place (not in the code repository).

---

## Step 5: join the Wi-Fi (the lab router or the lab network)
On each Pi or Jetson (NetworkManager), run:
```
sudo nmcli dev wifi connect "<network name>" password "<password>"
```
- First, set the **Wi-Fi country** if necessary (`sudo raspi-config` → Localisation → WLAN Country).
- **Raspbots start in hotspot mode.** They may need Yahboom's own steps to join a normal network.
- **IWU-AI-LAB is an "Enhanced Open" (OWE) network, and the Pi's Wi-Fi chip (brcmfmac) cannot do OWE.** Make the saved profile plain open: `sudo nmcli con modify IWU-AI-LAB remove 802-11-wireless-security`. That worked on `pi01`.
- **raspbot1 still cannot join IWU-AI-LAB** (2026-11-10), even with the open profile and both MACs registered by IT: every try ends with `ASSOC-REJECT status_code=16`. The probable cause is its old software (kernel 6.6.31, Wi-Fi firmware 7.45.234 from 2021, NetworkManager 1.42.4). `pi01` joins with kernel 6.18, firmware 7.45.265 and NetworkManager 1.52. A next step, not tried: `sudo apt install firmware-brcm80211` on raspbot1 (the version offered may still not have 7.45.265). Details: `docs/dev/GOTCHAS.md` (2026-11-10, raspbot1 Wi-Fi).
- **In plain words (for the professor):** IWU-AI-LAB has no password, but it is encrypted with a newer method ("Enhanced Open"). The Raspbot's Wi-Fi chip does not know that method, so we set it to join the network's plain "open" side; that works for `pi01`. On raspbot1, even that fails at the first step, before the network answers: its own Wi-Fi software stops (status 16, a time-out). The MAC registration is probably not the problem (IT registered both addresses). The probable cause is the old software that Yahboom put on it (Wi-Fi firmware from 2021): `pi01`, the same kind of computer with newer software, joins correctly. This is probable, not proven.
- **Would the lab's own router fix it? Very probably, for this problem.** The router's Wi-Fi uses a normal password (WPA2), which Pis have used for years, and needs no IT registration. raspbot1's own hotspot uses the same kind of password and works. What the router does not fix: the Newline's slowness (that is the screen itself), the Raspbot's other old software, and the range (about one room). **Test before you buy:** make raspbot1 join a phone hotspot set to WPA2 (`docs/guides/lab-checklist.md` → "Optional: raspbot1 on a phone hotspot"). If it joins, the router will very probably work too.
- To check that it worked: `ip addr` must show an address on the `wl…` entry.

---

## Step 6: from the Linux desktop: SSH keys and short names
Once, on the desktop:
```
ssh-keygen -t ed25519          # press Enter for each question
```
For each device (once):
```
ssh-copy-id <user>@<device address or name.local>
```
Then add a short name for each device to `~/.ssh/config`:
```
Host raspbot1
    HostName <address or raspbot1.local>
    User pi
```
Test it:
```
ssh raspbot1 hostname         # it must show "raspbot1" without a password question
```
After this, Claude Code (on the desktop) can reach every device by its name.

---

## Step 7: the brain's secure address (for voice on every screen)
**For later (decision 2026-11-10):** voice works first on `localhost` and with Chrome's flag (`docs/archive/guides-2026-11-25/voice.md` → "Secure pages").
- **A fixed address for the brain:** a DHCP reservation in the lab router, so that `hub.indwesailab.com` always points to the correct computer. (Before the router, the desktop's university address can change: check it before you use the name.)
- **A local DNS entry in the router:** `hub.indwesailab.com` → the brain's address, so that the name works without the internet. On the GL.iNet (OpenWrt), this is a custom DNS or hosts entry.
- **DNS rebinding protection:** routers and some networks block public names that point to private addresses (such as `192.168.x.x`). If the name does not work on the lab network, allow the domain in the router's rebind protection, or use the local DNS entry.
- **Can the screens reach the brain?** University networks often block devices from each other. Before the router, it works on the lab Wi-Fi between `pi01` and the desktop, and from the Newline through `pi01` ("Networks before the router" → options 1 and 2).

## Problems found so far
- The Wi-Fi MAC is not the Ethernet MAC.
- The Pi 5 has micro-HDMI; the Jetson Orin Nano dev kit has DisplayPort.
- Phones and Quests can use random MACs.
- Identical robots have the same factory hostnames.
- The Raspbot starts in hotspot mode and needs its WLAN country set.
- Managed Wi-Fi can have client isolation.
- The Pi's Wi-Fi cannot do OWE ("Enhanced Open"): save open networks as plain open.
- raspbot1's time zone is China time (Asia/Shanghai, UTC+8), so its logs look 13 h ahead of the desktop. The clock itself is correct.
- **raspbot1 did not join an Android phone's hotspot either** (2026-11-13: 2.4 GHz, correct password). So OWE is not the only problem. The next test: set the hotspot's security to **WPA2-Personal** (Android: Hotspot → Security; many phones use WPA3 or WPA2/WPA3 by default, which older Pi Wi-Fi may not support), and read why it failed on the Raspbot over its cable (`journalctl -u NetworkManager -b | tail -50`). The answer matters for the router: set to WPA2, it should work.
- The lab's wall Ethernet port works (tested with a Raspbot that shared the internet through a hotspot). The professor approved the lab's travel router on it (2026-11-20). Any other router or hotspot on it still needs the professor's OK.
