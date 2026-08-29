#!/usr/bin/env python3
r"""
V168 -- THE BASE-ASSIST SLOPE CAP.  Base = V158.  ONE cal cell: 0xC6384  2048 -> 1536.
        The first build in this kit's history to touch the largest torque-fed loop-gain term.

WHY THIS BUILD EXISTS -- A LEVER CLASS THE KIT HAS NEVER TRIED
---------------------------------------------------------------
The arc since V38: V38-V52 authority/filters/poles/caves - V53-V61 telemetry probes and lane mutes -
V62-V73 the rate lane (r24/r26) - V74-V83a the base-assist damper - V84 damper reverted to Honda -
V85-V122 friction/knee/alpha2 and the Coulomb relay - V133-V167 the damper's shape and Path-2 weight.
EVERY ONE of those is a lever on a term that is NOT the dominant one.

`gp-0x6b86`, the base power-assist map (`FUN_000352b4`), is the LARGEST torque-fed term in the
aggregator: window +/-0x3000, the widest of all eleven slots, and 5.8-7.8x the ENTIRE PID at 7.79 Hz.
Its per-segment slope is hard-capped at cal `0xC6384` = 2048 Q10 = 2.000x.

    ** 0xC6384 IS BYTE-IDENTICAL ON ALL 161 IMAGES.  IT HAS NEVER BEEN MOVED. **

That is not a coincidence of neglect -- it is exactly the profile the measurement demands.

WHAT THE MEASUREMENT SAYS (this session, validated estimator, slope-matched nulls)
----------------------------------------------------------------------------------
  * the ratchet is FIRMWARE-CREATED: engaged arm clears its null 7/7 routes, manual arm 0/7,
    speed-matched ratio median 19.9x [4.82, 35.64].  It is not a mechanical mode being amplified.
  * it is in TORQUE, not angle: margins tq 7.62 / cs_tq 7.42 / ws 3.9-4.4 / cs_rate 1.03 (chance) /
    angle 0.79-0.83 / command 0.56-0.67.  Every prior 6-9 Hz endpoint read the WRONG CHANNEL.
  * THIRTY-PLUS BUILDS HAVE NOT MOVED IT: post-V102 rho -0.14 (p 0.787) against a floor that would
    have shown 1.9x, frequency pinned at 8.64 Hz +/- 7.4 % across V91->V122.
  * meanwhile the GRIND falls monotonically post-V102, rho -0.94 (p 0.005) in three channels.
    => grind and ratchet are DISSOCIATED, and every lever found so far is the GRIND's.
  * the Coulomb relay is EXONERATED for the ratchet: its knee spans 10x (300-3000) with rho -0.06
    (p 0.874); gain-matched, knee 300->1800/3000 cuts the grind 2.8x and moves the ratchet 1.18x,
    inside its own 1.63x split-half floor.

THE CAP BINDS -- IT IS NOT AN INERT CEILING
--------------------------------------------
The 10-knot curve is initialised data copied ROM->RAM at boot (hence only 3 st.h target the 20-knot
block, and 2 of those are `st.h r0` clears).  Found in the image by the shape the decompile requires:

    0xCE47A   X   0   25   60  100  150  250  450  900 1800 4150
              Y   0  154  338  460  549  635  702  766  824  857
              slope  6.16 5.26 3.05 1.78 0.86 0.34 0.14 0.06 0.01   -> cap BINDS 3/9 over X 0-100
    0xCF372   max slope 16.37 -> binds 4/9 over X 0-450
    0xCF3CA   max slope 11.97 -> binds 3/9 over X 0-150
    (+ 0xCE4A6 / 0xCF39E / 0xCF3F6 duplicates -- the mode-selected pointer-table family)

All six records are byte-identical across the 161 images.  The cap therefore pins the map's
SMALL-SIGNAL GAIN at exactly 2.000 over the low-torque region -- the CEILING value of `s` in the loop
census.  The loop's largest single term sits permanently at its maximum.

GATE 2 -- ANCHORED ON THE MEASURED Q RATIO, NOT A CENSUS PHASE
---------------------------------------------------------------
The census's L phase (-148 deg) with P real-positive gives |1-P.L| = 1.92 > 1, i.e. a loop that ADDS
damping -- which contradicts the measured 93 % cancellation.  P's phase is explicitly "not in the
image" and the SIGN of the result depends on it, so anchor on the measurement:

    Q_eff/Q_passive = 40/2.8 = 14.3  =>  |1-P.L| = 0.0700  =>  P.L = 0.9300 at stock
    [ASSUMPTION, stated] P.L real-positive at the peak -- what the measured ratio REQUIRES, and the
    standard form for a damping-cancelling loop.

    cap    s       |L|     |1-P.L|   Q ratio    vs stock
    2048   2.000   2.825   0.0700    14.29      stock
    1792   1.750   2.575   0.1523     6.57      2.2x more damped
 -> 1536   1.500   2.325   0.2346     4.26      3.4x MORE DAMPED   <- THIS BUILD
    1280   1.250   2.075   0.3169     3.16      4.5x
    1024   1.000   1.825   0.3992     2.50      5.7x

  MAGNITUDE passes.  PHASE passes: the map term is a REAL GAIN, so lowering the cap scales |L|
  WITHOUT rotating it; under the real-positive P.L the measurement requires, |1-P.L| can only move
  away from zero => monotonically more damped at every cap value, with NO value at which it reverses.

AND IT ACCOUNTS FOR THE ENGAGED-ONLY BEHAVIOUR
-----------------------------------------------
The map is always live and supplies s = 2.000 of L.  The rest (PID 0.2565, r24 0.049-0.293,
r26 0.098-1.17 live only while gp-0x6b5e==0, FUN_36682 0.0032) is engagement-conditional.  With P
calibrated from the ENGAGED arm ALONE, the manual arm is then PREDICTED, not fitted:

    ENGAGED  |L| 2.825   Q ratio 14.29   (measured)
    MANUAL   |L| 2.000   Q ratio  2.93   (PREDICTED)
    => predicted engaged/manual = 4.88   vs MEASURED 19.9 [4.82, 35.64]

  Consistent, at the LOWER EDGE of the measured CI.  [BELIEF -- the census's per-lane magnitudes
  carry their own assumptions and the manual arm's true L is not separately measured.]

WHY THIS DOES NOT COST LKAS AUTHORITY  [EVIDENCE]
--------------------------------------------------
The map's input is `clamp(gp-0x4f60, +/-cal(0xC6200)=8192) + gp-0x6b4a`, and gp-0x6b4a IS ZERO:

    cal 0xC616C = 0  =>  a clamp with limit 0 annihilates its input
                     =>  gp-0x6b76 in {0, 0x7FFF}, and 0x7FFF exceeds FUN_0003405a's own 20480 gate
                     =>  forced to 0  =>  gp-0x62e0[] == 0  =>  gp-0x6298[] == 0  =>  gp-0x6b4a == 0

  0xC616C is 0 in stock AND on all 161 images (asserted below).  So the map is fed by the DRIVER
  TORQUE SENSOR alone and this edit CANNOT touch the LKAS lane (gp-0x6b4c).

THE FEEL TRADE -- STATED PLAINLY BECAUSE IT CUTS AGAINST A STANDING OPERATOR CONSTRAINT
----------------------------------------------------------------------------------------
The cap binds over the LOW-torque segments, so lowering it means less assist per unit driver torque
near centre => HEAVIER STEERING THERE, in the regime the operator asked to keep light.  It is real.
It is narrower than the constraint's wording suggests, though:
  * the curve is UNCAPPED and unchanged above X ~ 450 => PEAK AUTHORITY AND MAX RATES ARE UNTOUCHED;
  * the map is driver-torque fed, not the LKAS lane (proved above) => LKAS effort is unchanged.
1536 (1.5x) is the SMALLEST step whose predicted effect (3.4x) clears the one-episode detection
margin.  Deliberately not the largest dose -- the feel cost should be met in the smallest useful
increment, and 1280/1024 remain available if 1536 reads clean but incomplete.

WHAT A NULL WILL LICENSE  (written BEFORE the cut, per the design law)
-----------------------------------------------------------------------
The drive scores ONE continuous 15 s engaged creep pass with rlog-tools/score/score_band_excess.py.
  * ratchet 5-12 Hz excess drops BELOW its slope-matched null  => the ratchet is gone in that regime,
    and the loop-gain account is confirmed.
  * excess unchanged (V122 reference ~33, null ~4)             => a 3.4x predicted damping increase
    produced no measurable change in the peak.  That FALSIFIES the real-positive P.L assumption, and
    with it the claim that this loop produces the 14.3x cancellation => the cause is OUTSIDE this
    loop, and the assist map is exonerated the way the Coulomb relay now is.
  * excess RISES                                               => lowering |L| sharpened the mode,
    which is only possible if P.L is NOT real-positive; revert and re-derive the phase.
Detection: a single 15 s episode detected the ratchet in 11/11 episodes at 5-65x margin, so all three
outcomes are readable from one pass.  There is no "uninterpretable" branch.

BASE = V158, so this build also carries V158's damper shape and scores the GRIND from the same
episode in a different band -- the two symptoms are separated by the INSTRUMENT, not by the build.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

# --- PATH BOOTSTRAP -------------------------------------------------------------------------
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V168_WRITE", "").strip().lower()

BASE_NAME = "_v158_V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE_plain_image.bin"
BASE_SHA = "42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf"

u16 = V106B.u16

# ---- THE EDIT ------------------------------------------------------------------------------
CAP_CAL = 0xC6384                 # base-assist per-segment slope cap, Q10
CAP_OLD, CAP_NEW = 2048, 1536     # 2.000x -> 1.500x

# ---- ASSERTED UNTOUCHED, because each one is load-bearing for the argument above -------------
INPUT_CLAMP, INPUT_CLAMP_VAL = 0xC6200, 8192     # the map's input clamp
TERM0_RELAY, TERM0_RELAY_VAL = 0xC616C, 0        # == 0 is what makes gp-0x6b4a identically zero
MANUAL_LAG, MANUAL_LAG_VAL = 0xC6382, 41         # the manual-arm lag coefficient
CURVE_RECORDS = (0xCE47A, 0xCE4A6, 0xCF372, 0xCF39E, 0xCF3CA, 0xCF3F6)
GAIN_CAL, GAIN_VAL = 0xC6CD0, 5346               # LKAS gain HELD at 6x

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def slopes(img, off):
    """Per-segment slope of a 10-knot record, as the firmware computes it."""
    X = [u16(img, off + 2 * k) for k in range(10)]
    Y = [u16(img, off + 20 + 2 * k) for k in range(10)]
    return X, Y, [(Y[j + 1] - Y[j]) / float(X[j + 1] - X[j]) for j in range(9)]


def build(cap_new=CAP_NEW, vnum=168, write_env="ACCORD_V168_WRITE"):
    """Build the slope-cap lever at `cap_new`.  V169/V170/V171 are the same edit at other
    doses and call straight into here -- one verified builder, four build numbers."""
    write_mode = os.environ.get(write_env, "").strip().lower()
    print("=" * 102)
    print(f"  V{vnum} -- BASE-ASSIST SLOPE CAP 0xC6384  {CAP_OLD} -> {cap_new}"
          f"  ({CAP_OLD/1024.0:.3f}x -> {cap_new/1024.0:.3f}x)   (base V158)")
    print("=" * 102)

    print("\n  [1] BASE")
    base_path = plain_image_path(BASE_NAME)
    base = bytearray(Path(base_path).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V158 ({BASE_SHA[:16]}...)")
    check(len(base) == 0x100000, "base image is 1 MiB")
    code = bytearray(base)

    print("\n  [2] THE CAP BINDS -- verified on the base image, not assumed")
    for off in CURVE_RECORDS:
        X, Y, sl = slopes(base, off)
        binds = [j for j, s in enumerate(sl) if s >= CAP_OLD / 1024.0]
        check(len(binds) >= 3,
              f"0x{off:05X} max slope {max(sl):5.2f} >= cap {CAP_OLD/1024.0:.3f} on "
              f"{len(binds)}/9 segments, over X {X[binds[0]]}-{X[binds[-1]+1]}")
    check(u16(base, CAP_CAL) == CAP_OLD,
          f"0x{CAP_CAL:05X} slope cap reads {CAP_OLD} on the V158 base")

    print("\n  [3] THE ARGUMENT'S LOAD-BEARING CELLS ARE UNTOUCHED ON THE BASE")
    for addr, val, why in ((INPUT_CLAMP, INPUT_CLAMP_VAL, "map input clamp"),
                           (TERM0_RELAY, TERM0_RELAY_VAL, "== 0 => gp-0x6b4a == 0 => no LKAS path"),
                           (MANUAL_LAG, MANUAL_LAG_VAL, "manual-arm lag coefficient"),
                           (GAIN_CAL, GAIN_VAL, "LKAS gain HELD at 6x")):
        check(u16(base, addr) == val, f"0x{addr:05X} = {val:<6d} {why}")

    print("\n  [4] THE EDIT")
    struct.pack_into("<H", code, CAP_CAL, cap_new)
    attributed = set(range(CAP_CAL, CAP_CAL + 2))
    check(u16(code, CAP_CAL) == cap_new,
          f"0x{CAP_CAL:05X} {CAP_OLD} -> {cap_new}  ({CAP_OLD/1024.0:.3f}x -> {cap_new/1024.0:.3f}x)")

    print("\n  [5] WHAT THE NEW CAP DOES TO EACH RECORD")
    for off in CURVE_RECORDS:
        X, Y, sl = slopes(code, off)
        nb = sum(1 for s in sl if s >= cap_new / 1024.0)
        ob = sum(1 for s in sl if s >= CAP_OLD / 1024.0)
        print(f"      0x{off:05X}  binds {ob}/9 -> {nb}/9   small-signal gain "
              f"{CAP_OLD/1024.0:.3f} -> {cap_new/1024.0:.3f}")
        check(nb >= ob, f"0x{off:05X} the lower cap binds on at least as many segments")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [7] FULL BYTE DIFF vs V158 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    # 2048 = 0x0800 -> 1536 = 0x0600 differs in the HIGH byte only, so LE gives ONE payload
    # byte, not two.  Asserting a hardcoded 2 here has bitten this kit before; assert the
    # VALUE instead, which cannot be fooled by how many bytes happened to change.
    n_expected = sum(1 for k in range(2)
                     if ((CAP_OLD >> (8 * k)) & 0xFF) != ((cap_new >> (8 * k)) & 0xFF))
    check(payload == n_expected,
          f"exactly {n_expected} payload byte(s) ({payload} found) -- the u16 slope cap, "
          f"0x{CAP_OLD:04X} -> 0x{cap_new:04X} (high byte only)")
    check(u16(code, CAP_CAL) == cap_new and u16(base, CAP_CAL) == CAP_OLD,
          f"value check: 0x{CAP_CAL:05X} reads {CAP_OLD} on base and {cap_new} on the build")

    print("\n  [8] THE CURVE RECORDS THEMSELVES ARE UNTOUCHED")
    for off in CURVE_RECORDS:
        check(bytes(code[off:off + 40]) == bytes(base[off:off + 40]),
              f"0x{off:05X} 40-byte curve record byte-identical to base")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, f"V{vnum} output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = f"V{vnum}-V158BASE-ASSIST.SLOPECAP.{CAP_OLD}.TO.{cap_new}"
    img_out = plain_image_path(f"_v{vnum}_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if write_mode == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set {write_env}=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if write_mode == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
