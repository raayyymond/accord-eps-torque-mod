# -*- coding: utf-8 -*-
r"""V278 rev 3 -- THE REFERENCE BROUGHT BACK INTO REACH.  K = 2.  BASE: V268.  Plus the DELIVERED-TORQUE tap.

=== REV 3 (2026-09-02) ===========================================================================
Same two cal edits as rev 2 ([A] map x2, [B] feedback clamp x2).  The 34-byte packer window is now
V279 rev 2's DELIVERED-TORQUE tap instead of rev 2's damping comparator, because the operator's
open question -- "should the P/sum clamps be WIDENED?" -- needs the SATURATION duty, which the
comparator cannot read and T reads directly (T at its 2505 ceiling <=> the sum clamp is railed).
The damping fraction is NOT lost: sign(T) != sign(0x18F rate) is the lane opposing the wheel (the
full sign chain is under [C]).  One tap, both questions, one drive.
Rev 2 (image 4bc51073...) is SUPERSEDED-DO-NOT-FLASH.  The window bytes are byte-identical to
V279 rev 2's (asserted against that image); the cal region is byte-identical to rev 2's (asserted).


=== WHY THIS BUILD EXISTS ======================================================================
V276 (reference x6) FLEW on 2026-09-01.  Operator: "Amazing authority now on turns as I would like
on 6x torque.  However, there is now a large, slower (2-4 Hz) oscillation when LKAS engaged ...
excites itself even on straight roads.  Only way to stop it is to hold the steering wheel very firmly."

THE MECHANISM (EVIDENCE, from the bytes and from his rlog r2e):
  E = 32*setpoint - feedback   at 0x29d78.   E > 0 the lane PUSHES.   E < 0 the lane DAMPS.
  Kp, Kd, the forward gain (0xC6CD0 = 5346) and the cap (0xC61B4 = 3072) are byte-identical
  V268 -> V276.  V276 scaled the setpoint AND the feedback clamp by 6, so the rate at which E can go
  negative moved OUT OF PHYSICAL REACH: the loop can no longer change sign, so it never damps.
  His log: a 3.9 Hz amplitude-modulated sinusoid (Q 4, rate excess 4.58 vs corpus median 0.83,
  no flown build has this mode), openpilot's command following the MEASURED angle with coh >= 0.97
  while its desired path is flat -- a COMBINED-loop instability: an EPS lane that never damps plus
  openpilot's outer follower.  The same openpilot did not ring before V276.

THE DOSE, SIZED FROM HIS OWN DRIVE -- frame by frame, not from the map's ceiling.
The feedback operand r26 at 0x29d78 is s_old + s_new of the lag filter (add r9,r26 @0x28FA4 --
verified by the orchestrator), DC gain 2*1560/101 = 30.89 per raw count; the 0x18F wire is
-gp-0x6a56 at 1:1 and 8 counts/deg/s (measured on the log, corr 0.997).  So stock's crossover at
the map's CEILING is 5504/30.89 = 178 wire = 22.3 deg/s -- the inherited figure, reconciled.
But the ceiling is the wrong operating point: during the straight-road oscillation openpilot's
command is only +-300-1300 counts (median 354 -> demand index 22 -> Y 46, not 172), so the
crossover during the oscillation is command-dependent and far lower.  Computed on all 7 episodes
(87 half-cycle peaks) and on normal engaged driving, with the real command, the real rate, the exact
filter and the taper (rlog-tools/studies/osc-2to4/dose_e_sign_by_k.py):

    K    OSC frames: lane OPPOSES wheel    NORMAL engaged: lane opposes wheel
    1            0.94                              0.80        <- stock: no oscillation
    1.5          0.90                              0.75
  * 2            0.86                              0.70
    2.5          0.82                              0.65
    3            0.78                              0.61
    6            0.57                              0.48        <- V276: oscillates

THE MECHANISM IS A MATTER OF DEGREE, NOT A THRESHOLD.  V276 did not stop damping outright; it
cut the fraction of oscillation time in which the lane opposes the wheel from 0.94 to 0.57, and
the combined loop (EPS lane + openpilot's follower) went unstable somewhere in between.  K=2
restores 0.86 of it while keeping the ceiling crossover at 44.5 deg/s (stock 22.3, V276 134) --
so on turns the lane still pushes through the median achieved rate (~27 deg/s) where stock yielded.
The crossover does NOT cap the oscillation's amplitude (V276's peaks overshot theirs 1.5-2x), so a
residual, if any, is not predicted to settle at a particular size.  K=1.5 (0.90) is the fallback.
PEAK TORQUE IS UNTOUCHED AT EVERY K.  The 6x TORQUE (V112: gain redirect + 0xC61B4) stays.

=== THE CELLS ==================================================================================
  [A] ASSIST MAP  -- the 28 LERP records reached via the pointer family 0xC9A88 (data at
      0xE4000-0xE8105): every Y knot xK from the V268 (stock-shape) base.  Honda's SHAPE preserved.
      All 28 dosed, as V276 did; the live slot is 7 (record 11, TVCA4, selector 7 -- CONFIRMED on
      the V276 wire, 35 = 7x5, 46,576/46,576 frames, two decoders).  Slot 7 ceiling 172 -> 344.
  [B] FEEDBACK CLAMP  0xC62E6:  7680 -> 7680*K (stored x256: 30 -> 60).  Ratio 1.395 preserved --
      STRUCTURALLY, because the clamp bounds the same r26 that is subtracted at 0x29d78.
  [C] TELEMETRY -- the CAN-427 packer 0x55DF0-0x55E11 rewritten IN PLACE, 34 bytes, same length,
      jarl 0x55E12 (-> 0x49A90 clamp) untouched -- V279 rev 2's window, byte-identical:
          wire = (sign(T) << 9) | (|T| >> 3)        T = gp-0x6b38 = the DELIVERED lane torque
      T = clamp(-lane x 5346 >> 15, +-3072), st.h r1 @0x2A23C every tick (the added term gp-0x6b2c
      is provably zero: all-zero table + a gate with no writer).  Resolution 8 counts; the 2505
      ceiling 15360 x 5346 >> 15 = 2505 is NEVER reached: the output lag's readout (s_old+s_new)>>5 has DC
      2*507/32/32 = 0.990, so a railed sum delivers 15210 x 5346 >> 15 = 2481, which READS 310 (adv278r3c,
      confirmed by the orchestrator from 0xC63EC/EE).  A reading of 313 would refute the arithmetic.
      Decode T = (-1 if bit9 else 1) * ((w & 0x1ff) << 3).
      SATURATION duty = fraction of engaged frames with |T| >= 2472 (wire |field| >= 309).
      DAMPING fraction = fraction of engaged frames with sign(T) != sign(0x18F rate).  Sign chain, each link
      from the bytes (adv278r3b + orchestrator): T = -lane (gp-0x6752 = -1, gain 5346 > 0, no other negation
      0x2A1FC..0x2A23C); lane has the sign of E (every Kp knot 205..717 and Kd knot 64..128 positive on all
      28 records, lag coefs positive); fb has the sign of gp-0x6a56 (two-sample sum, DC +30.89); the 0x18F
      wire = -gp-0x6a56.  damping <=> sign(E) != sign(fb) <=> sign(T) != sign(wire).  An earlier draft of
      this docstring had `==` -- that reads PUMPING.
      r9 is never saved by the packer's prologue; r6/r7/r8/r10 are dead scratch; abs touches only
      r6, r10, lp.  4 trailing nop.  This REPLACES V112's gp-0x6abc tap on 427 (V268's window).

=== THE SENTENCE A NULL LICENSES ===============================================================
Two duties from one drive, both from the T field:  DAMPING = P(sign(T) != sign(0x18F rate)) over engaged
frames, and SATURATION = P(|T| >= 2472, i.e. |field| >= 309).
PRE-REGISTERED (rlog-tools/studies/osc-2to4/PREREG-V278R3-CLAMP-READ.md, simulated on the V276 log with
the exact chain): the tap's damping read is LOWER than the rev-2 comparator's 0.86 because T lags E through
the 5.05 Hz output lag (~38 deg at 3.9 Hz): predicted 0.68 in an oscillation / 0.60 normal at K=2, versus
0.37 / 0.40 at K=6 (V276).  Predicted saturation at K=2: 0.000 osc / 0.004 normal -- the PRE-REGISTERED
answer to the clamp question is "do not widen"; a reading of SAT >= 0.05 refutes it.
Also corrected here: P = E x Kp >> 8 with E = 32 x sp - fb -- ONE factor 32 (decompile lines 975/1034/1036,
confirmed by the orchestrator).  P rails at |E| = 15360 x 256 / Kp = 15855 operand counts (64 deg/s) at
Kp 248, 5650 (22.9 deg/s) at Kp 696 -- NOT at 440.  The "bang-bang servo" memory carried a second x32.
  damping ~0.86, oscillation gone           -> mechanism confirmed; then read saturation:
      saturation high  -> the clamps 0xC61BC/0xC61BE are the binding constraint -> widen next
      saturation low   -> the linear band is adequate at K=2 -> leave the clamps
  damping ~0.86, oscillation persists       -> the damping fraction is not the whole mechanism;
                                               openpilot's follower gain is the other term
  damping low (~0.57), saturation low       -> K still too high, not the clamps -> K=1.5
  damping low AND saturation high           -> saturation is eating the damping -> clamps, not K
  T reads 0 while engaged                   -> the tap or the lane is dead; the map bytes decide.
No outcome is uninterpretable.  The delivered surface (T vs 0xE4 command) comes for free.

=== RISK, PLAINLY ==============================================================================
This is a REDUCTION of a live gain -- the third in ~240 builds, and the first in response to a
symptom a build of ours created.  The two prior reductions (V93/V94) made the car worse.  The felt
authority on turns WILL be less than V276's; it should be clearly more than stock's.  The
oscillation may shrink rather than vanish (see above).  The override taper is byte-stock, so the
operator's escape hatch (a firm grip at ~2500 raw, where the cliff begins) is unchanged.

=== CLASS OF BUILD =============================================================================
The same lever as V276 (the reference), pushed the OTHER way, sized from the operator's own drive
rather than guessed -- plus the first tap in this kit that puts the DELIVERED lane torque on the wire.
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

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V278R3_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
K = 2                                                   # the reference scale -- THE dose
TAG = f"V278R3-V268BASE-REFERENCE{K}X.MAP.FEEDBACK.TORQUE.TAP"
REV2_IMAGE = "SUPERSEDED_v278_rev2_SIGNE.TAP_plain_image.bin"        # rev 2 (renamed SUPERSEDED 2026-09-02): same cals, comparator tap
REV2_SHA = "4bc510734c7b53fcdb242a28ce97149ecb4eb86fd2da1f4a39dbedff2865a22c"
V279_IMAGE = "_v279_V279-V268BASE-PURE.FEEDFORWARD.FB0.KD0.LINEAR.TORQUE.TAP_plain_image.bin"  # rev 2: same window, other cals
V279_SHA = "a165b1a59307ab67867fd5488c287a2271d51e322ff601d527853712ea423485"

# ---- [A] assist map --------------------------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
LIVE_SLOTS = (0, 1, 3, 4, 6, 7, 8, 9)                   # selector max 9; 2 and 5 are dead shapes
LIVE_SLOT = 7                                           # record 11 TVCA4 -- on the wire, 35 = 7x5
MAP_CHANGED_EXPECT = 378                                # 28 x 9 nonzero knots: 252 low bytes + 126 high bytes (x2 of Y<128 leaves the high byte 0) -- audited

# ---- [B] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK = 0xC62E6, 7680
FB_NEW = FB_STOCK * K
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)                  # must all be ld.hu (low byte 0xe5)

# ---- [C] the packer --------------------------------------------------------------------------
PACK_LO, PACK_HI, JARL_CLAMP = 0x55DF0, 0x55E12, 0x55E12
PACK_V268 = bytes.fromhex("24374495bfff663c0a30803effffbfff7a3cca36ffff"
                          "e53740022046ff03003aa332")
PACK_NEW = bytes.fromhex(
    "2437c894"      # ld.h  -0x6b38[gp],r6    T = delivered lane torque (signed 16)
    "0648"          # mov   r6,r9             signed copy, taken BEFORE the abs call
    "bfff643c"      # jarl  0x49a5a           abs  (site moved +2; target unchanged)
    "0a30"          # mov   r10,r6            |T|
    "a332"          # sar   0x3,r6            |T| >> 3   (<= 384)
    "9f4a"          # shr   0x1f,r9           sign(T) -> 0/1
    "c94a"          # shl   0x9,r9            -> bit 9
    "0931"          # or    r9,r6
    "2046ff03"      # movea 0x3ff,r0,r8       clamp hi (unchanged)
    "003a"          # mov   0x0,r7            clamp lo (unchanged)
    "0000000000000000")   # 4 x nop
T_CELL_DISP, T_STORE_SITE, T_STORE_BYTES = -0x6b38, 0x2A23C, bytes.fromhex("640fc894")   # st.h r1,-0x6b38,gp
ABS_FN = 0x49A5A
E_STORE_SITE, E_STORE_BYTES = 0x2A18C, bytes.fromhex("64870993")   # E cell no longer tapped in rev 2; store still asserted untouched
SEL_WRITER, DEMAND_WRITER = 0x4272A, 0x29D14

# ---- frozen torque path, all asserted --------------------------------------------------------
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,     # output cap / forward gain -- the 6x TORQUE, untouched
    0xC61B6: 10240,  0xC61BA: 10240,    # D clamp / I anti-windup
    0xC61BC: 15360,  0xC61BE: 15360,    # P clamp / SUM clamp -- 0xC61BE is the REAL 2505 ceiling
    0xC63E6: 0,                         # Ki OFF
    0xC63E8: 923,    0xC63EA: 1560,     # feedback lag  (16.5 Hz)
    0xC63EC: 992,    0xC63EE: 507,      # output lag    (5.05 Hz)
    0xC62E4: 4,                         # error deadband
    0xC6B26: 256,    0xC6B12: 98,       # the OTHER PID (driver-side)
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
}
GAIN_SITE = 0x2A1EE
CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1
KP_PTR, KD_PTR, KP_N, KD_N = 0xCB994, 0xCB7D4, 5, 4
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

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


# ---- V850 field decoders, used to PROVE the written bytes are the instructions claimed ---------
def f_I(hw):                      # Format I:  reg2<<11 | op<<5 | reg1
    return hw >> 11, (hw >> 5) & 0x3F, hw & 0x1F


def f_II(hw):                     # Format II: reg2<<11 | op<<5 | imm5
    r2, op, imm = f_I(hw)
    return r2, op, imm


def dec_ld(img, a):               # ld.bu / ld.w gp-relative: returns (mnemonic, reg2, disp)
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    if op in (0x3C, 0x3D):
        disp = (hw2 & ~1) | (op & 1)          # ld.bu: hw2 = disp|1, TRUE bit0 lives in the opcode
        if disp & 0x8000:
            disp -= 0x10000
        return "ld.bu", r2, r1, disp
    if op == 0x39 and hw2 & 1:
        disp = hw2 & ~1
        if disp & 0x8000:
            disp -= 0x10000
        return "ld.w", r2, r1, disp
    return "?", r2, r1, None


def dec_ld_h(img, a):              # ld.h gp-relative: op 0x39 with EVEN hw2 -> (reg2, reg1, disp)
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    if op != 0x39 or (hw2 & 1):
        return None
    return r2, r1, hw2 - 0x10000 if hw2 & 0x8000 else hw2


def dec_imm16(img, a):
    hw1, imm = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    return op, r2, r1, imm


def jarl_target(addr, img, require_lp=True):
    """Format V jarl: reg2 (hw1[15:11]) is the link register. reg2 == r0 is `jr` and reg2 != lp never
    returns to the caller -- a `jr 0x49A5A` here would make the abs helper's `jmp [lp]` return to the
    PACKER'S caller, silently skipping the rest of the window. Audit finding adv279d(a)."""
    hw1, hw2 = u16(img, addr), u16(img, addr + 2)
    if (hw1 >> 6) & 0x1F != 0b11110:
        return None
    if require_lp and (hw1 >> 11) != 31:
        return None
    disp = (((hw1 & 0x3F) << 16) | hw2) & ~1
    if disp & (1 << 21):
        disp -= 1 << 22
    return addr + disp


def jump_targets(img):
    out = {}
    for a_ in range(START, END - 4, 2):
        hw1 = u16(img, a_)
        if (hw1 >> 6) & 0x1F == 0b11110:
            d = (((hw1 & 0x3F) << 16) | u16(img, a_ + 2)) & ~1
            if d & (1 << 21):
                d -= 1 << 22
            out.setdefault(a_ + d, []).append(a_)
        if (hw1 >> 5) == 0x17 and (hw1 & 0x1F) == 0:
            d = struct.unpack_from("<i", img, a_ + 2)[0]
            out.setdefault(a_ + d, []).append(a_)
    return out


def build():
    print("=" * 102)
    print(f"  V278 rev 3 -- THE REFERENCE x{K} (from x6).  Kp/Kd/taper/gain/clamps FROZEN.  DELIVERED-TORQUE TAP.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK} (stock)")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "index clamp +-240")
    check(base[GAIN_SITE] == 0x25, f"0x{GAIN_SITE:05X} is ld.h (sign-ext) -- gain capped at 32767")
    for a in FB_SITES:
        check(base[a] == 0xE5, f"feedback clamp read @0x{a:05X} is ld.hu -- safe above 32768")
    SIGN_SITES = {0xC61BE: ((0x2A13E, 0xE5), (0x2A146, 0x25), (0x2A14C, 0xE5), (0x2A156, 0xE5),
                            (0x2B024, 0xE5), (0x2B02C, 0x25), (0x2B032, 0xE5), (0x2B03C, 0xE5)),
                  0xC61B4: ((0x2A1F8, 0xE5), (0x2A20C, 0x25), (0x2A212, 0xE5), (0x2A21C, 0xE5),
                            (0x2A910, 0xE5), (0x2A91E, 0x25), (0x2A924, 0xE5), (0x2A92E, 0xE5))}
    for cal_, sites in SIGN_SITES.items():
        for a, want in sites:
            check(base[a] == want, f"0x{cal_:05X} read @0x{a:05X} = {'ld.h SIGN-ext' if want == 0x25 else 'ld.hu'}")
    print("      -> 0xC61BE and 0xC61B4 each carry a sign-extended read: both FROZEN, both < 32768.")

    print("\n  [1b] THE SELECTOR AND THE E CELL, IN THE BASE")
    check(bytes(base[E_STORE_SITE:E_STORE_SITE + 4]) == E_STORE_BYTES,
          "0x2A18C is `st.w r16,-0x6cf8,gp` -- E is stored every PID tick (64 87 09 93)")
    hw1 = u16(base, E_STORE_SITE)
    check(hw1 >> 11 == 16 and (hw1 & 0x1F) == 4, "  ... reg2 = r16, reg1 = gp (decoded from the bytes)")
    check((u16(base, E_STORE_SITE + 2) & ~1) - 0x10000 == -0x6cf8, "  ... disp = -0x6cf8 (decoded from the bytes)")
    check(dec_ld(base, 0x2A178) == ("ld.w", 9, 4, -0x3d3c),
          "POSITIVE CONTROL: 0x2A178 decodes as `ld.w -0x3d3c[gp],r9` (same hw1 form as the tap's ld.w)")
    check(u16(base, 0x2A178) == 0x4F24, "  ... its hw1 is 24 4f -- identical to the tap's ld.w hw1")

    print("\n  [1c] THE SECOND WRITER OF gp-0x6cf8 IS UNREACHABLE -- scanned from the image, positive-controlled")
    # FUN_0002a93a also stores gp-0x6cf8 (at 0x2B058). If it ran, bit 9 would not mean sign(E). Prove no static
    # path reaches it: every jarl/jr disp22, every 48-bit jarl32/jr32, and every absolute pointer in the image.
    def _jump_targets(img):
        out = {}
        for a_ in range(START, END - 4, 2):
            hw1 = u16(img, a_)
            if (hw1 >> 6) & 0x1F == 0b11110:                       # Format V jarl / jr
                d = (((hw1 & 0x3F) << 16) | u16(img, a_ + 2)) & ~1
                if d & (1 << 21):
                    d -= 1 << 22
                out.setdefault(a_ + d, []).append(a_)
            if (hw1 >> 5) == 0x17 and (hw1 & 0x1F) == 0:           # Format VI jarl32 / jr32
                d = struct.unpack_from("<i", img, a_ + 2)[0]
                out.setdefault(a_ + d, []).append(a_)
        return out
    _jt = _jump_targets(base)
    check(0x22522 in _jt.get(0x28EA6, []), "POSITIVE CONTROL: the scan finds FUN_00028ea6's real caller at 0x22522")
    check(0x2A93A not in _jt, "NO jarl/jr/jarl32/jr32 anywhere in the image targets FUN_0002a93a (0x2A93A)")
    check(bytes(base).find(struct.pack("<I", 0x2A93A), START) == -1, "NO absolute pointer to 0x2A93A anywhere in the image")
    print("      -> the only writer of E that can execute is st.w at 0x2A18C in FUN_00028ea6 (residual: register-indirect call, no pointer exists)")

    code = bytearray(base)
    attributed = set()

    # ------------------------------------------------------------------------------------------
    print(f"\n  [2] [A] ASSIST MAP -- scaled x{K} from STOCK shape, all {N_SLOTS} records")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(START <= p < END for p in ptrs), f"all {len(ptrs)} map pointers in range")
    check(bytes(code[MAP_PTR:MAP_PTR + 4 * N_SLOTS]) == bytes(base[MAP_PTR:MAP_PTR + 4 * N_SLOTS]),
          "the pointer family 0xC9A88 itself is byte-identical (the edit is in the DATA)")
    shapes = {}
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        newY = tuple(K * y for y in Y)
        check(all(isinstance(v, int) for v in newY), f"map 0x{p:05X} every knot scales to an INTEGER at K={K}")
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        bY = rec(base, p, n)[1]                                    # re-read from BASE, not the loop's tuple
        check(all(gY[i] == K * bY[i] for i in range(n)) and gY[-1] == K * bY[-1],
              f"map 0x{p:05X} every WRITTEN knot == {K} x BASE knot (independent re-read), ceiling {bY[-1]} -> {gY[-1]}")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  ceiling {oldY[-1]:4d} -> {newY[-1]:5d}   (Honda's shape, x{K})")
    for p in ptrs:
        bY, gY = rec(base, p, MAP_N)[1], rec(code, p, MAP_N)[1]
        rs = {gY[i] / bY[i] for i in range(MAP_N) if bY[i]}
        check(rs == {float(K)}, f"map 0x{p:05X}: every nonzero knot ratio to BASE is exactly {K} (no over-dose, no reshape)")
    n_scaled = sum(len(ps) for ps in shapes.values())
    check(n_scaled == len(ptrs) == 28, f"ALL 28 records scaled ({n_scaled}) -- an under-dosed record cannot pass silently")
    map_changed = sum(1 for p in ptrs for i in range(MAP_N) for k in (0, 1)
                      if code[p + 2 + 2 * MAP_N + 2 * i + k] != base[p + 2 + 2 * MAP_N + 2 * i + k])
    check(map_changed == MAP_CHANGED_EXPECT, f"exactly {MAP_CHANGED_EXPECT} map bytes changed ({map_changed})")
    live_p = u32(base, MAP_PTR + 4 * LIVE_SLOT)
    lX, lY = rec(code, live_p, MAP_N)
    check(lY[-1] == 172 * K, f"LIVE slot {LIVE_SLOT} (record 11 TVCA4) ceiling = 172 x {K} = {172 * K}")
    print(f"      live slot {LIVE_SLOT} @0x{live_p:05X}: Y = {lY}")
    print(f"      crossover threshold (operand counts) = 32 x {172 * K} = {32 * 172 * K}")

    # ------------------------------------------------------------------------------------------
    print(f"\n  [3] [B] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == FB_NEW and FB_NEW < 65536, f"feedback clamp == {FB_NEW}, fits u16")
    r0 = FB_STOCK / (32 * 172)
    r1 = FB_NEW / (32 * 172 * K)
    check(abs(r1 - r0) < 1e-9, f"Honda's setpoint:feedback ratio {r0:.4f} preserved EXACTLY")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] [C] THE PACKER -- signed delivered lane torque: sign(T)<<9 | |T|>>3, T = gp-0x6b38")
    check(bytes(base[PACK_LO:PACK_HI]) == PACK_V268, "base packer window == the V268/stock 34 bytes")
    check(jarl_target(JARL_CLAMP, base) == 0x49A90 and (u16(base, JARL_CLAMP) >> 11) == 31, "0x55E12 is `jarl 0x49A90,lp` (the clamp) -- target and lp DECODED")
    check(len(PACK_NEW) == 34, "new window is exactly 34 bytes")
    code[PACK_LO:PACK_HI] = PACK_NEW
    attributed |= set(range(PACK_LO, PACK_HI))
    check(jarl_target(JARL_CLAMP, code) == 0x49A90 and (u16(code, JARL_CLAMP) >> 11) == 31, "jarl 0x49A90,lp intact after the rewrite")
    a = PACK_LO
    hw1_t, hw2_t = u16(code, a), u16(code, a + 2)
    check(f_I(hw1_t) == (6, 0x39, 4) and not (hw2_t & 1) and (hw2_t - 0x10000) == T_CELL_DISP,
          "ld.h -0x6b38[gp],r6  (op 0x39 with EVEN hw2 = ld.h; disp decoded from the bytes)"); a += 4
    check(f_I(u16(code, a)) == (9, 0x00, 6), "mov r6,r9  (signed copy before the abs)"); a += 2
    check(jarl_target(a, code) == ABS_FN and (u16(code, a) >> 11) == 31, "jarl 0x49A5A,lp  (abs) -- target AND link register lp DECODED from the moved site"); a += 4
    check(f_I(u16(code, a)) == (6, 0x00, 10), "mov r10,r6  (|T|)"); a += 2
    check(f_II(u16(code, a)) == (6, 0x15, 3), "sar 0x3,r6  (|T| >> 3)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x14, 0x1F), "shr 0x1f,r9  (sign(T) -> 0/1)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x16, 9), "shl 0x9,r9  (-> bit 9)"); a += 2
    check(f_I(u16(code, a)) == (6, 0x08, 9), "or r9,r6"); a += 2
    check(dec_imm16(code, a) == (0x31, 8, 0, 0x3FF), "movea 0x3ff,r0,r8  (clamp hi)"); a += 4
    check(f_II(u16(code, a)) == (7, 0x10, 0), "mov 0x0,r7  (clamp lo)"); a += 2
    check(all(u16(code, a + k) == 0 for k in (0, 2, 4, 6)), "4 x nop"); a += 8
    check(a == PACK_HI, "the 10 decoded instructions + 4 nop tile the window exactly")
    check(dec_ld_h(base, PACK_LO) == (6, 4, -0x6abc), "the V268 window loads gp-0x6ABC (V112's tap), NOT stock's gp-0x6c18 -- decoded")
    check(u16(base, PACK_LO) == hw1_t, "POSITIVE CONTROL: the V268 window's own `ld.h -0x6abc,gp,r6` (V112's repoint of stock's -0x6c18) has the SAME hw1 (24 37) -- only the disp changed")
    check(jarl_target(0x55DF4, base) == ABS_FN, "POSITIVE CONTROL: the V268 window's jarl at 0x55DF4 decodes to the same abs 0x49A5A, with lp")
    check(bytes(base[T_STORE_SITE:T_STORE_SITE + 4]) == T_STORE_BYTES and f_I(u16(base, T_STORE_SITE)) == (1, 0x3B, 4)
          and (u16(base, T_STORE_SITE + 2) - 0x10000) == T_CELL_DISP,
          "0x2A23C is `st.h r1,-0x6b38,gp` -- the delivered lane torque is stored every tick (disp decoded)")
    check(bytes(code[T_STORE_SITE:T_STORE_SITE + 4]) == T_STORE_BYTES, "T store untouched")
    _abs = bytes(base[ABS_FN:ABS_FN + 0x18])
    check(all(bytes(code[ABS_FN + k:ABS_FN + k + 2]) == bytes(base[ABS_FN + k:ABS_FN + k + 2]) for k in range(0, 0x18, 2)), "abs helper 0x49A5A byte-identical")
    check(dec_ld(base, 0x2A178) == ("ld.w", 9, 4, -0x3d3c), "POSITIVE CONTROL: 0x2A178 decodes as `ld.w -0x3d3c[gp],r9`")
    check(f_II(u16(base, 0x2A1AC)) == (9, 0x15, 5), "POSITIVE CONTROL: 0x2A1AC decodes as `sar 0x5,r9`")
    for site in (SEL_WRITER, DEMAND_WRITER, E_STORE_SITE, T_STORE_SITE):
        check(bytes(code[site:site + 4]) == bytes(base[site:site + 4]), f"writer at 0x{site:05X} untouched")
    print("      wire = (sign(T) << 9) | (|T| >> 3)      T = gp-0x6b38, |T| <= 3072 -> max 0x380 = 896 < 1023")
    print("      -> T = (-1 if bit9 else 1) * ((wire & 0x1ff) << 3);  a railed sum reads 310 (2481 through the output lag), never 313")

    def decode(w):
        return (-1 if (w >> 9) & 1 else 1) * ((w & 0x1FF) << 3)
    check(decode(310) == 2480 and decode(512 | 310) == -2480 and decode(0) == 0, "decode: 310 -> +2480 (the railed-sum delivery at 8-count resolution), bit 9 -> negative")
    check((3072 >> 3) | 0x200 == 896 < 1023, "max wire value 896 -- the clamp helper stays a pass-through")

    # ------------------------------------------------------------------------------------------
    print("\n  [5] EVERYTHING ELSE BYTE-IDENTICAL TO V268")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "V112 cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]), "FUN_00028ea6 byte-identical -- the PID is not touched")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == v, f"0x{a_:05X} still {v}")
    for nm, ptr, npt in (("Kp", KP_PTR, KP_N), ("Kd", KD_PTR, KD_N)):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = s16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"{nm} slot {s} byte-identical")
            check(min(rec(code, p, n)[1]) > 0, f"{nm} slot {s}: every Y knot > 0 -- the lane keeps the sign of E (the damping decode rests on this)")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-stock")
    print(f"      {len(tps)} taper records byte-stock: the operator's grip escape (cliff at 2240-2560) is unchanged")

    # ------------------------------------------------------------------------------------------
    print("\n  [6] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [7] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(PACK_LO, PACK_HI)) | {FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    check(set(pay) <= allow, "every payload byte is a MAP Y knot, the feedback clamp, or the 34-byte packer window")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(all(PACK_LO <= x < PACK_HI for x in cb), f"all {len(cb)} changed code bytes lie inside the packer window")
    print(f"      {len(pay)} payload bytes, {len(cb)} code, {len(blocks)} CRC trailers")

    print("\n  [7b] CROSS-IMAGE: rev 2 (same cals) and V279 rev 2 (same window) -- read from THOSE images")
    rev2 = Path(plain_image_path(REV2_IMAGE)).read_bytes()
    v279 = Path(plain_image_path(V279_IMAGE)).read_bytes()
    check(hashlib.sha256(rev2).hexdigest() == REV2_SHA, "V278 rev 2 image sha256 matches the reported hash")
    check(hashlib.sha256(v279).hexdigest() == V279_SHA, "V279 rev 2 image sha256 matches the reported hash")
    d2 = [x for x in range(START, END) if code[x] != rev2[x] and (x & 0xFFF) < 0xFFC]
    check(d2 and all(PACK_LO <= x < PACK_HI for x in d2), f"vs rev 2: the ONLY payload difference is inside the packer window ({len(d2)} bytes)")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(v279[PACK_LO:PACK_HI]), "the window is BYTE-IDENTICAL to V279 rev 2's (the audited tap)")
    check(bytes(code[0x13000:0xC0000]) == bytes(v279[0x13000:0xC0000]), "code region 0x13000-0xC0000 byte-identical to V279 rev 2 (no CRC trailer lies in this range; the 0x13000 block trailer is at 0xC4FFC)")
    d9 = [x for x in range(0xC0000, END) if code[x] != v279[x] and (x & 0xFFF) < 0xFFC]
    check(d9 and all(x >= 0xC0000 for x in d9), f"vs V279 rev 2: every payload difference is a CAL byte ({len(d9)} bytes)")
    dc = [x for x in range(0xC0000, END) if code[x] != rev2[x] and (x & 0xFFF) < 0xFFC]
    check(dc == [], "cal region 0xC0000-0x100000 payload byte-identical to rev 2 (the two edits are unchanged)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V278 rev 3 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49")
    # FAIL-CLOSED cipher validation (V277's fix: an hasattr-gated `else True` passed while printing "validated")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN EXISTS -- the non-circular cipher test is REACHABLE")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image")

    print("\n  [8b] END STATE -- re-read from the FINAL image and the DECODED .rwd")
    for nm, im in (("code", code), ("dec", dec)):
        check(u16(im, FB_CELL) == FB_NEW, f"{nm}: 0xC62E6 == {FB_NEW}")
        check(rec(im, u32(im, MAP_PTR + 4 * LIVE_SLOT), MAP_N)[1][-1] == 172 * K, f"{nm}: live slot ceiling {172 * K}")
        check(all(rec(im, p, MAP_N)[1] == [K * y for y in rec(base, p, MAP_N)[1]] for p in ptrs), f"{nm}: all 28 map records == {K} x base")
        check(bytes(im[PACK_LO:PACK_HI]) == PACK_NEW, f"{nm}: packer window == the torque tap")
        check((u16(im, 0xC61BE) * u16(im, 0xC6CD0)) >> 15 == 2505, f"{nm}: sum-clamp ceiling 15360 x 5346 >> 15 == 2505 (delivered 2481 through the 0.990 readout; reads 310)")
        _s = u16(im, 0xC61BE) * u16(im, 0xC63EE) >> 5; _ro = (_s + _s) >> 5
        check((_ro * u16(im, 0xC6CD0) >> 15) >> 3 == 310, f"{nm}: railed-sum delivered torque through the output lag = {(_ro * u16(im, 0xC6CD0) >> 15)} -> reads {(_ro * u16(im, 0xC6CD0) >> 15) >> 3} (never 313)")
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    _scr = os.environ.get("ACCORD_V278R3_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v278_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v278_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v278_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V278R3_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
