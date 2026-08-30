#!/usr/bin/env python3
"""Extract route `5a` (**V73**, segments 0-17) to .npz caches. THE CANONICAL ROUTE-5A EXTRACTOR.

Route `75604b0a432fdc89_0000005a--2d32bec040`, segments 0..17 -- 18 segments. This is the **V73 test
drive**, and V73's probe reads ONE byte: `gp+0x63FD`, the **base-assist damper's MODE SELECTOR** --
the byte every FactorB/C/D/E lookup in `FUN_00034350` indexes on (`mode * 4` into the pointer arrays
0xC9E9C / 0xC9F84), the byte the friction lane indexes on (`0x36c4a`), and the byte r24's gain_B
selector indexes on (`0x3ad88`). Every "mode 10" statement this kit has ever made is an INFERENCE
from the part number; the coded row lives in EEPROM, not in the flash image, and has never been read
back. **This drive reads it.**

🛑 ONE ROUTE, ONE EXTRACTOR. Two agents once wrote `extract/extract_r4f_cache.py` and `r4f_extract_cache.py`
in the same session, both writing `_scratch/cache/r4f/r4fs*.npz` with DIFFERENT field sets, and whichever
ran last silently dropped the other's channels. If you need a variant, add a flag, not a file.

Every non-probe channel is byte-for-byte `extract/extract_r59_cache.py`'s (and therefore
`extract/extract_r58_cache.py`'s and `extract/extract_r50_cache.py`'s), so `_grind2_lib.wrecs`, `_r31_common.load`
and `_r4f_lib.avg_periodogram` read this cache with the identical instrument they read every prior
route with. The ONE substantive change is the byte4 decoder, which is BUILD-SPECIFIC and here
carries **V73's**.

THE BUILD ON THIS ROUTE
-----------------------
    39990-TVA,A160-V73-V72BASE-frictionx1.5-C407E850-ratchet-modes0_5_12_14-Y0eqY1-probe-MODEBYTE-
    0x13000-0x100000.rwd

V73 = **V72, carried byte-identically** (LEVER A both rate lanes dosed across the whole rate axis at
the 0 and 10 km/h records UNGATED and exactly 1.000x at/above 50 km/h; LEVER B mode-10/11 FactorC/E;
LEVER C `0xC63A0` = 2048; the carried-but-inert `0x454FE`), plus:

  EDIT 1  GRIND #1, the friction lane. `0xD2A44` Y[0..2] x1.5 **paired with** the lane's own
          symmetric self-clamp `0xC407E` (tp+0x507e) 511 -> 850. 🛑 The RECORD is **MODE-INDEXED**
          (`0xCBE74[mode * 4]`, mode 10 -> `0xD2A44`); **`0xC407E` is NOT** -- a scalar tp cell read
          unconditionally, so **the clamp acts in EVERY mode**.
  EDIT 2  THE RATCHET, on modes **0, 1, 2, 3, 4, 5, 12, 14** (16 cells / 32 bytes): `Y[0] := that
          record's OWN Y[1]`, every address DERIVED from `0xC9E9C` / `0xC9F84` at `mode * 4`.
          🛑 **10 and 11 are EXCLUDED** -- V72 owns them, and V72's own bit4 null (0 / 87,940, incl.
          0 / 34,275 above 35 km/h, where the rung had to fire ~100%) excludes them decisively.
  EDIT 3  this probe.

🛑🛑 **THE TWO LEVERS ARE DISJOINT IN MODE, AND THIS PROBE SETTLES WHICH ACTED.** EDIT 1's LERP half
is mode-**10**-indexed; EDIT 2 covers 0-5, 12 and 14. **At most one can have acted on this drive.**

🛑 **THE DOSE IS NOT UNIFORM ACROSS FAMILIES.** Delivered `|gp-0x6bd0|` at creep, `(C*E)>>10` with
FactorB/D flat 1024: **modes 0-3 -> 106 counts · modes 4/5 -> 33 · modes 12/14 -> 31** -- a 3.4x
spread, because each family's own Y[1] is the value being lifted to. ⇒ **if this reads 4, 5, 12 or
14, a null result must NOT be scored as falsifying the lever** -- it is an UNDER-DOSE.

🛑 **V73 IS UNGATED, exactly as V72 was** (`0x3AA96` = 0xC5, the dead cell) ⇒ the rate-lane dose
applies in MANUAL steering below ~30 km/h too, unlike V67/V68/V71C. `cc_lat` still splits engagement,
but on THIS route the manual arm is **NOT a stock control** -- it is dosed. Score it separately.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
----------------------------------------
    bit7     = 1                                LIVENESS. field == 0 ⇒ the cave did not fire ⇒ VOID.
    bits 6:3 = (*(byte *)(gp + 0x63FD)) & 0xF   ★★★★ **THE MODE.**
    bits 2:0 = stock STEER_SENSOR_STATUS         preserved, untouched.

⚠ **THE 4-BIT FIELD ALIASES MOD 16.** Modes 16-33 exist in the ROM table but only on TVC/TWA chassis
rows. Every mode a `TVA*` or blank row can select is < 16, which the builder asserts against the
0xCD000 table on the image being built, so the field is **lossless for this car** -- but what is
written to `mode` below is `mode & 0xF`, and that is how it must be reported.

⚠ **WEAK BUILD IDENTITY, STATED UP FRONT.** All 16 payload values are legal here, so unlike V72
(whose `bit5 => bit6` invariant made 4 of 16 payloads structurally impossible) **the value set proves
only that SOME bit7-setting cave ran.** Two consequences this cache is built around:

  1. 🛑 **THERE IS NO `order_viol` ANALOGUE, AND A ZEROED CHANNEL WOULD BE A LIE.** `extract_r59`
     writes `order_viol` because V72's `bit5 => bit6` is structurally guaranteed; route 54/58's
     caches deliberately OMIT it because V71's four rungs were independent. V73 is the 54/58 case:
     no invariant exists. This cache therefore writes `order_viol` as **NaN**, not 0 -- the same
     convention `g6806` uses for "not measured on this build". A zero would assert an invariant V73
     does not hold, and `.sum()` on NaN fails loudly instead of silently reporting "no violations".
  2. 🛑 **THE 0x87 COLLISION.** On V73 `mode 0` transmits as **0x87** with all three status bits set
     -- the SAME byte V64's probe emitted, constant, for 14,980 frames when its detector never
     armed. A constant-0x87 stream is a legitimate V73 answer AND a known failure signature of a
     different build, and **the payload cannot tell them apart.** Filename + CAVE_HEX only.
  3. ⚠ **AN EARLIER V73 CUT EXISTS**, targeting modes 0/2 ONLY, renamed `SUPERSEDED-DO-NOT-FLASH-…`.
     Its cave is byte-identical to this one (the probe did not change between cuts), so **the stream
     cannot discriminate the two cuts either.** This is the recorded re-cut hazard; the `.rwd`
     FILENAME is the only pre-drive discriminator.

`_assert_cave_bytes()` below re-reads CAVE_HEX out of `rlog-tools/probe/decode_v73_probe.py` at import time
and fails this extractor if any load displacement, mask immediate or register field has drifted --
including the two one-bit traps that would silently void the measurement:
  · **`ld.bu` op 0x3D vs `st.b` op 0x3A** at offset 4. `0x63FD` is ODD, so ld.bu carries the
    displacement's own bit 0 IN THE OPCODE (0x3D, not the even form 0x3C). The firmware's own
    `st.b r8,0x63fd,gp` @0x426AE is `4447fd63` against our `a437fd63` -- one nibble, and the cave
    would REWRITE the selector byte every damper table, the friction lane and gain_B index on.
  · **`or r6,r7` (0639) vs `or r7,r6` (0731)** at offset 12. SAME opcode, register fields SWAPPED,
    both real instructions in this image. The wrong one ORs the mode into the SCRATCH register and
    **every frame reads "mode 0"** -- the exact false negative the probe exists to avoid, and one
    that would land on the 0x87 collision above.

🛑 THERE IS NO `g6806` BIT: the probe spends its whole field on the mode. `g6806` is NaN here and
`wrecs` falls back to `cc_lat`, the kit's standing engagement convention (V67 measured them agreeing
99.983%).

RPM (0x17C bytes 2:3, big-endian, src 1) is pulled in the SAME pass -- the engine-order veto needs
it and a second walk over 18 x ~11 MB segments is pure cost.

★ SAMPLE RATE comes from `_r4f_lib.fs_lattice`, never `1/median(dt)`. CAN frames are timestamped per
LOG PACKET, so several share a timestamp and the legacy estimator is biased HIGH by a
ROUTE-DEPENDENT ~1.3% -- three quarters of a bin at 21 Hz.

Usage:  python extract/extract_r5a_cache.py            # all 18 segments
        python extract/extract_r5a_cache.py 0 1        # chosen segments
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
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

# 🛑 WINDOWS REDIRECT FIX -- cp1252 raises UnicodeEncodeError on the first 🛑/★/⚠ glyph, so the
# header below crashes the run before a single segment is written. Same guard decode_v73_probe uses.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parents[1]
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages          # noqa: E402
from _r4f_lib import fs_lattice, install_fs   # noqa: E402  -- the ONE owner of the fs estimator

install_fs()

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_0000005a--2d32bec040"
SEGS = list(range(18))
OUT = Path(os.environ.get("R5A_CACHE", ROOT / "_scratch/cache/r5a"))
PFX = "r5as"

BUILD = "V73"
# 🛑 ONE LINE, and asserted below to equal `decode_v73_probe.RWD_NAME` read out of that file's
# source. The filename is the pre-drive build discriminator, so a drifted copy here is not cosmetic.
RWD_NAME = "39990-TVA,A160-V73-V72BASE-frictionx1.5-C407E850-ratchet-modes0_5_12_14-Y0eqY1-probe-MODEBYTE-0x13000-0x100000.rwd"  # noqa: E501

# ★ THE ONE CELL. A POSITIVE gp displacement -- gp+0x63FD, NOT gp-0x63FD. Unlike V72 (three cells
# across five rungs) V73 spends the whole field on ONE byte, so a scalar IS correct here and both
# the scalar and the array form are written for whichever convention a downstream script reaches for.
MODE_DISP = 0x63FD
PROBE_CELL = MODE_DISP
PROBE_LANE = "gp+0x63fd base-assist damper MODE SELECTOR"
PROBE_CELLS = (MODE_DISP,)
PROBE_RUNGS = ("bits6:3 (gp+0x63fd)&0xF MODE",)

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

BIT_LIVE = 0x80               # bit7  the cave ran
MODE_FIELD = 0x78             # bits 6:3  ★★★★ (gp+0x63FD) & 0xF
MODE_SHIFT = 3
MODE_MASK = 0xF
PROBE_MASK = 0xF8
STATUS_MASK = 0x07            # STEER_SENSOR_STATUS, preserved

FACTORC_ONSET_KMH = 35.0      # below this, mode-10/11 STOCK base-assist damping is a HARD ZERO
CREEP_MAX_MS = 4.0            # the ratchet and grind #1 are creep symptoms (1-4 m/s)

# Which modes EDIT 2 covers, which V72 owns, and which are reachable but uncovered.
RATCHET_MODES = (0, 1, 2, 3, 4, 5, 12, 14)
EXCLUDED_MODES = (10, 11)          # V72's LEVER B; EDIT 1's LERP is mode 10 ONLY
UNCOVERED_MODES = (13, 15)         # ⚠ TVAA7's e013/e015 arms -- NEITHER edit live
DOSE = {0: 106, 1: 106, 2: 106, 3: 106, 4: 33, 5: 33, 12: 31, 14: 31}   # counts at creep
SMALL_DOSE_MODES = (4, 5, 12, 14)  # 🛑 a null here is a SMALL DOSE, not a falsification

# 🛑 ALL 16 payloads are legal on V73 -- there is no `bit5 => bit6` analogue. This is NOT a copy of
# route 59's 12-value LEGAL_FIELD, and the difference is the whole reason `order_viol` is NaN here.
LEGAL_FIELD = {BIT_LIVE | (m << MODE_SHIFT) for m in range(MODE_MASK + 1)}
assert len(LEGAL_FIELD) == 16, "all 16 mode payloads must be legal on V73 -- no invariant exists"
assert all(b & BIT_LIVE for b in LEGAL_FIELD), "a legal payload has bit7 clear"
assert MODE_FIELD == MODE_MASK << MODE_SHIFT == 0x78, "the mode field is not bits 6:3"
assert BIT_LIVE | MODE_FIELD == PROBE_MASK
assert PROBE_MASK & STATUS_MASK == 0, "the probe bits collide with STEER_SENSOR_STATUS"

# 🛑 A COLLISION THIS KIT HAS ALREADY BEEN BITTEN BY -- see the module docstring, point 2.
V64_STUCK_VALUE = 0x87
assert (BIT_LIVE | (0 << MODE_SHIFT)) | STATUS_MASK == V64_STUCK_VALUE, \
    "V73 `mode 0` no longer transmits as 0x87 -- the documented V64 collision note is stale"


def wire_byte4(mode_byte, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order.

    Ported VERBATIM from `rlog-tools/probe/decode_v73_probe.py`. 0xC4B34 movea 0x10,r0,r7 /
    ld.bu 0x63fd[gp],r6 / andi 0xf / or r6,r7 / shl 0x3 / merge / st.b.
    """
    r7 = 0x10                                       # movea 0x10,r0,r7
    r6 = mode_byte & 0xFF                           # ld.bu 0x63fd[gp],r6  (a BYTE, zero-extended)
    r6 &= MODE_MASK                                 # andi  0xf,r6,r6
    r7 |= r6                                        # or    r6,r7   🛑 NOT `or r7,r6`
    return ((r7 << MODE_SHIFT) & 0xFF) | (status_bits & STATUS_MASK)


# The cave's REAL instruction boundaries, as (offset, length). Every byte-level check below is made
# on these rather than on "every even offset" -- a displacement halfword decoded as an opcode is how
# a store gets invented or missed.
BOUNDARIES = ((0, 4), (4, 4), (8, 4), (12, 2), (14, 2),              # seed + mode + mask + or + shl
              (16, 4), (20, 4), (24, 2), (26, 4), (30, 4), (34, 2))  # tail
PAD_OFF = 36


def _assert_cave_bytes():
    """🛑 THE MECHANICAL LINK TO THE IMAGE, retargeted at V73's own decoder.

    Re-read `CAVE_HEX` out of `rlog-tools/probe/decode_v73_probe.py` (by REGEX, not by import, so this
    does not drag in that file's import chain) and fail this extractor if any load displacement,
    mask immediate or register field has drifted. If this ever fires, the cache would have been
    labelled with the wrong cell -- which is the exact defect that ran for four builds.
    """
    src = (ROOT / "rlog-tools" / "probe/decode_v73_probe.py").read_text(encoding="utf-8")
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', src, re.M)
    assert m, "CAVE_HEX not found in probe/decode_v73_probe.py -- cannot verify the probe cell"
    raw = bytes.fromhex(m.group(1))
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, expected the proven 68-byte cave"
    assert sum(n for _o, n in BOUNDARIES) == PAD_OFF, "the boundary table does not tile the code"
    for prev, nxt in zip(BOUNDARIES, BOUNDARIES[1:]):
        assert prev[0] + prev[1] == nxt[0], f"the boundary table is not contiguous at {prev}"
    assert raw[PAD_OFF:] == bytes(68 - PAD_OFF), \
        "the bytes after `jmp [lp]` are not all 0x00 -- the padding claim is wrong"
    assert raw[0:4] == bytes.fromhex("203e1000"), "offset 0 is not `movea 0x10,r0,r7`"
    assert raw[34:36] == bytes.fromhex("7f00"), "offset 34 is not `jmp [lp]`"
    # ---- THE MODE LOAD, by displacement AND by opcode field --------------------------------------
    # 🛑🛑 ld.bu (ODD displacement) is op 0x3D; 0x3C is the EVEN form and 0x3A is st.b. The
    # firmware's own `st.b r8,0x63fd,gp` @0x426AE is `4447fd63` against our `a437fd63`.
    assert raw[4:8] == bytes.fromhex("a437fd63"), "offset 4 is not `ld.bu 0x63fd[gp],r6`"
    assert raw[4:8] != bytes.fromhex("4447fd63"), \
        "the mode load IS the real `st.b r8,0x63fd,gp` @0x426AE -- the cave would REWRITE the byte " \
        "that every damper factor table, the friction lane and r24's gain_B all index on. NOT V73."
    _hw1 = int.from_bytes(raw[4:6], "little")
    assert (_hw1 >> 5) & 0x3F == 0x3D, \
        f"the mode load's opcode field is 0x{(_hw1 >> 5) & 0x3F:02X}, MUST be 0x3D (ld.bu, ODD " \
        "displacement); 0x3C is the EVEN form and 0x3A is st.b -- this cache would be mislabelled"
    assert (_hw1 >> 11) == 6 and (_hw1 & 0x1F) == 4, "the mode load is not `... [gp],r6`"
    assert int.from_bytes(raw[6:8], "little") == (MODE_DISP & 0xFFFE) | 1 == 0x63FD, \
        f"the mode load does not carry the displacement +0x{MODE_DISP:04X} -- WRONG CELL"
    # ---- the field arithmetic, byte by byte ------------------------------------------------------
    for off, want, what in ((8, "c6360f00", "andi 0xf,r6,r6   -- the 4-bit mask"),
                            (12, "0639", "or r6,r7         -- mode INTO the payload"),
                            (14, "c33a", "shl 0x3,r7       -- field -> bits 7:3"),
                            (16, "8437edea", "ld.bu -0x1514[gp],r6"),
                            (20, "c6360700", "andi 0x7,r6,r6   -- keep the status bits"),
                            (24, "0731", "or r7,r6         -- the MERGE"),
                            (26, "4437ecea", "st.b r6,-0x1514[gp] -- THE ONLY STORE"),
                            (30, "2436e8ea", "movea -0x1518,gp,r6 -- the displaced instruction")):
        assert raw[off:off + len(want) // 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what}) -- the probe does not mean what we decode"
    # 🛑🛑 `or r6,r7` vs `or r7,r6`: SAME opcode, register fields SWAPPED, BOTH real in this image.
    # Decode the FIELDS -- a byte comparison alone is not a proof here.
    assert raw[12:14] != bytes.fromhex("0731"), \
        "offset 12 is `or r7,r6`, not `or r6,r7` -- the mode would be OR'd into the SCRATCH " \
        "register and EVERY frame would read mode 0, landing on the 0x87 collision. NOT V73."
    _or = int.from_bytes(raw[12:14], "little")
    assert (_or >> 5) & 0x3F == 0x08 and (_or >> 11) == 7 and (_or & 0x1F) == 6, \
        f"the accumulate's fields are wrong: op 0x{(_or >> 5) & 0x3F:02X}, dest r{_or >> 11}, " \
        f"src r{_or & 0x1F} -- must be op 0x08, dest r7, src r6"
    assert raw[8:12] != raw[20:24], "the 0xF and 0x7 masks collapsed -- the mode's top bit is lost"
    assert int.from_bytes(raw[10:12], "little") == MODE_MASK and \
        int.from_bytes(raw[22:24], "little") == STATUS_MASK, \
        "the two andi immediates are not 0xF (the mode) and 0x7 (the preserved status bits)"
    # 🛑 EXACTLY ONE STORE, on the REAL instruction boundaries. GATE 1 is vacuous only if this holds.
    stores = [o for o, n in BOUNDARIES
              if n >= 4 and ((int.from_bytes(raw[o:o + 2], "little") >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert stores == [26], f"the cave's store set is {stores}, expected exactly [26]"
    # ---- and the .rwd name, so this cache cannot be labelled with a different artefact ------------
    mn = re.search(r'^RWD_NAME\s*=\s*"([^"]+)"', src, re.M)
    assert mn, "RWD_NAME not found in probe/decode_v73_probe.py"
    assert mn.group(1) == RWD_NAME, \
        f"RWD_NAME drifted from the decoder's:\n  here    {RWD_NAME}\n  decoder {mn.group(1)}"


def _self_check():
    """The payload claims as executable assertions, over ALL 256 values the mode byte can hold."""
    assert wire_byte4(0, 0) & PROBE_MASK == BIT_LIVE, "an all-zero mode is not bare liveness"
    # ---- the rung, EXHAUSTIVELY -- and the VECTORISED decode this file actually uses, against the
    # ---- instruction model. Two independent methods, which is what the kit requires.
    r = np.arange(256, dtype=np.int32)
    ref = np.array([wire_byte4(int(v)) for v in r], dtype=np.int32)
    vec_mode = r & MODE_MASK
    assert np.array_equal(vec_mode, (ref & MODE_FIELD) >> MODE_SHIFT), \
        "the vectorised mode decode differs from the instruction model"
    assert (ref & BIT_LIVE).all(), "the liveness bit is clear for some mode byte"
    assert np.isin(ref & PROBE_MASK, sorted(LEGAL_FIELD)).all(), "a payload falls outside LEGAL"
    # 🛑 the ALIASING is a property of the rung, not a caveat bolted on afterwards.
    assert wire_byte4(16) == wire_byte4(0) and wire_byte4(26) == wire_byte4(10), \
        "the 4-bit field does not ALIAS mod 16 -- the aliasing note in the docstring is wrong"
    for status in range(8):
        assert wire_byte4(0xFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
        assert wire_byte4(0, status) == 0x80 | status
    # every mode value must be reachable, and the dose table must cover exactly EDIT 2's modes
    assert {int(v) for v in vec_mode} == set(range(16)), "not all 16 modes are reachable"
    assert set(DOSE) == set(RATCHET_MODES), "the dose table does not cover exactly EDIT 2's modes"
    assert set(RATCHET_MODES) & set(EXCLUDED_MODES) == set(), "EDIT 2 overlaps V72's LEVER B modes"
    assert set(RATCHET_MODES) | set(EXCLUDED_MODES) | set(UNCOVERED_MODES) | {6, 7, 8, 9} == \
        set(range(16)), "the mode partition does not tile 0..15"


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

    # ---- V73 probe decode -----------------------------------------------------------------------
    # ★★★★ bits 6:3 ARE THE MODE -- `(gp+0x63FD) & 0xF`, the base-assist damper's selector, the byte
    # every FactorB/C/D/E lookup, the friction lane and r24's gain_B selector all index on. This is
    # the first direct read of it in the kit's history; every prior "mode 10" was an INFERENCE.
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & BIT_LIVE) != 0)
    mode = ((p & MODE_FIELD) >> MODE_SHIFT)
    d["live"] = live.astype(float)
    # SEMANTIC name -- what the field MEANS on this build. ⚠ This is `mode & 0xF`, see the docstring.
    d["mode"] = mode.astype(float)
    # CELL-QUALIFIED alias, matching the r50/r54/r58/r59 caches' naming convention so a generic
    # script that reaches for a cell name finds the RIGHT cell and cannot silently read a lane.
    d["m_63fd"] = mode.astype(float)
    # ⚠ HELPER MASKS, so a downstream script does not re-derive the mode partition and get it wrong.
    d["mode_is_edit2"] = np.isin(mode, RATCHET_MODES).astype(float)     # EDIT 2 (ratchet) was live
    d["mode_is_v72lb"] = np.isin(mode, EXCLUDED_MODES).astype(float)    # EDIT 1's LERP + V72 LEVER B
    d["mode_is_uncov"] = np.isin(mode, UNCOVERED_MODES).astype(float)   # NEITHER edit live
    # ★ THE DELIVERED CREEP DOSE, per frame, in counts -- NaN where EDIT 2 did not cover the mode.
    # 🛑 Modes 4/5/12/14 deliver 31-33 counts against 106 on 0-3: a null there is an UNDER-DOSE.
    d["dose"] = np.array([DOSE.get(int(m), np.nan) for m in mode], dtype=float)
    # 🛑 NO INVARIANT EXISTS ON V73 -- `order_viol` is NaN, NOT 0. See the module docstring, point 1:
    # V72's `bit5 => bit6` came from one shared `sar`; V73's 16 payloads are all legal, so a zero
    # here would assert a structural guarantee this build does not have. NaN fails loudly.
    d["order_viol"] = np.full(len(p), np.nan)
    # 🛑 NO `g6806` BIT: the probe spends its whole field on the mode. `cc_lat` is the engagement
    # channel, and on this UNGATED build it does NOT select the firmware's arms -- V73 carries V72's
    # LEVER A unchanged and doses BOTH arms at creep.
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
        # ★ PROVENANCE. Unlike route 59 (five rungs across THREE cells, where a scalar would be
        # wrong for four of them) V73 reads exactly ONE cell, so the scalar form is correct and is
        # written alongside the array form for whichever convention a downstream script reaches for.
        probe_build=np.array([BUILD]), probe_cell=np.array([PROBE_CELL]),
        probe_lane=np.array([PROBE_LANE]), probe_cells=np.array(PROBE_CELLS),
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
    mu, mc = np.unique(mode, return_counts=True)
    mstr = " ".join(f"m{int(v)}:{int(c)}" for v, c in zip(mu, mc))
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.3f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** ILLEGAL {bad_b4}" if bad_b4 else "   (all legal)") + "\n"
          f"      VOID {void}   ★★★★ MODE {mstr}   "
          f"illegal {int(d['illegal'].sum())}\n"
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
    print(f"ROUTE 5A = {BUILD}   rungs: " + " | ".join(PROBE_RUNGS) +
          f"\n  ★★★★ THE MODE SELECTOR gp+0x63FD, read directly for the first time."
          f"\n  🛑 ALL 16 payloads legal ⇒ NO build identity from the stream; `order_viol` is NaN."
          f"\n  🛑 mode 0 transmits as 0x87 -- the SAME byte V64 emitted when its detector never"
          f"\n     armed. A constant-0x87 stream needs the FILENAME + CAVE_HEX to interpret."
          f"\n  rwd: {RWD_NAME}")
    for s in args:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{PFX}{s}")
