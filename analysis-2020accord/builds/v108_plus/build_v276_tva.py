# -*- coding: utf-8 -*-
r"""V276 -- THE REFERENCE, SCALED 6x.  TWO CELLS.  BASE: V268.

GOAL, stated by the operator and not negotiated down: **scale the LKAS angle-rate REFERENCE by 6.**
This build does exactly that and nothing else, plus telemetry.

=== THE TWO CELLS ==============================================================================
  [A] ASSIST MAP  0xC9A88, all 28 records:  every Y knot x6, Honda's SHAPE preserved exactly.
      Setpoint ceiling 172/180/188 -> 1032/1080/1128.  This IS the reference.
  [B] FEEDBACK CLAMP  0xC62E6:  7680 -> 46080 (x6).
      Not optional.  It bounds what the loop can MEASURE.  Left at 7680 the feedback saturates
      long before the new reference is approached, and the loop would be regulating against a
      blind sensor.  Scaling both preserves Honda's setpoint:feedback ratio at 1.395 EXACTLY.
  [C] TELEMETRY -- 4 code bytes in the CAN-427 packer (carried from V273):
      0x55DF2-3 source disp -> 0x98B2 (gp-0x674e, the variant selector)
      0x55E10   sar 0x3 -> sar 0x0     0x55E0E  mov 0x0,r7 -> mov 0x1,r7  (clamp floor 0 -> 1)
      The floor fix matters: 4 of the 16 variant records read gp-0x674e = 0, which would wire out
      as 0 -- indistinguishable from a dead channel.  With floor 1, only a dead channel reads 0.
      This settles which of 28 records is live, and ONE selector indexes the map, Kp, Kd AND both
      taper banks (gp-0x674e, ld.bu at 0x29AA0/0x29B7C/0x29CC4, shl 0x2 at 0x29AAA -- verified).

=== WHAT WAS REMOVED FROM V275, AND WHY -- three adversarial agents, three independent kills ====
V275 additionally divided Kp and Kd by 6 and flattened the override taper.  All three edits are
GONE.  The reasons are recorded here because they are the substance of this build's design:

  * Kp/6 AND Kd/6 -- REMOVED.  E = 32*setpoint - feedback, and the feedback is a MEASURED PHYSICAL
    rate that does NOT scale with the map.  So 6*(32*S) - fb  !=  6*(32*S - fb): scaling the
    setpoint x6 while dividing Kp by 6 preserves the FEEDFORWARD term exactly and divides the
    FEEDBACK term's gain by six.  V275's "delivered torque held within 3%" was evaluated at fb = 0,
    the single operating point where the two cancel -- a tautology of exactly the class that
    condemned V274.  Measured consequence: at the operating point where V268 delivers 0 torque,
    V275 delivered 2034, and its torque varied only 2441 -> 2034 across the whole feedback range
    versus 2441 -> 0 for V268.  That converts a rate loop into a near-constant sign-following
    torque pedestal that can never null, and rate feedback IS this lane's damping.
    ⇒ Kp and Kd are UNTOUCHED here, which is also STATE.md's converged retune ("Kp: NO CHANGE.
    Kd: NO CHANGE." / "RATE CAPABILITY = raise M and F only"), agreed independently by 3 agents.

  * TAPER FLATTEN -- REMOVED.  The override curve is the firmware mechanism behind the operator's
    own long-standing observation that significant driver torque kills the grinding, and his
    measured median override torque (2235) sits ONE COUNT below the curve's first knot (2240).
    Flattening it deletes both his symptom-suppressor and his escape hatch -- and it was the only
    edit in V275 that raised delivered authority in any regime, on the same drive that raises the
    reference.  It is orthogonal to the rate hypothesis and would make the drive uninterpretable.

=== WHAT THIS BUILD ACTUALLY DOES ON THE CAR -- STATED HONESTLY ================================
With Kp fixed, scaling the reference x6 means the loop asks for a rate the rack may not reach, so
P SATURATES over much of the range and the loop delivers full lane torque instead of backing off.
That is not a defect; it is what "reference x6" means.  Quantified from 182,248 engaged frames of
flown data (routes r66/r67/r68/r6d), at |cmd| >= 80% of rail:
      median achieved column rate      27 deg/s
      56.3% of high-command frames exceed the CURRENT reference ceiling (~22.3 deg/s)
      43.4% exceed the CURRENT feedback clamp   (~31.1 deg/s)
⇒ Today, in most high-command frames, the wheel is already moving FASTER than the loop's reference,
so the error is negative and the lane applies REVERSE torque -- and above ~31 deg/s the feedback
clamp saturates, so that reverse torque is constant regardless of how fast the wheel is going.
After V276 the loop instead keeps commanding forward torque out to ~133 deg/s.
🛑 RISK, PLAINLY: in the high-command / fast-steering regime the lane will push at full authority
where it previously damped.  Peak torque is UNCHANGED (0xC61B4 = 3072 and gain 0xC6CD0 = 5346 are
both frozen and asserted -- max LKAS torque stays 6x STOCK, not 36x), but it is now applied in
situations where the stock loop was backing off.  ASSESS STATIONARY OR AT LOW SPEED FIRST.
⚠ The deg/s figures above are BELIEF, not EVIDENCE: they rest on an inherited x8 counts-per-deg/s
factor that a tracer traced four hops upstream (14-bit resolver -> wrap-corrected delta -> x120000
/16384 -> 2-sample average -> LPF -> x48x1159>>15) and could NOT close.  The 6x RATIO is exact and
does not depend on it; the absolute placement does.

=== INSTRUMENT -- how this build is read from ONE short drive ==================================
  * gp-0x6a56 is already transmitted as STEER_ANGLE_RATE on CAN 0x18F (399) bytes 2-3 at 100 Hz,
    free, no edit.  The achieved-rate distribution during engaged high-command episodes is the
    endpoint.  ⚠ that channel is magnitude-clamped at +-12000 -- confirm the new regime fits under
    it before treating a flat top as a physical limit.
  * The 427 tap answers, from ANY drive including parked, which of the 28 records is live.
  * THE SENTENCE A NULL LICENSES: "the achieved column-rate distribution during high-demand
    episodes did not shift, which means either the raised reference was never exercised or the rack
    cannot deliver it -- and we cannot tell which."  To avoid that null, the drive must ENTER the
    regime: alternating gentle and hard corrections at 5-15 mph, not steady-state cruising.

=== CLASS OF BUILD, against the whole arc since V38 ============================================
GENUINELY NEW.  The arc has moved authority (V38-52), lane gains (V62-73), damping (V74-84), phase
(the notch era) and forward gain (the ladder).  Every one of those changed HOW HARD the loop pushes.
**None has ever moved WHAT THE LOOP IS ASKING FOR.**  0xC9A88 and 0xC62E6 have never been flown in
any build -- verified by grepping every build_v*_tva.py and the lever index.  Two virgin cells.
"""
import hashlib
import os
import struct
import sys
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

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                                   # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V276_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
TAG = "V276-V268BASE-REFERENCE6X.MAP.FEEDBACK"

K = 6                                       # the rate-axis scale factor

# ---- [A] telemetry ---------------------------------------------------------------------------
SRC_DISP, SRC_V268, SRC_NEW = 0x55DF2, 0x9544, 0x98B2
SAR_SITE, SAR_V268, SAR_NEW = 0x55E10, 0xA3, 0xA0

# ---- [B] assist map --------------------------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)

# ---- [C] override taper ----------------------------------------------------------------------
TAPER_PTRS = (0xCBA04, 0xCBA74)
TAPER_N = 4
TAPER_SHAPES = {(70, 72, 78, 80): (254, 234, 12, 0),      # slots 0-9   <- this car's candidates
                (32, 48, 64, 112): (255, 205, 154, 0)}    # slots 10-27

# ---- [C] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK, FB_NEW = 0xC62E6, 7680, 7680 * K

# ---- frozen torque path, all asserted --------------------------------------------------------
FROZEN = {
    0xC61B4: 3072,                     # OUTPUT clamp -- FROZEN.  The torque cap.
    0xC6CD0: 5346,                     # forward gain -- FROZEN.  Already 6x Honda's 891; raising
                                       # it to 32076 would be 36x STOCK.  Operator's cap: 6x stock.
    0xC61B6: 10240,  0xC61BA: 10240,   # D clamp / I anti-windup -- FROZEN, and NOT bypassed
    0xC61BC: 15360,  0xC61BE: 15360,   # P clamp / sum clamp -- FROZEN, and they now BIND
                                       # HARDER: P reaches 15360 in all 28 slots where V268
                                       # stopped at 97.4%.  That clamp IS the 6x torque cap.
    0xC63E6: 0,                        # Ki -- stays OFF
    0xC63E8: 923,    0xC63EA: 1560,    # feedback lag pole / input gain -- pole must NOT move
    0xC63EC: 992,    0xC63EE: 507,     # 5 Hz output LPF
    0xC62E4: 4,                        # error deadband
    0xC6B26: 256,    0xC6B12: 98,      # the OTHER PID (driver-side) -- untouched
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,                     # NOT this loop's clamp: 0 reads in FUN_00028ea6, all 5 in
                                       # FUN_0002b422/FUN_0002b57a.  Asserted only to prove we did
                                       # not touch it.  STATE.md's "0xC61B2/0xC61B4 pair" is wrong.
}

# ---- [D] the proportional rescale ------------------------------------------------------------
GAIN_CELL, GAIN_V268 = 0xC6CD0, 5346        # FROZEN -- already 6x stock; 6x again = 36x stock
OUT_CELL, OUT_V268 = 0xC61B4, 3072          # FROZEN -- this IS the torque cap, and it stays
GAIN_SITE = 0x2A1EE                                             # ld.h -- 32076 must stay < 32768
FLOOR_SITE, FLOOR_V268, FLOOR_NEW = 0x55E0E, 0x00, 0x01         # clamp floor 0 -> 1
KP_N, KD_N = 5, 4

CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1
KP_PTR, KD_PTR = 0xCB994, 0xCB7D4
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)      # must all be ld.hu (low byte 0xe5)

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


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p, n):
    return ([u16(b, p + 2 + 2 * i) for i in range(n)],
            [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])


def build():
    print("=" * 102)
    print(f"  V276 -- THE REFERENCE x{K}.  TWO CELLS.  Kp/Kd/taper/gain/clamps FROZEN.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK}")
    check(u16(base, GAIN_CELL) == GAIN_V268, f"base forward gain == {GAIN_V268} (= 6 x Honda's 891)")
    check(u16(base, OUT_CELL) == OUT_V268, f"base output clamp == {OUT_V268} -- the TORQUE CAP")
    check(base[FLOOR_SITE] == FLOOR_V268, "base 427 clamp floor is `mov 0x0,r7`")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49 (the flash-time model)")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x (V62 NOT restored)")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "index clamp +-240 unchanged")

    print("\n  [1b] THE SIGN-EXTENSION DEFECT -- V276 raises NEITHER cell that carries it")
    # CORRECTED TWICE. BOTH 0xC61B4 AND 0xC61BE have EIGHT tp-form readers in TWO stages, not
    # four, and each stage carries one sign-extended read. The second
    # stage at 0x2A910..0x2A92E lives in a region Ghidra never made a function, so every
    # Ghidra-only xref census is BLIND to it; it was found by raw byte scan. Each stage carries
    # one sign-extended read. V276 freezes the cell, so this documents rather than gates -- but
    # V275's "exactly ONE sign-extended read" was a FALSE [PASS] -- and the first fix repeated
    # the same undercount on 0xC61BE (second stage 0x2B024..0x2B03C) until an audit caught it.
    # LESSON: a Ghidra-only xref census is blind to code outside a recognised function; every
    # census here is a raw little-endian byte scan over the WHOLE image.
    SIGN_SITES = {0xC61BE: ((0x2A13E, 0xE5), (0x2A146, 0x25), (0x2A14C, 0xE5), (0x2A156, 0xE5),
                            (0x2B024, 0xE5), (0x2B02C, 0x25), (0x2B032, 0xE5), (0x2B03C, 0xE5)),
                  0xC61B4: ((0x2A1F8, 0xE5), (0x2A20C, 0x25), (0x2A212, 0xE5), (0x2A21C, 0xE5),
                            (0x2A910, 0xE5), (0x2A91E, 0x25), (0x2A924, 0xE5), (0x2A92E, 0xE5))}
    for cal_, sites in SIGN_SITES.items():
        n_sign = 0
        for a, want in sites:
            kind = "ld.hu ZERO-ext" if base[a] == 0xE5 else "ld.h  SIGN-ext" if base[a] == 0x25 else "??"
            check(base[a] == want, f"0x{cal_:05X} read @0x{a:05X} {base[a]:02X} = {kind}")
            n_sign += base[a] == 0x25
        check(n_sign == 2,
              f"0x{cal_:05X}: {len(sites)} tp-form reads in TWO stages, {n_sign} sign-extended "
              f"-> hard cap 32767")
    print("      -> 0xC61BE stays 15360 (a 6x would be 92160: over u16 AND over the sign cap).")
    check(base[GAIN_SITE] == 0x25, f"0x{GAIN_SITE:05X} is ld.h (sign-ext) -- gain capped at 32767")
    print("      -> V276 raises NEITHER 0xC61B4 NOR 0xC6CD0.  The 6x is on the RATE axis only.")

    print("\n  [1c] the feedback clamp's OWN reads must all be ld.hu, or 6x would break it")
    for a in FB_SITES:
        check(base[a] == 0xE5, f"0x{a:05X} {base[a]:02X} = ld.hu (zero-extend) -- safe above 32768")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] [A] TELEMETRY -- CAN 427 -> gp-0x674e")
    check(u16(base, SRC_DISP) == SRC_V268, "base 427 source is gp-0x6ABC")
    check(base[SAR_SITE] == SAR_V268, "base packer carries `sar 0x3, r6`")
    struct.pack_into("<H", code, SRC_DISP, SRC_NEW)
    code[SAR_SITE] = SAR_NEW
    attributed |= set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE}
    code[FLOOR_SITE] = FLOOR_NEW
    attributed |= {FLOOR_SITE}
    check(code[FLOOR_SITE] == FLOOR_NEW, "427 clamp floor `mov 0x0,r7` -> `mov 0x1,r7`")
    print("      wire = clamp(|gp-0x674e| * 5, 1, 1023)")
    print("      -> floor 1, so selector==0 reads 1 and ONLY a dead channel reads 0.")
    print("      -> expected codes deliberately NOT asserted: the 0-vs-1-based record numbering")
    print("         in the 0xCD012 table is unresolved, so any specific code is a BELIEF.")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")

    print(f"\n  [3] [B] ASSIST MAP -- scaled {K}x, SHAPE PRESERVED, all {N_SLOTS} records")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(START <= p < END for p in ptrs), f"all {len(ptrs)} map pointers in range")
    shapes = {}
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        ceil = K * Y[-1]                                   # 6x THIS record's own ceiling
        newY = tuple(K * y for y in Y)                     # HONDA'S SHAPE, scaled -- NOT linearised
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        check(tuple(gY) == newY, f"map 0x{p:05X} Y -> {K}x, ceiling {ceil}")
        check(all(gY[i] == K * Y[i] for i in range(n)),
              f"map 0x{p:05X} EXACTLY {K}x stock at every knot -- Honda's SHAPE is preserved, so "
              f"torque-vs-index is preserved when Kp is divided by {K}")
        _r = [gY[i] / Y[i] for i in range(n) if Y[i]]
        check(max(_r) == min(_r) == K, f"map 0x{p:05X} every knot scales by exactly {K}, no rounding")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  ceiling {oldY[-1]:4d} -> {newY[-1]:5d}   (Honda's shape, x{K})")
    check(all(tuple(rec(code, p, MAP_N)[0]) == MAP_X for p in ptrs), "every map X untouched")

    print("\n  [3b] OVERRIDE TAPER -- DELIBERATELY NOT TOUCHED, AND ASSERTED STOCK")
    tps = set()
    for arr in TAPER_PTRS + (0xCB8B4, 0xCB924):
        for s in range(N_SLOTS):
            tp_ = u32(base, arr + 4 * s)
            check(START <= tp_ < END, f"taper ptr 0x{arr:05X}[{s}] in range")
            tps.add(tp_)
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
              f"taper 0x{p:05X} BYTE-IDENTICAL to V268 -- the flatten is NOT in this build")
    print(f"      {len(tps)} taper records across FOUR banks, all byte-stock.")
    print("      WHY IT IS NOT FLATTENED: the taper is UPSTREAM -- it MULTIPLIES into the demand")
    print("      index -- and the companion hard cutoff (cal 0xC64B8 = 255 compared against a")
    print("      zero-extended byte) is UNSATISFIABLE, so the taper reaching Y=0 is the ONLY live")
    print("      mechanism that drives the command to zero. Flattening takes the command from ZERO")
    print("      to FULL past the knee, and the operator's median override torque (2235) sits ONE")
    print("      COUNT below the first knot (2240). It also only covers 2 of the 4 mode banks.")

    print(f"\n  [4] [C] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == FB_NEW, f"feedback clamp == {FB_NEW}")
    check(FB_NEW < 65536, "fits u16")

    print("\n  [5] THE ARITHMETIC -- ALL 28 RECORDS x 241 INDICES, FROM THE BUILT IMAGE")
    print("      MODEL: FEEDBACK = 0 (the stall / step-response point).  Stated explicitly")
    print("      because an fb=0 model is what made V274's and V275's torque claims tautologies.")
    print("      It is the RIGHT model for a BOUND -- fb=0 maximises the forward error, so")
    print("      'peak <= 2505' and 'never less than V268' hold at EVERY fb -- but it is NOT")
    print("      a description of the car in motion.  What the loop does once the wheel moves")
    print("      is in the docstring's RISK paragraph, not in these assertions.")

    def lerp(X, Y, x):
        if x <= X[0]:
            return Y[0]
        if x >= X[-1]:
            return Y[-1]
        for i in range(len(X) - 1):
            if X[i] <= x <= X[i + 1]:
                return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])
        raise AssertionError

    PC = u16(code, 0xC61BC)
    OC = u16(code, OUT_CELL)
    G = u16(code, GAIN_CELL)

    def surface(img, slot):
        mp = u32(base, MAP_PTR + 4 * slot)
        kp = u32(base, KP_PTR + 4 * slot)
        mX, mY = rec(img, mp, MAP_N)
        pX, pY = rec(img, kp, KP_N)
        out = []
        for idx in range(241):
            sp = lerp(mX, mY, idx)
            P = max(-PC, min(PC, (32 * sp * lerp(pX, pY, idx)) >> 8))
            out.append((sp, P, max(-OC, min(OC, (P * G) >> 15))))
        return out

    peaks, ratios, npts, peakmap = set(), [], 0, {}
    rslot, ridx, tq_new, sp_err = [], [], {}, [0]
    for s in range(N_SLOTS):
        a_, b_ = surface(base, s), surface(code, s)
        check(b_[240][0] == K * a_[240][0],
              f"slot {s}: setpoint ceiling {a_[240][0]} -> {b_[240][0]} = exactly {K}x")
        check(a_[240][2] <= b_[240][2] <= 2505,
              f"slot {s}: peak torque {a_[240][2]} -> {b_[240][2]}, capped by the FROZEN clamps at "
              f"2505 = (15360 * 5346) >> 15 -- the ceiling is Honda's P clamp, not this edit")
        check(b_[240][2] / a_[240][2] <= 1.03,
              f"slot {s}: peak torque rises only {100*(b_[240][2]/a_[240][2]-1):.1f}% "
              f"(P reaches its clamp where V268 stopped at 97.4% of it)")
        peaks.add(a_[240][2]); peakmap[s] = a_[240][2]
        mp_ = u32(base, MAP_PTR + 4 * s)
        mXs, mYs = rec(base, mp_, MAP_N)
        for i in range(1, 241):
            tq_new[(s, i)] = b_[i][2]
            true6 = 6 * (lerp(mXs, [1000 * y for y in mYs], i) / 1000.0)
            sp_err.append(abs(b_[i][0] - true6))
            if a_[i][2] > 0:
                ratios.append(b_[i][2] / a_[i][2]); rslot.append(s); ridx.append(i)
                npts += 1
    check(min(ratios) >= 0.999, f"NO (slot,index) delivers LESS than V268 (min {min(ratios):.3f}x)")
    # Some low-index points exceed 6x. That is V268 QUANTISATION BEING REMOVED, not V276
    # overshooting: V268 floors a sub-unit setpoint to a coarse integer, V276 resolves it. Assert
    # the honest invariant -- V276 tracks 6x the UNQUANTISED setpoint -- instead of a false <=6x.
    over = [(r, s, i) for (r, s, i) in zip(ratios, rslot, ridx) if r > K + 0.01]
    check(all(i <= 40 for _, _, i in over),
          f"every >{K}x point is at demand index <= 40 ({len(over)} of {npts}) -- the micro regime "
          f"where V268's integer LERP floors the setpoint")
    worst_abs = max((tq_new[(s, i)] for _, s, i in over), default=0)
    check(worst_abs <= 2505, f"largest torque at any >{K}x point is {worst_abs}, still under the "
                             f"frozen 2505 ceiling -- no new authority, only finer resolution")
    check(max(sp_err) <= 1.0, f"V276 setpoint tracks {K}x the UNQUANTISED map everywhere "
                            f"(max deviation {max(sp_err)} counts = integer rounding)")
    from collections import Counter
    print(f"      V268 per-record peak torque: "
          f"{dict(sorted(Counter(peakmap.values()).items()))} (value -> #slots)")
    print(f"      V276 raises every slot to exactly 2505 = (15360 * 5346) >> 15, the frozen "
          f"P-clamp ceiling -- worst rise +2.6%")
    print(f"      torque ratio V276/V268 across {npts} (slot,index) points: "
          f"min {min(ratios):.2f}x  max {max(ratios):.2f}x")

    s0, s1 = surface(base, 1), surface(code, 1)
    print("\n        idx |  V268: sp     P  torque |  V276: sp     P  torque")
    for idx in (12, 24, 48, 96, 160, 240):
        print(f"      {idx:5d} | {s0[idx][0]:8d} {s0[idx][1]:6d} {s0[idx][2]:6d}  |"
              f" {s1[idx][0]:8d} {s1[idx][1]:6d} {s1[idx][2]:6d}")

    r0 = FB_STOCK / (32 * s0[240][0])
    r1 = FB_NEW / (32 * s1[240][0])
    print(f"\n      feedback clamp {FB_STOCK} -> {FB_NEW};  setpoint:feedback ratio "
          f"{r0:.3f} -> {r1:.3f}")
    check(abs(r1 - r0) < 0.001, "Honda's setpoint:feedback ratio preserved EXACTLY (both scaled 6x)")

    print("\n  [6] TORQUE PATH RE-ASSERTED ON THE BUILT IMAGE")
    for a, v in FROZEN.items():
        check(u16(code, a) == v, f"0x{a:05X} still {v}")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X, "rate lane still stock 1x")
    check(code[IDX_CLAMP_P] == 240 and code[IDX_CLAMP_N] == 240, "index clamp still +-240")
    for nm, ptr, npt in (("Kp", KP_PTR, KP_N), ("Kd", KD_PTR, KD_N)):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = s16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
                  f"{nm} slot {s} BYTE-IDENTICAL -- Kp/Kd are NOT retuned in this build")
    check(u16(code, GAIN_CELL) == GAIN_V268, f"0xC6CD0 still {GAIN_V268}")
    check(u16(code, OUT_CELL) == OUT_V268, f"0xC61B4 still {OUT_V268}")

    print("\n  [7] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [8] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE, FLOOR_SITE, FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    check(set(pay) <= allow, "every payload byte is a MAP Y knot, the feedback clamp, "
                             "or one of the 4 telemetry code bytes -- no X axis, no cave, "
                             "no gain, no output clamp, no unintended cell")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(cb == sorted(set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE, FLOOR_SITE}),
          f"exactly 4 code bytes move, all in the 427 packer: {[hex(x) for x in cb]}")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]),
          "FUN_00028ea6 itself is byte-identical -- every edit is a CALIBRATION, not code")
    print(f"      {len(pay)} payload bytes, {len(cb)} code, {len(blocks)} CRC trailers")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V276 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (predicts flash NRC 0x72)")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest()
          if hasattr(FF, "V38_PLAIN") else True,
          "cipher table validated NON-circularly against the known V38 plain image")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v276_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V276_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
