"""Create placeholder PNGs for bots listed in custom_bot.json when asset files are missing."""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    raise SystemExit(
        "Pillow is required: pip install Pillow\n"
        "Then run from repo root: python scripts/gen_missing_bot_avatars.py\n"
        "Or from Golf_solver: python scripts/gen_missing_bot_avatars.py"
    ) from e

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "static" / "AI_bot_images"

# Filename must match custom_bot.json img_path basename
ASSETS: list[tuple[str, str, str, str]] = [
    ("hal_orderly.png", "H", "#2c3e50", "#ecf0f1"),
    ("chubbs_peterson.png", "C", "#1e4620", "#f4d03f"),
    ("grandma_gilmore.png", "G", "#6c3483", "#fdebd0"),
    ("donald_caddy.png", "D", "#5d4037", "#b3e5fc"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    size = 512
    for fname, letter, bg_hex, fg_hex in ASSETS:
        im = Image.new("RGB", (size, size), bg_hex)
        draw = ImageDraw.Draw(im)
        margin = size // 12
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            outline=fg_hex,
            width=max(4, size // 64),
        )
        try:
            font = ImageFont.truetype("arial.ttf", size // 2)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), letter, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (size - tw) // 2 - bbox[0]
        y = (size - th) // 2 - bbox[1]
        draw.text((x, y), letter, fill=fg_hex, font=font)
        path = OUT / fname
        im.save(path, format="PNG", optimize=True)
        print("wrote", path)


if __name__ == "__main__":
    main()
