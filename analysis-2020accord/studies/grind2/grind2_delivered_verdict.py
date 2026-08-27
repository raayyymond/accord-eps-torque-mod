#!/usr/bin/env python3
"""(A) THE `sar` ITSELF  vs  (B) THE DELIVERED MULTIPLIERS -- and what V76's risk actually is.

🛑 EVENTS, NOT WINDOWS. Windows overlap 50% and a single 2 s burst produces 2-3 of them, so a
window-count Poisson test inflates every count by ~3x and every p-value by ~3 orders of magnitude.
`docs/STATE.md`'s "0 in 2,656 s vs 31, p = 6e-5" is a WINDOW count. Here a burst EVENT is a maximal
run of burst windows in one segment separated by <= 5.12 s (two window steps); a build's rate is
events per exposure-second, and every test below is on events. The window numbers are printed
alongside so the two can be compared, never mixed.

🛑 THE PROVOKING REGIME IS PART OF THE EXPOSURE. 18 of 21 creep burst windows sit at |ang| >= 100
deg, so seconds of plain creep are not interchangeable with seconds of engaged creep CORNERING.
Every cell below is reported with its own reference rate measured in the SAME cell.

Usage:  python studies/grind2/grind2_delivered_verdict.py
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
from scipy.stats import binomtest, poisson

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r47_orchestrator_checks as R47  # noqa: E402
import _grind2_delivered_lib as D  # noqa: E402

BURST, BAND, WIN_S = 500.0, "40-49", 2.56
CREEP = (0.3, 4.0)
GAP_S = 5.12                       # two window steps -- the event-merge gap
OUT = {}

ROUTES = [("V61", ["_scratch/cache/r31"]), ("V58", ["_scratch/cache/r2b"]), ("V59", ["_scratch/cache/r2c"]),
          ("V64", ["_scratch/cache/r35"]), ("V62", ["_scratch/cache/r37"]), ("V65", ["_scratch/cache/r3a", "_scratch/cache/r3b"]),
          ("V67", ["_scratch/cache/r47"]), ("V68", ["_scratch/cache/v68"]), ("V69", ["_scratch/cache/r4f"]),
          ("V70", ["_scratch/cache/r50"]), ("V71B", ["_scratch/cache/r54"]), ("V71C", ["_scratch/cache/r58"]),
          ("V72", ["_scratch/cache/r59"]), ("V73", ["_scratch/cache/r5a"]), ("V74", ["_scratch/cache/r5d"])]
OP_KMH, OP_RK = 0, 3000


def hdr(s):
    print("\n" + "=" * 120 + f"\n{s}\n" + "=" * 120)


# --------------------------------------------------------- harvest, with a per-window TIME key ---
# `_windows` returns ep=(path, block); the window index inside the file is block*4*... -- not
# recoverable. So re-harvest with the file + start index kept, using the SAME estimator.
import glob  # noqa: E402
from scipy.signal import butter, detrend, hilbert, sosfiltfilt  # noqa: E402


def harvest(cache, tag):
    rows = []
    for p in sorted(glob.glob(str(D.FW.parent.parent / "accord-eps-torque-mod" / cache / "*.npz"))):
        if "_imu" in p:
            continue
        d = dict(np.load(p))
        if "cs_v" not in d or "tq" not in d:
            continue
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        if not 95 < fs < 105:
            continue
        sos = butter(4, [40 / (fs / 2), min(49, fs / 2 * 0.98) / (fs / 2)], btype="band",
                     output="sos")
        env = np.abs(hilbert(sosfiltfilt(sos, detrend(d["tq"]))))
        n, hop = int(WIN_S * fs), int(WIN_S * fs) // 2
        lat = d["cc_lat"] > 0.5
        for i in range(0, len(t) - n, hop):
            sl = slice(i, i + n)
            rows.append(dict(tag=tag, seg=Path(p).stem, t0=float(t[i]),
                             v=float(np.median(d["cs_v"][sl])), lat=float(lat[sl].mean()),
                             ang=float(np.abs(d["ang"][sl]).max()),
                             ratemax=float(np.abs(d["rate_c"][sl]).max()),
                             p99=float(np.percentile(env[sl], 99))))
    return rows


print("harvesting ...", flush=True)
ROWS = {}
for name, caches in ROUTES:
    r = []
    for c in caches:
        r += harvest(c, name)
    ROWS[name] = r
    print(f"   {name:5s} {len(r):5d} windows", flush=True)

B = D.load_all()
st = B["stock"]
DEL = {n: D.delivered(B[n], st, OP_KMH, OP_RK, engaged=True) for n, _ in ROUTES}
DEL["V76"] = D.delivered(B["V76"], st, OP_KMH, OP_RK, engaged=True)


def sel(rows, arm, vlo, vhi, angmin=None):
    out = []
    for r in rows:
        if arm == "eng" and r["lat"] <= 0.5:
            continue
        if arm == "man" and r["lat"] >= 0.5:
            continue
        if not (vlo <= r["v"] < vhi):
            continue
        if angmin is not None and r["ang"] < angmin:
            continue
        out.append(r)
    return out


def events(rows):
    """Maximal runs of burst windows in one segment separated by <= GAP_S."""
    b = sorted([r for r in rows if r["p99"] > BURST], key=lambda r: (r["seg"], r["t0"]))
    ev, cur = [], None
    for r in b:
        if cur and r["seg"] == cur[-1]["seg"] and r["t0"] - cur[-1]["t0"] <= GAP_S:
            cur.append(r)
        else:
            if cur:
                ev.append(cur)
            cur = [r]
    if cur:
        ev.append(cur)
    return ev


def cellstat(rows):
    ev = events(rows)
    return dict(n=len(rows), secs=len(rows) * WIN_S / 2.0,
                win=sum(1 for r in rows if r["p99"] > BURST), ev=len(ev),
                mx=max((r["p99"] for r in rows), default=float("nan")))


CELLS = {
    "creep 0.3-4 m/s": dict(vlo=CREEP[0], vhi=CREEP[1]),
    "★ creep CORNER |ang|>=100 (18/21 creep bursts live here)": dict(vlo=CREEP[0], vhi=CREEP[1],
                                                                     angmin=100),
    "non-highway 0.3-14 m/s": dict(vlo=0.3, vhi=14.0),
}

# ============================================================ §1 =================================
hdr("§1  BURST EVENTS (merged) vs BURST WINDOWS, per build, per cell.\n"
    "    ⚠ For a gated build (V67/V68/V71C) the MANUAL arm runs byte-stock firmware, so its seconds "
    "do NOT test the lever;\n    for an ungated build (V62/V65/V71B/V72/V73/V74) the manual arm IS "
    "dosed and DOES count.")
GATED = {"V67", "V68", "V71C", "V76"}
for cname, kw in CELLS.items():
    print(f"\n   --- {cname} ---")
    print(f"   {'build':6s} {'delivered r24/r26':>18s} {'dosed arms':>12s} | {'DOSED secs':>11s} "
          f"{'events':>7s} {'windows':>8s} {'max':>9s}")
    for name, _ in ROUTES:
        arms = ["eng"] if name in GATED else ["eng", "man"]
        rows = sum([sel(ROWS[name], a, **kw) for a in arms], [])
        s = cellstat(rows)
        e = DEL[name]
        print(f"   {name:6s} {e[0]:8.3f}/{e[1]:8.3f} {'+'.join(arms):>12s} | {s['secs']:11.1f} "
              f"{s['ev']:7d} {s['win']:8d} {s['mx']:9.1f}")

# ============================================================ §2 =================================
hdr("§2  THE FOUR-CELL DESIGN. Builds pooled by DELIVERED (r24, r26); only DOSED arms counted.")
GROUPS = {
    "STOCK LANE          r24 1.0  r26 1.0": ["V58", "V59", "V61", "V64", "V69", "V70"],
    "r26 CUT only        r24 1.0  r26 0.25": ["V72", "V73", "V74"],
    "r26 UP only         r24 1.0  r26 2.0": ["V71B"],
    "BOTH UP (sar)       r24 2.0  r26 2.0": ["V62", "V65"],
    "BOTH UP (gate)      r24 3.4  r26 1.5": ["V71C"],
    "★ r24 UP, r26 CUT   r24 3.4  r26 0.25  ← V76's CELL": ["V67", "V68"],
}
for cname, kw in CELLS.items():
    print(f"\n   --- {cname} ---")
    print(f"   {'group':52s} {'DOSED secs':>11s} {'events':>7s} {'windows':>8s} {'ev/1000s':>9s} "
          f"{'max':>9s}")
    G = {}
    for g, blds in GROUPS.items():
        rows = []
        for name in blds:
            arms = ["eng"] if name in GATED else ["eng", "man"]
            rows += sum([sel(ROWS[name], a, **kw) for a in arms], [])
        s = cellstat(rows)
        G[g] = s
        print(f"   {g:52s} {s['secs']:11.1f} {s['ev']:7d} {s['win']:8d} "
              f"{1000 * s['ev'] / s['secs'] if s['secs'] else float('nan'):9.2f} {s['mx']:9.1f}")
    OUT[cname] = {g: {k: v for k, v in s.items()} for g, s in G.items()}

    # exact binomial: are the zero cells distinguishable from the positive pool?
    pos = [g for g in G if G[g]["ev"] > 0]
    if not pos:
        continue
    ref_ev = sum(G[g]["ev"] for g in pos)
    ref_s = sum(G[g]["secs"] for g in pos)
    print(f"\n   reference (all bursting groups pooled) = {ref_ev} events in {ref_s:.1f} s "
          f"= {1000 * ref_ev / ref_s:.2f} / 1000 s")
    print(f"   {'zero group':52s} {'secs':>8s} {'lambda':>7s} {'P(0) events':>12s} "
          f"{'P(0) windows':>13s}  exact-binom p")
    ref_w = sum(G[g]["win"] for g in pos)
    for g in G:
        if G[g]["ev"] > 0 or G[g]["secs"] == 0:
            continue
        lam = G[g]["secs"] * ref_ev / ref_s
        lamw = G[g]["secs"] * ref_w / ref_s
        bt = binomtest(ref_ev, ref_ev, ref_s / (ref_s + G[g]["secs"]), alternative="greater")
        print(f"   {g:52s} {G[g]['secs']:8.1f} {lam:7.2f} {poisson.pmf(0, lam):12.4f} "
              f"{poisson.pmf(0, lamw):13.4f}  {bt.pvalue:.4f}")

# ============================================================ §3 =================================
hdr("§3  (A) THE `sar` vs (B) THE DELIVERED MULTIPLIERS -- the discriminator.")
print("   Byte-read from each image (`0x3AB76` r26 / `0x3AC20` r24; the low byte is the imm5):")
for n in ["V62", "V65", "V71A", "V71C", "V67", "V68", "V76"]:
    b = B[n]
    print(f"      {n:5s} sar r24 = {b.sar24}, sar r26 = {b.sar26}  "
          f"{'<-- V62 s DOUBLING' if b.sar24 == 9 else '(both STOCK)'}")
v71c = sum([sel(ROWS["V71C"], "eng", **CELLS['creep 0.3-4 m/s'])], [])
ev = events(v71c)
print(f"\n   ⇒ V71C carries NEITHER `sar` byte and produced {len(ev)} creep burst EVENT(s) "
      f"({sum(len(e) for e in ev)} windows).")
for e in ev:
    print(f"      event: seg {e[0]['seg']}  t {e[0]['t0']:.1f}-{e[-1]['t0'] + WIN_S:.1f} s  "
          f"({len(e)} win, {e[-1]['t0'] + WIN_S - e[0]['t0']:.1f} s)  max p99 "
          f"{max(r['p99'] for r in e):.1f}  v {min(r['v'] for r in e):.2f}-"
          f"{max(r['v'] for r in e):.2f} m/s  |ang| up to {max(r['ang'] for r in e):.0f} deg")
mx_other = max(r["p99"] for n in ["V58", "V59", "V61", "V64", "V69", "V70", "V71B", "V72", "V73",
                                  "V74", "V67", "V68"]
               for r in sel(ROWS[n], "eng", **CELLS['creep 0.3-4 m/s']))
print(f"   the largest creep-engaged p99 on ANY non-bursting build is {mx_other:.1f} counts "
      f"⇒ the V71C event is {max(r['p99'] for e in ev for r in e) / mx_other:.1f}x that.")

# ============================================================ §4 =================================
hdr("§4  ★ V76's RISK AND ITS POWER. V76's rate lane is BYTE-IDENTICAL to V67/V68 "
    "(gate 0xFB, 0xC6446 = 5244, 0xC6444 = 512, both `sar` stock).")
for n in ("V67", "V68", "V76"):
    b = B[n]
    print(f"   {n:5s} gate 0x{b.gate_byte:02X}  C6446 = {b.arm24_gate}  C6444 = {b.arm26_gate}  "
          f"sar {b.sar24}/{b.sar26}  ⇒ delivered engaged {DEL[n][0]:.3f} / {DEL[n][1]:.3f}")
print()
for cname, kw in CELLS.items():
    rows = sum([sel(ROWS[n], "eng", **kw) for n in ("V67", "V68")], [])
    s = cellstat(rows)
    ref = []
    for n in ("V62", "V65"):
        ref += sum([sel(ROWS[n], a, **kw) for a in ("eng", "man")], [])
    rs = cellstat(ref)
    r71c = cellstat(sel(ROWS["V71C"], "eng", **kw))
    for refname, rr in (("V62+V65", rs), ("V71C (single-variable: only 0xC6444 differs)", r71c)):
        if rr["secs"] == 0 or rr["ev"] == 0:
            continue
        rate = rr["ev"] / rr["secs"]
        lam = s["secs"] * rate
        # MDE: the smallest event rate this exposure would have detected with 80% power
        mde = -np.log(0.20) / s["secs"] if s["secs"] else float("nan")
        print(f"   {cname[:46]:46s} ref {refname[:34]:34s}")
        print(f"      V67+V68 exposure {s['secs']:7.1f} s, {s['ev']} events | ref rate "
              f"{1000 * rate:6.2f}/1000 s ⇒ expected {lam:5.2f} ⇒ **P(0) = {poisson.pmf(0, lam):.3f}"
              f"**, power {1 - poisson.pmf(0, lam):.0%}")
        print(f"      MDE at 80% power on this exposure = {1000 * mde:6.2f} events/1000 s "
              f"= {mde / rate:5.2f}x the reference rate\n")

(HERE / "_scratch/out/_grind2_delivered_verdict.json").write_text(json.dumps(OUT, indent=1), encoding="utf-8")
print(f"wrote {HERE / '_scratch/out/_grind2_delivered_verdict.json'}")
