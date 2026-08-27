#!/usr/bin/env python3
"""Extract V59 route `2c` signals to .npz caches.

Same grid and decode conventions as decode/extract_r2b_cache.py (0x14A src1 arrivals, 0x18F held-last),
but byte4 now carries the **V59 THERMOMETER**, not V58's flag set:

    bit7 = 1                          LIVENESS (0 => cave did not fire; field==0 is VOID)
    bit6 = (gp-0x6ba6 <  0)           the 0xFFFF FAULT SENTINEL
    bit5 = ((gp-0x6ba6 >>  9) == 0)   index < 512
    bit4 = ((gp-0x6ba6 >> 10) == 0)   index < 1024
    bit3 = ((gp-0x6ba6 >> 11) == 0)   index < 2048
    bits 2:0 = stock STEER_SENSOR_STATUS, preserved

Derived columns written for convenience (all on the 0x14A grid):
    lt512/lt1024/lt2048  the three thermometer bits as 0/1
    lvl                  0..3 depth level = 3 - lt512 - lt1024 - lt2048
                         (0 => index<512, 1 => 512-1k, 2 => 1k-2k, 3 => >=2048)
    mono                 1 where bit5=>bit4=>bit3 holds (decode-valid frame)

Usage:  python decode/extract_r2c_cache.py SEG [SEG ...]      # e.g. 0 1 3 4 8 9 10 11 12
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
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = Path(__file__).resolve().parents[2] / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_0000002c--eb219f392c"
OUT = Path(os.environ.get("R2C_CACHE", Path(__file__).resolve().parents[2] / "_scratch/cache/r2c"))


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def extract(paths, tag, t0=None):
    rows, e4hist = [], []
    last18, lastE4 = None, (0.0, 0)
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}

    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    src, addr = int(m.src), int(m.address)
                    d = bytes(m.dat)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        # 🛑 DELIBERATE, and it costs exactly one frame per segment (9 of ~51,000
                        # on route 2c): 0x14A arrives before 0x18F in each segment's first CAN
                        # batch, so the held-last merge has nothing to hold yet. Dropping is the
                        # conservative choice -- the alternative is a NaN, and a SINGLE NaN
                        # propagates through the FFT to make every sample NaN, which then reads
                        # as "0 hands-off frames": a plausible null rather than a visible error.
                        # Same guard as probe/decode_v59_boostindex.py. Do not "fix" this.
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                try:
                    cs["press"].append(float(bool(c.steeringPressed)))
                except Exception:
                    cs["press"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                try:
                    cc["req"].append(float(evt.carControl.actuators.torque))
                except Exception:
                    cc["req"].append(np.nan)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    if t0 is None:
        t0 = d["t"][0]
    d["t"] = d["t"] - t0
    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V59 thermometer decode -------------------------------------------------------------
    p = d["probe"].astype(int)
    d["live"] = ((p & 0x80) != 0).astype(float)
    d["fault"] = ((p & 0x40) != 0).astype(float)
    lt512 = ((p & 0x20) != 0)
    lt1024 = ((p & 0x10) != 0)
    lt2048 = ((p & 0x08) != 0)
    d["lt512"] = lt512.astype(float)
    d["lt1024"] = lt1024.astype(float)
    d["lt2048"] = lt2048.astype(float)
    # 🛑 monotonicity is a VALIDITY flag, not a filter to average over. bit5=>bit4=>bit3.
    d["mono"] = (~((lt512 & ~lt1024) | (lt1024 & ~lt2048))).astype(float)
    d["lvl"] = (3 - lt512.astype(int) - lt1024.astype(int) - lt2048.astype(int)).astype(float)

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    np.savez_compressed(OUT / f"{tag}.npz", **d, e4hist=e4)
    fs = 1.0 / np.median(np.diff(d["t"]))
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s  "
          f"mono {100 * d['mono'].mean():.3f}%  live {100 * d['live'].mean():.2f}%  "
          f"lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[1:]:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"r2cs{s}")
