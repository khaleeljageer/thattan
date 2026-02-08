"""Theme colors and color utilities for the UI."""


class HomeColors:
    """Light theme palette (ported from `test.py`)."""

    BG_TOP = "#e0f7fa"
    BG_MIDDLE = "#b2ebf2"
    BG_BOTTOM = "#80deea"

    PRIMARY = "#00838f"
    PRIMARY_LIGHT = "#4fb3bf"
    PRIMARY_DARK = "#005662"

    CORAL = "#ff8a65"
    AMBER = "#ffb74d"
    MINT = "#69f0ae"
    LAVENDER = "#b39ddb"

    CARD_BG = "rgba(255, 255, 255, 0.85)"
    CARD_BG_HOVER = "rgba(255, 255, 255, 0.95)"
    CARD_BORDER = "rgba(255, 255, 255, 0.6)"

    TEXT_PRIMARY = "#1a3a3a"
    TEXT_SECONDARY = "#4a6572"
    TEXT_MUTED = "#78909c"

    # Progress card (முன்னேற்றம்) – light glass bar
    PROGRESS_CARD_BG = "#f8fcfd"
    PROGRESS_TRACK = "#e6f0f0"
    PROGRESS_FILL = "#107878"
    PROGRESS_LABEL_MUTED = "#648282"


def blend_hex(a: str, b: str, t: float) -> str:
    """Blend two #RRGGBB colors. t=0 -> a, t=1 -> b."""
    try:
        a = a.strip()
        b = b.strip()
        if not (a.startswith("#") and b.startswith("#") and len(a) == 7 and len(b) == 7):
            return a
        t = max(0.0, min(1.0, float(t)))
        ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
        br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
        r = int(ar + (br - ar) * t)
        g = int(ag + (bg - ag) * t)
        bl = int(ab + (bb - ab) * t)
        return f"#{r:02X}{g:02X}{bl:02X}"
    except Exception:
        return a
