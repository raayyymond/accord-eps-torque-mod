#!/usr/bin/env python3
r"""=================================================================================================
V102 -- THE GAIN DOSE.  8× -> 6×, ONE CELL, FULLY INSTRUMENTED.  Comparator cave + 427 repoint.
=================================================================================================

BASE: **V101** (`_v101_V99BASE-GAIN8X.C6CD0.7128-NOLEVERB-CAVE.LKASSAT.SIGNS-427.6B94_plain_image.bin`)
      sha256 c8cb5c3a2d0ce1853660414159723b314f194e6cae4a197b71814f1fcf50a6c7 -- **ON THE CAR**,
      flown as route 0x95, identity duty 1.000000 over 25,551 frames, fault-free.

    FOUR EDITS.  **EXACTLY ONE INDEPENDENT CALIBRATION VARIABLE: THE LKAS GAIN.**
    1.  0xC6CD0   7128 -> 5346    THE LKAS GAIN, 8× -> **6×** Honda's 891   ⬅ THE OPERATOR'S RULING
    2.  0xC61B2   4096 -> 3072    forward-path clamp, TRACKING the gain (not independent)
    3.  0xC61B4   4096 -> 3072    arb output clamp,   TRACKING the gain (not independent)
    4.  cave payload 114 -> 154 B  +  0x55DF2 CAN 427 source gp-0x6b94 -> gp-0x6b4c (`sar 6` KEPT)

🛑 **THE 6× IS THE OPERATOR'S OWN DECISION**, taken against a trade table put to him directly.  It
is not an inference by this script or by any agent.  He is giving up torque he explicitly asked for,
in exchange for the predicted 22-26 Hz reduction below.  **Do not "improve" the dose.**

    ⚙ `ACCORD_V102_GAIN` selects the dose.  **The DEFAULT IS THE SHIPPED 6× (5346)**, so a bare
      re-run of this script reproduces the flown artifact bit-for-bit.  `=8x` restores V101's value
      (and then this build has zero calibration edits); `=4x` gives the pre-V101 3564.

    **NOTHING ELSE IN THE CONTROL LAW MOVES.**  Every other calibration cell is asserted FROZEN at
    the value that is on the car right now -- both halves of Lever B, K1, and the whole
    `0xCBE74` friction family.

-------------------------------------------------------------------------------------------------
🛑 WHY THIS BUILD CARRIES NO LEVER -- THE MEASUREMENT THAT KILLED THE ONE IT WAS GOING TO CARRY
-------------------------------------------------------------------------------------------------
V102 was specified as **Lever B restored** (`0x3AA96` 0xC5->0xFB, `0xC6446` 512->5244) to kill the
23 Hz line V101 introduced.  **That content was withdrawn before the cut, on measurement.**

The 2×2 was re-run in **SHAPE units** (band ÷ a 32–38 Hz control band) against a **measured shape
floor** taken from the V89-vs-V89 placebo pair, and the `0xCBE74` confound `k` was measured directly
from the single-variable pair V90 (r77) vs V91 (r78).  The shape statistic is ~2× more sensitive
than raw band power, and the raw numbers had been contaminated by drive-to-drive level (V91's whole
spectrum sits 0.75× below V90's).

**At 22–26 Hz, de-confounded, floor 1.45× (EVIDENCE):**

| | value | verdict |
|---|---|---|
| **the 8× gain** | **G = 2.7–3.9×** | **REAL** -- clears the floor by 1.9–2.7× |
| **Lever B** | **B = 0.84–1.30×** | **INSIDE THE FLOOR. NOT A RESULT.** On `tq` and `rate_c` it points *below* 1 |

⇒ **RESTORING LEVER B WOULD NOT TOUCH THE 23 Hz LINE.**  The conclusion is insensitive to `k`
across its whole CI.

🛑 **AND IT IS WORSE THAN NEUTRAL -- REMOVING LEVER B WAS A MEASURED WIN.**  The same 2×2 at
**6–9 Hz**, the operator's micro-ratchet band, floor 1.35×, `k` ≈ 1 so no correction needed:

    tq  0.31 [0.19, 0.49]  ·  rate_c  0.31 [0.25, 0.46]  ·  cs_ang  0.35 [0.26, 0.64]

**V101's removal of Lever B cut the micro-ratchet band to roughly ONE THIRD**, on all three
channels, all far outside the floor.  ⚠ Creep-only (5–15 km/h, thin V100 arm) -- EVIDENCE at creep,
unproven above it.

⇒ **Restoring Lever B would UNDO a measured 3× win at 6–9 Hz and buy nothing at 23 Hz.
   V102 does not do that.  `0x3AA96` and `0xC6446` are FROZEN at Honda's values.**

**Two more cells were retired on the same evidence, and both are frozen here:**
- **`0xCBE74` ×1.5: measured INERT** at 22–26 Hz (`k` = 0.86–0.90 against a 1.45× floor) **and** at
  6–9 Hz.  The earlier T10-invalid null is now replaced by a direct in-band measurement.
- **`0xC40D2` 102->204 (K1): measured NULL** at both bands with real exposure (V88 r73 vs V89
  r75+r76; 8 cells, 163/270 windows, `imu_vert` control flat).  🛑 This null is **not** T10-invalid,
  because it is scored on the shape statistic against a measured floor.
  It also failed its own power test: P(separate) 48–62 % at every exposure from 15 s to 60 s, 10–90
  spread still 2.48–16.9 at 60 s -- **the sentence a null would license is: none.**
  ⇒ **K1 ships HELD AT 204 AND INSTRUMENTED BY THE NEW b5 COMPARATOR, NOT DOSED.**
  🛑 *This is deliberate.  No future session should read the 204 as an oversight.*

-------------------------------------------------------------------------------------------------
WHAT V102 IS, THEN -- A DOSE OF THE ONE TERM MEASURED TO CARRY THE LINE
-------------------------------------------------------------------------------------------------
Every other candidate in this band is now **measured null**: Lever B, K1, `0xCBE74`.  The **gain is
the only term that cleared the floor** (G = 2.7-3.9× against 1.45×).  So V102 doses the gain and
instruments everything else.

**The operator's V101 report is what this build answers:** a vibration/grinding at all speeds, only
while LKAS commands, killed by applying driver torque, returning and growing when he lets go.

🛑 **AND THE MECHANISM IS NOT THE OBVIOUS ONE.  "MORE GAIN = MORE EXCITATION" IS REFUTED.**
Within either route, the 22-26 Hz band **does not scale with command amplitude**: slope
**+0.01 [-0.36, +0.31]** on V101 across a **>10× command range**.  ⇒ **the gain acts on the LOOP,
not on the drive.**  Lowering it is a *loop-gain* change, which is why it can move a pole and why a
pure excitation argument would have predicted the wrong thing.

⭐ **WHY COMPARATORS AND NOT THRESHOLDS.**  Neither `gp-0x6ada`/`gp-0x6adc` nor
`gp-0x6ae2`/`gp-0x6b26` has a measured distribution.  A threshold rung against an unmeasured
quantity is this kit's single most reliable source of uninterpretable nulls (V64, V68, V92, V96,
V97).  A comparator is **immune to UNDER-RANGED and OVER-RANGED by construction**: no LSB, no
ceiling, no assumed distribution.  It compares at full precision *inside* the cave, before
quantisation exists, and **its duty is the answer.**

-------------------------------------------------------------------------------------------------
THE CAVE -- 154 B of a 1,212 B extent.  TWO COMPARATORS, TWO SIGNS.
-------------------------------------------------------------------------------------------------
| bit | measurand | form | bytes |
|-----|-----------|------|-------|
| `byte7[7:6]` | **IDENTITY = 3** | constant block | 18 |
| **b3** | **IDENTITY = 0** -- forced by PASS 1's `andi 0xb7` mask | *no instruction* | **0** |
| **b6** | **`\|gp-0x6ada\| >= \|gp-0x6adc\|`** -- r24 arm vs r26 arm, per frame | **COMPARATOR** | 46 |
| **b5** | **`\|gp-0x6ae2\| >= \|gp-0x6b26\|`** -- modelled Coulomb friction (K1's output ×1024) vs the inertia term | **COMPARATOR** | 46 |
| **b7** | `gp-0x6b4c < 0` -- LKAS command sign | sign | (PASS 3) |
| **b4** | `gp-0x6ada < 0` -- r24 lane sign | sign | (PASS 3) |

    PASS 1   46 B   b6 COMPARATOR                       andi 0xb7   (also forces b3 = 0)
    PASS 2   46 B   b5 COMPARATOR                       andi 0xdf
    PASS 3   38 B   b7 + b4 SIGNS                       andi 0x6f
    BYTE7    18 B   byte7[7:6] = 3                      andi 0x3f
    RET       6 B
    TOTAL   154 B   =  12.7 % of the 1,212 B extent.  7.9× margin.

🛑 **PASS ORDER IS LOAD-BEARING.**  The cave is straight-line, so **a live bit in the LAST pass
proves every earlier pass ran.**  Deleting V101's b3-as-constant-1 removes its "PASS 2 executed"
witness; putting both COMPARATORS FIRST and the SIGN pass LAST restores it **at zero cost** -- b7
and b4 are signs of live signals and flip constantly.  ⊕ The byte-7 identity block runs after
PASS 3, so `byte7[7:6] == 3` is a **second, independent** end-of-cave witness.

**Liveness rule, PRE-REGISTERED (the V64/V68 distinction, made checkable):**
> a comparator bit reading constant with 0 flips **while the LAST pass's sign bits are flipping** is
> a **REAL ANSWER** ("A always dominates").  Constant with 0 flips **while the last pass is also
> dead** is **VOID.**

**GATE 1 -- no new RAM claim.**  `gp-0x6ada`/`gp-0x6adc` are the r24/r26 aggregator lane mirrors,
**written-but-never-read**, so reading them is zero-blast-radius.  Every new access is an `ld.h`
(a load has no side effect).  Registers written: **{r6, r7}** only, as V101.  Stores go to the
**same two cells** `{gp-0x1514, gp-0x1511}`.
⚠ **Precise wording, because "no new stores" would be wrong:** V101 wrote `gp-0x1514` **twice**;
V102 writes it **three times** (one read-modify-write per pass).  **Same RAM owned, same registers,
one extra RMW inside our own byte.**

**GATE 2 -- vacuous for the cave.**  Straight-line leaf: no loop, no call, no divide, no float.
**58 instructions** (V101: 42) at 100 Hz inside Honda's own `di`/`ei` critical section ⇒ well under
1 µs, ~0.006 % duty.  DTC 0x18 is **BOOT-ONLY**, so caves carry no timing deadline.
**For the control law GATE 2 is trivially satisfied: no calibration cell moves at all.**

-------------------------------------------------------------------------------------------------
THE 427 LANE -- repoint to gp-0x6b4c, **KEEP `sar 6`**
-------------------------------------------------------------------------------------------------
    CAN 427 (0x1AB) MOTOR_TORQUE, ~49.8 Hz:   clamp(|src| * 5 >> 6, 0, 0x3FF)

🛑 **427 MUST NOT BE USED TO READ THE 23 Hz SPECTRUM.**  It samples at ~49.8 Hz (Nyquist 24.9 Hz)
and the mode sits at **23.4 Hz -- 1.5 Hz under Nyquist.**  Anything that moves the mode above
24.9 Hz **aliases and INVERTS** the readout.  The bus channels (`0x18F` `tq`/`rate_f` at 100.74 Hz)
already carry that spectrum at full fidelity, and cave bits must **complete** the bus picture, not
duplicate it.

**427's job here is the `gp-0x6b4c` MAGNITUDE DISTRIBUTION**, paired with b7's sign.

**GATE 3 sizing, computed not guessed:** against the forward-path clamp,
`clamp * 5 >> 6` of 1023 -- printed by the build.  At the current 4096 that is **320 of 1023 = 31 %
of the field, and it cannot clip below |x| = 13,094.**  `sar 6` is kept deliberately: **under-range
is recoverable, censoring is not** (V96 lost a whole channel to a 34× over-range guess).  `sar 5`
would give 640/1023, but only if ±4096 is a true bound -- and this session's own finding is that
those clamps are **structurally unreachable**, so the real bound is unknown.  **Keeping `sar 6` also
changes ZERO bytes at `0x55E10`.**

-------------------------------------------------------------------------------------------------
🛑 THE IDENTITY -- a 3-bit field.  V102 is code 6.
-------------------------------------------------------------------------------------------------
    ID3  =  (0x14A byte7[7:6] << 1)  |  (0x14A byte4 bit3)

    V99 = 4 (2,0) · V100 = 5 (2,1) · **V101 = 7 (3,1)** · **V102 = 6 (3,0)**

`0x14A` byte 7 is FULLY ALLOCATED and cannot widen: bits 7:6 ours, bits 5:4 Honda's redundancy-voted
counter (`0x55C02 andi 0xcf,r8,r8`), bits 3:0 Honda's checksum nibble (`0x55C2A andi 0xf0,r6,r6`) --
those two are `gp-0x1511`'s ONLY writers, verified two ways in the V92 work.

**Why (3,0) is unreachable on V101 -- EVIDENCE, by construction, not by a measured duty:** V101's b3
is `483a` = `add 0x8,r7` at cave **+0x4A**, **unconditional, with no branch above it**, read out of
the flown V101 image.  V102 has no `add 0x8,r7` anywhere before its byte-4 masks, and PASS 1's
`andi 0xb7` clears bit 3.  ⇒ **b3 ≡ 0.  A single frame with `byte7[7:6]==3 AND b3==0` proves V102.**

🛑 **WARNING TO DECODER AUTHORS -- DO NOT PULL THE BUILD FOR THIS:**
> **V102 ⇒ `byte4[7:3]` is EVEN on 100 % of frames.  V101 was always ODD.  THAT IS THE IDENTITY,
> NOT A DEFECT.**  (Same phenomenon `STATE.md:266` already flagged for V99.)

🛑 **GENERATION-3 IDENTITY SPACE IS EXHAUSTED AFTER V102.**  (3,0) and (3,1) are both burned, as
(2,0)/(2,1) already are.  **V103 must sacrifice a byte4 DATA rung to identity, or hook a second CAN
ID.**  Recorded as a decision, so V103 does not discover it.

-------------------------------------------------------------------------------------------------
⚙ THE DOSE -- `ACCORD_V102_GAIN`.  DEFAULT = THE SHIPPED 6×.
-------------------------------------------------------------------------------------------------
`0xC6CD0` is the private forward-LKAS gain (V57 decoupled it from the shared sensor scale
`0xC646C`, which stays at Honda's 891).  It is the **only independent calibration variable** in this
build, and it is **the torque the operator asked for.**

    ACCORD_V102_GAIN unset / =6x  ->  5346  ( 6× )   ⬅ **THE SHIPPED DOSE.  DEFAULT.**
    ACCORD_V102_GAIN=8x           ->  7128  ( 8× )   V101's value => zero calibration edits
    ACCORD_V102_GAIN=4x           ->  3564  ( 4× )   the pre-V101 value

The two forward-path clamps track it exactly, as they have on every gain step since V14 -- they are
**not** independent variables:

    CLAMP = GAIN * 512 // 891   stock 891->512 · 4× 3564->2048 · 6× 5346->3072 · 8× 7128->4096
    ratio 0.5746 at every step, asserted EXACT (no rounding is permitted)

🛑 **A STRUCTURAL CAP THE OPERATOR SHOULD KNOW ABOUT: THIS GAIN CANNOT REACH 10×.**  The soft-EME
boost floor `0xC674E` = 5120 must stay strictly **ABOVE** the tracking clamp -- that is the
authority gate.  At 10× the clamp would be exactly 5120 and the gate fails.  **The build refuses to
cut**, verified: `ACCORD_V102_GAIN=10x` aborts on that assertion.  ⇒ **the reachable window is
Honda's 1× up to just under 10×**, and 8× (V101) was already close to the top of it.

-------------------------------------------------------------------------------------------------
🛑 THE PRE-REGISTERED READOUT -- RE-ISSUED FOR A GAIN DOSE.  Verbatim, before the drive.
-------------------------------------------------------------------------------------------------
⚠ The readout issued with the *earlier* V102 spec scored **Lever B**, and Lever B does not fly.
**That decision rule is VOID and is not used.**  What follows replaces it.

**PRIMARY ENDPOINT: within-route shape ratio, `tq` band-RMS(21.5–25.5 Hz) ÷ band-RMS(2.5–4.5 Hz),
median over 1 s engaged windows.**  No cross-route normalisation, no matched speed, no matched
driver behaviour.

    BASELINES:   V101 (8×) = 5.07      V100 (4×) = 0.62

**PREDICTION AT 6×: the 22–26 Hz band falls to 0.61× [0.57–0.66] of V101's**, from a fitted exponent
**p = 1.74 [1.43, 1.96]** anchored on the measured V101/V100 step of **3.34× [2.69–3.89]** against a
**1.45× placebo floor**.

    DECISION RULE
      falls to ~0.6× of V101 or lower  =>  THE GAIN CARRIES THE LINE and the dose-response holds.
                                           V103 then picks a further step from a THREE-point curve.
      stays at ~1.0× of V101           =>  THE GAIN IS NOT THE CARRIER.  The 2×2 attribution is
                                           wrong and this session's conclusion is REFUTED.
                                           **That is a real, licensed answer.**
      overshoots well below 0.6×       =>  the exponent is STEEPER than 1.74, and less gain
                                           reduction buys the same result -- worth knowing before
                                           he gives up any more torque.

🛑 **THE HONEST CAVEAT, AND IT IS NOT SMALL: `p` RESTS ON TWO POINTS.  There is no third rung.**
It is an **empirical exponent, not a physical law**, and V102 is the rung that tests it.

**SECONDARY, DIAGNOSTIC ONLY, NEVER DISQUALIFYING:**
- **peak frequency** -- V101 sits at 23.0–23.4 Hz; if the gain moved the pole, 6× should walk it
  back toward ~21 Hz.
- **`d(b6)`** -- r24-vs-r26 dominance.  **`d(b5)`** -- friction-vs-inertia, **which is precisely what
  makes a V103 dose of K1 scoreable.**
- the **`gp-0x6b4c` distribution** from CAN 427 + b7's sign.

⚠ **Q / −3 dB WIDTH IS NOT AN ENDPOINT AND MUST NOT CARRY A CONCLUSION.**  Two analysts disagree on
its **SIGN** for the very same transition -- one measures Q **31.4 → 47.4**, the other **34.5 →
23.6** -- at a resolution where **three bins decide it.**  Report it if you like; never conclude
from it.

**PROTECTED METRIC, to be re-measured post-flight:** wheel-angle rate under a hard command,
hands-light.  Predicted **0.78× [0.74–0.81] of V101, still 1.43× [1.35–1.53] of V100.**

-------------------------------------------------------------------------------------------------
🛑 A VERIFIER TRAP FOUND WHILE BUILDING THIS -- it belongs in every build script in this kit
-------------------------------------------------------------------------------------------------
The byte-diff-vs-base check used to attribute each changed run by the run's **FIRST ADDRESS**.
That silently mislabels any **single-high-byte** calibration edit:

    0xC61B2:  4096 -> 3072  is  `00 10` -> `00 0C` little-endian
              => ONLY the HIGH byte moves => the changed run starts at 0xC61B3, not 0xC61B2
              => a start-address lookup finds nothing and reports "?? UNATTRIBUTED"

**The bytes were correct; the CHECK was wrong.  The failure mode is a FALSE ALARM ON A CORRECT
BUILD -- which is exactly how a good build gets pulled.**  It had been passing only by alignment
luck (the cave and the 427 halfword happen to start on their named addresses).
✅ **FIX, applied here: attribute by INTERSECTION with the byte set the script actually wrote**, never
by the start address.

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
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V102_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = "_v101_V99BASE-GAIN8X.C6CD0.7128-NOLEVERB-CAVE.LKASSAT.SIGNS-427.6B94_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "c8cb5c3a2d0ce1853660414159723b314f194e6cae4a197b71814f1fcf50a6c7"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =================================================================================================
# ⚙ THE DOSE.  🛑 THE DEFAULT IS THE SHIPPED 6× -- THE OPERATOR'S OWN RULING, taken against a trade
#    table put to him directly.  The default is the shipped value so that a BARE re-run of this
#    script reproduces the flown artifact bit-for-bit.  Do not change it.
# =================================================================================================
GAIN_ADDR, GAIN_STOCK, GAIN_V101 = 0xC6CD0, 891, 7128
GAIN_DEFAULT = 5346                             # 6× -- THE OPERATOR'S RULING, 2026-08-20
CLAMP_B2_ADDR, CLAMP_B4_ADDR = 0xC61B2, 0xC61B4
CLAMP_STOCK, CLAMP_V101 = 512, 4096
CLAMP_RATIO = CLAMP_STOCK / GAIN_STOCK          # 0.5746 -- constant across every gain step since V14

_g = os.environ.get("ACCORD_V102_GAIN", "").strip().lower()
if not _g:
    GAIN_VALUE = GAIN_DEFAULT
elif _g.endswith("x"):
    GAIN_VALUE = int(round(float(_g[:-1]) * GAIN_STOCK))
else:
    GAIN_VALUE = int(_g, 0)
CLAMP_VALUE = GAIN_VALUE * CLAMP_STOCK // GAIN_STOCK
GAIN_MOVES = GAIN_VALUE != GAIN_V101            # i.e. does the gain differ from the V101 BASE

# =================================================================================================
# THE CAVE -- source cells
# =================================================================================================
SRC_R24 = 0x6ADA         # gp-0x6ada  r24 aggregator lane mirror.  b6 operand A, b4 sign.
SRC_R26 = 0x6ADC         # gp-0x6adc  r26 aggregator lane mirror.  b6 operand B.
SRC_FRIC = 0x6AE2        # gp-0x6ae2  modelled Coulomb friction x1024 (K1's output).  b5 operand A.
SRC_INER = 0x6B26        # gp-0x6b26  the INERTIA term.  b5 operand B.
SRC_CMD = 0x6B4C         # gp-0x6b4c  LKAS command (the 8× gained lane).  b7 sign + CAN 427.
DST_B4 = 0x1514          # gp-0x1514  CAN 0x14A byte 4
DST_B7 = 0x1511          # gp-0x1511  CAN 0x14A byte 7

IDENTITY_GEN, IDENTITY_B3 = 3, 0
IDENTITY_ID3 = (IDENTITY_GEN << 1) | IDENTITY_B3        # == 6

MASK_PASS1 = 0x00B7      # writes bit 6, CLEARS bit 3 (the identity)  -> keeps 7,5,4 + Honda 2:0
MASK_PASS2 = 0x00DF      # writes bit 5                               -> keeps 7,6,4,3 + Honda 2:0
MASK_PASS3 = 0x006F      # writes bits 7 and 4                        -> keeps 6,5,3 + Honda 2:0
MASK_B7 = 0x003F         # byte7 writes bits 7:6                      -> preserves Honda 5:0

CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V101_CAVE_LEN, CAVE_LEN = 114, 154

PAYLOAD = bytes.fromhex(
    # =============================================================================================
    # PASS 1 -- b6 COMPARATOR:  |gp-0x6ada| >= |gp-0x6adc|   (r24 arm vs r26 arm)
    #           andi 0xb7 also CLEARS bit 3  =>  b3 == 0 == THE V102 IDENTITY.
    # =============================================================================================
    "24372695"      # +0x00  ld.h  -0x6ada[gp],r6    A = r24 lane mirror
    "6032" "ae05"   # +0x04  cmp 0x0,r6 / bge +4 -> +0x0A
    "8031"          # +0x08  subr  r0,r6            r6 = |A|
    "0638"          # +0x0A  mov   r6,r7            r7 = |A|
    "24372495"      # +0x0C  ld.h  -0x6adc[gp],r6   B = r26 lane mirror
    "6032" "ae05"   # +0x10  cmp 0x0,r6 / bge +4 -> +0x16
    "8031"          # +0x14  subr  r0,r6            r6 = |B|
    "e639"          # +0x16  cmp   r6,r7           flags = |A| - |B|  (cmp reg1,reg2 => reg2-reg1)
    "043a"          # +0x18  mov   0x4,r7          ASSUME SET (pre-shift bit2 -> b6)
    "ae05"          # +0x1A  bge   +4 -> +0x1E     cond 0xE = signed GE, taken iff |A| >= |B|
    "003a"          # +0x1C  mov   0x0,r7          else CLEAR
    "c43a"          # +0x1E  shl   0x4,r7          -> byte4 bit 6
    "8437edea"      # +0x20  ld.bu -0x1514[gp],r6
    "c636" "b700"   # +0x24  andi  0xb7,r6,r6      clear bits 6 and 3
    "0731"          # +0x28  or    r7,r6
    "4437ecea"      # +0x2A  st.b  r6,-0x1514[gp]  CAN 0x14A byte 4, pass 1
    # =============================================================================================
    # PASS 2 -- b5 COMPARATOR:  |gp-0x6ae2| >= |gp-0x6b26|   (modelled friction vs inertia)
    # =============================================================================================
    "24371e95"      # +0x2E  ld.h  -0x6ae2[gp],r6   A = modelled Coulomb friction x1024 (K1 output)
    "6032" "ae05"   # +0x32  cmp 0x0,r6 / bge +4 -> +0x38
    "8031"          # +0x36  subr  r0,r6            r6 = |A|
    "0638"          # +0x38  mov   r6,r7            r7 = |A|
    "2437da94"      # +0x3A  ld.h  -0x6b26[gp],r6   B = the INERTIA term
    "6032" "ae05"   # +0x3E  cmp 0x0,r6 / bge +4 -> +0x44
    "8031"          # +0x42  subr  r0,r6            r6 = |B|
    "e639"          # +0x44  cmp   r6,r7           flags = |A| - |B|
    "023a"          # +0x46  mov   0x2,r7          ASSUME SET (pre-shift bit1 -> b5)
    "ae05"          # +0x48  bge   +4 -> +0x4C     taken iff |A| >= |B|
    "003a"          # +0x4A  mov   0x0,r7          else CLEAR
    "c43a"          # +0x4C  shl   0x4,r7          -> byte4 bit 5
    "8437edea"      # +0x4E  ld.bu -0x1514[gp],r6
    "c636" "df00"   # +0x52  andi  0xdf,r6,r6      clear bit 5 only
    "0731"          # +0x56  or    r7,r6
    "4437ecea"      # +0x58  st.b  r6,-0x1514[gp]  CAN 0x14A byte 4, pass 2
    # =============================================================================================
    # PASS 3 -- THE SIGNS, LAST.  b7 = gp-0x6b4c < 0, b4 = gp-0x6ada < 0.
    #           🛑 THE LIVENESS WITNESS: it runs last, so a flipping bit here proves both
    #              comparator passes executed.
    # =============================================================================================
    "003a"          # +0x5C  mov   0x0,r7          init accumulator
    "2437b494"      # +0x5E  ld.h  -0x6b4c[gp],r6   LKAS command
    "6032" "ae05"   # +0x62  cmp 0x0,r6 / bge +4 -> +0x68
    "483a"          # +0x66  add   0x8,r7          b7 = (gp-0x6b4c < 0), pre-shift bit3
    "24372695"      # +0x68  ld.h  -0x6ada[gp],r6   r24 lane mirror
    "6032" "ae05"   # +0x6C  cmp 0x0,r6 / bge +4 -> +0x72
    "413a"          # +0x70  add   0x1,r7          b4 = (gp-0x6ada < 0), pre-shift bit0
    "c43a"          # +0x72  shl   0x4,r7          -> byte4 bits {7,4}
    "8437edea"      # +0x74  ld.bu -0x1514[gp],r6
    "c636" "6f00"   # +0x78  andi  0x6f,r6,r6      clear bits 7 and 4
    "0731"          # +0x7C  or    r7,r6
    "4437ecea"      # +0x7E  st.b  r6,-0x1514[gp]  CAN 0x14A byte 4, pass 3
    # =============================================================================================
    # byte 7 -- THE GENERATION.  byte7[7:6] = 3.  Byte-identical to V101.
    # =============================================================================================
    "033a"          # +0x82  mov   0x3,r7          byte7[7:6] == 3
    "c63a"          # +0x84  shl   0x6,r7          -> 0xC0
    "a437efea"      # +0x86  ld.bu -0x1511[gp],r6
    "c636" "3f00"   # +0x8A  andi  0x3f,r6,r6      keep Honda's bits 5:0
    "0731"          # +0x8E  or    r7,r6
    "4437efea"      # +0x90  st.b  r6,-0x1511[gp]  CAN 0x14A byte 7
    # =============================================================================================
    # return.  Byte-identical to V101.
    # =============================================================================================
    "2436e8ea"      # +0x94  movea -0x1518,gp,r6   restore the hooked instruction
    "7f00")         # +0x98  jmp   [lp]

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp

# ---- THE 427 REPOINT ---------------------------------------------------------------------------
R427_ADDR = 0x55DF2                      # hw2 of the ld.h inside the 0x1AB builder
R427_FROM, R427_TO = 0x6B94, SRC_CMD     # gp-0x6b94 -> gp-0x6b4c
R427_INSN_ADDR, R427_HW1 = 0x55DF0, bytes.fromhex("2437")
R427_SAR_ADDR, R427_SAR = 0x55E10, bytes.fromhex("a632")     # sar 0x6,r6 -- CARRIED, not edited
R427_MUL, R427_SHIFT, R427_FIELD_MAX = 5, 6, 0x3FF           # clamp(|src| * 5 >> 6, 0, 0x3FF)

_gtok = ("NOCALEDIT" if not GAIN_MOVES
         else f"GAIN{GAIN_VALUE // GAIN_STOCK}X.C6CD0.{GAIN_VALUE}")
VARIANT_TOKEN = f"V101BASE-{_gtok}-CAVE.CMP.6ADA.6AE2-SIGNS-427.6B4C-ID.ID3.6"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v102_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V102-{TAG}-0x{START:X}-0x{END:X}.rwd")

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  With the toggle OFF this is EVERY calibration cell in the ledger.
# =================================================================================================
FROZEN = {
    0x3AA96: (1, 0xC5, "🛑 LEVER B GATE -- HONDA STOCK / DEAD. Restoring it is MEASURED to buy "
                       "nothing at 22-26 Hz (B = 0.84-1.30x, floor 1.45x) and to UNDO a measured "
                       "3x win at 6-9 Hz (0.31 [0.19,0.49]). DO NOT RESTORE."),
    0xC6446: (2, 512, "🛑 LEVER B ARM -- HONDA STOCK. Same evidence as the gate. DO NOT RESTORE."),
    0xC407E: (2, 511, "HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC40BC: (2, 300, "Coulomb ramp knee (V99's lever, ON THE CAR since route 0x82)"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- matches 0xC63AC=102/1024"),
    0xC40D2: (2, 204, "🛑 K1 -- HELD AT 204 DELIBERATELY. INSTRUMENTED BY b5, NOT DOSED. Measured "
                      "NULL at 22-26 AND 6-9 Hz (V88 r73 vs V89 r75+r76, shape stat vs a measured "
                      "floor), and its own endpoint failed the power test at every exposure."),
    0xC40D4: (2, 573, "command-branch EMA -- VIRGIN"),
    0xC40D6: (2, 246, "accel/inertia EMA -- VIRGIN"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP"),
    0xC63AC: (2, 102, "accumulator pole -- Honda's own value (V99's revert)"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN (b5's operand B)"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane (b7 / 427 source)"),
    0xC63AE: (2, 1024, "Stage-2 LERP index scale"),
    0xC6200: (2, 8192, "PID reference clamp -- DEAD (V100 measured 0.000000)"),
    0xC6444: (2, 512, "r24 lane companion cal -- VIRGIN, and NOT Lever B's arm"),
    0xC6468: (2, 2639, "shared model gain"),
    0xC646C: (2, 891, "shared sensor scale -- Honda's 891 (decoupled by V57)"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
    0xC649B: (1, 0, "byte cal -- asserted zero"),
    0xC62EA: (2, 0, "steer-to-zero, V53, on the car"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through"),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN"),
    0xC6B12: (2, 98, "PID Ki -- VIRGIN"),
    0xC6B26: (2, 256, "PID Kp -- VIRGIN"),
    0xC6194: (2, 3, "the REAL LKAS slew limiter -- DEAD (0xC4118 partition)"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- V62's fix, half. Carried"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- carried"),
    0xC64A1: (1, 1, "READ-ONLY"),
    0xC63D2: (2, 6, "FUN_00036682 pole"),
    0xC640A: (2, 0xE000, "FALLBACK-2 STOCK"),
    0xC640C: (2, 0xF333, "FALLBACK-1 STOCK"),
}
if not GAIN_MOVES:      # the toggle is OFF => the gain cells are FROZEN too
    FROZEN[GAIN_ADDR] = (2, GAIN_V101, "the PRIVATE forward-LKAS gain -- V101's 8×, NOT MOVED")
    FROZEN[CLAMP_B2_ADDR] = (2, CLAMP_V101, "LKAS fwd-path clamp -- V101's, NOT MOVED")
    FROZEN[CLAMP_B4_ADDR] = (2, CLAMP_V101, "arb output clamp -- V101's, NOT MOVED")

# =================================================================================================
# THE FRICTION DOSE FAMILY.  🛑 THE CAR IS TVCA4: 24/25 = MANUAL, 26/27 = ENGAGED.
# "An address is not a mode" cost this kit ~5 days on V73 => DEREFERENCE THE POINTER, print the mode.
# ⚠ The spec's "records at 0xD6A6C / 0xD7A5C / 0xD7A6C" are the Y ARRAYS (record + 8), not the
#   record starts.  Both are printed below so the distinction cannot be lost again.
# =================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
REC_X_OFF, REC_Y_OFF = 0x02, 0x08
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)   # x1.5, carried V96 onward incl. V101. MEASURED INERT.

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

# the non-stock ledger.  🛑 0x3AA96 and 0xC6446 are NOT here -- they are at Honda's values.
VS_STOCK = [
    (0x13109, 0x1310A, "pre-V38", "part-number '-' -> ','"),
    (0x14120, 0x14121, "pre-V38", "part-number 2nd copy"),
    (0x2A1F0, 0x2A1F2, "V57", "forward-LKAS reader repointed tp+0x746C -> tp+0x7CD0"),
    (0x454FE, 0x454FF, "V42", "state-4 governor bne -> br (INERT, carried)"),
    (0x55C0E, 0x55C12, "V53+", "THE CAVE HOOK -- jarl 0xC4B34,lp"),
    (0x55DF2, 0x55DF4, "V102", "CAN 427 source gp-0x6c18 (stock) -> gp-0x6b4c"),
    (0x55E10, 0x55E11, "V96", "CAN 427 scaler sar 0x3 -> sar 0x6"),
    (0xC40BC, 0xC40BE, "V99", "Coulomb ramp knee 600 -> 300"),
    (0xC40D2, 0xC40D3, "V89", "K1 Coulomb gain 102 -> 204 -- HELD, instrumented not dosed"),
    (0xC4B34, 0xC4B34 + CAVE_LEN, "CAVE", "the code cave -- V102's 154 B"),
    (0xC61B2, 0xC61B6, "V101", "LKAS forward-path clamps 512 -> the tracking value"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0"),
    (0xC64B4, 0xC64B9, "V36/V37", "STEER_STATUS debounce + DTC-0x49"),
    (0xC64DE, 0xC64DF, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor FLOAT 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC6CD0, 0xC6CD2, "V101", "the PRIVATE forward-LKAS gain"),
    (0xD7A5C, 0xD7A62, "V92", "friction dose x1.5 engaged mode 26 -- MEASURED INERT"),
    (0xD7A6C, 0xD7A72, "V92", "friction dose x1.5 engaged mode 27 -- MEASURED INERT"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank"),
]

# -------------------------------------------------------------------------------------------------
# A LINEAR DECODER for exactly the instruction forms this cave contains.  Every mnemonic below was
# decoded field-by-field from its halfword AND confirmed by Ghidra on Honda's own analysed code.
# -------------------------------------------------------------------------------------------------
INSN_HW1_2B = {
    "003a": "mov 0x0,r7", "023a": "mov 0x2,r7", "043a": "mov 0x4,r7", "033a": "mov 0x3,r7",
    "413a": "add 0x1,r7", "423a": "add 0x2,r7", "483a": "add 0x8,r7",
    "c43a": "shl 0x4,r7", "c63a": "shl 0x6,r7",
    "0638": "mov r6,r7", "8031": "subr r0,r6", "6032": "cmp 0x0,r6", "e639": "cmp r6,r7",
    "0731": "or r7,r6", "7f00": "jmp [lp]", "ae05": "bge +4",
}
INSN_HW1_4B = {
    "2437": "ld.h  disp[gp],r6", "8437": "ld.bu disp[gp],r6", "a437": "ld.bu disp[gp],r6",
    "4437": "st.b  r6,disp[gp]", "2436": "movea disp,gp,r6", "c636": "andi  imm,r6,r6",
    "2036": "movea imm,r0,r6",          # V101 only -- kept so V101's cave still decodes
}
BRANCH_MNEM, BRANCH_SPAN = "bge +4", 4
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


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


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
    """🛑 DEREFERENCE THE POINTER AND PRINT THE MODE NUMBER.  An address is not a mode."""
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
    """Two independent legs per range: byte-identical to the AUDITED V101 base (nothing disturbed)
       AND differing from STOCK (the fix is actually present)."""
    print(f"\n  ---- EME AUDIT ({label}) ----")
    print(f"    {'range':<21} {'B':>4} {'!=stock':>8}  {'==V101':>7}  origin      what")
    allok = True
    for lo, hi, origin, what in EME_RANGES:
        same_as_base = bytes(img[lo:hi]) == bytes(base[lo:hi])
        n_vs_stock = sum(1 for i in range(lo, hi) if img[i] != stock[i])
        allok &= same_as_base and n_vs_stock > 0
        print(f"    {'0x%05X-0x%05X' % (lo, hi - 1):<21} {hi - lo:>4} {n_vs_stock:>8}  "
              f"{'YES' if same_as_base else 'NO!':>7}  {origin:<10}  {what}")
    check(allok, f"{label}: all {len(EME_RANGES)} EME ranges carried "
                 f"(identical to the audited V101 base AND non-stock)")

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

    floor, clamp = u16(img, 0xC674E), u16(img, CLAMP_B2_ADDR)
    check(floor == 5120 and floor > clamp,
          f"{label}: soft-EME boost floor INT = {floor} > {clamp} (the fwd-path clamp) "
          f"=> authority sufficient  [this gate caps the gain below 10×]")
    check(u16(img, 0xC407E) == 511,
          f"{label}: hard-fault interlock 0xC407E = 511 (Honda's own, one under its 512 trip)")
    check(u16(img, 0xC4080) == 0, f"{label}: 0xC4080 (K0) = 0 -- NEVER-RAISE, untouched")


def build():
    print("=" * 102)
    if GAIN_MOVES:
        print(f"  V102 -- THE GAIN DOSE.  0xC6CD0 {GAIN_V101} -> {GAIN_VALUE} "
              f"({GAIN_V101 // GAIN_STOCK}× -> {GAIN_VALUE / GAIN_STOCK:.3g}×), "
              f"clamps {CLAMP_V101} -> {CLAMP_VALUE} (tracking).")
        print("           Comparator cave + 427 repoint.  🛑 THE DOSE IS THE OPERATOR'S RULING.")
    else:
        print("  V102 -- INSTRUMENT-ONLY.  ZERO CALIBRATION EDITS.  Two comparators, two signs.")
    print("=" * 102)

    # ==============================================================================================
    print("\n  [1] THE BASE -- V101, ON THE CAR (route 0x95)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V101, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    # ==============================================================================================
    print("\n  [2] THE CONTROL LAW -- what this build does NOT touch")
    check(not GAIN_MOVES or GAIN_VALUE % GAIN_STOCK == 0,
          f"gain {GAIN_VALUE} is an exact multiple of Honda's {GAIN_STOCK} "
          f"({GAIN_VALUE / GAIN_STOCK:.3g}×) so the clamp ratio is exact")
    check(GAIN_VALUE * CLAMP_STOCK % GAIN_STOCK == 0
          and abs(CLAMP_VALUE / GAIN_VALUE - CLAMP_RATIO) < 1e-9,
          f"clamp = {GAIN_VALUE}*{CLAMP_STOCK}//{GAIN_STOCK} = {CLAMP_VALUE}, "
          f"ratio {CLAMP_VALUE / GAIN_VALUE:.6f} == {CLAMP_RATIO:.6f} EXACTLY (no rounding)")
    if not GAIN_MOVES:
        check(True, "⚙ ACCORD_V102_GAIN is UNSET => the gain toggle is OFF => "
                    "**ZERO CALIBRATION EDITS IN THIS BUILD**")
    print("\n       the three cells this build was ORIGINALLY specified to move, and did not:")
    for a, w, lbl in ((0x3AA96, 1, "LEVER B GATE -- measured null at 22-26 Hz, and its removal "
                                   "was a measured 3x WIN at 6-9 Hz"),
                      (0xC6446, 2, "LEVER B ARM  -- same evidence"),
                      (0xC40D2, 2, "K1           -- measured null at both bands; instrumented "
                                   "by the new b5 comparator instead")):
        print(f"         0x{a:05X}  base {rdw(base, a, w):>5}  stock {rdw(stock, a, w):>5}   {lbl}")

    print("\n  [3] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    assert_frozen(base, "V101 base")
    assert_friction_family(base, "V101 base")

    # ==============================================================================================
    print("\n  [4] THE CAVE REGION AND ITS HOOK")
    V101_CAVE = rd(base, CAVE_BASE, V101_CAVE_LEN)
    CAVE_PRE = rd(base, CAVE_BASE, CAVE_LEN)
    check(all(b == 0xFF for b in base[CAVE_BASE + V101_CAVE_LEN:CAVE_FREE_END]),
          f"V101's cave is {V101_CAVE_LEN} B, tail virgin 0xFF to 0x{CAVE_FREE_END:05X}")
    check(CAVE_PRE == V101_CAVE + b"\xff" * (CAVE_LEN - V101_CAVE_LEN),
          f"the {CAVE_LEN} B we overwrite = V101's {V101_CAVE_LEN} B + "
          f"{CAVE_LEN - V101_CAVE_LEN} B of virgin 0xFF")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} unchanged")
    check(len(PAYLOAD) == CAVE_LEN and CAVE_BASE + CAVE_LEN <= CAVE_FREE_END,
          f"payload is {len(PAYLOAD)} B, ends 0x{CAVE_BASE + CAVE_LEN:05X} <= "
          f"0x{CAVE_FREE_END:05X}  ({100 * CAVE_LEN / (CAVE_FREE_END - CAVE_BASE):.1f}% of extent, "
          f"{(CAVE_FREE_END - CAVE_BASE) / CAVE_LEN:.1f}× margin)")

    print("\n  [4b] LINEAR DECODE -- every byte on an instruction boundary, every branch resolved")
    dec_ins = decode_cave(PAYLOAD, "V102")
    bounds = {o for o, _, _ in dec_ins}
    branches = [(o, o + BRANCH_SPAN) for o, _, m in dec_ins if m == BRANCH_MNEM]
    check(sum(ln for _, ln, _ in dec_ins) == len(PAYLOAD),
          f"{len(PAYLOAD)} B decode to {len(dec_ins)} instructions, full coverage")
    check(all(hi in bounds for _, hi in branches),
          f"all {len(branches)} `bge +4` targets land on an instruction boundary")
    check(dec_ins[-1][2] == "jmp [lp]" and dec_ins[-2][2] == "movea disp,gp,r6",
          "stream ends `movea -0x1518,gp,r6` / `jmp [lp]` -- the hooked instruction is restored")
    v101_ins = decode_cave(V101_CAVE, "V101")
    print(f"       V101 {len(v101_ins)} instructions -> V102 {len(dec_ins)} "
          f"(+{len(dec_ins) - len(v101_ins)}); straight-line leaf, no loop/call/divide/float")

    print("\n  [4c] BRANCH CONDITION -- decoded field-by-field.  🛑 the `ba05`/`b205` trap")
    for hexs, want_cond, want_name in (("ae05", 0xE, "bge (signed GE)"),
                                       ("ba05", 0xA, "bne -- MUST NOT APPEAR"),
                                       ("b205", 0x2, "be  -- MUST NOT APPEAR")):
        hw = struct.unpack("<H", bytes.fromhex(hexs))[0]
        cond, opc = hw & 0xF, (hw >> 7) & 0xF
        disp = (((hw >> 11) & 0x1F) << 4 | ((hw >> 4) & 0x7) << 1)
        check(cond == want_cond and opc == 0xB,
              f"  `{hexs}` -> hw 0x{hw:04X}: Bcond opcode 0b1011 ✓, cond 0x{cond:X} = {want_name}"
              + (f", disp +{disp}" if hexs == "ae05" else ""))
    check(bytes.fromhex("ba05") not in PAYLOAD and bytes.fromhex("b205") not in PAYLOAD,
          "the payload contains NO `bne`/`be` -- every branch is `ae05` = signed GE")
    check(PAYLOAD.count(bytes.fromhex("ae05")) == len(branches) == 8,
          f"exactly {len(branches)} branches, all `ae05`: 2 abs() + 1 verdict per comparator (= 6) "
          f"plus 2 sign tests in PASS 3")

    print("\n  [4d] THE COMPARATOR SEMANTICS -- `cmp reg1,reg2` computes reg2 - reg1")
    for lbl, off, a_disp, b_disp, bit in (
            ("b6", 0x00, SRC_R24, SRC_R26, 6), ("b5", 0x2E, SRC_FRIC, SRC_INER, 5)):
        ld_a = bytes.fromhex("2437") + struct.pack("<h", -a_disp)
        ld_b = bytes.fromhex("2437") + struct.pack("<h", -b_disp)
        check(PAYLOAD[off:off + 4] == ld_a and PAYLOAD[off + 0x0C:off + 0x10] == ld_b,
              f"  {lbl}: A = ld.h -0x{a_disp:04X}[gp] ({ld_a.hex()}), "
              f"B = ld.h -0x{b_disp:04X}[gp] ({ld_b.hex()})")
        check(PAYLOAD[off + 0x16:off + 0x18] == bytes.fromhex("e639"),
              f"  {lbl}: `e639` = cmp r6,r7 with r7=|A|, r6=|B| => flags = |A| - |B|")
        pre = 1 << (bit - 4)
        check(PAYLOAD[off + 0x18:off + 0x1A] == bytes([pre, 0x3A])
              and PAYLOAD[off + 0x1A:off + 0x1C] == bytes.fromhex("ae05")
              and PAYLOAD[off + 0x1C:off + 0x1E] == bytes.fromhex("003a")
              and PAYLOAD[off + 0x1E:off + 0x20] == bytes.fromhex("c43a"),
              f"  {lbl}: mov 0x{pre:X},r7 / bge +4 / mov 0x0,r7 / shl 0x4 "
              f"=> bit {bit} SET iff |A| >= |B|")

    print("\n  [4e] MASK COVERAGE -- every telemetry bit written exactly once, Honda 2:0 preserved")
    cleared = set()
    for lbl, m, bits in (("PASS1 b6 + b3=0", MASK_PASS1, {6, 3}), ("PASS2 b5", MASK_PASS2, {5}),
                         ("PASS3 b7 + b4", MASK_PASS3, {7, 4})):
        got = {b for b in range(8) if not (m >> b) & 1}
        check(got == bits and (m & 0x07) == 0x07,
              f"  {lbl:<16} andi 0x{m:02X} clears {sorted(bits, reverse=True)}, "
              f"preserves Honda bits 2:0")
        check(not (cleared & bits), f"  {lbl:<16} touches no bit an earlier pass already wrote")
        cleared |= bits
    check(cleared == {7, 6, 5, 4, 3},
          f"passes cover exactly byte4 bits 7:3 = {sorted(cleared, reverse=True)}")
    check((MASK_B7 & 0x3F) == 0x3F and (MASK_B7 >> 6) == 0,
          f"  byte7 andi 0x{MASK_B7:02X} writes bits 7:6, preserves Honda's counter (5:4) "
          f"and checksum nibble (3:0)")

    print("\n  [4f] PASS ORDER -- load-bearing.  Comparators FIRST, the SIGN pass LAST")
    st_offs = [o for o, _, m in dec_ins if m.startswith("st.b")]
    check(len(st_offs) == 4 and all(PAYLOAD[o:o + 4] == ST_B4_INSN for o in st_offs[:3])
          and PAYLOAD[st_offs[3]:st_offs[3] + 4] == ST_B7_INSN,
          f"4 stores at +{[hex(o) for o in st_offs]}: 1-3 -> gp-0x1514, 4 -> gp-0x1511")
    check(st_offs[2] == 0x7E and PAYLOAD[0x5E:0x62] == bytes.fromhex("2437b494"),
          "the LAST byte4 pass is PASS 3 = the SIGNS (live bits) => it is the liveness witness")

    print("\n  [4g] GATE 1 -- RAM ownership.  Loads only; the store SET is unchanged")
    n_b4 = sum(1 for i in range(len(PAYLOAD) - 3) if PAYLOAD[i:i + 4] == ST_B4_INSN)
    n_b7 = sum(1 for i in range(len(PAYLOAD) - 3) if PAYLOAD[i:i + 4] == ST_B7_INSN)
    v101_b4 = sum(1 for i in range(len(V101_CAVE) - 3) if V101_CAVE[i:i + 4] == ST_B4_INSN)
    v101_b7 = sum(1 for i in range(len(V101_CAVE) - 3) if V101_CAVE[i:i + 4] == ST_B7_INSN)
    check((n_b4, n_b7) == (3, 1) and (v101_b4, v101_b7) == (2, 1),
          f"stores: {n_b4}×gp-0x1514 + {n_b7}×gp-0x1511 (V101: {v101_b4}+{v101_b7}) -- "
          f"SAME TWO CELLS, no new RAM claimed; one extra RMW inside our own byte4")
    check(not [o for o, ln, m in dec_ins
               if m.startswith("st.") and PAYLOAD[o:o + 4] not in (ST_B4_INSN, ST_B7_INSN)],
          "no store anywhere else in the payload")
    regs = set()
    for _, _, m in dec_ins:
        regs |= {t.strip("[],") for t in m.replace(",", " ").split()
                 if t.strip("[],").startswith(("r", "gp", "lp"))}
    check(regs <= {"r0", "r6", "r7", "gp", "lp"},
          f"every register the payload names is in {{r0, r6, r7, gp, lp}} -- got {sorted(regs)}; "
          f"r8/r10 are LIVE across the hook and the cave never touches them")

    print("\n  [4h] CAVE DISCIPLINE -- no byte is hand-invented")
    outside = bytes(base[START:CAVE_BASE]) + bytes(base[CAVE_FREE_END:END])
    verbatim, split = [], []
    for o, ln, m in dec_ins:
        ins = PAYLOAD[o:o + ln]
        if ins in outside or ins in V101_CAVE:
            verbatim.append((o, ins, m))
        else:
            check((ins[:2] in outside or ins[:2] in V101_CAVE) and ins[2:] in outside,
                  f"  +0x{o:02X} {ins.hex()} ({m}): hw1 AND hw2 each appear in verified code")
            split.append((o, ins, m))
    check(len(verbatim) + len(split) == len(dec_ins),
          f"all {len(dec_ins)} instructions accounted: {len(verbatim)} byte-verbatim from the flown "
          f"V101 cave or Honda's own code, {len(split)} assembled from a verbatim hw1 + a verbatim "
          f"hw2 (the gp displacement, taken from Honda's own store to the SAME cell)")

    print("\n  [4i] THE IDENTITY -- 3-bit field ID3 = (byte7[7:6] << 1) | byte4 b3")
    check(PAYLOAD[0x82:0x84] == bytes.fromhex("033a")
          and PAYLOAD[0x84:0x86] == bytes.fromhex("c63a"),
          f"byte7: `033a` (mov 0x3,r7) + `c63a` (shl 0x6,r7) => byte7[7:6] == {IDENTITY_GEN}")
    check(bytes.fromhex("483a") not in PAYLOAD[:0x66]
          and PAYLOAD[0x66:0x68] == bytes.fromhex("483a"),
          "the ONLY `add 0x8,r7` in the payload is PASS 3's b7 SIGN at +0x66 -- "
          "nothing sets bit 3 anywhere")
    check((MASK_PASS1 >> 3) & 1 == 0 and (MASK_PASS2 >> 3) & 1 == 1
          and (MASK_PASS3 >> 3) & 1 == 1,
          f"PASS 1's andi 0x{MASK_PASS1:02X} CLEARS bit 3; passes 2 and 3 preserve it "
          f"=> b3 reads {IDENTITY_B3} unconditionally")
    check(IDENTITY_ID3 == 6,
          f"ID3 = ({IDENTITY_GEN} << 1) | {IDENTITY_B3} = {IDENTITY_ID3}  "
          f"(V99=4, V100=5, V101=7, V102=6 -- no collision; generation 3 now EXHAUSTED)")

    # ==============================================================================================
    code = bytearray(base)
    attributed = set()

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
        print(f"    0x{addr:05X}  {len(post):4d} B   {label}")

    print(f"\n  [5] THE EDITS -- {'four' if GAIN_MOVES else 'two'}, and every byte is named")
    apply(CAVE_BASE, CAVE_PRE, PAYLOAD,
          f"EDIT 1  CAVE           0x{CAVE_BASE:05X}  {V101_CAVE_LEN} -> {CAVE_LEN} B  "
          f"(2 comparators + 2 signs, b3 identity 1 -> 0)")
    apply(R427_ADDR, struct.pack("<h", -R427_FROM), struct.pack("<h", -R427_TO),
          f"EDIT 2  CAN 427 SOURCE 0x{R427_ADDR:05X}  gp-0x{R427_FROM:04X} -> gp-0x{R427_TO:04X}")
    if GAIN_MOVES:
        apply(GAIN_ADDR, struct.pack("<H", GAIN_V101), struct.pack("<H", GAIN_VALUE),
              f"EDIT 3  ⚙ LKAS GAIN     0x{GAIN_ADDR:05X}  {GAIN_V101} -> {GAIN_VALUE}  "
              f"({GAIN_VALUE / GAIN_STOCK:.3g}× Honda's {GAIN_STOCK})")
        for a in (CLAMP_B2_ADDR, CLAMP_B4_ADDR):
            apply(a, struct.pack("<H", CLAMP_V101), struct.pack("<H", CLAMP_VALUE),
                  f"EDIT 4  ⚙ TRACKING CLAMP 0x{a:05X}  {CLAMP_V101} -> {CLAMP_VALUE}")
    else:
        print(f"    (no calibration edit -- ACCORD_V102_GAIN is unset)")

    # ==============================================================================================
    print("\n  [6] POST-EDIT VERIFICATION -- read back out of the image being built")
    check(rd(code, CAVE_BASE, CAVE_LEN) == PAYLOAD, "cave payload byte-identical")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"cave tail 0x{CAVE_BASE + CAVE_LEN:05X}-0x{CAVE_FREE_END:05X} is virgin 0xFF")
    check(s16(code, R427_ADDR) == -R427_TO and rd(code, R427_INSN_ADDR, 2) == R427_HW1,
          f"427 reads gp-0x{R427_TO:04X}; hw1 {R427_HW1.hex()} (ld.h ..,r6) UNMOVED")
    check(rd(code, R427_SAR_ADDR, 2) == R427_SAR and rd(base, R427_SAR_ADDR, 2) == R427_SAR,
          f"427 packer scaler 0x{R427_SAR_ADDR:05X} = {R427_SAR.hex()} = sar 0x{R427_SHIFT},r6 "
          f"-- CARRIED from V101, zero bytes changed")
    code_max = min((CLAMP_VALUE * R427_MUL) >> R427_SHIFT, R427_FIELD_MAX)
    check(code_max < R427_FIELD_MAX,
          f"GATE 3: clamp({CLAMP_VALUE}*{R427_MUL}>>{R427_SHIFT}) = {code_max} of "
          f"{R427_FIELD_MAX} = {100 * code_max / R427_FIELD_MAX:.0f}% of the field; CANNOT CLIP "
          f"below |x| = {(R427_FIELD_MAX << R427_SHIFT) // R427_MUL:,}")
    check(u16(code, GAIN_ADDR) == GAIN_VALUE
          and u16(code, CLAMP_B2_ADDR) == u16(code, CLAMP_B4_ADDR) == CLAMP_VALUE,
          f"gain 0x{GAIN_ADDR:05X} = {u16(code, GAIN_ADDR)}, clamps = {CLAMP_VALUE} "
          f"({'MOVED by the toggle' if GAIN_MOVES else 'V101 values, UNTOUCHED'})")

    print("\n  [6b] FROZEN + the friction dose family, AFTER the edit")
    assert_frozen(code, "built image (pre-CRC)")
    assert_friction_family(code, "built image (pre-CRC)")

    if not GAIN_MOVES:
        print("\n  [6c] 🛑 THE CONTROL LAW IS BIT-FOR-BIT V101's")
        cal_lo, cal_hi = 0xC4000, 0xCC000
        diffs = [i for i in range(cal_lo, cal_hi)
                 if code[i] != base[i] and not (CAVE_BASE <= i < CAVE_FREE_END)]
        check(not diffs,
              f"ZERO calibration bytes differ from V101 across [0x{cal_lo:05X},0x{cal_hi:05X}) "
              f"outside the cave -- the car's behaviour is UNCHANGED")
        code_lo_diffs = [i for i in range(START, 0xC0000) if code[i] != base[i]
                         and i not in (R427_ADDR, R427_ADDR + 1)]
        check(not code_lo_diffs,
              f"ZERO code bytes differ from V101 below 0xC0000 except the 427 source halfword")

    # ==============================================================================================
    eme_audit(code, base, stock, "built image, pre-CRC")

    # ==============================================================================================
    print("\n  [7] CRC RECOMPUTATION")
    touched = sorted(attributed)
    for blk in sorted({tuple(V53.owning_block(code, a)) for a in touched}):
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit on trailer 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        n_in = len([a for a in touched if blk[0] <= a < blk[1]])
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old_crc:08X} -> 0x{new_crc:08X}  "
              f"{n_in} of {len(touched)} edited bytes")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    # ==============================================================================================
    print("\n  [8] FULL BYTE DIFF vs HONDA STOCK")
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

    print("\n  [8b] FULL BYTE DIFF vs THE V101 BASE -- what THIS build changed")
    bruns = [i for i in range(START, END) if code[i] != base[i]]
    runs = []
    for i in bruns:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    # 🛑 Attribute by INTERSECTION with the bytes this script actually wrote, never by the run's
    #    first address.  A 4096 -> 3072 clamp edit only moves the HIGH byte, so the run starts at
    #    0xC61B3, not at the named 0xC61B2 -- keying on the start silently mislabels it.
    named = [(R427_ADDR, 2, "CAN 427 SOURCE"), (CAVE_BASE, CAVE_LEN, "CAVE"),
             (GAIN_ADDR, 2, "⚙ LKAS GAIN"), (CLAMP_B2_ADDR, 2, "⚙ CLAMP 0xC61B2"),
             (CLAMP_B4_ADDR, 2, "⚙ CLAMP 0xC61B4")]
    unnamed = []
    for lo, hi in runs:
        span = set(range(lo, hi))
        if (lo & 0xFFF) >= 0xFFC:
            tag = "CRC trailer"
        else:
            hits = [w for a, n, w in named if span & set(range(a, a + n))]
            tag = " + ".join(hits) if hits else "?? UNATTRIBUTED"
            if not hits or not span <= (attributed | {a for a_, n_, _ in named
                                                      for a in range(a_, a_ + n_)}):
                unnamed.append((lo, hi))
        print(f"       0x{lo:05X}..0x{hi - 1:05X}  {hi - lo:4d} B   {tag}")
    check(not unnamed,
          f"every one of the {len(runs)} changed runs vs V101 lies inside a named edit or a CRC "
          f"trailer" + ("" if not unnamed else f"  -- STRAY: {[(hex(a), hex(b)) for a, b in unnamed]}"))

    # ==============================================================================================
    print("\n  [9] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V102 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V102_WRITE=rwd to cut.")
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

            # ======================================================================================
            # EVERYTHING BELOW READS THE SHIPPED FILE BACK OFF DISK.  No script claims.
            # ======================================================================================
            print("\n  [10] FROM-DISK VERIFICATION -- the shipped .rwd, decoded")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha, "shipped .rwd sha256 OK")
            FF.assert_x31_checksum(shipped, "V102 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "shipped .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped CRC 50/50")
            disk_img = bytearray(Path(BIN_OUT).read_bytes())
            check(hashlib.sha256(bytes(disk_img)).hexdigest() == img_sha,
                  "plain image re-read from disk, sha256 OK")
            check(bytes(disk_img) == bytes(sd), "plain image on disk == decoded shipped .rwd")

            print("\n  [10b] THE CELL TABLE, READ OUT OF THE SHIPPED IMAGE")
            print(f"       {'address':<10} {'stock':>7} {'V101':>7} {'V102':>7}  {'':6} what")
            for a, w, why in (
                    (0x3AA96, 1, "🛑 LEVER B GATE -- HONDA STOCK. Measured null; DO NOT RESTORE"),
                    (0xC6446, 2, "🛑 LEVER B ARM -- HONDA STOCK. Same evidence"),
                    (0xC40D2, 2, "🛑 K1 -- HELD at 204, instrumented by b5, NOT dosed"),
                    (GAIN_ADDR, 2, "⚙ the PRIVATE forward-LKAS gain (the one toggle)"),
                    (CLAMP_B2_ADDR, 2, "LKAS fwd-path clamp -- tracks the gain"),
                    (CLAMP_B4_ADDR, 2, "arb output clamp -- tracks the gain"),
                    (0xC407E, 2, "hard-fault interlock -- Honda's 511"),
                    (0xC4080, 2, "K0 -- NEVER-RAISE"),
                    (0xC40BC, 2, "Coulomb ramp knee (V99)"),
                    (0xC63AC, 2, "accumulator pole (V99's revert to Honda)"),
                    (0xC40D0, 2, "friction EMA alpha"),
                    (0xC61F6, 2, "r24 deadzone"),
                    (0xC6444, 2, "r24 lane companion cal -- VIRGIN"),
                    (0x454FE, 1, "V42 state-4 governor byte")):
                mv = "MOVED" if rdw(disk_img, a, w) != rdw(base, a, w) else "  =  "
                print(f"       0x{a:05X}    {rdw(stock, a, w):>7} {rdw(base, a, w):>7} "
                      f"{rdw(disk_img, a, w):>7}  {mv:<6} {why}")
            check(disk_img[0x3AA96] == 0xC5 and u16(disk_img, 0xC6446) == 512,
                  "shipped: LEVER B IS HONDA-STOCK (gate dead, arm 512) -- NOT restored")
            check(u16(disk_img, 0xC40D2) == 204, "shipped: K1 HELD at 204")
            check(rd(disk_img, CAVE_BASE, CAVE_LEN) == PAYLOAD,
                  f"shipped: {CAVE_LEN}-byte cave payload byte-identical")
            check(decode_cave(rd(disk_img, CAVE_BASE, CAVE_LEN), "shipped")
                  == decode_cave(PAYLOAD, "V102"),
                  "shipped: the cave RE-DECODES from disk to the same instruction stream")
            check(bytes.fromhex("ba05") not in rd(disk_img, CAVE_BASE, CAVE_LEN)
                  and bytes.fromhex("b205") not in rd(disk_img, CAVE_BASE, CAVE_LEN)
                  and rd(disk_img, CAVE_BASE, CAVE_LEN).count(bytes.fromhex("ae05")) == 8,
                  "shipped: 8 × `ae05` (signed GE), ZERO `ba05`/`b205` -- the trap is clear")
            check(s16(disk_img, R427_ADDR) == -R427_TO
                  and rd(disk_img, R427_SAR_ADDR, 2) == R427_SAR,
                  f"shipped: CAN 427 reads gp-0x{R427_TO:04X}, sar {R427_SHIFT} carried")
            check(disk_img[CAVE_BASE + 0x82:CAVE_BASE + 0x84] == bytes.fromhex("033a")
                  and bytes.fromhex("483a") not in bytes(disk_img[CAVE_BASE:CAVE_BASE + 0x66]),
                  f"shipped: byte7[7:6] = {IDENTITY_GEN}, b3 = {IDENTITY_B3} "
                  f"=> ID3 = {IDENTITY_ID3}")
            assert_frozen(disk_img, "SHIPPED image")
            assert_friction_family(disk_img, "SHIPPED image")
            eme_audit(disk_img, base, stock, "SHIPPED image, from disk")

    print("\n" + "=" * 102)
    print(f"  V102 [{VARIANT_TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    if GAIN_MOVES:
        print(f"  ⚙ EXACTLY ONE INDEPENDENT CALIBRATION VARIABLE -- THE OPERATOR'S RULING:")
        print(f"       0xC6CD0  {GAIN_V101} -> {GAIN_VALUE}   "
              f"({GAIN_V101 // GAIN_STOCK}× -> {GAIN_VALUE / GAIN_STOCK:.3g}× Honda's {GAIN_STOCK})")
        print(f"       0xC61B2 / 0xC61B4  {CLAMP_V101} -> {CLAMP_VALUE}   "
              f"TRACKING (= GAIN*512//891, exact), NOT independent")
        print(f"     PRE-REGISTERED: 22-26 Hz shape ratio falls to 0.61x [0.57-0.66] of V101's 5.07."
              f"  ~1.0x REFUTES the gain attribution.")
        print(f"     🛑 p = 1.74 [1.43,1.96] rests on TWO POINTS. Empirical exponent, not a law."
              f"  Q/-3dB is NOT an endpoint (analysts disagree on its SIGN).")
        print(f"     🛑 STRUCTURAL CAP: 0xC674E = 5120 must exceed the clamp => this gain CANNOT "
              f"reach 10x. Verified: =10x aborts.")
    else:
        print(f"  🛑 **ZERO CALIBRATION EDITS.** The control law is bit-for-bit V101's.")
    print(f"     Lever B stays Honda-stock (0x3AA96=0xC5, 0xC6446=512) -- measured null at "
          f"22-26 Hz, and its removal was a measured 3× WIN at 6-9 Hz.")
    print(f"     K1 stays 204, INSTRUMENTED by b5, NOT dosed. 0xCBE74 ×1.5 carried, measured INERT.")
    print(f"  CAVE: {CAVE_LEN} B = {100 * CAVE_LEN / (CAVE_FREE_END - CAVE_BASE):.1f}% of extent. "
          f"b6/b5 COMPARATORS first, b7/b4 SIGNS last (liveness witness).")
    print(f"  427:  source -> gp-0x{R427_TO:04X}, sar {R427_SHIFT} carried. "
          f"🛑 NOT for the 23 Hz spectrum (Nyquist 24.9 Hz) -- magnitude distribution only.")
    print(f"  IDENTITY: ID3 = ({IDENTITY_GEN} << 1) | {IDENTITY_B3} = {IDENTITY_ID3}. V101 = 7. "
          f"⚠ byte4[7:3] is EVEN on every frame -- THAT IS THE IDENTITY, not a defect.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
