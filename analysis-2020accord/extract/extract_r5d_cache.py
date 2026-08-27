#!/usr/bin/env python3
"""Extract route `5d` (**V74**, segments 0-16) to .npz caches. THE CANONICAL ROUTE-5D EXTRACTOR.

Route `75604b0a432fdc89_0000005d--33cf31c2e4`, segments 0..16 -- 17 segments. This is the **V74 test
drive**. V74's probe spends its 5-bit field on TWO things, and the first of them is the positive
control the last five probes lacked:

    bit7      = (*(short *)(gp - 0x6BD0) != 0)   ★★★★ THE DAMPER'S OWN OUTPUT.
    bits 6:3  = (*(byte  *)(gp - 0x67FA)) & 0xF  ★★ the assist-chain STATE.
    bits 2:0  = stock STEER_SENSOR_STATUS         preserved, untouched.

🛑 ONE ROUTE, ONE EXTRACTOR. Two agents once wrote `extract/extract_r4f_cache.py` and `r4f_extract_cache.py`
in the same session, both writing `_scratch/cache/r4f/r4fs*.npz` with DIFFERENT field sets, and whichever ran
last silently dropped the other's channels. If you need a variant, add a flag, not a file.

Every channel `extract/extract_r5a_cache.py` wrote is written here under the SAME name with the SAME units,
so `_grind2_lib.wrecs`, `_r31_common.load` and `_r4f_lib.avg_periodogram` read this cache with the
identical instrument they read every prior route with. What CHANGED is listed at the bottom of this
docstring, and every change is either (a) the build-specific probe decode or (b) a channel the route
needs that no prior extractor captured.

THE BUILD ON THIS ROUTE
-----------------------
    39990-TVA,A160-V74-V73BASE-ENGCOLS13-x12-addonly-FactorCY0eqY2-FactorEX0to12-Y1eqY2-
    frictionx1p5-C407E850-probe-67fa-6bd0nz-0x13000-0x100000.rwd

V74 = **V73's base**, plus LEVER E' (`FactorC Y[0] := Y[2]` · `FactorE X[0]: 60 -> 12` ·
`FactorE Y[1] := Y[2]`) and LEVER D' (friction lane x1.5), written to the **ENGAGED COLUMN OF ALL 16
CONFIG ROWS** -- the 13 modes {2,3,5,11,14,15,17,23,26,27,29,32,33}. The disengaged column
{0,1,4,10,12,13,16,22,24,25,28,30,31} is disjoint and left byte-stock, so manual and parking steering
are untouched. The car is row 11 `TVCA4`: mode **24 manual / 26 ENGAGED** (V73's probe, 104,061
frames, not an inference).

🛑🛑 READ THE LIVENESS FIRST, AND THEN READ THE BUILD IDENTITY
--------------------------------------------------------------
1. **LIVENESS IS STRUCTURAL, AND IT IS `bits 6:3`, NOT `bit7`.** `gp-0x67FA`'s complete value set is
   {1,3,4,5,6,7,8,9,10,11} -- all 33 `st.b` writers store literals. **0 is impossible**, so
   `bits 6:3` constant 0 across the drive can ONLY mean the cave never fired ⇒ VOID, and nothing
   else in the log is interpretable. `d["live"]` below is `state != 0`.
   ⚠ **THIS IS A SEMANTIC BREAK FROM ROUTE 5A.** On V73 `bit7` was a hard-wired liveness `1` and
   `d["live"]` meant "bit7 set". On V74 `bit7` is the DAMPER. A script that reads `d["live"]` still
   gets "the cave fired"; a script that assumes `live == (probe & 0x80)` is WRONG here.
   `probe_live_semantics` in the .npz says so in words.
2. **BUILD IDENTITY IS THE KNOWN FAILURE MODE ON THIS EXACT FILE PAIR.** Every `V7x` cave writes the
   SAME cell (`gp-0x1514`, CAN 0x14A byte4) in the SAME bit positions, and the alphabets OVERLAP:
   V73's `bits 6:3` are `mode & 0xF`, which on this car is 24/26 -> **8/10**, and both 8 and 10 are
   legal `gp-0x67FA` states. Run against V73's own flight (route 5a), `probe/decode_v74_probe.py` printed
   *"bit7 fires on 100.000% of frames ⇒ LEVER E' IS DELIVERING"* -- reading V73's constant liveness
   seed as V74's damper. ⇒ `summarize()` below runs `decode_v74_probe.identify()` over the WHOLE
   route and records its verdict in the summary JSON. **The guard can only ever REJECT, never
   confirm; the `.rwd` FILENAME remains the pre-drive discriminator.**
   ⊕ Three V74 cuts exist and **all three share a byte-identical cave**, so no payload distinguishes
   them either. Two are renamed `SUPERSEDED-DO-NOT-FLASH-…`.

`_assert_cave_bytes()` re-reads `CAVE_HEX` out of `rlog-tools/probe/decode_v74_probe.py` at import time and
fails this extractor if any load displacement, mask immediate, condition nibble or register field has
drifted -- including the four one-bit traps that would silently void the measurement:
  · **`ld.h` op 0x39 vs `st.h` op 0x3B** at offset 2. `st.h` is a REAL instruction at 0x34730 writing
    this very cell, so the wrong bit would have the cave OVERWRITE the damper output it is reading.
  · **`be` (cond 0x2, `b205`) vs `bne` (cond 0xA, `ba05`)** at offset 8 -- the recorded rung-inversion
    trap. `be` skips the `movea`, so bit7 means `!= 0`; `bne` would inverts it to `== 0`.
  · **`ld.bu` op 0x3C (EVEN displacement) vs `st.b` op 0x3A** at offset 14, and the `hw2 = disp|1`
    form: `-0x67FA` is `0x9806`, so hw2 is `0x9807`. The real `st.b …,-0x67fa[gp]` @0x19862 is
    `44370698`; this cell is lockstep-shadowed at `gp-0x4c39`, so a stray write escalates.
  · **`or r6,r7` (0639) vs `or r7,r6` (0731)** at offset 22. SAME opcode, register fields SWAPPED,
    BOTH real in this image. The wrong one ORs the state into the SCRATCH register and every frame
    reads state 0 -- indistinguishable from a VOID cave.

WHAT THIS EXTRACTOR ADDS OVER `extract/extract_r5a_cache.py`, AND WHY
-------------------------------------------------------------
  1. ★ **WHEEL SPEEDS, from RAW CAN `0x1D0` src 1** (4 x 15-bit, 0.01 kph, big-endian packed).
     🛑 **`carState.wheelSpeeds` is IDENTICALLY ZERO on this fork** -- fl=fr=rl=rr=0 on every sample
     of every segment while `vEgo` reads 24.7 m/s. The summary reports that max explicitly so the
     null is on record rather than rediscovered. The raw decode is validated against `vEgo` in the
     summary (`ws_vego_med_abs_err`). Tyre-order discrimination needs this and route 5a lacks it.
  2. ★ **THE IMU, in the SAME PASS**, written to `{tag}_imu.npz` in `extract/extract_imu_cache.py`'s EXACT
     schema (`at/ax/ay/az/gt/gx/gy/gz` + hardware-clock offsets). 🛑 **On the sensor's OWN hardware
     lattice, NOT resampled onto the 100 Hz CAN grid** -- resampling destroys precisely the
     independence that makes the IMU the kit's only witness off the EPS signal path
     (`_r47_imu_lib` docstring). `extract/extract_imu_cache.py` has never had routes 50/54/58/59/5a/5d
     registered, so folding it in here is the difference between having an independent witness on
     this route and not having one; a second walk over 17 x ~10 MB segments is pure cost.
  3. **`{tag}_snd.npz` sidecar** in `extract/extract_sound_cache.py`'s schema (adds `spwdb`), so
     `_r47_imu_lib.load_snd` works on this route. The in-main `snd_t/snd_sp/snd_spw` arrays route 5a
     wrote are kept unchanged as well.
  4. **openpilot's command from the `sendcan` MESSAGE, not only the CAN loopback.** Route 5a took
     0x0E4 from `can` src **129** (the panda's TX echo). That is correct and is kept as `e4tq`/
     `e4req`/`e4hist`; `sc_tq`/`sc_req`/`sc_hist` are the same signal read out of the `sendcan`
     message on src 1, i.e. at the moment openpilot emitted it. Two clocks on one quantity.
  5. **`co_req` / `co_tqcan`** -- `carOutput.actuatorsOutput.torque` and `.torqueOutputCan`, the
     applied actuator output, alongside route 5a's `cc_req` (`carControl.actuators.torque`).
  6. The V74 probe decode, and **`mode` / `m_63fd` written as NaN**: V74's probe does NOT carry the
     mode byte. `_r5a_lib._add_mode` reads `d["mode"]` by name and would happily label every window
     with `gp-0x67FA`'s state if this were left as a number.

★ SAMPLE RATE comes from `_r4f_lib.fs_lattice`, never `1/median(dt)`. CAN frames are timestamped per
LOG PACKET, so several share a timestamp and the legacy estimator is biased HIGH by a
ROUTE-DEPENDENT ~1.3% -- three quarters of a bin at 21 Hz.

Usage:  python extract/extract_r5d_cache.py              # all 17 segments, then the summary
        python extract/extract_r5d_cache.py 0 1          # chosen segments (no summary)
        python extract/extract_r5d_cache.py --summary    # summary only, from the caches on disk
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
# header below crashes the run before a single segment is written.
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
ROUTE = "75604b0a432fdc89_0000005d--33cf31c2e4"
SEGS = list(range(17))
OUT = Path(os.environ.get("R5D_CACHE", ROOT / "_scratch/cache/r5d"))
PFX = "r5ds"
SUMMARY = HERE / "_scratch/out/_r5d_extract_summary.json"

BUILD = "V74"
# 🛑 ONE LINE, and asserted below to equal `decode_v74_probe.RWD_NAME` read out of that file's
# source. The filename is the pre-drive build discriminator, so a drifted copy here is not cosmetic.
RWD_NAME = "39990-TVA,A160-V74-V73BASE-ENGCOLS13-x12-addonly-FactorCY0eqY2-FactorEX0to12-Y1eqY2-frictionx1p5-C407E850-probe-67fa-6bd0nz-0x13000-0x100000.rwd"  # noqa: E501

# ★ THE TWO CELLS. Both are NEGATIVE gp displacements.
STATE_DISP = 0x67FA           # gp-0x67FA, the assist-chain fault state -- BYTE, zero-extended
DAMP_DISP = 0x6BD0            # gp-0x6BD0, the base-assist damper output -- HALFWORD, SIGNED
CAN_DISP = 0x1514             # gp-0x1514, the CAN 0x14A byte4 staging cell
PROBE_CELLS = (DAMP_DISP, STATE_DISP)
PROBE_LANE = "bit7 gp-0x6bd0!=0 DAMPER OUT | bits6:3 gp-0x67fa STATE"
PROBE_RUNGS = ("bit7 (gp-0x6bd0 != 0) DAMPER OUTPUT -- the positive control",
               "bits6:3 (gp-0x67fa)&0xF assist-chain STATE -- 0 impossible => liveness")
PROBE_CELL = STATE_DISP       # scalar alias: the liveness cell, the one to read first

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

BIT_DAMP_NZ = 0x80            # bit7  (gp-0x6BD0 != 0)   ★ THE POSITIVE CONTROL
STATE_FIELD = 0x78            # bits 6:3  (gp-0x67FA) & 0xF
STATE_SHIFT = 3
STATE_MASK = 0xF
PROBE_MASK = 0xF8
STATUS_MASK = 0x07            # STEER_SENSOR_STATUS, preserved

# ★ 0 IS UNREACHABLE. All 33 `st.b` writers store literals; 30 are inline immediates and the 3
# register stores were read in Ghidra (0x19862 -> 3, 0x19D24 -> 6, 0x1A0BA re-stores the cell's own
# value during the lockstep compare against gp-0x4C39). ⇒ constant 0 == VOID, never "no fault".
STATE_VALUE_SET = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11)
# 🛑 V73's bits 6:3 were `mode & 0xF` and this car's modes 24/26 give 8/10 -- BOTH legal here.
V73_MODE_FIELD_VALUES = {24 & 0xF, 26 & 0xF}

FACTORC_ONSET_MS = 9.72       # 35 km/h -- FactorC's stock X[0]; below it the DISENGAGED column is 0
FACTORE_X0_STOCK = 60         # counts of motor rate; V74 moves the ENGAGED column's X[0] to 12
CREEP_MAX_MS = 4.0            # the ratchet and grind #1 are creep symptoms (1-4 m/s)
CRUISE_MIN_MS = 20.0          # STATE.md flight condition (2): the tyre-order-clean high-speed test
# ⚠ Tyre order 1 is in-band (6-9 Hz) at 12.5-18.7 m/s, order 2 at 6.2-9.4, order 3 at 4.2-6.2.
TYRE_DIRTY = ((4.2, 6.2), (6.2, 9.4), (12.5, 18.7))
TYRE_CLEAN = ((9.4, 12.5), (20.0, 99.0))

# All 20 payloads V74 can structurally emit: bit7 free x 10 reachable states.
LEGAL_FIELD = {(b7 << 4) | s for b7 in (0, 1) for s in STATE_VALUE_SET}
LEGAL_BYTE4 = {f << STATE_SHIFT for f in LEGAL_FIELD}
assert len(LEGAL_FIELD) == 20, "V74's payload alphabet is 2 x the 10 reachable gp-0x67fa states"
assert STATE_FIELD == STATE_MASK << STATE_SHIFT == 0x78, "the state field is not bits 6:3"
assert BIT_DAMP_NZ | STATE_FIELD == PROBE_MASK
assert PROBE_MASK & STATUS_MASK == 0, "the probe bits collide with STEER_SENSOR_STATUS"
assert 0 not in STATE_VALUE_SET, "state 0 must be unreachable -- liveness is structural on that"

# 🛑 A COLLISION THIS KIT HAS ALREADY BEEN BITTEN BY, TWICE. 0x87 is V73's `mode 0` payload AND the
# byte V64's probe emitted, constant, for 14,980 frames when its detector never armed.
V64_STUCK_VALUE = 0x87

# ---- wheel speeds: CAN 0x1D0 (464) src 1, 4 x 15-bit unsigned, 0.01 kph, packed MSB-first ---------
# 🛑 `carState.wheelSpeeds` is IDENTICALLY ZERO on this fork (checked on every segment, reported in
# the summary as `cs_ws_max`), so this raw decode is the ONLY wheel-speed source on this route.
KPH_TO_MS = 1.0 / 3.6


def wheel_speeds_kph(d):
    """0x1D0 -> (fl, fr, rl, rr) in kph. 15 bits each, 0.01 kph/count, big-endian bit order."""
    fl = (d[0] << 7) | (d[1] >> 1)
    fr = ((d[1] & 0x01) << 14) | (d[2] << 6) | (d[3] >> 2)
    rl = ((d[3] & 0x03) << 13) | (d[4] << 5) | (d[5] >> 3)
    rr = ((d[5] & 0x07) << 12) | (d[6] << 4) | (d[7] >> 4)
    return fl * 0.01, fr * 0.01, rl * 0.01, rr * 0.01


def wire_byte4(damp_val, state_byte, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order, same widths.

    0xC4B34  mov 0x0,r7 / ld.h -0x6bd0[gp],r6 / cmp r0,r6 / be +6 / movea 0x10,r0,r7 /
             ld.bu -0x67fa[gp],r6 / andi 0xf / or r6,r7 / shl 0x3 / ld.bu -0x1514[gp],r6 /
             andi 0x7 / or r7,r6 / st.b r6,-0x1514[gp].
    """
    r7 = 0x00                                       # mov   0x0,r7
    r6 = int(damp_val)                              # ld.h  -0x6bd0[gp],r6   SIGNED halfword
    r6 = ((r6 + 0x8000) & 0xFFFF) - 0x8000          #   ... sign-extended, as ld.h does
    if r6 != 0:                                     # cmp r0,r6 ; be +6  (skips the movea)
        r7 = 0x10                                   # movea 0x10,r0,r7    -> bit7 after the shl
    r6 = int(state_byte) & 0xFF                     # ld.bu -0x67fa[gp],r6  (a BYTE, zero-extended)
    r6 &= STATE_MASK                                # andi  0xf,r6,r6
    r7 |= r6                                        # or    r6,r7   🛑 NOT `or r7,r6`
    return ((r7 << STATE_SHIFT) & 0xFF) | (int(status_bits) & STATUS_MASK)


# The cave's REAL instruction boundaries, as (offset, length). Every byte-level check below is made
# on these rather than on "every even offset" -- a displacement halfword decoded as an opcode is how
# a store gets invented or missed.
BOUNDARIES = ((0, 2), (2, 4), (6, 2), (8, 2), (10, 4),          # seed + damper + cmp + be + movea
              (14, 4), (18, 4), (22, 2), (24, 2),               # state + mask + or + shl
              (26, 4), (30, 4), (34, 2), (36, 4), (40, 4), (44, 2))   # merge + store + tail
PAD_OFF = 46


def _op(hw):
    """The V850 Format-VII opcode field: bits 10:5 of the first halfword."""
    return (hw >> 5) & 0x3F


def _assert_cave_bytes():
    """🛑 THE MECHANICAL LINK TO THE IMAGE, retargeted at V74's own decoder.

    Re-read `CAVE_HEX` out of `rlog-tools/probe/decode_v74_probe.py` (by REGEX, not by import, so this does
    not drag in that file's import chain) and fail this extractor if anything the payload's meaning
    depends on has drifted. If this ever fires, the cache would have been labelled with the wrong
    cell -- which is the exact defect that ran for four builds.
    """
    src = (ROOT / "rlog-tools" / "probe/decode_v74_probe.py").read_text(encoding="utf-8")
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', src, re.M)
    assert m, "CAVE_HEX not found in probe/decode_v74_probe.py -- cannot verify the probe cells"
    raw = bytes.fromhex(m.group(1))
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, expected the proven 68-byte cave"
    assert sum(n for _o, n in BOUNDARIES) == PAD_OFF, "the boundary table does not tile the code"
    for prev, nxt in zip(BOUNDARIES, BOUNDARIES[1:]):
        assert prev[0] + prev[1] == nxt[0], f"the boundary table is not contiguous at {prev}"
    assert raw[PAD_OFF:] == bytes(68 - PAD_OFF), \
        "the bytes after `jmp [lp]` are not all 0x00 -- the padding claim is wrong"
    assert raw[0:2] == bytes.fromhex("003a"), "offset 0 is not `mov 0x0,r7` (the bit7 = 0 seed)"
    assert raw[44:46] == bytes.fromhex("7f00"), "offset 44 is not `jmp [lp]`"

    # ---- THE DAMPER LOAD, by displacement AND by opcode field -------------------------------------
    # 🛑🛑 `ld.h` is op 0x39; its one-bit twin `st.h` (0x3B) is a REAL instruction @0x34730 writing
    # THIS VERY CELL, so the wrong bit would have the cave OVERWRITE the damper output.
    assert raw[2:6] == bytes.fromhex("24373094"), "offset 2 is not `ld.h -0x6bd0[gp],r6`"
    _hd = int.from_bytes(raw[2:4], "little")
    assert _op(_hd) == 0x39, \
        f"the damper load's opcode field is 0x{_op(_hd):02X}, MUST be 0x39 (ld.h, SIGNED). 0x3B is " \
        "st.h -- the cave would WRITE the damper cell instead of reading it"
    assert (_hd >> 11) == 6 and (_hd & 0x1F) == 4, "the damper load is not `... [gp],r6`"
    _dd = int.from_bytes(raw[4:6], "little")
    assert _dd - 0x10000 == -DAMP_DISP, \
        f"the damper load carries 0x{_dd:04X}, not -0x{DAMP_DISP:04X} -- WRONG CELL"

    # ---- THE BRANCH POLARITY -- the recorded `b205`/`ba05` rung-inversion trap ---------------------
    assert raw[6:8] == bytes.fromhex("e031"), "offset 6 is not `cmp r0,r6`"
    assert raw[8:10] == bytes.fromhex("b205"), "offset 8 is not `be +6`"
    _b = int.from_bytes(raw[8:10], "little")
    assert (_b >> 7) & 0xF == 0xB, "offset 8 is not a Format-III Bcond"
    assert (_b & 0xF) == 0x2, \
        f"the branch condition nibble is 0x{_b & 0xF:X}, MUST be 0x2 (be/bz). 0xA is `bne` -- bit7 " \
        "would read `gp-0x6bd0 == 0` and EVERY conclusion about the damper would be INVERTED"
    _disp = (((_b >> 11) & 0x1F) << 4 | ((_b >> 4) & 0x7)) << 1
    assert _disp == 6, \
        f"the `be` displacement is +{_disp}, MUST be +6 -- it skips a FOUR-byte movea, and +4 would " \
        "land INSIDE it"
    assert raw[10:14] == bytes.fromhex("203e1000"), "offset 10 is not `movea 0x10,r0,r7`"

    # ---- THE STATE LOAD ---------------------------------------------------------------------------
    # 🛑 -0x67FA = 0x9806 is EVEN => op 0x3C (the ODD form is 0x3D); hw2 = (disp & 0xFFFE) | 1.
    assert raw[14:18] == bytes.fromhex("84370798"), "offset 14 is not `ld.bu -0x67fa[gp],r6`"
    assert raw[14:18] != bytes.fromhex("44370698"), \
        "the state load IS the real `st.b …,-0x67fa[gp]` @0x19862 -- the cave would WRITE a cell " \
        "that is LOCKSTEP-shadowed at gp-0x4c39, escalating to FUN_0006b9fa. NOT V74."
    _hs = int.from_bytes(raw[14:16], "little")
    assert _op(_hs) == 0x3C, \
        f"the state load's opcode field is 0x{_op(_hs):02X}, MUST be 0x3C (ld.bu, EVEN " \
        "displacement); 0x3D is the ODD form and 0x3A is st.b -- this cache would be mislabelled"
    assert (_hs >> 11) == 6 and (_hs & 0x1F) == 4, "the state load is not `... [gp],r6`"
    _neg = (-STATE_DISP) & 0xFFFF
    assert int.from_bytes(raw[16:18], "little") == (_neg & 0xFFFE) | 1 == 0x9807, \
        f"the state load does not carry -0x{STATE_DISP:04X} in the `hw2 = disp|1` form -- WRONG CELL"

    # ---- the field arithmetic, byte by byte -------------------------------------------------------
    for off, want, what in ((18, "c6360f00", "andi 0xf,r6,r6   -- the 4-bit state mask"),
                            (22, "0639", "or r6,r7         -- state INTO the payload"),
                            (24, "c33a", "shl 0x3,r7       -- field -> bits 7:3"),
                            (26, "8437edea", "ld.bu -0x1514[gp],r6"),
                            (30, "c6360700", "andi 0x7,r6,r6   -- keep the status bits"),
                            (34, "0731", "or r7,r6         -- the MERGE"),
                            (36, "4437ecea", "st.b r6,-0x1514[gp] -- THE ONLY STORE"),
                            (40, "2436e8ea", "movea -0x1518,gp,r6 -- the displaced instruction")):
        assert raw[off:off + len(want) // 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what}) -- the probe does not mean what we decode"
    # 🛑🛑 `or r6,r7` vs `or r7,r6`: SAME opcode, register fields SWAPPED, BOTH real in this image.
    # Decode the FIELDS -- a byte comparison alone is not a proof here.
    assert raw[22:24] != raw[34:36], "offsets 22 and 34 are the same `or` -- one of them is swapped"
    _or = int.from_bytes(raw[22:24], "little")
    assert _op(_or) == 0x08 and (_or >> 11) == 7 and (_or & 0x1F) == 6, \
        f"the accumulate's fields are wrong: op 0x{_op(_or):02X}, dest r{_or >> 11}, " \
        f"src r{_or & 0x1F} -- must be op 0x08, dest r7, src r6 (`or r6,r7`). The swapped form ORs " \
        "the state into the SCRATCH register and every frame reads state 0 -- a fake VOID."
    _mg = int.from_bytes(raw[34:36], "little")
    assert _op(_mg) == 0x08 and (_mg >> 11) == 6 and (_mg & 0x1F) == 7, "the merge is not `or r7,r6`"
    assert raw[18:22] != raw[30:34], "the 0xF and 0x7 masks collapsed -- the state's top bit is lost"
    assert int.from_bytes(raw[20:22], "little") == STATE_MASK and \
        int.from_bytes(raw[32:34], "little") == STATUS_MASK, \
        "the two andi immediates are not 0xF (the state) and 0x7 (the preserved status bits)"
    # 🛑 EXACTLY ONE STORE, on the REAL instruction boundaries. GATE 1 is vacuous only if this holds.
    stores = [o for o, n in BOUNDARIES
              if n >= 4 and _op(int.from_bytes(raw[o:o + 2], "little")) in (0x3A, 0x3B)]
    assert stores == [36], f"the cave's store set is {stores}, expected exactly [36]"
    _st = int.from_bytes(raw[38:40], "little")
    assert _st == ((-CAN_DISP) & 0xFFFF), \
        f"the only store does not target -0x{CAN_DISP:04X} (the CAN 0x14A byte4 staging cell)"
    # ---- and the .rwd name, so this cache cannot be labelled with a different artefact -------------
    mn = re.search(r'^RWD_NAME\s*=\s*"([^"]+)"', src, re.M)
    assert mn, "RWD_NAME not found in probe/decode_v74_probe.py"
    assert mn.group(1) == RWD_NAME, \
        f"RWD_NAME drifted from the decoder's:\n  here    {RWD_NAME}\n  decoder {mn.group(1)}"


def _self_check():
    """The payload claims as executable assertions, over every value the two cells can hold."""
    # ---- bit7 is the DAMPER, and it is a `!= 0` test on a SIGNED halfword -------------------------
    assert wire_byte4(0, 1, 0) & BIT_DAMP_NZ == 0, "bit7 is set at damper output 0"
    for v in (1, -1, 32767, -32768, 64, -64):
        assert wire_byte4(v, 1, 0) & BIT_DAMP_NZ == BIT_DAMP_NZ, f"bit7 is clear at damper {v}"
    assert wire_byte4(0x10000, 1, 0) & BIT_DAMP_NZ == 0, \
        "the damper load is not a 16-bit halfword -- 0x10000 must truncate to 0"
    # ---- the state rung, EXHAUSTIVELY, against the VECTORISED decode this file actually uses ------
    r = np.arange(256, dtype=np.int32)
    ref0 = np.array([wire_byte4(0, int(v)) for v in r], dtype=np.int32)
    ref1 = np.array([wire_byte4(7, int(v)) for v in r], dtype=np.int32)
    assert np.array_equal(r & STATE_MASK, (ref0 & STATE_FIELD) >> STATE_SHIFT), \
        "the vectorised state decode differs from the instruction model"
    assert np.array_equal((ref0 & STATE_FIELD), (ref1 & STATE_FIELD)), \
        "the damper bit leaks into the state field"
    assert not (ref0 & BIT_DAMP_NZ).any() and (ref1 & BIT_DAMP_NZ).all(), "bit7 is not the damper"
    # ⚠ the 4-bit field ALIASES mod 16 -- a property of the rung, not a caveat bolted on afterwards.
    assert wire_byte4(0, 16) == wire_byte4(0, 0) and wire_byte4(0, 26) == wire_byte4(0, 10), \
        "the 4-bit state field does not ALIAS mod 16"
    # ★ but it is LOSSLESS here: gp-0x67FA's whole value set is < 16.
    assert max(STATE_VALUE_SET) < 16, "a reachable state exceeds the 4-bit field -- NOT lossless"
    for status in range(8):
        assert wire_byte4(1, 0xFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
        assert wire_byte4(0, 0, status) == 0x00 | status
    # ---- the legal alphabet ----------------------------------------------------------------------
    assert {wire_byte4(0, s, 0) >> STATE_SHIFT for s in STATE_VALUE_SET} | \
           {wire_byte4(1, s, 0) >> STATE_SHIFT for s in STATE_VALUE_SET} == LEGAL_FIELD, \
        "the legal-field set is not what the instruction model emits"
    # 🛑 the V73 overlap, as an executable statement rather than a warning in prose.
    assert V73_MODE_FIELD_VALUES <= set(STATE_VALUE_SET), \
        "V73's mode-field values {8,10} are no longer legal V74 states -- the documented alphabet " \
        "overlap is stale and identify()'s D3 fingerprint needs revisiting"
    assert wire_byte4(1, 0, 0x7) == V64_STUCK_VALUE, \
        "V74 no longer emits 0x87 for (damper != 0, state 0) -- the V64 collision note is stale"


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


def _grid(t_out, t_in, v_in):
    """Linear interpolation onto the 0x14A lattice; NaN if the channel is absent."""
    t_in = np.asarray(t_in, float)
    if not len(t_in):
        return np.full(len(t_out), np.nan)
    return np.interp(t_out, t_in, np.asarray(v_in, float))


def extract(paths, tag, t0=None):
    rows, e4hist, events = [], [], []
    last18, lastE4 = None, (0.0, 0)
    raw = {0x14A: [], 0x18F: [], 0x1FA: [], 0x0E4: [], 0x1D0: []}
    # 🛑 INDEPENDENT SECOND METHOD for the STEER_STATUS census and the byte4 histogram: every
    # 0x18F / 0x14A src-1 frame exactly as it arrived, no hold, no grid.
    raw18_st, raw18_b4, raw14_b4 = [], [], []
    rpm_t, rpm_v = [], []
    ws_t, ws_v = [], []                     # raw 0x1D0 src1, kph
    sc_t, sc_tq, sc_rq = [], [], []         # the `sendcan` MESSAGE, src 1, 0x0E4
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cs_ws_max = 0.0                         # 🛑 identically 0 on this fork -- proven, not assumed
    cc = {"t": [], "lat": [], "en": [], "req": []}
    co = {"t": [], "req": [], "can": []}
    clk = {"t": [], "w": []}
    init_wall = []
    snd = {"t": [], "sp": [], "spw": [], "db": []}
    # IMU: hardware timestamps, kept on their OWN lattice (see the module docstring, point 2).
    a_hw, a_mono, a_v, a_st = [], [], [], []
    g_hw, g_mono, g_v, g_st = [], [], [], []

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
                        raw18_b4.append(d[4])
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x17C and len(d) >= 4:
                        rpm_t.append(tm)
                        rpm_v.append((d[2] << 8) | d[3])
                    elif src == 1 and addr == 0x1D0 and len(d) >= 8:
                        ws_t.append(tm)
                        ws_v.append(wheel_speeds_kph(d))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
            elif w == "sendcan":
                # ★ openpilot's command AT EMISSION, not at the panda's TX echo. Same quantity as
                # `e4tq`, a different clock -- see the module docstring, point 4.
                for m in evt.sendcan:
                    if int(m.src) == 1 and int(m.address) == 0x0E4:
                        d = bytes(m.dat)
                        if len(d) >= 3:
                            sc_t.append(tm)
                            sc_tq.append(float(i16be(d, 0)))
                            sc_rq.append(float((d[2] >> 7) & 1))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                try:
                    ws = c.wheelSpeeds
                    cs_ws_max = max(cs_ws_max, float(ws.fl), float(ws.fr), float(ws.rl),
                                    float(ws.rr))
                except Exception:
                    pass
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
            elif w == "carOutput":
                try:
                    a = evt.carOutput.actuatorsOutput
                    co["t"].append(tm)
                    co["req"].append(float(a.torque))
                    try:
                        co["can"].append(float(a.torqueOutputCan))
                    except Exception:
                        co["can"].append(np.nan)
                except Exception:
                    pass
            elif w == "accelerometer":
                try:
                    m = evt.accelerometer
                    a_hw.append(int(m.timestamp) * 1e-9); a_mono.append(tm)
                    a_v.append(list(m.acceleration.v)); a_st.append(int(m.acceleration.status))
                except Exception:
                    pass
            elif w == "gyroscope":
                try:
                    m = evt.gyroscope
                    # `gyroUncalibrated` is the populated field on this fork; `gyro` is empty.
                    try:
                        v, st = list(m.gyroUncalibrated.v), int(m.gyroUncalibrated.status)
                    except Exception:
                        v, st = list(m.gyro.v), int(m.gyro.status)
                    g_hw.append(int(m.timestamp) * 1e-9); g_mono.append(tm)
                    g_v.append(v); g_st.append(st)
                except Exception:
                    pass
            elif w == "soundPressure":
                try:
                    m = evt.soundPressure
                    snd["t"].append(tm)
                    snd["sp"].append(float(m.soundPressure))
                    snd["spw"].append(float(m.soundPressureWeighted))
                    try:
                        snd["db"].append(float(m.soundPressureWeightedDb))
                    except Exception:
                        snd["db"].append(np.nan)
                except Exception:
                    for k in ("t", "sp", "spw", "db"):
                        if len(snd[k]) > min(len(snd[j]) for j in ("t", "sp", "spw", "db")):
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

    # ---- V74 probe decode -------------------------------------------------------------------------
    # 🛑 LIVENESS IS `bits 6:3 != 0`, NOT bit7. On V73 bit7 was a hard-wired 1 and `live` meant it;
    # here bit7 is the DAMPER and a legitimate 0. See the module docstring, point 1.
    p = d["probe"].astype(int)
    d["field"] = ((p >> STATE_SHIFT) & 0x1F).astype(float)   # the whole 5-bit probe field
    state = (p & STATE_FIELD) >> STATE_SHIFT
    damp = (p & BIT_DAMP_NZ) != 0
    d["live"] = (state != 0).astype(float)          # ★ STRUCTURAL: gp-0x67FA can never hold 0
    d["state"] = state.astype(float)                # SEMANTIC name -- what the field MEANS
    d["s_67fa"] = state.astype(float)               # CELL-QUALIFIED alias (r50/r54/r58/r59 naming)
    d["damp_nz"] = damp.astype(float)               # ★★★★ bit7 -- THE POSITIVE CONTROL
    d["d_6bd0_nz"] = damp.astype(float)             # CELL-QUALIFIED alias
    # ⚠ HELPER MASK: the state is outside the 33-writer-verified value set ⇒ the cell moved, or the
    # reading is wrong. NOT the same thing as `illegal` on route 5a (which meant "bit7 clear").
    d["state_unknown"] = (~np.isin(state, STATE_VALUE_SET)).astype(float)
    d["illegal"] = ((state == 0) | d["state_unknown"].astype(bool)).astype(float)
    # 🛑 V74's PROBE DOES NOT CARRY THE MODE. `_r5a_lib._add_mode` reads `d["mode"]` BY NAME and
    # would otherwise label every window with gp-0x67FA's state. NaN fails loudly; a number lies.
    d["mode"] = np.full(len(p), np.nan)
    d["m_63fd"] = np.full(len(p), np.nan)
    # 🛑 NO STRUCTURAL ORDERING INVARIANT among V74's 20 payloads (V72's `bit5 => bit6` came from one
    # shared `sar`), and NO `g6806` bit -- the field is spent on the damper and the state.
    d["order_viol"] = np.full(len(p), np.nan)
    d["g6806"] = np.full(len(p), np.nan)

    # ---- wheel speeds: raw 0x1D0, gridded onto the 0x14A lattice, in m/s ---------------------------
    wst = np.array(ws_t, float) - t0
    wsv = np.array(ws_v, float).reshape(-1, 4)
    for i, k in enumerate(("fl", "fr", "rl", "rr")):
        d["ws_" + k] = _grid(d["t"], wst, wsv[:, i] * KPH_TO_MS) if len(wst) else \
            np.full(len(d["t"]), np.nan)
    d["ws_mean"] = np.nanmean(np.vstack([d["ws_fl"], d["ws_fr"], d["ws_rl"], d["ws_rr"]]), axis=0) \
        if len(wst) else np.full(len(d["t"]), np.nan)

    # ---- the command, both clocks ------------------------------------------------------------------
    sct = np.array(sc_t, float) - t0
    d["sc_tq"] = _grid(d["t"], sct, sc_tq)
    d["sc_req"] = held_last(d["t"], sct, sc_rq, 0.0) if len(sct) else np.full(len(d["t"]), np.nan)
    cot = np.array(co["t"], float) - t0
    d["co_req"] = _grid(d["t"], cot, co["req"])
    d["co_tqcan"] = _grid(d["t"], cot, co["can"])

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
    n_snd = min(len(snd["t"]), len(snd["sp"]), len(snd["spw"]), len(snd["db"]))
    snd_t = np.array(snd["t"][:n_snd], float) - t0
    snd_sp = np.array(snd["sp"][:n_snd], float)
    snd_spw = np.array(snd["spw"][:n_snd], float)
    snd_db = np.array(snd["db"][:n_snd], float)

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
        ws_t=wst, ws_kph=wsv,
        sc_t=sct, sc_hist=np.column_stack([sct, sc_tq, sc_rq]) if len(sct) else np.zeros((0, 3)),
        clk_mono=clk_mono, clk_wall=clk_wall, init_wall=iw,
        snd_t=snd_t, snd_sp=snd_sp, snd_spw=snd_spw, snd_db=snd_db,
        raw18_st=np.array(raw18_st, np.int16), raw18_b4=np.array(raw18_b4, np.int16),
        raw14_b4=np.array(raw14_b4, np.int16),
        t0_mono=np.array([t0]), wall_t0=np.array([off]), wall_off_sd=np.array([off_sd]),
        cs_ws_max=np.array([cs_ws_max]),
        # ★ PROVENANCE. V74 reads TWO cells, so the array form is the correct one; the scalar
        # `probe_cell` is the LIVENESS cell, the one to read first.
        probe_build=np.array([BUILD]), probe_cell=np.array([PROBE_CELL]),
        probe_lane=np.array([PROBE_LANE]), probe_cells=np.array(PROBE_CELLS),
        probe_rungs=np.array(PROBE_RUNGS), probe_rwd=np.array([RWD_NAME]),
        probe_live_semantics=np.array([
            "live == (bits6:3 != 0), the STRUCTURAL liveness of gp-0x67fa. 🛑 NOT bit7: on V74 "
            "bit7 is the DAMPER OUTPUT (gp-0x6bd0 != 0) and 0 is a legitimate reading. On V73 "
            "bit7 was a hard-wired liveness 1 and `live` meant that instead."]))
    np.savez_compressed(OUT / f"{tag}_rpm.npz", t=rpm_ts, rpm=rpm_vs)
    np.savez_compressed(OUT / f"{tag}_snd.npz", t=snd_t, sp=snd_sp, spw=snd_spw, spwdb=snd_db,
                        t0_mono=np.array([t0]))
    _write_imu(tag, t0, a_hw, a_mono, a_v, a_st, g_hw, g_mono, g_v, g_st)
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    # ★ THE LATTICE ESTIMATOR, never 1/median(dt) -- see the module docstring.
    fs = fs_lattice(d)
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    void = int((d["state"] == 0).sum())
    import time as _time
    wstr = (_time.strftime("%H:%M:%S", _time.localtime(off)) if np.isfinite(off) else "??")
    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad_b4 = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & PROBE_MASK) not in LEGAL_BYTE4}
    rp = np.array(rpm_v, float)
    rok = (rp > 400) & (rp < 7000)
    su, sc_ = np.unique(state, return_counts=True)
    sstr = " ".join(f"s{int(v)}:{int(c)}" for v, c in zip(su, sc_))
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.3f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** OUTSIDE V74's ALPHABET {bad_b4}" if bad_b4 else "   (all legal)") + "\n"
          f"      VOID {void}   ★★ STATE {sstr}   "
          f"★★★★ bit7 DAMPER duty {100.0 * damp.mean():.3f}%   "
          f"unknown-state {int(d['state_unknown'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"blinker {100 * (d['cs_lchg'] > 0.5).mean():.1f}%  "
          f"ST==4 {int((d['sstat'] == 4).sum())}  ST==3 {int((d['sstat'] == 3).sum())}  "
          f"mic {n_snd}  imu {len(a_hw)}/{len(g_hw)}  ws {len(wst)}  sendcan {len(sct)}  "
          f"rpm {len(rp)}"
          + (f" ({np.percentile(rp[rok], 5):.0f}..{np.percentile(rp[rok], 95):.0f})"
             if rok.any() else "") +
          f"  gears {gsum}  events {len(events)}")
    return d


def _write_imu(tag, t0, a_hw, a_mono, a_v, a_st, g_hw, g_mono, g_v, g_st):
    """`{tag}_imu.npz` in `extract/extract_imu_cache.py`'s EXACT schema -- the sensor's OWN lattice.

    🛑 NOT resampled onto the CAN grid. The comma's LSM6DS3TR-C shares no signal path with the EPS,
    which is the whole point; putting it on the 100 Hz CAN lattice would destroy the independence.
    `t` is referenced to the SAME t0 as the CAN cache, via the median hardware-vs-logMono offset.
    """
    a_hw, g_hw = np.array(a_hw, float), np.array(g_hw, float)
    a_mono, g_mono = np.array(a_mono, float), np.array(g_mono, float)
    A = np.array(a_v, float).reshape(-1, 3)
    G = np.array(g_v, float).reshape(-1, 3)
    off_a = float(np.median(a_mono - a_hw)) if len(a_hw) else np.nan
    off_g = float(np.median(g_mono - g_hw)) if len(g_hw) else np.nan
    np.savez_compressed(
        OUT / f"{tag}_imu.npz",
        at=a_hw + off_a - t0, at_mono=a_mono - t0,
        ax=A[:, 0], ay=A[:, 1], az=A[:, 2], a_status=np.array(a_st, float),
        gt=g_hw + off_g - t0, gt_mono=g_mono - t0,
        gx=G[:, 0], gy=G[:, 1], gz=G[:, 2], g_status=np.array(g_st, float),
        a_hw_off=np.array([off_a]), g_hw_off=np.array([off_g]),
        a_off_sd=np.array([float(np.std(a_mono - a_hw)) if len(a_hw) else np.nan]),
        g_off_sd=np.array([float(np.std(g_mono - g_hw)) if len(g_hw) else np.nan]),
        t0_mono=np.array([t0]))


# ======================================================================= THE EXPOSURE CENSUS =======
V_EDGES = [0, 0.5, 1, 2, 3, 4, 6, 8, 9.4, 12.5, 15, 18.7, 20, 22, 25, 30, 40]
R_EDGES = [0, 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256, 1024]
EP_MIN_S = 1.0          # drop sub-second latActive chatter
EP_MERGE_S = 1.0        # merge two episodes separated by less than this


def _runs(mask, t, min_s=0.0, merge_s=0.0):
    """Maximal runs of a boolean mask on a (possibly gappy) time base -> [(t0, t1), ...]."""
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    idx = np.flatnonzero(m)
    brk = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[brk + 1]]
    ends = np.r_[idx[brk], idx[-1]]
    runs = [(float(t[s]), float(t[e])) for s, e in zip(starts, ends)]
    if merge_s > 0:
        merged = [list(runs[0])]
        for s, e in runs[1:]:
            if s - merged[-1][1] <= merge_s:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        runs = [tuple(r) for r in merged]
    return [r for r in runs if r[1] - r[0] >= min_s]


def _hist(x, edges, w):
    """Seconds in each bin (plus an overflow bin), from a per-sample weight `w` in seconds."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    h, _ = np.histogram(x[ok], bins=list(edges) + [np.inf], weights=np.full(int(ok.sum()), w))
    labs = [f"{edges[i]}-{edges[i + 1]}" for i in range(len(edges) - 1)] + [f"{edges[-1]}-inf"]
    assert len(labs) == len(h), "the histogram label table does not tile the bins"
    return {labs[i]: round(float(h[i]), 3) for i in range(len(h))}


def summarize():
    """Read the caches back off disk and write `_scratch/out/_r5d_extract_summary.json`.

    Deliberately reads the CACHE, not in-memory state, so the summary is also a round-trip check.
    """
    from collections import Counter

    segs, missing, T, LAT, V, RATE, B4 = [], [], [], [], [], [], []
    STATE_ALL, DAMP_ALL, PROBE_ALL = [], [], []
    for s in SEGS:
        p = OUT / f"{PFX}{s}.npz"
        if not p.exists():
            missing.append(s)
            continue
        z = np.load(p, allow_pickle=True)
        t, fs = np.asarray(z["t"], float), float(fs_lattice({"t": np.asarray(z["t"], float)}))
        dt = np.diff(t)
        raw14 = np.asarray(z["raw14A"], float)
        b4 = np.asarray(z["raw14_b4"], int)
        ws = np.asarray(z["ws_mean"], float)
        ok = np.isfinite(ws) & (np.asarray(z["cs_v"], float) > 1.0)
        segs.append(dict(
            seg=s, n=int(len(t)), span_s=round(float(t[-1] - t[0]), 3), fs=round(fs, 4),
            n_gaps_gt_50ms=int((dt > 0.05).sum()), max_gap_s=round(float(dt.max()), 4),
            n_dup_timestamps=int((dt == 0).sum()),
            n_raw_14A=int(len(raw14)), n_raw_18F=int(len(z["raw18F"])),
            n_raw_1D0=int(len(z["ws_t"])), n_raw_0E4_bus=int(len(z["raw0E4"])),
            n_sendcan_0E4=int(len(z["sc_t"])), n_e4_loopback=int(len(z["e4hist"])),
            n_imu_acc=int(len(np.load(OUT / f"{PFX}{s}_imu.npz")["at"])),
            n_imu_gyr=int(len(np.load(OUT / f"{PFX}{s}_imu.npz")["gt"])),
            n_mic=int(len(z["snd_t"])), n_rpm=int(len(z["rpm_t"])),
            cs_wheelSpeeds_max=round(float(z["cs_ws_max"][0]), 6),
            ws_vego_med_abs_err_ms=(round(float(np.median(np.abs(ws[ok] - np.asarray(
                z["cs_v"], float)[ok]))), 4) if ok.sum() > 50 else None),
            vego_min=round(float(np.asarray(z["cs_v"], float).min()), 3),
            vego_max=round(float(np.asarray(z["cs_v"], float).max()), 3),
            lat_pct=round(100.0 * float((np.asarray(z["cc_lat"], float) > 0.5).mean()), 3),
            state_counts={int(k): int(v) for k, v in
                          zip(*np.unique(np.asarray(z["state"], int), return_counts=True))},
            damp_duty_pct=round(100.0 * float(np.asarray(z["damp_nz"], float).mean()), 4),
            t0_mono=float(z["t0_mono"][0]), wall_t0=float(z["wall_t0"][0])))
        T.append(t + float(z["t0_mono"][0]))
        LAT.append(np.asarray(z["cc_lat"], float) > 0.5)
        V.append(np.asarray(z["cs_v"], float))
        RATE.append(np.asarray(z["rate_c"], float))
        STATE_ALL.append(np.asarray(z["state"], int))
        DAMP_ALL.append(np.asarray(z["damp_nz"], float) > 0.5)
        PROBE_ALL.append(np.asarray(z["probe"], int))
        B4.append(b4)

    # 🛑 SORT BY ABSOLUTE TIME, and reorder EVERY channel with the SAME permutation. A segment
    # ordering taken from the filename index and a mask taken from wall time is how two channels
    # get silently misaligned by one segment.
    order = np.argsort([t[0] for t in T])
    T = np.concatenate([T[i] for i in order])
    lat = np.concatenate([LAT[i] for i in order])
    v = np.concatenate([V[i] for i in order])
    rate = np.concatenate([RATE[i] for i in order])
    state = np.concatenate([STATE_ALL[i] for i in order])
    damp = np.concatenate([DAMP_ALL[i] for i in order])
    probe = np.concatenate([PROBE_ALL[i] for i in order])
    b4all = np.concatenate([B4[i] for i in order])
    fs = float(np.median([g["fs"] for g in segs]))
    w = 1.0 / fs

    eps_raw = _runs(lat, T)
    eps = _runs(lat, T, min_s=EP_MIN_S, merge_s=EP_MERGE_S)
    ep_dur = [round(b - a, 3) for a, b in eps]

    # ---- flight condition (1): congested lane-marked arterial, engaged, ~15 min, many re-engages --
    arterial = lat & (v > 1.0) & (v < CRUISE_MIN_MS)
    # ---- flight condition (2): steady >= 20 m/s cruise, engaged, 8-10 min ------------------------
    cruise = lat & (v >= CRUISE_MIN_MS)
    cruise_runs = _runs(cruise, T, min_s=5.0, merge_s=2.0)

    def _tyre(lo, hi, mask):
        return round(float((mask & (v >= lo) & (v < hi)).sum()) * w, 2)

    out = dict(
        route=ROUTE, build=BUILD, rwd=RWD_NAME,
        cache_dir=str(OUT), prefix=PFX, segments_expected=SEGS, segments_missing=missing,
        fs_lattice_hz=round(fs, 4),
        totals=dict(
            n_samples=int(len(T)),
            duration_s=round(float(len(T)) * w, 2),
            wallclock_span_s=round(float(T[-1] - T[0]), 2),
            engaged_s=round(float(lat.sum()) * w, 2),
            engaged_pct=round(100.0 * float(lat.mean()), 3),
            manual_s=round(float((~lat).sum()) * w, 2),
            moving_s=round(float((v > 1.0).sum()) * w, 2),
            engaged_moving_s=round(float((lat & (v > 1.0)).sum()) * w, 2),
            engaged_creep_s=round(float((lat & (v <= CREEP_MAX_MS) & (v > 0.3)).sum()) * w, 2),
            manual_creep_s=round(float(((~lat) & (v <= CREEP_MAX_MS) & (v > 0.3)).sum()) * w, 2)),
        episodes=dict(
            definition=f"maximal runs of carControl.latActive, merged across gaps <= {EP_MERGE_S}s, "
                       f"minimum duration {EP_MIN_S}s",
            n_raw=len(eps_raw), n=len(eps),
            durations_s=ep_dur,
            total_s=round(float(sum(ep_dur)), 2),
            median_s=round(float(np.median(ep_dur)), 3) if ep_dur else None,
            p10_s=round(float(np.percentile(ep_dur, 10)), 3) if ep_dur else None,
            p90_s=round(float(np.percentile(ep_dur, 90)), 3) if ep_dur else None,
            longest_s=round(max(ep_dur), 3) if ep_dur else None),
        speed_hist_s=dict(all=_hist(v, V_EDGES, w), engaged=_hist(v[lat], V_EDGES, w),
                          manual=_hist(v[~lat], V_EDGES, w), units="seconds per m/s bin"),
        rate_hist_s=dict(
            channel="rate_c = CAN 0x14A bytes 2:3 x -1.0, column STEER_ANGLE_RATE, deg/s",
            all=_hist(np.abs(rate), R_EDGES, w), engaged=_hist(np.abs(rate[lat]), R_EDGES, w),
            units="seconds per |deg/s| bin"),
        byte4_census=dict(
            note="INDEPENDENT count off `raw14_b4` -- every 0x14A src-1 frame as it arrived, no "
                 "hold, no grid. Cross-check only; a sibling agent decodes this in depth.",
            n_frames=int(len(b4all)),
            full_byte={f"0x{int(k):02X}": int(c) for k, c in
                       zip(*np.unique(b4all, return_counts=True))},
            bits_7_3={int(k): int(c) for k, c in
                      zip(*np.unique((b4all & PROBE_MASK) >> STATE_SHIFT, return_counts=True))},
            bits_6_3_state={int(k): int(c) for k, c in
                            zip(*np.unique((b4all & STATE_FIELD) >> STATE_SHIFT,
                                           return_counts=True))},
            bit7_damper_set=int(((b4all & BIT_DAMP_NZ) != 0).sum()),
            bit7_damper_duty_pct=round(100.0 * float(((b4all & BIT_DAMP_NZ) != 0).mean()), 4),
            bits_2_0_status={int(k): int(c) for k, c in
                             zip(*np.unique(b4all & STATUS_MASK, return_counts=True))},
            outside_v74_alphabet={f"0x{int(k):02X}": int(c) for k, c in
                                  zip(*np.unique(b4all, return_counts=True))
                                  if (int(k) & PROBE_MASK) not in LEGAL_BYTE4},
            void_state0_frames=int(((b4all & STATE_FIELD) == 0).sum())),
        probe_on_lattice=dict(
            state_counts={int(k): int(c) for k, c in
                          zip(*np.unique(state, return_counts=True))},
            damp_duty_pct=round(100.0 * float(damp.mean()), 4),
            damp_duty_engaged_pct=(round(100.0 * float(damp[lat].mean()), 4) if lat.any() else None),
            damp_duty_manual_pct=(round(100.0 * float(damp[~lat].mean()), 4)
                                  if (~lat).any() else None),
            damp_duty_engaged_creep_pct=(
                round(100.0 * float(damp[lat & (v <= CREEP_MAX_MS)].mean()), 4)
                if (lat & (v <= CREEP_MAX_MS)).any() else None),
            damp_duty_manual_creep_pct=(
                round(100.0 * float(damp[(~lat) & (v <= CREEP_MAX_MS)].mean()), 4)
                if ((~lat) & (v <= CREEP_MAX_MS)).any() else None)),
        flight_conditions=dict(
            cond1_congested_arterial=dict(
                asked="congested lane-marked arterial, ENGAGED, ~15 min (900 s), many "
                      "re-engagements (~40 events)",
                engaged_moving_below_20ms_s=round(float(arterial.sum()) * w, 2),
                n_episodes=len(eps),
                achieved_pct_of_900s=round(100.0 * float(arterial.sum()) * w / 900.0, 1)),
            cond2_highspeed_cruise=dict(
                asked=f"steady >= {CRUISE_MIN_MS} m/s cruise, ENGAGED, 8-10 min (480-600 s)",
                engaged_above_20ms_s=round(float(cruise.sum()) * w, 2),
                n_blocks_ge_5s=len(cruise_runs),
                longest_block_s=(round(max(b - a for a, b in cruise_runs), 2)
                                 if cruise_runs else 0.0),
                achieved_pct_of_480s=round(100.0 * float(cruise.sum()) * w / 480.0, 1)),
            tyre_order_exposure_s=dict(
                note="order 1 is in the 6-9 Hz band at 12.5-18.7 m/s, order 2 at 6.2-9.4, order 3 "
                     "at 4.2-6.2. Clean windows: 9.4-12.5 and >= 20.",
                engaged_dirty={f"{lo}-{hi}": _tyre(lo, hi, lat) for lo, hi in TYRE_DIRTY},
                engaged_clean={f"{lo}-{hi}": _tyre(lo, hi, lat) for lo, hi in TYRE_CLEAN})),
        per_segment=segs)

    # ---- THE BUILD-IDENTITY GUARD, route-wide -----------------------------------------------------
    # 🛑 This decoder certified a V73 log as a V74 win five days ago. Run it, record the verdict.
    try:
        sys.path.insert(0, str(ROOT / "rlog-tools"))
        import decode_v74_probe as V74D
        print("\n" + "=" * 96)
        print("  BUILD IDENTITY GUARD -- decode_v74_probe.identify(), route-wide")
        print("=" * 96)
        not_excluded = bool(V74D.identify(b4=probe, engaged=lat, speed_ms=v, rate_degs=rate, t=T))
        out["build_identity"] = dict(
            guard="rlog-tools/decode_v74_probe.identify()",
            not_excluded_as_v74=not_excluded,
            note="🛑 'not excluded' is NOT 'confirmed'. Every V7x cave writes the same cell in the "
                 "same bit positions and V73's alphabet {8,10} is a SUBSET of V74's legal states. "
                 "The .rwd FILENAME is the only pre-drive discriminator, CAVE_HEX the post-hoc one.")
    except Exception as ex:                                  # noqa: BLE001
        out["build_identity"] = dict(guard="decode_v74_probe.identify()", error=str(ex))

    SUMMARY.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {SUMMARY}")
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    argv = sys.argv[1:]
    summary_only = "--summary" in argv
    args = [int(x) for x in argv if not x.startswith("--")]
    if not summary_only:
        print(f"ROUTE 5D = {BUILD}   rungs:\n    " + "\n    ".join(PROBE_RUNGS) +
              "\n  ★★★★ bit7 IS THE DAMPER'S OWN OUTPUT -- the positive control the last five"
              "\n     probes lacked. 0 is a LEGITIMATE reading; it is NOT a liveness bit."
              "\n  🛑 LIVENESS IS bits 6:3 != 0 (gp-0x67fa can never hold 0). Constant 0 => VOID."
              "\n  🛑 V73's field values {8,10} are LEGAL V74 states -- the alphabets OVERLAP and"
              "\n     this decoder has already certified a V73 log as a V74 win. identify() runs"
              "\n     route-wide in the summary."
              f"\n  rwd: {RWD_NAME}")
        for s in (args or SEGS):
            extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{PFX}{s}")
    if summary_only or not args:
        summarize()
