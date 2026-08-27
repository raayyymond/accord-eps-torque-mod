#!/usr/bin/env python3
"""RATCHET DISCRIMINATORS -- PART 3.  The remaining checks on TEST A's positive hit.

CTRL-4  ARTEFACT CONTROL AT MATCHED DETECTION QUALITY.  Part 2's control ran at an injection
        amplitude whose lock rate was 55.9% against the real arm's 86.4%, so its CI was wider than
        the effect it was meant to bound (|DC column tq| upper bound +0.950 vs an observed
        +0.467).  Re-run across amplitudes and report the control at, and above, the real arm's
        own lock rate.

CTRL-5  IS THE TORQUE EFFECT JUST HANDS-ON?  `f_press` (driver touching the wheel) is a genuine
        boundary-condition change and correlates with column torque.  Partial the two apart:
        residualise f_free on speed bin AND `f_press`, then re-fit the torque slope; and fit
        `f_press` residualised on torque.

CTRL-6  LEAVE-ONE-ROUTE-OUT on the pooled TEST-A hit -- is it one route carrying it?

CTRL-7  HANDS-ON vs HANDS-OFF as a paired, speed-stratified DIFFERENCE (overlapping CIs are not
        a test), on frequency and on line amplitude.

usage:  python studies/ratchet/ratchet_discriminators_ctrl2.py
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
import _r31_common as C31        # noqa: E402,F401
import v86_freq_test as V86      # noqa: E402
import ratchet_discriminators as RD           # noqa: E402
import ratchet_discriminators_ctrl as RC      # noqa: E402

RNG = np.random.default_rng(879_014_223)
OUT = {}
PROXIES = [("ld_ang", "|steer angle| deg"), ("ld_tqdc", "|DC column tq| ct"),
           ("ld_tqabs", "median|column tq| ct"), ("ld_e4", "|commanded tq| ct"),
           ("ld_rate", "|steer rate| deg/s"), ("ld_cstq", "|carState steerTq|"),
           ("f_press", "hands-on fraction")]


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def resid2_slope(rs, xkey, ckey, ykey="f_free", min_per_bin=4):
    """Slope of y on x, with BOTH the speed bin's median AND a linear covariate `ckey` removed.
    Done by within-bin centring then a two-regressor least squares, reporting the x coefficient."""
    by = {}
    for r in rs:
        if all(np.isfinite(r.get(k, np.nan)) for k in (xkey, ckey, ykey)):
            by.setdefault(RD.sbin_of(r["v"]), []).append(r)
    X, C, Y = [], [], []
    for k, v in by.items():
        if k < 0 or len(v) < min_per_bin:
            continue
        mx = float(np.median([r[xkey] for r in v]))
        mc = float(np.median([r[ckey] for r in v]))
        my = float(np.median([r[ykey] for r in v]))
        X += [r[xkey] - mx for r in v]
        C += [r[ckey] - mc for r in v]
        Y += [r[ykey] - my for r in v]
    if len(X) < 10:
        return np.nan
    A = np.column_stack([np.asarray(X, float), np.asarray(C, float), np.ones(len(X))])
    try:
        beta, *_ = np.linalg.lstsq(A, np.asarray(Y, float), rcond=None)
    except Exception:
        return np.nan
    return float(beta[0])


def main():
    hdr("BUILD POOLS")
    ENG, MAN, ALLV, POOL, POOL_MAN = RC.build_pools()
    f0 = float(np.median([r["f_free"] for r in POOL if np.isfinite(r["f_free"])]))
    real_hit = float(np.mean([abs(r["f_free"] - f0) <= 0.4 for r in POOL
                              if np.isfinite(r["f_free"])]))
    real_prom = float(np.nanmedian([r["p_free"] for r in POOL]))
    print(f"  POOLED n={len(POOL)} blk={len(RD.blocks_of(POOL))}   f0={f0:.3f} Hz   "
          f"real lock-rate(|Δf|<=0.4)={real_hit:.3f}   median p_free={real_prom:.2f}")
    OUT["real_arm"] = dict(n=len(POOL), nblk=len(RD.blocks_of(POOL)), f0=f0,
                           lock_rate=real_hit, p_free_med=real_prom)

    # -------------------------------------------------------------------------------------
    hdr("CTRL-4  ARTEFACT CONTROL AT MATCHED (AND BETTER) DETECTION QUALITY")
    print("  Line notched out at ±0.6 Hz, a FIXED-frequency line injected -> true slope is 0.")
    print(f"  Match target: the real arm's lock-rate {real_hit:.3f}.")
    OUT["ctrl4"] = {}
    for amp in (100.0, 160.0, 250.0, 400.0):
        reps = [RC.inject_fixed(POOL, f0, amp, f0, rng=np.random.default_rng(2000 + i))
                for i in range(5)]
        hit = float(np.mean([abs(r["f_free"] - f0) <= 0.4 for rep in reps for r in rep
                             if np.isfinite(r["f_free"])]))
        prom = float(np.nanmedian([r["p_free"] for rep in reps for r in rep]))
        sub(f"amp={amp:.0f} ct   lock-rate {hit:.3f} (real {real_hit:.3f})   med prom {prom:.1f}")
        ent = dict(amp=amp, lock_rate=hit, p_free_med=prom, proxies={})
        for key, lab in PROXIES:
            pts, los, his = [], [], []
            for rep in reps:
                b = RD.boot_blocks(rep, lambda z, k=key: RD.resid_slope(z, k), nboot=1200)
                pts.append(b["pt"])
                los.append(b["lo"])
                his.append(b["hi"])
            vals = np.array([r[key] for r in POOL if np.isfinite(r[key])], float)
            span = float(np.percentile(vals, 90) - np.percentile(vals, 10))
            pt, lo, hi = (float(np.nanmedian(pts)), float(np.nanmedian(los)),
                          float(np.nanmedian(his)))
            sig = bool(lo > 0 or hi < 0)
            ent["proxies"][key] = dict(label=lab, df_over_span=pt * span, lo=lo * span,
                                       hi=hi * span, ARTEFACT=sig)
            print(f"      {lab:24s} Δf over p10-p90 {pt * span:+.3f}"
                  f"[{lo * span:+.3f},{hi * span:+.3f}] Hz  "
                  f"{'⚠ ARTEFACT' if sig else 'clean'}")
        OUT["ctrl4"][f"amp{int(amp)}"] = ent

    # -------------------------------------------------------------------------------------
    hdr("CTRL-5  IS THE COLUMN-TORQUE EFFECT JUST HANDS-ON?")
    OUT["ctrl5"] = {}
    rs = [r for r in POOL if np.isfinite(r["f_free"])]
    for xk, ck, lab in (("ld_tqdc", "f_press", "|DC column tq| | hands-on"),
                        ("ld_tqabs", "f_press", "median|column tq| | hands-on"),
                        ("f_press", "ld_tqdc", "hands-on | |DC column tq|"),
                        ("ld_tqdc", "ld_e4", "|DC column tq| | command"),
                        ("ld_tqdc", "ld_rate", "|DC column tq| | steer rate"),
                        ("ld_tqdc", "ld_ang", "|DC column tq| | steer angle")):
        b0 = RD.boot_blocks(rs, lambda z, k=xk: RD.resid_slope(z, k), nboot=2000)
        b1 = RD.boot_blocks(rs, lambda z, k=xk, c=ck: resid2_slope(z, k, c), nboot=2000)
        vals = np.array([r[xk] for r in rs if np.isfinite(r[xk])], float)
        span = float(np.percentile(vals, 90) - np.percentile(vals, 10))
        OUT["ctrl5"][lab] = dict(
            raw=b0["pt"] * span, raw_lo=b0["lo"] * span, raw_hi=b0["hi"] * span,
            partial=b1["pt"] * span, partial_lo=b1["lo"] * span, partial_hi=b1["hi"] * span,
            span=span, nblk=b1["nblk"],
            sig_partial=bool(b1["lo"] * span > 0 or b1["hi"] * span < 0))
        e = OUT["ctrl5"][lab]
        print(f"    {lab:34s} raw {e['raw']:+.3f}[{e['raw_lo']:+.3f},{e['raw_hi']:+.3f}]"
              f"   partial {e['partial']:+.3f}[{e['partial_lo']:+.3f},{e['partial_hi']:+.3f}] Hz"
              f"   {'SIG' if e['sig_partial'] else '-'}")

    # -------------------------------------------------------------------------------------
    hdr("CTRL-6  LEAVE-ONE-ROUTE-OUT on the pooled TEST-A hit")
    OUT["ctrl6"] = {}
    for key, lab in (("ld_tqdc", "|DC column tq|"), ("ld_tqabs", "median|column tq|"),
                     ("ld_cstq", "|carState steerTq|"), ("ld_e4", "|commanded tq|")):
        sub(lab)
        OUT["ctrl6"][key] = {}
        for drop in [None] + RD.SCORED:
            sel = [r for r in rs if drop is None or r["build"] != drop]
            b = RD.boot_blocks(sel, lambda z, k=key: RD.resid_slope(z, k), nboot=2000)
            vals = np.array([r[key] for r in sel if np.isfinite(r[key])], float)
            span = float(np.percentile(vals, 90) - np.percentile(vals, 10))
            nm = "ALL" if drop is None else f"-{drop}"
            OUT["ctrl6"][key][nm] = dict(n=len(sel), nblk=b["nblk"], df=b["pt"] * span,
                                         lo=b["lo"] * span, hi=b["hi"] * span,
                                         sig=bool(b["lo"] > 0 or b["hi"] < 0))
            e = OUT["ctrl6"][key][nm]
            print(f"      {nm:14s} n={len(sel):3d} blk={b['nblk']:2d}  Δf {e['df']:+.3f}"
                  f"[{e['lo']:+.3f},{e['hi']:+.3f}] Hz  {'SIG' if e['sig'] else '-'}")

    # -------------------------------------------------------------------------------------
    hdr("CTRL-7  HANDS-ON vs HANDS-OFF, speed-stratified paired difference")
    OUT["ctrl7"] = {}

    def strat_diff(z, key):
        num = den = 0.0
        for i in range(len(RD.SBINS)):
            on = [r[key] for r in z if RD.sbin_of(r["v"]) == i and r["f_press"] > 0.5
                  and np.isfinite(r[key])]
            of = [r[key] for r in z if RD.sbin_of(r["v"]) == i and r["f_press"] <= 0.5
                  and np.isfinite(r[key])]
            if len(on) < 2 or len(of) < 2:
                continue
            w = min(len(on), len(of))
            num += w * (np.median(on) - np.median(of))
            den += w
        return num / den if den > 0 else np.nan

    for key, lab, unit in (("f_free", "f_c", "Hz"), ("amp", "line amplitude", "ct")):
        b = RD.boot_blocks(rs, lambda z, k=key: strat_diff(z, k), nboot=3000)
        OUT["ctrl7"][key] = dict(label=lab, diff=b["pt"], lo=b["lo"], hi=b["hi"],
                                 nblk=b["nblk"], sig=bool(np.isfinite(b["lo"])
                                                          and (b["lo"] > 0 or b["hi"] < 0)))
        e = OUT["ctrl7"][key]
        print(f"    {lab:18s} ON-minus-OFF {b['pt']:+.3f}[{b['lo']:+.3f},{b['hi']:+.3f}] {unit}"
              f"  blk={b['nblk']}  {'SIG' if e['sig'] else '-'}")
    cnt = {}
    for i, (lo, hi) in enumerate(RD.SBINS):
        on = sum(1 for r in rs if RD.sbin_of(r["v"]) == i and r["f_press"] > 0.5)
        of = sum(1 for r in rs if RD.sbin_of(r["v"]) == i and r["f_press"] <= 0.5)
        if on or of:
            cnt[f"{lo}-{hi}"] = [on, of]
    OUT["ctrl7"]["counts_on_off_per_sbin"] = cnt
    print(f"    per-speed-bin [on, off] counts: {cnt}")

    # -------------------------------------------------------------------------------------
    hdr("CTRL-8  the size of the TEST-A effect in physical terms")
    for key, lab in (("ld_tqdc", "|DC column tq| ct"), ("ld_tqabs", "median|column tq| ct"),
                     ("ld_ang", "|steer angle| deg")):
        vals = np.array([r[key] for r in rs if np.isfinite(r[key])], float)
        b = RD.boot_blocks(rs, lambda z, k=key: RD.resid_slope(z, k), nboot=2000)
        span = float(np.percentile(vals, 90) - np.percentile(vals, 10))
        df = b["pt"] * span
        OUT.setdefault("ctrl8", {})[key] = dict(
            label=lab, p10=float(np.percentile(vals, 10)),
            p50=float(np.percentile(vals, 50)), p90=float(np.percentile(vals, 90)),
            span=span, df=df, pct_of_f0=100 * df / f0,
            implied_stiffness_pct=100 * ((1 + df / f0) ** 2 - 1))
        e = OUT["ctrl8"][key]
        print(f"    {lab:24s} p10={e['p10']:.1f} p50={e['p50']:.1f} p90={e['p90']:.1f}  "
              f"Δf={df:+.3f} Hz = {e['pct_of_f0']:+.2f}% of f0  "
              f"⇒ implied Δk = {e['implied_stiffness_pct']:+.1f}% if f ∝ sqrt(k)")

    hdr("MERGE")
    p = ROOT / "_scratch/cache/r6f" / "ratchet_discriminators.json"
    D = json.loads(p.read_text(encoding="utf-8"))
    D["controls2"] = OUT
    p.write_text(json.dumps(D, indent=1, default=lambda o: None), encoding="utf-8")
    print(f"  wrote {p}")


if __name__ == "__main__":
    main()
