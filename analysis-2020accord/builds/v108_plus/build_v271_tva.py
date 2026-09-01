# -*- coding: utf-8 -*-
r"""V270 -- ENABLE THE LKAS-PATH INTEGRAL TERM.  ONE CALIBRATION HALFWORD.

    0xC63E6   Ki   0 -> 5      the integral gain of the PID in the LKAS COMMAND path

\U0001f6d1 **I TOLD THE OPERATOR "THERE IS NO PID ON THE LKAS OUTPUT; THE PATH IS FEEDFORWARD."
THAT WAS WRONG.**  An independent contributor who worked this firmware ~4 years ago pointed at it; the
decompile of `FUN_00028ea6`'s tail confirms him exactly:

    if ((uVar18 != 0 || cVar15 == 1) && bVar3) {
        if (gp-0x680a == 1) { iVar34 = 0; }              <- explicit RESET path
    } else {
        iVar26 = (cal(0xC61BA) << 10) >> 3;              <- ANTI-WINDUP clamp
        iVar34 = (gp-0x6dd0 >> 3) + ((err * cal(0xC63E6)) >> 3);   <- INTEGRATE
        ... clamped to +-iVar26 ...
    }
    gp-0x6dd0 = iVar34;                                  <- store, unconditional

The error feeding it is deadbanded against `cal(0xC62E4) = 4`.  **Honda shipped the complete
controller -- reset path, anti-windup clamp, deadband -- and disabled it with a ZERO GAIN.**

⚠ **AND IT WAS IN MY OWN ZERO-CAL CENSUS AND I WALKED PAST IT.**  `analysis-2020accord/verify/
zero_cal_census.py` listed `0xC63E6` among the 89 zero-valued cals with a torque-path reader (site
`0x2AC8E`).  I adjudicated two of the 89 and moved on.  This was one of the other 87.

WHY THIS IS THE RIGHT LEVER FOR WHAT THE OPERATOR ACTUALLY ASKED FOR:
  * **LKAS authority** -- an integral term removes STEADY-STATE ERROR, so the same command produces
    the torque it asked for instead of settling short.  That is more effective authority WITHOUT
    raising the proportional gain.
  * **peak command oscillation** -- if the loop is railing because it is winding up against a
    persistent offset, the integral removes the offset and the rail duty falls.
  * **and it does NOT raise Kp**, which is the term that tracks the 21 Hz mode (rho -0.819 across 16
    flown builds).  Every previous authority lever this kit tried went through the gain or the clamp.
    This one does not.

⭐ **INDEPENDENT ON-CAR EVIDENCE, WHICH THIS KIT HAS FOR NOTHING ELSE ON THE SHELF.**  an independent contributor
ran exactly this change on this platform: *"I was able to change the integral from 0 gain to nonzero
and get rid of steady state error and get more torque without heavy oscillation... its a game
changer."*  He left Kp and Kd at stock and set Ki from **0 to 5** -- the value this build uses.

\U0001f6d1 WHAT I HAVE NOT RESOLVED, STATED PLAINLY.  Read literally the update is
`acc = acc/8 + err*Ki/8`, which is a LEAKY integrator with DC gain `Ki/7` -- self-limiting, and the
+-1,310,720 clamp would never bind.  Read as a scaled accumulator (the `>>3` being how the 32-bit
state is kept) it is a TRUE integrator and the clamp is what bounds it.  **I cannot separate those two
readings from the decompile, and they differ in how hard Ki=5 pushes.**  What makes Ki=5 defensible
anyway is that it is not my number -- it is the value someone drove on this car's firmware.

\U0001f6d1 AND THE LESSON FROM V255/V269 IS APPLIED HERE.  Those doubled the rate lane and were
UNDRIVEABLE -- massive vibration while parked and DISENGAGED, continuing for seconds after the wheel
stopped.  My GATE 2 claim for them, *"Kd is a DAMPING term; it adds phase lead and moves no pole into
the right half plane"*, was **false**: in a loop with delay, derivative gain amplifies exactly where
the phase is already near -180 deg, and what the operator felt was a limit cycle.  **This build adds
INTEGRAL, not derivative.**  Integral action adds phase LAG at low frequency and rolls off as 1/f, so
it cannot excite a 21 Hz mode the way a derivative can -- the opposite failure mode to V255's.

⊕ **SINGLE VARIABLE, AND ON THE BASE THE OPERATOR IS KNOWN TO TOLERATE.**  Base is V112 -- the
configuration he has been driving.  Two payload bytes.  No code byte moves; the `sar` immediates,
forward gain, both clamps, all three live rate-lane arms, both pump families and every damper record
are asserted STOCK, so nothing from the failed V255/V269 line is present.

WHAT EACH OUTCOME LICENSES:
  * more torque / less steady-state lag, no new vibration  => the integral is the authority lever this
    kit never had, and Ki can be trimmed up or down from 5.
  * no change                                              => either the leaky reading is right and
    Ki/7 is too small, or the branch that integrates is not entered in normal driving. Try Ki higher
    before concluding anything.
  * oscillation or wind-up surge on engage                  => the reset path does not cover the case
    that matters; revert and drop Ki to 2.

BASE: V112.  Two bytes.
"""
import hashlib
import os
import struct
import sys
import math
import zlib
from pathlib import Path

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
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V271_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("fa15f3bffaed6b3f25d9fcbf16d7693f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 5244        # V88's bracketed optimum -- CARRIED, asserted
RESID_SCALE_VAL = 1024                      # CARRIED, asserted
SLOPE_CAP, CAP_STOCK = 0xC6384, 2048        # V236's lever -- NOT touched here, asserted
BQ = 0xC60A8                                # a1, a2, b1, c4 -- four float32, direct form II
CLAMP_P, CLAMP_N = 0xC61B2, 0xC61B4         # forward clamps -- tracking BROKEN deliberately
CLAMP_OLD, CLAMP_NEW = 3072, 4096           # the ceiling that peak torque actually is
GAIN_CELL = 0xC6CD0                         # forward LKAS gain
GAIN_OLD, GAIN_NEW = 5346, 4455             # 6x -> 5x
SOFT_EME = 0xC674E                          # the interlock the clamp must stay BELOW
FB26 = 0xD774C                              # FactorB record, ENGAGED mode 26 (manual 24 @0xD6760)
FB_OLD, FB_NEW = 1024, 2048                 # flat Q10 gain at unity -> x2, no shape to corrupt
FB24 = 0xD6760                              # MANUAL FactorB -- asserted UNTOUCHED
FC26 = 0xD77D0                              # FactorC record, ENGAGED mode 26 (manual 24 @0xD67E4)
FC_Y0 = FC26 + 2 + 8                        # layout [npt][X x4][Y x4] -> Y[0]
FC_OLD, FC_NEW = 0, 429                     # := Y[2]; below X[0] the LERP clamps flat to Y[0]
FC24 = 0xD67E4                              # MANUAL FactorC -- asserted UNTOUCHED
FE26 = 0xD780C                              # FactorE record, ENGAGED mode 26 (manual 24 @0xD6820)
FE_X0, FE_Y1 = FE26 + 2, FE26 + 2 + 8 + 2   # layout [npt][X x4][Y x4]
X0_OLD, X0_NEW = 60, 12                     # open the rate dead zone
Y1_OLD, Y1_NEW = 140, 539                   # := Y[2], real slope on the first segment
FE24 = 0xD6820                              # MANUAL record -- asserted UNTOUCHED
OP_POINT = 99                               # gp-0x6ac0 in-burst, measured on-car [94,113]
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V271-V268BASE-LKAS.PID.KI.5"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # asserted UNCHANGED here -- V255/V269 were undriveable
KI_CELL, KI_OLD, KI_NEW = 0xC63E6, 0, 5   # the LKAS-path integral gain
KI_CLAMP = 0xC61BA                        # anti-windup, (v<<10)>>3
KI_DEADBAND = 0xC62E4                     # error deadband ahead of the integrator
PUMP_SURF = (0xD7A88, 0xD7AC4, 0xD7B00, 0xD7B3C)
PUMP_BOOST = (0xD78F8, 0xD78A4)
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def build():
    print("=" * 102)
    print("  V271 -- V268 (the build that DROVE) + THE LKAS INTEGRAL TERM.")
    print("=" * 102)

    print("\n  [1] BASE = V268 -- the only new build that drove acceptably")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X,
          "base carries the STOCK 1x rate lane (sar 0xa at both sites) -- V62's fix is ABSENT, "
          "which is the whole reason for this build")
    check(u16(base, LEVER_B) == LEVER_B_VAL,
          f"Lever B is {LEVER_B_VAL} on this car (V62 flew with it at stock 512) -- the lane arm "
          f"is 10.2x higher, so the doubled lane clips on large transients where V62's never did")
    check(u16(base, GAIN_CELL) == 5346, "forward gain is 5346 (6x) -- NOT touched by this build")
    check(u16(base, CLAMP_P) == 3072 and u16(base, CLAMP_N) == 3072,
          "forward clamps are 3072 -- NOT touched by this build")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- the LKAS-path integral gain")
    check(u16(base, KI_CELL) == KI_OLD,
          f"base Ki = {KI_OLD} -- the integrator is shipped DISABLED by a zero gain")
    check(u16(base, KI_CLAMP) > 0,
          f"the anti-windup clamp 0x{KI_CLAMP:05X} = {u16(base, KI_CLAMP)} is LIVE, so Ki is the only "
          f"thing holding the term at zero")
    _hw = (u16(base, KI_CLAMP) << 10) >> 3
    print(f"      anti-windup headroom = ({u16(base, KI_CLAMP)} << 10) >> 3 = {_hw:,}")
    check(u16(base, KI_DEADBAND) <= 16,
          f"the error deadband 0x{KI_DEADBAND:05X} = {u16(base, KI_DEADBAND)} is small, so the "
          f"integrator sees essentially all of the error")
    struct.pack_into("<H", code, KI_CELL, KI_NEW)
    attributed |= {KI_CELL, KI_CELL + 1}
    check(u16(code, KI_CELL) == KI_NEW,
          f"Ki {KI_OLD} -> {KI_NEW} -- a value driven on this platform by an independent contributor, with Kp and Kd "
          f"left at stock")
    check(u16(code, KI_CLAMP) == u16(base, KI_CLAMP) and
          u16(code, KI_DEADBAND) == u16(base, KI_DEADBAND),
          "the anti-windup clamp and the deadband are UNTOUCHED -- only the gain is enabled")

    print("\n  [3] NOTHING FROM THE FAILED V255/V269 LINE IS PRESENT")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X,
          "both sar immediates are STOCK -- V255/V256/V269 carried the doubled rate lane and were "
          "UNDRIVEABLE (massive vibration parked and DISENGAGED, persisting after the wheel stopped)")
    check(u16(code, 0xC6440) == 2048 and u16(code, 0xC6442) == 1024 and u16(code, 0xC643E) == 1536,
          "the three live rate-lane arms are STOCK")
    check(u16(code, 0xC6CD0) == 5346 and u16(code, 0xC61B2) == 3072 and u16(code, 0xC61B4) == 3072,
          "forward gain and both clamps are STOCK -- this build adds NO proportional authority, "
          "which is the term that tracks the 21 Hz mode")
    for _p in PUMP_SURF + PUMP_BOOST:
        check(bytes(code[_p:_p + 26]) == bytes(base[_p:_p + 26]),
              f"pump record 0x{_p:06X} unchanged vs THIS base (V268 already flattened it)")
    for _p in (0xD6760, 0xD67E4, 0xD6820):
        check(bytes(code[_p:_p + 20]) == bytes(base[_p:_p + 20]),
              f"MANUAL damper record 0x{_p:06X} byte-identical")

    print("\n  [4] THE RAILS AND EVERYTHING ELSE ARE FROZEN")
    for a, want in sorted(RAIL_SITES.items()):
        check(bytes(code[a:a + 4]).hex() == want,
              f"0x{a:05X} = {want} -- the +-8192 lane rail is UNTOUCHED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- not the bricking class")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")
    check(u16(code, GAIN_CELL) == 5346, "forward gain UNTOUCHED -- single variable")
    check(u16(code, CLAMP_P) == 3072 and u16(code, CLAMP_N) == 3072, "clamps UNTOUCHED")
    check(code[ALPHA2] == 14, "alpha2 stays at the CAR's 14 -- this build does not touch it")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the biquad block is BYTE-IDENTICAL -- no notch change in this build")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = u32(code, blk[1])
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block byte-identical to base")

    print("\n  [7] FULL BYTE DIFF vs V112")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 2, f"{len(pay)} payload byte(s) -- the Ki halfword")
    check(set(pay) <= {KI_CELL, KI_CELL + 1},
          "every payload byte is the Ki cal -- no code byte, no other cal")
    check(KI_CELL in pay, "the Ki cal actually moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V271 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v271_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V271_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V270 -- ENABLE THE LKAS-PATH INTEGRAL TERM. ONE CAL HALFWORD, TWO BYTES.                           **")
    print("  **   0xC63E6   Ki   0 -> 5                                                                            **")
    print("  ** I TOLD THE OPERATOR 'THERE IS NO PID ON THE LKAS OUTPUT'. THAT WAS WRONG.                          **")
    print("  ** an independent contributor pointed at it and the decompile of FUN_00028ea6's tail confirms:                      **")
    print("  **   if (guard) { if (gp-0x680a==1) iVar34 = 0; }        <- RESET path                                **")
    print("  **   else { iVar34 = (acc>>3) + ((err*cal(0xC63E6))>>3);  <- INTEGRATE                                **")
    print("  **          clamped to +-((cal(0xC61BA)<<10)>>3); }       <- ANTI-WINDUP (live, 10240)                **")
    print("  **   gp-0x6dd0 = iVar34;                                                                              **")
    print("  ** Honda shipped the COMPLETE controller -- reset, anti-windup, deadband 4 -- and                     **")
    print("  ** disabled it with a ZERO GAIN. It was in my own zero-cal census (reader 0x2AC8E)                    **")
    print("  ** among the 89 torque-path hits; I adjudicated two and walked past this one.                         **")
    print("  ** WHY IT FITS WHAT WAS ASKED: integral removes STEADY-STATE ERROR -> more effective                  **")
    print("  ** authority WITHOUT raising Kp, the term that tracks the 21 Hz mode. And if the                      **")
    print("  ** loop rails against a persistent offset, removing the offset cuts rail duty.                        **")
    print("  ** ON-CAR EVIDENCE THIS KIT HAS FOR NOTHING ELSE ON THE SHELF: an independent contributor ran                       **")
    print("  ** exactly Ki 0->5 on this platform, Kp/Kd stock -- 'got rid of steady state error                    **")
    print("  ** and more torque without heavy oscillation... a game changer.'                                      **")
    print("  ** V255/V269 LESSON APPLIED: those doubled the rate lane and were UNDRIVEABLE. My                     **")
    print("  ** GATE 2 claim that 'Kd adds phase lead and moves no pole right' was FALSE. This                     **")
    print("  ** adds INTEGRAL, which adds phase LAG and rolls off as 1/f -- it cannot excite a                     **")
    print("  ** 21 Hz mode the way a derivative can. No sar byte moves; gain and clamps stock.                     **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
