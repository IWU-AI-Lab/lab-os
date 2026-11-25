"""`lab-os usb` (quick job 115) on a fake /sys: every device under its controller, with names."""

import os

from lab_os import usb_map
from lab_os.devices import Device, Registry, UsbId

CTRL = "0000:00:14.0"


def add(sys_dir, chain, vid, pid, product, kind, serial="", controller=CTRL):
    """One USB device at `chain` with one interface of class `kind` (hex)."""
    folder = sys_dir / "devices" / "pci0000:00" / controller / "usb1" / f"1-{chain}"
    folder.mkdir(parents=True)
    for f, v in (("idVendor", vid), ("idProduct", pid), ("product", product), ("speed", "480")):
        (folder / f).write_text(v + "\n")
    if serial:
        (folder / "serial").write_text(serial + "\n")
    (folder / f"1-{chain}:1.0").mkdir()
    (folder / f"1-{chain}:1.0" / "bInterfaceClass").write_text(kind + "\n")
    os.symlink(folder, sys_dir / "bus" / "usb" / "devices" / f"1-{chain}")
    return folder


def fake_lab(tmp_path):
    sys_dir = tmp_path / "sys"
    (sys_dir / "bus" / "usb" / "devices").mkdir(parents=True)
    root = sys_dir / "devices" / "pci0000:00" / CTRL / "usb1"
    root.mkdir(parents=True)
    (root / "product").write_text("xHCI Host Controller\n")
    os.symlink(root, sys_dir / "bus" / "usb" / "devices" / "usb1")
    add(sys_dir, "7", "1a40", "0101", "USB 2.0 Hub", "09")
    arm = add(sys_dir, "7.1", "1a86", "55d3", "USB Single Serial", "02", serial="5B41532410")
    add(sys_dir, "7.2", "0c45", "6366", "USB Camera", "0e", serial="SN0001")
    add(sys_dir, "7.3", "0c45", "6366", "USB Camera", "0e", serial="SN0001")
    add(sys_dir, "3", "0d8c", "0014", "USB Audio Device", "01")
    add(sys_dir, "5", "ffff", "0035", "Card Reader", "03")
    (sys_dir / "class" / "tty" / "ttyACM0").mkdir(parents=True)
    os.symlink(arm / "1-7.1:1.0", sys_dir / "class" / "tty" / "ttyACM0" / "device")
    (tmp_path / "ttyACM0").touch()
    port = tmp_path / "usb-1a86_USB_Single_Serial_5B41532410-if00"
    port.symlink_to(tmp_path / "ttyACM0")
    reg = Registry(
        {
            "so101-white": Device(
                "so101-white",
                "so101",
                ports=(str(port),),
                usb=(UsbId(0x1A86, 0x55D3, serial="5B41532410"),),
            ),  # fmt: skip
            "white-wrist": Device("white-wrist", "camera", beside="so101-white", hub_port="2"),
            "green-wrist": Device("green-wrist", "camera", socket="usb-0:8"),
        }
    )
    return str(sys_dir), reg


def test_every_device_under_its_controller_with_its_name(tmp_path):
    sys_dir, reg = fake_lab(tmp_path)
    out = usb_map.report(sys_dir, reg)
    lines = out.splitlines()
    assert lines[0] == f"USB controller {CTRL} (xHCI Host Controller)"
    assert any("7.1" in line and "so101-white: serial" in line for line in lines)
    wrist = next(line for line in lines if " 7.2 " in line)
    assert "white-wrist: camera" in wrist and '[beside: so101-white, hub_port: "2"]' in wrist
    stand = next(line for line in lines if " 7.3 " in line)
    assert "not in devices.yaml: camera" in stand and 'hub_port: "3"' in stand  # says what to add
    assert any("Card Reader" in line and "keyboard/mouse" in line for line in lines)
    assert "3 cameras and microphones share this controller" in out


def test_no_sys_says_linux_only(tmp_path):
    assert "Linux only" in usb_map.report(str(tmp_path), Registry({}))
