#!/usr/bin/env python3
"""v75_step_lib.py -- route-5d telemetry loader + the gp-0x6bd0 replay, for the V75 STEP-SIZE test.

WHAT THIS IS
------------
V75's pre-flight clip check (kit RULE 8) tested the damper's OUTPUT MAGNITUDE only. This module
supplies the machinery for the question nobody asked: the PER-TICK STEP `|d gp-0x6bd0|`, replayed
frame-for-frame over route 5d (V74's 1,011 s flight) under BOTH builds' calibration surfaces.

THE RATE SIGNAL -- and why `rate_f` (0x18F), not `rate_c` (0x14A), is the right proxy  [EVIDENCE]
-------------------------------------------------------------------------------------------------
FactorE is indexed by `gp-0x6ac0`. Chain, all from the firmware record:
  · `gp-0x6ac0 == |gp-0x6abe|` -- ONE producer `FUN_00041464`, signed vs rectified faces of the
    SAME EMA state, to within +-1 LSB of truncation.
    [[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]]
  · `gp-0x6a56 = polarity(gp-0x6752) * ((gp-0x6abe * 0x30 * cal(0xC613A=1159)) >> 15)`
             = +- gp-0x6abe * 3477/2048   (a fixed Q15 scale -- NO extra filter, NO extra pole)
    [[reference_accord_gp6abe_column_degps_scale_settled]]
  · CAN 0x18F bytes 2:3 packs `-gp-0x6a56` UNSHIFTED. CAN 0x14A bytes 2:3 packs `(-gp-0x6a56)>>3`.
    The extractor decodes 0x18F with factor -0.1 (`rate_f`) and 0x14A with factor -1.0 (`rate_c`),
    which is why `rate_f == 0.8 * rate_c` identically in the cache (verified below, §check).

  => THE EXACT RECONSTRUCTION USED HERE:
        gp-0x6a56 = 10 * rate_f                       (rate_f is that halfword in units of 0.1)
        gp-0x6ac0 = |gp-0x6a56| * 2048/3477 = |rate_f| * 5.88898
     Residual uncertainty: +-0.6 counts (one truncation step of the 1.698 counts-of-6a56 per count
     of 6abe scale). The `rate_c` route gives the kit's settled 4.7121 counts per column deg/s
     (= 5.88898 / 1.25, since rate_f = 0.8 * rate_c) but at 8x COARSER quantisation (1 deg/s LSB
     = 4.71 counts of gp-0x6ac0). Both are computed; `rate_f` is primary.
  🛑 The scales are the SAME settled scale -- 5.88898 counts per 0.1-unit of the fine field IS
     4.7121 counts per column deg/s. This is NOT the "on-car fit of 5.80"; no scale is switched.

  ⚠ [BELIEF, small] `polarity(gp-0x6752)` is a global +-1 on the bus copy. The damper output is an
    ODD function of rate, so |delta out| is invariant to it. Sign-of-output plots would not be.

  ⚠ [EVIDENCE, direction stated] `rate_f` is 0x18F's value ZERO-ORDER-HELD onto the 0x14A arrival
    lattice by the extractor. Both frames are 100 Hz from the same ECU, so pairing is ~1:1, but a
    missed/duplicated 0x18F update collapses two ticks into one step or inserts a zero step. The
    census in §check quantifies it. Net effect on the headline: it can only SMEAR the step
    distribution, and it applies IDENTICALLY to V74 and V75 (same frames, same rate).

WHAT IS AN UPPER BOUND, DELIBERATELY
------------------------------------
  · `seed` (gp-0x698a) is a MIN-reduce CEILING of 1024 that can only be pulled DOWN
    [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] §corrected 2026-08-05.
    Using 1024 gives the LARGEST dose and the LARGEST step. Unobservable on this route.
  · the FactorC plausibility gate `gp-0x67f4 == 1` is assumed to pass (it fails OPEN to unity 1024,
    which is >566 -- so a failure would make BOTH builds larger and is a common-mode, not a delta).
  · the ceiling's own index `gp-0x6ac2` (a DIFFERENT signal, the backdrive/plausibility rate) is not
    observable; the ceiling is LERP(X=(300,800), Y=(512,1024)) so it lies in [512,1024]. 512 is the
    floor => the MOST clamping => the SMALLEST steps. Both bounds are reported.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import v75_fault_exact_model as M          # noqa: E402  -- the instruction-annotated surface
import v75_fault_tables as T               # noqa: E402

CACHE = ROOT / "_cache_r5d"
PFX = "r5ds"
SEGS = list(range(17))

# ---- the settled scale, both routes ---------------------------------------------------------------
CTS_PER_DEGS = 4.71210813920046            # gp-0x6ac0 counts per column deg/s  (via rate_c)
FINE_TO_6AC0 = 10.0 * 2048.0 / 3477.0      # gp-0x6ac0 counts per unit of rate_f (== 1.25*4.7121)
CTS_PER_KMH = 64.0                         # gp-0x6a5e counts per km/h (settled: 2240 == 35 km/h)
MS_TO_CTS = 3.6 * CTS_PER_KMH              # 230.4 counts per m/s

# ---- the governor's slew step, from FUN_0004503c (as briefed) --------------------------------------
SLEW_TIGHT = 205                           # counts/tick, once speed sustained >= 1062 cts for 10 cyc
SLEW_LOOSE = 512                           # counts/tick, below that
SPEED_SEL_CTS = 1062                       # ~16.59 km/h
SPEED_SEL_HOLD = 10                        # cycles

# ---- V73's measured mode-selector lags (see _r5d_lib.lever_mask) -----------------------------------
MODE_LAG_RISE_S = 1.0209
MODE_LAG_FALL_S = 2.0798
MODE_ENGAGED, MODE_MANUAL = 26, 24

CHANS = ("t", "cs_v", "rate_c", "rate_f", "cc_lat", "damp_nz", "sca", "cs_gear", "cs_std",
         "ws_mean", "state", "tq", "e4tq")


def load_route():
    """Concatenate all 17 segments onto one monotone clock, keeping the segment id per frame."""
    out = {k: [] for k in CHANS}
    out["seg"] = []
    out["t_seg"] = []
    t_off = 0.0
    for s in SEGS:
        p = CACHE / f"{PFX}{s}.npz"
        d = np.load(p)
        n = len(d["t"])
        for k in CHANS:
            out[k].append(np.asarray(d[k], float) if k in d.files else np.full(n, np.nan))
        out["seg"].append(np.full(n, s, float))
        out["t_seg"].append(np.asarray(d["t"], float))
        out["t"][-1] = np.asarray(d["t"], float) + t_off
        t_off += float(d["t"][-1]) + 0.01
    D = {k: np.concatenate(v) for k, v in out.items()}
    return D


# ---------------------------------------------------------------------------- the replay ------------
class Replay(object):
    """gp-0x6bd0 per frame, for one build, honouring the mode selector."""

    def __init__(self, build, ceiling=None):
        self.build = build
        self.S = {m: M.Surface(build, m) for m in (MODE_MANUAL, MODE_ENGAGED)}
        self.ceiling = ceiling             # None -> the model's own fallback (512)

    def _out(self, mode, sp, rt):
        s = self.S[mode]
        # cache the surface as a plain lookup: the LERPs are integer and pure, so memoise on
        # (speed, rate) -- route 5d has ~101k frames but far fewer distinct (sp, rt) pairs.
        c = s.factorC(int(sp))
        E = s.factorE(abs(int(rt)), int(rt))
        if E is None:
            d = 0
        else:
            d = (1024 * 1024) >> 10                       # seed*B, both 1024 (B flat, verified)
            d = (d * c) >> 10
            d = (d * 1024) >> 10                          # *D, flat 1024 (verified)
            d = (d * (E & 0xFFFF)) >> 10
            if int(rt) > 0:
                d = -d
        ceil = self.ceiling if self.ceiling is not None else s.ceiling(0)
        if d > ceil:
            v = ceil
        elif d >= -ceil:
            v = d
        else:
            v = -ceil
        v &= 0xFFFF
        return v - 0x10000 if v & 0x8000 else v

    def run(self, sp, rt, mode):
        """Vectorised-by-memoisation replay. sp/rt/mode are integer arrays of equal length."""
        sp = np.asarray(sp, np.int64)
        rt = np.asarray(rt, np.int64)
        mode = np.asarray(mode, np.int64)
        out = np.empty(len(sp), np.int64)
        memo = {}
        for i in range(len(sp)):
            k = (int(mode[i]), int(sp[i]), int(rt[i]))
            v = memo.get(k)
            if v is None:
                v = self._out(k[0], k[1], k[2])
                memo[k] = v
            out[i] = v
        return out


# ---------------------------------------------------------------------------- helpers ---------------
def mode_masks(lat, t):
    """(in_force_26, byte_stock_24, ambiguous) -- _r5d_lib.lever_mask, re-implemented locally."""
    lat = np.asarray(lat, float) > 0.5
    t = np.asarray(t, float)
    on = np.interp(t - MODE_LAG_RISE_S, t, lat.astype(float)) > 0.5
    off = np.interp(t - MODE_LAG_FALL_S, t, lat.astype(float)) > 0.5
    in_force = on & off & lat
    byte_stock = (~on) & (~off) & (~lat)
    return in_force, byte_stock, ~(in_force | byte_stock)


def episodes(lat, t, merge_s=1.0, min_s=1.0):
    """Engagement episodes -- the extractor's own definition, so n must reproduce its 9."""
    lat = np.asarray(lat, float) > 0.5
    t = np.asarray(t, float)
    idx = np.flatnonzero(lat)
    if not len(idx):
        return []
    brk = np.flatnonzero(np.diff(idx) > 1)
    runs = np.split(idx, brk + 1)
    merged = [runs[0]]
    for r in runs[1:]:
        if t[r[0]] - t[merged[-1][-1]] <= merge_s:
            merged[-1] = np.concatenate([merged[-1], r])
        else:
            merged.append(r)
    return [r for r in merged if t[r[-1]] - t[r[0]] >= min_s]


def q(x, name=""):
    x = np.asarray(x, float)
    if not len(x):
        return dict(n=0)
    return dict(n=int(len(x)),
                p50=float(np.percentile(x, 50)), p90=float(np.percentile(x, 90)),
                p99=float(np.percentile(x, 99)), p999=float(np.percentile(x, 99.9)),
                max=float(np.max(x)), mean=float(np.mean(x)))
