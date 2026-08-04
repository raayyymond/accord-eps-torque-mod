#!/usr/bin/env python3
"""DELIVERABLE 1 -- is 18-22 Hz (GRIND #1) elevated on route `4f` (V69)?

The operator reports "grind #1 is BACK" after flashing V69. Grind #1 is the ~21 Hz torsional column
mode that V62 FIXED (8x down at creep, 42x at |rate| 16-32 deg/s; V67 replicated at 0.40
[0.27, 0.58] vs the Kd=1 pool, null [0.88, 1.13]). It lives on the torsion-bar STEER torque channel
(`tq`, CAN 0x18F bytes 0:1), not on the chassis IMU.

WHAT THIS SCRIPT DOES, IN THE ORDER THE KIT'S RULES REQUIRE

  ss0  EXPOSURE CENSUS FIRST. Per-segment and per-speed-bin seconds, engaged and manual. An
       averaged spectrum compares two routes only if their SPEED DISTRIBUTIONS MATCH -- a moving
       wheel order concentrates in a narrow-speed route and smears in a wide one, which manufactures
       an "only on route X" line.
  ss1  AVERAGE PERIODOGRAMS, THEN PEAK-FIND. Never a median-of-per-window-argmax: that manufactures
       a line at band centre when none exists (it once beat the alternative at dBIC 249-460 and was
       wrong). Prominence = peak / local median floor; the kit's line criterion is prom > 4.
  ss2  THE ORDER VETO, WITH THE ARITHMETIC SHOWN. Wheel order n: f = n*v/CIRC, CIRC 2.073-2.088 m,
       so order 1 = 0.483*v (m/s). Engine order k: f = k*rpm/60. Both are computed from the SAME
       windows that built the spectrum.
  ss3  THE BAND-CENTRE TEST. Sweep the search band 18-22 -> 12-30 -> 15-45 Hz. A real line does not
       move; a band-floor artefact pins to the edge or tracks the centre.
  ss4  THE PER-WINDOW PROMINENCE CENSUS -- necessary because ss3 is NOT sufficient. A line present in
       a few windows and a line present in all of them give the same averaged peak.

Writes `_r4f_line.json`.  Usage: python r4f_grind1_line.py
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
import _r4f_lib as L  # noqa: E402

L.install_fs()
OUT = {}
rng = np.random.default_rng(20260803)

BUILD = "V69/r4f"
KMH = 3.6

# ---------------------------------------------------------------- ss0 exposure census ------------
L.hdr("ss0  ROUTE 4f EXPOSURE CENSUS -- per segment and per V69 speed breakpoint")
B = G.BUILDS[BUILD]
tot = {}
seg_rows = []
for s in B["segs"]:
    d = G.wrecs.__globals__["load"](s, B["cache"], B["pfx"]) if False else None
import _r31_common as C  # noqa: E402

for s in B["segs"]:
    d = C.load(s, B["cache"], B["pfx"])
    fs = G.fs_of(d)
    n = len(d["t"])
    eng = np.asarray(d["cc_lat"], float) > 0.5
    v = np.abs(np.asarray(d["cs_v"], float))
    seg_rows.append(dict(seg=int(s), secs=n / fs, fs=float(fs),
                         eng=float(eng.mean()), vmin=float(v.min()), vmax=float(v.max()),
                         vmed=float(np.median(v)),
                         rpm=float(np.nanmedian(d["rpm"])) if "rpm" in d else np.nan))
    for i, (lo, hi) in enumerate(L.VBINS_V69):
        m = (v >= lo) & (v < hi)
        tot.setdefault(i, [0.0, 0.0])
        tot[i][0] += float((m & eng).sum()) / fs
        tot[i][1] += float((m & ~eng).sum()) / fs
print(f"  {'seg':>4} {'secs':>7} {'fs':>8} {'engaged%':>9} {'v med':>7} {'v min':>7} {'v max':>7} "
      f"{'rpm med':>8}")
for r in seg_rows:
    print(f"  {r['seg']:>4} {r['secs']:>7.1f} {r['fs']:>8.3f} {100 * r['eng']:>8.1f}% "
          f"{r['vmed']:>7.2f} {r['vmin']:>7.2f} {r['vmax']:>7.2f} {r['rpm']:>8.0f}")
print(f"\n  {'km/h bin':>10} {'V69 dose':>9} {'engaged s':>10} {'manual s':>9}   "
      f"wheel-order-1 Hz at bin edges")
for i, nm in enumerate(L.VBIN_NAMES):
    lo, hi = L.VBINS_V69[i]
    hh = min(hi, 30.0)
    print(f"  {nm:>10} {L.V69_DOSE[nm]:>8.3f}x {tot[i][0]:>10.1f} {tot[i][1]:>9.1f}   "
          f"{L.wheel_order(lo):.2f} - {L.wheel_order(hh):.2f} Hz")
OUT["exposure"] = dict(segments=seg_rows,
                       vbins={nm: dict(eng=tot[i][0], man=tot[i][1], dose=L.V69_DOSE[nm])
                              for i, nm in enumerate(L.VBIN_NAMES)})

# ---------------------------------------------------------------- ss1 averaged periodogram -------
L.hdr("ss1  AVERAGED PERIODOGRAM on the torsion-bar channel -- average FIRST, peak-find AFTER")


def peakrow(f, P, lo, hi):
    R = G.prom_spectrum(f, P)
    f0, pr = G.locate(f, P, lo, hi, R=R)
    return f0, pr


def show(tag, f, P, K, extra=""):
    if P is None or K == 0:
        print(f"  {tag:<34} K=0   (EMPTY CELL)")
        return None
    f0, pr = peakrow(f, P, 18.0, 22.0)
    f0f, prf = peakrow(f, P, 12.0, 30.0)
    print(f"  {tag:<34} K={K:>4}  18-22Hz peak {f0:6.2f} prom {pr:6.2f}   "
          f"free 12-30 {f0f:6.2f} prom {prf:6.2f}  {extra}")
    return dict(K=int(K), f0=float(f0), prom=float(pr), f0_free=float(f0f), prom_free=float(prf))


print("  ENGAGED, per segment")
per_seg = {}
for s in B["segs"]:
    f, P, K, st, meta = L.avg_periodogram(BUILD, L.eng_mask, segs=[s])
    per_seg[f"s{s}"] = show(f"seg {s} engaged", f, P, K)
print("  MANUAL, per segment")
per_seg_man = {}
for s in B["segs"]:
    f, P, K, st, meta = L.avg_periodogram(BUILD, L.man_mask, segs=[s])
    per_seg_man[f"s{s}"] = show(f"seg {s} manual", f, P, K)

print("\n  POOLED")
pooled = {}
f_e, P_e, K_e, st_e, meta_e = L.avg_periodogram(BUILD, L.eng_mask)
pooled["engaged"] = show("ALL segs engaged", f_e, P_e, K_e)
f_m, P_m, K_m, st_m, meta_m = L.avg_periodogram(BUILD, L.man_mask)
pooled["manual"] = show("ALL segs manual", f_m, P_m, K_m)

print("\n  ENGAGED, split on V69's own speed breakpoints  (dose 4.000x below 10 km/h, 1.000x >= 50)")
by_v = {}
stacks = {}
for i, nm in enumerate(L.VBIN_NAMES):
    lo, hi = L.VBINS_V69[i]
    f, P, K, st, meta = L.avg_periodogram(BUILD, L.eng_mask, vlo=lo, vhi=hi)
    by_v[nm] = show(f"{nm} km/h  ({L.V69_DOSE[nm]:.3f}x)", f, P, K)
    if K:
        stacks[nm] = (f, st, meta)
OUT["avg_periodogram"] = dict(per_seg_engaged=per_seg, per_seg_manual=per_seg_man,
                              pooled=pooled, by_speed_engaged=by_v)

# ---------------------------------------------------------------- ss2 order veto -----------------
L.hdr("ss2  THE ORDER VETO -- arithmetic shown, computed from the SAME windows as the spectra above")
print(f"  wheel circumference CIRC = {L.CIRC_LO}-{L.CIRC_HI} m (established); midpoint {L.CIRC:.4f}")
print(f"  wheel order n:  f = n*v/CIRC  ->  order 1 = {1 / L.CIRC:.4f}*v(m/s) = "
      f"{1 / L.CIRC / KMH:.4f}*v(km/h)")
print("  engine order k: f = k*rpm/60")
print(f"\n  {'cell':>12} {'K':>5} {'v med':>7} {'w1':>7} {'w2':>7} {'w3':>7} {'rpm':>7} "
      f"{'e1':>7} {'e2':>7} {'e1/2':>7}   verdict for an 18-22 Hz line")
veto = {}
for nm in L.VBIN_NAMES:
    if nm not in stacks:
        continue
    f, st, meta = stacks[nm]
    vm = float(np.median([m["v"] for m in meta]))
    rp = float(np.nanmedian([m["rpm"] for m in meta]))
    w = [L.wheel_order(vm, n) for n in (1, 2, 3)]
    e1, e2, ehalf = L.engine_order(rp, 1), L.engine_order(rp, 2), L.engine_order(rp, 0.5)
    hits = [nmn for nmn, val in (("w1", w[0]), ("w2", w[1]), ("w3", w[2]),
                                 ("e1", e1), ("e2", e2), ("e0.5", ehalf))
            if 18.0 <= val <= 22.0]
    print(f"  {nm:>12} {len(meta):>5} {vm:>7.2f} {w[0]:>7.2f} {w[1]:>7.2f} {w[2]:>7.2f} "
          f"{rp:>7.0f} {e1:>7.2f} {e2:>7.2f} {ehalf:>7.2f}   "
          + ("*** IN BAND: " + ",".join(hits) if hits else "no order in 18-22 Hz -> VETO CLEAR"))
    veto[nm] = dict(K=len(meta), v=vm, rpm=rp, w1=w[0], w2=w[1], w3=w[2],
                    e1=float(e1), e2=float(e2), e05=float(ehalf), in_band=hits)
OUT["order_veto"] = veto

# per-window order test: does the observed peak TRACK speed or rpm?
print("\n  Does the engaged 18-22 Hz peak TRACK v or rpm?  (Theil-Sen on per-window free-band f0)")
rs = L.records()[BUILD]
eng = [r for r in rs if r["eng"] == 1 and np.isfinite(r["f_18-26"])]


def theil_sen(x, y, nmax=4000, rng=rng):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 5:
        return np.nan, np.nan, np.nan, n
    ii = rng.integers(0, n, (nmax, 2))
    ii = ii[x[ii[:, 0]] != x[ii[:, 1]]]
    sl = (y[ii[:, 1]] - y[ii[:, 0]]) / (x[ii[:, 1]] - x[ii[:, 0]])
    return (float(np.median(sl)), float(np.percentile(sl, 2.5)),
            float(np.percentile(sl, 97.5)), n)


for band, key in (("18-26", "f_18-26"), ("12-30 free", "f_12-30")):
    yy = [r[key] for r in eng]
    sv = theil_sen([r["v"] for r in eng], yy)
    sr = theil_sen([r["rpm"] for r in eng], yy)
    print(f"    {band:>12}  d f0 / d v   = {sv[0]:+.4f} [{sv[1]:+.4f}, {sv[2]:+.4f}] Hz per m/s "
          f"(wheel order 1 predicts {1 / L.CIRC:+.4f}, order 2 {2 / L.CIRC:+.4f}, a MODE 0)")
    print(f"    {band:>12}  d f0 / d rpm = {sr[0]:+.5f} [{sr[1]:+.5f}, {sr[2]:+.5f}] Hz per rpm "
          f"(engine order 1 predicts +0.01667, order 2 +0.03333, a MODE 0)")
    OUT.setdefault("tracking", {})[band] = dict(dv=sv, drpm=sr)

# ---------------------------------------------------------------- ss3 band-centre test -----------
L.hdr("ss3  BAND-CENTRE TEST -- sweep the search band. A real line does not move with the band.")
print(f"  {'search band':>14} {'engaged f0':>11} {'prom':>7}   {'manual f0':>10} {'prom':>7}")
sweep = {}
for lo, hi in [(18, 22), (17, 23), (16, 24), (15, 25), (12, 30), (14, 34), (15, 45), (10, 45)]:
    fe, pe = (peakrow(f_e, P_e, lo, hi) if P_e is not None else (np.nan, np.nan))
    fm, pm = (peakrow(f_m, P_m, lo, hi) if P_m is not None else (np.nan, np.nan))
    print(f"  {f'{lo}-{hi} Hz':>14} {fe:>11.2f} {pe:>7.2f}   {fm:>10.2f} {pm:>7.2f}")
    sweep[f"{lo}-{hi}"] = dict(eng_f0=float(fe), eng_prom=float(pe),
                               man_f0=float(fm), man_prom=float(pm))
OUT["band_sweep"] = sweep
print("  ⇒ a peak whose f0 sits at the band edge, or slides to the centre of every band, is the")
print("    band-floor artefact the kit has been burned by; a stable f0 across all eight is a line.")

# ---------------------------------------------------------------- ss4 per-window census ----------
L.hdr("ss4  PER-WINDOW PROMINENCE CENSUS -- necessary because the band-centre test is not sufficient")
print("  kit line criterion: prominence > 4 on an averaged periodogram. Here: the FRACTION of")
print("  individual windows carrying prom > 4 and > 10 in 18-22 Hz, which the averaged peak hides.")
print(f"\n  {'build':<11} {'cell':>16} {'wins':>5} {'eps':>4} {'prom p50':>9} {'prom p90':>9} "
      f"{'>4':>7} {'>10':>7} {'f0 p50':>7} {'f0 sd':>6}")
census = {}
store = L.records()
CELLS = [("engaged, all v", lambda r: r["eng"] == 1),
         ("engaged creep <4", lambda r: r["eng"] == 1 and r["v"] < 4.0),
         ("engaged 4-14 m/s", lambda r: r["eng"] == 1 and 4.0 <= r["v"] < 14.0),
         ("engaged >=13.9", lambda r: r["eng"] == 1 and r["v"] >= 13.889),
         ("manual, all v", lambda r: r["eng"] == 0)]
for b in [BUILD] + L.POOL_KD2 + L.POOL_GATED + L.POOL_KD1:
    if b not in store:
        continue
    for cname, fn in CELLS:
        sel = [r for r in store[b] if fn(r)]
        pr = np.array([r["p_18-22"] for r in sel], float)
        f0 = np.array([r["f_18-22"] for r in sel], float)
        pr, f0 = pr[np.isfinite(pr)], f0[np.isfinite(f0)]
        if not len(pr):
            print(f"  {b:<11} {cname:>16} {'0':>5}  --- EMPTY CELL ---")
            census[f"{b}|{cname}"] = dict(n=0)
            continue
        ne = len({r["ep"] for r in sel})
        row = dict(n=int(len(pr)), eps=int(ne), p50=float(np.median(pr)),
                   p90=float(np.percentile(pr, 90)), f4=float((pr > 4).mean()),
                   f10=float((pr > 10).mean()), f0=float(np.median(f0)), f0sd=float(np.std(f0)))
        census[f"{b}|{cname}"] = row
        print(f"  {b:<11} {cname:>16} {row['n']:>5} {ne:>4} {row['p50']:>9.2f} {row['p90']:>9.2f} "
              f"{100 * row['f4']:>6.1f}% {100 * row['f10']:>6.1f}% {row['f0']:>7.2f} "
              f"{row['f0sd']:>6.2f}")
    print()
OUT["census"] = census

(HERE / "_r4f_line.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_r4f_line.json'}")
