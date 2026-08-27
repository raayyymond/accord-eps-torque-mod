#!/usr/bin/env python3
"""Step 0 of the highway event hunt: HOW MUCH engaged highway exposure exists, by route and dose.

Nothing here is a finding. It exists because the last three sessions each made a claim about the
highway population without first counting it, and one of them ("no Kd=1 highway sample exists")
was false -- route 2b held 227 s of it, hidden by a hardcoded segment list.

🛑 SEGMENTS: every route is swept over ALL its segments. `_r31_common.SEGS_2B` and
`_r37_ratchet_lib.ROUTES` hardcode route 2b as [0,1,2,11,12,13]; that list EXCLUDES segments 3-10,
which is exactly where 2b's highway lives. Do not inherit it.

Usage:  python studies/highway/highway_exposure_inventory.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Route -> (cache tag, prefix, segments, build, Kd at highway).  Kd values are the DELIVERED
# highway multiplier from _r47_imu_lib.DOSE_HW / _r47_lib.DOSE_HWY, not the creep dose.
ROUTES = [
    ("2b", "_scratch/cache/r2b", "r2bs", list(range(0, 14)), "V58", 1.00),
    ("2c", "_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], "V59", 1.00),
    ("31", "_scratch/cache/r31", "r31s", [0, 1, 2, 3], "V61", 0.00),
    ("35", "_scratch/cache/r35", "r35s", [0, 1, 2], "V64", 1.00),
    ("37", "_scratch/cache/r37", "r37s", list(range(0, 15)), "V62", 2.00),
    ("3a", "_scratch/cache/r3a", "r3as", list(range(0, 7)), "V65", 2.00),
    ("3b", "_scratch/cache/r3b", "r3bs", list(range(0, 14)), "V65", 2.00),
    ("47", "_scratch/cache/r47", "r47s", list(range(0, 26)), "V67", 2.44),
    ("4a", "_scratch/cache/r4a", "r4as", list(range(0, 40)), "V67", 2.44),
]

V_BANDS = [(0.0, 12.0), (12.0, 17.0), (17.0, 22.0), (22.0, 28.0), (28.0, 99.0)]


def main():
    rows, tot = [], {}
    print(f"{'rt':<4}{'build':<6}{'Kd':>5}  {'segs':>5} {'frames':>8} {'fs':>6}  "
          + "  ".join(f"{lo:g}-{hi:g}" for lo, hi in V_BANDS)
          + "     (engaged seconds per speed band)")
    print("-" * 118)
    for rt, cd, pfx, segs, build, kd in ROUTES:
        cache = ROOT / cd
        acc = np.zeros(len(V_BANDS))
        accm = np.zeros(len(V_BANDS))     # manual (disengaged) seconds
        nfr, nseg, fss, imu, snd = 0, 0, [], 0, 0
        for s in segs:
            p = cache / f"{pfx}{s}.npz"
            if not p.exists():
                continue
            d = dict(np.load(p))
            t = d["t"]
            if len(t) < 100:
                continue
            nseg += 1
            nfr += len(t)
            fs = 1.0 / float(np.median(np.diff(t)))
            fss.append(fs)
            imu += (cache / f"{pfx}{s}_imu.npz").exists()
            snd += (cache / f"{pfx}{s}_snd.npz").exists()
            v = np.abs(d["cs_v"])
            eng = d["cc_lat"] > 0.5
            for i, (lo, hi) in enumerate(V_BANDS):
                m = (v >= lo) & (v < hi)
                acc[i] += float((m & eng).sum()) / fs
                accm[i] += float((m & ~eng).sum()) / fs
        if not nseg:
            continue
        fs = float(np.median(fss))
        rows.append(dict(route=rt, build=build, kd=kd, nseg=nseg, frames=nfr, fs=fs,
                         imu_segs=imu, snd_segs=snd,
                         eng_s=[round(x, 1) for x in acc], man_s=[round(x, 1) for x in accm]))
        print(f"{rt:<4}{build:<6}{kd:>5.2f}  {nseg:>5} {nfr:>8} {fs:>6.2f}  "
              + "  ".join(f"{x:7.1f}" for x in acc) + f"   imu {imu}/{nseg} snd {snd}/{nseg}")
        tot.setdefault(kd, np.zeros(len(V_BANDS)))
        tot[kd] += acc
    print("-" * 118)
    print("MANUAL (disengaged) seconds, same bands:")
    for r in rows:
        print(f"{r['route']:<4}{r['build']:<6}{r['kd']:>5.2f}  {'':>5} {'':>8} {'':>6}  "
              + "  ".join(f"{x:7.1f}" for x in r["man_s"]))
    print("-" * 118)
    print("ENGAGED seconds pooled by highway Kd dose:")
    for kd in sorted(tot):
        print(f"  Kd={kd:.2f}x  " + "  ".join(f"{x:8.1f}" for x in tot[kd]))
    (HERE / "_scratch/out/_hwy_exposure.json").write_text(json.dumps(
        {"bands": V_BANDS, "rows": rows,
         "pooled_eng_s": {str(k): list(np.round(v, 1)) for k, v in tot.items()}}, indent=1))
    print(f"\nwrote {HERE / '_scratch/out/_hwy_exposure.json'}")


if __name__ == "__main__":
    main()
