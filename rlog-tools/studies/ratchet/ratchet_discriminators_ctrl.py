#!/usr/bin/env python3
"""RATCHET DISCRIMINATORS -- PART 2: the three controls that decide whether Part 1's TEST A hit
is real.  Appends to `_scratch/cache/r6f/ratchet_discriminators.json`.

CTRL-1  Q NULL.  Part 1 measures Q ~ 26 on the engaged line via `C31.q_of`.  `q_of` walks down
        from the peak while the periodogram is monotone, so a single noisy bin STOPS the walk and
        the statistic is biased HIGH.  Run it on (a) DISENGAGED windows and (b) simulated
        featureless spectra.  If those also read ~26, the number measures periodogram noise, not
        a mode, and no Q claim may be made.

CTRL-2  ARTEFACT CONTROL for TESTS A and C -- the crux.  TEST A regresses f_free on |DC column
        torque|, and the frequency is measured on the SAME channel.  A larger DC torque means a
        redder background, which tilts `prom_spectrum`'s local floor and can bias the free argmax
        UPWARD with no change in the underlying line.  Control: NOTCH the real line out (+-0.6 Hz,
        exactly `v86_freq_main.inject_recover`'s notch) and inject a synthetic line at a FIXED
        frequency, leaving every window's own background intact.  The true frequency is now
        constant BY CONSTRUCTION, so any slope the estimator reports is pure artefact.

CTRL-3  RUNG COLLINEARITY for TEST B.  All four V85 rungs returned an amplitude ratio of
        1.425/1.425/1.425/1.455 in Part 1 -- suspiciously identical.  `gp-0x6ae2` is
        `102*|model|*min(|rate|/500,1)`, so the FRICTION rungs may be tracking motor RATE and
        nothing else, in which case TEST B cannot separate friction from rate at all.

usage:  python studies/ratchet/ratchet_discriminators_ctrl.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G          # noqa: E402,F401
import _r31_common as C31        # noqa: E402
import v86_freq_test as V86      # noqa: E402
import ratchet_discriminators as RD   # noqa: E402

RNG = np.random.default_rng(87_901_422)
OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def build_pools():
    ENG, MAN, ALLV = {}, {}, {}
    for route, (cache, pfx, segs) in RD.ROUTES.items():
        e = V86.spectra(RD.windows_ext(route, cache, pfx, segs, engaged=True))
        m = V86.spectra(RD.windows_ext(route, cache, pfx, segs, engaged=False))
        ALLV[route] = e
        ENG[route] = V86.in_speed(e)
        MAN[route] = V86.in_speed(m)
    POOL, POOL_MAN = [], []
    for route in RD.SCORED:
        for r in ENG[route]:
            q = dict(r)
            q["blk"] = route + "|" + r["blk"]
            POOL.append(q)
        for r in MAN[route]:
            q = dict(r)
            q["blk"] = route + "|" + r["blk"]
            POOL_MAN.append(q)
    return ENG, MAN, ALLV, POOL, POOL_MAN


# =================================================================================================
def q_list(rs):
    return [C31.q_of(r["f"], r["P"], r["f_free"], RD.FLO, RD.FHI)
            for r in rs if np.isfinite(r["f_free"])]


def ctrl1_q_null(POOL, POOL_MAN, nsim=1500):
    sub("CTRL-1  Q null")
    res = {}
    for name, rs in (("engaged POOLED", POOL), ("disengaged POOLED", POOL_MAN)):
        q = np.array(q_list(rs), float)
        q = q[np.isfinite(q)]
        b = RD.boot_blocks([r for r in rs if np.isfinite(r["f_free"])],
                           lambda z: float(np.median(q_list(z))), nboot=2000)
        res[name] = dict(n=len(q), med=float(np.median(q)), lo=b["lo"], hi=b["hi"],
                         p25=float(np.percentile(q, 25)), p75=float(np.percentile(q, 75)))
        print(f"    {name:20s} n={len(q):3d}  Q med={np.median(q):6.2f} "
              f"[{b['lo']:.2f},{b['hi']:.2f}]  IQR[{np.percentile(q, 25):.1f},"
              f"{np.percentile(q, 75):.1f}]")
    for kind in ("white", "red"):
        qs = []
        for _ in range(nsim):
            w = RNG.standard_normal(RD.NW)
            if kind == "red":
                X = np.fft.rfft(w)
                fr = np.fft.rfftfreq(RD.NW, 1 / 101.04)
                X[1:] /= np.maximum(fr[1:], 0.1)
                w = np.fft.irfft(X, RD.NW)
            r = dict(x=w, fs=101.04, v=1.0, blk="s", ep="s", t0=0.0)
            V86.spectra([r])
            if np.isfinite(r["f_free"]):
                qs.append(C31.q_of(r["f"], r["P"], r["f_free"], RD.FLO, RD.FHI))
        qs = np.array([q for q in qs if np.isfinite(q)], float)
        res[f"sim {kind}"] = dict(n=len(qs), med=float(np.median(qs)),
                                  p25=float(np.percentile(qs, 25)),
                                  p75=float(np.percentile(qs, 75)),
                                  p95=float(np.percentile(qs, 95)))
        print(f"    {'sim ' + kind:20s} n={len(qs):3d}  Q med={np.median(qs):6.2f}"
              f"  IQR[{np.percentile(qs, 25):.1f},{np.percentile(qs, 75):.1f}]"
              f"  p95={np.percentile(qs, 95):.1f}")
    cap = 8.0 / (1.44 * 101.04 / RD.NW)
    res["hann_cap"] = float(cap)
    print(f"    Hann main-lobe cap on measurable Q at 8 Hz: {cap:.1f}")
    return res


# =================================================================================================
def inject_fixed(rs, f_fixed, amp, notch_at, jitter=0.0, rng=None):
    """`v86_freq_main.inject_recover`'s construction, returning records.  Notch the real line out
    (+-0.6 Hz, narrow so the local FLOOR survives), add a line at a FIXED frequency, keep the
    window's own background bit-identical, re-run the SAME instrument."""
    rng = rng or RNG
    out = []
    for r in rs:
        x = np.asarray(r["x"], float)
        bs = butter(2, [max(notch_at - 0.6, 0.4), notch_at + 0.6], btype="bandstop", fs=r["fs"])
        x = filtfilt(*bs, x)
        tt = np.arange(len(x)) / r["fs"]
        fi = f_fixed * (1.0 + jitter * (rng.random() - 0.5))
        x = x + amp * np.sin(2 * np.pi * fi * tt + 2 * np.pi * rng.random())
        q = dict(x=x, fs=r["fs"], v=r["v"], blk=r["blk"], ep=r["ep"], t0=r["t0"])
        V86.spectra([q])
        for k in list(RD.AUX) + ["amp", "amp69"] + list(RD.FRIC):
            q[k] = r.get(k, np.nan)
        out.append(q)
    return out


def ctrl2_artefact(POOL, f0, prom_target):
    sub(f"CTRL-2  fixed-frequency artefact control  (f fixed at {f0:.3f} Hz, true slope = 0)")
    print("    calibrating injection amplitude to the engaged median prominence "
          f"{prom_target:.2f}")
    best, cal = None, []
    for amp in (400.0, 250.0, 160.0, 100.0, 65.0, 40.0, 25.0, 15.0):
        q = inject_fixed(POOL, f0, amp, f0)
        pm = float(np.nanmedian([r["p_free"] for r in q]))
        hr = float(np.mean([abs(r["f_free"] - f0) <= 0.4 for r in q]))
        cal.append(dict(amp=amp, prom=pm, hit=hr))
        print(f"      amp {amp:7.1f} ct   med prom {pm:7.2f}   hit {100 * hr:5.1f}%")
        if best is None or abs(pm - prom_target) < abs(best[1] - prom_target):
            best = (amp, pm)
    amp = best[0]
    print(f"    ⇒ using amp = {amp:.1f} ct (med prom {best[1]:.2f})")
    res = dict(calibration=cal, amp_used=float(amp), f_fixed=float(f0), proxies={}, testC={})

    reps = [inject_fixed(POOL, f0, amp, f0, rng=np.random.default_rng(1000 + i))
            for i in range(5)]
    print("\n    TEST-A proxies on the fixed-frequency surrogate (any nonzero slope = ARTEFACT):")
    for key, lab in RD.__dict__.get("_PROXIES", []) or [
            ("ld_ang", "|steer angle| deg"), ("ld_tqdc", "|DC column tq| ct"),
            ("ld_tqabs", "median|column tq| ct"), ("ld_e4", "|commanded tq| ct"),
            ("ld_rate", "|steer rate| deg/s"), ("ld_cstq", "|carState steerTq|"),
            ("f_press", "hands-on fraction")]:
        pts, los, his = [], [], []
        for rep in reps:
            b = RD.boot_blocks(rep, lambda z, k=key: RD.resid_slope(z, k), nboot=1200)
            pts.append(b["pt"])
            los.append(b["lo"])
            his.append(b["hi"])
        vals = np.array([r[key] for r in POOL if np.isfinite(r[key])], float)
        span = float(np.percentile(vals, 90) - np.percentile(vals, 10)) if len(vals) else np.nan
        pt = float(np.nanmedian(pts))
        lo, hi = float(np.nanmedian(los)), float(np.nanmedian(his))
        sig = bool(lo > 0 or hi < 0)
        res["proxies"][key] = dict(label=lab, slope=pt, lo=lo, hi=hi, span=span,
                                   df_over_span=pt * span, df_lo=lo * span, df_hi=hi * span,
                                   ARTEFACT=sig, nrep=len(reps))
        print(f"      {lab:24s} Δf over p10-p90 {pt * span:+.3f}[{lo * span:+.3f},"
              f"{hi * span:+.3f}] Hz   {'⚠ ARTEFACT' if sig else 'clean'}")

    print("\n    TEST-C amplitude terciles on the fixed-frequency surrogate:")
    for key in ("amp", "amp69"):
        d = []
        for rep in reps:
            rr = RD.within_bin_rank(rep, key)
            b = RD.boot_blocks(rr, lambda z, k=key: RD.d_terciles(z, k), nboot=1200)
            d.append((b["pt"], b["lo"], b["hi"]))
        d = np.array(d, float)
        pt, lo, hi = float(np.nanmedian(d[:, 0])), float(np.nanmedian(d[:, 1])), \
            float(np.nanmedian(d[:, 2]))
        sig = bool(lo > 0 or hi < 0)
        res["testC"][key] = dict(df=pt, lo=lo, hi=hi, ARTEFACT=sig)
        print(f"      {key:8s} Δ(T3-T1) {pt:+.3f}[{lo:+.3f},{hi:+.3f}] Hz   "
              f"{'⚠ ARTEFACT' if sig else 'clean'}")
    return res


# =================================================================================================
def ctrl3_rungs(ENG, ALLV):
    sub("CTRL-3  V85 rung collinearity -- can TEST B separate FRICTION from RATE at all?")
    res = {}
    for arm, rs in (("lowspeed_0p5_5", ENG[RD.FRICTION_ROUTE]),
                    ("allspeed", ALLV[RD.FRICTION_ROUTE])):
        keys = list(RD.FRIC) + ["ld_rate", "ld_ang", "ld_tqdc", "v"]
        M = np.array([[r[k] for k in keys] for r in rs], float)
        ok = np.all(np.isfinite(M), axis=1)
        M = M[ok]
        C = np.corrcoef(M.T)
        res[arm] = dict(n=int(M.shape[0]), keys=keys,
                        corr={keys[i]: {keys[j]: float(C[i, j]) for j in range(len(keys))}
                              for i in range(len(keys))})
        print(f"    {arm}  n={M.shape[0]}")
        print("      " + " " * 13 + "".join(f"{k[:9]:>11s}" for k in keys))
        for i, k in enumerate(keys):
            print(f"      {k:13s}" + "".join(f"{C[i, j]:+11.3f}" for j in range(len(keys))))
        # do the terciles actually differ between rungs?
        ov = {}
        sets = {}
        for k in RD.FRIC:
            rr = RD.within_bin_rank(rs, k)
            sets[k] = set(id(r) for r in rr if r[k + "_rk"] >= 2 / 3)
        # ids are per-copy; recompute on a shared copy instead
        rr = [dict(r) for r in rs]
        for k in RD.FRIC:
            tmp = RD.within_bin_rank(rr, k)
            for a, b in zip(rr, tmp):
                a[k + "_rk"] = b[k + "_rk"]
        for k in RD.FRIC:
            sets[k] = set(i for i, r in enumerate(rr) if r[k + "_rk"] >= 2 / 3)
        ks = list(RD.FRIC)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = sets[ks[i]], sets[ks[j]]
                ov[f"{ks[i]}|{ks[j]}"] = (len(a & b) / max(len(a | b), 1))
        res[arm]["T3_jaccard"] = {k: float(v) for k, v in ov.items()}
        print("      T3 (top-tercile) Jaccard overlap between rungs:")
        for k, v in ov.items():
            print(f"        {k:28s} {v:.3f}")
    return res


# =================================================================================================
def main():
    hdr("BUILD POOLS (same instrument, same arms as Part 1)")
    ENG, MAN, ALLV, POOL, POOL_MAN = build_pools()
    print(f"  POOLED engaged n={len(POOL)} blk={len(RD.blocks_of(POOL))}   "
          f"POOLED manual n={len(POOL_MAN)} blk={len(RD.blocks_of(POOL_MAN))}")

    hdr("CTRL-1  Q NULL")
    OUT["ctrl1_Q"] = ctrl1_q_null(POOL, POOL_MAN)

    hdr("CTRL-2  FIXED-FREQUENCY ARTEFACT CONTROL")
    f0 = float(np.median([r["f_free"] for r in POOL if np.isfinite(r["f_free"])]))
    prom = float(np.nanmedian([r["p_free"] for r in POOL]))
    OUT["ctrl2_artefact"] = ctrl2_artefact(POOL, f0, prom)

    hdr("CTRL-3  RUNG COLLINEARITY")
    OUT["ctrl3_rungs"] = ctrl3_rungs(ENG, ALLV)

    hdr("EXTRA  hands-on / hands-off as a boundary-condition load proxy")
    press = [r["f_press"] for r in POOL]
    print(f"  pooled engaged hands-on fraction: med={np.median(press):.3f} "
          f"n(>0.5)={sum(1 for p in press if p > 0.5)}  n(<0.5)={sum(1 for p in press if p <= 0.5)}")
    on = [r for r in POOL if r["f_press"] > 0.5 and np.isfinite(r["f_free"])]
    off = [r for r in POOL if r["f_press"] <= 0.5 and np.isfinite(r["f_free"])]
    bon = RD.boot_blocks(on, lambda z: float(np.median([q["f_free"] for q in z])), nboot=2000)
    bof = RD.boot_blocks(off, lambda z: float(np.median([q["f_free"] for q in z])), nboot=2000)
    aon = RD.boot_blocks(on, lambda z: float(np.median([q["amp"] for q in z])), nboot=2000)
    aof = RD.boot_blocks(off, lambda z: float(np.median([q["amp"] for q in z])), nboot=2000)
    OUT["hands_on_off"] = dict(
        n_on=len(on), n_off=len(off),
        f_on=bon["pt"], f_on_ci=[bon["lo"], bon["hi"]], nblk_on=bon["nblk"],
        f_off=bof["pt"], f_off_ci=[bof["lo"], bof["hi"]], nblk_off=bof["nblk"],
        amp_on=aon["pt"], amp_on_ci=[aon["lo"], aon["hi"]],
        amp_off=aof["pt"], amp_off_ci=[aof["lo"], aof["hi"]])
    print(f"  hands ON  n={len(on):3d} blk={bon['nblk']:2d}  f_c={bon['pt']:.3f}"
          f"[{bon['lo']:.3f},{bon['hi']:.3f}] Hz  amp={aon['pt']:.1f}"
          f"[{aon['lo']:.1f},{aon['hi']:.1f}] ct")
    print(f"  hands OFF n={len(off):3d} blk={bof['nblk']:2d}  f_c={bof['pt']:.3f}"
          f"[{bof['lo']:.3f},{bof['hi']:.3f}] Hz  amp={aof['pt']:.1f}"
          f"[{aof['lo']:.1f},{aof['hi']:.1f}] ct")

    hdr("MERGE INTO ratchet_discriminators.json")
    p = ROOT / "_scratch/cache/r6f" / "ratchet_discriminators.json"
    D = json.loads(p.read_text(encoding="utf-8"))
    D["controls"] = OUT
    p.write_text(json.dumps(D, indent=1, default=lambda o: None), encoding="utf-8")
    print(f"  wrote {p}")


if __name__ == "__main__":
    main()
