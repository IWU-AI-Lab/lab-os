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
