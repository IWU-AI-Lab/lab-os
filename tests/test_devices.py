"""The device registry and the checks before anything is opened. No hardware: /proc and
/dev/v4l/by-path are fake folders here."""

import os

import pytest

from lab_os.devices import (
    InUse,
    PortNotAllowed,
    camera_device,
    camera_paths,
    check_not_in_use,
    check_port_allowed,
    check_usb_allowed,
    default_device,
    load_registry,
    serial_port,
    users_of,
)

GREEN_FOLLOWER = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00"
GREEN_LEADER = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00"


# ---- the green arms: borrowed, not off limits (step 11) -----------------------------------------
def test_the_green_arms_are_borrowed_devices():
    reg = load_registry()
    follower, leader = reg.devices["so101-green"], reg.devices["so101-green-leader"]
    assert (follower.kind, leader.kind) == ("so101", "so101-leader")
    assert follower.ports == (GREEN_FOLLOWER,) and leader.ports == (GREEN_LEADER,)
    for d in (follower, leader):
        assert d.borrowed and not d.off_limits
        assert d.calibration == "lerobot"  # read only from LeRobot's cache
    assert reg.borrowed_serials() == {"5B41533501", "5B41531599"}
    assert reg.off_limits_serials() == set()


def test_the_green_follower_hands_out_its_port():
    assert serial_port("so101-green") == GREEN_FOLLOWER
    check_port_allowed(GREEN_LEADER)


def test_a_borrowed_arm_is_never_a_default():
    assert default_device(("so101",)) == "so101-white"  # name the green one to use it


def test_the_training_cameras_by_socket_and_the_model_block_is_gone():
    reg = load_registry()
    cams = {d.name: d.socket for d in reg.devices.values() if d.kind == "camera"}
    # HACK: the white-cam names are a temporary alias of the same two sockets (devices.yaml)
    assert cams == {
        "so101-green-cam-a": "usb-0:7",
        "so101-green-cam-b": "usb-0:8",
        "so101-white-cam-a": "usb-0:7",
        "so101-white-cam-b": "usb-0:8",
    }
    assert all(reg.devices[n].borrowed for n in cams if "green" in n)
    check_usb_allowed({"vendor_id": 0x0C45, "product_id": 0x6366, "serial_number": "SN0001"})


# ---- off limits still means never (another place's devices) -------------------------------------
def test_off_limits_devices_are_refused(locked):
    with pytest.raises(PortNotAllowed, match="off limits"):
        serial_port("locked-arm", locked)
    port = locked.devices["locked-arm"].ports[0]
    with pytest.raises(PortNotAllowed):
        check_port_allowed(port, locked)
    with pytest.raises(PortNotAllowed):  # its serial under another name
        check_port_allowed("/dev/serial/by-id/usb-other_LOCKED0001-if00", locked)


def test_an_off_limits_camera_model_blocks_every_serial(locked):
    cam = {"vendor_id": 0x0C45, "product_id": 0x6366, "serial_number": "SN0001", "path": b"x"}
    with pytest.raises(PortNotAllowed):
        check_usb_allowed(cam, locked)
    with pytest.raises(PortNotAllowed):
        check_usb_allowed(cam | {"serial_number": "ANY-OTHER"}, locked)
    check_usb_allowed(cam | {"product_id": 0x1234}, locked)  # same vendor, other model


@pytest.mark.parametrize("port", ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"])
def test_raw_tty_refused(port):
    with pytest.raises(PortNotAllowed):
        check_port_allowed(port)


def test_other_by_id_port_allowed():
    check_port_allowed("/dev/serial/by-id/usb-some_other_adapter-if00")


def test_unconfigured_device_has_no_port():
    with pytest.raises(LookupError):
        serial_port("so101-white-leader")


def test_white_board_is_not_green():
    white = load_registry().devices["so101-white"]
    assert serial_port("so101-white") == white.ports[0]
    assert white.usb[0].serial not in load_registry().borrowed_serials()


# ---- one program per port ------------------------------------------------------------------------
def fake_proc(tmp_path, holders: dict[str, str]):
    """/proc with one process per entry: pid -> the device file it has open."""
    proc = tmp_path / "proc"
    proc.mkdir(parents=True)
    for i, (name, target) in enumerate(holders.items(), start=4200):
        (proc / str(i) / "fd").mkdir(parents=True)
        (proc / str(i) / "comm").write_text(name + "\n")
        os.symlink("/dev/null", proc / str(i) / "fd" / "0")
        os.symlink(target, proc / str(i) / "fd" / "7")
    (proc / "self").mkdir()  # not a pid: skipped
    return proc


def test_a_port_another_program_has_open_is_refused_with_a_sentence(tmp_path):
    port = tmp_path / "ttyACM0"
    port.touch()
    proc = fake_proc(tmp_path, {"lelab": str(port)})
    assert users_of(str(port), proc) == ["lelab (pid 4200)"]
    with pytest.raises(InUse) as e:
        check_not_in_use("so101-green", [str(port)], proc)
    assert "so101-green is in use by lelab (pid 4200): one program per port" in str(e.value)
    assert isinstance(e.value, PortNotAllowed)  # every caller that refuses ports refuses this too


def test_a_by_id_link_counts_as_its_device(tmp_path):
    tty = tmp_path / "ttyACM1"
    tty.touch()
    by_id = tmp_path / "usb-green-if00"
    by_id.symlink_to(tty)
    proc = fake_proc(tmp_path, {"python3": str(tty)})
    with pytest.raises(InUse, match="python3"):
        check_not_in_use("so101-green", [str(by_id)], proc)


def test_a_free_port_passes_and_our_own_process_doesnt_count(tmp_path, monkeypatch):
    port = tmp_path / "ttyACM0"
    port.touch()
    proc = fake_proc(tmp_path, {"other": str(tmp_path / "elsewhere")})
    check_not_in_use("so101-white", [str(port)], proc)
    mine = fake_proc(tmp_path / "2", {"lab-os": str(port)})
    monkeypatch.setattr(os, "getpid", lambda: 4200)
    check_not_in_use("so101-white", [str(port)], mine)


def test_processes_we_may_not_look_into_are_skipped(tmp_path):
    proc = tmp_path / "proc"
    (proc / "1").mkdir(parents=True)  # no fd folder readable (root's, another user's)
    assert users_of(str(tmp_path / "x"), proc) == []


# ---- cameras by socket ---------------------------------------------------------------------------
def by_path(tmp_path):
    """Two identical cameras in sockets 7 and 8, as /dev/v4l/by-path/ links to video files."""
    folder = tmp_path / "by-path"
    folder.mkdir()
    for n, socket in enumerate((7, 7, 8, 8)):
        video = tmp_path / f"video{n}"
        video.touch()
        (folder / f"pci-0000:00:14.0-usb-0:{socket}:1.0-video-index{n % 2}").symlink_to(video)
    return folder


def test_cameras_are_found_by_socket(tmp_path):
    folder = by_path(tmp_path)
    paths = camera_paths("so101-green-cam-a", by_path=str(folder))
    assert [os.path.basename(p) for p in paths] == [
        "pci-0000:00:14.0-usb-0:7:1.0-video-index0",  # the picture first
        "pci-0000:00:14.0-usb-0:7:1.0-video-index1",
    ]
    proc = fake_proc(tmp_path, {})
    got = camera_device("so101-green-cam-b", by_path=str(folder), proc=proc)
    assert got.endswith("usb-0:8:1.0-video-index0")


def test_a_camera_in_use_is_refused(tmp_path):
    folder = by_path(tmp_path)
    proc = fake_proc(tmp_path, {"lelab": str(tmp_path / "video0")})  # LeLab records socket 7
    with pytest.raises(InUse, match="so101-green-cam-a is in use by lelab"):
        camera_device("so101-green-cam-a", by_path=str(folder), proc=proc)
    camera_device("so101-green-cam-b", by_path=str(folder), proc=proc)  # the other one is free


def test_a_missing_camera_says_where_it_looked(tmp_path):
    with pytest.raises(LookupError, match="no camera in socket usb-0:7"):
        camera_paths("so101-green-cam-a", by_path=str(tmp_path))
    with pytest.raises(LookupError, match="needs kind: camera"):
        camera_paths("so101-white", by_path=str(tmp_path))


def test_an_off_limits_camera_is_refused_before_looking(locked, tmp_path):
    with pytest.raises(PortNotAllowed):
        camera_paths("locked-cams", locked, by_path=str(tmp_path))
