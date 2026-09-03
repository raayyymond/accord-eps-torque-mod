# -*- coding: utf-8 -*-
r"""V283 -- V282 + the LKAS rate-PID INTEGRAL GAIN Ki, 0xC63E6, 0 -> 50.  ONE CAL HALFWORD.

=== OPERATOR DECISION (2026-09-03) ==============================================================
V281 rev 3 flew Kp flat 248 on route r35 (`HIGHANGLE-r35-V281R3-2026-09-03.md` / `V281R3-READ-r35-2026-09-03.md`,
agent v281read): the 7 Hz strong-turn ripple is GONE ((a) 0 F7 episodes/100s vs r34 6.8; (b') ripple/level 0.18
vs r34 0.37) -- PASS on the PREREG decision rule -- but seven 1-3 s STALLED-WHEEL runs appeared at idx 54-79,
delivering only 0.62 of V280's torque there (14.8 s total, |angle| 46-70 deg, hands light, wheel at 9-22 deg/s
against a 30-44 deg/s reference).  This is exactly the predicted cost of a P-only loop's low-demand deadband
at a flattened, lowered Kp (`docs/research/7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md` sec.10 / `ki_sizing.py`
sec.C: a held error the P term cannot clear because it never accumulates).  The branch in that doc's own
decision tree (`sec.10.6`) that fires is: "7 Hz FIXED AND the stall/deadband cost bites" -> cut V283 with Ki
at 0xC63E6.

=== THE ARITHMETIC, RE-DERIVED FROM THE DECOMPILE THIS SESSION (FUN_00028ea6, code.bin) ========
Independently confirmed by direct GhidraMCP disassembly of the live function (not taken on the strength of any
prior report):

    E        = 32*sp - fb                                          # 0x29D76 shl 0x5,r16 ; 0x29D78 sub r26,r16
    excess   = deadband(E >> 5, cal(0xC62E4) = 4)                   # 0x29D7C..0x29D9A -- a DEADBAND on the error
    Ki       = cal(0xC63E6)          <- ld.hu 0x73e6,tp,r6  @ 0x29D9C   (tp = 0xBF000, 0xBF000+0x73E6 = 0xC63E6)
    clampcal = cal(0xC61BA)          <- ld.hu 0x71ba,tp,r13 @ 0x29DA0   (0xBF000+0x71BA = 0xC61BA)
    acc_old  = gp-0x6dd0             <- ld.w  -0x6dd0,gp,r10 @ 0x29DA4
    prod     = excess * Ki           <- mul r6,r9,r0         @ 0x29DA8  (excess in r9 from the deadband block; low32 -> r9)
    bound    = (clampcal << 10) >> 3 <- shl 0xa,r13 ; sar 0x3,r13 @ 0x29DAC/DAE
    acc_new  = clamp((acc_old >> 3) + (prod >> 3), +-bound) <- sar 0x3,r10 ; sar 0x3,r9 ; add r9,r10 ; cmp/cmovgt/cmovle @ 0x29DB0-DC2
    gp-0x6dd0 = acc_new << 3         <- shl 0x3,r24 @ 0x29DE4 ; st.w r24,-0x6dd0,gp @ 0x2A190 (unconditional store)
    ... (later in the same call, same acc_new value still held in r2 from the clamp above)
    I_term   = acc_new >> 7          <- sar 0x7,r2 @ 0x29F18   => |I_term| <= clampcal = 10240 (the bound<<7>>7 = clampcal)
    sum      = clamp(I_term + P + D, +-0xC61BE = 15360) <- add r9,r2 @ 0x29F1E (+P) ; add r8,r2 @ 0x29F24 (+D)

Reset sites (single writer to gp-0x6dd0, confirmed by the same 4-access census the deep-analysis doc used):
  0x2A164 -- `mov 0x0,r24` on the not-engaged/not-valid clear path (also zeros r29,r27,r22,r16,r12) -- the
             normal disengage/reset arm.
  0x2A0C6 -- the `gp-0x680a` alternate-taper arm; per kit memory (twistloop) this arm has NO WRITER on stock/
             flown builds, so in practice only 0x2A164 fires.
The dead twin `FUN_0002A93A` carries a byte-identical copy of the same Ki/clamp reads (0x2AC8E, 0x2ACA0) and
the same accumulator pair (0x2AC96 ld.w / 0x2B05C st.w, per the deep-analysis census) -- confirmed structurally
identical to the live function's tail at 0x2AC80-0x2ACA6 (re-disassembled this session).  It is NOT called from
any live path (established in an earlier session); it does not change this build's arithmetic.

=== THE 0x59B90 BUILD GATE -- RESOLVED THIS SESSION, BY DIRECT DISASSEMBLY =======================
7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md sec.10.1 flagged a raw LE byte-scan hit at 0x59B90 as a possible
THIRD reader of 0xC63E6 needing confirmation before this build.  Disassembled directly (dry_run):

    0x59B84  sar   0x8, r16
    0x59B86  sst.b r16, 0x3, ep
    0x59B88  ld.h  -0x4ec2, gp, r16      (6-byte extended-displacement gp-relative form)
    0x59B8E  sst.b r16, 0x4, ep
    0x59B90  ld.h  -0x4ec2, gp, r14      <-- the flagged site
    0x59B96  sar   0x8, r14
    0x59B98  sst.b r14, 0x5, ep
    0x59B9A  ld.h  -0x6b98, gp, r12      (a DIFFERENT well-known cell, the final FOC/motor command per kit memory)
    ...

This is a **gp-relative RAM load** (`ld.h -0x4ec2, gp, r14`, base register gp) inside what is structurally a
CAN-frame byte packer (sar 0x8 -> sst.b to ep+0x3/0x4/0x5/0x6, the same "extract byte, store to frame buffer"
idiom as the 0x14A/427 packers documented elsewhere in this kit).  0xC63E6 is a **tp-relative FLASH cal**
(base register tp, displacement 0x73E6): a completely different base register, address space and physical
target from gp-0x4ec2.  The raw-byte hit was a coincidental partial match on the encoded bytes of an unrelated
6-byte gp-relative instruction, not a second reader of the Ki cal.  DECIDED: 0x59B90 is NOT a reader of
0xC63E6.  [EVIDENCE -- disassembled directly, dry_run, this session; confirms the doc's own suspicion]

=== PRODUCT WIDTH -- CANNOT OVERFLOW AT Ki=50 ====================================================
excess is `E>>5` deadbanded; E = 32*sp - fb with sp in the LKAS map's range (<=1032, per the Kp-bank records)
and fb clamped to +-46080 (0xC62E6, carried from V280 rev 2/V281 rev 3/V282, asserted below).  |E| is therefore
bounded well under 2^17, so |excess| << 2^16.  `mul r6,r9,r0` is V850's 32x32->64 form (low32 into the named
register, high32 discarded into r0); at Ki=50 the product magnitude is at most a few hundred thousand -- far
inside signed 32-bit range.  No overflow at this dose. [EVIDENCE -- bound derived from the FROZEN cal set below,
all reconfirmed against the base image in [1]]

=== WHY Ki=50 (not the doc's 100) =================================================================
`ki_sizing.py` sec.A: the PI corner f_i = 1.2434*Ki/Kp Hz.  At Kp=248 (the flown V281 rev 3 / V282 value):
  Ki=50  -> f_i=0.25 Hz, cost at 7 Hz: x0.984 amplitude, -1.38 deg phase -- negligible against the measured
           7.3 Hz ring (r24-dominated, sec.B: alpha=1, r24 untouched by this build).
  Ki=100 -> f_i=0.50 Hz, roughly double the phase cost, faster stall-release (0.83 s vs 1.77 s) but a larger
           overshoot on release and a corner closer to the outer (openpilot) loop's own 1-5 Hz band.
No Ki has ever flown on this car -- V270/V271 built Ki=5 (see LINEAGE below) but neither was reported flown.
50 is the SMALLER of the two doc-considered doses (50 conservative, 100 the doc's own preferred), chosen here
because this is the first flown Ki: it already fixes the sizing's own PASS bar (idx 40-80 stalled |T| p50
predicted >=2100 at Ki 100; at Ki 50 the accumulation rate is half, so the release is slower but the direction
and mechanism are identical, and the dose can be raised from 50 once the mechanism is confirmed on the wire
rather than guessing a bigger first step).  Costs no new authority ceiling: the sum clamp (0xC61BE=15360), the
+-3072 output cap, and every downstream clamp are UNCHANGED -- the integral term is bounded to the SAME +-10240
window the anti-windup clamp (0xC61BA) already enforced at Ki=0 (dormant), so Ki=50 spends none of the existing
headroom, it only makes the existing window reachable over time. Adds phase LAG (rolls off 1/f), the opposite
failure mode to V255/V269's derivative doubling (which was UNDRIVEABLE).

=== LINEAGE: 0xC63E6 has been touched before, never flown ========================================
`grep -l C63E6 analysis-2020accord/builds/*/*.py` -> build_v270_tva.py (Ki 0->5, base V112, unflown per the kit
record), build_v271_tva.py (carries V270's edit forward), build_v272/273/274/275/276/277/278/278r3/279/280/
281/281r3/282 (all list it in a FROZEN={0xC63E6:0,...} dict, i.e. asserted STOCK/ZERO on every one of those
builds -- V283 is the first to move it off zero on the V280-rev-2-descended line).  V270's docstring already
flagged the reset-path/anti-windup-clamp/deadband structure and an outside report of Ki 0->5 on this platform
("game changer... more torque without heavy oscillation, no windup") -- consistent with, not contradicted by,
this build's own decompile.

=== WHAT IS CARRIED, UNCHANGED, FROM V282 =========================================================
V282's cave repoint (0xC4B34, bits 5/6 of CAN 0x14A re-pointed to r24-vs-T and r24-vs-aggregator comparators),
V281 rev 3's Kp bank (flat 248 on the live slot 7 / all 28 records), the map, clamp 0xC62E6=46080, Kd, tapers,
the 427 delivered-torque tap window (0x55DF0-0x55E11) -- everything carried byte-for-byte.  See build_v282_tva.py
and build_v281r3_tva.py for those builds' own rationale; not restated here.

=== THE INSTRUMENT (already on the wire; no new cave, no new bits) ================================
CAN-427 T tap (gp-0x6b38, unchanged) directly reads the integral's effect: a stalled-wheel run at idx 40-80
should show |T| rising over ~1-2 s instead of sitting flat at the P-only value, and the tap's rise time can be
fit against the predicted excess*Ki/1024-per-ms accumulation to check the arithmetic in situ.  CAN 0x14A bit 4
(sign of r24, carried from V282/before) is unaffected -- this build touches no cell r24 depends on.
SCORE THE DRIVE FROM rlog-tools/studies/osc-highangle/PREREG-V283-READ.md (numeric thresholds: stalled runs <= 2, idx 40-80 rate
>= 70 % of reference, dead fraction <= 0.10; lurch > 20 deg/s or > 3 s = cost FAIL), not from this docstring.

=== PRE-REGISTRATION (drive-time; recorded for the close-out, not a build-time assertion) =========
Primary: at |angle| >= 30 deg stalled frames (rate/ref < 0.5) at idx 40-80, tap |T| p50 -- V281 rev 3 read
778-868 on the WIRE there (the r35 stall runs; 1240-1700 are ki_sizing's MODEL values at Ki 0/5, not a read); PASS if it rises measurably (half the Ki=100 sizing's effect, since Ki=50 halves the
accumulation rate) and the stalled-run COUNT/duration falls vs V281 rev 3's 7 runs / 14.8 s.  Cost: peak rate
after a stall breaks free -- FAIL if it exceeds the reference by more than 20 deg/s or the operator reports a
lurch; and PREREG-V281's statistic (g) (highway 4-8 Hz rate power / OSC episodes) -- FAIL if a new slow
0.2-1 Hz weave appears (the outer-loop-interaction risk named in the deep-analysis doc, sec.10.6 gate iii).
FAIL sentence: "If Ki=50 leaves the idx 40-80 stalled-frame |T| p50 unmoved from V281 rev 3's 778-868 (wire) and
the stall-run count/duration unchanged, the integral path is not live on the car as decoded here -- the
reset condition fires more often than the decompile shows, or gp-0x680a-class gating exists that was not
found -- and no larger Ki is licensed until the accumulator (gp-0x6dd0) is tapped directly instead of inferred
from the sum."

=== CLASS OF BUILD =================================================================================
A DOSE, the first authority change since V281 rev 3's Kp cut -- and the first Ki ever flown on this car. It
raises no ceiling (every clamp, the gain, the output cap: unchanged) and touches a DIFFERENT term (integral,
1/f roll-off) from every prior authority lever in the post-V38 arc, which has moved P (gain/Kp) or D (the
V255/V269 rate-lane doubling that was undriveable). Cal-only: one u16, two bytes, one CRC trailer.
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
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V283_WRITE", "").strip().lower()

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
             "_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"
GRANDPARENT_NAME = "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GRANDPARENT_SHA = "b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa"
TAG = "V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"

# ---- [A] carried from V281 rev 3 / V282 -- the Kp bank, asserted byte-identical, not re-derived here --------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y_R3 = (0, 68, 112, 136, 208), (248,) * 5
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)

# ---- [B] the cave from V282 -- asserted byte-identical, this build touches NONE of it -------------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
HOOK = 0x55C0E
HOOK_STOCK4 = bytes.fromhex("86ff26ef")
V282_EDIT_SITES = (0xC4B36, 0xC4B42, 0xC4B64, 0xC4B70)   # the 4 hw2 halfwords V282 repointed

PACK_LO, PACK_HI = 0x55DF0, 0x55E12
MAP_PTR, MAP_N = 0xC9A88, 10
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

# ---- [C] the one edit -----------------------------------------------------------------------------------
KI_CELL, KI_OLD, KI_NEW = 0xC63E6, 0, 50    # the LKAS-path integral gain
KI_CLAMP = 0xC61BA                          # anti-windup bound -- MUST NOT MOVE (3 outside readers per kit record)
KI_DEADBAND = 0xC62E4                       # error deadband ahead of the integrator -- MUST NOT MOVE

FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,
    0xC61B6: 10240,  0xC61BA: 10240,
    0xC61BC: 15360,  0xC61BE: 15360,
    0xC63E8: 923,    0xC63EA: 1560,
    0xC63EC: 992,    0xC63EE: 507,
    0xC62E4: 4,
    0xC6B26: 256,    0xC6B12: 98,
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
    0xC6446: 5244,                          # V282's probe target (r24 gain arm) -- must not move
    0xC62E6: 46080,                         # the feedback clamp (V280 rev 2's edit)
}

OK, BAD = "[PASS]", "[FAIL]"
_census = {"S": 0, "V": 0, "T": 0}
_checks = [0, 0]


def check(cond, msg, kind="S"):
    assert kind in _census
    _checks[0] += 1
    _census[kind] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} [{kind}] {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def independent_rebuild(base):
    """A second, minimal implementation with none of build()'s bookkeeping: patch the Ki halfword directly,
    then re-CRC every block touched -- via FF.crc_block_map, not the address hardcoded elsewhere."""
    img = bytearray(base)
    assert u16(img, KI_CELL) == KI_OLD
    struct.pack_into("<H", img, KI_CELL, KI_NEW)
    touched = {KI_CELL, KI_CELL + 1}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 106)
    print("  V283 -- V282 + the LKAS rate-PID integral gain Ki, 0xC63E6, 0 -> 50.  ONE CAL HALFWORD, TWO BYTES.")
    print("=" * 106)

    print("\n  [1] BASE = V282")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V282 base sha256 matches", "S")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    check(u16(base, KI_CELL) == KI_OLD, f"base Ki = {KI_OLD} -- shipped/carried disabled through V282", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and n7 == 5
          and tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y_R3,
          f"base live Kp slot {LIVE_SLOT} @0x{LIVE_KP_REC:05X}: X {LIVE_KP_X} Y {LIVE_KP_Y_R3} "
          f"(V281 rev 3's flat-248, carried through V282)", "V")
    check(bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK4, "base hook 0x55C0E == jarl 0xc4b34,lp", "V")
    for a in V282_EDIT_SITES:
        check(s16(base, a) in (-0x6ADA, -0x6B38, -0x6B94),
              f"base cave site 0x{a:05X} carries a V282-repointed displacement (not the pre-V282 value)", "V")

    print("\n  [2] THE ONE EDIT -- the LKAS-path integral gain")
    check(u16(base, KI_CLAMP) > 0,
          f"the anti-windup clamp 0x{KI_CLAMP:05X} = {u16(base, KI_CLAMP)} is LIVE, bounding I_term at "
          f"exactly this value regardless of Ki", "V")
    _bound = u16(base, KI_CLAMP)
    print(f"      |I_term| bound = cal(0xC61BA) = {_bound:,} (bound<<10>>3 for the accumulator, >>7 for I_term "
          f"-- the two shifts cancel to leave the bound in I_term's own units, confirmed by disassembly at "
          f"0x29DAC-DAE and 0x29F18)")
    check(u16(base, KI_DEADBAND) <= 16,
          f"the error deadband 0x{KI_DEADBAND:05X} = {u16(base, KI_DEADBAND)} is small (+-0.52 deg/s of rate "
          f"error), so the integrator sees essentially all of a sustained stall's error", "V")

    code = bytearray(base)
    attributed = set()

    struct.pack_into("<H", code, KI_CELL, KI_NEW)
    attributed |= {KI_CELL, KI_CELL + 1}
    check(u16(code, KI_CELL) == KI_NEW, f"Ki {KI_OLD} -> {KI_NEW} at 0x{KI_CELL:05X}", "T")
    check(u16(code, KI_CLAMP) == u16(base, KI_CLAMP) and u16(code, KI_DEADBAND) == u16(base, KI_DEADBAND),
          "the anti-windup clamp and the deadband are UNTOUCHED -- only the gain is enabled", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [3] PRODUCT-WIDTH CHECK -- excess*Ki cannot overflow at Ki=50")
    fb_clamp = u16(base, 0xC62E6)
    sp_max = 1032   # sp lives in the assist map, not the Kp bank; this is the map's own ceiling (checked below)
    map_ptr0 = u32(base, MAP_PTR)
    n_map = s16(base, map_ptr0)
    map_y = [u16(base, map_ptr0 + 2 + 2 * n_map + 2 * i) for i in range(n_map)]
    check(max(map_y) <= sp_max, f"assist-map Y ceiling {max(map_y)} <= assumed sp_max {sp_max}", "S")
    e_max = 32 * sp_max + fb_clamp
    excess_max = e_max // 32  # E>>5, deadband only reduces this
    prod_max = excess_max * KI_NEW
    check(prod_max < (1 << 31), f"|excess_max * Ki| = {excess_max} * {KI_NEW} = {prod_max:,} << 2**31 "
          f"(mul is V850's 32x32->64, low32 used) -- no overflow at this dose", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    outside = [x for x in range(START, END) if x not in (KI_CELL, KI_CELL + 1) and code[x] != base[x]]
    check(outside == [], f"no byte outside the Ki cell changed before CRC recompute ({len(outside)} stray diffs)", "S")
    for a, v in FROZEN.items():
        check(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}", "S")
    check(bytes(code[CAVE_START:CAVE_END]) == bytes(base[CAVE_START:CAVE_END]),
          "the whole V282 cave (164 B) is byte-identical -- this build adds no telemetry, changes none", "S")
    check(bytes(code[HOOK:HOOK + 4]) == HOOK_STOCK4, "hook 0x55C0E byte-identical", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          "427 tap window 0x55DF0-0x55E11 byte-identical -- the delivered-torque tap is kept", "S")
    map_ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    for p in map_ptrs:
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]), f"map 0x{p:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        p = u32(base, KP_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kp slot {s} @0x{p:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        p = u32(base, KD_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kd slot {s} @0x{p:05X} byte-identical", "S")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [5] CRC TRAILER -- located GENERICALLY via V53.owning_block")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    check(len(blocks) == 1, f"exactly ONE CRC block owns the Ki cell ({blocks})", "S")
    b0, b1 = blocks[0]
    check(b0 == 0xC6000 and b1 == 0xC6FFC, f"block is [0x{b0:05X},0x{b1:05X}) -- the main cal block", "S")
    check(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:06X}", "S")
    oldc = u32(code, b1)
    newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved", "S")
    struct.pack_into("<I", code, b1, newc)
    attributed |= set(range(b1, b1 + 4))
    print(f"      Ki page [0x{b0:06X},0x{b1:06X})  CRC trailer 0x{b1:06X}  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [6] FULL BYTE DIFF vs V282")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(set(diff) <= attributed, f"every one of the {len(diff)} differing bytes is the Ki cal or its CRC trailer", "S")
    ki_bytes_expected = sum(1 for j in (0, 1)
                            if struct.pack("<H", KI_OLD)[j] != struct.pack("<H", KI_NEW)[j])
    check(ki_bytes_expected == 1,
          f"Ki {KI_OLD}->{KI_NEW}: only the LOW byte of the u16 differs (high byte stays 0x00, since "
          f"{KI_NEW} < 256) -- {ki_bytes_expected} of the 2 touched Ki bytes actually change", "S")
    check(len(diff) == ki_bytes_expected + 4,
          f"total diff vs V282 is exactly {ki_bytes_expected} payload byte(s) (Ki, of 2 touched) + 4-byte "
          f"CRC trailer = {ki_bytes_expected + 4}, got {len(diff)}", "S")
    check(KI_CELL in diff, "the Ki cal's low byte actually moved", "S")
    for s, e in runs(diff):
        kind = "CRC trailer" if s == b1 else "Ki cal (0xC63E6)"
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {kind}  {bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")

    print("\n  [6b] CROSS-IMAGE vs V281 rev 3 and V280 rev 2 -- confirm no lever from those builds moved here")
    parent = Path(plain_image_path(PARENT_NAME)).read_bytes()
    check(hashlib.sha256(parent).hexdigest() == PARENT_SHA, "V281 rev 3 image sha256 matches", "S")
    grandparent = Path(plain_image_path(GRANDPARENT_NAME)).read_bytes()
    check(hashlib.sha256(grandparent).hexdigest() == GRANDPARENT_SHA, "V280 rev 2 image sha256 matches", "S")
    diff_v282_vs_parent = set(a for a in range(START, END) if base[a] != parent[a])   # V282's own cave edit
    diff_parent_vs_gp = set(a for a in range(START, END) if parent[a] != grandparent[a])  # V281r3's Kp edit
    diff_v283_vs_gp = set(a for a in range(START, END) if code[a] != grandparent[a])
    expected = diff_v282_vs_parent | diff_parent_vs_gp | set(diff)
    check(diff_v283_vs_gp == expected,
          f"V283 vs V280 rev 2 diff ({len(diff_v283_vs_gp)} B) == V282's cave diff ({len(diff_v282_vs_parent)} B) "
          f"UNION V281 rev 3's Kp diff ({len(diff_parent_vs_gp)} B) UNION this build's Ki+CRC diff ({len(diff)} B), "
          f"no overlap, nothing extra", "S")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(parent[HOOK:HOOK + 4]) == bytes(grandparent[HOOK:HOOK + 4]) == HOOK_STOCK4,
          "hook byte-identical all the way back to V280 rev 2", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(grandparent[PACK_LO:PACK_HI]),
          "427 tap window byte-identical all the way back to V280 rev 2", "S")
    check(u16(parent, KI_CELL) == 0 and u16(grandparent, KI_CELL) == 0,
          "Ki was 0 on both ancestor images -- V283 is the FIRST build in this line to move it", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V283 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN exists -- the non-circular cipher test is reachable", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [8] END STATE -- re-read from the FINAL image and from the DECODED .rwd")
    for nm, im in (("code", code), ("dec", dec)):
        kind = "T" if nm == "code" else "S"
        check(u16(im, KI_CELL) == KI_NEW, f"{nm}: 0x{KI_CELL:05X} (Ki) == {KI_NEW}", kind)
        check(u16(im, KI_CLAMP) == 10240, f"{nm}: 0x{KI_CLAMP:05X} (I clamp) == 10240, untouched", kind)
        check(u16(im, KI_DEADBAND) == 4, f"{nm}: 0x{KI_DEADBAND:05X} (deadband) == 4, untouched", kind)
        for a, v in FROZEN.items():
            check(u16(im, a) == v, f"{nm}: 0x{a:05X} == {v}", kind)
        check(bytes(im[CAVE_START:CAVE_END]) == bytes(base[CAVE_START:CAVE_END]), f"{nm}: V282 cave untouched", kind)
        check(bytes(im[HOOK:HOOK + 4]) == HOOK_STOCK4, f"{nm}: hook untouched", kind)
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: 427 tap window untouched", kind)
        n7, X7, Y7 = rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y_R3, f"{nm}: live Kp record == flat-248, carried", kind)
        # KI VALUE PINS (adversary ADV283-C finding 1): tie the dose to something outside KI_NEW.
        import re as _re
        _prereg = Path(__file__).resolve().parents[2].parent / "rlog-tools" / "studies" / "osc-highangle" / "PREREG-V283-READ.md"
        _m = _re.search(r"Ki 0 → (\d+)", _prereg.read_text(encoding="utf-8"))
        check(_m is not None and u16(im, KI_CELL) == int(_m.group(1)), f"{nm}: Ki on the image == the dose in PREREG-V283-READ.md ({_m.group(1) if _m else '?'})", "S")
        _fi = 1.2434 * u16(im, KI_CELL) / Y7[0]
        check(0.24 <= _fi <= 0.26, f"{nm}: integral corner 1.2434*Ki/Kp(image) = {_fi:.3f} Hz in [0.24, 0.26]", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [9] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild (direct Ki-halfword patch + generic re-CRC, no shared state) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print(f"\n  [10] KI PAGE / TRAILER SUMMARY")
    print(f"      Ki cell   0x{KI_CELL:05X}  page [0x{b0:06X},0x{b1:06X})  trailer 0x{b1:06X}")
    print(f"      Ki value  {KI_OLD} -> {KI_NEW}")

    _scr = os.environ.get("ACCORD_V283_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v283_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v283_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(f"_v283_{TAG}_plain_image.bin"))
        out_rwd = Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        others = [f.name for f in Path(RWD_DIR).glob("*V283*.rwd") if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"exactly ONE flashable V283 rwd on disk (others: {others})", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V283_WRITE=rwd to emit the files")

    print("\n" + "=" * 106)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- census: {_census['S']} substantive, "
          f"{_census['V']} vacuous (entailed by the base sha256), {_census['T']} tautological (readback of a write)")
    print("  ** V283 -- LKAS-path integral gain Ki, 0xC63E6, 0 -> 50.  ONE CAL HALFWORD, TWO BYTES.            **")
    print("  ** Base V282 (V281 rev 3 Kp flat 248 + the r24 comparator tap).  Cost this build answers: the     **")
    print("  ** V281 rev 3 stall class at idx 40-80 (7 runs, 14.8s, |T| 0.62 of V280's, r35 read).             **")
    print("  ** 0x59B90 build gate RESOLVED: a gp-relative RAM load (base gp), not a reader of the tp-relative **")
    print("  ** flash cal 0xC63E6 -- confirmed by direct disassembly, not by re-reading the doc's suspicion.   **")
    print("=" * 106)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
