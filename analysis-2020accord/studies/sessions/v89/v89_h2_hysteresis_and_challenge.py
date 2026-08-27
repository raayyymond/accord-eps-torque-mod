#!/usr/bin/env python3
"""studies/sessions/v89/v89_h2_hysteresis_and_challenge.py -- the M2 test that does NOT depend on ring-down yield,
plus an attempt to BREAK my own +1.074 command coefficient.

PART A -- THE CHALLENGE (run first, because it can invalidate part of the case for M2).
My earlier result: on 175 engaged windows, log e_6-9 regressed on log|cmd| rms gives
+1.074 [+0.812, +1.445], band contrast +0.950 over the 32-38 Hz control.  The orchestrator calls
that the strongest single support for M2.  Two ways it could be true without load-dependent friction:
  A1 CIRCULARITY.  `|cmd| rms` was taken over the WHOLE band, so it contains the command's own
     6-9 Hz content, and cmd<->column coherence at 7.79 Hz is 0.343.  Regressor and response share
     a component.  FIX: recompute the regressor with 6-9 Hz REMOVED from the command.
  A2 THE MODE'S OWN Q.  A lightly-damped mode (zeta 0.017-0.036, Q 14-29) amplifies ANY broadband
     drive at its resonance and not at 32-38 Hz.  That yields a band-specific magnitude coefficient
     with no friction at all.  Not separable by regression -- stated, not tested.

PART B -- HYSTERESIS WIDTH vs COMMAND.  Independent of edge yield.
Per window fit the standard friction decomposition
     tq = a0 + a1*ang + a2*sgn(rate) + a3*rate
`a2` is the COULOMB half-width (the hysteresis loop half-height), `a3` the viscous term.
     M1 (linear superposition) : width FLAT in command magnitude
     M2 (quasi-harmonic FIV)   : width RISES with command magnitude
`a3` (viscous) is carried as a NEGATIVE CONTROL -- it should not track command under either model.

CONTROLS BEFORE MEASUREMENTS
  K1 recover a KNOWN injected Coulomb width -- validates `a2` as an estimator
  K2 identifiability: reject windows without both rate signs well represented
  K3 block-permutation placebo on the command, before any coefficient is quoted
  K4 the viscous coefficient as a negative control
DAMPER SCREEN: only stock-FactorC routes with an `sc_tq` channel -> r6d/V84, r6e/V85, r6f/V86,
r71/V87, r73/V88.  r75/r76 are FlightV89's and are NOT read.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[3].parent
OUT = ROOT / "_scratch/cache/r73" / "v89_h2_hysteresis.json"
RNG = np.random.default_rng(890840)

NW, HOP, FS = 256, 128, 100.0
ROUTES = {"r6d": "v84", "r6e": "v85", "r6f": "v86", "r71": "v87", "r73": "v88"}


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


def load(rt):
    z = np.load(ROOT / ("_cache_" + rt) / (rt + ".npz"), allow_pickle=True)
    n = len(z["t"])
    return {"tq": np.asarray(z["tq"], float), "ang": np.asarray(z["ang"], float),
            "rate": np.asarray(z["rate_c"], float), "v": np.asarray(z["cs_v"], float),
            "eng": np.asarray(z["cc_lat"], float) > 0.5,
            "sst": np.asarray(z["sstat"], float),
            "seg": (np.asarray(z["seg"], int) if "seg" in z.files else np.zeros(n, int)),
            "cmd": np.asarray(z["sc_tq"], float)}


def coulomb(tq, ang, rate):
    """a2 of tq = a0 + a1*ang + a2*sgn(rate) + a3*rate. Returns (coulomb, viscous) or None."""
    s = np.sign(rate)
    if min((s > 0).mean(), (s < 0).mean()) < 0.20:      # K2 identifiability
        return None
    X = np.column_stack([np.ones(len(tq)), ang - ang.mean(), s, rate])
    if np.linalg.matrix_rank(X) < 4:
        return None
    b = np.linalg.lstsq(X, tq, rcond=None)[0]
    return abs(float(b[2])), abs(float(b[3]))


def harvest():
    rows = []
    for rt in ROUTES:
        D = load(rt)
        n = len(D["tq"])
        sos = butter(4, 3.0 / (FS / 2), btype="low", output="sos")
        g = np.isfinite(D["tq"])
        lf = np.zeros(n)
        if g.sum() > 30:
            lf[g] = sosfiltfilt(sos, D["tq"][g])
        for s0 in range(0, n - NW + 1, HOP):
            sl = slice(s0, s0 + NW)
            if D["eng"][sl].mean() < 0.999 or (D["sst"][sl] != 0).any():
                continue
            if not (np.isfinite(D["tq"][sl]).all() and np.isfinite(D["cmd"][sl]).all()):
                continue
            vm = float(np.median(D["v"][sl]))
            rm = float(np.median(np.abs(D["rate"][sl])))
            if not (0.3 < vm) or rm < 1.0:
                continue
            cw = coulomb(D["tq"][sl], D["ang"][sl], D["rate"][sl])
            if cw is None or cw[0] <= 0 or cw[1] <= 0:
                continue
            c = D["cmd"][sl]
            rows.append({"route": rt, "seg": int(np.median(D["seg"][sl])), "i0": s0,
                         "v": vm, "rate": rm, "hands": max(float(np.median(np.abs(lf[sl]))), 1e-3),
                         "coul": cw[0], "visc": cw[1],
                         "cmd_all": max(bandrms(c, 0, 0, exclude=True), 1e-6),
                         "cmd_out69": max(bandrms(c, 6.0, 9.0, exclude=True), 1e-6),
                         "cmd_lf": max(bandrms(c, 0.5, 5.0), 1e-6),
                         "e69": max(bandrms(D["tq"][sl], 6.0, 9.0), 1e-9),
                         "e32": max(bandrms(D["tq"][sl], 32.0, 38.0), 1e-9)})
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


def model(rows, blk, yname, xname, nb=2000, label=""):
    n = len(rows)
    lx = np.log([r[xname] for r in rows])
    lr = np.log([r["rate"] for r in rows])
    lv = np.log([r["v"] for r in rows])
    lh = np.log([r["hands"] for r in rows])
    cols = [np.ones(n), lx - lx.mean(), lr - lr.mean(), lv - lv.mean(), lh - lh.mean()]
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
    # K3 placebo: permute the regressor across episode blocks
    P = []
    for _ in range(400):
        perm = RNG.permutation(uq)
        xs = np.empty(n)
        for a, c in zip(uq, perm):
            ia, ic = idx[a], idx[c]
            xs[ia] = lx[ic][np.arange(len(ia)) % len(ic)]
        Xp = X.copy()
        Xp[:, 1] = xs - xs.mean()
        P.append(fit(Xp, y)[1])
    p95 = float(np.percentile(np.abs(P), 95))
    tag = "EXCLUDES 0" if (lo > 0 or hi < 0) else "NULL"
    beats = "ABOVE placebo p95" if abs(b) > p95 else "INSIDE placebo"
    print("   {:34s} {:+7.3f} [{:+6.3f},{:+6.3f}]  placebo |b| p95 {:5.3f}  {} / {}".format(
        label or (yname + " ~ " + xname), b, lo, hi, p95, tag, beats))
    return {"b": float(b), "ci": [float(lo), float(hi)], "placebo_p95": p95,
            "verdict": tag, "vs_placebo": beats}


def main():
    rep = {}
    print("=" * 104)
    print("K1 -- CONTROL: can `a2` recover a KNOWN Coulomb width?")
    print("=" * 104)
    for true_c in (5.0, 20.0, 80.0):
        got = []
        for _ in range(300):
            t = np.arange(NW) / FS
            a = 30 * np.sin(2 * np.pi * 0.4 * t + RNG.uniform(0, 6.3))
            rate = np.gradient(a) * FS
            y = (2.0 * a + true_c * np.sign(rate) + 0.4 * rate
                 + 8.0 * RNG.standard_normal(NW))
            r = coulomb(y, a, rate)
            if r:
                got.append(r[0])
        g = np.array(got)
        print("   true Coulomb {:5.1f} ct -> recovered {:6.2f} [{:5.2f}, {:6.2f}]   {}".format(
            true_c, np.median(g), *np.percentile(g, [2.5, 97.5]),
            "PASS" if abs(np.median(g) - true_c) < 0.15 * true_c + 1 else "FAIL"))

    rows = harvest()
    blk = blocks_of(rows)
    print("\n" + "=" * 104)
    print("EXPOSURE -- engaged, moving, identifiable windows on stock-damper routes")
    print("=" * 104)
    for rt in sorted(ROUTES):
        sub = [r for r in rows if r["route"] == rt]
        print("   {:5s} {:6s} {:4d} windows".format(rt, ROUTES[rt], len(sub)))
    print("   TOTAL {} windows / {} episode blocks".format(len(rows), len(np.unique(blk))))
    rep["n"] = len(rows)
    rep["blocks"] = int(len(np.unique(blk)))
    if len(rows) < 40:
        print("   too few -- UNINTERPRETABLE")
        OUT.write_text(json.dumps(rep, indent=1))
        return

    lc = np.log([r["cmd_all"] for r in rows])
    lo69 = np.log([r["cmd_out69"] for r in rows])
    print("\n   corr(log cmd_all, log cmd_out69) = {:+.4f}".format(
        float(np.corrcoef(lc, lo69)[0, 1])))

    print("\n" + "=" * 104)
    print("PART A -- CHALLENGE: does the +1.074 survive removing 6-9 Hz FROM THE COMMAND?")
    print("=" * 104)
    rep["A"] = {}
    for yn, ylab in (("e69", "log e_6-9"), ("e32", "log e_32-38 (control band)")):
        for xn, xlab in (("cmd_all", "|cmd| rms, WHOLE band"),
                         ("cmd_out69", "|cmd| rms EXCLUDING 6-9 Hz"),
                         ("cmd_lf", "|cmd| rms 0.5-5 Hz only")):
            rep["A"][ylab + " ~ " + xlab] = model(
                rows, blk, yn, xn, label="{} ~ {}".format(ylab, xlab))
        print()

    print("=" * 104)
    print("PART B -- HYSTERESIS (Coulomb) WIDTH vs COMMAND MAGNITUDE")
    print("   M1 predicts FLAT.  M2 predicts RISING.  `viscous` is the negative control.")
    print("=" * 104)
    rep["B"] = {}
    for yn, ylab in (("coul", "log COULOMB width"), ("visc", "log VISCOUS (neg. control)")):
        for xn, xlab in (("cmd_all", "|cmd| rms, WHOLE band"),
                         ("cmd_out69", "|cmd| rms EXCLUDING 6-9 Hz")):
            rep["B"][ylab + " ~ " + xlab] = model(
                rows, blk, yn, xn, label="{} ~ {}".format(ylab, xlab))
        print()

    c = np.array([r["coul"] for r in rows])
    print("   Coulomb width distribution: p10 {:.1f}  median {:.1f}  p90 {:.1f} counts".format(
        *np.percentile(c, [10, 50, 90])))
    rep["coulomb_pcts"] = [float(x) for x in np.percentile(c, [10, 50, 90])]

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
