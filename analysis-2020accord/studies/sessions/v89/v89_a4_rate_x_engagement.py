#!/usr/bin/env python3
"""studies/sessions/v89/v89_a4_rate_x_engagement.py -- the operator's axis, measured properly.

THE MEASUREMENT
    At MATCHED steering-wheel rate, how much does ENGAGING LKAS multiply the 6-9 Hz column
    torque?  The operator's phenomenology says that multiplier should GROW with wheel rate:
        micro-ratcheting = engaged + spinning the wheel AT ALL
        ratcheting       = engaged + spinning the wheel QUICKLY

WHY THIS CONTRAST AND NOT THE OTHERS (all tried first, all recorded)
  - v89_a1's band-specificity was an ARTEFACT: it order-vetoed each band on a different window
    set. On matched windows (v89_a2 T2) all three bands respond to rate at ~the same slope
    (+0.49 / +0.39 / +0.40, contrast CI includes 0). Spinning the wheel raises the WHOLE column
    spectrum, so a rate slope alone cannot separate the firmware from the driver.
  - v89_a3's coherence attribution is CONFOUNDED: `gp-0x6b98` is the TOTAL motor command, base
    assist included, and base assist is a function of column torque. Its 6-9 Hz coherence with
    the column is 0.254 engaged but 0.544 MANUAL, where the LKAS command is identically absent.
    That is loop feedthrough, not attribution. Dropped.
  - ENGAGED-vs-MANUAL at matched rate is immune to both: the driver's own broadband excitation
    is held fixed by the matching, and engagement is the only thing that changes.

CONTROLS
  K1  negative control band 32-38 Hz -- the SAME contrast; a firmware effect must not appear there
  K2  hands-on check -- both arms must have the driver's hands on the wheel at matched rate,
      else "engaged" is confounded with grip damping. Proxy: sustained (<3 Hz) |column torque|.
  K3  speed distributions reported per bin, both arms
  K4  wheel-order veto, and a per-route breakdown (pooling builds could manufacture the trend)
  K5  episode bootstrap CIs -- never window bootstraps
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[3].parent
OUT = ROOT / "_scratch/cache/r73" / "v89_a4_rate_x_engagement.json"
RNG = np.random.default_rng(890404)

NW, HOP = 256, 128
CIRC_LO, CIRC_HI = 2.073, 2.088
RATE_BINS = [(1, 3), (3, 8), (8, 20), (20, 50), (50, 1e9)]
V_LO, V_HI = 0.3, 8.0


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


def windows(path):
    z = np.load(path, allow_pickle=True)
    need = {"t", "tq", "rate_c", "cc_lat", "cs_v", "sstat", "seg", "ang"}
    if not need <= set(z.files):
        return None, []
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    if not (80 < fs < 130):
        return None, []
    tq = np.asarray(z["tq"], float)
    rate = np.asarray(z["rate_c"], float)
    v = np.asarray(z["cs_v"], float)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    sst = np.asarray(z["sstat"], float)
    seg = np.asarray(z["seg"], int)
    ang = np.asarray(z["ang"], float)

    # K2 hands-on proxy: sustained (<3 Hz) column torque magnitude
    sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
    good = np.isfinite(tq)
    tq_lf = np.zeros_like(tq)
    if good.sum() > 30:
        tq_lf[good] = sosfiltfilt(sos, tq[good])

    rows = []
    for s in range(0, len(t) - NW + 1, HOP):
        sl = slice(s, s + NW)
        e = eng[sl].mean()
        if not (e > 0.98 or e < 0.02):
            continue
        if (sst[sl] != 0).any() or not np.isfinite(tq[sl]).all():
            continue
        vm = float(np.median(v[sl]))
        if not (V_LO < vm < V_HI):
            continue
        f, p = spec(tq[sl], fs)
        rows.append({"i0": s, "seg": int(np.median(seg[sl])), "engaged": bool(e > 0.98),
                     "v_med": vm,
                     "rate_med": float(np.median(np.abs(rate[sl]))),
                     "hands": float(np.median(np.abs(tq_lf[sl]))),
                     "ang_ptp": float(np.ptp(ang[sl])),
                     "e69": brms(f, p, 6.0, 9.0),
                     "e32": brms(f, p, 32.0, 38.0),
                     "veto69": order_hits(vm, 6.0, 9.0),
                     "veto32": order_hits(vm, 32.0, 38.0)})
    return fs, rows


def blocks(rows):
    b, cur, last = [], 0, None
    for r in rows:
        if last is not None and (r.get("route") != last.get("route")
                                 or r["seg"] != last["seg"] or r["i0"] - last["i0"] > 3 * HOP):
            cur += 1
        b.append(cur)
        last = r
    return np.array(b)


def ratio_ci(e_rows, m_rows, key, n=4000):
    """Median(engaged)/median(manual) with an episode bootstrap on BOTH arms."""
    ev = np.array([r[key] for r in e_rows])
    mv = np.array([r[key] for r in m_rows])
    eb, mb = blocks(e_rows), blocks(m_rows)
    ue, um = np.unique(eb), np.unique(mb)
    if len(ue) < 2 or len(um) < 2:
        return float(np.median(ev) / np.median(mv)), None, None, len(ue), len(um)
    draws = []
    ie = {g: np.where(eb == g)[0] for g in ue}
    im = {g: np.where(mb == g)[0] for g in um}
    for _ in range(n):
        pe = np.concatenate([ie[g] for g in RNG.choice(ue, len(ue), replace=True)])
        pm = np.concatenate([im[g] for g in RNG.choice(um, len(um), replace=True)])
        draws.append(np.median(ev[pe]) / max(np.median(mv[pm]), 1e-9))
    return (float(np.median(ev) / np.median(mv)),
            float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)),
            len(ue), len(um))


def main():
    caches = [p for p in sorted(ROOT.glob("_cache_r*/r*.npz"))
              if p.stem[1:].isdigit() or (len(p.stem) <= 4 and p.stem.startswith("r"))]
    caches = [p for p in sorted(ROOT.glob("_cache_r*/r*.npz")) if "s" not in p.stem[1:]]
    pool = []
    per_route = {}
    for c in caches:
        fs, rows = windows(c)
        if not rows:
            continue
        for r in rows:
            r["route"] = c.stem
        per_route[c.stem] = rows
        pool += rows
    print(f"loaded {len(per_route)} routes, {len(pool)} windows "
          f"({sum(r['engaged'] for r in pool)} engaged)")
    rep = {"routes": {k: len(v) for k, v in per_route.items()}, "n_windows": len(pool)}

    # ------------------------------------------------------------ headline
    print("\n" + "=" * 92)
    print("ENGAGED / MANUAL ratio of 6-9 Hz COLUMN TORQUE, at MATCHED |steer rate|   (all routes)")
    print("=" * 92)
    print(f"  {'|rate| deg/s':>13s} {'n_eng':>6s} {'n_man':>6s} "
          f"{'v eng':>6s} {'v man':>6s} {'hands e':>8s} {'hands m':>8s} "
          f"{'RATIO 6-9':>22s} {'ctrl 32-38':>20s}")
    rep["headline"] = []
    for lo, hi in RATE_BINS:
        e = [r for r in pool if r["engaged"] and lo <= r["rate_med"] < hi and not r["veto69"]]
        m = [r for r in pool if not r["engaged"] and lo <= r["rate_med"] < hi and not r["veto69"]]
        lab = f"{lo:.0f}-{hi:.0f}" if hi < 1e8 else f"{lo:.0f}+"
        if len(e) < 5 or len(m) < 5:
            print(f"  {lab:>13s} {len(e):6d} {len(m):6d}   -- insufficient")
            rep["headline"].append({"lo": lo, "hi": hi, "n_eng": len(e), "n_man": len(m),
                                    "ratio": None})
            continue
        r69, lo69, hi69, be, bm = ratio_ci(e, m, "e69")
        ec = [r for r in e if not r["veto32"]]
        mc = [r for r in m if not r["veto32"]]
        r32, lo32, hi32, _, _ = ratio_ci(ec, mc, "e32") if len(ec) >= 5 and len(mc) >= 5 \
            else (float("nan"), None, None, 0, 0)
        ci69 = f"[{lo69:5.2f},{hi69:6.2f}]" if lo69 else "[--]"
        ci32 = f"[{lo32:5.2f},{hi32:6.2f}]" if lo32 else "[--]"
        print(f"  {lab:>13s} {len(e):6d} {len(m):6d} "
              f"{np.median([r['v_med'] for r in e]):6.2f} {np.median([r['v_med'] for r in m]):6.2f} "
              f"{np.median([r['hands'] for r in e]):8.0f} "
              f"{np.median([r['hands'] for r in m]):8.0f} "
              f"{r69:8.2f}x {ci69:>13s} {r32:6.2f}x {ci32:>13s}")
        rep["headline"].append({
            "lo": lo, "hi": hi, "n_eng": len(e), "n_man": len(m),
            "blocks_eng": be, "blocks_man": bm,
            "v_eng": float(np.median([r["v_med"] for r in e])),
            "v_man": float(np.median([r["v_med"] for r in m])),
            "hands_eng": float(np.median([r["hands"] for r in e])),
            "hands_man": float(np.median([r["hands"] for r in m])),
            "ratio69": r69, "ci69": [lo69, hi69],
            "ratio32": r32, "ci32": [lo32, hi32]})

    # ------------------------------------------------------------ K4 per route
    print("\n" + "=" * 92)
    print("K4  PER-ROUTE -- the trend must not be an artefact of pooling different builds")
    print("=" * 92)
    rep["per_route"] = {}
    for rt, rows in sorted(per_route.items()):
        cells = []
        for lo, hi in RATE_BINS:
            e = [r for r in rows if r["engaged"] and lo <= r["rate_med"] < hi and not r["veto69"]]
            m = [r for r in rows if not r["engaged"] and lo <= r["rate_med"] < hi
                 and not r["veto69"]]
            cells.append(f"{np.median([r['e69'] for r in e])/np.median([r['e69'] for r in m]):7.1f}x"
                         if len(e) >= 4 and len(m) >= 4 else "      --")
        if all(c.strip() == "--" for c in cells):
            continue
        print(f"  {rt:8s} " + " ".join(cells))
        rep["per_route"][rt] = cells
    print(f"  {'bins:':8s} " + " ".join(f"{(f'{lo:.0f}-{hi:.0f}' if hi<1e8 else f'{lo:.0f}+'):>8s}"
                                        for lo, hi in RATE_BINS))

    # ------------------------------------------------------------ engaged-only dose
    print("\n" + "=" * 92)
    print("THE ENGAGED DOSE CURVE alone (what the operator feels), 6-9 Hz, order-vetoed")
    print("=" * 92)
    rep["engaged_dose"] = []
    for lo, hi in RATE_BINS:
        e = [r for r in pool if r["engaged"] and lo <= r["rate_med"] < hi and not r["veto69"]]
        if len(e) < 5:
            continue
        vals = np.array([r["e69"] for r in e])
        b = blocks(e)
        u = np.unique(b)
        idx = {g: np.where(b == g)[0] for g in u}
        dr = [np.median(vals[np.concatenate([idx[g] for g in RNG.choice(u, len(u), replace=True)])])
              for _ in range(3000)] if len(u) >= 2 else []
        lab = f"{lo:.0f}-{hi:.0f}" if hi < 1e8 else f"{lo:.0f}+"
        ci = f"[{np.percentile(dr,2.5):7.1f}, {np.percentile(dr,97.5):7.1f}]" if dr else ""
        print(f"  |rate| {lab:>8s} deg/s  n={len(e):4d} ({len(u):3d} episodes)  "
              f"e_6-9 = {np.median(vals):8.1f} {ci}")
        rep["engaged_dose"].append({"lo": lo, "hi": hi, "n": len(e), "episodes": int(len(u)),
                                    "e69": float(np.median(vals)),
                                    "ci": [float(np.percentile(dr, 2.5)),
                                           float(np.percentile(dr, 97.5))] if dr else None})

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
