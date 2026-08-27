#!/usr/bin/env python3
r"""Exploration pass over `_scratch/cache/r7e` / `_scratch/cache/r7f`: verify the route-time map, confirm the
signal identities and sign conventions, decode the V96 cave map, and locate the low-speed
elicitation blocks the operator describes (parking, start and end of each route).

Nothing here is decision-bearing on its own -- it exists so the plotting pass is not guessing.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
CACHE = {"7e": ROOT / "analysis-2020accord" / "_scratch/cache/r7e" / "r7e.npz",
         "7f": ROOT / "analysis-2020accord" / "_scratch/cache/r7f" / "r7f.npz"}


def load(r):
    return np.load(CACHE[r], allow_pickle=True)


def route_time_map(z, r):
    """Is the cache `t` a faithful proxy for comma-connect route time?"""
    sb = np.asarray(z["seg_bounds"], float)
    print(f"\n--- route {r}: segment bounds (seg, t_first, t_last) vs 60*seg ---")
    for s, a, b in sb:
        print(f"  seg {int(s):>2}  t {a:8.2f} .. {b:8.2f}   60*seg = {60*int(s):>4}   "
              f"offset {a - 60*int(s):+7.2f} s")
    return sb


def identities(z, r):
    print(f"\n--- route {r}: signal identity / sign checks ---")
    ang, csang = z["ang"], z["cs_ang"]
    tq, cstq = z["tq"], z["cs_tq"]
    e4, sc = z["e4tq"], z["sc_tq"]
    for nm, a, b in (("ang(0x14A) vs cs_ang", ang, csang),
                     ("tq(0x18F) vs cs_tq", tq, cstq),
                     ("e4tq(0x0E4 rx) vs sc_tq(sendcan)", e4, sc)):
        m = np.isfinite(a) & np.isfinite(b)
        c = float(np.corrcoef(a[m], b[m])[0, 1])
        s = float(np.polyfit(b[m], a[m], 1)[0])
        print(f"  {nm:<36} r={c:+.4f}  slope(a on b)={s:+.4f}  "
              f"a[{a[m].min():+8.1f},{a[m].max():+8.1f}] b[{b[m].min():+8.1f},{b[m].max():+8.1f}]")


def cave(z, r):
    print(f"\n--- route {r}: V96 cave map ---")
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    b7_76 = (b7 >> 6) & 0x3
    print(f"  frames {n:,}")
    print(f"  byte7[7:6] hist: " +
          "  ".join(f"{k}:{int(v):,}" for k, v in zip(*np.unique(b7_76, return_counts=True))))
    print(f"  POS-1 byte7 b6 == 1 duty : {np.mean((b7 >> 6) & 1):.6f}   "
          f"(V96 identity; V94 cannot write byte 7 at all)")
    print(f"  MAP-3 byte7[7:6] in {{1,3}} : {np.mean(np.isin(b7_76, (1, 3))):.6f}")
    b3 = (b4 >> 3) & 1
    print(f"  byte4 b3 (gp-0x674e < 28) duty : {b3.mean():.6f}  "
          f"constant={bool(b3.min() == b3.max())}   [RULE-7 authority-curve mode rung]")
    mhi = ((b4 >> 4) & 1) | (((b4 >> 5) & 1) << 1)
    mlo = (b7 >> 7) & 1
    M = 2 * mhi + mlo
    print(f"  Mhi hist {dict(zip(*[x.tolist() for x in np.unique(mhi, return_counts=True)]))}"
          f"   Mlo duty {mlo.mean():.6f}   M hist "
          f"{dict(zip(*[x.tolist() for x in np.unique(M, return_counts=True)]))}")
    print(f"    => |gp-0x374c>>4| bound: M==0 on {np.mean(M == 0)*100:.3f}% of frames "
          f"=> |v| < 2048 there")
    s6b70 = (b4 >> 7) & 1
    s374c = (b4 >> 6) & 1
    print(f"  byte4 b7 (gp-0x6b70 < 0) duty : {s6b70.mean():.4f}")
    print(f"  byte4 b6 (gp-0x374c>>4 < 0) duty : {s374c.mean():.4f}")
    mt = np.asarray(z["ab_mt"], int)
    print(f"  427 wire |gp-0x6b70|*5>>6 : n={len(mt):,} p50={np.percentile(mt,50):.0f} "
          f"p95={np.percentile(mt,95):.0f} max={mt.max()}  => |gp-0x6b70| p50 "
          f"{np.percentile(mt,50)*12.8:.0f} max {mt.max()*12.8:.0f} counts (clamp 8192)")


def lowspeed_blocks(z, r, vmax=3.0, minsec=5.0):
    """Contiguous stretches below `vmax` m/s -- the parking blocks."""
    t = np.asarray(z["t"], float)
    v = np.abs(np.asarray(z["cs_v"], float))
    m = v < vmax
    d = np.diff(m.astype(int))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0] + 1)
    if m[0]:
        starts = [0] + starts
    if m[-1]:
        ends = ends + [len(m) - 1]
    lat = np.asarray(z["cc_lat"], float) > 0.5
    ang = np.asarray(z["ang"], float)
    tq = np.asarray(z["tq"], float)
    out = []
    print(f"\n--- route {r}: low-speed blocks (|vEgo| < {vmax} m/s, >= {minsec} s) ---")
    print(f"  {'t0':>8} {'t1':>8} {'dur':>7} {'eng%':>6} {'|ang|max':>9} {'ang span':>9} "
          f"{'|tq|p99':>8}")
    for a, b in zip(starts, ends):
        if t[b] - t[a] < minsec:
            continue
        sl = slice(a, b)
        rec = dict(t0=float(t[a]), t1=float(t[b]), dur=float(t[b] - t[a]),
                   eng=float(lat[sl].mean()), ang_absmax=float(np.abs(ang[sl]).max()),
                   ang_span=float(ang[sl].max() - ang[sl].min()),
                   tq_p99=float(np.percentile(np.abs(tq[sl]), 99)))
        out.append(rec)
        print(f"  {rec['t0']:8.1f} {rec['t1']:8.1f} {rec['dur']:7.1f} {100*rec['eng']:5.1f}% "
              f"{rec['ang_absmax']:9.1f} {rec['ang_span']:9.1f} {rec['tq_p99']:8.0f}")
    return out


if __name__ == "__main__":
    summary = {}
    for r in ("7e", "7f"):
        z = load(r)
        print("=" * 96)
        print(f"ROUTE {r}   n={len(z['t']):,}  {z['t'][-1]:.1f} s  "
              f"probe_build={str(z['probe_build'][0])}")
        route_time_map(z, r)
        identities(z, r)
        cave(z, r)
        summary[r] = lowspeed_blocks(z, r)
    (ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_lowspeed.json").write_text(
        json.dumps(summary, indent=1))
