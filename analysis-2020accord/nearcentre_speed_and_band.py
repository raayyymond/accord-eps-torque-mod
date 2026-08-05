#!/usr/bin/env python3
"""THE 25 mph CEILING, the ZERO-CROSSING hypothesis, and the MICRO-RATCHET BAND PRIOR.

ss1  THE SPEED CEILING. The operator reports grind #1 gone above 25 mph (11.18 m/s). Where does
     `e_18-22` actually collapse, and is the collapse SHARP (a firmware breakpoint) or GRADUAL?
     FactorC's first breakpoint is 35.0 km/h = 9.72 m/s = 21.7 mph, strikingly close, so the shape
     matters as much as the location. 🛑 Engaged exposure thins fast with speed on most routes --
     the census is printed with every number.

ss2  THE ZERO-CROSSING HYPOTHESIS. "Near centre" and "crossing centre" are different physical
     claims and only the second implicates a deadband / hysteresis / torque-reversal nonlinearity.
     Tested on the RE-CENTRED angle, at matched manoeuvre rate, plus the same test on the torque
     channel's own sign reversal.

ss3  THE MICRO-RATCHET BAND PRIOR. The operator reports a NEW low-amplitude non-audible ratcheting
     felt in the column at creep, distinct from the 7.79 Hz ratchet V72 targets. Swept on the best
     prior builds (V67/V68) as an averaged prominence spectrum over 1.5-18 Hz, engaged creep, with
     the manual arm and the stock pool beside it so a line that is merely the CAR is visible as
     such. 🛑 A wheel order moves with speed, so the per-window speed census is mandatory
     (memory: accord-averaged-spectrum-needs-matched-speed-distributions).

Usage: python nearcentre_speed_and_band.py [ep|blk]  -> writes _nearcentre_speed_band.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r58_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT = 2000
OUT = {"epkey": G.EPKEY}

store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["a_c"] = r["a_mean"] - c
        r["absa"] = abs(r["a_c"])
        r["ab"] = N.abin(r["absa"])
        # 🛑 the re-centred crossing, not the raw one: with a -4.4 deg sensor offset a raw
        # `min<0<max` test asks whether the wheel crossed a point 4.4 deg off the sensor's zero.
        r["x_c"] = float((r["a_min"] - c) < 0.0 < (r["a_max"] - c))

# ------------------------------------------------------------------ ss1 the speed ceiling --------
N.hdr("ss1  ★★★ THE SPEED CEILING -- where does e_18-22 actually collapse, and how sharply?")
VE = [0, 1, 2, 3, 4, 5.556, 7, 8.5, 9.72, 11.18, 13, 15, 18, 22, 1e9]
VN = ["0-1", "1-2", "2-3", "3-4", "4-5.6", "5.6-7", "7-8.5", "8.5-9.7", "9.7-11.2", "11.2-13",
      "13-15", "15-18", "18-22", "22+"]
print("  Bin edges are placed ON the two candidate breakpoints: 5.556 m/s = the kit's creep cut")
print("  (20 km/h), 9.72 m/s = FactorC's first breakpoint (35.0 km/h = 21.7 mph), 11.18 m/s =")
print("  the operator's 25 mph. ENGAGED windows only, all angles.\n")


def vbins(rs):
    out = []
    for i in range(len(VN)):
        c = [r for r in rs if VE[i] <= r["v"] < VE[i + 1]]
        nb = len({r[G.EPKEY] for r in c})
        if len(c) < 8 or nb < 3:
            v = G.col(c, "e_18-22")
            v = v[np.isfinite(v)]
            out.append(dict(n=len(c), nb=nb, med=float(np.median(v)) if len(v) else np.nan,
                            lo=np.nan, hi=np.nan, thin=True))
        else:
            m, lo, hi = G.boot_median_ci(c, "e_18-22", RNG, nboot=NBOOT)
            out.append(dict(n=len(c), nb=nb, med=float(m), lo=float(lo), hi=float(hi), thin=False))
    return out


ARM_ALL = {k: [r for n in v for r in store[n]] for k, v in N.ARMS.items()}
ARM_ALL["POOLED"] = [r for b in N.LADDER for r in store[b]]
sp = {}
print(f"  {'arm / mask':<20} " + " ".join(f"{n:>12}" for n in VN))
for k in ["POOLED"] + list(N.ARMS):
    for lab, m in (("engaged", 1), ("manual", 0)):
        rs = [r for r in ARM_ALL[k] if r["eng"] == m]
        row = vbins(rs)
        sp[f"{k}|{lab}"] = row
        cells = []
        for d in row:
            if d["n"] == 0:
                cells.append(f"{'EMPTY':>12}")
            elif d["thin"]:
                cells.append(f"{d['med']:>6.0f}~n{d['n']:<3}".rjust(12))
            else:
                cells.append(f"{d['med']:>7.0f}n{d['n']:<3}".rjust(12))
        print(f"  {k + ' ' + lab:<20} " + " ".join(cells))
        if k == "POOLED" and m == 0:
            print()
    if k == "POOLED":
        print()
OUT["speed"] = sp

print("\n  --- SHARP OR GRADUAL? engaged, pooled: ratio of consecutive speed bins")
row = sp["POOLED|engaged"]
for i in range(1, len(VN)):
    a, b = row[i - 1], row[i]
    if not (np.isfinite(a["med"]) and np.isfinite(b["med"]) and a["med"] > 0):
        continue
    flag = "  <-- LARGEST DROP" if b["med"] / a["med"] < 0.45 else ""
    print(f"      {VN[i - 1]:>9} -> {VN[i]:<9} {b['med'] / a['med']:>7.3f}  "
          f"(n {a['n']} -> {b['n']}){flag}")

# ------------------------------------------------------------------ ss2 zero crossing ------------
N.hdr("ss2  ★★ THE ZERO-CROSSING HYPOTHESIS -- 'near centre' vs 'CROSSING centre'")
print("  A crossing window contains a sign change of the RE-CENTRED angle, so the torque through")
print("  the column reverses inside it. That is what a deadband / hysteresis / friction")
print("  nonlinearity would key on, and it is a different claim from 'the angle is small'.")
print("  Stratified on (v, eff, |rate| bin) with the ANGLE BIN ALSO in the stratum, so a crossing")
print("  window is only ever compared against a non-crossing window at the SAME angle and rate.\n")

RB2 = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 64.0), (64.0, 128.0), (128.0, 1e9)]
for b in N.LADDER:
    for r in store[b]:
        r["rb2"] = G.binof(r["rate_lp"], RB2)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
POOL = [r for b in N.LADDER for r in ENGC[b]]

print(f"      {'arm':<12} {'nX':>5} {'n~X':>5} {'medX':>8} {'med~X':>8} {'ratio':>7} "
      f"{'[95% CI]':>17} {'cells':>6} {'null':<16} p")
zc = {}
for k in ["POOLED"] + list(N.ARMS):
    rs = N.recell(POOL if k == "POOLED" else ARM[k],
                  lambda r: (r["cell"][1], r["cell"][2], r["rb2"], r["ab"]))
    A = [r for r in rs if r["x_c"] > 0.5]
    B = [r for r in rs if r["x_c"] <= 0.5]
    if len(A) < 8 or len(B) < 8:
        print(f"      {k:<12} {len(A):>5} {len(B):>5}   *** UNDERPOWERED")
        zc[k] = dict(nA=len(A), nB=len(B), underpowered=True)
        continue
    ratio, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, "e_18-22", RNG, nboot=NBOOT,
                                                        min_ep=2, min_win=4)
    nl = G.split_half_null(rs, "e_18-22", RNG, nrep=200, min_ep=2, min_win=4)
    _, p = G.perm_p(A, B, "e_18-22", RNG, nperm=1500, min_ep=2, min_win=4)
    zc[k] = dict(nA=len(A), nB=len(B), ratio=float(ratio), lo=float(lo), hi=float(hi),
                 ncells=int(nc), null=[float(x) for x in nl], p=float(p),
                 medA=float(np.median(G.col(A, "e_18-22"))),
                 medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"      {k:<12} {len(A):>5} {len(B):>5} {np.median(G.col(A, 'e_18-22')):>8.0f} "
          f"{np.median(G.col(B, 'e_18-22')):>8.0f} {ratio:>7.3f} [{lo:>7.3f},{hi:>8.3f}] "
          f"{nc:>6} [{nl[1]:.2f},{nl[2]:.2f}]".ljust(0) + f"  {p:.4f}")
OUT["zero_cross"] = zc

# ------------------------------------------------------------------ ss3 micro-ratchet band -------
N.hdr("ss3  ★★★ THE MICRO-RATCHET BAND PRIOR -- averaged spectrum 1.5-18 Hz, engaged creep")
print("  Averaged periodogram over DISJOINT engagement runs (never spliced), then the PROMINENCE")
print("  spectrum (peak / local median floor). Peak-find AFTER averaging. Speed census beside it,")
print("  and each candidate line's wheel-order prediction n*v/2.08 m at the arm's own mean speed.\n")

ARMS_SPEC = {"V67+V68 (best)": ["V67/r47", "V68/r4e"], "stock pool": N.ARMS["stock pool"],
             "V62+V65": N.ARMS["V62+V65"], "V71C/r58": ["V71C/r58"], "V71B/r54": ["V71B/r54"]}
band = {}
for k, names in ARMS_SPEC.items():
    for lab, mfn in (("engaged", L.eng_mask), ("manual", L.man_mask)):
        accs, Ks, vs, fref = [], 0, [], None
        for n in names:
            segs = [s for s in G.BUILDS[n]["segs"] if s not in L.PARKED.get(n, [])]
            f, P, K, stack, meta = L.avg_periodogram(n, mask_fn=mfn, vlo=0.0, vhi=N.CREEP,
                                                     segs=segs)
            if P is None or K == 0:
                continue
            fref, Ks = f, Ks + K
            accs.append(P * K)
            vs += [m["v"] for m in meta]
        if not accs or Ks == 0:
            print(f"  {k:<16} {lab:<8}  *** EMPTY (no engaged-creep windows)")
            continue
        P, f = np.sum(accs, axis=0) / Ks, fref
        R = G.prom_spectrum(f, P)
        vm = float(np.mean(vs))
        print(f"  --- {k:<16} {lab:<8} K={Ks:<5} v = {vm:.2f} +/- {np.std(vs):.2f} m/s "
              f"| wheel orders 1/2/3 = {L.wheel_order(vm):.2f} / {L.wheel_order(vm, 2):.2f} / "
              f"{L.wheel_order(vm, 3):.2f} Hz")
        # every local maximum of the prominence spectrum in 1.5-18 Hz, strongest first
        m = (f >= 1.5) & (f <= 18.0) & np.isfinite(R)
        idx = [i for i in np.flatnonzero(m)
               if 0 < i < len(R) - 1 and R[i] >= R[i - 1] and R[i] >= R[i + 1]]
        idx.sort(key=lambda i: -R[i])
        rows = []
        for i in idx[:6]:
            # amplitude of that line, as a p-p torque count: P is |rfft(hann)|^2 of a 256-pt window
            amp = float(2 * np.sqrt(P[i]) / (0.5 * G.NFFT))
            rows.append(dict(f=float(f[i]), prom=float(R[i]), pp=2 * amp))
            print(f"        f = {f[i]:>6.2f} Hz   prominence {R[i]:>7.2f}   "
                  f"amplitude ~{amp:>7.1f} counts ({2 * amp:>7.1f} p-p)")
        band[f"{k}|{lab}"] = dict(K=Ks, v=vm, vsd=float(np.std(vs)), peaks=rows)
        print()
OUT["band"] = band

(HERE.parent / "_nearcentre_speed_band.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_nearcentre_speed_band.json'}")
