"""Generate tileable short-pile fleece textures for the v2 suit (spec 7.3).

Run:
    python scripts/make_fabric_textures.py

Outputs (1K, tileable, 0.5 m per tile):
    art/textures/fabric_albedo_1k.png   (sRGB)
    art/textures/fabric_rough_1k.jpg    (linear)
    art/textures/fabric_normal_1k.jpg   (tangent space, linear)
"""

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art" / "textures"
OUT.mkdir(parents=True, exist_ok=True)

N = 1024
rng = np.random.default_rng(20261109)


def fbm(size, beta, seed, aniso=1.0):
    """Periodic (tileable) fractal noise via filtered white noise in FFT space."""
    r = np.random.default_rng(seed)
    white = r.normal(size=(size, size))
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    f = np.sqrt((fx * aniso) ** 2 + fy ** 2)
    f[0, 0] = 1.0
    amp = f ** (-beta)
    amp[0, 0] = 0.0
    field = np.real(np.fft.ifft2(np.fft.fft2(white) * amp))
    field -= field.mean()
    field /= max(1e-6, field.std())
    return field


def value_noise(size, cells, seed):
    """Tileable smooth value noise: random grid of `cells` cells, cosine interpolation."""
    r = np.random.default_rng(seed)
    grid = r.random((cells, cells))
    ys = (np.arange(size) + 0.5) * cells / size - 0.5
    y0 = np.floor(ys).astype(int)
    fy = ys - y0
    wy = 0.5 - 0.5 * np.cos(np.pi * fy)
    xs = (np.arange(size) + 0.5) * cells / size - 0.5
    x0 = np.floor(xs).astype(int)
    fx = xs - x0
    wx = 0.5 - 0.5 * np.cos(np.pi * fx)
    a = grid[y0 % cells][:, x0 % cells]
    b = grid[y0 % cells][:, (x0 + 1) % cells]
    c = grid[(y0 + 1) % cells][:, x0 % cells]
    d = grid[(y0 + 1) % cells][:, (x0 + 1) % cells]
    top = a * (1 - wx) + b * wx
    bot = c * (1 - wx) + d * wx
    out = top * (1 - wy[:, None]) + bot * wy[:, None]
    return (out - out.mean()) / max(1e-6, out.std())


# ---- height field: soft fleece clumps + fine fibres ------------------------
clumps = 0.75 * value_noise(N, 40, 21) + 0.35 * value_noise(N, 110, 22)
fibre = fbm(N, 0.55, 12, aniso=0.45)
pills = np.clip(value_noise(N, 220, 23) - 1.3, 0, None)
height = 0.80 * clumps + 0.45 * fibre + 0.9 * pills

# ---- tangent-space normal from the height gradient -------------------------
slope = 1.35
dhdx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * slope
dhdy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * slope
nx, ny, nz = -dhdx, -dhdy, np.ones_like(height)
norm = np.sqrt(nx * nx + ny * ny + nz * nz)
normal = np.stack([nx / norm, ny / norm, nz / norm], axis=-1)
normal_rgb = ((normal * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)

# ---- albedo: warm off-white with faint mottling ----------------------------
albedo_mottling = fbm(N, 1.9, 14)
albedo = np.zeros((N, N, 3), dtype=np.float32)
base_rgb = np.array([0.902, 0.898, 0.886])          # linear-ish #E9E9E9
for i in range(3):
    albedo[..., i] = base_rgb[i] * (1.0 + 0.030 * albedo_mottling)
albedo_rgb = (np.clip(albedo, 0, 1) ** (1 / 2.2) * 255.0).clip(0, 255).astype(np.uint8)

# ---- roughness: fleece is rough, with fibre mottling -----------------------
rough = 0.84 + 0.08 * fbm(N, 1.4, 15)
rough = (np.clip(rough, 0, 1) * 255.0).astype(np.uint8)
rough_rgb = np.dstack([rough, rough, rough])

Image.fromarray(albedo_rgb).save(OUT / "fabric_albedo_1k.png", optimize=True)
Image.fromarray(rough_rgb).save(OUT / "fabric_rough_1k.jpg", quality=92, optimize=True)
Image.fromarray(normal_rgb).save(OUT / "fabric_normal_1k.jpg", quality=92, optimize=True)
print("wrote", OUT / "fabric_albedo_1k.png", OUT / "fabric_rough_1k.jpg", OUT / "fabric_normal_1k.jpg")
