#!/usr/bin/env python3
"""Route `5d` -- the three pre-registered FALSIFIERS with proper uncertainty, and their calibration.

`r5d_ratchet.py` produced the point estimates. Three of them are decision-bearing and were quoted
there without an interval or a calibration, which is not good enough for a flight gate:

  B  5 x f0 PROMINENCE > 3.0  =>  ABORT.  Needs (i) a CI, and (ii) the SAME number computed on
     builds whose verdict is already known -- because if stock itself exceeds 3.0 under this
     instrument, the threshold does not separate anything.
     🛑 A prominence read off an AVERAGED spectrum also depends on K (more averaging => smoother
     local floor => larger prominence), and K differs 7 vs 25 across arms here. So the per-WINDOW
     prominence (`_grind2_lib.wrecs`'s own `p_*`, K-free) is computed beside it.
  A  duty ratio > 1.2 TOGETHER WITH prominence ratio > 1.3  =>  self-excitation.
  C  |Δf0| > 0.5 Hz.  f0 falls with load, and the arms differ in speed, so the raw difference is
     confounded; a SPEED-MATCHED Δf0 is computed as well.

Usage:  python r5d_falsifiers.py   ->  writes _r5d_falsifiers.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5d_lib as L  # noqa: E402
import d6_events as D  # noqa: E402
from d6b_events_fixed import bursts  # noqa: E402

RNG = np.random.default_rng(880505)
OUT = {}
D.PARKED["V74/r5d"] = [2, 3, 9]
L.install_fs()
BUILDS = ["V59/r2c", "V58/r2b", "V62/r37", "V65/r3b", "V67/r47", "V69/r4f", "V71B/r54",
          "V71C/r58", "V72/r59", "V73/r5a", "V74/r5d"]
STOCK = ["V59/r2c", "V58/r2b"]


def load_runs(build, vhi=12.5):
    out = []
    for _, s, a, b, d, fs in D.runs(build, 0.0, vhi, True, 512):
        out.append(dict(run=(build, s, a), x=np.asarray(d["tq"][a:b], float), fs=fs,
                        v=float(np.mean(np.abs(d["cs_v"][a:b])))))
    return out


RUNS = {b: load_runs(b) for b in BUILDS}
RUNS_CREEP = {b: load_runs(b, 4.0) for b in BUILDS}


def avg_spec(runs, nfft):
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


def harm5(runs, nfft):
    """(f0, prom(f0), f(5x), prom(5x)) from the averaged spectrum."""
    fr, P, K = avg_spec(runs, nfft)
    if P is None or K < 2:
        return (np.nan,) * 4 + (K,)
    R = G.prom_spectrum(fr, P)
    f0, p0 = G.locate(fr, P, 6, 9, R=R)
    j = int(np.argmin(np.abs(fr - 5 * f0)))
    w = slice(max(0, j - 4), j + 5)
    k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
    return float(f0), float(p0), float(fr[k]), float(R[k]), K


# ================================================================== B ============================
L.hdr("FALSIFIER B -- 5 x f0 prominence, WITH a CI and WITH the corpus calibration")
print("  Instrument: averaged periodogram over engaged runs, v < 12.5 m/s. CI resamples RUNS and")
print("  rebuilds the averaged spectrum each draw, so it carries the run-to-run variability that a")
print("  single pooled spectrum hides.\n")
print(f"  {'build':<10} {'K':>4} {'f0':>6} {'5xf0 Hz':>8} {'prom(5xf0)':>10} {'95% CI':>18}  "
      f"verdict vs 3.0")
b5 = {}
for b in BUILDS:
    rs = RUNS[b]
    if len(rs) < 3:
        print(f"  {b:<10}  -- fewer than 3 runs")
        continue
    f0, p0, f5, p5, K = harm5(rs, 2048)
    dr = np.full(600, np.nan)
    for i in range(600):
        samp = [rs[j] for j in RNG.integers(0, len(rs), len(rs))]
        dr[i] = harm5(samp, 2048)[3]
    lo, hi = np.nanpercentile(dr, [2.5, 97.5])
    vd = "ABORT" if p5 > 3.0 else ("clear" if hi <= 3.0 else "clear (CI touches 3.0)")
    b5[b] = dict(f0=f0, prom_f0=p0, f5=f5, prom5=p5, lo=float(lo), hi=float(hi), K=K)
    print(f"  {b:<10} {K:>4} {f0:>6.2f} {f5:>8.2f} {p5:>10.2f} [{lo:>7.2f}, {hi:>7.2f}]  {vd}")
OUT["falsifier_B"] = b5
p5s = [v["prom5"] for v in b5.values()]
print(f"\n  🛑 CORPUS SPREAD of this statistic: {min(p5s):.2f} .. {max(p5s):.2f} across "
      f"{len(p5s)} builds, median {np.median(p5s):.2f}.")
print(f"  Builds at or above the 3.0 abort line: "
      f"{[k for k, v in b5.items() if v['prom5'] >= 3.0] or 'none'}")

print("\n  --- the registered baseline, reproduced on ITS OWN instrument "
      "(pooled CREEP corpus, NFFT 2048) ---")
pool = [r for b in ["V59/r2c", "V64/r35", "V58/r2b", "V62/r37", "V65/r3a", "V65/r3b", "V67/r47",
                    "V69/r4f", "V70/r50", "V71B/r54", "V71C/r58", "V72/r59", "V73/r5a"]
        for r in RUNS_CREEP.get(b, [])]
if len(pool) >= 3:
    f0, p0, f5, p5, K = harm5(pool, 2048)
    print(f"  pooled corpus creep: K={K}  f0 {f0:.2f}  5xf0 {f5:.2f} Hz  prominence {p5:.2f}   "
          f"(registered as ~0.80 at ~38.5 Hz)")
    OUT["baseline_pooled_creep"] = dict(f0=f0, f5=f5, prom5=p5, K=K)
v74c = RUNS_CREEP["V74/r5d"]
if len(v74c) >= 1:
    f0, p0, f5, p5, K = harm5(v74c, 2048)
    print(f"  V74 creep only:      K={K}  f0 {f0:.2f}  5xf0 {f5:.2f} Hz  prominence {p5:.2f}   "
          f"⚠ K={K} -- 2 runs, indicative")
    OUT["v74_creep_5xf0"] = dict(f0=f0, f5=f5, prom5=p5, K=K)

# ---- the K-free second method ---------------------------------------------------------------
L.hdr("FALSIFIER B, SECOND METHOD -- per-WINDOW prominence at 5 x f0, which carries no K bias")
print("  Every NFFT-512 window's own prominence spectrum, read at its own 5 x f0. Median over")
print("  windows with the CI resampling RUNS. An averaged-spectrum prominence rises with K; this")
print("  does not, so if the two disagree, this one is the safer number.\n")
pw5 = {}
for b in BUILDS:
    vals, un = [], []
    for r in RUNS[b]:
        x, fs = r["x"], r["fs"]
        f = np.fft.rfftfreq(512, 1 / fs)
        for i in range(0, len(x) - 512 + 1, 256):
            P = C.periodogram(x[i:i + 512], fs, 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            f0, p0 = G.locate(f, P, 6, 9, R=R)
            if not np.isfinite(f0) or p0 < 3.0:
                continue
            j = int(np.argmin(np.abs(f - 5 * f0)))
            w = slice(max(0, j - 2), j + 3)
            k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
            vals.append(float(R[k]))
            un.append(r["run"])
    if len(vals) < 10:
        print(f"  {b:<10}  -- {len(vals)} windows, underpowered")
        continue
    per = {}
    for v, u in zip(vals, un):
        per.setdefault(u, []).append(v)
    ks = list(per)
    dr = np.array([np.median(np.concatenate([per[ks[j]] for j in RNG.integers(0, len(ks), len(ks))]))
                   for _ in range(3000)])
    lo, hi = np.nanpercentile(dr, [2.5, 97.5])
    pw5[b] = dict(med=float(np.median(vals)), lo=float(lo), hi=float(hi), n=len(vals))
    print(f"  {b:<10} n={len(vals):>4}  median prominence at 5xf0 {np.median(vals):>5.2f} "
          f"[{lo:.2f}, {hi:.2f}]")
OUT["falsifier_B_perwindow"] = pw5

# ================================================================== A ============================
L.hdr("FALSIFIER A -- duty ratio > 1.2 AND prominence ratio > 1.3, BOTH required")
print("  duty = the 6-9 Hz relative burst duty (d6b's own definition). prominence = the per-window")
print("  6-9 Hz line prominence (`p_6-9`), median, run-resampled -- K-free.\n")
duty, prom = {}, {}
for b in BUILDS:
    rs = RUNS[b]
    dv, du = [], []
    pv, pu = [], []
    for r in rs:
        env = np.abs(D.analytic(D.bp(r["x"], r["fs"], *D.RATCHET)))
        bs = bursts(env, r["fs"])
        dv.append(float(sum(j - i for i, j, _ in bs) / max(len(env), 1)))
        du.append(r["run"])
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            _, pp = G.locate(f, P, 6.0, 9.0)
            if np.isfinite(pp):
                pv.append(pp)
                pu.append(r["run"])
    duty[b] = (dv, du)
    prom[b] = (pv, pu)


def rr(av, au, bv, bu, nb=3000):
    pa, pb = {}, {}
    for v, u in zip(av, au):
        pa.setdefault(u, []).append(v)
    for v, u in zip(bv, bu):
        pb.setdefault(u, []).append(v)
    ka, kb = list(pa), list(pb)
    if len(ka) < 2 or len(kb) < 2:
        return (np.nan,) * 3
    dr = np.full(nb, np.nan)
    for i in range(nb):
        x = np.median(np.concatenate([pa[ka[j]] for j in RNG.integers(0, len(ka), len(ka))]))
        y = np.median(np.concatenate([pb[kb[j]] for j in RNG.integers(0, len(kb), len(kb))]))
        dr[i] = x / y if y else np.nan
    obs = (np.median(np.concatenate([pa[k] for k in ka])) /
           np.median(np.concatenate([pb[k] for k in kb])))
    return float(obs), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


print(f"  {'vs build':<10} {'duty ratio':>22} {'prominence ratio':>22}   FALSIFIER A")
for b in ("V73/r5a", "V72/r59", "V59/r2c", "V58/r2b"):
    d_ = rr(*duty["V74/r5d"], *duty[b])
    p_ = rr(*prom["V74/r5d"], *prom[b])
    fired = "🛑 FIRES" if (d_[0] > 1.2 and p_[0] > 1.3) else "clear"
    print(f"  {b:<10} {d_[0]:6.3f} [{d_[1]:5.2f},{d_[2]:6.2f}] {p_[0]:6.3f} "
          f"[{p_[1]:5.2f},{p_[2]:6.2f}]   {fired}")
    OUT.setdefault("falsifier_A", {})[b] = dict(duty=list(d_), prom=list(p_), fires=fired)

# ================================================================== C ============================
L.hdr("FALSIFIER C -- Δf0, raw and SPEED-MATCHED")
print("  f0 is known to FALL with load, and the arms differ in speed, so the raw difference is")
print("  confounded. The matched version pools per-window f0 inside shared speed bins.\n")
VB = [(0.0, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
f0w = {}
for b in BUILDS:
    rows = []
    for r in RUNS[b]:
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            ff, pp = G.locate(f, P, 5, 12, R=R)
            if np.isfinite(ff) and pp >= 3.0:
                rows.append((ff, r["v"], r["run"]))
    f0w[b] = rows
print(f"  {'build':<10} " + " ".join(f"{lo:.0f}-{hi:.1f}".rjust(11) for lo, hi in VB) + "   overall")
for b in BUILDS:
    cells = []
    for lo, hi in VB:
        v = [x for x, vv, _ in f0w[b] if lo <= vv < hi]
        cells.append(f"{np.median(v):>6.2f}({len(v):>3})" if len(v) >= 8 else f"{'--':>11}")
    allv = [x for x, _, _ in f0w[b]]
    print(f"  {b:<10} " + " ".join(c.rjust(11) for c in cells) +
          f"   {np.median(allv):.2f}" if allv else "")
for b in ("V73/r5a", "V72/r59"):
    ds, ws = [], []
    for lo, hi in VB:
        a = [x for x, vv, _ in f0w["V74/r5d"] if lo <= vv < hi]
        c = [x for x, vv, _ in f0w[b] if lo <= vv < hi]
        if len(a) >= 8 and len(c) >= 8:
            ds.append(np.median(a) - np.median(c))
            ws.append(1.0 / (1.0 / len(a) + 1.0 / len(c)))
    if ds:
        md = float(np.average(ds, weights=ws))
        print(f"\n  SPEED-MATCHED Δf0(V74 - {b}) = {md:+.3f} Hz over {len(ds)} shared speed bins   "
              f"=> |Δf0| <= 0.3 {'PASS' if abs(md) <= 0.3 else 'FAIL'} · "
              f"> 0.5 {'ABORT' if abs(md) > 0.5 else 'clear'}")
        OUT.setdefault("falsifier_C", {})[b] = dict(matched=md, nbins=len(ds))
    else:
        print(f"\n  SPEED-MATCHED Δf0(V74 - {b}): no shared speed bin with >= 8 windows both sides")

with open(ROOT / "_r5d_falsifiers.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _r5d_falsifiers.json")
