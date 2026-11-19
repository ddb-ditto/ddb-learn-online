#!/usr/bin/env python3
"""Generate the site's icons from the brand artwork.

    pip install pillow
    python3 tools/make_icons.py

Run it when either source in `brand/` changes; the results are committed, so
nothing else needs an image library.

There are three sources and they do different jobs.

`brand/wordmark.png` is the wide mark — "DDB" over "learn online". It is the
site's own logo and appears on the front page, which is the only page that
belongs to the whole site rather than to one subject. A PNG rather than a
JPEG because it arrives with an alpha channel; see `dechroma` for why that
alpha is not to be trusted.

`brand/french.jpg` is the Year 7 French wordmark, for that section's front
page. It arrives on white and is flooded out from the border.

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
# A PNG, not a JPEG: this one arrives with an alpha channel of its own. It is
# not a usable one — see `dechroma` — but JPEG cannot carry it at all, so the
# source has to be a format that can.
WORDMARK = BRAND / "wordmark.png"
APPICON = BRAND / "appicon.jpg"
# The Year 7 French mark, which belongs to that section's front page the way
# the roundel belongs to /italian/. Same treatment as the site wordmark: cut
# out of its white card, because a white rectangle on the dark palette is a
# glaring square.
FRENCH = BRAND / "french.jpg"

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
    # Quantise the alpha along with the colour rather than splitting it off
    # and putting a full eight-bit channel back afterwards.
    #
    # That split is what the first version did, and on flat artwork it costs
    # nothing. On the comic wordmark it cost five times the file: every
    # halftone dot is its own island of alpha, so the channel is as detailed
    # as the picture and compresses about as well. Same artwork, 256 KB split
    # and 49 KB palletised, and composited over either theme the two differ by
    # a mean of three parts in 255 — which is to say not at all, on the page
    # everybody loads first.
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


# The flat green the site wordmark was drawn on, sampled from the file. The
# nearest colour the artwork itself uses is its blue, 138 away in RGB, so a
# radius of 100 keys the card and nothing that was painted on it.
CHROMA = (4, 164, 74)
CHROMA_RADIUS = 100


def dechroma(im: Image.Image, keyed: int = 14) -> Image.Image:
    """Take the green background out of artwork that was cut out badly.

    The site wordmark arrived as a PNG whose alpha was already set — and
    whose alpha was wrong. It is strictly binary, 0 or 255 and nothing
    between, and large patches of the green it was drawn on were left opaque:
    a circle bottom left, another bottom right, a patch above the second D.
    They look like olive smudges on the cream theme and worse on the navy one.

    Keying on green is safe here because the palette has none. Red, blue,
    yellow, black and white: yellow's green channel sits just below its red,
    blue's below its blue, so "green above both of the others" is only ever
    the background. Anything over the threshold goes transparent.

    Then the despill. Where green met artwork the render blended the two, so
    cutting the flat colour leaves a rim of green-tinted pixels — the halo
    that makes a keyed image look keyed. Clamping the green channel to the
    larger of the other two removes the tint and touches nothing else, for
    the same reason the key is safe: in every colour this artwork uses, green
    is already the middle or the smallest channel.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    cut = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                # Clear pixels keep the green underneath them, which bleeds
                # back in the moment anything resamples. Blank it.
                px[x, y] = (0, 0, 0, 0)
                continue
            near = ((r - CHROMA[0]) ** 2 + (g - CHROMA[1]) ** 2
                    + (b - CHROMA[2]) ** 2) ** 0.5 < CHROMA_RADIUS
            if g - max(r, b) > keyed or near:
                # Two tests, because neither catches the other's case. The
                # first finds any green; the second finds the card's own
                # colour where it has been blended dark enough with the
                # artwork that its green no longer dominates. Without it 779
                # pixels of the card survived, and only survived harmlessly
                # because the resize happened to average them away.
                px[x, y] = (0, 0, 0, 0)
                cut += 1
            elif g > max(r, b):
                px[x, y] = (r, max(r, b), b, a)      # despill
    print(f"  {'':22} {cut} green pixels keyed out of the artwork")
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
    for src in (WORDMARK, APPICON, FRENCH):
        if not src.exists():
            sys.exit(f"No artwork at {src.relative_to(REPO)}")

    # The site logo. This artwork came already cut out, badly — see
    # `dechroma` — so the green is keyed rather than flooded, and the resize
    # premultiplies so nothing bleeds in from behind the transparent pixels.
    # Quantised afterwards: this is comic halftone, where a hundred-odd
    # colours is invisible and the difference between half a megabyte and
    # forty kilobytes on the page everybody loads first.
    mark = dechroma(Image.open(WORDMARK))
    # `thumbnail` on RGBA does not average the colour behind transparent
    # pixels into the ones beside them — checked, because the usual advice is
    # that it does and the fix is to premultiply by hand. On this artwork the
    # two paths are byte for byte identical, so the hand-rolled version came
    # back out: a guard that prevents nothing, with a comment saying it
    # prevents something, is worse than no guard at all.
    mark.thumbnail((LOGO_WIDTH * 2, LOGO_WIDTH * 2), Image.LANCZOS)
    mark = quantise(mark, colors=64, dither=False)
    mark.save(PUBLIC / "logo-site.png", optimize=True)
    kb = (PUBLIC / "logo-site.png").stat().st_size / 1024
    print(f"  {'logo-site.png':22} {mark.size[0]}x{mark.size[1]}  wordmark, cut out   {kb:.0f} KB")

    # The French section's mark, cut out the same way. Its white lettering —
    # the word YEAR — is enclosed by the dark outline, so the flood never
    # reaches it and the letters survive the cut.
    fr = transparent(Image.open(FRENCH))
    fr.thumbnail((LOGO_WIDTH * 2, LOGO_WIDTH * 2), Image.LANCZOS)
    fr = quantise(fr, colors=48, dither=False)
    fr.save(PUBLIC / "logo-french.png", optimize=True)
    kb = (PUBLIC / "logo-french.png").stat().st_size / 1024
    print(f"  {'logo-french.png':22} {fr.size[0]}x{fr.size[1]}  Year 7 French       {kb:.0f} KB")

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
