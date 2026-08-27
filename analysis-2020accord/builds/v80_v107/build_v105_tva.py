#!/usr/bin/env python3
r"""=================================================================================================
V105 -- RETUNE Honda's biquad from a 55 Hz notch to a **25.5 Hz notch** (E1), and repoint the
        cave's `b6` rung to a **governor clip-duty comparator** (E2).  Cal-only + two displacement
        immediates INSIDE an already-flown cave pass.  NO NEW CAVE CODE, NO LENGTH CHANGE, NO NEW
        REGISTER, NO MASK CHANGE, RET UNTOUCHED.
=================================================================================================

BASE: **V104** (`_v104_V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4_plain_image.bin`)
      sha256 b556a0b16da5ac2ad850cae036e5533a4de347e84f2c907f37653cc0f7201a03, 1,048,576 B.

🛑 **V104 FLEW, as route `a4`.**  `docs/STATE.md` and `docs/BUILD-LINEAGE.md` both still say
"V104 BUILT, NOT FLASHED" -- **both are STALE**, confirmed from telemetry by the orchestrator.
Do not trust the on-car status in any doc; this builder does not depend on it either way.

-------------------------------------------------------------------------------------------------
E1 -- THE PLANT, DECOMPILED.  `FUN_000352b4`.  Every constant read LITTLE-ENDIAN off the base.
-------------------------------------------------------------------------------------------------
Ghidra's decompile of the armed branch (tp = 0xBF000, so tp+0x70a8 = 0xC60A8 -- NOT 0xC70A8):

    cVar4 = *(char *)(tp + 0x749b);                       // 0xC649B  ARM CAL   -- V103 set it to 1
    *(short *)(gp + -0x6b7e) = (short)(iVar14 >> 7);       // p[n], the near-DC PEDESTAL
    if ((cVar4 == '\x01') && (<V103's engaged test>)) {
        fVar29 = *(float *)(gp + -0x3818);                                     // w[n-1]
        fVar37 = -( *(float*)(tp+0x70ac) * *(float*)(gp+-0x3814)               // a2 * w[n-2]
                  - -( fVar29 * *(float*)(tp+0x70a8)                           // a1 * w[n-1]
                     - (float)iVar34 * 0.0009765625 * *(float*)(tp+0x70b4) ));  // c4 * u[n]
        fVar38 = *(float*)(gp+-0x3814) + fVar29 * *(float*)(tp+0x70b0) + fVar37;
        *(float *)(gp + -0x3814) = fVar29;                 // w[n-2] <- w[n-1]
        *(float *)(gp + -0x3818) = fVar37;                 // w[n-1] <- w[n]
        ... fVar22 = clamp(fVar38, -12.0f, +12.0f) ...
        iVar34 = (int)(fVar22 * 1024.0);                   // |iVar34| <= 12288
    }
    sVar15 = (short)iVar34 + (short)(iVar14 >> 7);         // filter output + pedestal
    sVar15 = clamp(sVar15, -0x3000, +0x3000);              // +-12288
    *(short *)(gp + -0x6b86) = sVar15;                     // THE LANE OUTPUT

Unfolding the sign nest gives the recursion EXACTLY (u[n] = gp-0x6b82 / 1024, fs = 1000 Hz):

    w[n] = c4*u[n] - a1*w[n-1] - a2*w[n-2]           a1  @ 0xC60A8
    y[n] = w[n] + b1*w[n-1] + w[n-2]                 a2  @ 0xC60AC
                                                     b1  @ 0xC60B0
    H(z) = c4 * (1 + b1*z^-1 + z^-2)                 c4  @ 0xC60B4
                / (1 + a1*z^-1 + a2*z^-2)            DIRECT FORM II

-------------------------------------------------------------------------------------------------
🛑 WHAT E1 DOES, AND WHAT IT UNDOES.  ALL FOUR COEFFICIENTS MOVE -- THIS IS A RE-TUNE, NOT A DOSE.
-------------------------------------------------------------------------------------------------
🛑🛑 **THE FORMULA IS THE SPECIFICATION.  THE DECIMALS BELOW ARE DISPLAY ONLY.**  A 6-decimal-place
decimal DOES NOT ROUND-TRIP A FLOAT32: `a1` needs 8 significant digits, `b1` needs 9.  Three agents
produced three different byte strings for `b1` in one session -- not an encoding bug, they encoded
three DIFFERENT NUMBERS, each correctly.  The builder DERIVES all four at double precision from
`R_POLE = 0.950, F_POLE = 22.0 Hz, F_ZERO = 25.5 Hz, fs = 1000 Hz` and only then packs.

| cell | V104 (flown) | V105 (derived) | float32 | role |
|---|---|---|---|---|
| 0xC60A8 `a1` | -1.5372   | -1.8818767088236372 | `56e1f0bf` | pole angle -- 42.35 Hz -> **22.00 Hz** |
| 0xC60AC `a2` | +0.63462  |  0.9025             | `3d0a673f` | pole radius -- 0.796630 -> **0.950000** |
| 0xC60B0 `b1` | -1.8808   | -1.9743840279896383 | `9eb8fcbf` | ZERO angle -- **the notch centre**, 55.23 -> **25.50 Hz** |
| 0xC60B4 `c4` | +1.512023 |  0.8050950074438165 | `b51a4e3f` | scalar input gain -- **V104's x1.85 IS REVERTED** |

    a1 = -2*R_POLE*cos(2*pi*F_POLE/fs)      a2 = R_POLE**2
    b1 = -2*cos(2*pi*F_ZERO/fs)             c4 = (1 + a1 + a2) / (2 + b1)

⚠ **`c4` 1.512023 -> 0.805095 IS FORCED BY THE UNITY-DC CONSTRAINT, NOT CHOSEN.**  `H(0) =
c4*(2+b1)/(1+a1+a2)`, so `c4 = (1+a1+a2)/(2+b1)` is the ONLY value that holds `|H(0)| = 1`.  You
cannot keep V104's `c4` and hold DC.  It lands **within 1.5 % of Honda's stock 0.817310**, so V105
reads as *"V104 with Honda's flat gain restored and the filter re-shaped"* -- **not a gain lever and
not a stray edit.**  V104's x1.85 flew and produced a null; carrying it would have made the retuned
notch a broadband raise as well, the very thing V104 showed does nothing useful.

**WHAT CHANGED IN KIND, vs V104.**  V104 moved `c4` ONLY -- a pure scalar, which by construction
CANNOT move the notch: it scaled the whole response by 1.85 and left the null at 55.23 Hz, decades
above every symptom band, so the ratio was a **flat x1.85 in 6-9 Hz and in 20-28 Hz alike**.  V105
moves `a1`/`a2`/`b1` -- **the first build ever to move the notch's own SHAPE and CENTRE** -- and puts
the null **on the 21-26 Hz band the record indicts**, while holding DC at unity so the operator feels
no weight change.  V104 = amplitude on a filter aimed at nothing.  V105 = aim.

    f (Hz)    |H| V104    |H| V105     V105 dB     V105 phase
      1.00      1.8500     0.999837     -0.00       -1.70 deg
      6.00      1.8314     0.992887     -0.06      -10.80 deg
      7.79      1.8185     0.986282     -0.12      -14.58 deg      <- the ratchet line, ~untouched
      9.00      1.8155     0.979589     -0.18      -17.40 deg
     15.00      1.7300     0.883790     -1.07      -36.99 deg
     20.00      1.5000     0.589282     -4.59      -65.30 deg
     21.73      1.5830     0.414964     -7.64      -77.60 deg      <- the ~21-23 Hz vibration line
     24.00      1.4870     0.160122    -15.91      -93.78 deg
     24.90      1.4780     0.062089    -24.14      -99.76 deg      <- lower skirt endpoint
     25.50      1.4700     0.0000021  -113.61      +76.47 deg      <- THE NULL
     26.80      1.4300     0.122877    -18.21      +68.96 deg      <- upper skirt endpoint
     30.00      1.3900     0.351530     -9.08      +54.41 deg
     55.23      0.0002     0.764000     -2.34      +19.90 deg      <- V104's null, now just a shelf
    499.00      1.8500     0.845518     -1.46       +0.01 deg

⭐ **THE 25.5 Hz CUT BITES HARDER THAN THE SUPERSEDED 26.0 Hz ONE where it matters:** at 21.73 Hz
0.4683 -> **0.4150**, at 24 Hz 0.2163 -> **0.1601**, and it costs almost nothing at the ratchet line
(0.9881 -> 0.9863).  The pole also moved 22.5 -> 22.0 Hz, keeping the pole/zero spacing.

-------------------------------------------------------------------------------------------------
🛑 GATE 2 -- MAGNITUDE PASSES OUTRIGHT.  PHASE IS A STATED RESIDUAL, NOT AN ASSERTED PASS.
-------------------------------------------------------------------------------------------------
**MAGNITUDE [EVIDENCE, computed below from the BUILT image's own bytes over 200,000 points]:**
`max |H| = 0.999999 over 0.01-499.9 Hz`, attained at DC.  `|H| <= 1` EVERYWHERE ⇒ **the section can
only REMOVE loop gain, never add it**, at every frequency, for every loop the lane sits in.  That is
the same GATE 2 argument V103 passed on, and it is unconditional.  Poles |p| = 0.950 < 0.97 ⇒ stable,
tau = 19.50 ms, 99 % ring-down 89.78 ms -- short against the 15-30 s symptomatic drive.

⚠ **PHASE -- STATED PLAINLY BECAUSE IT IS THE ONE THING THIS EDIT CANNOT ASSERT AWAY.**  A notch
adds LAG below its centre and LEAD above it.  At 7.79 Hz -- the measured ratchet line, a lightly
damped resonance with zeta 0.017-0.036 (`accord-ratchet-is-a-lightly-damped-resonance`) -- this
section contributes **-14.58 deg with |H| = 0.986**.  Magnitude alone cannot destabilise a loop it
only attenuates, but ~14 deg of lag in a lane whose 6-9 Hz `Re(Z)` is already NEGATIVE on three
drives (`accord-rez-antidamping-replicated-three-drives`) is a real term, and it is **not** covered
by the |H| <= 1 argument.  **BELIEF, not evidence:** the residual is small relative to the -3375 to
-3073 ct.s/rad gap those drives measured, and the 0.98 magnitude assertion below bounds the
amplitude side of it.  **This build does not close it, and the null it licenses does not either.**

-------------------------------------------------------------------------------------------------
E2 -- THE `b6` RUNG REPOINTED.  Two halfwords, inside the flown 46-byte PASS1 block.
-------------------------------------------------------------------------------------------------
PASS1 is a two-operand magnitude comparator that writes CAN 0x14A byte4 bit 6.  Disassembled off
the V104 image (GhidraMCP, and re-decoded from the BUILT image by this script):

    +0x00  0xC4B34  24372695   ld.h  -0x6ada, gp, r6      <- OPERAND A   ** E2a moves this disp **
    +0x04  0xC4B38  6032       cmp   0x0, r6
    +0x06  0xC4B3A  ae05       bge   +4
    +0x08  0xC4B3C  8031       subr  r0, r6                  negate  => r6 = |A|
    +0x0A  0xC4B3E  0638       mov   r6, r7                  r7 = |A|
    +0x0C  0xC4B40  24372495   ld.h  -0x6adc, gp, r6      <- OPERAND B   ** E2b moves this disp **
    +0x10  0xC4B44  6032       cmp   0x0, r6
    +0x12  0xC4B46  ae05       bge   +4
    +0x14  0xC4B48  8031       subr  r0, r6                  r6 = |B|
    +0x16  0xC4B4A  e639       cmp   r6, r7                  flags on (|A| - |B|)
    +0x18  0xC4B4C  043a       mov   0x4, r7
    +0x1A  0xC4B4E  ae05       bge   +4                      |A| >= |B|  => keep 4
    +0x1C  0xC4B50  003a       mov   0x0, r7                 else        => 0
    +0x1E  0xC4B52  c43a       shl   0x4, r7                 4<<4 = 0x40 = BIT 6
    +0x20  0xC4B54  8437edea   ld.bu -0x1514, gp, r6         read byte4
    +0x24  0xC4B58  c636bf00   andi  0xbf, r6, r6            clear bit 6 ONLY (Honda's 2:0 kept)
    +0x28  0xC4B5C  0731       or    r7, r6
    +0x2A  0xC4B5E  4437ecea   st.b  r6, -0x1514, gp         write back

    b6  ==  ( |A| >= |B| )

| addr | V104 | V105 | operand |
|---|---|---|---|
| 0xC4B36 | `26 95` = -0x6ADA | **`6C 94` = -0x6B94** | A: `gp-0x6b94`, the AGGREGATOR SUM |
| 0xC4B42 | `24 95` = -0x6ADC | **`9C B0` = -0x4F64** | B: `gp-0x4f64`, the GOVERNOR BOUND |

⇒ **`b6` becomes `|gp-0x6b94| >= |gp-0x4f64|` -- the governor clip comparator.  ITS DUTY IS THE
ANSWER.**  This is the design law's escape from sizing: a COMPARATOR rung is immune to under- and
over-range by construction -- it compares at full precision inside the cave, before quantisation
exists.  No LSB, no ceiling, no assumed distribution.

⭐ **ENCODING RISK IS ZERO ON BOTH HALFWORDS [EVIDENCE].**
  * `24 37 6c 94` = `ld.h -0x6b94, gp, r6` **already exists VERBATIM at 0x453E0 in this very image.**
  * Both were confirmed by GhidraMCP `disassemble_bytes(dry_run=true)` on a scratch
    `V850:LE:32:default` import of the FULL 46-byte PASS1 block, BEFORE any byte was written: the
    V105 block decodes to the **same 18 instructions at the same 18 offsets** as V104's, with only
    the two `ld.h` displacements changed.
  * Both displacements are EVEN (bit0 = 0), which `ld.h` requires -- unlike `ld.bu`'s `disp|1` form.
  * hw1 is `24 37` on both sides ⇒ same opcode, same base register (gp), same destination (r6).

🛑 **WHAT E2 DOES *NOT* TOUCH** -- each asserted below, from the built image:
  cave LENGTH (164 B, unchanged) · the `andi 0xbf` MASK · the `st.b`/`ld.bu` RAM cells (gp-0x1514)
  · the REGISTERS used (r6/r7 only, exactly as flown) · the `bge` displacements · the RET
  (`jmp [lp]` at +0xA2) · PASS2 / PASS3 / BYTE7 · the hook at 0x55C0E.
This is the V62/V67 risk class -- an in-place immediate inside code that has already flown -- not
the V24/V27/V48B cave-authoring class that bricked the ECU three times.

-------------------------------------------------------------------------------------------------
CRC -- TWO trailers, the same split V104 used.
    0xC4B36, 0xC4B42 (the cave)  ->  main app block [0x13000,0xC4FFC)  ->  trailer 0xC4FFC
    0xC60A8..0xC60B7 (the coeffs) ->  cal block     [0xC6000,0xC6FFC)  ->  trailer 0xC6FFC
Both recomputed via the existing owning_block/walk_all_blocks machinery.  No new CRC path.
=================================================================================================
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
import cmath
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
import build_v67_tva as V67                # noqa: E402  -- Lever B's constants, never re-typed
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V105_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000
FS = 1000.0                              # control-task rate -- `control-task-tick-confirmed-1khz`

BASE_NAME = ("_v104_V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4"
             "_plain_image.bin")
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "b556a0b16da5ac2ad850cae036e5533a4de347e84f2c907f37653cc0f7201a03"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =================================================================================================
# E1 -- THE BIQUAD RETUNE.
#
# 🛑🛑 THE FORMULA IS THE SPECIFICATION.  A ROUNDED DECIMAL IS NOT, AND HEX IN A MESSAGE IS NOT.
# Three different byte strings for `b1` circulated in one session, and the root cause was NOT an
# encoding bug: **a 6-decimal-place decimal does not round-trip a float32.**  `a1` needs 8
# significant digits and `b1` needs 9.  Three agents encoded three DIFFERENT NUMBERS, each
# correctly.  So the coefficients below are DERIVED at double precision and only then packed;
# the expected hex is ASSERTED against, never typed as the source.
# =================================================================================================
BQ_A1, BQ_A2, BQ_B1, BQ_C4 = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
BQ_LO, BQ_HI = BQ_A1, BQ_C4 + 4                       # the contiguous 16-byte coefficient block

# V105 biquad: 25.5 Hz notch, poles at 22.0 Hz, r = 0.950, fs = 1000 Hz
R_POLE, F_POLE, F_ZERO = 0.950, 22.0, 25.5
A1 = -2.0 * R_POLE * math.cos(2.0 * math.pi * F_POLE / 1000.0)   # -1.8818767088236372
A2 = R_POLE * R_POLE                                             #  0.9025
B1 = -2.0 * math.cos(2.0 * math.pi * F_ZERO / 1000.0)            # -1.9743840279896383
C4 = (1.0 + A1 + A2) / (2.0 + B1)                                #  0.8050950074438165
# 🛑 C4 is FORCED by the unity-DC constraint H(0) = c4*(2+b1)/(1+a1+a2) = 1.  It is NOT a free
# choice, and it is NOT a stray edit: it lands 1.5 % from Honda's stock 0.817310, so V105 reads as
# "V104 with Honda's flat gain restored and the filter re-shaped", not as a gain lever.

# (name, address, V104 decimal, V105 double)   -- the V104 column is a PRE-image check only
BQ_SPEC = (("a1", BQ_A1, -1.5372,   A1),
           ("a2", BQ_A2, +0.63462,  A2),
           ("b1", BQ_B1, -1.8808,   B1),
           ("c4", BQ_C4, +1.512023, C4))
SIGFIG_REL = 5e-7                                     # "6 significant figures"
PACK_TOL = 1e-6                                       # float32 must represent the double this well

# 🛑 ASSERTED, NOT TYPED AS THE SOURCE.  If a future edit changes the formula these must move too;
# if they do not, the formula and the intent have silently diverged.
BQ_EXPECT_HEX = {BQ_A1: "56e1f0bf", BQ_A2: "3d0a673f",
                 BQ_B1: "9eb8fcbf", BQ_C4: "b51a4e3f"}
# what a 6-dp restatement of the same numbers would have produced -- the trap, asserted AGAINST
BQ_LOSSY_DECIMALS = {BQ_A1: -1.881877, BQ_A2: +0.902500,
                     BQ_B1: -1.974384, BQ_C4: +0.805095}

BQ_ARM_CAL = 0xC649B                     # V103's arm -- must already be 1 on the base
BQ_STATE_X1, BQ_STATE_X2 = 0x3818, 0x3814
BQ_FUNC_LO, BQ_FUNC_HI = 0x352B4, 0x35B1F
BQ_OUT_CLAMP = 12288                     # +-0x3000, the gp-0x6b86 store clamp
BQ_FLOAT_CLAMP = 12.0                    # the +-12.0f clamp applied BEFORE the *1024

# pre-registered behavioural endpoints -- these are the SPEC, and they are never relaxed to pass
TGT_NOTCH_HZ = F_ZERO                                 # 25.5
TGT_POLE_HZ = F_POLE                                  # 22.0
TGT_FREQ_TOL = 0.01
TGT_DC, TGT_DC_TOL = 1.000, 0.002
TGT_HMAX = 1.0005
TGT_NOTCH_DEPTH = 0.01
TGT_SKIRT_LO_HZ, TGT_SKIRT_LO_MAX = 24.9, 0.10        # expect ~0.062
TGT_SKIRT_HI_HZ, TGT_SKIRT_HI_MAX = 26.8, 0.20        # expect ~0.123
TGT_RATCHET_HZ = 7.79
TGT_RATCHET_LO, TGT_RATCHET_HI = 0.975, 1.000         # expect ~0.986
TGT_POLE_R = 0.97
SWEEP_LO, SWEEP_HI, SWEEP_N = 0.01, 499.9, 200000

# =================================================================================================
# E2 -- the `b6` rung repointed to the governor clip comparator.  TWO halfwords, in-place.
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
CAVE_LEN = 164                           # 🛑 UNCHANGED from V103/V104
HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp

# V104's cave layout, by offset.  PASS1 is the ONLY block V105 touches.
V104_PASS1, V104_PASS2 = (0x00, 0x2E), (0x2E, 0x5C)      # b6, b5      46 B each
V104_PASS3 = (0x5C, 0x8C)                                 # b7+b4+b3   48 B
V104_BYTE7, V104_RET = (0x8C, 0x9E), (0x9E, 0xA4)         # identity 18 B, return 6 B
CARRIED_BLOCKS = (("PASS2 b5", V104_PASS2), ("PASS3 b7+b4+b3", V104_PASS3),
                  ("BYTE7 identity", V104_BYTE7), ("RET", V104_RET))

E2A_ADDR, E2A_OFF = 0xC4B36, 0x02        # disp16 halfword of the FIRST  ld.h  (operand A)
E2B_ADDR, E2B_OFF = 0xC4B42, 0x0E        # disp16 halfword of the SECOND ld.h  (operand B)
E2A_DISP_PRE, E2A_DISP_POST = -0x6ADA, -0x6B94      # r24 lane mirror   -> AGGREGATOR SUM
E2B_DISP_PRE, E2B_DISP_POST = -0x6ADC, -0x4F64      # r26 lane mirror   -> GOVERNOR BOUND
E2_LD_HW1 = bytes.fromhex("2437")        # ld.h ...[gp],r6 -- opcode/base/dest, MUST NOT MOVE
E2A_INSN_ADDR, E2B_INSN_ADDR = 0xC4B34, 0xC4B40
# `ld.h -0x6b94, gp, r6` already exists verbatim here -- the zero-encoding-risk twin
E2A_TWIN = 0x453E0

# everything in PASS1 that must NOT move, by offset within the cave
PASS1_INVARIANTS = (
    (0x04, bytes.fromhex("6032"), "cmp 0x0,r6            (operand A sign test)"),
    (0x06, bytes.fromhex("ae05"), "bge +4                (skip the negate)"),
    (0x08, bytes.fromhex("8031"), "subr r0,r6            (negate => |A|)"),
    (0x0A, bytes.fromhex("0638"), "mov r6,r7             (r7 = |A|)"),
    (0x10, bytes.fromhex("6032"), "cmp 0x0,r6            (operand B sign test)"),
    (0x12, bytes.fromhex("ae05"), "bge +4"),
    (0x14, bytes.fromhex("8031"), "subr r0,r6            (negate => |B|)"),
    (0x16, bytes.fromhex("e639"), "cmp r6,r7             (flags on |A|-|B|)"),
    (0x18, bytes.fromhex("043a"), "mov 0x4,r7"),
    (0x1A, bytes.fromhex("ae05"), "bge +4                (|A|>=|B| keeps the 4)"),
    (0x1C, bytes.fromhex("003a"), "mov 0x0,r7"),
    (0x1E, bytes.fromhex("c43a"), "shl 0x4,r7            (4<<4 = 0x40 = BIT 6)"),
    (0x20, bytes.fromhex("8437edea"), "ld.bu -0x1514,gp,r6   (read byte4)"),
    (0x24, bytes.fromhex("c636bf00"), "🛑 andi 0xbf,r6,r6    THE MASK -- clears bit 6 ONLY"),
    (0x28, bytes.fromhex("0731"), "or r7,r6"),
    (0x2A, bytes.fromhex("4437ecea"), "st.b r6,-0x1514,gp    (write back)"),
)

# CAN 0x14A byte4 ownership.  Honda keeps bits 2:0 -- V105 does not change a single mask.
BIT_OWNERS = {7: "PASS3  LKAS command sign", 6: "PASS1  🆕 |6b94| >= |4f64|  GOVERNOR CLIP DUTY",
              5: "PASS2  |6ae2| >= |6b26|", 4: "PASS3  r24 lane sign",
              3: "PASS3  D_state sign"}
HONDA_BITS_KEPT = {2, 1, 0}          # gp-0x6799, gp-0x679b, gp-0x679a -- ALL PRESERVED

# V103's Part A code edits (the biquad arm) -- carried, asserted untouched
V103_PARTA = ((0x35A06, bytes.fromhex("844ffb97"), "arm source -> gp-0x6806 engagement flag"),
              (0x35A12, bytes.fromhex("e049"), "cmp r0,r9"),
              (0x35A18, bytes.fromhex("ea370000"), "setfne r6"))

# ---- a linear decoder over the cave payload: every byte must land on an instruction boundary ----
INSN_HW1_2B = {
    "003a": "mov 0x0,r7", "013a": "mov 0x1,r7", "023a": "mov 0x2,r7", "033a": "mov 0x3,r7",
    "043a": "mov 0x4,r7", "413a": "add 0x1,r7", "483a": "add 0x8,r7",
    "c43a": "shl 0x4,r7", "c63a": "shl 0x6,r7",
    "0638": "mov r6,r7", "8031": "subr r0,r6", "6032": "cmp 0x0,r6", "e639": "cmp r6,r7",
    "0731": "or r7,r6", "7f00": "jmp [lp]", "ae05": "bge +4",
}
INSN_HW1_4B = {
    "2437": "ld.h  disp[gp],r6", "8437": "ld.bu disp[gp],r6", "a437": "ld.bu disp[gp],r6",
    "4437": "st.b  r6,disp[gp]", "2436": "movea disp,gp,r6", "c636": "andi  imm,r6,r6",
}
ST_B4_INSN = bytes.fromhex("4437ecea")      # st.b r6,-0x1514[gp]
ST_B7_INSN = bytes.fromhex("4437efea")      # st.b r6,-0x1511[gp]


def decode_cave(payload, name):
    """Linear sweep.  Raises if any byte is not covered by a known instruction form."""
    i, out = 0, []
    while i < len(payload):
        hw1 = payload[i:i + 2].hex()
        if hw1 in INSN_HW1_2B:
            out.append((i, 2, INSN_HW1_2B[hw1]))
            i += 2
        elif hw1 in INSN_HW1_4B:
            if i + 4 > len(payload):
                raise SystemExit(f"{name}: truncated 32-bit instruction at +0x{i:02X}")
            out.append((i, 4, INSN_HW1_4B[hw1]))
            i += 4
        else:
            raise SystemExit(f"{name}: UNKNOWN instruction hw1 {hw1} at +0x{i:02X}")
    return out


# 🛑 THE FINAL ARTIFACT HASHES.  Frozen once the build is accepted; a docstring edit must not move
# a byte.  `None` means "not yet frozen" and the build prints a loud notice instead of asserting.
EXPECT_IMG_SHA = "2666a000415a29fef98ac9cd6c183536269c3e61a61fc822c17586f2adde7e00"
EXPECT_RWD_SHA = "5592f7ca52d07247152e5930c579b6ba35e2f5fa5a3adcafcb08b95fff6c89a8"

# ⚠ A FIRST CUT OF V105 EXISTED AT A 26.0 Hz NOTCH and was SUPERSEDED before flight.  Its
# coefficients came from 6-dp decimals (the lossy-spec failure above) and its centre frequency was
# re-optimised to 25.5 Hz.  Its PLAIN IMAGE is retained as the artifact of record with a
# `SUPERSEDED-DO-NOT-FLASH-NOTCH26HZ-` prefix; its **`.rwd` was DELETED** on the operator's ruling
# -- a prefixed near-miss `.rwd` is still a flashable file in a directory of flashable files, and
# the prefix is one careless glob away from being invisible.  ⇒ **exactly ONE V105 `.rwd` exists
# on disk, and it is this one.**  The `.rwd` is reproducible from the retained image, so nothing
# is lost.  SHAs recorded for the audit trail:
#   superseded image 98f94e7e6f7b9b6d3ae20b94aaed947aff9b901128c180afb0a142ec44de52db  (RETAINED)
#   superseded .rwd  4ee8ea111609a6d0c2014cbea3949e2bed5c8975fdf570a709b8012dd5a6a6fb  (DELETED)
TOKEN = "V104BASE-NOTCH25.5HZ.C60A8-C60B4-PROBE.B6.6B94.GE.4F64"
BIN_OUT = str(plain_image_path(f"_v105_{TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V105-{TOKEN}-0x{START:X}-0x{END:X}.rwd")

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  V104's ledger, PLUS the four cells V104 itself wrote -- those are
# now CARRIED state, and the brief names all four explicitly.
# =================================================================================================
FROZEN = {
    0x3AA96: (1, 0xFB, "🛑 LEVER B GATE (V104) -- ld.bu -0x6806[gp],r15. CARRIED, not re-flown"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- V62's fix, half. Carried"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- carried"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried"),
    0x55DF2: (1, 0x7A, "🛑 CAN 427 SOURCE low byte (V104) -- gp-0x6b86, the biquad lane. CARRIED"),
    0x55E10: (1, 0xA4, "🛑 CAN 427 SCALER (V104) -- sar 0x4. CARRIED"),
    0xC407E: (2, 511, "HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC40BC: (2, 300, "Coulomb ramp knee (V99's lever, carried)"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- matches 0xC63AC=102/1024"),
    0xC40D2: (2, 204, "K1 -- HELD AT 204. Instrumented by the cave's b5, NOT dosed. Carried."),
    0xC40D4: (2, 573, "command-branch EMA -- VIRGIN"),
    0xC40D6: (2, 246, "accel/inertia EMA -- VIRGIN"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP"),
    0xC6194: (2, 3, "the REAL LKAS slew limiter -- DEAD (0xC4118 partition)"),
    0xC61B2: (2, 3072, "fwd-path clamp -- tracks the gain, frozen with it"),
    0xC61B4: (2, 3072, "arb output clamp -- tracks the gain, frozen with it"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC6200: (2, 8192, "PID reference clamp -- DEAD (V100 measured 0.000000)"),
    0xC62EA: (2, 0, "steer-to-zero, V53, on the car"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN (the cave's b5 operand B)"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane (the cave's b7 source)"),
    0xC63AC: (2, 102, "accumulator pole -- Honda's own value (V99's revert)"),
    0xC63AE: (2, 1024, "Stage-2 LERP index scale"),
    0xC63D2: (2, 6, "FUN_00036682 pole"),
    0xC640A: (2, 0xE000, "FALLBACK-2 STOCK"),
    0xC640C: (2, 0xF333, "FALLBACK-1 STOCK"),
    0xC6444: (2, 512, "r26's arm -- the DECOUPLER. Deliberately stock: NOT Lever B's arm"),
    0xC6446: (2, 5244, "🛑 LEVER B ARM (V104) -- 5244. CARRIED, not re-flown"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through"),
    0xC6468: (2, 2639, "shared model gain"),
    0xC646C: (2, 891, "shared sensor scale -- Honda's 891 (decoupled by V57)"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
    0xC649B: (1, 1, "🛑 V103's BIQUAD ARM -- must ALREADY be 1, or E1 retunes a DISARMED filter "
                    "and the whole build is inert"),
    0xC64A1: (1, 1, "READ-ONLY"),
    0xC64FA: (1, 5, "🛑 SHARED OSCILLATION-DETECTOR CEIL -- ~18 in-code readers. V103 armed the "
                    "biquad by patching the COMPARISON privately at 0x35A12, NOT by raising this "
                    "widely-shared cell. V105 does not touch it either."),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN"),
    0xC6B12: (2, 98, "PID Ki -- VIRGIN"),
    0xC6B26: (2, 256, "PID Kp -- VIRGIN"),
    0xC6CD0: (2, 5346, "🛑 LKAS GAIN -- 6x, THE OPERATOR'S RULING. DOES NOT MOVE in V105."),
}

# =================================================================================================
# THE FRICTION DOSE FAMILY.  Car is TVCA4: 24/25 = MANUAL, 26/27 = ENGAGED.  Carried from V104.
# =================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
REC_X_OFF, REC_Y_OFF = 0x02, 0x08
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)

# =================================================================================================
# THE EME AUDIT -- every V25 -> V37 EME-prevention fix, re-run against the BUILT image.
# =================================================================================================
EME_RANGES = [
    (0xC64B4, 0xC64BA, "V36/V37", "STEER_STATUS debounce disable + DTC-0x49 (0xC64B8 -> 0xFF)"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals maxed to 0xFFFF"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f (and -1.0f -> -5.0f)"),
    (0xC65C6, 0xC65D0, "V31->V38", "soft-EME boost floor FLOAT 0.0f/1.5f/2.0f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC64DE, 0xC64E0, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384, bank 1"),
    (0xE5180, 0xE5260, "V38", "same taper surface, bank 2"),
]
EME_SCALARS = [
    (0xC64B8, 1, 0xFF, 0x70, "DTC-0x49 counter-B gate -- 112 -> 0xFF, can never increment (V37)"),
    (0xC61C0, 2, 0xFFFF, 1600, "debounce cal 0 (V36)"),
    (0xC61C2, 2, 0xFFFF, 896, "debounce cal 1 (V36)"),
    (0xC61C4, 2, 0xFFFF, 1280, "debounce cal 2 (V36)"),
    (0xC64DE, 1, 27, 17, "re-engage ramp (pre-V38)"),
    (0xC674E, 2, 5120, 1024, "soft-EME boost floor INT -- THE AUTHORITY FLOOR"),
]
EME_FLOATS = [
    (0xC6598, 5.0, 1.0, "soft-EME boost floor FLOAT #1 (V29->V38)"),
    (0xC659C, 5.0, 1.0, "soft-EME boost floor FLOAT #2 (V29->V38)"),
    (0xC65AC, -5.0, -1.0, "soft-EME boost floor FLOAT #3, negative rail (V29->V38)"),
    (0xC65B0, -5.0, -1.0, "soft-EME boost floor FLOAT #4, negative rail (V29->V38)"),
    (0xC65C4, 5.0, 0.0, "soft-EME boost floor FLOAT #5 (V31->V38)"),
    (0xC65C8, 5.0, 1.5, "soft-EME boost floor FLOAT #6 (V31->V38)"),
    (0xC65CC, 5.0, 2.0, "soft-EME boost floor FLOAT #7 (V31->V38)"),
]

# the non-stock ledger vs HONDA STOCK.  V104's, with 0xC60B4 widened to the whole coeff block.
VS_STOCK = [
    (0x13109, 0x1310A, "pre-V38", "part-number '-' -> ','"),
    (0x14120, 0x14121, "pre-V38", "part-number 2nd copy"),
    (0x2A1F0, 0x2A1F2, "V57", "forward-LKAS reader repointed tp+0x746C -> tp+0x7CD0"),
    (0x35A06, 0x35A0A, "V103", "biquad arm source, reversal-counter -> gp-0x6806 engagement flag"),
    (0x35A12, 0x35A14, "V103", "biquad arm: cmp r12,r9 -> cmp r0,r9"),
    (0x35A18, 0x35A1C, "V103", "biquad arm: setfnc -> setfne (unsigned>= -> !=0)"),
    (0x3AA96, 0x3AA97, "V104", "LEVER B gate: ld.bu -0x683c[gp],r15 -> -0x6806[gp],r15"),
    (0x454FE, 0x454FF, "V42", "state-4 governor bne -> br (INERT, carried)"),
    (0x55C0E, 0x55C12, "V53+", "THE CAVE HOOK -- jarl 0xC4B34,lp"),
    (0x55DF2, 0x55DF4, "V104", "CAN 427 source gp-0x6c18 (stock) -> gp-0x6b86 (the biquad lane)"),
    (0x55E10, 0x55E11, "V104", "CAN 427 scaler sar 0x3 (stock) -> sar 0x4"),
    (0xC40BC, 0xC40BE, "V99", "Coulomb ramp knee 600 -> 300"),
    (0xC40D2, 0xC40D3, "V89", "K1 Coulomb gain 102 -> 204 -- HELD, instrumented not dosed"),
    (0xC4B34, 0xC4B34 + CAVE_LEN, "CAVE", "the 164 B code cave -- V104's, with E2's two "
                                          "displacement halfwords repointed"),
    (BQ_LO, BQ_HI, "V105", "E1 THE BIQUAD RETUNED -- a1/a2/b1/c4, 55.23 Hz notch -> 25.50 Hz "
                           "notch, DC held at unity (c4 reverts V104's x1.85)"),
    (0xC61B2, 0xC61B6, "V101", "LKAS forward-path clamps -- FROZEN at the tracking value"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0"),
    (0xC6446, 0xC6448, "V104", "LEVER B arm 512 -> 5244"),
    (0xC649B, 0xC649C, "V103", "arms Honda's dormant biquad, 0 -> 1"),
    (0xC64B4, 0xC64B9, "V36/V37", "STEER_STATUS debounce + DTC-0x49"),
    (0xC64DE, 0xC64DF, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor FLOAT 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC6CD0, 0xC6CD2, "V101", "the PRIVATE forward-LKAS gain -- FROZEN at 6x"),
    (0xD7A5C, 0xD7A62, "V92", "friction dose x1.5 engaged mode 26 -- MEASURED INERT"),
    (0xD7A6C, 0xD7A72, "V92", "friction dose x1.5 engaged mode 27 -- MEASURED INERT"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank"),
]

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def f32(buf, a):
    return struct.unpack_from("<f", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rdw(buf, a, w):
    return u16(buf, a) if w == 2 else (buf[a] if w == 1 else rd(buf, a, w))


def rec_addr(buf, mode):
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


def rec_x(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_X_OFF)


def sigfig6(got, want):
    """True iff `got` reproduces `want` to 6 significant figures."""
    return abs(got - want) / abs(want) < SIGFIG_REL


# =================================================================================================
# THE PLANT, mirrored from the decompiled arithmetic.  float32-read constants, because the firmware
# reads them as float32; the recursion is the one unfolded from FUN_000352b4's sign nest.
# =================================================================================================
def biquad_H(f_hz, a1, a2, b1, c4):
    """H(e^jw) for w[n] = c4*u[n] - a1*w[n-1] - a2*w[n-2] ; y[n] = w[n] + b1*w[n-1] + w[n-2]."""
    z = cmath.exp(-2j * math.pi * f_hz / FS)          # z^-1
    return c4 * (1.0 + b1 * z + z * z) / (1.0 + a1 * z + a2 * z * z)


def disp_of(raw2):
    """Sign-extended 16-bit displacement of a V850 4-byte gp-relative form."""
    return struct.unpack("<h", raw2)[0]


def assert_frozen(buf, label):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


def assert_friction_family(buf, label):
    print(f"\n    friction dose family 0x{FRICTION_PTR_ARRAY:05X} ({label}) -- "
          f"CAR IS TVCA4: 24/25 MANUAL, 26/27 ENGAGED")
    bad = []
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(buf, m)
        want = FRICTION_Y_STOCK if m in MANUAL_MODES else FRICTION_Y_V92
        got = rec_y(buf, m)
        role = "MANUAL " if m in MANUAL_MODES else "ENGAGED"
        if got != want:
            bad.append(m)
        print(f"      {OK if got == want else BAD} mode {m:2d} {role}  record 0x{ra:05X}  "
              f"Y@0x{ra + REC_Y_OFF:05X} = {got}  X = {rec_x(buf, m)}")
    check(not bad, f"{label}: all 4 friction records at their expected Y "
                   f"(manual STOCK, engaged V92 x1.5 -- MEASURED INERT, carried unchanged)")


def eme_audit(img, base, stock, label):
    print(f"\n  ---- EME AUDIT ({label}) ----")
    print(f"    {'range':<21} {'B':>4} {'!=stock':>8}  {'==base':>7}  origin      what")
    allok = True
    for lo, hi, origin, what in EME_RANGES:
        same_as_base = bytes(img[lo:hi]) == bytes(base[lo:hi])
        n_vs_stock = sum(1 for i in range(lo, hi) if img[i] != stock[i])
        allok &= same_as_base and n_vs_stock > 0
        print(f"    {'0x%05X-0x%05X' % (lo, hi - 1):<21} {hi - lo:>4} {n_vs_stock:>8}  "
              f"{'YES' if same_as_base else 'NO!':>7}  {origin:<10}  {what}")
    check(allok, f"{label}: all {len(EME_RANGES)} EME ranges carried "
                 f"(identical to the audited V104 base AND non-stock)")

    print(f"\n    scalar cells:")
    bad = []
    for a, w, want, stk, why in EME_SCALARS:
        got = rdw(img, a, w)
        print(f"      {OK if got == want else BAD} 0x{a:05X}  = {got:<7} (stock {stk:<7})  {why}")
        if got != want:
            bad.append(a)
    check(not bad, f"{label}: all {len(EME_SCALARS)} EME scalar cells at their fixed values")

    print(f"\n    float cells:")
    bad = []
    for a, want, stk, why in EME_FLOATS:
        got = f32(img, a)
        print(f"      {OK if got == want else BAD} 0x{a:05X}  = {got:<7} (stock {stk:<7})  {why}")
        if got != want:
            bad.append(a)
    check(not bad, f"{label}: all {len(EME_FLOATS)} EME float cells at their fixed values")

    floor, clamp = u16(img, 0xC674E), u16(img, 0xC61B2)
    check(floor == 5120 and floor > clamp,
          f"{label}: soft-EME boost floor INT = {floor} > {clamp} (the fwd-path clamp) "
          f"=> authority sufficient")
    check(u16(img, 0xC407E) == 511,
          f"{label}: hard-fault interlock 0xC407E = 511 (Honda's own, one under its 512 trip)")
    check(u16(img, 0xC4080) == 0, f"{label}: 0xC4080 (K0) = 0 -- NEVER-RAISE, untouched")


def build():
    print("=" * 102)
    print("  V105 -- Honda's biquad RETUNED 55.23 Hz -> 25.50 Hz notch, DC held at unity (E1)")
    print("          + the cave's b6 rung repointed to |gp-0x6b94| >= |gp-0x4f64| (E2).")
    print("          Cave LENGTH, MASKS, REGISTERS and RET all UNCHANGED.")
    print("=" * 102)

    # =============================================================================================
    print("\n  [1] THE BASE -- V104 (which FLEW, as route a4; the docs saying otherwise are stale)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V104, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    # =============================================================================================
    print("\n  [2] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    assert_frozen(base, "V104 base")
    assert_friction_family(base, "V104 base")

    # =============================================================================================
    print("\n  [3] E1 -- PRE-IMAGE: the four coefficients, read LE off the V104 base")
    pre_vals, post_bytes, post_vals = {}, {}, {}
    for name, addr, v104_dec, v105_dec in BQ_SPEC:
        got = f32(base, addr)
        pre_vals[name] = got
        check(sigfig6(got, v104_dec),
              f"0x{addr:05X} {name} = {rd(base, addr, 4).hex()} = {got:+.9f}f "
              f"== V104's {v104_dec:+.6f} to 6 s.f. (rel err {abs(got - v104_dec) / abs(v104_dec):.2e})")
    check(base[BQ_ARM_CAL] == 1,
          f"0x{BQ_ARM_CAL:05X} = 1 -- V103's arm is ALREADY SET, so E1 retunes a filter that "
          f"actually runs (a 0 here would make the whole build inert)")
    check(rd(base, BQ_A1, 12) == rd(stock, BQ_A1, 12),
          "a1/a2/b1 are still HONDA STOCK on the base -- V105 is the FIRST build ever to move the "
          "notch's own SHAPE and CENTRE (V104 moved only the scalar c4)")
    check(rd(base, BQ_C4, 4) != rd(stock, BQ_C4, 4),
          f"c4 IS non-stock on the base ({f32(stock, BQ_C4):+.8f}f -> {f32(base, BQ_C4):+.8f}f) "
          f"-- V104's x1.85, which E1 REVERTS as part of the DC re-normalisation")
    for a, want, why in V103_PARTA:
        check(rd(base, a, len(want)) == want, f"V103's arm edit 0x{a:05X} = {want.hex()} -- {why}")

    print("\n  [3b] E1 -- THE BYTES, DERIVED FROM THE FORMULA AT DOUBLE PRECISION")
    print(f"       R_POLE = {R_POLE}   F_POLE = {F_POLE} Hz   F_ZERO = {F_ZERO} Hz   fs = {FS} Hz")
    print("       🛑 no hex and no rounded decimal is the source: the coefficients are COMPUTED,")
    print("          then struct.pack('<f', v); the expected hex is ASSERTED, never typed in.")
    print(f"       {'':4} {'addr':<8} {'derived double (repr)':>24}  {'packed':<10} "
          f"{'float32':>22}")
    for name, addr, v104_dec, v105_dbl in BQ_SPEC:
        pk = struct.pack("<f", v105_dbl)
        rt = struct.unpack("<f", pk)[0]
        post_bytes[name], post_vals[name] = pk, rt
        print(f"       {name:<4} 0x{addr:05X}  {repr(v105_dbl):>24}  {pk.hex():<10} {rt:>22.17g}")
        check(abs(rt - v105_dbl) < PACK_TOL,
              f"  {name}: float32 represents the derived double to < {PACK_TOL:g} "
              f"(err {abs(rt - v105_dbl):.3e})")
        check(len(pk) == 4 and pk.hex() == BQ_EXPECT_HEX[addr],
              f"  {name}: packs to {pk.hex()} == the expected {BQ_EXPECT_HEX[addr]} "
              f"-- formula and intent agree")
    print("\n       🛑 THE LOSSY-DECIMAL TRAP, asserted AGAINST (this is why the formula is the spec):")
    n_lossy = 0
    for name, addr, _, v105_dbl in BQ_SPEC:
        lossy = struct.pack("<f", BQ_LOSSY_DECIMALS[addr])
        same = lossy == post_bytes[name]
        n_lossy += 0 if same else 1
        print(f"       {name:<4} 6-dp restatement {BQ_LOSSY_DECIMALS[addr]:+.6f} -> {lossy.hex()}"
              f"   {'same' if same else '*** DIFFERENT from ' + post_bytes[name].hex() + ' ***'}")
    check(n_lossy == 2,
          f"  exactly {n_lossy} of 4 coefficients (a1, b1) are MISENCODED by a 6-dp decimal "
          f"-- a1 needs 8 significant digits and b1 needs 9. a2/c4 coincide by luck, not design.")
    E1_PRE = rd(base, BQ_LO, BQ_HI - BQ_LO)
    E1_POST = b"".join(post_bytes[n] for n, _, _, _ in BQ_SPEC)
    check(len(E1_POST) == 16 and E1_PRE != E1_POST,
          f"  the coefficient block is 16 contiguous bytes: {E1_PRE.hex()} -> {E1_POST.hex()}")

    # =============================================================================================
    print("\n  [4] E2 -- PRE-IMAGE: the cave and the PASS1 comparator, read off the base")
    V104_CAVE = rd(base, CAVE_BASE, CAVE_LEN)
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp")
    check(all(b == 0xFF for b in base[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"cave tail is virgin 0xFF to 0x{CAVE_FREE_END:05X} "
          f"({CAVE_FREE_END - CAVE_BASE - CAVE_LEN} B free)")
    ret_at = V104_CAVE.rfind(bytes.fromhex("7f00"))
    check(ret_at == CAVE_LEN - 2 and ret_at == V104_RET[1] - 2,
          f"the cave's ONLY exit `jmp [lp]` is at +0x{ret_at:02X}, the last 2 B -- E2 writes at "
          f"+0x{E2A_OFF:02X} and +0x{E2B_OFF:02X}, both far INSIDE PASS1, so control flow is "
          f"structurally untouched")
    for lbl, (lo, hi) in CARRIED_BLOCKS:
        check(len(V104_CAVE[lo:hi]) == hi - lo, f"  {lbl:<16} +0x{lo:02X}..0x{hi - 1:02X} present")

    print("\n  [4b] E2 -- THE TWO EDIT SITES, and every PASS1 byte that must NOT move")
    check(rd(base, E2A_INSN_ADDR, 4) == E2_LD_HW1 + rd(base, E2A_ADDR, 2)
          and disp_of(rd(base, E2A_ADDR, 2)) == E2A_DISP_PRE,
          f"0x{E2A_INSN_ADDR:05X} = {rd(base, E2A_INSN_ADDR, 4).hex()} = "
          f"ld.h -0x{-E2A_DISP_PRE:04X},gp,r6  (operand A, V104's r24 lane mirror)")
    check(rd(base, E2B_INSN_ADDR, 4) == E2_LD_HW1 + rd(base, E2B_ADDR, 2)
          and disp_of(rd(base, E2B_ADDR, 2)) == E2B_DISP_PRE,
          f"0x{E2B_INSN_ADDR:05X} = {rd(base, E2B_INSN_ADDR, 4).hex()} = "
          f"ld.h -0x{-E2B_DISP_PRE:04X},gp,r6  (operand B, V104's r26 lane mirror)")
    check(rd(base, E2A_ADDR, 2) == bytes.fromhex("2695"), "0xC4B36 == 2695 (the brief's PRE)")
    check(rd(base, E2B_ADDR, 2) == bytes.fromhex("2495"), "0xC4B42 == 2495 (the brief's PRE)")
    for off, want, why in PASS1_INVARIANTS:
        check(V104_CAVE[off:off + len(want)] == want,
              f"  PASS1 +0x{off:02X} = {want.hex():<8} {why}")

    print("\n  [4c] E2 -- THE NEW DISPLACEMENTS, DERIVED FROM THE BITS (never copied as hex)")
    E2A_POST = struct.pack("<h", E2A_DISP_POST)
    E2B_POST = struct.pack("<h", E2B_DISP_POST)
    for lbl, raw, want, cell in (("A", E2A_POST, E2A_DISP_POST, "gp-0x6b94  AGGREGATOR SUM"),
                                 ("B", E2B_POST, E2B_DISP_POST, "gp-0x4f64  GOVERNOR BOUND")):
        hw = struct.unpack("<H", raw)[0]
        check(disp_of(raw) == want and (hw & 1) == 0,
              f"  operand {lbl}: {raw.hex()} -> hw2 0x{hw:04X} -> sext16 {disp_of(raw)} "
              f"= -0x{-want:04X}  ({cell}); bit0 = 0, the `ld.h` halfword-aligned form")
    check(E2A_POST == bytes.fromhex("6c94"), "  operand A packs to 6C94 (the brief's POST)")
    check(E2B_POST == bytes.fromhex("9cb0"), "  operand B packs to 9CB0 (the brief's POST)")
    check(rd(base, E2A_TWIN, 4) == E2_LD_HW1 + E2A_POST,
          f"  ⭐ ZERO ENCODING RISK on operand A: the exact 4 bytes "
          f"{(E2_LD_HW1 + E2A_POST).hex()} = ld.h -0x6b94,gp,r6 already exist VERBATIM at "
          f"0x{E2A_TWIN:05X} in this image")
    n_twinB = sum(1 for i in range(START, END - 4)
                  if bytes(base[i:i + 4]) == E2_LD_HW1 + E2B_POST)
    print(f"      operand B's exact 4 bytes {(E2_LD_HW1 + E2B_POST).hex()} appear {n_twinB}x in "
          f"the base image (0 is fine -- the encoding was proven in Ghidra, see the docstring)")

    # =============================================================================================
    code = bytearray(base)
    attributed = set()

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
        print(f"    0x{addr:05X}  {len(post):2d} B   {label}")

    print(f"\n  [5] THE EDITS -- two sites. NO CAVE LENGTH CHANGE, NO NEW CODE.")
    apply(BQ_LO, E1_PRE, E1_POST,
          f"E1   BIQUAD RETUNE  0xC60A8..0xC60B7  a1/a2/b1/c4  55.23 Hz notch -> 25.50 Hz notch")
    apply(E2A_ADDR, bytes.fromhex("2695"), E2A_POST,
          f"E2a  b6 OPERAND A   0xC4B36  ld.h -0x6ada,gp,r6 -> ld.h -0x6b94,gp,r6")
    apply(E2B_ADDR, bytes.fromhex("2495"), E2B_POST,
          f"E2b  b6 OPERAND B   0xC4B42  ld.h -0x6adc,gp,r6 -> ld.h -0x4f64,gp,r6")
    check(len(attributed) == 20,
          f"exactly {len(attributed)} bytes written: 16 (E1, four float32) + 2 (E2a) + 2 (E2b)")

    # =============================================================================================
    print("\n  [6] POST-IMAGE VERIFICATION -- read back out of the image being built")
    for name, addr, _, v105_dbl in BQ_SPEC:
        got = f32(code, addr)
        check(abs(got - v105_dbl) < PACK_TOL and rd(code, addr, 4) == post_bytes[name]
              and rd(code, addr, 4).hex() == BQ_EXPECT_HEX[addr],
              f"E1: 0x{addr:05X} {name} = {rd(code, addr, 4).hex()} = {got:+.10f}f "
              f"== the FORMULA value {v105_dbl!r}")
    check(rd(code, E2A_ADDR, 2) == bytes.fromhex("6c94"), "E2a: 0xC4B36 == 6C94")
    check(rd(code, E2B_ADDR, 2) == bytes.fromhex("9cb0"), "E2b: 0xC4B42 == 9CB0")
    check(rd(code, E2A_INSN_ADDR, 4) == bytes.fromhex("24376c94"),
          "E2a: 0xC4B34 reads 24376c94 = ld.h -0x6b94,gp,r6  (the AGGREGATOR SUM)")
    check(rd(code, E2B_INSN_ADDR, 4) == bytes.fromhex("24379cb0"),
          "E2b: 0xC4B40 reads 24379cb0 = ld.h -0x4f64,gp,r6  (the GOVERNOR BOUND)")

    print("\n  [6b] 🛑 THE CAVE -- LENGTH, MASKS, REGISTERS, RET, and every carried block")
    NEW_CAVE = rd(code, CAVE_BASE, CAVE_LEN)
    check(len(NEW_CAVE) == CAVE_LEN == 164, f"cave length == {CAVE_LEN} -- UNCHANGED")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"the cave tail is still virgin 0xFF to 0x{CAVE_FREE_END:05X} "
          f"({CAVE_FREE_END - CAVE_BASE - CAVE_LEN} B free) -- nothing was appended")
    for lbl, (lo, hi) in CARRIED_BLOCKS:
        check(NEW_CAVE[lo:hi] == V104_CAVE[lo:hi],
              f"  {lbl:<16} +0x{lo:02X}..0x{hi - 1:02X}  BYTE-IDENTICAL to V104")
    p1_diff = [i for i in range(*V104_PASS1) if NEW_CAVE[i] != V104_CAVE[i]]
    check(p1_diff == [E2A_OFF, E2A_OFF + 1, E2B_OFF, E2B_OFF + 1],
          f"  PASS1 b6         +0x00..0x2D  differs from V104 in EXACTLY 4 bytes, "
          f"+{[hex(x) for x in p1_diff]} -- the two `ld.h` displacements and nothing else")
    for off, want, why in PASS1_INVARIANTS:
        check(NEW_CAVE[off:off + len(want)] == want, f"  PASS1 +0x{off:02X} STILL {want.hex()}")
    check(NEW_CAVE[0x24:0x28] == bytes.fromhex("c636bf00"),
          "  🛑 THE MASK `andi 0xbf,r6,r6` IS UNCHANGED -- b6 only; Honda's bits 2:0 preserved")
    check(NEW_CAVE.rfind(bytes.fromhex("7f00")) == CAVE_LEN - 2,
          "  🛑 THE RET `jmp [lp]` is untouched and still the cave's last 2 bytes")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"  the hook 0x{HOOK_ADDR:05X} is unchanged")
    n_b4 = sum(1 for i in range(len(NEW_CAVE) - 3) if NEW_CAVE[i:i + 4] == ST_B4_INSN)
    n_b7 = sum(1 for i in range(len(NEW_CAVE) - 3) if NEW_CAVE[i:i + 4] == ST_B7_INSN)
    check((n_b4, n_b7) == (3, 1),
          f"  stores: {n_b4}x gp-0x1514 + {n_b7}x gp-0x1511 -- V104's set exactly, NO NEW RAM")

    print("\n  [6c] THE CAVE, RE-DECODED LINEARLY -- every byte on an instruction boundary")
    dec_new = decode_cave(NEW_CAVE, "V105 cave")
    dec_old = decode_cave(V104_CAVE, "V104 cave")
    check(len(dec_new) == len(dec_old)
          and [(o, n) for o, n, _ in dec_new] == [(o, n) for o, n, _ in dec_old],
          f"  {len(dec_new)} instructions at the SAME {len(dec_old)} offsets and lengths as V104 "
          f"-- no boundary moved, so no byte can be misinterpreted as a different opcode")
    check(sum(n for _, n, _ in dec_new) == CAVE_LEN,
          f"  the decode covers all {CAVE_LEN} bytes with no gap and no overrun")
    print("      PASS1, decoded from the BUILT image:")
    for off, n, mnem in dec_new:
        if off >= V104_PASS1[1]:
            break
        raw = NEW_CAVE[off:off + n]
        extra = ""
        if raw[:2] == E2_LD_HW1:
            extra = f"   <- disp {disp_of(raw[2:4])} = -0x{-disp_of(raw[2:4]):04X}"
        mark = "  **" if off in (E2A_OFF - 2, E2B_OFF - 2) else "    "
        print(f"      {mark} +0x{off:02X}  0x{CAVE_BASE + off:05X}  {raw.hex():<8}  {mnem}{extra}")

    print("\n  [6d] THE CARRIED LEVERS the brief names explicitly -- read from the built image")
    for a, w, want, lbl in ((0x3AA96, 1, 0xFB, "LEVER B gate  ld.bu -0x6806[gp],r15"),
                            (0xC6446, 2, 5244, "LEVER B arm"),
                            (0x55DF2, 1, 0x7A, "CAN 427 source low byte (gp-0x6b86)"),
                            (0x55E10, 1, 0xA4, "CAN 427 scaler  sar 0x4"),
                            (0xC6CD0, 2, 5346, "LKAS GAIN 6x -- the operator's ruling"),
                            (0xC649B, 1, 1, "the BIQUAD ARM")):
        got = rdw(code, a, w)
        check(got == want, f"  0x{a:05X} = {got} (0x{got:X}) == {want} -- {lbl}")

    print("\n  [6e] CAN 0x14A byte4 -- NO MASK CHANGED, so ownership is exactly V104's")
    cleared = set()
    for m, bits, lbl in ((0x00BF, {6}, "PASS1 b6"), (0x00DF, {5}, "PASS2 b5"),
                         (0x0067, {7, 4, 3}, "PASS3 b7+b4+b3")):
        got = {b for b in range(8) if not (m >> b) & 1}
        check(got == bits and (m & 0x07) == 0x07,
              f"  {lbl:<16} andi 0x{m:02X} clears {sorted(bits, reverse=True)} and PRESERVES "
              f"Honda's bits 2:0")
        cleared |= bits
    check(cleared == set(BIT_OWNERS) == {7, 6, 5, 4, 3},
          f"the cave owns exactly bits {sorted(cleared, reverse=True)} -- unchanged from V104")
    check(set(range(8)) - cleared == HONDA_BITS_KEPT,
          f"  Honda keeps bits {sorted(HONDA_BITS_KEPT, reverse=True)} -- gp-0x6799, gp-0x679b, "
          f"gp-0x679a, all written in FUN_00055a98 BEFORE the hook")
    for b in sorted(BIT_OWNERS, reverse=True):
        print(f"      bit {b}  {BIT_OWNERS[b]}")

    # =============================================================================================
    print("\n  [7] 🛑 BEHAVIOURAL -- H(z) evaluated FROM THE BUILT IMAGE'S OWN BYTES")
    a1, a2, b1, c4 = (f32(code, BQ_A1), f32(code, BQ_A2), f32(code, BQ_B1), f32(code, BQ_C4))
    print(f"      a1 = {a1:+.9f}   a2 = {a2:+.9f}   b1 = {b1:+.9f}   c4 = {c4:+.9f}")

    # zeros of z^2 + b1 z + 1 ; poles of z^2 + a1 z + a2
    zr = abs(complex(-b1 / 2, math.sqrt(max(0.0, 1.0 - (b1 / 2) ** 2))))
    f_zero = math.acos(max(-1.0, min(1.0, -b1 / 2))) * FS / (2 * math.pi)
    pole_r = math.sqrt(a2)
    f_pole = math.acos(max(-1.0, min(1.0, -a1 / (2 * pole_r)))) * FS / (2 * math.pi)
    tau_ms = -1000.0 / (FS * math.log(pole_r))
    ring99_ms = 1000.0 * math.log(0.01) / math.log(pole_r) / FS
    print(f"      zeros |z| = {zr:.9f}  ->  f_notch = {f_zero:.4f} Hz")
    print(f"      poles |p| = {pole_r:.9f}  ->  f_pole  = {f_pole:.4f} Hz")
    print(f"      tau = {tau_ms:.3f} ms      99% ring-down = {ring99_ms:.3f} ms")

    step = (SWEEP_HI - SWEEP_LO) / (SWEEP_N - 1)
    mags = [abs(biquad_H(SWEEP_LO + k * step, a1, a2, b1, c4)) for k in range(SWEEP_N)]
    kmax = max(range(SWEEP_N), key=lambda k: mags[k])
    kmin = min(range(SWEEP_N), key=lambda k: mags[k])
    h_dc = abs(biquad_H(0.0, a1, a2, b1, c4))
    h_notch = abs(biquad_H(TGT_NOTCH_HZ, a1, a2, b1, c4))
    h_ratchet = abs(biquad_H(TGT_RATCHET_HZ, a1, a2, b1, c4))

    h_skirt_lo = abs(biquad_H(TGT_SKIRT_LO_HZ, a1, a2, b1, c4))
    h_skirt_hi = abs(biquad_H(TGT_SKIRT_HI_HZ, a1, a2, b1, c4))

    check(abs(zr - 1.0) < 1e-5,
          f"  zeros lie ON the unit circle (|z| = {zr:.9f}) => the notch is a TRUE null, "
          f"infinitely deep in exact arithmetic")
    check(abs(f_zero - TGT_NOTCH_HZ) <= TGT_FREQ_TOL,
          f"  ENDPOINT 1/9: notch CENTRE {f_zero:.6f} Hz == {TGT_NOTCH_HZ} +/- {TGT_FREQ_TOL} "
          f"(V104's was 55.2254 Hz)")
    check(abs(f_pole - TGT_POLE_HZ) <= TGT_FREQ_TOL,
          f"  ENDPOINT 2/9: POLE frequency {f_pole:.6f} Hz == {TGT_POLE_HZ} +/- {TGT_FREQ_TOL} "
          f"(V104's was 42.3451 Hz)")
    check(abs(h_dc - TGT_DC) <= TGT_DC_TOL,
          f"  ENDPOINT 3/9: |H(0)| = {h_dc:.9f}, within {TGT_DC:.3f} +/- {TGT_DC_TOL} "
          f"=> NO WEIGHT CHANGE the operator can feel")
    check(mags[kmax] <= TGT_HMAX,
          f"  ENDPOINT 4/9: max|H| over {SWEEP_LO}-{SWEEP_HI} Hz = {mags[kmax]:.9f} "
          f"(at {SWEEP_LO + kmax * step:.4f} Hz) <= {TGT_HMAX} => the section NEVER boosts, "
          f"anywhere; it can only REMOVE loop gain  [GATE 2, magnitude]")
    check(h_notch < TGT_NOTCH_DEPTH,
          f"  ENDPOINT 5/9: |H({TGT_NOTCH_HZ} Hz)| = {h_notch:.6e} < {TGT_NOTCH_DEPTH} "
          f"=> the null is real ({20 * math.log10(max(h_notch, 1e-30)):+.2f} dB)")
    check(h_skirt_lo < TGT_SKIRT_LO_MAX,
          f"  ENDPOINT 6/9: |H({TGT_SKIRT_LO_HZ} Hz)| = {h_skirt_lo:.9f} < {TGT_SKIRT_LO_MAX} "
          f"=> the LOWER skirt is deep enough to bite below the null")
    check(h_skirt_hi < TGT_SKIRT_HI_MAX,
          f"  ENDPOINT 7/9: |H({TGT_SKIRT_HI_HZ} Hz)| = {h_skirt_hi:.9f} < {TGT_SKIRT_HI_MAX} "
          f"=> the UPPER skirt is deep enough to bite above the null")
    check(TGT_RATCHET_LO <= h_ratchet <= TGT_RATCHET_HI,
          f"  ENDPOINT 8/9: |H({TGT_RATCHET_HZ} Hz)| = {h_ratchet:.9f} in "
          f"[{TGT_RATCHET_LO}, {TGT_RATCHET_HI}] => the ratchet line is left essentially alone")
    check(pole_r < TGT_POLE_R,
          f"  ENDPOINT 9/9: pole radius {pole_r:.9f} < {TGT_POLE_R} => STABLE, and the ring is "
          f"short: tau {tau_ms:.2f} ms, 99% settled in {ring99_ms:.2f} ms")
    print(f"      min|H| over the sweep = {mags[kmin]:.6e} at {SWEEP_LO + kmin * step:.4f} Hz")

    print(f"\n      the delivered surface -- |H| and PHASE, from the built bytes:")
    print(f"        {'f (Hz)':>9}  {'|H| V105':>10}  {'dB':>9}  {'phase':>9}   {'|H| V104':>9}")
    v104_c = (pre_vals["a1"], pre_vals["a2"], pre_vals["b1"], pre_vals["c4"])
    for f in (0.5, 1, 3, 6, 7.79, 9, 12, 15, 18, 20, 21.73, 23, 24, 24.9, 25.5, 26.8, 28, 30, 35,
              40, 55.23, 80, 150, 300, 499):
        h = biquad_H(f, a1, a2, b1, c4)
        ho = abs(biquad_H(f, *v104_c))
        print(f"        {f:>9.2f}  {abs(h):>10.6f}  {20 * math.log10(max(abs(h), 1e-30)):>+9.2f}  "
              f"{math.degrees(cmath.phase(h)):>+9.2f}   {ho:>9.6f}")

    print(f"\n      ⚠ GATE 2 -- PHASE IS A STATED RESIDUAL, NOT AN ASSERTED PASS.")
    print(f"        |H| <= 1 everywhere is UNCONDITIONAL and is asserted above. A notch also adds")
    print(f"        LAG below its centre: at {TGT_RATCHET_HZ} Hz this section contributes "
          f"{math.degrees(cmath.phase(biquad_H(TGT_RATCHET_HZ, a1, a2, b1, c4))):+.2f} deg")
    print(f"        with |H| = {h_ratchet:.4f}. The 6-9 Hz lane already measures Re(Z) < 0 on three")
    print(f"        drives. That term is NOT covered by the magnitude argument. BELIEF: it is small")
    print(f"        against the measured gap. This build does not close it.")

    # =============================================================================================
    print("\n  [8] FROZEN + the friction dose family, AFTER the edit")
    assert_frozen(code, "built image (pre-CRC)")
    assert_friction_family(code, "built image (pre-CRC)")
    check(rd(code, BQ_LO, 16) != rd(stock, BQ_LO, 16)
          and rd(code, 0x35A06, 4) == V103_PARTA[0][1],
          "the coefficient block is non-stock and V103's arm edits are intact")
    check(all(not (a <= x < a + 4) for a in (0x35A2C, 0x35A4C, 0x35A64, 0x35A6A)
              for x in attributed),
          f"the four gp-0x{BQ_STATE_X1:04X}/gp-0x{BQ_STATE_X2:04X} biquad-state load/store "
          f"instructions are untouched -- E1 changes COEFFICIENTS, never the state access")
    check(BQ_FUNC_LO <= 0x35A06 < BQ_FUNC_HI,
          f"V103's arm edits remain inside FUN_000352b4 [0x{BQ_FUNC_LO:05X},0x{BQ_FUNC_HI:05X})")

    print("\n  [8b] Everything outside the two edit sites is bit-for-bit V104's")
    diffs = [i for i in range(START, END) if code[i] != base[i] and i not in attributed]
    check(not diffs, f"ZERO bytes differ from the V104 base outside the named edits "
                     f"-- the control law is otherwise UNCHANGED from the flown V104")

    # =============================================================================================
    eme_audit(code, base, stock, "built image, pre-CRC")

    # =============================================================================================
    print("\n  [9] CRC RECOMPUTATION -- reusing the existing owning_block/walk_all_blocks machinery")
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    check(len(blocks) == 2,
          f"the edits span exactly {len(blocks)} CRC blocks (expected 2: the main app block "
          f"0xC4FFC for E2, and the cal block 0xC6FFC for E1) -- {[hex(b[1]) for b in blocks]}")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit on trailer 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        n_in = len([a for a in touched if blk[0] <= a < blk[1]])
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old_crc:08X} -> 0x{new_crc:08X}  "
              f"{n_in} of {len(touched)} edited bytes  (trailer 0x{blk[1]:06X})")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    # =============================================================================================
    print("\n  [10] FULL BYTE DIFF vs HONDA STOCK")
    sruns = [i for i in range(START, END) if code[i] != stock[i]]
    scrc = {b + k for b in (0xC4FFC, 0xC5FFC, 0xC6FFC, 0xCCFFC) for k in range(4)}
    scrc |= {b + 0xFFC + k for b in range(0xCD000, 0x100000, 0x1000) for k in range(4)}
    sattr = set()
    for lo, hi, bld, what in VS_STOCK:
        sattr |= {i for i in sruns if lo <= i < hi}
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"       {len(sruns)} bytes differ from STOCK total, {len(sattr)} attributed, "
          f"{len(set(sruns) & scrc)} CRC")
    check(not sun, "ZERO unattributed bytes vs stock"
                   + ("" if not sun else "  -- " + str([hex(x) for x in sun[:16]])))

    print("\n  [10b] 🛑 FULL BYTE DIFF vs THE V104 BASE -- every changed run, named")
    bruns = [i for i in range(START, END) if code[i] != base[i]]
    runs = []
    for i in bruns:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    named = [(BQ_A1, 4, f"E1 a1  pole angle  42.35 -> {TGT_POLE_HZ:.2f} Hz"),
             (BQ_A2, 4, f"E1 a2  pole radius 0.7966 -> {R_POLE:.4f}"),
             (BQ_B1, 4, f"E1 b1  NOTCH CENTRE 55.23 -> {TGT_NOTCH_HZ:.2f} Hz"),
             (BQ_C4, 4, f"E1 c4  input gain 1.5120 -> {C4:.4f} (DC forced to 1; stock is 0.8173)"),
             (E2A_ADDR, 2, "E2a b6 operand A -> gp-0x6b94 (aggregator sum)"),
             (E2B_ADDR, 2, "E2b b6 operand B -> gp-0x4f64 (governor bound)")]
    unnamed = []
    print(f"       {'range':<20} {'B':>4}   {'V104':<10} -> {'V105':<10}  what")
    for lo, hi in runs:
        span = set(range(lo, hi))
        if (lo & 0xFFF) >= 0xFFC:
            tag = "CRC trailer"
        else:
            hits = [w for a, n, w in named if span & set(range(a, a + n))]
            tag = " + ".join(hits) if hits else "?? UNATTRIBUTED"
            if not hits or not span <= attributed:
                unnamed.append((lo, hi))
        print(f"       0x{lo:05X}..0x{hi - 1:05X}  {hi - lo:>4}   {bytes(base[lo:hi]).hex():<10} -> "
              f"{bytes(code[lo:hi]).hex():<10}  {tag}")
    check(not unnamed,
          f"every one of the {len(runs)} changed runs vs V104 lies inside a named edit or a "
          f"CRC trailer"
          + ("" if not unnamed else f"  -- STRAY: {[(hex(a), hex(b)) for a, b in unnamed]}"))
    n_payload = len([i for i in bruns if (i & 0xFFF) < 0xFFC])
    check(set(i for i in bruns if (i & 0xFFF) < 0xFFC) <= attributed,
          f"all {n_payload} changed payload bytes are inside the {len(attributed)} bytes this "
          f"script wrote (the other {len(attributed) - n_payload} written bytes happened to keep "
          f"their V104 value -- float32 sign/exponent bytes that coincide)")

    # =============================================================================================
    print("\n  [11] .rwd ENCODE + READBACK (pipeline check -- WRITE_MODE gates whether files land)")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V105 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if EXPECT_IMG_SHA is None or EXPECT_RWD_SHA is None:
        print(f"    [....] SHAs NOT YET FROZEN -- image {img_sha}")
        print(f"    [....]                        .rwd  {rwd_sha}")
    else:
        check(img_sha == EXPECT_IMG_SHA,
              f"image SHA256 == the FROZEN value {EXPECT_IMG_SHA[:20]}... -- a docstring edit "
              f"must not move a byte")
        check(rwd_sha == EXPECT_RWD_SHA,
              f".rwd  SHA256 == the FROZEN value {EXPECT_RWD_SHA[:20]}...")

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V105_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"a DIFFERENT {OUT} already exists.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            # =====================================================================================
            # EVERYTHING BELOW READS THE SHIPPED FILE BACK OFF DISK.  No script claims.
            # =====================================================================================
            print("\n  [12] FROM-DISK VERIFICATION -- the shipped .rwd, decoded")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha, "shipped .rwd sha256 OK")
            FF.assert_x31_checksum(shipped, "V105 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "shipped .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped CRC 50/50")
            disk_img = bytearray(Path(BIN_OUT).read_bytes())
            check(hashlib.sha256(bytes(disk_img)).hexdigest() == img_sha,
                  "plain image re-read from disk, sha256 OK")
            check(bytes(disk_img) == bytes(sd), "plain image on disk == decoded shipped .rwd")
            for name, addr, _, v105_dbl in BQ_SPEC:
                check(abs(f32(disk_img, addr) - v105_dbl) < PACK_TOL
                      and rd(disk_img, addr, 4).hex() == BQ_EXPECT_HEX[addr],
                      f"shipped: 0x{addr:05X} {name} = {rd(disk_img, addr, 4).hex()} = "
                      f"{f32(disk_img, addr):+.10f}f == the FORMULA value, from disk")
            check(rd(disk_img, E2A_INSN_ADDR, 4) == bytes.fromhex("24376c94")
                  and rd(disk_img, E2B_INSN_ADDR, 4) == bytes.fromhex("24379cb0"),
                  "shipped: both b6 operands repointed, re-read from disk")
            check(rd(disk_img, CAVE_BASE + V104_PASS2[0], CAVE_LEN - V104_PASS2[0])
                  == V104_CAVE[V104_PASS2[0]:],
                  f"shipped: PASS2/PASS3/BYTE7/RET byte-identical to V104, from disk")
            check(len(rd(disk_img, CAVE_BASE, CAVE_LEN)) == CAVE_LEN
                  and all(b == 0xFF for b in disk_img[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
                  f"shipped: cave still {CAVE_LEN} B with a virgin 0xFF tail, from disk")
            check(disk_img[BQ_ARM_CAL] == 1 and disk_img[0xC64FA] == 5,
                  "shipped: biquad arm still 1, 0xC64FA still 5")
            a1d, a2d = f32(disk_img, BQ_A1), f32(disk_img, BQ_A2)
            b1d, c4d = f32(disk_img, BQ_B1), f32(disk_img, BQ_C4)
            fz_d = math.acos(max(-1.0, min(1.0, -b1d / 2))) * FS / (2 * math.pi)
            pr_d = math.sqrt(a2d)
            fp_d = math.acos(max(-1.0, min(1.0, -a1d / (2 * pr_d)))) * FS / (2 * math.pi)
            hd = max(abs(biquad_H(SWEEP_LO + k * step, a1d, a2d, b1d, c4d))
                     for k in range(SWEEP_N))
            check(abs(fz_d - TGT_NOTCH_HZ) <= TGT_FREQ_TOL
                  and abs(fp_d - TGT_POLE_HZ) <= TGT_FREQ_TOL and hd <= TGT_HMAX,
                  f"shipped: notch {fz_d:.6f} Hz, pole {fp_d:.6f} Hz, max|H| = {hd:.9f} "
                  f"<= {TGT_HMAX}, ALL recomputed from the ON-DISK bytes")
            check(abs(biquad_H(TGT_NOTCH_HZ, a1d, a2d, b1d, c4d)) < TGT_NOTCH_DEPTH
                  and abs(biquad_H(TGT_SKIRT_LO_HZ, a1d, a2d, b1d, c4d)) < TGT_SKIRT_LO_MAX
                  and abs(biquad_H(TGT_SKIRT_HI_HZ, a1d, a2d, b1d, c4d)) < TGT_SKIRT_HI_MAX
                  and TGT_RATCHET_LO <= abs(biquad_H(TGT_RATCHET_HZ, a1d, a2d, b1d, c4d))
                  <= TGT_RATCHET_HI,
                  f"shipped: null/skirts/ratchet all in spec from the ON-DISK bytes")
            assert_frozen(disk_img, "SHIPPED image")
            assert_friction_family(disk_img, "SHIPPED image")
            eme_audit(disk_img, base, stock, "SHIPPED image, from disk")

    print("\n" + "=" * 102)
    print(f"  V105 [{TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  E1  0xC60A8..0xC60B7 -- HONDA'S BIQUAD RETUNED. a1/a2/b1 move the notch's own SHAPE")
    print(f"      and CENTRE for the FIRST time in the whole arc: {f_zero:.2f} Hz null (was 55.23),")
    print(f"      pole {f_pole:.2f} Hz at r = {pole_r:.4f}. c4 {pre_vals['c4']:.6f} -> {c4:.6f}")
    print(f"      REVERTS V104's x1.85 -- it is the DC normaliser, |H(0)| = {h_dc:.6f}.")
    print(f"      max|H| = {mags[kmax]:.6f} <= 1 EVERYWHERE => can only REMOVE loop gain.")
    print(f"      |H(21.73)| = {abs(biquad_H(21.73, a1, a2, b1, c4)):.4f}, "
          f"|H(7.79)| = {h_ratchet:.4f}, |H(26.0)| = {h_notch:.2e}.")
    print(f"  E2  0xC4B36 / 0xC4B42 -- the cave's b6 rung repointed IN PLACE:")
    print(f"      b6 = ( |gp-0x6b94| >= |gp-0x4f64| ) -- aggregator sum vs governor bound.")
    print(f"      A COMPARATOR: immune to under- and over-range by construction. ITS DUTY IS THE")
    print(f"      ANSWER. Cave {CAVE_LEN} B UNCHANGED, masks unchanged, r6/r7 only, RET untouched;")
    print(f"      PASS1 differs from V104 in EXACTLY 4 bytes and no instruction boundary moved.")
    print(f"  CARRIED: Lever B (0x3AA96=fb, 0xC6446=5244), 427 tap (0x55DF2=7a, 0x55E10=a4),")
    print(f"      0xC6CD0=5346 (6x gain), 0xC649B=1 (the arm). All re-read from the built image.")
    print(f"  CRC: two trailers, 0xC4FFC (E2, the cave) and 0xC6FFC (E1, the coefficients).")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
