#!/usr/bin/env python3
r"""Extract route `85` -- THE V100 FLIGHT (the SATURATION INSTRUMENT) -- into
`analysis-2020accord/_scratch/cache/r85/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Like `decode/extract_r80.py` / `decode/extract_r81.py` / `decode/extract_r82.py`,
this file only adds a row to `decode_v84_probe_r6d.ROUTES` and calls `extract_r7d`'s
`extract_route()` -- the SAME code that wrote every cache since `_scratch/cache/r6d/`.  Field names,
ZOH/interp convention, sentinel definition and `PASS_1D` are bit-for-bit the ones every prior route
was scored with.  The 0x1AB full tap, the 0x14A byte-7 tap and the `row2raw14` off-by-one fix all
come along unchanged, including the elementwise byte-4 assertion that kills the run rather than
silently mispairing.

===================================================================================================
ROUTE 85 == V100.  V99 BASE + a CAVE SHRINK (154 B -> 132 B) + a 2-byte 427 REPOINT.  ZERO CAL BYTES.
===================================================================================================
    byte4 b7 0x80 = gp-0x6b94 < 0                        ⭐ THE SIGN FOR THE 427 MAGNITUDE LANE
    byte4 b6 0x40 = |gp-0x4f60 - gp-0x6ad6| >= 10240     RUNG D'  -- the PID ERROR clamp predicate
    byte4 b5 0x20 = |gp-0x6ad6| >= cal(0xC6200) = 8192   RUNG A   -- the PID REFERENCE clamp
    byte4 b4 0x10 = gp-0x6ad6 < 0                        sign / THE POSITIVE CONTROL
    byte4 b3 0x08 = 🛑 UNCONDITIONAL CONSTANT 1          ⭐ THE BUILD IDENTITY
    byte7[7:6]    = 2  (byte7 & 0xC0 == 0x80)            identity + liveness, carried from V98/V99

    427 (0x1AB) = clamp(|gp-0x6b94| * 5 >> 6, 0, 0x3FF)  -- packer UNCHANGED, SOURCE REPOINTED
                  => counts = wire * 64/5 = wire * 12.8
                  🛑 gp-0x6b94's OWN writer clamps it to +-10240 (0x3acf6 / 0x3ad0e), so the
                     maximum REACHABLE code is (10240*5)>>6 = 800 of 1023.  The STRUCTURAL ceiling
                     is 800, NOT 1023.  Both are reported.

🛑 **THE 427 LANE MUST BE READ SIGNED.**  `sign = b7 ? -1 : +1`; `gp-0x6b94 = sign * code * 12.8`.
   Feeding this lane RECTIFIED into a band statistic was measured to understate 6-9 Hz RMS by
   4.9x (r81) / 5.5x (r82).  This extractor therefore emits the reconstructed SIGNED lane as a
   first-class column (`x6b94`), so no downstream scorer has to re-derive it.

🛑 **THE ~50-BUILD "byte4[7:3] IS ALWAYS ODD" CONVENTION DOES NOT HOLD, AND NEITHER DOES V99's
   "byte4[7:3] IS ALWAYS EVEN".**  On V100 `b3` is a hard 1 (so the field is ODD on every frame)
   but b7/b6/b5/b4 are all measurands, so byte4 takes many values.  **Do not pull the build for
   that.**  Liveness is `byte7[7:6] == 2` AND `b3 == 1`.

🛑 **SEGMENT 17 IS ABSENT FROM DISK.**  The route on disk is segments 15, 16, 18, 19, 20.  The
   upstream extractor enumerates `range(nseg)`, so this file installs a MISSING-FILE GUARD that
   yields an empty stream for a segment that is not present.  The consequence is deliberate and
   good: the `seg` column carries the TRUE segment number (15/16/18/19/20), and the per-segment
   caches are `r85s15.npz` .. `r85s20.npz`.
   ⚠ The whole-route `t` axis therefore contains a ~60 s HOLE between seg 16 and seg 18.  Any
   `np.gradient` over the whole-route arrays is WRONG at that seam.  Per-segment files (`r85s*.npz`)
   have no seam and are the correct unit for any rate/spectral work.  `duration_s` in the census
   spans the hole; `covered_s` (sum of per-segment durations) does not.

🛑 **PAIRING CONVENTION PRODUCED BY THIS EXTRACTOR (asserted by `extract_r7d._row2raw14`):**
       t == raw14_t[1:]   and   probe == raw14_b4[1:]   and   probe == raw14_b4[row2raw14]
   ⇒ **SAFE PAIRS: (t, probe) or (raw14_t, raw14_b4).**  Pairing `t` with `raw14_b4` reads the
   cave byte ~10 ms early = 28 deg of phase at 7.79 Hz.
   Every V100 bit column emitted by `derive()` (`v100_b7` .. `v100_b3`) is decoded from `probe`,
   i.e. it lives on the `t` row grid and is SAFE to pair with `t`, `cs_ang`, `cc_lat`, ...

INSTRUMENT FACTS honoured here:
  * `carState.yawRate` is identically zero on this car.  This extractor taps
    `livePose.angularVelocityDevice.z` instead and emits it as `lp_yaw` (rad/s, z-DOWN ⇒ NEGATIVE
    on a LEFT turn).  `cs_yaw` is still emitted by the upstream extractor and is still zero -- it
    is kept only so the schema does not change.  **Do not use `cs_yaw`.**
  * `vEgo` is invalid as a speed reference at angle (+7.9 % fast at 250-400 deg).  This extractor
    emits `v_rear` = (ws_rl + ws_rr)/2 in km/h.  **Use `v_rear`, not `cs_v`, for kinematics.**

🛑 **OPERATOR-CONFIRMED SIGN CONVENTION, 2026-08-13.**  NEGATIVE driver torque AND NEGATIVE steering
   angle = a RIGHT turn.  +LKAS demands NEGATIVE angle; +driver torque demands POSITIVE angle ⇒ a
   positive LKAS command and a positive driver torque push the wheel OPPOSITE ways.  Any analysis
   mixing the two channels without a sign flip measures the negative of what it thinks.  The
   angle-sensor zero is offset slightly LEFT (measured centre offset -4.25 deg; openpilot's learned
   -4.78 deg).  **This extractor applies NO sign flip and NO offset removal** -- it emits the
   channels in their native frames, exactly as every prior cache does, and the convention is stated
   here so a scorer applies it once, deliberately, rather than twice or never.

Usage:
    python decode/extract_r85.py                 # extract + derive + identity + health + census
    python decode/extract_r85.py extract 85
    python decode/extract_r85.py derive 85
    python decode/extract_r85.py identity 85
    python decode/extract_r85.py health 85
    python decode/extract_r85.py census 85
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

ROUTE = "85"
PREFIX = "75604b0a432fdc89_00000085--cad692c3d3"
SEGMENTS_ON_DISK = (15, 16, 18, 19, 20)
NSEG_SCAN = 21                      # enumerate 0..20 so `seg` == the TRUE segment number

NEW = {
    ROUTE: (PREFIX, NSEG_SCAN, "analysis-2020accord/_scratch/cache/r85", "r85s", "r85", "V100"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v
D.ROUTES.setdefault("82", ("75604b0a432fdc89_00000082--e30d55731b", 2,
                           "analysis-2020accord/_scratch/cache/r82", "r82s", "r82", "V99"))
D.ROUTES.setdefault("81", ("75604b0a432fdc89_00000081--c7103d2cb4", 3,
                           "analysis-2020accord/_scratch/cache/r81", "r81s", "r81", "V98"))

# ---- V100's 427 spec: packer UNCHANGED (`sar 6`), SOURCE repointed to the aggregator output.
X.WIRE_SCALE[ROUTE] = 64.0 / 5.0
X.WIRE_SOURCE[ROUTE] = ("gp-0x6b94 (AGGREGATOR OUTPUT), sar 6  [V100 REPOINT; packer is "
                        "V96/V97/V98/V99's, UNTOUCHED]")
X.WIRE_SCALE.setdefault("82", 64.0 / 5.0)
X.WIRE_SOURCE.setdefault("82", "gp-0x6b70 (PID reference lane), sar 6")

# ---- V100's byte-4 map, read off `builds/v80_v107/build_v100_tva.py`'s PAYLOAD, not inferred.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES[ROUTE] = {
    "b7_sign_6b94_neg": M_B7,          # gp-0x6b94 < 0            -- the 427 SIGN
    "b6_RUNG_Dp_errclamp": M_B6,       # |gp-0x4f60 - gp-0x6ad6| >= 10240
    "b5_RUNG_A_refclamp": M_B5,        # |gp-0x6ad6| >= cal(0xC6200) = 8192
    "b4_sign_6ad6_neg": M_B4,          # gp-0x6ad6 < 0            -- the POSITIVE CONTROL
    "b3_IDENTITY_const1": M_B3,        # unconditional 1
}

IDENT_MASK, IDENT_CODE2 = 0xC0, 0x80   # byte7[7:6] == 2  ⇒  byte7 & 0xC0 == 0x80
WIRE_SAT_FIELD = 1023                  # the 10-bit CAN field
WIRE_SAT_STRUCT = 800                  # (10240*5)>>6 -- gp-0x6b94's own writer clamp, THE REAL ONE
COUNTS_PER_LSB = 64.0 / 5.0            # 12.8
REF_CLAMP = 8192                       # cal 0xC6200
ERR_CLAMP = 10240                      # 0x2800, an immediate

# columns `derive()` adds; appended to the upstream PASS_1D so `split()` carries them per segment
DERIVED = ["v100_b7", "v100_b6", "v100_b5", "v100_b4", "v100_b3",
           "mag427", "sgn427", "x6b94", "v_rear", "lp_yaw"]


# ======================================================================================
#  MISSING-SEGMENT GUARD + a livePose tap.  Both are pass-through: the upstream event
#  stream is unchanged, so the extractor cannot tell the difference.
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
    print(f"\n  segments absent from disk: {len(MISSING_SEGMENTS)} "
          f"(expected 16: 0-14 and 17)   livePose samples: {len(LP['t']):,}")
    return rep


# ======================================================================================
#  DERIVE -- the V100 bit columns, the SIGNED 427 lane, rear-axle speed, livePose yaw.
#  Written back into the whole-route npz, then `split()` is re-run so the per-segment
#  caches carry them too.
# ======================================================================================
def derive(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / f"{stem}.npz"
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    # ---- the five cave bits.  🛑 decoded from `probe`, which is the SAFE partner of `t`.
    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the pairing contract is broken"
    z["v100_b7"] = ((p & M_B7) != 0).astype(float)
    z["v100_b6"] = ((p & M_B6) != 0).astype(float)
    z["v100_b5"] = ((p & M_B5) != 0).astype(float)
    z["v100_b4"] = ((p & M_B4) != 0).astype(float)
    z["v100_b3"] = ((p & M_B3) != 0).astype(float)

    # ---- CAN 427 magnitude, ZOH onto the row grid, then RE-SIGNED with b7.
    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    sgn = np.where(z["v100_b7"] > 0.5, -1.0, 1.0)
    z["mag427"] = mag                                   # raw 10-bit code, ZOH
    z["sgn427"] = sgn                                   # +1 / -1 from byte4 b7
    z["x6b94"] = sgn * mag * COUNTS_PER_LSB             # ⭐ THE SIGNED LANE, in counts

    # ---- rear-axle speed (vEgo is invalid at angle)
    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    z["v_rear"] = 0.5 * (rl + rr)                       # km/h

    # ---- livePose yaw rate (carState.yawRate is identically zero on this car)
    if len(LP["t"]) > 1:
        t0 = float(z["t0_mono"][0])
        lt = np.array(LP["t"], float) - t0
        o = np.argsort(lt)
        z["lp_yaw"] = np.interp(t, lt[o], np.array(LP["z"], float)[o])
    elif "lp_yaw" in z:
        pass                                             # keep what a previous run produced
    else:
        z["lp_yaw"] = np.full(n, np.nan)

    np.savez_compressed(f, **z)

    for k in DERIVED:
        if k not in D.PASS_1D:
            D.PASS_1D.append(k)
    D.split(route)

    print(f"\n  === DERIVED COLUMNS, route {route} ===")
    print(f"    v100_b7..b3 decoded from `probe` ({n:,} rows, SAFE pairing with `t`)")
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
#  IDENTITY -- V100's PRE-REGISTERED RULE: byte7[7:6] == 2 AND b3 == 1, ON THE FRAME.
#  "IF IT FAILS, NOTHING IN THE READOUT MAY BE REPORTED."  (builds/v80_v107/build_v100_tva.py)
# ======================================================================================
def identity(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    duty2 = float((code == 2).mean())
    b3 = (b4 & M_B3) != 0
    b3_duty = float(b3.mean())
    joint = float(((code == 2) & b3).mean())
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)

    ok_b7 = duty2 >= 0.9999
    ok_b3 = b3_duty >= 0.9999
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code2_duty=duty2, byte7_code2_frames=int((code == 2).sum()),
               b3_duty=b3_duty, b3_zero_frames=int((~b3).sum()),
               joint_byte7eq2_and_b3_duty=joint,
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               byte4_field_odd_frac=float(((field & 1) == 1).mean()),
               pre_registered_rule="byte7[7:6] == 2 AND b3 == 1, on the frame",
               ok_byte7=bool(ok_b7), ok_b3=bool(ok_b3),
               identity_pass=bool(ok_b7 and ok_b3))

    print(f"\n  === IDENTITY, route {route} (expected {lab}): {n:,} 0x14A frames ===")
    print("    byte7[7:6] code histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(cu, cc)))
    print(f"    byte7[7:6] == 2 duty = {duty2:.6f}  ({out['byte7_code2_frames']:,} frames)")
    print(f"    ⭐ b3 duty = {b3_duty:.6f}   ({out['b3_zero_frames']:,} frames with b3 == 0)"
          f"   -- V100 hard-wires 1; V98/V99 measured 0.0000 (gp-0x6752 const NEGATIVE)")
    print(f"    ⭐ JOINT (byte7[7:6]==2 AND b3==1) duty = {joint:.6f}  <- the single-frame rule")
    print("    byte4 field = (byte4>>3)&0x1F histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(fu, fc)))
    print(f"    field ODD on {100*out['byte4_field_odd_frac']:.4f} % of frames "
          f"(V100 => 100 %; V98/V99 => 0 %).  🛑 byte4 taking many values is EXPECTED: "
          f"b7/b6/b5/b4 are all measurands.")

    if out["identity_pass"]:
        out["verdict"] = ("✅ V100 IS ON THE CAR -- byte7[7:6] == 2 AND b3 == 1 on a single frame. "
                          "V98/V99 emit byte7==2 but MEASURED b3 duty 0.0000 over ~30,000 frames on "
                          "two routes, so neither has ever produced this frame.  Builds <= V97 "
                          "cannot produce byte7[7:6] == 2 at all (V96/V97 hard-wire 1; <= V91 give "
                          "0).")
    elif not ok_b7:
        out["verdict"] = (f"🛑 IDENTITY FAILS -- byte7[7:6] == 2 duty {duty2:.6f} < 1.0000. "
                          f"NOTHING IN THE READOUT MAY BE REPORTED.")
    else:
        out["verdict"] = (f"🛑 IDENTITY FAILS -- b3 duty {b3_duty:.6f} < 1.0000.  b3 is an "
                          f"UNCONDITIONAL constant on V100; anything less says this is not V100's "
                          f"cave.  NOTHING IN THE READOUT MAY BE REPORTED.")
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
