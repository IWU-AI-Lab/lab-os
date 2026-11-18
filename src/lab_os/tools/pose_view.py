"""`pose_view`: a picture of the arm's 3D model in a given pose, for an AI that can't see the arm
(focus step 3, docs/guides/ai-control.md). No camera: the model is drawn from its URDF meshes
(models/so101).

Two views side by side, both to the same scale, with a grid in cm:
- **side**, in the arm's own plane (turned with shoulder_pan, so the arm is never seen end-on):
  across = reach from the base's turning axis, up = height above the table;
- **top**, seen from above with the arm's forward (x) up the picture and its left (y) to the left,
  as if standing behind the arm.

Marked on both: the gripper point (between the fingertips), the last move_to target, and any
`marks` the AI adds (e.g. where it thinks the cube is). Flat shading, painter's algorithm: crude
but plain, and fast enough without a GPU (a fraction of a second once the meshes are loaded).
"""

import functools
import io
import math
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lab_os.kinematics import SO101_URDF, Mat3, Vec3, _about, _mm, _mv, _rpy

URDFS = {"so101": SO101_URDF}  # arm model → URDF with meshes
CELL_M = 0.003  # meshes are simplified to a 3 mm grid (~300k triangles → a few thousand)
PANEL_W, PANEL_H = 500, 470
HEAD_H = 46
SIDE_RANGE = ((-15.0, 50.0), (-4.0, 50.0))  # cm: reach, height (grown to fit what's drawn)
TOP_RANGE = ((-40.0, 40.0), (-15.0, 50.0))  # cm: y (left → right on screen = +y → −y), x
MAX_MARKS = 10

BG = (250, 250, 247)
GRID = (222, 222, 216)
GRID_10 = (196, 196, 188)
TEXT = (40, 40, 40)
TABLE = (150, 120, 90)
PRINTED = (238, 196, 70)  # the 3D-printed parts
MOTOR = (70, 70, 76)  # the servos
TIP = (220, 30, 30)
TARGET = (190, 30, 190)
MARK = (0, 140, 170)


@dataclass(frozen=True)
class Part:
    link: str
    color: tuple[int, int, int]
    verts: tuple[Vec3, ...]  # in the link's frame (metres)
    tris: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class Joint:
    name: str
    parent: str
    child: str
    xyz: Vec3
    rot: Mat3
    axis: Vec3 | None


def _floats(s: str) -> tuple[float, ...]:
    return tuple(float(v) for v in s.split())


def _read_stl(path: Path) -> list[tuple[Vec3, Vec3, Vec3]]:
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:400]:  # ASCII STL
        nums = [
            _floats(line.split("vertex", 1)[1])
            for line in data.decode().splitlines()
            if "vertex" in line
        ]
        return [tuple(nums[i : i + 3]) for i in range(0, len(nums) - 2, 3)]
    (n,) = struct.unpack_from("<I", data, 80)
    out = []
    for rec in struct.iter_unpack("<12fH", data[84 : 84 + 50 * n]):
        out.append((rec[3:6], rec[6:9], rec[9:12]))
    return out


def _simplify(tris, rot: Mat3, xyz: Vec3) -> tuple[tuple[Vec3, ...], tuple]:
    """Move the triangles into the link's frame and merge vertices on a CELL_M grid (vertex
    clustering): small triangles collapse and are dropped, the shape stays."""
    index: dict[tuple[int, int, int], int] = {}
    sums: list[list[float]] = []
    faces = set()
    for tri in tris:
        ids = []
        for v in tri:
            p = _mv(rot, v)
            p = (p[0] + xyz[0], p[1] + xyz[1], p[2] + xyz[2])
            key = (round(p[0] / CELL_M), round(p[1] / CELL_M), round(p[2] / CELL_M))
            i = index.get(key)
            if i is None:
                i = index[key] = len(sums)
                sums.append([0.0, 0.0, 0.0, 0])
            s = sums[i]
            s[0] += p[0]
            s[1] += p[1]
            s[2] += p[2]
            s[3] += 1
            ids.append(i)
        if len(set(ids)) == 3:
            faces.add(tuple(ids))
    verts = tuple((s[0] / s[3], s[1] / s[3], s[2] / s[3]) for s in sums)
    return verts, tuple(faces)


@functools.cache
def load_model(urdf: Path) -> tuple[tuple[Part, ...], tuple[Joint, ...], str]:
    """The URDF's visual meshes (simplified) and joints. Slow-ish the first time (~1–2 s)."""
    root = ET.parse(urdf).getroot()
    parts = []
    for link in root.findall("link"):
        for vis in link.findall("visual"):
            mesh = vis.find("geometry/mesh")
            if mesh is None:
                continue
            o = vis.find("origin")
            xyz = _floats(o.get("xyz", "0 0 0")) if o is not None else (0.0, 0.0, 0.0)
            rpy = _floats(o.get("rpy", "0 0 0")) if o is not None else (0.0, 0.0, 0.0)
            mat = vis.find("material")
            color = MOTOR if mat is not None and "sts3215" in mat.get("name", "") else PRINTED
            verts, tris = _simplify(_read_stl(urdf.parent / mesh.get("filename")), _rpy(*rpy), xyz)
            parts.append(Part(link.get("name"), color, verts, tris))
    joints = []
    for j in root.findall("joint"):  # top level only: <transmission> has <joint> inside too
        o = j.find("origin")
        axis = j.find("axis")
        joints.append(
            Joint(
                j.get("name"),
                j.find("parent").get("link"),
                j.find("child").get("link"),
                _floats(o.get("xyz", "0 0 0")),
                _rpy(*_floats(o.get("rpy", "0 0 0"))),
                _floats(axis.get("xyz")) if j.get("type") != "fixed" and axis is not None else None,
            )
        )
    children = {j.child for j in joints}
    base = next(
        link.get("name") for link in root.findall("link") if link.get("name") not in children
    )
    return tuple(parts), tuple(joints), base


def link_frames(joints: tuple[Joint, ...], base: str, q: dict[str, float]) -> dict:
    """World position + rotation of every link for joint angles `q` (degrees)."""
    eye: Mat3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    frames = {base: ((0.0, 0.0, 0.0), eye)}
    pending = list(joints)
    while pending:
        rest = []
        for j in pending:
            if j.parent not in frames:
                rest.append(j)
                continue
            pos, rot = frames[j.parent]
            pos = tuple(p + d for p, d in zip(pos, _mv(rot, j.xyz), strict=True))
            rot = _mm(rot, j.rot)
            if j.axis is not None:
                rot = _mm(rot, _about(j.axis, math.radians(q.get(j.name, 0.0))))
            frames[j.child] = (pos, rot)
        if len(rest) == len(pending):
            break  # links not connected to the base: leave them out
        pending = rest
    return frames


@dataclass
class View:
    """An orthographic view: screen across = a·p, up = b·p, depth (far = big) = c·p (cm)."""

    title: str
    a: Vec3
    b: Vec3
    c: Vec3
    range_a: tuple[float, float]
    range_b: tuple[float, float]
    ox: int = 0  # the panel's left edge in the picture
    scale: float = 1.0
    a0: float = 0.0
    b1: float = 0.0

    def fit(self, scale: float) -> None:
        self.scale = scale
        mid_a = sum(self.range_a) / 2
        mid_b = sum(self.range_b) / 2
        self.a0 = mid_a - (PANEL_W - 20) / 2 / scale
        self.b1 = mid_b + (PANEL_H - HEAD_H - 20) / 2 / scale

    def dot(self, v: Vec3, p: Vec3) -> float:
        return v[0] * p[0] + v[1] * p[1] + v[2] * p[2]

    def px(self, p_cm: Vec3) -> tuple[float, float]:
        return self.px2(self.dot(self.a, p_cm), self.dot(self.b, p_cm))

    def px2(self, a: float, b: float) -> tuple[float, float]:
        return (self.ox + 10 + (a - self.a0) * self.scale, HEAD_H + 10 + (self.b1 - b) * self.scale)


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except (TypeError, OSError):  # Pillow without FreeType: the small bitmap font
        return ImageFont.load_default()


def _shade(color, normal: Vec3, toward: Vec3) -> tuple[int, int, int]:
    n = math.sqrt(sum(c * c for c in normal)) or 1.0
    lit = abs(sum(a * b for a, b in zip(normal, toward, strict=True))) / n
    k = 0.45 + 0.55 * lit
    return tuple(int(c * k) for c in color)


def _grid(d: ImageDraw.ImageDraw, v: View, font, label_a: str, label_b: str, flip_a=False) -> None:
    left, top = v.ox + 10, HEAD_H + 10
    right, bottom = v.ox + PANEL_W - 10, PANEL_H - 10
    a_lo, a_hi = v.a0, v.a0 + (right - left) / v.scale
    b_lo, b_hi = v.b1 - (bottom - top) / v.scale, v.b1
    for k in range(math.ceil(a_lo / 5), math.floor(a_hi / 5) + 1):
        x, _ = v.px2(k * 5, 0)
        d.line([(x, top), (x, bottom)], fill=GRID_10 if k % 2 == 0 else GRID)
        if k % 2 == 0 and x < right - 24:
            d.text((x + 2, bottom - 14), f"{-k * 5 if flip_a else k * 5:g}", fill=TEXT, font=font)
    for k in range(math.ceil(b_lo / 5), math.floor(b_hi / 5) + 1):
        _, y = v.px2(0, k * 5)
        d.line([(left, y), (right, y)], fill=GRID_10 if k % 2 == 0 else GRID)
        if k % 2 == 0 and y > top + 30:
            d.text((left + 2, y - 13), f"{k * 5:g}", fill=TEXT, font=font)
    d.text((right - 4, bottom - 28), label_a, fill=TEXT, font=font, anchor="ra")
    d.text((left + 2, top + 2), label_b, fill=TEXT, font=font)
    d.rectangle([left, top, right, bottom], outline=GRID_10)


def _cross(d, xy, r, color, width=2) -> None:
    x, y = xy
    d.line([(x - r, y - r), (x + r, y + r)], fill=color, width=width)
    d.line([(x - r, y + r), (x + r, y - r)], fill=color, width=width)


def render(
    model: str,
    joints: dict[str, float],
    tip_cm: Vec3,
    tool_angle_deg: float,
    target: tuple[Vec3, float] | None = None,
    marks: list[dict] | None = None,
    table_z_cm: float = 0.0,
) -> bytes:
    """The two views as a PNG. `marks`: [{"x_cm", "y_cm", "z_cm", "label"?, "size_cm"?}].
    Heights are from the table: the arm is drawn `-table_z_cm` higher (it stands on a plate)."""
    lift = -table_z_cm
    parts, urdf_joints, base = load_model(URDFS[model])
    frames = link_frames(urdf_joints, base, joints)
    pan = math.radians(joints.get("shoulder_pan", 0.0))
    u = (math.cos(pan), -math.sin(pan), 0.0)  # where the arm faces (+pan turns it to its right)
    w = (math.sin(pan), math.cos(pan), 0.0)  # the arm's left
    side = View(
        f"Side, in the arm's plane (pan {joints.get('shoulder_pan', 0.0):.0f}°)",
        u,
        (0.0, 0.0, 1.0),
        w,
        *SIDE_RANGE,
    )
    top = View(
        "Top, from above (behind the arm)",
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0, 0, -1.0),
        *TOP_RANGE,
    )
    marks = marks or []
    points = (
        [tip_cm]
        + ([target[0]] if target else [])
        + [(m["x_cm"], m["y_cm"], m["z_cm"]) for m in marks]
    )
    for v in (side, top):  # grow the ranges so every marked point is in the picture
        ra, rb = list(v.range_a), list(v.range_b)
        for p in points:
            pa, pb = v.dot(v.a, p), v.dot(v.b, p)
            ra = [min(ra[0], pa - 4), max(ra[1], pa + 4)]
            rb = [min(rb[0], pb - 4), max(rb[1], pb + 4)]
        v.range_a, v.range_b = tuple(ra), tuple(rb)
    scale = min(
        min((PANEL_W - 20) / (v.range_a[1] - v.range_a[0]) for v in (side, top)),
        min((PANEL_H - HEAD_H - 20) / (v.range_b[1] - v.range_b[0]) for v in (side, top)),
    )
    side.fit(scale)
    top.fit(scale)
    top.ox = PANEL_W

    img = Image.new("RGB", (PANEL_W * 2, PANEL_H), BG)
    d = ImageDraw.Draw(img)
    font, small = _font(14), _font(12)
    _grid(d, side, small, "reach from the base axis (cm)", "height (cm)")
    _grid(d, top, small, "left = +y, right = -y (cm)", "forward x (cm)", flip_a=True)

    # the table, in the side view
    tl, tr = side.px2(side.a0, 0), side.px2(side.a0 + (PANEL_W - 20) / scale, 0)
    d.rectangle([tl[0], tl[1], tr[0], PANEL_H - 10], fill=(232, 222, 208))
    d.line([tl, tr], fill=TABLE, width=2)
    if lift > 0:  # the plate the arm stands on (so101-white: the stand camera's base)
        a, b = side.px2(-7, lift), side.px2(7, 0)
        d.rectangle([a[0], a[1], b[0], b[1]], fill=(170, 170, 165), outline=TABLE)

    # the arm: every triangle into world cm, then drawn far to near in each view
    tris = []
    for part in parts:
        if part.link not in frames:
            continue
        pos, rot = frames[part.link]
        world = [
            tuple((pos[i] + r) * 100 + (lift if i == 2 else 0.0) for i, r in enumerate(_mv(rot, v)))
            for v in part.verts
        ]
        for i0, i1, i2 in part.tris:
            tris.append((world[i0], world[i1], world[i2], part.color))
    for v in (side, top):
        drawn = []
        for p0, p1, p2, color in tris:
            e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            normal = (
                e1[1] * e2[2] - e1[2] * e2[1],
                e1[2] * e2[0] - e1[0] * e2[2],
                e1[0] * e2[1] - e1[1] * e2[0],
            )
            depth = v.dot(v.c, p0) + v.dot(v.c, p1) + v.dot(v.c, p2)
            drawn.append((depth, (v.px(p0), v.px(p1), v.px(p2)), _shade(color, normal, v.c)))
        drawn.sort(key=lambda t: -t[0])
        for _, poly, color in drawn:
            d.polygon(poly, fill=color)
        # the base's turning axis
        d.ellipse(
            [*(c - 3 for c in v.px((0, 0, lift))), *(c + 3 for c in v.px((0, 0, lift)))],
            outline=TEXT,
        )

    # marks, target, gripper point (on top of the arm)
    for v in (side, top):
        for m in marks:
            p = (m["x_cm"], m["y_cm"], m["z_cm"])
            x, y = v.px(p)
            s = float(m.get("size_cm") or 0)
            if s > 0:
                h = s * scale / 2
                d.rectangle([x - h, y - h, x + h, y + h], outline=MARK, width=2)
            else:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=MARK, width=2)
            if m.get("label"):
                d.text((x + 8, y - 16), str(m["label"])[:30], fill=MARK, font=small)
        if target:
            _cross(d, v.px(target[0]), 7, TARGET)
        x, y = v.px(tip_cm)
        if v is side:  # a drop line to the table: how high is it?
            _, y0 = v.px((tip_cm[0], tip_cm[1], 0.0))
            for yy in range(int(y) + 6, int(y0), 6):
                d.line([(x, yy), (x, yy + 3)], fill=TIP)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=TIP)

    for v in (side, top):
        d.text((v.ox + 10, 6), v.title, fill=TEXT, font=font)
    d.text(
        (10, 26),
        f"dot: gripper point ({tip_cm[0]:.1f}, {tip_cm[1]:.1f}, {tip_cm[2]:.1f}) cm, "
        f"tool angle {tool_angle_deg:.0f}°",
        fill=TIP,
        font=small,
    )
    if target:
        (tx, ty, tz), ta = target
        d.text(
            (PANEL_W + 10, 26),
            f"x: last move_to target ({tx:.1f}, {ty:.1f}, {tz:.1f}) cm, {ta:.0f}°",
            fill=TARGET,
            font=small,
        )
    d.line([(PANEL_W, 0), (PANEL_W, PANEL_H)], fill=GRID_10)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
