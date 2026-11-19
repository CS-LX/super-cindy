"""Prepare a private Minecraft skin from an existing Java Edition installation.

No network access, image drawing, recolouring or atlas composition. PNG files are
copied byte for byte. The font converter traces the original opaque pixel runs
into a webfont; it does not substitute or design glyphs. Generated files MUST NOT
be committed or distributed with the public fork.
Requires: python -m pip install fonttools[woff] Pillow
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "apps/desktop/src/renderer/assets/minecraft-local"
TEXTURES = {
    "button": "sprites/widget/button.png",
    "button-hover": "sprites/widget/button_highlighted.png",
    "button-disabled": "sprites/widget/button_disabled.png",
    "field": "sprites/widget/text_field.png",
    "field-focus": "sprites/widget/text_field_highlighted.png",
    "panel": "sprites/popup/background.png",
    "tooltip": "sprites/tooltip/background.png",
    "slider": "sprites/widget/slider.png",
    "slider-handle": "sprites/widget/slider_handle.png",
    "slider-handle-hover": "sprites/widget/slider_handle_highlighted.png",
    "checkbox": "sprites/widget/checkbox.png",
    "checkbox-on": "sprites/widget/checkbox_selected.png",
    "checkbox-hover": "sprites/widget/checkbox_highlighted.png",
    "checkbox-on-hover": "sprites/widget/checkbox_selected_highlighted.png",
    "scroller": "sprites/widget/scroller.png",
    "menu": "menu_background.png",
}


def read_json(data: bytes):
    # Mojang's asset-index font override has a trailing comma in __ranges.
    return json.loads(re.sub(r",\s*([}\]])", r"\1", data.decode("utf-8")))


def glyph(rows: list[list[bool]], scale: int, ascent: int, left: int = 0):
    pen = TTGlyphPen(None)
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if not row[x]:
                x += 1
                continue
            start = x
            while x < len(row) and row[x]:
                x += 1
            x0, x1 = (start - left) * scale, (x - left) * scale
            y0, y1 = (ascent - y - 1) * scale, (ascent - y) * scale
            pen.moveTo((x0, y0))
            pen.lineTo((x0, y1))
            pen.lineTo((x1, y1))
            pen.lineTo((x1, y0))
            pen.closePath()
    return pen.glyph()


def save_font(name: str, items: dict, output: Path):
    # Fixed time keeps repeated imports byte-identical.
    font = FontBuilder(1024, isTTF=True)
    order = [".notdef"] + [f"u{cp:04X}" for cp in sorted(items)]
    font.setupGlyphOrder(order)
    font.setupCharacterMap({cp: f"u{cp:04X}" for cp in items})
    font.setupGlyf({".notdef": TTGlyphPen(None).glyph(), **{
        f"u{cp:04X}": value[0] for cp, value in items.items()
    }})
    font.setupHorizontalMetrics({".notdef": (512, 0), **{
        f"u{cp:04X}": (value[1], 0) for cp, value in items.items()
    }})
    font.setupHorizontalHeader(ascent=896, descent=-256, lineGap=0)
    font.setupNameTable({
        "familyName": name, "styleName": "Regular", "fullName": name,
        "psName": name.replace(" ", ""), "uniqueFontIdentifier": name + "-local-v1",
        "version": "Version 1.000", "copyright": "Converted from the user's local Minecraft game resources. Not for redistribution.",
    })
    font.setupOS2(sTypoAscender=896, sTypoDescender=-256, sTypoLineGap=0,
                 usWinAscent=1408, usWinDescent=384)
    font.setupPost()
    font.setupMaxp()
    font.font['head'].created = font.font['head'].modified = 2082844800
    font.font.recalcTimestamp = False
    font.font.flavor = "woff2"
    font.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--index", default="19", help="Java 1.21.4 uses asset index 19")
    args = parser.parse_args()
    index = read_json((args.assets / "indexes" / f"{args.index}.json").read_bytes())["objects"]
    evidence = {"jarSha1": hashlib.sha1(args.jar.read_bytes()).hexdigest(), "assetIndex": args.index, "textures": {}, "fonts": {}}

    def asset(name: str):
        info = index[name]
        data = (args.assets / "objects" / info["hash"][:2] / info["hash"]).read_bytes()
        if hashlib.sha1(data).hexdigest() != info["hash"]:
            raise ValueError(f"Game asset hash mismatch: {name}")
        evidence["fonts"][name] = info["hash"]
        return data

    with zipfile.ZipFile(args.jar) as jar:
        # Validate every required texture before writing anything.
        files = {key: jar.read("assets/minecraft/textures/gui/" + path) for key, path in TEXTURES.items()}
        OUTPUT.mkdir(parents=True, exist_ok=True)
        css = ["/* Generated from local game resources. Do not commit or redistribute. */"]
        declarations = []
        for key, data in files.items():
            filename = f"{key}.png"
            (OUTPUT / filename).write_bytes(data)
            evidence["textures"][filename] = {"source": TEXTURES[key], "sha256": hashlib.sha256(data).hexdigest()}
            declarations.append(f"  --mc-{key}-image: url('./{filename}');")
            meta_path = "assets/minecraft/textures/gui/" + TEXTURES[key] + ".mcmeta"
            if meta_path in jar.namelist():
                # CSS border-image is the browser's native nine-slice renderer.
                meta = read_json(jar.read(meta_path))["gui"]["scaling"]
                border = meta.get("border", 0)
                if isinstance(border, dict):
                    border = ' '.join(str(border[side]) for side in ['top', 'right', 'bottom', 'left'])
                declarations.append(f"  --mc-{key}-slice: {border};")

        latin = {}
        providers = read_json(jar.read("assets/minecraft/font/include/default.json"))["providers"]
        for provider in providers:
            if provider["type"] != "bitmap":
                continue
            source = "assets/" + provider["file"].replace(":", "/textures/", 1)
            bitmap = Image.open(io.BytesIO(jar.read(source))).convert("RGBA")
            chars = provider["chars"]
            width, height = bitmap.width // len(chars[0]), bitmap.height // len(chars)
            scale = round(128 * provider.get("height", 8) / height)
            ascent = round(provider["ascent"] * 128 / scale)
            for y, row in enumerate(chars):
                for x, char in enumerate(row):
                    cp = ord(char)
                    if cp == 0 or cp in latin:
                        continue
                    rows = [[bitmap.getpixel((x * width + dx, y * height + dy))[3] > 0
                             for dx in range(width)] for dy in range(height)]
                    right = max((dx for row_pixels in rows for dx, on in enumerate(row_pixels) if on), default=-1)
                    latin[cp] = (glyph(rows, scale, ascent), (right + 1) * scale + 128)
        spaces = read_json(jar.read("assets/minecraft/font/include/space.json"))["providers"][0]["advances"]
        for char, advance in spaces.items():
            latin[ord(char)] = (TTGlyphPen(None).glyph(), round(advance * 128))
        save_font("Minecraft Game Latin", latin, OUTPUT / "minecraft-latin.woff2")

    unicode_items = {}
    unicode_count = 0
    unicode_block = None
    unicode_faces = []

    def flush_unicode():
        if not unicode_items:
            return
        start = min(unicode_items)
        end = max(unicode_items)
        filename = f"minecraft-unicode-{start:04x}.woff2"
        save_font("Minecraft Game Unicode", unicode_items, OUTPUT / filename)
        unicode_faces.append(
            "@font-face { font-family: 'Minecraft Game Unicode'; "
            f"src: url('./{filename}') format('woff2'); "
            "font-weight: 100 900; font-style: normal; font-display: swap; "
            f"unicode-range: U+{start:04X}-{end:04X}; }}"
        )
        unicode_items.clear()

    provider = next(p for p in read_json(asset("minecraft/font/include/unifont.json"))["providers"]
                    if p.get("hex_file") == "minecraft:font/unifont.zip")
    with zipfile.ZipFile(io.BytesIO(asset("minecraft/font/unifont.zip"))) as archive:
        for name in archive.namelist():
            if not name.endswith('.hex'):
                continue
            for line in archive.read(name).decode('ascii').splitlines():
                code, bits = line.split(':')
                cp = int(code, 16)
                # A webfont is limited to 65535 glyphs. BMP includes CJK, kana,
                # Hangul and UI punctuation; supplementary glyphs use system fallback.
                if cp > 0xFFFF or 0xD800 <= cp <= 0xDFFF:
                    continue
                # Subset by Unicode block without changing any glyph. Bound the
                # conversion's memory and only load glyph ranges used on screen.
                block = cp // 512
                if block != unicode_block:
                    flush_unicode()
                    unicode_block = block
                width = len(bits) // 4
                rows = [[bool(int(bits[y * width // 4:(y + 1) * width // 4], 16) & (1 << (width - x - 1)))
                         for x in range(width)] for y in range(16)]
                columns = [x for row in rows for x, on in enumerate(row) if on]
                left, right = (min(columns), max(columns)) if columns else (0, width - 1)
                for override in provider.get('size_overrides', []):
                    if ord(override['from']) <= cp <= ord(override['to']):
                        left, right = override['left'], override['right']
                        break
                # Minecraft unihex glyphs are 16px tall rendered at 8 game pixels.
                unicode_items[cp] = (glyph(rows, 64, 14, left), (right - left + 1) * 64 + 128)
                unicode_count += 1
        if 'LICENSE.txt' in archive.namelist():
            (OUTPUT / 'UNICODE-LICENSE.txt').write_bytes(archive.read('LICENSE.txt'))
    flush_unicode()
    css.extend(unicode_faces)
    for family, filename in [("Minecraft Game Latin", "minecraft-latin")]:
        css.append(f"@font-face {{ font-family: '{family}'; src: url('./{filename}.woff2') format('woff2'); font-weight: 100 900; font-style: normal; font-display: swap; }}")
    css.append(":root[data-theme='minecraft'] {\n" + '\n'.join(declarations) + "\n}")
    (OUTPUT / 'minecraft-assets.css').write_text('\n'.join(css) + '\n', encoding='utf-8')
    evidence['glyphs'] = {'latin': len(latin), 'unicodeBmp': unicode_count}
    (OUTPUT / 'provenance.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(OUTPUT), 'copiedTextures': len(files), **evidence['glyphs']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
