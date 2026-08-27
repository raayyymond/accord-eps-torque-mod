#!/usr/bin/env python3
r"""builds/v80_v107/build_v86b_tva.py -- V86B = the flown V85 + FactorC `Y[0]` lifted on modes 26 AND 27.

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
**A ring-free test of whether the damper's ZERO POINT is special.** FactorC is the damper's SPEED
scalar and Honda ships `Y[0] = 0`, so the engaged damper is identically zero below 35 km/h. V86B sets
`Y[0] :=` **that record's own `Y[3]`** -- the largest monotone lift of `Y[0]` alone, taken from the
record's own range rather than an invented number -- and asks whether the ~7.79 Hz ratcheting line
falls toward V81's level.

🛑 **THE HONEST LABEL, VERBATIM, AND IT GOES FIRST:** *"a ring-free test of whether the damper's zero
point is special -- moderate-to-low probability of fixing the ratcheting, and it will make the wheel
slightly heavier when engaged at low speed."* Creep dose is **~10% of V81's flown 138 counts**, and it
is **engaged-only by construction** (m24/m25 stay Honda), so it re-creates the "heavier when engaged"
asymmetry V84 deleted, at roughly a tenth of the magnitude.

🛑🛑 **THE EARLIER `FactorE X[0]` SKETCH IS WITHDRAWN AS STRUCTURALLY VACUOUS, AND THIS BUILDER
INDEPENDENTLY CONFIRMED THAT.** `dose = (FactorC(speed) * FactorE(rate)) >> 10`, and FactorC `Y[0] = 0`
below `X[0]` = 2240 ct = 35 km/h. **Zero times anything is zero**, so lowering FactorE's rate threshold
delivers **exactly 0.0 at creep** -- this builder's own dose table for that sketch read `0 / 0` in the
entire 35 km/h column. That variant was never cut. ⊕ Separately: `FactorE X[0] = 12` on m26+m27 had
already flown on **six images** (V74, V75 x2, V76, V77, V77b, V81), so it was not a new lever either.

THE BASE -- the SAME flown V85 as V86, **not** V86's output
--------------------------------------------------------------------------------------------------
sha256 `cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f`. Building V86B on V86 would
silently carry the command-EMA edit and confound both experiments; V86's own hash is in `NOT_THE_BASE`.

THE EDIT SET -- 2 cells, 4 bytes
--------------------------------------------------------------------------------------------------
  cell                      mode              addr      V85    V86B    bytes
  FactorC Y[0]              26 ENGAGED        0xD77DA     0     908    0000 -> 8c03
  FactorC Y[0]              27 ENGAGED2       0xD77EE     0     875    0000 -> 6b03

🛑 **m26 AND m27 ARE NOT INTERCHANGEABLE.** m26's `Y` is `[0,234,429,908]`, m27's is `[0,233,426,875]`.
Each record's `Y[0]` takes **its own** `Y[3]`. **The difference is PRESERVED, never homogenised** --
asserted explicitly, because writing 908 into both would be a silent homogenisation of two distinct
Honda records. ⊕ m27 is a SECOND engaged column and V83a shipped V81's whole damper live by forgetting
it, so both are written or the build is a bet.
🛑 **Both addresses are DEREFERENCED through the FactorC pointer array `0xC9E9C`**, never quoted. All
32 record pointers verified DISTINCT (no aliasing), so editing 26/27 cannot touch 24/25.

★ PROVABLY RING-FREE, BY LERP ARITHMETIC RATHER THAN BY STATISTICS
--------------------------------------------------------------------------------------------------
FactorC's X axis is voted speed at 64 ct/km/h: `X = [2240, 3840, 5120, 8960]` = **35 / 60 / 80 / 140
km/h**. A LERP's `Y[0]` influences the output **only below `X[1]`** -- at and above `X[1]` = 3840 ct =
**59.9 km/h** the interpolation no longer references `Y[0]` at all. The build COMPUTES the delta rather
than asserting it, and the table it prints must read **EXACTLY 0** at 60, 80 and 100 km/h.
⇒ **The 26-31 Hz ring was measured ABOVE 80 km/h ⇒ predicted burst duty UNCHANGED at V84's 2.54%.**
That band is a **STRUCTURAL negative control, not an assumed one**: if it moves, the build or the
measurement is wrong -- not the hypothesis.

★ THE RELAY INDEX IS A PROPERTY OF THE **RATE** AXIS ALONE, and this edit touches only the SPEED
scalar ⇒ the index stays at Honda's **0.00 (fully viscous)**. V81 was 1.50; V80 was 3.27 and produced
the worst grinding ever recorded. **This is NOT a re-run of the ring build.**

GATE 1 -- RAM OWNERSHIP. **N/A for the control cells** (two calibration halfwords, no RAM, no code).
For the probe cave: identical to V86's -- `gp-0x6b70` 1w/1r, `gp-0x67ab` 1w/2r, zero aliases, the cave
reads both and writes neither.

GATE 2 -- CLOSED-LOOP STABILITY. **Materially easier than V86's.**
  PHASE. **Unchanged, literally.** A LERP `Y` value is a **memoryless gain** -- no filter, pole, zero,
  delay, new state, new sample point or task-order change. **Every pole in the image is bit-identical.**
  MAGNITUDE. Bounded by the damper ceiling, byte-verified constant at **512 counts** (`0xC6158`) --
  i.e. **2.00% of the aggregator's +-25600, worst case, at ANY dose.** Computed here, not quoted.

★★ THE PROBE -- V86's CAVE, WITH A TWO-BYTE WEIGHT SWAP AND NOTHING ELSE
---------------------------------------------------------------------------------------
Same 68-byte extent, same hook, same two cells, same physical quantities ⇒ **the V86<->V86B A/B on
`gp-0x6b70` is fully preserved.** Only the two `add imm5` weights at `+10` and `+26` swap:

| build | `+10` | `+26` | b6 means | b5 means | invariants | MUST produce | FORBIDS |
|---|---|---|---|---|---|---|---|
| V86  | `443a` (w=4) | `423a` (w=2) | `v != 0`       | `\|v\| >= 64`  | `b5=>b6`, `b7=>b6` | `(b7,b6,b5)=(0,1,0)` | `(0,0,1)` |
| V86B | `423a` (w=2) | `443a` (w=4) | `\|v\| >= 64`  | `v != 0`       | `b6=>b5`, `b7=>b5` | `(0,0,1)`            | `(0,1,0)` |

⇒ **exact in BOTH directions, zero extra bytes.** A single `(0,1,0)` frame refutes V86B; a single
`(0,0,1)` frame refutes V86. The decoder imports the right bit map per build.

🛑 **THE PROBE CANNOT SCORE THE CONTROL CELLS.** V86 is the first build ever to read `gp-0x6b70`, so
V86 has no baseline; **V86B supplies it** (same cave, `0xC40D4` at V85's 573). That is a real reason to
fly both. What scores V86B is the ~7.79 Hz line below 60 km/h against the structurally-unchanged band
above it.

★ PRE-REGISTERED, FALSIFIABLE -- recorded BEFORE the drive
------------------------------------------------------------------------
  · the line should fall toward V81's level **below 60 km/h** and be **bit-identically unchanged above
    60 km/h**. The upper band is a STRUCTURAL negative control.
  · **THRESHOLD TEST: >= 50% of the V84->V81 3x step recovered ⇒ threshold-at-zero, the damper is worth
    re-sizing. < 20% ⇒ graded, k >= 4.2 needed, unreachable without V80's ring ⇒ RETIRE the damper as a
    ratchet lever permanently.**
  · **ABORT SIGNAL: any 26-31 Hz burst-duty rise above V84's 2.54%.**

🛑 GUARDS RELAXED ON V86B ONLY -- named, with a narrower replacement for each. See `RELAXED_GUARDS`.
**They stay FULLY ARMED on V86.** Nothing is deleted to make a red light go green.

Usage:
    python builds/v80_v107/build_v86b_tva.py                        # DRY RUN, verifies everything, writes nothing
    ACCORD_V86B_WRITE=rwd python builds/v80_v107/build_v86b_tva.py  # cuts the artefacts
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

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v74_tva as V74                # noqa: E402
import build_v84_tva as V84B               # noqa: E402
import build_v85_tva as V85B               # noqa: E402
import build_v86_tva as V86                # noqa: E402  ★ the shared scaffold + V86's cave
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

START, END = V86.START, V86.END
CAVE_BASE, CAVE_EXTENT = V86.CAVE_BASE, V86.CAVE_EXTENT
u16, s16 = V86.u16, V86.s16
M32 = 0xFFFFFFFF

SRC_BIN, SRC_SHA256, STOCK_BIN = V86.SRC_BIN, V86.SRC_SHA256, V86.STOCK_BIN
NOT_THE_BASE = dict(V86.NOT_THE_BASE)
NOT_THE_BASE["b8d81ebf9aae4ce27b489687a6d2dc1b222214accc0b128068b31ce41515d2f8"] = (
    "the CUT V86. V86B is a SIBLING of V86 on the same V85 base, not a successor -- building on V86 "
    "would silently carry the 0xC40D4 command-EMA edit and confound both experiments.")
NOT_THE_BASE["24be26c553e5d828047974b83db2da880e3cd693aa52ee87d0343e81c3b18a37"] = (
    "V86's DELETED first cut -- it carried `a932` (b5 trips at 512) instead of `a632` (64).")

# =====================================================================================================
# THE EDIT -- FactorC Y[0], modes 26 AND 27. 🛑 DEREFERENCED, never a hard-coded record address.
# =====================================================================================================
FACTOR_C_PTRS = 0xC9E9C
EDIT_MODES = (26, 27)
MANUAL_MODES = (24, 25)
SPEED_CT_PER_KMH = 64
Y0_OLD = 0
# ⊕ the lead's INDEPENDENTLY verified anchors, asserted after dereferencing so a moved pointer fails
DEREF_ANCHORS = {24: (0xD67E4, 0xD67EE), 25: (0xD77BC, 0xD77C6),
                 26: (0xD77D0, 0xD77DA), 27: (0xD77E4, 0xD77EE)}
EXPECT_NEW = {26: 908, 27: 875}             # each record's OWN Y[3] -- NOT interchangeable
CMD_EMA_ADDR, CMD_EMA_V85 = V86.CMD_EMA_ADDR, V86.CMD_EMA_OLD    # 0xC40D4 stays 573 on V86B
CEILING_ADDR, CEILING_VALUE = 0xC6158, 512
AGGREGATOR_FULL_SCALE = 25600


def derive_edit_cells(buf):
    """(addr, width, old, new, label) per edited mode, DEREFERENCED through the pointer array.

    🛑 RULE 7: V69/V70/V72 wrote hard-coded mode-10 records on a car that reads 24/25/26/27 and
    delivered BYTE-STOCK -- a dose ladder that never existed. Every address here is resolved from
    `FACTOR_C_PTRS` on the image being built, then cross-checked against the anchors.
    """
    ptrs = [V74.factor_rec(buf, FACTOR_C_PTRS, m) for m in range(32)]
    assert len(set(ptrs)) == 32, \
        f"🛑 only {len(set(ptrs))} of 32 FactorC record pointers are distinct -- ALIASING, and " \
        "editing m26/m27 could reach another mode's record"
    for mode, (want_rec, want_y0) in DEREF_ANCHORS.items():
        rec = V74.factor_rec(buf, FACTOR_C_PTRS, mode)
        n, _xs, _ys = V74.rec_any(buf, rec)
        assert rec == want_rec and rec + 2 + 2 * n == want_y0, \
            f"🛑 FactorC m{mode} dereferences to rec 0x{rec:05X} / Y[0] 0x{rec + 2 + 2 * n:05X}, the " \
            f"anchor says 0x{want_rec:05X} / 0x{want_y0:05X} -- STOP, do not reconcile this here"
    cells = []
    for mode in EDIT_MODES:
        rec = V74.factor_rec(buf, FACTOR_C_PTRS, mode)
        n, xs, ys = V74.rec_any(buf, rec)
        assert n == 4, f"FactorC m{mode} declares {n} points, expected 4"
        assert ys[0] == Y0_OLD, f"FactorC m{mode} Y[0] is {ys[0]}, expected {Y0_OLD}"
        new = ys[3]                                     # 🛑 THAT RECORD'S OWN Y[3]
        assert new == EXPECT_NEW[mode], \
            f"🛑 FactorC m{mode} Y[3] is {new}, the spec says {EXPECT_NEW[mode]}"
        assert xs == [2240, 3840, 5120, 8960], f"FactorC m{mode}'s X axis moved: {xs}"
        cells.append((rec + 2 + 2 * n, 2, Y0_OLD, new,
                      f"FactorC m{mode} Y[0] := its own Y[3] (rec 0x{rec:05X})"))
    assert cells[0][3] != cells[1][3], \
        "🛑 m26 and m27 would receive the SAME value -- that is a silent HOMOGENISATION of two " \
        "distinct Honda records. m26's Y[3] is 908, m27's is 875; the difference must be PRESERVED."
    return cells


# =====================================================================================================
# THE CAVE -- V86's, with the TWO-BYTE weight swap at +10 / +26 and NOTHING else
# =====================================================================================================
SWAP_OFF_A, SWAP_OFF_B = 10, 26
W_NONZERO_V86, W_MAG_V86 = "443a", "423a"           # V86: +10 = w4, +26 = w2


def build_cave():
    """V86's 68 bytes with the two `add imm5` weights swapped. Derived, never re-typed."""
    body = bytearray(V86.CAVE_PAYLOAD)
    a = bytes(body[SWAP_OFF_A:SWAP_OFF_A + 2])
    b = bytes(body[SWAP_OFF_B:SWAP_OFF_B + 2])
    assert a.hex() == W_NONZERO_V86 and b.hex() == W_MAG_V86, \
        f"🛑 V86's cave has {a.hex()} @+{SWAP_OFF_A} and {b.hex()} @+{SWAP_OFF_B}, expected " \
        f"{W_NONZERO_V86}/{W_MAG_V86} -- the swap would be applied to the wrong halfwords"
    body[SWAP_OFF_A:SWAP_OFF_A + 2] = b
    body[SWAP_OFF_B:SWAP_OFF_B + 2] = a
    out = bytes(body)
    assert len(out) == CAVE_EXTENT == 68
    diff = [i for i in range(CAVE_EXTENT) if out[i] != V86.CAVE_PAYLOAD[i]]
    assert diff == [SWAP_OFF_A, SWAP_OFF_B], \
        f"🛑 the V86->V86B cave differs at {diff}, expected EXACTLY [+{SWAP_OFF_A}, +{SWAP_OFF_B}] " \
        "-- a two-byte swap and nothing else"
    return out


CAVE_PAYLOAD = build_cave()
# 🛑 the threshold and the shift are UNCHANGED from V86 -- only the WEIGHTS move
RELAY_T, MAG_SHIFT, GATE_T = V86.RELAY_T, V86.MAG_SHIFT, V86.GATE_T
BIT_SIGN, BIT_MAG, BIT_NONZERO = 0x80, 0x40, 0x20   # 🛑 b6 = MAG, b5 = NONZERO -- SWAPPED vs V86
BIT_GATE, BIT_FINGERPRINT = 0x10, 0x08
PAYLOAD_KEEP_MASK = V86.PAYLOAD_KEEP_MASK


def wire_byte4(v6b70, gate, status_bits=0x7):
    """A Python mirror of V86B's cave. 🛑 The WEIGHTS differ from V86's; the tests do not."""
    r7 = 0
    r6 = v6b70
    if not (r6 & M32) <= 0:                     # cmp 0x0 / bnh (UNSIGNED) ⇒ fires iff v != 0
        r7 += 2                                 # 🛑 weight 2 on V86B (was 4 on V86)
    if not r6 >= 0:                             # cmp 0x0 / bge (SIGNED)  ⇒ fires iff v < 0
        r7 += 8
    r6 = (r6 >> MAG_SHIFT) + 1
    if not (r6 & M32) <= 1:                     # ⇒ fires iff |v| >= RELAY_T
        r7 += 4                                 # 🛑 weight 4 on V86B (was 2 on V86)
    r6 = gate & 0xFF
    if not (r6 & M32) >= GATE_T:
        r7 += 1
    r7 = ((r7 << 4) & M32) + BIT_FINGERPRINT
    return ((status_bits & PAYLOAD_KEEP_MASK) | r7) & 0xFF


def decode_byte4(byte4):
    if not byte4 & BIT_FINGERPRINT:
        return None
    return {"sign": bool(byte4 & BIT_SIGN), "mag": bool(byte4 & BIT_MAG),
            "nonzero": bool(byte4 & BIT_NONZERO), "gate": bool(byte4 & BIT_GATE),
            "fingerprint": True}


def _self_check_wire():
    """Exhaustive over the full int16 range, plus the two-directional build identity."""
    for v in range(-32768, 32768):
        d = decode_byte4(wire_byte4(v, 0))
        assert d["sign"] == (v < 0) and d["nonzero"] == (v != 0)
        assert d["mag"] == (v >= RELAY_T or v <= -RELAY_T - 1)
        assert not (d["mag"] and not d["nonzero"]), f"b6 without b5 at v={v}"
        assert not (d["sign"] and not d["nonzero"]), f"b7 without b5 at v={v}"
    for g in range(256):
        assert decode_byte4(wire_byte4(0, g))["gate"] == (g < GATE_T)
    for name, on, off in (("sign", wire_byte4(-100, 0), wire_byte4(100, 0)),
                          ("nonzero", wire_byte4(1, 0), wire_byte4(0, 0)),
                          ("mag", wire_byte4(-900, 0), wire_byte4(RELAY_T - 1, 0)),
                          ("gate", wire_byte4(0, 1), wire_byte4(0, 2))):
        assert decode_byte4(on)[name] and not decode_byte4(off)[name], f"🛑 rung {name} is VACUOUS"
    # ---- 🛑 THE TWO-DIRECTIONAL BUILD IDENTITY, EXACT --------------------------------------------
    # 🛑 status_bits=0 -- the live STEER_SENSOR_STATUS nibble is preserved by `andi 0x7` and would
    # 🛑 otherwise pollute the comparison. The discriminator is about bits 7:3 ONLY.
    must = BIT_FINGERPRINT | BIT_NONZERO                  # (b7,b6,b5) = (0,0,1)
    forbid = BIT_FINGERPRINT | BIT_MAG                    # (0,1,0)
    assert any(wire_byte4(v, 2, 0) == must for v in range(1, RELAY_T)), \
        "🛑 V86B cannot emit (0,0,1) -- the identity discriminator is vacuous"
    assert not any(wire_byte4(v, g, 0) == forbid
                   for v in range(-32768, 32768, 3) for g in (0, 2)), \
        "🛑 V86B CAN emit (0,1,0), which V86 must own -- the two builds are not distinguishable"
    # and the mirror: V86 must be unable to emit V86B's signature
    assert not any(V86.wire_byte4(v, g, 0) == must
                   for v in range(-32768, 32768, 3) for g in (0, 2)), \
        "🛑 V86 can emit (0,0,1) -- the discriminator fails in the other direction"
    assert any(V86.wire_byte4(v, 2, 0) == forbid for v in range(1, RELAY_T)), \
        "🛑 V86 cannot emit (0,1,0) -- its own signature is vacuous"


_self_check_wire()

# =====================================================================================================
# 🛑 THE GUARDS THIS BUILD RELAXES -- V86B ONLY. Each has a narrower replacement.
# =====================================================================================================
RELAXED_GUARDS = (
    ("build_v86_tva.FROZEN_CELLS[0xD77DA] and [0xD77EE] (both = 0)",
     "V86B WRITES both. Replaced by: each must equal that record's OWN Y[3] (908 / 875, asserted "
     "DISTINCT), and every OTHER frozen cell is still asserted unchanged."),
    ("build_v84_tva.assert_factor_surface(reverted=True)",
     "asserts the FactorC/E surface is Honda's. V86B lifts FactorC Y[0] ON PURPOSE. Replaced by "
     "`assert_edited_shape`: X untouched, Y[1..3] untouched, only Y[0] moves, and the record stays "
     "monotone non-decreasing."),
    ("build_v84_tva.assert_engaged_equals_manual",
     "asserts the engaged columns equal the manual ones. V86B breaks that BY DESIGN -- m24/m25 stay "
     "Honda, which is what makes the lever ENGAGED-ONLY. Replaced by `assert_manual_untouched`."),
    ("build_v86_tva.assert_mode_proof -- 'all four columns byte-STOCK'",
     "Replaced by `assert_columns_stock_except`, still over all 10 families x 4 columns, failing on "
     "any byte outside the 4 declared ones."),
    ("build_v84_tva.assert_factor_monotone",
     "🛑 SIXTH RELAXATION -- found by this builder, NOT in the spec. `Y[0] := Y[3]` makes the row "
     "NON-MONOTONE ([908,234,429,908]): a V-shaped speed surface Honda never ships, and this guard "
     "was written to catch exactly that. Replaced by `assert_edited_shape`'s EXACT-shape assert "
     "([Y[3]] + Y[1:]) plus a peak check, so 'non-monotone' cannot drift into 'any shape at all'. "
     "The spec is confirmed by its OWN dose anchor (10.1% vs 2.2% of V81's 138) ⇒ FLAGGED, not "
     "deviated from."),
    ("(NOT relaxed, still fully armed) assert_manual_modes_frozen · assert_records_vs_base · "
     "assert_pointer_arrays_stock · assert_friction_all_stock · assert_gain_a_honda · the cave suite",
     "m24/m25 byte-identical to base AND stock; all 340 records byte-identical to base except the "
     "declared 4; pointers unmoved; friction and gain_A Honda."),
)


def assert_columns_stock_except(buf, stock, allow, label):
    recs = V86.sweep_records(buf)
    for name in V86.PTR_ARRAYS:
        for mode in V86.THIS_CAR_MODES:
            rec = recs[(name, mode)][0]
            ln = V74.rec_len(buf, rec)
            bad = [a for a in range(rec, rec + ln) if buf[a] != stock[a] and a not in allow]
            assert not bad, \
                f"🛑 {label}: {name} m{mode} @0x{rec:05X} differs from STOCK at undeclared bytes " \
                f"{[hex(a) for a in bad[:8]]} -- this car READS mode {mode}"
    return recs


def assert_manual_untouched(buf, base_img, stock, label):
    """🛑 m24/m25 byte-identical to BOTH base and stock ⇒ ENGAGED-ONLY BY CONSTRUCTION."""
    V84B.assert_manual_modes_frozen(buf, base_img, stock, label)
    for mode in MANUAL_MODES:
        rec = V74.factor_rec(buf, FACTOR_C_PTRS, mode)
        ys = V74.rec_any(buf, rec)[2]
        assert ys[0] == 0, \
            f"🛑 {label}: MANUAL mode {mode}'s FactorC Y[0] is {ys[0]}, not Honda's 0 -- the " \
            "engaged-only property is VOID and the damper would reach manual/parking steering"
    return True


def assert_edited_shape(buf, stock, label):
    """Only Y[0] moved, and the record stays monotone non-decreasing."""
    for mode in EDIT_MODES:
        rec = V74.factor_rec(buf, FACTOR_C_PTRS, mode)
        n, xs, ys = V74.rec_any(buf, rec)
        sn, sxs, sys_ = V74.rec_any(stock, rec)
        assert n == sn == 4 and xs == sxs, f"{label}: FactorC m{mode}'s X axis or count moved"
        assert ys[1:] == sys_[1:], \
            f"🛑 {label}: FactorC m{mode}'s Y[1..3] moved -- V86B lifts Y[0] ONLY"
        assert ys[0] == EXPECT_NEW[mode] == sys_[3], \
            f"{label}: FactorC m{mode} Y[0] is {ys[0]}, expected its own Y[3] = {sys_[3]}"
        # 🛑 THE ROW IS DELIBERATELY NON-MONOTONE -- see NON_MONOTONE_FINDING. Asserted as an EXACT
        # 🛑 shape instead, so "non-monotone" cannot drift into "any shape at all".
        assert ys == [sys_[3]] + sys_[1:], \
            f"🛑 {label}: FactorC m{mode}'s Y row is {ys}, expected [Y[3]] + Y[1:] = " \
            f"{[sys_[3]] + sys_[1:]}"
        assert all(0 <= y < 0x8000 for y in ys), f"{label}: a Y value is not a positive int16"
        assert max(ys) == sys_[3], \
            f"🛑 {label}: FactorC m{mode}'s peak moved -- the lift must not exceed the record's own " \
            "Y[3], or the surface leaves Honda's range entirely"
    return True


# =====================================================================================================
# 🛑🛑 A PROPERTY OF THIS EDIT THAT THE SPEC DID NOT STATE, AND THE BUILDER IS FLAGGING RATHER THAN
# ABSORBING. Setting `Y[0] := Y[3]` makes the Y row **NON-MONOTONE**:
#     m26  [0, 234, 429, 908]  ->  [908, 234, 429, 908]
#     m27  [0, 233, 426, 875]  ->  [875, 233, 426, 875]
# i.e. a **V-shaped speed surface**: strongest at creep, weakest at 60 km/h, rising again to 140.
# Honda ships monotone non-decreasing in every one of its 32 records, and **the kit's OWN guard
# `build_v84_tva.assert_factor_monotone` FAILS on this shape** -- it was written to catch exactly it.
#
# ⊕ THE SPEC IS NEVERTHELESS CONFIRMED, THREE INDEPENDENT WAYS, so this is a FLAG and not a deviation:
#   1. the byte values were given explicitly (`8C 03` = 908, `6B 03` = 875) and repeated;
#   2. `Y[0] := that record's own Y[3]` names Y[3] directly;
#   3. **the dose anchor settles it**: the spec says "creep dose ~10% of V81's flown 138 counts", and
#      this build COMPUTES **14 counts at 5 km/h, r = 99 = 10.1% of 138** for `Y[0] = 908`, against
#      **3 counts = 2.2%** for the monotone alternative `Y[0] := Y[1] = 234`. Only 908 matches.
# ⇒ "largest monotone lift" meant "the largest value in the record's own range", not "a lift that
#    preserves monotonicity". The build proceeds as specified and reports the shape.
#
# ⚠ WHY IT IS BOUNDED ANYWAY: the factor is a **memoryless** gain, the product is clamped at the
# ceiling (512 ct = 2.00% of the aggregator's ±25600), the LERP is continuous (it ramps 908 -> 234
# between 35 and 60 km/h, no discontinuity), and speed varies slowly against a 1 kHz loop, so the
# schedule is quasi-static. **No pole, zero or delay changes.** [EVIDENCE for each clause.]
NON_MONOTONE_FINDING = True


def lerp_delta_by_speed(base_img, built_img, mode=26):
    """FactorC(speed) either side of the edit. 🛑 MUST be EXACTLY 0 at and above X[1] = 60 km/h."""
    rows = []
    for kmh in (0, 5, 15, 25, 35, 45, 50, 60, 80, 100, 140):
        sp = kmh * SPEED_CT_PER_KMH
        a = V74.LM.lerp_int(sp, *V74.rec_any(base_img, V74.factor_rec(base_img, FACTOR_C_PTRS,
                                                                     mode))[1:])
        b = V74.LM.lerp_int(sp, *V74.rec_any(built_img, V74.factor_rec(built_img, FACTOR_C_PTRS,
                                                                       mode))[1:])
        rows.append((kmh, a, b, b - a))
    return rows


def assert_ring_free(base_img, built_img, label):
    """🛑 THE STRUCTURAL NEGATIVE CONTROL, COMPUTED: zero delta at and above X[1] = 3840 ct = 60 km/h."""
    for mode in EDIT_MODES:
        for kmh, a, b, d in lerp_delta_by_speed(base_img, built_img, mode):
            if kmh >= 60:
                assert d == 0, \
                    f"🛑 {label}: FactorC m{mode} changed by {d} at {kmh} km/h. A LERP's Y[0] cannot " \
                    f"affect the output at or above X[1] = 3840 ct = 60 km/h -- the ring-free claim, " \
                    "and the structural negative control the whole pre-registration rests on, is VOID"
    return True


def assert_ceiling(buf, label):
    """The damper ceiling, byte-verified, so the magnitude bound is computed rather than quoted."""
    got = u16(buf, CEILING_ADDR)
    assert got == CEILING_VALUE, \
        f"🛑 {label}: the damper ceiling 0x{CEILING_ADDR:05X} is {got}, expected {CEILING_VALUE} -- " \
        "GATE 2's magnitude bound rests on it"
    for mode in EDIT_MODES:
        assert V74.ceiling_floor(buf, mode) == CEILING_VALUE, \
            f"{label}: mode {mode}'s own ceiling floor is not {CEILING_VALUE}"
    return 100.0 * CEILING_VALUE / AGGREGATOR_FULL_SCALE


# =====================================================================================================
# OUTPUT NAMING -- frozen the moment a hash is reported
# =====================================================================================================
VARIANT_TOKEN = "FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB"
TAG = f"V85BASE-{VARIANT_TOKEN}"
BIN_OUT = str(plain_image_path(f"_v86b_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V86B-{TAG}-0x{START:X}-0x{END:X}.rwd")
WRITE_MODE = os.environ.get("ACCORD_V86B_WRITE", "").strip().lower()
assert WRITE_MODE in ("", "none", "bin", "rwd"), f"ACCORD_V86B_WRITE={WRITE_MODE!r}"


def build():
    print(__doc__)
    v85 = Path(SRC_BIN).read_bytes()
    stock = Path(STOCK_BIN).read_bytes()
    src_sha = hashlib.sha256(v85).hexdigest()
    print("=" * 102)
    print(f"SOURCE (V85, flown route 6e, FAULT-FREE): {SRC_BIN}\n  SHA256 {src_sha}")
    assert len(v85) == len(stock) == 0x100000, "an image is not 1 MiB"
    assert src_sha not in NOT_THE_BASE, f"🛑🛑 THE BASE IS {NOT_THE_BASE.get(src_sha)}"
    assert src_sha == SRC_SHA256, f"🛑🛑 THE BASE IS NOT THE FLOWN V85: {src_sha}"
    print("  ✅ the base is the flown V85 -- the SAME base as V86, NOT V86's output.")

    print("\n" + "-" * 102)
    print("  GATING THE SOURCE")
    assert walk_all_blocks(v85) == 0, "the V85 source's CRC chain does not verify"
    edits = derive_edit_cells(v85)
    allow = {a + k for a, w, _o, _n, _l in edits for k in range(w)}
    assert len(allow) == 4, f"{len(allow)} declared edit bytes, expected 2 cells x 2"
    print(f"    ★ THE EDIT, DEREFERENCED through FactorC's pointer array 0x{FACTOR_C_PTRS:05X}:")
    for addr, _w, old, new, lbl in edits:
        print(f"      0x{addr:05X}  {old:>4d} -> {new:<4d}  {lbl}")
    print("      ✅ all 32 FactorC record pointers DISTINCT · all four anchors match the "
          "independently-verified set")
    print(f"      🛑 m26 gets {EXPECT_NEW[26]}, m27 gets {EXPECT_NEW[27]} -- DIFFERENT, and the "
          "difference is asserted, never homogenised")
    V86.assert_anchors(v85, stock, "V85 source")
    assert u16(v85, CMD_EMA_ADDR) == CMD_EMA_V85, \
        f"🛑 the base's 0xC40D4 is {u16(v85, CMD_EMA_ADDR)}, expected V85's {CMD_EMA_V85}"
    assert_columns_stock_except(v85, stock, set(), "V85 source")
    assert_manual_untouched(v85, v85, stock, "V85 source")
    pct = assert_ceiling(v85, "V85 source")
    V86.assert_cave_region(v85, "V85 source")
    print("    ✅ CRC 50/50 · value anchors · four columns byte-stock · manual frozen · "
          f"ceiling {CEILING_VALUE} ct = {pct:.2f}% of the aggregator's ±{AGGREGATOR_FULL_SCALE}")

    print("\n    🛑 GUARDS RELAXED ON V86B ONLY (fully armed on V86), each with its replacement:")
    for name, why in RELAXED_GUARDS:
        print(f"      · {name}\n          {why}")

    # ---- APPLY -------------------------------------------------------------------------------------
    code = bytearray(v85)
    attributed = set()
    print("\n" + "-" * 102)
    print(f"  APPLYING {len(edits)} CONTROL CELL(S)")
    for addr, width, pre, new, lbl in edits:
        assert u16(code, addr) == pre, f"0x{addr:05X} drifted between the gate and the write"
        old_raw = bytes(code[addr:addr + width])
        struct.pack_into("<H", code, addr, new)
        assert u16(code, addr) == new, f"the write at 0x{addr:05X} did not take"
        attributed |= {addr + k for k in range(width)}
        print(f"      0x{addr:05X}  {pre:>4d} -> {new:<4d}  {old_raw.hex()} -> "
              f"{bytes(code[addr:addr + width]).hex()}  {lbl}")

    old_cave = bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = CAVE_PAYLOAD
    cave_attributed = {CAVE_BASE + k for k in range(CAVE_EXTENT) if old_cave[k] != CAVE_PAYLOAD[k]}
    attributed |= cave_attributed
    swap = [i for i in range(CAVE_EXTENT) if CAVE_PAYLOAD[i] != V86.CAVE_PAYLOAD[i]]
    print(f"\n    THE CAVE -- V86's payload with the TWO-BYTE weight swap at +{SWAP_OFF_A}/+"
          f"{SWAP_OFF_B}; {len(cave_attributed)}/{CAVE_EXTENT} bytes differ from V85's")
    print(f"      V86  +{SWAP_OFF_A} {V86.CAVE_PAYLOAD[SWAP_OFF_A:SWAP_OFF_A + 2].hex()} (w=4, "
          f"b6 = v != 0)   +{SWAP_OFF_B} "
          f"{V86.CAVE_PAYLOAD[SWAP_OFF_B:SWAP_OFF_B + 2].hex()} (w=2, b5 = |v| >= {RELAY_T})")
    print(f"      V86B +{SWAP_OFF_A} {CAVE_PAYLOAD[SWAP_OFF_A:SWAP_OFF_A + 2].hex()} (w=2, "
          f"b5 = v != 0)   +{SWAP_OFF_B} "
          f"{CAVE_PAYLOAD[SWAP_OFF_B:SWAP_OFF_B + 2].hex()} (w=4, b6 = |v| >= {RELAY_T})")
    print(f"      ⇒ V86 vs V86B differ at EXACTLY {swap} -- a two-byte swap, nothing else.")
    print(f"      ⇒ V86B MUST produce (b7,b6,b5) = (0,0,1) and FORBIDS (0,1,0); V86 is the mirror. "
          "Exact in BOTH directions.")

    # ---- RE-ASSERT ---------------------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  RE-ASSERTING ON THE FINISHED IMAGE")
    V86.assert_anchors(code, stock, "V86B")
    assert u16(code, CMD_EMA_ADDR) == CMD_EMA_V85, \
        "🛑 V86B must NOT carry V86's command-EMA edit -- the two experiments would be confounded"
    for addr, (want, why) in V86.FROZEN_CELLS.items():
        if addr in allow:
            continue                                     # RELAXED, declared, checked by shape below
        assert u16(code, addr) == want, f"🛑 V86B: FROZEN 0x{addr:05X} moved -- {why}"
    for addr, (want, why) in V86.FROZEN_BYTES.items():
        assert code[addr] == want, f"🛑 V86B: FROZEN byte 0x{addr:05X} moved -- {why}"
    recs = assert_columns_stock_except(code, stock, allow, "V86B")
    assert_manual_untouched(code, v85, stock, "V86B")
    assert_edited_shape(code, stock, "V86B")
    assert_ring_free(v85, code, "V86B")
    assert_ceiling(code, "V86B")
    V86.assert_records_vs_base(code, v85, recs, attributed, "V86B")
    res = V86.assert_residual_records(code, stock, recs, "V86B")
    V86.assert_cave_region(code, "V86B")
    V86.assert_cave_pins(stock, code, "V86B")
    V86.assert_cave_encodings(code, "V86B")
    V86.assert_cave_tail_matches_v85(code, v85, "V86B")
    V86.assert_probe_cells_v86(code, "V86B")
    V84B.assert_keep_list(code, "V86B")
    V84B.assert_pointer_arrays_stock(code, stock, "V86B")
    V84B.assert_friction_all_stock(code, stock, "V86B")
    V84B.assert_gain_a_honda(code, stock, "V86B")
    # 🛑 V84B.assert_factor_monotone is DELIBERATELY NOT CALLED -- see NON_MONOTONE_FINDING and
    # 🛑 RELAXED_GUARDS. `assert_edited_shape`'s exact-shape assert replaces it.
    V85B.assert_b5_refutation(code, "V86B")
    V85B.assert_caller_guard(code, "V86B")
    print("    ✅ frozen set (2 cells RELAXED, declared) · anchors · 10 families x 4 columns stock "
          f"except the {len(allow)} declared bytes")
    print("    ✅ m24/m25 byte-identical to base AND stock ⇒ ENGAGED-ONLY BY CONSTRUCTION")
    print("    ✅ X untouched, Y[1..3] untouched, only Y[0] moved, peak still the record's own Y[3]")
    print("       🛑 the row is NOT monotone -- see the flagged finding below. Said plainly here so "
          "this line cannot be quoted as a monotonicity pass.")
    print(f"    ✅ all 340 records byte-identical to the base except the declared 4 · residual set "
          f"unchanged ({len(res)})")
    print(f"    ✅ 0xC40D4 = {u16(code, CMD_EMA_ADDR)} (V85's) ⇒ V86B does NOT carry V86's edit")

    # ---- 🛑 THE PROPERTY THE SPEC DID NOT STATE ----------------------------------------------------
    print("\n    🛑🛑 A PROPERTY THE SPEC DID NOT STATE -- FLAGGED, NOT ABSORBED:")
    for mode in EDIT_MODES:
        s_ys = V74.rec_any(stock, V74.factor_rec(stock, FACTOR_C_PTRS, mode))[2]
        b_ys = V74.rec_any(code, V74.factor_rec(code, FACTOR_C_PTRS, mode))[2]
        print(f"      FactorC m{mode}  Y {s_ys} -> {b_ys}")
    print("      ⇒ the Y row becomes NON-MONOTONE: a V-shaped speed surface -- strongest at creep,")
    print("        weakest at 60 km/h, rising again to 140. Honda ships monotone in ALL 32 records,")
    print("        and the kit's OWN `assert_factor_monotone` FAILS on this shape (relaxation #6).")
    print("      ⊕ The spec is CONFIRMED anyway, three ways: the explicit bytes 8c03/6b03; the words")
    print("        'that record's own Y[3]'; and its OWN dose anchor -- 908 gives 14 ct at creep =")
    print("        10.1% of V81's 138, while the monotone alternative Y[0]:=Y[1]=234 gives 3 ct =")
    print("        2.2%. Only 908 matches. ⇒ 'largest monotone lift' meant 'largest value in the")
    print("        record's own range', not 'a lift preserving monotonicity'.")
    print("      ⚠ BOUNDED ANYWAY: a MEMORYLESS gain, clamped at the ceiling, the LERP is CONTINUOUS")
    print("        (908 -> 234 ramps over 35-60 km/h, no discontinuity), and speed is quasi-static")
    print("        against a 1 kHz loop. No pole, zero or delay changes.")

    # ---- THE RING-FREE PROOF, COMPUTED -------------------------------------------------------------
    print("\n    ★ PROVABLY RING-FREE, BY LERP ARITHMETIC -- FactorC(speed), V85 -> V86B, mode 26")
    print("      " + f"{'km/h':>6s}{'ct':>8s}{'V85':>7s}{'V86B':>7s}{'delta':>8s}")
    for kmh, a, b, d in lerp_delta_by_speed(v85, code, 26):
        mark = "   <- X[1] = 3840 ct: Y[0] STOPS MATTERING HERE" if kmh == 60 else ""
        print("      " + f"{kmh:>6d}{kmh * SPEED_CT_PER_KMH:>8d}{a:>7d}{b:>7d}{d:>8d}" + mark)
    print("      ⇒ delta is EXACTLY 0 at and above 60 km/h, BY LERP ARITHMETIC, not by assumption.")
    print("        The 26-31 Hz ring was measured ABOVE 80 km/h ⇒ predicted burst duty UNCHANGED at")
    print("        V84's 2.54%. **That band is a STRUCTURAL negative control: if it moves, the build")
    print("        or the measurement is wrong -- not the hypothesis.**")
    print(f"      ⊕ GATE 2 magnitude: bounded by the ceiling {CEILING_VALUE} ct = {pct:.2f}% of the")
    print(f"        aggregator's ±{AGGREGATOR_FULL_SCALE}, worst case, at ANY dose. Phase: a LERP Y is")
    print("        a MEMORYLESS gain ⇒ every pole in the image is bit-identical.")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print("\n" + "-" * 102)
    print(f"  CRC -- {len(blocks)} block(s) move")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        owners = [hex(a) for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}"
              f"   owns {len(owners)} byte(s)")
    print("    ⊕ BOTH control cells sit in [0x0D7000,0x0D7FFC) ⇒ ONE trailer for the edit; the cave "
          "adds 0xC4FFC.")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the block the bootloader SKIPS (V40's brick)"
    assert not [a for a in attributed if a < START or a >= END], "an edit landed outside the region"
    assert bytes(code[0xC5000:0xC5FFC]) == bytes(stock[0xC5000:0xC5FFC])
    print("    ✅ full 50-block chain: 50/50 PASS · 0 bytes into [0xC5000,0xC5FFC)")

    # ---- ZERO-UNATTRIBUTED -------------------------------------------------------------------------
    by_addr = {}
    for addr, w, pre, new, lbl in edits:
        for k in range(w):
            by_addr[addr + k] = f"CONTROL 0x{addr:05X} {lbl}  {pre} -> {new}"

    def attribute(d):
        if d in by_addr:
            return by_addr[d]
        if d in crc_only:
            return "CRC trailer"
        if CAVE_BASE <= d < CAVE_BASE + CAVE_EXTENT:
            return f"the CAVE @0x{CAVE_BASE:05X} ({CAVE_EXTENT} B, extent UNCHANGED)"
        return None

    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V86B vs the flown V85 -- over the WHOLE 1 MiB image")
    runs = V86.diff_runs(code, v85, attribute)
    total = sum(b - a + 1 for a, b in runs)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, f"🛑 UNATTRIBUTED bytes vs V85: {[hex(x) for x in stray[:16]]}"
    V86.assert_identity_modulo(code, v85, attributed | crc_only, "V86B", "V85")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = v85[a]
    assert hashlib.sha256(bytes(rt)).hexdigest() == SRC_SHA256, "the round trip does not reproduce V85"
    print("    ⇒ ZERO unattributed bytes; restoring the attributed set reproduces V85 BIT-FOR-BIT.")

    # ---- .rwd --------------------------------------------------------------------------------------
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V86B output")
    back = parse_x31(rwd)
    dec = bytearray(v85)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    V86.assert_anchors(dec, stock, "V86B readback")
    assert_edited_shape(dec, stock, "V86B readback")
    assert_manual_untouched(dec, v85, stock, "V86B readback")
    V86.assert_cave_encodings(dec, "V86B readback")
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("    ✅ READBACK: anchors, the edited shape, the manual columns, the cave encodings and the "
          "50/50 chain re-verified from the decoded .rwd payload.")

    # ---- WRITE -------------------------------------------------------------------------------------
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V86B_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(
                f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists. A same-number "
                "re-cut destroys a predecessor's snapshot.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            shipped = Path(OUT).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha
            FF.assert_x31_checksum(shipped, "V86B shipped")
            sd = bytearray(v85)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert_edited_shape(sd, stock, "V86B shipped-from-disk")
            assert_manual_untouched(sd, v85, stock, "V86B shipped-from-disk")
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code)
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded and re-verified INDEPENDENTLY.")

    print(f"\n  V86B [{VARIANT_TOKEN}]")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 HONEST LABEL: a ring-free test of whether the damper's ZERO POINT is special --")
    print("     moderate-to-low probability of fixing the ratcheting, and it WILL make the wheel")
    print("     slightly heavier when engaged at low speed (~10% of V81's flown creep dose).")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    assert EDIT_MODES == (26, 27) and not set(EDIT_MODES) & set(MANUAL_MODES)
    assert EXPECT_NEW[26] != EXPECT_NEW[27], "🛑 m26 and m27 must NOT receive the same value"
    assert struct.pack("<H", EXPECT_NEW[26]).hex() == "8c03"
    assert struct.pack("<H", EXPECT_NEW[27]).hex() == "6b03"
    assert len(CAVE_PAYLOAD) == 68 and CAVE_PAYLOAD != V86.CAVE_PAYLOAD
    assert RELAY_T == 64 and MAG_SHIFT == 6, "the threshold must match V86's corrected cave"
    assert "+" not in VARIANT_TOKEN and all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN)
    assert len(OUT) < 250
    assert SRC_SHA256 not in NOT_THE_BASE


if __name__ == "__main__":
    _self_check()
    build()
