# -*- coding: utf-8 -*-
"""sr_lib.py -- the estimator and its cluster (block) bootstrap, done on GRAM SUMS so a
400-rep bootstrap over a million-sample bin costs O(n_blocks) per rep instead of O(n).

TLS through the origin of y on x is the eigenvector of the SMALLEST eigenvalue of the 2x2
Gram matrix [[Sxx,Sxy],[Sxy,Syy]]; slope = -n0/n1.  Because the Gram is additive over samples
it is also additive over blocks, so resampling blocks = resampling their Gram contributions.
`_selfcheck()` proves the closed form against np.linalg.svd on random data.
"""
import numpy as np

FS = 100.0
BOOT = 400


def tls_origin_gram(a, b, c):
    """smallest-eigenvector slope of [[a,b],[b,c]]; a=Sxx b=Sxy c=Syy."""
    tr = a + c
    disc = np.sqrt(np.maximum((a - c) ** 2 + 4.0 * b * b, 0.0))
    lam = 0.5 * (tr - disc)
    # eigenvector (b, lam - a); slope = -n0/n1
    n0, n1 = b, lam - a
    with np.errstate(divide="ignore", invalid="ignore"):
        return -n0 / n1


def tls_origin(x, y):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    return float(tls_origin_gram(float(x @ x), float(x @ y), float(y @ y)))


def tls_free(x, z, y):
    """3-var TLS: y = sR*x + c*z.  Returns (sR, c).  z is the curvature-factor column, so
    c is the free angle offset in RADIANS of wheel angle (see sr_analyze docstring)."""
    M = np.stack([x, z, y], 1).astype(np.float64)
    Gm = M.T @ M
    w, V = np.linalg.eigh(Gm)
    n = V[:, 0]
    if abs(n[2]) < 1e-300:
        return np.nan, np.nan
    return float(-n[0] / n[2]), float(-n[1] / n[2])


def block_grams(x, y, blk):
    """per-block (Sxx, Sxy, Syy, n).  blk is an integer cluster id."""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    u, inv = np.unique(blk, return_inverse=True)
    nb = len(u)
    a = np.bincount(inv, weights=x * x, minlength=nb)
    b = np.bincount(inv, weights=x * y, minlength=nb)
    c = np.bincount(inv, weights=y * y, minlength=nb)
    n = np.bincount(inv, minlength=nb).astype(np.float64)
    return a, b, c, n


def tls_ci(x, y, blk, nboot=BOOT, seed=0, min_n=200):
    """point estimate + block-bootstrap 95 % CI (blocks resampled with replacement)."""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    m = np.isfinite(x) & np.isfinite(y)
    x, y, blk = x[m], y[m], blk[m]
    n = len(x)
    if n < min_n:
        return np.nan, n, np.nan, np.nan
    s = tls_origin(x, y)
    a, b, c, cnt = block_grams(x, y, blk)
    nb = len(a)
    if nb < 8:
        return s, n, np.nan, np.nan
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nb, size=(nboot, nb))
    A = a[pick].sum(1); B = b[pick].sum(1); C = c[pick].sum(1)
    out = tls_origin_gram(A, B, C)
    out = out[np.isfinite(out)]
    if len(out) < 20:
        return s, n, np.nan, np.nan
    return s, n, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def _selfcheck():
    rng = np.random.default_rng(7)
    for _ in range(20):
        n = rng.integers(200, 2000)
        x = rng.normal(0, 1, n)
        y = 3.7 * x + rng.normal(0, 0.2, n)
        _, _, V = np.linalg.svd(np.stack([x, y], 1), full_matrices=False)
        ref = float(-V[-1][0] / V[-1][1])
        got = tls_origin(x, y)
        assert abs(ref - got) < 1e-9 * max(1.0, abs(ref)), (ref, got)
        # block additivity
        blk = rng.integers(0, 20, n)
        a, b, c, _ = block_grams(x, y, blk)
        assert abs(float(tls_origin_gram(a.sum(), b.sum(), c.sum())) - got) < 1e-9
    # free-intercept recovers a planted offset
    for _ in range(5):
        n = 20000
        v = rng.uniform(5, 30, n)
        cf = 1.0 / (1.0 - (-0.0015) * v ** 2) / 2.83
        d = rng.normal(0, 0.002, n)
        off = np.radians(-4.9)
        sR = 15.5
        sa = sR * d / cf
        ang = sa + off
        yraw = cf * ang
        g, co = tls_free(d, cf, yraw)
        assert abs(g - sR) < 0.05 and abs(np.degrees(co) - np.degrees(off)) < 0.1, (g, np.degrees(co))
    return True


if __name__ == "__main__":
    print("sr_lib self-check:", _selfcheck())
