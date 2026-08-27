#!/usr/bin/env python3
"""T2 (the angle-RATE deficit) and T3 (the engaged-vs-manual impedance asymmetry), route 67 / V81.

The two operator claims under test, quoted:
  (4) "LKAS steering angle RATE is severely limited -- very slow angle rate. LKAS steering TORQUE is
      high because the angle error/range is larger than normal. openpilot is DEMANDING a higher
      angle rate and not getting it."
  (5) "Manual steering feels much HARDER when LKAS is engaged than when disengaged -- even when the
      driver turns in the SAME direction as the LKAS torque command."

🛑🛑 THE CORRECTION THAT MAKES THIS TABLE MEAN ANYTHING -- read it before any number below.
The RAW `rate_c` is NOT a measure of how fast the driver/LKAS is turning the wheel: on a route with
a 20-30 Hz torsional oscillation, the instantaneous rate is dominated by the OSCILLATION. A 28 Hz
line of only +/-0.5 deg amplitude carries a peak rate of 2*pi*28*0.5 = 88 deg/s -- larger than any
real steering input at motorway speed. The first cut of this script reported V80's engaged ">80 kph
p50 rate = 48 deg/s" and a 10x impedance drop, both of which were the limit cycle, not steering.
⇒ EVERY rate and impedance number here is computed on `rate_lf` = d/dt of the 3 Hz-lowpassed
  column angle (per SEGMENT, zero-phase), and `tq_lf` = the 3 Hz-lowpassed torsion bar -- the kit's
  own `sustained()` convention. The oscillation is reported separately as `hf` and never enters a
  denominator.
🛑 SENTINELS: route 5e (V75) carries `rate_c` = 32767 frames. Any |rate| > 1000 deg/s or
  |ang| > 1000 deg is dropped as a sentinel, counted, and reported.

CHANNELS, and why each one -- [EVIDENCE] from the Honda DBC in `reference/opendbc/honda/carstate.py`
  ACHIEVED rate   `rate_c` = STEERING_SENSORS (0x14A) STEER_ANGLE_RATE. This is literally
                  `carState.steeringRateDeg`. Quantised to 1 deg/s. `rate_lf` (see above) is
                  derived from `ang` (STEER_ANGLE, 0.1 deg) and is what every table uses.
  DRIVER torque   `tq` = STEER_STATUS (0x18F) STEER_TORQUE_SENSOR = `carState.steeringTorque`. The
                  TORSION BAR, i.e. the driver's own twist, upstream of the motor.
  COMMAND         `sc_tq` = the STEER_TORQUE field openpilot puts on 0x0E4 (sendcan). Its sign
                  convention against `tq` is MEASURED here, not assumed -- see `command_sign()`.
  DEMAND          `ct_dcurv` = controlsState.desiredCurvature [1/m] -> a desired COLUMN angle by the
                  steady-state bicycle model delta = kappa * WB * SR (the same model `_r47_lib`
                  uses forward), and its time derivative is the demanded column rate.
                  ⚠ THIS IS AN APPROXIMATION AND IT IS THE WEAKEST LINK IN T2. openpilot on this
                  car is a TORQUE controller: it never commands an angle rate. "Demanded rate" here
                  means "the rate at which openpilot's own target angle is moving", which is the
                  thing the column has to track. Marked [BELIEF] wherever the conclusion rests on
                  the bicycle model; the achieved-rate CEILING (T2c) rests on no model at all.

🛑 A raw engaged-vs-manual comparison is confounded: you steer less on a motorway. Every comparison
here is MATCHED -- on speed cell, and for T3 additionally on |angle| and on the sign of the driver's
own torque. CIs resample EPISODES (contiguous engagement runs), and every effect is quoted against
a SPLIT-HALF NULL of the same estimator inside the same build.

Usage:  python studies/loop-causality/r67_v81_t2t3.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

STEER_RATIO = 16.33
WHEELBASE = 2.83
KMH = 1.0 / 3.6

ROUTES = {
    "V81/r67": (ROOT / "_scratch/cache/r67x", "r67xs", list(range(14)), [13]),
    "V80/r66": (ROOT / "_scratch/cache/r66x", "r66xs", list(range(15)), []),
    "V76/r65": (ROOT / "_scratch/cache/r65", "r65s", list(range(11)), [0, 10]),
    "V75/r5e": (ROOT / "_scratch/cache/r5e_sym", "r5es", [0, 1, 2, 3, 4], [0]),
}
ORDER = ["V76/r65", "V75/r5e", "V81/r67", "V80/r66"]
STRATA = [("creep <10 kph", 0.0, 10 * KMH), ("10-40 kph", 10 * KMH, 40 * KMH),
          ("40-80 kph", 40 * KMH, 80 * KMH), (">80 kph", 80 * KMH, 1e9)]
RNG = np.random.default_rng(8167)
OUT = {}


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def segments(build):
    cache, pfx, segs, parked = ROUTES[build]
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists() or s in parked:
            continue
        yield s, {k: v for k, v in np.load(p).items()}


SENTINEL_RATE = 1000.0        # deg/s -- route 5e carries rate_c = 32767
SENTINEL_ANG = 1000.0         # deg


def lowpass(x, fs, fc=3.0):
    """Zero-phase lowpass, NaN-guarded. Applied PER SEGMENT so a segment join cannot ring."""
    y = np.asarray(x, float).copy()
    bad = ~np.isfinite(y)
    if bad.all() or len(y) < 8:
        return y
    if bad.any():
        y[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), y[~bad])
    mu = y.mean()
    X = np.fft.rfft(y - mu)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    X[f > fc] = 0.0
    return np.fft.irfft(X, n=len(y)) + mu


def bandenv(x, fs, lo, hi):
    """Analytic-signal envelope of x restricted to [lo, hi] Hz -- the oscillation AMPLITUDE."""
    y = np.asarray(x, float).copy()
    bad = ~np.isfinite(y)
    if bad.all() or len(y) < 8:
        return np.full(len(y), np.nan)
    if bad.any():
        y[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), y[~bad])
    X = np.fft.rfft(y - y.mean())
    f = np.fft.rfftfreq(len(y), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(y)))


def episodes_of(mask, min_n=50):
    m = np.asarray(mask, bool).astype(np.int8)
    e = np.diff(np.concatenate(([0], m, [0])))
    return [(a, b) for a, b in zip(np.flatnonzero(e > 0), np.flatnonzero(e < 0))
            if b - a >= min_n]


def gather(build):
    """One flat frame table per build, plus an episode id per frame (engaged runs and manual runs
    are separate episodes; a segment boundary always breaks an episode)."""
    cols = {}
    nep = 0
    nsent = 0
    for s, d in segments(build):
        n = len(d["t"])
        fs = 1.0 / np.median(np.diff(d["t"]))
        lat = d["cc_lat"] > 0.5
        ang = np.asarray(d["ang"], float).copy()
        rate = np.asarray(d["rate_c"], float).copy()
        bad = (np.abs(rate) > SENTINEL_RATE) | (np.abs(ang) > SENTINEL_ANG)
        nsent += int(bad.sum())
        ang[bad] = np.nan
        rate[bad] = np.nan
        ang_lf = lowpass(ang, fs, 3.0)
        tq_lf = lowpass(d["tq"], fs, 3.0)
        sc_lf = lowpass(d["sc_tq"], fs, 3.0) if "sc_tq" in d else np.full(n, np.nan)
        loc = dict(
            t=d["t"], seg=np.full(n, s, float), v=np.abs(d["cs_v"]), lat=lat.astype(float),
            ang=ang, rate=rate, tq=np.asarray(d["tq"], float),
            sc=d.get("sc_tq", np.full(n, np.nan)),
            ang_lf=ang_lf, rate_lf=np.gradient(ang_lf) * fs, tq_lf=tq_lf, sc_lf=sc_lf,
            ang_hf=bandenv(ang, fs, 5.0, 49.0), tq_hf=bandenv(d["tq"], fs, 5.0, 49.0),
            e4=d["e4tq"], press=d.get("cs_press", np.zeros(n)),
            fs=np.full(n, fs, float), sstat=d["sstat"], sent=bad.astype(float),
        )
        for k in ("cs_brake", "ct_dcurv", "cc_curv", "cs_rate", "cs_yaw", "cs_lchg", "imu_vert",
                  "damp_nz", "thermo", "g6ac2"):
            loc[k] = d[k] if k in d else np.full(n, np.nan)
        loc["dem_ang"] = (lowpass(np.asarray(d["ct_dcurv"], float), fs, 3.0)
                          * WHEELBASE * STEER_RATIO * 180.0 / np.pi
                          if "ct_dcurv" in d else np.full(n, np.nan))
        loc["dem_rate"] = np.gradient(loc["dem_ang"]) * fs
        # episode ids: contiguous runs of the engagement mask inside one segment
        ids = np.full(n, -1.0)
        for pol in (True, False):
            for a, b in episodes_of(lat == pol, min_n=25):
                nep += 1
                ids[a:b] = nep
        loc["ep"] = ids
        for k, v in loc.items():
            cols.setdefault(k, []).append(np.asarray(v, float))
    out = {k: np.concatenate(v) for k, v in cols.items()}
    out["__sentinels__"] = nsent
    return out


def command_sign(D):
    """MEASURE the sign convention of `sc_tq` against the achieved column rate. [EVIDENCE]

    Engaged + hands-off (|tq_lf| small) frames only: correlate the lowpassed command with the
    lowpassed achieved rate. The returned +/-1 makes `s * sc_lf > 0` mean 'the LKAS command pushes
    the column in the direction a POSITIVE `tq` would'.
    """
    m = ((D["lat"] > 0.5) & (np.abs(D["tq_lf"]) < 100) & np.isfinite(D["sc_lf"])
         & np.isfinite(D["rate_lf"]))
    if m.sum() < 1000:
        return np.nan, int(m.sum())
    return float(np.corrcoef(D["sc_lf"][m], D["rate_lf"][m])[0, 1]), int(m.sum())


def qstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return dict(n=0)
    return dict(n=int(len(x)), p50=float(np.percentile(x, 50)), p90=float(np.percentile(x, 90)),
                p99=float(np.percentile(x, 99)), p999=float(np.percentile(x, 99.9)),
                max=float(x.max()), mean=float(x.mean()))


def ep_boot(vals, eps, stat=np.median, nboot=2000, rng=RNG):
    """(point, lo, hi, n_episodes) resampling EPISODES with replacement."""
    vals, eps = np.asarray(vals, float), np.asarray(eps, float)
    ok = np.isfinite(vals)
    vals, eps = vals[ok], eps[ok]
    if not len(vals):
        return np.nan, np.nan, np.nan, 0
    per = [vals[eps == u] for u in np.unique(eps)]
    pt = float(stat(vals))
    if nboot <= 1:
        return pt, np.nan, np.nan, len(per)
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        v = np.concatenate([per[j] for j in rng.integers(0, len(per), len(per))])
        if len(v):
            dr[b] = stat(v)
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), len(per)


def split_half(vals, eps, stat=np.median, nrep=300, rng=RNG):
    """The estimator's own noise floor: halve THIS pool's episodes and take the ratio.

    An effect inside this interval is not distinguishable from route/exposure noise.
    """
    vals, eps = np.asarray(vals, float), np.asarray(eps, float)
    ok = np.isfinite(vals)
    vals, eps = vals[ok], eps[ok]
    uniq = np.unique(eps)
    if len(uniq) < 4:
        return np.nan, np.nan, np.nan
    per = [vals[eps == u] for u in uniq]
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(per))
        h = len(per) // 2
        a = np.concatenate([per[i] for i in idx[:h]])
        b = np.concatenate([per[i] for i in idx[h:]])
        if len(a) and len(b):
            sa, sb = stat(a), stat(b)
            if sb > 0:
                out.append(sa / sb)
    out = np.array(out, float)
    if not len(out):
        return np.nan, np.nan, np.nan
    return (float(np.median(out)), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def ratio_boot(vA, eA, vB, eB, stat=np.median, nboot=1500, rng=RNG):
    """Ratio of two pooled statistics, both episode-resampled."""
    vA, eA, vB, eB = (np.asarray(x, float) for x in (vA, eA, vB, eB))
    okA, okB = np.isfinite(vA), np.isfinite(vB)
    vA, eA, vB, eB = vA[okA], eA[okA], vB[okB], eB[okB]
    if not len(vA) or not len(vB):
        return np.nan, np.nan, np.nan
    pa, pb = float(stat(vA)), float(stat(vB))
    if pb == 0:
        return np.nan, np.nan, np.nan
    perA = [vA[eA == u] for u in np.unique(eA)]
    perB = [vB[eB == u] for u in np.unique(eB)]
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        a = np.concatenate([perA[j] for j in rng.integers(0, len(perA), len(perA))])
        c = np.concatenate([perB[j] for j in rng.integers(0, len(perB), len(perB))])
        if len(a) and len(c):
            sb = stat(c)
            if sb > 0:
                dr[b] = stat(a) / sb
    return pa / pb, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def p99(x):
    return float(np.percentile(x, 99))


# =================================================================================================
def main():
    D = {b: gather(b) for b in ORDER}
    print("  sentinel frames dropped (|rate| > 1000 or |ang| > 1000): "
          + ", ".join(f"{b} {D[b]['__sentinels__']}" for b in ORDER))
    for b in ORDER:
        D[b].pop("__sentinels__", None)

    hdr("T2a  ACHIEVED STEERING RATE `rate_lf` (3 Hz-lowpassed column angle, differentiated) --\n"
        "     ENGAGED vs MANUAL, matched on speed cell.  NOT the raw STEER_ANGLE_RATE: that is\n"
        "     dominated by the 20-30 Hz oscillation.  hf = 5-49 Hz angle envelope = the vibration.")
    OUT["t2a"] = {}
    for b in ORDER:
        d = D[b]
        print(f"\n  ---- {b} ----")
        print(f"     {'stratum':14s} {'mode':8s} {'n':>7s} {'sec':>6s} | "
              f"{'p50':>6s} {'p90':>6s} {'p99':>7s} {'max':>7s} | {'|ang| p50':>9s} "
              f"{'hf ang p50':>10s} {'hf ang p99':>10s}")
        for nm, lo, hi in STRATA:
            base = (d["v"] >= lo) & (d["v"] < hi)
            for mode, mm in (("ENGAGED", base & (d["lat"] > 0.5)),
                             ("manual", base & (d["lat"] <= 0.5))):
                r = np.abs(d["rate_lf"][mm])
                r = r[np.isfinite(r)]
                if len(r) < 200:
                    print(f"     {nm:14s} {mode:8s} {int(mm.sum()):7d}  -- too few --")
                    continue
                q = qstat(r)
                hf = np.abs(d["ang_hf"][mm])
                print(f"     {nm:14s} {mode:8s} {q['n']:7d} {q['n'] / 100.0:6.1f} | "
                      f"{q['p50']:6.2f} {q['p90']:6.1f} {q['p99']:7.1f} {q['max']:7.1f} | "
                      f"{np.nanmedian(np.abs(d['ang'][mm])):9.1f} "
                      f"{np.nanpercentile(hf, 50):10.3f} {np.nanpercentile(hf, 99):10.3f}")
                OUT["t2a"].setdefault(b, {})[f"{nm}|{mode}"] = q

    hdr("T2b  THE SAME STATISTIC ACROSS BUILDS -- ENGAGED only.  If V81's rate ceiling were lower\n"
        "     than V76's, the limiter would localise to what V81/V75 have and V76 lacks.")
    print(f"  {'stratum':14s} " + " ".join(f"{b.split('/')[0]:>28s}" for b in ORDER))
    OUT["t2b_cross"] = {}
    for nm, lo, hi in STRATA:
        cells = []
        for b in ORDER:
            d = D[b]
            m = (d["v"] >= lo) & (d["v"] < hi) & (d["lat"] > 0.5)
            r = np.abs(d["rate_lf"][m])
            r = r[np.isfinite(r)]
            if len(r) < 200:
                cells.append("   n/a (n=%5d)          " % len(r))
                continue
            cells.append("p50%5.2f p90%6.1f p99%6.1f" % (np.percentile(r, 50),
                                                         np.percentile(r, 90),
                                                         np.percentile(r, 99)))
            OUT["t2b_cross"][f"{b}|{nm}"] = qstat(r)
        print(f"  {nm:14s} " + " ".join(f"{c:>28s}" for c in cells))

    print("\n  ENGAGED/MANUAL ratio of p99 |rate_lf| inside each speed cell.  <1 = engaged turns\n"
          "  SLOWER.  Read each point against its own split-half null.")
    OUT["t2b"] = {}
    for b in ORDER:
        d = D[b]
        for nm, lo, hi in STRATA:
            base = (d["v"] >= lo) & (d["v"] < hi) & np.isfinite(d["rate_lf"])
            me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
            if me.sum() < 500 or mm.sum() < 500:
                continue
            rr = ratio_boot(np.abs(d["rate_lf"][me]), d["ep"][me],
                            np.abs(d["rate_lf"][mm]), d["ep"][mm], stat=p99)
            nl = split_half(np.abs(d["rate_lf"][me]), d["ep"][me], stat=p99)
            verdict = ("OUTSIDE null" if (np.isfinite(nl[1]) and
                                          (rr[0] < nl[1] or rr[0] > nl[2])) else "inside null")
            print(f"    {b:10s} {nm:14s} eng/man p99 = {rr[0]:6.3f} [{rr[1]:6.3f},{rr[2]:6.3f}]"
                  f"   null [{nl[1]:6.3f},{nl[2]:6.3f}]  {verdict}  "
                  f"nE={int(me.sum())} nM={int(mm.sum())}")
            OUT["t2b"][f"{b}|{nm}"] = dict(ratio=list(rr), null=list(nl),
                                           nE=int(me.sum()), nM=int(mm.sum()))

    hdr("T2c  IS THERE A HARD CEILING IN deg/s?  Tail of ENGAGED |rate_lf|.  A firmware rate limit\n"
        "     shows as a PILE-UP at one value; a soft limit as a bent tail; no limit as a smooth\n"
        "     tail whose top is set by the biggest manoeuvre asked for.")
    for b in ORDER:
        d = D[b]
        r = np.abs(d["rate_lf"][d["lat"] > 0.5])
        r = r[np.isfinite(r)]
        top = np.sort(r)[-10:][::-1]
        print(f"  {b:10s} n={len(r):6d}  p99.0={np.percentile(r,99):6.1f} "
              f"p99.9={np.percentile(r,99.9):6.1f} p99.99={np.percentile(r,99.99):6.1f} "
              f"max={r.max():6.1f}   top-10 {np.round(top,1).tolist()}")

    hdr("T2d  DEMANDED vs ACHIEVED steering rate -- V81/r67 only (controlsState.desiredCurvature\n"
        "     is not in the older caches).  [BELIEF where it rests on the bicycle model.]")
    d = D["V81/r67"]
    m = (d["lat"] > 0.5) & np.isfinite(d["dem_rate"]) & np.isfinite(d["rate_lf"])
    err = d["dem_ang"] - d["ang_lf"]
    print(f"  engaged frames with a finite demand: {int(m.sum())}")
    print(f"  |demanded column angle| p50 {np.nanpercentile(np.abs(d['dem_ang'][m]),50):7.2f} deg  "
          f"p90 {np.nanpercentile(np.abs(d['dem_ang'][m]),90):7.2f}  "
          f"p99 {np.nanpercentile(np.abs(d['dem_ang'][m]),99):8.2f}")
    print(f"  |achieved  column angle| p50 {np.nanpercentile(np.abs(d['ang_lf'][m]),50):7.2f} deg  "
          f"p90 {np.nanpercentile(np.abs(d['ang_lf'][m]),90):7.2f}  "
          f"p99 {np.nanpercentile(np.abs(d['ang_lf'][m]),99):8.2f}")
    print(f"  |tracking error|         p50 {np.nanpercentile(np.abs(err[m]),50):7.2f} deg  "
          f"p90 {np.nanpercentile(np.abs(err[m]),90):7.2f}  "
          f"p99 {np.nanpercentile(np.abs(err[m]),99):8.2f}")
    print("\n  TRANSFER -- bin frames by |demanded rate|; report the achieved rate in those frames.")
    print(f"  {'|demanded| deg/s':>18s} {'n':>7s} {'med|dem|':>9s} {'med|ach|':>9s} "
          f"{'p90|ach|':>9s} {'ach/dem':>8s} {'med|err|deg':>12s} {'med|cmd|ct':>11s} "
          f"{'cmd sat %':>9s}")
    EDGES = [0, 0.5, 1, 2, 4, 8, 16, 32, 1e9]
    OUT["t2d"] = []
    for a, b_ in zip(EDGES[:-1], EDGES[1:]):
        mm = m & (np.abs(d["dem_rate"]) >= a) & (np.abs(d["dem_rate"]) < b_)
        if mm.sum() < 100:
            continue
        ach, dem = np.abs(d["rate_lf"][mm]), np.abs(d["dem_rate"][mm])
        row = dict(lo=a, hi=min(b_, 999), n=int(mm.sum()), dem50=float(np.median(dem)),
                   ach50=float(np.median(ach)), ach90=float(np.percentile(ach, 90)),
                   ratio=float(np.median(ach) / max(np.median(dem), 1e-9)),
                   err50=float(np.nanmedian(np.abs(err[mm]))),
                   cmd50=float(np.nanmedian(np.abs(d["sc"][mm]))),
                   sat=float(np.nanmean(np.abs(d["sc"][mm]) > 3800) * 100))
        print(f"  {('%.1f-%.1f' % (a, min(b_, 99))):>18s} {row['n']:7d} {row['dem50']:9.2f} "
              f"{row['ach50']:9.2f} {row['ach90']:9.2f} {row['ratio']:8.2f} {row['err50']:12.2f} "
              f"{row['cmd50']:11.0f} {row['sat']:9.1f}")
        OUT["t2d"].append(row)
    print("\n  Per-speed-stratum, ENGAGED:")
    for nm, lo, hi in STRATA:
        mm = m & (d["v"] >= lo) & (d["v"] < hi)
        if mm.sum() < 300:
            continue
        print(f"    {nm:14s} n={int(mm.sum()):6d} | |dem| p50 "
              f"{np.median(np.abs(d['dem_rate'][mm])):6.2f} p90 "
              f"{np.percentile(np.abs(d['dem_rate'][mm]),90):7.2f} | |ach| p50 "
              f"{np.median(np.abs(d['rate_lf'][mm])):6.2f} p90 "
              f"{np.percentile(np.abs(d['rate_lf'][mm]),90):7.2f} | ach/dem p50 "
              f"{np.median(np.abs(d['rate_lf'][mm])) / max(np.median(np.abs(d['dem_rate'][mm])),1e-9):5.2f}"
              f" | |err| p50 {np.nanmedian(np.abs(err[mm])):6.2f} | |cmd| p50 "
              f"{np.nanmedian(np.abs(d['sc'][mm])):5.0f} "
              f"sat {np.nanmean(np.abs(d['sc'][mm]) > 3800) * 100:4.1f}%")

    hdr("T2e  COMMAND SIGN CONVENTION -- measured, not assumed.")
    SIGN = {}
    for b in ORDER:
        c, n = command_sign(D[b])
        SIGN[b] = 1.0 if (np.isfinite(c) and c > 0) else -1.0
        print(f"  {b:10s} corr(sc_lf, rate_lf) on engaged hands-off = {c:+.4f}  n={n}  "
              f"=> s={SIGN[b]:+.0f}")
    OUT["sign"] = {b: SIGN[b] for b in ORDER}

    hdr("T3  IMPEDANCE = |tq_lf| per deg/s of |rate_lf| -- how HEAVY the wheel is.  ENGAGED vs\n"
        "    MANUAL, matched on speed AND |angle|.  Frames restricted to the driver actually\n"
        "    steering: |tq_lf| > 300 counts AND |rate_lf| >= 2 deg/s.  ratio > 1 = HEAVIER engaged.")
    ANG_BINS = [(0.0, 5.0), (5.0, 20.0), (20.0, 1e9)]
    OUT["t3"] = {}
    for b in ORDER:
        d = D[b]
        act = (np.abs(d["tq_lf"]) > 300) & (np.abs(d["rate_lf"]) >= 2.0)
        imp = np.where(act, np.abs(d["tq_lf"]) / np.maximum(np.abs(d["rate_lf"]), 1e-9), np.nan)
        print(f"\n  ---- {b} ----")
        print(f"     {'stratum':14s} {'|ang|':>8s} {'nE':>6s} {'nM':>6s} | {'eng':>7s} {'man':>7s}"
              f" | {'ratio [95% CI]':>24s} | {'split-half null':>18s} | verdict")
        for nm, lo, hi in STRATA:
            for alo, ahi in ANG_BINS:
                base = act & (d["v"] >= lo) & (d["v"] < hi) & \
                    (np.abs(d["ang"]) >= alo) & (np.abs(d["ang"]) < ahi)
                me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
                if me.sum() < 200 or mm.sum() < 200:
                    continue
                rr = ratio_boot(imp[me], d["ep"][me], imp[mm], d["ep"][mm])
                nl = split_half(imp[me], d["ep"][me])
                v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (rr[0] < nl[1] or rr[0] > nl[2]))
                     else "inside null")
                tag = f"{alo:.0f}-{ahi:.0f}" if ahi < 1e8 else f">{alo:.0f}"
                print(f"     {nm:14s} {tag:>8s} {int(me.sum()):6d} {int(mm.sum()):6d} | "
                      f"{np.nanmedian(imp[me]):7.1f} {np.nanmedian(imp[mm]):7.1f} | "
                      f"{rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:6.3f}] | "
                      f"[{nl[1]:6.3f},{nl[2]:6.3f}] | {v}")
                OUT["t3"].setdefault(b, {})[f"{nm}|{tag}"] = dict(
                    ratio=list(rr), null=list(nl), nE=int(me.sum()), nM=int(mm.sum()),
                    eng=float(np.nanmedian(imp[me])), man=float(np.nanmedian(imp[mm])))

    hdr("T3b  THE SAME-DIRECTION TEST (operator claim 5, exactly as stated).  ENGAGED frames split\n"
        "     by whether the DRIVER's torque agrees in sign with the LKAS command, each compared to\n"
        "     MANUAL at matched speed.  If assisting torque in the driver's OWN direction still\n"
        "     reads HEAVIER, that is the falsifiable form of 'engagement cuts the base assist'.")
    OUT["t3b"] = {}
    for b in ORDER:
        d = D[b]
        s = SIGN[b]
        act = (np.abs(d["tq_lf"]) > 300) & (np.abs(d["rate_lf"]) >= 2.0)
        imp = np.where(act, np.abs(d["tq_lf"]) / np.maximum(np.abs(d["rate_lf"]), 1e-9), np.nan)
        agree = np.sign(s * d["sc_lf"]) == np.sign(d["tq_lf"])
        big = np.abs(d["sc_lf"]) > 400
        print(f"\n  ---- {b}  (s={s:+.0f}) ----")
        print(f"     {'stratum':14s} {'nSAME':>6s} {'nOPP':>6s} {'nMAN':>6s} | "
              f"{'same/man':>21s} | {'opp/man':>21s} | {'same/opp':>21s} | null(same)")
        for nm, lo, hi in STRATA:
            base = act & (d["v"] >= lo) & (d["v"] < hi)
            same = base & (d["lat"] > 0.5) & agree & big
            opp = base & (d["lat"] > 0.5) & (~agree) & big
            man = base & (d["lat"] <= 0.5)
            if same.sum() < 150 or man.sum() < 150:
                print(f"     {nm:14s} {int(same.sum()):6d} {int(opp.sum()):6d} "
                      f"{int(man.sum()):6d} | -- too few --")
                continue
            r1 = ratio_boot(imp[same], d["ep"][same], imp[man], d["ep"][man], nboot=1200)
            r2 = (ratio_boot(imp[opp], d["ep"][opp], imp[man], d["ep"][man], nboot=1200)
                  if opp.sum() >= 150 else (np.nan,) * 3)
            r3 = (ratio_boot(imp[same], d["ep"][same], imp[opp], d["ep"][opp], nboot=1200)
                  if opp.sum() >= 150 else (np.nan,) * 3)
            nl = split_half(imp[same], d["ep"][same])
            print(f"     {nm:14s} {int(same.sum()):6d} {int(opp.sum()):6d} {int(man.sum()):6d} | "
                  f"{r1[0]:6.3f} [{r1[1]:6.3f},{r1[2]:6.3f}] | "
                  f"{r2[0]:6.3f} [{r2[1]:6.3f},{r2[2]:6.3f}] | "
                  f"{r3[0]:6.3f} [{r3[1]:6.3f},{r3[2]:6.3f}] | [{nl[1]:5.3f},{nl[2]:5.3f}]")
            OUT["t3b"].setdefault(b, {})[nm] = dict(
                same_man=list(r1), opp_man=list(r2), same_opp=list(r3), null=list(nl),
                n=[int(same.sum()), int(opp.sum()), int(man.sum())])

    hdr("T3c  THE TWO FACTORS SEPARATELY -- is the driver pushing harder, or moving less, or both?")
    OUT["t3c"] = {}
    for b in ORDER:
        d = D[b]
        print(f"\n  ---- {b} ----")
        for nm, lo, hi in STRATA:
            base = (d["v"] >= lo) & (d["v"] < hi) & (np.abs(d["tq_lf"]) > 300) \
                & np.isfinite(d["rate_lf"])
            me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
            if me.sum() < 200 or mm.sum() < 200:
                continue
            te, tm = np.median(np.abs(d["tq_lf"][me])), np.median(np.abs(d["tq_lf"][mm]))
            re, rm = np.median(np.abs(d["rate_lf"][me])), np.median(np.abs(d["rate_lf"][mm]))
            print(f"     {nm:14s} |tq_lf| eng {te:6.0f} / man {tm:6.0f} ({te / tm:5.3f}x)   "
                  f"|rate_lf| eng {re:6.2f} / man {rm:6.2f} ({re / max(rm, 1e-9):5.3f}x)   "
                  f"nE={int(me.sum())} nM={int(mm.sum())}")
            OUT["t3c"][f"{b}|{nm}"] = dict(tq=[te, tm], rate=[re, rm])

    (ROOT / "_scratch/cache/r67x" / "r67_t2t3.json").write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {ROOT / '_scratch/cache/r67x' / 'r67_t2t3.json'}")


if __name__ == "__main__":
    main()
