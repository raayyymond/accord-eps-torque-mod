# -*- coding: utf-8 -*-
"""pg_lib.py -- p-gain lens helpers on top of the shared harness.

  surface_table(c)        the delivered steady surface T(idx) at fb = 0, taper 254, from the golden model's own march
                          (H.surface), cached per (Kp, map) pair.
  local_slope(c, idx)     d T / d wire at idx (T counts per 0xE4 count), central difference over +-8 idx on that
                          surface -- the small-signal FF gain the fork's loop sees at that operating point.
  static_ratio(c, idx)    T_c(idx) / T_V294(idx).
  outer_local(c, p, v, f, idx_op)
                          the harness's outer_frf, but LINEARISED AT idx_op for a SCHEDULED candidate: the trim uses
                          Kp(idx_op) and the FF path uses the surface's true local slope d(map*Kp)/d idx (the harness's
                          ff_tf uses map' * Kp(idx_op), which omits map * Kp' -- exact only for a flat Kp).  Done by an
                          equivalent flat cell set (Kp flat = Kp(idx_op); map scaled so map' * Kp = the true local slope).
  monotone(c)             the surface is non-decreasing over idx 0..240.
ANALYSIS ONLY."""
import sys

import numpy as np

HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
if HARN not in sys.path:
    sys.path.insert(0, HARN)
import v295_harness as H  # noqa: E402

_SURF = {}


def surface_table(c):
    k = (tuple(c.kp_x), tuple(c.kp_y), tuple(c.map_x), tuple(c.map_y), c.e_shift, c.p_clamp)
    if k not in _SURF:
        _SURF[k] = np.array(H.surface(c, range(0, 241)), float)
    return _SURF[k]


def local_slope(c, idx, half=8):
    S = surface_table(c)
    i0, i1 = max(idx - half, 0), min(idx + half, 240)
    return (S[i1] - S[i0]) / ((i1 - i0) * H.WIRE_PER_IDX)


def static_ratio(c, idx, base=None):
    base = base or H.Cells.v294()
    a, b = surface_table(c)[idx], surface_table(base)[idx]
    return a / b if b else float("nan")


def monotone(c):
    S = surface_table(c)
    return bool(np.all(np.diff(S) >= 0)), int(np.min(np.diff(S)))


def equivalent_flat(c, idx_op, half=8):
    """a flat-Kp cell set whose LINEAR behaviour at idx_op equals c's: Kp = Kp(idx_op) (the trim), map scaled so that
    ff_tf's slope (map' over +-8 idx times Kp) equals the surface's true local slope."""
    kp = int(H.lerp_table(c.kp_x, c.kp_y)[idx_op])
    mt = H.lerp_table(c.map_x, c.map_y)
    i0, i1 = max(idx_op - half, 0), min(idx_op + half, c.idx_clamp)
    map_slope = (mt[i1] - mt[i0]) / float(i1 - i0)
    # the true local slope of (map<<e)*Kp/256 over the same window, from the tables (the surface's pre-lag product)
    prod = (mt.astype(float) * (2 ** c.e_shift)) * H.lerp_table(c.kp_x, c.kp_y).astype(float) / 256.0
    true_slope = (prod[i1] - prod[i0]) / float(i1 - i0)                   # P counts per idx
    ff_slope = map_slope * (2 ** c.e_shift) * kp / 256.0
    s = true_slope / ff_slope if ff_slope else 1.0
    my = tuple(int(round(y * s)) for y in c.map_y)
    return c.replace(kp_y=(kp,) * 5, map_y=my, name=c.name + "@%d" % idx_op), s


def outer_local(c, p, v, f, idx_op, relay=True):
    ce, _ = equivalent_flat(c, idx_op)
    return H.outer_frf(ce, p, v, f, relay=relay, idx_op=idx_op)


def inner_local(c, p, f, idx_op):
    ce, _ = equivalent_flat(c, idx_op)
    return H.loop_frf(ce, p, f)
