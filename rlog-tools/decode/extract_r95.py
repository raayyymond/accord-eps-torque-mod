#!/usr/bin/env python3
r"""Extract route `95` -- **THE V101 FLIGHT (the 8x LKAS GAIN)** -- into
`analysis-2020accord/_scratch/cache/r95/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Like `extract_r80/81/82/85.py`, this file only adds a row
to `decode_v84_probe_r6d.ROUTES` and calls `extract_r7d`'s `extract_route()` -- the SAME code that
wrote every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention, sentinel definition and
`PASS_1D` are bit-for-bit the ones every prior route was scored with.  The 0x1AB full tap, the 0x14A
byte-7 tap and the `row2raw14` off-by-one fix all come along unchanged, including the elementwise
byte-4 assertion that kills the run rather than silently mispairing.

===================================================================================================
ROUTE 95 == V101.  V99 BASE + FIVE CAL CELLS + a 114 B CAVE + the 427 REPOINT (carried from V100).
===================================================================================================
    cal 0xC6CD0  3564 -> 7128   ⭐ THE 8x LKAS FORWARD GAIN (stock 891; 4x on every build V57..V100)
    cal 0xC61B2  2048 -> 4096      forward-path clamp tracking the gain (stock 512)
    cal 0xC61B4  2048 -> 4096      arb-output clamp tracking the gain (stock 512)
    cod 0x3AA96  0xFB -> 0xC5      LEVER B GATE reverted to Honda stock
    cal 0xC6446  5244 -> 512       LEVER B ARM  reverted to Honda stock

    byte4 b7 0x80 = gp-0x6b94 < 0                        ⭐ THE SIGN FOR THE 427 MAGNITUDE LANE
    byte4 b6 0x40 = |gp-0x6b4c| >= 4096                  ⭐ THE 8x LKAS COMMAND HITS ITS CLAMP
    byte4 b5 0x20 = gp-0x6b4c < 0                        ⭐ THE LKAS COMMAND SIGN
    byte4 b4 0x10 = gp-0x6ad6 < 0                        PID reference sign
    byte4 b3 0x08 = 🛑 UNCONDITIONAL CONSTANT 1          ⭐ THE BUILD IDENTITY (as on V100)
    byte7[7:6]    = 3  (byte7 & 0xC0 == 0xC0)            ⭐ NEW CODE -- 0=<=V91, 1=V96/V97,
                                                            2=V98/V99/V100, 3=V101

    427 (0x1AB) = clamp(|gp-0x6b94| * 5 >> 6, 0, 0x3FF)  -- packer and source BOTH carried from V100
                  => counts = wire * 64/5 = wire * 12.8
                  🛑 gp-0x6b94's OWN writer clamps it to +-10240, so the maximum REACHABLE code is
                     (10240*5)>>6 = 800 of 1023.  The STRUCTURAL ceiling is 800, NOT 1023.

🛑 **THE 427 LANE MUST BE READ SIGNED.**  `sign = b7 ? -1 : +1`;  `gp-0x6b94 = sign * code * 12.8`.
   Feeding this lane RECTIFIED into a band statistic understated 6-9 Hz RMS by 4.9x (r81) / 5.5x
   (r82).  `derive()` therefore emits the reconstructed SIGNED lane as `x6b94`.

🛑 **IDENTITY IS byte7[7:6] == 3 AND b3 == 1, ON THE FRAME.**  V100 emits code 2; V98/V99 emit
   code 2 with b3 duty 0.0000; V96/V97 emit code 1; <= V91 emit 0.  No prior build can produce
   code 3.  If it fails, NOTHING IN THE READOUT MAY BE REPORTED.

🛑 **PAIRING CONVENTION (asserted by `extract_r7d._row2raw14`):**
       t == raw14_t[1:]   and   probe == raw14_b4[1:]   and   probe == raw14_b4[row2raw14]
   ⇒ **SAFE PAIRS: (t, probe) or (raw14_t, raw14_b4).**  Every V101 bit column emitted by
   `derive()` (`v101_b7` .. `v101_b3`) is decoded from `probe`, i.e. lives on the `t` row grid and
   is SAFE to pair with `t`, `cs_ang`, `cc_lat`, ...

INSTRUMENT FACTS honoured here (identical to `decode/extract_r85.py`):
  * `carState.yawRate` is identically zero on this car -- `lp_yaw` taps
    `livePose.angularVelocityDevice.z` (rad/s, z-DOWN => NEGATIVE on a LEFT turn) instead.
  * `vEgo` is invalid as a speed reference at angle (+7.9 % fast at 250-400 deg).  Use `v_rear` =
    (ws_rl + ws_rr)/2 in km/h for kinematics.

🛑 **OPERATOR-CONFIRMED SIGN CONVENTION, 2026-08-13.**  NEGATIVE driver torque AND NEGATIVE steering
   angle = a RIGHT turn.  +LKAS demands NEGATIVE angle; +driver torque demands POSITIVE angle => a
   positive LKAS command and a positive driver torque push the wheel OPPOSITE ways.  **This
   extractor applies NO sign flip and NO offset removal** -- channels are emitted in their native
   frames so a scorer applies the convention once, deliberately, rather than twice or never.

Usage:
    python decode/extract_r95.py                 # extract + derive + identity + lane427 + health + census
    python decode/extract_r95.py extract 95
    python decode/extract_r95.py derive 95
    python decode/extract_r95.py identity 95
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

ROUTE = "95"
PREFIX = "75604b0a432fdc89_00000095--6d7c6deef5"
SEGMENTS_ON_DISK = (0, 1, 2, 3, 4)
NSEG_SCAN = 5

NEW = {
    ROUTE: (PREFIX, NSEG_SCAN, "analysis-2020accord/_scratch/cache/r95", "r95s", "r95", "V101"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v
D.ROUTES.setdefault("85", ("75604b0a432fdc89_00000085--cad692c3d3", 21,
                           "analysis-2020accord/_scratch/cache/r85", "r85s", "r85", "V100"))
D.ROUTES.setdefault("82", ("75604b0a432fdc89_00000082--e30d55731b", 2,
                           "analysis-2020accord/_scratch/cache/r82", "r82s", "r82", "V99"))

# ---- V101's 427 spec: packer AND source both carried from V100, untouched.
X.WIRE_SCALE[ROUTE] = 64.0 / 5.0
X.WIRE_SOURCE[ROUTE] = ("gp-0x6b94 (AGGREGATOR OUTPUT), sar 6  [carried from V100; packer is "
                        "V96..V100's, UNTOUCHED]")

# ---- V101's byte-4 map, read off `builds/v80_v107/build_v101_tva.py`'s PAYLOAD, not inferred.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES[ROUTE] = {
    "b7_sign_6b94_neg": M_B7,          # gp-0x6b94 < 0            -- the 427 SIGN
    "b6_LKAS_CLAMP_ge4096": M_B6,      # |gp-0x6b4c| >= 4096      -- the 8x command ceiling
    "b5_sign_6b4c_neg": M_B5,          # gp-0x6b4c < 0            -- the LKAS command SIGN
    "b4_sign_6ad6_neg": M_B4,          # gp-0x6ad6 < 0            -- PID reference sign
    "b3_IDENTITY_const1": M_B3,        # unconditional 1
}

IDENT_MASK, IDENT_CODE3 = 0xC0, 0xC0   # byte7[7:6] == 3  =>  byte7 & 0xC0 == 0xC0
WIRE_SAT_FIELD = 1023                  # the 10-bit CAN field
WIRE_SAT_STRUCT = 800                  # (10240*5)>>6 -- gp-0x6b94's own writer clamp, THE REAL ONE
COUNTS_PER_LSB = 64.0 / 5.0            # 12.8
LKAS_CLAMP = 4096                      # cal 0xC61B2/0xC61B4 -- the value RUNG b6 tests

DERIVED = ["v101_b7", "v101_b6", "v101_b5", "v101_b4", "v101_b3",
           "mag427", "sgn427", "x6b94", "v_rear", "lp_yaw"]


# ======================================================================================
#  MISSING-SEGMENT GUARD + a livePose tap.  Both pass-through, verbatim from extract_r85.
# ======================================================================================
_TAPPED_READ = rlog_parse.read_messages      # extract_r7d's tapped reader (already installed)
MISSING_SEGMENTS = []
LP = {"t": [], "z": []}


def _read_guarded(path):
    """Yield nothing for an absent segment; otherwise pass through and tap livePose."""
    p = Path(path)
    if not p.exists():
        MISSING_SEGMENTS.append(p.name)
        print(f"  ⚠ segment file ABSENT, skipped: {p.name}", flush=True)
        return
    for evt in _TAPPED_READ(path):
        try:
            if evt.which() == "livePose":
                LP["t"].append(evt.logMonoTime * 1e-9)
                LP["z"].append(float(evt.livePose.angularVelocityDevice.z))
        except Exception:
            pass
        yield evt


rlog_parse.read_messages = _read_guarded


# ======================================================================================
#  EXTRACT
# ======================================================================================
def extract_route(route=ROUTE):
    MISSING_SEGMENTS.clear()
    LP["t"].clear()
    LP["z"].clear()
    rep = X.extract_route(route)
    rep["segments_on_disk"] = list(SEGMENTS_ON_DISK)
    rep["segments_absent"] = list(MISSING_SEGMENTS)
    rep["livePose_samples"] = len(LP["t"])
    print(f"\n  segments absent from disk: {len(MISSING_SEGMENTS)}   "
          f"livePose samples: {len(LP['t']):,}")
    return rep


# ======================================================================================
#  DERIVE
# ======================================================================================
def derive(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / f"{stem}.npz"
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the pairing contract is broken"
    z["v101_b7"] = ((p & M_B7) != 0).astype(float)
    z["v101_b6"] = ((p & M_B6) != 0).astype(float)
    z["v101_b5"] = ((p & M_B5) != 0).astype(float)
    z["v101_b4"] = ((p & M_B4) != 0).astype(float)
    z["v101_b3"] = ((p & M_B3) != 0).astype(float)

    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    sgn = np.where(z["v101_b7"] > 0.5, -1.0, 1.0)
    z["mag427"] = mag
    z["sgn427"] = sgn
    z["x6b94"] = sgn * mag * COUNTS_PER_LSB             # ⭐ THE SIGNED AGGREGATOR LANE, in counts

    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    z["v_rear"] = 0.5 * (rl + rr)                       # km/h

    if len(LP["t"]) > 1:
        t0 = float(z["t0_mono"][0])
        lt = np.array(LP["t"], float) - t0
        o = np.argsort(lt)
        z["lp_yaw"] = np.interp(t, lt[o], np.array(LP["z"], float)[o])
    elif "lp_yaw" in z:
        pass
    else:
        z["lp_yaw"] = np.full(n, np.nan)

    np.savez_compressed(f, **z)

    for k in DERIVED:
        if k not in D.PASS_1D:
            D.PASS_1D.append(k)
    D.split(route)

    print(f"\n  === DERIVED COLUMNS, route {route} ===")
    print(f"    v101_b7..b3 decoded from `probe` ({n:,} rows, SAFE pairing with `t`)")
    print(f"    mag427  nonzero {100*np.mean(mag > 0):.2f} %  distinct {len(np.unique(mag))}  "
          f"max {mag.max():.0f}   sat@1023 {100*np.mean(mag >= 1023):.4f} %  "
          f"sat@800(structural) {100*np.mean(mag >= 800):.4f} %")
    print(f"    x6b94   signed counts: p1 {np.percentile(z['x6b94'],1):.0f}  "
          f"p50 {np.percentile(z['x6b94'],50):.0f}  p99 {np.percentile(z['x6b94'],99):.0f}  "
          f"|.|max {np.abs(z['x6b94']).max():.0f}")
    print(f"    v_rear  median {np.nanmedian(z['v_rear']):.2f} km/h   "
          f"lp_yaw finite {100*np.mean(np.isfinite(z['lp_yaw'])):.1f} %")
    return z


# ======================================================================================
#  IDENTITY -- V101's PRE-REGISTERED RULE: byte7[7:6] == 3 AND b3 == 1, ON THE FRAME.
# ======================================================================================
def identity(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    duty3 = float((code == 3).mean())
    b3 = (b4 & M_B3) != 0
    b3_duty = float(b3.mean())
    joint = float(((code == 3) & b3).mean())
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)

    ok_b7 = duty3 >= 0.9999
    ok_b3 = b3_duty >= 0.9999
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code3_duty=duty3, byte7_code3_frames=int((code == 3).sum()),
               b3_duty=b3_duty, b3_zero_frames=int((~b3).sum()),
               joint_byte7eq3_and_b3_duty=joint,
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               byte4_field_odd_frac=float(((field & 1) == 1).mean()),
               pre_registered_rule="byte7[7:6] == 3 AND b3 == 1, on the frame",
               ok_byte7=bool(ok_b7), ok_b3=bool(ok_b3),
               identity_pass=bool(ok_b7 and ok_b3))

    print(f"\n  === IDENTITY, route {route} (expected {lab}): {n:,} 0x14A frames ===")
    print("    byte7[7:6] code histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(cu, cc)))
    print(f"    ⭐ byte7[7:6] == 3 duty = {duty3:.6f}  ({out['byte7_code3_frames']:,} frames)"
          f"  -- code 3 is NEW at V101; no prior build can emit it")
    print(f"    ⭐ b3 duty = {b3_duty:.6f}   ({out['b3_zero_frames']:,} frames with b3 == 0)")
    print(f"    ⭐ JOINT (byte7[7:6]==3 AND b3==1) duty = {joint:.6f}  <- the single-frame rule")
    print("    byte4 field = (byte4>>3)&0x1F histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(fu, fc)))
    print(f"    field ODD on {100*out['byte4_field_odd_frac']:.4f} % of frames (V101 => 100 %)")

    if out["identity_pass"]:
        out["verdict"] = ("✅ V101 IS ON THE CAR -- byte7[7:6] == 3 AND b3 == 1 on a single frame. "
                          "Code 3 is introduced by V101; V98/V99/V100 emit 2, V96/V97 emit 1, "
                          "<= V91 emit 0.")
    elif not ok_b7:
        out["verdict"] = (f"🛑 IDENTITY FAILS -- byte7[7:6] == 3 duty {duty3:.6f} < 1.0000. "
                          f"NOTHING IN THE READOUT MAY BE REPORTED.")
    else:
        out["verdict"] = (f"🛑 IDENTITY FAILS -- b3 duty {b3_duty:.6f} < 1.0000.  b3 is an "
                          f"UNCONDITIONAL constant on V101.  NOTHING MAY BE REPORTED.")
    print(f"    VERDICT: {out['verdict']}")
    (ROOT / cdir / f"{stem}_identity.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  427 LANE HEALTH -- a saturating lane is a DEAD INSTRUMENT.  Structural ceiling is 800.
# ======================================================================================
def lane427(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    mt = np.asarray(z["ab_mt"], int)
    n = len(mt)
    q = {p: float(np.percentile(mt, p)) for p in (50, 90, 99)}
    out = dict(route=route, build=lab, frames=int(n),
               source=X.WIRE_SOURCE[route], counts_per_lsb=COUNTS_PER_LSB,
               nonzero_frac=float(np.mean(mt > 0)), distinct=int(len(np.unique(mt))),
               p50=q[50], p90=q[90], p99=q[99], max=int(mt.max()),
               sat_field_1023_frac=float(np.mean(mt >= WIRE_SAT_FIELD)),
               sat_struct_800_frac=float(np.mean(mt >= WIRE_SAT_STRUCT)),
               above_struct_ceiling_n=int(np.sum(mt > WIRE_SAT_STRUCT)))
    for k in ("p50", "p90", "p99", "max"):
        out[k + "_counts"] = out[k] * COUNTS_PER_LSB
    print(f"\n  === CAN 427 LANE HEALTH, route {route} ({lab}) ===")
    print(f"    source: {out['source']}")
    print(f"    {n:,} frames  nonzero {100*out['nonzero_frac']:.2f} %  distinct codes "
          f"{out['distinct']}")
    print(f"    code   p50 {out['p50']:.0f}  p90 {out['p90']:.0f}  p99 {out['p99']:.0f}  "
          f"max {out['max']}")
    print(f"    counts p50 {out['p50_counts']:.0f}  p90 {out['p90_counts']:.0f}  "
          f"p99 {out['p99_counts']:.0f}  max {out['max_counts']:.0f}")
    print(f"    saturation @1023 (CAN field)      : {100*out['sat_field_1023_frac']:.4f} %")
    print(f"    saturation @800  (STRUCTURAL, the writer clamp +-10240): "
          f"{100*out['sat_struct_800_frac']:.4f} %")
    if out["above_struct_ceiling_n"]:
        print(f"    🛑 {out['above_struct_ceiling_n']:,} frames ABOVE the structural ceiling 800 -- "
              f"impossible if 427 really carries gp-0x6b94.  INDICTS THE REPOINT.")
    if out["sat_struct_800_frac"] > 0.001:
        print("    🛑🛑 THE LANE SATURATES AT ITS STRUCTURAL CEILING -- IT IS A DEAD INSTRUMENT ON "
              "THOSE FRAMES AND EVERY PERCENTILE ABOVE IT IS A LOWER BOUND.")
    (ROOT / cdir / f"{stem}_lane427.json").write_text(json.dumps(out, indent=1, default=float))
    return out


def health(route=ROUTE):
    return X.health(route)


def census(route=ROUTE):
    return X.census(route)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        extract_route(ROUTE)
        derive(ROUTE)
        identity(ROUTE)
        lane427(ROUTE)
        health(ROUTE)
        census(ROUTE)
    else:
        fn = {"extract": extract_route, "derive": derive, "identity": identity,
              "lane427": lane427, "health": health, "census": census}[args[0]]
        for r in (args[1:] or [ROUTE]):
            fn(r)
