#!/usr/bin/env python3
"""builds/v50_v79/build_v79_tva.py -- V79 = V78 + TWO u16 damper cells. Probe UNCHANGED. UNFLASHED.

★ WHY THIS BUILD EXISTS -- the operator's directive, 2026-08-07, verbatim:
    "Do not double 0xC63A0, that is what was causing hard faults. You need to double the tables at
     least at 5 mph and keep both tables relu like or monotone increasing."

  · `0xC63A0` STAYS 1024 (stock). It is in `NOT_CARRIED` and its five siblings 0xC63A2..0xC63AA are
    asserted at 1024 as well, on the base, on the built image and on the .rwd readback.
  · "double at 5 mph" -> dose(5 mph, r = 99 ct) 206 -> 412, EXACTLY 2.000x V78.
  · "relu like or monotone increasing" -> FactorE Y strictly INCREASING [0, 897, 912, 927];
    FactorC untouched at [566, 566, 566, 908], already monotone non-decreasing.

THE EDIT -- exactly TWO u16 cells, both in the mode-26 FactorE record
--------------------------------------------------------------------
    Y[1]  449 -> 897        Y[2]  539 -> 912
        after (V79):  X = [0, 119, 2500, 4000]   Y = [0, 897, 912, 927]
        before (V78): X = [0, 119, 2500, 4000]   Y = [0, 449, 539, 927]
FactorC is UNCHANGED, mode 24 stays byte-stock, X is unchanged, every other factor untouched.
🛑 The record address is DEREFERENCED from `FACTOR_E_PTRS = 0xC9F84`, entry 26 -> 0xD780C. Never
   hard-coded into a write.

🛑🛑 `k` = 4.1597 IS FORCED, NOT CHOSEN
--------------------------------------
With `E_X0` = 0 the ramp passes through the origin, so `dose(r) = k*r` and `dose(99) = k*99`.
Doubling the dose at the reference rate therefore DOUBLES the loop gain, exactly. No table shape
avoids it while `E_X0` = 0, and raising `E_X0` is forbidden in a different way (it is what makes the
Y[0] clamp a Coulomb relay). **k = 4.1597 = 2.000x V78, 2.633x V75, 3.000x V76 -- by far the highest
loop gain this kit has ever built.**

🛑🛑🛑 THE ONE THING THE BRIEF'S GUARD DOES NOT COVER -- reported, not silently swallowed
----------------------------------------------------------------------------------------
The brief asks to assert no-clip "wherever FactorC = 566". That is CREEP, and it PASSES exactly:
`(566*927)>>10 = 512` = the ceiling floor, so V79 never clips at or below **80.17 km/h**, the same
as V78. **Above that speed the statement "this edit introduces no clipping V78 did not already
have" is FALSE, and by a very large margin.** At the ceiling FLOOR (512, the `tp+0x7158` fallback
and the LERP's own `Y[0]`):

    speed     V78 first clipping rate      V79 first clipping rate
    -------   --------------------------   -----------------------
     85 km/h  3838 ct = 814 deg/s          **118 ct = 25 deg/s**
     96.7     3490 ct = 741 deg/s          **106 ct = 22 deg/s**
    140       2655 ct = 563 deg/s          ** 77 ct = 16 deg/s**

The kit's OBSERVED steering-rate maximum over its whole corpus is 1,941 counts (route 5d, RULE 8).
Inside that envelope V78 clips at **0 of 305,808** sampled (speed, rate) points and V79 clips at
**79.96%**. ⇒ V79 puts the damper ON THE RAIL for ordinary highway steering whenever the backdrive
index holds the ceiling near its floor. That is RULE 12(b)'s hazard verbatim: the output sign comes
from `gp-0x6abe` while the index is `gp-0x6ac0`, so a railed damper is a Coulomb relay -- the exact
mechanism that got the ReLU plan overruled. It is NOT a reason not to build; it IS a reason the
build is not cleared to fly, and it is the single largest new exposure V79 carries.
⚠ It is ceiling-dependent: at ceiling >= 1024 (backdrive index >= 800) V79 never clips at all.
`gp-0x6ac2`'s operational distribution has NEVER been probed, so which regime the car lives in is
**OPEN**. [EVIDENCE for the arithmetic; the on-car frequency is unknown.]

WHAT IS CARRIED FROM V78 BY BEING BUILT ON IT
---------------------------------------------
The base is V78's own plain image, so the DTC-0x1d interlock (`0xC407E` = 511 against the 512-count
trip in `FUN_00036d74`), the byte-stock friction table, `0xC63A0` = 1024, byte-stock mode 24 and the
68-byte probe cave all come across untouched. Each is asserted BY VALUE here (RULE 3).

🛑 RULE 11 -- `0xC407E` IS A DO-NOT-RAISE CELL. A clamp may be an interlock.
🛑 RULE 12 -- a table's shape is bounded by its OUTPUT CLAMP, not by its breakpoint count.

THE PROBE -- BYTE-IDENTICAL TO V78, and its meaning CHANGES
-----------------------------------------------------------
Not one byte of the cave moves. But the same two thresholds now sit somewhere completely different
on the surface, and the report must say so:

    rung                     V78 trip rate at 5 mph      V79 trip rate at 5 mph
    bit6  |gp-0x6bd0| >= 192   93 ct = 19.7 deg/s          **47 ct = 10.0 deg/s**
    bit7  |gp-0x6bd0| >= 448 3552 ct = 753.8 deg/s         **108 ct = 22.9 deg/s**

🛑 **bit7 STOPS BEING A NO-CLIP GUARANTEE.** On V78 it was predicted never to fire, and its null
proved no clipping occurred anywhere on the drive. On V79 it fires above 22.9 deg/s at creep -- just
ABOVE the design reference rate `R_OP` = 99 ct = 21.0 deg/s -- so it becomes a routinely-firing,
roughly-50%-duty rung inside exactly the grind-#1 bursts this build is dosed for. It still carries
information (it is now the rail-proximity indicator at speed), but **a non-zero bit7 on V79 is
EXPECTED and is not evidence of a fault.** bit6 at 10.0 deg/s is close to always-on while steering.

CAVE DISCIPLINE
---------------
🛑 Growing a cave is this kit's ONLY bricking class -- V24, V27 and V48B all bricked the ECU. This
build does not write the cave at all: it re-derives V78's 68 bytes from `build_v78_tva.build_cave()`,
asserts the base already carries them, re-disassembles them from the image and RE-EMULATES them.
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
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HERE)

if hasattr(sys.stdout, "reconfigure"):          # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, encoders, crc_block_map)
import build_v68_tva as V68                # noqa: E402  (cave geometry constants)
import build_v76_v38base_tva as V76B       # noqa: E402  (interlock + CRC + census helpers)
import build_v78_tva as V78                # noqa: E402  (the BASE build -- cave + pins + encoders)
import v76_surface as VS                   # noqa: E402  (the evaluator mirror, per-instruction)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000

# =====================================================================================================
# THE BASE -- V78 (which sits on V76, which sits on V38)
# =====================================================================================================
SRC_BIN = plain_image_path("_v78_v76base_ey1_449_dose206_plain_image.bin")
SRC_SHA256 = "c8d8e5e1c606dd920ccec8d41ea6398c73dbe473f58912092770e700ffd50ab1"
SRC_RWD_SHA256 = "305234c37f797d0476b89ac793b414d6b0d5ba7cbbadf665d6e64778fe091afb"
STOCK_BIN = stock_fw_path("code.bin")

# ⚠ A BUILD-SPECIFIC image name, per the recorded plain-image-overwrite hazard: two V70 cuts both
# wrote `_v70_plain_image.bin` and the second destroyed the first's snapshot, leaving a flashable
# artefact no gate could check.
BIN_OUT = str(plain_image_path("_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin"))
# 🛑 Paths this build must NEVER write -- above all its own BASE.
FORBIDDEN_OVERWRITE = {
    str(plain_image_path("_v78_v76base_ey1_449_dose206_plain_image.bin")),
    str(plain_image_path("_v76_v38base_relu_damper_plain_image.bin")),
    str(plain_image_path("_v76_gate_fb_arm5244_gateprobe_plain_image.bin")),
    str(plain_image_path("_v76_v38base_relu_damper_probe6b26_plain_image.bin")),
    str(plain_image_path("_v77_C63A0.1024_v74base_plain_image.bin")),
    str(plain_image_path("_v77b_C63A0.1024_v75base_plain_image.bin")),
}

TAG = "V79-V78BASE-EY1.897-EY2.912-dose412-probe-6bd0-63fd-67fa"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")

# =====================================================================================================
# 🛑🛑 THE SAFETY-CRITICAL INTERLOCK -- inherited, asserted here BY VALUE (RULE 3 / RULE 11)
# =====================================================================================================
FAULT_CLAMP_ADDR = V76B.FAULT_CLAMP_ADDR        # 0xC407E, the friction-lane clamp
FAULT_CLAMP_MAX = V76B.FAULT_CLAMP_MAX          # 511
FAULT_THRESH_ADDR = V76B.FAULT_THRESH_ADDR      # 0xC4004, the f32 FUN_00036d74 compares against
FAULT_THRESH_BYTES = V76B.FAULT_THRESH_BYTES    # 0000003f
FAULT_TRIP_COUNTS = V76B.FAULT_TRIP_COUNTS      # 512
NOT_CARRIED = V76B.NOT_CARRIED                  # includes 0xC63A0 = 1024

# 🛑🛑 THE OPERATOR'S EXPLICIT MUST-NOT-CHANGE CELL, and its five siblings. 0xC63A0 flew at 2048 on
#     V74 and V75 ONLY, and BOTH hard-faulted. It is 1024 here and stays 1024.
C63A0_BLOCK = tuple(range(0xC63A0, 0xC63AC, 2))     # 0xC63A0 .. 0xC63AA
C63A0_VALUE = 1024

# =====================================================================================================
# GROUP 1 -- THE TWO CALIBRATION CELLS
# =====================================================================================================
FACTOR_C_PTRS, FACTOR_E_PTRS = V76B.FACTOR_C_PTRS, V76B.FACTOR_E_PTRS      # 0xC9E9C / 0xC9F84
FACTOR_B_PTRS, FACTOR_D_PTRS = V76B.FACTOR_B_PTRS, V76B.FACTOR_D_PTRS
CEILING_PTRS, FRICTION_PTRS = V76B.CEILING_PTRS, V76B.FRICTION_PTR_ARRAY
# 🛑 SIX arrays, not five -- the friction records are the sixth, and V74's x1.5 lived there.
ALL_PTR_ARRAYS = {"FactorB": FACTOR_B_PTRS, "FactorC": FACTOR_C_PTRS, "FactorD": FACTOR_D_PTRS,
                  "FactorE": FACTOR_E_PTRS, "ceiling": CEILING_PTRS, "friction": FRICTION_PTRS}
N_SLOTS_SCAN = V76B.N_SLOTS_SCAN                # 58 -- the FactorC array's true extent
N_MODES = V76B.N_MODES                          # 34
LIVE_MODE, MANUAL_MODE = V76B.LIVE_MODE, V76B.MANUAL_MODE      # 26 engaged / 24 manual
rec_len = V76B.rec_len                          # 4 + 4*count  -- NOT a flat 0x18 window
REC_STRIDE, REC_DATA_LEN = V76B.REC_STRIDE, V76B.REC_DATA_LEN  # 0x14 / 18
EXPECT_ADDR = V76B.EXPECT_ADDR                  # {("C",24):0xD67E4, ("C",26):0xD77D0, ...}

# The V78 base contents of the mode-26 records, asserted before writing.
BASE_C26 = ([2240, 3840, 5120, 8960], [566, 566, 566, 908])
BASE_E26 = ([0, 119, 2500, 4000], [0, 449, 539, 927])
NEW_C26 = BASE_C26                              # 🛑 FactorC is NOT TOUCHED by this build
NEW_E26 = ([0, 119, 2500, 4000], [0, 897, 912, 927])

R_OP = 99                       # counts; the measured in-burst median rate for grind #1 (21.0 deg/s)
SPEED_CTS_PER_KMH = VS.SPEED_CTS_PER_KMH        # 64.0
RATE_CTS_PER_DEGS = VS.RATE_CTS_PER_DEGS        # 4.7121
DOSE_TARGET = 412                               # EXACTLY 2x V78's 206, on the integer surface
V78_DOSE, V76_DOSE, V75_DOSE = 206, 137, 137
SPEED_5MPH_CT = 515                             # 5 mph = 8.04672 km/h -> 515 counts
CEILING_FLOOR = 512                             # the tp+0x7158 fallback AND the ceiling LERP's Y[0]
FLAT_C = 566                                    # FactorC's flat value, 0 .. 80.17 km/h

# The independent statement of the write list. Asserted against what this builder actually emits.
# 🛑 Y[i] lives at rec + 2 + 2*n + 2*i with n = 4  =>  Y[1] = 0xD780C+12 = 0xD7818, Y[2] = 0xD781A.
EXPECTED_WRITES = {0xD7818: (449, 897, "FactorE m26 Y[1]"),
                   0xD781A: (539, 912, "FactorE m26 Y[2]")}

# =====================================================================================================
# GROUP 2 -- THE PROBE CAVE (CARRIED, NOT REWRITTEN)
# =====================================================================================================
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = V78.CAVE_EXTENT              # 🛑 68. THE PROVEN EXTENT. NEVER GROW IT.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK        # 0x55C0E, `movea -0x1518,gp,r6`
HOOK_RETURN, HOOK_RETURN_INSN = V78.HOOK_RETURN, V78.HOOK_RETURN_INSN
BD0_DISP = V78.BD0_DISP                    # -0x6BD0, the damper output
BIT_STATE5, BIT_MODEIDX = V78.BIT_STATE5, V78.BIT_MODEIDX
BIT_DAMP_LO, BIT_DAMP_HI = V78.BIT_DAMP_LO, V78.BIT_DAMP_HI
DAMP_LO_THRESH, DAMP_HI_THRESH = V78.DAMP_LO_THRESH, V78.DAMP_HI_THRESH      # 192 / 448
LEGAL_PAYLOAD_HI, ILLEGAL_BIT5 = V78.LEGAL_PAYLOAD_HI, V78.ILLEGAL_BIT5

SPEED_GATE, RATE_GATE = 0x7D00, 0x32C9      # FactorC gate @0x344E0, FactorE gate @0x345FA


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


# =====================================================================================================
# Record helpers -- every address is DEREFERENCED, never hard-coded into a write
# =====================================================================================================
def rec_addr(buf, ptrs, mode):
    return u32(buf, ptrs + 4 * mode)


def read_rec(buf, ptrs, mode):
    """-> (addr, count, X, Y). Reads the count from the record itself; never assumes 4.

    🛑 Layout: base+0 u16 count | base+2 n x i16 X | base+2+2n n x i16 Y | base+2+4n u16 terminator.
    X starts at base+2, NOT base+4 -- getting that wrong silently reads [X1,X2,X3,Y0]."""
    off = rec_addr(buf, ptrs, mode)
    n = u16(buf, off)
    assert 1 <= n <= 16, f"record @0x{off:05X} claims count={n} -- refusing to parse"
    X = [s16(buf, off + 2 + 2 * i) for i in range(n)]
    Y = [s16(buf, off + 2 + 2 * n + 2 * i) for i in range(n)]
    return off, n, X, Y


def write_rec(buf, ptrs, mode, X, Y):
    """Write a record IN PLACE. 🛑 Writes exactly 2+4*count bytes; never the full 0x14 stride."""
    off = rec_addr(buf, ptrs, mode)
    n = u16(buf, off)
    assert len(X) == len(Y) == n, \
        f"record @0x{off:05X} has count={n} but {len(X)} points were supplied -- changing the " \
        f"count would change rec_len ({rec_len(n)} -> {rec_len(len(X))}) and could spill"
    for i, v in enumerate(X):
        struct.pack_into("<h", buf, off + 2 + 2 * i, v)
    for i, v in enumerate(Y):
        struct.pack_into("<h", buf, off + 2 + 2 * n + 2 * i, v)
    return off, 2 + 4 * n


def assert_write_addresses(buf, label):
    """🛑 The two write addresses are DERIVED from the dereferenced record, then compared with the
    independently-stated `EXPECTED_WRITES`. A pointer-array misread cannot silently retarget."""
    off = rec_addr(buf, FACTOR_E_PTRS, LIVE_MODE)
    n = u16(buf, off)
    derived = {off + 2 + 2 * n + 2 * i for i in (1, 2)}
    assert derived == set(EXPECTED_WRITES), (
        f"🛑 {label}: Y[1]/Y[2] derive to {sorted(map(hex, derived))} but the spec says "
        f"{sorted(map(hex, EXPECTED_WRITES))}")
    return off


def assert_no_aliasing(buf, label):
    """🛑 GUARD 7. Nothing else may own the bytes we write, in ANY of the six arrays.

    Uses `rec_len = 4 + 4n` per record -- NOT a flat 0x18 window. V73's guard window was 4 bytes too
    wide and false-positived across adjacent modes. Also reports the nearest OTHER record."""
    write_addrs = set(EXPECTED_WRITES)
    nearest = None
    for name, ptrs in ALL_PTR_ARRAYS.items():
        owners = {}
        for m in range(N_SLOTS_SCAN):
            r = rec_addr(buf, ptrs, m)
            n = u16(buf, r)
            if 1 <= n <= 16:
                owners.setdefault((r, rec_len(n)), []).append(m)
        for a in write_addrs:
            for (rec, ln), modes in owners.items():
                if rec <= a < rec + ln:
                    assert name == "FactorE" and modes == [LIVE_MODE], (
                        f"🛑 {label}: write 0x{a:05X} lands inside {name} record 0x{rec:05X}, owned "
                        f"by modes {modes} -- it would leak outside mode {LIVE_MODE}")
                else:
                    d = rec - a if rec > a else a - (rec + ln) + 1
                    if nearest is None or d < nearest[0]:
                        nearest = (d, name, rec, modes)
    live_e = rec_addr(buf, FACTOR_E_PTRS, LIVE_MODE)
    for name, ptrs in (("FactorC", FACTOR_C_PTRS), ("FactorE", FACTOR_E_PTRS)):
        owners = {}
        for m in range(N_SLOTS_SCAN):
            owners.setdefault(rec_addr(buf, ptrs, m), []).append(m)
        live = rec_addr(buf, ptrs, LIVE_MODE)
        assert owners[live] == [LIVE_MODE], \
            f"{label}: {name} m{LIVE_MODE} record 0x{live:05X} is ALSO used by modes " \
            f"{[m for m in owners[live] if m != LIVE_MODE]} -- the edit would leak"
        assert rec_addr(buf, ptrs, MANUAL_MODE) != live, \
            f"{label}: {name}: modes {MANUAL_MODE} and {LIVE_MODE} share a record"
    assert live_e == EXPECT_ADDR[("E", LIVE_MODE)]
    return nearest


def assert_pointer_arrays_stock(buf, stock, label):
    """🛑 GUARD 7. All SIX pointer arrays byte-identical to STOCK over all 34 modes."""
    for name, ptrs in ALL_PTR_ARRAYS.items():
        got = bytes(buf[ptrs:ptrs + 4 * N_MODES])
        want = bytes(stock[ptrs:ptrs + 4 * N_MODES])
        assert got == want, \
            f"🛑 {label}: the {name} pointer array @0x{ptrs:05X} differs from STOCK over " \
            f"{N_MODES} modes -- a retargeted pointer would silently move every edit"
    return len(ALL_PTR_ARRAYS)


def assert_untouched_surfaces(buf, base, label):
    """FactorB/C/D, the ceiling and friction must stay as the base has them, in BOTH modes.

    Also asserts the edited record's HEADER (the point count -- a change would move rec_len) and its
    TAIL (the 2 bytes whose mis-sizing produced the V73 spill)."""
    for name, ptrs in (("FactorB", FACTOR_B_PTRS), ("FactorC", FACTOR_C_PTRS),
                       ("FactorD", FACTOR_D_PTRS), ("ceiling", CEILING_PTRS),
                       ("friction", FRICTION_PTRS)):
        for mode in (MANUAL_MODE, LIVE_MODE):
            off = rec_addr(buf, ptrs, mode)
            n = u16(buf, off)
            ln = 2 + 4 * n
            assert bytes(buf[off:off + ln]) == bytes(base[off:off + ln]), \
                f"🛑 {label}: {name} mode {mode} @0x{off:05X} CHANGED -- this build touches only " \
                f"FactorE mode {LIVE_MODE}"
    off = rec_addr(buf, FACTOR_E_PTRS, LIVE_MODE)
    assert u16(buf, off) == 4 == u16(base, off), \
        f"🛑 {label}: FactorE m{LIVE_MODE} HEADER changed -- the point count must stay 4"
    assert bytes(buf[off + REC_DATA_LEN:off + REC_STRIDE]) == b"\x00\x00", \
        f"🛑 {label}: FactorE m{LIVE_MODE} TAIL is not 0x0000 -- the V73 spill signature"
    _o, _n, cx, cy = read_rec(buf, FACTOR_C_PTRS, LIVE_MODE)
    assert (cx, cy) == NEW_C26, f"🛑 {label}: FactorC m26 is {(cx, cy)}, must stay {NEW_C26}"
    # 🛑 X is not a lever in this build -- assert it separately from Y.
    _o, _n, ex, _ey = read_rec(buf, FACTOR_E_PTRS, LIVE_MODE)
    assert ex == BASE_E26[0] == NEW_E26[0], \
        f"🛑 {label}: FactorE m26 X is {ex} -- this build changes Y ONLY"


def assert_record_geometry(buf, label):
    for (kind, mode), want in EXPECT_ADDR.items():
        ptrs = FACTOR_C_PTRS if kind == "C" else FACTOR_E_PTRS
        got = rec_addr(buf, ptrs, mode)
        assert got == want, \
            f"{label}: Factor{kind} mode {mode} dereferences to 0x{got:05X}, expected 0x{want:05X}"
        n = u16(buf, got)
        assert n == 4 and rec_len(n) == REC_STRIDE == 0x14, \
            f"{label}: Factor{kind} m{mode} count={n}, rec_len=0x{rec_len(n):X} (expected 4 / 0x14)"


# =====================================================================================================
# 🛑🛑 THE INTERLOCK GUARD, the operator's DO-NOT-DOUBLE cell, and the levers not to resurrect
# =====================================================================================================
def assert_fault_interlock(buf, label):
    return V76B.assert_fault_interlock(buf, label)


def assert_not_carried(buf, label):
    for addr, (want, why) in NOT_CARRIED.items():
        got = u16(buf, addr)
        assert got == want, f"{label}: 0x{addr:05X} = {got}, expected {want} -- {why}"


def assert_c63a0_block(buf, stock, label):
    """🛑🛑 GUARD 5 -- THE OPERATOR'S EXPLICIT DIRECTIVE, 2026-08-07:
       "Do not double 0xC63A0, that is what was causing hard faults."

    0xC63A0 was V72's LEVER C. It flew at 2048 on V74 and V75 ONLY and BOTH hard-faulted. It is
    1024 (stock) on this base and stays 1024, together with its five siblings 0xC63A2..0xC63AA."""
    for a in C63A0_BLOCK:
        got, want = u16(buf, a), u16(stock, a)
        assert got == C63A0_VALUE, (
            f"🛑🛑 {label}: 0x{a:05X} = {got}, MUST be {C63A0_VALUE}. The operator's directive is "
            f"explicit: do not double 0xC63A0. It flew at 2048 on V74/V75 and both hard-faulted.")
        assert got == want, f"🛑 {label}: 0x{a:05X} = {got} but STOCK carries {want}"
    return len(C63A0_BLOCK)


def assert_manual_mode_stock(buf, stock, label):
    """🛑 GUARD 7. Mode 24 is MANUAL steering. Byte-identical to STOCK, not merely to the base."""
    for kind, ptrs in (("C", FACTOR_C_PTRS), ("E", FACTOR_E_PTRS)):
        off = rec_addr(buf, ptrs, MANUAL_MODE)
        assert off == EXPECT_ADDR[(kind, MANUAL_MODE)]
        got, want = bytes(buf[off:off + REC_STRIDE]), bytes(stock[off:off + REC_STRIDE])
        assert got == want, (
            f"🛑 {label}: Factor{kind} mode {MANUAL_MODE} @0x{off:05X} differs from STOCK "
            f"({want.hex()} -> {got.hex()}) -- manual steering must stay byte-stock")
    for name, ptrs in (("FactorB", FACTOR_B_PTRS), ("FactorD", FACTOR_D_PTRS),
                       ("ceiling", CEILING_PTRS), ("friction", FRICTION_PTRS)):
        off = rec_addr(buf, ptrs, MANUAL_MODE)
        n = u16(buf, off)
        assert bytes(buf[off:off + 2 + 4 * n]) == bytes(stock[off:off + 2 + 4 * n]), \
            f"🛑 {label}: {name} mode {MANUAL_MODE} @0x{off:05X} differs from STOCK"


# =====================================================================================================
# THE SURFACE GUARDS -- through `v76_surface`'s per-instruction evaluator mirror
# =====================================================================================================
def surfaces(img_before, img_after):
    return (VS.Surface(img=bytes(img_before), mode=LIVE_MODE),
            VS.Surface(img=bytes(img_after), mode=LIVE_MODE),
            VS.Surface(img=VS.load("stock"), mode=LIVE_MODE))


def assert_table_shape(X, Y, label):
    """GUARD 1 + GUARD 2 -- the operator's shape constraint, stated as arithmetic."""
    assert all(X[i] < X[i + 1] for i in range(len(X) - 1)), f"{label}: X is not STRICTLY increasing"
    assert all(Y[i] < Y[i + 1] for i in range(len(Y) - 1)), (
        f"🛑 {label}: Y = {Y} is not STRICTLY increasing. The operator asked for 'relu like or "
        f"monotone increasing'; a flat or descending segment is neither.")
    assert Y[0] == 0, (
        f"🛑 {label}: E_Y[0] = {Y[0]} != 0. A non-zero Y[0] is a COULOMB RELAY: the LERP index "
        f"(gp-0x6ac0) and the output sign (gp-0x6abe) are DIFFERENT cells, so it gives constant "
        f"magnitude with a rate-flipped sign -- describing function 4*M0/(pi*A), unbounded as the "
        f"amplitude falls. NEVER RAISE IT.")


def assert_factorC_monotone(S, label):
    """The operator's constraint applied to the OTHER table: FactorC monotone non-decreasing."""
    X, Y = S.XY("C")
    assert all(Y[i] <= Y[i + 1] for i in range(len(Y) - 1)), \
        f"🛑 {label}: FactorC Y = {Y} is not monotone non-decreasing"
    assert all(X[i] < X[i + 1] for i in range(len(X) - 1)), f"{label}: FactorC X not increasing"
    return X, Y


def assert_add_only(S78, S79, STK):
    """🛑 GUARD 4, EXACT and EXHAUSTIVE -- by factor monotonicity, not a subsampled grid.

    |gp-0x6bd0| = min( (C(speed) * E(rate)) >> 10 , ceiling ) with seed = B = D = 1024 (four
    back-to-back `mulu` + logical `shr 0xa` at 0x34684-0x3469C, ZERO add/or). Both `>>10` and the
    ceiling clamp min(|d|, c) are monotone non-decreasing in each factor, and both gates depend only
    on the index, so proving E and C add-only per-axis proves the WHOLE 32000 x 13001 surface.
    """
    for r in range(RATE_GATE):
        e79, e78, es = S79.factorE(r), S78.factorE(r), STK.factorE(r)
        assert (e79 is None) == (e78 is None) == (es is None), f"the FactorE GATE moved at r={r}"
        if e79 is None:
            continue
        assert e79 >= e78 >= es, f"FactorE add-only FAILS at rate {r}: {es} -> {e78} -> {e79}"
    for sp in range(SPEED_GATE):
        c79, c78, cs = S79.factorC(sp), S78.factorC(sp), STK.factorC(sp)
        assert c79 == c78 >= cs, f"FactorC changed or dropped below stock at speed {sp}"
    for w in ("B", "D"):
        assert S79.XY(w) == S78.XY(w) == STK.XY(w), f"Factor{w} moved"
    assert S79.XY("CEIL") == S78.XY("CEIL") == STK.XY("CEIL"), "the ceiling record moved"
    assert S79.ceil_fallback == S78.ceil_fallback == CEILING_FLOOR
    return RATE_GATE, SPEED_GATE


def assert_add_only_direct(S79, S78, STK, step_s=53, step_r=71):
    """The required SECOND METHOD: a direct subsampled sweep of the full 2-D surface, vs BOTH the
    base and stock, at the ceiling floor AND at the ceiling ceiling (the clamp is monotone, but the
    add-only claim must survive it -- a clamp can erase an increase, never invert one)."""
    worst_s = worst_b = 0
    at_s = at_b = None
    n = 0
    for bd in (0, 800):
        for sp in range(0, SPEED_GATE, step_s):
            for r in range(0, RATE_GATE, step_r):
                a = S79.mag(sp, r, backdrive_idx=bd)
                b = STK.mag(sp, r, backdrive_idx=bd)
                c = S78.mag(sp, r, backdrive_idx=bd)
                n += 1
                if b - a > worst_s:
                    worst_s, at_s = b - a, (bd, sp, r, a, b)
                if c - a > worst_b:
                    worst_b, at_b = c - a, (bd, sp, r, a, c)
    assert worst_s == 0, f"🛑 add-only vs STOCK FAILS by {worst_s} counts at {at_s}"
    assert worst_b == 0, f"🛑 add-only vs V78 FAILS by {worst_b} counts at {at_b}"
    return n


def assert_no_clip_at_creep(S79, S78):
    """🛑 GUARD 3 -- THE BRIEF'S NO-CLIP GUARD, exactly as specified and exactly as scoped.

    "Assert the product never exceeds 512 wherever FactorC = 566."

    FactorC is constant 566 over the whole flat band, so the maximum product there is
    (566 * E_max) >> 10 with E_max taken over EVERY gated rate index -- an exact supremum, not a
    sample. It comes out at exactly 512 = the ceiling FLOOR, so `d > c` is never true and no point
    that failed to clip on V78 can clip on V79 anywhere in that band, at ANY ceiling the LERP can
    produce (the LERP's own Y[0] is 512 and it only rises).
    """
    flat = [sp for sp in range(SPEED_GATE) if S79.factorC(sp) == FLAT_C]
    assert flat and min(flat) == 0, "FactorC is not flat from 0 -- the guard's premise moved"
    e_max = max(e for e in (S79.factorE(r) for r in range(RATE_GATE)) if e is not None)
    flat_worst = max(((FLAT_C * e) >> 10)
                     for e in (S79.factorE(r) for r in range(RATE_GATE)) if e is not None)
    assert flat_worst == (FLAT_C * e_max) >> 10, "the supremum is not attained at E_max"
    assert flat_worst <= CEILING_FLOOR, (
        f"🛑 GUARD 3 FAILS: max (566*E)>>10 over the flat band is {flat_worst} > the ceiling floor "
        f"{CEILING_FLOOR} -- this edit WOULD introduce new clipping at creep")
    # second method: the clip FLAG straight off the evaluator, over the flat band, every gated rate
    n79 = n78 = 0
    for sp in range(0, max(flat) + 1, 37):
        for r in range(0, RATE_GATE, 23):
            n79 += S79.output(sp, r, backdrive_idx=0)[1]
            n78 += S78.output(sp, r, backdrive_idx=0)[1]
    assert n79 == n78 == 0, \
        f"🛑 GUARD 3 second method: {n79} clipped points on V79 ({n78} on V78) inside the flat band"
    return flat_worst, e_max, len(flat), max(flat)


def first_clip_rate(S, speed, ceil):
    for r in range(RATE_GATE):
        e = S.factorE(r)
        if e is not None and ((S.factorC(speed) * e) >> 10) > ceil:
            return r
    return None


def clip_census(S78, S79):
    """🛑🛑 THE GUARD THE BRIEF DID NOT ASK FOR, MEASURED AND REPORTED -- NOT a build blocker.

    The brief's no-clip guard is scoped to FactorC = 566, i.e. creep. Above 80.17 km/h FactorC
    rises to 908 and the global statement "no clipping V78 did not already have" is FALSE. This
    function quantifies exactly how false, because RULE 12(b) says a railed damper IS the Coulomb
    relay (index gp-0x6ac0, sign gp-0x6abe are different cells) -- the hazard that got the ReLU
    plan overruled. Returns everything the report needs; asserts only what still holds.
    """
    rows = []
    for kmh in (5, 20, 35, 60, 80, 85, 96.7, 120, 140):
        sp = int(round(kmh * SPEED_CTS_PER_KMH))
        if sp >= SPEED_GATE:
            continue
        rows.append((kmh, S79.factorC(sp),
                     first_clip_rate(S78, sp, CEILING_FLOOR),
                     first_clip_rate(S79, sp, CEILING_FLOOR)))
    # 🛑 The highest speed at which V79 provably never clips, at the ceiling floor -- computed in ONE
    #    O(SPEED_GATE) pass, exactly. At a fixed speed C is constant and E |-> (C*E)>>10 is monotone
    #    non-decreasing, so the supremum over ALL gated rates is (C(sp)*E_max)>>10: no rate scan is
    #    needed. The clip-free set is then asserted to be a PREFIX (it must be, since FactorC is
    #    monotone non-decreasing, but that is asserted elsewhere and is not assumed here).
    e_max_all = max(e for e in (S79.factorE(r) for r in range(RATE_GATE)) if e is not None)
    clip_free = [sp for sp in range(SPEED_GATE)
                 if ((S79.factorC(sp) * e_max_all) >> 10) <= CEILING_FLOOR]
    assert clip_free and clip_free == list(range(len(clip_free))), \
        "the clip-free speed set is not a prefix -- FactorC is not monotone in speed"
    clip_free_max = clip_free[-1]
    assert first_clip_rate(S79, clip_free_max, CEILING_FLOOR) is None, \
        "the closed-form clip-free boundary disagrees with a direct rate scan"
    assert first_clip_rate(S79, clip_free_max + 1, CEILING_FLOOR) is not None, \
        "the closed-form clip-free boundary is not tight"
    # clip fraction inside the kit's OBSERVED rate envelope (route 5d max, RULE 8)
    n = n78 = n79 = 0
    for sp in range(0, SPEED_GATE, 29):
        for r in range(0, 1942, 7):
            n += 1
            n78 += S78.output(sp, r, backdrive_idx=0)[1]
            n79 += S79.output(sp, r, backdrive_idx=0)[1]
    # ceiling sensitivity -- at 1024 the clamp is never reached at all
    ceil_rows = []
    for c in (512, 640, 768, 1024):
        ceil_rows.append((c, [first_clip_rate(S79, int(round(k * SPEED_CTS_PER_KMH)), c)
                              for k in (80, 96.7, 140)]))
    # what still holds: the PRE-CLAMP maximum product is unchanged, because E_max is unchanged
    c_max = max(S79.factorC(sp) for sp in range(SPEED_GATE))
    e_max79 = max(e for e in (S79.factorE(r) for r in range(RATE_GATE)) if e is not None)
    e_max78 = max(e for e in (S78.factorE(r) for r in range(RATE_GATE)) if e is not None)
    assert e_max79 == e_max78 == 927, "E_max moved -- the 'same peak product' statement would break"
    peak = (c_max * e_max79) >> 10
    assert peak == (c_max * e_max78) >> 10 == 821, "the peak product moved"
    assert clip_free_max >= 5120, \
        f"🛑 V79 clips below 80 km/h (clip-free only to {clip_free_max} ct) -- GUARD 3's band shrank"
    return rows, clip_free_max, (n, n78, n79), ceil_rows, c_max, peak


def first_rate_for(S, speed, thresh):
    for r in range(RATE_GATE):
        if S.mag(speed, r) >= thresh:
            return r
    return None


def probe_trip_rates(S78, S79):
    """🛑 The probe is byte-identical to V78, but the SURFACE moved under it. Recompute both rungs'
    trip rates exactly, on both builds, so the operator knows what the wire will actually show."""
    rows = {}
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        rows[thr] = {}
        for kmh in (5, 20, 35, 60, 80, 96.7, 140):
            sp = int(round(kmh * SPEED_CTS_PER_KMH))
            rows[thr][kmh] = (first_rate_for(S78, sp, thr), first_rate_for(S79, sp, thr))
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        assert any(v[1] is not None for v in rows[thr].values()), \
            f"🛑 the |gp-0x6bd0| >= {thr} rung is STRUCTURALLY DEAD on V79 -- it can never fire"
    lo79, lo78 = rows[DAMP_LO_THRESH][5][1], rows[DAMP_LO_THRESH][5][0]
    hi79, hi78 = rows[DAMP_HI_THRESH][5][1], rows[DAMP_HI_THRESH][5][0]
    assert lo79 < lo78 and hi79 < hi78, \
        "neither rung discriminates V78 from V79 -- the probe would not measure the dose step"
    # 🛑 the reading that CHANGES: bit7 was a no-clip guarantee on V78 because it was predicted
    #    never to fire. On V79 it fires just above the design reference rate.
    assert hi79 is not None and hi79 > R_OP, (
        "bit7 now fires at or below R_OP -- it would be saturated, not a ~50% duty rung; re-size it")
    assert DAMP_HI_THRESH < CEILING_FLOOR, \
        "bit7's threshold no longer sits strictly below the ceiling floor"
    return rows, (lo78, lo79), (hi78, hi79)


# =====================================================================================================
# The gp-cell census / CRC -- shared, unchanged
# =====================================================================================================
cell_census = V76B.cell_census
assert_cell_censuses = V78.assert_cell_censuses
assert_pins = V78.assert_pins
owning_block = V76B.owning_block
refresh_crcs = V76B.refresh_crcs
assert_crc_chain = V76B.assert_crc_chain
changed_runs = V76B.changed_runs


def main():
    print("=" * 102)
    print("  V79 -- V78 + FactorE m26 Y[1] 449->897 and Y[2] 539->912 (dose 412 = 2.000x V78)")
    print("=" * 102)
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it"
    assert "v79" in os.path.basename(BIN_OUT).lower() and "V79" in TAG, \
        "the artefact names must carry the build number"

    base = bytes(SRC_BIN.read_bytes())
    assert len(base) == 0x100000, f"the base must be 1 MiB, got 0x{len(base):X}"
    assert hashlib.sha256(base).hexdigest() == SRC_SHA256, "the base is NOT the V78 plain image"
    stock = bytes(STOCK_BIN.read_bytes())
    print(f"\n  base  {SRC_BIN.name}\n        sha256 {SRC_SHA256}  VERIFIED")

    # ---- BASE IDENTITY beyond the hash: V78's own cave, re-derived from its builder ------------
    v78_cave, v78_listing = V78.build_cave()
    assert bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v78_cave, \
        "the base's cave is not the one builds/v50_v79/build_v78_tva.py emits -- WRONG BASE"
    assert bytes(base[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "the base's hook is not already the `jarl` to the cave"
    assert bytes(stock[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, \
        "the STOCK hook site is not the `movea` the cave replays"
    assert bytes(base[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "0x55C12 is not `mov 0x8,r7` -- the proof that r7 is dead across the hook"
    print("        base cave re-derived from build_v78_tva.build_cave(): IDENTICAL (68 B)")

    # ---- everything checkable BEFORE a byte is written -----------------------------------------
    n_enc = V78._self_check_encoders(base)
    n_pay = V78._check_wire_model()
    n_pins = assert_pins(base, "V78 base")
    n_ptr = assert_pointer_arrays_stock(base, stock, "V78 base")
    nearest = assert_no_aliasing(base, "V78 base")
    assert_untouched_surfaces(base, base, "V78 base")
    assert_record_geometry(base, "V78 base")
    assert_write_addresses(base, "V78 base")
    clamp, thresh, fric = assert_fault_interlock(base, "V78 base")
    assert_not_carried(base, "V78 base")
    n_c63 = assert_c63a0_block(base, stock, "V78 base")
    assert_manual_mode_stock(base, stock, "V78 base")
    assert_cell_censuses(base, range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT), True, "V78 base")
    assert_crc_chain(base, "V78 base")
    print(f"  base OK: {n_enc} encoder round-trips, {n_pins} pins, {n_ptr} pointer arrays == STOCK "
          f"over {N_MODES} modes,\n           record geometry, write addresses, no aliasing, "
          f"censuses, CRC chain 50/50, {n_pay} legal payloads")
    print(f"  🛑 INTERLOCK on the base: 0xC407E = {clamp} (<= {FAULT_CLAMP_MAX}), "
          f"0xC4004 = {thresh} => trip at {FAULT_TRIP_COUNTS} counts, friction m26 @0x{fric:05X} STOCK")
    print(f"  🛑🛑 OPERATOR DIRECTIVE: 0xC63A0 = {u16(base, 0xC63A0)} on the base "
          f"({n_c63} cells 0xC63A0..0xC63AA all == {C63A0_VALUE} == STOCK). NOT DOUBLED, NOT TOUCHED.")
    print(f"  nearest OTHER record to the write set: {nearest[0]} bytes "
          f"({nearest[1]} @0x{nearest[2]:05X}, modes {nearest[3][:4]})")

    code = bytearray(base)
    touched = []

    # ---- GROUP 1 -- the two calibration cells ---------------------------------------------------
    print("\n" + "-" * 102)
    print("  GROUP 1 -- FactorE mode 26 (ENGAGED), TWO u16 cells.  Mode 24, FactorC and X UNTOUCHED.")
    print("-" * 102)
    off, n, ox, oy = read_rec(code, FACTOR_E_PTRS, LIVE_MODE)
    assert (ox, oy) == BASE_E26, f"FactorE m26 base is X={ox} Y={oy}, expected {BASE_E26}"
    assert off == u32(code, FACTOR_E_PTRS + 4 * LIVE_MODE) == EXPECT_ADDR[("E", LIVE_MODE)]
    print(f"    pointer array 0x{FACTOR_E_PTRS:05X} + 26*4 = 0x{FACTOR_E_PTRS + 104:05X} "
          f"-> record 0x{off:05X}  (n={n}, rec_len={rec_len(n)})")
    assert_table_shape(*NEW_E26, label="FactorE m26 (new)")
    slack_before = bytes(code[off + REC_DATA_LEN:off + REC_STRIDE])
    woff, wlen = write_rec(code, FACTOR_E_PTRS, LIVE_MODE, *NEW_E26)
    assert wlen == REC_DATA_LEN, f"wrote {wlen}B, expected {REC_DATA_LEN}"
    assert bytes(code[off + REC_DATA_LEN:off + REC_STRIDE]) == slack_before, \
        "🛑 FactorE m26: the 2 slack bytes changed -- this is the V73 spill"
    touched.extend(range(off, off + REC_DATA_LEN))
    print(f"    FactorE m26 @0x{woff:05X}  X {ox} -> {NEW_E26[0]}   (UNCHANGED)")
    print(f"    {'':>18s}  Y {oy} -> {NEW_E26[1]}")
    for a, (old, new, lbl) in sorted(EXPECTED_WRITES.items()):
        print(f"      0x{a:05X}  {lbl:<20s} {old:5d} = 0x{old:04X}  ->  {new:5d} = 0x{new:04X}   "
              f"bytes {old.to_bytes(2, 'little').hex()} -> {new.to_bytes(2, 'little').hex()}")

    runs1 = changed_runs(base, code)
    got_writes = {}
    for a, ln in runs1:
        for w in range(a, a + ln, 2):
            got_writes[w] = (u16(base, w), u16(code, w))
    assert set(got_writes) == set(EXPECTED_WRITES), \
        f"the write set differs from the spec: {sorted(map(hex, set(got_writes) ^ set(EXPECTED_WRITES)))}"
    for a, (old, new, lbl) in EXPECTED_WRITES.items():
        assert got_writes[a] == (old, new), f"0x{a:05X} ({lbl}): got {got_writes[a]}, spec {(old, new)}"
    print(f"    {len(EXPECTED_WRITES)} halfword writes = {2 * len(EXPECTED_WRITES)} bytes "
          f"({sum(ln for _a, ln in runs1)} changed bytes in {len(runs1)} run)")
    assert_manual_mode_stock(code, stock, "after group 1")
    assert_untouched_surfaces(code, base, "after group 1")
    assert_fault_interlock(code, "after group 1")
    assert_not_carried(code, "after group 1")
    assert_c63a0_block(code, stock, "after group 1")
    assert_pointer_arrays_stock(code, stock, "after group 1")
    assert_write_addresses(code, "after group 1")

    # ---- THE SURFACE GUARDS ----------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  SURFACE GUARDS  (v76_surface's per-instruction mirror of FUN_00034350)")
    print("-" * 102)
    S78, S79, STK = surfaces(base, code)
    d79 = S79.mag(SPEED_5MPH_CT, R_OP)
    d78 = S78.mag(SPEED_5MPH_CT, R_OP)
    e99 = S79.factorE(R_OP)
    c515 = S79.factorC(SPEED_5MPH_CT)
    k79 = ((c515 * NEW_E26[1][1]) >> 10) / (NEW_E26[0][1] - NEW_E26[0][0])
    k78 = ((S78.factorC(SPEED_5MPH_CT) * BASE_E26[1][1]) >> 10) / (BASE_E26[0][1] - BASE_E26[0][0])
    assert c515 == FLAT_C and d79 == DOSE_TARGET and d78 == V78_DOSE, \
        f"the target arithmetic does not reproduce: E(99)={e99} C(515)={c515} dose={d79}"
    assert d79 == 2 * d78, f"the dose is {d79}, not exactly 2x V78's {d78}"
    print(f"    E({R_OP}) = {NEW_E26[1][1]}*{R_OP}//{NEW_E26[0][1]} = {e99}  ·  C(515) = {c515}  ·  "
          f"dose = ({c515}*{e99})>>10 = {d79}")
    print(f"    dose {d79} = {d79 / d78:.4f}x V78's {d78}  ·  {d79 / V75_DOSE:.4f}x V75's {V75_DOSE}"
          f"  ·  {d79 / V76_DOSE:.4f}x V76's {V76_DOSE}")
    print(f"    k(truncated) = {k79:.4f}   = {k79 / k78:.4f}x V78 ({k78:.4f})  "
          f"= {k79 / 1.5798:.4f}x V75 (1.5798)  = {k79 / 1.3866:.4f}x V76 (1.3866)")
    print(f"    🛑 k IS FORCED, NOT CHOSEN: E_X0 = {NEW_E26[0][0]}, so dose(r) = k*r exactly and "
          f"dose({R_OP}) = k*{R_OP}.\n       Doubling the dose at the reference rate NECESSARILY "
          f"doubles the loop gain. No table shape avoids it.")

    assert_table_shape(*S79.XY("E"), label="GUARD 1/2 built FactorE m26")
    cX, cY = assert_factorC_monotone(S79, "GUARD 1 built FactorC m26")
    print(f"    GUARD 1  FactorE Y {S79.XY('E')[1]} STRICTLY increasing; X strictly increasing;")
    print(f"             FactorC Y {cY} monotone non-decreasing (untouched)     PASS")
    print(f"    GUARD 2  E_Y[0] == 0 retained -- no Coulomb relay at the LERP's own hard clamp  PASS")

    nr, ns = assert_add_only(S78, S79, STK)
    ndirect = assert_add_only_direct(S79, S78, STK)
    print(f"    GUARD 4  add-only vs STOCK **and** vs V78, EXACT by factor monotonicity: FactorE "
          f"over all\n             {nr:,} gated rate indices and FactorC over all {ns:,} gated "
          f"speed indices (B/D/ceiling identical)")
    print(f"             second method -- direct 2-D sweep, {ndirect:,} (ceiling,speed,rate) "
          f"points, worst drop 0   PASS")

    flat_worst, e_max, nflat, flat_top = assert_no_clip_at_creep(S79, S78)
    print(f"    GUARD 3  NO NEW CLIPPING AT CREEP (the brief's guard, exactly as scoped).")
    print(f"             FactorC == {FLAT_C} over {nflat:,} speed indices, 0 .. {flat_top} ct = "
          f"{flat_top / SPEED_CTS_PER_KMH:.2f} km/h.\n             max ({FLAT_C}*E)>>10 over EVERY "
          f"gated rate = {flat_worst} <= the ceiling FLOOR {CEILING_FLOOR}  (E_max = {e_max})")
    print(f"             second method -- the evaluator's own clip flag: 0 clipped points on V79 "
          f"and 0 on V78\n             across the whole flat band   PASS")

    # ---- 🛑🛑 THE HIGH-SPEED CLIP CENSUS -- reported, NOT a build blocker -----------------------
    rows, clip_free_max, (nsamp, n78c, n79c), ceil_rows, c_max, peak = clip_census(S78, S79)
    print("\n    🛑🛑 WHAT GUARD 3 DOES **NOT** COVER -- the clip set ABOVE the flat band")
    print(f"       FactorC rises {FLAT_C} -> {c_max} from {flat_top} ct to 8960 ct, so above "
          f"{clip_free_max / SPEED_CTS_PER_KMH:.2f} km/h\n       the global claim 'no clipping V78 "
          f"did not already have' is FALSE. At the ceiling FLOOR ({CEILING_FLOOR}):")
    print(f"       {'km/h':>7} {'FactorC':>8} | {'V78 first clip':>26} | {'V79 first clip':>26}")
    for kmh, c, a, b in rows:
        f = lambda r: "never" if r is None else f"{r} ct = {r / RATE_CTS_PER_DEGS:.0f} deg/s"
        print(f"       {kmh:>7} {c:>8} | {f(a):>26} | {f(b):>26}")
    print(f"       inside the kit's OBSERVED rate envelope (<= 1,941 ct, route 5d / RULE 8), over "
          f"{nsamp:,}\n       sampled (speed, rate) points at the ceiling floor:  "
          f"V78 clips {n78c:,} ({100 * n78c / nsamp:.2f}%)  ·  "
          f"**V79 clips {n79c:,} ({100 * n79c / nsamp:.2f}%)**")
    print("       ceiling sensitivity -- first clipping rate at 80 / 96.7 / 140 km/h:")
    for c, rs in ceil_rows:
        cells = ["never" if r is None else f"{r} ct" for r in rs]
        print(f"         ceiling {c:>4} : " + "  ".join(f"{x:>9}" for x in cells))
    print(f"       ⇒ the PRE-CLAMP peak product is UNCHANGED at {peak} (C_max {c_max} x E_max "
          f"{e_max}); what moves\n         is the RATE at which the rail is reached. RULE 12(b): a "
          f"railed damper whose sign comes\n         from gp-0x6abe while its index is gp-0x6ac0 IS "
          f"a Coulomb relay. **This is V79's largest\n         new exposure and it is NOT closed by "
          f"argument.**  gp-0x6ac2's distribution is UNPROBED.")

    # ---- THE PROBE'S TRIP RATES ------------------------------------------------------------------
    trip, (lo78, lo79), (hi78, hi79) = probe_trip_rates(S78, S79)
    print("\n    PROBE TRIP RATES -- the cave is byte-identical to V78; the SURFACE moved under it")
    print(f"       {'km/h':>7} | {'bit6 >=192  V78':>18} {'V79':>18} | "
          f"{'bit7 >=448  V78':>18} {'V79':>18}")
    for kmh in (5, 20, 35, 60, 80, 96.7, 140):
        cells = []
        for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
            for r in trip[thr][kmh]:
                cells.append("never" if r is None
                             else f"{r} ct = {r / RATE_CTS_PER_DEGS:.1f} d/s")
        print(f"       {kmh:>7} | {cells[0]:>18} {cells[1]:>18} | {cells[2]:>18} {cells[3]:>18}")
    print(f"       🛑 bit7 STOPS BEING A NO-CLIP GUARANTEE. On V78 it needed {hi78} ct "
          f"({hi78 / RATE_CTS_PER_DEGS:.0f} deg/s) at 5 mph and\n          was predicted never to "
          f"fire; on V79 it needs {hi79} ct ({hi79 / RATE_CTS_PER_DEGS:.1f} deg/s), just ABOVE "
          f"R_OP = {R_OP} ct\n          ({R_OP / RATE_CTS_PER_DEGS:.1f} deg/s). It becomes a "
          f"~50%-duty rung inside the grind-#1 bursts. A NON-ZERO bit7 on\n          V79 is "
          f"EXPECTED and is NOT evidence of a fault.")
    print(f"       bit6 needs {lo79} ct ({lo79 / RATE_CTS_PER_DEGS:.1f} deg/s) vs {lo78} ct on V78 "
          f"-- close to always-on while steering.\n          It remains the dose-in-force "
          f"discriminator: a {lo78 / lo79:.2f}x shift in the rate required to trip it.")

    # ---- GROUP 2 -- the probe cave, CARRIED UNCHANGED --------------------------------------------
    print("\n" + "-" * 102)
    print(f"  GROUP 2 -- the {CAVE_EXTENT}-byte probe cave @0x{CAVE_BASE:05X}: "
          f"CARRIED FROM V78, NOT REWRITTEN")
    print("-" * 102)
    redis = V78.redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    for addr, raw, text in redis:
        print(f"    0x{addr:05X}  {raw.hex():<8s}  {text}")
    assert b"".join(r for _a, r, _t in redis) == v78_cave, \
        "the re-disassembly does not reconstruct the base's cave bytes"
    assert [(a, r) for a, r, _t in redis] == [(a, r) for a, r, _t in v78_listing], \
        "the base's cave does not re-disassemble to build_v78_tva's emitted listing"
    n_emul = V78._check_emulator(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    print(f"\n    RE-EMULATED from the image bytes on a V850 interpreter, compared to the mirror "
          f"over\n    {n_emul:,} (state, mode, |d|, status) combinations -- ALL MATCH. "
          f"ZERO cave bytes changed.")
    assert bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == \
        bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v78_cave, "the cave moved"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "the hook must stay the base's `jarl` -- this build does not re-hook"
    assert bytes(code[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        bytes(base[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the cave tail is not virgin 0xFF"

    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert_cell_censuses(code, cave_span, True, "after group 2")
    assert_pins(code, "after group 2")

    # ---- CRC ------------------------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  CRC")
    print("-" * 102)
    changed = refresh_crcs(code, touched)
    for trailer, (old, new, bstart) in sorted(changed.items()):
        touched.extend(range(trailer, trailer + 4))
        print(f"    block [0x{bstart:05X}, 0x{trailer:05X})  trailer 0x{old:08X} -> 0x{new:08X}")
    n_blocks = assert_crc_chain(code, "V79")
    print(f"    {len(changed)} trailer(s) rewritten; full chain re-verified: {n_blocks}/50 blocks PASS")

    # ---- the full attributed diff ---------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  FULL BYTE DIFF  V78 -> V79")
    print("-" * 102)
    e_rec = rec_addr(code, FACTOR_E_PTRS, LIVE_MODE)
    groups = {}
    for a, ln in changed_runs(base, code):
        if e_rec <= a and a + ln <= e_rec + REC_STRIDE:
            g = "1 FactorE m26 cells"
        elif CAVE_BASE <= a < CAVE_BASE + CAVE_EXTENT:
            g = "2 probe cave (MUST BE ABSENT)"
        elif any(t <= a < t + 4 for t in changed):
            g = "3 CRC trailer"
        else:
            g = "UNATTRIBUTED"
        groups.setdefault(g, []).append((a, ln))
    total = 0
    for g in sorted(groups):
        n = sum(ln for _a, ln in groups[g])
        total += n
        print(f"    {g:30s} {len(groups[g]):3d} run(s) {n:4d} byte(s)   "
              f"{', '.join(f'0x{a:05X}+{ln}' for a, ln in groups[g][:5])}"
              f"{' ...' if len(groups[g]) > 5 else ''}")
    assert "UNATTRIBUTED" not in groups, f"UNATTRIBUTED bytes: {groups.get('UNATTRIBUTED')}"
    assert "2 probe cave (MUST BE ABSENT)" not in groups, "the cave changed -- it must not"
    # 🛑 COUNT CELLS, NOT BYTES. V78's single edit moved only ONE byte because 300 and 449 share a
    #    high byte. Here BOTH bytes of BOTH cells move (449=0x01C1 -> 897=0x0381, 539=0x021B ->
    #    912=0x0390), and the two cells are adjacent, so the four bytes come out as ONE run.
    tbl = groups["1 FactorE m26 cells"]
    tbl_bytes = sum(ln for _a, ln in tbl)
    assert len(EXPECTED_WRITES) == 2 and tbl_bytes <= 4, \
        f"the table delta is {tbl_bytes} bytes across {len(tbl)} run(s) -- expected 2 CELLS (<=4 B)"
    lo_cell, hi_cell = min(EXPECTED_WRITES), max(EXPECTED_WRITES)
    for a, ln in tbl:
        assert lo_cell <= a and a + ln <= hi_cell + 2, \
            f"a table diff run 0x{a:05X}+{ln} escapes the two cells 0x{lo_cell:05X}..0x{hi_cell + 1:05X}"
    print(f"    TOTAL {sum(len(v) for v in groups.values())} runs, {total} bytes, ALL ATTRIBUTED")
    print(f"    🛑 table delta = 2 CELLS (0x{lo_cell:05X}, 0x{hi_cell:05X}) = {tbl_bytes} changed "
          f"bytes in {len(tbl)} run.\n       BOTH bytes of BOTH cells move here (V78's single edit "
          f"moved only one byte, because 300 and 449\n       share a high byte). COUNT CELLS, NOT "
          f"BYTES -- then check the bytes anyway.")

    # ---- write + .rwd ---------------------------------------------------------------------------
    assert BIN_OUT not in FORBIDDEN_OVERWRITE, \
        f"🛑 {BIN_OUT} is a retired or BASE snapshot path -- a same-number re-cut has destroyed a " \
        "predecessor's snapshot before and produced an artefact no gate could check"
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image is already there (on disk "
            f"{hashlib.sha256(existing).hexdigest()}, about to write "
            f"{hashlib.sha256(bytes(code)).hexdigest()}). Rename it deliberately, then re-run.")
    if os.path.exists(OUT) and Path(OUT).read_bytes() and existing is None:
        raise SystemExit(f"🛑 {OUT} exists but its plain image does not -- refusing to proceed")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n        SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "the source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "container source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V79 output")
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    assert rwd_sha != SRC_RWD_SHA256, "the output .rwd is byte-identical to V78's -- nothing changed"

    # ---- 🛑 EVERYTHING re-derived FROM THE READBACK --------------------------------------------
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec[START:END]) == bytes(code[START:END]), "the decoded payload != the built image"

    assert_pins(dec, "readback")
    assert_pointer_arrays_stock(dec, stock, "readback")
    assert_no_aliasing(dec, "readback")
    assert_untouched_surfaces(dec, base, "readback")
    assert_record_geometry(dec, "readback")
    assert_write_addresses(dec, "readback")
    rb_clamp, rb_thresh, rb_fric = assert_fault_interlock(dec, "readback")
    assert_not_carried(dec, "readback")
    rb_c63 = assert_c63a0_block(dec, stock, "readback")
    assert_manual_mode_stock(dec, stock, "readback")
    assert_cell_censuses(dec, cave_span, True, "readback")
    assert_crc_chain(dec, "readback")
    _o, _n, rx, ry = read_rec(dec, FACTOR_E_PTRS, LIVE_MODE)
    assert (rx, ry) == NEW_E26, f"readback FactorE m26 is X={rx} Y={ry}, expected {NEW_E26}"
    _o, _n, rcx, rcy = read_rec(dec, FACTOR_C_PTRS, LIVE_MODE)
    assert (rcx, rcy) == NEW_C26, "readback FactorC m26 moved -- it must be untouched"
    S_rb = VS.Surface(img=bytes(dec), mode=LIVE_MODE)
    assert S_rb.mag(SPEED_5MPH_CT, R_OP) == DOSE_TARGET == 2 * V78_DOSE, \
        "the readback dose is not 412 = 2x V78"
    assert_table_shape(*S_rb.XY("E"), label="readback FactorE m26")
    assert_factorC_monotone(S_rb, "readback FactorC m26")
    assert_no_clip_at_creep(S_rb, S78)
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v78_cave, \
        "the readback cave is not V78's"
    assert bytes(dec[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "readback: the hook is not the `jarl` to the cave"
    assert bytes(dec[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "readback: the hook's return site 0x55C12 was disturbed"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]).count(HOOK_STOCK) == 1, \
        "readback: the displaced `movea` is not replayed EXACTLY once in the cave"
    assert bytes(dec[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the readback cave tail is not 0xFF"
    redis_rb = V78.redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    assert [(a, r) for a, r, _t in redis_rb] == [(a, r) for a, r, _t in v78_listing], \
        "the readback cave does not re-disassemble to V78's emitted listing"
    assert V78._check_emulator(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])) == n_emul
    rb_runs = changed_runs(base, dec)
    assert sum(ln for _a, ln in rb_runs) == total, "the readback diff size differs"

    print("\n  READBACK -- re-derived FROM THE DECODED .rwd BYTES: the FactorE record via its")
    print("     pointer array, the dose 412, the shape guards, the creep no-clip guard, FactorC and")
    print(f"     mode-24 identity vs STOCK, all six pointer arrays, the DTC-0x1d interlock, "
          f"0xC63A0\n     ({rb_c63} cells) = 1024, the dropped levers, all {n_pins} pins, every "
          f"probed cell's census, the\n     whole 68-byte cave, its re-disassembly, its "
          f"re-EMULATION, the cave tail, and the full\n     50-block CRC chain. ALL PASS.")
    print(f"\n  wrote {OUT}\n        SHA256 {rwd_sha}")

    print("\n" + "=" * 102)
    print("  V79 BUILT on the V78 base.  🛑 UNFLASHED. NOT A FLASH CLEARANCE. NOT CLEARED TO FLY.")
    print(f"  ★ TWO CELLS: FactorE m26 Y[1] 449 -> 897 @0x{lo_cell:05X}, Y[2] 539 -> 912 "
          f"@0x{hi_cell:05X}.")
    print(f"     dose(5 mph, {R_OP} ct) = {DOSE_TARGET} = EXACTLY 2.000x V78's {V78_DOSE}, "
          f"{DOSE_TARGET / V75_DOSE:.3f}x V75's {V75_DOSE}.")
    print(f"  🛑 k = {k79:.4f} -- FORCED by E_X0 = 0, not chosen. {k79 / k78:.3f}x V78, "
          f"{k79 / 1.5798:.3f}x V75, {k79 / 1.3866:.3f}x V76.\n     THE HIGHEST LOOP GAIN THIS KIT "
          f"HAS EVER BUILT. GATE 2 (magnitude AND phase) is NOT satisfied by argument.")
    print(f"  🛑 INTERLOCK CARRIED: 0xC407E = {rb_clamp} against a {FAULT_TRIP_COUNTS}-count trip "
          f"(0xC4004 = {rb_thresh});")
    print(f"     friction m26 @0x{rb_fric:05X} byte-stock; MODE 24 byte-STOCK; FactorC untouched;")
    print(f"     🛑🛑 0xC63A0 = {u16(dec, 0xC63A0)} (STOCK, NOT DOUBLED) -- the operator's explicit "
          f"directive.")
    print(f"  🛑 NEW CLIPPING ABOVE {clip_free_max / SPEED_CTS_PER_KMH:.1f} km/h: V79 rails at "
          f"{rows[6][3]} ct ({rows[6][3] / RATE_CTS_PER_DEGS:.0f} deg/s) at 96.7 km/h where V78\n"
          f"     needed {rows[6][2]} ct. {100 * n79c / nsamp:.1f}% of the observed-envelope grid "
          f"clips at the ceiling floor vs 0.0% on V78.\n     RULE 12(b): a railed damper IS a "
          f"Coulomb relay. NOT closed by argument. gp-0x6ac2 is UNPROBED.")
    print(f"  ★ probe UNCHANGED from V78 (0 cave bytes moved) but bit7 now trips at {hi79} ct "
          f"({hi79 / RATE_CTS_PER_DEGS:.1f} deg/s) at\n     creep, not {hi78} -- it is NO LONGER a "
          f"no-clip guarantee. bit6 trips at {lo79} ct "
          f"({lo79 / RATE_CTS_PER_DEGS:.1f} deg/s).")
    print(f"     bit{V78.BITS_CLEAR[0]} is STRUCTURALLY ZERO and bit{BIT_DAMP_HI} ALWAYS implies "
          f"bit{BIT_DAMP_LO}. Legal byte4 & 0xF8 =")
    print(f"     {sorted(hex(v) for v in LEGAL_PAYLOAD_HI)}")
    print("     Any payload with byte4 & 0x20, or bit7 without bit6, is an integrity failure.")
    print("     Read bit3 FIRST: all-zero on bits 7,6,4,3 for a whole drive = the cave never fired.")
    print("  🛑 GRIND #1 ONLY. The micro-ratchet is DOSE-INDEPENDENT (slope CI contains zero);")
    print("     this build is NOT expected to change it and must not be reported as if it were.")
    print("  🛑 Flash ONLY on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    main()
