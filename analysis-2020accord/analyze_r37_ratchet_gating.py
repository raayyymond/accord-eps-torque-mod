#!/usr/bin/env python3
"""Is the ~7.4 Hz ratchet still LKAS-gated on V62, and is it now at road speed?

Deliverable 1 and 3 of the ratchet brief. Two things are done differently from the sweep that
produced the headline numbers:

  * EPISODES, not windows. Windows inside one contiguous engaged run share the same physical
    event; counting them as independent inflates n several-fold. Every contrast below is reported
    both ways.
  * PHYSICAL AMPLITUDE next to every prominence (band RMS and envelope p99, in torque counts), so
    a large ratio in a quiet window cannot masquerade as a large oscillation.

Segment 0 IS included (10:11:03-10:12:05, mostly a manual creep arm at large angle) -- it is the
population the engaged-vs-manual contrast most needs. Its PARK frames are excluded from the manual
arm: a stationary car in park is not a steering-load control for a moving car in drive.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402
import _r37_ratchet_lib as L  # noqa: E402

DRIVE, REVERSE = 2.0, 4.0


def arms(cache, pfx, segs, vlo, vhi, elo=0.0, ehi=1e9, gears=(DRIVE,)):
    """(engaged, manual) window records in a speed/effort/gear cell."""
    def mk(want_lat):
        def f(d):
            fs = C.fs_of(d)
            eff = C.sustained(d["tq"], fs)
            # Route 2b/2c/31 caches predate cs_gear. Those routes have no reverse/park stretches
            # in the cells used here, so "no gear channel" is treated as "gear passes".
            g = (np.isin(d["cs_gear"], list(gears)) if "cs_gear" in d
                 else np.ones(len(d["t"]), bool))
            lat = d["cc_lat"] > 0.5
            return ((lat if want_lat else ~lat) & g &
                    (d["cs_v"] >= vlo) & (d["cs_v"] < vhi) &
                    (np.abs(eff) >= elo) & (np.abs(eff) < ehi))
        return f
    return (L.collect(cache, pfx, segs, mask_fn=mk(True)),
            L.collect(cache, pfx, segs, mask_fn=mk(False)))


def line(lbl, rs):
    if not rs:
        return f"    {lbl:26s}  nwin=0  nep=0"
    eps = L.episodes(rs)
    pr = np.array([r["pr"] for r in rs])
    fr = np.array([r["fr"] for r in rs])
    rms = np.array([r["rms_r"] for r in rs])
    env = np.array([r["env_r"] for r in rs])
    pw = np.array([r["pow_r"] for r in rs])
    # per-episode statistic: the episode's own median, so long episodes don't dominate
    ep_pr = np.array([np.median([x["pr"] for x in e]) for e in eps])
    ep_rms = np.array([np.median([x["rms_r"] for x in e]) for e in eps])
    pres = float(np.mean(pr >= 10))
    return (f"    {lbl:26s}  nwin={len(rs):4d} nep={len(eps):3d} | "
            f"f0 {np.nanmedian(fr):5.2f} sd {np.nanstd(fr):4.2f} | "
            f"prom w-p50 {np.nanmedian(pr):8.1f} ep-p50 {np.nanmedian(ep_pr):8.1f} | "
            f"RMS {np.nanmedian(rms):7.1f} ep {np.nanmedian(ep_rms):7.1f} | "
            f"env99 {np.nanmedian(env):7.1f} | pow {np.nanmedian(pw):9.3g} | "
            f"pres {100*pres:5.1f}%")


def contrast(name, cache, pfx, segs, cells):
    print(f"\n{'='*150}\n{name}\n{'='*150}")
    for lbl, kw in cells:
        e, m = arms(cache, pfx, segs, **kw)
        print(f"  --- {lbl} ---")
        print(line("ENGAGED", e))
        print(line("MANUAL", m))
        if e and m:
            pe = np.nanmedian([r["pow_r"] for r in e])
            pm = np.nanmedian([r["pow_r"] for r in m])
            re_ = np.nanmedian([r["rms_r"] for r in e])
            rm = np.nanmedian([r["rms_r"] for r in m])
            qe = np.nanmedian([r["pr"] for r in e])
            qm = np.nanmedian([r["pr"] for r in m])
            print(f"    {'RATIO eng/man':26s}  power {pe/max(pm,1e-30):8.1f}x   "
                  f"RMS {re_/max(rm,1e-9):6.1f}x   prominence {qe/max(qm,1e-9):7.1f}x")


def main():
    cache, pfx, segs = C.ROOT / "_cache_r37", "r37s", list(range(0, 15))

    contrast("ROUTE 37 (V62) -- engaged vs manual, DRIVE gear only", cache, pfx, segs, [
        ("creep 0.3-2.5 m/s", dict(vlo=0.3, vhi=2.5)),
        ("creep 0.3-2.5 m/s, effort 200-1000", dict(vlo=0.3, vhi=2.5, elo=200, ehi=1000)),
        ("2.5-6 m/s", dict(vlo=2.5, vhi=6.0)),
        ("6-12 m/s", dict(vlo=6.0, vhi=12.0)),
        ("12-20 m/s", dict(vlo=12.0, vhi=20.0)),
        (">20 m/s", dict(vlo=20.0, vhi=40.0)),
    ])

    # reverse gear is its own arm -- historically the ratchet was absent there
    print("\n  --- REVERSE gear, any speed (historically ratchet-free) ---")
    e, m = arms(cache, pfx, segs, 0.0, 40.0, gears=(REVERSE,))
    print(line("ENGAGED", e))
    print(line("MANUAL", m))

    # ---- where does the manual exposure actually live? ---------------------------------------
    print(f"\n{'='*150}\nMANUAL EXPOSURE INVENTORY (drive gear), route 37 -- what the control arm "
          f"is made of\n{'='*150}")
    print(f"  {'seg':>3s} {'manual s':>9s} {'v>0.3 s':>9s} {'v>2.5 s':>9s} {'v>6 s':>8s} "
          f"{'|ang| p95':>10s} {'eff p50':>8s}")
    for s in segs:
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        dt = 1 / fs
        man = (d["cc_lat"] <= 0.5) & (d["cs_gear"] == DRIVE)
        if not man.any():
            continue
        eff = np.abs(C.sustained(d["tq"], fs))
        print(f"  {s:3d} {man.sum()*dt:9.1f} {(man & (d['cs_v'] > 0.3)).sum()*dt:9.1f} "
              f"{(man & (d['cs_v'] > 2.5)).sum()*dt:9.1f} "
              f"{(man & (d['cs_v'] > 6)).sum()*dt:8.1f} "
              f"{np.percentile(np.abs(d['ang'][man]), 95):10.1f} "
              f"{np.median(eff[man]):8.0f}")

    # ---- the same gating test on every earlier build ------------------------------------------
    print(f"\n{'='*150}\nCROSS-BUILD: engaged vs manual at creep (0.3-2.5 m/s, DRIVE)\n{'='*150}")
    for nm, ca, pf, sg in L.ROUTES:
        e, m = arms(ca, pf, sg, 0.3, 2.5)
        print(f"  {nm}")
        print(line("  ENGAGED", e))
        print(line("  MANUAL", m))


if __name__ == "__main__":
    main()
