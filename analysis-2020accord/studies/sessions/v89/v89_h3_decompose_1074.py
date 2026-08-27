#!/usr/bin/env python3
"""studies/sessions/v89/v89_h3_decompose_1074.py -- WHY did the +1.074 command coefficient collapse to +0.012?

v89_h2 re-ran the symptom-vs-command regression on a bigger, better-controlled sample and got
+0.012 [-0.006, +0.061] where my earlier run gave +1.074 [+0.812, +1.445].  Before either number is
quoted I have to know which single change is responsible.  Four differ at once:

  1. THE REGRESSOR.  Earlier: `sqrt(mean(cmd^2))` -- the RAW rms, which is dominated by the command's
     DC level (how hard LKAS is pushing = the mesh LOAD).  v89_h2: a DEMEANED band rms -- the
     command's FLUCTUATION.  For a load-dependent-friction hypothesis the DC level is the physically
     correct regressor, so this matters and is not a detail.
  2. THE ROUTES.  Earlier: r6f + r70 only.  v89_h2: r6d, r6e, r6f, r71, r73 (r70 dropped as
     damper-armed).
  3. THE SPEED CAP.  Earlier: v < 5.2 m/s (parking lot).  v89_h2: none.
  4. ROUTE DUMMIES and an extra Coulomb-identifiability screen.

This walks from the original specification to the new one ONE CHANGE AT A TIME.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[3].parent
OUT = ROOT / "_scratch/cache/r73" / "v89_h3_decompose.json"
RNG = np.random.default_rng(890841)
NW, HOP, FS = 256, 128, 100.0
ALL = {"r6d": "v84", "r6e": "v85", "r6f": "v86", "r70": "v86b", "r71": "v87", "r73": "v88"}
ARMED = {"r70"}


def bandrms(x, lo, hi, exclude=False, demean=True):
    """Hann-windowed one-sided PSD band rms -- IDENTICAL to v89_e1's spec()/brms() pair.
    🛑 The first cut of this function applied NO window. The column torque's low-frequency
    content then leaks into 32-38 Hz and inflates the control band's coefficient."""
    x = x - x.mean() if demean else x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * FS)
    p[1:-1] *= 2.0
    f = np.fft.rfftfreq(len(x), 1.0 / FS)
    m = (f >= lo) & (f < hi)
    if exclude:
        m = ~m
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def harvest():
    rows = []
    for rt in ALL:
        z = np.load(ROOT / ("_cache_" + rt) / (rt + ".npz"), allow_pickle=True)
        n = len(z["t"])
        tq = np.asarray(z["tq"], float)
        ang = np.asarray(z["ang"], float)
        rate = np.asarray(z["rate_c"], float)
        v = np.asarray(z["cs_v"], float)
        eng = np.asarray(z["cc_lat"], float) > 0.5
        sst = np.asarray(z["sstat"], float)
        seg = np.asarray(z["seg"], int) if "seg" in z.files else np.zeros(n, int)
        cmd = np.asarray(z["sc_tq"], float)
        sos = butter(4, 3.0 / (FS / 2), btype="low", output="sos")
        g = np.isfinite(tq)
        lf = np.zeros(n)
        if g.sum() > 30:
            lf[g] = sosfiltfilt(sos, tq[g])
        for s0 in range(0, n - NW + 1, HOP):
            sl = slice(s0, s0 + NW)
            if eng[sl].mean() < 0.999 or (sst[sl] != 0).any():
                continue
            if not (np.isfinite(tq[sl]).all() and np.isfinite(cmd[sl]).all()):
                continue
            vm = float(np.median(v[sl]))
            rm = float(np.median(np.abs(rate[sl])))
            hm = max(float(np.median(np.abs(lf[sl]))), 1e-3)
            if vm <= 0.3 or rm < 1.0 or hm < 1.0:
                continue
            c = cmd[sl]
            raw = float(np.sqrt(np.mean(c ** 2)))
            if raw <= 0:
                continue
            rows.append({"route": rt, "seg": int(np.median(seg[sl])), "i0": s0,
                         "v": vm, "rate": rm, "hands": hm,
                         "cmd_raw": raw,                       # the ORIGINAL regressor (has DC)
                         "cmd_absmean": max(float(np.mean(np.abs(c))), 1e-6),
                         "cmd_ac": max(bandrms(c, 0, 0, exclude=True), 1e-6),   # demeaned
                         "cmd_raw_out69": max(bandrms(c, 6.0, 9.0, exclude=True, demean=False),
                                              1e-6),
                         "e69": max(bandrms(tq[sl], 6.0, 9.0), 1e-9),
                         "e32": max(bandrms(tq[sl], 32.0, 38.0), 1e-9)})
    return rows


def blocks_of(rows):
    blk, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["route"] != last["route"] or r["seg"] != last["seg"]
                                 or r["i0"] - last["i0"] > 3 * HOP):
            cur += 1
        blk.append(cur)
        last = r
    return np.array(blk)


def fit(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def run(rows, xname, yname="e69", dummies=False, nb=2000):
    if len(rows) < 30:
        return None
    blk = blocks_of(rows)
    n = len(rows)
    lx = np.log([r[xname] for r in rows])
    cols = [np.ones(n), lx - lx.mean()]
    for k in ("rate", "v", "hands"):
        a = np.log([r[k] for r in rows])
        cols.append(a - a.mean())
    if dummies:
        rts = sorted({r["route"] for r in rows})
        for rt in rts[1:]:
            cols.append(np.array([1.0 if r["route"] == rt else 0.0 for r in rows]))
    X = np.column_stack(cols)
    y = np.log([r[yname] for r in rows])
    b = fit(X, y)[1]
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    D = []
    for _ in range(nb):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            D.append(fit(X[pick], y[pick])[1])
        except np.linalg.LinAlgError:
            pass
    lo, hi = np.percentile(D, [2.5, 97.5])
    return {"b": float(b), "ci": [float(lo), float(hi)], "n": n, "blocks": int(len(uq))}


def show(lab, r):
    if r is None:
        print("   {:52s}  too few windows".format(lab))
        return
    tag = "EXCLUDES 0" if (r["ci"][0] > 0 or r["ci"][1] < 0) else "NULL"
    print("   {:52s} {:+7.3f} [{:+6.3f},{:+6.3f}]  n={:4d}/{:3d}blk  {}".format(
        lab, r["b"], r["ci"][0], r["ci"][1], r["n"], r["blocks"], tag))


def main():
    rows = harvest()
    rep = {}
    print("=" * 112)
    print("WALK FROM THE ORIGINAL SPEC TO THE NEW ONE, ONE CHANGE AT A TIME  (response: log e_6-9)")
    print("=" * 112)
    orig = [r for r in rows if r["route"] in ("r6f", "r70") and r["v"] < 5.2]
    steps = [
        ("0. ORIGINAL: r6f+r70, v<5.2, cmd_raw, dummies", orig, "cmd_raw", True),
        ("1. + regressor DEMEANED (cmd_ac)", orig, "cmd_ac", True),
        ("2. + regressor = mean|cmd| (the LOAD proxy)", orig, "cmd_absmean", True),
        ("3. ORIGINAL regressor, drop the v<5.2 cap", [r for r in rows if r["route"] in
                                                       ("r6f", "r70")], "cmd_raw", True),
        ("4. ORIGINAL regressor, all 6 routes, v<5.2", [r for r in rows if r["v"] < 5.2],
         "cmd_raw", True),
        ("5. ORIGINAL regressor, all 6 routes, no cap", rows, "cmd_raw", True),
        ("6. as 5 but stock-damper only (drop r70)",
         [r for r in rows if r["route"] not in ARMED], "cmd_raw", True),
        ("7. as 6, regressor DEMEANED", [r for r in rows if r["route"] not in ARMED],
         "cmd_ac", True),
    ]
    for lab, sub, xn, du in steps:
        r = run(sub, xn, dummies=du)
        rep[lab] = r
        show(lab, r)

    print("\n" + "=" * 112)
    print("THE SAME STEPS ON THE 32-38 Hz CONTROL BAND  (a real band-specific effect must NOT")
    print("appear here; if the control band moves with the command too, it is not band-specific)")
    print("=" * 112)
    rep["ctrl"] = {}
    for lab, sub, xn, du in steps:
        r = run(sub, xn, yname="e32", dummies=du)
        rep["ctrl"][lab] = r
        show(lab, r)

    print("\n" + "=" * 112)
    print("BAND CONTRAST (6-9 minus 32-38) at each step -- the statistic that is actually claimed")
    print("=" * 112)
    for lab, sub, xn, du in steps:
        a, b = rep.get(lab), rep["ctrl"].get(lab)
        if a and b:
            print("   {:52s} {:+7.3f}".format(lab, a["b"] - b["b"]))

    print("\n" + "=" * 112)
    print("WHY: what does the speed cap do to the COMMAND's own dynamic range?")
    print("=" * 112)
    for lab, sub in (("v < 5.2 m/s (parking lot)", [r for r in rows if r["v"] < 5.2]),
                     ("v >= 5.2 m/s", [r for r in rows if r["v"] >= 5.2]),
                     ("all", rows)):
        c = np.log([r["cmd_raw"] for r in sub])
        e = np.log([r["e69"] for r in sub])
        print("   {:26s} n={:4d}  sd(log cmd_raw) {:.3f}   sd(log e_6-9) {:.3f}   "
              "corr {:+.3f}".format(lab, len(sub), c.std(), e.std(),
                                    float(np.corrcoef(c, e)[0, 1])))
    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
