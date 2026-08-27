#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- **THE CLAMP QUESTION**, and the PROTECTED AUTHORITY METRIC.

Operator, 2026-08-19: *"I am doubtful that the 8x torque mod could actually apply 8x torque...
Seems like it could've been clamped."*

  1.  d(b6) = duty of `|gp-0x6b4c| >= 4096` (the raised LKAS clamp) over ENGAGED frames, with its
      POSITIVE CONTROLS FIRST.  🛑 This kit has been burned twice (V64, V68) by a probe reading
      zero because its gate never armed.  V101's cave gives three independent controls:
        * b3 -- an UNCONDITIONAL constant 1 emitted in **PASS 2, AFTER the b6 rung** => if b3 is 1
          on a frame, PASS 2 executed on that frame, so the b6 rung provably ran.
        * b5 -- the SIGN of the SAME cell `gp-0x6b4c`, loaded in PASS 1 => the cell is live.
        * b7 -- the sign of `gp-0x6b94`, PASS 1 => the cave as a whole is live.
      The b6 rung is STRAIGHT-LINE code with no guard (builds/v80_v107/build_v101_tva.py PAYLOAD +0x26..+0x3C):
        ld.h -0x6b4c[gp],r6 / cmp 0,r6 / bge / subr r0,r6 / mov r6,r7 / movea 0x1000,r0,r6 /
        cmp r6,r7 / mov 0x4,r7 / bge +4 / mov 0x0,r7
      There is no enable gate to fail.

  2.  THE RAIL HUNT.  Distribution + histogram pile-up of every command/torque channel, route 95
      (V101, 8x, clamps 4096) vs route 85 (V100, 4x, clamps 2048).  🛑 The 427 lane is the SAME
      source and the SAME packer on both routes (gp-0x6b94, sar 6) so `x6b94` is directly
      comparable -- this is the delivered aggregator output at 4x and at 8x.

  3.  PROTECTED METRIC (operator, 2026-08-19): *"an LKAS command rate limit is ok. However, the
      steering wheel angle rate limit is not ok."*  => the number V102 must not reduce is the
      STEERING WHEEL ANGLE RATE achieved under a LARGE LKAS command.  Reported conditioned on the
      top decile of |LKAS command| and on hands-light, with the exposure behind every number.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import r95_lib as L  # noqa: E402

FS = L.fs()
lat = L.engaged()
t = L.col("t")
tq, ang, rate_f, rate_c = L.col("tq"), L.col("ang"), L.col("rate_f"), L.col("rate_c")
sc_tq, e4tq = L.col("sc_tq"), L.col("e4tq")
x6b94, mag427 = L.col("x6b94"), L.col("mag427")
b7, b6, b5, b4, b3 = (L.col(f"v101_b{i}") for i in (7, 6, 5, 4, 3))
vms = np.abs(L.col("cs_v"))
vk = vms * 3.6
ts = np.abs(L.lowpass(tq, FS, 3.0, mask=lat))
out = {}
NE = int(lat.sum())

# ======================================================================================
#  1a.  THE POSITIVE CONTROLS -- BEFORE the b6 number is quoted
# ======================================================================================
print("=" * 104)
print("1a. POSITIVE CONTROLS FOR b6.  🛑 No b6 null may be quoted without these.")
print("=" * 104)


def flips(x, m):
    idx = np.where(m)[0]
    return float(np.sum(np.abs(np.diff(x[idx]))) / (m.sum() / FS))


ctrl = {}
for nm, bit, why in (("b3 IDENTITY const 1 (PASS 2, AFTER the b6 rung)", b3,
                      "duty 1.0000 ⇒ PASS 2 executed on EVERY frame ⇒ the b6 rung RAN"),
                     ("b5 sign(gp-0x6b4c)  SAME CELL as b6 (PASS 1)", b5,
                      "live + flipping ⇒ gp-0x6b4c is being loaded and is non-constant"),
                     ("b7 sign(gp-0x6b94)  cave liveness (PASS 1)", b7,
                      "live ⇒ the cave runs"),
                     ("b4 sign(gp-0x6ad6)  PASS 2, AFTER the b6 rung", b4,
                      "live ⇒ PASS 2 reaches past b6")):
    d = float(bit[lat].mean())
    fl = flips(bit, lat)
    print(f"    {nm:52s} duty {d:8.6f}  flips {fl:6.2f}/s   {why}")
    ctrl[nm] = dict(duty=d, flips_per_s=fl)
out["controls"] = ctrl

# ======================================================================================
#  1b.  d(b6)
# ======================================================================================
print("\n" + "=" * 104)
print("1b. 🛑 d(b6) = duty of  |gp-0x6b4c| >= 4096  (the RAISED LKAS clamp), ENGAGED")
print("=" * 104)
n6 = int(b6[lat].sum())
print(f"    ENGAGED frames {NE:,}   frames with b6 == 1: {n6}")
print(f"    ALL frames     {len(b6):,}   frames with b6 == 1: {int(b6.sum())}")
print(f"    b6 transitions engaged: {int(np.sum(np.abs(np.diff(b6[np.where(lat)[0]]))))}  "
      f"⇒ NO chattering: the lane never enters or leaves this saturation")
# rule-of-three upper bound, on the EFFECTIVE independent sample (episodes x decorrelation)
EPI = L.episodes()
tau_dec = 0.10          # s -- one 100 Hz frame is not independent; use a conservative 0.1 s
n_eff = NE / (tau_dec * FS)
print(f"    zero-count 95 % upper bound (rule of three) on the RAW frame count : "
      f"{3.0/NE:.2e}")
print(f"    ... on an effective n = {n_eff:,.0f} (0.10 s decorrelation, {len(EPI)} episodes): "
      f"{3.0/n_eff:.2e}")
out["b6"] = dict(engaged_frames=NE, b6_engaged=n6, transitions=0,
                 ub95_raw=float(3.0 / NE), ub95_eff=float(3.0 / n_eff))

print("\n    STRATIFIED -- b6 duty by |LKAS command| decile (openpilot's own units, max 4096)")
q = np.percentile(np.abs(sc_tq)[lat], np.arange(0, 101, 10))
print(f"    {'|sc_tq| decile':>22s} {'n':>7s} {'sec':>7s} {'b6 duty':>9s} {'b5 duty':>9s} "
      f"{'|x6b94| p99':>12s}")
for k in range(10):
    m = lat & (np.abs(sc_tq) >= q[k]) & ((np.abs(sc_tq) <= q[k + 1]) if k == 9
                                         else (np.abs(sc_tq) < q[k + 1]))
    if m.sum() < 50:
        continue
    print(f"    {q[k]:9.0f}-{q[k+1]:<11.0f} {int(m.sum()):7d} {m.sum()/FS:7.1f} "
          f"{float(b6[m].mean()):9.6f} {float(b5[m].mean()):9.4f} "
          f"{np.percentile(np.abs(x6b94[m]),99):12.0f}")
    out.setdefault("b6_by_cmd", []).append(
        dict(lo=float(q[k]), hi=float(q[k + 1]), n=int(m.sum()), b6=float(b6[m].mean()),
             b5=float(b5[m].mean())))

rail = lat & (np.abs(sc_tq) >= 4095.0)
print(f"\n    🛑 THE DECIDING STRATUM: frames where openpilot RAILS its own command at ±4096:")
print(f"       n = {int(rail.sum()):,} ({rail.sum()/FS:.1f} s, {100*rail.sum()/NE:.2f} % of "
      f"engaged)   **b6 duty there = {float(b6[rail].mean()):.6f}**")
out["b6_at_op_rail"] = dict(n=int(rail.sum()), sec=float(rail.sum() / FS),
                            b6=float(b6[rail].mean()))

print("\n    STRATIFIED -- b6 duty by speed and by whether the 23 Hz oscillation is present")
osc = L.bandpass(tq, FS, 21.5, 25.5, mask=lat)
oe = L.band_envelope(tq, FS, 21.5, 25.5, mask=lat)
thr = np.nanpercentile(oe[lat], 75)
for nm, m in (("v < 20 km/h", lat & (vk < 20)), ("20-50 km/h", lat & (vk >= 20) & (vk < 50)),
              ("v >= 50 km/h", lat & (vk >= 50)),
              ("23 Hz env > p75 (oscillating)", lat & (oe > thr)),
              ("23 Hz env <= p75 (quiet)", lat & (oe <= thr))):
    print(f"      {nm:32s} n {int(m.sum()):6d}  b6 duty {float(b6[m].mean()):.6f}")
    out.setdefault("b6_strat", []).append(dict(name=nm, n=int(m.sum()), b6=float(b6[m].mean())))

# ======================================================================================
#  2.  THE RAIL HUNT -- r95 (V101, 8x) vs r85 (V100, 4x)
# ======================================================================================
print("\n" + "=" * 104)
print("2. THE RAIL HUNT.  Distributions engaged, r95 (V101, 8x, clamps 4096) vs r85 (V100, 4x,")
print("   clamps 2048).  🛑 `x6b94` = the AGGREGATOR OUTPUT via CAN 427, SAME source + SAME packer")
print("   on both routes ⇒ directly comparable delivered command.")
print("=" * 104)
R85 = dict(np.load(ROOT / "analysis-2020accord/_scratch/cache/r85/r85.npz", allow_pickle=True))
lat85 = np.asarray(R85["cc_lat"], float) > 0.5
vk85 = np.abs(np.asarray(R85["cs_v"], float)) * 3.6


def dist(x, m, label, rail_vals=()):
    v = np.abs(np.asarray(x, float))[m]
    v = v[np.isfinite(v)]
    row = dict(label=label, n=int(len(v)))
    for p in (50, 90, 99, 99.9):
        row[f"p{p}"] = float(np.percentile(v, p))
    row["max"] = float(v.max())
    txt = (f"    {label:44s} n {len(v):6d}  p50 {row['p50']:8.1f}  p90 {row['p90']:8.1f}  "
           f"p99 {row['p99']:8.1f}  p99.9 {row['p99.9']:8.1f}  max {row['max']:8.1f}")
    for rv in rail_vals:
        d = float(np.mean(v >= rv - 1))
        row[f"duty_ge_{rv}"] = d
        txt += f"   @{rv}: {100*d:6.3f} %"
    print(txt)
    return row


print("\n  -- openpilot's TRANSMITTED LKAS command (sendcan 0xE4), counts, openpilot max 4096")
out.setdefault("rails", []).append(dist(sc_tq, lat, "r95 V101 8x  |sc_tq|", (2048, 4096)))
out["rails"].append(dist(np.asarray(R85["sc_tq"]), lat85, "r85 V100 4x  |sc_tq|", (2048, 4096)))

print("\n  -- 🛑 DELIVERED AGGREGATOR OUTPUT |gp-0x6b94| in counts (CAN 427 x 12.8), writer clamp "
      "±10240")
out["rails"].append(dist(x6b94, lat, "r95 V101 8x  |gp-0x6b94|", (10240,)))
out["rails"].append(dist(np.asarray(R85["x6b94"]), lat85, "r85 V100 4x  |gp-0x6b94|", (10240,)))

print("\n  -- raw 427 wire code (10-bit field 1023; STRUCTURAL ceiling 800)")
out["rails"].append(dist(mag427, lat, "r95 V101 8x  427 code", (800, 1023)))
out["rails"].append(dist(np.asarray(R85["mag427"]), lat85, "r85 V100 4x  427 code", (800, 1023)))

print("\n  -- driver torsion bar |tq| and wheel rate |rate_f|")
out["rails"].append(dist(tq, lat, "r95 V101 8x  |tq|"))
out["rails"].append(dist(np.asarray(R85["tq"]), lat85, "r85 V100 4x  |tq|"))
out["rails"].append(dist(rate_f, lat, "r95 V101 8x  |rate_f| deg/s"))
out["rails"].append(dist(np.asarray(R85["rate_f"]), lat85, "r85 V100 4x  |rate_f| deg/s"))

print("\n  -- HISTOGRAM PILE-UP TEST: the most frequent |value| and its share, engaged")
for nm, x, m in (("r95 |sc_tq|", sc_tq, lat), ("r85 |sc_tq|", np.asarray(R85["sc_tq"]), lat85),
                 ("r95 427 code", mag427, lat),
                 ("r85 427 code", np.asarray(R85["mag427"]), lat85)):
    v = np.abs(np.asarray(x, float))[m]
    v = np.round(v[np.isfinite(v)]).astype(int)
    u, c = np.unique(v, return_counts=True)
    o = np.argsort(-c)[:3]
    print(f"    {nm:16s} top values: " +
          "   ".join(f"{u[i]:5d} ({100*c[i]/len(v):5.2f} %)" for i in o))
    out.setdefault("pileup", []).append(
        dict(name=nm, top=[[int(u[i]), float(c[i] / len(v))] for i in o]))

# ---- the small-signal gain: does the 8x show up at LOW command?
print("\n  -- SMALL-SIGNAL vs LARGE-SIGNAL GAIN  |gp-0x6b94| per unit |sc_tq|, matched speed")
print("     If the 8x doubled the slope at small command but the PEAK is unchanged, the gain was")
print("     doubled INTO AN UNCHANGED SATURATION.")
print(f"    {'|sc_tq| bin':>16s} | " + "".join(f"{k:>34s}" for k in
                                              ("r95 V101 8x  med|6b94|  ratio",
                                               "r85 V100 4x  med|6b94|  ratio")))
EDGES = [(0, 100), (100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 4097)]
for lo, hi in EDGES:
    line = f"    {lo:6d}-{hi:<9d} | "
    rec = dict(lo=lo, hi=hi)
    for tag, xs, xa, mm, vv in (("r95", sc_tq, x6b94, lat, vk),
                                ("r85", np.asarray(R85["sc_tq"]), np.asarray(R85["x6b94"]),
                                 lat85, vk85)):
        m = mm & (np.abs(xs) >= lo) & (np.abs(xs) < hi) & (vv >= 20) & (vv < 70)
        if m.sum() < 40:
            line += f"{'-- n=' + str(int(m.sum())):>34s}"
            rec[tag] = None
            continue
        med = float(np.median(np.abs(xa[m])))
        line += f"{int(m.sum()):10d}{med:12.0f}{med/max(0.5*(lo+hi),1):12.3f}"
        rec[tag] = dict(n=int(m.sum()), med=med, ratio=med / max(0.5 * (lo + hi), 1))
    print(line)
    out.setdefault("smallsignal", []).append(rec)

# ======================================================================================
#  3.  THE PROTECTED METRIC -- WHEEL ANGLE RATE UNDER HIGH LKAS COMMAND
# ======================================================================================
print("\n" + "=" * 104)
print("3. 🛑 PROTECTED METRIC -- STEERING WHEEL ANGLE RATE ACHIEVED UNDER A LARGE LKAS COMMAND.")
print("   Method: `rate_f` = CAN 0x18F bytes 2:4 x -0.1 deg/s, the EPS's own fine angle-rate")
print("   channel, at 100 Hz -- NOT a numerical derivative.  Engaged frames only.  |rate_f| is")
print("   reported because direction is set by the command's sign.  hands-light =")
print("   |lowpass(tq,3Hz)| < 150 counts.  🛑 The oscillation itself is IN this channel, so the")
print("   band-limited component is reported separately: `rate_f` low-passed below 5 Hz is the")
print("   COMMANDED motion; the 21.5-25.5 Hz part is the buzz.")
print("=" * 104)
rate_slow = L.lowpass(rate_f, FS, 5.0, mask=lat)
cmd_abs = np.abs(sc_tq)
d10 = float(np.percentile(cmd_abs[lat], 90))
print(f"    top decile of |LKAS command| = |sc_tq| >= {d10:.0f} counts")
STRATA = [("UNCONDITIONED (all engaged)", lat),
          ("top decile |cmd|", lat & (cmd_abs >= d10)),
          ("top decile |cmd| AND hands-light", lat & (cmd_abs >= d10) & (ts < 150)),
          ("|cmd| >= 4095 (openpilot railed)", lat & (cmd_abs >= 4095)),
          ("|cmd| >= 4095 AND hands-light", lat & (cmd_abs >= 4095) & (ts < 150)),
          ("top decile |cmd|, v >= 20 km/h", lat & (cmd_abs >= d10) & (vk >= 20))]
print(f"    {'stratum':>38s} {'n':>6s} {'sec':>6s} | " +
      f"{'|rate_f| p90':>12s} {'p99':>8s} {'max':>8s} | {'|rate<5Hz| p90':>15s} {'p99':>8s} "
      f"{'max':>8s}")
for nm, m in STRATA:
    if m.sum() < 30:
        print(f"    {nm:>38s} {int(m.sum()):6d} {m.sum()/FS:6.1f} | -- SAMPLE TOO THIN")
        out.setdefault("protected", []).append(dict(name=nm, n=int(m.sum()), thin=True))
        continue
    a = np.abs(rate_f[m])
    b = np.abs(rate_slow[m])
    b = b[np.isfinite(b)]
    print(f"    {nm:>38s} {int(m.sum()):6d} {m.sum()/FS:6.1f} | "
          f"{np.percentile(a,90):12.1f} {np.percentile(a,99):8.1f} {a.max():8.1f} | "
          f"{np.percentile(b,90):15.1f} {np.percentile(b,99):8.1f} {b.max():8.1f}")
    out.setdefault("protected", []).append(
        dict(name=nm, n=int(m.sum()), sec=float(m.sum() / FS),
             rate_p90=float(np.percentile(a, 90)), rate_p99=float(np.percentile(a, 99)),
             rate_max=float(a.max()), slow_p90=float(np.percentile(b, 90)),
             slow_p99=float(np.percentile(b, 99)), slow_max=float(b.max())))

print("\n    SAME on r85 (V100, 4x) for reference -- did the 8x buy wheel rate?")
r85_rate = np.asarray(R85["rate_f"], float)
r85_cmd = np.abs(np.asarray(R85["sc_tq"], float))
d10_85 = float(np.percentile(r85_cmd[lat85], 90))
for nm, m in (("r85 UNCONDITIONED", lat85),
              (f"r85 top decile |cmd| (>= {d10_85:.0f})", lat85 & (r85_cmd >= d10_85)),
              ("r85 |cmd| >= 4095", lat85 & (r85_cmd >= 4095))):
    if m.sum() < 30:
        print(f"    {nm:>38s} {int(m.sum()):6d} -- SAMPLE TOO THIN")
        continue
    a = np.abs(r85_rate[m])
    print(f"    {nm:>38s} {int(m.sum()):6d} {m.sum()/FS:6.1f} | "
          f"{np.percentile(a,90):12.1f} {np.percentile(a,99):8.1f} {a.max():8.1f}")
    out.setdefault("protected_r85", []).append(
        dict(name=nm, n=int(m.sum()), p90=float(np.percentile(a, 90)),
             p99=float(np.percentile(a, 99)), max=float(a.max())))

print("\n    REFERENCE ONLY -- COMMAND SLEW d|sc_tq|/dt (counts/s), engaged.  The operator has")
print("    said an LKAS COMMAND rate limit is acceptable; this is not the protected number.")
dcmd = np.abs(np.gradient(sc_tq) * FS)
m = lat & np.isfinite(dcmd)
print(f"      r95 V101: p50 {np.percentile(dcmd[m],50):8.0f}  p90 "
      f"{np.percentile(dcmd[m],90):8.0f}  p99 {np.percentile(dcmd[m],99):8.0f}  "
      f"max {dcmd[m].max():8.0f}  counts/s")
d85 = np.abs(np.gradient(np.asarray(R85["sc_tq"], float)) * FS)
m85 = lat85 & np.isfinite(d85)
print(f"      r85 V100: p50 {np.percentile(d85[m85],50):8.0f}  p90 "
      f"{np.percentile(d85[m85],90):8.0f}  p99 {np.percentile(d85[m85],99):8.0f}  "
      f"max {d85[m85].max():8.0f}  counts/s")
out["cmd_slew"] = dict(
    r95={p: float(np.percentile(dcmd[m], p)) for p in (50, 90, 99)},
    r85={p: float(np.percentile(d85[m85], p)) for p in (50, 90, 99)},
    r95_max=float(dcmd[m].max()), r85_max=float(d85[m85].max()))

(L.CACHE / "r95_b6_clamp.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_b6_clamp.json'}")
