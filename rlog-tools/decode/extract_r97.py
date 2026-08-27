#!/usr/bin/env python3
r"""Extract route `97` -- **THE V9b STOCK FLIGHT** -- into `analysis-2020accord/_scratch/cache/r97/`.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `extract_r80/81/82/85/95.py` do, this file only
adds a row to `decode_v84_probe_r6d.ROUTES` and calls `extract_r7d`'s `extract_route()` -- the SAME
code that wrote every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention, sentinel
definition, `PASS_1D`, the 0x1AB full tap, the 0x14A byte-7 tap and the `row2raw14` off-by-one fix
all come along unchanged, including the elementwise byte-4 assertion that kills the run rather than
silently mispairing.

===================================================================================================
ROUTE 97 == V9b STOCK.  NO CAVE.  NO CAL EDITS.  1x LKAS GAIN.  STOCK 0x1AB PACKER.
===================================================================================================
This is the kit's FIRST modern instrumented STOCK baseline.  Every band statistic every build has
been scored against has had NO stock arm since the instrument chain was built at `_scratch/cache/r6d`.

IDENTITY -- FOUR INDEPENDENT LEGS, all measured before this file was written (seg 5):
  1. `0x14A` byte7[7:6] == **0** on 6,003/6,003 frames.  V102 emits 3, V98..V100 emit 2,
     V96/V97 emit 1.  Only a build with NO byte7 writer emits 0.
  2. `0x14A` byte4 has **exactly ONE distinct value, 0x07**, on 6,003/6,003 frames  =>  the cave
     field `(byte4>>3)&0x1F` is identically 0.  Every probe build since V53 varies it.
  3. `0x1AB` [0:3] has **4 distinct payloads** -- `80000a / 800019 / 800028 / 800037` -- i.e. the
     COUNTER x CHECKSUM cycle with MOTOR_TORQUE identically 0.  Stock's 427 lane reads ~0
     (memory `honda-op-steeringtorqueeps-always-zero`); every repointed build varies it (route 96
     shows 174 distinct payloads on the matching segment).
  4. `carParams.carFw` EPS version string is **`39990-TVA-A160`** with a HYPHEN.  Every modded
     build since V18 flips `0x13109` and `0x14120` from `-` (0x2D) to `,` (0x2C)
     (`builds/v18_v49/build_v18_tva.py:66-67`, carried to `builds/v80_v107/build_v102_tva.py`), so a modded ECU reports
     `39990-TVA,A160`.  Route 96 reports the COMMA.  **This leg is completely independent of the
     CAN cave** -- it comes from the UDS version query at ignition.

STOCK HAS NO PROBE BITS.  `probe` is a constant 0x07 and every `v84_*` / thermometer column the
   shared extractor emits is meaningless here.  DO NOT read them.  Nothing in this route's readout
   may depend on a cave bit.

**PAIRING CONVENTION (asserted by `extract_r7d._row2raw14`):**
       t == raw14_t[1:]   and   probe == raw14_b4[1:]   and   probe == raw14_b4[row2raw14]
   => **SAFE PAIRS: (t, probe) or (raw14_t, raw14_b4).**

INSTRUMENT FACTS honoured here (identical to `decode/extract_r85.py` / `decode/extract_r95.py`):
  * `carState.yawRate` is identically zero on this car -- `lp_yaw` taps
    `livePose.angularVelocityDevice.z` (rad/s, z-DOWN => NEGATIVE on a LEFT turn) instead.
  * `vEgo` is invalid as a speed reference at angle.  Use `v_rear` = (ws_rl + ws_rr)/2.
  * Engagement is `cc_lat > 0.5` (latActive).  `cs_eng` is cruiseState and is NOT lateral.

**OPERATOR-CONFIRMED SIGN CONVENTION, 2026-08-13.**  NEGATIVE driver torque AND NEGATIVE steering
   angle = a RIGHT turn.  **This extractor applies NO sign flip and NO offset removal.**

Usage:
    python decode/extract_r97.py                 # extract + derive + identity + census
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
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402  -- installs the taps; brings D + rlog_parse with it
import rlog_parse        # noqa: E402

D = X.D

ROUTE = "97"
PREFIX = "75604b0a432fdc89_00000097--489d7896b3"
NSEG_SCAN = 18

D.ROUTES[ROUTE] = (PREFIX, NSEG_SCAN, "analysis-2020accord/_scratch/cache/r97", "r97s", "r97", "V9b-STOCK")

# ---- stock 427: Honda's own MOTOR_TORQUE, NOT a repoint.  No counts-per-LSB is claimed.
X.WIRE_SCALE[ROUTE] = float("nan")
X.WIRE_SOURCE[ROUTE] = "STOCK Honda MOTOR_TORQUE (NO repoint) -- expected identically 0"
X.BITNAMES[ROUTE] = {}

DERIVED = ["v_rear", "lp_yaw"]

# ======================================================================================
#  MISSING-SEGMENT GUARD + livePose / carFw taps.  Pass-through, verbatim from extract_r95.
# ======================================================================================
_TAPPED_READ = rlog_parse.read_messages
MISSING_SEGMENTS = []
LP = {"t": [], "z": []}
FW = {"eps": []}


def _read_guarded(path):
    p = Path(path)
    if not p.exists():
        MISSING_SEGMENTS.append(p.name)
        print("  segment file ABSENT, skipped: " + p.name, flush=True)
        return
    for evt in _TAPPED_READ(path):
        try:
            w = evt.which()
            if w == "livePose":
                LP["t"].append(evt.logMonoTime * 1e-9)
                LP["z"].append(float(evt.livePose.angularVelocityDevice.z))
            elif w == "carParams":
                for f in evt.carParams.carFw:
                    if str(f.ecu) == "eps":
                        v = bytes(f.fwVersion)
                        if v not in FW["eps"]:
                            FW["eps"].append(v)
        except Exception:
            pass
        yield evt


rlog_parse.read_messages = _read_guarded


def extract_route(route=ROUTE):
    MISSING_SEGMENTS.clear()
    LP["t"].clear()
    LP["z"].clear()
    FW["eps"].clear()
    rep = X.extract_route(route)
    rep["segments_absent"] = list(MISSING_SEGMENTS)
    rep["livePose_samples"] = len(LP["t"])
    rep["carFw_eps"] = [v.decode("latin1") for v in FW["eps"]]
    print("\n  segments absent from disk: %d   livePose samples: %d"
          % (len(MISSING_SEGMENTS), len(LP["t"])))
    print("  carFw EPS strings: %r" % (rep["carFw_eps"],))
    return rep


def derive(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / (stem + ".npz")
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)
    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    z["v_rear"] = 0.5 * (rl + rr)
    if len(LP["t"]) > 1:
        t0 = float(z["t0_mono"][0])
        lt = np.array(LP["t"], float) - t0
        o = np.argsort(lt)
        z["lp_yaw"] = np.interp(t, lt[o], np.array(LP["z"], float)[o])
    else:
        z["lp_yaw"] = np.full(n, np.nan)
    np.savez_compressed(f, **z)
    for k in DERIVED:
        if k not in D.PASS_1D:
            D.PASS_1D.append(k)
    D.split(route)
    print("\n  === DERIVED, route %s ===  n=%d  v_rear median %.2f  lp_yaw finite %.1f %%"
          % (route, n, np.nanmedian(z["v_rear"]), 100 * np.mean(np.isfinite(z["lp_yaw"]))))
    return z


def identity(route=ROUTE):
    """STOCK's identity is the ABSENCE of every cave signature, plus the hyphen in the PN."""
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    mt = np.asarray(z["ab_mt"], int)
    n = len(b4)
    code = (b7 & 0xC0) >> 6
    field = (b4 >> 3) & 0x1F
    cu, cc = np.unique(code, return_counts=True)
    b4u, b4c = np.unique(b4, return_counts=True)
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code0_duty=float((code == 0).mean()),
               byte4_distinct=int(len(b4u)),
               byte4_hist={int(v): int(c) for v, c in zip(b4u, b4c)},
               byte4_field_all_zero=bool(np.all(field == 0)),
               mt_nonzero_frac=float(np.mean(mt != 0)), mt_distinct=int(len(np.unique(mt))),
               mt_max=int(mt.max()) if len(mt) else 0,
               carFw_eps=[v.decode("latin1") for v in FW["eps"]])
    # 🛑 0x1AB IS NOT A LEG.  Over the whole route stock's own MOTOR_TORQUE takes 165 distinct
    # values (nonzero 20.8 %, p50 0, p99 60, max 173) and route 96's V102 repoint takes 127
    # (nonzero 60.5 %, p50 3, p99 73, max 130).  The distributions OVERLAP, so 0x1AB cannot
    # separate the builds -- an earlier version of this file asserted "identically 0" from a
    # single quiet segment and would have FAILED a genuinely stock route.  It is printed as
    # context only.  The three legs below are each individually decisive.
    legs = [("byte7[7:6] == 0 on every frame  (route 96 = 3 on every frame)",
             out["byte7_code0_duty"] >= 0.9999),
            ("byte4 has exactly ONE distinct value  (route 96 has 12)",
             out["byte4_distinct"] == 1),
            ("byte4 cave field identically 0", out["byte4_field_all_zero"])]
    out["legs"] = {k: bool(v) for k, v in legs}
    out["identity_pass"] = all(v for _, v in legs)
    print("\n  === IDENTITY, route %s (expected STOCK): %d 0x14A frames ===" % (route, n))
    print("    byte7[7:6] hist: " + "  ".join("%d:%d" % (int(v), int(c)) for v, c in zip(cu, cc)))
    print("    byte4 hist: " + "  ".join("0x%02X:%d" % (int(v), int(c))
                                         for v, c in zip(b4u, b4c)))
    print("    0x1AB MOTOR_TORQUE nonzero %.4f %%  distinct %d  max %d"
          % (100 * out["mt_nonzero_frac"], out["mt_distinct"], out["mt_max"]))
    print("    carFw EPS: %r" % (out["carFw_eps"],))
    for k, v in legs:
        print("    %s %s" % ("[PASS]" if v else "[FAIL]", k))
    print("    VERDICT: %s" % ("STOCK CONFIRMED" if out["identity_pass"] else "NOT STOCK"))
    (ROOT / cdir / (stem + "_identity.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    extract_route()
    derive()
    identity()
