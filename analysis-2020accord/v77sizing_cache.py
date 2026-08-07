#!/usr/bin/env python3
"""Re-shape route `65` (V76) into the per-segment cache layout `_grind2_lib` / `_r31_common` expect.

Reads `_cache_r65/r65.npz` (the route-GLOBAL extract written by `v77sizing_extract.py`, 63,477
frames / 636.3 s, 11 segments) and splits by `seg`, writing `r65s{N}.npz` with `t` RESET to 0 at
each segment start -- the convention every `_r*_lib.py` in this kit assumes (`_r31_common.fs_of`,
`runs_of`, `load()`).

🛑 V76's probe carries only THREE live bits (COMBO B): `friction_hit` (bit7, the root-cause lane
margin), `mode_bit1` (bit4, one bit of the 5-bit mode index), `state_eq5` (bit3, a POSITIVE CONTROL
equality test, not the state value). None of these is `damp_nz` / `state` / `mode` / `g6806` in the
sense `_r5d_lib._add_probe` or `_r5a_lib._add_mode` expect -- writing a number into those fields
would silently mislabel a partial bit as a full covariate. They are THEREFORE NOT WRITTEN. Anyone
reading this cache for `d["state"]` or `d["mode"]` gets a KeyError, not a wrong answer.

Usage:  python v77sizing_cache.py
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

SRC = ROOT / "_cache_r65" / "r65.npz"
DST = ROOT / "_cache_r65"          # same dir as the global extract, per-segment files alongside it
PFX = "r65s"

# Fields `_grind2_lib.wrecs` / `_r31_common.load` / `_r47_lib.augment` read by name, straight
# passthrough (no rename needed -- `v77sizing_extract.py` already used the kit's field names).
PASS_1D = ["t", "ang", "rate_c", "wang", "tq", "rate_f", "sca", "sstat", "slow3", "e4tq", "e4req",
           "cs_v", "cs_eng", "cs_ang", "cs_tq", "cs_press", "cs_gear", "cs_std", "cs_lblink",
           "cs_rblink", "cs_lchg", "cc_lat", "cc_en", "cc_req", "co_req", "co_tqcan", "sc_tq",
           "sc_req", "ws_fl", "ws_fr", "ws_rl", "ws_rr", "dtc_active", "imu_vert",
           # V76's own probe -- kept under their OWN names, not shoehorned into `damp`/`state`/`mode`.
           "friction_hit", "mode_bit1", "state_eq5", "bits65_viol", "field", "status"]


def main():
    d = np.load(SRC)
    n = len(d["t"])
    t, seg = d["t"], d["seg"]

    # sanity: the probe's structural invariant must hold route-wide, not just in the extractor's
    # own summary -- re-check it here so a stale/edited cache cannot silently pass downstream.
    assert not np.any(d["bits65_viol"] > 0.5), \
        f"{int(np.sum(d['bits65_viol']))} frames set bit6/5 -- this cache is not a clean V76 COMBO B"
    dtc = d["dtc_active"]
    print(f"route 65: {n} frames / {t[-1] - t[0]:.1f} s, {len(np.unique(seg))} segments")
    print(f"  dtc_active: max={np.nanmax(dtc):.0f}  (0 = the drive never hard-faulted)")
    print(f"  friction_hit duty {100 * d['friction_hit'].mean():.4f}%  "
          f"(never exceeded the 448-count margin anywhere on this drive)"
          if d["friction_hit"].mean() == 0 else
          f"  friction_hit duty {100 * d['friction_hit'].mean():.4f}%")

    DST.mkdir(exist_ok=True)
    census = {"segments": {}}
    for s in np.unique(seg.astype(int)):
        m = seg == s
        if m.sum() < 256:
            print(f"  seg{s}: {int(m.sum())} frames -- SKIPPED (< 256)")
            continue
        out = {}
        for k in PASS_1D:
            if k in d.files:
                out[k] = d[k][m]
        out["t"] = out["t"] - out["t"][0]        # ★ RESET per-segment, the convention every lib uses
        out["probe_build"] = np.array(["V76"])
        out["probe_rwd"] = d["probe_rwd"]
        np.savez_compressed(DST / f"{PFX}{s}.npz", **out)
        tt, vv = out["t"], np.abs(out["cs_v"])
        ll = out["cc_lat"] > 0.5
        census["segments"][int(s)] = dict(n=int(m.sum()), sec=float(tt[-1] - tt[0]),
                                          v_mean=float(np.mean(vv)), v_max=float(np.max(vv)),
                                          lat_frac=float(np.mean(ll)),
                                          eng_sec=float(np.sum(ll) * 0.01))
        print(f"  seg{s}: n={int(m.sum()):6d}  {tt[-1] - tt[0]:6.1f} s  v_mean {np.mean(vv):5.2f} "
              f"(max {np.max(vv):5.2f})  engaged {np.mean(ll) * 100:5.1f}% "
              f"({np.sum(ll) * 0.01:5.1f} s)")
    with open(DST / "r65_census_seg.json", "w", encoding="utf-8") as fh:
        json.dump(census, fh, indent=1)
    print(f"\nwrote {DST} / {PFX}{{0..{int(seg.max())}}}.npz")


if __name__ == "__main__":
    main()
