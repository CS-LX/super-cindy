"""Package the user-provided meme originals without redrawing their faces.

Requires Pillow, reportlab and ffmpeg. Run from any directory; --font may point at a CJK bold font.
Original JPEGs are copied byte-for-byte from the supplied reference document.
Only layout, proportional resizing, crop, and format conversion are performed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ORIGINALS = HERE / "originals"
DESKTOP = ROOT / "apps/desktop"
ART = DESKTOP / "src/renderer/assets"
MOBILE = ROOT / "apps/mobile/assets"
OUTPUTS: dict[str, dict] = {}
GALLERY = [
    "naiwa-standing", "naidan", "naiwa-laugh", "naiwa-thinking",
    "naiwa-peeking", "naiwa-surprised", "naiwa-crawling", "naiwa-stance",
    "nailong", "naigou", "naiji", "naicha", "naishu", "naicai",
    "nainiu", "naiwa-belly-laugh",
]
SKINS = dict(zip(
    ["cindy", "blackcat", "erika", "pululu", "tarara", "boli", "whitesnow", "annie", "chaku", "muffin"],
    ["naiwa-laugh", "naigou", "naishu", "naidan", "nailong", "naidan", "naiji", "naiwa-peeking", "naiwa-thinking", "naicha"],
))


def original(name: str) -> Image.Image:
    return Image.open(ORIGINALS / f"{name}.jpg").convert("RGB")


def fit(name: str, size: tuple[int, int], *, margin: float = 0) -> Image.Image:
    """Keep every feature and the entire source frame; never stretch a character."""
    im = original(name)
    target = (max(1, round(size[0] * (1 - margin * 2))), max(1, round(size[1] * (1 - margin * 2))))
    im = ImageOps.contain(im, target, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return canvas


def dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def record(path: Path, source: str) -> None:
    OUTPUTS[path.relative_to(ROOT).as_posix()] = {
        "source": source,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def save(im: Image.Image, path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    if ext == ".webp":
        im.save(path, lossless=True, method=6)
    elif ext in (".jpg", ".jpeg"):
        im.convert("RGB").save(path, quality=95, subsampling=0)
    else:
        im.save(path)
    record(path, source)


def replace(path: Path, name: str) -> None:
    save(fit(name, dimensions(path)), path, name)


def rounded_icon(size: tuple[int, int]) -> Image.Image:
    im = fit("naidan", size, margin=0.04).convert("RGBA")
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=size[0] * .21, fill=255)
    im.putalpha(mask)
    return im


def lettering(path: Path, text: str, font: str, light: bool) -> None:
    size = dimensions(path)
    im = Image.new("RGBA", size)
    draw = ImageDraw.Draw(im)
    point = size[1]
    while point > 1:
        face = ImageFont.truetype(font, point)
        box = draw.textbbox((0, 0), text, font=face)
        if box[2] - box[0] <= size[0] * .94 and box[3] - box[1] <= size[1] * .88:
            break
        point -= 1
    x = (size[0] - box[2] + box[0]) / 2 - box[0]
    y = (size[1] - box[3] + box[1]) / 2 - box[1]
    draw.text((x, y), text, font=face, fill="white" if light else "#202020")
    save(im, path, "typography: " + text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default="C:/Windows/Fonts/msyhbd.ttc")
    args = parser.parse_args()
    if not Path(args.font).is_file():
        raise SystemExit("Pass --font with a CJK bold TrueType/OpenType font.")

    # Existing IDs, names and asset URLs stay stable so saved preferences still resolve.
    for path in [DESKTOP / "resources/companion-preset-avatars/cindy.png", ART / "bot-presets/cindy.png", MOBILE / "bot-presets/cindy.png"]:
        replace(path, "naiwa-laugh")
    for name, character in [("dash", "naidan"), ("lizi", "nailong")]:
        replace(DESKTOP / f"resources/legacy-teammate-avatars/{name}.png", character)
        replace(MOBILE / f"bot-presets/{name}.png", character)

    for path in [ART / "cindy-avatar-account.png", ART / "cindy-avatar-lockup.png", ART / "head-image-dark.png", ART / "head-image-light.png"]:
        replace(path, "naiwa-laugh")
    for path in [ART / "cindy-share-character.jpg", MOBILE / "share/cindy-share-character.jpg"]:
        replace(path, "naiwa-stance")

    gallery = Image.new("RGB", (1024, 1024), "white")
    mobile_portraits = []
    for index, name in enumerate(GALLERY):
        portrait = fit(name, (256, 256))
        gallery.paste(portrait, ((index % 4) * 256, (index // 4) * 256))
        # Mobile's existing gallery is an array of base64 JPEG payloads.
        jpeg = io.BytesIO()
        portrait.save(jpeg, format="JPEG", quality=95, subsampling=0)
        mobile_portraits.append(base64.b64encode(jpeg.getvalue()).decode("ascii"))
    save(gallery, DESKTOP / "resources/teammate-portrait-gallery.png", ", ".join(GALLERY))
    path = MOBILE / "bot-presets/portrait-gallery.json"
    path.write_text(json.dumps(mobile_portraits, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    record(path, ", ".join(GALLERY))

    # Bundled package avatars have a byte-integrity contract; update only their art metadata/hash.
    for index, path in enumerate(sorted((DESKTOP / "resources/bot-packages").glob("*/*/assets/avatar.webp"))):
        name = GALLERY[index % len(GALLERY)]
        replace(path, name)
        manifest_path = path.parent.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["integrity"]["files"]["assets/avatar.webp"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["presentation"]["avatar"]["rights"] = {
            "kind": "user-provided",
            "source": f"Meme reference supplied by the fork owner; {name}; see scripts/meme-assets/SOURCES.json",
            "permissionEvidence": "Fork owner explicitly requested using these original reference images for this personal build on 2026-11-02; no claim of original authorship or general redistribution license.",
            "review": "PENDING",
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")

    icons = [DESKTOP / f"resources/{name}" for name in ["icon-dock.png", "icon-master-1024.png", "icon.icns"]]
    icons += [MOBILE / name for name in ["icon.png", "favicon.png", "splash-icon.png", "android-icon-foreground.png"]]
    for path in icons:
        save(rounded_icon(dimensions(path)), path, "naidan")
    # Use the existing Windows encoder for all seven 32-bit BMP frames and their
    # transparency masks. Pillow's default PNG-in-ICO output changes that contract.
    subprocess.run(["node", str(DESKTOP / "scripts/generate-win-ico.mjs")], check=True)
    for directory in [DESKTOP / "resources", DESKTOP / "cindy-updater/src-tauri/icons"]:
        for ext in ["png", "ico"]:
            record(directory / f"icon.{ext}", "naidan")
    # The OS's monochrome icon uses the egg's actual silhouette, without a solid square.
    monochrome = MOBILE / "android-icon-monochrome.png"
    icon = fit("naidan", dimensions(monochrome), margin=.18)
    mask = Image.new("L", icon.size)
    mask.putdata([255 if r > 100 and r > b * 1.4 and g > b * 1.2 else 0 for r, g, b in icon.getdata()])
    # Fill interior facial features; only the outside silhouette belongs to a monochrome icon.
    flood = mask.copy(); ImageDraw.floodfill(flood, (0, 0), 128)
    mask.putdata([0 if pixel == 128 else 255 for pixel in flood.getdata()])
    ink = Image.new("RGBA", icon.size, "black")
    ink.putalpha(mask)
    save(ink, monochrome, "naidan icon silhouette")
    # Trace the original silhouette for tiny template icons, including native widgets.
    # No invented features: every left/right point comes from the same source mask.
    outline = mask.resize((96, 96), Image.Resampling.NEAREST)
    left, right = [], []
    for y in range(96):
        xs = [x for x in range(96) if outline.getpixel((x, y)) > 127]
        if xs:
            left.append((min(xs) / 4, y / 4))
            right.append((max(xs) / 4, y / 4))
    points = left + list(reversed(right))
    vector = "M " + " L ".join(f"{x:g},{y:g}" for x, y in points) + " Z"
    shared_mark = ROOT / "packages/model-providers/src/cindyMark.ts"
    shared_mark.write_text(
        '/** Naidan silhouette traced from the unchanged reference; see scripts/meme-assets. */\n'
        'export const CINDY_MARK_TRANSFORM = "";\n'
        f'export const CINDY_MARK_PATH = "{vector}";\n'
        'export const CINDY_MARK_EARRING_PATH = "";\n'
        'export const CINDY_MARK_EARRING_COLOR = "currentColor";\n',
        encoding="utf-8", newline="\n",
    )
    widget = ROOT / "apps/mobile/plugins/usage-widgets/Assets.xcassets/logo-cindy.imageset/logo-cindy.svg"
    widget.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="#000" d="{vector}"/></svg>\n',
        encoding="utf-8", newline="\n",
    )
    record(widget, "naidan icon silhouette")
    android = ROOT / "apps/mobile/modules/cindy-usage-widgets/android/src/main/java/app/cindy/usagewidgets/WidgetLogos.kt"
    android.write_text(re.sub(r'"cindy" to "[^"]*"', f'"cindy" to "{vector}"', android.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    menubar = DESKTOP / "native/menubar/macos-menubar-helper.swift"
    swift = re.sub(r'let cindySilhouettePath = "[^"]*"', f'let cindySilhouettePath = "{vector}"', menubar.read_text(encoding="utf-8"))
    swift = re.sub(r'let cindyMarkPath = cindySilhouettePath[^\n]*', 'let cindyMarkPath = cindySilhouettePath', swift)
    swift = swift.replace('// The Cindy "A" mark from the brand kit (24pt viewBox, 20pt ink, even-odd `>` cut-out).', '// Naidan silhouette traced from the original reference (24pt viewBox).')
    menubar.write_text(swift, encoding="utf-8", newline="\n")
    for path in [DESKTOP / "resources/macicon.jpg", DESKTOP / "resources/bgicon.jpg", MOBILE / "update/app-icon.jpg"]:
        replace(path, "naidan")

    for path in [ART / "login/hero.png", ART / "login/hero@2x.png", ART / "splash/illustration.webp"]:
        replace(path, "naiwa-belly-laugh")
    for path in (MOBILE / "login").glob("*hero*.png"):
        replace(path, "naiwa-belly-laugh")
    for path in (MOBILE / "splash").glob("*illustration*.webp"):
        replace(path, "naiwa-belly-laugh")
    for path in (ART / "login/chibi").glob("*.png"):
        name = "naiwa-surprised" if "failure" in path.name else "naiwa-laugh" if "success" in path.name else "naiwa-thinking"
        replace(path, name)

    for directory in [ART, ART / "login", ART / "splash", MOBILE / "login", MOBILE / "splash"]:
        for path in directory.glob("*.png"):
            if any(word in path.name for word in ["logo-", "wordmark", "slogan", "script"]):
                slogan = "slogan" in path.name or "script" in path.name
                light = "dark" in path.name or "white" in path.name
                if directory.name == "splash" and path.name in ["wordmark.png", "script.png"]:
                    light = True
                lettering(path, "捧腹大笑" if slogan else "奶蛙", args.font, light)

    for skin, name in SKINS.items():
        if skin == "pululu":
            # The renderer keeps its existing SVG URL, now containing the unchanged egg portrait.
            portrait = fit(name, (128, 128))
            data = io.BytesIO(); portrait.save(data, format="PNG")
            path = ART / "agent-island-pululu.svg"
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><image width="128" height="128" href="data:image/png;base64,' + base64.b64encode(data.getvalue()).decode("ascii") + '"/></svg>\n', encoding="utf-8", newline="\n")
            record(path, name)
        else:
            replace(ART / f"agent-island-{skin}.png", name)
            replace(DESKTOP / f"native/agent-island/mascots/{skin}.png", name)

    wallpaper_names = dict(zip(
        ["cindy-window", "cindy-studio", "cindy-dream", "cindy-whisper", "cindy-scarlet-stroll", "cindy-prism", "cindy-night-glance", "cindy-neon"],
        ["naiwa-peeking", "naiwa-thinking", "naidan", "naiwa-laugh", "naiwa-stance", "naiji", "naicha", "naishu"],
    ))
    for path in (ART / "wallpapers").rglob("*.webp"):
        if path.stem in wallpaper_names:
            replace(path, wallpaper_names[path.stem])
    manifest_path = DESKTOP / "src/shared/wallpaper-video-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for stem in wallpaper_names:
        path = ART / f"wallpapers/{stem}.webp"
        manifest[stem] = {"delivery": "bundled", "image": {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
        }}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    # Video wallpaper IDs were already retired upstream. Still replace their legacy payloads
    # so an old saved URL or a future re-enable cannot reveal the original Cindy artwork.
    for stem in ["cindy-window", "cindy-studio", "cindy-dream"]:
        path = ART / f"wallpapers/{stem}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(path.with_suffix(".webp")), "-t", "2", "-vf", "scale=1280:800", "-r", "12", "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)], check=True)
        record(path, wallpaper_names[stem] + " (still video, no character animation)")

    # Finder's PDF background shares the fork's splash art, including on a Windows rebuild.
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    path = DESKTOP / "resources/dmg/background.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(900, 610), invariant=1)
    pdf.setTitle("Naiwa meme edition installer")
    pdf.setFillColorRGB(.97, .97, .95); pdf.rect(0, 0, 900, 610, fill=1, stroke=0)
    pdf.drawImage(ImageReader(ART / "splash/illustration.webp"), 220, 377, 220, 220, preserveAspectRatio=True, mask="auto")
    pdf.drawImage(ImageReader(ART / "splash/wordmark-light.png"), 265, 350, 130, 44, mask="auto")
    pdf.setStrokeColorRGB(.4, .4, .4); pdf.setLineWidth(3)
    pdf.line(292, 275, 368, 275); pdf.line(355, 285, 368, 275); pdf.line(355, 265, 368, 275)
    pdf.showPage(); pdf.save()
    record(path, "naiwa-belly-laugh + fork typography")

    (HERE / "outputs.json").write_text(json.dumps(OUTPUTS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Packaged {len(OUTPUTS)} assets using unchanged meme originals.")


if __name__ == "__main__":
    main()
