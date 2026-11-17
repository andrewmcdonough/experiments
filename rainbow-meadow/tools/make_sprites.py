# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "scipy"]
# ///
"""Turn the green-screen character art in art/ into game sprites in sprites/.

Each art image has both characters side by side on a flat green background. For every
character, all of its frames are cropped with the same box, so the head stays in the same
place from frame to frame and the game can draw any frame from one anchor point.

Run from the rainbow-meadow folder:  uv run tools/make_sprites.py
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "art"
OUT = ROOT / "sprites"

# Which art file each character's frames come from, and which side of the image she is on
CHARACTERS = {
    "floral": {"side": "left", "frames": {"stand": "stand", "walk": "walk", "jump": "jump-tucked"}},
    "dots": {"side": "right", "frames": {"stand": "stand", "walk": "walk", "jump": "jump-arms-up"}},
}
SCALE = 0.14  # art is ~1700px tall; sprites are drawn at half their pixel size for sharp retina output
SOLID_GREEN = 100  # greenness above this is definitely background
SCREEN_MATCH = 60  # enclosed pixels this close to the green-screen colour are background too
EDGE_GREEN = (40, 140)  # greenness range blended into transparency at the edges
MIN_PART = 0.02  # pieces smaller than this fraction of a character are stray artefacts


def greenness(rgb):
    return rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])


def background_mask(rgb):
    """Green connected to the image border, plus enclosed gaps (between legs, under arms)
    that are the exact green-screen colour. Muted greens in the outfits stay."""
    labels, _ = ndimage.label(greenness(rgb) > SOLID_GREEN)
    edges = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    border = np.unique(edges[edges > 0])
    outside = np.isin(labels, border)
    screen = np.median(rgb[outside], axis=0)
    enclosed = np.linalg.norm(rgb - screen, axis=-1) < SCREEN_MATCH
    return outside | enclosed


def character_masks(rgb):
    """One mask per side of the image, dropping specks like the stray blobs Gemini leaves."""
    labels, count = ndimage.label(~background_mask(rgb), structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
    centres = ndimage.center_of_mass(np.ones_like(labels), labels, range(1, count + 1))
    width = rgb.shape[1]
    masks = {"left": np.zeros(labels.shape, bool), "right": np.zeros(labels.shape, bool)}
    for part, (size, (_, cx)) in enumerate(zip(sizes, centres), start=1):
        if size >= MIN_PART * sizes.max():
            masks["left" if cx < width / 2 else "right"] |= labels == part
    return masks


def to_rgba(rgb, mask):
    """Soft, de-greened edges so no green halo is left around the outline."""
    near_edge = mask & ~ndimage.binary_erosion(mask, iterations=3)
    lo, hi = EDGE_GREEN
    edge_alpha = np.clip((hi - greenness(rgb)) / (hi - lo), 0, 1)
    alpha = np.where(near_edge, edge_alpha, mask.astype(float))
    out = rgb.copy()
    despilled = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]))
    out[..., 1] = np.where(near_edge, despilled, rgb[..., 1])
    return np.dstack([out, alpha * 255]).clip(0, 255).astype(np.uint8)


def bbox(mask):
    ys, xs = np.nonzero(mask)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def main():
    OUT.mkdir(exist_ok=True)
    art = {}
    for path in ART.glob("*.jpeg"):
        rgb = np.asarray(Image.open(path).convert("RGB")).astype(int)
        art[path.stem] = (rgb, character_masks(rgb))

    meta = {}
    for name, spec in CHARACTERS.items():
        frames = {f: (art[src][0], art[src][1][spec["side"]]) for f, src in spec["frames"].items()}
        boxes = [bbox(mask) for _, mask in frames.values()]
        pad = 8
        x0 = min(b[0] for b in boxes) - pad
        y0 = min(b[1] for b in boxes) - pad
        x1 = max(b[2] for b in boxes) + pad
        y1 = max(b[3] for b in boxes) + pad
        size = (round((x1 - x0) * SCALE), round((y1 - y0) * SCALE))

        files = {}
        for frame, (rgb, mask) in frames.items():
            rgba = to_rgba(rgb, mask)[y0:y1, x0:x1]
            file = f"{name}-{frame}.png"
            Image.fromarray(rgba, "RGBA").resize(size, Image.LANCZOS).save(OUT / file)
            files[frame] = f"sprites/{file}"

        sx0, sy0, sx1, sy1 = bbox(frames["stand"][1])
        meta[name] = {
            "frames": files,
            "width": size[0],
            "height": size[1],
            # Where the standing feet touch the ground, in sprite pixels
            "footX": round(((sx0 + sx1) / 2 - x0) * SCALE),
            "footY": round((sy1 - y0) * SCALE),
            "bodyWidth": round((sx1 - sx0) * SCALE),
            "bodyHeight": round((sy1 - sy0) * SCALE),
        }
        print(name, meta[name])

    (OUT / "sprites.js").write_text("window.SPRITES = " + json.dumps(meta, indent=2) + ";\n")


if __name__ == "__main__":
    main()
