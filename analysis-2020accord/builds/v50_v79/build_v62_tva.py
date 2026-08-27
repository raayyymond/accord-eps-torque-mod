"""
builds/v50_v79/build_v62_tva.py -- V62 = V59 + DOUBLE the torsion-bar RATE lane. The exact inverse of V61.

THE POINT
---------
V61 zeroed the torsion-bar torque-RATE lane at both taps of its shared value r1 (0x3AB6C mul r1,r6,r0
-> mul r0,r6,r0 and 0x3AC16 mov r1,r8 -> mov r0,r8). Flashed 2026-07-31. On-car, operator:

    LKAS ON  (forward): grinding still present and "significantly worse" -- higher amplitude, louder.
    LKAS OFF (forward): grinding NEWLY present in manual driving when turning.
    LKAS OFF (reverse): grinding DEFINITELY newly present in manual driving.

That is the first SIGNED on-car result this kit has obtained on this lane, and it inverts the record.

WHY THE RECORD WAS BACKWARDS
----------------------------
model/eps_lkas_chain_model.py:1792 framed r26 as "excitation-to-amplifier: faster slew -> bigger column-torque
derivative -> bigger r26 -> more motor torque -> more column motion -> repeat", which predicts that
KILLING it helps. V61 killed both taps and it got worse, in engaged AND manual driving. The amplifier
framing is falsified on-car.

The sign, verified by the orchestrator directly from image bytes (NOT relayed from a subagent):
  * polarity gp-0x6752 is a single load @0x3AB78 reused unmodified by BOTH lanes, and the SAME byte is
    read by FUN_0003a382's resonance lane @0x3A71A -- the one aggregator lane with a genuine
    torque-PROPORTIONAL P-term. Polarity therefore CANCELS in the comparison; its concrete value is not
    needed to answer the sign question.
  * the combine chain 0x3ACC8-0x3ACDA is ten instructions, every lane entering with `add`, each add's
    reg1 threading the previous add's reg2 (a textbook accumulator chain). Not one `sub`.
  => r24, r26 = +Kd * d(T_bar)/dt, ADDED IN PHASE WITH ASSIST. Kp*x + Kd*dx/dt -- a lead compensator.

WHY "in phase with assist" IS DAMPING, not positive feedback
------------------------------------------------------------
Hands-off, the mode is the steering-wheel inertia on the torsion bar. theta_w = wheel angle (J_w, free),
theta_c = column angle (J_c), bar stiffness k, sensed torque T_b = k*(theta_w - theta_c), phi = the
twist, motor torque applied to the COLUMN only as T_m = K*T_b + Kd*dT_b/dt:

    J_w*theta_w'' = -T_b ;   J_c*theta_c'' = +T_b + T_m - T_road
    ------------------------------------------------------------------
    phi'' + (Kd*k/J_c)*phi' + k*(1/J_w + (1+K)/J_c)*phi = T_road/J_c
    ------------------------------------------------------------------

The phi' coefficient is Kd*k/J_c > 0: POSITIVE DAMPING, LINEAR IN Kd. At Kd = 0 the mode has no damping
term at all. That is V61, and that is what the car did -- including in manual driving, where base assist
is the only loop running, and worst in reverse.

Once the motor/current-loop lag tau is included, the K*T_b term contributes ~ -K*k*tau/J_c, so
    zeta_net ~ (Kd - K*tau) * k / (2*J_c*omega)
Stock pins the operating point: the mode SUSTAINS with no ring-down at all (66 candidate decays, longest
0.63 cycles) => zeta_net ~ 0 => Kd ~ K*tau. Therefore:
    V61 (Kd = 0)    => zeta_net ~ -K*tau  < 0   -> diverges.  OBSERVED.
    V62 (Kd = 2*Kd) => zeta_net ~ +Kd*... > 0   -> decays.    PREDICTED.
V62 is the SAME-SIZED STEP IN THE OPPOSITE DIRECTION as V61 -- a matched, symmetric experiment, and the
smallest edit that moves zeta_net from ~0 to +zeta_lead.
[INFERRED] the 2-DOF plant model is a lumped idealisation. It predicts DIRECTION and LINEARITY in Kd,
not an absolute zeta. No dB figure is claimed from it.

WHY THE EDIT IS TWO `sar` IMMEDIATES AND NOT THE GAIN CALS
-----------------------------------------------------------
The obvious lever was the gain calibrations. It is the WRONG instrument, for three reasons found while
tracing:
 1. The gain is selected by a PRIORITY CHAIN, and which arm is live at creep cannot be pinned statically:
      r24: gate_671d!=0 ? 1024(0xC6442) : gate_683c!=0 ? 512(0xC6446) : state>=5 ? 2048(0xC6440)
                                                                                : gain_B LERP
      r26: (gate_6b5e!=0 AND state>=5) ? avg collapses to 1 (lane ~= 0)
                                       : gate_683c!=0 ? 512(0xC6444) : state<5 ? 1536(0xC643E) : LERP
    and `assist_state_671a` is a bounded [0,5] PERSISTENCE RAMP tracking consistent SIGN of a rate
    signal -- during a 21 Hz oscillation it plausibly never saturates, which would put r24 on the LERP
    arm. Editing calibrations means betting on a branch.
 2. r24's default arm is a MODE-INDEXED table, not one location. FUN_0003ad74's B-bank half reads a
    mode-select byte at gp+0x63fd (`0003ad88 ld.bu 0x63fd,gp,r16`) and uses mode*4 to index FOUR ROM
    pointer arrays (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214). Byte-pattern search on the LE pointer values:
    0xD2AEC is reached from 0xCC154 = index 10 of 0xCC12C, and 0xD2B28 from 0xCC23C = index 10 of
    0xCC214 -- mode 10's pair. 0xD6AEC is reached from 0xCC184 = **index 22** of the same array.
    ⚠ CORRECTION to an earlier reading of mine: 0xD6AEC is NOT a redundancy twin of 0xD2AEC and this is
    NOT the V27 desync class. The two blocks are byte-identical, but they are two DIFFERENT modes'
    records, each reached through its own valid pointer slot. Editing r24's default gain by calibration
    would mean editing every mode's record, or knowing the boot mode for certain.
    (Mode 10 IS this car's index -- independently established: PN 39990-TVA-A160 -> key TVAA1 -> config
    row 2 -> INDEX 10, the chain V44/V47 were confirmed to hit on 2026-07-28. But the `sar` edit does not
    have to rely on that, which is the point.)
 3. gp-0x683c has ZERO writers image-wide, so the 512 arms (0xC6446/0xC6444) are structurally
    unreachable dead calibration anyway.

`sar 0xa` -> `sar 0x9` doubles the lane output REGARDLESS of which gain arm is selected. It is immune to
every one of the three problems above, and it is the same EDIT CLASS as V61 -- an immediate/register
field change on a verified instruction, opcode and reg2 byte-identical, same length, no cave.

    0x3AC20  42AA -> 42A9   sar 0xa,r8 -> sar 0x9,r8    r24: (dtorque * gain_B) >> 10 -> >> 9
    0x3AB76  32AA -> 32A9   sar 0xa,r6 -> sar 0x9,r6    r26: (stage1  * gain_A) >> 10 -> >> 9

WHY 0x3AB76 AND NOT 0x3AB70 FOR r26 -- an overflow argument, not a coin flip
----------------------------------------------------------------------------
r26 is two chained multiplies:  stage1 = (dtorque*avg)>>10 @0x3AB70 ; pre = (stage1*gain_A)>>10 @0x3AB76.
V850 `mul r1,r6,r0` discards the HIGH word into r0, so a 32-bit overflow is SILENTLY TRUNCATED into a
garbage, possibly sign-flipped lane value. Worst case with avg = 0xFFFF and dtorque = 5120:
    stock            : stage1 = 327,675 ; stage1*gain_A(3072) = 1.007e9  = 47% of INT32_MAX
    edit @0x3AB70    : stage1 = 655,350 ; stage1*gain_A(3072) = 2.013e9  = 94% of INT32_MAX  <-- 6% margin
    edit @0x3AB76    : product UNCHANGED at 1.007e9            = 47% of INT32_MAX  <-- no new risk
Editing the SECOND shift doubles the result while leaving every multiply operand at its stock magnitude.
0x3AB70 is rejected on that margin alone.
r24 has a single multiply: dtorque(5120) * gain_B(<=2305) = 11.8M, trivially safe either way.

HEADROOM -- the lane is nowhere near saturating, so doubling stays LINEAR
-------------------------------------------------------------------------
A saturating lead term is worse than useless (describing-function gain falls with amplitude), so this is
the binding constraint. Producer FUN_0007e74a: gp-0x4f62 = ((current - delayed) << 1) / dt, delay D = 4
(cal 0xC6C42, byte-verified), 1000 Hz. For a sinusoid, peak(current-delayed) = 2*A*sin(w*D/(2*Fs)).
🛑 CORRECTED against the V61 drive. This section first assumed A = 1400 counts, the historical figure.
   The V61 rlog MEASURED the mode far larger -- engaged creep hands-off pp median 3216 / p90 5451 /
   p99 6437, i.e. **+/-3218 counts at p99, 3.4x V59's median** -- and the strict 18-26 Hz band
   understated it 20-29% because the mode had MOVED BELOW that band. Redone on measured amplitudes:

   bar amp   0x4f62   %in  | r24@2048  %lane   clip | r24@3072  %lane   clip
       473      107   2.1% |      211   2.6%  38.3x |      318   3.9%  25.5x   V59 median
      1610      366   7.1% |      729   8.9%  11.2x |     1095  13.4%   7.5x   V61 median
      2726      619  12.1% |     1235  15.1%   6.6x |     1854  22.6%   4.4x   V61 p90
      3218      731  14.3% |     1459  17.8%   5.6x |     2190  26.7%   3.7x   V61 p99  <-- BINDING

   BINDING CASE = p99 amplitude AND the worst gain arm (natural LERP at stock max 3072): clips at
   **3.7x** stock gain, so doubling reaches **54% of the clamp with ~1.9x margin left**.
   ⚠ That is TIGHTER than the ">=3.6x under every arm" this file first claimed. It is still firmly in
   the linear region and nothing saturates -- but the honest number at the loudest measured moment on
   the worst arm is ~2x margin, not ~4x. Recorded rather than smoothed.
   ⚠ Note also that the p99 row is V61's PATHOLOGICAL amplitude. V62's entire purpose is to reduce it,
   which walks the operating point back up the table toward the V59 rows, where margin is 25-38x.
   See studies/models/rate_lane_damping_model.py.

WHAT IT COSTS
-------------
Manual feel WILL change -- there is no LKAS-only decoupling point in this chain (traced). A doubled lead
term makes response to FAST inputs crisper and adds damping to transients; the risk direction is
"nervous"/noise-sensitive rather than heavy. Note this is the lane whose REMOVAL the operator felt
immediately, so a change in feel is expected and is itself confirmation the edit is live.
Reversible by reflashing V59 (stock lane) or V61 (killed lane).

GATE 1 (RAM ownership): VACUOUS. No cave, no new RAM cell, no new opcode. Caves are this kit's only
                        bricking class (V24, V27, V48B); this build introduces none.
GATE 2 (closed-loop stability): this IS the gate-2 argument -- the edit raises the damping coefficient of
                        the mode in question, in the one lane fast enough to act on it. Unlike the
                        boost/damping lanes (task 5, 100 Hz, 38-75 deg of ZOH lag at 20.9 Hz, which is
                        the structural reason every damper lever was null), FUN_0003aa2c is task 1 at
                        1000 Hz -- 3.8 deg of lag at 20.9 Hz. It is on the right side of that problem.
  ⚠ RESIDUAL, stated not smoothed: avg(gp-0x69a4) -- r26's slope factor -- has an UNMEASURED magnitude
    ([OPEN] across three sessions). If it were large enough for r26 to already be pinned at +/-8192,
    doubling would deepen a saturation. Bounding argument against that: a lane pinned at 8192 would
    dominate the aggregator's own +/-10240 sum clamp, and V61 (which zeroed it) would have produced a far
    more dramatic change than the one reported. Not proof. r24's magnitude is fully bounded and is not
    subject to this residual.

BASE = V59, so V61's two-byte kill is reverted BY CONSTRUCTION and the build asserts both taps are back
at r1 before editing. V59's probe is UNCHANGED and rides along as a secondary readout.

🛑 LINEAGE, stated explicitly because these lanes HAVE been flashed before:
   V39 killed r24 (cals 0xC6440/42/46, 0xC61F6) -- and only CONDITIONALLY.  -> NULL on-car.
   V42 killed r26 (gain_A Y rows + 0xC643E/0xC6444).                        -> NULL on-car.
   V61 killed BOTH, unconditionally.                                        -> WORSE on-car.
   Every one of those tested the lane DOWNWARD. V62 is the first test UPWARD. This is the reverse of the
   FactorC/V44 trap: there, a withdrawn RATIONALE was mistaken for a withdrawn RESULT. Here the results
   all stand -- they simply bracket the wrong side of the optimum, and V61 measured the gradient.
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

import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v59_tva as V59                # noqa: E402
import build_v61_tva as V61                # noqa: E402

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

# ---- THE TWO EDITS -----------------------------------------------------------------------------
# Format II: reg2 = bits[15:11], opcode = bits[10:5] (0x15 = sar), imm5 = bits[4:0].
R26_SAR = 0x3AB76            # sar 0xa,r6  -- AFTER `mul stage1,gain_A`. NOT 0x3AB70 (see docstring).
R24_SAR = 0x3AC20            # sar 0xa,r8  -- AFTER `mul dtorque,gain_B`.
SAR_STOCK_HW = {R26_SAR: 0x32AA, R24_SAR: 0x42AA}
SAR_NEW_HW = {R26_SAR: 0x32A9, R24_SAR: 0x42A9}
SAR_OPCODE = 0x15

EDITS = ((R24_SAR, "r24 lane: (dtorque * gain_B) >> 10  ->  >> 9"),
         (R26_SAR, "r26 lane: (stage1  * gain_A) >> 10  ->  >> 9"))

# 🛑 The OTHER r26 shift must stay at 10 -- editing it instead would push a multiply operand to 94% of
# INT32_MAX, and V850 `mul` discards the high word into r0 (silent truncation, possible sign flip).
R26_SAR_FIRST = 0x3AB70
R26_SAR_FIRST_HW = 0x32AA

# The two V61 tap sites. V62 baselines on V59, so both must read r1 (STOCK), not r0 (V61's kill).
TAP_STOCK = ((0x3AB6C, 0x37E1, "r26 tap: mul r1,r6,r0"), (0x3AC16, 0x4001, "r24 tap: mov r1,r8"))

# The shared clamp that PRODUCES r1, and the aggregator's add order. Neither may move.
CLAMP_CTX = V61.CLAMP_CTX
SUM_CTX = V61.SUM_CTX

# 🛑 Every r24/r26 GAIN cal must be STOCK -- V62 changes SHIFTS, not calibration. This is what makes the
# CAL CRC assertion below a machine proof, and it keeps V62 an independent test of the SHIFT, not a
# re-run of V39/V42 layered underneath.
RATE_GAIN_CALS = V61.RATE_GAIN_CALS
RATE_A_RECORDS = V61.RATE_A_RECORDS
RATE_A_Y_STOCK = V61.RATE_A_Y_STOCK

# r24's mode-10 default-arm records, and mode 22's byte-identical pair. NOT a redundancy mirror -- two
# different modes reached through their own slots in the 0xCC12C / 0xCC214 pointer arrays. Asserted
# untouched, and asserted still equal to each other, purely as a tripwire that no cal edit crept in.
GAIN_B_LERP_MODE10 = (0xD2AEC, 0xD2B28)
GAIN_B_LERP_MODE22 = (0xD6AEC, 0xD6B28)

TAG = "LKAS-4x-mss0-decouple0xC646C-boostindexdepth-ratelane2x-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V62-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v62_plain_image.bin"))
V59_BIN = str(plain_image_path("_v59_plain_image.bin"))

BLEND_ADDR, BLEND_STOCK = 0xD2006, 102     # V60's falsified lever -- must be back at stock here


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def decode_fmt2(halfword):
    """V850 Format-II field split: imm5 = bits[4:0], opcode = bits[10:5], reg2 = bits[15:11]."""
    return {"imm5": halfword & 0x1F, "opcode": (halfword >> 5) & 0x3F, "reg2": (halfword >> 11) & 0x1F}


def assert_sar_sites(code, label, expect_doubled):
    """Both shifts are sar imm5,regN with ONLY the immediate moved 10 -> 9. Nothing else may differ."""
    for addr, what in EDITS:
        want = SAR_NEW_HW[addr] if expect_doubled else SAR_STOCK_HW[addr]
        got = u16(code, addr)
        assert got == want, f"{label}: 0x{addr:05X} is 0x{got:04X}, expected 0x{want:04X} ({what})"
        f_got, f_stock = decode_fmt2(got), decode_fmt2(SAR_STOCK_HW[addr])
        assert f_got["opcode"] == SAR_OPCODE, \
            f"{label}: 0x{addr:05X} opcode is 0x{f_got['opcode']:02X}, not sar (0x15)"
        assert f_got["opcode"] == f_stock["opcode"] and f_got["reg2"] == f_stock["reg2"], \
            f"{label}: 0x{addr:05X} changed more than the immediate -- opcode/reg2 moved"
        assert f_got["imm5"] == (9 if expect_doubled else 10), \
            f"{label}: 0x{addr:05X} imm5 is {f_got['imm5']}"
    assert u16(code, R26_SAR_FIRST) == R26_SAR_FIRST_HW, \
        f"{label}: 0x{R26_SAR_FIRST:05X} moved -- editing the FIRST r26 shift pushes a mul operand to " \
        "94% of INT32_MAX and V850 mul truncates the high word silently"


def assert_untouched_context(code, label):
    """Everything the edit's MEANING depends on: the taps, the clamp, the sum, and every gain cal."""
    for addr, want, what in TAP_STOCK:
        assert u16(code, addr) == want, \
            f"{label}: tap 0x{addr:05X} ({what}) is 0x{u16(code, addr):04X}, expected STOCK 0x{want:04X} " \
            "-- V62 must NOT carry V61's kill; it doubles a lane that must first be present"
    for addr, want, what in CLAMP_CTX:
        got = bytes(code[addr:addr + len(want)])
        assert got == want, f"{label}: shared-clamp context at 0x{addr:05X} ({what}) is {got.hex()}"
    for addr, want, what in SUM_CTX:
        assert u16(code, addr) == want, f"{label}: aggregator sum at 0x{addr:05X} ({what}) moved"
    for addr, want, what in RATE_GAIN_CALS:
        assert u16(code, addr) == want, \
            f"{label}: rate gain cal 0x{addr:05X} ({what}) is {u16(code, addr)}, expected {want} -- " \
            "V62 edits SHIFTS, not calibration"
    for base, ys in zip(RATE_A_RECORDS, RATE_A_Y_STOCK):
        assert struct.unpack_from("<4h", code, base + 0xA) == ys, \
            f"{label}: r26 gain_A record 0x{base:05X} Y row moved -- V42's edit must NOT be present"
    # r24's mode-10 and mode-22 default-arm records: untouched, and still equal to each other.
    for a, t in zip(GAIN_B_LERP_MODE10, GAIN_B_LERP_MODE22):
        assert bytes(code[a:a + 0x12]) == bytes(code[t:t + 0x12]), \
            f"{label}: gain_B default record mode-10 0x{a:05X} != mode-22 0x{t:05X} -- a calibration " \
            "edit reached r24's default arm, which V62 must not do"


def build():
    if not os.path.exists(V59_BIN):
        print(f"  {V59_BIN} missing -- running the V59 builder first\n")
        V59.build()
    v59 = bytearray(open(V59_BIN, "rb").read())
    print(f"  V59 source {V59_BIN}\n    SHA256 {hashlib.sha256(bytes(v59)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v59, "V59 source")
    assert walk(bytes(v59), label="V59 source") == 0
    assert walk_all_blocks(bytes(v59), label="V59 source") == 0
    V59.assert_probe_sites(v59, "V59 source")
    V59.assert_index_chain(v59, "V59 source")
    V55.assert_variant_tables(v59)
    V57.assert_decoupled(v59, "V59 source")
    assert u16(v59, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V59 source lost the lockout edit"
    assert u16(v59, BLEND_ADDR) == BLEND_STOCK, \
        "0xD2006 is not stock 102 -- V62 must NOT carry V60's falsified blend edit"
    assert_sar_sites(v59, "V59 source", expect_doubled=False)
    assert_untouched_context(v59, "V59 source")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    assert_sar_sites(baseline, "V38 baseline", expect_doubled=False)
    assert_untouched_context(baseline, "V38 baseline")

    code = bytearray(v59)

    # ---- the two edits ---------------------------------------------------------------------------
    print("\n  THE EDIT -- double the torsion-bar RATE lane at both lanes' final shift:")
    for addr, what in EDITS:
        struct.pack_into("<H", code, addr, SAR_NEW_HW[addr])
        print(f"    0x{addr:05X}  0x{SAR_STOCK_HW[addr]:04X} -> 0x{SAR_NEW_HW[addr]:04X}   "
              f"sar 0xa -> sar 0x9   {what}")
    print(f"    0x{R26_SAR_FIRST:05X} deliberately LEFT at sar 0xa (overflow margin -- see docstring).")
    print("    Gain arms, deadzone and both LERP surfaces are untouched, so the doubling applies")
    print("    under EVERY branch of the gain priority chain.")
    assert_sar_sites(code, "V62", expect_doubled=True)
    assert_untouched_context(code, "V62")

    # ---- everything else must be byte-identical to V59 -------------------------------------------
    assert bytes(code[V59.CAVE_BASE:V59.CAVE_BASE + len(V55.CAVE_BYTES)]) == \
        bytes(v59[V59.CAVE_BASE:V59.CAVE_BASE + len(V55.CAVE_BYTES)]), "the cave moved"
    assert bytes(code[V59.HOOK_ADDR:V59.HOOK_ADDR + 4]) == \
        bytes(v59[V59.HOOK_ADDR:V59.HOOK_ADDR + 4]), "the hook moved"
    V59.assert_probe_sites(code, "V62")
    V59.assert_index_chain(code, "V62")
    V57.assert_decoupled(code, "V62")
    V55.assert_variant_tables(code)
    assert u16(code, BLEND_ADDR) == BLEND_STOCK, "V62 must leave 0xD2006 at stock"
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC6424, "shaper deadband"),
                    (0xC646C, "shared sensor scale"), (0xC6CD0, "private LKAS gain"),
                    (0xC62EA, "low-speed lockout"),
                    # ⚠ CORRECTION: an earlier draft called 0xC6C42 unsafe because gp-0x4f62 is
                    # lockstep-shadowed to gp-0x4488. That reasoning is WRONG and is retracted here.
                    # 0xC6C42 has exactly ONE reader, FUN_0007e74a itself (4 ld.hu inside it), and D
                    # feeds a SINGLE computation whose result is stored to BOTH cells in sync -- there
                    # is no mechanism by which moving D desyncs the pair. The real reason it stays
                    # stock: D is the differentiator's time WINDOW (4 ticks), and its response at any
                    # other D is uncharacterised. It is a PHASE lever, and a legitimate future one --
                    # D 4->2 halves the lead's transport lag (15.1 deg -> 7.6 deg at 20.9 Hz).
                    (0xC6C42, "rate delay D -- a future PHASE lever, deliberately stock in V62"),
                    (0xC63BA, "FUN_3b66a EMA alpha -- pre-falsified by V60, NOT a lever")):
        assert u16(code, a) == u16(v59, a), f"{name} 0x{a:05X} moved -- V62 edits TWO code halfwords"
    assert code[0xC64DE] == 27 and code[0xC64A3] == 1
    assert struct.unpack_from("<9H", code, 0xD27BC) == \
        struct.unpack_from("<9H", baseline, 0xD27BC), "FactorC 0xD27BC moved (V44 is falsified)"
    for addr, n in ((V59.LERP1_ADDR, 13), (V59.LERP4_ADDR, 13)):
        assert struct.unpack_from(f"<{n}H", code, addr) == \
            struct.unpack_from(f"<{n}H", baseline, addr), f"amplitude curve 0x{addr:05X} moved"

    # ---- CRC -------------------------------------------------------------------------------------
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
        if block == CAL_BLOCK:
            assert old_crc == new_crc, "CAL CRC moved -- V62 changes NO 0xC6xxx calibration"

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff against a full_image(): 0xFF filler below 0x13000 reports ~51,000 bogus
    # bytes. Restricted to [0x13000,0x100000).
    d59 = [i for i in range(0x13000, 0x100000) if code[i] != v59[i]]
    crc_range = range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)
    code_changed = sorted(i for i in d59 if i not in crc_range)
    crc_changed = sorted(i for i in d59 if i in crc_range)
    # 0x32AA->0x32A9 and 0x42AA->0x42A9 each move ONLY the low byte (the imm5 field).
    assert code_changed == sorted((R26_SAR, R24_SAR)), \
        f"expected exactly the two imm5 bytes 0x{R24_SAR:05X}/0x{R26_SAR:05X}, " \
        f"got {[hex(x) for x in code_changed]}"
    assert crc_changed, "the MAIN block CRC did not move, but two code bytes did"
    # ⚠ Do NOT assert a fixed TOTAL byte count -- that silently encodes which CRC bytes happened to
    # differ. Assert the two code bytes exactly, and tie the rest to the CRC word actually changing.
    assert len(d59) == 2 + len(crc_changed), f"unexpected extra bytes in the diff: {len(d59)}"
    print(f"\n  V62 vs V59: {len(d59)} bytes  "
          f"(2 immediate-field bytes + {len(crc_changed)} MAIN block CRC bytes ONLY)")
    print("    => CAL CRC unchanged        = machine proof no 0xC6xxx calibration moved")
    print("    => 0xD2000-block CRC unchanged = machine proof V60's blend AND r24's gain_B LERP are stock")

    d61 = None
    v61_bin = str(plain_image_path("_v61_plain_image.bin"))
    if os.path.exists(v61_bin):
        v61 = bytearray(open(v61_bin, "rb").read())
        d61 = [i for i in range(0x13000, 0x100000) if code[i] != v61[i]]
        print(f"  V62 vs V61: {len(d61)} bytes  (the two taps reverted + the two shifts + CRC)")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V62 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V62")
    assert walk(bytes(code), label="V62") == 0
    assert walk_all_blocks(bytes(code), label="V62") == 0
    V59.assert_probe_sites(code, "V62")
    V55.assert_variant_tables(code)
    assert_sar_sites(code, "V62", expect_doubled=True)
    assert_untouched_context(code, "V62")

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback -----------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == FF.EXPECTED_HEADERS
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    rwd = encode_x31(source_info["headers"], source_info["blocks"],
                     [bytes(code[START:END]).translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V62 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V62 readback")
    assert walk(bytes(readback), label="V62 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V62 readback") == 0
    V59.assert_probe_sites(readback, "V62 readback")
    V59.assert_index_chain(readback, "V62 readback")
    V57.assert_decoupled(readback, "V62 readback")
    V55.assert_variant_tables(readback)
    assert_sar_sites(readback, "V62 readback", expect_doubled=True)
    assert_untouched_context(readback, "V62 readback")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("\n  THE DRIVE -- the V61 route again, so the comparison is like-for-like:")
    print("     parking-lot creep, LKAS on/off passes at matched speed and angle, AND the same manual")
    print("     forward + manual REVERSE passes that showed the new grinding on V61.")
    print("     The manual-reverse pass is the highest-information single test: V61 introduced grinding")
    print("     there from nothing, so it is the cleanest read on the lane's damping with no LKAS in the")
    print("     loop at all.")
    print("     Decode with rlog-tools/probe/decode_v59_boostindex.py (probe unchanged, secondary readout).")
    print("\n     PREDICTION -- TWO independent observables, because the V61 rlog showed the mode MOVED:")
    print("       (a) AMPLITUDE falls. V61 raised engaged-creep power 7.9x (5.26e8 -> 4.15e9,")
    print("           speed-matched vs V59 route 2c); manual reverse must return toward the manual-")
    print("           forward floor (5.78e8 -> ~3.8e6 is the gap V61 opened).")
    print("       (b) FREQUENCY rises back. V61 moved the engaged line 21.18 -> 18.25 Hz (-2.93 Hz).")
    print("           🛑 A pure GAIN change CANNOT move a resonance frequency -- a PHASE change can, and")
    print("           removing a lead lowers the frequency where the loop phase reaches -180 deg.")
    print("           Doubling the lead should push it back to >= 21.2 Hz, or remove the line entirely.")
    print("     (b) is the stronger test: it is structural, and amplitude alone could be confounded by")
    print("     route/effort differences. If amplitude falls but the frequency does NOT move, the lane")
    print("     is acting as a plain gain and the lead interpretation is wrong -- say so.")
    print("     A NULL on both would mean the damping is phase-limited, not gain-limited, and the next")
    print("     step is the 1 kHz lead's PHASE (delay D at 0xC6C42, 4->2), not its gain.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
