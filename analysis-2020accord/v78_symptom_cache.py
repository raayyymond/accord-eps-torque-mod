#!/usr/bin/env python3
"""Re-shape route `5e` (V75) into the per-segment cache layout the grind harness expects.

🛑 READ-ONLY on `_cache_r5e/` -- a sibling agent owns the FAULT forensics there. This writes a
SEPARATE cache, `_cache_r5e_sym/`, for the SYMPTOM question only.

What it does, and nothing else:
  1. loads `_cache_r5e/r5e.npz`, the route-GLOBAL extract (39,961 frames, 401.2 s, 7 segments);
  2. TRUNCATES at the fault. `sstat` (0x18F byte4 bits 7:4) is 0 for 28,318 frames and then 7 for
     every remaining frame, one single transition at t = 284.805 s, and `cc_lat` is 0 from that
     instant on. Post-fault frames are a DIFFERENT PLANT (assist is gone), so they are dropped;
  3. splits by `seg` and writes `r5es{seg}.npz` with the `_cache_r5d` field names, so
     `_grind2_lib.wrecs` / `d6_events.runs` / `r5d_ratchet.inventory` run on it UNCHANGED.

Probe remap (V75's thermometer -> V74's field names):
    b7 -> `damp_nz`   (gp-0x6bd0 != 0)          -- the SAME bit V74 carried, the cross-build anchor
    b6/b5/b4 kept as `thermo_128/288/448`       -- V75-only magnitude rungs
    b3 -> `g6ac2`                               -- back-drive gate; NOT V74's `state`
`state` / `mode` / `rpm` are written as NaN, exactly as `_r5d_lib` does for channels a build's probe
does not carry, so a downstream reader fails loudly instead of silently mislabelling.

Usage:  python v78_symptom_cache.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = ROOT / "_cache_r5e" / "r5e.npz"
DST = ROOT / "_cache_r5e_sym"


def main():
    d = np.load(SRC)
    n = len(d["t"])
    t, seg, ss, lat = d["t"], d["seg"], d["sstat"], d["cc_lat"]

    fault = np.flatnonzero(ss > 0.5)
    if not len(fault):
        raise SystemExit("no sstat fault found -- check the wire model")
    i_f = int(fault[0])
    t_f = float(t[i_f])
    # the transition must be SINGLE and TERMINAL, or "pre-fault" is not a well-defined slice
    assert np.all(ss[i_f:] > 0.5), "sstat returns to 0 after the fault -- not a terminal transition"
    assert np.all(ss[:i_f] < 0.5), "sstat is not clean before the fault"
    assert not np.any(lat[i_f:] > 0.5), "latActive after the fault -- unexpected"

    keep = np.arange(n) < i_f
    print(f"route 5e: {n} frames / {t[-1] - t[0]:.1f} s, 7 segments")
    print(f"FAULT (sstat 0 -> 7) at t = {t_f:.3f} s, frame {i_f}; single terminal transition.")
    print(f"KEEPING {int(keep.sum())} frames / {t_f:.1f} s pre-fault; dropping "
          f"{int((~keep).sum())} frames / {t[-1] - t_f:.1f} s post-fault.")
    print(f"  pre-fault engaged: {np.sum(lat[keep] > 0.5) * 0.01:.1f} s")

    DST.mkdir(exist_ok=True)
    ren = {"b7": "damp_nz", "b6": "thermo_128", "b5": "thermo_288", "b4": "thermo_448",
           "b3": "g6ac2"}
    census = {"fault_t": t_f, "fault_idx": i_f, "segments": {}}
    for s in range(7):
        m = keep & (seg == s)
        if m.sum() < 256:
            print(f"  seg{s}: {int(m.sum())} pre-fault frames -- SKIPPED (< 256)")
            continue
        out = {}
        for k in d.files:
            a = d[k]
            if a.ndim == 1 and len(a) == n:
                out[ren.get(k, k)] = a[m]
            elif a.ndim == 2 and a.shape[0] == n:
                out[k] = a[m]
        nn = int(m.sum())
        for k in ("state", "s_67fa", "mode", "m_63fd", "rpm", "g6806"):
            out[k] = np.full(nn, np.nan)
        out["probe_build"] = np.array(["V75"])
        out["probe_rwd"] = d["probe_rwd"]
        np.savez_compressed(DST / f"r5es{s}.npz", **out)
        tt = out["t"]
        vv = np.abs(out["cs_v"])
        ll = out["cc_lat"] > 0.5
        census["segments"][s] = dict(n=nn, t0=float(tt[0]), t1=float(tt[-1]),
                                     sec=float(tt[-1] - tt[0]), v_mean=float(np.mean(vv)),
                                     v_max=float(np.max(vv)), lat_frac=float(np.mean(ll)),
                                     eng_sec=float(np.sum(ll) * 0.01))
        print(f"  seg{s}: n={nn:6d}  {tt[0]:7.1f}-{tt[-1]:7.1f} s  v {np.mean(vv):5.2f} "
              f"(max {np.max(vv):5.2f})  engaged {np.mean(ll) * 100:5.1f}% "
              f"({np.sum(ll) * 0.01:5.1f} s)")
    with open(DST / "census.json", "w", encoding="utf-8") as fh:
        json.dump(census, fh, indent=1)
    print(f"\nwrote {DST}")


if __name__ == "__main__":
    main()
