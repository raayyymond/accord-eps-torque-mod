#!/usr/bin/env python3
"""Route 5d (V74, CLEAN) -- the reference population of vertical road excursions, i.e. BUMPS.

🛑 THE AXIS IS `ax`, NOT `az`. Established empirically in `studies/sessions/v74_v75/v74base_imuaxes.py`, not assumed:
   ax  mean +9.70 m/s^2 (carries g), r=0.00 with dv/dt and r=0.02 with yaw*v   -> VERTICAL
   ay  r = 0.38..0.77 with (yaw rate x speed)                                   -> LATERAL
   az  r = -0.56..-0.80 with dv/dt                                              -> LONGITUDINAL
   gx  r = 0.87..0.99 with (steer angle x speed)                                -> YAW rate
   A run over "|az|" would have measured braking, not bumps.

The excursion metric is `vz = ax - movmedian(ax, 2 s)`: a 2 s moving median removes gravity, mount
tilt and road grade while passing anything faster than ~0.5 Hz. A bump EVENT is a local peak of
|vz| above a threshold with a 0.5 s refractory, so one impact counts once.

This file is the INSTRUMENT for the route-61 fault comparison -- run it unchanged there.
"""
import json
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE, PFX, SEGS = "_scratch/cache/r5d", "r5ds", list(range(17))
MEDWIN_S = 2.0
REFRAC_S = 0.5
LEVELS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20]


def movmedian(x, w):
    """Centred moving median, w odd, edge-replicated. Index-based: the lattice is ~101 Hz, +-1%."""
    n = len(x)
    h = w // 2
    xp = np.concatenate([np.full(h, x[0]), x, np.full(h, x[-1])])
    idx = np.arange(n)[:, None] + np.arange(w)[None, :]
    return np.median(xp[idx], axis=1)


def peaks(v, t, thr, refrac):
    """Local maxima of `v` above `thr`, greedily thinned to one per `refrac` seconds."""
    cand = np.flatnonzero((v[1:-1] >= v[:-2]) & (v[1:-1] > v[2:]) & (v[1:-1] >= thr)) + 1
    out, last = [], -np.inf
    for i in cand[np.argsort(-v[cand])]:
        if all(abs(t[i] - t[j]) >= refrac for j in out):
            out.append(i)
    return np.array(sorted(out), int)


def main():
    VZ, T, SEG, V, LAT = [], [], [], [], []
    for s in SEGS:
        im = dict(np.load(f"{CACHE}/{PFX}{s}_imu.npz"))
        cn = dict(np.load(f"{CACHE}/{PFX}{s}.npz"))
        t = im["at"]
        w = int(round(MEDWIN_S / np.median(np.diff(t))))
        w += 1 - w % 2
        vz = im["ax"] - movmedian(im["ax"], w)
        VZ.append(vz); T.append(t); SEG.append(np.full(len(t), s))
        V.append(np.interp(t, cn["t"], cn["cs_v"]))
        LAT.append(np.interp(t, cn["t"], cn["cc_lat"]) > 0.5)
    vz, t, seg, v, lat = map(np.concatenate, (VZ, T, SEG, V, LAT))
    a = np.abs(vz)
    moving = v > 0.5

    print("=" * 90)
    print(f"ROUTE 5d / V74 CLEAN -- vertical excursion vz = ax - movmedian(ax, {MEDWIN_S:g}s)")
    print(f"  n={len(a)} accel samples ({len(a)/101.03:.1f} s), of which moving (vEgo>0.5): "
          f"{int(moving.sum())} ({moving.sum()/101.03:.1f} s)")
    print("=" * 90)

    print("\n--- 6a. |vz| PERCENTILES (m/s^2) --------------------------------------------------")
    print(f"  {'pct':>8} {'all':>9} {'moving':>9} {'engaged':>9} {'manual':>9}")
    for q in (50, 75, 90, 95, 99, 99.9, 99.99, 100):
        r = [np.percentile(a[m], q) for m in
             (np.ones_like(moving), moving, moving & lat, moving & ~lat)]
        print(f"  {q:>8} " + " ".join(f"{x:>9.3f}" for x in r))
    print(f"  {'rms':>8} " + " ".join(
        f"{np.sqrt(np.mean(a[m]**2)):>9.3f}" for m in
        (np.ones_like(moving), moving, moving & lat, moving & ~lat)))

    print("\n--- 6b. HOW MANY BUMPS OF EACH MAGNITUDE DID V74 SURVIVE CLEANLY? ------------------")
    print(f"  events = local peaks of |vz| >= level, {REFRAC_S:g}s refractory, over the WHOLE route")
    print(f"  {'level m/s^2':>12} {'events':>8} {'per min':>9} {'engaged':>8} {'manual':>8} "
          f"{'max v m/s':>10}")
    pk_all = peaks(a, t, LEVELS[0], REFRAC_S)
    for L in LEVELS:
        p = pk_all[a[pk_all] >= L]
        n = len(p)
        if n:
            print(f"  {L:>12} {n:>8} {60.0*n/(len(a)/101.03):>9.2f} "
                  f"{int(lat[p].sum()):>8} {int((~lat[p]).sum()):>8} {v[p].max():>10.2f}")
        else:
            print(f"  {L:>12} {0:>8} {0.0:>9.2f} {0:>8} {0:>8} {'--':>10}")

    print("\n--- 6c. TOP 15 EXCURSIONS ON THE CLEAN DRIVE --------------------------------------")
    top = pk_all[np.argsort(-a[pk_all])][:15]
    print(f"  {'#':>3} {'seg':>4} {'t (s)':>9} {'|vz|':>8} {'vz':>8} {'vEgo':>7} {'lat':>4}")
    for i, k in enumerate(top, 1):
        print(f"  {i:>3} {int(seg[k]):>4} {t[k]:>9.3f} {a[k]:>8.3f} {vz[k]:>8.3f} "
              f"{v[k]:>7.2f} {int(lat[k]):>4}")

    print("\n--- 6d. EXCEEDANCE, for sizing the fault bump -------------------------------------")
    print("  P(|vz| >= x) over MOVING samples, and the rank a fault-drive bump of that size "
          "would hold")
    for x in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15):
        n = int((a[moving] >= x).sum())
        ev = int((a[pk_all] >= x).sum())
        print(f"    >= {x:>2} m/s^2 : {n:>7} samples ({100.0*n/moving.sum():.4f}%), "
              f"{ev:>4} events on 1011 s of clean V74 driving")

    json.dump(dict(n=len(a), pct={str(q): float(np.percentile(a[moving], q))
                                  for q in (50, 90, 99, 99.9, 100)},
                   events={str(L): int((a[pk_all] >= L).sum()) for L in LEVELS},
                   top=[dict(seg=int(seg[k]), t=float(t[k]), vz=float(vz[k]),
                             v=float(v[k]), lat=bool(lat[k])) for k in top]),
              open("v74base_bumps.json", "w"), indent=1)


if __name__ == "__main__":
    main()
