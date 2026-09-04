# -*- coding: utf-8 -*-
r"""V284 -- V282 (Ki 0) + M8*, a BAND-LIMITED Kp bump on BOTH AXES of the live LERP record.  ONE RECORD, SLOT 7.

    0xE5378   X  (0, 68, 112, 136, 208)  ->  (0, 32, 36, 44, 88)
              Y  (248, 248, 248, 248, 248) -> (248, 248, 512, 512, 248)

Eight payload bytes plus one 4-byte page CRC.  No code byte, no cave byte, no other cal, no other slot.

=== BASE IS V282, **NOT** V283 -- Ki IS REMOVED =================================================
V284 descends from `_v282_..._plain_image.bin` (sha256 0ea98d06...), so `0xC63E6` **Ki = 0**.  The build
asserts that on the base AND on the built image AND on the decoded .rwd.  V283 (Ki 50) is a SIBLING of this
build, not its parent: the operator's structural objection is that openpilot models the EPS output as a
TORQUE, and integral action inside the EPS turns it into a rate/position servo, changing the interface his
outer tune was calibrated against (`OVERSTEER-V283-r36-r38-2026-09-03.md` sec.6/9/10).  M8* is the
MEMORYLESS answer to the same stall/deadband cost: static, feed-forward, no new state.

=== WHY THIS TABLE -- read from the studies, not asserted =======================================
`STUTTER-7HZ-V283-r36-r38-2026-09-03.md` A10.0 corrected its own A9.2: on a detector-driven (unbiased)
tabulation the residual 7 Hz ring sits at **median idx 70**, i.e. ON TOP of the stall band, and A10.5
concluded no band-limited table could separate them.  ADDENDUM 3 (A11) then re-opened it at higher
resolution on the X axis (A11.2, time-weighted index histograms):

    population            40-54   54-68   68-80   80-96   96-112   112+
    STALLS (21.8 s)       0.391   0.282   0.168   0.096   0.052    0.011      <- 67 % of stall time in 40-68
    RING   (8.9 s)        0.117   0.193   0.173   0.154   0.141    0.079      <- spread evenly 40-112

**The stalls are bottom-heavy in demand index; the ring is not.**  A bump centred low and decayed by idx 88
catches two thirds of the stalls while leaving the ring's upper two thirds at 248.  Only the X axis can
exploit that -- a Y-only band table (the "BAND" row below) puts 512 across the ring's own plateau and is the
WORST candidate on every gate.

A11.4, all tables through the same chain on the same frames (Ki 0), `stutter_v283_m8_knots.py`:

    candidate                     idx 8  20   32   45   60   80  100 | benefit | ring worst x0.90 | P-rail max
    V283/V282 on car, flat 248     248  248  248  248  248  248  248 |  1.000  |  0.900           |  0.0017
    M1 flat 341                    341  341  341  341  341  341  341 |  1.375  |  0.949           |  0.0032
    M2 flat 400                    400  400  400  400  400  400  400 |  1.613  |  1.007  RE-ARMS  |  0.0208
    BAND (Y-only 248,512,512,..)   279  326  372  423  481  512  512 |  1.900  |  1.134  RE-ARMS  |  0.0848
    ** M8* [0,32,36,44,88] K512    248  248  248  506  416  296  248 |  1.622  |  0.949           |  0.0036 **

    chain |T| INTO THE STALL, per route (r35/r36/r37/r38), A11.4's table:
        V282 flat 248   951 /  706 /  646 /  892        <- what is on the car now
        M1 flat 341    1291 /  937 /  833 / 1222
        M2 flat 400    1506 / 1086 /  954 / 1434
        ** M8*         1549 / 1289 /  954 / 1738 **     <- more than flat 400 on three of four routes
    for reference, V283's own measured (Ki 50) stall figures were 951/706/646/892 -> the Ki route reached
    the same place by ACCUMULATION; M8* reaches it by GAIN, at the index where the error is small.

**Why it works, and why no flat table can (A11.4, quoted):** P rails at |E| >= 3,932,160/Kp, so the P-rail
cost of gain is paid where E is LARGE -- the high-index, big-setpoint frames.  The ring's cost of gain is
paid where the RING's index mass is -- 68-112.  The stalls need gain where the STALL mass is -- 40-68, and
there E is small because the setpoint is small.  M8* puts 512 exactly on that low, small-E, stall-heavy band
and is back to 248 before either of the other two costs lands.  A flat table pays all three everywhere.

=== THE LERP, RE-DERIVED FROM THE DECOMPILE THIS SESSION (V282 IMAGE, not code.bin, not the brief) =========
Disassembled directly against the V282 plain image in GhidraMCP (`dry_run`), 0x29DC6-0x29E3B, inside the live
rate-PID `FUN_00028ea6`.  The record layout AND the clamp/interpolate structure both come from these bytes:

    0x29DC6  mov   0xcb994, r10          r10 = the Kp POINTER TABLE base
    0x29DCC  mov   r12, ep               r12 = slot*4  (the selector byte scaled somewhere upstream)
    0x29DCE  add   r10, ep
    0x29DD0  sld.w 0x0, ep, ep           ep  = *(0xCB994 + slot*4)  = THE RECORD BASE   <- WALK THE POINTER
    0x29DD6  ld.w  0x0, r9, r10          r10 = the same record base
    0x29DDA  st.h  r7, -0x697a, gp       (the demand index is published to RAM here -- a future tap site)
    0x29DDE  sld.hu 0x2, ep, r9          r9  = X[0]      <- rec+0x02 IS X[0], EXPLICIT.  No implicit X0.
    0x29DE2  add   0xc, r10              r10 = &Y[0]     <- rec+0x0C
    0x29DE6  add   0x2, ep               ep  = &X[0]
    0x29DE8  zxh   r7                    idx zero-extended to 16 bits
    0x29DEA  cmp r9,r7 ; bh  0x29DF4     if NOT (idx > X[0])  -> 0x29DEE: r9 = Y[0]; return   [LOW CLAMP]
    0x29DF4  sld.hu 0x8, ep, r6          r6  = X[4]      (ep = rec+0x02, +8 -> rec+0x0A)
    0x29DF6  cmp r6,r7 ; bnc 0x29E04     if idx >= X[4]      -> 0x29E04: r9 = Y[4]; return    [HIGH CLAMP]
    0x29DFA .. 0x29E12                   walk X and Y pointers together while idx >= X[i]
    0x29E14  r9 = Y[i] ; r13 = Y[i-1] ; r8 = X[i-1] ; r6 = X[i]      (all ld.hu -- ZERO extended)
    0x29E20  sub r13,r9                  r9 = Y[i] - Y[i-1]      (32-bit signed; NEGATIVE on a falling leg)
    0x29E24  sub r8,r7                   r7 = idx - X[i-1]
    0x29E26  mul r7,r9,r0                r9 = (idx - X[i-1]) * (Y[i] - Y[i-1])
    0x29E2A  sub r8,r6                   r6 = X[i] - X[i-1]                       <- THE SEGMENT WIDTH
    0x29E2C  divq r6,r9,r0               r9 = product / width     SIGNED, TRUNCATES TOWARD ZERO
    0x29E30  add r13,r9                  + Y[i-1]
    0x29E32  zxh r9                      result truncated to 16 bits
    0x29E36  mul r9,r8,r0                ... and straight into the P term

The Python emulator in [4] below mirrors exactly that, integer for integer, including truncate-toward-zero
on a descending leg, and is run over the record READ BACK FROM THE BUILT IMAGE (and again from the decoded
.rwd).  [EVIDENCE -- disassembled this session against the V282 image itself]

🛑 **HARD GATE from `0x29E2C divq r6,r9`: X MUST BE STRICTLY INCREASING.**  A duplicate knot makes the
divisor zero.  Asserted on the built image and on the decoded .rwd, not merely on the constants.

⚠ The 32->36 leg is 4 wide -- 99 Kp counts per index step, the steepest ramp in any shipped record (Honda's
narrowest is 48).  It is continuous and the divide is exact at the knots, but it is OUTSIDE Honda's own
design envelope and is named as such (A11.5 caveat 1).  A gentler shelf [0,32,44,60,88] was searched and is
WORSE on both gates (ring 0.983, P-rail 0.0201): the steepness is buying the safety, not costing it.

=== SLOT 7 ONLY -- and the two reasons, the second stronger than the first =====================
V281 rev 3 blanket-wrote all 28 records.  This build does NOT.

1. **The selector census (A11.7, verified there by GhidraMCP + a raw LE scan that agree exactly):**
   `gp-0x674e` has ONE writer (0x4272A, the UDS coding path) and four reads, all inside the live PID, all
   loading the same byte into the same register -- 0x29CC4 being the one that feeds this lookup.  One
   selector value per tick drives map/Kp/Kd/both tapers.  **No runtime mode consults a second slot.**
2. **The page CRCs.**  The 28 records are scattered across FIVE separately-CRC'd 4 KB pages
   (0xE4000 slots 0-5 · 0xE5000 slots 6-11 · 0xE6000 12-17 · 0xE7000 18-23 · 0xE8000 24-27).  A slot-7-only
   edit touches ONE page CRC; a blanket write touches FIVE.  On a build class whose only bricking mode is a
   bad write, a 5x smaller CRC surface is the argument that should lead.  [1c] asserts the other four page
   CRCs are bit-unchanged.

**The fallback is safe, read from the base image, not assumed:** Y by slot is 205 (0,2,4,5) · 266 (1,6) ·
248 (3,7,8,9) · 307 (10-27, dead -- the selector maxes at 9).  If the coding ever moved off 7 the car falls
back to a FLAT Kp no stiffer than 266, far under any Kp_crit on A9.3's curve.

=== BUILDABILITY PRECEDENT -- an X edit on THIS record has been built before ===================
**V281 rev 2** (`build_v281_tva.py`, built, hash-verified, SUPERSEDED, never flown) moved this exact
record's X knots.  Verified here by direct byte read of the superseded image on disk, in [1d]:

    SUPERSEDED_v281_rev2_FLAT341_plain_image.bin  0xE5378: 0500 0000 1800 4400 8800 d000  f800 5501 5501 5501 5501
                                                  ->  X (0, 24, 68, 136, 208)   Y (248, 341, 341, 341, 341)
    the V282 base (= V281 rev 3 restored)         0xE5378: 0500 0000 4400 7000 8800 d000  f800 f800 f800 f800 f800
                                                  ->  X (0, 68, 112, 136, 208)  Y (248, 248, 248, 248, 248)

i.e. rev 2 wrote 0xE537C (X[1]) and 0xE537E (X[2]).  **Those are the two offsets this build also writes**
(plus X[3] at 0xE5380, X[4] at 0xE5382 and Y[2]/Y[3] at 0xE5388/0xE538A).  The record address and the field
layout are therefore confirmed by a THIRD independent route on top of the disassembly and the pointer walk.
⚠ Record-keeping correction: the lineage's description of V281 rev 2 as "flat 341 from idx 24" is
incomplete -- **it moved knots too.**

=== LINEAGE: what has and has not been done to the Kp bank ======================================
`grep -l CB994 analysis-2020accord/builds/*/*.py` -> V274-V283 all reference the pointer bank.
  · V280 rev 2 and earlier  -- stock LERP on slot 7: X (0,68,112,136,208), Y (248,512,645,696,696).  FLOWN
    (r32/r33/r34).  Ring PRESENT, F7 4.3-8.1 per 100 s; zero stalls.
  · V281 rev 2  -- X (0,24,68,136,208), Y (248,341,341,341,341) on every record.  BUILT, SUPERSEDED, NEVER FLOWN.
  · V281 rev 3  -- Y flattened to Y[0] on all 28 records, X stock.  FLOWN (r35).  Ring GONE (F7 0.0);
    SEVEN stalled runs at idx 54-79, 14.8 s, tap 778-868 counts.
  · V282  -- Kp bank untouched (cave repoint only).  V283 -- Kp bank untouched (Ki 50 only).  FLOWN (r36-r38).
**Nothing has ever flown between flat 248 and the stock LERP's 512-696.**  M8* is the first table to put a
NON-CONSTANT, NON-STOCK gain shape on the car, and its peak (512) is below the stock LERP's peak (696) --
asserted in [4] against the V280 rev 2 image, not against a remembered number.

=== THE INSTRUMENT -- already on the wire, and it can distinguish THIS table ====================
No new cave, no new bits, no length change.  V284 carries, byte-identical to V282 (asserted in [3]/[5]):
  · the CAN-427 delivered-torque tap (packer window 0x55DF0-0x55E11, source gp-0x6b38 = T);
  · V282's cave at 0xC4B34 with 0x14A byte 4 bit 6 = |r24| >= |T|, bit 5 = |r24| >= |aggregator|,
    bit 4 = sign(r24) -- 164 bytes, hash-identical;
  · the hook `jarl 0xc4b34,lp` at 0x55C0E.

**Kp is readable from the 427 tap by the window-local method already written and already validated on five
routes** -- `v283_read_r36_r38.py` sec.1b: simulate the chain's T under each candidate Kp table, then take
the median per-window (2 s, 0.25 s hop) correlation and least-squares scale of the simulated T against the
measured tap, plus the whole-route correlation broken out by demand-index cell (1-40 / 40-68 / 68-112 /
112-241).  r35 (flat 248, known-correct) calibrates what a right answer looks like.
🛑 **M8* is DISCRIMINABLE from flat 248 by construction:** the two tables are IDENTICAL outside idx 32-88
and differ by up to 2.06x inside it, so the 40-68 index cell must separate while the 112-241 cell must NOT.
That is a within-drive, within-frame contrast with a built-in negative control -- exactly the design the
probe law asks for, and it needs no matched episode and no cross-build comparison.

**THE SENTENCE A NULL WILL LICENSE, written before the drive:**
    "If V284's idx 40-80 stalled-run count and stall-frame tap |T| p50 come back at V282/r35's values
     (7 runs / 14.8 s / 892-895 counts) AND sec.1b's 40-68 index cell still prefers flat 248 over M8*,
     then the X knots are not reaching the live lookup as decoded -- the selector is not 7, or the demand
     index the LERP sees is not the 0xE4-derived index we tabulate offline.  No further X-axis table is
     licensed until the index itself is tapped, and the tap site is already identified:
     `st.h r7, -0x697a, gp` at 0x29DDA publishes it to RAM every tick."
    (If sec.1b DOES prefer M8* in 40-68 while the stalls persist, that is a different and INTERPRETABLE
     result: the gain is arriving and the stall is not an error-gain problem -- road load above what
     Kp 512 can break -- and the lever moves to the map or to 0xC6446.)

=== RISK, STATED BEFORE THE DRIVE ==============================================================
Authority RISES, and here is by how much and where.  Over the whole demand-index axis 0-255 the delivered
Kp changes ONLY on 32 < idx < 88; everywhere else it is bit-identical to what has been on the car since
V281 rev 3.  Peak Kp 512 = 2.06x today's 248, and 0.74x the stock LERP peak (696) that flew on r32/r33/r34.
  · **Ring (7 Hz strong-turn):** worst individual episode's return ratio 0.949 x |L_tot(248)| -- the SAME
    number as flat 341, on all four routes' own measured Ls/Lr shares (A11.4).  EVIDENCE on Ls/Lr and on
    the index distributions; **BELIEF on |L_tot(248)| = 0.90**, which is the prereg's plant-free model and
    is not measured.  At 0.95 M8* reads 1.002 -- at the edge -- but so does flat 341 (1.001).  **M8*
    inherits M1's exposure exactly, no more.**
  · **P-rail duty:** max 0.0036 across routes vs V282's 0.0017 and flat 400's 0.0208 (5.8x cleaner than
    flat 400).  OPEN-LOOP chain counterfactuals on the measured rate -- upper bounds; the ordering is what
    is robust, since all tables are evaluated on identical frames.
  · **Every clamp is UNCHANGED:** feedback clamp 46080, sum clamp 15360, output cap 3072, anti-windup 10240,
    the assist map, Kd, both tapers, the r24 gain 5244.  The dose cannot exceed a ceiling that has flown.
  · **Untouched bands, deliberately:** idx 0-32 (18.2 % of all engaged time, and the lane-change band) is
    exactly 248 -- the A11.3 search was restricted to a >= 32 for that reason and cost nothing; idx 88-112
    (r37's ring median 103) is exactly 248.
  · What this build does NOT do: it does not touch the 20 Hz creep grind lane (0xC6446 untouched), and it
    does not change the FLAT fallback of any other slot.

=== CLASS OF BUILD -- how it differs from the recent arc ========================================
A **SHAPE** change, and the first one in the post-V38 arc.  V280 rev 2 changed the assist MAP; V281 rev 2/3
changed the Kp LEVEL (a knee, then flat); V282 changed only TELEMETRY; V283 added a new TERM (integral).
V284 changes neither level nor term but the **GAIN'S DEPENDENCE ON DEMAND** -- 512 where the error is small
and the stalls are, 248 where the ring and the P-rail cost are.  It is the memoryless counterpart of V283
and answers the same cost by a different mechanism, so the two are a matched pair and NOT a repeat.
Cal-only: one 24-byte record, 8 payload bytes, one page CRC.
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
WRITE_MODE = os.environ.get("ACCORD_V284_WRITE", "").strip().lower()

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
             "_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"
GRANDPARENT_NAME = "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GRANDPARENT_SHA = "b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa"
REV2_NAME = "SUPERSEDED_v281_rev2_FLAT341_plain_image.bin"    # X-knot precedent on THIS record
SIBLING_NAME = ("_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
                "_plain_image.bin")                            # the Ki arm -- V284 must NOT resemble it
TAG = "V284-V282BASE-KI0-KP.M8.SLOT7.512.IDX32.88-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"

# ---- [A] the Kp bank ------------------------------------------------------------------------------------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
BASE_KP_X, BASE_KP_Y = (0, 68, 112, 136, 208), (248,) * 5      # V281 rev 3's flat-248, carried through V282
NEW_KP_X, NEW_KP_Y = (0, 32, 36, 44, 88), (248, 248, 512, 512, 248)     # M8*
STOCK_KP_Y = (248, 512, 645, 696, 696)                          # V280 rev 2 / Honda, for the ceiling check
REV2_KP_X, REV2_KP_Y = (0, 24, 68, 136, 208), (248, 341, 341, 341, 341)  # the X-knot precedent
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)
KP_PAGES = (0xE4000, 0xE5000, 0xE6000, 0xE7000, 0xE8000)        # the five pages the 28 records live on
EDIT_PAGE = 0xE5000

# the pre-registered gain-vs-index table, computed by rlog-tools/studies/osc-highangle/stutter_v283_m8_knots.py
# (a DIFFERENT implementation, by a different agent) and quoted in STUTTER-7HZ-... A11.4.  The emulator in [4]
# is written from the disassembly and must reproduce these independently.
PREREG_CURVE = {8: 248, 20: 248, 32: 248, 45: 506, 60: 416, 80: 296, 100: 248}

# ---- [B] the cave / tap from V282 -- this build touches NONE of it --------------------------------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
CAVE_SHA8 = None                       # recorded from the base at runtime; asserted equal on the built image
HOOK = 0x55C0E
HOOK_STOCK4 = bytes.fromhex("86ff26ef")
V282_EDIT_SITES = (0xC4B36, 0xC4B42, 0xC4B64, 0xC4B70)
PACK_LO, PACK_HI = 0x55DF0, 0x55E12
MAP_PTR, MAP_N = 0xC9A88, 10
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

# ---- [C] cells that MUST NOT move ------------------------------------------------------------------------
KI_CELL = 0xC63E6                       # the integral gain -- MUST BE 0 (this is the memoryless arm)
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,
    0xC61B6: 10240,  0xC61BA: 10240,
    0xC61BC: 15360,  0xC61BE: 15360,
    0xC63E6: 0,                             # Ki -- ZERO.  V284 is NOT V283.
    0xC63E8: 923,    0xC63EA: 1560,
    0xC63EC: 992,    0xC63EE: 507,
    0xC62E4: 4,
    0xC6B26: 256,    0xC6B12: 98,
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
    0xC6446: 5244,                          # the r24 gain arm -- the 20 Hz creep lever, not this build's
    0xC62E6: 46080,                         # the feedback clamp (V280 rev 2's edit)
}

OK, BAD = "[PASS]", "[FAIL]"
# ASSERTION CENSUS -- the V274 lesson: 720/720 passing assertions coexisted with a false central claim.
#   S = SUBSTANTIVE   -- can fail on a real defect and is entailed by nothing already asserted.
#   V = VACUOUS       -- a read of the BASE image against a constant; entailed by BASE_SHA.
#   T = TAUTOLOGICAL  -- reads back, at the same address, the value this script just wrote.
#   R = REDUNDANT     -- true by construction given an assertion that already passed earlier in this run
#                        (chiefly: everything asserted on `dec` after `dec == code` has been proved).
_census = {"S": 0, "V": 0, "T": 0, "R": 0}
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


def kp_lerp(X, Y, idx):
    """The Kp lookup, mirroring FUN_00028ea6 0x29DE8-0x29E32 instruction for instruction.
    X/Y are the five u16 words as read from the image (ld.hu -> zero-extended).
    """
    idx &= 0xFFFF                                   # 0x29DE8  zxh r7
    if not (idx > X[0]):                            # 0x29DEA  cmp r9,r7 ; bh   (unsigned)
        return Y[0]                                 # 0x29DEE  ld.hu 0x0,r10,r9      [LOW CLAMP]
    if idx >= X[4]:                                 # 0x29DF6  cmp r6,r7 ; bnc  (unsigned)
        return Y[4]                                 # 0x29E04  ld.hu 0x8,r10,r9      [HIGH CLAMP]
    i = 1                                           # 0x29DFA/0x29E0A  walk while idx >= X[i]
    while idx >= X[i]:
        i += 1
    num = (idx - X[i - 1]) * (Y[i] - Y[i - 1])      # 0x29E24 sub ; 0x29E20 sub ; 0x29E26 mul
    den = X[i] - X[i - 1]                           # 0x29E2A sub          <- THE divq DIVISOR
    q = -((-num) // den) if num < 0 else num // den  # 0x29E2C divq -- SIGNED, TRUNCATES TOWARD ZERO
    return (Y[i - 1] + q) & 0xFFFF                  # 0x29E30 add ; 0x29E32 zxh


def curve(X, Y, n=256):
    return [kp_lerp(X, Y, i) for i in range(n)]


def independent_rebuild(base):
    """A second, minimal implementation with none of build()'s bookkeeping: walk the pointer, pack the ten
    halfwords straight in, then re-CRC every block touched via FF.crc_block_map (not a hardcoded address)."""
    img = bytearray(base)
    p = u32(img, KP_PTR + 4 * LIVE_SLOT)
    assert u16(img, p) == 5
    touched = set()
    for i in range(5):
        for off, v in ((2 + 2 * i, NEW_KP_X[i]), (12 + 2 * i, NEW_KP_Y[i])):
            struct.pack_into("<H", img, p + off, v)
            touched |= {p + off, p + off + 1}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 112)
    print("  V284 -- V282 (Ki 0) + M8*: the live Kp record 0xE5378 reshaped on BOTH axes.  SLOT 7 ONLY.")
    print("=" * 112)

    # =========================================================================================
    print("\n  [1] BASE = V282  (NOT V283 -- Ki must be 0)")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V282 base sha256 matches", "S")
    check(len(base) == 0x100000, "base is 1,048,576 bytes", "V")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in sorted(FROZEN.items()):
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    check(u16(base, KI_CELL) == 0,
          "base Ki (0xC63E6) == 0 -- the base is V282, the MEMORYLESS arm, not V283's Ki 50", "V")

    print("\n  [1b] THE LIVE RECORD, REACHED BY WALKING THE POINTER TABLE (never by a contiguous stride)")
    p7 = u32(base, KP_PTR + 4 * LIVE_SLOT)
    check(p7 == LIVE_KP_REC, f"u32(0x{KP_PTR:05X} + 4*{LIVE_SLOT}) == 0x{p7:05X} (expected 0x{LIVE_KP_REC:05X})", "V")
    n7, X7, Y7 = rec(base, p7)
    check(n7 == 5 and tuple(X7) == BASE_KP_X and tuple(Y7) == BASE_KP_Y,
          f"base live record: n={n7} X={tuple(X7)} Y={tuple(Y7)} (V281 rev 3's flat 248)", "V")
    check(u16(base, p7 + 0x16) == 0, "base record pad at rec+0x16 == 0", "V")
    ptrs = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    check(len(set(ptrs)) == N_SLOTS, f"all {N_SLOTS} Kp record pointers are DISTINCT (no aliasing onto slot 7)", "S")
    check(sorted(ptrs) != [ptrs[0] + 0x18 * i for i in range(N_SLOTS)],
          "the records are NOT contiguous at stride 0x18 -- a contiguous model would be wrong "
          f"(pointers span 0x{min(ptrs):05X}-0x{max(ptrs):05X})", "S")
    pages = sorted({q & ~0xFFF for q in ptrs})
    check(tuple(pages) == KP_PAGES, f"the 28 records live on exactly {len(pages)} pages: "
          f"{', '.join(f'0x{q:05X}' for q in pages)}", "S")
    check(all(not (p7 <= q < p7 + 0x18) for q in ptrs if q != p7),
          "no other record overlaps slot 7's 24 bytes", "S")

    print("\n  [1c] THE OTHER FOUR PAGES' CRC TRAILERS -- recorded now, asserted UNCHANGED in [5]")
    crc_before = {q: u32(base, q + 0xFFC) for q in KP_PAGES}
    for q in KP_PAGES:
        print(f"      page 0x{q:05X}  trailer 0x{q + 0xFFC:05X} = 0x{crc_before[q]:08X}"
              f"{'   <- the ONLY page this build touches' if q == EDIT_PAGE else ''}")

    print("\n  [1d] THE X-KNOT PRECEDENT -- V281 rev 2, read from the SUPERSEDED image on disk")
    rev2_path = Path(plain_image_path(REV2_NAME))
    if rev2_path.exists():
        rev2 = rev2_path.read_bytes()
        p7r2 = u32(rev2, KP_PTR + 4 * LIVE_SLOT)
        _, X2, Y2 = rec(rev2, p7r2)
        check(p7r2 == LIVE_KP_REC, f"rev 2's pointer resolves to the SAME record 0x{p7r2:05X}", "S")
        check(tuple(X2) == REV2_KP_X and tuple(Y2) == REV2_KP_Y,
              f"rev 2 record: X={tuple(X2)} Y={tuple(Y2)} -- an X edit on this record HAS been built before", "S")
        moved = [a for a in range(LIVE_KP_REC, LIVE_KP_REC + 0x18) if rev2[a] != base[a]]
        check(0xE537C in moved and 0xE537E in moved,
              f"rev 2 wrote 0xE537C (X[1]) and 0xE537E (X[2]) -- exactly two of the offsets this build "
              f"also writes; rev-2-vs-base differs at {len(moved)} bytes of the record", "S")
    else:
        check(False, f"the V281 rev 2 superseded image is on disk at {rev2_path}", "S")

    # =========================================================================================
    print("\n  [2] THE EDIT -- slot 7's ten knot halfwords, and NOTHING else")
    check(tuple(sorted(NEW_KP_X)) == NEW_KP_X and len(set(NEW_KP_X)) == 5,
          f"constants gate: X {NEW_KP_X} is STRICTLY INCREASING (divq at 0x29E2C divides by X[i]-X[i-1])", "S")
    check(min(NEW_KP_X[i + 1] - NEW_KP_X[i] for i in range(4)) >= 4,
          f"constants gate: narrowest segment width = "
          f"{min(NEW_KP_X[i + 1] - NEW_KP_X[i] for i in range(4))} (>=4, non-zero divisor with margin)", "S")
    check(NEW_KP_X[0] == 0 and NEW_KP_X[1] >= 32,
          f"constants gate: the bump starts at idx {NEW_KP_X[1]} >= 32, so idx 0-32 (18.2 % of engaged time, "
          f"the lane-change band) is untouched", "S")
    check(max(NEW_KP_Y) == 512 and NEW_KP_Y[0] == NEW_KP_Y[1] == NEW_KP_Y[4] == 248,
          f"constants gate: Y {NEW_KP_Y} -- peak 512, both shoulders back to today's 248", "S")

    code = bytearray(base)
    attributed = set()
    for i in range(5):
        for off, v in ((2 + 2 * i, NEW_KP_X[i]), (12 + 2 * i, NEW_KP_Y[i])):
            struct.pack_into("<H", code, p7 + off, v)
            attributed |= {p7 + off, p7 + off + 1}
    nb, Xb, Yb = rec(code, p7)
    check(nb == 5 and tuple(Xb) == NEW_KP_X and tuple(Yb) == NEW_KP_Y,
          f"record written: n={nb} X={tuple(Xb)} Y={tuple(Yb)}", "T")
    check(u16(code, p7) == u16(base, p7) == 5, "the COUNT word at rec+0x00 is UNTOUCHED (5)", "S")
    check(u16(code, p7 + 0x16) == u16(base, p7 + 0x16) == 0, "the PAD at rec+0x16 is UNTOUCHED (0)", "S")
    check(len(attributed) == 20, f"exactly 20 record bytes were written ({len(attributed)})", "S")

    # =========================================================================================
    print("\n  [3] EVERYTHING ELSE BYTE-IDENTICAL TO V282, BEFORE THE CRC RECOMPUTE")
    outside = [a for a in range(START, END) if a not in attributed and code[a] != base[a]]
    check(outside == [], f"no byte outside slot 7's record changed ({len(outside)} stray diffs)", "S")
    for a, v in sorted(FROZEN.items()):
        check(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}",
              "R")   # entailed by the base read in [1] + `outside == []` immediately above
    check(u16(code, KI_CELL) == 0, "Ki (0xC63E6) is STILL 0 on the built image -- V284 is the memoryless arm", "S")
    base_cave = hashlib.sha256(bytes(base[CAVE_START:CAVE_END])).hexdigest()
    check(hashlib.sha256(bytes(code[CAVE_START:CAVE_END])).hexdigest() == base_cave,
          f"the V282 cave (0x{CAVE_START:05X}-0x{CAVE_END - 1:05X}, {CAVE_END - CAVE_START} B) is "
          f"byte-identical, sha256[:8] {base_cave[:8]} -- the r24 comparator bits survive", "S")
    for a in V282_EDIT_SITES:
        check(s16(code, a) == s16(base, a) and s16(code, a) in (-0x6ADA, -0x6B38, -0x6B94),
              f"cave site 0x{a:05X} still carries its V282 displacement ({s16(code, a)})", "S")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK4,
          "hook 0x55C0E == jarl 0xc4b34,lp, byte-identical", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          f"427 delivered-torque tap window 0x{PACK_LO:05X}-0x{PACK_HI - 1:05X} byte-identical", "S")
    for q in sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)}):
        check(bytes(code[q:q + 2 + 4 * MAP_N]) == bytes(base[q:q + 2 + 4 * MAP_N]), f"assist map 0x{q:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        q = ptrs[s]
        if s == LIVE_SLOT:
            continue
        check(bytes(code[q:q + 0x18]) == bytes(base[q:q + 0x18]),
              f"Kp slot {s:2d} @0x{q:05X} byte-identical -- its own X axis {tuple(rec(base, q)[1])} preserved", "S")
    for s in range(N_SLOTS):
        q = u32(base, KD_PTR + 4 * s)
        n = u16(base, q)
        check(bytes(code[q:q + 2 + 4 * n]) == bytes(base[q:q + 2 + 4 * n]), f"Kd slot {s} @0x{q:05X} byte-identical", "S")
    tps = {u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)}
    for q in sorted(tps):
        n = s16(base, q)
        check(bytes(code[q:q + 2 + 4 * n]) == bytes(base[q:q + 2 + 4 * n]), f"taper 0x{q:05X} byte-identical", "S")

    # =========================================================================================
    print("\n  [4] THE DELIVERED GAIN SURFACE -- emulated from the DISASSEMBLY, over the BUILT IMAGE")
    _, Xr, Yr = rec(code, u32(code, KP_PTR + 4 * LIVE_SLOT))     # re-read through the pointer, not from constants
    cb, cc = curve(BASE_KP_X, BASE_KP_Y), curve(Xr, Yr)
    print("        idx    V282 (flat 248)   V284 (M8*)   ratio")
    for i in (0, 8, 16, 20, 32, 34, 36, 40, 44, 45, 54, 60, 68, 80, 88, 100, 136, 208, 240):
        print(f"        {i:3d}         {cb[i]:4d}          {cc[i]:4d}      {cc[i] / cb[i]:.3f}")
    for i, want in sorted(PREREG_CURVE.items()):
        check(cc[i] == want,
              f"gain@idx {i:3d} == {want} -- matches stutter_v283_m8_knots.py's independently-computed "
              f"A11.4 row (image-read knots, disassembly-derived emulator)", "S")
    check(all(cc[i] == cb[i] for i in range(0, NEW_KP_X[1] + 1)),
          f"idx 0-{NEW_KP_X[1]} UNCHANGED at 248 -- the lane-change band is not touched", "S")
    check(all(cc[i] == cb[i] for i in range(NEW_KP_X[4], 256)),
          f"idx {NEW_KP_X[4]}-255 UNCHANGED at 248 -- the ring's upper mass and every high-index frame "
          f"see exactly what is on the car today", "S")
    changed = [i for i in range(256) if cc[i] != cb[i]]
    check(changed and min(changed) == NEW_KP_X[1] + 1 and max(changed) == NEW_KP_X[4] - 1,
          f"the gain changes on EXACTLY idx {min(changed)}-{max(changed)} ({len(changed)} of 256 indices)", "S")
    check(all(cc[i] >= cb[i] for i in range(256)), "the gain never DROPS at any index -- no band loses authority", "S")
    check(max(cc) == 512, f"peak delivered Kp == {max(cc)} (2.06x today's 248)", "S")
    stock_curve = curve(BASE_KP_X, STOCK_KP_Y)
    check(max(cc) < max(stock_curve),
          f"peak Kp {max(cc)} < the STOCK LERP peak {max(stock_curve)} that flew on r32/r33/r34 -- "
          f"this build stays inside gain that has already been on the car", "S")
    check(all(cc[i] <= max(stock_curve) for i in range(256)), "no index exceeds the stock LERP's peak", "S")
    # strictly-increasing gate re-asserted on the IMAGE, not the constants
    check(all(Xr[i] < Xr[i + 1] for i in range(4)),
          f"IMAGE X {tuple(Xr)} strictly increasing -- divq at 0x29E2C has a non-zero divisor at every knot", "S")
    check(min(Xr[i + 1] - Xr[i] for i in range(4)) > 0, "every segment width read from the image is > 0", "S")
    # cross-check the stock record on the grandparent image, so STOCK_KP_Y is not a remembered number
    gp_img = Path(plain_image_path(GRANDPARENT_NAME)).read_bytes()
    check(hashlib.sha256(gp_img).hexdigest() == GRANDPARENT_SHA, "V280 rev 2 image sha256 matches", "S")
    _, Xg, Yg = rec(gp_img, u32(gp_img, KP_PTR + 4 * LIVE_SLOT))
    check(tuple(Yg) == STOCK_KP_Y and tuple(Xg) == BASE_KP_X,
          f"the stock/flown LERP on the V280 rev 2 IMAGE is X={tuple(Xg)} Y={tuple(Yg)} -- the 696 ceiling "
          f"is read, not remembered", "S")

    # =========================================================================================
    print("\n  [5] CRC TRAILER -- located GENERICALLY via V53.owning_block")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    check(len(blocks) == 1, f"exactly ONE CRC block owns the whole edit ({blocks})", "S")
    b0, b1 = blocks[0]
    check(b0 == EDIT_PAGE and b1 == EDIT_PAGE + 0xFFC,
          f"block is [0x{b0:05X},0x{b1:05X}) -- the slot 6-11 page, ONE of the five record pages", "S")
    check(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:05X}", "S")
    oldc = u32(code, b1)
    newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    check(newc != oldc, f"block [0x{b0:05X},0x{b1:05X}) CRC actually moved", "S")
    struct.pack_into("<I", code, b1, newc)
    attributed |= set(range(b1, b1 + 4))
    print(f"      Kp page [0x{b0:05X},0x{b1:05X})  trailer 0x{b1:05X}  0x{oldc:08X} -> 0x{newc:08X}")
    for q in KP_PAGES:
        if q == EDIT_PAGE:
            continue
        check(u32(code, q + 0xFFC) == crc_before[q],
              f"page 0x{q:05X} CRC trailer UNCHANGED (0x{crc_before[q]:08X}) -- slot-7-only kept the CRC "
              f"surface to one page of five", "S")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # =========================================================================================
    print("\n  [6] FULL-FILE BYTE DIFF vs V282")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(set(diff) <= attributed, f"every one of the {len(diff)} differing bytes is a written record byte "
          f"or the page CRC trailer", "S")
    expect_payload = sum(1 for i in range(5) for off, ov, nv in
                         ((2 + 2 * i, BASE_KP_X[i], NEW_KP_X[i]), (12 + 2 * i, BASE_KP_Y[i], NEW_KP_Y[i]))
                         for j in (0, 1) if struct.pack("<H", ov)[j] != struct.pack("<H", nv)[j])
    check(expect_payload == 8,
          f"of the 20 written record bytes, exactly {expect_payload} actually CHANGE value "
          f"(X[1..4] low bytes = 4, Y[2]/Y[3] both bytes = 4; X[0], Y[0], Y[1], Y[4] and every high byte "
          f"of X are already correct)", "S")
    check(len(diff) == expect_payload + 4,
          f"total diff vs V282 == {expect_payload} payload + 4 CRC = {expect_payload + 4}, got {len(diff)}", "S")
    check(all(LIVE_KP_REC <= a < LIVE_KP_REC + 0x18 or b1 <= a < b1 + 4 for a in diff),
          "every differing byte is inside slot 7's 24-byte record or the one 4-byte trailer", "S")
    for s, e in runs(diff):
        kind = f"page CRC trailer 0x{b1:05X}" if s == b1 else f"0xE5378 record +0x{s - LIVE_KP_REC:02X}"
        print(f"      0x{s:05X}-0x{e - 1:05X} ({e - s:2d} B)  {kind:28s}  "
              f"{bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")
    print(f"      runs: {len(runs(diff))}   bytes: {len(diff)}   "
          f"(payload {expect_payload} + CRC 4)")

    print("\n  [6b] CROSS-IMAGE -- V284 must be V282 + this edit, and must NOT resemble V283")
    parent = Path(plain_image_path(PARENT_NAME)).read_bytes()
    check(hashlib.sha256(parent).hexdigest() == PARENT_SHA, "V281 rev 3 image sha256 matches", "S")
    d_v282_par = {a for a in range(START, END) if base[a] != parent[a]}
    d_par_gp = {a for a in range(START, END) if parent[a] != gp_img[a]}
    d_v284_gp = {a for a in range(START, END) if code[a] != gp_img[a]}
    sites = d_v282_par | d_par_gp | set(diff)
    check(d_v284_gp <= sites,
          f"V284 vs V280 rev 2 ({len(d_v284_gp)} B) introduces NO byte outside the three known deltas: "
          f"V282's cave ({len(d_v282_par)} B) + V281 rev 3's Kp-Y ({len(d_par_gp)} B) + this build "
          f"({len(diff)} B), {len(sites)} distinct addresses", "S")
    reverted = sorted(a for a in sites if code[a] == gp_img[a])
    check(d_v284_gp == sites - set(reverted),
          f"...and every one of those addresses differs from V280 rev 2 except the {len(reverted)} that "
          f"this build coincidentally restores to the stock byte", "S")
    check(reverted == [LIVE_KP_REC + 0x11, LIVE_KP_REC + 0x13],
          f"the restored bytes are exactly the HIGH bytes of Y[2]/Y[3] "
          f"({', '.join(f'0x{a:05X}' for a in reverted)}) -- 512 (0x0200) shares its high byte 0x02 with "
          f"the stock 645 (0x0285) and 696 (0x02B8); a coincidence of encoding, not a reverted lever", "S")
    sib = Path(plain_image_path(SIBLING_NAME))
    if sib.exists():
        v283 = sib.read_bytes()
        check(u16(v283, KI_CELL) == 50, "the V283 sibling image on disk carries Ki = 50", "S")
        check(u16(code, KI_CELL) == 0, "V284 carries Ki = 0 -- the two arms differ in the integral term", "S")
        _, X83, Y83 = rec(v283, u32(v283, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(X83) == BASE_KP_X and tuple(Y83) == BASE_KP_Y,
              "the V283 sibling carries flat 248 with stock X -- V284 changes the Kp SHAPE where V283 "
              "changed the TERM; the pair is a matched contrast", "S")
        d_284_283 = {a for a in range(START, END) if code[a] != v283[a]}
        d_283_base = {a for a in range(START, END) if v283[a] != base[a]}
        check(d_284_283 == set(diff) | d_283_base,
              f"V284 vs V283 == this build's {len(diff)} bytes UNION V283's own {len(d_283_base)}-byte Ki+CRC "
              f"delta ({len(d_284_283)} B), disjoint -- the two arms share the V282 base exactly", "S")
        check(not (set(diff) & d_283_base), "the two arms' edits do not overlap a single byte", "S")
    else:
        print(f"      (V283 sibling image not on disk at {sib} -- cross-check skipped)")

    # =========================================================================================
    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V284 output")
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

    # =========================================================================================
    print("\n  [8] END STATE -- re-read from the FINAL image AND from the DECODED .rwd")
    # `dec` was already proved byte-identical to `code` in [7]; every check on it is therefore REDUNDANT.
    # It is kept because it is the only path that would survive a change to the encode/decode table.
    for nm, im in (("code", code), ("dec ", dec)):
        kind = "T" if nm == "code" else "R"
        pp = u32(im, KP_PTR + 4 * LIVE_SLOT)
        nn, XX, YY = rec(im, pp)
        check(pp == LIVE_KP_REC and nn == 5 and tuple(XX) == NEW_KP_X and tuple(YY) == NEW_KP_Y,
              f"{nm}: slot 7 @0x{pp:05X} n={nn} X={tuple(XX)} Y={tuple(YY)}", kind)
        check(all(XX[i] < XX[i + 1] for i in range(4)), f"{nm}: X strictly increasing (divq gate)",
              "R" if nm != "code" else "S")
        cx = curve(XX, YY)
        check(all(cx[i] == PREREG_CURVE[i] for i in sorted(PREREG_CURVE)),
              f"{nm}: gain curve at {sorted(PREREG_CURVE)} == {[PREREG_CURVE[i] for i in sorted(PREREG_CURVE)]}",
              "R")
        check(u16(im, KI_CELL) == 0, f"{nm}: Ki (0xC63E6) == 0", "R")
        for a, v in sorted(FROZEN.items()):
            check(u16(im, a) == v, f"{nm}: 0x{a:05X} == {v}", "R")
        check(hashlib.sha256(bytes(im[CAVE_START:CAVE_END])).hexdigest() == base_cave,
              f"{nm}: V282 cave hash-identical ({base_cave[:8]})", "R")
        check(bytes(im[HOOK:HOOK + 4]) == HOOK_STOCK4, f"{nm}: hook untouched", "R")
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: 427 tap window untouched", "R")
        for s in range(N_SLOTS):
            if s == LIVE_SLOT:
                continue
            check(bytes(im[ptrs[s]:ptrs[s] + 0x18]) == bytes(base[ptrs[s]:ptrs[s] + 0x18]),
                  f"{nm}: Kp slot {s:2d} untouched", "R")
        for q in KP_PAGES:
            if q == EDIT_PAGE:
                continue
            check(u32(im, q + 0xFFC) == crc_before[q], f"{nm}: page 0x{q:05X} CRC unchanged", "R")
        # pin the table to the STUDY, not to this file's constants
        _st = (Path(__file__).resolve().parents[3] / "rlog-tools" / "studies" / "osc-highangle"
               / "STUTTER-7HZ-V283-r36-r38-2026-09-03.md")
        import re as _re
        _m = _re.search(r"M8★ = `0xE5378` X \[([\d, ]+)\] · Y \[([\d, ]+)\]", _st.read_text(encoding="utf-8"))
        check(_m is not None
              and tuple(int(t) for t in _m.group(1).split(",")) == tuple(XX)
              and tuple(int(t) for t in _m.group(2).split(",")) == tuple(YY),
              f"{nm}: the record ON THE IMAGE == the M8* table specified in "
              f"STUTTER-7HZ-V283-r36-r38-2026-09-03.md A11.4 "
              f"(X {_m.group(1) if _m else '?'} / Y {_m.group(2) if _m else '?'})",
              "S" if nm == "code" else "R")

    # =========================================================================================
    print("\n  [9] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild (direct pointer-walk + generic re-CRC, no shared state) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # =========================================================================================
    _scr = os.environ.get("ACCORD_V284_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v284_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v284_{TAG}.rwd").write_bytes(rwd)
        print(f"\n      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(f"_v284_{TAG}_plain_image.bin"))
        out_rwd = Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        others = [f.name for f in Path(RWD_DIR).glob("*V284*.rwd") if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"exactly ONE flashable V284 rwd on disk (others: {others})", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V284_WRITE=rwd to emit the files")

    print("\n" + "=" * 112)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- CENSUS: {_census['S']} SUBSTANTIVE  |  "
          f"{_census['V']} vacuous (entailed by the base sha256)  |  {_census['T']} tautological "
          f"(readback of a write)  |  {_census['R']} redundant (entailed by an assertion that already "
          f"passed above -- chiefly the `dec` arm, which `dec == code` in [7] already settles)")
    print("  ** V284 -- the live Kp record 0xE5378 reshaped on BOTH axes: X (0,68,112,136,208)->(0,32,36,44,88), **")
    print("  ** Y (248x5)->(248,248,512,512,248).  SLOT 7 ONLY -- one page CRC of five.  Ki stays 0.           **")
    print("  ** 512 on the low, small-error, stall-heavy band (idx 33-87); exactly 248 everywhere else.        **")
    print("  ** Instrument: the 427 tap, read by v283_read_r36_r38.py sec.1b's window-local corr/scale, with   **")
    print("  ** the 112-241 index cell as a built-in negative control (identical to flat 248 there).           **")
    print("=" * 112)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
