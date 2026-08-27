#!/usr/bin/env python3
"""builds/v80_v107/build_v83a_tva.py -- V83a = THE FLOWN V81, with three dosed cells reverted to HONDA. CAL-ONLY.

🛑 STATUS: BUILT (dry-run by default), UNFLASHED. Writing is gated on `ACCORD_V83A_WRITE`; the
default is a DRY RUN that verifies everything -- including a full in-memory .rwd encode/decode --
and writes nothing. **NO CAVE, NO CODE, NO INSTRUCTION BYTE.** Twelve halfwords, and every single
one of them is a REVERT TO HONDA'S OWN VALUE at that address.

🛑🛑 THIS BUILD WAS RE-CUT. The 11-edit cut (image sha256 `38baa9ca…`, .rwd `4c011076…`) was WRITTEN
AND REPORTED before edit 12 was authorised. Its artefacts are NOT overwritten -- the kit's rule is
exactly one flashable .rwd per build number, and a same-name re-cut destroys its predecessor's
snapshot and leaves a flashable artefact no gate can check. The 12-edit cut therefore carries its
lever set in BOTH filenames (`…-C63A0.1024…`) and the 11-edit pair was renamed
`SUPERSEDED-DO-NOT-FLASH-…`. Both remain on disk and both remain verifiable.

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
V81 is the image on the car (flown as route 67). It carries three dosed calibration cells inherited
from the V72->V75 lineage: the mode-26 damper `FactorE` ramp (V75's `k` = 1.5798), V72's `gain_A`
r26 cut (rec0/rec1 flattened to 512), and V72's Path-2 damper weight `0xC63A0` doubled to 2048.
**V83a puts all three back to Honda and changes nothing else.** It is the cleanest single statement
this kit can make about those levers, because after the build every edited cell is *byte-identical
to `stock_fw_dump/code.bin`* -- not "close to", not "scaled from", byte-identical. That is asserted
here by value, per address, on the built image and again on the decoded `.rwd` readback.

THE BASE.  `_v81_C407E.511-FRICTION.STOCK_plain_image.bin`
  sha256 `4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b`, asserted before a byte
  moves. V81 = the flown V75 with `0xC407E` restored to Honda's 511 (the DTC-0x1d interlock) and the
  friction rows reverted to stock. It flew as route 67, so V83a's base is *the image on the car*,
  which makes V83a a single-step delta from lived experience rather than from a paper build.

THE EDIT SET -- 12 halfwords, ALL reverts TO STOCK
--------------------------------------------------------------------------------------------------
  #   cell                      addr       V81      V83a     bytes
  1   FactorE mode-26 X[0]      0xD780E      12        60     0c00 -> 3c00
  2   FactorE mode-26 X[1]      0xD7810     200       400     c800 -> 9001
  3   FactorE mode-26 Y[1]      0xD7818     539       140     1b02 -> 8c00
  4   gain_A rec0 Y[0]          0xC6A72     512      3072     0002 -> 000c
  5   gain_A rec0 Y[1]          0xC6A74     512      3072     0002 -> 000c
  6   gain_A rec0 Y[2]          0xC6A76     512      2434     0002 -> 8209
  7   gain_A rec0 Y[3]          0xC6A78     512      2048     0002 -> 0008
  8   gain_A rec1 Y[0]          0xC6A86     512      3072     0002 -> 000c
  9   gain_A rec1 Y[1]          0xC6A88     512      3072     0002 -> 000c
 10   gain_A rec1 Y[2]          0xC6A8A     512      2488     0002 -> b809
 11   gain_A rec1 Y[3]          0xC6A8C     512      1536     0002 -> 0006
 12   Path-2 damper weight      0xC63A0    2048      1024     0008 -> 0004

Both edited RECORDS end the build BYTE-IDENTICAL TO STOCK over their whole `rec_len` -- so this is
not a partial write into a multi-cell record (the `0xD2A7E` hybrid's failure mode), it is a whole-
record revert. Asserted as such, per record, resolved through the pointer array / the hardcoded
record pointers, never against a guessed span. Edit 12 is a bare `tp` SCALAR, not a record member;
it is checked as a scalar and by census instead.

⚠ COUNT CELLS, NOT BYTES -- this kit has been bitten by that three times, and edit 12 is exactly the
shape that does it (2048 -> 1024 is ONE byte: `00 08` -> `00 04`, only `0xC63A1` moves). Three
different numbers describe this build and the build asserts all three, derived independently:
  · **12 cells / 12 functional runs**  -- the right way to count a lever set
  ·  24 bytes WRITTEN                  -- 12 halfwords, `struct.pack_into` twice each
  ·  **16 bytes DIFFER** from the base -- eight of the twelve targets share their high byte with V81
A full-image diff therefore reports **12 functional runs / 16 bytes**, plus 8 CRC bytes in 2 runs.
Anyone expecting "23 bytes" or "24 bytes" out of the diff will think a write went missing; it did
not. (The 23 in the authorising brief was 22 + 1, mixing the write count with the diff count.)

EDITS 1-3 -- THE mode-26 DAMPER `FactorE` RAMP, BACK TO HONDA'S
----------------------------------------------------------------
`FactorE` mode 26 is dereferenced through `0xC9F84[26]` -> `0xD780C`; X lives at **base+2** (not
base+4) and Y at base+0x0A, so `0xD780E`/`0xD7810` are X[0]/X[1] and `0xD7818` is Y[1]. Read off the
images rather than quoted:

    V81   X = [ 12, 200, 2500, 4000]   Y = [0, 539, 539, 927]
    V83a  X = [ 60, 400, 2500, 4000]   Y = [0, 140, 539, 927]   == STOCK, byte for byte

The ramp-regime incremental gain of the whole damper path is the frequency-INDEPENDENT scalar

    k = ((FactorC_Y[0] * FactorE_Y[1]) >> 10) / (FactorE_X[1] - FactorE_X[0])

    V81   k = ((566 * 539) >> 10) / (200 -  12) = 297/188 = **1.5798**
    V83a  k = ((566 * 140) >> 10) / (400 -  60) =  77/340 = **0.2265**

⇒ a 6.98x REDUCTION in the damper's ramp gain, achieved entirely by restoring Honda's own numbers.
`FactorC` mode-26 Y stays at V75's **[566, 234, 429, 908]** (Honda's Y[0] is 0) -- that lever is
explicitly OUT of scope here and is asserted unmoved.

⚠ MEASURED, AND IT CORRECTS THE BRIEF I WAS GIVEN. The FactorE *table* on V83a is byte-identical to
the one V71c / V72 / V73 flew -- verified by reading all three images plus stock. But **k on those
builds was 0.0000, not 0.2265**, because they carried Honda's `FactorC` Y[0] = **0**; the 566 is
V75's lever and V83a keeps it. So `k = 0.2265` is a combination that has NEVER FLOWN. What is true,
and is the honest form of the bracket, is that it is *interpolated inside* one:

    k = 0.0000  V71c / V72 / V73   flew, no fault
    k = 0.2265  **V83a**           <- interpolated, never flown as a combination
    k = 0.5799  V74                flew (its fault is pinned to `0xC407E`, not the damper)
    k = 1.5798  V75 / V81          flew (V75's fault likewise pinned to `0xC407E`)
    k = 4.1597  V79 / V80          flew; V80 = the worst grinding ever recorded, damper pinned at
                                   97% of ceiling ⇒ the damper became a RELAY

⚠ AND A SECOND CORRECTION TO THE BRIEF, measured rather than assumed. The brief predicted "above
35 km/h V83a deletes the engaged/manual asymmetry entirely". **It is off by one LERP segment.** The
only remaining asymmetry is `FactorC` m26 Y[0] = 566 against mode-24's 0, and a search over speed
counts 0..14000 (rates 0/94/198/528/999/1758/4500) puts the last differing point at **3839 counts =
59.93 km/h**, not ~2240 counts = 34.97 km/h. `FactorC` X[0] = 2240 is where Y[0] stops being the
LERP's CLAMP; it keeps WEIGHTING the interpolation all the way to X[1] = 3840 = 59.94 km/h. The
brief's 60 / 93 / 100 km/h equalities all hold exactly, and so does its creep prediction -- only the
crossover speed was wrong. `asymmetry_boundary()` re-derives it on every run.

EDITS 4-11 -- V72's `gain_A` r26 CUT, BACK TO HONDA'S
-------------------------------------------------------
`gain_A` is four HARDCODED 4-point records at `0xC6A68 / 0xC6A7C / 0xC6A90 / 0xC6AA4`, cross-LERPed
over speed and then indexed on the rate axis (`build_v71b_tva.gain_a_q10`, mirroring
`FUN_0003ad74`'s second half plus the LERP at 0x3AAD0-0x3AB2A). V72 flattened **rec0 and rec1 only**
to 512 -- the cut is creep-only *by record selection*, which is why rec2/rec3 are byte-stock on every
image in the lineage. V83a reverts rec0/rec1; rec2/rec3 are asserted untouched and byte-stock.

    rec0 Y   V81 [512, 512,  512,  512]  ->  V83a [3072, 3072, 2434, 2048]  == STOCK
    rec1 Y   V81 [512, 512,  512,  512]  ->  V83a [3072, 3072, 2488, 1536]  == STOCK
    rec2 Y                                   [2664, 2664, 2243, 1436]  == STOCK, UNTOUCHED
    rec3 Y                                   [2560, 2560, 2145, 1331]  == STOCK, UNTOUCHED

This is a **manual-arm revert**: with the LKAS gate dead, as it is on this lineage, the LERP is the
live path, so restoring the records is what actually reaches the car. After the build the kit's own
`build_v71b_tva.assert_gain_a(buf, label, doubled=False)` -- the guard that demands ALL FOUR records
equal Honda's -- passes on V83a, on the readback, and it is exactly the guard that FAILS on V81.

EDIT 12 -- `0xC63A0` 2048 -> 1024, AND THE DIRECTIVE THAT IS BEING RETIRED TO ALLOW IT
----------------------------------------------------------------------------------------
🛑 **A STANDING OPERATOR DIRECTIVE SAID: "do not double `0xC63A0`, that is what was causing the hard
faults." THAT DIRECTIVE IS RETIRED HERE -- BY DECISION, ON EVIDENCE, NOT QUIETLY IGNORED.**
**PROVENANCE, RECORDED EXACTLY: the operator was ASKED DIRECTLY and EXPLICITLY APPROVED retiring it
on the evidence below (2026-08-07).** The distinction between "retired by an informed decision" and
"overridden because it was inconvenient" is the entire point of this paragraph -- a future reader
finding `0xC63A0` moved off the keep-list must be able to see WHO decided and ON WHAT. The
directive rested on a premise the record has since falsified:
  · `0xC63A0` = tp+0x73A0 has **exactly ONE reader image-wide** -- `ld.hu -0x73a0[tp],r9` @`0x381AC`
    -- and **ZERO writers**. Re-measured on this build by `V72.assert_lever_c_single_reader`, a raw
    byte scan over both displacement parities plus the disp23 form, run on the input, the output and
    the `.rwd` readback.
  · Its only reader is `FUN_00038148`, the Path-2 aggregator, where it weights the `gp-0x6bd0`
    (damper) term of a six-term sum. `FUN_00038148` writes exactly TWO cells, `gp-0x374c` (its own
    accumulator) and `gp-0x6b70` (its output). **It never writes `gp-0x6b26`, `gp-0x6c2c` or
    `gp-0x6a5e`** ⇒ there is NO firmware data path from `0xC63A0` to the faulting monitor.
  · The actual fault mechanism was `0xC407E` = 850 against a 512-count trip -- **already reverted in
    V81**, and asserted still at 511 by this build.
⇒ Retiring the directive costs nothing that the interlock does not already cover.

🛑 **THE REASON FOR THE EDIT IS COMPARABILITY, NOT EFFICACY. Say so plainly.** Stock, the FLOWN V76
(`_v76_v38base_relu_damper`, the V38-base cut behind
`V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd`) and V80 **all read 1024**, measured
from the bytes for this build. V81's 2048 is therefore the LAST remaining cell that makes V83a
non-comparable to the corpus it will be scored against. It also moves loop gain in the same
direction as the FactorE revert. ⚠ A trap for anyone spot-checking this: the SUPERSEDED
`_v76_gate_fb_arm5244_gateprobe` sibling reads **2048** -- it never flew. Check the V38-base cut.

🛑 **IT IS NOT CLAIMED TO EXPLAIN THE RING.** An independent analysis bounds its maximum effect at
**<= 1.32x**, not the naive 1.5x, because `FUN_00038148`'s accumulator carries a one-pole IIR at
`0xC63AC` = 102 ⇒ alpha = 102/1024 = 0.0996. Re-derived numerically in `_self_check()` at fs = 1 kHz:
the true -3 dB corner is **16.71 Hz**, and at 27.75 Hz Path 2 arrives at **|H| = 0.516, -54.1 deg**,
so the paths do NOT sum in phase. Applying that correction still leaves V81 at 1.81 against an
observed ring ratio of 2.68 ⇒ this cell does not close the gap and is not being asked to.
`0xC63AC` = 102 is on the must-not-move list precisely because the bound above depends on it.
⊕ Prior art: V77 (`V77-V74BASE-C63A0.1024-loopgain-revert`) and V77B (`V77B-V75BASE-C63A0.1024-
NOT-RECOMMENDED-UNFLASHED`) both cut this exact lever and **neither flew**; both .rwd files are on
disk under `SUPERSEDED-2026-08-07-BY-V76-V38BASE-`.

GATE 1 -- RAM OWNERSHIP.  **PASS, and VACUOUS BY CONSTRUCTION.** [EVIDENCE]
----------------------------------------------------------------------------
V83a is CAL-ONLY. It allocates no RAM, writes no code, adds no instruction, moves no cave byte and
introduces no new reader or writer of anything. **Zero new RAM ⇒ nothing to own.** Said explicitly,
because "vacuous" is a claim and not an excuse, here is what is MEASURED rather than argued:
  · Both edit targets are pure DATA. `FactorE` m26 is reachable ONLY through the pointer array
    `0xC9F84`, which is asserted byte-STOCK for all 34 modes (as are the other five arrays);
    `gain_A` is reachable only through four record pointers hardcoded in `FUN_0003ad74`, whose
    addresses, counts, X rows and terminators are all asserted unmoved.
  · The 68-byte cave at `0xC4B34` and the hook at `0x55C0E`: byte-identical to V81 AND equal to
    `build_v75_tva.build_cave()`'s from-scratch re-derivation, then re-disassembled out of the built
    image by V75's own decoder. Zero cave risk spent. Caves are this kit's ONLY bricking class.
  · The V75 probe's own GATE 1 (`assert_probe_censuses`) is re-run unchanged on input, output and
    readback: the cave READS `gp-0x6bd0` and `gp-0x6ac2`, writes NEITHER, touches no lockstep shadow.
  · `0xC407E`'s census (0 writers / 3 signed `ld.h` readers, all in `FUN_00036c12`) is re-run via
    `V74.assert_clamp_census` -- the DTC-0x1d interlock V81 restored is asserted still at 511.
  · Whole-record identity: both edited records are byte-STOCK afterwards, so no neighbouring record,
    count word, X axis or terminator is clipped by a partial write.

GATE 2 -- CLOSED-LOOP STABILITY (MAGNITUDE **AND** PHASE).  Argued honestly.
------------------------------------------------------------------------------
  PHASE. **Unchanged, literally.** V83a introduces no filter, no pole, no zero, no delay, no new
  state, no new sample point and no task-order change. The only things that move are two STATIC LERP
  TABLES. Every pole, zero and task-order relationship in the image is bit-identical to V81's, so
  the phase response of every loop these signals are in is unchanged. This is the strongest form
  this gate can take. [EVIDENCE]

  MAGNITUDE. Two directions, and they must be stated separately -- "no loop gain rises anywhere" is
  TRUE against Honda and FALSE against V81, and pretending otherwise would bury the real content of
  edits 4-11:
   (a) **Against STOCK: nothing rises. Every one of the 11 target values IS Honda's value at that
       address** -- asserted cell by cell against `stock_fw_dump/code.bin`. No loop gain in the
       image exceeds Honda's anywhere, on either lever, at any frequency.
   (b) **Against the flown V81: the damper ramp gain FALLS 6.98x (k 1.5798 -> 0.2265) and the r26
       `gain_A` lane RISES up to 6.0x at creep** (512 -> 3072 on rec0/rec1). The rise is deliberate
       and is the whole point of edits 4-11. Its GATE-2 justification is not "it is small" -- it is
       that 3072/2434/2048 and 3072/2488/1536 are Honda's own shipped operating point, carried by
       every image in this kit up to and including V71c and by the recent V38-base line
       (V76 / V78 / V79 / V80), all measured from the bytes for this build. The cut being reverted
       was introduced by V72 and is `creep-only by record selection`, so the rise is bounded to the
       low-speed end where rec0/rec1 dominate the cross-LERP; at and above ~50 km/h rec2/rec3 carry
       the surface and they never moved.
   (c) The one nonlinearity in the damper path -- the ceiling clamp, `X=[300,800] Y=[512,1024]`,
       fallback `0xC6158` = 512 -- moves AWAY from saturation, not toward it. The delivered-dose
       table is recomputed FROM THE BUILT IMAGE and printed below; nothing on the reported grid
       clips.

🛑 THE RATIONALE FOR THE DAMPER REVERT IS **DOSE**, NOT **RELAY-NESS** -- CORRECTED
------------------------------------------------------------------------------------
An earlier draft of this header justified edits 1-3 as "removes the relay". **That is wrong and it
is worth stating why, because the wrong version is the intuitive one.** Relay-ness does NOT order
the ring: V81 is the LEAST relay-like of the three flown builds and it rings the HARDEST. The
supported rationale is narrower and it is quantitative -- **it reduces the delivered damper dose at
the ring's own operating point.** Scored at 100 km/h and R = 551 counts (the measured ring
amplitude), recomputed from each image's bytes:

    build                 dose    vs V76    observed ring
    V76 (flown)            227     1.00x        1.00
    V81 (flown)            310     1.37x        2.68
    V80 (flown)            496     2.19x        3.46
    **V83a**                96    **0.42x**     -- predicted below

  ⚠ CORRECTION TO THE AUTHORISING BRIEF: it quoted V83a at "96 counts = 0.36x V76". The absolute
  dose 96 is right and reproduces exactly; the RATIO is **0.42x** (96/227 = 0.4229), not 0.36x.
  All three flown doses (227 / 310 / 496) and their ratios reproduce exactly as stated.

★ PRE-REGISTERED, FALSIFIABLE PREDICTION -- recorded BEFORE the drive, on purpose:
  **If V83a's 26-31 Hz ring is not below V76's, the dose model is WRONG and the damper is not what
  drives the ring.** The dose ordering above is monotone with the observed ring across all three
  flown builds; V83a is the first point that extrapolates BELOW the corpus rather than inside it,
  which is what makes it a test and not a fit.

🛑 THE HONEST COST, NOT BURIED
--------------------------------
**V83a gives up whatever ratchet suppression the damper dose was buying.** The record: 6-9 Hz is
FLAT across `k` = 0.58 -> 1.58, and improves only at V80's `k` = 4.16 (0.418, CI [0.33, 0.61] -- the
sole point outside its null), which cost a 2.09x broadband HF lift and produced the worst grinding
ever recorded. So the dose was cheap to give up in the 0.58-1.58 band *on the measured evidence*,
but V83a goes BELOW that band to 0.2265, which is untested territory on the low side. If the
micro-ratchet gets worse on V83a, edits 1-3 are the cause and reverting them is 6 bytes.
⚠ Edits 4-11 additionally restore 6.0x of creep r26 gain the car has not had since V71c. That is a
FEEL change as well as a lever change, and it is the more likely of the two to be noticed first.

Usage:
    python builds/v80_v107/build_v83a_tva.py                            # DRY RUN, verifies everything, writes nothing
    ACCORD_V83A_WRITE=rwd python builds/v80_v107/build_v83a_tva.py      # writes the plain image AND the flashable .rwd
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

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, START/END, encoders)
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v68_tva as V68                # noqa: E402  (cave geometry)
import build_v71b_tva as GA                # noqa: E402  ★ the gain_A record model + its own guard
import build_v72_tva as V72                # noqa: E402  (CAVE_EXTENT, ceiling constants)
import build_v74_tva as V74                # noqa: E402  (record readers, censuses, mode columns)
import build_v75_tva as V75                # noqa: E402  (cave re-derivation, probe census, surface)
import build_v81_tva as V81                # noqa: E402  ★ THE BASE's builder -- its attributed set
import v72_lane_model as LM                # noqa: E402  (lerp_int)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
CAVE_BASE = V68.CAVE_BASE                          # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT                      # 68 -- the PROVEN extent. Never grow it.
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
TP = LM.TP                                         # 0xBF000

u16, s16, u32 = V75.u16, V75.s16, V75.u32
rec_any, rec_len, rec4_y = V74.rec_any, V74.rec_len, V74.rec4_y
factor_rec, ceiling_floor = V74.factor_rec, V74.ceiling_floor
damper_authority = V74.damper_authority

# =====================================================================================================
# THE BASE -- the FLOWN V81 (route 67), and ONLY that cut
# =====================================================================================================
SRC_BIN = plain_image_path("_v81_C407E.511-FRICTION.STOCK_plain_image.bin")
SRC_SHA256 = "4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b"
NOT_THE_BASE = {  # sha256 -> why it must never be accepted
    "e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c":
        "_v75_CY0.566-EX1.200_magprobe -- V81's OWN base. It carries 0xC407E = 850, the DTC-0x1d "
        "hard-fault mechanism. V83a must never be cut on it.",
    "9a96b7fe0cb5263f9cbc528cb0a0a67744048f439373f326f5a7c966ff37f3d1":
        "_v75_CY0.566_magprobe -- the EX1-off sibling. It never flew.",
}
STOCK_BIN = stock_fw_path("code.bin")
# ⊕ the chain anchor: V81's own base, so V83a can be stated as V75 + two attributed sets + CRC.
V75_BIN, V75_SHA256 = V81.SRC_BIN, V81.SRC_SHA256

# =====================================================================================================
# THE EDIT SET -- (addr, V81 value to ASSERT, value to WRITE, which record, label)
# 🛑 Every `new` is asserted equal to STOCK at the same address. That is the strongest single check
# 🛑 on this build: V83a is a PURE REVERT TO HONDA in both tables.
# =====================================================================================================
FACTOR_E_REC = 0xD780C                  # asserted by DEREFERENCE, never quoted
GAIN_A_REC0, GAIN_A_REC1 = GA.RATE_A_RECORDS[0], GA.RATE_A_RECORDS[1]   # 0xC6A68, 0xC6A7C
GAIN_A_REC2, GAIN_A_REC3 = GA.RATE_A_RECORDS[2], GA.RATE_A_RECORDS[3]   # 0xC6A90, 0xC6AA4
REC4_X_OFF, REC4_Y_OFF = V75.REC4_X_OFF, V75.REC4_Y_OFF                 # 0x02, 0x0A

EDITS = (
    (0xD780E,  12,   60, "FactorE", "FactorE mode-26 X[0]"),
    (0xD7810, 200,  400, "FactorE", "FactorE mode-26 X[1]"),
    (0xD7818, 539,  140, "FactorE", "FactorE mode-26 Y[1]"),
    (0xC6A72, 512, 3072, "gainA0",  "gain_A rec0 Y[0]"),
    (0xC6A74, 512, 3072, "gainA0",  "gain_A rec0 Y[1]"),
    (0xC6A76, 512, 2434, "gainA0",  "gain_A rec0 Y[2]"),
    (0xC6A78, 512, 2048, "gainA0",  "gain_A rec0 Y[3]"),
    (0xC6A86, 512, 3072, "gainA1",  "gain_A rec1 Y[0]"),
    (0xC6A88, 512, 3072, "gainA1",  "gain_A rec1 Y[1]"),
    (0xC6A8A, 512, 2488, "gainA1",  "gain_A rec1 Y[2]"),
    (0xC6A8C, 512, 1536, "gainA1",  "gain_A rec1 Y[3]"),
    (0xC63A0, 2048, 1024, "scalar", "Path-2 damper weight"),
)
EDITED_RECORDS = {"FactorE": FACTOR_E_REC, "gainA0": GAIN_A_REC0, "gainA1": GAIN_A_REC1}

# ---- EDIT 12's own constants, stated once ----------------------------------------------------------
DAMP_WEIGHT_ADDR = V72.DAMP_WEIGHT_ADDR          # 0xC63A0
DAMP_WEIGHT_TP_DISP = V72.DAMP_WEIGHT_TP_DISP    # 0x73A0  (⚠ tp = 0xBF000, NOT 0xC0000)
DAMP_WEIGHT_READER = V72.DAMP_WEIGHT_READER      # 0x381AC, the ONE `ld.hu -0x73a0[tp],r9`
DAMP_WEIGHT_BASE, DAMP_WEIGHT_NEW = 2048, 1024   # V72's double -> Honda's own
PATH2_IIR_ADDR, PATH2_IIR_VALUE = 0xC63AC, 102   # the accumulator's one-pole coefficient
PATH2_FS_HZ = 1000.0                             # the confirmed control-task tick
RING_HZ, RING_AMPL_COUNTS = 27.75, 551           # the 26-31 Hz ring and its measured amplitude
# ⊕ the dose ladder the pre-registration rests on, stated independently and RE-MEASURED at runtime.
DOSE_LADDER_EXPECT = {"V76": 227, "V81": 310, "V80": 496, "V83a": 96}
DOSE_LADDER_IMAGES = {  # 🛑 the FLOWN cut of each, by filename -- the superseded siblings differ
    "V76": "_v76_v38base_relu_damper_plain_image.bin",
    "V80": "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin",
}

FACTOR_E_M26_BASE_XY = ([12, 200, 2500, 4000], [0, 539, 539, 927])      # the flown V81's
FACTOR_E_M26_NEW_XY = ([60, 400, 2500, 4000], [0, 140, 539, 927])       # == Honda's
GAIN_A_BASE_Y = {GAIN_A_REC0: [512] * 4, GAIN_A_REC1: [512] * 4}        # V72's cut, on the base
GAIN_A_NEW_Y = {GAIN_A_REC0: list(GA.RATE_A_Y_STOCK[0]), GAIN_A_REC1: list(GA.RATE_A_Y_STOCK[1])}
GAIN_A_FROZEN = (GAIN_A_REC2, GAIN_A_REC3)      # V72's cut is PARTIAL by record selection

# =====================================================================================================
# WHAT MUST NOT MOVE -- stated by VALUE, as literals, so a drift in any imported module FAILS here
# =====================================================================================================
KEEP_CELLS = {
    0xC6CD0: (3564, "V57's decoupled forward-reader cell."),
    0xC646C: (891,  "the SHARED sensor scale -- V57 decoupled the forward reader OFF it. STOCK."),
    # 🛑 RELABELLED 2026-08-08. These are NOT a deadband arm -- the pre-gain deadband is
    # 0xC61B8 = 102, the NEXT cell, and it was never rescaled alongside the gain. Both of
    # these are output clamps and both are 4x Honda (512 -> 1024 at V22 -> 2048 at V38).
    0xC61B2: (2048, "ARBITRATION output clamp (FUN_0002b422, +/-tp+0x71b2). 4x Honda's 512."),
    0xC61B4: (2048, "LKAS-GAIN output clamp (+/-tp+0x71b4). 4x Honda's 512."),
    0xC407E: (511,  "🛑 THE DTC-0x1d INTERLOCK. Honda's clamp, one count under its own 512 trip. "
                    "V81 restored it after V73 raised it to 850 and V74/V75 hard-faulted."),
    0xC62EA: (0,    "the low-speed steer lockout, removed since V52."),
    # 🛑 0xC63A0 was on this list for the 11-edit cut. EDIT 12 MOVES IT -- see the header for the
    # 🛑 explicit retirement of the "do not touch 0xC63A0" directive. It is now an EDIT, not a KEEP.
    0xC63AC: (102,  "🛑 the Path-2 accumulator's one-pole IIR coefficient. UNTOUCHED -- the <=1.32x "
                    "bound on edit 12's effect is DERIVED from it (alpha = 102/1024, corner "
                    "16.71 Hz, |H| = 0.516 at 27.75 Hz)."),
    0xC6444: (512,  "gain_A ARM, stock -- 🛑 NOT the gain_A records. Raising it is UNTESTED and is "
                    "not this build's business."),
    0xC6446: (512,  "gain_B arm, stock."),
    0xC643E: (1536, "gain_A arm, stock."),
    0xC6206: (512,  "stock."),
    0xC6208: (205,  "stock."),
    0xC521A: (3584, "🛑 inside the CRC-SKIPPED block [0xC5000,0xC5FFC). Untouched."),
    0xC5232: (3584, "🛑 inside the CRC-SKIPPED block [0xC5000,0xC5FFC). Untouched."),
    0xC6158: (512,  "the ceiling's tp+0x7158 FALLBACK -- both branches must still yield 512."),
    0xC407C: (461,  "the interlock clamp's NEIGHBOUR. Owner UNIDENTIFIED. Untouched."),
}
KEEP_BYTES = {
    0x454FE: (0xB5, "V42's macro-ratchet fix (`br` not `bne`). KEEP."),
    0x3AA96: (0xC5, "V72's gate byte."),
    0x3AB76: (0xAA, "the r26 `sar` site -- STOCK. 🛑 V62's `a9` CAUSES GRIND #2; the fix is an ABSENCE."),
    0x3AC20: (0xAA, "the r24 `sar` site -- STOCK. Same reason."),
}
KEEP_HALFWORDS = {
    0x2A1F0: (0x7CD0, "V57's decoupling displacement -> tp+0x7CD0 = 0xC6CD0."),
}
KEEP_F32 = {
    0xC4004: (bytes.fromhex("0000003f"), 0.5,
              "the DTC-0x1d monitor's THRESHOLD. FROZEN -- V83a loosens nothing."),
}
SAR_SITES = V75.SAR_SITES                       # both at STOCK, checked as full halfwords too

FACTOR_B_PTRS, FACTOR_C_PTRS = V75.FACTOR_B_PTRS, V75.FACTOR_C_PTRS
FACTOR_D_PTRS, FACTOR_E_PTRS = V75.FACTOR_D_PTRS, V75.FACTOR_E_PTRS
CEILING_PTRS, FRICTION_PTR_ARRAY = V75.CEILING_PTRS, V74.FRICTION_PTR_ARRAY
ALL_PTR_ARRAYS = {"FactorB": FACTOR_B_PTRS, "FactorC": FACTOR_C_PTRS, "FactorD": FACTOR_D_PTRS,
                  "FactorE": FACTOR_E_PTRS, "ceiling": CEILING_PTRS, "friction": FRICTION_PTR_ARRAY}
N_MODES = 34
LIVE_MODE, MANUAL_MODE = V75.LIVE_MODE, 24          # 26 = engaged, 24 = THIS car's MANUAL
ENGAGED_EXPECTED, DISENGAGED_EXPECTED = V75.ENGAGED_EXPECTED, V75.DISENGAGED_EXPECTED
THIS_CAR_ROW, THIS_CAR_KEY = V75.THIS_CAR_ROW, V75.THIS_CAR_KEY
Q10 = V75.Q10
MANUAL_EXPECT = {"B": 0xD6760, "C": 0xD67E4, "D": 0xD67A4, "E": 0xD6820,
                 "ceiling": 0xD60B4, "friction": 0xD6A64}
FACTOR_C_M26_KEEP = [566, 234, 429, 908]        # V75's lever. OUT OF SCOPE here; asserted unmoved.
FACTOR_C_M26_REC = 0xD77D0
CEILING_X, CEILING_Y = V74.CEILING_X, V74.CEILING_Y      # [300, 800], [512, 1024]
CEILING_FLOOR = V75.CEILING_FLOOR                        # 512
FRICTION_NPT, FRICTION_X = V74.FRICTION_NPT, V74.FRICTION_X
FRICTION_Y_STOCK = V74.FRICTION_Y_STOCK

# ---- the axes, stated once, as the operator specified them -----------------------------------------
SPEED_COUNTS_PER_KMH = 64.0625          # voted vehicle speed, FactorB/FactorC axis
RATE_COUNTS_PER_DEG_S = 4.7121          # motor rate, FactorD/FactorE axis
REPORT_SPEEDS_KMH = (5, 60, 100)
REPORT_RATES = (94, 198, 528, 999, 1758)
CREEP_DEG_S = 20                        # the operator's creep reference point

# =====================================================================================================
# OUTPUT NAMING -- 🛑 exactly ONE flashable .rwd and ONE plain image per build number on disk
# =====================================================================================================
# A recorded hazard: two V70 cuts both wrote `_v70_plain_image.bin`, so the second OVERWROTE the
# first's snapshot while the first's `.rwd` stayed flashable -- an artefact NO gate could check.
# 🛑 THE SEPARATOR IS `.`/`-`, NEVER `+`: the Ghidra MCP layer once URL-decoded a `+` to a SPACE.
# 🛑 THE LEVER SET IS IN BOTH FILENAMES. The 11-edit cut shipped as `FACTORE.STOCK-GAINA.STOCK`;
# 🛑 edit 12 makes a DIFFERENT image, so it gets a DIFFERENT name rather than a same-name re-cut.
VARIANT_TOKEN = "FACTORE.STOCK-GAINA.STOCK-C63A0.1024"
SUPERSEDED_11_EDIT = {  # the reported 11-edit pair -- renamed, never overwritten, never deleted
    "image": "_v83a_FACTORE.STOCK-GAINA.STOCK_plain_image.bin",
    "image_sha": "38baa9cad1f858e4b719f7135ff4ff3b3442d38052fdb38835bc9914bfb98f5c",
    "rwd_sha": "4c011076de7a5a5fc10d8e595168293cd3b2260ff8af831a1221be4cd6f97ca1",
}
TAG = f"V81BASE-{VARIANT_TOKEN}-magprobe-6bd0-thermo-6ac2"
BIN_OUT = str(plain_image_path(f"_v83a_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V83A-{TAG}-0x{START:X}-0x{END:X}.rwd")

WRITE_MODE = os.environ.get("ACCORD_V83A_WRITE", "").strip().lower()
assert WRITE_MODE in ("", "none", "bin", "rwd"), \
    f"ACCORD_V83A_WRITE={WRITE_MODE!r} -- expected '' (dry run), 'bin' or 'rwd'"


# =====================================================================================================
# ASSERTIONS
# =====================================================================================================

def assert_edit_geometry(buf, label):
    """🛑 Every edit address is DERIVED from its record, never trusted as a literal.

    The `X at base+2, not base+4` trap is on the kit's record, and so is the flat-0x18 window that
    spills into the next mode's record. Both are closed here by dereferencing and by `rec_len`.
    """
    rec = factor_rec(buf, FACTOR_E_PTRS, LIVE_MODE)
    assert rec == FACTOR_E_REC, \
        f"{label}: FactorE m{LIVE_MODE} dereferences to 0x{rec:05X}, expected 0x{FACTOR_E_REC:05X}"
    n = u16(buf, rec)
    assert n == 4 and rec_len(buf, rec) == 0x14, f"{label}: FactorE m{LIVE_MODE} count is {n}"
    want = {0xD780E: rec + REC4_X_OFF + 0, 0xD7810: rec + REC4_X_OFF + 2,
            0xD7818: rec + REC4_Y_OFF + 2}
    for addr, derived in want.items():
        assert addr == derived, \
            f"🛑 {label}: the edit at 0x{addr:05X} is NOT where the record puts it (0x{derived:05X})"
    assert GA.RATE_A_RECORDS == (GAIN_A_REC0, GAIN_A_REC1, GAIN_A_REC2, GAIN_A_REC3) == \
        (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4), \
        f"{label}: the hardcoded gain_A record pointers moved: {GA.RATE_A_RECORDS}"
    for i, base in enumerate(GA.RATE_A_RECORDS):
        assert u16(buf, base) == 4, f"{label}: gain_A 0x{base:05X} count moved"
        assert u16(buf, base + 0x12) == 0, f"{label}: gain_A 0x{base:05X} terminator moved"
        assert list(struct.unpack_from("<4h", buf, base + REC4_X_OFF)) == \
            list(GA.RATE_A_X_STOCK[i]), f"{label}: gain_A 0x{base:05X} X row moved"
    for j, addr in enumerate((0xC6A72, 0xC6A74, 0xC6A76, 0xC6A78)):
        assert addr == GAIN_A_REC0 + REC4_Y_OFF + 2 * j, f"🛑 {label}: 0x{addr:05X} is not rec0 Y[{j}]"
    for j, addr in enumerate((0xC6A86, 0xC6A88, 0xC6A8A, 0xC6A8C)):
        assert addr == GAIN_A_REC1 + REC4_Y_OFF + 2 * j, f"🛑 {label}: 0x{addr:05X} is not rec1 Y[{j}]"
    # ---- EDIT 12: a bare `tp` SCALAR, not a record member -------------------------------------------
    # ⚠ THE RECURRENT OFF-BY-0x1000: tp = 0xBF000, so tp+0x73A0 is 0xC63A0, NOT 0xC73A0.
    assert DAMP_WEIGHT_ADDR - TP == DAMP_WEIGHT_TP_DISP == 0x73A0, \
        f"🛑 {label}: 0x{DAMP_WEIGHT_ADDR:05X} is not tp+0x{DAMP_WEIGHT_TP_DISP:04X} -- the " \
        "off-by-0x1000 trap has recurred four times in this kit"
    assert DAMP_WEIGHT_ADDR == 0xC63A0 and PATH2_IIR_ADDR == 0xC63AC


def assert_lever_c_census(buf, label):
    """🛑 GATE 1 FOR EDIT 12 -- the whole safety argument for retiring the directive, MEASURED.

    `V72.assert_lever_c_single_reader` is a RAW BYTE scan over both displacement parities plus the
    disp23 form; it fails loudly if a second reader or any writer exists. Run on input, output and
    the `.rwd` readback, so a change that silently gave this cell another consumer would fail the
    build rather than fly.
    """
    n_odd, real = V72.assert_lever_c_single_reader(bytes(buf))
    assert [a for a, _r in real] == [DAMP_WEIGHT_READER], \
        f"🛑 {label}: 0x{DAMP_WEIGHT_ADDR:05X} readers are {[hex(a) for a, _ in real]}"
    assert u16(buf, PATH2_IIR_ADDR) == PATH2_IIR_VALUE, \
        f"🛑 {label}: the Path-2 IIR coefficient 0x{PATH2_IIR_ADDR:05X} moved -- the <=1.32x bound " \
        "on edit 12 is derived from it"
    return len(real), n_odd


def path2_response(freq_hz, alpha=None, fs=None):
    """`FUN_00038148`'s accumulator as a one-pole IIR: y += alpha*(x - y). |H| and phase, exact.

    🛑 The -3 dB corner is NOT alpha*fs/(2*pi) (that gives 15.85 Hz); solved numerically it is
    16.71 Hz. Quoted from this function, never from the approximation.
    """
    import cmath
    import math
    a = alpha if alpha is not None else PATH2_IIR_VALUE / 1024
    f = fs if fs is not None else PATH2_FS_HZ
    z = cmath.exp(1j * 2 * math.pi * freq_hz / f)
    h = a / (1 - (1 - a) * z ** -1)
    return abs(h), math.degrees(cmath.phase(h))


def path2_corner_hz():
    """The true -3 dB corner, bisected rather than approximated."""
    lo, hi = 0.1, 500.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if path2_response(mid)[0] > 2 ** -0.5:
            lo = mid
        else:
            hi = mid
    return lo


def assert_targets_are_stock(stock):
    """🛑🛑 THE STRONGEST SINGLE CHECK ON THIS BUILD. Every target value IS Honda's."""
    for addr, _pre, new, _rec, lbl in EDITS:
        got = u16(stock, addr)
        assert got == new, \
            f"🛑🛑 0x{addr:05X} ({lbl}): STOCK carries {got}, V83a wants to write {new}. V83a is " \
            "DEFINED as a pure revert to Honda in both tables -- if a target is not stock's own " \
            "value, the premise of this whole build is void. STOP."


def assert_base_preconditions(buf):
    for addr, pre, _new, _rec, lbl in EDITS:
        got = u16(buf, addr)
        assert got == pre, \
            f"🛑 the base's 0x{addr:05X} ({lbl}) is {got}, expected the flown V81's {pre}"


def assert_keep_list(buf, label):
    for addr, (want, why) in KEEP_CELLS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: 0x{addr:05X} = {got}, expected {want} -- {why}"
    for addr, (want, why) in KEEP_BYTES.items():
        assert buf[addr] == want, \
            f"🛑 {label}: 0x{addr:05X} = 0x{buf[addr]:02X}, expected 0x{want:02X} -- {why}"
    for addr, (want, why) in KEEP_HALFWORDS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: 0x{addr:05X} = 0x{got:04X}, expected 0x{want:04X} -- {why}"
    for addr, (raw, val, why) in KEEP_F32.items():
        got = bytes(buf[addr:addr + 4])
        assert got == raw and struct.unpack("<f", got)[0] == val, \
            f"🛑 {label}: 0x{addr:05X} = {got.hex()}, expected {raw.hex()} ({val}) -- {why}"
    for addr, raw in SAR_SITES.items():
        assert bytes(buf[addr:addr + 2]) == raw, \
            f"🛑 {label}: the `sar` site 0x{addr:05X} is {bytes(buf[addr:addr + 2]).hex()}, expected " \
            f"the STOCK {raw.hex()} -- reintroducing V62's `a9` CAUSES GRIND #2; the fix is an ABSENCE"


def assert_pointer_arrays_stock(buf, stock, label):
    """🛑 FactorE is reachable ONLY through these. A moved pointer redirects the lever silently."""
    for name, arr in ALL_PTR_ARRAYS.items():
        for mode in range(N_MODES):
            got, want = u32(buf, arr + mode * 4), u32(stock, arr + mode * 4)
            assert got == want, \
                f"{label}: {name} array 0x{arr:05X}[{mode}] -> 0x{got:05X}, STOCK says 0x{want:05X}"


def assert_manual_mode_frozen(buf, base_img, stock, label):
    """🛑 Mode 24 is THIS car's MANUAL steering. Byte-identical to the BASE across all six record
    types -- and, since V81's mode 24 is byte-stock, to STOCK as well. Every address RESOLVED
    THROUGH THE POINTER ARRAY and checked against an independently stated expectation."""
    out = {}
    for name, arr in ALL_PTR_ARRAYS.items():
        key = {"FactorB": "B", "FactorC": "C", "FactorD": "D", "FactorE": "E"}.get(name, name)
        rec = factor_rec(buf, arr, MANUAL_MODE)
        assert rec == MANUAL_EXPECT[key], \
            f"{label}: {name} m{MANUAL_MODE} dereferences to 0x{rec:05X}, expected " \
            f"0x{MANUAL_EXPECT[key]:05X}"
        n = rec_len(buf, rec)                # 🛑 the record's OWN length: 4 + 4*count
        assert bytes(buf[rec:rec + n]) == bytes(base_img[rec:rec + n]), \
            f"🛑 {label}: MANUAL mode {MANUAL_MODE} {name} @0x{rec:05X} ({n} B) differs from the BASE"
        assert bytes(buf[rec:rec + n]) == bytes(stock[rec:rec + n]), \
            f"🛑 {label}: MANUAL mode {MANUAL_MODE} {name} @0x{rec:05X} ({n} B) differs from STOCK"
        out[key] = rec
    return out


def assert_friction_all_stock(buf, stock, label):
    """All 34 friction records byte-STOCK -- V81 reverted them and V83a must not touch them."""
    for mode in range(N_MODES):
        rec = factor_rec(buf, FRICTION_PTR_ARRAY, mode)
        n, xs, ys = rec_any(buf, rec)
        assert (n, xs, ys) == (FRICTION_NPT, FRICTION_X, FRICTION_Y_STOCK), \
            f"🛑 {label}: friction m{mode} @0x{rec:05X} is ({n}, {xs}, {ys}), expected Honda's " \
            f"({FRICTION_NPT}, {FRICTION_X}, {FRICTION_Y_STOCK})"
        ln = rec_len(buf, rec)
        assert bytes(buf[rec:rec + ln]) == bytes(stock[rec:rec + ln]), \
            f"🛑 {label}: friction m{mode} @0x{rec:05X} is not byte-STOCK"


def assert_gain_a(buf, base_img, stock, label, reverted):
    """gain_A, by exact value on all four records -- plus whole-record byte identity to STOCK on the
    two V83a reverts and to the BASE on the two it must not touch."""
    for i, base in enumerate(GA.RATE_A_RECORDS):
        want = (GAIN_A_NEW_Y.get(base) or list(GA.RATE_A_Y_STOCK[i])) if reverted else \
            (GAIN_A_BASE_Y.get(base) or list(GA.RATE_A_Y_STOCK[i]))
        got = rec4_y(buf, base)
        assert got == want, f"🛑 {label}: gain_A 0x{base:05X} Y is {got}, expected {want}"
        for y in got:
            assert 0 < y < 0x8000, \
                f"🛑 {label}: gain_A 0x{base:05X} Y = {y} is not a positive SIGNED halfword -- " \
                "FUN_0003ad74 reads these through `short *` and the lane would INVERT"
    for base in GAIN_A_FROZEN:
        n = rec_len(buf, base)
        assert bytes(buf[base:base + n]) == bytes(base_img[base:base + n]) == \
            bytes(stock[base:base + n]), \
            f"🛑 {label}: gain_A 0x{base:05X} moved -- V72's cut is PARTIAL by record selection and " \
            "rec2/rec3 are byte-stock on every image in the lineage. UNTOUCHED is the whole point."
    if reverted:
        for base in (GAIN_A_REC0, GAIN_A_REC1):
            n = rec_len(buf, base)
            assert bytes(buf[base:base + n]) == bytes(stock[base:base + n]), \
                f"🛑 {label}: gain_A 0x{base:05X} is not byte-STOCK after the revert -- a WHOLE-" \
                "record revert is what makes this a revert and not a partial write"
        # 🛑 the kit's OWN gain_A guard, the one that FAILS on the base, must now PASS.
        GA.assert_gain_a(buf, label, doubled=False)


def assert_factor_surface(buf, stock, label, reverted):
    """FactorC m26 unmoved; FactorE m26 at the expected X/Y and, after the revert, byte-STOCK."""
    rec = factor_rec(buf, FACTOR_C_PTRS, LIVE_MODE)
    assert rec == FACTOR_C_M26_REC, f"{label}: FactorC m{LIVE_MODE} -> 0x{rec:05X}"
    n, xs, ys = rec_any(buf, rec)
    assert (n, ys) == (4, FACTOR_C_M26_KEEP), \
        f"🛑 {label}: FactorC m{LIVE_MODE} Y is {ys}, expected V75's {FACTOR_C_M26_KEEP} -- that " \
        "lever is explicitly OUT OF SCOPE for V83a"
    erec = factor_rec(buf, FACTOR_E_PTRS, LIVE_MODE)
    n, ex, ey = rec_any(buf, erec)
    want = FACTOR_E_M26_NEW_XY if reverted else FACTOR_E_M26_BASE_XY
    assert (n, ex, ey) == (4, want[0], want[1]), \
        f"🛑 {label}: FactorE m{LIVE_MODE} is ({ex}, {ey}), expected {want}"
    if reverted:
        ln = rec_len(buf, erec)
        assert bytes(buf[erec:erec + ln]) == bytes(stock[erec:erec + ln]), \
            f"🛑 {label}: FactorE m{LIVE_MODE} is not byte-STOCK after the revert"
    # FactorB / FactorD FLAT 1024 and the ceiling floor, per engaged mode, read BY COUNT
    for mode in ENGAGED_EXPECTED:
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD")):
            cnt, _x, y = rec_any(buf, factor_rec(buf, ptrs, mode))
            assert set(y) == {Q10}, f"{label}: {name} m{mode} ({cnt}-point) is not FLAT {Q10}: {y}"
        assert ceiling_floor(buf, mode) == CEILING_FLOOR, \
            f"{label}: mode {mode}'s ceiling floor moved"
    return ex, ey, ys


def damper_k(buf, mode):
    """The ramp-regime incremental gain: a frequency-INDEPENDENT scalar on the whole damper path."""
    _n, ex, ey = rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, mode))
    _n, _cx, cy = rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, mode))
    return (cy[0] * ey[1]) >> 10, ex[1] - ex[0]


def assert_cave_identical(buf, base_img, label):
    """🛑 THE CAVE AND THE HOOK ARE BYTE-IDENTICAL TO V81, three independent ways.

    Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU). V83a does not
    write the cave at all -- it RE-DERIVES V75's 68 bytes from `build_v75_tva.build_cave()`, asserts
    the image already carries them, re-disassembles them out of the image with V75's own decoder,
    and asserts byte identity with the base.
    """
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    assert cave == bytes(base_img[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]), \
        f"🛑 {label}: the 68-byte cave @0x{CAVE_BASE:05X} differs from the base's"
    derived, listing = V75.build_cave()
    assert cave == derived, \
        f"🛑 {label}: the cave does not equal `build_v75_tva.build_cave()`'s re-derivation\n" \
        f"      image  {cave.hex()}\n      derive {derived.hex()}"
    redis = V75.redisassemble_cave(cave)
    assert [r for _a, r, _m in redis] == [r for _a, r, _t in listing], \
        f"{label}: the readback re-disassembly diverges from the emitted listing"
    assert not [m for _a, _r, m in redis if m == "nop" or m.startswith("??")], \
        f"{label}: the cave re-disassembly contains a nop or an undecoded halfword"
    stores = [m for _a, _r, m in redis if m.startswith(("st.b", "st.h", "st.w"))]
    assert len(stores) == 1 and stores[0].startswith("st.b"), \
        f"{label}: the cave contains {stores}, expected exactly ONE st.b to the CAN-330 payload"
    assert bytes(buf[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(base_img[HOOK_ADDR:HOOK_ADDR + 4]) == \
        FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: the hook @0x{HOOK_ADDR:05X} is not `jarl 0x{CAVE_BASE:05X}`"
    assert bytes(buf[HOOK_ADDR + 4:HOOK_ADDR + 6]) == V75.HOOK_RETURN_INSN, \
        f"{label}: 0x{HOOK_ADDR + 4:05X} is not `mov 0x8,r7`"
    assert cave.count(HOOK_STOCK) == 1, f"{label}: the displaced movea is not present exactly once"
    return cave


def assert_identity_modulo(buf, ref_img, allowed, label, refname):
    """🛑 THE VALUE-ANCHORED VERIFIER -- whole-image identity modulo an ATTRIBUTED set.

    `verify/diff_build_vs_stock.py` is SPAN-based and will pass a WRONG VALUE inside a RIGHT RANGE. This is
    the strongest statement available: restore every byte V83a is ALLOWED to have changed, then
    assert the result is byte-for-byte the reference over the FULL 1 MiB -- not over [START, END).
    """
    probe = bytearray(buf)
    for a in allowed:
        probe[a] = ref_img[a]
    diff = [i for i in range(len(ref_img)) if probe[i] != ref_img[i]]
    assert not diff, \
        f"🛑 {label}: after restoring the {len(allowed)} ATTRIBUTED bytes, the image still differs " \
        f"from {refname} at {len(diff)} byte(s): {[hex(x) for x in diff[:16]]}. V83a is defined as " \
        f"{refname} plus the attributed set and NOTHING else."
    return bytes(probe)


def diff_runs(a_img, b_img, attribute, lo=0, hi=0x100000):
    """Contiguous differing runs, split wherever the attribution changes."""
    runs, prev = [], None
    for d in range(lo, hi):
        if a_img[d] == b_img[d]:
            prev = None
            continue
        if prev is not None and d == prev[1] + 1 and attribute(d) == attribute(prev[0]):
            prev = (prev[0], d)
            runs[-1] = prev
        else:
            prev = (d, d)
            runs.append(prev)
    return runs


def dose_table(buf, mode):
    """The delivered |gp-0x6bd0|, RECOMPUTED from the image, over the reported grid."""
    return {(kmh, r): damper_authority(buf, mode, int(kmh * SPEED_COUNTS_PER_KMH), r)
            for kmh in REPORT_SPEEDS_KMH for r in REPORT_RATES}


def asymmetry_boundary(buf, rates):
    """The speed counts at which mode 26 and mode 24 stop differing. SEARCHED, not asserted.

    ⊕ Reported because it is the only remaining engaged/manual asymmetry after edits 1-3, and the
    brief's stated expectation for it disagrees with the bytes -- see the header.
    """
    bad = [sc for sc in range(0, 14001)
           if any(damper_authority(buf, LIVE_MODE, sc, r) != damper_authority(buf, MANUAL_MODE, sc, r)
                  for r in rates)]
    return (min(bad), max(bad)) if bad else None


# =====================================================================================================
# THE BUILD
# =====================================================================================================

def build():
    print(__doc__)
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it."
    assert VARIANT_TOKEN in os.path.basename(BIN_OUT) and VARIANT_TOKEN in os.path.basename(OUT), \
        "🛑 the variant is not in BOTH filenames"
    assert "+" not in OUT and "+" not in BIN_OUT, "🛑 `+` in a filename URL-decodes to a SPACE"

    v81 = bytes(Path(SRC_BIN).read_bytes())
    stock = bytes(Path(STOCK_BIN).read_bytes())
    v75 = bytes(Path(V75_BIN).read_bytes())
    print("=" * 102)
    print(f"SOURCE (the FLOWN V81, route 67): {SRC_BIN}")
    src_sha = hashlib.sha256(v81).hexdigest()
    print(f"  SHA256 {src_sha}")
    for name, img in (("V81", v81), ("stock", stock), ("V75", v75)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert src_sha not in NOT_THE_BASE, f"🛑🛑 THE BASE IS {NOT_THE_BASE.get(src_sha)}"
    assert src_sha == SRC_SHA256, \
        f"🛑🛑 THE BASE IS NOT THE FLOWN V81. SHA256 is {src_sha}, expected {SRC_SHA256}."
    assert hashlib.sha256(v75).hexdigest() == V75_SHA256, "the V75 chain anchor drifted"
    print("  ✅ the base SHA256 is the V81 cut EXACTLY -- the image currently on the car.")
    print(f"  WRITE MODE: {WRITE_MODE or 'DRY RUN -- nothing will be written to disk'}")

    # =================================================================================================
    # GATE THE SOURCE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  GATING THE SOURCE -- everything below is measured on the INPUT before a byte moves")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert walk_all_blocks(v81) == 0, "the V81 source's own CRC chain does not verify"
    assert_targets_are_stock(stock)
    assert_base_preconditions(v81)
    assert_edit_geometry(v81, "V81 source")
    assert_keep_list(v81, "V81 source")
    assert_pointer_arrays_stock(v81, stock, "V81 source")
    assert_manual_mode_frozen(v81, v81, stock, "V81 source")
    assert_friction_all_stock(v81, stock, "V81 source")
    assert_gain_a(v81, v81, stock, "V81 source", reverted=False)
    assert_factor_surface(v81, stock, "V81 source", reverted=False)
    assert_cave_identical(v81, v81, "V81 source")
    V75.assert_probe_censuses(v81, cave_span, V75.CAVE_ACCESS_ON_OUTPUT)
    V74.assert_clamp_census(v81)
    n_rd, n_odd = assert_lever_c_census(v81, "V81 source")
    rows, ENGAGED, DISENGAGED = V74.derive_mode_columns(v81)
    assert tuple(ENGAGED) == ENGAGED_EXPECTED and tuple(DISENGAGED) == DISENGAGED_EXPECTED
    assert not (set(ENGAGED) & set(DISENGAGED)), "🛑 THE MODE COLUMNS ARE NOT DISJOINT"
    assert rows[THIS_CAR_ROW][1] == THIS_CAR_KEY, f"row {THIS_CAR_ROW} is not {THIS_CAR_KEY}"
    print(f"    ✅ CRC 50/50 · mode columns re-derived (row {THIS_CAR_ROW} {THIS_CAR_KEY!r} = "
          f"{rows[THIS_CAR_ROW][2]}, live {LIVE_MODE}, manual {MANUAL_MODE})")
    print(f"    ✅ ALL {len(EDITS)} TARGET VALUES ARE BYTE-IDENTICAL TO `stock_fw_dump/code.bin` at "
          "the same address -- V83a is a PURE REVERT.")
    print(f"    ✅ all {len(EDITS)} base preconditions, the edit GEOMETRY (dereferenced, X at "
          "base+2), the keep-list, the six")
    print(f"       pointer arrays over {N_MODES} modes, mode {MANUAL_MODE} byte-STOCK, all 34 "
          "friction records byte-STOCK,")
    print("       gain_A rec2/rec3 byte-STOCK, the 68-byte cave and the probe census: verified on "
          "the INPUT.")
    print(f"    ✅ 0xC407E = {u16(v81, 0xC407E)} (Honda's), threshold 0xC4004 = f32 "
          f"{struct.unpack_from('<f', v81, 0xC4004)[0]} ⇒ DTC-0x1d interlock intact and FROZEN.")
    mag, ph = path2_response(RING_HZ)
    print(f"    ✅ EDIT 12's GATE 1: 0x{DAMP_WEIGHT_ADDR:05X} = tp+0x{DAMP_WEIGHT_TP_DISP:04X} has "
          f"{n_rd} reader (0x{DAMP_WEIGHT_READER:05X}, `ld.hu`) / 0 writers,")
    print(f"       raw-byte scan, both parities + disp23 ({n_odd} odd-parity halfword hit(s), "
          f"{n_rd} on an instruction boundary). Its sole")
    print("       reader FUN_00038148 writes only gp-0x374c and gp-0x6b70 -- never gp-0x6b26 / "
          "gp-0x6c2c / gp-0x6a5e")
    print("       ⇒ NO firmware data path to the faulting monitor. 🛑 THE 'do not touch 0xC63A0' "
          "DIRECTIVE IS RETIRED")
    print("       EXPLICITLY, ON THE OPERATOR'S DECISION, ON THIS EVIDENCE -- not quietly ignored.")
    print(f"    ✅ Path-2 IIR 0x{PATH2_IIR_ADDR:05X} = {u16(v81, PATH2_IIR_ADDR)} ⇒ alpha "
          f"{PATH2_IIR_VALUE / 1024:.4f}, -3 dB corner {path2_corner_hz():.2f} Hz, and at "
          f"{RING_HZ} Hz")
    print(f"       Path 2 arrives at |H| = {mag:.3f}, {ph:+.1f} deg ⇒ the paths do NOT sum in "
          "phase. Edit 12's effect is bounded")
    print("       at <= 1.32x, NOT the naive 1.5x. 🛑 It is NOT claimed to explain the ring.")

    # =================================================================================================
    # APPLY THE EDITS
    # =================================================================================================
    code = bytearray(v81)
    print("\n" + "-" * 102)
    print(f"  APPLYING THE {len(EDITS)} EDITS -- every one asserted BEFORE, AFTER, and against STOCK")
    print(f"      {'#':>2s} {'addr':<9s} {'cell':<22s} {'V81':>6s} {'V83a':>6s}  {'bytes':<16s} "
          "stock?")
    attributed = set()
    for i, (addr, pre, new, _rec, lbl) in enumerate(EDITS, 1):
        assert u16(code, addr) == pre, f"0x{addr:05X} moved between the gate and the write"
        old_raw = bytes(code[addr:addr + 2])
        struct.pack_into("<H", code, addr, new)
        new_raw = bytes(code[addr:addr + 2])
        assert u16(code, addr) == new and s16(code, addr) == new, \
            f"the write at 0x{addr:05X} did not take, or {new} does not round-trip as a signed int16"
        assert new_raw == bytes(stock[addr:addr + 2]), \
            f"🛑🛑 0x{addr:05X} is now {new_raw.hex()}, STOCK is {bytes(stock[addr:addr + 2]).hex()}"
        attributed |= {addr, addr + 1}
        print(f"      {i:2d} 0x{addr:05X}  {lbl:<22s} {pre:6d} {new:6d}  "
              f"{old_raw.hex()} -> {new_raw.hex()}    == STOCK")
    assert len(attributed) == 2 * len(EDITS) == 24, \
        f"{len(attributed)} attributed bytes, expected {2 * len(EDITS)} ({len(EDITS)} halfwords)"

    # ---- whole-record identity, the thing that makes this a REVERT and not a partial write ----------
    print("\n    WHOLE-RECORD IDENTITY (the `0xD2A7E` hybrid's failure mode, closed by construction):")
    for name, rec in EDITED_RECORDS.items():
        n = rec_len(code, rec)
        ok = bytes(code[rec:rec + n]) == bytes(stock[rec:rec + n])
        assert ok, f"🛑 {name} @0x{rec:05X} is not byte-STOCK after the revert"
        print(f"      {name:<8s} @0x{rec:05X}  {n:2d} B  {bytes(code[rec:rec + n]).hex()}  "
              "== STOCK, whole record")
    assert bytes(code[DAMP_WEIGHT_ADDR:DAMP_WEIGHT_ADDR + 2]) == \
        bytes(stock[DAMP_WEIGHT_ADDR:DAMP_WEIGHT_ADDR + 2]), "edit 12 is not byte-STOCK"
    print(f"      {'scalar':<8s} @0x{DAMP_WEIGHT_ADDR:05X}   2 B  "
          f"{bytes(code[DAMP_WEIGHT_ADDR:DAMP_WEIGHT_ADDR + 2]).hex()}                  "
          "== STOCK (a bare tp scalar, not a record member)")

    # =================================================================================================
    # RE-ASSERT EVERYTHING ON THE FINISHED IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  RE-ASSERTING ON THE FINISHED IMAGE")
    assert_edit_geometry(code, "V83a")
    assert_keep_list(code, "V83a")
    assert_pointer_arrays_stock(code, stock, "V83a")
    man = assert_manual_mode_frozen(code, v81, stock, "V83a")
    assert_friction_all_stock(code, stock, "V83a")
    assert_gain_a(code, v81, stock, "V83a", reverted=True)
    ex, ey, cy = assert_factor_surface(code, stock, "V83a", reverted=True)
    cave = assert_cave_identical(code, v81, "V83a")
    V75.assert_probe_censuses(bytes(code), cave_span, V75.CAVE_ACCESS_ON_OUTPUT)
    V74.assert_clamp_census(bytes(code))
    assert assert_lever_c_census(code, "V83a") == (n_rd, n_odd), \
        "🛑 the 0xC63A0 census moved across the edit -- a cal write cannot change a census"
    _r2, eng2, dis2 = V74.derive_mode_columns(bytes(code))
    assert (eng2, dis2) == (ENGAGED, DISENGAGED), "the mode columns moved"
    assert u16(code, DAMP_WEIGHT_ADDR) == DAMP_WEIGHT_NEW == u16(stock, DAMP_WEIGHT_ADDR), \
        "edit 12 did not take, or it is not Honda's value"
    print(f"    ✅ MANUAL mode {MANUAL_MODE} byte-STOCK on all six record types: "
          f"{', '.join(f'{k}@0x{v:05X}' for k, v in man.items())}")
    print(f"    ✅ gain_A all four records == HONDA ({GA.assert_gain_a.__name__} PASSES on V83a, and "
          "it FAILS on the base)")
    print(f"    ✅ FactorC m{LIVE_MODE} Y {cy} (V75's lever, unmoved) · FactorE m{LIVE_MODE} "
          f"X {ex} Y {ey} == STOCK")
    print(f"    ✅ CAVE: 68 B @0x{CAVE_BASE:05X} byte-identical to V81 AND to "
          "`build_v75_tva.build_cave()`; hook unchanged.")
    print(f"       {cave.hex()}")

    # =================================================================================================
    # THE DAMPER SURFACE, RE-DERIVED FROM THE BUILT IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  ★ THE DAMPER SURFACE, RE-DERIVED FROM THE BUILT IMAGE (not from the inputs)")
    kn_b, kd_b = damper_k(v81, LIVE_MODE)
    kn, kd = damper_k(code, LIVE_MODE)
    print(f"    ramp gain k = ((FactorC_Y0 * FactorE_Y1) >> 10) / (FactorE_X1 - FactorE_X0)")
    print(f"       the flown V81 : {kn_b:4d}/{kd_b:<4d} = {kn_b / kd_b:.4f}")
    print(f"       V83a          : {kn:4d}/{kd:<4d} = {kn / kd:.4f}   "
          f"⇒ {(kn_b / kd_b) / (kn / kd):.2f}x REDUCTION")
    assert kn / kd < kn_b / kd_b, "🛑 V83a's damper ramp gain is not BELOW the flown V81's"
    creep_rate = int(CREEP_DEG_S * RATE_COUNTS_PER_DEG_S)
    dc = damper_authority(code, LIVE_MODE, 0, creep_rate)
    db = damper_authority(v81, LIVE_MODE, 0, creep_rate)
    ds = damper_authority(stock, LIVE_MODE, 0, creep_rate)
    print(f"\n    engaged drag at {CREEP_DEG_S} deg/s creep (rate {creep_rate} counts, speed 0): "
          f"V83a {dc} · V81 {db} · stock {ds}")

    print(f"\n    DELIVERED |gp-0x6bd0| (FactorB/D FLAT {Q10} ⇒ the chain reduces to (C*E)>>10, "
          f"seed {Q10}).")
    print(f"    axes: speed {SPEED_COUNTS_PER_KMH} counts/km/h · rate {RATE_COUNTS_PER_DEG_S} counts "
          f"per deg/s · ceiling X={CEILING_X} Y={CEILING_Y}, fallback 0xC6158 = {CEILING_FLOOR}")
    t26, t24 = dose_table(code, LIVE_MODE), dose_table(code, MANUAL_MODE)
    b26 = dose_table(v81, LIVE_MODE)
    hdr = "  ".join(f"r={r:<5d}" for r in REPORT_RATES)
    print(f"      {'mode':<6s} {'km/h':>5s} {'counts':>7s} | {hdr}")
    for label, tbl in ((f"m{LIVE_MODE}", t26), (f"m{MANUAL_MODE}", t24), (f"m{LIVE_MODE}/V81", b26)):
        for kmh in REPORT_SPEEDS_KMH:
            sc = int(kmh * SPEED_COUNTS_PER_KMH)
            row = "  ".join(f"{tbl[(kmh, r)]:7d}" for r in REPORT_RATES)
            print(f"      {label:<6s} {kmh:5d} {sc:7d} | {row}")
    # every reported dose stays strictly under the ceiling FLOOR -- V80's relay hazard, closed
    worst = max(max(t26.values()), max(t24.values()))
    assert worst < CEILING_FLOOR, \
        f"🛑 the reported grid delivers {worst}, at or above the ceiling FLOOR {CEILING_FLOOR} -- a " \
        "hard-clipping element inside the loop is exactly what turned V80's damper into a RELAY"
    print(f"    ✅ worst reported dose {worst} < the ceiling FLOOR {CEILING_FLOOR} ⇒ no clipping "
          "anywhere on the reported grid.")
    for kmh in (60, 100):
        for r in REPORT_RATES:
            sc = int(kmh * SPEED_COUNTS_PER_KMH)
            a, b = damper_authority(code, LIVE_MODE, sc, r), damper_authority(code, MANUAL_MODE, sc, r)
            assert a == b, f"🛑 at {kmh} km/h rate {r}: m{LIVE_MODE} {a} != m{MANUAL_MODE} {b}"
    print(f"    ✅ at 60 and 100 km/h the mode-{LIVE_MODE} dose EQUALS the mode-{MANUAL_MODE} dose "
          "EXACTLY, on every reported rate.")

    # ---- ⚠ THE CORRECTION: where the engaged/manual asymmetry ACTUALLY ends ------------------------
    bnd = asymmetry_boundary(code, REPORT_RATES + (0, 4500))
    lo, hi = bnd
    print(f"\n    ⚠ THE ONLY REMAINING ENGAGED/MANUAL ASYMMETRY is FactorC m{LIVE_MODE} Y[0] = "
          f"{cy[0]} vs mode-{MANUAL_MODE}'s {u16(stock, FACTOR_C_M26_REC + REC4_Y_OFF)}.")
    print(f"      SEARCHED over speed counts 0..14000: m{LIVE_MODE} differs from m{MANUAL_MODE} on "
          f"[{lo}, {hi}] counts = [{lo / SPEED_COUNTS_PER_KMH:.2f}, "
          f"{hi / SPEED_COUNTS_PER_KMH:.2f}] km/h.")
    print(f"      🛑 The brief's expectation 'above 35 km/h V83a deletes the asymmetry entirely' is "
          "OFF BY ONE LERP SEGMENT.")
    print(f"      FactorC X[0] = 2240 counts = 34.97 km/h is where Y[0] STOPS BEING THE CLAMP; it "
          "keeps WEIGHTING the")
    print(f"      LERP until X[1] = 3840 counts = 59.94 km/h. The 60/93/100 km/h equalities the "
          "brief predicts all hold.")
    assert hi < int(60 * SPEED_COUNTS_PER_KMH), \
        "the asymmetry persists past 60 km/h -- the reported equality would be inconsistent"

    # ---- the r26 gain_A surface, the other half of the magnitude story ------------------------------
    print(f"\n    r26 `gain_A` surface (build_v71b.gain_a_q10, mirroring FUN_0003ad74), V83a / V81:")
    print(f"      {'km/h':>5s} {'counts':>7s} | {'V81':>6s} {'V83a':>6s} {'ratio':>6s}")
    for kmh in (0, 5, 20, 50, 100):
        sc = int(kmh * SPEED_COUNTS_PER_KMH)
        a, b = GA.gain_a_q10(v81, sc, 0), GA.gain_a_q10(code, sc, 0)
        print(f"      {kmh:5d} {sc:7d} | {a:6d} {b:6d} {b / a:6.3f}")
    print("      🛑 THIS IS THE RISE, STATED PLAINLY: edits 4-11 RAISE r26 at the low-speed end. "
          "Every value is Honda's own.")

    # ---- ★ THE DOSE LADDER AND THE PRE-REGISTRATION -------------------------------------------------
    print(f"\n    ★ THE RING'S OPERATING POINT: 100 km/h, R = {RING_AMPL_COUNTS} counts (the "
          "MEASURED ring amplitude).")
    print("      🛑 THE RATIONALE FOR EDITS 1-3 IS **DOSE**, NOT **RELAY-NESS**. Relay-ness does "
          "NOT order the ring --")
    print("      V81 is the LEAST relay-like of the three flown builds and rings the HARDEST.")
    sc100 = int(100 * SPEED_COUNTS_PER_KMH)
    ladder = {"V83a": damper_authority(code, LIVE_MODE, sc100, RING_AMPL_COUNTS),
              "V81": damper_authority(v81, LIVE_MODE, sc100, RING_AMPL_COUNTS)}
    for nm, fn in DOSE_LADDER_IMAGES.items():
        p = plain_image_path(fn)
        assert os.path.exists(p), f"the FLOWN {nm} image {fn} is missing -- the ladder is unverifiable"
        img = Path(p).read_bytes()
        assert len(img) == 0x100000, f"the {nm} image is not 1 MiB"
        ladder[nm] = damper_authority(img, LIVE_MODE, sc100, RING_AMPL_COUNTS)
    for nm, want in DOSE_LADDER_EXPECT.items():
        assert ladder[nm] == want, \
            f"🛑 the {nm} dose re-measures as {ladder[nm]}, the pre-registration says {want} -- the " \
            "ladder the prediction rests on does not reproduce. STOP."
    ref = ladder["V76"]
    observed = {"V76": 1.00, "V81": 2.68, "V80": 3.46, "V83a": None}
    print(f"      {'build':<6s} {'dose':>5s} {'vs V76':>7s}   observed ring")
    for nm in ("V76", "V81", "V80", "V83a"):
        obs = f"{observed[nm]:.2f}" if observed[nm] is not None else "-- PREDICTED BELOW V76 --"
        star = "  <-- V83a" if nm == "V83a" else ""
        print(f"      {nm:<6s} {ladder[nm]:5d} {ladder[nm] / ref:6.2f}x   {obs}{star}")
    assert ladder["V76"] < ladder["V81"] < ladder["V80"], \
        "the flown dose ladder is not monotone -- the pre-registration's premise fails"
    assert ladder["V83a"] < ladder["V76"], \
        "🛑 V83a's dose is not BELOW V76's -- the prediction below would not be an extrapolation"
    print(f"      ⚠ the authorising brief quoted V83a at '96 counts = 0.36x V76'. The dose "
          f"{ladder['V83a']} is exact; the")
    print(f"        RATIO is {ladder['V83a'] / ref:.2f}x ({ladder['V83a']}/{ref}), not 0.36x. All "
          "three FLOWN doses reproduce exactly.")
    print("      ★ PRE-REGISTERED, FALSIFIABLE: **if V83a's 26-31 Hz ring is not below V76's, the "
          "dose model is WRONG")
    print("        and the damper is not what drives the ring.** Recorded BEFORE the drive, on "
          "purpose.")

    # ---- the Path-2 weight, and what it can and cannot buy ------------------------------------------
    mag, ph = path2_response(RING_HZ)
    print(f"\n    EDIT 12 -- Path-2 damper weight 0x{DAMP_WEIGHT_ADDR:05X} "
          f"{DAMP_WEIGHT_BASE} -> {DAMP_WEIGHT_NEW} (== STOCK, == the FLOWN V76, == V80)")
    print(f"      naive weight ratio {DAMP_WEIGHT_NEW / DAMP_WEIGHT_BASE:.3f}x, but Path 2 is "
          f"one-pole-filtered at 0x{PATH2_IIR_ADDR:05X} = {PATH2_IIR_VALUE}")
    print(f"      (alpha {PATH2_IIR_VALUE / 1024:.4f}, -3 dB corner {path2_corner_hz():.2f} Hz) ⇒ at "
          f"{RING_HZ} Hz it arrives |H| = {mag:.3f} at {ph:+.1f} deg,")
    print("      so the paths do NOT sum in phase and the cell's maximum effect is <= 1.32x, not "
          "1.5x. Applying that")
    print("      correction still leaves V81 at 1.81 against an observed ring ratio of 2.68 ⇒ "
          "🛑 EDIT 12 IS FOR")
    print("      COMPARABILITY WITH THE CORPUS (stock / the FLOWN V76 / V80 all read 1024), NOT "
          "EFFICACY.")

    # =================================================================================================
    # CRC
    # =================================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = [0xC6FFC, 0xD7FFC]
    assert [b[1] for b in blocks] == expect_trailers, \
        f"expected trailers {[hex(t) for t in expect_trailers]}, got {[hex(b[1]) for b in blocks]}"
    print("\n" + "-" * 102)
    print(f"  CRC -- EXACTLY {len(blocks)} block(s) move (ASSERTED against "
          f"{[hex(t) for t in expect_trailers]}, not observed):")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full 50-block chain re-walked: 50/50 PASS (0 mismatches)")
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block, V40 ignition precedent"
    assert not [a for a in attributed if a < START or a >= END], \
        f"an edit landed outside the flashable region [0x{START:X},0x{END:X})"
    print(f"    ✅ none of the {len(attributed)} edited bytes lands in [0xC5000,0xC5FFC) (the "
          "CRC-skipped block, V40 ignition precedent),")
    print(f"       and all of them lie inside the flashable region [0x{START:X},0x{END:X}).")

    # =================================================================================================
    # 🛑 THE FULL BYTE DIFF vs THE FLOWN V81
    # =================================================================================================
    by_addr = {a: (pre, new, lbl) for a, pre, new, _r, lbl in EDITS}

    def attribute(d):
        for a in (d, d - 1):
            if a in by_addr:
                pre, new, lbl = by_addr[a]
                return f"0x{a:05X} {lbl}  {pre} -> {new}  (== STOCK)"
        if d in crc_only:
            return "CRC trailer"
        return None

    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V83a vs THE FLOWN V81 -- over the WHOLE 1 MiB image")
    runs = diff_runs(code, v81, attribute)
    total = sum(b - a + 1 for a, b in runs)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    print(f"      {'range':<21s} {'len':>4s}  {'V81':<10s}    {'V83a':<10s}  attribution")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {bytes(v81[a:b + 1]).hex():<10s} -> "
              f"{bytes(code[a:b + 1]).hex():<10s}  {attribute(a)}")
    assert not stray, \
        f"🛑 UNATTRIBUTED bytes vs the flown V81: {[hex(x) for x in stray[:16]]} -- STOP AND REPORT"
    functional = total - len(crc_only & {d for a, b in runs for d in range(a, b + 1)})
    fn_runs = [r for r in runs if attribute(r[0]) != "CRC trailer"]
    # 🛑 THE WRITE COUNT AND THE DIFF COUNT ARE NOT THE SAME NUMBER, and conflating them is a real
    # trap: V83a WRITES 24 bytes (12 halfwords) but only DIFFERS in 16, because eight of the twelve
    # targets share their high byte with the base (`0002` -> `000c` and `0008` -> `0004` each move ONE
    # byte, not two). 🛑 COUNT CELLS, NOT BYTES -- the right number for a lever set is 12. All three
    # are asserted here, derived independently, so none can silently absorb an error in the others.
    expect_diff = sum(sum(1 for k in range(2) if v81[a + k] != struct.pack("<H", new)[k])
                      for a, _p, new, _r, _l in EDITS)
    assert expect_diff == 16, f"the per-edit differing-byte count re-derives as {expect_diff}, not 16"
    assert functional == expect_diff, \
        f"{functional} functional bytes differ, the per-edit derivation says {expect_diff}"
    assert len(attributed) == 24, f"{len(attributed)} bytes written, expected 24 (12 halfwords)"
    assert len(fn_runs) == len(EDITS) == 12, \
        f"{len(fn_runs)} functional runs, expected {len(EDITS)}"
    assert len(runs) == len(EDITS) + len(blocks), \
        f"{len(runs)} runs, expected {len(EDITS)} functional + {len(blocks)} CRC"
    print(f"    ⇒ {len(fn_runs)} FUNCTIONAL run(s) = {len(EDITS)} CELLS, covering {functional} "
          f"differing byte(s), + {total - functional} CRC byte(s) in {len(blocks)} run(s).")
    print(f"      🛑 COUNT CELLS, NOT BYTES. V83a writes {len(attributed)} bytes ({len(EDITS)} "
          f"halfwords) but only {functional} DIFFER --")
    print("      eight targets share their high byte with V81 (`0002` -> `000c`, and `0008` -> "
          "`0004`, each move ONE byte).")
    print("      All three counts are asserted independently.")

    # ---- THE VALUE-ANCHORED VERIFIERS: whole-image identity modulo the attributed set --------------
    assert_identity_modulo(code, v81, attributed | crc_only, "V83a", "the flown V81")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = v81[a]
    rt_sha = hashlib.sha256(bytes(rt)).hexdigest()
    assert rt_sha == SRC_SHA256, f"the round trip yields {rt_sha}, expected {SRC_SHA256}"
    print(f"    ✅ VALUE-ANCHORED ROUND TRIP: restoring the {len(attributed)} attributed + "
          f"{len(crc_only)} CRC bytes reproduces")
    print(f"       the V81 base BIT-FOR-BIT -- sha256 back to {rt_sha[:16]}… over all 0x100000 "
          "bytes. A TOTAL statement.")

    # ---- chained to the flown V75, so the whole post-V75 delta is attributed in one statement ------
    v81_attr = ({V81.CLAMP_ADDR, V81.CLAMP_ADDR + 1}
                | {y + k for y in V81.FRICTION_X15_Y_EXPECT for k in range(6)})
    v81_crc = {t + k for t in (0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC, 0xD4FFC, 0xD6FFC,
                               0xD7FFC, 0xD8FFC, 0xD9FFC) for k in range(4)}
    assert_identity_modulo(code, v75, attributed | crc_only | v81_attr | v81_crc, "V83a",
                           "the flown V75")
    print(f"    ✅ CHAINED: restoring V83a's {len(attributed)} bytes AND V81's own "
          f"{len(v81_attr)} attributed bytes (0xC407E +")
    print("       14 friction Y rows) plus both builds' CRC trailers reproduces the FLOWN V75 "
          "byte-for-byte ⇒ the")
    print("       entire V75 -> V83a delta is attributed, with nothing unexplained anywhere in the "
          "image.")
    d_stock = sum(1 for i in range(0x100000) if code[i] != stock[i])
    d_stock_v81 = sum(1 for i in range(0x100000) if v81[i] != stock[i])
    print(f"    ⊕ vs STOCK: V83a differs at {d_stock} bytes, the flown V81 at {d_stock_v81} "
          f"⇒ V83a is {d_stock_v81 - d_stock} bytes CLOSER to Honda.")
    assert d_stock < d_stock_v81, "🛑 V83a is not closer to stock than its base -- it is a REVERT"

    # =================================================================================================
    # THE .rwd -- ENCODED AND READ BACK IN MEMORY EVEN ON A DRY RUN
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  .rwd ENCODE + READBACK (in memory even on a dry run)")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V83a output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v81)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, never from the in-memory build.
    assert_edit_geometry(dec, "V83a readback")
    assert_keep_list(dec, "V83a readback")
    assert_pointer_arrays_stock(dec, stock, "V83a readback")
    assert_manual_mode_frozen(dec, v81, stock, "V83a readback")
    assert_friction_all_stock(dec, stock, "V83a readback")
    assert_gain_a(dec, v81, stock, "V83a readback", reverted=True)
    assert_factor_surface(dec, stock, "V83a readback", reverted=True)
    assert_cave_identical(dec, v81, "V83a readback")
    V75.assert_probe_censuses(bytes(dec), cave_span, V75.CAVE_ACCESS_ON_OUTPUT)
    V74.assert_clamp_census(bytes(dec))
    assert assert_lever_c_census(dec, "V83a readback") == (n_rd, n_odd), "the readback census differs"
    assert u16(dec, DAMP_WEIGHT_ADDR) == DAMP_WEIGHT_NEW, "the readback's 0xC63A0 is not 1024"
    assert V74.derive_mode_columns(bytes(dec))[1:] == (ENGAGED, DISENGAGED)
    assert damper_k(dec, LIVE_MODE) == (kn, kd), "the readback's damper k differs"
    assert dose_table(dec, LIVE_MODE) == t26 and dose_table(dec, MANUAL_MODE) == t24, \
        "the readback's dose table differs"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert_identity_modulo(dec, v81, attributed | crc_only, "V83a readback", "the flown V81")
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    print(f"    ✅ READBACK: the edit geometry, all {len(EDITS)} values (each == STOCK), the "
          "keep-list, the six")
    print(f"       pointer arrays, MANUAL mode {MANUAL_MODE} byte-STOCK, all 34 friction records, "
          "gain_A all four")
    print("       records, the FactorC/FactorE surface, k, the whole dose table, the 68-byte cave "
          "and its")
    print("       re-disassembly, identity to the flown V81 outside the attributed set, and the "
          "full 50/50 CRC")
    print("       chain: ALL re-verified FROM THE DECODED .rwd PAYLOAD.")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # =================================================================================================
    # WRITE -- only if explicitly enabled
    # =================================================================================================
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WAS WRITTEN TO DISK.")
        print("     Re-run with ACCORD_V83A_WRITE=rwd to cut the artefacts.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(
                f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists (on disk "
                f"{hashlib.sha256(existing).hexdigest()}, about to write {img_sha}). A same-number "
                "re-cut destroyed a predecessor's snapshot once already and produced an artefact NO "
                "gate could check. Rename or delete it deliberately, then re-run.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(
                    f"🛑 a DIFFERENT {OUT} already exists -- exactly ONE flashable .rwd per build "
                    "number. Rename or delete it deliberately, then re-run.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            # ---- 🛑 A SEPARATE FROM-DISK DECODE OF THE SHIPPED FILE -------------------------------
            shipped = Path(OUT).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha, "the shipped .rwd re-hashes wrong"
            FF.assert_x31_checksum(shipped, "V83a shipped")
            sb = parse_x31(shipped)
            assert sb["headers"] == FF.EXPECTED_HEADERS
            assert sb["blocks"] == [{"start": START, "length": END - START}]
            sd = bytearray(v81)
            sd[START:END] = bytes(sb["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert_gain_a(sd, v81, stock, "V83a shipped-from-disk", reverted=True)
            assert_factor_surface(sd, stock, "V83a shipped-from-disk", reverted=True)
            assert_keep_list(sd, "V83a shipped-from-disk")
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code), \
                "the written plain image does not re-read as the built image"
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded, and its payload")
            print("     re-verified (gain_A, the surface, the keep-list, 50/50 CRC) INDEPENDENTLY "
                  "of the in-memory build.")

    print(f"\n  V83a [{VARIANT_TOKEN}] -- image SHA256 {img_sha}")
    print(f"                                    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  ★ {len(EDITS)} CELLS ({len(attributed)} bytes written, {functional} differing), ALL "
          f"reverts to Honda. k {kn_b / kd_b:.4f} -> {kn / kd:.4f};")
    print(f"    gain_A rec0/rec1 512 -> STOCK; 0x{DAMP_WEIGHT_ADDR:05X} {DAMP_WEIGHT_BASE} -> "
          f"{DAMP_WEIGHT_NEW}. Ring dose {ladder['V83a']} = "
          f"{ladder['V83a'] / ref:.2f}x the FLOWN V76.")
    print("  🛑 THE COST: whatever ratchet suppression the dose was buying is given up, and 6.0x of "
          "creep r26 gain")
    print("     the car has not had since V71c comes back. Both are FEEL changes as well as lever "
          "changes.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without touching an image."""
    assert len(EDITS) == 12 and len({a for a, *_ in EDITS}) == 12
    assert sum(1 for _a, _p, _n, r, _l in EDITS if r == "FactorE") == 3
    assert sum(1 for _a, _p, _n, r, _l in EDITS if r.startswith("gainA")) == 8
    assert sum(1 for _a, _p, _n, r, _l in EDITS if r == "scalar") == 1
    assert all(0 < n < 0x8000 for _a, _p, n, _r, _l in EDITS), "a target is not a positive int16"
    # ---- EDIT 12's arithmetic, so the header's numbers are DERIVED and not quoted ------------------
    assert (DAMP_WEIGHT_BASE, DAMP_WEIGHT_NEW) == (2048, 1024)
    assert struct.pack("<H", 2048) == bytes.fromhex("0008")
    assert struct.pack("<H", 1024) == bytes.fromhex("0004")
    assert struct.pack("<H", 2048)[0] == struct.pack("<H", 1024)[0], \
        "🛑 2048 -> 1024 must move exactly ONE byte -- COUNT CELLS, NOT BYTES"
    assert DAMP_WEIGHT_ADDR - TP == 0x73A0, "the off-by-0x1000 trap: tp = 0xBF000"
    mag, ph = path2_response(RING_HZ)
    assert abs(mag - 0.516) < 5e-4 and abs(ph + 54.1) < 0.05, \
        f"the Path-2 response at {RING_HZ} Hz re-derives as |H|={mag:.4f}, {ph:+.2f} deg -- the " \
        "header quotes 0.516 / -54.1 deg"
    assert abs(path2_corner_hz() - 16.71) < 0.01, "the -3 dB corner re-derives away from 16.71 Hz"
    assert GAIN_A_NEW_Y[GAIN_A_REC0] == [3072, 3072, 2434, 2048]
    assert GAIN_A_NEW_Y[GAIN_A_REC1] == [3072, 3072, 2488, 1536]
    assert ((566 * 140) >> 10) / (400 - 60) == 77 / 340        # V83a's k
    assert ((566 * 539) >> 10) / (200 - 12) == 297 / 188       # the flown V81's k
    assert "+" not in VARIANT_TOKEN and all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN)
    assert int(CREEP_DEG_S * RATE_COUNTS_PER_DEG_S) == 94


if __name__ == "__main__":
    _self_check()
    build()
