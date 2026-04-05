"""Generate a GitHub social preview image (1280x640px) for paperflow.

Usage:
    python -m scripts.gen_preview
    # Output: static/social_preview.png

Then upload to: GitHub repo → Settings → Social preview
"""

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow not installed. Run: pip install Pillow")

BG = "#0d1117"
FG = "#e6edf3"
ACCENT = "#58a6ff"
DIM = "#8b949e"

W, H = 1280, 640
PAD = 80

DIAGRAM = """\
[arXiv] ──fetch──▶ [Candidates] ──batch──▶ [NotebookLM]
                        │                        │
                   review & score          trend analysis
                        │                        │
                   [Key Papers] ◀────── identify ┘
                        │
                   discuss with LLM
                        │
                   [paperflow notes]  ◀── the step that matters\
"""


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a monospace font, fall back to default."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate(output_path: Path = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).resolve().parent.parent / "static" / "social_preview.png"

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Name
    font_name = _font(72, bold=True)
    draw.text((PAD, PAD), "paperflow", fill=ACCENT, font=font_name)

    # Tagline
    font_tag = _font(28)
    draw.text((PAD, PAD + 90), "Read less. Know more. Write what matters.", fill=FG, font=font_tag)

    # Divider
    draw.line([(PAD, PAD + 140), (W - PAD, PAD + 140)], fill="#30363d", width=1)

    # Diagram
    font_mono = _font(20)
    y = PAD + 165
    for line in DIAGRAM.splitlines():
        color = ACCENT if "◀── the step that matters" in line else FG
        draw.text((PAD, y), line, fill=color, font=font_mono)
        y += 34

    # Footer
    font_footer = _font(20)
    draw.text((PAD, H - PAD - 10), "github.com/sherrymao/paperflow", fill=DIM, font=font_footer)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    print(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    generate()
