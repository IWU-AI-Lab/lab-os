"""The card swipe without the page in focus (quick job 113): the brain reads the card reader."""

import asyncio
import os
from pathlib import Path

import pytest

from lab_os.devices import Device, Registry, UsbId
from lab_os.hub import card_reader as cr

# key codes: 1…9 = 2…10, 0 = 11, ; = 39, / = 53, Enter = 28, Shift = 42
KEYS = {str((i + 1) % 10): 2 + i for i in range(10)} | {";": 39, "=": 13, "^": 7}


def _press(s: cr.Swipe, text: str, t: float = 0.0, step: float = 0.005) -> bool:
    out = False
    for ch in text:
        if ch == "?":
            s.key(42, 1, t)
            out = s.key(53, 1, t) or out
            s.key(53, 0, t)
            s.key(42, 0, t)
        else:
            out = s.key(KEYS[ch], 1, t) or out
            s.key(KEYS[ch], 0, t)
        t += step
    return s.key(28, 1, t) or out


def test_a_student_id_is_a_swipe():
    assert _press(cr.Swipe(), ";1234567890?")
    assert _press(cr.Swipe(), "123456")


def test_other_data_is_not():
    assert not _press(cr.Swipe(), "123")  # too short
    assert not _press(cr.Swipe(), "1234=5678")  # a bank card's data
    s = cr.Swipe()
    for ch in "12":
        s.key(KEYS[ch], 1, 0.0)
    assert not _press(s, "34", t=5.0)  # a long gap starts over: only "34" is left


def _input(root: Path, ev: str, name: str, vendor: str, product: str, keys: str = "1 ff") -> None:
    d = root / ev / "device"
    (d / "id").mkdir(parents=True)
    (d / "capabilities").mkdir()
    (d / "name").write_text(name + "\n")
    (d / "id" / "vendor").write_text(vendor + "\n")
    (d / "id" / "product").write_text(product + "\n")
    (d / "capabilities" / "key").write_text(keys + "\n")


def test_finds_the_reader_but_never_a_keyboard(tmp_path):
    _input(tmp_path, "event3", "Logitech USB Keyboard", "046d", "c31c")
    _input(tmp_path, "event5", "IDTECH USB Card Reader", "0acd", "0001")
    _input(tmp_path, "event7", "HID 1234:abcd", "1234", "abcd")
    _input(tmp_path, "event8", "HID 1234:abcd", "1234", "abcd", keys="0")  # no keys
    assert cr.find_readers(set(), tmp_path) == ["event5"]
    reg = Registry({"r": Device("r", "card-reader", usb=(UsbId(0x1234, 0xABCD),))})
    assert cr.find_readers(cr.reader_ids(reg), tmp_path) == ["event5", "event7"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs a pipe")
async def test_run_reads_a_swipe_from_the_device(tmp_path):
    sys_root, dev = tmp_path / "sys", tmp_path / "dev"
    dev.mkdir()
    _input(sys_root, "event5", "USB Card Reader", "0c45", "7403")
    os.mkfifo(dev / "event5")  # stands in for /dev/input/event5
    swiped = asyncio.Event()

    async def on_swipe() -> None:
        swiped.set()

    task = asyncio.create_task(cr.run(Registry({}), on_swipe, sys_root, dev))
    fd = await asyncio.to_thread(os.open, dev / "event5", os.O_WRONLY)
    data = b"".join(
        cr.EVENT.pack(1, i * 1000, cr.EV_KEY, code, v)
        for i, code in enumerate([2, 3, 4, 5, 6, 28])
        for v in (1, 0)
    )
    os.write(fd, data)
    await asyncio.wait_for(swiped.wait(), 3)
    os.close(fd)
    task.cancel()


async def test_only_the_pages_on_this_computer_get_the_swipe():
    from lab_os.hub.hub_devices import HubDevices, Window

    class Ws:
        def __init__(self):
            self.got = []

        async def send_str(self, s):
            self.got.append(s)

    devices = HubDevices(lambda: {})
    here, there = Ws(), Ws()
    devices.windows = {
        "a": Window("a", "desk", here, "127.0.0.1", here=True),
        "b": Window("b", "newline", there, "192.168.8.50"),
    }
    await devices.tell_here({"type": "card"})
    assert here.got == ['{"type": "card"}'] and there.got == []
