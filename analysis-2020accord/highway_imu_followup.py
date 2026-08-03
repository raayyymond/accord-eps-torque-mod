#!/usr/bin/env python3
"""§2b -- the IMU 30-49 Hz event concentration on V67, taken apart before it is believed.

§2 of highway_event_hunt.py found, at threshold 10x the Kd=1 speed-band median:

    ay 40-49 Hz   Kd1  0 | Kd2  1 | Kd2.44 17
    gz 40-49 Hz   Kd1  0 | Kd2  1 | Kd2.44 15
    gx 40-49 Hz   Kd1  1 | Kd2  4 | Kd2.44 13
    ay 30-40 Hz   Kd1  1 | Kd2  2 | Kd2.44 15

🛑 THE CONFOUND THAT COULD BE ALL OF IT. Route 47 (V67) holds 623.8 s above 28 m/s; the whole
Kd=1 pool holds 39.2 s and Kd=2 holds 118.3 s. If the events live at the top of the speed range,
the "dose effect" is an EXPOSURE effect, and the >28 m/s threshold is estimated from 39 s of one
route. This file tests exactly that, plus:

  * per-ROUTE counts, so one route cannot be a pool
  * SPEED-MATCHED rates, restricted to bands every dose actually visited
  * a split-half null inside a single dose with the identical estimator
  * co-occurrence: are ay/gx/gz firing on the SAME instants (one physical event) or independently?
  * f0 vs speed on the IMU lattice -- MODE or ORDER
  * the alias arithmetic at 40-49 Hz on a ~101 Hz lattice

Usage:  python highway_imu_followup.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _r47_imu_lib as I            # noqa: E402
import highway_event_hunt as H      # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_hwy_imu_followup.json"
AXES = ["ay", "gx", "gz", "ax", "az", "gy"]
FOCUS = [("ay", "40-49"), ("gz", "40-49"), ("gx", "40-49"), ("ay", "30-40"), ("gz", "30-40")]


def main():
    irecs = H.collect_imu()
    print(f"[{len(irecs)} IMU segments]")
    store = {}

    # ---------------------------------------------------------------- 1. exposure by route ------
    H.G.hdr("1.  ENGAGED-HIGHWAY EXPOSURE ON THE IMU LATTICE, per route and speed band")
    expo_rt, expo_kd = {}, {}
    print(f"{'rt':<5}{'bld':<5}{'Kd':>5}" + "".join(f"{f'{a:g}-{b:g}':>10}" for a, b in H.V_BANDS))
    for r in irecs:
        n = min(len(r["a_v"]), len(r["a_lat"]))
        v, lat, odr = r["a_v"][:n], r["a_lat"][:n], r["ax_odr"]
        for i, (a, b) in enumerate(H.V_BANDS):
            s = float(((v >= a) & (v < b) & (lat > 0.5)).sum()) / odr
            expo_rt.setdefault(r["route"], np.zeros(len(H.V_BANDS)))[i] += s
            expo_kd.setdefault(r["kd"], np.zeros(len(H.V_BANDS)))[i] += s
    for rt in sorted(expo_rt):
        kd = H.KD[rt]
        print(f"{rt:<5}{H.BUILD[rt]:<5}{kd:>5.2f}" + "".join(f"{x:10.1f}" for x in expo_rt[rt]))
    print("-" * 60)
    for kd in sorted(expo_kd):
        print(f"{'POOL':<5}{'':<5}{kd:>5.2f}" + "".join(f"{x:10.1f}" for x in expo_kd[kd]))
    store["exposure"] = {str(k): list(np.round(v, 1)) for k, v in expo_kd.items()}

    # ---------------------------------------------------------------- 2. where do events live ---
    H.G.hdr("2.  THE EVENTS' OWN SPEED DISTRIBUTION -- is the 'dose effect' an EXPOSURE effect?")
    allev = {}
    for ax, band in FOCUS:
        f50 = H.imu_floor(irecs, ax, band, q=50)
        evs = H.imu_events(irecs, ax, band, {i: 10 * f50[i] for i in f50})
        allev[(ax, band)] = evs
        print(f"\n  {ax} {band} Hz   floor(10x med) per band: "
              + "  ".join(f"{f'{a:g}-{b:g}'}:{10 * f50[i]:.4g}"
                          for i, (a, b) in enumerate(H.V_BANDS)))
        print(f"    {'route':<7}{'Kd':>5}{'n':>5}   " + "".join(
            f"{f'{a:g}-{b:g}':>10}" for a, b in H.V_BANDS) + "   (events per speed band)")
        for rt in sorted({e["route"] for e in evs} | set(expo_rt)):
            c = np.zeros(len(H.V_BANDS))
            for e in evs:
                if e["route"] == rt:
                    c[H.vbin(e["v"])] += 1
            if c.sum() == 0 and rt not in expo_rt:
                continue
            print(f"    {rt:<7}{H.KD[rt]:>5.2f}{int(c.sum()):>5}   "
                  + "".join(f"{int(x):10d}" for x in c))
        # rate per hour, per speed band, per dose -- the exposure-corrected view
        print(f"    {'RATE/h':<7}{'':<5}{'':>5}   " + "".join(
            f"{f'{a:g}-{b:g}':>10}" for a, b in H.V_BANDS))
        for kd in sorted(expo_kd):
            c = np.zeros(len(H.V_BANDS))
            for e in evs:
                if e["kd"] == kd:
                    c[H.vbin(e["v"])] += 1
            rr = [3600 * c[i] / expo_kd[kd][i] if expo_kd[kd][i] > 20 else np.nan
                  for i in range(len(H.V_BANDS))]
            print(f"    {'Kd':<7}{kd:>5.2f}{'':>5}   "
                  + "".join(f"{x:10.1f}" if np.isfinite(x) else f"{'--':>10}" for x in rr))
        store.setdefault("by_speed", {})[f"{ax}|{band}"] = {
            str(kd): [int(sum(1 for e in evs if e["kd"] == kd and H.vbin(e["v"]) == i))
                      for i in range(len(H.V_BANDS))] for kd in sorted(expo_kd)}

    # ---------------------------------------------------------------- 3. speed-MATCHED rate -----
    H.G.hdr("3.  SPEED-MATCHED EVENT RATE, restricted to bands EVERY dose visited (>=60 s each)\n"
            "    Blocks of 20 s are the bootstrap unit; the ratio is stratified by speed band.")
    store["matched"] = {}
    for ax, band in FOCUS:
        evs = allev[(ax, band)]
        bl = imu_blocks(irecs, evs, ax)
        ok = [i for i in range(len(H.V_BANDS))
              if all(expo_kd.get(k, np.zeros(4))[i] >= 60 for k in (1.0, 2.0, 2.44))]
        print(f"\n  {ax} {band} Hz   speed bands with >=60 s on EVERY dose: "
              + (", ".join(f"{H.V_BANDS[i][0]:g}-{H.V_BANDS[i][1]:g}" for i in ok) or "NONE"))
        for a, b in ((2.44, 1.0), (2.44, 2.0), (2.0, 1.0)):
            r, lo, hi, na, nb, ea, eb = block_ratio(bl, a, b, ok, RNG)
            print(f"      Kd {a:g}/{b:g}   rate ratio {r:8.3f}  [{lo:.3f}, {hi:.3f}]   "
                  f"events {na:3d} vs {nb:3d}   exposure {ea:6.0f} s vs {eb:6.0f} s")
            store["matched"].setdefault(f"{ax}|{band}", {})[f"{a:g}/{b:g}"] = dict(
                ratio=r, lo=lo, hi=hi, nA=na, nB=nb, expA=ea, expB=eb)
        n1 = split_half(bl, 2.0, ok, RNG)
        print(f"      SPLIT-HALF NULL inside the Kd=2 pool: {n1[0]:.3f} [{n1[1]:.3f}, {n1[2]:.3f}]"
              f"  (n={n1[3]})")
        store["matched"][f"{ax}|{band}"]["null_kd2"] = list(n1[:3])

    # ---------------------------------------------------------------- 4. co-occurrence ----------
    H.G.hdr("4.  CO-OCCURRENCE -- are ay / gx / gz firing on the SAME instants?")
    keyed = {k: [(e["route"], e["seg"], e["t"]) for e in v] for k, v in allev.items()}
    ks = [("ay", "40-49"), ("gz", "40-49"), ("gx", "40-49")]
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            A, B = keyed[ks[i]], keyed[ks[j]]
            hit = sum(1 for a in A if any(b[0] == a[0] and b[1] == a[1] and abs(b[2] - a[2]) < 1.0
                                          for b in B))
            print(f"    {ks[i][0]} vs {ks[j][0]}  ({len(A)} vs {len(B)} events): "
                  f"{hit} of {len(A)} co-occur within 1.0 s")
    store["cooccur"] = {f"{a[0]}|{b[0]}": None for a in ks for b in ks}

    # ---------------------------------------------------------------- 5. mode vs order ----------
    H.G.hdr("5.  MODE vs ORDER on the IMU: f0 of each event vs speed, free 10-49 Hz argmax")
    store["mode"] = {}
    for ax, band in FOCUS:
        evs = allev[(ax, band)]
        f0s, vs, ords = [], [], []
        for e in evs:
            r = irecs[e["rec"]]
            env_key = (ax, band)
            if env_key not in r:
                continue
            g = ax[0]
            # rebuild the uniform series for this axis to take a spectrum at the peak
            u = r.get("_u_" + ax)
            if u is None:
                p = ROOT / dict((x[0], x[1]) for x in H.ROUTES)[r["route"]] / \
                    f"{dict((x[0], x[2]) for x in H.ROUTES)[r['route']]}{r['seg']}_imu.npz"
                di = dict(np.load(p))
                t = di["at"] if g == "a" else di["gt"]
                u = I.uniform(t, di[ax])[0]
                r["_u_" + ax] = u
            fs = r[ax + "_odr"]
            n = H.NFFT
            a0 = max(0, min(len(u) - n, e["ipk"] - n // 2))
            P = I.periodogram(u[a0:a0 + n], fs, n, True)
            if P is None:
                continue
            f = np.fft.rfftfreq(n, 1 / fs)
            f0, _ = I.locate(f, P, 10.0, 49.5)
            if not np.isfinite(f0):
                continue
            f0s.append(f0)
            vs.append(e["v"])
            ords.append(f0 * H.CIRC / e["v"])
        if len(f0s) < 6:
            print(f"  {ax} {band}: n={len(f0s)} -- too few")
            continue
        s, lo, hi, ic, n = H.theil_sen(np.array(vs), np.array(f0s), RNG, 600)
        print(f"  {ax} {band} Hz  n={n}  f0 p50 {np.median(f0s):.2f} Hz  sd {np.std(f0s):.2f}  "
              f"speed {np.min(vs):.1f}-{np.max(vs):.1f} m/s")
        print(f"      Theil-Sen slope {s:+.4f} Hz/(m/s)  [{lo:+.4f}, {hi:+.4f}]  intercept "
              f"{ic:.2f} Hz   implied order p50 {np.median(ords):.2f} (sd {np.std(ords):.2f})")
        for o in (1, 2, 3, 4):
            q = o / H.CIRC
            if lo <= q <= hi:
                print(f"        ⚠ wheel order {o} (slope {q:.3f}) is INSIDE the CI")
        print(f"        slope 0 (pure MODE): "
              f"{'INSIDE' if lo <= 0 <= hi else 'EXCLUDED BY'} the CI")
        store["mode"][f"{ax}|{band}"] = dict(n=n, slope=s, lo=lo, hi=hi, intercept=ic,
                                             f0_p50=float(np.median(f0s)),
                                             f0_sd=float(np.std(f0s)),
                                             order_p50=float(np.median(ords)))

    # ---------------------------------------------------------------- 6. alias ------------------
    H.G.hdr("6.  THE ALIAS, stated honestly")
    odrs = [r["ax_odr"] for r in irecs] + [r["gx_odr"] for r in irecs]
    print(f"    IMU lattice ODR: p50 {np.median(odrs):.3f} Hz, range "
          f"{np.min(odrs):.3f}-{np.max(odrs):.3f}  => Nyquist {np.median(odrs) / 2:.2f} Hz")
    print(f"    CAN grid: 100.000 Hz exactly => Nyquist 50.00 Hz")
    for fo in (40.0, 45.0, 49.0):
        fam = ", ".join(f"{x:.1f}" for x in I and
                        sorted({fo, np.median(odrs) - fo, np.median(odrs) + fo,
                                2 * np.median(odrs) - fo, 2 * np.median(odrs) + fo}))
        print(f"      an apparent {fo:.0f} Hz line is indistinguishable from: {fam} Hz")
    print("    ⇒ a FIXED apparent pitch is consistent with EITHER a true sub-50 Hz mode OR an\n"
          "      aliased higher one. Neither CAN nor the IMU can separate them. The microphone\n"
          "      is the only channel in this kit without the ceiling.")

    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


def imu_blocks(irecs, evs, ax, sec=20.0):
    """20 s contiguous blocks of engaged-highway IMU exposure with their event counts."""
    g = ax[0]
    by = {}
    for e in evs:
        by.setdefault((e["rec"],), []).append(e)
    out = []
    for ri, r in enumerate(irecs):
        n = min(len(r[g + "_v"]), len(r[g + "_lat"]))
        v, lat, odr = r[g + "_v"][:n], r[g + "_lat"][:n], r[ax + "_odr"]
        m = (v >= H.VMIN) & (lat > 0.5)
        if not m.any():
            continue
        w = int(sec * odr)
        for a in range(0, n, w):
            sl = slice(a, min(a + w, n))
            k = int(m[sl].sum())
            if k < w // 2:
                continue
            hits = sum(1 for e in by.get((ri,), []) if a <= e["ipk"] < a + w)
            out.append(dict(kd=r["kd"], route=r["route"], expo=k / odr, hit=hits,
                            vbin=H.vbin(float(np.mean(v[sl][m[sl]])))))
    return out


def block_ratio(bl, kdA, kdB, ok, rng, nboot=3000):
    A = [b for b in bl if b["kd"] == kdA and b["vbin"] in ok]
    B = [b for b in bl if b["kd"] == kdB and b["vbin"] in ok]

    def est(X, Y):
        num = den = 0.0
        for i in ok:
            a = [x for x in X if x["vbin"] == i]
            b = [x for x in Y if x["vbin"] == i]
            if len(a) < 3 or len(b) < 3:
                continue
            ra = (sum(x["hit"] for x in a) + 0.5) / max(sum(x["expo"] for x in a), 1e-9)
            rb = (sum(x["hit"] for x in b) + 0.5) / max(sum(x["expo"] for x in b), 1e-9)
            w = 1.0 / (1.0 / len(a) + 1.0 / len(b))
            num += w * np.log(ra / rb)
            den += w
        return num / den if den else np.nan
    p = est(A, B)
    if not (A and B):
        return np.nan, np.nan, np.nan, 0, 0, 0.0, 0.0
    dr = np.full(nboot, np.nan)
    for k in range(nboot):
        dr[k] = est([A[i] for i in rng.integers(0, len(A), len(A))],
                    [B[i] for i in rng.integers(0, len(B), len(B))])
    lo = float(np.exp(np.nanpercentile(dr, 2.5))) if np.isfinite(dr).any() else np.nan
    hi = float(np.exp(np.nanpercentile(dr, 97.5))) if np.isfinite(dr).any() else np.nan
    return (float(np.exp(p)), lo, hi, sum(x["hit"] for x in A), sum(x["hit"] for x in B),
            sum(x["expo"] for x in A), sum(x["expo"] for x in B))


def split_half(bl, kd, ok, rng, nrep=400):
    P = [b for b in bl if b["kd"] == kd and b["vbin"] in ok]
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(P))
        h = len(P) // 2
        a = [P[i] for i in idx[:h]]
        b = [P[i] for i in idx[h:]]
        for x in a:
            x["_k"] = 1
        for x in b:
            x["_k"] = 2
        v = block_ratio([dict(x, kd=x["_k"]) for x in a + b], 1, 2, ok, rng, nboot=0)[0]
        if np.isfinite(v) and v > 0:
            out.append(v)
    if not out:
        return np.nan, np.nan, np.nan, 0
    o = np.array(out)
    return (float(np.exp(np.median(np.log(o)))), float(np.percentile(o, 2.5)),
            float(np.percentile(o, 97.5)), len(o))


if __name__ == "__main__":
    main()
