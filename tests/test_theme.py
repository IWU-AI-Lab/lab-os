import re

from lab_os.theme import load_theme

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _colors(node, path=""):
    for key, value in node.items():
        if isinstance(value, dict):
            yield from _colors(value, f"{path}{key}.")
        else:
            yield f"{path}{key}", value


def test_theme_has_starter_tokens():
    t = load_theme()
    for key in ("background", "text", "primary", "accent", "ok", "text_dim"):
        assert key in t["colors"], key
    assert t["font"]["family"]
    assert t["font"]["base_size_px"] > 0


def test_every_color_token_is_hex():
    t = load_theme()
    for section in ("colors", "arm3d"):
        for path, value in _colors(t[section], f"{section}."):
            assert HEX.match(value), f"{path} = {value!r}"


def test_tokens_used_by_the_3d_views_exist():
    """Every color() path in the web code must exist in theme.yaml."""
    from lab_os.teleop.server import WEB_DIR

    t = load_theme()
    used = set()
    for js in WEB_DIR.rglob("*.js"):
        if "vendor" in js.parts:
            continue
        used |= set(re.findall(r'color\("([a-z0-9_.]+)"\)', js.read_text()))
        used |= {
            f"arm3d.xarm.{p}"
            for p in re.findall(r'"(metal|servo|plate|cup|board)"', js.read_text())
        }
    assert used, "no color() calls found"
    for path in used:
        node = t
        for key in path.split("."):
            assert key in node, f"{path} missing from config/theme.yaml"
            node = node[key]
