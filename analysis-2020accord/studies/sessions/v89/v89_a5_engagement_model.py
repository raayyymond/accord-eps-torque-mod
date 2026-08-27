#!/usr/bin/env python3
"""studies/sessions/v89/v89_a5_engagement_model.py -- does ENGAGEMENT amplify the 6-9 Hz column mode, and does that
amplification GROW with steering-wheel rate, once route, speed and driver load are controlled?

v89_a4 produced a monotone engaged/manual dose curve (2.09x -> 21.17x with wheel rate) but its
own controls fired twice:
  K2  the arms are NOT load-matched. At 8-50 deg/s the MANUAL arm carries ~9x the sustained
      column torque (1724-1878 ct vs 193-201) -- it is slower, heavier parking. A hard-gripped
      wheel is damped by the driver's arm impedance, which alone could produce the contrast.
  K4  the bins are not route-matched. Only 5 routes contribute any cell and they contribute to
      DIFFERENT bins, so a route/build effect can masquerade as a rate trend.

So the binned contrast cannot carry the claim. This does it with a model instead:

    log e_band  ~  route  +  eng  +  eng x log|rate|  +  log|rate|  +  log v  +  log hands

  `eng`              = the engagement effect at the reference rate
  `eng x log|rate|`  = THE OPERATOR'S CLAIM. > 0 means engagement's amplification grows with
                       how fast the wheel is being turned -- micro-ratcheting becoming ratcheting.

CONTROL: the identical model on the 32-38 Hz negative-control band. A firmware-generated mode
must show a LARGER interaction at 6-9 Hz than at 32-38 Hz; a driver/plant artefact shows the same.
Inference is a block bootstrap over EPISODES, and the headline is the 6-9 minus 32-38 CONTRAST.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[3].parent
OUT = ROOT / "_scratch/cache/r73" / "v89_a5_engagement_model.json"
RNG = np.random.default_rng(890505)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088


def order_hits(v, lo, hi, nmax=6):
    if v <= 0.05:
        return False
    for circ in (CIRC_LO, CIRC_HI):
        for n in range(1, nmax + 1):
            if lo <= n * v / circ < hi:
                return True
    return False


def spec(x, fs):
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    return np.fft.rfftfreq(len(x), 1.0 / fs), p


def brms(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def load_windows():
    rows = []
    seen = set()          # 🛑 _scratch/cache/r66 and _scratch/cache/r66x hold the SAME route. Glob by ROUTE.
    for c in sorted(ROOT.glob("_cache_r*/r*.npz")):
        if "s" in c.stem[1:] or c.stem in seen:
            continue
        seen.add(c.stem)
        z = np.load(c, allow_pickle=True)
        if not {"t", "tq", "rate_c", "cc_lat", "cs_v", "sstat", "seg"} <= set(z.files):
            continue
        t = np.asarray(z["t"], float)
        fs = 1.0 / float(np.median(np.diff(t)))
        if not (80 < fs < 130):
            continue
        tq = np.asarray(z["tq"], float)
        rate = np.asarray(z["rate_c"], float)
        v = np.asarray(z["cs_v"], float)
        eng = np.asarray(z["cc_lat"], float) > 0.5
        sst = np.asarray(z["sstat"], float)
        seg = np.asarray(z["seg"], int)
        sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
        g = np.isfinite(tq)
        tq_lf = np.zeros_like(tq)
        if g.sum() > 30:
            tq_lf[g] = sosfiltfilt(sos, tq[g])
        for s in range(0, len(t) - NW + 1, HOP):
            sl = slice(s, s + NW)
            e = eng[sl].mean()
            if not (e > 0.98 or e < 0.02):
                continue
            if (sst[sl] != 0).any() or not np.isfinite(tq[sl]).all():
                continue
            vm = float(np.median(v[sl]))
            rm = float(np.median(np.abs(rate[sl])))
            hm = float(np.median(np.abs(tq_lf[sl])))
            if not (0.3 < vm < 8.0) or rm < 1.0 or hm < 1.0:
                continue
            if order_hits(vm, 6.0, 9.0) or order_hits(vm, 32.0, 38.0):
                continue
            f, p = spec(tq[sl], fs)
            e69, e32 = brms(f, p, 6.0, 9.0), brms(f, p, 32.0, 38.0)
            if e69 <= 0 or e32 <= 0:
                continue
            rows.append({"route": c.stem, "seg": int(np.median(seg[sl])), "i0": s,
                         "eng": 1.0 if e > 0.98 else 0.0, "v": vm, "rate": rm, "hands": hm,
                         "e69": e69, "e32": e32})
    return rows


def design(rows, routes):
    n = len(rows)
    lr = np.log([r["rate"] for r in rows])
    lr_c = lr - lr.mean()                        # centre so `eng` reads at the MEAN rate
    eng = np.array([r["eng"] for r in rows])
    cols = [np.ones(n), eng, eng * lr_c, lr_c,
            np.log([r["v"] for r in rows]), np.log([r["hands"] for r in rows])]
    names = ["const", "eng", "eng x log rate", "log rate", "log v", "log hands"]
    for rt in routes[1:]:
        cols.append(np.array([1.0 if r["route"] == rt else 0.0 for r in rows]))
        names.append(f"route[{rt}]")
    return np.column_stack(cols), names, lr_c


def blocks(rows):
    b, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r["route"] != last["route"] or r["seg"] != last["seg"]
                                 or r["i0"] - last["i0"] > 3 * HOP or r["eng"] != last["eng"]):
            cur += 1
        b.append(cur)
        last = r
    return np.array(b)


def main():
    rows = load_windows()
    routes = sorted({r["route"] for r in rows})
    print(f"{len(rows)} windows, {len(routes)} routes, "
          f"{int(sum(r['eng'] for r in rows))} engaged / {int(sum(1-r['eng'] for r in rows))} manual")
    # how much overlap is there actually? the model can only work inside the common support
    for arm, lab in ((1.0, "engaged"), (0.0, "manual")):
        a = [r for r in rows if r["eng"] == arm]
        print(f"  {lab:8s} n={len(a):5d}  |rate| p10/50/90 = "
              f"{np.percentile([r['rate'] for r in a], [10, 50, 90]).round(1)}  "
              f"hands p10/50/90 = {np.percentile([r['hands'] for r in a], [10, 50, 90]).round(0)}  "
              f"v p10/50/90 = {np.percentile([r['v'] for r in a], [10, 50, 90]).round(2)}")

    X, names, lr_c = design(rows, routes)
    y69 = np.log([r["e69"] for r in rows])
    y32 = np.log([r["e32"] for r in rows])
    fit = lambda y, Xm=X: np.linalg.lstsq(Xm, y, rcond=None)[0]
    b69, b32 = fit(y69), fit(y32)

    blk = blocks(rows)
    uq = np.unique(blk)
    idx = {g: np.where(blk == g)[0] for g in uq}
    D69, D32, DC_eng, DC_int = [], [], [], []
    for _ in range(3000):
        pick = np.concatenate([idx[g] for g in RNG.choice(uq, len(uq), replace=True)])
        try:
            a = fit(y69[pick], X[pick])
            b = fit(y32[pick], X[pick])
        except np.linalg.LinAlgError:
            continue
        D69.append(a)
        D32.append(b)
        DC_eng.append(a[1] - b[1])
        DC_int.append(a[2] - b[2])
    D69, D32 = np.array(D69), np.array(D32)

    print(f"\n  {len(uq)} episode blocks")
    print("\n" + "=" * 88)
    print("MODEL  log e_band ~ route + eng + eng x log|rate| + log|rate| + log v + log hands")
    print("=" * 88)
    print(f"  {'term':18s} {'6-9 Hz (ratchet)':>28s} {'32-38 Hz (control)':>28s}")
    rep = {"n": len(rows), "routes": routes, "blocks": int(len(uq)), "terms": {}}
    for i, nm in enumerate(names[:6]):
        c69 = [np.percentile(D69[:, i], 2.5), np.percentile(D69[:, i], 97.5)]
        c32 = [np.percentile(D32[:, i], 2.5), np.percentile(D32[:, i], 97.5)]
        print(f"  {nm:18s} {b69[i]:+8.3f} [{c69[0]:+7.3f},{c69[1]:+7.3f}] "
              f"{b32[i]:+8.3f} [{c32[0]:+7.3f},{c32[1]:+7.3f}]")
        rep["terms"][nm] = {"b69": float(b69[i]), "ci69": [float(x) for x in c69],
                            "b32": float(b32[i]), "ci32": [float(x) for x in c32]}

    ce = [np.percentile(DC_eng, 2.5), np.percentile(DC_eng, 97.5)]
    ci_ = [np.percentile(DC_int, 2.5), np.percentile(DC_int, 97.5)]
    print("\n  THE HEADLINE CONTRASTS (6-9 minus 32-38, same windows, same model)")
    print(f"    eng             {b69[1]-b32[1]:+8.3f} [{ce[0]:+7.3f},{ce[1]:+7.3f}]  "
          f"{'EXCLUDES 0' if ce[0] > 0 or ce[1] < 0 else 'includes 0'}")
    print(f"    eng x log rate  {b69[2]-b32[2]:+8.3f} [{ci_[0]:+7.3f},{ci_[1]:+7.3f}]  "
          f"{'EXCLUDES 0' if ci_[0] > 0 or ci_[1] < 0 else 'includes 0'}")
    rep["contrast"] = {"eng": {"d": float(b69[1] - b32[1]), "ci": [float(x) for x in ce]},
                       "eng_x_lograte": {"d": float(b69[2] - b32[2]),
                                         "ci": [float(x) for x in ci_]}}

    # translate the interaction into the operator's language
    print("\n  WHAT THE INTERACTION MEANS -- engagement's 6-9 Hz amplification vs wheel rate")
    rmean = np.exp(np.mean(np.log([r["rate"] for r in rows])))
    print(f"    (reference |rate| = geometric mean = {rmean:.1f} deg/s)")
    rep["amplification"] = []
    for rate in (2, 5, 10, 20, 50, 100):
        lg = np.log(rate) - np.log(rmean)
        amp69 = np.exp(b69[1] + b69[2] * lg)
        amp32 = np.exp(b32[1] + b32[2] * lg)
        dr = np.exp(D69[:, 1] + D69[:, 2] * lg)
        print(f"    |rate| {rate:4d} deg/s : engaged/manual 6-9 Hz = {amp69:6.2f}x "
              f"[{np.percentile(dr,2.5):5.2f}, {np.percentile(dr,97.5):6.2f}]   "
              f"control {amp32:5.2f}x")
        rep["amplification"].append({"rate": rate, "amp69": float(amp69),
                                     "ci": [float(np.percentile(dr, 2.5)),
                                            float(np.percentile(dr, 97.5))],
                                     "amp32": float(amp32)})

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
