# Lab inventory

Every device in the lab, what it is, and its name in lab-os. This page is the one list of the lab's devices. How lab-os recognizes and drives a device (serial numbers, sockets, calibration, the green arms' rules) is in `config/devices.yaml`. Network addresses are in `docs/archive/guides-2026-11-25/network-setup-checklist.md`. Started 2026-11-25 from the plan log, `config/devices.yaml` and the lab reports. "Not checked" means that nobody has counted or tested it yet.

Every device has a sticker. The Raspberry Pis are numbered 1 to 10. The desktops and ThinkCentres carry a university IT number.

## Computers
| Device | How many | lab-os name | Notes |
|---|---|---|---|
| Desktop, RTX 5070, Ubuntu | 2 | the brain: `ai-comp-lab-ubuntu-76358` (192.168.8.130); the other Ubuntu desktop | The brain runs lab-os and has the arms on its USB. The other one can drive the Newline or be a backup brain. |
| Desktop, RTX 5070, Windows 11 | 4 | `win-1`, `win-2` (names from [the earlier lab check M.1](https://github.com/IWU-AI-Lab/lab-os/blob/efbc5b1567b8dc37b69861ca10077dcb5c846068/docs/guides/lab-checklist.md); may change) | One runs the Raspbot program; one belongs to someone else. The GPU memory (12 GB) is not checked. |
| Jetson Orin Nano | 5 | `jetson1` to `jetson5` | On the big switch. The video port is DisplayPort. |
| Raspberry Pi 5 | about 10 | `pi01` …, `pi-1` … | One drives the Newline (HDMI and the touch cable). Some are on the big switch. |
| ThinkCentre | 7 | none | No Wi-Fi. 4 at the front, 3 at the back. Not used. |

## Screens
| Device | How many | lab-os name | Notes |
|---|---|---|---|
| Newline Q Pro Elite, about 75", on wheels | 1 | `newline` | Runs Android. Used by HDMI at 1600×900 from a Pi, with the USB touch cable. Its microphone reaches the Pi through the touch cable (card 2, "Newline Q Pro Elite"). Manual: `docs/device_manuals/` (another model). |
| Raspberry Pi touchscreen, about 7 to 9" | 3 | `pi-1` … | |
| ViewSonic 32" monitor | not checked | | On the desktops. |
| Projector | 1 | | For the system diagram in the demo. |

## Robots
| Device | How many | lab-os name | Notes |
|---|---|---|---|
| SO-101 arm, white set (follower and leader) | 1 set | `so101-white`, `so101-white-leader` | lab-os's own set. USB and a wall power supply, no switch. |
| SO-101 arm, green set (follower and leader) | 1 set | `so101-green`, `so101-green-leader` | The builder's training set. lab-os may use it with four rules (`AGENTS.md`). |
| xArm 1S | 2 | `xarm1` (works), `xarm2` (not built) | USB. |
| Yahboom Raspbot v2 (Raspberry Pi 5) | 2 | `raspbot1`, `raspbot2` | raspbot1 is on the router's 5 GHz Wi-Fi; `ssh raspbot1`. It has a camera on a pan-and-tilt mount, an ultrasonic sensor and a USB microphone. |
| TonyBot v1 (Arduino) | 1 | none | USB or Bluetooth. |
| PiCar Pro | 3 | `picar1` to `picar3` (later) | Not built. |
| Air:bit 2 drone | 3 | none | Drones stay out of AI, voice and visitor control. |
| Hiwonder wireless glove | 2 | none | Manuals: `docs/device_manuals/`. |

## Cameras
| Device | How many | lab-os name | Notes |
|---|---|---|---|
| Innomaker U20CAM-1080p | 2 | `so101-green-cam-wrist`, `so101-green-cam-stand` | The green set's. Both have the serial SN0001, so lab-os tells them apart by USB socket. |
| Arm cameras of the white set | 2 | `so101-white-cam-wrist`, `so101-white-cam-stand` | Today they use the green set's sockets (the hack in `docs/plan/current-focus.md`). The model is not checked. |
| Logitech C615 webcam (1080p) | 1 | none | For Webcam Control. Its microphone is not used. |
| Kinect for Xbox 360 (model 1414) | 1 | none | Needs drivers that need `sudo`. |
| The Raspbot's camera | 2 | (raspbot1's) | On the pan-and-tilt mount. |

## Sound
| Device | How many | Notes |
|---|---|---|
| USB microphone (small dongle) | 4 | One on raspbot1, one in the brain's front port, two for the Windows desktops. They are weak; the roof fan is loud. |
| The Newline's microphones and speakers | 1 | See Screens. |
| The Quest's microphone and speakers | 3 | See Wearables. |
| Phones, laptops, old Nokias, a Pixel C | not checked | Possible microphones and remotes (quick job 124). |

## Wearables
| Device | How many | lab-os name | Notes |
|---|---|---|---|
| Meta Quest 3 | 3 | `quest-a`, `quest-b`, `quest-c` | Serial numbers in `config/devices.yaml`. The Quest on the router is 192.168.8.180. Quest B or C is on loan to an AI club member. |
| Google Glass Explorer Edition | 1 | none | Boots; voice commands work. |

## Network
| Device | How many | Notes |
|---|---|---|
| GL.iNet Beryl 7 router (GL-MT3600BE) | 1 | Since 2026-11-22. Admin page 192.168.8.1. Its one LAN port goes to the big switch. |
| Big switch | 1 | The Jetsons and 4 Pis. |
| Ethernet cables | many | |

## Other
| Device | How many | Notes |
|---|---|---|
| USB card reader | 1 | Reads student IDs (the card swipe). It types like a keyboard. |
| USB hub, 3 ports (two USB 2.0, one USB 3.0) | 1 | The builder's own, lent for now. |
| Cables, adapters, extension cords, boxes, a trolley | many | The demo kit. |

## To buy
- A powered USB hub with 7 ports, for the brain desktop.
- A USB-C power bank, for the router away from the lab.
- Stronger table clamps for the SO-101s.
- A USB speakerphone for the room, only if the nearest-microphone feature is not enough.
