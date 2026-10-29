import pytest

from lab_os.devices import PortNotAllowed, check_port_allowed, load_registry, serial_port

GREEN_PORTS = (
    "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41531599-if00",
    "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B41533501-if00",
)


def test_registry_marks_green_off_limits():
    green = load_registry().devices["so101-green"]
    assert green.off_limits
    assert set(green.ports) == set(GREEN_PORTS)


def test_green_device_refused():
    with pytest.raises(PortNotAllowed):
        serial_port("so101-green")


@pytest.mark.parametrize("port", GREEN_PORTS)
def test_green_ports_refused(port):
    with pytest.raises(PortNotAllowed):
        check_port_allowed(port)


@pytest.mark.parametrize("port", ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"])
def test_raw_tty_refused(port):
    with pytest.raises(PortNotAllowed):
        check_port_allowed(port)


def test_other_by_id_port_allowed():
    check_port_allowed("/dev/serial/by-id/usb-some_other_adapter-if00")


def test_unconfigured_device_has_no_port():
    with pytest.raises(LookupError):
        serial_port("so101-white")


CAMERA = {"vendor_id": 0x0C45, "product_id": 0x6366, "serial_number": "SN0001", "path": b"x"}


def test_training_cameras_are_blocked_by_model():
    from lab_os.devices import check_usb_allowed

    with pytest.raises(PortNotAllowed):
        check_usb_allowed(CAMERA)
    with pytest.raises(PortNotAllowed):
        check_usb_allowed(CAMERA | {"serial_number": "ANY-OTHER"})  # same model, any serial


def test_other_usb_devices_are_allowed():
    from lab_os.devices import check_usb_allowed

    check_usb_allowed({"vendor_id": 0x0483, "product_id": 0x5750, "serial_number": "X"})
    check_usb_allowed(CAMERA | {"product_id": 0x1234})  # same vendor, other model
