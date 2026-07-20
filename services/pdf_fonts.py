"""Register Unicode-capable fonts for ReportLab clinic PDFs (French accents)."""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_REGISTERED = False
FONT_REGULAR = "ClinicSans"
FONT_BOLD = "ClinicSans-Bold"

_CANDIDATES = [
    (
        Path(__file__).resolve().parent.parent / "assets" / "fonts" / "DejaVuSans.ttf",
        Path(__file__).resolve().parent.parent / "assets" / "fonts" / "DejaVuSans-Bold.ttf",
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ),
]


def ensure_clinic_fonts() -> tuple[str, str]:
    """Return (regular, bold) font names; fall back to Helvetica if no TTF found."""
    global _REGISTERED
    if _REGISTERED:
        return FONT_REGULAR, FONT_BOLD
    for regular_path, bold_path in _CANDIDATES:
        if regular_path.is_file() and bold_path.is_file():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
            _REGISTERED = True
            return FONT_REGULAR, FONT_BOLD
    _REGISTERED = True
    return "Helvetica", "Helvetica-Bold"
