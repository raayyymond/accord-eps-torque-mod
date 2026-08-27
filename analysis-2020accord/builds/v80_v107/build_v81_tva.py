#!/usr/bin/env python3
"""builds/v80_v107/build_v81_tva.py -- V81 = THE FLOWN V75, with Honda's friction clamp restored. CAL-ONLY.

🛑 STATUS: BUILT, UNFLASHED. Variant **A (FRICTION=STOCK)** was named by the operator on 2026-08-07
and is the ONE flashable .rwd cut under this build number. Variant B remains implemented behind
`ACCORD_V81_FRICTION=V75` for reproduction only -- 🛑 do not cut it; the kit's rule is exactly one
flashable .rwd per build number on disk. Writing is gated on `ACCORD_V81_WRITE`; the default is a
DRY RUN that verifies everything (including a full in-memory .rwd encode/decode) and writes nothing.

★★★★ THE ONE-LINE REASON THIS BUILD EXISTS
-------------------------------------------
V75 is the best-rated build this kit has produced -- route `5e`, no grind #1, no grind #2, the
micro-ratchet barely perceptible -- and it HARD-FAULTED (latched total loss of assist, DTC 0x1d).
The fault is not in the damper V75 was tuning. It is a one-cell interlock that V73 removed without
knowing it was one. **V81 puts that cell back and changes nothing else.** No cave, no code, no
damper surface: ONE u16 (plus, if the operator selects it, a REVERT of the friction Y rows to
Honda's own values). Every other byte of the flown V75 is asserted IDENTICAL -- over the WHOLE
1 MiB image, not over a span.

EDIT 1 -- MANDATORY, AND THE WHOLE POINT.  `0xC407E`  850 -> 511   (u16 LE `5203` -> `ff01`)
--------------------------------------------------------------------------------------------
Re-verified for this build by decompiling both functions and by a FOUR-METHOD raw byte census
(disp16 + 6-byte disp23 + LE32 address literal + movhi/movea pair), on BOTH the stock image and
the V75 base. Every count below is a MEASUREMENT, not a recollection. [EVIDENCE]

  THE MONITOR.  `FUN_00036d74`, called UNCONDITIONALLY exactly once, from `FUN_0002214a` @0x2290A
  -- the kit's established 1 kHz control task (`get_xrefs_to` returns that single
  UNCONDITIONAL_CALL and nothing else):

      fVar3 = (float)(int)*(short *)(gp - 0x6b26) * 0.0009765625;   // = /1024, Q10
      fVar2 = *(float *)(tp + 0x5004) * -1.0;
      if ((*(float *)(tp + 0x5004) < fVar3) || (fVar3 < fVar2))
          FUN_000462e6(0x39bc, fVar3, 0, +CEIL, -CEIL);             // -> DTC 0x1d, HARD FAULT

  `tp+0x5004` = `0xC4004` (⚠ tp = 0xBF000; 0xBF000 + 0x5004 = 0xC4004, NOT 0xC5004). Raw bytes
  `0000003f` = f32 **0.5** ⇒ the trip point is 0.5 * 1024 = **512 raw counts**, symmetric, with no
  debounce, no re-sample and no timing escape. The threshold cell has 3 readers (all `ld.w`, all
  inside FUN_00036d74) and **ZERO writers**.

  THE FAULT PATH.  `FUN_000462e6` calls `FUN_00016de6(0x1d, param_1, 1, 1)` -- read directly off
  the decompile for this build, not relayed. DTC **0x1d**.

  THE SOLE WRITER.  `gp-0x6b26` (= 0xFEDF14DA) census, all four methods, stock AND V75:
      disp16 5 hits · disp23 0 · LE32 literals 0 · movhi/movea pairs 0
      => **1 WRITER**: `st.h r6,-0x6b26[gp]` @**0x36CF0**, inside `FUN_00036c12`.
         4 readers: 0x36CE4 (the lockstep compare, in the writer itself), **0x36D78 (the monitor)**,
         0x3815C (the Path-2 aggregator FUN_00038148), 0x3AC98.
      Its lockstep shadow `gp-0x4cd0` has the matching 1 writer / 1 reader pair at 0x36CF4 / 0x36CE8.
  Every hit lands on an even (instruction-boundary) offset, and the scan is a raw Python LE byte
  scan -- `search_instructions` silently undercounts and still reports `truncated:false`.

  WHAT THAT WRITER STORES.  `FUN_00036c12`, decompiled:
      sVar7 = LERP(gp-0x6a5e voted speed, friction record via 0xCBE74[mode])   // Y all NEGATIVE
      iVar4 = (((gp-0x6c2c * gate) * sVar7) >> 6) * 0x111                      // 273
      iVar5 = iVar4 >> 0x12                                                    // 18
      clamp SYMMETRICALLY to +/- *(short *)(tp + 0x507e)                       // = 0xC407E
      if (gp-0x6b26 == gp-0x4cd0) { gp-0x6b26 = iVar5; gp-0x4cd0 = iVar5; } else escalate
  `0xC407E` census: **3 readers, ALL `ld.h` (SIGNED), ALL inside FUN_00036c12** (0x36C34, 0x36CD0,
  0x36CDC), **ZERO writers**, zero disp23 hits. All three are the same clamp -- the top-of-function
  read and the two clamp arms. ⇒ **the cell's entire blast radius is this one lane's magnitude.**

  THE INTERLOCK, AND ITS REMOVAL.  Read off the images:
      stock / V38 / V72 : 0xC407E = **511**  vs trip 512  ⇒ margin **+1**  ⇒ UNTRIPPABLE
      V73 / V74 / V75   : 0xC407E = **850**  vs trip 512  ⇒ margin **-338** ⇒ TRIPPABLE
  Honda set the clamp to exactly ONE count below the monitor's own trip point. A clamped signal
  cannot trip its own fault check. V73 raised it and removed the interlock; V74 then multiplied the
  friction Y row by 1.5, which cut the `gp-0x6c2c` magnitude needed to cross 512 by a third. V74
  faulted (manual, over a bump) and V75 faulted (engaged, stoplight launch).
  ⇒ At 511 the monitor is **untrippable BY CONSTRUCTION**: the only value that ever reaches
  `gp-0x6b26` is already clamped to +/-511 < 512, whatever the plant, the mode or the lever set.

  🛑 The 0xC407E edit LOOSENS NOTHING. It lowers a clamp, so the lane's authority can only shrink,
  and the monitor's own threshold `0xC4004` is asserted BYTE-UNCHANGED.

EDIT 2 -- THE FRICTION VARIANT.  ✅ THE OPERATOR NAMED **A (FRICTION=STOCK)**, 2026-08-07.
--------------------------------------------------------------------------------------------
V74 multiplied the 3-point friction Y row by exactly 1.5 on **14** records (not 13 -- see below),
and V75 carried it. Both variants remain implemented and byte-attributed; A is what shipped:

  FRICTION=STOCK  (variant A) ✅ SELECTED -- revert all 14 Y rows to Honda's [-9830,-5734,-1966].
  FRICTION=V75    (variant B) -- keep x1.5, ZERO friction bytes move. NOT CUT.

  THE OPERATOR'S FOUR REASONS, recorded here because they are the build's justification:
   1. A MEASURED ZERO BACKS IT. V76 flew route 65 with stock friction AND 0xC407E = 511. Its cave
      probes `|gp-0x6b26| > 448` and that bit fired **0 / 63,477 frames**, while its positive
      control (bit3, `gp-0x67fa == 5`) ran 99.926% and bit4 ran 70.0% ⇒ the cave was LIVE and the
      lane genuinely never approached the clamp with Honda's friction row.
      🛑 Cite `V76-V38BASE-...-probe-6b26-63fd` (extracted by `studies/sessions/v76/v76flight_extract.py` ->
      `_scratch/data/_cache_r65_records.pkl`), NOT `rlog-tools/probe/decode_v76_probe.py`, which documents the
      SUPERSEDED V74-base V76 whose bit7 is `gp-0x6bd0 != 0`.
   2. THE x1.5 CONTRIBUTED NOTHING TO THE GRINDING FIX. V74 already carried it and still measured
      grind #1 at 2.72x and the ratchet at 3.27x. The V74 -> V75 delta that eliminated the grinding
      was FactorC Y[0] (dose 50 -> 137), NOT the friction table.
   3. IT IS IMPLICATED IN A COMPLAINT, NOT A BENEFIT. The V75 handoff attributes the operator's
      CREEP HEAVINESS to x1.5 friction plus 0xC407E 511 -> 850 -- and 0xC407E is a bare `tp` scalar
      with no mode index, so it raised the drag ceiling in **MANUAL** too. V81 removes both.
   4. DEFENCE IN DEPTH. It takes out the SECOND leg of the recorded fault mechanism instead of
      resting the whole build on one cell.

★ THE EMPIRICAL GATE-2 ANCHOR -- V75's damper NEVER entered its saturated regime; V80's lives there
----------------------------------------------------------------------------------------------------
    |gp-0x6bd0| >= 448 counts, engaged        V75 (route 5e, 28,317 pre-fault frames):  0.000%
                                                  -- and never above 128 counts at all above 40 km/h
                                             V80 (route 66): 19.4% overall · 32.7% above 15 m/s
                                                  · 71% through the worst 29 s event
  And in the last 5 s before V75's fault the damper was identically ZERO for 4.98 s, reaching only
  level 2 (128-288) 19 ms before the trip, while column-rate jerk hit 7,154 deg/s^2 = 4.3x that
  route's own p99.9. ⇒ **THE DAMPER DID NOT CAUSE V75's FAULT** -- exactly what the 0xC407E
  mechanism predicts, and the reason V81 carries V75's damper surface byte-for-byte.

  ⚠ FOURTEEN RECORDS, NOT THIRTEEN, AND ONE OF THEM IS A **DISENGAGED** MODE. Derived here from
  the pointer array over all 34 modes, never hand-listed: the x1.5 set is the 13 ENGAGED modes
  {2,3,5,11,14,15,17,23,26,27,29,32,33} **plus mode 10, which is in the DISENGAGED column**. Mode
  10's record `0xD2A44` was raised by **V73** (verified across the image lineage: stock/V70/V71c/V72
  carry Honda's row; V73/V74/V75 carry x1.5), so V74's own engaged-only derivation never saw it.
  Variant A therefore edits a DISENGAGED-column record -- a deliberate, declared deviation from
  V74's "disengaged stays frozen" rule, and it is a deviation in the SAFE direction: it is a REVERT
  TO STOCK, so that column can only become MORE stock. Asserted as exactly that, by value.
  🛑 Mode 24 -- THIS car's manual mode -- is byte-STOCK on the base and on both variants.

EVERYTHING ELSE IS THE FLOWN V75, ASSERTED RATHER THAN REWRITTEN
----------------------------------------------------------------
  · FactorC m26 `0xD77DA..E0` = [566, 234, 429, 908] · FactorE m26 X `0xD780E..` = [12, 200, 2500,
    4000], Y = [0, 539, 539, 927]  ⇒ k = 297/188 = 1.5798, dose(r=99) 137 at creep -> 56 at 60 km/h
  · `0xC63A0` = **2048** (V72's LEVER C) -- KEPT. See the note below; the "it caused the faults"
    premise is refuted on evidence in this file.
  · `0x2A1F0` disp = `0x7CD0` (V57's decouple; reads 0xC6CD0 = 3564, shared 0xC646C stays 891)
  · `0xC62EA` = 0 (low-speed lockout removed) · `0x454FE` = 0xB5 (V42's macro-ratchet fix)
  · The 68-byte cave @0xC4B34 and the hook @0x55C0E: **byte-identical to V75**, re-derived from
    `build_v75_tva.build_cave()` and re-disassembled out of the built image. V81 spends ZERO cave
    risk. Code caves are this kit's ONLY bricking class (V24, V27, V48B).
  · The V75 probe therefore reads the same on V81 as on route `5e`, which makes the two builds
    directly comparable frame for frame.

🛑🛑 `0xC63A0` STAYS AT 2048 -- AND HERE IS THE EVIDENCE, NOT AN ASSURANCE
--------------------------------------------------------------------------
A prior operator directive said "do not double 0xC63A0, that caused the hard faults" (it is baked
into `build_v80_tva.assert_c63a0_block`). On this lineage that premise is **refuted**:
  · `0xC63A0` = tp+0x73A0. Census: **exactly ONE reader**, `ld.hu -0x73a0[tp],r9` @**0x381AC**,
    ZERO writers, zero disp23 hits -- on stock AND on V75.
  · Its only reader is `FUN_00038148`, the Path-2 aggregator. Decompiled: 0xC63A0 is the weight on
    the **`gp-0x6bd0` (damper)** term of a six-term sum. `FUN_00038148` writes exactly TWO cells --
    `gp-0x374c` (its own accumulator) and `gp-0x6b70` (its output). **It never writes `gp-0x6b26`,
    `gp-0x6c2c` or `gp-0x6a5e`.**
  · `gp-0x6b26` has exactly ONE writer image-wide (0x36CF0), and `gp-0x6c2c` -- the friction lane's
    multiplier -- has exactly TWO, both inside `FUN_00041464` (0x4184E, 0x41AC2).
  ⇒ **There is no firmware data path from 0xC63A0 to the faulting monitor.** [EVIDENCE]
  ⊕ The honest caveat: a PHYSICAL path exists (aggregator -> motor -> plant -> motor rate ->
    gp-0x6c2c). It does not matter here, because Edit 1 makes the monitor untrippable for ANY value
    of gp-0x6c2c -- the clamp is applied before the store. That is why the interlock is the fix and
    the weight is not the culprit.

🛑 GATE 1 -- RAM OWNERSHIP.  **PASS, and it is VACUOUS BY CONSTRUCTION.** [EVIDENCE]
-------------------------------------------------------------------------------------
V81 is CAL-ONLY. It allocates no RAM, writes no code, adds no instruction, and moves no cave byte.
The 68-byte cave at 0xC4B34 and the hook at 0x55C0E are asserted byte-identical to the flown V75
AND equal to `build_v75_tva.build_cave()`'s from-scratch re-derivation (which re-runs every encoder
pin against the STOCK image and the exhaustive 65,536-point wire model), then re-disassembled out
of the built image by V75's own self-contained Python decoder. **Zero new RAM ⇒ nothing to own.**
The gate is nonetheless MEASURED rather than argued, on the input, the output and the .rwd readback:
  · `gp-0x6b26` (the monitored cell)  : 1 writer / 4 readers, all four scan methods agree, and the
    single writer is 0x36CF0 -- the clamp site itself. NO address literal, NO movhi/movea pair
    ⇒ no register-indirect writer can hide from the displacement scans.
  · `gp-0x4cd0` (its lockstep shadow) : the matching 1w/1r pair at 0x36CF4 / 0x36CE8, untouched.
  · `0xC407E`  (the edited cal)       : 0 writers / 3 SIGNED `ld.h` readers, ALL inside the one
    function FUN_00036c12 ⇒ the edit's entire blast radius is that lane's clamp magnitude.
  · `0xC4004`  (the monitor threshold): 0 writers, byte-FROZEN. V81 loosens nothing.
  · `gp-0x6c2c` (the lane's input)    : 2 writers, both inside FUN_00041464, unmoved.
  · The friction records are pure DATA reached only through the pointer array 0xCBE74, which is
    asserted byte-STOCK for all 34 modes; V81 writes 6 bytes inside 14 of them and never the
    count word, the X axis or the 2 slack bytes (record length is 4 + 4*count, re-read per record --
    a flat 0x18 window spills into the NEXT mode's record, and that bug is on the kit's record).
  · The V75 probe's own GATE 1 (`assert_probe_censuses`) is re-run unchanged on input, output and
    readback: the cave READS gp-0x6bd0 and gp-0x6ac2 and writes NEITHER, and touches none of the
    three lockstep shadows.

🛑 GATE 2 -- CLOSED-LOOP STABILITY (MAGNITUDE **AND** PHASE).  **PASS, EMPIRICALLY.**
--------------------------------------------------------------------------------------
The honest framing first: **V81 does not change any loop.** Its damper surface, its rate lanes, its
gate, both `sar` sites, `0xC63A0` and every filter coefficient are byte-identical to the build that
flew route 5e. The only dynamic element V81 touches is a SATURATION BOUND, and it moves it DOWN.

  MAGNITUDE.  The ramp-regime incremental gain k = ((C_Y0 * E_Y1) >> 10) / (E_X1 - E_X0) = 297/188
  = **1.5798**, re-derived from the bytes and asserted equal to the flown V75's. k is a
  frequency-INDEPENDENT scalar on the whole damper path, so V81's loop gain equals V75's at EVERY
  frequency, by construction -- no plant model is needed to compare them. [EVIDENCE]
  The friction revert LOWERS an open-loop feed-forward magnitude (the lane's Y row is a speed-
  indexed coefficient, not a feedback term) and the clamp revert LOWERS a bound. Neither can raise
  gain anywhere.

  PHASE.  V81 introduces no filter, no delay, no new state and no new sample point. Every pole,
  zero and task-order relationship in the image is bit-identical to V75's. **The phase response of
  every loop the signals are in is therefore literally unchanged**, which is the strongest form
  this gate can take. [EVIDENCE]

  THE ONE NONLINEARITY THAT MOVES, stated plainly. Lowering the clamp 850 -> 511 makes the friction
  lane's saturation reachable ~10% earlier (creep: |gp-0x6c2c| >= 3189 vs 3539). A saturating
  element inside a loop is exactly the kit's RULE-12(b) hazard -- a clamped lane whose sign flips
  degenerates into a Coulomb relay. Three things bound it, and only the third is decisive:
   (a) The lane is FEED-FORWARD friction compensation indexed on voted vehicle speed with a
       motor-rate multiplier; V81 restores Honda's OWN operating point in it exactly -- same Y row,
       same 511 clamp -- so its saturation behaviour is stock's, which has 8 years of fleet history.
   (b) At 511 the lane still sits far inside the aggregator's +/-1024 ZERO-REJECT window, so a
       saturated lane still CONTRIBUTES its clamped value rather than falling off a cliff to zero.
   (c) ★ MEASURED: on V76 -- Honda's friction row with 0xC407E = 511, i.e. exactly V81's
       configuration in this lane -- the `|gp-0x6b26| > 448` probe bit fired **0 / 63,477 frames**
       over route 65, with a 99.926% positive control proving the cave was live. **The lane does
       not reach 448, let alone 511.** The relay hazard is therefore not merely bounded, it is
       measured to be unexercised. [EVIDENCE]

  ⊕ THE STRONGEST ARGUMENT AVAILABLE, and it is empirical rather than analytic: **V75's damper
  surface FLEW and eliminated the grinding** (route 5e, operator-rated best-ever: no grind #1, no
  grind #2, micro-ratchet barely perceptible), and it flew with `|gp-0x6bd0| >= 448` at **0.000%**
  of engaged frames -- i.e. it never entered its saturated regime at all. V81 carries that surface
  byte-for-byte. This kit has never made a stronger GATE 2 case by analysis.

  ⚠ WHAT IS **NOT** CLOSED, stated as BELIEF rather than EVIDENCE:
   · "0xC407E = 850 CAUSED both hard faults" is a strong BELIEF, not proof. What is EVIDENCE is
     that the mechanism exists, is single-frame, is mode-proof, and that the build history lines up
     exactly (V38-V72 could not fault; V73 could but needed a large event; V74/V75 needed a third
     less and both faulted). V81 closes the mechanism whether or not it fired.
   · `gp-0x6c2c`'s physical scale (deg/s per raw count) is still underived, so "3189 counts is a
     rare excursion" rests on V76's measured zero, not on a unit conversion.
   · V81 removes drag the operator may have grown used to; creep effort will differ from V75's.
     That is intended (reason 3 above) but it is a FEEL change, not just a safety change.

Usage:
    python builds/v80_v107/build_v81_tva.py                          # DRY RUN, variant A, writes nothing
    ACCORD_V81_WRITE=rwd python builds/v80_v107/build_v81_tva.py     # ✅ reproduces THE FLASHABLE ARTEFACT
    ACCORD_V81_FRICTION=V75 python builds/v80_v107/build_v81_tva.py  # DRY RUN of variant B. 🛑 never with WRITE.
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

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, START/END, encoders)
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the raw byte scan)
import build_v68_tva as V68                # noqa: E402  (cave geometry)
import build_v72_tva as V72                # noqa: E402  (CAVE_EXTENT)
import build_v74_tva as V74                # noqa: E402  (record readers, mirrors, keep-list)
import build_v75_tva as V75                # noqa: E402  ★ THE BASE -- its cave, probe and surface
import build_v76_v38base_tva as V76B       # noqa: E402  (the interlock constants, stated once)
import v72_lane_model as LM                # noqa: E402  (lerp_int)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
CAVE_BASE = V68.CAVE_BASE                          # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT                      # 68 -- the PROVEN extent. Never grow it.
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
TP = LM.TP                                         # 0xBF000
GP_ABS = 0xFEDF8000

# =====================================================================================================
# THE BASE -- the FLOWN V75, and ONLY that cut
# =====================================================================================================
# 🛑 THIS IS THE CUT THAT FLEW (route 5e) AND THAT THE OPERATOR RATED BEST-EVER. It is NOT the
# `_v75_CY0.566_magprobe` sibling, which was never flown. The SHA is the discriminator; the cave is
# byte-identical across every V75 lever set, so neither the payload nor a span check can tell them
# apart. Asserted before a single byte is touched.
SRC_BIN = plain_image_path("_v75_CY0.566-EX1.200_magprobe_plain_image.bin")
SRC_SHA256 = "e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c"
NOT_THE_BASE = {  # sha256 -> why it must never be accepted
    "9a96b7fe0cb5263f9cbc528cb0a0a67744048f439373f326f5a7c966ff37f3d1":
        "_v75_CY0.566_magprobe -- the EX1-off sibling. It NEVER FLEW; every V81 claim rests on 5e.",
    "8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959":
        "_v74_engagedcols_x0_12_addonly -- V75's own base, one lever short.",
}
V74_BIN = plain_image_path("_v74_engagedcols_x0_12_addonly_plain_image.bin")
V74_SHA256 = "8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959"
STOCK_BIN = stock_fw_path("code.bin")

# =====================================================================================================
# EDIT 1 -- THE INTERLOCK. Constants imported from V76B so there is ONE statement of them in the kit.
# =====================================================================================================
CLAMP_ADDR = V76B.FAULT_CLAMP_ADDR              # 0xC407E
CLAMP_TP_DISP = 0x507E                          # asserted: CLAMP_ADDR - TP
CLAMP_BASE_VALUE = 850                          # what the flown V75 carries
CLAMP_NEW_VALUE = V76B.FAULT_CLAMP_MAX          # 511 -- Honda's own, one count under the trip
CLAMP_READERS = V74.CLAMP_READERS               # [0x36C34, 0x36CD0, 0x36CDC], all in FUN_00036c12
CLAMP_NEIGHBOUR = V74.CLAMP_NEIGHBOUR           # (0xC407C, 461) -- owner UNIDENTIFIED, untouched
THRESH_ADDR = V76B.FAULT_THRESH_ADDR            # 0xC4004
THRESH_BYTES = V76B.FAULT_THRESH_BYTES          # 0000003f
THRESH_VALUE = V76B.FAULT_THRESH_VALUE          # 0.5
FAULT_SCALE = V76B.FAULT_SCALE                  # 1024
TRIP_COUNTS = V76B.FAULT_TRIP_COUNTS            # 512
MONITOR_FN = 0x36D74                            # FUN_00036d74
MONITOR_CALLER = (0x2214A, 0x2290A)             # FUN_0002214a, the 1 kHz task; UNCONDITIONAL_CALL
WRITER_FN = 0x36C12                             # FUN_00036c12
CELL_DISP = V76B.FAULT_CELL_DISP                # 0x6B26
CELL_SHADOW_DISP = 0x4CD0                       # gp-0x4cd0, its lockstep twin (escalates on drift)
CELL_WRITER = 0x36CF0                           # the ONE `st.h r6,-0x6b26[gp]` image-wide
CELL_READERS = [0x36CE4, 0x36D78, 0x3815C, 0x3AC98]
CELL_SHADOW_WRITER, CELL_SHADOW_READER = 0x36CF4, 0x36CE8
DRIVE_DISP = 0x6C2C                             # gp-0x6c2c, the lane's multiplier (motor-rate deriv)
DRIVE_WRITERS = [0x4184E, 0x41AC2]              # both inside FUN_00041464
SPEED_DISP = 0x6A5E                             # gp-0x6a5e, the friction LERP index (voted speed)
AGG_ZERO_REJECT = V74.AGGREGATOR_ZERO_REJECT    # 1024 -- the aggregator's +/-0x400 window
FRICTION_MUL, FRICTION_SHIFT_A, FRICTION_SHIFT_B = 0x111, 6, 0x12   # FUN_00036c12's own constants

# =====================================================================================================
# EDIT 2 -- THE FRICTION VARIANT.  🛑 THE OPERATOR NAMES IT; this file refuses to guess.
# =====================================================================================================
FRICTION_PTR_ARRAY = V74.FRICTION_PTR_ARRAY     # 0xCBE74
FRICTION_NPT, FRICTION_Y_OFF = V74.FRICTION_NPT, V74.FRICTION_Y_OFF      # 3, 0x08
FRICTION_X = V74.FRICTION_X                     # [0, 1280, 5760] counts = [0, 20, 90] km/h
FRICTION_Y_STOCK = V74.FRICTION_Y_STOCK         # [-9830, -5734, -1966]
FRICTION_Y_V75 = V74.FRICTION_Y_NEW             # [-14745, -8601, -2949]  (= x3/2, exact)
SPEED_COUNTS_PER_KMH = V74.SPEED_COUNTS_PER_KMH  # 64
# ⊕ Stated independently and asserted after DEREFERENCING all 34 modes -- never used to find them.
FRICTION_X15_Y_EXPECT = [0xCF6E0, 0xCF6F0, 0xD0A5C, 0xD2A4C, 0xD2A5C, 0xD3A5C, 0xD3A6C,
                         0xD4A5C, 0xD6A5C, 0xD7A5C, 0xD7A6C, 0xD8A5C, 0xD9A5C, 0xD9A6C]
FRICTION_X15_MODES_EXPECT = [2, 3, 5, 10, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33]
# 🛑 mode 10 is in the DISENGAGED column and V73 -- not V74 -- put it here. Declared, see the header.
FRICTION_X15_DISENGAGED = [10]

FRICTION_VARIANTS = ("STOCK", "V75")
FRICTION = os.environ.get("ACCORD_V81_FRICTION", "STOCK").strip().upper()
assert FRICTION in FRICTION_VARIANTS, \
    f"ACCORD_V81_FRICTION={FRICTION!r} -- expected one of {FRICTION_VARIANTS}"
FRICTION_TARGET = FRICTION_Y_STOCK if FRICTION == "STOCK" else FRICTION_Y_V75

# =====================================================================================================
# WHAT MUST NOT MOVE -- stated by VALUE, as literals, so a drift in any imported module FAILS here
# =====================================================================================================
KEEP_CELLS = {
    0xC63A0: (2048, "V72 LEVER C, the Path-2 aggregator weight on gp-0x6bd0. KEPT -- see the header: "
                    "its sole reader FUN_00038148 never writes gp-0x6b26 / gp-0x6c2c / gp-0x6a5e."),
    0xC62EA: (0,    "the low-speed steer lockout, removed since V52."),
    0xC6CD0: (3564, "V57's decoupled forward-reader cell."),
    0xC646C: (891,  "the SHARED sensor scale -- V57 decoupled the forward reader OFF it. STOCK."),
    0xC407C: (461,  "the clamp's NEIGHBOUR. Owner UNIDENTIFIED. Untouched."),
    0xC643E: (1536, "gain_A arm, stock."),
    0xC6444: (512,  "gain_A arm, stock -- raising it is UNTESTED and is not this build's business."),
    0xC6446: (512,  "gain_B arm, stock."),
    0xC6158: (512,  "the ceiling's tp+0x7158 FALLBACK -- both branches must still yield 512."),
}
KEEP_BYTES = {
    0x454FE: (0xB5, "V42's macro-ratchet fix (`br` not `bne`). Restored on the V75 lineage; KEEP."),
    0x3AA96: (0xC5, "V72's gate byte."),
}
KEEP_HALFWORDS = {
    0x2A1F0: (0x7CD0, "V57's decoupling displacement -> tp+0x7CD0 = 0xC6CD0."),
}
SAR_SITES = V75.SAR_SITES                       # both at STOCK -- the grind #2 fix is an ABSENCE
V72_GAIN_A = V75.V72_GAIN_A
GAIN_B_M10_KEEP = V75.GAIN_B_M10_KEEP

# ---- the LIVE mode's damper surface, stated independently and asserted after dereferencing ---------
FACTOR_B_PTRS, FACTOR_C_PTRS = V75.FACTOR_B_PTRS, V75.FACTOR_C_PTRS
FACTOR_D_PTRS, FACTOR_E_PTRS = V75.FACTOR_D_PTRS, V75.FACTOR_E_PTRS
CEILING_PTRS = V75.CEILING_PTRS
ALL_PTR_ARRAYS = {"FactorB": FACTOR_B_PTRS, "FactorC": FACTOR_C_PTRS, "FactorD": FACTOR_D_PTRS,
                  "FactorE": FACTOR_E_PTRS, "ceiling": CEILING_PTRS, "friction": FRICTION_PTR_ARRAY}
N_MODES = 34
LIVE_MODE, MANUAL_MODE = V75.LIVE_MODE, 24
THIS_CAR_ROW, THIS_CAR_KEY = V75.THIS_CAR_ROW, V75.THIS_CAR_KEY
ENGAGED_EXPECTED, DISENGAGED_EXPECTED = V75.ENGAGED_EXPECTED, V75.DISENGAGED_EXPECTED
REC4_X_OFF, REC4_Y_OFF = V75.REC4_X_OFF, V75.REC4_Y_OFF
Q10 = V75.Q10
BURST_RATE, BURST_RATE_69HZ = V75.BURST_RATE, V75.BURST_RATE_69HZ

LIVE_SURFACE_EXPECT = {
    "factor_c": 0xD77D0, "factor_c_xy": ([2240, 3840, 5120, 8960], [566, 234, 429, 908]),
    "factor_e": 0xD780C, "factor_e_xy": ([12, 200, 2500, 4000], [0, 539, 539, 927]),
    "friction": 0xD7A54,
    "dose_at_99": 137, "dose_at_127": 181, "dose_60kmh_at_99": 56,
    "k_num": 297, "k_den": 188,      # k = ((566*539)>>10) / (200-12) = 1.5798, the V75 loop gain
}
MANUAL_EXPECT = {"B": 0xD6760, "C": 0xD67E4, "D": 0xD67A4, "E": 0xD6820,
                 "ceiling": 0xD60B4, "friction": 0xD6A64}
CEILING_FLOOR = V75.CEILING_FLOOR                # 512

# =====================================================================================================
# OUTPUT NAMING -- 🛑 THE VARIANT IS IN BOTH FILENAMES
# =====================================================================================================
# A recorded hazard: two V70 cuts both wrote `_v70_plain_image.bin`, so the second OVERWROTE the
# first's snapshot while the first's `.rwd` stayed flashable -- an artefact NO gate could check. The
# cave is byte-identical across V81's two variants, so the PAYLOAD cannot tell them apart either.
# 🛑 THE SEPARATOR IS `.`/`-`, NEVER `+`: the Ghidra MCP layer once URL-decoded a `+` to a SPACE.
WRITE_MODE = os.environ.get("ACCORD_V81_WRITE", "").strip().lower()
assert WRITE_MODE in ("", "none", "bin", "rwd"), \
    f"ACCORD_V81_WRITE={WRITE_MODE!r} -- expected '' (dry run), 'bin' or 'rwd'"


def variant_token():
    tok = f"C407E.511-FRICTION.{FRICTION}"
    assert all(c.isalnum() or c in ".-" for c in tok), "the variant token carries a mangling risk"
    return tok


def tag():
    return f"V75BASE-{variant_token()}-magprobe-6bd0-thermo-6ac2"


def bin_out():
    return str(plain_image_path(f"_v81_{variant_token()}_plain_image.bin"))


def out_rwd():
    return os.path.join(RWD_DIR, f"39990-TVA,A160-V81-{tag()}-0x{START:X}-0x{END:X}.rwd")


# =====================================================================================================
# Readers -- all imported from V74 so the record layout has ONE implementation in the kit
# =====================================================================================================
u16, s16, u32 = V75.u16, V75.s16, V75.u32
rec_any, rec_len = V74.rec_any, V74.rec_len
rec3_x, rec3_y, rec4_y = V74.rec3_x, V74.rec3_y, V74.rec4_y
factor_rec = V74.factor_rec
ceiling_floor = V74.ceiling_floor
damper_authority = V74.damper_authority


# =====================================================================================================
# THE FRICTION LANE, mirrored instruction for instruction from FUN_00036c12
# =====================================================================================================

def friction_raw(y, drive):
    """The PRE-clamp lane output. Mirrors `((drive * y) >> 6) * 0x111 >> 0x12` EXACTLY.

    🛑 Integer `>>` on a negative value is an ARITHMETIC shift in both Python and V850 (`sar`), so
    the mirror is exact including the floor behaviour. `drive` is `(short)(gp-0x6c2c * gate)`; the
    gate is 0 or 1 so it drops out of the magnitude arithmetic.
    """
    return (((drive * y) >> FRICTION_SHIFT_A) * FRICTION_MUL) >> FRICTION_SHIFT_B


def friction_out(buf, rec, speed_counts, drive):
    """The POST-clamp lane output = what is stored into gp-0x6b26. V74's mirror, re-stated."""
    y = LM.lerp_int(speed_counts, rec3_x(buf, rec), rec3_y(buf, rec))
    v = friction_raw(y, drive)
    lim = s16(buf, CLAMP_ADDR)
    return max(-lim, min(lim, v))


def drive_to_saturate(y, lim):
    """The smallest |gp-0x6c2c| whose PRE-clamp output reaches |lim|. Searched, not solved.

    ⊕ Reported for BOTH variants so the operator can compare duty cycles directly. A bisection on a
    monotone-in-|drive| function; the monotonicity is asserted by the caller over the swept range.
    """
    lo, hi = 0, 1 << 16
    while lo < hi:
        mid = (lo + hi) // 2
        if abs(friction_raw(y, mid)) >= lim:
            hi = mid
        else:
            lo = mid + 1
    return lo


# =====================================================================================================
# CENSUSES -- raw LE byte scans, BOTH gp-relative encodings, every hit on an instruction boundary
# =====================================================================================================
_OPS = {0x38: ("ld.b", False), 0x39: ("ld.h/ld.w", False), 0x3A: ("st.b", True),
        0x3B: ("st.h/st.w", True), 0x3C: ("ld.bu", False), 0x3D: ("ld.bu", False),
        0x3F: ("ld.hu", False)}


def _disp16_of(op, hw1, hw2):
    if op in (0x38, 0x3A):
        return hw2
    if op in (0x39, 0x3B):
        return hw2 & 0xFFFE if (hw2 & 1) else hw2
    if op in (0x3C, 0x3D):
        return (hw2 & 0xFFFE) | ((hw1 >> 5) & 1)     # 🛑 ld.bu carries disp bit0 in the OPCODE field
    if op == 0x3F:
        return hw2 & 0xFFFE
    return None


def scan_disp16(buf, want16, base_reg):
    """The 4-byte form. Even offsets only ⇒ every hit is on an instruction boundary."""
    out = []
    for a in range(0, len(buf) - 4, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        if (hw1 & 0x1F) != base_reg:
            continue
        op = (hw1 >> 5) & 0x3F
        if op not in _OPS:
            continue
        reg2 = hw1 >> 11
        mnem, is_store = _OPS[op]
        # reg2 == 0 is the ESCAPE to the 6-byte form for LOADS only; for STORES it is `st r0` (= 0).
        if reg2 == 0 and not is_store:
            continue
        hw2 = struct.unpack_from("<H", buf, a + 2)[0]
        if op == 0x39:
            mnem = "ld.w" if (hw2 & 1) else "ld.h"
        if op == 0x3B:
            mnem = "st.w" if (hw2 & 1) else "st.h"
        if _disp16_of(op, hw1, hw2) == want16:
            out.append((a, mnem, reg2, is_store, "disp16"))
    return out


def scan_disp23(buf, want_signed, base_reg):
    """🛑 THE 6-BYTE EXTENDED-DISPLACEMENT FORM a disp16-only scan is BLIND TO.

    hw2 carries disp[6:0] in bits 10:4, hw3 carries disp[22:7]; reg2 == 0 selects the form.
    """
    out = []
    for a in range(0, len(buf) - 6, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        if (hw1 & 0x1F) != base_reg or (hw1 >> 11) != 0:
            continue
        op = (hw1 >> 5) & 0x3F
        if op not in _OPS:
            continue
        hw2, hw3 = struct.unpack_from("<HH", buf, a + 2)
        disp = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
        if disp & 0x400000:
            disp -= 0x800000
        if disp != want_signed:
            continue
        mnem, is_store = _OPS[op]
        out.append((a, f"{mnem}(ext,sub{hw2 & 0xF})", hw2 >> 11, is_store, "disp23"))
    return out


def scan_abs_literal(buf, abs_addr):
    """LE32 literal of the absolute address -- catches `mov imm32,reg` + register-indirect."""
    pat, out, i = struct.pack("<I", abs_addr), [], 0
    i = buf.find(pat)
    while i >= 0:
        out.append(i)
        i = buf.find(pat, i + 1)
    return out


def scan_movhi_movea(buf, abs_addr):
    """movhi hi16 / movea lo16 immediate pair that would materialise abs_addr."""
    lo, hi = abs_addr & 0xFFFF, (abs_addr >> 16) & 0xFFFF
    if lo & 0x8000:                       # movea sign-extends, so movhi must pre-compensate
        hi = (hi + 1) & 0xFFFF
    out = []
    for a in range(0, len(buf) - 4, 2):
        if struct.unpack_from("<H", buf, a + 2)[0] != hi:
            continue
        if ((struct.unpack_from("<H", buf, a)[0] >> 5) & 0x3F) != 0x32:
            continue
        for b in range(a + 4, min(a + 28, len(buf) - 4), 2):
            hw = struct.unpack_from("<H", buf, b)[0]
            if ((hw >> 5) & 0x3F) == 0x31 and struct.unpack_from("<H", buf, b + 2)[0] == lo:
                out.append((a, b))
                break
    return out


def census_gp4(buf, disp_neg):
    """All FOUR methods for a gp-relative cell. Returns (writers, readers, extras)."""
    h = sorted(scan_disp16(buf, (0x10000 - disp_neg) & 0xFFFF, 4)
               + scan_disp23(buf, -disp_neg, 4))
    abs_addr = GP_ABS - disp_neg
    extras = (scan_abs_literal(buf, abs_addr), scan_movhi_movea(buf, abs_addr))
    return [x for x in h if x[3]], [x for x in h if not x[3]], extras


def census_tp2(buf, addr):
    """disp16 + disp23 for a tp-relative CAL. (writers, readers)."""
    d = addr - TP
    h = sorted(scan_disp16(buf, d & 0xFFFF, 5) + scan_disp23(buf, d, 5))
    return [x for x in h if x[3]], [x for x in h if not x[3]]


def assert_interlock_censuses(buf, label):
    """🛑🛑 GATE 1 FOR EDIT 1 -- the whole safety argument, MEASURED from raw bytes on this image.

    Everything here is asserted EXACTLY (never as a bound), on both the input and the output, so a
    change that silently added a writer to the monitored cell would fail the build rather than fly.
    """
    out = {}
    # ---- the monitored cell: EXACTLY ONE writer image-wide -----------------------------------------
    w, r, (lit, mhi) = census_gp4(buf, CELL_DISP)
    assert [a for a, _m, _rg, _s, _f in w] == [CELL_WRITER], \
        f"🛑🛑 {label}: gp-0x{CELL_DISP:04x} writers are " \
        f"{[hex(a) for a, *_ in w]}, expected exactly [0x{CELL_WRITER:05X}]. The ENTIRE V81 " \
        "argument is 'the only value that reaches this cell is already clamped'. STOP."
    assert [a for a, _m, _rg, _s, _f in r] == CELL_READERS, \
        f"{label}: gp-0x{CELL_DISP:04x} readers moved: {[hex(a) for a, *_ in r]}"
    assert all(m in ("ld.h", "st.h") for _a, m, _rg, _s, _f in w + r), \
        f"{label}: gp-0x{CELL_DISP:04x} has a non-halfword access -- the cell is not an int16"
    assert not lit and not mhi, \
        f"🛑 {label}: gp-0x{CELL_DISP:04x} is reachable by an ADDRESS LITERAL " \
        f"({[hex(x) for x in lit]}) or a movhi/movea pair ({mhi}) -- a register-indirect writer " \
        "would be invisible to the displacement scans and the single-writer claim would be VOID"
    assert MONITOR_FN in [a for a, *_ in r] or any(
        MONITOR_FN <= a < MONITOR_FN + 0x100 for a, *_ in r), \
        f"{label}: the monitor FUN_{MONITOR_FN:08x} does not appear among gp-0x{CELL_DISP:04x}'s readers"
    out["cell"] = (len(w), len(r))
    # ---- the lockstep shadow: the matching 1w/1r pair ----------------------------------------------
    sw, sr, _e = census_gp4(buf, CELL_SHADOW_DISP)
    assert [a for a, *_ in sw] == [CELL_SHADOW_WRITER] and [a for a, *_ in sr] == [CELL_SHADOW_READER], \
        f"{label}: the gp-0x{CELL_SHADOW_DISP:04x} lockstep pair moved -- a drift between the two " \
        "halves escalates through FUN_0006b9fa"
    # ---- the clamp cal: 3 SIGNED readers, ZERO writers, all inside the one writer function ---------
    cw, cr, = census_tp2(buf, CLAMP_ADDR)
    assert CLAMP_ADDR - TP == CLAMP_TP_DISP, \
        f"0x{CLAMP_ADDR:05X} is not tp+0x{CLAMP_TP_DISP:04X} -- ⚠ the recurrent off-by-0x1000 trap"
    assert not cw, f"🛑🛑 {label}: 0x{CLAMP_ADDR:05X} HAS WRITERS at {[hex(a) for a, *_ in cw]} -- " \
                   "a runtime-written clamp cannot be pinned by a cal edit"
    assert [a for a, *_ in cr] == CLAMP_READERS, \
        f"{label}: 0x{CLAMP_ADDR:05X} readers are {[hex(a) for a, *_ in cr]}, expected " \
        f"{[hex(a) for a in CLAMP_READERS]} -- all three inside FUN_{WRITER_FN:08x}"
    assert all(m == "ld.h" for _a, m, *_ in cr), \
        f"🛑 {label}: a 0x{CLAMP_ADDR:05X} read is not `ld.h` -- an `ld.hu` would read 511 unsigned " \
        "and the SIGN of the negative clamp arm would be lost"
    assert all(WRITER_FN <= a < MONITOR_FN for a, *_ in cr), \
        f"{label}: a clamp reader sits outside FUN_{WRITER_FN:08x}"
    out["clamp"] = (len(cw), len(cr))
    # ---- the monitor's own threshold: byte-frozen, ZERO writers ------------------------------------
    tw, tr = census_tp2(buf, THRESH_ADDR)
    raw = bytes(buf[THRESH_ADDR:THRESH_ADDR + 4])
    thresh = struct.unpack("<f", raw)[0]
    assert not tw, f"🛑🛑 {label}: the monitor threshold 0x{THRESH_ADDR:05X} has WRITERS"
    assert raw == THRESH_BYTES and thresh == THRESH_VALUE, \
        f"🛑🛑 {label}: 0x{THRESH_ADDR:05X} is {raw.hex()} ({thresh!r}), expected " \
        f"{THRESH_BYTES.hex()} ({THRESH_VALUE}). V81 must LOOSEN NOTHING -- this cell is FROZEN."
    assert int(thresh * FAULT_SCALE) == TRIP_COUNTS, "the trip-point arithmetic drifted"
    assert len(tr) == 3 and all(m == "ld.w" for _a, m, *_ in tr), \
        f"{label}: the threshold's readers are {[(hex(a), m) for a, m, *_ in tr]}"
    out["thresh"] = (len(tw), len(tr))
    # ---- the lane's multiplier: its writers must stay where the blast-radius argument put them -----
    dw, dr, _e = census_gp4(buf, DRIVE_DISP)
    assert [a for a, *_ in dw] == DRIVE_WRITERS, \
        f"{label}: gp-0x{DRIVE_DISP:04x} writers are {[hex(a) for a, *_ in dw]}, expected " \
        f"{[hex(a) for a in DRIVE_WRITERS]} (both inside FUN_00041464)"
    out["drive"] = (len(dw), len(dr))
    return out


def assert_interlock_margin(buf, label, want_clamp):
    """🛑🛑 THE SINGLE MOST IMPORTANT ASSERTION IN THIS FILE. Do not relax it."""
    clamp = s16(buf, CLAMP_ADDR)
    assert clamp == want_clamp, \
        f"{label}: 0x{CLAMP_ADDR:05X} is {clamp}, expected {want_clamp}"
    assert 0 < clamp <= V76B.FAULT_CLAMP_MAX, \
        f"🛑🛑 {label}: FRICTION CLAMP 0x{CLAMP_ADDR:05X} = {clamp} > {V76B.FAULT_CLAMP_MAX}. " \
        f"FUN_{MONITOR_FN:08x} faults to DTC 0x1d above {TRIP_COUNTS} counts. THIS IS THE V74/V75 " \
        "HARD-FAULT MECHANISM -- latched total loss of power steering. STOP."
    assert clamp < TRIP_COUNTS, \
        f"🛑🛑 {label}: the clamp {clamp} is not STRICTLY below the {TRIP_COUNTS}-count trip point"
    assert clamp < AGG_ZERO_REJECT, \
        f"🛑 {label}: the clamp {clamp} reaches the aggregator's +/-{AGG_ZERO_REJECT} ZERO-REJECT " \
        "window, so a saturated lane would contribute NOTHING instead of its clamped value"
    return clamp, TRIP_COUNTS - clamp


# =====================================================================================================
# THE FRICTION SET -- DERIVED over all 34 modes, then checked against the independent statement
# =====================================================================================================

def derive_friction(buf, base_img):
    """{y_addr: (rec, mode, old_Y, new_Y)} for every record the x1.5 lever touched.

    🛑 Nothing is hand-listed: the records are DEREFERENCED through 0xCBE74 for all 34 modes, the
    x1.5 set is found by COMPARING each record's Y row against Honda's, and only then is the result
    checked against `FRICTION_X15_Y_EXPECT`. A pointer-array misread cannot silently retarget.
    """
    seen, x15, stock_rows = {}, {}, 0
    for mode in range(N_MODES):
        rec = factor_rec(buf, FRICTION_PTR_ARRAY, mode)
        n, xs, ys = rec_any(buf, rec)
        assert (n, xs) == (FRICTION_NPT, FRICTION_X), \
            f"🛑 friction m{mode} @0x{rec:05X} is ({n}, {xs}), expected ({FRICTION_NPT}, " \
            f"{FRICTION_X}) -- STOP, do not guess the layout"
        assert ys in (FRICTION_Y_STOCK, FRICTION_Y_V75), \
            f"🛑 friction m{mode} @0x{rec:05X} Y = {ys} is NEITHER Honda's {FRICTION_Y_STOCK} NOR " \
            f"V74's x1.5 {FRICTION_Y_V75}. STOP: the base is not the build this file expects."
        assert rec not in seen, f"friction m{mode} @0x{rec:05X} is ALSO mode {seen[rec]}'s"
        seen[rec] = mode
        assert bytes(buf[rec:rec + rec_len(buf, rec)]) == \
            bytes(base_img[rec:rec + rec_len(buf, rec)]) or base_img is buf, \
            f"friction m{mode} moved relative to the reference image"
        if ys == FRICTION_Y_V75:
            x15[rec + FRICTION_Y_OFF] = (rec, mode, ys, FRICTION_TARGET)
        else:
            stock_rows += 1
    assert sorted(x15) == FRICTION_X15_Y_EXPECT, \
        f"the x1.5 Y-row set DERIVED from the pointer array is {[hex(a) for a in sorted(x15)]}, " \
        f"the independent statement says {[hex(a) for a in FRICTION_X15_Y_EXPECT]}"
    assert sorted(v[1] for v in x15.values()) == FRICTION_X15_MODES_EXPECT, \
        f"the x1.5 MODE set is {sorted(v[1] for v in x15.values())}, expected " \
        f"{FRICTION_X15_MODES_EXPECT}"
    assert stock_rows == N_MODES - len(x15) == 20, f"{stock_rows} stock friction rows, expected 20"
    # ⚠ the declared deviation, asserted as data rather than trusted as prose
    dis = sorted(m for _rec, m, _o, _n in x15.values() if m in DISENGAGED_EXPECTED)
    assert dis == FRICTION_X15_DISENGAGED, \
        f"the DISENGAGED modes carrying x1.5 are {dis}, the declaration says " \
        f"{FRICTION_X15_DISENGAGED} -- an undeclared disengaged record is in the edit set"
    assert MANUAL_MODE not in [v[1] for v in x15.values()], \
        f"🛑 mode {MANUAL_MODE} (THIS car's MANUAL mode) carries x1.5 friction -- it must be stock"
    # x1.5 must be EXACT in integers, or the "revert" is not a revert
    assert [(y * 3) // 2 for y in FRICTION_Y_STOCK] == FRICTION_Y_V75 and \
        all(y * 3 % 2 == 0 for y in FRICTION_Y_STOCK), "x1.5 is not exact on Honda's row"
    return x15


def assert_friction_uniform(buf, label, want):
    """Every one of the 34 friction records carries `want` or Honda's row -- and the moved set is
    exactly the declared one. Stated as a TOTAL over all modes, not as a spot check."""
    for mode in range(N_MODES):
        rec = factor_rec(buf, FRICTION_PTR_ARRAY, mode)
        n, xs, ys = rec_any(buf, rec)
        expect = want if (rec + FRICTION_Y_OFF) in FRICTION_X15_Y_EXPECT else FRICTION_Y_STOCK
        assert (n, xs, ys) == (FRICTION_NPT, FRICTION_X, expect), \
            f"🛑 {label}: friction m{mode} @0x{rec:05X} is ({n}, {xs}, {ys}), expected " \
            f"({FRICTION_NPT}, {FRICTION_X}, {expect})"
        assert all(a < b <= 0 for a, b in zip(ys, ys[1:])), \
            f"{label}: friction m{mode} Y {ys} is not monotone increasing toward zero -- Honda's " \
            "shape must be preserved"


# =====================================================================================================
# THE KEEP-LIST -- V81's own statement, by VALUE, on the image in front of it
# =====================================================================================================

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
    for addr, raw in SAR_SITES.items():
        assert bytes(buf[addr:addr + 2]) == raw, \
            f"🛑 {label}: the `sar` site 0x{addr:05X} is {bytes(buf[addr:addr + 2]).hex()}, expected " \
            f"the STOCK {raw.hex()} -- reintroducing V62's `a9` CAUSES GRIND #2; the fix is an ABSENCE"
    for base, want in V72_GAIN_A.items():
        assert rec4_y(buf, base) == want, f"{label}: gain_A 0x{base:05X} Y = {rec4_y(buf, base)}"
    for base, want in GAIN_B_M10_KEEP.items():
        assert rec4_y(buf, base) == want, f"{label}: gain_B m10 0x{base:05X} Y = {rec4_y(buf, base)}"


def assert_pointer_arrays_stock(buf, stock, label):
    """🛑 Every edited table is reachable ONLY through these. A moved pointer redirects the lever."""
    for name, arr in ALL_PTR_ARRAYS.items():
        for mode in range(N_MODES):
            got, want = u32(buf, arr + mode * 4), u32(stock, arr + mode * 4)
            assert got == want, \
                f"{label}: {name} array 0x{arr:05X}[{mode}] -> 0x{got:05X}, STOCK says 0x{want:05X}"


def assert_manual_mode_stock(buf, stock, label):
    """🛑 Mode 24 is THIS car's MANUAL steering. Byte-identical to STOCK across ALL SIX record
    types, every address RESOLVED THROUGH THE POINTER ARRAY and checked against an independently
    stated expectation -- never a guessed byte range. That record-length trap has bitten V73 and a
    V75 spot-check: a flat 0x18 window spills 4 bytes into the NEXT mode's record."""
    for name, arr in ALL_PTR_ARRAYS.items():
        key = {"FactorB": "B", "FactorC": "C", "FactorD": "D", "FactorE": "E"}.get(name, name)
        rec = factor_rec(buf, arr, MANUAL_MODE)
        assert rec == MANUAL_EXPECT[key], \
            f"{label}: {name} m{MANUAL_MODE} dereferences to 0x{rec:05X}, expected " \
            f"0x{MANUAL_EXPECT[key]:05X}"
        n = rec_len(buf, rec)               # 🛑 the record's OWN length: 4 + 4*count
        assert bytes(buf[rec:rec + n]) == bytes(stock[rec:rec + n]), \
            f"🛑 {label}: MANUAL mode {MANUAL_MODE} {name} @0x{rec:05X} ({n} B) differs from STOCK " \
            f"({bytes(stock[rec:rec + n]).hex()} -> {bytes(buf[rec:rec + n]).hex()})"
    return {k: MANUAL_EXPECT[k] for k in MANUAL_EXPECT}


def assert_live_surface(buf, label):
    """The V75 damper surface, asserted BY VALUE after dereferencing -- never rewritten."""
    for kind, ptrs, key in (("FactorC", FACTOR_C_PTRS, "factor_c"),
                            ("FactorE", FACTOR_E_PTRS, "factor_e")):
        rec = factor_rec(buf, ptrs, LIVE_MODE)
        assert rec == LIVE_SURFACE_EXPECT[key], \
            f"{label}: {kind} m{LIVE_MODE} -> 0x{rec:05X}, expected 0x{LIVE_SURFACE_EXPECT[key]:05X}"
        n, xs, ys = rec_any(buf, rec)
        assert (xs, ys) == LIVE_SURFACE_EXPECT[key + "_xy"], \
            f"🛑 {label}: {kind} m{LIVE_MODE} is ({xs}, {ys}), expected " \
            f"{LIVE_SURFACE_EXPECT[key + '_xy']} -- V81 must carry the FLOWN V75 surface EXACTLY"
        assert n == 4
    rec = factor_rec(buf, FRICTION_PTR_ARRAY, LIVE_MODE)
    assert rec == LIVE_SURFACE_EXPECT["friction"], f"{label}: friction m{LIVE_MODE} -> 0x{rec:05X}"
    # FactorB / FactorD FLAT 1024 on every engaged mode, read BY COUNT (FactorD is FIVE-point)
    for mode in ENGAGED_EXPECTED:
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD")):
            n, _xs, ys = rec_any(buf, factor_rec(buf, ptrs, mode))
            assert set(ys) == {Q10}, f"{label}: {name} m{mode} ({n}-point) is not FLAT {Q10}: {ys}"
        assert ceiling_floor(buf, mode) == CEILING_FLOOR, \
            f"{label}: mode {mode}'s ceiling floor moved"
    # the delivered dose, RECOMPUTED from the bytes through FUN_00034350's mirror
    d99 = damper_authority(buf, LIVE_MODE, 0, BURST_RATE)
    d127 = damper_authority(buf, LIVE_MODE, 0, BURST_RATE_69HZ)
    d60 = damper_authority(buf, LIVE_MODE, 60 * SPEED_COUNTS_PER_KMH, BURST_RATE)
    assert (d99, d127, d60) == (LIVE_SURFACE_EXPECT["dose_at_99"],
                                LIVE_SURFACE_EXPECT["dose_at_127"],
                                LIVE_SURFACE_EXPECT["dose_60kmh_at_99"]), \
        f"{label}: the live dose is ({d99}, {d127}, {d60}), the spec says " \
        f"({LIVE_SURFACE_EXPECT['dose_at_99']}, {LIVE_SURFACE_EXPECT['dose_at_127']}, " \
        f"{LIVE_SURFACE_EXPECT['dose_60kmh_at_99']}) -- the damper surface is NOT V75's"
    # the ramp-regime incremental gain k, the frequency-independent GATE 2 scalar
    _n, ex, ey = rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, LIVE_MODE))
    _n, _cx, cy = rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, LIVE_MODE))
    k_num, k_den = (cy[0] * ey[1]) >> 10, ex[1] - ex[0]
    assert (k_num, k_den) == (LIVE_SURFACE_EXPECT["k_num"], LIVE_SURFACE_EXPECT["k_den"]), \
        f"{label}: k = {k_num}/{k_den}, the flown V75's is " \
        f"{LIVE_SURFACE_EXPECT['k_num']}/{LIVE_SURFACE_EXPECT['k_den']}"
    return d99, d127, d60, k_num / k_den


def assert_cave_identical(buf, base_img, label):
    """🛑 THE CAVE AND THE HOOK ARE BYTE-IDENTICAL TO V75, three independent ways.

    Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU). V81 does not
    write the cave at all -- it RE-DERIVES V75's 68 bytes from `build_v75_tva.build_cave()`, which
    re-runs every encoder pin and the exhaustive wire model, and asserts the image already carries
    them; it re-disassembles them out of the image with V75's own self-contained Python decoder;
    and it asserts byte identity with the base.
    """
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    assert cave == bytes(base_img[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]), \
        f"🛑 {label}: the 68-byte cave @0x{CAVE_BASE:05X} differs from V75's"
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
    # the hook, and the displaced original the cave re-executes
    assert bytes(buf[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(base_img[HOOK_ADDR:HOOK_ADDR + 4]) == \
        FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: the hook @0x{HOOK_ADDR:05X} is not `jarl 0x{CAVE_BASE:05X}`"
    assert bytes(buf[HOOK_ADDR + 4:HOOK_ADDR + 6]) == V75.HOOK_RETURN_INSN, \
        f"{label}: 0x{HOOK_ADDR + 4:05X} is not `mov 0x8,r7` -- the proof that r7 is DEAD across " \
        "the hook is void"
    assert cave.count(HOOK_STOCK) == 1, f"{label}: the displaced movea is not present exactly once"
    return cave, redis


# =====================================================================================================
# THE VALUE-ANCHORED VERIFIER -- whole-image identity modulo an ATTRIBUTED set
# =====================================================================================================
# 🛑 `verify/diff_build_vs_stock.py` is SPAN-based and has missed things. This is the strongest statement
# available: restore every byte V81 is ALLOWED to have changed, then assert the result is
# byte-for-byte the flown V75 over the FULL 1 MiB -- not over [START, END), the WHOLE image.

def assert_identity_modulo(buf, base_img, allowed, label):
    probe = bytearray(buf)
    for a in allowed:
        probe[a] = base_img[a]
    diff = [i for i in range(len(base_img)) if probe[i] != base_img[i]]
    assert not diff, \
        f"🛑 {label}: after restoring the {len(allowed)} ATTRIBUTED bytes, the image still differs " \
        f"from the flown V75 at {len(diff)} byte(s): {[hex(x) for x in diff[:16]]}. V81 is defined " \
        "as V75 plus the attributed set and NOTHING else."
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


# =====================================================================================================
# THE BUILD
# =====================================================================================================

def build():
    print(__doc__)
    BIN_OUT, OUT = bin_out(), out_rwd()
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it. Shorten the " \
        "tag BEFORE building; nothing has been written yet."
    assert variant_token() in os.path.basename(BIN_OUT) and variant_token() in os.path.basename(OUT), \
        "🛑 the variant is not in BOTH filenames -- the two cuts would be indistinguishable, and " \
        "the cave is byte-identical across them so the payload cannot tell them apart either"

    v75 = bytes(Path(SRC_BIN).read_bytes())
    v74 = bytes(Path(V74_BIN).read_bytes())
    stock = bytes(Path(STOCK_BIN).read_bytes())
    print("=" * 102)
    print(f"SOURCE (the FLOWN V75): {SRC_BIN}")
    src_sha = hashlib.sha256(v75).hexdigest()
    print(f"  SHA256 {src_sha}")
    for name, img in (("V75", v75), ("V74", v74), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert src_sha not in NOT_THE_BASE, \
        f"🛑🛑 THE BASE IS {NOT_THE_BASE[src_sha]}"
    assert src_sha == SRC_SHA256, \
        f"🛑🛑 THE BASE IS NOT THE FLOWN V75. SHA256 is {src_sha}, expected {SRC_SHA256}. V81 is " \
        "defined as the route-5e cut plus these edits; any other base voids EVERY claim in this file."
    assert hashlib.sha256(v74).hexdigest() == V74_SHA256, "the V74 reference image drifted"
    print("  ✅ the base SHA256 is the route-5e cut EXACTLY -- not the EX1-off sibling.")
    print(f"  VARIANT: FRICTION={FRICTION}   token {variant_token()}")
    print(f"  WRITE MODE: {WRITE_MODE or 'DRY RUN -- nothing will be written to disk'}")

    # =================================================================================================
    # GATE THE SOURCE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  GATING THE SOURCE -- everything below is measured on the INPUT before a byte moves")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert walk_all_blocks(v75) == 0, "the V75 source's own CRC chain does not verify"
    src_cens = assert_interlock_censuses(v75, "V75 source")
    base_clamp = s16(v75, CLAMP_ADDR)
    assert base_clamp == CLAMP_BASE_VALUE, \
        f"the base's 0x{CLAMP_ADDR:05X} is {base_clamp}, expected V73's live {CLAMP_BASE_VALUE}"
    assert base_clamp > TRIP_COUNTS, \
        "the base's clamp is already below the trip point -- this is not the build V81 is fixing"
    assert_keep_list(v75, "V75 source")
    assert_pointer_arrays_stock(v75, stock, "V75 source")
    assert_manual_mode_stock(v75, stock, "V75 source")
    assert_live_surface(v75, "V75 source")
    assert_cave_identical(v75, v75, "V75 source")
    V75.assert_probe_censuses(v75, cave_span, V75.CAVE_ACCESS_ON_OUTPUT)
    V74.assert_clamp_census(v75)
    x15 = derive_friction(v75, v75)
    rows, ENGAGED, DISENGAGED = V74.derive_mode_columns(v75)
    assert tuple(ENGAGED) == ENGAGED_EXPECTED and tuple(DISENGAGED) == DISENGAGED_EXPECTED
    assert not (set(ENGAGED) & set(DISENGAGED)), "🛑 THE MODE COLUMNS ARE NOT DISJOINT"
    assert rows[THIS_CAR_ROW][1] == THIS_CAR_KEY, "row 11 is not TVCA4"
    print(f"    ✅ CRC 50/50 · the mode columns re-derived (row {THIS_CAR_ROW} {THIS_CAR_KEY!r} = "
          f"{rows[THIS_CAR_ROW][2]}, live {LIVE_MODE}, manual {MANUAL_MODE})")
    print(f"    ✅ the V75 keep-list, the six pointer arrays over {N_MODES} modes, mode "
          f"{MANUAL_MODE} byte-STOCK, the live surface, and the 68-byte cave: ALL verified on the input.")
    print(f"    ✅ interlock censuses on the INPUT: gp-0x{CELL_DISP:04x} "
          f"{src_cens['cell'][0]}w/{src_cens['cell'][1]}r · 0x{CLAMP_ADDR:05X} "
          f"{src_cens['clamp'][0]}w/{src_cens['clamp'][1]}r · 0x{THRESH_ADDR:05X} "
          f"{src_cens['thresh'][0]}w/{src_cens['thresh'][1]}r · gp-0x{DRIVE_DISP:04x} "
          f"{src_cens['drive'][0]}w/{src_cens['drive'][1]}r")

    # =================================================================================================
    # THE INTERLOCK, WRITTEN OUT IN FULL
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  🛑🛑 EDIT 1 -- THE DTC-0x1d INTERLOCK, re-verified for THIS build [EVIDENCE]")
    thresh = struct.unpack_from("<f", v75, THRESH_ADDR)[0]
    print(f"    MONITOR   FUN_{MONITOR_FN:08x}  <- UNCONDITIONAL_CALL from FUN_{MONITOR_CALLER[0]:08x} "
          f"@0x{MONITOR_CALLER[1]:05X} (the 1 kHz task), and from NOWHERE else")
    print(f"              faults via FUN_000462e6(0x39bc,..) -> FUN_00016de6(0x{0x1d:02X},..) = DTC 0x1d")
    print(f"    THRESHOLD 0x{THRESH_ADDR:05X} = tp+0x{THRESH_ADDR - TP:04X}  raw "
          f"{bytes(v75[THRESH_ADDR:THRESH_ADDR + 4]).hex()} = f32 {thresh}  ⇒ trip at "
          f"|gp-0x{CELL_DISP:04x}| > {int(thresh * FAULT_SCALE)} counts   [FROZEN by V81]")
    print(f"    WRITER    st.h r6,-0x{CELL_DISP:04x}[gp] @0x{CELL_WRITER:05X}, inside "
          f"FUN_{WRITER_FN:08x} -- the ONLY writer image-wide")
    print(f"              (4 methods: disp16 · 6-byte disp23 · LE32 literal · movhi/movea pair; "
          f"readers {[hex(a) for a in CELL_READERS]})")
    print(f"    CLAMP     0x{CLAMP_ADDR:05X} = tp+0x{CLAMP_TP_DISP:04X}   3 SIGNED `ld.h` readers "
          f"{[hex(a) for a in CLAMP_READERS]}, ZERO writers ⇒ blast radius = this ONE lane")
    for who, val in (("stock/V38", s16(stock, CLAMP_ADDR)), ("the flown V75", base_clamp),
                     ("V81", CLAMP_NEW_VALUE)):
        m = TRIP_COUNTS - val
        print(f"      {who:>14s}: clamp {val:4d} vs trip {TRIP_COUNTS}  ⇒ margin {m:+5d}  "
              f"{'UNTRIPPABLE BY CONSTRUCTION' if m > 0 else '🛑 TRIPPABLE'}")

    # =================================================================================================
    # APPLY THE EDITS
    # =================================================================================================
    code = bytearray(v75)
    print("\n" + "-" * 102)
    print("  APPLYING THE EDITS -- every one asserted BEFORE and AFTER")

    # ---- EDIT 1 -------------------------------------------------------------------------------------
    assert u16(code, CLAMP_ADDR) == CLAMP_BASE_VALUE, "the clamp moved between the gate and the write"
    old_raw = bytes(code[CLAMP_ADDR:CLAMP_ADDR + 2])
    struct.pack_into("<H", code, CLAMP_ADDR, CLAMP_NEW_VALUE)
    new_raw = bytes(code[CLAMP_ADDR:CLAMP_ADDR + 2])
    assert u16(code, CLAMP_ADDR) == CLAMP_NEW_VALUE and s16(code, CLAMP_ADDR) == CLAMP_NEW_VALUE, \
        "the clamp write did not take, or 511 does not round-trip as a positive int16"
    print(f"    EDIT 1  0x{CLAMP_ADDR:05X}  {CLAMP_BASE_VALUE} -> {CLAMP_NEW_VALUE}   "
          f"{old_raw.hex()} -> {new_raw.hex()}   (u16 LE)")
    assert u16(code, CLAMP_NEIGHBOUR[0]) == CLAMP_NEIGHBOUR[1], \
        f"0x{CLAMP_NEIGHBOUR[0]:05X} moved -- adjacent to the clamp, owner UNIDENTIFIED"
    print(f"            neighbour 0x{CLAMP_NEIGHBOUR[0]:05X} = {CLAMP_NEIGHBOUR[1]} untouched "
          "(owner UNIDENTIFIED)")

    # ---- EDIT 2 -------------------------------------------------------------------------------------
    print(f"\n    EDIT 2  FRICTION = {FRICTION}   target Y = {FRICTION_TARGET}")
    print(f"            {len(x15)} records carry V74's x1.5, DERIVED through 0x{FRICTION_PTR_ARRAY:05X} "
          f"over all {N_MODES} modes:")
    moved_fr = []
    for y_addr in sorted(x15):
        rec, mode, old_y, new_y = x15[y_addr]
        col = "ENG" if mode in ENGAGED else ("DIS ⚠" if mode in DISENGAGED else "???")
        assert rec3_y(code, rec) == old_y, f"friction m{mode} @0x{rec:05X} moved before the write"
        if new_y != old_y:
            struct.pack_into("<3h", code, y_addr, *new_y)
            moved_fr.append(y_addr)
        assert rec3_y(code, rec) == new_y, f"friction m{mode} @0x{rec:05X} did not take {new_y}"
        assert rec3_x(code, rec) == FRICTION_X, f"friction m{mode} X moved"
        flag = "" if new_y != old_y else "   (no-op: FRICTION=V75)"
        print(f"              m{mode:2d} {col:5s} rec 0x{rec:05X}  Y@0x{y_addr:05X}  "
              f"{old_y} -> {new_y}{flag}")
    want_moved = 0 if FRICTION == "V75" else len(x15)
    assert len(moved_fr) == want_moved, \
        f"{len(moved_fr)} friction rows moved, expected {want_moved} for FRICTION={FRICTION}"
    assert_friction_uniform(code, "V81", FRICTION_TARGET)
    if FRICTION == "STOCK":
        for mode in range(N_MODES):
            rec = factor_rec(code, FRICTION_PTR_ARRAY, mode)
            n = rec_len(code, rec)
            assert bytes(code[rec:rec + n]) == bytes(stock[rec:rec + n]), \
                f"🛑 V81: friction m{mode} @0x{rec:05X} is not byte-STOCK after the revert"
        print(f"            ✅ ALL {N_MODES} friction records are now byte-identical to HONDA STOCK.")
        print(f"            ⚠ DECLARED DEVIATION: mode(s) {FRICTION_X15_DISENGAGED} are in the "
              "DISENGAGED column. The edit is a")
        print("              REVERT TO STOCK, so that column can only become MORE stock -- asserted "
              "above, not argued.")
    else:
        print("            ✅ ZERO friction bytes move -- V81-B is single-variable against the "
              "flown V75.")

    # =================================================================================================
    # THE LANE ARITHMETIC -- what the two variants actually cost, recomputed from the bytes written
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  THE FRICTION LANE, RECOMPUTED FROM THE BYTES JUST WRITTEN "
          "(FUN_00036c12's arithmetic, mirrored)")
    print("    |gp-0x6c2c| needed to SATURATE the clamp, per speed. Lower = saturates more often.")
    live_rec = factor_rec(code, FRICTION_PTR_ARRAY, LIVE_MODE)
    print(f"      {'km/h':>5} {'counts':>7} | {'Y stock':>8} {'Y x1.5':>8} | "
          f"{'V75 flown':>10} {'V81-A':>8} {'V81-B':>8} | {'A/V75':>6} {'B/V75':>6}")
    sat_rows = []
    for kmh in (0, 5, 10, 20, 40, 60, 90):
        sc = kmh * SPEED_COUNTS_PER_KMH
        y_st = LM.lerp_int(sc, FRICTION_X, FRICTION_Y_STOCK)
        y_15 = LM.lerp_int(sc, FRICTION_X, FRICTION_Y_V75)
        d_v75 = drive_to_saturate(y_15, CLAMP_BASE_VALUE)        # x1.5 + clamp 850  (what flew)
        d_a = drive_to_saturate(y_st, CLAMP_NEW_VALUE)           # stock  + clamp 511
        d_b = drive_to_saturate(y_15, CLAMP_NEW_VALUE)           # x1.5   + clamp 511
        sat_rows.append((kmh, y_st, y_15, d_v75, d_a, d_b))
        print(f"      {kmh:5d} {sc:7d} | {y_st:8d} {y_15:8d} | {d_v75:10d} {d_a:8d} {d_b:8d} | "
              f"{d_a / d_v75:6.2f} {d_b / d_v75:6.2f}")
    # 🛑 the monotonicity the bisection assumes, asserted rather than believed
    for _kmh, y_st, y_15, _a, _b, _c in sat_rows:
        prev = -1
        for dv in range(0, 8000, 97):
            cur = abs(friction_raw(y_15, dv))
            assert cur >= prev, "|friction_raw| is not monotone in |drive| -- the bisection is invalid"
            prev = cur
    d_v75_0, d_a_0, d_b_0 = sat_rows[0][3], sat_rows[0][4], sat_rows[0][5]
    stock_thr = drive_to_saturate(LM.lerp_int(0, FRICTION_X, FRICTION_Y_STOCK),
                                  s16(stock, CLAMP_ADDR))
    print("\n    ⇒ AT CREEP (the ratchet's own speed band), the |gp-0x6c2c| needed to REACH the clamp:")
    print(f"       STOCK / V38            >= {stock_thr}")
    print(f"       the FLOWN V75          >= {d_v75_0}   ({d_v75_0 / stock_thr:.2f}x stock)")
    print(f"       V81-A (FRICTION=STOCK) >= {d_a_0}   ({d_a_0 / d_v75_0:.2f}x V75)")
    print(f"       V81-B (FRICTION=V75)   >= {d_b_0}   ({d_b_0 / d_v75_0:.2f}x V75)")
    assert d_a_0 == stock_thr, \
        "V81-A's saturation threshold is not identical to STOCK's -- the revert is not a revert"
    print("       🛑 READ THIS THE RIGHT WAY ROUND: a LOWER threshold means the lane reaches its "
          "clamp MORE often.")
    print(f"          V81-A's threshold is {d_a_0 / d_v75_0:.2f}x V75's, so in raw duty-cycle terms "
          "it clamps slightly MORE often --")
    print("          BUT it is BYTE-FOR-BYTE STOCK's (same Y row, same 511 clamp), and at 511 the "
          "clamp is BELOW the")
    print("          512-count trip, so clamping is HARMLESS by construction. The thing that "
          "matters is not how often the")
    print("          lane clamps but whether the clamp can trip the monitor -- and at 511 it cannot, "
          "ever. [EVIDENCE]")
    print("       ⊕ EMPIRICALLY the lane does not even get close on this configuration: V76 flew "
          "route 65 with Honda's")
    print("          friction row and 0xC407E = 511, and its `|gp-0x6b26| > 448` probe bit fired "
          "**0 / 63,477 frames**")
    print("          with a 99.926% positive control. V81-B's threshold, by contrast, is "
          f"{d_b_0 / d_v75_0:.2f}x V75's -- strictly")
    print("          worse than the build that faulted. That is why variant A was selected.")
    print(f"    ⊕ At the clamp the lane still sits well inside the aggregator's +/-{AGG_ZERO_REJECT} "
          f"ZERO-REJECT window ({CLAMP_NEW_VALUE} < {AGG_ZERO_REJECT}) ⇒ no contribution cliff.")

    # =================================================================================================
    # RE-ASSERT EVERYTHING ON THE FINISHED IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  RE-ASSERTING ON THE FINISHED IMAGE")
    out_cens = assert_interlock_censuses(code, "V81")
    assert out_cens == src_cens, f"the censuses moved: {src_cens} -> {out_cens}"
    clamp, margin = assert_interlock_margin(code, "V81", CLAMP_NEW_VALUE)
    assert_keep_list(code, "V81")
    assert_pointer_arrays_stock(code, stock, "V81")
    man = assert_manual_mode_stock(code, stock, "V81")
    d99, d127, d60, k = assert_live_surface(code, "V81")
    cave_bytes, _redis = assert_cave_identical(code, v75, "V81")
    V75.assert_probe_censuses(bytes(code), cave_span, V75.CAVE_ACCESS_ON_OUTPUT)
    V74.assert_clamp_census(bytes(code))
    _rows2, eng2, dis2 = V74.derive_mode_columns(bytes(code))
    assert (eng2, dis2) == (ENGAGED, DISENGAGED), "the mode columns moved"
    print(f"    ✅ INTERLOCK: 0x{CLAMP_ADDR:05X} = {clamp}, margin {margin:+d} to the "
          f"{TRIP_COUNTS}-count trip ⇒ UNTRIPPABLE BY CONSTRUCTION")
    print(f"    ✅ MANUAL mode {MANUAL_MODE} byte-STOCK on all six record types, resolved through the "
          f"pointer arrays: {', '.join(f'{k_}@0x{v:05X}' for k_, v in man.items())}")
    print(f"    ✅ LIVE mode {LIVE_MODE}: FactorC {LIVE_SURFACE_EXPECT['factor_c_xy'][1]} · FactorE X "
          f"{LIVE_SURFACE_EXPECT['factor_e_xy'][0]} Y {LIVE_SURFACE_EXPECT['factor_e_xy'][1]}")
    print(f"       dose(r={BURST_RATE}) = {d99} at creep, {d60} at 60 km/h · dose(r={BURST_RATE_69HZ}) "
          f"= {d127} · k = {k:.4f}   -- IDENTICAL to the flown V75")
    print(f"    ✅ CAVE: 68 B @0x{CAVE_BASE:05X} byte-identical to V75 AND equal to "
          f"`build_v75_tva.build_cave()`'s re-derivation; hook @0x{HOOK_ADDR:05X} unchanged.")
    print(f"       {cave_bytes.hex()}")

    # ---- the inherited V74/V75 keep-list, run on a RESTORED probe -----------------------------------
    # 🛑 `V74.assert_must_not_change` asserts 0xC407E == 850 and the friction rows == x1.5, both of
    # which V81 deliberately changes. Rather than WEAKEN the guard, restore exactly those bytes on a
    # copy, run the guard IN FULL, and assert the exception set is exactly the attributed one. That
    # is V74's own idiom for its mode-12 relaxation.
    attributed = {CLAMP_ADDR, CLAMP_ADDR + 1} | {a + k for a in moved_fr for k in range(6)}
    probe = bytearray(code)
    for a in attributed:
        probe[a] = v75[a]
    exc = [i for i in range(len(v75)) if probe[i] != v75[i]]
    assert not exc, f"the relaxation copy is not the flown V75: {[hex(x) for x in exc[:8]]}"
    V74.assert_must_not_change(probe, "V81 (attributed bytes restored)", stock, v74)
    print("    ✅ THE FULL INHERITED KEEP-LIST re-run on a copy with ONLY the attributed bytes")
    print("       restored -- both `sar` sites, the gate, all three arms, V72's gain_A r26 cut, "
          "LEVER C,")
    print("       0x454FE, the six pointer arrays, the config table, V57's decoupling, V53's")
    print("       STOCK_CALS, the partial-record-write rule and the whole DISENGAGED column: PASS.")

    # =================================================================================================
    # CRC
    # =================================================================================================
    touched = sorted({CLAMP_ADDR} | set(moved_fr))
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = ([0xC4FFC] if FRICTION == "V75" else
                       [0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC, 0xD4FFC, 0xD6FFC, 0xD7FFC,
                        0xD8FFC, 0xD9FFC])
    assert [b[1] for b in blocks] == expect_trailers, \
        f"expected trailers {[hex(t) for t in expect_trailers]}, got {[hex(b[1]) for b in blocks]}"
    print("\n" + "-" * 102)
    print(f"  CRC -- EXACTLY {len(blocks)} block(s) move (asserted, not observed):")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")
    all_edit_bytes = set(attributed)
    assert not [a for a in all_edit_bytes if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block, V40 ignition precedent"
    assert not [a for a in all_edit_bytes if a < START or a >= END], \
        f"an edit landed outside the flashable region [0x{START:X},0x{END:X})"
    print(f"    ✅ none of the {len(all_edit_bytes)} edited bytes lands in [0xC5000,0xC5FFC) (the "
          "CRC-skipped block, V40 ignition precedent),")
    print(f"       and all of them lie inside the flashable region [0x{START:X},0x{END:X}).")

    # =================================================================================================
    # 🛑 DELIVERABLE 2 -- THE FULL BYTE DIFF vs THE FLOWN V75
    # =================================================================================================
    def attribute(d):
        if d in (CLAMP_ADDR, CLAMP_ADDR + 1):
            return f"EDIT 1  0x{CLAMP_ADDR:05X} clamp {CLAMP_BASE_VALUE} -> {CLAMP_NEW_VALUE}"
        for y in moved_fr:
            if y <= d < y + 6:
                return f"EDIT 2  friction Y x1.5 -> {FRICTION}"
        if d in crc_only:
            return "CRC trailer"
        return None

    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V81 vs THE FLOWN V75 -- over the WHOLE 1 MiB image")
    runs = diff_runs(code, v75, attribute)
    total = sum(b - a + 1 for a, b in runs)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    print(f"      {'range':<21s} {'len':>4s}  {'V75':<14s}    {'V81':<14s}  attribution")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {bytes(v75[a:b + 1]).hex():<14s} -> "
              f"{bytes(code[a:b + 1]).hex():<14s}  {attribute(a)}")
    assert not stray, \
        f"🛑 UNATTRIBUTED bytes vs the flown V75: {[hex(x) for x in stray[:16]]} -- STOP AND REPORT"
    functional = total - len(crc_only & {d for a, b in runs for d in range(a, b + 1)})
    want_fn = 2 + 6 * len(moved_fr)
    assert functional == want_fn, f"{functional} functional bytes, expected {want_fn}"
    print(f"    ⇒ {functional} FUNCTIONAL byte(s) + {total - functional} CRC byte(s). "
          f"Nothing else moved, anywhere in the image.")

    # ---- THE VALUE-ANCHORED VERIFIER: whole-image identity modulo the attributed set ---------------
    assert_identity_modulo(code, v75, attributed | crc_only, "V81")
    print(f"    ✅ VALUE-ANCHORED: restoring the {len(attributed)} attributed + {len(crc_only)} CRC "
          "bytes reproduces the flown V75")
    print("       BYTE-FOR-BYTE over all 0x100000 bytes. This is a TOTAL statement, not a span check.")

    # ---- and vs STOCK, so the carried lineage is visible --------------------------------------------
    d_stock = [i for i in range(len(stock)) if code[i] != stock[i]]
    d_stock_v75 = [i for i in range(len(stock)) if v75[i] != stock[i]]
    print(f"    ⊕ vs STOCK: V81 differs at {len(d_stock)} bytes, the flown V75 at "
          f"{len(d_stock_v75)} -- the V38->V75 lineage is carried.")

    # =================================================================================================
    # THE .rwd -- ENCODED AND READ BACK IN MEMORY EVEN ON A DRY RUN
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  .rwd ENCODE + READBACK (done in memory even on a dry run, so the container path is "
          "proven before the operator names the variant)")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V81 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v75)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, never from the in-memory build.
    rb_cens = assert_interlock_censuses(dec, "V81 readback")
    assert rb_cens == out_cens, "the readback censuses differ"
    rb_clamp, rb_margin = assert_interlock_margin(dec, "V81 readback", CLAMP_NEW_VALUE)
    assert_keep_list(dec, "V81 readback")
    assert_pointer_arrays_stock(dec, stock, "V81 readback")
    assert_manual_mode_stock(dec, stock, "V81 readback")
    rb_surface = assert_live_surface(dec, "V81 readback")
    assert rb_surface == (d99, d127, d60, k), "the readback surface differs"
    assert_cave_identical(dec, v75, "V81 readback")
    V75.assert_probe_censuses(bytes(dec), cave_span, V75.CAVE_ACCESS_ON_OUTPUT)
    V74.assert_clamp_census(bytes(dec))
    assert_friction_uniform(dec, "V81 readback", FRICTION_TARGET)
    derive_friction(dec, dec) if FRICTION == "V75" else None
    assert V74.derive_mode_columns(bytes(dec))[1:] == (ENGAGED, DISENGAGED)
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_probe = bytearray(dec)
    for a in attributed:
        rb_probe[a] = v75[a]
    for a in crc_only:
        rb_probe[a] = v75[a]
    assert bytes(rb_probe) == v75, "the readback is not the flown V75 outside the attributed set"
    V74.assert_must_not_change(rb_probe, "V81 readback (restored)", stock, v74)
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    print(f"    ✅ READBACK: the interlock ({rb_clamp}, margin {rb_margin:+d}), all four censuses, "
          "the keep-list, the six")
    print("       pointer arrays, MANUAL mode 24 byte-STOCK, the live surface and dose table, the "
          "68-byte cave and its")
    print("       re-disassembly, EVERY friction record, identity to the flown V75 outside the "
          "attributed set, and the")
    print("       full 50/50 CRC chain: ALL re-verified FROM THE DECODED .rwd PAYLOAD.")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # =================================================================================================
    # WRITE -- only if explicitly enabled
    # =================================================================================================
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WAS WRITTEN TO DISK.")
        print("     The friction variant is the OPERATOR's call; re-run with ACCORD_V81_WRITE=rwd")
        print("     once it is named. Exactly ONE flashable .rwd per build number is the kit's rule.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(
                f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists (on disk "
                f"{hashlib.sha256(existing).hexdigest()}, about to write {img_sha}). A same-number "
                "re-cut destroyed a predecessor's snapshot once already and produced an artefact NO "
                "gate could check. Rename or delete it deliberately, then re-run.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}")
        if WRITE_MODE == "rwd":
            assert not os.path.exists(OUT) or Path(OUT).read_bytes() == rwd, \
                f"🛑 a DIFFERENT {OUT} already exists -- exactly ONE flashable .rwd per build number"
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}")

    print(f"\n  V81 [{variant_token()}] -- image SHA256 {img_sha}")
    print(f"                            .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  ★ EDIT 1 restores Honda's DTC-0x1d interlock: 0x{CLAMP_ADDR:05X} = {CLAMP_NEW_VALUE} "
          f"vs a {TRIP_COUNTS}-count trip.")
    print(f"  ★ EDIT 2 = FRICTION {FRICTION}. Everything else is the flown V75, byte for byte.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without touching an image."""
    assert CLAMP_ADDR - TP == CLAMP_TP_DISP == 0x507E
    assert CLAMP_NEW_VALUE < TRIP_COUNTS == 512 and TRIP_COUNTS - CLAMP_NEW_VALUE == 1
    assert struct.unpack("<f", THRESH_BYTES)[0] == THRESH_VALUE == 0.5
    assert int(THRESH_VALUE * FAULT_SCALE) == TRIP_COUNTS
    assert [(y * 3) // 2 for y in FRICTION_Y_STOCK] == FRICTION_Y_V75
    assert len(FRICTION_X15_Y_EXPECT) == len(FRICTION_X15_MODES_EXPECT) == 14
    assert set(FRICTION_X15_MODES_EXPECT) - set(ENGAGED_EXPECTED) == set(FRICTION_X15_DISENGAGED)
    assert MANUAL_MODE not in FRICTION_X15_MODES_EXPECT
    assert "+" not in variant_token()
    # the friction mirror against a hand-worked point
    assert friction_raw(-9830, 1000) == (((1000 * -9830) >> 6) * 0x111) >> 0x12


if __name__ == "__main__":
    _self_check()
    build()
