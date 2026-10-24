import pytest

from lab_os.teleop.messages import parse_frame


def frame(**right):
    hand = {"pos": [0, 1, 0], "quat": [0, 0, 0, 1], "trigger": 0.2, "grip": 0.9} | right
    return {"type": "xr_input", "t": 12.5, "hands": {"right": hand}}


def test_parse_full_frame():
    f = parse_frame(frame(buttons={"a": True}, thumbstick=[0.5, -0.5]))
    c = f.hands["right"]
    assert f.t == 12.5
    assert c.pos == (0.0, 1.0, 0.0)
    assert c.tracked
    assert c.buttons == {"a": True, "b": False, "thumbstick": False}
    assert c.thumbstick == (0.5, -0.5)


def test_tracking_lost_is_untracked():
    assert not parse_frame(frame(pos=None)).hands["right"].tracked


def test_unknown_sides_dropped():
    raw = frame()
    raw["hands"]["head"] = raw["hands"]["right"]
    assert set(parse_frame(raw).hands) == {"right"}


@pytest.mark.parametrize(
    "raw",
    [
        {"type": "hello"},
        {"type": "xr_input", "hands": []},
        frame(pos=[0, 1]),
        frame(grip=1.5),
        frame(quat="nope"),
    ],
)
def test_malformed_rejected(raw):
    with pytest.raises(ValueError):
        parse_frame(raw)
