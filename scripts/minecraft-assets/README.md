# Private Minecraft appearance

The fork owner's 2026-11-19 request adds a **Minecraft / 我的世界** appearance while
retaining the Naiwa artwork. It uses **original Java Edition game resources**, not
redrawn textures or AI illustrations. The existing icons are retained. Filled
buttons use Minecraft's normal/highlighted/disabled sprites; bare icon buttons
stay flat and transparent. Panels, fields, checkboxes and slider handles use the
corresponding original textures. Text uses the original bitmap glyphs and the
game's hard, offset shadow.

## Prepare resources locally

Only the integration code is in Git. Game images and converted fonts are private
build inputs under `apps/desktop/src/renderer/assets/minecraft-local/`, which is
gitignored. They are **not for redistribution**. No resource download or image
generation is performed by the importer or at application runtime.

Using an existing Java Edition **1.21.4** installation (asset index **19**):

```sh
python -m pip install "fonttools[woff]" Pillow
python scripts/minecraft-assets/prepare.py --jar "<game>/versions/<version>/<version>.jar" --assets "<game>/assets" --index 19
```

The importer copies PNG bytes unchanged, consumes the game's `.mcmeta` nine-slice
rules, and verifies asset-index SHA-1 hashes. `provenance.json` records the JAR and
texture hashes without local paths. Font conversion traces opaque pixel runs
from `font/include/default.json` and the asset index's `unifont.zip`; it preserves
the glyph pixels, ascent and advance rules. Unicode BMP ranges are split into
small webfonts to bound conversion memory and load only needed ranges. Characters
outside the BMP use the system fallback. The Unifont license travels with the
private inputs.

The appearance picker only offers this skin in builds with prepared resources.
The theme is dark-only, like the game menus; selecting another theme restores its
geometry and typography. Existing theme preferences, explicit custom fonts,
wallpaper, avatar and user data are not rewritten. Terminal/code fonts retain
their existing preferences. Build and validate normally after preparing assets;
do not publish a package containing the private game inputs.

## References and implementation

- [PrismarineJS web client](https://github.com/PrismarineJS/prismarine-web-client),
  particularly its original-texture button rendering in
  `lib/menus/components/button.js`, was inspected as an open-source reference.
- The texture sources and stretch rules come from the local official game JAR,
  not from community redrawn packs. Minecraft itself is not treated as an
  open-source artwork library.
- Palette source: `packages/design-tokens/src/reference/themes.json` and
  `src/themes/builtin.json`; generated adapter: `themes/builtin/minecraft.ts`.
- Texture-backed rendering: `renderer/styles/minecraft.css`; private import:
  `renderer/themes/minecraft-assets.ts`. The `data-theme='minecraft'` scope also
  reaches portals without modifying other themes or embedded third-party pages.

The fork owner's opt-in skin explicitly supersedes the default Inter/pill/no-shadow
treatment in `docs/design-rules/DESIGN.md` §§1, 3–7 for this theme only. Keyboard,
disabled states, hit targets, accessible names, status colours and user preferences
keep their existing contracts. This does not change upstream Cindy's default
design or imply upstream design approval.
