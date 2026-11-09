"""Compare a render against art/refs/eliz_front.jpg (silhouette IoU + row widths)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def mask_of(path, kind):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    if kind == "ref":
        return lum > 8            # reference background is pure black
    return lum > 24               # render background is black


def bbox_rows(mask):
    ys, xs = np.nonzero(mask)
    return ys.min(), ys.max(), xs.min(), xs.max()


def row_profile(mask, n=21):
    y0, y1, x0, x1 = bbox_rows(mask)
    out = []
    for i in range(n):
        y = int(round(y0 + (y1 - y0) * i / (n - 1)))
        x = np.nonzero(mask[y])[0]
        out.append((x.max() - x.min() + 1) if len(x) else 0)
    return np.array(out, dtype=float)


def iou(a, b):
    # normalise each mask to its own bbox, then resample to a common grid
    def crop(m):
        y0, y1, x0, x1 = bbox_rows(m)
        return Image.fromarray((m[y0:y1 + 1, x0:x1 + 1] * 255).astype(np.uint8)).resize((200, 295), Image.NEAREST)

    A = np.asarray(crop(a)) > 127
    B = np.asarray(crop(b)) > 127
    return (A & B).sum() / max(1, (A | B).sum())


ref = mask_of(ROOT / "art/refs/eliz_front.jpg", "ref")
ren = mask_of(ROOT / sys.argv[1] if len(sys.argv) > 1 else "art/renders/v2_front_match.png", "render")
print("ref bbox", bbox_rows(ref), "render bbox", bbox_rows(ren))
print("IoU", round(iou(ref, ren), 4))
pr, pn = row_profile(ref), row_profile(ren)
scale = pn.max() / pr.max()
print("ref widths ", " ".join(f"{v:.0f}" for v in pr))
print("render width", " ".join(f"{v:.0f}" for v in pn))
print("ratio(ren/ref*scale)", " ".join(f"{v / max(1e-6, r * scale):.2f}" for v, r in zip(pn, pr)))
