#!/usr/bin/env python3
"""Extract the EPS wire signals one route at a time into `_scratch/cache/<route>/lx_slot.npz`.

Purpose (TRACE-2026-10-05-lx-rlog-slot-inference): compare the 2019 Accord LX (dongle b308cfc5781b463d)
against the operator's 2020 Accord on the MANUAL-steering relation 0x1AB motor torque vs 0x18F column
torque, to infer the LX's row in the variant table @0xCD000.

Decode (opendbc honda_accord_2018_can_generated.dbc, MSB-first bit numbering; the kit's own conventions
in decode/extract_r29_cache.py):
  0x18F (399, src 1, DLC 7)   b0:2 BE s16  STEER_TORQUE_SENSOR (raw wire counts; DBC scale -1.0 NOT applied)
                              b2:4 BE s16  STEER_ANGLE_RATE fine (raw; DBC -0.1 deg/s per count)
                              b4 bit3      STEER_CONTROL_ACTIVE ; b4 bits7:4 STEER_STATUS ; b5 bit4 (fault-class)
  0x1AB (427, src 1, DLC 3)   ((b0&3)<<8)|b1  MOTOR_TORQUE 10-bit = clamp(|gp-0x6c18|*5>>3, 0, 1023) on STOCK
                              b0 bit7 CONFIG_VALID, b0 bit2 (DTC-active), b2 bit6 OUTPUT_DISABLED
  0x14A (330, src 1, DLC 8)   b0:2 BE s16 STEER_ANGLE (raw; -0.1 deg) ; b2:4 BE s16 STEER_ANGLE_RATE coarse
  0xE4  (228)                 src 2 = camera, sendcan bus 1 = openpilot: b0:2 BE s16 STEER_TORQUE, b2 bit7 REQUEST
  0x158 (344, src 1)          b0:2 BE u16 XMISSION_SPEED * 0.01 km/h
  carState.vEgo / steeringPressed ; carControl.latActive  (cereal; `which()` wrapped because the LX runs a
  different openpilot whose schema has events ours lacks)

Every array is concatenated across segments with `t` = logMonoTime - t0(route) in seconds.
Run once per route (seconds per segment); analysis scripts read the cache only.

Usage:  python extract_lx_slot.py <route-dir-or-glob-prefix> [...]
   e.g. python extract_lx_slot.py analysis-2020accord/rlogs/b308cfc5781b463d_000000a6--f3e9e379ee
        python extract_lx_slot.py analysis-2020accord/rlogs/75604b0a432fdc89_0000002b--7926e8f7e5
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
for _root in ([_repo] if _repo else []) + [_r]:
    for _d in ("", "lib", "decode", "score", "probe", "studies"):
        _p = _os.path.join(_root, _d) if _d else _root
        if _os.path.isdir(_p) and _p not in _sys.path:
            _sys.path.insert(0, _p)
# --- END PATH BOOTSTRAP ----------------------------------------------------
import glob
import sys
import time
from pathlib import Path

import numpy as np

import rlog_parse

REPO = Path(_repo)
CACHE = REPO / "_scratch" / "cache"


def s16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


def extract_route(prefix):
    prefix = str(prefix).rstrip("/\\")
    if _os.path.isdir(prefix):
        segs = glob.glob(_os.path.join(prefix, "*--rlog.zst"))
    else:
        segs = glob.glob(prefix + "--*--rlog.zst")
    segs = sorted(segs, key=lambda s: int(Path(s).name.split("--")[2]))
    if not segs:
        print(f"no segments for {prefix}")
        return
    route = Path(segs[0]).name.rsplit("--", 2)[0]
    out_dir = CACHE / route
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "lx_slot.npz"

    C = {k: [] for k in ("t18f", "tq18f", "rate18f", "status", "ctrl", "b5b4",
                         "t1ab", "mt", "b0_1ab", "b2_1ab",
                         "t14a", "ang", "rate14a",
                         "te4", "src_e4", "req_e4", "tq_e4",
                         "t158", "v158",
                         "tcs", "vego", "pressed", "tcc", "lat")}
    meta = {"segments": [], "t0": None, "n_msgs": 0, "truncated": []}
    t_start = time.time()
    for seg in segs:
        n = 0
        try:
            for evt in rlog_parse.read_messages(seg):
                n += 1
                try:
                    w = evt.which()
                except Exception:          # schema member unknown to our cereal ("Member was null")
                    continue
                tm = evt.logMonoTime * 1e-9
                if meta["t0"] is None:
                    meta["t0"] = tm
                tm -= meta["t0"]
                if w == "can":
                    for m in evt.can:
                        a = int(m.address); s = int(m.src); d = bytes(m.dat)
                        if s == 1 and a == 0x18F and len(d) >= 6:
                            C["t18f"].append(tm); C["tq18f"].append(s16be(d, 0)); C["rate18f"].append(s16be(d, 2))
                            C["status"].append(d[4] >> 4); C["ctrl"].append((d[4] >> 3) & 1)
                            C["b5b4"].append((d[5] >> 4) & 1 if len(d) > 5 else 0)
                        elif s == 1 and a == 0x1AB and len(d) >= 3:
                            C["t1ab"].append(tm); C["mt"].append(((d[0] & 3) << 8) | d[1])
                            C["b0_1ab"].append(d[0]); C["b2_1ab"].append(d[2])
                        elif s == 1 and a == 0x14A and len(d) >= 4:
                            C["t14a"].append(tm); C["ang"].append(s16be(d, 0)); C["rate14a"].append(s16be(d, 2))
                        elif a == 0xE4 and len(d) >= 3:
                            C["te4"].append(tm); C["src_e4"].append(s); C["req_e4"].append((d[2] >> 7) & 1)
                            C["tq_e4"].append(s16be(d, 0))
                        elif s == 1 and a == 0x158 and len(d) >= 2:
                            C["t158"].append(tm); C["v158"].append(((d[0] << 8) | d[1]) * 0.01)
                elif w == "sendcan":
                    for m in evt.sendcan:
                        a = int(m.address); s = int(m.src); d = bytes(m.dat)
                        if a == 0xE4 and len(d) >= 3:
                            C["te4"].append(tm); C["src_e4"].append(100 + s); C["req_e4"].append((d[2] >> 7) & 1)
                            C["tq_e4"].append(s16be(d, 0))
                elif w == "carState":
                    cs = evt.carState
                    C["tcs"].append(tm); C["vego"].append(float(cs.vEgo)); C["pressed"].append(int(cs.steeringPressed))
                elif w == "carControl":
                    cc = evt.carControl
                    try:
                        lat = int(cc.latActive)
                    except Exception:
                        lat = int(cc.enabled)
                    C["tcc"].append(tm); C["lat"].append(lat)
        except Exception as exc:
            meta["truncated"].append((Path(seg).name, n, str(exc).splitlines()[0]))
        meta["segments"].append((Path(seg).name, n))
        meta["n_msgs"] += n
        print(f"  {Path(seg).name}: {n:,} msgs  ({time.time() - t_start:.1f} s)", flush=True)
    arrays = {k: np.asarray(v) for k, v in C.items()}
    np.savez_compressed(out, **arrays, meta=np.array(repr(meta)))
    print(f"wrote {out}  0x18F {len(arrays['t18f']):,}  0x1AB {len(arrays['t1ab']):,}  "
          f"0x14A {len(arrays['t14a']):,}  carState {len(arrays['tcs']):,}  "
          f"truncated {len(meta['truncated'])}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        extract_route(p)
