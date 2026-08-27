#!/usr/bin/env python3
"""T1 (build identity + health) and T6 (the V75 magprobe damper census) for route 67 / V81.

🛑 V81's cave is BYTE-IDENTICAL to V75's, so the authority for the bit layout is
`probe/decode_v75_probe.py` and this file calls that module's OWN `identify()` / `report()` rather than
re-deriving the thresholds.  The only difference from running the decoder directly is that the
frames come from `_scratch/cache/r67x/` (already extracted) instead of a fresh rlog parse -- the probe byte
is carried through verbatim as `probe`, and the bit decode in `decode/extract_r67_v81.py` imports the same
BIT_* constants.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v75_probe as V75P  # noqa: E402
from extract_r67_v81 import CACHE, PFX, SEGS  # noqa: E402

OUT = {}


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100, flush=True)


def runs(mask):
    m = np.asarray(mask, bool).astype(np.int8)
    e = np.diff(np.concatenate(([0], m, [0])))
    return list(zip(np.flatnonzero(e > 0), np.flatnonzero(e < 0)))


def main():
    d = dict(np.load(CACHE / "r67.npz"))
    t = d["t"]
    n = len(t)
    fs = 1.0 / np.median(np.diff(t))
    b4 = d["probe"].astype(np.uint8)
    lat = d["cc_lat"] > 0.5
    v = d["cs_v"]

    hdr("T1  BUILD IDENTITY + HEALTH -- route 67, claimed V81 (= V75 image, cave byte-identical)")
    print(f"  frames            {n}")
    print(f"  duration          {t[-1] - t[0]:.2f} s  ({t[-1] - t[0]:.1f} s)")
    print(f"  sample rate       {fs:.3f} Hz  (median dt {np.median(np.diff(t)) * 1e3:.3f} ms)")
    print(f"  segments          {sorted(set(int(x) for x in d['seg']))}")
    print(f"  speed             {v.min():.2f} .. {v.max():.2f} m/s "
          f"({3.6 * v.min():.1f} .. {3.6 * v.max():.1f} km/h)")
    er = runs(lat)
    er_long = [(a, b) for a, b in er if (t[b - 1] - t[a]) >= 1.0]
    print(f"  latActive         {100 * lat.mean():.2f}%  ({lat.sum() / fs:.1f} s of "
          f"{t[-1] - t[0]:.1f} s)")
    print(f"  engagement runs   {len(er)} total, {len(er_long)} at least 1 s; "
          f"median {np.median([t[b - 1] - t[a] for a, b in er_long]):.1f} s, "
          f"max {max(t[b - 1] - t[a] for a, b in er_long):.1f} s")
    st, sc = np.unique(d["sstat"].astype(int), return_counts=True)
    print(f"  STEER_STATUS hist {dict(zip(st.tolist(), sc.tolist()))}   "
          f"(0 = normal; 3 = low-speed lockout; a terminal 0->7 is the V75 fault)")
    dtc = d["dtc_active"]
    dfin = dtc[np.isfinite(dtc)]
    dtr = int(np.sum(np.abs(np.diff(dfin)) > 0.5)) if len(dfin) > 1 else 0
    print(f"  0x1AB DTC-active  duty {100 * np.nanmean(dtc):.4f}%  transitions {dtr}  "
          f"(max {np.nanmax(dtc):.0f})")
    sent = d["sentinels"]
    print(f"  0x7FFF sentinels  0x14A angle {int(sent[0])}   0x18F torque {int(sent[1])}")
    print(f"  probe payloads    {dict(Counter(hex(int(x)) for x in b4).most_common(16))}")
    print(f"  bits 7:3 alphabet {sorted(hex(int(x)) for x in np.unique(d['field']))}")
    ev = json.loads((CACHE / "r67_events.json").read_text())
    en = Counter(e["name"] for e in ev)
    bad = Counter(e["name"] for e in ev if e["soft"] or e["immediate"])
    print(f"  onroadEvents      {len(ev)} rows, top: {en.most_common(8)}")
    print(f"  soft/immediate    {dict(bad)}")
    steerfault = [k for k in en if "steer" in k.lower() or "Steer" in k]
    print(f"  🛑 steer-fault-like event names: {steerfault if steerfault else 'NONE'}")
    OUT["t1"] = dict(frames=n, sec=float(t[-1] - t[0]), fs=float(fs),
                     lat_frac=float(lat.mean()), lat_sec=float(lat.sum() / fs),
                     runs=len(er), runs_1s=len(er_long),
                     sstat={int(a): int(b) for a, b in zip(st, sc)},
                     dtc_duty=float(np.nanmean(dtc)), dtc_transitions=dtr,
                     sentinels=[int(sent[0]), int(sent[1])],
                     v_min=float(v.min()), v_max=float(v.max()),
                     payloads={hex(int(k)): int(c) for k, c in
                               zip(*np.unique(b4, return_counts=True))},
                     events_soft=dict(bad))

    hdr("T1b  THE DECODER'S OWN IDENTITY GUARD (decode_v75_probe.identify)")
    ok = V75P.identify(b4, lat, v, d["rate_c"])
    OUT["t1"]["identify_pass"] = bool(ok)

    hdr("T6  THE DAMPER MAGNITUDE THERMOMETER |gp-0x6BD0| + the gp-0x6AC2 back-drive gate")
    V75P.report(b4, lat, v)

    lv = V75P.level(b4)
    print("\n  --- ENGAGED-ONLY level census (V75/route 5e read L4 = 0.000% of 28,317 frames) ---")
    for nm, m in (("ALL", np.ones(n, bool)), ("ENGAGED", lat), ("manual", ~lat)):
        k = int(m.sum())
        if not k:
            continue
        cnt = [int(((lv == i) & m).sum()) for i in range(5)]
        print(f"    {nm:9s} n={k:6d} | " + " ".join(
            f"L{i} {100.0 * c / k:7.3f}%" for i, c in enumerate(cnt)))
        OUT.setdefault("t6", {})[nm] = dict(n=k, levels=cnt,
                                            pct=[100.0 * c / k for c in cnt],
                                            backdrive=float(((d["g6ac2"] > 0.5) & m).sum() / k))

    print("\n  --- ENGAGED, stratified by speed ---")
    STR = [("creep <10 kph", 0.0, 10 / 3.6), ("10-40 kph", 10 / 3.6, 40 / 3.6),
           ("40-80 kph", 40 / 3.6, 80 / 3.6), (">80 kph", 80 / 3.6, 1e9)]
    print(f"    {'stratum':14s} {'n':>6s} | " + " ".join(f"{'L%d' % i:>9s}" for i in range(5))
          + " | bit3 backdrive")
    for nm, lo, hi in STR:
        m = lat & (np.abs(v) >= lo) & (np.abs(v) < hi)
        k = int(m.sum())
        if k < 100:
            print(f"    {nm:14s} {k:6d} | -- too few --")
            continue
        row = " ".join(f"{100.0 * ((lv == i) & m).sum() / k:8.3f}%" for i in range(5))
        bd = 100.0 * ((d["g6ac2"] > 0.5) & m).sum() / k
        print(f"    {nm:14s} {k:6d} | {row} | {bd:8.3f}%")
        OUT.setdefault("t6_speed", {})[nm] = dict(
            n=k, pct=[100.0 * ((lv == i) & m).sum() / k for i in range(5)], backdrive=bd)

    print("\n  --- the invariant, re-checked on the DATA ---")
    viol = int(d["illegal"].sum())
    print(f"    illegal payloads (outside the 10-value thermometer alphabet): {viol} of {n}")
    print(f"    thermometer level p50={np.median(lv):.0f}  p90={np.percentile(lv, 90):.0f}  "
          f"p99={np.percentile(lv, 99):.0f}  max={lv.max()}")
    OUT["t6_illegal"] = viol

    (CACHE / "r67_t1t6.json").write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {CACHE / 'r67_t1t6.json'}")


if __name__ == "__main__":
    main()
