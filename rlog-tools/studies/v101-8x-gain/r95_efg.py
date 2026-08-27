#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- **E. DRIVER-TORQUE SUPPRESSION**, **G. COMMAND PROPORTIONALITY**,
**F. IS OPENPILOT IN THE LOOP**.

WINDOW TABLE: NON-OVERLAPPING 2.0 s windows over the contiguous engaged runs.  Overlapping
windows are NOT used anywhere a CI is quoted (they inflate dof).  A moving-BLOCK bootstrap over
blocks of 3 consecutive windows (6 s) is used for every interval, and the SPLIT-HALF NULL runs
FIRST -- no ratio is quoted until the split-half agrees.

CHANNELS / TRAPS
  * `tq` is the driver torsion bar.  The oscillation LIVES in it, so |tq| raw is contaminated.
    The driver's SUSTAINED push is `lowpass(tq, 3 Hz)`; the oscillation is `band_envelope(tq)`.
  * 🛑 SIGN: +LKAS demands NEGATIVE angle, +driver torque demands POSITIVE angle.  `sc_tq_ang`
    = -sc_tq is the command in the ANGLE frame.  Only magnitudes are stratified on, so the flip
    matters only for the coherence phase, where it is applied and stated.
  * The angle-sensor zero is offset LEFT; the measured centre offset is -4.25 deg (V100 record).
    `ang_off` = ang - CENTRE is used for the "off-centre" operating-point term.
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

import numpy as np

import r95_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.fs()
lat = L.engaged()
n = len(lat)
CENTRE = -4.25                       # deg, the measured angle-sensor zero offset (LEFT)

tq = L.col("tq")
ang = L.col("ang")
rate_f = L.col("rate_f")
x6b94 = L.col("x6b94")
sc_tq = L.col("sc_tq")
vms = np.abs(L.col("cs_v"))
press = L.col("cs_press")

BANDS = {"B8  (7.3-9.3 Hz)": (7.3, 9.3),
         "B23 (21.5-25.5 Hz)": (21.5, 25.5),
         "CTRL (2.5-4.5 Hz)": (2.5, 4.5),
         "CTRL2 (33-43 Hz)": (33.0, 43.0)}

ENV = {}
for bn, (lo, hi) in BANDS.items():
    ENV[("tq", bn)] = L.bandpass(tq, FS, lo, hi, mask=lat)
    ENV[("rate_f", bn)] = L.bandpass(rate_f, FS, lo, hi, mask=lat)
    ENV[("x6b94", bn)] = L.bandpass(x6b94, FS, lo, hi, mask=lat)

tq_sus = L.lowpass(tq, FS, 3.0, mask=lat)          # the driver's sustained push (signed)
cmd_sus = L.lowpass(sc_tq, FS, 3.0, mask=lat)      # the LKAS demand (signed, native frame)

WLEN = int(round(2.0 * FS))
rows = []


def _runs(mask, min_n):
    idx = np.where(mask)[0]
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            if prev - s + 1 >= min_n:
                out.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        out.append((s, prev + 1))
    return out


for a, b in _runs(lat, WLEN):
    for i in range(a, b - WLEN + 1, WLEN):
        sl = slice(i, i + WLEN)
        r = dict(i0=i, sec=WLEN / FS,
                 v=float(np.median(vms[sl])),
                 tq_sus=float(np.median(np.abs(tq_sus[sl]))),
                 cmd=float(np.median(np.abs(cmd_sus[sl]))),
                 ang_off=float(np.median(np.abs(ang[sl] - CENTRE))),
                 rate=float(np.median(np.abs(rate_f[sl]))),
                 press=float(np.mean(press[sl])))
        for bn in BANDS:
            for ch in ("tq", "rate_f", "x6b94"):
                e = ENV[(ch, bn)][sl]
                e = e[np.isfinite(e)]
                r[f"{ch}|{bn}"] = float(np.sqrt(np.mean(e ** 2)))   # BAND RMS of the signal
        rows.append(r)

NW = len(rows)
print(f"{NW} NON-OVERLAPPING 2.0 s engaged windows  = {NW*2.0:.1f} s")
V = {k: np.array([r[k] for r in rows], float) for k in rows[0]}

out = {"n_windows": NW, "window_s": 2.0, "centre_deg": CENTRE}

# =====================================================================================
#  0. THE SPLIT-HALF NULL CONTROL -- run BEFORE any ratio is quoted
# =====================================================================================
print("\n" + "=" * 106)
print("0. SPLIT-HALF NULL CONTROL  (blocks of 3 windows, alternating halves).  A statistic that")
print("   does not reproduce across halves may NOT be quoted.")
print("=" * 106)
blk = np.arange(NW) // 3
halfA = (blk % 2) == 0
halfB = ~halfA


def q_ratio(env, sel, lowmask, highmask):
    a = env[sel & lowmask]
    b = env[sel & highmask]
    if len(a) < 4 or len(b) < 4:
        return float("nan")
    return float(np.median(b) / np.median(a))


tq_lo = V["tq_sus"] <= np.percentile(V["tq_sus"], 33)
tq_hi = V["tq_sus"] >= np.percentile(V["tq_sus"], 67)
cmd_lo = V["cmd"] <= np.percentile(V["cmd"], 33)
cmd_hi = V["cmd"] >= np.percentile(V["cmd"], 67)

print(f"    {'statistic':46s} {'ALL':>9s} {'halfA':>9s} {'halfB':>9s}  agree?")
for ch in ("tq", "rate_f"):
    for bn in BANDS:
        e = V[f"{ch}|{bn}"]
        rall = q_ratio(e, np.ones(NW, bool), tq_hi, tq_lo)     # LOW-torque / HIGH-torque
        rA = q_ratio(e, halfA, tq_hi, tq_lo)
        rB = q_ratio(e, halfB, tq_hi, tq_lo)
        ok = "YES" if (np.isfinite(rA) and np.isfinite(rB)
                       and abs(np.log(rA / rB)) < np.log(1.6)) else "🛑 NO"
        print(f"    env({ch},{bn}) LOWtq/HIGHtq{'':>{max(0,10-len(ch))}} "
              f"{rall:9.3f} {rA:9.3f} {rB:9.3f}  {ok}")
        out.setdefault("split_half", []).append(
            dict(ch=ch, band=bn, stat="lowtq_over_hightq", all=rall, A=rA, B=rB, agree=ok))

# =====================================================================================
#  G. AMPLITUDE vs |LKAS COMMAND|   -- THE DISCRIMINATING QUESTION
# =====================================================================================
print("\n" + "=" * 106)
print("G. BAND ENVELOPE vs |LKAS COMMAND|  (median |lowpass(sc_tq,3Hz)| over the window)")
print("   command-PROPORTIONAL relay/gain  =>  envelope rises with |cmd| and -> floor at cmd~0")
print("   UNSTABLE LOOP POLE               =>  envelope is present and large at |cmd| ~ 0")
print("=" * 106)
qs = np.percentile(V["cmd"], [0, 20, 40, 60, 80, 100])
print(f"    |cmd| quintile edges: {np.array2string(qs, precision=1)}")
print(f"    {'|cmd| bin':>18s} {'n':>4s} {'v med':>6s} {'tq_sus':>7s} | " +
      "  ".join(f"{bn.split()[0]:>10s}" for bn in BANDS))
gtab = []
for k in range(5):
    lo, hi = qs[k], qs[k + 1]
    m = (V["cmd"] >= lo) & (V["cmd"] <= hi) if k == 4 else (V["cmd"] >= lo) & (V["cmd"] < hi)
    if m.sum() < 3:
        continue
    line = (f"    {lo:8.1f}-{hi:<8.1f} {int(m.sum()):4d} {np.median(V['v'][m]):6.2f} "
            f"{np.median(V['tq_sus'][m]):7.1f} | ")
    rec = dict(lo=float(lo), hi=float(hi), n=int(m.sum()), v=float(np.median(V["v"][m])),
               tq_sus=float(np.median(V["tq_sus"][m])))
    for bn in BANDS:
        val = float(np.median(V[f"tq|{bn}"][m]))
        rec[bn] = val
        line += f"  {val:10.1f}"
    print(line)
    gtab.append(rec)
out["G_env_tq_by_cmd"] = gtab

print("\n    SAME TABLE on rate_f (deg/s):")
print(f"    {'|cmd| bin':>18s} {'n':>4s} | " + "  ".join(f"{bn.split()[0]:>10s}" for bn in BANDS))
for k in range(5):
    lo, hi = qs[k], qs[k + 1]
    m = (V["cmd"] >= lo) & (V["cmd"] <= hi) if k == 4 else (V["cmd"] >= lo) & (V["cmd"] < hi)
    if m.sum() < 3:
        continue
    line = f"    {lo:8.1f}-{hi:<8.1f} {int(m.sum()):4d} | "
    for bn in BANDS:
        line += f"  {np.median(V[f'rate_f|{bn}'][m]):10.2f}"
    print(line)

# --- the headline number: ratio of top-quintile to bottom-quintile |cmd|, with block bootstrap
print("\n    RATIO  env(top |cmd| quintile) / env(bottom |cmd| quintile), block bootstrap "
      "(3-window = 6 s blocks, 4000 draws)")
for ch in ("tq", "rate_f"):
    for bn in BANDS:
        e = V[f"{ch}|{bn}"]
        mlo = V["cmd"] <= qs[1]
        mhi = V["cmd"] >= qs[4]
        rng = np.random.default_rng(11)
        blocks = [np.arange(i, min(i + 3, NW)) for i in range(0, NW, 3)]
        bs = []
        for _ in range(4000):
            j = np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])
            a, b = e[j][mlo[j]], e[j][mhi[j]]
            if len(a) >= 3 and len(b) >= 3:
                bs.append(np.median(b) / np.median(a))
        pt = np.median(e[mhi]) / np.median(e[mlo])
        lo95, hi95 = np.percentile(bs, [2.5, 97.5])
        print(f"      {ch:6s} {bn:20s}  {pt:6.3f}  [{lo95:.3f}, {hi95:.3f}]"
              f"{'   ** CI excludes 1' if (lo95 > 1 or hi95 < 1) else ''}")
        out.setdefault("G_ratios", []).append(dict(ch=ch, band=bn, ratio=float(pt),
                                                   lo=float(lo95), hi=float(hi95)))

# =====================================================================================
#  E. DRIVER-TORQUE SUPPRESSION
# =====================================================================================
print("\n" + "=" * 106)
print("E. BAND ENVELOPE vs |SUSTAINED DRIVER TORQUE|  (median |lowpass(tq,3Hz)|, counts)")
print("=" * 106)
qt = np.percentile(V["tq_sus"], [0, 20, 40, 60, 80, 100])
print(f"    |tq_sus| quintile edges (counts): {np.array2string(qt, precision=0)}")
print(f"    {'|tq_sus| bin':>18s} {'n':>4s} {'v med':>6s} {'|cmd|':>7s} {'|ang-c|':>8s} "
      f"{'|rate|':>7s} | " + "  ".join(f"{bn.split()[0]:>10s}" for bn in BANDS))
etab = []
for k in range(5):
    lo, hi = qt[k], qt[k + 1]
    m = (V["tq_sus"] >= lo) & (V["tq_sus"] <= hi) if k == 4 else \
        (V["tq_sus"] >= lo) & (V["tq_sus"] < hi)
    if m.sum() < 3:
        continue
    line = (f"    {lo:8.0f}-{hi:<8.0f} {int(m.sum()):4d} {np.median(V['v'][m]):6.2f} "
            f"{np.median(V['cmd'][m]):7.1f} {np.median(V['ang_off'][m]):8.2f} "
            f"{np.median(V['rate'][m]):7.2f} | ")
    rec = dict(lo=float(lo), hi=float(hi), n=int(m.sum()))
    for bn in BANDS:
        val = float(np.median(V[f"tq|{bn}"][m]))
        rec[bn] = val
        line += f"  {val:10.1f}"
    print(line)
    etab.append(rec)
out["E_env_tq_by_driver_torque"] = etab

print("\n    SAME TABLE on rate_f (deg/s) -- the channel the driver's hand does NOT sit inside:")
print(f"    {'|tq_sus| bin':>18s} {'n':>4s} | " + "  ".join(f"{bn.split()[0]:>10s}" for bn in BANDS))
for k in range(5):
    lo, hi = qt[k], qt[k + 1]
    m = (V["tq_sus"] >= lo) & (V["tq_sus"] <= hi) if k == 4 else \
        (V["tq_sus"] >= lo) & (V["tq_sus"] < hi)
    if m.sum() < 3:
        continue
    line = f"    {lo:8.0f}-{hi:<8.0f} {int(m.sum()):4d} | "
    for bn in BANDS:
        line += f"  {np.median(V[f'rate_f|{bn}'][m]):10.2f}"
    print(line)

print("\n    RATIO  env(bottom |tq_sus| quintile) / env(top quintile)  -- 'how much torque kills "
      "it', block bootstrap")
for ch in ("tq", "rate_f", "x6b94"):
    for bn in BANDS:
        e = V[f"{ch}|{bn}"]
        mlo = V["tq_sus"] <= qt[1]
        mhi = V["tq_sus"] >= qt[4]
        rng = np.random.default_rng(13)
        blocks = [np.arange(i, min(i + 3, NW)) for i in range(0, NW, 3)]
        bs = []
        for _ in range(4000):
            j = np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])
            a, b = e[j][mhi[j]], e[j][mlo[j]]
            if len(a) >= 3 and len(b) >= 3:
                bs.append(np.median(b) / np.median(a))
        pt = np.median(e[mlo]) / np.median(e[mhi])
        lo95, hi95 = np.percentile(bs, [2.5, 97.5])
        print(f"      {ch:6s} {bn:20s}  {pt:6.3f}  [{lo95:.3f}, {hi95:.3f}]"
              f"{'   ** CI excludes 1' if (lo95 > 1 or hi95 < 1) else ''}")
        out.setdefault("E_ratios", []).append(dict(ch=ch, band=bn, ratio=float(pt),
                                                   lo=float(lo95), hi=float(hi95)))

# =====================================================================================
#  E-2.  IS IT |TORQUE| OR THE OPERATING POINT?   -- a weighted multiple regression
# =====================================================================================
print("\n" + "=" * 106)
print("E-2. PARTIALLING:  log10 env  ~  a*log10(1+|tq_sus|) + b*log10(1+|ang-c|) + "
      "c*log10(1+|rate|) + d*log10(1+|cmd|) + e*v")
print("   All five terms are entered together, so each coefficient is the PARTIAL effect.")
print("   The CTRL bands are the negative control: a real band-specific effect must NOT appear "
      "there.")
print("=" * 106)
X = np.column_stack([np.log10(1 + V["tq_sus"]), np.log10(1 + V["ang_off"]),
                     np.log10(1 + V["rate"]), np.log10(1 + V["cmd"]), V["v"],
                     np.ones(NW)])
NAMES = ["log|tq_sus|", "log|ang-c|", "log|rate|", "log|cmd|", "v m/s", "const"]
rng = np.random.default_rng(17)
blocks = [np.arange(i, min(i + 3, NW)) for i in range(0, NW, 3)]
for ch in ("tq", "rate_f"):
    print(f"\n    --- channel {ch} ---")
    print("      " + f"{'band':20s}" + "".join(f"{nm:>22s}" for nm in NAMES[:4]) + f"{'R2':>7s}")
    for bn in BANDS:
        y = np.log10(np.maximum(V[f"{ch}|{bn}"], 1e-6))
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        bs = []
        for _ in range(3000):
            j = np.concatenate([blocks[k] for k in rng.integers(0, len(blocks), len(blocks))])
            try:
                bs.append(np.linalg.lstsq(X[j], y[j], rcond=None)[0])
            except np.linalg.LinAlgError:
                pass
        bs = np.array(bs)
        r2 = 1 - np.var(y - X @ beta) / np.var(y)
        cells = ""
        for c in range(4):
            lo95, hi95 = np.percentile(bs[:, c], [2.5, 97.5])
            star = "*" if (lo95 > 0 or hi95 < 0) else " "
            cells += f"{beta[c]:+7.3f}[{lo95:+6.3f},{hi95:+6.3f}]{star}"
        print(f"      {bn:20s}" + cells + f"{r2:7.3f}")
        out.setdefault("E2_regression", []).append(
            dict(ch=ch, band=bn, r2=float(r2),
                 coefs={NAMES[c]: dict(beta=float(beta[c]),
                                       lo=float(np.percentile(bs[:, c], 2.5)),
                                       hi=float(np.percentile(bs[:, c], 97.5)))
                        for c in range(len(NAMES))}))

# =====================================================================================
#  F.  IS OPENPILOT IN THE LOOP?
# =====================================================================================
print("\n" + "=" * 106)
print("F. COHERENCE  openpilot command (sendcan 0xE4, sign-flipped into the ANGLE frame)  vs")
print("   the oscillation, engaged only.  Control = the SAME command series CIRCULARLY ROTATED")
print("   by 7.3 s inside each run (destroys timing, preserves spectrum exactly).")
print("=" * 106)
cmd_ang = L.lkas_in_angle_frame()
rot = np.copy(cmd_ang)
SHIFT = int(round(7.3 * FS))
for a, b in _runs(lat, WLEN):
    rot[a:b] = np.roll(cmd_ang[a:b], SHIFT % max(1, (b - a)))

for ch, x in (("ang", ang), ("rate_f", rate_f), ("tq", tq), ("x6b94", x6b94)):
    f, coh, ph, K = L.coherence(cmd_ang, x, lat, FS, nfft=256)
    _f, coh0, _p, _K = L.coherence(rot, x, lat, FS, nfft=256)
    chance = 1.0 / K
    print(f"\n    cmd -> {ch}   K={K} NON-OVERLAPPING windows, chance coh^2 = 1/K = {chance:.4f}")
    for bn, (lo, hi) in [("0.5-3 Hz (the command's own band)", (0.5, 3.0))] + \
                        [(b, r) for b, r in BANDS.items()]:
        m = (f >= lo) & (f <= hi)
        c1, c0 = float(coh[m].mean()), float(coh0[m].mean())
        print(f"      {bn:34s} coh² {c1:6.4f}   rotated-control {c0:6.4f}   "
              f"ratio {c1/max(c0,1e-9):5.2f}   phase {float(np.mean(ph[m])):+7.1f}°")
        out.setdefault("F_coherence", []).append(
            dict(ch=ch, band=bn, K=K, coh=c1, control=c0, chance=float(chance)))

# =====================================================================================
#  E-3 / G-2.  MATCHED-OPERATING-POINT STRATA.
#  🛑 The raw quintiles are CONFOUNDED: the top |tq_sus| quintile sits at v = 4.2 m/s with
#  |ang-c| = 135 deg -- a parking manoeuvre, not the same car state at all.  Restrict to a
#  narrow driving stratum first, THEN stratify.
# =====================================================================================
print("\n" + "=" * 106)
print("E-3 / G-2.  MATCHED STRATUM:  v >= 5 m/s  AND  |ang - centre| <= 25 deg")
print("=" * 106)
S = (V["v"] >= 5.0) & (V["ang_off"] <= 25.0)
print(f"    {int(S.sum())} of {NW} windows survive  ({S.sum()*2.0:.0f} s).  "
      f"v {np.percentile(V['v'][S],10):.1f}-{np.percentile(V['v'][S],90):.1f} m/s   "
      f"|ang-c| p90 {np.percentile(V['ang_off'][S],90):.1f} deg")


def strat(sel, key, nbin, label, chans=("tq", "rate_f")):
    q = np.percentile(V[key][sel], np.linspace(0, 100, nbin + 1))
    print(f"\n    --- by {label} within the matched stratum ---")
    print(f"    {'bin':>20s} {'n':>4s} {'v':>5s} {'|ang-c|':>8s} {'|rate|':>7s} {'|cmd|':>7s} "
          f"{'|tq_sus|':>9s} | " +
          "  ".join(f"{ch}:{bn.split()[0]:<10s}" for ch in chans for bn in BANDS))
    rec = []
    for k in range(nbin):
        m = sel & (V[key] >= q[k]) & ((V[key] <= q[k + 1]) if k == nbin - 1
                                      else (V[key] < q[k + 1]))
        if m.sum() < 3:
            continue
        line = (f"    {q[k]:9.0f}-{q[k+1]:<9.0f} {int(m.sum()):4d} {np.median(V['v'][m]):5.1f} "
                f"{np.median(V['ang_off'][m]):8.2f} {np.median(V['rate'][m]):7.2f} "
                f"{np.median(V['cmd'][m]):7.0f} {np.median(V['tq_sus'][m]):9.0f} | ")
        d = dict(lo=float(q[k]), hi=float(q[k + 1]), n=int(m.sum()))
        for ch in chans:
            for bn in BANDS:
                val = float(np.median(V[f"{ch}|{bn}"][m]))
                d[f"{ch}|{bn}"] = val
                line += f"  {val:12.2f}"
        print(line)
        rec.append(d)
    return rec


out["E3_by_torque_matched"] = strat(S, "tq_sus", 4, "|SUSTAINED DRIVER TORQUE| (counts)")
out["G2_by_cmd_matched"] = strat(S, "cmd", 4, "|LKAS COMMAND| (openpilot counts)")
out["G2_by_speed_matched"] = strat(S, "v", 4, "SPEED (m/s)")


def ratio_ci(sel, key, ch, bn, lowhigh, seed):
    """median(env | top quartile of key) / median(env | bottom quartile), block bootstrap."""
    q = np.percentile(V[key][sel], [25, 75])
    e = V[f"{ch}|{bn}"]
    mlo = sel & (V[key] <= q[0])
    mhi = sel & (V[key] >= q[1])
    a, b = (mhi, mlo) if lowhigh == "hi/lo" else (mlo, mhi)
    rng = np.random.default_rng(seed)
    bl = [np.arange(i, min(i + 3, NW)) for i in range(0, NW, 3)]
    bs = []
    for _ in range(4000):
        j = np.concatenate([bl[k] for k in rng.integers(0, len(bl), len(bl))])
        u, w = e[j][a[j]], e[j][b[j]]
        if len(u) >= 3 and len(w) >= 3:
            bs.append(np.median(u) / np.median(w))
    return float(np.median(e[a]) / np.median(e[b])), float(np.percentile(bs, 2.5)), \
        float(np.percentile(bs, 97.5))


print("\n    MATCHED-STRATUM RATIOS (top quartile / bottom quartile), block bootstrap 6 s blocks")
for key, lab, lh in (("tq_sus", "|driver torque|", "hi/lo"), ("cmd", "|LKAS command|", "hi/lo"),
                     ("v", "speed", "hi/lo")):
    print(f"      --- {lab} ---")
    for ch in ("tq", "rate_f"):
        for bn in BANDS:
            pt, lo95, hi95 = ratio_ci(S, key, ch, bn, lh, seed=hash((key, ch, bn)) % 10000)
            flag = "  ** CI excludes 1" if (lo95 > 1 or hi95 < 1) else ""
            print(f"        {ch:6s} {bn:20s} {pt:6.3f}  [{lo95:.3f}, {hi95:.3f}]{flag}")
            out.setdefault("matched_ratios", []).append(
                dict(key=key, ch=ch, band=bn, ratio=pt, lo=lo95, hi=hi95))

(L.CACHE / "r95_EFG.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_EFG.json'}")
