# -*- coding: utf-8 -*-
r"""THE PHYSICAL SCALE OF THE WHEEL-RATE OPERAND x (gp-0x6a56), MEASURED ON THE WIRE.  2026-09-21.

Why this exists.  V294's trim gain was sized on "8 x-counts per deg/s", a value the record had inherited
(V293 trace sec.7.1, marked BELIEF).  Adversary C (Ghidra, 2026-09-21) argued from the ISR's own constant
(120000 = 360/0.003) and from a packer chain that x is 1.0 or 1.7 -- which would make V294's trim 5-8x too
weak.  This script measures x directly from three routes on which the EPS RATE LOOP WAS LIVE (V292, routes
6d/6e/6f, fork 305732c85): there the LKAS lane delivers

    T = 0.1603 * (248/256) * (32*sp - 30.9*x)          (V292: Kp 248, fb DC 2*958/(1024-962) = 30.9)

so at near-zero command the CAN-427 tap reads T = -4.80 * x per x-count, and x/rate = |T| / (4.80 * |rate|)
with rate = carState.steeringRateDeg (the 0x14A STEER_ANGLE_RATE field, deg/s at factor 1 -- a sign flip
between the +left frame and the EPS's +T sense is expected and observed).

RESULT (EVIDENCE): binned medians at every rate bin from +-2 to +-12 deg/s, three routes: x = 7.1..7.8
counts per deg/s (median-of-magnitudes ratio 7.8 / 7.9 / 8.1).  The forward regression reads 4..5.7 and the
reverse 6.9..8.1 -- the errors-in-variables bracket around the same value.  8 STANDS.  Adversary C's hop 11
(the bus rate field = -x raw at gp-0x14ce) mis-identified the frame: the kit's record places the 0x14A TX
buffer at gp-0x1518 (checksum call FUN_00057b24(gp-0x1518, 8, 0x14a), TRACE-2026-08-13-v100-6ad6-and-ivar6),
so gp-0x14ce is a different frame and the "0x14A rate is deg/s" regression says nothing about x.  The
ISR-constant reading (3 ms, 1 count per deg/s at gp-0x29c4) is consistent with 8 if the differenced position
is a shaft geared 4.71:1 to the steering wheel (claim B's 4.7121 x hop 7's 1.6978 = 8.00) -- BELIEF, open.

Caches: analysis-2020accord/_scratch/cache/v280/r6{d,e,f}_v292.npz (v280 format: t1ab/b0/b1 = the 427 tap
at 50 Hz, te4/cmd/req = the 0xE4 command, tcs/cs_rate/vego = carState).
"""
import json
import sys
from pathlib import Path

import numpy as np

KIT = Path(__file__).resolve().parents[3]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
OUT = Path(__file__).resolve().parent / "out"
MAPX = [0, 12, 20, 24, 32, 64, 96, 128, 160, 240]
MAPY = [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032]
KP_V292, DC_V292, GAIN = 248, 2 * 958 / (1024 - 962), 0.1603
DT_DX = -GAIN * KP_V292 / 256 * DC_V292            # -4.80 T-counts per x-count


def lag(x, t, fc):
    y = np.zeros_like(x)
    a = 0.0
    for i in range(1, len(x)):
        dt = t[i] - t[i - 1]
        al = dt / (dt + 1 / (2 * np.pi * fc))
        a = a + al * (x[i] - a)
        y[i] = a
    return y


def main():
    results = {}
    print(f"V292 lane: dT/dx = {DT_DX:.2f} T-counts per x-count (Kp {KP_V292}, fb DC {DC_V292:.1f}, forward {GAIN})")
    for tag in ("r6d_v292", "r6e_v292", "r6f_v292"):
        z = np.load(CACHE / f"{tag}.npz", allow_pickle=True)
        prm = json.load(open(CACHE / f"{tag}_params.json"))
        t1, b0, b1 = z["t1ab"], z["b0"].astype(int), z["b1"].astype(int)
        fld = ((b0 & 3) << 8) | b1
        T = np.where(fld & 0x200, -1.0, 1.0) * ((fld & 0x1ff) << 3)          # the 427 tap, T counts
        cmd = np.interp(t1, z["te4"], z["cmd"])
        req = np.interp(t1, z["te4"], z["req"]) > 0.5
        rate = np.interp(t1, z["tcs"], z["cs_rate"])
        v = np.interp(t1, z["tcs"], z["vego"])
        idx = np.clip(np.abs(cmd) / 16.125736, 0, 240)
        sp = np.sign(cmd) * np.interp(idx, MAPX, MAPY)
        FF = GAIN * np.clip(32 * sp * KP_V292 // 256, -15360, 15360)          # the lane's FF at fb = 0
        rl = lag(lag(rate, t1, 9.94), t1, 5.05)                                # the EPS's own lags on the rate
        m = req & (idx < 8) & (v > 5) & (np.abs(T) < 2200) & (np.abs(rl) > 1.0)
        res, r = (T - FF)[m], rl[m]
        fwd = np.polyfit(r, res, 1)[0]
        rev = 1.0 / np.polyfit(res, r, 1)[0]
        ratio = np.sign(np.median(res * r)) * np.median(np.abs(res)) / np.median(np.abs(r))
        rows = []
        for lo, hi in ((2, 4), (4, 7), (7, 12)):
            for s_ in (+1, -1):
                sel = (s_ * r >= lo) & (s_ * r < hi)
                if sel.sum() > 30:
                    rows.append((s_ * lo, s_ * hi, int(sel.sum()), float(r[sel].mean()), float(np.median(res[sel])),
                                 float(np.median(res[sel]) / r[sel].mean() / abs(DT_DX))))
        results[tag] = dict(commit=prm.get("GitCommit", "")[:9], n=int(m.sum()), forward=fwd, reverse=rev, ratio=ratio,
                            x_fwd=abs(fwd) / abs(DT_DX), x_rev=abs(rev) / abs(DT_DX), x_ratio=abs(ratio) / abs(DT_DX), bins=rows)
        print(f"\n{tag} (fork {prm.get('GitCommit', '')[:9]}), near-zero command, n = {m.sum()}:")
        print(f"   forward slope {fwd:+.1f}  reverse {rev:+.1f}  median-ratio {ratio:+.1f} T-counts per deg/s"
              f"   ->  x = {abs(fwd) / abs(DT_DX):.1f} .. {abs(rev) / abs(DT_DX):.1f} (bracket), ratio {abs(ratio) / abs(DT_DX):.1f}")
        for lo, hi, n, mr, mt, xs in rows:
            print(f"   rate {lo:+d}..{hi:+d} deg/s: n {n:5d}  mean rate {mr:+6.2f}  median T-FF {mt:+6.0f}  ->  x = {xs:+.2f} counts per deg/s")
    xs = [b[5] for t in results.values() for b in t["bins"]]
    print(f"\nALL BINS, THREE ROUTES: x = {np.median(xs):.2f} counts per deg/s (min {min(xs):.2f}, max {max(xs):.2f}, n_bins {len(xs)})")
    print("=> the operand is ~8 counts per (steering-wheel) deg/s.  V294's K_alpha/J = 1.0 at 8 is 0.9-1.0 at the measured value.")
    OUT.mkdir(exist_ok=True)
    json.dump(results, open(OUT / "x_scale_from_v292_wire.json", "w"), indent=1)


if __name__ == "__main__":
    main()
