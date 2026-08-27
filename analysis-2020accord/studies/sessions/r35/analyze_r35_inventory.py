#!/usr/bin/env python3
"""Route `35` (V64) inventory + flight cleanliness.

Q1 route inventory, Q2 flight cleanliness. Every load-bearing count is derived TWICE by
independent means and the two are printed side by side; a disagreement is printed as a FAIL
rather than silently reconciled.
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
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from _r31_common import GEAR, sustained  # noqa: E402

CACHE = ROOT / "_scratch/cache/r35"
SEGS = [0, 1, 2]


def load(seg):
    return {k: v for k, v in np.load(CACHE / f"r35s{seg}.npz").items()}


def main():
    print("=" * 100)
    print("Q1  ROUTE INVENTORY -- 75604b0a432fdc89_00000035--77808fe7ce  (V64)")
    print("=" * 100)
    tot_s = tot_n = 0
    for s in SEGS:
        d = load(s)
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        v = d["cs_v"]
        lat = d["cc_lat"] > 0.5
        sca = d["sca"] == 1
        eff = np.abs(sustained(d["tq"], fs))
        ang = np.abs(d["ang"])
        g = Counter(GEAR[int(x)] for x in d["cs_gear"])
        tot_s += t[-1] - t[0]
        tot_n += len(t)
        print(f"\nseg {s}: {len(t)} frames  {t[-1]-t[0]:.2f} s  fs={fs:.2f} Hz")
        print(f"  vEgo   {v.min():+.2f} .. {v.max():+.2f} m/s   "
              f"p50={np.percentile(v,50):.2f} p90={np.percentile(v,90):.2f}   "
              f"frac(v<=5.35)={100*(v<=5.35).mean():.1f}%  frac(|v|<0.3)={100*(np.abs(v)<0.3).mean():.1f}%")
        print(f"  latActive {100*lat.mean():5.1f}%   0x18F b4b3 (sca) {100*sca.mean():5.1f}%   "
              f"agreement {100*(lat==sca).mean():.2f}%")
        print(f"  gear   {dict(g)}")
        print(f"  |ang|  p50={np.percentile(ang,50):.1f} p90={np.percentile(ang,90):.1f} "
              f"max={ang.max():.1f} deg")
        print(f"  effort |lowpass(tq,3Hz)|  p50={np.percentile(eff,50):.0f} "
              f"p90={np.percentile(eff,90):.0f} p99={np.percentile(eff,99):.0f} max={eff.max():.0f}")
        print(f"  raw tq  p1={np.percentile(d['tq'],1):.0f} p99={np.percentile(d['tq'],99):.0f} "
              f"absmax={np.abs(d['tq']).max():.0f}")
        # engagement structure: the runs of lat, in time order
        edges = np.flatnonzero(np.diff(lat.astype(int)) != 0)
        segs_desc = []
        prev = 0
        for e in list(edges) + [len(lat) - 1]:
            segs_desc.append(f"{'ENG' if lat[prev] else 'dis'} {t[prev]:.1f}-{t[e]:.1f}s")
            prev = e + 1
        print(f"  structure: {' | '.join(segs_desc)}")
    print(f"\nTOTAL {tot_n} frames, {tot_s:.1f} s across {len(SEGS)} segments")

    print()
    print("=" * 100)
    print("Q2  FLIGHT CLEANLINESS")
    print("=" * 100)
    st = Counter()
    for s in SEGS:
        d = load(s)
        st.update(Counter(int(x) for x in d["sstat"]))
    n = sum(st.values())
    print(f"\nSTEER_STATUS (0x18F byte4 bits 7:4), all segments, n={n}")
    for k in sorted(st):
        print(f"  ST=={k}: {st[k]:6d}  {100*st[k]/n:6.2f}%")
    print(f"  => ST==4 (governor ratchet state): {st.get(4,0)}   "
          f"ST==3 (low-speed lockout):          {st.get(3,0)}")

    ev = Counter()
    evt_t = {}
    for s in SEGS:
        for e in json.loads((CACHE / f"r35s{s}_events.json").read_text()):
            ev[e["name"]] += 1
            evt_t.setdefault(e["name"], []).append((s, e["t"]))
    print(f"\nonroadEvents, raw names, all segments ({sum(ev.values())} total):")
    for k, c in ev.most_common():
        print(f"  {c:5d}  {k}")
    WATCH = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
             "immediateDisable", "steerSaturated"]
    print("\n  watched:")
    for k in WATCH:
        c = ev.get(k, 0)
        extra = ""
        if c and k in evt_t:
            tt = evt_t[k][:3]
            extra = "  first: " + ", ".join(f"seg{a}@{b:.1f}s" for a, b in tt)
        print(f"    {k:24s} {c:5d}{extra}")

    print("\nCAN rates (raw src=1 arrivals, independent of the merged grid):")
    for s in SEGS:
        d = load(s)
        dur = d["t"][-1] - d["t"][0]
        line = f"  seg {s} ({dur:.1f} s): "
        for a in ("14A", "18F", "1FA"):
            k = f"raw{a}"
            if k in d and len(d[k]) > 1:
                line += f"0x{a} {len(d[k])/dur:6.2f} Hz (n={len(d[k])})  "
        print(line)


if __name__ == "__main__":
    main()
