#!/usr/bin/env python3
"""One-segment reconnaissance for the `command <-> response causality` question.

Answers three things BEFORE any analysis is written:
  1. which of the 0x0E4 copies actually exist in this corpus (`sendcan` src1 vs `can` src129),
  2. the ARRIVAL-TIME relationship between the three clocks that matter
     (openpilot's send clock, the EPS's 0x14A clock, the EPS's 0x18F clock),
  3. how big the frame-to-frame jitter is, i.e. how much phase error a naive
     `np.interp` onto a foreign lattice would inject at 27 Hz.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


def main(path):
    seen = {}
    sc_t, sc_v = [], []
    e4_t, e4_v = [], []
    t14, t18, t1ab = [], [], []
    for evt in read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        if w == "can":
            for m in evt.can:
                src, addr = int(m.src), int(m.address)
                seen[(src, addr)] = seen.get((src, addr), 0) + 1
                if src == 1 and addr == 0x14A:
                    t14.append(tm)
                elif src == 1 and addr == 0x18F:
                    t18.append(tm)
                elif src == 1 and addr == 0x1AB:
                    t1ab.append(tm)
                elif src == 129 and addr == 0x0E4:
                    e4_t.append(tm)
                    e4_v.append(float(i16be(bytes(m.dat), 0)))
        elif w == "sendcan":
            for m in evt.sendcan:
                if int(m.address) == 0x0E4:
                    seen[("send", int(m.src), 0x0E4)] = seen.get(("send", int(m.src), 0x0E4), 0) + 1
                    if int(m.src) == 1:
                        sc_t.append(tm)
                        sc_v.append(float(i16be(bytes(m.dat), 0)))

    print(f"--- {Path(path).name}")
    top = sorted(seen.items(), key=lambda kv: -kv[1])[:18]
    print("  frame census (src, addr) -> n:")
    for k, v in top:
        if isinstance(k[0], str):
            print(f"    sendcan src{k[1]} 0x{k[2]:03X}: {v}")
        else:
            print(f"    can src{k[0]:3d} 0x{k[1]:03X}: {v}")

    for nm, t in (("0x14A", t14), ("0x18F", t18), ("0x1AB", t1ab),
                  ("sendcan 0x0E4", sc_t), ("can129 0x0E4", e4_t)):
        t = np.asarray(t, float)
        if len(t) < 3:
            print(f"  {nm:14s}: n={len(t)}  (too few)")
            continue
        dt = np.diff(t)
        fs = (len(t) - 1) / (t[-1] - t[0])
        print(f"  {nm:14s}: n={len(t):6d}  fs=(n-1)/span={fs:8.4f} Hz  "
              f"1/median(dt)={1/np.median(dt):8.4f}  dt p5/p50/p95="
              f"{np.percentile(dt,5)*1e3:6.2f}/{np.median(dt)*1e3:6.2f}/"
              f"{np.percentile(dt,95)*1e3:6.2f} ms  ndup={int((dt==0).sum())}")

    # --- inter-clock offsets: for each 0x14A, the age of the newest frame of each other stream
    t14 = np.asarray(t14, float)
    for nm, t in (("0x18F", t18), ("sendcan 0x0E4", sc_t), ("can129 0x0E4", e4_t)):
        t = np.asarray(t, float)
        if len(t) < 3 or len(t14) < 3:
            continue
        j = np.searchsorted(t, t14, side="right") - 1
        ok = j >= 0
        age = (t14[ok] - t[j[ok]]) * 1e3
        print(f"  age of newest {nm:14s} at each 0x14A: mean {age.mean():6.2f} ms  "
              f"p5 {np.percentile(age,5):6.2f}  p50 {np.percentile(age,50):6.2f}  "
              f"p95 {np.percentile(age,95):6.2f}")

    # --- sendcan -> bus echo latency, the one transport delay we CAN measure
    sc_t, e4_t = np.asarray(sc_t, float), np.asarray(e4_t, float)
    if len(sc_t) > 10 and len(e4_t) > 10:
        j = np.searchsorted(sc_t, e4_t, side="right") - 1
        ok = j >= 0
        lat = (e4_t[ok] - sc_t[j[ok]]) * 1e3
        print(f"  sendcan->can129 echo latency: mean {lat.mean():.2f} ms  "
              f"p5 {np.percentile(lat,5):.2f}  p50 {np.percentile(lat,50):.2f}  "
              f"p95 {np.percentile(lat,95):.2f}   (n={ok.sum()})")
        sc_v, e4_v = np.asarray(sc_v, float), np.asarray(e4_v, float)
        same = (e4_v[ok] == sc_v[j[ok]]).mean()
        print(f"  echo value identical to the newest sent value: {100*same:.2f}%")

    # --- what a naive interp costs at 27 Hz
    if len(sc_t) > 3:
        dt = np.diff(sc_t)
        jit = np.std(dt) * 1e3
        print(f"  NAIVE-INTERP COST: sendcan dt sd = {jit:.2f} ms -> "
              f"{360*27.34*jit*1e-3:.1f} deg of phase jitter at 27.34 Hz")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(HERE.parent / "analysis-2020accord" / "rlogs" /
             "75604b0a432fdc89_0000006d--5d03a5adb4--5--rlog.zst"))
