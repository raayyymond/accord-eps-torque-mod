#!/usr/bin/env python3
"""DELIVERABLES 4, 5, 6 -- the saturation cost, command-bar coherence, and the episode inventory.

ss1  SATURATION (deliverable 4). V69's disclosed cost is that its peak gain 12288 rails the r24 lane
     at |dtorque| = 683 against a repo-recorded max of 839 (margin 0.81x). |dtorque| is the firmware
     cell gp-0x4f62 = (x[n] - x[n-4])/2 at 1 kHz. CAN cannot form a 4 ms difference at 100 Hz, but it
     CAN apply that difference's transfer function exactly for everything the grid represents:
         |H(f)| = |sin(pi * f * 0.004)|
     🛑 SILENT above 50 Hz, and |H| is still RISING there (0.35 @28 Hz, 0.59 @50, 0.95 @100), so
     EVERY |dtorque| figure in this kit -- including the 839 and the 511 -- is a LOWER BOUND.
     UNITS: counts on the STEER_TORQUE_SENSOR scale (CAN 0x18F bytes 0:1, signed, x-1). Identical
     estimator to `v69_surface_math.measured_dtorque`, so the numbers are comparable to the design.

ss2  COHERENCE (deliverable 5). Magnitude-squared coherence between openpilot's COMMAND and the
     torsion bar. 🛑 The command is `e4tq = i16be(d, 0)` on CAN 0x0E4 (sendcan, src 129). It is NOT
     `e4req = (d[2] >> 7) & 1`, which is the engagement BIT -- the kit burned a session computing
     coherence against that and got exact zeros. Both are computed here, and the near-zero variance
     of the bit is printed, so the wiring is visible rather than assumed. Recorded benchmark for
     grind #1: 0.917.

ss3  EPISODE INVENTORY (deliverable 6). An episode is a contiguous stretch where the 18-22 Hz
     analytic envelope of the bar exceeds a threshold SET FROM THIS ROUTE'S OWN MANUAL ARM (p99 of
     the disengaged envelope), so it is calibrated against what this car does with no LKAS on the
     same tyres, road and day -- not against an arbitrary constant.

Writes `_scratch/out/_r4f_sat_coh.json`.  Usage: python studies/sessions/r4f/r4f_saturation_coherence.py
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
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r4f_lib as L  # noqa: E402

L.install_fs()
RNG = np.random.default_rng(20260803)
OUT = {}
BUILD = "V69/r4f"
B = G.BUILDS[BUILD]
NFFT = G.NFFT

# V69's rail point for the r24 lane, from build_v69_tva / v69_surface_math.
RAIL_X4 = 683       # peak gain 12288
RAIL_X2 = 1366      # the x2 cut that was NOT built
REPO_MAX = 839      # the repo-recorded corpus max |dtorque| (itself a lower bound)


def dtorque(tq, fs=100.0):
    """gp-0x4f62's magnitude via the firmware's own difference transfer function. LOWER BOUND."""
    x = np.asarray(tq, float)
    ok = np.isfinite(x)
    x = np.where(ok, x, 0.0)
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(n, d=1 / fs)
    return np.fft.irfft(X * np.abs(np.sin(np.pi * f * 0.004)), n)


# ================================================================== ss1 saturation ================
L.hdr("ss1  DELIVERABLE 4 -- the |dtorque| distribution on route 4f, and V69's rail at 683")
print(f"  UNITS: STEER_TORQUE_SENSOR counts. V69 peak gain 12288 rails the r24 lane at "
      f"|dtorque| >= {RAIL_X4}.")
print(f"  🛑 Every figure below -- and the repo's {REPO_MAX} and the V68 routes' 511 -- is a "
      f"LOWER BOUND: |H(f)| is silent above 50 Hz and still rising through it.\n")
print(f"  {'seg':>4} {'secs':>6} {'v p50':>6} | {'|dt| p50':>8} {'|dt| p99':>8} {'|dt| p99.9':>10} "
      f"{'|dt| max':>8} | {'frac > 683':>10} {'frac > 1366':>11} | {'|tq| max':>8}")
segrows, dt_all, dt_eng, meta_all = [], [], [], []
for s in B["segs"]:
    d = C.load(s, B["cache"], B["pfx"])
    fs = G.fs_of(d)
    tq = np.asarray(d["tq"], float)
    dt = np.abs(dtorque(tq, fs))
    eng = np.asarray(d["cc_lat"], float) > 0.5
    v = np.abs(np.asarray(d["cs_v"], float))
    dt_all.append(dt)
    dt_eng.append(dt[eng])
    meta_all.append((v, eng, dt))
    row = dict(seg=int(s), secs=len(tq) / fs, v=float(np.median(v)),
               p50=float(np.percentile(dt, 50)), p99=float(np.percentile(dt, 99)),
               p999=float(np.percentile(dt, 99.9)), mx=float(dt.max()),
               f683=float((dt > RAIL_X4).mean()), f1366=float((dt > RAIL_X2).mean()),
               tqmax=float(np.abs(tq).max()))
    segrows.append(row)
    print(f"  {s:>4} {row['secs']:>6.1f} {row['v']:>6.2f} | {row['p50']:>8.1f} {row['p99']:>8.1f} "
          f"{row['p999']:>10.1f} {row['mx']:>8.1f} | {100 * row['f683']:>9.4f}% "
          f"{100 * row['f1366']:>10.4f}% | {row['tqmax']:>8.0f}")
DT = np.concatenate(dt_all)
DTE = np.concatenate(dt_eng)
print(f"\n  ROUTE 4f POOLED           n={len(DT)}  p50 {np.percentile(DT, 50):.1f}  "
      f"p99 {np.percentile(DT, 99):.1f}  p99.9 {np.percentile(DT, 99.9):.1f}  max {DT.max():.1f}")
print(f"  ROUTE 4f ENGAGED ONLY     n={len(DTE)}  p50 {np.percentile(DTE, 50):.1f}  "
      f"p99 {np.percentile(DTE, 99):.1f}  p99.9 {np.percentile(DTE, 99.9):.1f}  max {DTE.max():.1f}")
print(f"\n  ★ FRACTION OF TIME THE r24 LANE IS RAILED AT V69's x4 GAIN (|dtorque| > {RAIL_X4}):")
print(f"      whole route  {100 * (DT > RAIL_X4).mean():.4f}%   "
      f"({int((DT > RAIL_X4).sum())} of {len(DT)} samples = "
      f"{(DT > RAIL_X4).sum() / 100.0:.2f} s)")
print(f"      engaged      {100 * (DTE > RAIL_X4).mean():.4f}%   "
      f"({int((DTE > RAIL_X4).sum())} of {len(DTE)} samples = "
      f"{(DTE > RAIL_X4).sum() / 100.0:.2f} s)")
print(f"  ⇒ observed route max {DT.max():.0f} vs the rail {RAIL_X4}: "
      f"{'*** THE LANE DID RAIL' if DT.max() > RAIL_X4 else 'the lane never reached its rail'}"
      f"   (margin {RAIL_X4 / max(DT.max(), 1e-9):.2f}x)")

print("\n  BY SPEED BIN (V69's own breakpoints), engaged only:")
print(f"  {'km/h':>7} {'dose':>6} {'secs':>7} {'|dt| p50':>8} {'|dt| p99':>8} {'|dt| max':>8} "
      f"{'frac>683':>9}")
bysp = {}
for i, nm in enumerate(L.VBIN_NAMES):
    lo, hi = L.VBINS_V69[i]
    sel = np.concatenate([dt[(v >= lo) & (v < hi) & eng] for v, eng, dt in meta_all])
    if not len(sel):
        print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x {'--':>7}   EMPTY")
        bysp[nm] = None
        continue
    bysp[nm] = dict(n=int(len(sel)), secs=len(sel) / 100.0, p50=float(np.percentile(sel, 50)),
                    p99=float(np.percentile(sel, 99)), mx=float(sel.max()),
                    f683=float((sel > RAIL_X4).mean()))
    print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x {len(sel) / 100.0:>7.1f} "
          f"{bysp[nm]['p50']:>8.1f} {bysp[nm]['p99']:>8.1f} {bysp[nm]['mx']:>8.1f} "
          f"{100 * bysp[nm]['f683']:>8.4f}%")
OUT["dtorque"] = dict(segments=segrows, pooled=dict(
    n=int(len(DT)), p50=float(np.percentile(DT, 50)), p99=float(np.percentile(DT, 99)),
    p999=float(np.percentile(DT, 99.9)), mx=float(DT.max()),
    frac_gt_rail=float((DT > RAIL_X4).mean())),
    engaged=dict(n=int(len(DTE)), p50=float(np.percentile(DTE, 50)),
                 p99=float(np.percentile(DTE, 99)), mx=float(DTE.max()),
                 frac_gt_rail=float((DTE > RAIL_X4).mean())),
    by_speed=bysp, rail=RAIL_X4, repo_max=REPO_MAX)

# cross-route context: the same estimator on the comparison caches
print("\n  CROSS-ROUTE CONTEXT -- identical estimator on every cached route:")
print(f"  {'build':<10} {'n':>8} {'|dt| p99':>9} {'|dt| max':>9} {'frac>683':>9}")
ctx = {}
for bname in ["V69/r4f"] + L.POOL_KD2 + L.POOL_GATED + L.POOL_KD1:
    if bname not in G.BUILDS:
        continue
    Bx = G.BUILDS[bname]
    acc = []
    for s in Bx["segs"]:
        p = Bx["cache"] / f"{Bx['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, Bx["cache"], Bx["pfx"])
        acc.append(np.abs(dtorque(d["tq"], G.fs_of(d))))
    if not acc:
        continue
    a = np.concatenate(acc)
    ctx[bname] = dict(n=int(len(a)), p99=float(np.percentile(a, 99)), mx=float(a.max()),
                      f683=float((a > RAIL_X4).mean()))
    print(f"  {bname:<10} {len(a):>8} {ctx[bname]['p99']:>9.1f} {ctx[bname]['mx']:>9.1f} "
          f"{100 * ctx[bname]['f683']:>8.4f}%")
OUT["dtorque_context"] = ctx

# ================================================================== ss2 coherence =================
L.hdr("ss2  DELIVERABLE 5 -- COMMAND <-> BAR COHERENCE.  Command = e4tq, NEVER the engagement bit")


def coherence(x, y, fs, nfft=NFFT, hop=None):
    """(f, Cxy) by Welch averaging of the cross- and auto-spectra. Hann, 50% overlap, detrended."""
    hop = hop or nfft // 2
    w = np.hanning(nfft)
    Pxx = Pyy = Pxy = None
    K = 0
    for i in range(0, len(x) - nfft + 1, hop):
        a, b = np.asarray(x[i:i + nfft], float), np.asarray(y[i:i + nfft], float)
        if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
            continue
        r = np.arange(nfft, dtype=float)
        a = (a - np.polyval(np.polyfit(r, a, 1), r)) * w
        b = (b - np.polyval(np.polyfit(r, b, 1), r)) * w
        A, Bf = np.fft.rfft(a), np.fft.rfft(b)
        pxx, pyy, pxy = np.abs(A) ** 2, np.abs(Bf) ** 2, A * np.conj(Bf)
        Pxx = pxx if Pxx is None else Pxx + pxx
        Pyy = pyy if Pyy is None else Pyy + pyy
        Pxy = pxy if Pxy is None else Pxy + pxy
        K += 1
    if not K:
        return None, None, 0
    f = np.fft.rfftfreq(nfft, 1 / fs)
    with np.errstate(all="ignore"):
        Cxy = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    return f, Cxy, K


print("  WIRING CHECK first -- variance of each candidate 'command' channel on route 4f:")
vv = {"e4tq (i16be(d,0), THE COMMAND)": [], "e4req ((d[2]>>7)&1, the ENGAGEMENT BIT)": []}
for s in B["segs"]:
    d = C.load(s, B["cache"], B["pfx"])
    vv["e4tq (i16be(d,0), THE COMMAND)"].append(np.asarray(d["e4tq"], float))
    vv["e4req ((d[2]>>7)&1, the ENGAGEMENT BIT)"].append(np.asarray(d["e4req"], float))
for k, arrs in vv.items():
    a = np.concatenate(arrs)
    print(f"    {k:<42} sd={np.std(a):>9.2f}  min={a.min():>8.1f} max={a.max():>8.1f}  "
          f"distinct={len(np.unique(np.round(a, 3)))}")
print("  ⇒ a channel with 2 distinct values cannot carry a 21 Hz line; an exact 0.000 coherence")
print("    across every band is a wiring error, not a result.\n")

coh = {}
print(f"  {'cell':<40} {'runs':>5} {'K':>5} {'C 18-22 max':>12} {'f at max':>9} "
      f"{'C at 20.4':>10} {'C 1-4':>7} {'C 24-28':>8} {'C 30-40':>8}")


def coh_cell(label, pick, chan_cmd="e4tq"):
    Fs, Cs, Ks = [], [], 0
    nruns = 0
    accx = accy = accxy = None
    for s in B["segs"]:
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        m = pick(d)
        x = np.asarray(d[chan_cmd], float)
        y = np.asarray(d["tq"], float)
        for a, b in C.runs_of(m, d["t"], NFFT):
            nruns += 1
            f, Cxy, K = coherence(x[a:b], y[a:b], fs)
            if K == 0:
                continue
            # accumulate SPECTRA, not coherences: averaging coherences across runs is biased high
            w = np.hanning(NFFT)
            hop = NFFT // 2
            for i in range(a, b - NFFT + 1, hop):
                xa, yb = x[i:i + NFFT].astype(float), y[i:i + NFFT].astype(float)
                if not (np.all(np.isfinite(xa)) and np.all(np.isfinite(yb))):
                    continue
                r = np.arange(NFFT, dtype=float)
                xa = (xa - np.polyval(np.polyfit(r, xa, 1), r)) * w
                yb = (yb - np.polyval(np.polyfit(r, yb, 1), r)) * w
                A, Bf = np.fft.rfft(xa), np.fft.rfft(yb)
                accx = np.abs(A) ** 2 if accx is None else accx + np.abs(A) ** 2
                accy = np.abs(Bf) ** 2 if accy is None else accy + np.abs(Bf) ** 2
                accxy = A * np.conj(Bf) if accxy is None else accxy + A * np.conj(Bf)
                Ks += 1
            Fs = f
    if not Ks:
        print(f"  {label:<40} {nruns:>5} {0:>5}   EMPTY")
        return None
    with np.errstate(all="ignore"):
        Cxy = np.abs(accxy) ** 2 / (accx * accy)
    f = Fs

    def bandmax(lo, hi):
        m = (f >= lo) & (f <= hi)
        j = int(np.argmax(np.where(m, Cxy, -1)))
        return float(Cxy[j]), float(f[j])

    def bandmean(lo, hi):
        m = (f >= lo) & (f <= hi)
        return float(np.mean(Cxy[m]))
    c22, f22 = bandmax(18, 22)
    j204 = int(np.argmin(np.abs(f - 20.4)))
    row = dict(runs=nruns, K=Ks, c1822_max=c22, f_at_max=f22, c_at_204=float(Cxy[j204]),
               c14=bandmean(1, 4), c1822=bandmean(18, 22), c2428=bandmean(24, 28),
               c3040=bandmean(30, 40))
    print(f"  {label:<40} {nruns:>5} {Ks:>5} {c22:>12.3f} {f22:>9.2f} "
          f"{row['c_at_204']:>10.3f} {row['c14']:>7.3f} {row['c2428']:>8.3f} {row['c3040']:>8.3f}")
    return row


coh["engaged"] = coh_cell("ENGAGED, all speeds  (cmd = e4tq)", L.eng_mask)
coh["engaged_creep"] = coh_cell("ENGAGED + creep < 2.778 m/s",
                                lambda d: (np.asarray(d["cc_lat"], float) > 0.5)
                                & (np.abs(np.asarray(d["cs_v"], float)) < 2.778))
coh["engaged_hwy"] = coh_cell("ENGAGED + v >= 13.889 m/s (>=50 km/h)",
                              lambda d: (np.asarray(d["cc_lat"], float) > 0.5)
                              & (np.abs(np.asarray(d["cs_v"], float)) >= 13.889))
coh["manual"] = coh_cell("MANUAL (disengaged)  -- the null arm", L.man_mask)
coh["engaged_bit"] = coh_cell("ENGAGED, cmd = e4req  *** THE WIRING ERROR ***", L.eng_mask,
                              chan_cmd="e4req")
OUT["coherence"] = coh
print("\n  Recorded benchmark for grind #1 command<->bar coherence: 0.917.")

# ================================================================== ss3 episode inventory =========
L.hdr("ss3  DELIVERABLE 6 -- GRIND #1 EPISODE INVENTORY on route 4f")
# wall clock: seg 0's `clocks` messages carry a pre-NTP RTC (07:05 vs the route's real 23:01), the
# same defect route 37 seg 0 had. Anchor on segment 1 and step 60 s per segment.
anchors, sds = {}, {}
for s in B["segs"]:
    d = np.load(B["cache"] / f"{B['pfx']}{s}.npz")
    anchors[s] = float(d["wall_t0"][0])
    sds[s] = float(d["wall_off_sd"][0])
# 🛑 The pre-NTP RTC defect is NOT detectable from the offset's VALUE -- seg 0 reads 1751465105,
# a perfectly plausible epoch (2025-07-02). It is detectable from the SPREAD: seg 0's `clocks`
# messages disagree with each other by sd = 1.6e7 s, where every other segment is under 0.01 s.
good = {s: w for s, w in anchors.items() if np.isfinite(sds[s]) and sds[s] < 1.0}
base_seg = min(good)
base_w = good[base_seg]
WALL = {s: base_w + (s - base_seg) * 60.0 for s in B["segs"]}
print(f"  wall clock anchored on seg {base_seg} ({time.strftime('%H:%M:%S', time.localtime(base_w))}"
      f" local, sd {sds[base_seg]:.4f} s), +60 s per segment. 🛑 seg 0's own clocks read "
      f"{time.strftime('%H:%M:%S', time.localtime(anchors[0]))} with sd {sds[0]:.3e} s -- the "
      f"pre-NTP RTC defect route 37 seg 0 also had. UNUSED.")

# threshold from THIS route's own manual arm
man_env = []
for s in B["segs"]:
    d = C.load(s, B["cache"], B["pfx"])
    fs = G.fs_of(d)
    m = np.asarray(d["cc_lat"], float) <= 0.5
    for a, b in C.runs_of(m, d["t"], NFFT):
        man_env.append(C.band_envelope(np.asarray(d["tq"][a:b], float), fs, 18.0, 22.0))
MEN = np.concatenate(man_env) if man_env else np.array([0.0])
THR = float(np.percentile(MEN, 99))
print(f"  threshold = p99 of the 18-22 Hz envelope in this route's OWN MANUAL arm = {THR:.1f} counts"
      f"  (manual n={len(MEN)}, p50 {np.percentile(MEN, 50):.1f}, max {MEN.max():.1f})")
print(f"  an episode = envelope > {THR:.1f} for >= 0.30 s, gaps < 0.50 s merged.\n")

eps = []
for s in B["segs"]:
    d = C.load(s, B["cache"], B["pfx"])
    fs = G.fs_of(d)
    t = np.asarray(d["t"], float)
    env = C.band_envelope(np.asarray(d["tq"], float), fs, 18.0, 22.0)
    hot = env > THR
    idx = np.flatnonzero(hot)
    if not len(idx):
        continue
    runs, st, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if (t[i] - t[prev]) > 0.50:
            runs.append((st, prev))
            st = i
        prev = i
    runs.append((st, prev))
    for a, b in runs:
        if t[b] - t[a] < 0.30:
            continue
        sl = slice(a, b + 1)
        tqs = np.asarray(d["tq"][sl], float)
        eps.append(dict(
            seg=int(s), t0=float(t[a]), dur=float(t[b] - t[a]),
            wall=time.strftime("%H:%M:%S", time.localtime(WALL[s] + t[a])),
            envmax=float(env[sl].max()), pp=float(2 * env[sl].max()),
            tq_pp=float(tqs.max() - tqs.min()),
            v=float(np.mean(np.abs(d["cs_v"][sl]))),
            vkmh=float(3.6 * np.mean(np.abs(d["cs_v"][sl]))),
            ang=float(np.mean(np.abs(d["ang"][sl]))),
            rate=float(np.mean(np.abs(d["rate_c"][sl]))),
            eff=float(np.mean(np.abs(C.sustained(d["tq"][sl], fs)))),
            eng=float(np.mean(np.asarray(d["cc_lat"][sl], float) > 0.5)),
            e4=float(np.mean(np.abs(d["e4tq"][sl]))),
            dtmax=float(np.abs(dtorque(d["tq"], fs))[sl].max())))
eps.sort(key=lambda e: -e["envmax"])
print(f"  {len(eps)} episodes.  ENGAGED-only: {sum(1 for e in eps if e['eng'] > 0.5)}   "
      f"total episode time {sum(e['dur'] for e in eps):.1f} s\n")
print(f"  {'#':>3} {'seg':>3} {'t0':>7} {'wall':>9} {'dur':>5} {'env':>7} {'p-p':>7} "
      f"{'tq p-p':>7} {'km/h':>6} {'ang':>6} {'rate':>6} {'eff':>6} {'eng':>5} {'|e4|':>6} "
      f"{'|dt|max':>7}")
for i, e in enumerate(eps[:40]):
    print(f"  {i + 1:>3} {e['seg']:>3} {e['t0']:>7.2f} {e['wall']:>9} {e['dur']:>5.2f} "
          f"{e['envmax']:>7.0f} {e['pp']:>7.0f} {e['tq_pp']:>7.0f} {e['vkmh']:>6.1f} "
          f"{e['ang']:>6.1f} {e['rate']:>6.1f} {e['eff']:>6.0f} {e['eng']:>5.2f} {e['e4']:>6.0f} "
          f"{e['dtmax']:>7.0f}")
if len(eps) > 40:
    print(f"  ... {len(eps) - 40} more (all in the JSON)")
OUT["episodes"] = eps
OUT["episode_threshold"] = THR

# ★ the coherence the brief actually asks for: command<->bar INSIDE grind-#1 episodes.
L.hdr("ss3b  COMMAND <-> BAR COHERENCE *INSIDE GRIND-#1 EPISODES* -- deliverable 5, properly scoped")
print(f"  mask = 18-22 Hz envelope > {THR:.1f} AND engaged. Recorded benchmark 0.917.\n")
print(f"  {'cell':<40} {'runs':>5} {'K':>5} {'C 18-22 max':>12} {'f at max':>9} "
      f"{'C at 20.4':>10} {'C 1-4':>7} {'C 24-28':>8} {'C 30-40':>8}")


def ep_mask(d, eng=True):
    """The MERGED episode intervals, not the raw threshold crossing.

    🛑 A raw `env > THR` mask flutters at the threshold, so `runs_of` (which needs 256 CONTIGUOUS
    samples) finds nothing and every cell comes back empty -- which is what the first cut of this
    script did. Rebuild the mask from the merged intervals: gaps < 0.50 s closed, >= 0.30 s kept,
    exactly as ss3 defines an episode.
    """
    fs = G.fs_of(d)
    t = np.asarray(d["t"], float)
    env = C.band_envelope(np.asarray(d["tq"], float), fs, 18.0, 22.0)
    lat = np.asarray(d["cc_lat"], float) > 0.5
    m = np.zeros(len(t), bool)
    idx = np.flatnonzero(env > THR)
    if len(idx):
        st = prev = idx[0]
        runs = []
        for i in idx[1:]:
            if (t[i] - t[prev]) > 0.50:
                runs.append((st, prev))
                st = i
            prev = i
        runs.append((st, prev))
        for a, b in runs:
            if t[b] - t[a] >= 0.30:
                m[a:b + 1] = True
    return m & (lat if eng else ~lat)


coh["episodes_engaged"] = coh_cell("GRIND-#1 EPISODES, engaged (cmd = e4tq)", ep_mask)
coh["episodes_creep"] = coh_cell(
    "GRIND-#1 EPISODES, engaged + creep < 2.778",
    lambda d: ep_mask(d) & (np.abs(np.asarray(d["cs_v"], float)) < 2.778))
coh["episodes_hwy"] = coh_cell(
    "GRIND-#1 EPISODES, engaged + v >= 13.889",
    lambda d: ep_mask(d) & (np.abs(np.asarray(d["cs_v"], float)) >= 13.889))
coh["episodes_manual"] = coh_cell("high-18-22 windows, MANUAL -- the null arm",
                                  lambda d: ep_mask(d, eng=False))
OUT["coherence"] = coh

# same inventory on the comparison routes, identical threshold logic, for context
print("\n  CONTEXT -- the same detector on every cached route, EPISODE RATE per engaged second")
print(f"  (each route's threshold is ITS OWN manual p99; route 4f's is {THR:.0f})")
print(f"  {'build':<10} {'thr':>7} {'eps':>5} {'eng eps':>8} {'engaged s':>10} {'eps/eng-s':>10} "
      f"{'median env':>11} {'max env':>8}")
ctx2 = {}
for bname in ["V69/r4f"] + L.POOL_KD2 + L.POOL_GATED + L.POOL_KD1:
    if bname not in G.BUILDS:
        continue
    Bx = G.BUILDS[bname]
    mm, ee, engsec, evs = [], [], 0.0, []
    for s in Bx["segs"]:
        p = Bx["cache"] / f"{Bx['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, Bx["cache"], Bx["pfx"])
        fs = G.fs_of(d)
        t = np.asarray(d["t"], float)
        env = C.band_envelope(np.asarray(d["tq"], float), fs, 18.0, 22.0)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        engsec += float(lat.sum()) / fs
        for a, b in C.runs_of(~lat, t, NFFT):
            mm.append(env[a:b])
        ee.append((t, env, lat))
    if not mm or engsec < 10:
        continue
    thr = float(np.percentile(np.concatenate(mm), 99))
    ne = neeng = 0
    envs = []
    for t, env, lat in ee:
        hot = env > thr
        idx = np.flatnonzero(hot)
        if not len(idx):
            continue
        st, prev = idx[0], idx[0]
        runs = []
        for i in idx[1:]:
            if (t[i] - t[prev]) > 0.50:
                runs.append((st, prev))
                st = i
            prev = i
        runs.append((st, prev))
        for a, b in runs:
            if t[b] - t[a] < 0.30:
                continue
            ne += 1
            envs.append(float(env[a:b + 1].max()))
            if np.mean(lat[a:b + 1]) > 0.5:
                neeng += 1
    ctx2[bname] = dict(thr=thr, eps=ne, eps_eng=neeng, engsec=engsec,
                       rate=neeng / engsec if engsec else np.nan,
                       envmed=float(np.median(envs)) if envs else np.nan,
                       envmax=float(np.max(envs)) if envs else np.nan)
    c = ctx2[bname]
    print(f"  {bname:<10} {thr:>7.0f} {ne:>5} {neeng:>8} {engsec:>10.1f} {c['rate']:>10.4f} "
          f"{c['envmed']:>11.0f} {c['envmax']:>8.0f}")
OUT["episode_context"] = ctx2

(HERE / "_scratch/out/_r4f_sat_coh.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r4f_sat_coh.json'}")
