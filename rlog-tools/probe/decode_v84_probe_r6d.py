#!/usr/bin/env python3
"""probe/decode_v84_probe_r6d.py -- route `6d` (and `68`): extract, ESTABLISH THE BUILD, then decode.

This EXTENDS `analysis-2020accord/studies/probes/decode_v84_probe.py` (imported, not copied -- its `classify_log`
is still the refusal gate and its bit map still comes from `build_v84_tva`).  What this file adds:

  1. **an extractor** for routes `6d` and `68`, writing `_scratch/cache/r6d/` and `_scratch/cache/r68x/` with the
     VERBATIM schema of `decode/extract_r67_v81.py` (which is `compare_v75_v76_v80_grind.extract66`'s), so
     every existing `_r*_lib` / `_grind2_lib` harness loads them unchanged;
  2. **a build-identity battery with NO free parameters**, run on the raw `0x14A` byte-4 stream.

★ WHY THE IDENTITY TEST NEEDS NO FITTED NUMBER.  The V75/V81/V83a cave writes a **THERMOMETER** into
bits 7:4 -- `|damper|` against 0 / 128 / 288 / 448 -- so its bits are **NESTED BY CONSTRUCTION**:
`b4 => b5 => b6 => b7`, and only 10 of the 32 field values can ever appear.  V84's cave writes
**FIVE INDEPENDENT PREDICATES** into the same five bits, two of which (`r24 >= +1024`,
`r24 <= -1025`) are **MUTUALLY EXCLUSIVE**.  So the two hypotheses make *opposite* structural
predictions on the same bytes:

    | statistic                       | if V81/V83a (thermometer) | if V84 (5 predicates) |
    |---------------------------------|---------------------------|-----------------------|
    | `b3` duty                       | = P(gp-0x6ac2 != 0), free | **exactly 1.000**     |
    | `b7 AND b6` co-occurrence       | **= b6 duty** (nesting)   | **exactly 0.000**     |
    | field outside the 10-value set  | **exactly 0.000**         | > 0                   |
    | nesting violations b6=>b7 etc.  | **exactly 0.000**         | > 0                   |

None of those four rows contains a parameter.  They are read off the two caves' *structure*, and
they cannot both be true of one log.  Route 67 (known V81) is the method's positive control.

🛑 SAMPLING IS 100 Hz.  Every rung number below is a **DUTY CYCLE, never a peak**.

Usage:
    python probe/decode_v84_probe_r6d.py extract 6d      # -> _scratch/cache/r6d/
    python probe/decode_v84_probe_r6d.py extract 68      # -> _scratch/cache/r68x/
    python probe/decode_v84_probe_r6d.py identify 6d [68 67]
    python probe/decode_v84_probe_r6d.py rungs 6d
    python probe/decode_v84_probe_r6d.py health 6d
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import os
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

from compare_v75_v76_v80_grind import (GEAR, KMH, _grid, held_last,  # noqa: E402
                                       i16be, wheel_speeds_kph)
from decode_v75_probe import (BIT_BACKDRIVE, BIT_DAMP_NZ, BIT_MAG128,  # noqa: E402
                              BIT_MAG288, BIT_MAG448, LEGAL_PAYLOADS, PROBE_MASK)

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
SENTINEL = 0x7FFF

# route key -> (dongle-route prefix, n segs, cache dir, per-seg prefix, npz stem, label)
ROUTES = {
    "6d": ("75604b0a432fdc89_0000006d--5d03a5adb4", 12, "_scratch/cache/r6d", "r6ds", "r6d", "V84?"),
    "68": ("75604b0a432fdc89_00000068--0b7efae911", 8, "_scratch/cache/r68x", "r68xs", "r68", "V83a"),
    "67": ("75604b0a432fdc89_00000067--9b3ebbe218", 14, "_scratch/cache/r67x", "r67xs", "r67", "V81"),
}


# ======================================================================================
# 1.  EXTRACTION -- schema-verbatim with decode/extract_r67_v81.py
# ======================================================================================
def extract(route):
    from rlog_parse import read_messages

    pref, nseg, cdir, _pfx, stem, label = ROUTES[route]
    paths = [RLOGDIR / f"{pref}--{s}--rlog.zst" for s in range(nseg)]
    CACHE = ROOT / cdir

    rows, seg_of_row = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    raw1ab_t, raw1ab_b0 = [], []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    sent14 = sent18 = 0
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": [], "rate": [], "brake": [], "brakev": [], "yaw": []}
    cc = {"t": [], "lat": [], "en": [], "req": [], "curv": [], "ccurv": []}
    ct = {"t": [], "dcurv": [], "curv": []}
    co = {"t": [], "req": [], "can": []}
    a_hw, a_mono, a_v, a_st = [], [], [], []
    events = []

    for si, p in enumerate(paths):
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
                        raw18_t.append(tm)
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        raw18_b4.append(d[4])
                        sent18 += ((d[0] << 8) | d[1]) == SENTINEL
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 1 and addr == 0x1AB and len(d) >= 1:
                        raw1ab_t.append(tm)
                        raw1ab_b0.append(d[0])
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                    elif src == 1 and addr == 0x1D0 and len(d) >= 8:
                        ws_t.append(tm)
                        ws_v.append(wheel_speeds_kph(d))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_t.append(tm)
                        raw14_b4.append(d[4])
                        sent14 += ((d[0] << 8) | d[1]) == SENTINEL
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
                        seg_of_row.append(si)
            elif w == "sendcan":
                for m in evt.sendcan:
                    if int(m.src) == 1 and int(m.address) == 0x0E4:
                        d = bytes(m.dat)
                        if len(d) >= 3:
                            sc_t.append(tm)
                            sc_tq.append(float(i16be(d, 0)))
                            sc_rq.append(float((d[2] >> 7) & 1))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                cs["rate"].append(float(c.steeringRateDeg))
                cs["brakev"].append(float(c.brake))
                cs["yaw"].append(float(c.yawRate))
                for k, attr in (("press", "steeringPressed"), ("std", "standstill"),
                                ("lblink", "leftBlinker"), ("rblink", "rightBlinker"),
                                ("brake", "brakePressed")):
                    try:
                        cs[k].append(float(bool(getattr(c, attr))))
                    except Exception:
                        cs[k].append(0.0)
                try:
                    cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
                except Exception:
                    cs["gear"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                for k, get in (("req", lambda e: e.carControl.actuators.torque),
                               ("curv", lambda e: e.carControl.actuators.curvature),
                               ("ccurv", lambda e: e.carControl.currentCurvature)):
                    try:
                        cc[k].append(float(get(evt)))
                    except Exception:
                        cc[k].append(np.nan)
            elif w == "controlsState":
                ct["t"].append(tm)
                for k, attr in (("dcurv", "desiredCurvature"), ("curv", "curvature")):
                    try:
                        ct[k].append(float(getattr(evt.controlsState, attr)))
                    except Exception:
                        ct[k].append(np.nan)
            elif w == "carOutput":
                try:
                    a = evt.carOutput.actuatorsOutput
                    co["t"].append(tm); co["req"].append(float(a.torque))
                    try:
                        co["can"].append(float(a.torqueOutputCan))
                    except Exception:
                        co["can"].append(np.nan)
                except Exception:
                    pass
            elif w == "accelerometer":
                try:
                    m = evt.accelerometer
                    a_hw.append(int(m.timestamp) * 1e-9); a_mono.append(tm)
                    a_v.append(list(m.acceleration.v)); a_st.append(int(m.acceleration.status))
                except Exception:
                    pass
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        events.append((tm, str(e.name), bool(getattr(e, "enable", False)),
                                       bool(getattr(e, "softDisable", False)),
                                       bool(getattr(e, "immediateDisable", False)),
                                       bool(getattr(e, "noEntry", False))))
                    except Exception:
                        continue
        print(f"  seg {si} done, rows so far {len(rows)}", flush=True)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    t0 = d["t"][0]
    d["t"] = d["t"] - t0
    d["seg"] = np.array(seg_of_row, float)

    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press", "rate", "brakev", "yaw"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink", "brake"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req", "curv", "ccurv"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))
    ctt = np.array(ct["t"], float) - t0
    for k in ("dcurv", "curv"):
        d["ct_" + k] = _grid(d["t"], ctt, ct[k])
    cot = np.array(co["t"], float) - t0
    d["co_req"] = _grid(d["t"], cot, co["req"])
    d["co_tqcan"] = _grid(d["t"], cot, co["can"])
    sct = np.array(sc_t, float) - t0
    d["sc_tq"] = _grid(d["t"], sct, sc_tq)
    d["sc_req"] = held_last(d["t"], sct, sc_rq, 0.0) if len(sct) else np.full(len(d["t"]), np.nan)

    wst = np.array(ws_t, float) - t0
    wsv = np.array(ws_v, float).reshape(-1, 4)
    for i, k in enumerate(("fl", "fr", "rl", "rr")):
        d["ws_" + k] = (_grid(d["t"], wst, wsv[:, i] * KMH) if len(wst)
                        else np.full(len(d["t"]), np.nan))

    # ---- BOTH probe decodes, on every route.  🛑 This is deliberate: the identity battery needs
    # ---- the thermometer reading of a V84 log and the V84 reading of a V83a log to be side by side.
    p = d["probe"].astype(int)
    d["field"] = (p & PROBE_MASK).astype(float)
    d["status"] = (p & 0x07).astype(float)
    # -- V75/V81/V83a thermometer interpretation
    d["damp_nz"] = ((p & BIT_DAMP_NZ) != 0).astype(float)
    d["thermo_128"] = ((p & BIT_MAG128) != 0).astype(float)
    d["thermo_288"] = ((p & BIT_MAG288) != 0).astype(float)
    d["thermo_448"] = ((p & BIT_MAG448) != 0).astype(float)
    d["thermo"] = (d["damp_nz"] + d["thermo_128"] + d["thermo_288"] + d["thermo_448"])
    d["g6ac2"] = ((p & BIT_BACKDRIVE) != 0).astype(float)
    d["illegal"] = np.array([0.0 if int(x) in LEGAL_PAYLOADS else 1.0 for x in d["field"]])
    # -- V84 five-predicate interpretation (same five bits, different meaning)
    d["v84_r24_pos"] = ((p & 0x80) != 0).astype(float)
    d["v84_r24_neg"] = ((p & 0x40) != 0).astype(float)
    d["v84_r24_mag"] = ((p & 0xC0) != 0).astype(float)
    d["v84_fd_gate"] = ((p & 0x20) != 0).astype(float)
    d["v84_fd_axis"] = ((p & 0x10) != 0).astype(float)
    d["v84_fingerprint"] = ((p & 0x08) != 0).astype(float)

    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = (held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan)
                       if len(r1ab_t) else np.full(len(d["t"]), np.nan))

    A = np.array(a_v, float).reshape(-1, 3) if len(a_v) else np.zeros((0, 3))
    if len(A):
        off_a = float(np.median(np.array(a_mono, float) - np.array(a_hw, float)))
        at = np.array(a_hw, float) + off_a - t0
        means = np.array([A[:, i].mean() for i in range(3)])
        vi = int(np.argmin(np.abs(np.abs(means) - 9.807)))
        li = int(np.argmax([abs(means[i]) if i != vi else -1 for i in range(3)]))
        li = [i for i in range(3) if i != vi][0] if li == vi else li
        d["imu_vert"] = _grid(d["t"], at, A[:, vi])
        d["imu_lat"] = _grid(d["t"], at, A[:, li])
        print(f"  IMU gravity means {means} -> vertical = {'xyz'[vi]}, lateral = {'xyz'[li]}")
    else:
        d["imu_vert"] = np.full(len(d["t"]), np.nan)
        d["imu_lat"] = np.full(len(d["t"]), np.nan)

    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE / f"{stem}.npz", **d,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
        ws_t=wst, ws_kph=wsv, sc_t=sct, sc_tq_raw=np.array(sc_tq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        sentinels=np.array([sent14, sent18]),
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array([label]))
    (CACHE / f"{stem}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    print(f"\nroute {route}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print(f"  0x7FFF sentinels: 0x14A {sent14}  0x18F {sent18}")
    print(f"  latActive {100 * np.mean(d['cc_lat'] > 0.5):.1f}% of {d['t'][-1]:.0f} s")
    return d


PASS_1D = ["t", "ang", "rate_c", "wang", "tq", "rate_f", "sca", "sstat", "slow3", "e4tq", "e4req",
           "cs_v", "cs_eng", "cs_ang", "cs_tq", "cs_press", "cs_gear", "cs_std", "cs_lblink",
           "cs_rblink", "cs_lchg", "cs_rate", "cs_brake", "cs_brakev", "cs_yaw",
           "cc_lat", "cc_en", "cc_req", "cc_curv", "cc_ccurv", "ct_dcurv", "ct_curv",
           "co_req", "co_tqcan", "sc_tq", "sc_req", "ws_fl", "ws_fr", "ws_rl", "ws_rr",
           "dtc_active", "imu_vert", "imu_lat", "probe", "field", "status",
           "damp_nz", "thermo_128", "thermo_288", "thermo_448", "thermo", "g6ac2", "illegal",
           "v84_r24_pos", "v84_r24_neg", "v84_r24_mag", "v84_fd_gate", "v84_fd_axis",
           "v84_fingerprint"]


def split(route):
    """Per-segment files with `t` RESET to 0 -- the schema every `_r*_lib.py` assumes."""
    _pref, _n, cdir, pfx, stem, label = ROUTES[route]
    CACHE = ROOT / cdir
    d = np.load(CACHE / f"{stem}.npz")
    seg = d["seg"]
    census = {}
    for s in np.unique(seg.astype(int)):
        m = seg == s
        if m.sum() < 256:
            print(f"  seg{s}: {int(m.sum())} frames -- SKIPPED")
            continue
        out = {k: d[k][m] for k in PASS_1D if k in d.files}
        out["t"] = out["t"] - out["t"][0]
        out["probe_build"] = np.array([label])
        np.savez_compressed(CACHE / f"{pfx}{s}.npz", **out)
        tt, vv, ll = out["t"], np.abs(out["cs_v"]), out["cc_lat"] > 0.5
        census[int(s)] = dict(n=int(m.sum()), sec=float(tt[-1] - tt[0]),
                              v_mean=float(vv.mean()), v_max=float(vv.max()),
                              lat_frac=float(ll.mean()), eng_sec=float(ll.sum() * 0.01))
        print(f"  seg{s}: n={int(m.sum()):6d} {tt[-1] - tt[0]:6.1f}s  v_mean {vv.mean():5.2f} "
              f"(max {vv.max():5.2f})  engaged {ll.mean() * 100:5.1f}% ({ll.sum() * .01:5.1f}s)")
    (CACHE / f"{stem}_census_seg.json").write_text(json.dumps(census, indent=1))


# ======================================================================================
# 2.  BUILD IDENTITY -- four structural statistics, no free parameter in any of them
# ======================================================================================
THERMO_ALPHABET = set(LEGAL_PAYLOADS)


def identity(route):
    """Return the parameter-free identity battery for one route's raw 0x14A byte-4 stream."""
    _pref, _n, cdir, _pfx, stem, label = ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz")
    b4 = z["raw14_b4"].astype(int) & 0xFF
    f = b4 & 0xF8
    n = len(b4)
    b7 = (f & 0x80) != 0
    b6 = (f & 0x40) != 0
    b5 = (f & 0x20) != 0
    b4b = (f & 0x10) != 0
    b3 = (f & 0x08) != 0
    out = dict(route=route, cache_label=label, frames=int(n))
    out["b7_duty"] = float(b7.mean()); out["b6_duty"] = float(b6.mean())
    out["b5_duty"] = float(b5.mean()); out["b4_duty"] = float(b4b.mean())
    out["b3_duty"] = float(b3.mean())
    # (i) V84 says b7 and b6 are MUTUALLY EXCLUSIVE (r24 cannot be >= +1024 and <= -1025).
    #     the thermometer says b6 => b7 ALWAYS, so co-occurrence == b6 duty.
    out["b7_and_b6"] = float((b7 & b6).mean())
    # (ii) thermometer nesting: b4=>b5=>b6=>b7.  V84's predicates are independent.
    out["viol_b6_not_b7"] = float((b6 & ~b7).mean())
    out["viol_b5_not_b6"] = float((b5 & ~b6).mean())
    out["viol_b4_not_b5"] = float((b4b & ~b5).mean())
    out["nesting_violation_any"] = float(((b6 & ~b7) | (b5 & ~b6) | (b4b & ~b5)).mean())
    # (iii) alphabet: the thermometer can only ever emit 10 of the 32 field values.
    out["outside_thermo_alphabet"] = float(np.mean([int(v) not in THERMO_ALPHABET for v in f]))
    # (iv) V84's own structural self-check: FUN_0003fc16 zeroes gp-0x6a10 when the gate is shut.
    out["v84_axis_without_gate"] = float((b4b & ~b5).mean())
    fu, fc = np.unique(f, return_counts=True)
    out["field_hist"] = {f"0x{int(v):02X}": int(c) for v, c in zip(fu, fc)}
    return out


def identity_table(routes):
    res = [identity(r) for r in routes]
    w = 26
    hdr = "statistic".ljust(w) + "".join(f"{'route ' + r['route']:>18}" for r in res)
    lines = [hdr, "-" * len(hdr)]
    rows = [
        ("frames", "frames", "{:,}"),
        ("b7 duty", "b7_duty", "{:.5f}"),
        ("b6 duty", "b6_duty", "{:.5f}"),
        ("b5 duty", "b5_duty", "{:.5f}"),
        ("b4 duty", "b4_duty", "{:.5f}"),
        ("b3 duty  <- FINGERPRINT", "b3_duty", "{:.5f}"),
        ("b7 AND b6", "b7_and_b6", "{:.5f}"),
        ("viol b6 & !b7", "viol_b6_not_b7", "{:.5f}"),
        ("viol b5 & !b6", "viol_b5_not_b6", "{:.5f}"),
        ("viol b4 & !b5", "viol_b4_not_b5", "{:.5f}"),
        ("any nesting violation", "nesting_violation_any", "{:.5f}"),
        ("outside thermo alphabet", "outside_thermo_alphabet", "{:.5f}"),
    ]
    for lab, key, fmt in rows:
        lines.append(lab.ljust(w) + "".join(f"{fmt.format(r[key]):>18}" for r in res))
    lines.append("")
    for r in res:
        lines.append(f"route {r['route']} field histogram: " +
                     " ".join(f"{k}:{v}" for k, v in sorted(r["field_hist"].items())))
    return "\n".join(lines), res


# ======================================================================================
# 3.  THE FIVE RUNGS, stratified
# ======================================================================================
def _duty(mask, sel):
    sel = np.asarray(sel, bool)
    return float(mask[sel].mean()) if sel.sum() else float("nan")


def rungs(route):
    _pref, _n, cdir, _pfx, stem, _label = ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz")
    p = z["probe"].astype(int)
    lat = z["cc_lat"] > 0.5
    v = np.abs(z["cs_v"])                       # m/s
    rate = np.abs(z["rate_c"])                  # deg/s, from 0x14A
    R = {"b7 r24>=+1024": (p & 0x80) != 0,
         "b6 r24<=-1025": (p & 0x40) != 0,
         "b7|b6 |r24|>=1024": (p & 0xC0) != 0,
         "b5 gp-0x67fe in{1,2}": (p & 0x20) != 0,
         "b4 gp-0x6a10>=8": (p & 0x10) != 0,
         "b3 fingerprint": (p & 0x08) != 0}
    strata = [("ALL", np.ones(len(p), bool)),
              ("engaged", lat), ("manual", ~lat)]
    vb = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 30), (30, 100)]
    for lo, hi in vb:
        strata.append((f"eng v {lo}-{hi} m/s", lat & (v >= lo) & (v < hi)))
    rb = [(0, 5), (5, 20), (20, 60), (60, 1e9)]
    for lo, hi in rb:
        strata.append((f"eng |rate| {lo}-{hi}", lat & (rate >= lo) & (rate < hi)))
    lines = ["stratum".ljust(22) + "n".rjust(9) +
             "".join(k.split()[0].rjust(9) for k in R)]
    lines.append("-" * len(lines[0]))
    tbl = {}
    for name, sel in strata:
        lines.append(name.ljust(22) + f"{int(sel.sum()):>9,}" +
                     "".join(f"{_duty(m, sel):>9.4f}" for m in R.values()))
        tbl[name] = dict(n=int(sel.sum()), **{k: _duty(m, sel) for k, m in R.items()})
    return "\n".join(lines), tbl


# ======================================================================================
# 3b.  WHAT `gp-0x6a10` ACTUALLY IS -- the first measurement this kit has ever had of it
# ======================================================================================
def factord(route):
    """`b4` is a 1-bit comparator at `gp-0x6a10 >= 8`.  Sweeping the SIGNED column angle through
    its flip point identifies the cell's axis without any fitted parameter: if `gp-0x6a10` were a
    TRACKING error the flip would sit at different angles engaged vs manual (and would not exist at
    all in manual, where there is no LKAS target).  If it is |column angle| the flip is SYMMETRIC
    about 0 and IDENTICAL in both.  🛑 A 1-bit comparator sees ONE point of the curve -- everything
    beyond the flip location is extrapolation and must be marked BELIEF."""
    _pref, _n, cdir, _pfx, stem, _label = ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz")
    p = z["probe"].astype(int)
    b4 = (p & 0x10) != 0
    lat = z["cc_lat"] > 0.5
    a = z["ang"]
    out = {"signed_flip": [], "by_absangle": []}
    for lo in np.arange(-2.0, 2.0, 0.2):
        for tag, sel in (("engaged", lat), ("manual", ~lat)):
            m = sel & (a >= lo) & (a < lo + 0.2)
            if m.sum() >= 100:
                out["signed_flip"].append(dict(tag=tag, lo=round(float(lo), 2),
                                               n=int(m.sum()), b4=float(b4[m].mean())))
    for lo, hi in ((0, .8), (.8, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 15.0), (15.0, 45.0),
                   (45.0, 1e9)):
        for tag, sel in (("engaged", lat), ("manual", ~lat)):
            m = sel & (np.abs(a) >= lo) & (np.abs(a) < hi)
            if m.sum() >= 100:
                out["by_absangle"].append(dict(tag=tag, lo=lo, hi=hi, n=int(m.sum()),
                                               b4=float(b4[m].mean())))
    return out


# ======================================================================================
# 4.  FLIGHT HEALTH
# ======================================================================================
def health(route):
    _pref, _n, cdir, _pfx, stem, _label = ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz")
    t = z["t"]; lat = z["cc_lat"] > 0.5
    st = z["raw18_st"].astype(int)
    su, sc = np.unique(st, return_counts=True)
    b0 = z["raw1ab_b0"].astype(int)
    dtc = (b0 >> 2) & 1
    trans = int(np.sum(np.diff(dtc) != 0)) if len(dtc) > 1 else 0
    ep, n_ep, cur = [], 0, 0
    for x in lat:
        if x:
            cur += 1
        else:
            if cur:
                ep.append(cur)
            cur = 0
    if cur:
        ep.append(cur)
    ep = np.array(ep, float) * 0.01
    out = dict(
        route=route, samples=int(len(t)), duration_s=float(t[-1] - t[0]),
        engaged_frac=float(lat.mean()), engaged_s=float(lat.sum() * 0.01),
        episodes_ge_2s=int((ep >= 2.0).sum()), episodes_total=int(len(ep)),
        longest_episode_s=float(ep.max()) if len(ep) else 0.0,
        v_min=float(np.abs(z["cs_v"]).min()), v_max=float(np.abs(z["cs_v"]).max()),
        v_mean=float(np.abs(z["cs_v"]).mean()),
        steer_status_hist={int(k): int(c) for k, c in zip(su, sc)},
        dtc_frames=int(len(b0)), dtc_active_duty=float(dtc.mean()) if len(dtc) else float("nan"),
        dtc_transitions=trans,
        sentinel_14A=int(z["sentinels"][0]), sentinel_18F=int(z["sentinels"][1]),
        b0_1ab_hist={f"0x{int(v):02X}": int(c)
                     for v, c in zip(*np.unique(b0, return_counts=True))},
    )
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "identify"
    args = sys.argv[2:] or ["6d"]
    if cmd == "extract":
        for r in args:
            extract(r); split(r)
    elif cmd == "split":
        for r in args:
            split(r)
    elif cmd == "identify":
        txt, res = identity_table(args)
        print(txt)
        (ROOT / ROUTES[args[0]][2] / "identity.json").write_text(json.dumps(res, indent=1))
    elif cmd == "rungs":
        for r in args:
            txt, tbl = rungs(r)
            print(f"\n=== route {r} rungs ===\n{txt}")
            (ROOT / ROUTES[r][2] / "rungs.json").write_text(json.dumps(tbl, indent=1))
    elif cmd == "factord":
        for r in args:
            fd = factord(r)
            print(json.dumps(fd, indent=1))
            (ROOT / ROUTES[r][2] / "factord.json").write_text(json.dumps(fd, indent=1))
    elif cmd == "health":
        for r in args:
            h = health(r)
            print(json.dumps(h, indent=1))
            (ROOT / ROUTES[r][2] / "health.json").write_text(json.dumps(h, indent=1))
    else:
        raise SystemExit(__doc__)
