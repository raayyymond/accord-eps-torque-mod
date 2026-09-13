# -*- coding: utf-8 -*-
"""openloop_lib.py -- loader + shared derivations for the OPEN-LOOP RING DAMPING study
(subagent `openloop`, 2026-09-13).  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

WHY A NEW LOADER: the engagement-gating experiment of 2026-09-10 (outerloop_openloop.py) ran over the
18 routes in analysis-2020accord/_scratch/cache/v280, which is what creep20_loop_id.load reads.  The
question here -- the ring's damping with the LKAS rate loop OPEN -- lives entirely in the LATERAL-
DISENGAGED stratum, which is the RARE one, so it needs every cached route, not 18 of them.  The larger
family analysis-2020accord/_scratch/cache/<route>/<route>.npz holds 35 routes and carries the same
fields under different names.

The loader below reproduces creep20_loop_id.load's derivations EXACTLY on the shared routes -- that
equivalence is asserted in sec0 of openloop_ring.py and is the loader's positive control:
    bar   = driver torque * 1.024                 [memory accord-wire-torque-is-raw-times-1024]
    wire  = 0x18F STEER_ANGLE_RATE in RAW counts  (rate_c is the same channel already in deg/s;
            V.CPD = 8 raw counts per deg/s, i.e. the 0.125 deg/s LSB)
    eng   = 0x18F STEER_CONTROL_ACTIVE AND 0xE4 STEER_REQUEST
            [memory feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference]
    axis  = C20.dejitter of the raw 0x18F receive stamps, then C20.grid_from -- the kit's own uniform
            frame axis, NOT the jittered receive axis the big cache stores.
"""
import os
import pickle
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import _grind2_lib as G2                      # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

FS = 100.0

# route -> build.  The 18 from outerloop_openloop.py are the record's; the rest are read from
# docs/BUILD-LINEAGE + the route/build table in the census reports.  Where a route's build is not
# pinned in the record it is left "?" -- it does not matter for the DISENGAGED stratum (with
# STEER_REQUEST = 0 the LKAS lane is off and every post-V104 build's rate-lane edits are gated on
# STEER_CONTROL_ACTIVE), and every engaged number below is reported per route anyway.
BUILD = {"r22": "V112", "r23": "V112", "r2e": "V255-ish", "r31": "V278r3", "r32": "V280r2",
         "r33": "V280r2", "r34": "V280r2", "r35": "V281r3", "r39": "V282", "r3a": "V282",
         "r3c": "V282", "r5e_v288": "V288r2", "r62_v289": "V289r1", "r63_v289": "V289r1",
         "r97": "stock"}


def routes():
    out = []
    for k in sorted(os.listdir(CACHE)):
        if os.path.exists(os.path.join(CACHE, k, k + ".npz")):
            out.append(k)
    return out


_G = {}


def load(tag, force=False):
    """the big-family cache on the kit's canonical uniform 0x18F frame axis."""
    if tag in _G and not force:
        return _G[tag]
    fp = os.path.join(SCR, "openloop_g_%s.pkl" % tag)
    if os.path.exists(fp) and not force:
        with open(fp, "rb") as fh:
            g = pickle.load(fh)
        _G[tag] = g
        return g
    D = np.load(os.path.join(CACHE, tag, tag + ".npz"), allow_pickle=True)
    # NOTE: the big cache's `raw18_t` runs 1-2 samples LONGER than the data arrays on 25 of 35
    # routes; `t` always matches them, and dejitter returns the same period to 1e-8 s.  Use `t`.
    t18 = np.asarray(D["t"], float)
    k18, P18, tn18, res = C20.dejitter(t18, 0.01, 100)
    K = int(k18[-1])
    g = dict(tag=tag, P=P18, n=K + 1,
             jit=(float(np.percentile(res, 50)), float(np.percentile(res, 90))))
    g["t"] = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18
    # SIGN [EVIDENCE, sec0]: this cache family stores tq and rate_c NEGATED relative to the v280
    # cache that creep20_loop_id.load reads (corr = -1.00000000 on r39 before the flip).  The v280
    # convention is the kit's yardstick -- every census, episode and dose number is on it -- so flip.
    g["bar"], have = C20.grid_from(k18, -np.asarray(D["tq"], float) * 1.024, K)
    g["wire"], _ = C20.grid_from(k18, -np.asarray(D["rate_c"], float) * V.CPD, K)
    g["sca"], _ = C20.grid_from(k18, np.asarray(D["sca"], float), K)
    g["req"], _ = C20.grid_from(k18, np.asarray(D["e4req"], float), K)
    g["cmd"], _ = C20.grid_from(k18, np.asarray(D["e4tq"], float), K)
    g["ang"], _ = C20.grid_from(k18, np.asarray(D["ang"], float), K)
    g["vego"], _ = C20.grid_from(k18, np.asarray(D["cs_v"], float), K)
    g["press"], _ = C20.grid_from(k18, np.asarray(D["cs_press"], float), K)
    g["have"] = have
    g["eng"] = (g["sca"] > 0.5) & (g["req"] > 0.5) & have
    g["off"] = (~((g["sca"] > 0.5) & (g["req"] > 0.5))) & have
    g["rate_dps"] = g["wire"] / V.CPD                       # deg/s, 0.125 deg/s LSB
    g["idx"], g["sgn"] = V.demand(np.round(g["cmd"]), g["bar"])
    g["build"] = BUILD.get(tag, "?")
    with open(fp, "wb") as fh:
        pickle.dump(g, fh, protocol=4)
    _G[tag] = g
    return g


# ----------------------------------------------------------------------------------------------
def line_of(x, lo, hi, nfft=1024, fs=FS):
    """GI.line_of's estimator on a chosen search band (prominence spectrum over 4-34 Hz)."""
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    sl = (f >= 4.0) & (f <= 34.0)
    R = G2.prom_spectrum(f[sl], P[sl], 6.0, 1.5)
    return G2.locate(f[sl], P[sl], lo, hi, R=R)


def band(x, lo, hi, fs=FS):
    return GI.band(np.asarray(x, float) - np.mean(x), lo, hi, fs)


def bp(x, lo, hi, fs=FS):
    return C20.bandpass(np.asarray(x, float) - np.mean(x), lo, hi, fs)


def runs(mask, minlen):
    d = np.diff(np.r_[0, np.asarray(mask).astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def boot_ci(x, fn=np.median, n=4000, seed=0, lo=2.5, hi=97.5):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    b = np.array([fn(x[rng.integers(0, len(x), len(x))]) for _ in range(n)])
    return float(fn(x)), float(np.percentile(b, lo)), float(np.percentile(b, hi))
