#!/usr/bin/env python3
"""Generate the site's icons from the brand artwork.

    pip install pillow
    python3 tools/make_icons.py

Run it when either source in `brand/` changes; the results are committed, so
nothing else needs an image library.

There are two sources and they do different jobs.

`brand/wordmark.jpg` is the wide mark — "DDB" over "ddb-learn-online". It is
the site's own logo and appears on the front page, which is the only page that
belongs to the whole site rather than to one subject. It arrives on white, and
is cut out here so it does not render as a glaring slab on the dark palette.

`brand/appicon.jpg` is the square mark, drawn as an app icon and used as one at
512, 192 and 180 pixels.

Neither survives being shrunk to a favicon. At 32px the square mark is three
coloured smudges and at 16px it is a single muddy square, so those two sizes
are drawn here instead: one bold D in the brand's yellow on the brand's navy.
It is the same two colours and the same first letter, which is as much as 16
pixels can carry.

The Italian course keeps its own mark at `public/logo.png`, used on its own
contents page. That one says "GCSE Italian" on its face and belongs to the
course, not the site.
"""
import pathlib
import sys

try:
    from PIL import Image, ImageChops, ImageDraw
except ImportError:
    sys.exit("This needs Pillow: pip install pillow")

REPO = pathlib.Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
# The artwork lives outside public/: it is the source the icons are cut from,
# not something the site serves.
BRAND = REPO / "brand"
WORDMARK = BRAND / "wordmark.jpg"
APPICON = BRAND / "appicon.jpg"

# Sampled from the artwork rather than guessed, so the drawn favicon and the
# real icon are the same two colours.
NAVY = (0x02, 0x12, 0x29)
YELLOW = (0xFE, 0xD6, 0x02)

FROM_ICON = {"icon-512.png": 512, "icon-192.png": 192, "apple-touch-icon.png": 180}
DRAWN = {"favicon-32.png": 32, "favicon-16.png": 16}

# How wide the wordmark is drawn in the masthead. The file is twice this, for
# the screens that want it.
LOGO_WIDTH = 300


def quantise(im: Image.Image, colors: int = 128, dither: bool = True) -> Image.Image:
    """Down to a fixed palette, keeping any transparency.

    Spray texture is all gradient, so a full-colour PNG of it is enormous and
    looks identical to a quantised one at the sizes anybody sees.
    """
    if im.mode == "RGBA":
        alpha = im.getchannel("A")
        flat = im.convert("RGB").quantize(
            colors=colors, method=Image.FASTOCTREE,
            dither=Image.FLOYDSTEINBERG if dither else Image.NONE)
        flat = flat.convert("RGBA")
        flat.putalpha(alpha)
        return flat
    return im.quantize(colors=colors, method=Image.FASTOCTREE,
                       dither=Image.FLOYDSTEINBERG if dither else Image.NONE)


def transparent(im: Image.Image) -> Image.Image:
    """Cut the flat white from around the mark.

    Fills inward from the border and stops where the artwork starts. The
    wordmark's own white — the lettering, the crown — is enclosed by dark
    strokes, so the fill never reaches it, which is why this is done by
    flooding rather than by colour alone.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    stack = [(x, y) for x in range(w) for y in (0, h - 1)]
    stack += [(x, y) for y in range(h) for x in (0, w - 1)]

    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or seen[y][x]:
            continue
        r, g, b, _ = px[x, y]
        if min(r, g, b) < 225:              # reached the artwork
            continue
        seen[y][x] = True
        px[x, y] = (r, g, b, 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return im


def letter_d(size: int) -> Image.Image:
    """A bold D filling the frame, yellow on navy.

    Drawn rather than typeset, so it does not depend on a font being
    installed, and built out of two masks rather than painted in layers — the
    first attempt drew the bowl over the stem and then squared off the left
    edge, which erased the stem and left something that read as a C.

    A D is a shape with a straight left edge and a round right one: an ellipse
    with its left half squared off. The counter inside is the same shape,
    inset, and subtracted.
    """
    scale = 8                              # draw large, shrink for clean edges
    s = size * scale
    pad = s * 0.16
    top, bottom = pad, s - pad
    left, right = s * 0.22, s - pad * 0.85
    stroke = (bottom - top) * 0.27         # how thick the letter is

    def d_shape(l: float, t: float, r: float, b: float) -> Image.Image:
        """A filled D: an ellipse with its left half squared off."""
        m = Image.new("L", (s, s), 0)
        draw = ImageDraw.Draw(m)
        draw.ellipse([l, t, r, b], fill=255)
        draw.rectangle([l, t, (l + r) / 2, b], fill=255)
        return m

    outer = d_shape(left, top, right, bottom)
    counter = d_shape(left + stroke, top + stroke, right - stroke, bottom - stroke)
    # The counter is a hole, so take it out of the outer shape.
    mask = ImageChops.subtract(outer, counter)

    im = Image.new("RGB", (s, s), NAVY)
    im.paste(Image.new("RGB", (s, s), YELLOW), (0, 0), mask)
    return im.resize((size, size), Image.LANCZOS)


def main() -> int:
    for src in (WORDMARK, APPICON):
        if not src.exists():
            sys.exit(f"No artwork at {src.relative_to(REPO)}")

    # The site logo, cut out of its white background. Sized for twice the
    # width it is drawn at, and quantised: this is spray-paint texture, where
    # a hundred-odd colours is invisible and the difference between half a
    # megabyte and forty kilobytes on the page everybody loads first.
    mark = transparent(Image.open(WORDMARK))
    mark.thumbnail((LOGO_WIDTH * 2, LOGO_WIDTH * 2), Image.LANCZOS)
    mark = quantise(mark, colors=48, dither=False)
    mark.save(PUBLIC / "logo-site.png", optimize=True)
    kb = (PUBLIC / "logo-site.png").stat().st_size / 1024
    print(f"  {'logo-site.png':22} {mark.size[0]}x{mark.size[1]}  wordmark, cut out   {kb:.0f} KB")

    icon = Image.open(APPICON).convert("RGB")
    for name, size in FROM_ICON.items():
        # A home-screen icon is masked to a rounded square, so it wants a full
        # bleed rather than transparency.
        flat = quantise(icon.resize((size, size), Image.LANCZOS))
        flat.save(PUBLIC / name, optimize=True)
        kb = (PUBLIC / name).stat().st_size / 1024
        print(f"  {name:22} {size}x{size}  from the app icon   {kb:.0f} KB")

    for name, size in DRAWN.items():
        letter_d(size).save(PUBLIC / name, optimize=True)
        print(f"  {name:22} {size}x{size}  drawn, the mark is illegible here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
