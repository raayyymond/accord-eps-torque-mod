#!/usr/bin/env python3
"""builds/v50_v79/build_v77_tva.py -- SINGLE-VARIABLE REVERT of `0xC63A0` 2048 -> 1024 (back to STOCK).

★★★★ THE ONE-LINE REASON THIS FILE EXISTS. Two hard faults in two days -- a latched total loss of
power steering requiring an engine restart -- one **ENGAGED** (V75, stoplight launch, route 5e,
t = 284.7947 s) and one **DISENGAGED / MANUAL** (V74, driving over a bump). The manual fault rules
out every engaged-column lever by construction, and the mode-24 damper records are BYTE-IDENTICAL
to stock on both builds (FactorC 0xD67E4, FactorE 0xD6820, FactorB 0xD6760, FactorD 0xD67A4,
ceiling 0xD60B4 -- verified here, per build, from the pointer arrays). ⇒ **the FactorC/FactorE
edits cannot have caused the manual fault, and the `k*` bracket that framed the V75 analysis is
VOID: V74 is no longer a proven-clean point.**

🛑 THE ONE MECHANISM COMMON TO BOTH FAULTS is `0xC63A0` -- a bare `tp` scalar (`tp+0x73A0`,
`0xBF000 + 0x73A0`), **mode-proof and always live in manual AND engaged**, stock **1024**, set to
**2048 at V72** and never reverted since. It exclusively weights the damper output `gp-0x6bd0`
into "Path 2", a closed firmware-internal feedback loop
(`gp-0x6b98 -> FUN_0003b8f6 -> ... -> PID -> aggregator -> gp-0x6b98`, one-sample delay) whose
central gain estimate already exceeds unity at 7.79 Hz and 21 Hz.

    Reverting it is **-6.02 dB** on that loop term and **ZERO phase** (it is a pure Q10 scalar).
    It costs **ZERO grind performance**: the damping is delivered on Path 1 (`FUN_0003aa2c`,
    unity weight), which `0xC63A0` does not touch.
    It has **ONE reader** (`ld.hu 0x73a0[tp],r9` @0x381AC), **ZERO writers**, no monitor and no
    float mirror -- re-measured here from raw bytes, both displacement parities, on every image.

🛑 SINGLE-VARIABLE IS THE ENTIRE POINT. Nothing else moves. Not FactorC, not FactorE, not the
friction lane, not `0xC407E`, not the cave/probe, not the ceiling, not `0x454FE`, not either `sar`
site, not the gate, not the arms. The builder asserts this as a **byte diff**, not in prose: the
ONLY functional difference from the base is the 2-byte cell at `0xC63A0`, plus its owning block's
CRC word.

🛑 COUNT CELLS, NOT BYTES. `2048` is `00 08` little-endian and `1024` is `00 04`, so the cell's LOW
byte is `0x00` in BOTH and **only `0xC63A1` actually moves**: the edit is ONE 2-byte CALIBRATION
CELL whose BYTE diff is ONE byte. The expected byte set is DERIVED from the two encodings, never
hand-listed -- asserting "2 bytes" would FAIL a correct build. (The mirror image of this trap has
already bitten this kit: V75's modes 29/32/33 moved 565 -> 566, changing only the LOW byte.)

TWO ARTEFACTS, ONE EDIT EACH
---------------------------------------------------------------------------------------------------
  V77   = **V74 base** + `0xC63A0` 2048 -> 1024.      <- the candidate this file was written for.
          Single-variable against the build that FAULTED IN MANUAL, and it tests the mechanism in
          manual AND engaged simultaneously, because the cell is mode-proof.
  V77B  = **V75 base** + `0xC63A0` 2048 -> 1024.      🛑 **UNFLASHED AND NOT RECOMMENDED.**
          The "keep V75's grind fix, remove the mode-proof loop gain" option. It exists so that it
          exists. V75's engaged-mode configuration HARD-FAULTED and nothing has cleared it; this
          build removes one mechanism and leaves that configuration otherwise intact.

★ Both filenames encode the lever AND the base (`_v77_C63A0.1024_v74base_...` /
`_v77b_C63A0.1024_v75base_...`). A recorded hazard: two V70 cuts both wrote `_v70_plain_image.bin`,
so the second OVERWROTE the first's snapshot while the first's `.rwd` stayed flashable -- an
artefact NO gate could check. `build_one()` additionally REFUSES to overwrite a DIFFERING file.

🛑 NOT CLEARANCE TO FLY. This file builds artefacts. The flash decision is the operator's, names the
file and the bus, and is made outside this script.

Usage:  python builds/v50_v79/build_v77_tva.py
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
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 🛑 The default in lib/firmware_paths.py is STALE (`../accord-firmware`, singular). Set before import.
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import diff_build_vs_stock as DBS          # noqa: E402  (the kit's OWN labelled vs-stock EDITS table)
import build_vfourframe_tva as FF          # noqa: E402  (x31 container, cipher, crc_block_map)
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v72_tva as V72                # noqa: E402  (LEVER C + its single-reader census)
import build_v74_tva as V74                # noqa: E402  (the frozen keep-list, record readers)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = V72.START, V72.END            # 0x13000, 0x100000
CAVE_BASE = FF.CAVE_BASE                   # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT              # 68 -- the PROVEN extent. Never grow it.
CAVE_LAST = CAVE_BASE + CAVE_EXTENT - 1    # 0xC4B77
TP = V72.TP                                # 0xBF000
STOCK_BIN = stock_fw_path("code.bin")

# =====================================================================================================
# THE ONE EDIT
# =====================================================================================================
LEVER_ADDR = V72.DAMP_WEIGHT_ADDR          # 0xC63A0 -- re-declared from V72 so a drift there fails
LEVER_FROM = V72.DAMP_WEIGHT_NEW           # 2048 -- what V72 wrote and V73/V74/V75 all carry
LEVER_TO = V72.DAMP_WEIGHT_STOCK           # 1024 -- STOCK
LEVER_READER = V72.DAMP_WEIGHT_READER      # 0x381AC -- `ld.hu 0x73a0[tp],r9`, the ONLY reader
LEVER_TP_DISP = V72.DAMP_WEIGHT_TP_DISP    # 0x73A0
assert LEVER_ADDR == TP + LEVER_TP_DISP == 0xC63A0, "0xC63A0 is not tp+0x73A0 -- re-derive"
assert (LEVER_FROM, LEVER_TO) == (2048, 1024), "the lever's endpoints drifted from V72's record"

# 🛑🛑 COUNT CELLS, NOT BYTES -- and DERIVE the moved-byte set, never hand-list it.
# `2048` is `00 08` little-endian and `1024` is `00 04`, so the LOW byte is 0x00 in BOTH and only
# 0xC63A1 actually moves. The edit is ONE 2-byte CALIBRATION CELL whose byte diff is ONE byte.
# This kit has already been bitten by the mirror image of this: V75's modes 29/32/33 moved
# 565 -> 566, changing only the LOW byte, and a byte-count assertion of 22 would have FAILED a
# correct build. So the expected byte set is computed from the two encodings below.
LEVER_BYTES_FROM = struct.pack("<H", LEVER_FROM)
LEVER_BYTES_TO = struct.pack("<H", LEVER_TO)
LEVER_CELL_BYTES = [LEVER_ADDR, LEVER_ADDR + 1]          # the CELL's extent -- always 2
MOVED_BYTES = [LEVER_ADDR + k for k in range(2) if LEVER_BYTES_FROM[k] != LEVER_BYTES_TO[k]]
assert MOVED_BYTES == [LEVER_ADDR + 1], \
    f"the derived moved-byte set is {[hex(x) for x in MOVED_BYTES]} -- 2048/1024 differ only in " \
    "their HIGH byte; if this ever changes, every count below must be re-read"

# =====================================================================================================
# THE MODE-24 / MODE-26 DAMPER RECORDS -- named so the report can be read without the pointer maths
# =====================================================================================================
FACTOR_B_PTRS, FACTOR_C_PTRS = V74.FACTOR_B_PTRS, V74.FACTOR_C_PTRS   # 0xC9CCC / 0xC9E9C
FACTOR_D_PTRS, FACTOR_E_PTRS = V74.FACTOR_D_PTRS, V74.FACTOR_E_PTRS   # 0xC9DB4 / 0xC9F84
CEILING_PTRS = V74.CEILING_PTRS                                       # 0xC77A0
FRICTION_PTR_ARRAY = V74.FRICTION_PTR_ARRAY                           # 0xCBE74
PTR_ARRAYS = ((FACTOR_B_PTRS, "FactorB"), (FACTOR_C_PTRS, "FactorC"), (FACTOR_D_PTRS, "FactorD"),
              (FACTOR_E_PTRS, "FactorE"), (CEILING_PTRS, "ceiling"), (FRICTION_PTR_ARRAY, "friction"))
assert (FACTOR_C_PTRS, FACTOR_E_PTRS) == (0xC9E9C, 0xC9F84), "the FactorC/E pointer arrays moved"

MANUAL_MODE, LIVE_MODE = 24, 26            # ★ the car is TVCA4, row 11: manual 24, engaged 26
CHECK_MODES = (MANUAL_MODE, LIVE_MODE)
# ⊕ The mode-24 records the fault analysis names, stated INDEPENDENTLY and asserted after the
# dereference -- a quoted address that silently disagrees with the pointer array is the trap.
MODE24_EXPECT = {"FactorC": 0xD67E4, "FactorE": 0xD6820, "FactorB": 0xD6760,
                 "FactorD": 0xD67A4, "ceiling": 0xD60B4}

# =====================================================================================================
# THE VARIANTS
# =====================================================================================================
VARIANTS = {
    "V77": dict(
        src="_v74_engagedcols_x0_12_addonly_plain_image.bin",
        src_sha="8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959",
        src_label="V74",
        out_bin="_v77_C63A0.1024_v74base_plain_image.bin",
        tag="V74BASE-C63A0.1024-loopgain-revert",
        note="THE CANDIDATE -- single-variable against V74, the build that faulted IN MANUAL.",
        recommended=True,
    ),
    "V77B": dict(
        src="_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
        src_sha="e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c",
        src_label="V75",
        out_bin="_v77b_C63A0.1024_v75base_plain_image.bin",
        tag="V75BASE-C63A0.1024-NOT-RECOMMENDED-UNFLASHED",
        note="🛑 UNFLASHED AND NOT RECOMMENDED -- V75's engaged configuration HARD-FAULTED and "
             "nothing has cleared it. Built so the option exists, not as a proposal.",
        recommended=False,
    ),
}


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


rec_any = V74.rec_any        # (count, X, Y) driven by the record's OWN count word
rec_len = V74.rec_len        # 4 + 4n -- 🛑 NOT a flat 0x18 window
factor_rec = V74.factor_rec  # DEREFERENCED from the pointer array, never quoted


# =====================================================================================================
# The vs-STOCK classifier -- every residual byte is attributed to a NAMED owner or reported
# =====================================================================================================
NAMED_SPANS = [
    (0x3AA96, 1, "V71A gate byte 0x3AA96 (gp-0x683c repoint)"),
    (0x454FE, 1, "0x454FE state-4 governor branch (V42's ratchet fix, carried)"),
    (0xC407E, 2, "0xC407E clamp = 850 (V73)"),
    (LEVER_ADDR, 2, f"0x{LEVER_ADDR:05X} LEVER C damper weight  <- V77's ONLY edit"),
]
GAIN_A_RECS = (0xC6A68, 0xC6A7C)             # V72's r26 cut, 0 / 10 km/h
GAIN_B_M10_RECS = (0xD2A74, 0xD2AB0)         # V67/V68's r24 arm, carried
REC_STRIDE = V74.REC_STRIDE                  # 0x14


def build_class_map(img):
    """address -> owner label, derived from the image's OWN pointer arrays. No hand-listed extents."""
    cls = {}

    def paint(lo, n, label):
        for a in range(lo, lo + n):
            cls.setdefault(a, label)

    for a in range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT):
        cls[a] = "PROBE cave 0xC4B34+68"
    for lo, n, label in NAMED_SPANS:
        paint(lo, n, label)
    for _s, e in FF.crc_block_map(img):
        paint(e, 4, "CRC trailer")
    for base in GAIN_A_RECS:
        paint(base, REC_STRIDE, f"gain_A rec 0x{base:05X} (V72 r26 cut)")
    for base in GAIN_B_M10_RECS:
        paint(base, REC_STRIDE, f"gain_B mode-10 rec 0x{base:05X} (r24 arm)")
    owners = {}
    for arr, name in PTR_ARRAYS:
        for mode in range(34):
            base = factor_rec(img, arr, mode)
            owners.setdefault((base, name), []).append(mode)
    for (base, name), modes in sorted(owners.items()):
        paint(base, rec_len(img, base), f"{name} rec 0x{base:05X} modes {modes}")
    # ⊕ LAST LAYER, and deliberately last: the kit's OWN labelled vs-stock table, reused rather than
    # re-typed. It carries the V18/V22/V36/V37/V38/V53/V55/V57 code-site and scalar lineage that no
    # pointer array reaches. `paint` uses setdefault, so the structural layers above always win.
    for lo, hi, ebuild, text in DBS.EDITS:
        paint(lo, hi - lo, f"[{ebuild}] {text.splitlines()[0][:96]}")
    return cls


def diff_runs(a, b, lo=START, hi=END):
    """Contiguous runs of differing bytes over [lo, hi)."""
    runs, prev = [], None
    for i in range(lo, hi):
        if a[i] == b[i]:
            prev = None
            continue
        if prev is not None and i == prev[1] + 1:
            prev = (prev[0], i)
            runs[-1] = prev
        else:
            prev = (i, i)
            runs.append(prev)
    return runs


# =====================================================================================================
# The build
# =====================================================================================================

def build_one(name):
    v = VARIANTS[name]
    src_bin = plain_image_path(v["src"])
    bin_out = str(plain_image_path(v["out_bin"]))
    out_rwd = os.path.join(RWD_DIR, f"39990-TVA,A160-{name}-{v['tag']}-0x{START:X}-0x{END:X}.rwd")

    print("\n" + "=" * 102)
    print(f"  BUILD {name}  --  {v['src_label']} base + 0x{LEVER_ADDR:05X} {LEVER_FROM} -> {LEVER_TO}")
    print(f"  {v['note']}")
    print("=" * 102)

    # ---- 🛑 filename / path guards, BEFORE anything is written ------------------------------------
    assert len(out_rwd) < 250, \
        f"the .rwd path is {len(out_rwd)} chars -- Windows' 260 limit would truncate it"
    for path in (os.path.basename(bin_out), os.path.basename(out_rwd)):
        assert f"C63A0.1024" in path, \
            f"🛑 the lever is not in {path!r} -- a re-cut would be indistinguishable from a sibling"
        assert "+" not in path, "a `+` in an artefact name gets URL-decoded to a space by GhidraMCP"
    assert v["src_label"].lower() + "base" in os.path.basename(bin_out).lower(), \
        "🛑 the BASE is not in the plain-image filename -- V77 and V77B differ ONLY in their base, " \
        "so the base is the discriminator and it must be on the file"
    existing = Path(bin_out).read_bytes() if os.path.exists(bin_out) else None
    if existing is not None:
        print(f"  ⚠ {bin_out} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")

    base = bytearray(Path(src_bin).read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    print(f"\n  SOURCE ({v['src_label']}): {src_bin}")
    print(f"    SHA256 {hashlib.sha256(bytes(base)).hexdigest()}")
    print(f"  STOCK:        {STOCK_BIN}")
    for nm, img in ((v["src_label"], base), ("stock", stock)):
        assert len(img) == 0x100000, f"the {nm} image is not 1 MiB"
    assert hashlib.sha256(bytes(base)).hexdigest() == v["src_sha"], \
        f"🛑 THE BASE IS NOT {v['src_label']}. SHA256 is {hashlib.sha256(bytes(base)).hexdigest()}, " \
        f"expected {v['src_sha']}. {name} is defined as {v['src_label']} + ONE cell; any other base " \
        "voids every claim in this file."
    print(f"  ✅ the base SHA256 matches the recorded {v['src_label']} image exactly.")

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    V74.assert_must_not_change(base, f"{v['src_label']} source", stock, None)
    assert walk_all_blocks(bytes(base)) == 0, "the source's own CRC chain does not verify"
    assert u16(base, LEVER_ADDR) == LEVER_FROM, \
        f"🛑 the source's 0x{LEVER_ADDR:05X} is {u16(base, LEVER_ADDR)}, not V72's {LEVER_FROM} -- " \
        "the revert would be a NO-OP and this build would be a re-cut of its own base"
    assert u16(stock, LEVER_ADDR) == LEVER_TO, \
        f"🛑 STOCK's 0x{LEVER_ADDR:05X} is {u16(stock, LEVER_ADDR)}, not {LEVER_TO} -- the target " \
        "value is DEFINED as stock and is read from the stock image, never quoted"
    print(f"  ✅ the source passes the whole frozen keep-list and its own CRC chain, and carries "
          f"0x{LEVER_ADDR:05X} = {LEVER_FROM}.")
    print(f"  ✅ the target {LEVER_TO} is READ from the stock image at the same address, not quoted.")

    # ---- the single-reader census, on the SOURCE ---------------------------------------------------
    nhits, readers = V72.assert_lever_c_single_reader(bytes(base))
    print(f"  ✅ GATE 1 on 0x{LEVER_ADDR:05X}: {len(readers)} reader "
          f"(0x{readers[0][0]:05X} -> r{readers[0][1]}), 0 writers, both displacement parities "
          f"({nhits} raw halfword hit(s)).")

    # ---- THE ONE EDIT ------------------------------------------------------------------------------
    code = bytearray(base)
    struct.pack_into("<H", code, LEVER_ADDR, LEVER_TO)
    print(f"\n  THE EDIT -- exactly one 2-byte calibration cell:")
    print(f"    0x{LEVER_ADDR:05X}  {LEVER_FROM:5d} -> {LEVER_TO:5d}   "
          f"{bytes(base[LEVER_ADDR:LEVER_ADDR + 2]).hex()} -> "
          f"{bytes(code[LEVER_ADDR:LEVER_ADDR + 2]).hex()}   "
          f"tp+0x{LEVER_TP_DISP:04X}, Q10 damper weight into Path 2")
    print(f"    ⇒ -6.02 dB on the Path-2 loop term, ZERO phase (a pure Q10 scalar), and Path 1 "
          f"(FUN_0003aa2c, unity weight) is UNTOUCHED ⇒ zero grind cost.")

    # ---- the frozen keep-list, via the PROBE-COPY idiom --------------------------------------------
    # 🛑 V74.assert_must_not_change asserts LEVER C == 2048 by VALUE, which is exactly what this build
    # changes. Restore it on a COPY, run the FULL guard unweakened, and assert the exception set is
    # EXACTLY the two lever bytes. That is the kit's own idiom for a guarded relaxation.
    probe = bytearray(code)
    struct.pack_into("<H", probe, LEVER_ADDR, LEVER_FROM)
    V74.assert_must_not_change(probe, f"{name} (LEVER C restored for the inherited guard)",
                               stock, base)
    exc = [i for i in range(START, END) if probe[i] != code[i]]
    assert exc == MOVED_BYTES, \
        f"🛑 the keep-list relaxation covers {[hex(x) for x in exc]}, expected exactly " \
        f"{[hex(x) for x in MOVED_BYTES]} (the byte(s) of cell 0x{LEVER_ADDR:05X} that actually move)"
    print(f"\n  ✅ THE WHOLE FROZEN KEEP-LIST re-asserted on the output with 0x{LEVER_ADDR:05X} "
          f"restored on a COPY, and the relaxation set is EXACTLY {[hex(x) for x in exc]}:")
    print("     both `sar` sites at stock, the gate, all five arms, V72's gain_A r26 cut, the")
    print("     carried 0x454FE, the clamp at 850, the six pointer arrays over all 34 modes, the")
    print("     config table, V57's decoupling, V53's STOCK_CALS, the no-partial-record-write rule,")
    print("     and EVERY DISENGAGED-column record byte-identical to the base.")
    nhits2, readers2 = V72.assert_lever_c_single_reader(bytes(code))
    assert (nhits2, readers2) == (nhits, readers), "the reader census moved across the edit"
    print(f"  ✅ the single-reader census is UNCHANGED across the edit "
          f"(1 reader @0x{readers2[0][0]:05X}, 0 writers).")

    # ---- mode 24 / mode 26 damper records, DEREFERENCED --------------------------------------------
    print(f"\n  ✅ MODE {MANUAL_MODE} (manual) and MODE {LIVE_MODE} (engaged) damper records -- "
          "dereferenced from the pointer arrays, then compared BYTE-FOR-BYTE:")
    for mode in CHECK_MODES:
        for arr, nm in PTR_ARRAYS:
            rb = factor_rec(code, arr, mode)
            assert rb == factor_rec(base, arr, mode) == factor_rec(stock, arr, mode), \
                f"the {nm} pointer for mode {mode} MOVED -- every table is reached through it"
            ln = rec_len(code, rb)
            assert bytes(code[rb:rb + ln]) == bytes(base[rb:rb + ln]), \
                f"🛑 {name}: the mode-{mode} {nm} record @0x{rb:05X} MOVED vs the base"
            n, xs, ys = rec_any(code, rb)
            vs_stock = "== STOCK" if bytes(code[rb:rb + ln]) == bytes(stock[rb:rb + ln]) \
                else "!= stock (inherited)"
            flag = ""
            if mode == MANUAL_MODE and nm in MODE24_EXPECT:
                assert rb == MODE24_EXPECT[nm], \
                    f"mode-24 {nm} dereferences to 0x{rb:05X}, the fault analysis names " \
                    f"0x{MODE24_EXPECT[nm]:05X}"
                flag = "  ⊕ the address the fault analysis names"
            print(f"    m{mode:2d} {nm:8s} @0x{rb:05X} n={n} X={xs} Y={ys}   "
                  f"== base, {vs_stock}{flag}")
    for nm, want in MODE24_EXPECT.items():
        assert bytes(code[want:want + rec_len(code, want)]) == \
            bytes(stock[want:want + rec_len(stock, want)]), \
            f"🛑 the mode-24 {nm} record @0x{want:05X} is NOT byte-stock"
    print(f"    ★★ ALL FIVE mode-{MANUAL_MODE} records the fault analysis names are BYTE-STOCK on "
          "this build, as they were on V74 and V75.")

    # ---- the cave ----------------------------------------------------------------------------------
    cave = bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    assert cave == bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]), \
        f"🛑 {name}: the cave 0x{CAVE_BASE:05X}..0x{CAVE_LAST:05X} MOVED vs the base -- the probe " \
        "must survive intact"
    assert len(cave) == CAVE_EXTENT == 68 and CAVE_BASE + CAVE_EXTENT - 1 == CAVE_LAST == 0xC4B77, \
        "the cave extent is not the proven 68 bytes 0xC4B34..0xC4B77"
    assert bytes(code[CAVE_BASE + CAVE_EXTENT:FF.CAVE_HARD_LIMIT]) == \
        bytes(base[CAVE_BASE + CAVE_EXTENT:FF.CAVE_HARD_LIMIT]), "the cave TAIL moved"
    print(f"\n  ✅ THE PROBE CAVE 0x{CAVE_BASE:05X}..0x{CAVE_LAST:05X} ({CAVE_EXTENT} B) is "
          f"BYTE-IDENTICAL to {v['src_label']}'s:")
    print(f"     {cave.hex()}")

    # ---- CRC ---------------------------------------------------------------------------------------
    blk = tuple(V53.owning_block(code, LEVER_ADDR))
    assert blk == (0xC6000, 0xC6FFC), \
        f"0x{LEVER_ADDR:05X}'s owning CRC block is {tuple(hex(x) for x in blk)}, expected " \
        "(0xC6000, 0xC6FFC)"
    old_crc = u32(code, blk[1])
    new_crc = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, blk[1], new_crc)
    assert old_crc != new_crc, "the CRC word did not move -- the edit did not land in this block"
    print(f"\n  CRC -- EXACTLY 1 block moves (asserted, not observed):")
    print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")
    crc_only = set(range(blk[1], blk[1] + 4))
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    # 🛑 crc_block_map ALREADY carries the bridged main block [0x13000,0xC4FFC) as its last entry
    # -- V53.owning_block relies on that, and a "+1 for the bridge" here counts it twice.
    bmap = FF.crc_block_map(code)
    assert bmap[-1] == FF.MAIN_BLOCK, f"the map's last block is {bmap[-1]}, not the main block"
    nblocks = len(bmap)
    assert nblocks == FF.EXPECTED_BLOCKS == 50, f"{nblocks} CRC blocks, expected 50"
    print(f"    ✅ full CRC chain re-walked: {nblocks}/{nblocks} blocks PASS (0 mismatches)")
    assert not (0xC5000 <= LEVER_ADDR < 0xC5FFC) and not (0xC5000 <= LEVER_ADDR + 1 < 0xC5FFC), \
        "the edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block, V40 ignition precedent"
    print("    ✅ neither edited byte lands in [0xC5000,0xC5FFC) -- the CRC-skipped block, V40 "
          "ignition precedent.")

    # ---- THE FULL BYTE DIFF vs THE BASE ------------------------------------------------------------
    d_base = [i for i in range(START, END) if code[i] != base[i]]
    functional = [d for d in d_base if d not in crc_only]
    assert functional == MOVED_BYTES, \
        f"🛑 {name} is NOT single-variable: the functional diff vs {v['src_label']} is " \
        f"{[hex(x) for x in functional]}, expected exactly {[hex(x) for x in MOVED_BYTES]}"
    assert set(functional) <= set(LEVER_CELL_BYTES), "a functional byte lies outside the cell"
    assert set(d_base) - set(functional) <= crc_only, "a byte moved outside the lever and its CRC"
    assert u16(base, LEVER_ADDR) == LEVER_FROM and u16(code, LEVER_ADDR) == LEVER_TO, \
        "the CELL did not move even though its bytes did -- read the u16, not the bytes"
    print(f"\n  ★★ FULL BYTE DIFF vs {v['src_label']} (the base): {len(d_base)} bytes = "
          f"{len(functional)} functional + {len(d_base) - len(functional)} CRC")
    print(f"     🛑 COUNT CELLS, NOT BYTES: 2048 is `{LEVER_BYTES_FROM.hex()}` LE and 1024 is "
          f"`{LEVER_BYTES_TO.hex()}`, so the LOW byte 0x{LEVER_ADDR:05X} is 0x00 in BOTH and only")
    print(f"     0x{LEVER_ADDR + 1:05X} moves. The edit is ONE 2-byte CALIBRATION CELL whose byte "
          "diff is ONE byte. Asserting '2 bytes' would FAIL a correct build.")
    print(f"      {'range':<17} {'B':>2}  {'base':<10} -> {'built':<10}  owner")
    for a, b in diff_runs(code, base):
        owner = (f"CRC trailer of [0x{blk[0]:06X},0x{blk[1]:06X})" if a in crc_only else
                 f"LEVER C cell 0x{LEVER_ADDR:05X} {LEVER_FROM} -> {LEVER_TO} "
                 f"(tp+0x{LEVER_TP_DISP:04X}); high byte of the u16")
        print(f"      0x{a:05X}-0x{b:05X} {b - a + 1:2d}  {bytes(base[a:b + 1]).hex():<10} -> "
              f"{bytes(code[a:b + 1]).hex():<10}  {owner}")
    print(f"      0x{LEVER_ADDR:05X}-0x{LEVER_ADDR + 1:05X}  2  "
          f"{bytes(base[LEVER_ADDR:LEVER_ADDR + 2]).hex():<10} -> "
          f"{bytes(code[LEVER_ADDR:LEVER_ADDR + 2]).hex():<10}  (the same run read as the CELL: "
          f"{LEVER_FROM} -> {LEVER_TO})")
    assert bytes(code[LEVER_ADDR:LEVER_ADDR + 2]) == bytes(stock[LEVER_ADDR:LEVER_ADDR + 2]), \
        "the built cell is not byte-identical to STOCK at the same address"
    print(f"      ⇒ ONE calibration cell + ONE CRC word. Nothing else moved, anywhere in "
          f"[0x{START:X}, 0x{END:X}).")

    # ---- THE FULL BYTE DIFF vs STOCK, CLASSIFIED ---------------------------------------------------
    cls = build_class_map(code)
    runs = diff_runs(code, stock)
    d_stock = sum(b - a + 1 for a, b in runs)
    print(f"\n  FULL BYTE DIFF vs STOCK: {d_stock} bytes in {len(runs)} runs -- what {name} STILL "
          "carries:")
    print(f"      {'range':<17} {'B':>3}  owner")
    buckets, unclassified = {}, []
    for a, b in runs:
        owner = cls.get(a, "🛑 UNCLASSIFIED")
        if owner == "🛑 UNCLASSIFIED":
            unclassified.append((a, b))
        buckets[owner] = buckets.get(owner, 0) + (b - a + 1)
        print(f"      0x{a:05X}-0x{b:05X} {b - a + 1:3d}  {owner}")
    print(f"\n  vs-STOCK SUMMARY -- {len(buckets)} owners:")
    for owner, n in sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"      {n:4d} B  {owner}")
    assert not unclassified, \
        f"UNCLASSIFIED residual vs stock: {[(hex(a), hex(b)) for a, b in unclassified[:16]]}"
    assert LEVER_ADDR not in cls or all(code[i] == stock[i] for i in (LEVER_ADDR, LEVER_ADDR + 1)), \
        "0xC63A0 still differs from stock"
    assert not any(a <= LEVER_ADDR <= b for a, b in runs), \
        f"🛑 0x{LEVER_ADDR:05X} still appears in the vs-STOCK diff -- the revert did not take"
    print(f"      ★ 0x{LEVER_ADDR:05X} has VANISHED from the vs-stock diff: {name} carries the "
          "STOCK damper weight.")

    # ---- re-read the cell FROM THE BUILT IMAGE -----------------------------------------------------
    got = u16(code, LEVER_ADDR)
    assert got == LEVER_TO == 1024, f"the built image reads {got} at 0x{LEVER_ADDR:05X}"
    print(f"\n  ✅ RE-READ FROM THE BUILT IMAGE: 0x{LEVER_ADDR:05X} = {got} "
          f"(bytes {bytes(code[LEVER_ADDR:LEVER_ADDR + 2]).hex()}, little-endian) = STOCK.")

    # ---- write -------------------------------------------------------------------------------------
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {bin_out}: a DIFFERENT image already exists (on disk "
            f"{hashlib.sha256(existing).hexdigest()}, about to write "
            f"{hashlib.sha256(bytes(code)).hexdigest()}). A same-number re-cut destroyed a "
            "predecessor's snapshot once already and produced an artefact NO gate could check.")
    Path(bin_out).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {bin_out}\n    SHA256 {img_sha}")

    # ---- the .rwd, and the round-trip --------------------------------------------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(out_rwd).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, f"{name} output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec[START:END]) == bytes(code[START:END]), \
        "🛑 the decoded .rwd payload != the built image"
    assert bytes(dec) == bytes(code), \
        "🛑 the .rwd round-trip does not reproduce the plain image byte-for-byte"
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"  wrote {out_rwd}\n    SHA256 {rwd_sha}")
    print("  ✅ .rwd ROUND-TRIP: decoded with the on-ECU V9B cipher, it reproduces the plain image "
          "byte-for-byte (all 0x100000 bytes).")

    # ---- 🛑 EVERYTHING re-derived FROM THE READBACK ------------------------------------------------
    assert u16(dec, LEVER_ADDR) == LEVER_TO, f"readback 0x{LEVER_ADDR:05X} is {u16(dec, LEVER_ADDR)}"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave, "the readback cave differs"
    assert walk_all_blocks(bytes(dec)) == 0, "the readback CRC chain FAILED"
    probe_rb = bytearray(dec)
    struct.pack_into("<H", probe_rb, LEVER_ADDR, LEVER_FROM)
    V74.assert_must_not_change(probe_rb, f"{name} readback", stock, base)
    assert [i for i in range(START, END) if probe_rb[i] != dec[i]] == MOVED_BYTES, \
        "the readback's keep-list relaxation is not exactly the lever"
    rb_func = [i for i in range(START, END)
               if dec[i] != base[i] and i not in crc_only]
    assert rb_func == MOVED_BYTES, \
        f"the readback's functional diff vs the base is {[hex(x) for x in rb_func]}"
    V72.assert_lever_c_single_reader(bytes(dec))
    for mode in CHECK_MODES:
        for arr, nm in PTR_ARRAYS:
            rb = factor_rec(dec, arr, mode)
            ln = rec_len(dec, rb)
            assert rb == factor_rec(base, arr, mode) and \
                bytes(dec[rb:rb + ln]) == bytes(base[rb:rb + ln]), \
                f"readback: the mode-{mode} {nm} record @0x{rb:05X} differs from the base"
    V74.assert_clamp_census(bytes(dec))
    print("  ✅ READBACK: the cell, the whole cave, the frozen keep-list (relaxation = exactly the")
    print("     two lever bytes), the single-reader census, the mode-24/26 records, the clamp")
    print("     census and the full CRC chain -- ALL re-verified ON THE READ-BACK BYTES.")

    print("\n  " + "-" * 98)
    print(f"  {name} BUILT -- UNFLASHED." +
          ("" if v["recommended"] else "  🛑 NOT RECOMMENDED."))
    print(f"    plain image  {os.path.basename(bin_out)}\n      SHA256 {img_sha}")
    print(f"    rwd          {os.path.basename(out_rwd)}\n      SHA256 {rwd_sha}")
    print(f"    CHANGES vs {v['src_label']}: the 2-byte cell 0x{LEVER_ADDR:05X} {LEVER_FROM} -> "
          f"{LEVER_TO} (1 byte actually moves: 0x{LEVER_ADDR + 1:05X}, 0x08 -> 0x04) + its "
          f"0x{blk[1]:06X} CRC word. NOTHING ELSE.")
    print(f"    DOES NOT CHANGE: FactorC, FactorE, FactorB, FactorD, the ceiling, the friction lane,")
    print(f"      0xC407E, the {CAVE_EXTENT}-byte probe cave, 0x454FE, both `sar` sites, the gate,")
    print(f"      the five arms, V72's gain_A r26 cut, the pointer arrays, the config table, and")
    print(f"      every disengaged-column record.")
    if not v["recommended"]:
        print("    🛑 V77B IS NOT A RECOMMENDATION. It keeps V75's engaged-mode configuration, which")
        print("       HARD-FAULTED at a stoplight launch, and nothing has cleared that. It exists so")
        print("       the 'keep the grind fix, drop the mode-proof loop gain' option is on the shelf.")
    print("  " + "-" * 98)
    return {"bin": bin_out, "bin_sha": img_sha, "rwd": out_rwd, "rwd_sha": rwd_sha,
            "diff_base": len(d_base), "diff_stock": d_stock, "blocks": nblocks}


def build():
    print(__doc__)
    out = {}
    for name in ("V77", "V77B"):
        out[name] = build_one(name)
    print("\n" + "=" * 102)
    print("  BOTH ARTEFACTS BUILT -- UNFLASHED. Flash only on the operator's explicit instruction,")
    print("  naming the file and the bus.")
    for name, r in out.items():
        rec = "THE CANDIDATE" if VARIANTS[name]["recommended"] else "🛑 NOT RECOMMENDED"
        print(f"    {name:5s} [{rec}]")
        print(f"      {os.path.basename(r['bin'])}\n        {r['bin_sha']}")
        print(f"      {os.path.basename(r['rwd'])}\n        {r['rwd_sha']}")
    print("=" * 102)
    return out


def _self_check():
    """Everything checkable without an image."""
    assert LEVER_ADDR == 0xC63A0 and (LEVER_FROM, LEVER_TO) == (2048, 1024)
    assert LEVER_ADDR - TP == 0x73A0
    assert (CAVE_BASE, CAVE_EXTENT, CAVE_LAST) == (0xC4B34, 68, 0xC4B77)
    assert (START, END) == (0x13000, 0x100000)
    assert set(VARIANTS) == {"V77", "V77B"}
    assert len({v["out_bin"] for v in VARIANTS.values()}) == 2, "the two cuts share a filename"
    assert len({v["src"] for v in VARIANTS.values()}) == 2, "the two cuts share a base"


if __name__ == "__main__":
    _self_check()
    build()
