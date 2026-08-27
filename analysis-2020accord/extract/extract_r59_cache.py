#!/usr/bin/env python3
"""Extract route `59` (**V72**, segments 0-14) to .npz caches. THE CANONICAL ROUTE-59 EXTRACTOR.

Route `75604b0a432fdc89_00000059--9070b9dcee`, segments 0..14 -- 15 segments. This is the **V72 test
drive**, and V72's probe is the first one in this kit that measures `a` (gp-0x69a4), the weight that
sets r26's magnitude relative to r24 and that has made every "r24 vs r26" number conditional for
about ten builds.

🛑 ONE ROUTE, ONE EXTRACTOR. Two agents once wrote `extract/extract_r4f_cache.py` and `r4f_extract_cache.py`
in the same session, both writing `_scratch/cache/r4f/r4fs*.npz` with DIFFERENT field sets, and whichever
ran last silently dropped the other's channels. If you need a variant, add a flag, not a file.

Every non-probe channel is byte-for-byte `extract/extract_r58_cache.py`'s (and therefore
`extract/extract_r50_cache.py`'s), so `_grind2_lib.wrecs`, `_r31_common.load` and `_r4f_lib.avg_periodogram`
read this cache with the identical instrument they read every prior route with. The ONE substantive
change is the byte4 decoder, which is BUILD-SPECIFIC and here carries **V72's**.

THE BUILD ON THIS ROUTE
-----------------------
    39990-TVA,A160-V72-A-WHOLEAXIS-r24_5244-r26_512-V67CREEP-hwy1x-B-FactorCE-430_927-C-63A0x2-
    454FE-probe-a512-a1024-damp-rate512-0x13000-0x100000.rwd

  LEVER A  both rate lanes dosed across the WHOLE rate axis at the 0 and 10 km/h records (gain_B
           mode-10 rec0/rec1 Y[0..3] -> 5244 for r24, gain_A rec0/rec1 -> 512 for r26). The
           50/100 km/h records are BYTE-STOCK ⇒ highway is EXACTLY 1.000000x by record geometry.
  LEVER B  the base-assist damper opened at creep -- FactorC 0xD27C6/C8 -> 430, 0xD27DA/DC -> 431;
           FactorE 0xD2802/04/06 and 0xD2816/18/1A -> 927. **Stock has NO base-assist damping below
           35 km/h at all**, which is exactly where the ratchet and both grinds live.
  LEVER C  0xC63A0 1024 -> 2048, the weight on gp-0x6bd0 into FUN_00038148.
  CARRIED  0x454FE = 0xB5. 🛑 CARRIED, CURRENTLY INERT, UNTESTED -- V71's bit5 measured
           `gp-0x67fa == 4` at 0/123,277 (route 54) and 8/92,826 (route 58, all eight in park), so
           V42's substitution never ran. NOT a fix and NOT falsified; do not score the ratchet on it.
🛑 **V72 IS UNGATED** (`0x3AA96` = 0xC5, the dead cell) ⇒ the rate-lane dose applies in MANUAL
steering below ~30 km/h too, unlike V67/V68/V71C. `cc_lat` still splits engagement, but on THIS
route the manual arm is **NOT a stock control** -- it is dosed. Score it separately and say so.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
----------------------------------------
    bit7 = 1                     LIVENESS. field == 0 ⇒ the cave did not fire ⇒ the frame is VOID.
    bit6 = gp-0x69a4 >= 512      ★★★★ `a`, THE UNMEASURED WEIGHT. 512 = 0.5 in the Q10 reading.
    bit5 = gp-0x69a4 >= 1024     ★★★ the second thermometer step (a >= 1.0).
    bit4 = |gp-0x6bd0| >= 64     IS LEVER B (the base damper) IN FORCE? TWO-SIDED -- the damper is
                                 velocity-OPPOSING (0x3469e negates on gp-0x6abe > 0) so it
                                 alternates sign every half cycle and a one-sided rung would halve
                                 the count for nothing.
                                 ★ IT CARRIES ITS OWN POSITIVE CONTROL: above 35 km/h stock ALREADY
                                 damps, so **a rung silent at highway is BROKEN, not null.**
    bit3 = gp-0x6ac0 >= 512      📋 PRE-REGISTERED at 2.750% engaged duty (9,497 / 345,396 prior
                                 frames); must fire frame-for-frame with bus |rate_c| >= 108.7 deg/s
                                 (512 counts / 4.7121 counts-per-deg-s).
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved.

⚠ SIGNEDNESS, because bit6 and bit3 branch on a shift's Z flag rather than on a `cmp`, and that
looks like it could be fooled by a negative value. IT CANNOT BE, and the reason is the LOAD:

    +0x04  e4375d96  ld.hu -0x69a4[gp],r6   opcode 0x3F  ZERO-extends   (`a`)
    +0x14  24373094  ld.h  -0x6bd0[gp],r6   opcode 0x39  SIGN-extends   (damper -- the ONLY one)
    +0x24  e4374195  ld.hu -0x6ac0[gp],r6   opcode 0x3F  ZERO-extends   (rate)

[EVIDENCE, GhidraMCP `disassemble_bytes` on the analysed image: 0x3AB3A `e4375d96` decodes as
`ld.hu -0x69a4,gp,r6` -- the aggregator's OWN read of `a`, byte-identical to the cave's -- and
0x34730 `64373094` as `st.h r6,-0x6bd0,gp`, the one-bit store twin the cave must not be.]
⇒ r6 is in [0, 65535] for bit6/bit5/bit3, so `sar` == `shr` and bit6 is `raw16 >= 512` as an
UNSIGNED test. IF `a` were semantically a signed int16 and NEGATIVE, its raw pattern would be
>= 0x8000 = 32768, hence >= 1024, and **bit5 would fire**. bit5 read 0 in 87,940 / 87,940 frames on
route 59 ⇒ `raw16 < 1024` in every frame ⇒ **no frame carried a negative value, measured rather than
assumed**, and the `a` bracket holds under either signed or unsigned reading.

🛑 **`bit5 => bit6` IS A MONOTONE INVARIANT ON V72**, structurally guaranteed: both rungs come from
ONE `sar 0x9` (`a >= 512` is `s != 0`, `a >= 1024` is `s >= 2`). Only **12 of the 16** payloads are
legal, and a frame with bit5 SET and bit6 CLEAR **proves the artefact is not V72**. This cache
therefore CARRIES an `order_viol` channel -- unlike route 54/58's, whose four V71 rungs were
INDEPENDENT and where a zeroed channel would have asserted an invariant that build does not hold.
⚠ The invariant is ONE-WAY: a violation falsifies V72, holding does not prove it. The .rwd FILENAME
remains the pre-drive discriminator.

⚠ bit4's ONE-COUNT ASYMMETRY, because it is real and must not be glossed:

        bit4  =  (gp-0x6bd0 >= +64)  OR  (gp-0x6bd0 <= -65)

`sar` FLOORS, so `x sar 6 == -1` spans x in [-64,-1] and no single shifted compare can split x = -64
from x = -63. The negative arm therefore trips at -65: that is |x| >= 64 for every value EXCEPT
x == -64 exactly. `_self_check()` below proves it exhaustively over all 65,536 halfword patterns
rather than asserting it in prose.

🛑 THERE IS NO SINGLE "MIRROR CELL" ON THIS BUILD -- the five rungs read THREE different cells
(gp-0x69a4, gp-0x6bd0, gp-0x6ac0). So this cache writes `probe_cells`/`probe_rungs`, and deliberately
does NOT write route 50/54/58's scalar `probe_cell`/`probe_lane`: a generic script that reached for
a scalar would get an answer that is wrong for four of the five rungs. `_assert_cave_bytes()` below
re-reads CAVE_HEX out of `rlog-tools/probe/decode_v72_probe.py` at import time and fails this extractor if
any load displacement, condition nibble or `sar`->`be` adjacency drifts -- including the ld.h/st.h
one-bit trap at offset 20, where the firmware's own `st.h r6,-0x6bd0[gp]` @0x34730 is `64373094`
against our `24373094`.

🛑 AND THERE IS NO `g6806` BIT even though engagement matters on this route -- all five rungs are
spent elsewhere. `g6806` is NaN here and `wrecs` falls back to `cc_lat`, the kit's standing
engagement convention (V67 measured them agreeing 99.983%).

RPM (0x17C bytes 2:3, big-endian, src 1) is pulled in the SAME pass -- the engine-order veto needs
it and a second walk over 15 x ~11 MB segments is pure cost.

★ SAMPLE RATE comes from `_r4f_lib.fs_lattice`, never `1/median(dt)`. CAN frames are timestamped per
LOG PACKET, so several share a timestamp and the legacy estimator is biased HIGH by a
ROUTE-DEPENDENT ~1.3% -- three quarters of a bin at 21 Hz.

Usage:  python extract/extract_r59_cache.py            # all 15 segments
        python extract/extract_r59_cache.py 0 1        # chosen segments
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

# 🛑 WINDOWS REDIRECT FIX -- cp1252 raises UnicodeEncodeError on the first 🛑/★/⚠ glyph, so the
# header below crashes the run before a single segment is written. Same guard decode_v72_probe uses.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages          # noqa: E402
from _r4f_lib import fs_lattice, install_fs   # noqa: E402  -- the ONE owner of the fs estimator

install_fs()

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000059--9070b9dcee"
SEGS = list(range(15))
OUT = Path(os.environ.get("R59_CACHE", ROOT / "_scratch/cache/r59"))
PFX = "r59s"

BUILD = "V72"
# 🛑 ONE LINE, and asserted below to equal `decode_v72_probe.RWD_NAME` read out of that file's
# source. The filename is the pre-drive build discriminator, so a drifted copy here is not cosmetic.
RWD_NAME = "39990-TVA,A160-V72-A-WHOLEAXIS-r24_5244-r26_512-V67CREEP-hwy1x-B-FactorCE-430_927-C-63A0x2-454FE-probe-a512-a1024-damp-rate512-0x13000-0x100000.rwd"  # noqa: E501

# The three cells the five rungs read, in bit order. NOT a scalar -- see the docstring.
A_DISP, DAMP_DISP, RATE_DISP = 0x69A4, 0x6BD0, 0x6AC0
PROBE_CELLS = (A_DISP, A_DISP, DAMP_DISP, RATE_DISP)
PROBE_RUNGS = ("bit6 gp-0x69a4>=512 `a`", "bit5 gp-0x69a4>=1024 `a`",
               "bit4 |gp-0x6bd0|>=64 damper", "bit3 gp-0x6ac0>=512 rate")

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

BIT_LIVE = 0x80
BIT_A512 = 0x40               # bit6  gp-0x69a4 >= 512    ★★★★ `a`, THE UNMEASURED WEIGHT
BIT_A1024 = 0x20              # bit5  gp-0x69a4 >= 1024   ★ bit5 => bit6, MONOTONE
BIT_DAMPABS = 0x10            # bit4  |gp-0x6bd0| >= 64, TWO-SIDED -- IS LEVER B IN FORCE?
BIT_RATE512 = 0x08            # bit3  gp-0x6ac0 >= 512    📋 PRE-REGISTERED at 2.750% engaged
PROBE_MASK = 0xF8

A_THRESHOLD = 512             # bit6: ld.hu -> sar 0x9 -> be   (branches on the sar's own Z flag)
A2_THRESHOLD = 1024           # bit5: cmp 0x2 -> blt
D_THRESHOLD = 64              # bit4: ld.h  -> sar 0x6 -> cmp 0x1 / cmp -0x1
D_NEG_THRESHOLD = -65         # ⚠ `sar` FLOORS, so the NEGATIVE arm trips at -65, not -64.
R_THRESHOLD = 512             # bit3: ld.hu -> sar 0x9 -> be

RATE_SCALE_CTS_PER_DEGS = 4.7121          # the settled column-rate scale, three independent ways
RATE_DEGS = R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS         # 108.66 deg/s
PREREG_BIT3_DUTY = 2.750                  # 📋 percent engaged, 9,497 / 345,396 frames
FACTORC_ONSET_KMH = 35.0                  # below this, STOCK base-assist damping is a HARD ZERO

# ★ bit5 => bit6 is STRUCTURAL, so 4 of the 16 payloads are FORBIDDEN. This is the one real
# difference from route 54/58's LEGAL_FIELD, and it is why `order_viol` exists in this cache.
LEGAL_FIELD = {BIT_LIVE | a | b | c
               for a in (0, BIT_A512, BIT_A512 | BIT_A1024)
               for b in (0, BIT_DAMPABS) for c in (0, BIT_RATE512)}
assert len(LEGAL_FIELD) == 12, "bit5 => bit6 must forbid exactly 4 of the 16 payloads"
assert not any((b & BIT_A1024) and not (b & BIT_A512) for b in LEGAL_FIELD)
assert BIT_LIVE | BIT_A512 | BIT_A1024 | BIT_DAMPABS | BIT_RATE512 == PROBE_MASK
assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"


def _s16(raw):
    return raw - 0x10000 if raw & 0x8000 else raw


def wire_byte4(v69a4, v6bd0, v6ac0, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order.

    Ported VERBATIM from `rlog-tools/probe/decode_v72_probe.py`. 0xC4B34 movea 0x10,r0,r7 /
    ld.hu -0x69a4[gp],r6 / sar 0x9 / be ...
    """
    r7 = 0x10                                       # movea 0x10,r0,r7
    s = (v69a4 & 0xFFFF) >> 9                       # ld.hu ; sar 0x9   (SETS Z)
    if s != 0:                                      # be +4  <- reads the sar's own Z flag
        r7 += 0x08
    if not (s < 2):                                 # cmp 0x2,r6 ; blt +4
        r7 += 0x04
    d = _s16(v6bd0 & 0xFFFF) >> 6                   # ld.h ; sar 0x6  (Python >> floors == `sar`)
    if (d >= 1) or not (d >= -1):                   # cmp 0x1 ; bge SET ; cmp -0x1 ; bge SKIP ; SET
        r7 += 0x02
    q = (v6ac0 & 0xFFFF) >> 9                       # ld.hu ; sar 0x9  (SETS Z)
    if q != 0:                                      # be +4
        r7 += 0x01
    return ((r7 << 3) & 0xFF) | (status_bits & 0x07)


def _assert_cave_bytes():
    """🛑 THE MECHANICAL LINK TO THE IMAGE, retargeted at V72's own decoder.

    Re-read `CAVE_HEX` out of `rlog-tools/probe/decode_v72_probe.py` (by REGEX, not by import, so this
    does not drag in that file's import chain) and fail this extractor if any load displacement,
    condition nibble or `sar`->`be` adjacency has drifted. If this ever fires, the cache would have
    been labelled with the wrong cells -- which is the exact defect that ran for four builds.
    """
    src = (ROOT / "rlog-tools" / "probe/decode_v72_probe.py").read_text(encoding="utf-8")
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', src, re.M)
    assert m, "CAVE_HEX not found in probe/decode_v72_probe.py -- cannot verify the probe cells"
    raw = bytes.fromhex(m.group(1))
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, expected the 68-byte cave"
    assert raw[0:4] == bytes.fromhex("203e1000"), "offset 0 is not `movea 0x10,r0,r7`"
    assert raw.hex().endswith("2436e8ea7f00"), "the cave does not end in the displaced movea + jmp"
    # ---- the three loads, by displacement AND by opcode field ------------------------------------
    # ⚠ THE OPCODE FIELD IS THE SIGNEDNESS, and the signedness is load-bearing on bit6 (see the
    # module docstring): 0x3F = `ld.hu` ZERO-extends, 0x39 = `ld.h` SIGN-extends. Only the damper
    # load is signed. Asserted here so a silent swap cannot turn bit6 into a two-sided rung.
    for off, hw1, disp, kind, opc, what in (
            (4, "e437", A_DISP, "odd", 0x3F, "ld.hu `a` gp-0x69a4"),
            (20, "2437", DAMP_DISP, "even", 0x39, "ld.h damper gp-0x6bd0"),
            (36, "e437", RATE_DISP, "odd", 0x3F, "ld.hu rate gp-0x6ac0")):
        assert raw[off:off + 2] == bytes.fromhex(hw1), \
            f"CAVE_HEX offset {off} is not `{what},r6` -- a 0x44../0x64.. hw1 would be a STORE"
        got = (int.from_bytes(raw[off:off + 2], "little") >> 5) & 0x3F
        assert got == opc, \
            f"CAVE_HEX offset {off} has opcode 0x{got:02X}, expected 0x{opc:02X} ({what}) -- " \
            f"0x3F is ld.hu (zero-extends) and 0x39 is ld.h (sign-extends); swapping them changes " \
            f"what the rung MEANS, not just what it reads"
        want = (0x10000 - disp) & 0xFFFF
        want = (want & 0xFFFE) | 1 if kind == "odd" else (want & 0xFFFE)
        assert raw[off + 2:off + 4] == want.to_bytes(2, "little"), \
            f"CAVE_HEX offset {off} does not carry the displacement -0x{disp:04x} -- this cache " \
            f"would be labelled with the wrong cell"
    # 🛑🛑 THE ld.h / st.h ONE-BIT TRAP. gp-0x6bd0 has FIVE real readers incl. the 1 kHz aggregator,
    # so a slipped bit would WRITE a live lane, not corrupt a cell nobody reads.
    assert raw[20:24] != bytes.fromhex("64373094"), \
        "the damper load IS the real `st.h r6,-0x6bd0[gp]` @0x34730 -- the cave WRITES. NOT V72."
    _hw1 = int.from_bytes(raw[20:22], "little")
    assert (_hw1 >> 5) & 0x3F == 0x39, \
        f"the damper load's opcode field is 0x{(_hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h)"
    # ---- every condition nibble, BY VALUE. One nibble INVERTS a rung silently. --------------------
    for off, want, what in ((8, "a932", "sar 0x9,r6  (bit6/bit5, SETS Z)"),
                            (10, "a205", "be +4       (bit6, reads the sar's Z)"),
                            (12, "483a", "add 0x8,r7  (bit6 setter)"),
                            (14, "6232", "cmp 0x2,r6  (bit5)"),
                            (16, "a605", "blt +4      (bit5)"),
                            (18, "443a", "add 0x4,r7  (bit5 setter)"),
                            (24, "a632", "sar 0x6,r6  (bit4)"),
                            (26, "6132", "cmp 0x1,r6  (bit4 POSITIVE bound)"),
                            (28, "be05", "bge +6      (bit4 POSITIVE bound)"),
                            (30, "7f32", "cmp -0x1,r6 (bit4 NEGATIVE bound)"),
                            (32, "ae05", "bge +4      (bit4 NEGATIVE bound)"),
                            (34, "423a", "add 0x2,r7  (bit4 setter)"),
                            (40, "a932", "sar 0x9,r6  (bit3, SETS Z)"),
                            (42, "a205", "be +4       (bit3)"),
                            (44, "413a", "add 0x1,r7  (bit3 setter)"),
                            (46, "c33a", "shl 0x3,r7")):
        assert raw[off:off + 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what}) -- a wrong nibble INVERTS the rung"
    # 🛑 FLAG LIVENESS: each `sar 0x9` must be IMMEDIATELY followed by its `be`, or the branch reads
    # the PREVIOUS comparison's flags and the rung is meaningless.
    for sar_off in (8, 40):
        assert raw[sar_off + 2:sar_off + 4] == bytes.fromhex("a205"), \
            f"the `sar` at offset {sar_off} is not immediately followed by its `be` -- STALE flags"
    # 🛑 EXACTLY ONE STORE, and it is the byte4 write-back.
    assert raw[58:62] == bytes.fromhex("4437ecea"), \
        "offset 58 is not `st.b r6,-0x1514[gp]` -- the sole store moved"
    # ---- and the .rwd name, so this cache cannot be labelled with a different artefact ------------
    mn = re.search(r'^RWD_NAME\s*=\s*"([^"]+)"', src, re.M)
    assert mn, "RWD_NAME not found in probe/decode_v72_probe.py"
    assert mn.group(1) == RWD_NAME, \
        f"RWD_NAME drifted from the decoder's:\n  here   {RWD_NAME}\n  decoder {mn.group(1)}"


def _self_check():
    """The payload claims as executable assertions, including the one-count asymmetry."""
    assert wire_byte4(0, 0, 0) & PROBE_MASK == BIT_LIVE, "an all-zero input is not bare liveness"
    assert wire_byte4(512, 0, 0) & BIT_A512 and not wire_byte4(511, 0, 0) & BIT_A512
    assert wire_byte4(1024, 0, 0) & BIT_A1024 and not wire_byte4(1023, 0, 0) & BIT_A1024
    # ---- the VECTORISED decode this file actually uses, against the instruction model, over ALL
    # ---- 65,536 halfword patterns. Two independent methods, which is what the kit requires.
    r = np.arange(0x10000, dtype=np.int32)
    vec_a512 = r >= A_THRESHOLD
    vec_a1024 = r >= A2_THRESHOLD
    ref_a = np.array([wire_byte4(int(v), 0, 0) for v in r], dtype=np.int32)
    assert np.array_equal(vec_a512, (ref_a & BIT_A512) != 0), "the vectorised bit6 differs"
    assert np.array_equal(vec_a1024, (ref_a & BIT_A1024) != 0), "the vectorised bit5 differs"
    assert not (vec_a1024 & ~vec_a512).any(), "bit5 => bit6 is violated by the decode itself"
    x = np.where(r & 0x8000, r - 0x10000, r).astype(np.int32)
    s = x >> 6                                      # numpy `>>` on signed ints IS arithmetic
    vec_damp = (s >= 1) | (s < -1)
    ref_d = np.array([wire_byte4(0, int(v), 0) for v in r], dtype=np.int32)
    assert np.array_equal(vec_damp, (ref_d & BIT_DAMPABS) != 0), "the vectorised bit4 differs"
    assert np.array_equal(vec_damp, (x >= D_THRESHOLD) | (x <= D_NEG_THRESHOLD))
    mismatch = set(x[vec_damp != (np.abs(x) >= D_THRESHOLD)].tolist())
    assert mismatch == {-D_THRESHOLD}, \
        f"bit4 differs from |x| >= {D_THRESHOLD} at {sorted(mismatch)[:6]}, expected exactly " \
        f"{{{-D_THRESHOLD}}} -- `sar` floors and that is the ONLY value it can miss"
    assert wire_byte4(0, 0xFF00, 0) & BIT_DAMPABS, "bit4 does not fire at x = -256: NOT two-sided"
    vec_rate = r >= R_THRESHOLD
    ref_r = np.array([wire_byte4(0, 0, int(v)) for v in r], dtype=np.int32)
    assert np.array_equal(vec_rate, (ref_r & BIT_RATE512) != 0), "the vectorised bit3 differs"
    assert abs(RATE_DEGS - 108.7) < 0.1, "512 counts is not the pre-registered 108.7 deg/s"
    for status in range(8):
        assert wire_byte4(0xFFFF, 0x7FFF, 0xFFFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
        assert wire_byte4(0, 0, 0, status) == 0x80 | status
    # every payload the model can emit must be in LEGAL_FIELD, and all 12 must be reachable
    emitted = {wire_byte4(a, d, q) & PROBE_MASK
               for a in (0, 512, 1024) for d in (0, 100) for q in (0, 512)}
    assert emitted == LEGAL_FIELD, f"the model emits {len(emitted)} payloads, LEGAL_FIELD has 12"


_assert_cave_bytes()
_self_check()


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def held_last(t_out, t_in, v_in, fill):
    """Zero-order hold. For CATEGORICAL channels; np.interp would fabricate intermediate codes."""
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in), t_out, side="right") - 1
    out = np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)])
    return out.astype(float)


def extract(paths, tag, t0=None):
    rows, e4hist, events = [], [], []
    last18, lastE4 = None, (0.0, 0)
    raw = {0x14A: [], 0x18F: [], 0x1FA: [], 0x0E4: []}
    # 🛑 INDEPENDENT SECOND METHOD for the STEER_STATUS census and the byte4 histogram: every
    # 0x18F / 0x14A src-1 frame exactly as it arrived, no hold, no grid.
    raw18_st, raw14_b4 = [], []
    rpm_t, rpm_v = [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    clk = {"t": [], "w": []}
    init_wall = []
    snd = {"t": [], "sp": [], "spw": []}

    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    src, addr = int(m.src), int(m.address)
                    d = bytes(m.dat)
                    if src == 1 and addr in raw:
                        raw[addr].append(tm)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x17C and len(d) >= 4:
                        rpm_t.append(tm)
                        rpm_v.append((d[2] << 8) | d[3])
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                for k, attr in (("press", "steeringPressed"), ("std", "standstill"),
                                ("lblink", "leftBlinker"), ("rblink", "rightBlinker")):
                    try:
                        cs[k].append(float(bool(getattr(c, attr))))
                    except Exception:
                        cs[k].append(0.0)
                try:
                    cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
                except Exception:
                    cs["gear"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                try:
                    cc["req"].append(float(evt.carControl.actuators.torque))
                except Exception:
                    cc["req"].append(np.nan)
            elif w == "soundPressure":
                try:
                    m = evt.soundPressure
                    snd["t"].append(tm)
                    snd["sp"].append(float(m.soundPressure))
                    snd["spw"].append(float(m.soundPressureWeighted))
                except Exception:
                    for k in ("t", "sp", "spw"):
                        if len(snd[k]) > min(len(snd[j]) for j in ("t", "sp", "spw")):
                            snd[k].pop()
            elif w == "clocks":
                try:
                    wn = int(evt.clocks.wallTimeNanos)
                except Exception:
                    continue
                if wn > 0:
                    clk["t"].append(tm); clk["w"].append(wn * 1e-9)
            elif w == "initData":
                try:
                    wn = int(evt.initData.wallTimeNanos)
                except Exception:
                    wn = 0
                if wn > 0:
                    init_wall.append((tm, wn * 1e-9))
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        nm = str(e.name)
                    except Exception:
                        continue
                    events.append((tm, nm,
                                   bool(getattr(e, "enable", False)),
                                   bool(getattr(e, "softDisable", False)),
                                   bool(getattr(e, "immediateDisable", False)),
                                   bool(getattr(e, "noEntry", False))))

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    if t0 is None:
        t0 = d["t"][0]
    d["t"] = d["t"] - t0
    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V72 probe decode ---------------------------------------------------------------------
    # ★★★★ bit6/bit5 are a TWO-STEP THERMOMETER on `a` = gp-0x69a4, the weight that has made every
    # r24-vs-r26 number in this kit conditional for about ten builds. bit4 asks whether LEVER B (the
    # base damper) is in force; bit3 is the pre-registered rate-axis positive control.
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & BIT_LIVE) != 0)
    a512 = ((p & BIT_A512) != 0)      # bit6  gp-0x69a4 >= 512    `a` >= 0.5 in Q10
    a1024 = ((p & BIT_A1024) != 0)    # bit5  gp-0x69a4 >= 1024   `a` >= 1.0 in Q10
    damp = ((p & BIT_DAMPABS) != 0)   # bit4  |gp-0x6bd0| >= 64, TWO-SIDED
    rate = ((p & BIT_RATE512) != 0)   # bit3  gp-0x6ac0 >= 512 counts = 108.7 deg/s
    d["live"] = live.astype(float)
    # SEMANTIC names -- what the rung MEANS on this build.
    d["b6_a512"] = a512.astype(float)
    d["b5_a1024"] = a1024.astype(float)
    d["b4_damp"] = damp.astype(float)
    d["b3_rate"] = rate.astype(float)
    # CELL-QUALIFIED aliases, matching the r50/r54/r58 caches' naming convention so a generic script
    # that reaches for a cell name finds the RIGHT cell and cannot silently read the wrong lane.
    # ⚠ bit6 and bit5 read the SAME cell at two thresholds, so both carry the 69a4 tag.
    d["b6_69a4"] = a512.astype(float)
    d["b5_69a4"] = a1024.astype(float)
    d["b4_6bd0"] = damp.astype(float)
    d["b3_6ac0"] = rate.astype(float)
    # ★ THE MONOTONE INVARIANT, as a channel. `bit5 => bit6` is structurally guaranteed on V72 (both
    # rungs come from ONE `sar 0x9`), so a NON-ZERO count here PROVES the flashed artefact is not
    # V72 and nothing else in this cache may be interpreted. 🛑 This is the deliberate difference
    # from `extract_r54/r58_cache.py`, whose V71 rungs were INDEPENDENT -- do not port their
    # "no order_viol channel" comment here.
    d["order_viol"] = (a1024 & ~a512).astype(float)
    # 🛑 NO `g6806` BIT: all five rungs are spent elsewhere. `cc_lat` is the engagement channel, and
    # on this UNGATED build it does NOT select the firmware's arms -- V72 doses both arms at creep.
    d["g6806"] = np.full(len(p), np.nan)
    b4ok = np.isin(p & PROBE_MASK, sorted(LEGAL_FIELD))
    d["illegal"] = (~live | ~b4ok).astype(float)

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    rawout = {f"raw{addr:03X}": (np.array(v, float) - t0) for addr, v in raw.items()}

    clk_mono = np.array(clk["t"], float) - t0
    clk_wall = np.array(clk["w"], float)
    if len(clk_wall) >= 2:
        off = float(np.median(clk_wall - clk_mono))
        off_sd = float(np.std(clk_wall - clk_mono, ddof=1))
    elif len(clk_wall) == 1:
        off, off_sd = float(clk_wall[0] - clk_mono[0]), np.nan
    else:
        off, off_sd = np.nan, np.nan
    iw = np.array(init_wall, float).reshape(-1, 2)
    if len(iw):
        iw[:, 0] -= t0
    n_snd = min(len(snd["t"]), len(snd["sp"]), len(snd["spw"]))
    snd_t = np.array(snd["t"][:n_snd], float) - t0

    # 🛑 RPM IS WRITTEN THREE WAYS ON PURPOSE, and the first one is load-bearing.
    #   `rpm`            gridded onto the 0x14A lattice -- what `_r4f_lib._add_rpm` and
    #                    `avg_periodogram` look for. If this is missing they silently return NaN
    #                    and every engine-order veto reads "unknown" instead of failing loudly.
    #   `rpm_t`/`rpm_v`  the raw 0x17C stream, un-gridded, for anything that needs true timing.
    #   `{tag}_rpm.npz`  a separate file, kept because `extract/extract_v68_rpm.py`'s convention reads it.
    rpm_ts = np.array(rpm_t, float) - t0
    rpm_vs = np.array(rpm_v, float)
    d["rpm"] = (np.interp(d["t"], rpm_ts, rpm_vs) if len(rpm_ts)
                else np.full(len(d["t"]), np.nan))
    np.savez_compressed(
        OUT / f"{tag}.npz", **d, e4hist=e4, **rawout,
        rpm_t=rpm_ts, rpm_v=rpm_vs,
        clk_mono=clk_mono, clk_wall=clk_wall, init_wall=iw,
        snd_t=snd_t, snd_sp=np.array(snd["sp"][:n_snd], float),
        snd_spw=np.array(snd["spw"][:n_snd], float),
        raw18_st=np.array(raw18_st, np.int16), raw14_b4=np.array(raw14_b4, np.int16),
        t0_mono=np.array([t0]), wall_t0=np.array([off]), wall_off_sd=np.array([off_sd]),
        # ★ PROVENANCE. 🛑 NO scalar `probe_cell`/`probe_lane` on this build -- the five rungs read
        # THREE cells, and a scalar would be wrong for four of them.
        probe_build=np.array([BUILD]), probe_cells=np.array(PROBE_CELLS),
        probe_rungs=np.array(PROBE_RUNGS), probe_rwd=np.array([RWD_NAME]))
    np.savez_compressed(OUT / f"{tag}_rpm.npz", t=rpm_ts, rpm=rpm_vs)
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    # ★ THE LATTICE ESTIMATOR, never 1/median(dt) -- see the module docstring.
    fs = fs_lattice(d)
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    void = int((d["field"] == 0).sum())
    import time as _time
    wstr = (_time.strftime("%H:%M:%S", _time.localtime(off)) if np.isfinite(off) else "??")
    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad_b4 = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & PROBE_MASK) not in LEGAL_FIELD}
    rp = np.array(rpm_v, float)
    rok = (rp > 400) & (rp < 7000)
    kmh = d["cs_v"] * 3.6
    lo, hi = kmh < FACTORC_ONSET_KMH, kmh >= FACTORC_ONSET_KMH
    dl = 100 * d["b4_damp"][lo].mean() if lo.any() else float("nan")
    dh = 100 * d["b4_damp"][hi].mean() if hi.any() else float("nan")
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.3f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** ILLEGAL {bad_b4}" if bad_b4 else "   (all legal)") + "\n"
          f"      VOID {void}  "
          f"bit6 a>=512 {100 * d['b6_a512'].mean():.4f}%  "
          f"bit5 a>=1024 {100 * d['b5_a1024'].mean():.4f}%  "
          f"bit4 |6bd0|>=64 {100 * d['b4_damp'].mean():.4f}% (lo {dl:.3f}% / hi {dh:.3f}%)  "
          f"bit3 rate>=512 {100 * d['b3_rate'].mean():.4f}%  "
          f"illegal {int(d['illegal'].sum())}  ORDERVIOL {int(d['order_viol'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"blinker {100 * (d['cs_lchg'] > 0.5).mean():.1f}%  "
          f"ST==4 {int((d['sstat'] == 4).sum())}  ST==3 {int((d['sstat'] == 3).sum())}  "
          f"mic {n_snd}  rpm {len(rp)}"
          + (f" ({np.percentile(rp[rok], 5):.0f}..{np.percentile(rp[rok], 95):.0f})"
             if rok.any() else "") +
          f"  gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    args = [int(x) for x in sys.argv[1:]] or SEGS
    print(f"ROUTE 59 = {BUILD}   rungs: " + " | ".join(PROBE_RUNGS) +
          f"\n  🛑 bit5 => bit6 MONOTONE: order_viol > 0 proves this is NOT V72"
          f"\n  rwd: {RWD_NAME}")
    for s in args:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{PFX}{s}")
