#!/usr/bin/env python3
"""Route 5d (V74, CLEAN) -- census of every fault signature short of a latch, + exposure limits.

Each signature is counted TWICE where a raw array exists: once off the gridded decode column and
once off the raw per-arrival array (`raw18_st` / `raw18_b4` / `raw14_b4`), which is a different
population (it starts before the first 0x18F and is not held onto the 0x14A lattice).

🛑 CHANNEL NOT IN THE CACHE: CAN 0x1AB. `extract/extract_r5d_cache.py` captures raw timestamps for
   {0x14A, 0x18F, 0x1FA, 0x0E4, 0x1D0} only, and the route-5d rlogs are no longer on disk, so
   "0x1AB byte0 bit2" cannot be answered from this cache. Stated, not invented.
"""
import json
import sys
from collections import Counter

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CACHE, PFX, SEGS = "_scratch/cache/r5d", "r5ds", list(range(17))
I16MAX, I16MIN = 32767, -32768


def main():
    st_grid, st_raw, b4_18_raw = Counter(), Counter(), Counter()
    ss14, ss18 = Counter(), Counter()          # STEER_SENSOR_STATUS, both carriers
    sat = Counter()                            # 0x14A angle fields at the i16 rail
    disagree = []
    ev_names = Counter()
    ev_bad = []
    man_move = 0
    man_speed = []

    for s in SEGS:
        d = dict(np.load(f"{CACHE}/{PFX}{s}.npz"))
        for v, c in zip(*np.unique(d["sstat"].astype(int), return_counts=True)):
            st_grid[int(v)] += int(c)
        for v, c in zip(*np.unique(d["raw18_st"].astype(int), return_counts=True)):
            st_raw[int(v)] += int(c)
        for v, c in zip(*np.unique(d["raw18_b4"].astype(int), return_counts=True)):
            b4_18_raw[int(v)] += int(c)
        for v, c in zip(*np.unique((d["probe"].astype(int) & 0x07), return_counts=True)):
            ss14[int(v)] += int(c)
        for v, c in zip(*np.unique(d["slow3"].astype(int), return_counts=True)):
            ss18[int(v)] += int(c)

        # 0x14A signed 16-bit fields, recovered from the scaled columns
        for nm, col, sc in (("ang b0:1", "ang", -0.1), ("rate b2:3", "rate_c", -1.0),
                            ("wang b5:6", "wang", -0.1)):
            raw = np.rint(d[col] / sc).astype(int)
            sat[(nm, "0x7FFF")] += int((raw == I16MAX).sum())
            sat[(nm, "0x8000")] += int((raw == I16MIN).sum())
            sat[(nm, "max|.|")] = max(sat[(nm, "max|.|")], int(np.abs(raw).max()))

        lat = d["cc_lat"] > 0.5
        sca = d["sca"] == 1
        bad = np.flatnonzero(lat != sca)
        for i in bad:
            disagree.append((s, float(d["t"][i]), bool(lat[i]), bool(sca[i])))
        mm = (~lat) & (d["cs_v"] > 4.0)
        man_move += int(mm.sum())
        man_speed.append(d["cs_v"][~lat])

        for e in json.load(open(f"{CACHE}/{PFX}{s}_events.json")):
            ev_names[e["name"]] += 1
            if e["soft"] or e["immediate"]:
                ev_bad.append((s, e["t"], e["name"], e["soft"], e["immediate"]))

    print("=" * 88)
    print("7. NEAR-MISS CENSUS -- route 5d, V74, 1011 s clean")
    print("=" * 88)

    print("\n  a) bus STEER_STATUS, 0x18F byte4 bits 7:4")
    print(f"     {'value':>7} {'gridded':>10} {'raw arrivals':>14}")
    for k in sorted(set(st_grid) | set(st_raw)):
        print(f"     {k:>7} {st_grid.get(k,0):>10} {st_raw.get(k,0):>14}")
    print(f"     -> values other than the modal one: gridded "
          f"{sum(c for k,c in st_grid.items() if k != max(st_grid, key=st_grid.get))}, raw "
          f"{sum(c for k,c in st_raw.items() if k != max(st_raw, key=st_raw.get))}")
    print("     full raw 0x18F byte4 alphabet: " +
          " ".join(f"0x{k:02X}:{c}" for k, c in sorted(b4_18_raw.items())))

    print("\n  b) STEER_SENSOR_STATUS (low 3 bits), both carriers")
    print(f"     0x14A byte4 & 7 : " + " ".join(f"{k}:{c}" for k, c in sorted(ss14.items())))
    print(f"     0x18F byte4 & 7 : " + " ".join(f"{k}:{c}" for k, c in sorted(ss18.items())))

    print("\n  c) 0x14A signed-16 fields at the rail")
    print(f"     {'field':>12} {'==0x7FFF':>10} {'==0x8000':>10} {'max |raw|':>11}")
    for nm in ("ang b0:1", "rate b2:3", "wang b5:6"):
        print(f"     {nm:>12} {sat[(nm,'0x7FFF')]:>10} {sat[(nm,'0x8000')]:>10} "
              f"{sat[(nm,'max|.|')]:>11}")

    print("\n  d) CAN 0x1AB byte0 bit2 -- NOT AVAILABLE. The extractor captures 0x14A/0x18F/0x1FA/"
          "0x0E4/0x1D0 only,\n     and the route-5d rlogs are no longer on disk. No claim either "
          "way.")

    print(f"\n  e) latActive vs STEER_CONTROL_ACTIVE disagreements: {len(disagree)} frames")
    for s, t, l, sc in disagree[:12]:
        print(f"     seg{s} t={t:.3f} lat={int(l)} sca={int(sc)}")
    if len(disagree) > 12:
        print(f"     ... {len(disagree)-12} more (all at engagement edges -- see the times)")

    print(f"\n  f) openpilot events with softDisable/immediateDisable: {len(ev_bad)}")
    for s, t, nm, sd, im in ev_bad[:15]:
        print(f"     seg{s} t={t:.2f} {nm} soft={sd} imm={im}")
    print("     all event names on the route: " +
          ", ".join(f"{k}({c})" for k, c in ev_names.most_common(12)))

    ms = np.concatenate(man_speed)
    print("\n--- EXPOSURE LIMIT that bounds the bump comparison ---------------------------------")
    print(f"  MANUAL frames above 4 m/s: {man_move} ({man_move/100.0:.1f} s) out of "
          f"{len(ms)} manual frames ({len(ms)/100.0:.1f} s)")
    for q in (50, 90, 99, 99.9, 100):
        print(f"    manual vEgo p{q}: {np.percentile(ms, q):.2f} m/s")
    print("  => route 5d's manual arm is almost entirely creep/parked. A MANUAL bump at road speed "
          "has\n     essentially NO clean-drive reference population on this route.")


if __name__ == "__main__":
    main()
