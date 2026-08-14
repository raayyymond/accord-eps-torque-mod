#!/usr/bin/env python3
r"""DELIVERED-BYTES LEDGER, STOCK -> V100.  Reads the PLAIN IMAGES ON DISK, never the build scripts.

Successor to `ledger_v38_to_v84_bytes.py`, `ledger_v94_cells.py` and `ledger_v38_to_v98_bytes.py`
(all kept, not overwritten). Extends the V85..V98 reader by ONE build, V99, and otherwise carries
its logic unchanged: a FULL byte diff (not just named sites), FROZEN counts, and VIRGIN verdicts.

Plain images are flat 1 MiB code images: file offset == firmware address.  Anchored on every run
against stock `0xC646C == 891` and `code.bin[0x454FE] == 0xBA` -- the two guards against the
off-by-0x1000 tp-relative trap (tp = 0xBF000, so tp+0x6000 == 0xC5000, NOT 0xC6000).
V850E2 is LITTLE-ENDIAN.  Record layout: [npt:u16][X x npt][Y x npt], Y at base + 2 + 2*npt.

🛑 V95 DOES NOT EXIST -- it is a deliberately BURNED build number.  The chain is V94 -> V96.

Coverage caveat (EVIDENCE): the plain images are reconstructed from the RWD and leave spans 0xFF
that are real data in the stock dump.  50,284 bytes are 0xFF in ALL images => packaging, not
levers, and they are masked out of every diff.  The 12 bytes that are 0xFF on V98 but NOT on every
image -- 0x55C0F, 0xC61C0-0xC61C5, 0xC64B4-0xC64B8 -- are REAL edits and are kept.

Usage:
    python ledger_v38_to_v100_bytes.py            # everything: A + B1 + B2 + B3 + C, writes JSON
    python ledger_v38_to_v100_bytes.py diff V98 V99
    python ledger_v38_to_v100_bytes.py matrix | frozen | virgin | delta | mask
"""
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

try:                                    # Windows console defaults to cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           r"C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
STOCK = ROOT / "stock_fw_dump" / "code.bin"
HERE = Path(__file__).parent

TARGET = os.environ.get("LEDGER_TARGET", "V100")
PREV_ON_CAR = "V99"          # what was on the car before TARGET

# Build order.  Pre-V38 entries are kept so cells introduced in the V22-V37 era attribute to a real
# tag instead of collapsing onto V38.  V22 is the earliest image on disk.
BUILDS = [
    ("STOCK", STOCK),
    ("V22", "_v22_plain_image.bin"), ("V23", "_v23_plain_image.bin"),
    ("V24", "_v24_plain_image.bin"), ("V25", "_v25_plain_image.bin"),
    ("V26", "_v26_plain_image.bin"), ("V27", "_v27_plain_image.bin"),
    ("V28", "_v28_plain_image.bin"), ("V29", "_v29_plain_image.bin"),
    ("V30", "_v30_plain_image.bin"), ("V31", "_v31_plain_image.bin"),
    ("V31p", "_v31p_plain_image.bin"), ("V31p2", "_v31p_v2_plain_image.bin"),
    ("V31t", "_v31t_plain_image.bin"), ("V31u", "_v31u_plain_image.bin"),
    ("V32", "_v32_plain_image.bin"), ("V33", "_v33_plain_image.bin"),
    ("V34", "_v34_plain_image.bin"), ("V35", "_v35_plain_image.bin"),
    ("V36", "_v36_plain_image.bin"), ("V37", "_v37_plain_image.bin"),
    # ---- the post-V38 arc proper
    ("V38", "_v38_plain_image.bin"), ("V39", "_v39_plain_image.bin"),
    ("V40", "_v40_plain_image.bin"), ("V41", "_v41_plain_image.bin"),
    ("V42", "_v42_plain_image.bin"), ("V43", "_v43_plain_image.bin"),
    ("V44", "_v44_plain_image.bin"), ("V45", "_v45_plain_image.bin"),
    ("V46", "_v46_plain_image.bin"), ("V47", "_v47_plain_image.bin"),
    ("V48a", "_v48a_plain_image.bin"), ("V48b", "_v48b_plain_image.bin"),
    ("V49", "_v49_plain_image.bin"), ("V49p", "_v49p_plain_image.bin"),
    ("V50", "_v50_plain_image.bin"), ("V50p", "_v50probe_plain_image.bin"),
    ("V51p", "_v51probe_plain_image.bin"), ("V52", "_v52_plain_image.bin"),
    ("V52c", "_v52c_plain_image.bin"), ("V53", "_v53_plain_image.bin"),
    ("V54", "_v54_plain_image.bin"), ("V55", "_v55_plain_image.bin"),
    ("V56", "_v56_plain_image.bin"), ("V57", "_v57_plain_image.bin"),
    ("V58", "_v58_plain_image.bin"), ("V59", "_v59_plain_image.bin"),
    ("V60", "_v60_plain_image.bin"), ("V61", "_v61_plain_image.bin"),
    ("V62", "_v62_plain_image.bin"), ("V63", "_v63_plain_image.bin"),
    ("V64", "_v64_plain_image.bin"), ("V65", "_v65_plain_image.bin"),
    ("V66", "_v66_plain_image.bin"), ("V67", "_v67_plain_image.bin"),
    ("V68", "_v68_plain_image.bin"), ("V69", "_v69_plain_image.bin"),
    ("V70", "_v70_plain_image.bin"), ("V71a", "_v71a_plain_image.bin"),
    ("V71b", "_v71b_plain_image.bin"), ("V71c", "_v71c_plain_image.bin"),
    ("V72", "_v72_plain_image.bin"), ("V73", "_v73_plain_image.bin"),
    ("V74", "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
    ("V75", "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
    ("V76", "_v76_v38base_relu_damper_plain_image.bin"),
    ("V76g", "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"),
    ("V77", "_v77_C63A0.1024_v74base_plain_image.bin"),
    ("V77b", "_v77b_C63A0.1024_v75base_plain_image.bin"),
    ("V78", "_v78_v76base_ey1_449_dose206_plain_image.bin"),
    ("V79", "_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin"),
    ("V80", "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin"),
    ("V81", "_v81_C407E.511-FRICTION.STOCK_plain_image.bin"),
    ("V83a", "_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin"),
    ("V84", "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin"),
    # ---- the V85..V98 era this file adds
    ("V85", "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin"),
    ("V86", "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V86b", "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V87", "_v87_V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98_plain_image.bin"),
    ("V88", "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256_plain_image.bin"),
    ("V89", "_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin"),
    ("V90", "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin"),
    ("V91", "_v91_V90BASE-CBE74.M26.M27.X1.5_plain_image.bin"),
    ("V92", "_v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4_plain_image.bin"),
    ("V93", "_v93_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75_plain_image.bin"),
    ("V94", "_v94_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75-427.SAR1_plain_image.bin"),
    # V95 is a BURNED build number -- no image, deliberately never cut.
    ("V96", "_v96_V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6_plain_image.bin"),
    ("V97", "_v97_V96BASE-C63AC.102to150_plain_image.bin"),
    ("V98", "_v98_V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2_plain_image.bin"),
    # ---- V99, added by this file
    ("V99", "_v99_V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1_plain_image.bin"),
    # ---- V100, added by ledger_v38_to_v100_bytes.py (V101 arc-map pass, 2026-08-13)
    ("V100", "_v100_V99BASE-CAVE.SAT.6AD6.C6200.4F60-SIGN.6B94-ID.B3CONST1-427.6B94_plain_image.bin"),
]

BURNED = {"V95": "deliberately BURNED build number -- never cut, no image, not a missing file"}

# =================================================================================================
# SITES -- (addr, width, signed, label, name_source)
#   width 1 = byte, 2 = LE halfword, 4 = LE float when signed == "f".
#   name_source: where the SEMANTIC NAME came from.  A name is BELIEF unless it is sourced here.
# =================================================================================================
_BL = "docs/BUILD-LINEAGE.md"
_V98 = "build_v98_tva.py FROZEN"
_V96 = "build_v96_tva.py FROZEN"
_V94L = "ledger_v94_cells.py MATRIX_SCALARS"
_V38B = "build_v38_tva.py"
_V87B = "build_v87_tva.py"

SITES = [
    # ---- CODE region: in-place branch / displacement / opcode edits
    (0x13109, 1, False, "part-number ASCII byte (cosmetic build marker, '-'->',')", _V94L),
    (0x14120, 1, False, "part-number ASCII byte, second copy (cosmetic)", _V94L),
    (0x2A1F0, 2, False, "V57 decouple displacement (7CD0 => reads 0xC6CD0)", _V87B),
    (0x3AA96, 1, False, "Lever B GATE byte (C5 = dead 0x683C / FB = latActive 0x6806)", _V98),
    (0x3AB76, 1, False, "Lever A: V62 sar on r26 (AA stock / A9 = x2)", _V98),
    (0x3AC20, 1, False, "Lever A: V62 sar on r24 (AA stock / A9 = x2)", _V98),
    (0x454FE, 1, False, "V42 macro-ratchet fix (BA = stock bne / B5 = br)", _V98),
    (0x55C0E, 4, "raw", "CAN 0x14A cave HOOK -- the 4-byte jarl that calls the cave at 0xC4B34", _V87B),
    (0x55DF2, 2, False, "CAN-427 packer SOURCE displacement (which gp cell 0x1AB carries)", _V94L),
    (0x55E10, 1, False, "CAN-427 packer SHIFT byte (sar N on the 427 payload)", _V94L),
    # ---- CALIBRATION region 0xC4000-0xCFFFF
    (0xC4048, 2, True, "friction-family cal (checked VIRGIN)", "task brief"),
    (0xC407C, 2, True, "friction-comp clamp neighbour", _V94L),
    (0xC407E, 2, True, "HARD-FAULT INTERLOCK CLAMP (Honda 511, one under its 512 trip)", _V98),
    (0xC4080, 2, True, "K0 pure-Coulomb arm -- recorded NEVER-RAISE relay hazard", _V98),
    (0xC40BC, 2, True, "Coulomb relay breakpoint / friction relay gate", _V98),
    (0xC40D0, 2, True, "friction EMA alpha (16.7 Hz)", _V98),
    (0xC40D2, 2, True, "K1 modelled Coulomb friction gain (the MODEL arm)", _V98),
    (0xC40D4, 2, True, "observer torque IIR / command-branch EMA", _V98),
    (0xC40D6, 2, True, "accel/inertia IIR", _V98),
    (0xC40D8, 2, True, "gp-0x4f60 IIR (a no-op)", _V98),
    (0xC4120, 1, False, "V48a-era cal byte", "empirical (this file)"),
    (0xC520C, 2, True, "governor rate ceiling / cap table (V40 bricked on a neighbour)", _V98),
    (0xC6158, 2, True, "ceiling tp+0x7158 fallback", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC616C, 2, True, "(checked VIRGIN)", "task brief"),
    (0xC6194, 2, True, "the REAL LKAS slew limiter -- DEAD (0xC4118 all-1)", _V98),
    (0xC61B2, 2, True, "ARBITRATION output clamp", _V94L),
    (0xC61B4, 2, True, "LKAS-GAIN output clamp", _V94L),
    (0xC61B8, 2, True, "pre-gain deadband", _V94L),
    (0xC61C0, 2, False, "gentle-EME debounce RATE threshold [0]", _V94L),
    (0xC61C2, 2, False, "gentle-EME debounce RATE threshold [1]", _V94L),
    (0xC61C4, 2, False, "gentle-EME debounce RATE threshold [2]", _V94L),
    (0xC61D6, 2, True, "(checked VIRGIN)", "task brief"),
    (0xC61DA, 2, True, "Q10 integrator scale", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC61F6, 2, True, "r24 lane deadzone", _V98),
    (0xC6200, 2, True, "gp-0x6b70's OUTPUT CLAMP", _V98),
    (0xC6206, 2, True, "speed-selector cal A (V40 brick)", _V94L),
    (0xC6208, 2, True, "speed-selector cal B (V40 brick)", _V94L),
    (0xC62EA, 2, True, "low-speed steer lockout window (320 ct ~ 5 km/h); 0 = steer-to-zero", _V98),
    (0xC6316, 2, True, "governor vehicle-speed cal ~10 km/h", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC636E, 2, True, "(checked VIRGIN)", "task brief"),
    (0xC6372, 2, True, "(checked VIRGIN)", "task brief"),
    (0xC63A0, 2, True, "Path-2 lane weight w[0], gp-0x6bd0 (the damper lane)", _V98),
    (0xC63A2, 2, True, "Path-2 lane weight w[1], gp-0x6bbe (VISCOUS)", _V98),
    (0xC63A4, 2, True, "Path-2 lane weight w[2], gp-0x6b46", _V98),
    (0xC63A6, 2, True, "Path-2 lane weight w[3], gp-0x6b26 (INERTIA -- the NO-GO lever)", _V98),
    (0xC63A8, 2, True, "Path-2 lane weight w[4], gp-0x6b4e (lane provably == 0)", _V98),
    (0xC63AA, 2, True, "Path-2 lane weight w[5], gp-0x6b4c (the LKAS lane)", _V98),
    (0xC63AC, 2, True, "Stage-1 IIR alpha on the ACTUAL arm (gp-0x374c>>4); fc ~15.9 Hz @1 kHz", _V98),
    (0xC63AE, 2, True, "Stage-2 input scale", _V98),
    (0xC63B8, 2, True, "(checked VIRGIN)", "task brief"),
    (0xC63D2, 2, True, "FUN_00036682 pole, fc 0.93 Hz", _V98),
    (0xC63F8, 2, True, "authority ramp-rate UP", _V94L),
    (0xC63FC, 2, True, "authority ramp-rate, the 10x-asymmetric twin", _V94L),
    (0xC640A, 2, True, "FUN_00036c12 FALLBACK-2 flat gain (gp-0x671a >= 5)", _V98),
    (0xC640C, 2, True, "FUN_00036c12 FALLBACK-1 flat gain (outer gate fails)", _V98),
    (0xC643E, 2, True, "gain_A arm", _V94L),
    (0xC6440, 2, True, "third arm gp-0x671a", _V94L),
    (0xC6442, 2, True, "gp-0x671d arm", _V94L),
    (0xC6444, 2, True, "r26 engaged arm", _V94L),
    (0xC6446, 2, True, "r24 engaged arm -- LEVER B ARM", _V98),
    (0xC644A, 2, True, "PID D-path IIR / V43 dirty-derivative pole", _V98),
    (0xC6450, 2, True, "V46 lever", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC6468, 2, True, "model output gain -- SHARED, scales BOTH arms of the residual", _V98),
    (0xC646C, 2, True, "SHARED sensor scale (Honda 891)", _V98),
    (0xC646E, 2, True, "INERTIA/damping gain", _V98),
    (0xC64B4, 2, False, "gentle-EME debounce TORQUE threshold [0]", _V94L),
    (0xC64B6, 2, False, "gentle-EME debounce TORQUE threshold [1]", _V94L),
    (0xC64B8, 1, False, "DTC-0x49 fail-counter gate", _V94L),
    (0xC64C8, 1, False, "aggregator mode selector", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC64C9, 1, False, "blend mux", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC64DE, 2, False, "legacy re-engage ramp ('RAMPSTEP', label disputed)", _V94L),
    (0xC64FA, 1, False, "CEIL byte cal", "ledger_v38_to_v84_bytes.py SITES"),
    (0xC6598, 4, "f", "corridor wall FLOAT +A", _V94L),
    (0xC659C, 4, "f", "corridor wall FLOAT +B", _V94L),
    (0xC65AC, 4, "f", "corridor wall FLOAT -A", _V94L),
    (0xC65B0, 4, "f", "corridor wall FLOAT -B", _V94L),
    (0xC65C4, 4, "f", "boost floor FLOAT [0]", _V94L),
    (0xC65C8, 4, "f", "boost floor FLOAT [1]", _V94L),
    (0xC65CC, 4, "f", "boost floor FLOAT [2]", _V94L),
    (0xC674E, 2, True, "corridor wall INT +A", _V94L),
    (0xC6750, 2, True, "corridor wall INT +B", _V94L),
    (0xC675A, 2, True, "corridor wall INT -A", _V94L),
    (0xC675C, 2, True, "corridor wall INT -B", _V94L),
    (0xC6768, 2, True, "boost floor INT [0]", _V94L),
    (0xC676A, 2, True, "boost floor INT [1]", _V94L),
    (0xC676C, 2, True, "boost floor INT [2]", _V94L),
    (0xC6A72, 2, True, "gain_A rec0 [0]"), (0xC6A74, 2, True, "gain_A rec0 [1]"),
    (0xC6A9A, 2, True, "gain_A rec2 Y[0]"), (0xC6AAE, 2, True, "gain_A rec3 Y[0]"),
    (0xC6AE6, 2, True, "PID Kd", _V98),
    (0xC6B12, 2, True, "PID Ki", _V98),
    (0xC6B26, 2, True, "PID Kp", _V98),
    (0xC6CD0, 2, True, "V57 private forward LKAS gain (3564 = 4.000x)", _V98),
    # ---- the friction / inertia dose family (Y triples, dereferenced addresses asserted in V98)
    (0xD6A6C, 2, True, "friction/inertia mode 24 (MANUAL) Y[0]", _V98),
    (0xD6A6E, 2, True, "friction/inertia mode 24 (MANUAL) Y[1]", _V98),
    (0xD6A70, 2, True, "friction/inertia mode 24 (MANUAL) Y[2]", _V98),
    (0xD7A5C, 2, True, "friction/inertia mode 26 (ENGAGED) Y[0]", _V98),
    (0xD7A5E, 2, True, "friction/inertia mode 26 (ENGAGED) Y[1]", _V98),
    (0xD7A60, 2, True, "friction/inertia mode 26 (ENGAGED) Y[2]", _V98),
    (0xD7A6C, 2, True, "friction/inertia mode 27 (ENGAGED) Y[0]", _V98),
    (0xD7A6E, 2, True, "friction/inertia mode 27 (ENGAGED) Y[1]", _V98),
    (0xD7A70, 2, True, "friction/inertia mode 27 (ENGAGED) Y[2]", _V98),
    # ---- ARB setpoint limit records are GENERATED below from the pointer array, not hard-coded.
    (0xE5284, 2, True, "AUTHORITY COLLAPSE curve record", _V98),
    (0xE52FC, 2, True, "AUTHORITY COLLAPSE curve record", _V98),
    (0xE5404, 2, True, "AUTHORITY COLLAPSE curve record", _V98),
    (0xE547C, 2, True, "AUTHORITY COLLAPSE curve record", _V98),
]
# normalise the two 3-tuples above that omit a source
SITES = [(s if len(s) == 5 else (*s, "ledger_v38_to_v84_bytes.py SITES")) for s in SITES]

VIRGIN_CHECK = [0xC4080, 0xC4048, 0xC40D0, 0xC40D6, 0xC40D8, 0xC63A2, 0xC63A4, 0xC63A6, 0xC63A8,
                0xC63AA, 0xC6372, 0xC636E, 0xC63B8, 0xC61D6, 0xC616C, 0xC6158, 0xC61DA, 0xC6206,
                0xC6208, 0xC6316, 0xC63F8, 0xC63FC, 0xC6B12, 0xC520C, 0xC6194,
                0xE547C, 0xE5404, 0xE52FC, 0xE5284]

# ---- pointer arrays for the mode-indexed factor tables
PTRS = {"FactorB": 0xC9CCC, "FactorC": 0xC9E9C, "FactorD": 0xC9DB4, "FactorE": 0xC9F84,
        "ceiling": 0xC77A0, "friction": 0xCBE74}
GAIN_B_PTRS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
SETPOINT_PTR = 0xCB844          # build_v38_tva.py SETPOINT_PTR_ARRAY
MODES = [10, 11, 12, 24, 25, 26, 27]

FLASH_LO, FLASH_HI = 0x13000, 0x100000
# The cave arena.  build_v96_tva.py puts the last real calibration family at [0xC4000, 0xC4B34);
# everything from 0xC4B34 to the block CRC is free space the telemetry caves have used since V31p
# (V53's cave ran to 0xC4E39; V98's occupies 0xC4B34-0xC4BCD).
CAVE_LO, CAVE_HI = 0xC4B34, 0xC4FFC
CAL_RANGES = [(0xC4000, 0xD0000), (0xD6000, 0xE6000)]
CRC_MASK = 0xFFC                              # per-4KiB-block CRC lives at block_base + 0xFFC


# build_v38_tva.py: [u16 n][9 x u16 X][9 x u16 Y][u16 pad], stride 0x28, Y at record + 0x14.
SETPOINT_STRIDE, SETPOINT_Y_OFF, SETPOINT_N, SETPOINT_SELECTORS = 0x28, 0x14, 9, 12
SETPOINT_LIVE_SELECTOR = 1          # build_v38_tva.py: A160 == variant slot 2, key 'TVAA1'


def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    n = u16(b, base)
    if not (1 <= n <= 16) or base + 2 + 4 * n > len(b):
        return None
    xs = list(struct.unpack_from(f"<{n}h", b, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n))
    return n, xs, ys


def generated_sites(st):
    """Cells whose ADDRESSES are DEREFERENCED from a pointer array -- never hard-coded.
    (build_v98_tva.py: 'AN ADDRESS IS NOT A MODE'.)"""
    gen = []
    for sel in range(SETPOINT_SELECTORS):
        base = u32(st, SETPOINT_PTR + 4 * sel)
        if not (FLASH_LO <= base < FLASH_HI) or u16(st, base) != SETPOINT_N:
            continue
        live = "  [LIVE selector for A160]" if sel == SETPOINT_LIVE_SELECTOR else ""
        for k in range(SETPOINT_N):
            gen.append((base + SETPOINT_Y_OFF + 2 * k, 2, False,
                        f"ARB SETPOINT LIMIT sel{sel} Y[{k}] -- the +/-clamp on the LKAS setpoint "
                        f"gp-0x69ae{live}", _V38B, "ARB_SETPOINT_LIMIT"))
    fp = PTRS["friction"]
    for m in range(34):
        base = u32(st, fp + 4 * m)
        if not (FLASH_LO <= base < FLASH_HI):
            continue
        r = rec(st, base)
        if not r:
            continue
        kind = {24: " (MANUAL)", 25: " (MANUAL)", 26: " (ENGAGED)", 27: " (ENGAGED)"}.get(m, "")
        for k in range(r[0]):
            gen.append((base + 2 + 2 * r[0] + 2 * k, 2, True,
                        f"friction/inertia LERP mode {m}{kind} Y[{k}] "
                        f"(X={r[1][k]}) -- 0xCBE74 dose family", _V98, f"FRICTION_M{m}"))
    return gen


def all_cells(st):
    """SITES (fixed addresses) + generated (dereferenced).  Returns (cells, addr -> cell index)."""
    cells = [(a, w, sg, lab, src, None) for a, w, sg, lab, src in SITES] + generated_sites(st)
    amap = {}
    for i, (a, w, sg, lab, src, fam) in enumerate(cells):
        wid = 4 if sg in ("f", "raw") else w
        for off in range(wid):
            amap.setdefault(a + off, i)
    return cells, amap


def load_all():
    imgs, order, missing = {}, [], []
    for name, f in BUILDS:
        p = f if isinstance(f, Path) else ROOT / f
        if not p.exists():
            missing.append((name, str(p)))
            print(f"### MISSING (skipped, not fatal): {name}: {p}")
            continue
        b = p.read_bytes()
        assert len(b) == 0x100000, f"{name}: len {len(b):#x} != 0x100000"   # DELIVERABLE A.3
        imgs[name] = b
        order.append(name)
    st = imgs["STOCK"]
    assert len(st) == 0x100000, len(st)
    assert s16(st, 0xC646C) == 891, s16(st, 0xC646C)      # guards the off-by-0x1000 tp trap
    assert st[0x454FE] == 0xBA, hex(st[0x454FE])
    assert u32(st, PTRS["friction"] + 24 * 4) < 0x100000
    for tag, why in BURNED.items():
        print(f"### BURNED: {tag} -- {why}")
    return imgs, order, missing


def packaging_mask(imgs, order):
    """Bytes that are 0xFF in EVERY non-stock image but not in stock => RWD packaging, not levers."""
    st = imgs["STOCK"]
    tags = [n for n in order if n != "STOCK"]
    cand = [i for i in range(len(st)) if st[i] != 0xFF and imgs[TARGET][i] == 0xFF]
    return {i for i in cand if all(imgs[t][i] == 0xFF for t in tags)}, cand


def group(addrs):
    runs, cur = [], None
    for i in sorted(addrs):
        if cur and i == cur[1] + 1:
            cur[1] = i
        else:
            cur = [i, i]
            runs.append(cur)
    return runs


def region_of(a):
    if (a & 0xFFF) >= CRC_MASK:
        return "CRC"
    if CAVE_LO <= a < CAVE_HI:
        return "CAVE"
    if any(lo <= a < hi for lo, hi in CAL_RANGES):
        return "CAL"
    if a < 0x13000:
        return "PRE-FLASH"
    return "CODE"


def first_nonstock(imgs, order, addr):
    sv = imgs["STOCK"][addr]
    for n in order:
        if n != "STOCK" and imgs[n][addr] != sv:
            return n
    return None


def _read(b, addr, w, sg):
    if sg == "f":
        return f"{struct.unpack_from('<f', b, addr)[0]:g}f"
    if sg == "raw":
        return b[addr:addr + w].hex()
    if w == 1:
        return f"0x{b[addr]:02X}"
    return str(s16(b, addr) if sg else u16(b, addr))


def segments(order, valfn):
    segs, prev, run = [], None, []
    for n in order:
        v = valfn(n)
        if v != prev:
            if run:
                segs.append((prev, run))
            run, prev = [n], v
        else:
            run.append(n)
    if run:
        segs.append((prev, run))
    return segs


# =================================================================================================
# DELIVERABLE B1 -- the empirical union of every address that ever left stock
# =================================================================================================
def cmd_b1(imgs, order, mask):
    st = imgs["STOCK"]
    post = order[order.index("V38"):]
    union = set()
    for t in post:
        b = imgs[t]
        union |= {i for i in range(len(st)) if b[i] != st[i]}
    union -= mask
    runs = group(union)
    print(f"\n{'='*100}\nB1. UNION OF EVERY ADDRESS THAT DIFFERS FROM STOCK ON ANY BUILD V38..V98")
    print(f"    {len(union)} non-mask bytes in {len(runs)} contiguous runs\n{'='*100}")
    by_region = {}
    for a, b in runs:
        by_region.setdefault(region_of(a), []).append((a, b))
    for regname in ("CODE", "CAVE", "CAL", "CRC", "PRE-FLASH"):
        rs = by_region.get(regname, [])
        if not rs:
            continue
        tot = sum(b - a + 1 for a, b in rs)
        print(f"\n--- REGION {regname}: {len(rs)} runs, {tot} bytes ---")
        for a, b in rs:
            firsts = sorted({first_nonstock(imgs, order, x) for x in range(a, b + 1)},
                            key=lambda n: order.index(n) if n else 999)
            fs = "/".join(x or "?" for x in firsts)
            segs = segments(order, lambda n: imgs[n][a:b + 1].hex())
            comp = " | ".join(f"{(r[0] + '..' + r[-1]) if len(r) > 1 else r[0]}={v}"
                              for v, r in segs) if len(segs) <= 8 and (b - a) < 12 else \
                   f"{len(segs)} distinct values across builds"
            print(f"  0x{a:05X}-0x{b:05X} len{b - a + 1:>4}  first={fs:<20} {comp}")
    return union


# =================================================================================================
# DELIVERABLE B2 -- FROZEN counts (length of the trailing unchanged run)
# =================================================================================================
def cmd_b2(imgs, order, union=None):
    st = imgs["STOCK"]
    print(f"\n{'='*100}\nB2. FROZEN COUNTS -- 'unchanged for the last N builds' (N excludes the STOCK row)"
          f"\n    N counts consecutive BUILD images, newest-last, holding the value they hold on {TARGET}."
          f"\n{'='*100}")
    nb = len(order) - 1
    print(f"    {nb} build images on disk.  N == {nb} means NEVER MOVED ON ANY BUILD.\n")
    rows = []
    for addr, w, sg, label, src in SITES:
        segs = segments(order, lambda n: _read(imgs[n], addr, w, sg))
        last_v, last_r = segs[-1]
        frozen = len([n for n in last_r if n != "STOCK"])
        sv = _read(st, addr, w, sg)
        state = "STOCK" if last_v == sv else "NON-STOCK"
        rows.append((addr, label, sv, last_v, state, frozen, last_r[0], len(segs) - 1, src))
    rows.sort(key=lambda r: (r[5], r[0]))
    print(f"{'addr':<10} {'N frozen':>8} {'since':<7} {'moves':>5} {'stock':>10} "
          f"{TARGET:>10}  {'state':<10} what")
    for addr, label, sv, cv, state, fr, since, nmov, src in rows:
        print(f"0x{addr:05X}   {fr:>8} {since:<7} {nmov:>5} {sv:>10} {cv:>10}  {state:<10} {label}")
    return rows


# =================================================================================================
# DELIVERABLE B3 -- VIRGIN verdicts
# =================================================================================================
def cmd_b3(imgs, order):
    st = imgs["STOCK"]
    print(f"\n{'='*100}\nB3. VIRGIN VERDICTS -- byte-identical to STOCK on ALL {len(order)-1} images?"
          f"\n{'='*100}")
    out = {}
    for addr in VIRGIN_CHECK:
        w = 2
        movers = [n for n in order if n != "STOCK" and imgs[n][addr:addr + w] != st[addr:addr + w]]
        sv = s16(st, addr)
        if not movers:
            print(f"0x{addr:05X}  VIRGIN                       stock={sv}")
            out[f"0x{addr:05X}"] = {"verdict": "VIRGIN", "stock": sv}
        else:
            vals = sorted({s16(imgs[n], addr) for n in movers})
            print(f"0x{addr:05X}  MOVED-ON-BUILD-{movers[0]:<12} stock={sv}  "
                  f"{TARGET}={s16(imgs[TARGET], addr)}  moved on {len(movers)} builds {movers[:6]}"
                  f"{'...' if len(movers) > 6 else ''}  values seen {vals}")
            out[f"0x{addr:05X}"] = {"verdict": f"MOVED-ON-BUILD-{movers[0]}", "stock": sv,
                                    TARGET: s16(imgs[TARGET], addr), "movers": movers,
                                    "values": vals}
    return out


# =================================================================================================
# DELIVERABLE C -- the cumulative non-stock delta of a build
# =================================================================================================
SEMANTIC = {a: (lab, src) for a, w, sg, lab, src in SITES}


def cave_note(a):
    return "0x14A byte4/byte7 telemetry CAVE (probe code; changes NO control signal)"


def cmd_delta(imgs, order, mask, tag):
    st = imgs["STOCK"]
    tb = imgs[tag]
    diffs = [i for i in range(len(st)) if tb[i] != st[i] and i not in mask]
    runs = group(diffs)
    print(f"\n{'='*100}\nC. CUMULATIVE NON-STOCK DELTA -- {tag} vs STOCK")
    print(f"   image sha256 {hashlib.sha256(tb).hexdigest()}")
    print(f"   {len(diffs)} differing non-mask bytes in {len(runs)} runs\n{'='*100}")

    cave, crc, ctrl, unattr = [], [], [], []
    for a, b in runs:
        reg = region_of(a)
        firsts = sorted({first_nonstock(imgs, order, x) for x in range(a, b + 1)},
                        key=lambda n: order.index(n) if n else 999)
        fs = "/".join(x or "?" for x in firsts)
        item = {"lo": a, "hi": b, "len": b - a + 1, "first": fs,
                "stock_hex": st[a:b + 1].hex(), "val_hex": tb[a:b + 1].hex(), "region": reg}
        if None in firsts:
            unattr.append(item)
        if reg == "CAVE":
            cave.append(item)
        elif reg == "CRC":
            crc.append(item)
        else:
            ctrl.append(item)

    print(f"\n--- LIST 1: CAVE / PROBE bytes (telemetry code; does NOT change the control law) ---")
    tot = sum(x["len"] for x in cave)
    for x in cave:
        print(f"  0x{x['lo']:05X}-0x{x['hi']:05X}  {x['len']:>4} bytes   first={x['first']}"
              f"   {cave_note(x['lo'])}")
    print(f"  TOTAL CAVE: {tot} bytes")
    print(f"\n--- CRC/packaging consequences (block checksums; not levers) ---")
    for x in crc:
        print(f"  0x{x['lo']:05X}-0x{x['hi']:05X}  {x['len']:>4} bytes   "
              f"per-4KiB block CRC for block 0x{x['lo'] & ~0xFFF:05X}  "
              f"stock={x['stock_hex']} -> {x['val_hex']}")
    print(f"  TOTAL CRC: {sum(x['len'] for x in crc)} bytes")

    # --- resolve the control-law bytes PER BYTE onto named cells, then collapse families
    cells, amap = all_cells(st)
    ctrl_bytes = [i for x in ctrl for i in range(x["lo"], x["hi"] + 1)]
    seen, unnamed, ctrl_cells = {}, [], []
    for i in ctrl_bytes:
        ci = amap.get(i)
        if ci is None:
            unnamed.append(i)
            continue
        seen.setdefault(ci, []).append(i)
    for ci, addrs in seen.items():
        a, w, sg, lab, src, fam = cells[ci]
        wid = 4 if sg in ("f", "raw") else w
        ctrl_cells.append({"addr": f"0x{a:05X}", "width": wid,
                           "stock": _read(st, a, wid, sg), tag: _read(tb, a, wid, sg),
                           "first_build": first_nonstock(imgs, order, addrs[0]),
                           "what": lab, "name_source": src, "family": fam})
    for a, b in group(unnamed):
        ctrl_cells.append({"addr": f"0x{a:05X}-0x{b:05X}", "width": b - a + 1,
                           "stock": st[a:b + 1].hex(), tag: tb[a:b + 1].hex(),
                           "first_build": first_nonstock(imgs, order, a),
                           "what": "*** UNNAMED -- no SITES entry and not in any pointer table ***",
                           "name_source": None, "family": None})
    ctrl_cells.sort(key=lambda c: int(c["addr"].split("-")[0], 16))

    print(f"\n--- LIST 2: CONTROL-LAW cells (calibration + in-place code edits) ---")
    print(f"{'addr':<10} {'w':>2} {'stock':>12} {tag:>12}  {'first':<7} what")
    fam_done = set()
    for c in ctrl_cells:
        if c["family"]:
            key = (c["family"], c["stock"], c[tag], c["first_build"])
            if key in fam_done:
                continue
            fam_done.add(key)
            sibs = [x for x in ctrl_cells if (x["family"], x["stock"], x[tag],
                                              x["first_build"]) == key]
            span = f"{sibs[0]['addr']}..{sibs[-1]['addr']}" if len(sibs) > 1 else sibs[0]["addr"]
            print(f"{span:<24} {c['width']:>2} {c['stock']:>12} {c[tag]:>12}  "
                  f"{c['first_build']:<7} {c['what'].split(' -- ')[0]}"
                  f"{f'   [x{len(sibs)} cells, identical value]' if len(sibs) > 1 else ''}")
        else:
            print(f"{c['addr']:<10} {c['width']:>2} {c['stock']:>12} {c[tag]:>12}  "
                  f"{c['first_build']:<7} {c['what']}")
    print(f"  TOTAL CONTROL-LAW: {sum(x['len'] for x in ctrl)} bytes in {len(ctrl)} runs, "
          f"{len(ctrl_cells)} named cells, {len(unnamed)} unnamed bytes")

    if unattr:
        print(f"\n🛑🛑 UNATTRIBUTED BYTES ({sum(x['len'] for x in unattr)}): differ from stock on "
              f"{tag} but NO build in the chain is the first to move them -- IMPOSSIBLE unless the "
              f"chain is incomplete.  THIS IS A FINDING.")
        for x in unattr:
            print(f"    0x{x['lo']:05X}-0x{x['hi']:05X} {x['len']}")
    else:
        print(f"\n✅ ZERO UNATTRIBUTED BYTES -- every one of the {len(diffs)} differing bytes on "
              f"{tag} is attributed to a build present in the on-disk chain.")

    return {"build": tag, "sha256": hashlib.sha256(tb).hexdigest(),
            "total_differing_bytes": len(diffs), "runs": len(runs),
            "cave": cave, "cave_total_bytes": tot, "crc": crc,
            "control_law": ctrl_cells,
            "control_law_total_bytes": sum(x["len"] for x in ctrl),
            "unattributed": unattr}


def cmd_pairdiff(imgs, order, base, targ):
    st = imgs["STOCK"]
    bb, tb = imgs[base], imgs[targ]
    d = [i for i in range(len(st)) if bb[i] != tb[i]]
    print(f"\n{'='*100}\n{base} -> {targ}: {len(d)} differing bytes in {len(group(d))} runs\n{'='*100}")
    for a, b in group(d):
        print(f"  0x{a:05X}-0x{b:05X} {b - a + 1:>4} [{region_of(a)}]\n"
              f"      {base}: {bb[a:b + 1].hex()}\n      {targ}: {tb[a:b + 1].hex()}")


def cmd_matrix(imgs, order):
    print(f"\n{'='*100}\nA. CROSS-BUILD MATRIX -- every SITES cell, run-length along build order"
          f"\n{'='*100}")
    st = imgs["STOCK"]
    for addr, w, sg, label, src in SITES:
        segs = segments(order, lambda n: _read(imgs[n], addr, w, sg))
        sv, cv = _read(st, addr, w, sg), _read(imgs[TARGET], addr, w, sg)
        frozen = len([n for n in segs[-1][1] if n != "STOCK"])
        print(f"\n0x{addr:05X}  {label}   [name src: {src}]")
        print(f"    stock={sv}  {TARGET}={cv}  "
              f"[{'STOCK' if cv == sv else 'NON-STOCK'}]  frozen {frozen} builds (since {segs[-1][1][0]})")
        for v, r in segs:
            rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
            flag = "   <-- BACK TO STOCK" if (v == sv and r[0] != "STOCK") else ""
            print(f"      {rng:<18} {v}{flag}")

    print(f"\n{'='*100}\nFACTOR / GAIN_B RECORDS (only entries that CHANGE)\n{'='*100}")
    for fname, ptr in list(PTRS.items()) + [(f"gain_B[{i}]", p) for i, p in enumerate(GAIN_B_PTRS)]:
        for m in MODES:
            def val(n):
                b = imgs[n]
                base = u32(b, ptr + m * 4)
                if base >= 0x100000:
                    return f"PTR_OOR 0x{base:08X}"
                r = rec(b, base)
                return f"@0x{base:05X} n={r[0]} X={r[1]} Y={r[2]}" if r else f"BAD@0x{base:05X}"
            segs = segments(order, val)
            if len(segs) == 1:
                continue
            print(f"\n{fname} m{m}:")
            for v, r in segs:
                rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
                print(f"    {rng:<18} {v}")


def cmd_mask(imgs, order, mask, cand):
    print(f"\n{'='*100}\nCOVERAGE MASK AUDIT\n{'='*100}")
    print(f"stock non-FF where {TARGET} is FF : {len(cand)} bytes")
    print(f"of which FF in EVERY build        : {len(mask)}  => packaging, excluded from diffs")
    runs, co = group(mask), []
    for a, b in runs:
        if co and a - co[-1][1] < 0x100:
            co[-1][1] = b
        else:
            co.append([a, b])
    for a, b in co:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")
    late = sorted(set(cand) - mask)
    print(f"\nFF on {TARGET} but NOT on every build ({len(late)}) -- REAL EDITS, kept in the diff:")
    for a in late:
        print(f"    0x{a:05X} first went FF at {first_nonstock(imgs, order, a)}")


def main():
    imgs, order, missing = load_all()
    print(f"\nANCHORS OK: stock 0xC646C=891, code.bin[0x454FE]=0xBA, every image len=0x100000")
    print(f"{len(order) - 1} build images on disk (V22..V99); TARGET={TARGET}, "
          f"previous-on-car={PREV_ON_CAR}")
    mask, cand = packaging_mask(imgs, order)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "diff":
        return cmd_pairdiff(imgs, order, sys.argv[2], sys.argv[3])
    if cmd == "matrix":
        return cmd_matrix(imgs, order)
    if cmd == "frozen":
        return cmd_b2(imgs, order)
    if cmd == "virgin":
        return cmd_b3(imgs, order)
    if cmd == "mask":
        return cmd_mask(imgs, order, mask, cand)
    if cmd == "delta":
        return cmd_delta(imgs, order, mask, TARGET)

    # ---- everything
    cmd_mask(imgs, order, mask, cand)
    cmd_matrix(imgs, order)
    union = cmd_b1(imgs, order, mask)
    rows = cmd_b2(imgs, order, union)
    virgin = cmd_b3(imgs, order)
    d98 = cmd_delta(imgs, order, mask, TARGET)
    d97 = cmd_delta(imgs, order, mask, PREV_ON_CAR)
    cmd_pairdiff(imgs, order, PREV_ON_CAR, TARGET)

    print(f"\n{'='*100}\nPER-BUILD DELTA vs IMMEDIATE PREDECESSOR (V84..{TARGET})\n{'='*100}")
    i0 = order.index("V84")
    for i in range(i0, len(order)):
        prev, cur = order[i - 1], order[i]
        d = [x for x in range(len(imgs[cur])) if imgs[prev][x] != imgs[cur][x]]
        regs = {}
        for x in d:
            regs[region_of(x)] = regs.get(region_of(x), 0) + 1
        print(f"  {prev:>6} -> {cur:<6}: {len(d):>5} bytes, {len(group(d)):>3} runs   {regs}")

    js = {"target": TARGET, "previous_on_car": PREV_ON_CAR,
          "builds_on_disk": [n for n in order],
          "missing_images": missing, "burned_build_numbers": BURNED,
          "anchors": {"0xC646C": 891, "code.bin[0x454FE]": "0xBA", "len": "0x100000"},
          "packaging_mask_bytes": len(mask),
          "virgin": virgin,
          "frozen": [{"addr": f"0x{a:05X}", "what": lab, "stock": sv, TARGET: cv,
                      "state": stt, "frozen_builds": fr, "since": since, "moves": nmov,
                      "name_source": src}
                     for a, lab, sv, cv, stt, fr, since, nmov, src in rows],
          "delta_vs_stock": {TARGET: d98, PREV_ON_CAR: d97}}
    outp = HERE / "v99_vs_stock_delta.json"
    outp.write_text(json.dumps(js, indent=1, default=str))
    print(f"\nwrote {outp}")


if __name__ == "__main__":
    main()
