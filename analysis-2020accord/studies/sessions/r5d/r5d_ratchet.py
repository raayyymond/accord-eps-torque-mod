#!/usr/bin/env python3
"""Route `5d` (**V74**) -- THE PRE-REGISTERED CRITERIA, checked exactly as written.

Registered in `docs/STATE.md` / `handoffs/2026-08/HANDOFF-2026-08-05-the-car-is-tvca4-and-both-dead-zones.md` BEFORE
V74 flew:

  SUCCESS      6-9 Hz burst DUTY **and** DURATION both fall, with f0 unchanged (|Δf0| <= 0.3 Hz).
  FALSIFIER A  duty ratio > 1.2 *together with* prominence ratio > 1.3  => self-excitation.
  FALSIFIER B  **5 x f0 prominence > 3.0 => the relay is generating a new cycle. ABORT the lever.**
               (baseline ~38.5 Hz, prominence 0.80; 3x is unusable -- confounded with the 21 Hz ring)
  FALSIFIER C  |Δf0| > 0.5 Hz => a relay picks its frequency from loop delay; damping does not.

Instruments are `d6_events` / `d6b_events_fixed` UNCHANGED -- same 5-12 Hz ratchet band, same 12-28
Hz carrier, same `bursts()` (k = 1.8 x the run's own median envelope, minimum 0.30 s), same
`_grind2_lib.prom_spectrum` / `locate`. What this file adds is (a) a per-BUILD split instead of the
pooled corpus, (b) an ABSOLUTE-threshold duty beside the relative one, and (c) the exposure and
speed census that decides whether any of it is readable.

🛑 TWO LIMITATIONS, STATED BEFORE THE NUMBERS.
1. `d6b`'s `bursts()` threshold is **1.8 x the run's OWN median envelope**. That makes `duty` a
   SHAPE statistic: a build that halves the whole 6-9 Hz signal leaves this duty unchanged. The
   pre-registration says "duty", and `d6b` is what produced the registered baseline, so the relative
   form is reported first -- but an ABSOLUTE duty (fraction of samples above a fixed 600-count
   envelope, the corpus's own ratchet cut) is reported beside it, and they answer different
   questions.
2. Engaged CREEP yields **2 qualifying runs per build** on every route in this corpus (route 5d: 2
   runs / 44 s). The primary arm is therefore engaged v < 12.5 m/s, where route 5d has 12 runs /
   243 s. ⚠ Tyre order 2 (2v/2.080 Hz) is in the 6-9 Hz band at 6.2-9.4 m/s and IS inside that
   window, so the per-run speed census is printed and the arms are compared for speed match.

Usage:  python studies/sessions/r5d/r5d_ratchet.py   ->  writes _scratch/out/_r5d_ratchet.json
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5d_lib as L  # noqa: E402
import d6_events as D  # noqa: E402
from d6b_events_fixed import bursts  # noqa: E402

RNG = np.random.default_rng(20260806)
OUT = {}
RATCHET, CARRIER = D.RATCHET, D.CARRIER          # (5,12) and (12,28) Hz -- unchanged
T_ABS = 600.0                                    # counts of 5-12 Hz envelope == 1200 p-p, the
#                                                  corpus's own ratchet cut (`nearcentre_relay`)
BUILDS = ["V59/r2c", "V58/r2b", "V62/r37", "V65/r3b", "V67/r47", "V68/r4e", "V69/r4f",
          "V71B/r54", "V71C/r58", "V72/r59", "V73/r5a", "V74/r5d"]
D.PARKED["V74/r5d"] = [2, 3, 9]                  # from the per-segment census -- see `studies/sessions/r5d/r5d_bands.py`
L.install_fs()


def med_ci_units(vals, units, nb=4000):
    """(median, lo, hi) resampling the RESAMPLING UNIT (a run), never the individual values."""
    per = {}
    for v, u in zip(vals, units):
        if np.isfinite(v):
            per.setdefault(u, []).append(v)
    ks = list(per)
    if len(ks) < 2:
        return np.nan, np.nan, np.nan, len(ks)
    allv = np.concatenate([per[k] for k in ks])
    dr = np.full(nb, np.nan)
    for i in range(nb):
        j = RNG.integers(0, len(ks), len(ks))
        dr[i] = np.median(np.concatenate([per[ks[k]] for k in j]))
    return (float(np.median(allv)), float(np.nanpercentile(dr, 2.5)),
            float(np.nanpercentile(dr, 97.5)), len(ks))


def ratio_ci(a_vals, a_u, b_vals, b_u, nb=4000):
    """Ratio of two run-resampled medians, with its own CI. Both arms resample RUNS."""
    pa, pb = {}, {}
    for v, u in zip(a_vals, a_u):
        if np.isfinite(v):
            pa.setdefault(u, []).append(v)
    for v, u in zip(b_vals, b_u):
        if np.isfinite(v):
            pb.setdefault(u, []).append(v)
    ka, kb = list(pa), list(pb)
    if len(ka) < 2 or len(kb) < 2:
        return np.nan, np.nan, np.nan
    dr = np.full(nb, np.nan)
    for i in range(nb):
        x = np.median(np.concatenate([pa[ka[j]] for j in RNG.integers(0, len(ka), len(ka))]))
        y = np.median(np.concatenate([pb[kb[j]] for j in RNG.integers(0, len(kb), len(kb))]))
        dr[i] = x / y if y else np.nan
    obs = np.median(np.concatenate([pa[k] for k in ka])) / \
        np.median(np.concatenate([pb[k] for k in kb]))
    return float(obs), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


# ================================================================== collect =======================
def inventory(build, vhi):
    """Per-run burst inventory + the run's spectrum, for engaged runs under `vhi`."""
    runs = []
    for _, s, a, b, d, fs in D.runs(build, 0.0, vhi, True, 512):
        x = np.asarray(d["tq"][a:b], float)
        env = np.abs(D.analytic(D.bp(x, fs, *RATCHET)))
        bs = bursts(env, fs)
        v = np.abs(np.asarray(d["cs_v"][a:b], float))
        runs.append(dict(build=build, run=(build, s, a), n=b - a, fs=fs, sec=(b - a) / fs,
                         x=x, env=env, v=float(np.mean(v)), vmin=float(np.min(v)),
                         vmax=float(np.max(v)),
                         duty_rel=float(sum(j - i for i, j, _ in bs) / max(len(env), 1)),
                         duty_abs=float(np.mean(env >= T_ABS)),
                         env_p99=float(np.percentile(env, 99)),
                         env_med=float(np.median(env)),
                         nb=len(bs), durs=[(j - i) / fs for i, j, _ in bs],
                         peaks=[p for _, _, p in bs]))
    return runs


for arm_label, VHI in (("engaged, v < 12.5 m/s  (PRIMARY)", 12.5),
                       ("engaged, v < 4 m/s  (CREEP -- 2 runs/build, indicative only)", 4.0)):
    L.hdr(f"BURST INVENTORY -- {arm_label}")
    inv = {b: inventory(b, VHI) for b in BUILDS}
    print(f"  {'build':<10} {'runs':>5} {'sec':>7} {'v_med':>6} {'v_p10':>6} {'v_p90':>6} "
          f"{'duty_rel':>9} {'duty_ABS':>9} {'bursts':>7} {'dur_ms':>7} {'envp99':>7}")
    tab = {}
    for b in BUILDS:
        rs = inv[b]
        if not rs:
            print(f"  {b:<10} {'--':>5}  no qualifying run")
            continue
        vv = np.concatenate([np.full(1, r["v"]) for r in rs])
        durs = [d_ for r in rs for d_ in r["durs"]]
        du = [r["run"] for r in rs for _ in r["durs"]]
        dr_ = med_ci_units([r["duty_rel"] for r in rs], [r["run"] for r in rs])
        da_ = med_ci_units([r["duty_abs"] for r in rs], [r["run"] for r in rs])
        dd_ = med_ci_units(durs, du)
        ep_ = med_ci_units([r["env_p99"] for r in rs], [r["run"] for r in rs])
        tab[b] = dict(nrun=len(rs), sec=sum(r["sec"] for r in rs), vmed=float(np.median(vv)),
                      duty_rel=dr_, duty_abs=da_, dur=dd_, envp99=ep_,
                      nburst=len(durs),
                      onset=float(sum(r["nb"] for r in rs) / sum(r["sec"] for r in rs)))
        print(f"  {b:<10} {len(rs):>5} {sum(r['sec'] for r in rs):>7.1f} "
              f"{np.median(vv):>6.2f} {np.percentile(vv, 10):>6.2f} {np.percentile(vv, 90):>6.2f} "
              f"{dr_[0]:>9.3f} {da_[0]:>9.3f} {len(durs):>7} {1000 * dd_[0]:>7.0f} "
              f"{ep_[0]:>7.0f}")
    OUT[f"inventory|{VHI}"] = {k: {kk: (list(vv) if isinstance(vv, tuple) else vv)
                                   for kk, vv in v.items()} for k, v in tab.items()}

    # ---- the registered comparisons -----------------------------------------------------------
    print(f"\n  ★ V74 vs its predecessors -- run-resampled ratios (V74 / other). "
          f"< 1 means V74 is BETTER.")
    print(f"  {'vs':<10} {'duty_rel':>22} {'duty_ABS':>22} {'burst dur':>22} {'env p99':>22}")
    for b in ("V73/r5a", "V72/r59", "V71C/r58", "V67/r47", "V59/r2c"):
        if not inv.get(b) or not inv.get("V74/r5d"):
            continue
        A, B = inv["V74/r5d"], inv[b]
        cells = []
        for key, sel in (("duty_rel", lambda r: [r["duty_rel"]]),
                         ("duty_abs", lambda r: [r["duty_abs"]]),
                         ("dur", lambda r: r["durs"]),
                         ("envp99", lambda r: [r["env_p99"]])):
            av = [x for r in A for x in sel(r)]
            au = [r["run"] for r in A for _ in sel(r)]
            bv = [x for r in B for x in sel(r)]
            bu = [r["run"] for r in B for _ in sel(r)]
            cells.append(ratio_ci(av, au, bv, bu))
        print(f"  {b:<10} " + " ".join(f"{p:6.3f} [{lo:5.2f},{hi:6.2f}]" for p, lo, hi in cells))
        OUT.setdefault(f"ratios|{VHI}", {})[b] = {
            k: list(v) for k, v in zip(("duty_rel", "duty_abs", "dur", "envp99"), cells)}
    if VHI == 12.5:
        INV = inv

# ================================================================== f0 ============================
L.hdr("Δf0 -- the per-window line frequency in the FREE 5-12 Hz band (NFFT 512, prominence >= 3)")
print("  🛑 measured in the SPECTRUM, so it carries no detection-threshold confound. Engaged,")
print("  v < 12.5 m/s. A relay picks its frequency from loop delay; damping does not move f0.\n")
f0tab = {}
for b in BUILDS:
    pw, un = [], []
    for _, s, a, bb, d, fs in D.runs(b, 0.0, 12.5, True, 512):
        x = np.asarray(d["tq"][a:bb], float)
        f = np.fft.rfftfreq(512, 1 / fs)
        for i in range(0, len(x) - 512 + 1, 256):
            P = C.periodogram(x[i:i + 512], fs, 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            ff, pp = G.locate(f, P, 5, 12, R=R)
            if not np.isfinite(ff) or pp < 3.0:
                continue
            pw.append(ff)
            un.append((b, s, a))
    m, lo, hi, nu = med_ci_units(pw, un)
    f0tab[b] = dict(f0=m, lo=lo, hi=hi, n=len(pw), nruns=nu)
    print(f"  {b:<10} f0 = {m:6.3f} Hz [{lo:6.3f}, {hi:6.3f}]   n={len(pw):>4} windows, "
          f"{nu} runs")
OUT["f0"] = f0tab
for b in ("V73/r5a", "V72/r59"):
    if np.isfinite(f0tab[b]["f0"]) and np.isfinite(f0tab["V74/r5d"]["f0"]):
        d0 = f0tab["V74/r5d"]["f0"] - f0tab[b]["f0"]
        print(f"\n  Δf0(V74 - {b}) = {d0:+.3f} Hz   "
              f"|Δf0| <= 0.3 ? {'PASS' if abs(d0) <= 0.3 else 'FAIL'}    "
              f"|Δf0| > 0.5 (FALSIFIER C) ? {'ABORT' if abs(d0) > 0.5 else 'clear'}")
        OUT.setdefault("df0", {})[b] = float(d0)

# ================================================================== 5 x f0 ========================
L.hdr("★★ FALSIFIER B -- the 5 x f0 PROMINENCE. The single most important number here.")
print("  A bare sign() relay multiplying a vanishing quantity should add NO odd-harmonic structure.")
print("  A relay that has started generating its own cycle puts a line at 5 x f0 (~38-39 Hz).")
print("  🛑 Prominence depends on FFT resolution, so the registered baseline (0.80, measured at")
print("  NFFT 2048 on the pooled creep corpus) is RE-MEASURED here with the identical instrument")
print("  used on V74 -- a number computed at a different NFFT is not comparable to it.\n")


def avg_spec(runs, nfft):
    """AVERAGE FIRST, PEAK-FIND AFTER -- the mean periodogram over every full `nfft` window."""
    acc, K, fr = None, 0, None
    for r in runs:
        x, fs = r["x"], r["fs"]
        for i in range(0, len(x) - nfft + 1, nfft // 2):
            P = C.periodogram(x[i:i + nfft], fs, nfft, True)
            if P is None:
                continue
            fr = np.fft.rfftfreq(nfft, 1 / fs) if fr is None else fr
            acc = P.copy() if acc is None else acc + P
            K += 1
    return (fr, acc / K, K) if K else (None, None, 0)


harm = {}
for nfft in (2048, 512):
    print(f"\n  --- NFFT {nfft} ({nfft / 100:.2f} s, {100 / nfft:.3f} Hz bins) ---")
    print(f"  {'build':<10} {'K':>4} {'f0':>6} {'prom f0':>8} " +
          " ".join(f"{h}x@Hz  prom" for h in (2, 3, 4, 5)))
    for b in BUILDS:
        fr, P, K = avg_spec(INV.get(b, []), nfft)
        if P is None or K < 2:
            print(f"  {b:<10} {K:>4}   -- insufficient contiguous exposure at this NFFT")
            continue
        R = G.prom_spectrum(fr, P)
        f0, p0 = G.locate(fr, P, 6, 9, R=R)
        row = dict(K=K, f0=float(f0), prom0=float(p0))
        cells = []
        for h in (2, 3, 4, 5):
            j = int(np.argmin(np.abs(fr - h * f0)))
            w = slice(max(0, j - 4), j + 5)
            k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
            row[f"h{h}"] = dict(f=float(fr[k]), prom=float(R[k]))
            cells.append(f"{fr[k]:6.2f} {R[k]:5.2f}")
        harm[f"{b}|{nfft}"] = row
        print(f"  {b:<10} {K:>4} {f0:>6.2f} {p0:>8.2f} " + "  ".join(cells))
OUT["harmonics"] = harm

L.hdr("VERDICT ON THE PRE-REGISTERED CRITERIA")
for nfft in (2048, 512):
    r = harm.get(f"V74/r5d|{nfft}")
    if not r:
        continue
    p5 = r["h5"]["prom"]
    print(f"  FALSIFIER B, NFFT {nfft}:  V74 5xf0 = {r['h5']['f']:.2f} Hz, prominence {p5:.2f}  "
          f"=> {'🛑 ABORT' if p5 > 3.0 else 'CLEAR (<= 3.0)'}")
    for b in ("V73/r5a", "V72/r59", "V59/r2c"):
        q = harm.get(f"{b}|{nfft}")
        if q:
            print(f"      same instrument, {b:<9} 5xf0 = {q['h5']['f']:.2f} Hz "
                  f"prominence {q['h5']['prom']:.2f}")

with open(ROOT / "_scratch/out/_r5d_ratchet.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5d_ratchet.json")
