#!/usr/bin/env python3
"""builds/v50_v79/build_v71c_tva.py -- V71C = V67/V68's control path with the r26 CUT REMOVED, + the ratchet byte.

    V71C  ==  V67  +  0xC6444 512 -> 3072  +  0x454FE  +  a new cave,  AND NOTHING ELSE.

That identity is ASSERTED against `_v67_plain_image.bin`, not aimed at. It is the whole safety case:
V67 and V68 flew that control path TWICE, flight-clean.

WHY THIS BUILD EXISTS -- neither V71A nor V71B fixes BOTH grinds
-----------------------------------------------------------------
The standing request is a build that fixes both. The corpus says grind #2 is quietest when r26 sits
at STOCK, and grind #1 is fixed when r26 is MOVED -- in EITHER direction:

    r26                        grind #1        creep grind #2       highway grind #2
    x2 everywhere (V62)        168  ✓          CAUSED  ✗            --
    /6 engaged (V67/V68)       109  ✓          0 bursts ✓           PRESENT ✗
    x1 (V69/V70)               729/746 ✗       clean ✓              clean ✓

That reads like a one-variable trade -- **except V67/V68 beat it at creep**, fixing grind #1 (109,
the best in the kit) AND creep grind #2 (0 bursts, P(0) = 0.0005 on r4a) at the same time. Its ONLY
failure is highway. And the one thing V67/V68 does at highway that both clean builds do not is
**cut r26 by ~6x**. V71C removes exactly that cut and changes nothing else.

THE FIVE EDITS, off `_v70_plain_image.bin`
-------------------------------------------
    0x3AA96   0xC5 -> 0xFB    restore V67/V68's LKAS gate: `ld.bu -0x683c[gp],r15` becomes
                              `ld.bu -0x6806[gp],r15`. gp-0x683c has ZERO writers, so with the gate
                              on the dead cell BOTH arms are unreachable; repointing it to
                              gp-0x6806 ("LKAS is applying") makes both arms LIVE while engaged and
                              leaves MANUAL steering byte-for-byte STOCK.
    0xC6446   512 -> 5244     r24's arm -- EXACTLY V67/V68's value, not re-derived.
    0xC6444   512 -> 3072     r26's arm -- **THE NEW LEVER.** Removes the ~6x cut.
    0x454FE   0xBA -> 0xB5    V42's state-4 governor ratchet kill.
    0xD2A7E/80, 0xD2ABA/BC    V70's gain_B surface dose dropped back to STOCK.
    both `sar` sites          LEFT STOCK (0x3AB76 = 0x32AA, 0x3AC20 = 0x42AA).

★ WHY 3072 AND NOT 6144 -- the crux of the choice, and it is an ARITHMETIC argument
------------------------------------------------------------------------------------
3072 is `gain_A`'s own stock creep value, so the `mul r8,r6,r0` operand at 0x3AB72 stays at STOCK
magnitude. The structural worst case is `((5120 * 65535) >> 10) * gain_A = 327,675 * gain_A`, and
V850 `mul` discards the high word into r0 -- an overflow is a SILENT truncation with a possible sign
flip. Hence a hard ceiling of `2^31 / 327,675 = 6553`:

    gain_A  3072  (stock / V71A / **V71C**)   1,006,617,600   **46.87% of INT32_MAX**
    gain_A  6144  (V71B)                      2,013,235,200     93.75% of INT32_MAX
    gain_A  6553  (the ceiling)               2,147,244,  ...   ~100%  -- do not approach

⇒ **V71C carries NO INT32 headroom loss at all.** It sits exactly where stock and V71A sit, and
avoids the 93.75% band that V62's own build note rejected when it refused to edit 0x3AB70. Asserted
below, not asserted in prose.

🛑🛑 `0xC6444` IS LIVE ON THIS BUILD. THE "NULL BY CONSTRUCTION" STRIKE IS FOR V71A/V71B ONLY
-----------------------------------------------------------------------------------------------
The record currently strikes `0xC6444` as "a null lever by construction". **That strike is CORRECT
for V71A and V71B and WRONG for V71C**, and the difference is one byte. `0xC6444` is read at
`0x3AB5E` and ONLY when `lp != 0`:
    0x3AA94  ld.bu -0x683c[gp],r15     <- 0x3AA96 is the displacement byte this build repoints
    0x3AAA6  cmp   r0,r15
    0x3AAA8  setfne lp
    0x3AB5C  be    0x3AB64             ; lp == 0  -> skip the arm
    0x3AB5E  ld.hu 0x7444[tp],r8       ; 0xC6444  <- reached ONLY when lp != 0
On a GATELESS build (`0x3AA96` = 0xC5) `lp` derives from gp-0x683c, which has ZERO writers
image-wide, so `lp` is always 0 and the load never executes -- hence the strike. **V71C repoints the
gate, so `lp` becomes "LKAS is applying" and the load runs on every engaged tick.** Do not carry the
strike across builds; it is a property of the GATE byte, not of the cal.

THE DELIVERED DOSE
-------------------
  MANUAL (gp-0x6806 == 0 ⇒ lp == 0): both arms unreachable, both LERPs stock, both `sar` sites
      stock, gain_B stock ⇒ **byte-for-byte STOCK base steering.** That is V67/V68's own property
      and it is asserted by sweep below.
  ENGAGED: r24 = 5244 / gain_B_LERP  ·  r26 = 3072 / gain_A_LERP. Because gain_A's creep value IS
      3072, **r26 is 1.000x at creep** and rises only as the stock LERP rolls off with speed
      (max 3072/2560 = 1.200x at 100 km/h). Versus V67/V68 it is a flat **6.000x** un-cut.

🛑🛑 A CORRECTION TO THIS BUILD'S OWN RATIONALE -- THE HIGHWAY ATTRIBUTION IS NOT UNIQUE
------------------------------------------------------------------------------------------
The brief's reasoning was: *"the one thing V67/V68 does at highway that both clean builds do not is
cut r26 ~6x."* **That is not the only thing, and the sweep in this file proves it.** Engaged
delivered multiplier vs STOCK at 100 km/h, rateKey 0 (stock LERPs: gain_B 2151, gain_A 2560):

    build       r24        r26
    V67/V68     2.438x     0.200x     <- highway grind #2 PRESENT
    V69/V70     1.000x     1.000x     <- highway CLEAN
    **V71C**    **2.438x** **1.200x**

V67/V68 differ from the highway-clean builds in **BOTH** lanes: r26 is cut ~5-6x **and r24 is raised
2.44x**. A scalar ARM does not follow the LERP's own speed rolloff, so `arm / LERP` RISES with speed
and PEAKS at highway -- the exact property that drove V70's re-cut away from this topology.
**V71C removes only ONE of the two candidate causes.** It keeps r24's 2.438x highway rise, byte for
byte, because that is V67/V68's arm and this build deliberately does not touch it.

⇒ **IF the highway grind #2 came from the r24 rise rather than the r26 cut, V71C will NOT fix it.**
  Stated plainly because the operator has already overridden one build on exactly this symptom. The
  build is still worth flying -- it is the only clean single-variable test of the r26 cut, and its
  creep behaviour is V67/V68's, which is the best in the kit -- but it must not be sold as
  "fixes highway". Score highway grind #2 as the primary readout.
  ⚠ If it comes back, the follow-up is ONE halfword: `0xC6446` 5244 -> ~2151-2400, which flattens
    r24's highway rise while keeping most of its creep dose. Not built; named so it is not lost.

⚠ THE OTHER RESIDUAL, RECORDED UNSMOOTHED
-------------------------------------------
If V67/V68's 109 depended on the r26 **CUT** rather than on its r24 arm, then removing the cut loses
the grind #1 fix. That is the x2-vs-/6 paradox and it is **UNRESOLVED**. The argument that the r24
arm carries it: **V62 reached 168 with r24 x2 and NO r26 cut at all.** That is an argument, not a
measurement, and V71C is the experiment that separates them.

THE PROBE -- bit4/bit3 stay on `gp-0x6ada` (r24). The case, since it was left to my judgement:
-------------------------------------------------------------------------------------------------
V71C moves BOTH lanes, so the "instrument the lane you dose" rule does not pick for us. It resolves
on WHERE the dose actually lands:
  * r24 is dosed **~2.00x at creep** (arm 5244 against a stock LERP of 2622 at grind #1's operating
    point) -- and creep is where grind #1 lives.
  * r26 is dosed **1.000x at creep** and only 1.200x at 100 km/h. At the operating point that
    matters it is NOT dosed at all; watching it there would repeat V71B's original defect in mirror
    image.
  * Keeping gp-0x6ada makes **V71A and V71C directly comparable on bit4** -- same cell, same T, and
    both deliver ~2x to r24 at creep through DIFFERENT encodings (a `sar` immediate vs a scalar
    arm). That is the only like-for-like cross-build bit4 comparison in the whole A/B/C set, and it
    separates "the arm delivered" from "the shift delivered".
⚠ THE CASE AGAINST, stated so the choice can be reversed cheaply: a magnitude reading on
  `gp-0x6adc` would BOUND `avg(gp-0x69a4)` -- the unmeasured quantity that blocks every r26
  saturation argument in this kit -- because |r26| >= 128 at gain_A 3072 implies
  |dtorque| * avg >= 43,690. **V71B already provides exactly that reading**, so the set covers it:
  A and C watch r24, B watches r26. If V71C flies alone and `avg` matters more than the A/C
  comparison, it is ONE byte: cave+0x1A `0x26` -> `0x24`.

Usage:  python builds/v50_v79/build_v71c_tva.py
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
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v69_tva as V69                # noqa: E402  (gain_B model)
import build_v71a_tva as A                 # noqa: E402  (cave, gates, ratchet edit, surface consts)
import build_v71b_tva as B                 # noqa: E402  (gain_A model + the r26 arithmetic)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = A.START, A.END
CAVE_BASE, CAVE_EXTENT = A.CAVE_BASE, A.CAVE_EXTENT

# ---- the control path: V67/V68's, restored ------------------------------------------------------
GATE_ADDR, GATE_DEAD, GATE_LIVE = A.REPOINT_BYTE, A.GATE_DEAD, A.GATE_LIVE   # 0x3AA96, 0xC5, 0xFB
GATE_LOAD = (A.REPOINT_ADDR, bytes.fromhex("847fc597"), bytes.fromhex("847ffb97"))
R24_ARM, R24_ARM_STOCK, R24_ARM_NEW = A.ARM_ADDR, 512, 5244        # 0xC6446 -- V67/V68's value
R26_ARM, R26_ARM_STOCK, R26_ARM_NEW = 0xC6444, 512, 3072           # THE NEW LEVER
R26_ARM_READ = 0x3AB5E                     # `ld.hu 0x7444[tp],r8`, reached ONLY when lp != 0
R26_ARM_CEILING = 6553                     # 2^31 / ((5120 * 65535) >> 10) -- INT32, silent overflow
OTHER_R26_ARM = (0xC643E, 1536)            # state < CEIL -- untouched

# ---- the probe watches r24, which THIS build doses ~2x at creep --------------------------------
MIRROR = A.R24_MIRROR_DISP                 # 0x6ADA

CAL_BLOCK = (0xC6000, 0xC6FFC)

TAG = ("LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-V67gate-arm5244-r26arm3072UNCUT-"
       "sarSTOCK-probe2-671d-67fa4-6adaABS128-sign-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V71C-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v71c_plain_image.bin"))
SRC_BIN = plain_image_path("_v70_plain_image.bin")
V67_BIN = plain_image_path("_v67_plain_image.bin")
V68_BIN = plain_image_path("_v68_plain_image.bin")
STOCK_BIN = stock_fw_path("code.bin")
DECODER = os.path.join(HERE, "..", "rlog-tools", "probe/decode_v71_probe.py")

# The spans whose byte-identity to V67 IS the safety claim.
V67_IDENTICAL_SPANS = ((0x3A300, 0x3AE00, "both inline rate lanes, the aggregator and the GATE"),
                       (0xD2000, 0xD2FFC, "the mode-10 gain_B surface + V60's blend cells"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def r24_engaged_gain(buf, speed, rate):
    """Engaged, with the gate ON and gp-0x671d clear: r24's arm REPLACES the LERP (0x3AC08)."""
    return u16(buf, R24_ARM)


def r26_engaged_gain(buf, speed, rate):
    """Engaged, with the gate ON: r26's arm REPLACES the LERP (0x3AB5E)."""
    return u16(buf, R26_ARM)


def assert_control_path(buf, label, engaged_topology):
    """The (gate, r24 arm, r26 arm) triple, and the invariant that binds them.

    🛑 THE DANGEROUS COMBINATION is a repointed gate with a STOCK arm: the engaged lane is then
    pinned at 512 against a LERP of 2101-3072, i.e. ~5x BELOW stock everywhere -- V61 territory, and
    V61 measured WORSE on-car. Both directions are asserted so neither topology can be emitted
    broken.
    """
    gate, r24, r26 = buf[GATE_ADDR], u16(buf, R24_ARM), u16(buf, R26_ARM)
    if engaged_topology:
        assert (gate, r24) == (GATE_LIVE, R24_ARM_NEW), \
            f"{label}: (gate, r24 arm) is (0x{gate:02X}, {r24}), expected (0xFB, {R24_ARM_NEW})"
        assert r26 == R26_ARM_NEW, f"{label}: r26 arm is {r26}, expected {R26_ARM_NEW}"
        assert bytes(buf[GATE_LOAD[0]:GATE_LOAD[0] + 4]) == GATE_LOAD[2], \
            f"{label}: the gate load is not `ld.bu -0x6806[gp],r15`"
    else:
        assert (gate, r24, r26) == (GATE_DEAD, R24_ARM_STOCK, R26_ARM_STOCK), \
            f"{label}: expected the gateless topology (0xC5, 512, 512)"
        assert bytes(buf[GATE_LOAD[0]:GATE_LOAD[0] + 4]) == GATE_LOAD[1], \
            f"{label}: the gate load is not the stock `ld.bu -0x683c[gp],r15`"
    assert not (gate == GATE_LIVE and r24 == R24_ARM_STOCK), \
        f"{label}: the gate is LIVE with a STOCK r24 arm -- that pins the engaged lane ~5x BELOW " \
        "stock everywhere (V61 territory, measured WORSE on-car). Refusing to emit."
    assert not (gate == GATE_LIVE and r26 == R26_ARM_STOCK), \
        f"{label}: the gate is LIVE with a STOCK r26 arm -- that is V67/V68's ~6x CUT, which is " \
        "exactly what this build exists to remove. Refusing to emit."
    assert u16(buf, OTHER_R26_ARM[0]) == OTHER_R26_ARM[1], f"{label}: 0xC643E moved"


def assert_int32_headroom(gain_a, label):
    """The `mul r8,r6,r0` @0x3AB72 worst case, from STRUCTURAL bounds only."""
    stage1 = (B.DTORQUE_CLAMP * B.AVG_MAX) >> B.SAR1
    prod = stage1 * gain_a
    assert 2 ** 31 // stage1 == R26_ARM_CEILING, "the recorded 6553 ceiling does not re-derive"
    assert gain_a <= R26_ARM_CEILING, \
        f"{label}: gain_A {gain_a} exceeds the INT32 ceiling {R26_ARM_CEILING} -- V850 `mul` " \
        "discards the high word SILENTLY"
    return prod, prod / 2 ** 31 * 100


def assert_decoder_matches(cave_bytes):
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX_A\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m and m.group(1) == cave_bytes.hex(), \
        "V71C: the decoder's CAVE_HEX_A does not match this cave (V71C shares V71A's r24 probe)"
    assert "V71C" in txt, "V71C: the decoder does not mention V71C"
    assert os.path.basename(OUT) in txt, "V71C: the decoder does not carry V71C's .rwd basename"
    assert re.search(r'"v71a": dict\(cave=CAVE_HEX_A, lane="r24", cell=0x6ADA', txt), \
        "V71C: the decoder's r24 entry drifted"
    return True


def build():
    print(__doc__)
    src = Path(SRC_BIN)
    v70 = bytearray(src.read_bytes())
    v67 = Path(V67_BIN).read_bytes()
    v68 = Path(V68_BIN).read_bytes()
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V70): {src}\n  SHA256 {hashlib.sha256(bytes(v70)).hexdigest()}")
    print(f"CONTROL-PATH REFERENCE (V67): {V67_BIN}")

    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    for sibling in (A.BIN_OUT, B.BIN_OUT):
        assert Path(BIN_OUT).name != Path(sibling).name, \
            "V71C would overwrite a sibling's plain image -- the recorded same-number hazard"

    # ---- gate the SOURCE and the reference --------------------------------------------------------
    assert len(v70) == len(v67) == len(stock) == 0x100000
    A.assert_ratchet_edit(v70, "V70 source", expect_edited=False)
    A.assert_sar_sites(v70, "V70 source", expect_doubled=False)
    A.assert_no_external_entry(v70)
    assert_control_path(v70, "V70 source", engaged_topology=False)
    assert v67[GATE_ADDR] == GATE_LIVE and u16(v67, R24_ARM) == R24_ARM_NEW, \
        "the V67 reference does not carry the (0xFB, 5244) control path"
    assert u16(v67, R26_ARM) == R26_ARM_STOCK == 512, \
        "the V67 reference does not carry the ~6x r26 CUT this build removes"
    assert v67[GATE_ADDR] == v68[GATE_ADDR] and u16(v67, R24_ARM) == u16(v68, R24_ARM) \
        and u16(v67, R26_ARM) == u16(v68, R26_ARM), "V67 and V68 disagree on the control path"
    B.assert_gain_a(v70, "V70 source", doubled=False)
    B.assert_gain_a(stock, "stock", doubled=False)
    for lo, hi, what in A.STOCK_IDENTICAL_SPANS:
        assert not [i for i in range(lo, hi) if v70[i] != stock[i]], \
            f"[0x{lo:05X},0x{hi:05X}) ({what}) differs from stock"
    print(f"  source gates: gate 0x{GATE_DEAD:02X}, arms {R24_ARM_STOCK}/{R26_ARM_STOCK}, sar STOCK, "
          f"0x{A.RATCHET_ADDR:05X} stock  ✅")
    print(f"  ⭐ V67 AND V68 both carry (gate 0xFB, r24 arm 5244, r26 arm 512) -- the path this build")
    print("     restores, and the cut it removes. Both flew flight-clean.")

    code = bytearray(v70)

    # ---- EDIT 1 -- V42's ratchet fix ------------------------------------------------------------
    print("\n  EDIT 1 -- THE RATCHET FIX:")
    struct.pack_into("<H", code, A.RATCHET_ADDR, A.RATCHET_NEW_HW)
    A.assert_ratchet_edit(code, "V71C", expect_edited=True)
    A.assert_no_external_entry(code)
    n_state = A.assert_governor_monitor_safety(code, "V71C")
    print(f"    0x{A.RATCHET_ADDR:05X}  0x{A.RATCHET_STOCK_HW:04X} -> 0x{A.RATCHET_NEW_HW:04X}   "
          f"bne 0x455C4 -> br 0x455C4; FUN_0004595a safety re-derived ({n_state} state read)")

    # ---- EDIT 2 -- restore V67/V68's gate, then BOTH arms ---------------------------------------
    print("\n  EDIT 2 -- V67/V68's CONTROL PATH, restored, with the r26 CUT REMOVED:")
    code[GATE_ADDR] = GATE_LIVE
    struct.pack_into("<H", code, R24_ARM, R24_ARM_NEW)
    struct.pack_into("<H", code, R26_ARM, R26_ARM_NEW)
    print(f"    0x{GATE_ADDR:05X}  0x{GATE_DEAD:02X} -> 0x{GATE_LIVE:02X}   `ld.bu -0x683c` -> "
          "`ld.bu -0x6806` : the gate becomes LKAS-is-applying, so BOTH arms go LIVE")
    print(f"    0x{R24_ARM:05X}  {R24_ARM_STOCK:5d} -> {R24_ARM_NEW:5d}   r24's arm -- EXACTLY "
          "V67/V68's value")
    print(f"    0x{R26_ARM:05X}  {R26_ARM_STOCK:5d} -> {R26_ARM_NEW:5d}   r26's arm -- ★ THE NEW "
          f"LEVER: {R26_ARM_NEW // R26_ARM_STOCK}.000x un-cut vs V67/V68")
    assert_control_path(code, "V71C", engaged_topology=True)
    assert bytes(code[GATE_LOAD[0]:GATE_LOAD[0] + 4]) == bytes(v67[GATE_LOAD[0]:GATE_LOAD[0] + 4]), \
        "the emitted gate load is not byte-identical to V67's"
    print("    ✅ EDIT-ORDER INVARIANT asserted BOTH WAYS: a LIVE gate with a stock r24 arm (~5x "
          "BELOW stock, V61 territory) and a LIVE gate with a stock r26 arm (V67/V68's cut) are")
    print("       both REFUSED. The emitted gate load is byte-identical to V67's.")
    prod, pct = assert_int32_headroom(R26_ARM_NEW, "V71C")
    prod_b, pct_b = assert_int32_headroom(2 * 3072, "V71B (for comparison)")
    print(f"    ✅ INT32 HEADROOM at `mul r8,r6,r0` @0x3AB72, structural worst case "
          f"((5120 x 65535) >> 10) x gain_A:")
    print(f"       gain_A {R26_ARM_NEW:5d} (V71C)   {prod:>13,}  = {pct:5.2f}% of INT32_MAX   "
          "⇐ EXACTLY stock/V71A. NO headroom lost.")
    print(f"       gain_A {2 * 3072:5d} (V71B)   {prod_b:>13,}  = {pct_b:5.2f}% of INT32_MAX   "
          "⇐ the band V62's note rejected")
    print(f"    ✅ 0x{R26_ARM:05X} = {R26_ARM_NEW} is inside the INT32 ceiling {R26_ARM_CEILING} "
          f"(= 2^31 / (({B.DTORQUE_CLAMP} x {B.AVG_MAX}) >> {B.SAR1})), re-derived not quoted")

    # ---- EDIT 3 -- drop V70's gain_B surface dose; leave both `sar` sites stock -------------------
    print("\n  EDIT 3 -- V70's gain_B surface dose REVERTED; both `sar` sites LEFT STOCK:")
    for addr, old, new, name in A.SURFACE:
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   {name}")
    for base, ys in A.REC_Y_STOCK.items():
        assert bytes(code[base:base + 0x14]) == bytes(stock[base:base + 0x14]), \
            f"mode-10 gain_B record 0x{base:05X} is not byte-identical to STOCK"
    A.assert_sar_sites(code, "V71C", expect_doubled=False)
    B.assert_gain_a(code, "V71C", doubled=False)
    print("    ✅ all four gain_B records and all four gain_A records byte-identical to STOCK, and")
    print(f"       both `sar` sites stock ⇒ the ONLY levers on this build are the GATE, the two ARMS")
    print(f"       and 0x{A.RATCHET_ADDR:05X}.")

    # ---- EDIT 4 -- the probe (V71A's, watching r24) ----------------------------------------------
    print("\n  EDIT 4 -- THE PROBE, watching gp-0x6ADA = r24's mirror (the lane dosed ~2x at creep):")
    cave_bytes, cave_listing = A.build_cave(MIRROR)
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    nr, nw = A.assert_probe_census(bytes(code), cave_span, MIRROR)
    assert cave_bytes == A.build_cave(A.R24_MIRROR_DISP)[0], "V71C's cave is not V71A's"
    print(f"    ✅ GATE 1 re-measured from raw bytes: gp-0x67fa {nr}r/{nw}w, READ-ONLY by the cave;")
    print("       the sole store is the CAN-330 payload byte with bits 2:0 preserved.")
    print("    ✅ BYTE-IDENTICAL to V71A's cave ⇒ decode with `--v71a`'s bit map. 🛑 The wire cannot")
    print("       separate V71A from V71C; the .rwd FILENAME is the discriminator.")
    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/probe/decode_v71_probe.py matches this cave and names V71C")

    # ---- THE DELIVERED MULTIPLIER TABLE ----------------------------------------------------------
    print("\n  DELIVERED MULTIPLIER -- engaged and manual, both lanes, vs STOCK and vs V67/V68:")
    print(f"    {'km/h':>6}  {'r24 eng':>8} {'r26 eng':>8}  {'r24 man':>8} {'r26 man':>8}   "
          f"{'r24 vs V67':>10} {'r26 vs V67':>10}")
    rows = []
    for kmh in (0, 10, 50, 100):
        counts = int(kmh * 64.0625)
        gb, ga = V69.gain_q10(code, counts, 0), B.gain_a_q10(code, counts, 0)
        gb_s, ga_s = V69.gain_q10(stock, counts, 0), B.gain_a_q10(stock, counts, 0)
        r24_eng, r26_eng = r24_engaged_gain(code, counts, 0) / gb_s, r26_engaged_gain(code, counts, 0) / ga_s
        r24_man, r26_man = gb / gb_s, ga / ga_s
        r24_v67 = u16(code, R24_ARM) / u16(v67, R24_ARM)
        r26_v67 = u16(code, R26_ARM) / u16(v67, R26_ARM)
        rows.append((kmh, r24_eng, r26_eng, r24_man, r26_man, r24_v67, r26_v67))
        print(f"    {kmh:>6}  {r24_eng:>8.3f} {r26_eng:>8.3f}  {r24_man:>8.3f} {r26_man:>8.3f}   "
              f"{r24_v67:>10.3f} {r26_v67:>10.3f}")
    assert all(abs(r24_man - 1.0) < 1e-12 and abs(r26_man - 1.0) < 1e-12
               for _k, _a, _b, r24_man, r26_man, _c, _d in rows), \
        "a MANUAL multiplier is not exactly 1.000000 -- manual must be byte-for-byte stock"
    assert all(abs(v - 1.0) < 1e-12 for *_x, v in [(r[0], r[5]) for r in rows]), \
        "r24's arm is not identical to V67/V68's"
    assert all(abs(r[6] - R26_ARM_NEW / R26_ARM_STOCK) < 1e-12 for r in rows), \
        f"r26 vs V67 is not a flat {R26_ARM_NEW // R26_ARM_STOCK}.000x"
    print(f"    ✅ MANUAL is EXACTLY 1.000000x on BOTH lanes at every speed -- the arms are behind")
    print("       the gate, so disengaged steering is byte-for-byte STOCK. (V67/V68's own property.)")
    print(f"    ✅ vs V67/V68 the ONLY row that moves is r26: a flat "
          f"{R26_ARM_NEW // R26_ARM_STOCK}.000x un-cut. r24 is IDENTICAL.")
    print(f"    ⚠ r26 engaged is {rows[0][2]:.3f}x at creep (gain_A's own stock creep value IS "
          f"{R26_ARM_NEW}) rising to {rows[-1][2]:.3f}x at 100 km/h as the stock LERP rolls off.")
    # 🛑🛑 THE ATTRIBUTION CORRECTION, PRINTED so it cannot be missed by a reader who skips the note.
    hw = int(100 * 64.0625)
    v67_r24 = u16(v67, R24_ARM) / V69.gain_q10(stock, hw, 0)
    v67_r26 = u16(v67, R26_ARM) / B.gain_a_q10(stock, hw, 0)
    v70_r24 = V69.gain_q10(v70, hw, 0) / V69.gain_q10(stock, hw, 0)
    v70_r26 = B.gain_a_q10(v70, hw, 0) / B.gain_a_q10(stock, hw, 0)
    print("\n  🛑 THE HIGHWAY ATTRIBUTION IS NOT UNIQUE -- re-derived here, not argued:")
    print(f"     at 100 km/h, engaged, vs STOCK:   {'build':<10} {'r24':>8} {'r26':>8}")
    print(f"                                       {'V67/V68':<10} {v67_r24:>8.3f} {v67_r26:>8.3f}"
          "   <- highway grind #2 PRESENT")
    print(f"                                       {'V69/V70':<10} {v70_r24:>8.3f} {v70_r26:>8.3f}"
          "   <- highway CLEAN")
    print(f"                                       {'V71C':<10} {rows[-1][1]:>8.3f} "
          f"{rows[-1][2]:>8.3f}")
    assert abs(v67_r24 - rows[-1][1]) < 1e-12, "V71C's highway r24 is not V67/V68's"
    assert v70_r24 == 1.0 and v70_r26 == 1.0, "V69/V70 is not exactly stock at highway"
    print("     ⇒ V67/V68 differs from the highway-CLEAN builds in BOTH lanes: r26 cut ~5x AND r24")
    print("       RAISED 2.44x (a scalar arm does not follow the LERP's speed rolloff, so arm/LERP")
    print("       PEAKS at highway). V71C removes ONLY the r26 cut and KEEPS r24's rise byte for")
    print("       byte. 🛑 IF THE HIGHWAY SYMPTOM CAME FROM r24, V71C WILL NOT FIX IT. Score highway")
    print("       grind #2 as the primary readout. Follow-up lever if it returns: 0xC6446 5244 -> "
          "~2151-2400.")

    # ---- THE SAFETY CLAIM: byte-identity to V67 except 0xC6444 -----------------------------------
    print("\n  ★ THE SAFETY CLAIM -- byte-identity to V67, which flew twice flight-clean:")
    for lo, hi, what in V67_IDENTICAL_SPANS:
        d = [i for i in range(lo, hi) if code[i] != v67[i]]
        assert not d, f"[0x{lo:05X},0x{hi:05X}) differs from V67 at {[hex(x) for x in d[:8]]}"
        print(f"    ✅ [0x{lo:05X},0x{hi:05X}) byte-identical to V67 -- {what}")
    # ⚠ 512 = 0x0200 and 3072 = 0x0C00 share a ZERO low byte, so only 0xC6445 actually moves. Assert
    # the changed set is a SUBSET of the halfword AND that the halfword's VALUE is right -- a byte
    # count alone would be both wrong and weaker. (Same trap V42's note recorded: ten of its 36 r26
    # bytes were already 0x00, so the byte count did not match the halfword count.)
    dcal = [i for i in range(*CAL_BLOCK) if code[i] != v67[i]]
    assert set(dcal) <= {R26_ARM, R26_ARM + 1}, \
        f"the cal block differs from V67 at {[hex(x) for x in dcal]}, expected a subset of " \
        f"0x{R26_ARM:05X}/0x{R26_ARM + 1:05X}"
    assert u16(code, R26_ARM) == R26_ARM_NEW and u16(v67, R26_ARM) == R26_ARM_STOCK, \
        "the r26 arm halfword is not 3072 here / 512 on V67"
    print(f"    ✅ [0x{CAL_BLOCK[0]:05X},0x{CAL_BLOCK[1]:05X}) differs from V67 at "
          f"{[hex(x) for x in dcal]} ONLY -- the r26 arm halfword 0x{R26_ARM:05X}, "
          f"{R26_ARM_STOCK} -> {R26_ARM_NEW}. Nothing else in the whole calibration block moved.")
    print("       (only the HIGH byte differs: 512 = 0x0200 and 3072 = 0x0C00 share a zero low byte)")

    # ---- CRC --------------------------------------------------------------------------------------
    touched = [CAVE_BASE, A.RATCHET_ADDR, GATE_ADDR, R24_ARM, R26_ARM, A.SURFACE[0][0], A.SURFACE[-1][0]]
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    assert [b[1] for b in blocks] == [0xC4FFC, 0xC6FFC, 0xD2FFC], \
        f"expected the MAIN, CAL and 0xD2000 trailers, got {[hex(b[1]) for b in blocks]}"
    print(f"\n  CRC -- EXACTLY {len(blocks)} blocks move (asserted, not observed):")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")
    assert struct.unpack_from("<I", code, 0xD2FFC)[0] == struct.unpack_from("<I", v67, 0xD2FFC)[0], \
        "the 0xD2000-block CRC does not match V67's -- the surface revert is incomplete"

    # ---- the attributed diff -----------------------------------------------------------------------
    cave_range = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    surf_bytes = {a + k for a, _, _, _ in A.SURFACE for k in (0, 1)}
    cal_bytes = {R24_ARM, R24_ARM + 1, R26_ARM, R26_ARM + 1}
    code_bytes = {A.RATCHET_ADDR, GATE_ADDR}
    d70 = [i for i in range(START, END) if code[i] != v70[i]]
    f70 = [d for d in d70 if d not in crc_only]
    stray = [d for d in f70 if d not in cave_range | surf_bytes | cal_bytes | code_bytes]
    assert not stray, f"UNATTRIBUTED functional bytes vs V70: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V70: {len(d70)} bytes = {len(f70)} functional + {len(d70) - len(f70)} CRC")
    for d in sorted(f70):
        where = ("EDIT 4 cave" if d in cave_range else
                 "EDIT 3 gain_B surface (x2 -> STOCK)" if d in surf_bytes else
                 "EDIT 2 gate 0x3AA96" if d == GATE_ADDR else
                 "EDIT 2 r24 arm 0xC6446" if d in (R24_ARM, R24_ARM + 1) else
                 "EDIT 2 r26 arm 0xC6444  ★ THE NEW LEVER" if d in (R26_ARM, R26_ARM + 1) else
                 "EDIT 1 ratchet 0x454FE")
        print(f"    0x{d:05X}  {v70[d]:02X} -> {code[d]:02X}   {where}")
    d67 = [i for i in range(START, END) if code[i] != v67[i]]
    f67 = [i for i in d67 if i not in crc_only]
    assert set(f67) <= cave_range | {A.RATCHET_ADDR, R26_ARM, R26_ARM + 1}, \
        f"V71C differs from V67 outside the cave, 0x454FE and 0xC6444: " \
        f"{sorted(hex(x) for x in set(f67) - cave_range - {A.RATCHET_ADDR, R26_ARM, R26_ARM + 1})}"
    print(f"\n  ✅✅ EXACT DIFF vs V67: {len(d67)} bytes = the 68-byte cave + 0x{A.RATCHET_ADDR:05X} + "
          f"0x{R26_ARM:05X} + {len(d67) - len(f67)} CRC bytes, AND NOTHING ELSE.")
    print("      ⇒ V71C IS V67's FLOWN CONTROL PATH + V42's FLOWN RATCHET BYTE + ONE CAL HALFWORD.")
    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    print(f"  EXACT DIFF vs STOCK: {len(d_stock)} bytes -- run `python verify/diff_build_vs_stock.py v71c`")

    # ---- write + readback --------------------------------------------------------------------------
    if existing is not None and existing != bytes(code):
        raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V71C output")
    back = parse_x31(rwd)
    dec = bytearray(v70)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    A.assert_ratchet_edit(dec, "V71C readback", expect_edited=True)
    A.assert_sar_sites(dec, "V71C readback", expect_doubled=False)
    A.assert_governor_monitor_safety(dec, "V71C readback")
    assert_control_path(dec, "V71C readback", engaged_topology=True)
    B.assert_gain_a(dec, "V71C readback", doubled=False)
    A.assert_probe_census(bytes(dec), cave_span, MIRROR)
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    for base in A.REC_Y_STOCK:
        assert bytes(dec[base:base + 0x14]) == bytes(stock[base:base + 0x14])
    for lo, hi, _w in V67_IDENTICAL_SPANS:
        assert bytes(dec[lo:hi]) == bytes(v67[lo:hi]), "readback lost the V67 identity"
    V55.assert_variant_tables(dec)
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    print("\n  READBACK -- payload, the ratchet byte, both stock `sar` sites, the (gate, r24, r26)")
    print("     triple and both invariant directions, every gain_A and gain_B record == STOCK, the")
    print("     whole cave, the probe census, the V67 span identity and the full CRC chain: all")
    print("     re-verified ON THE DECODED READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V71C BUILT. V67/V68's flown control path with the ~6x r26 CUT REMOVED, plus the ratchet")
    print("  byte. Manual steering is byte-for-byte STOCK; engaged, r24 gets V67/V68's arm and r26")
    print("  returns to ~stock magnitude. NO INT32 headroom lost.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
