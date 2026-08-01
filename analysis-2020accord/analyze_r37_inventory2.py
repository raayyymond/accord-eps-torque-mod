#!/usr/bin/env python3
"""V62 route-37 sanity pass: fs, wall-clock anchor, engagement, gear, health flags per segment.

Preface to analyze_r37_newgrind.py. Nothing here is a conclusion; it exists so every later number
has a stated denominator. Segment 0 is a stale 07:05 boot and is EXCLUDED everywhere downstream.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402

C.CACHE = C.ROOT / "_cache_r37"
PFX = "r37s"
SEGS = list(range(0, 15))


def main():
    print("seg   n      fs      t_span        wall_t0     v_min..v_max   lat%   sca%   "
          "gear                     sstat!=0  ST==4  ev")
    for s in SEGS:
        f = C.CACHE / f"{PFX}{s}.npz"
        if not f.exists():
            continue
        d = C.load(s, C.CACHE, PFX)
        fs = C.fs_of(d)
        w0 = float(d["wall_t0"][0])
        wstr = time.strftime("%H:%M:%S", time.localtime(w0))
        g = {C.GEAR[int(x)]: int((d["cs_gear"] == x).sum()) for x in np.unique(d["cs_gear"])}
        ev = json.loads((C.CACHE / f"{PFX}{s}_events.json").read_text())
        n4 = int((d["sstat"] == 4).sum())
        nnz = int((d["sstat"] != 0).sum())
        print(f"{s:3d} {len(d['t']):6d} {fs:7.3f}  {d['t'][0]:6.2f}..{d['t'][-1]:6.2f}  {wstr}  "
              f"{d['cs_v'].min():6.2f}..{d['cs_v'].max():6.2f}  "
              f"{100*(d['cc_lat']>0.5).mean():5.1f}  {100*(d['sca']==1).mean():5.1f}  "
              f"{str(g):24s} {nnz:8d} {n4:6d} {len(ev):4d}")

    # ---- event names of interest, with wall clock -------------------------------------------
    print("\nEVENTS (deduped runs) across segs 1-14:")
    KEEP = ("steerSaturated", "controlsMismatch", "steerTempUnavailable", "steerUnavailable",
            "belowSteerSpeed", "steerTimeLimit", "commIssue", "selfdriveLagging",
            "selfdrivedLagging", "preLaneChange", "ldw")
    for s in SEGS[1:]:
        f = C.CACHE / f"{PFX}{s}_events.json"
        if not f.exists():
            continue
        d = C.load(s, C.CACHE, PFX)
        w0 = float(d["wall_t0"][0])
        ev = json.loads(f.read_text())
        runs = {}
        for e in ev:
            nm = e["name"]
            r = runs.setdefault(nm, [e["t"], e["t"], 0])
            r[1] = e["t"]
            r[2] += 1
        for nm, (a, b, n) in sorted(runs.items()):
            flag = "  <<" if any(k.lower() in nm.lower() for k in KEEP) else ""
            print(f"  seg{s:<3d} {nm:34s} n={n:5d}  t {a:6.2f}..{b:6.2f}  "
                  f"wall {time.strftime('%H:%M:%S', time.localtime(w0+a))}"
                  f"..{time.strftime('%H:%M:%S', time.localtime(w0+b))}{flag}")


if __name__ == "__main__":
    main()
