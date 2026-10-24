"""Parsing for the messages the XR page sends (format: docs/protocol.md)."""

from dataclasses import dataclass

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]  # x, y, z, w

BUTTON_NAMES = ("a", "b", "thumbstick")


@dataclass(frozen=True)
class ControllerState:
    """One controller in one frame. `pos`/`quat` are None when tracking is lost."""

    pos: Vec3 | None
    quat: Quat | None
    trigger: float
    grip: float
    buttons: dict[str, bool]
    thumbstick: tuple[float, float]

    @property
    def tracked(self) -> bool:
        return self.pos is not None and self.quat is not None


@dataclass(frozen=True)
class XRFrame:
    t: float  # sender's clock, milliseconds (only meaningful relative to other frames)
    hands: dict[str, ControllerState]  # "left" / "right"; a missing key = controller not present


def _floats(value, n: int, what: str) -> tuple[float, ...]:
    if not isinstance(value, list | tuple) or len(value) != n:
        raise ValueError(f"{what}: expected {n} numbers, got {value!r}")
    return tuple(float(v) for v in value)


def _unit(value, what: str) -> float:
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{what}: expected 0..1, got {v}")
    return v


def parse_controller(raw: dict) -> ControllerState:
    pos = raw.get("pos")
    quat = raw.get("quat")
    buttons = raw.get("buttons") or {}
    return ControllerState(
        pos=None if pos is None else _floats(pos, 3, "pos"),
        quat=None if quat is None else _floats(quat, 4, "quat"),
        trigger=_unit(raw.get("trigger", 0.0), "trigger"),
        grip=_unit(raw.get("grip", 0.0), "grip"),
        buttons={name: bool(buttons.get(name, False)) for name in BUTTON_NAMES},
        thumbstick=_floats(raw.get("thumbstick", [0.0, 0.0]), 2, "thumbstick"),
    )


def parse_frame(raw: dict) -> XRFrame:
    """Parse an `xr_input` message. Raises ValueError on anything malformed."""
    if raw.get("type") != "xr_input":
        raise ValueError(f"not an xr_input message: {raw.get('type')!r}")
    hands = raw.get("hands")
    if not isinstance(hands, dict):
        raise ValueError("hands: expected an object")
    return XRFrame(
        t=float(raw.get("t", 0.0)),
        hands={side: parse_controller(c) for side, c in hands.items() if side in ("left", "right")},
    )
