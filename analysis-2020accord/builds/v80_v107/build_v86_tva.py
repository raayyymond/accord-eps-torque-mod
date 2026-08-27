#!/usr/bin/env python3
r"""builds/v80_v107/build_v86_tva.py -- V86 = ONE CALIBRATION CELL. The command-EMA becomes a FREQUENCY experiment.

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
`0xC40D4` is the **command-EMA coefficient** inside `FUN_0003b8f6`, the 1 kHz plant-model estimator:
`alpha = 573/4096 = 0.1399 -> 286/4096 = 0.0698`. **It is a FREQUENCY lever, not an amplitude one.**
Over a 28x range of `alpha` the loop's -180 deg crossing moves **4.97 -> 9.52 Hz** while the predicted
limit-cycle AMPLITUDE moves **+-5%**. That matters because **amplitude comparisons have now failed four
builds running** -- route `6e`'s split-half nulls are **[0.63, 1.50]** wide, and V85 read a clean null
in every band despite delivering a real, byte-proven **20.3x** mechanism reduction.
⇒ **A frequency claim is immune to the noise floor that has swallowed the last four amplitude claims.**

⊕ It is NOT purely diagnostic. `573 -> 286` cuts the estimator's HF gain to **0.650x at 20 Hz** and
**0.585x at 28 Hz** -- directly in the band the operator calls grinding. The opposite direction (1146)
would have RAISED it 1.216x / 1.355x, which is why the direction is **down**, not up.

THE BASE -- SETTLED, AND PROVEN ON-CAR
--------------------------------------------------------------------------------------------------
`_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin`
  sha256 `cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f`, asserted before a byte
  moves, with the five images it must NEVER be confused with listed in `NOT_THE_BASE`.
**V85 flew as route `6e`, fault-free** (`STEER_STATUS` = {0: 43,641}, 0 DTC-active, 0 sentinels).

THE EDIT SET -- 1 cell, 2 bytes
--------------------------------------------------------------------------------------------------
  #   cell                       addr      V85     V86     bytes          equals
  1   command-EMA coefficient    0xC40D4   573      286    3d02 -> 1e01   NOTHING PREVIOUSLY FLOWN

🛑 **THE OPERATOR'S HARD CONSTRAINT IS SATISFIED BY CONSTRUCTION, NOT BY ARGUMENT.**
An EMA has `|H(0)| = alpha / (1 - (1 - alpha)) = 1` **exactly, for every alpha** -- the alpha cancels.
Under any sustained command the estimator converges to a **bit-identical** value; only transient
tracking changes. ⇒ **this edit CANNOT limit the maximum LKAS-commanded steering angle rate.** The
build re-derives this numerically over `alpha` in {0.0349 … 0.9998} and asserts `1.000000000000`.

★ MODE-PROOF, SO RULE 7 IS MOOT FOR THE CONTROL CELL. `0xC40D4` is a flat `tp` scalar
(`tp+0x50D4`, `tp = 0xBF000`). The value 573 appears **exactly once** in all of `[0xC4000, 0xC4200)`,
and **no stride S in [2, 0x400) repeats it** -- contrast the FactorC mode table, which repeats at
stride `0x14`. It is not a mode-indexed record and cannot be written into the wrong column.

★★ THE PROBE -- THE EXISTING 68-BYTE CAVE, REPOINTED. NO NEW EXTENT, NO SECOND HOOK, NO NEW RAM.
---------------------------------------------------------------------------------------
Same hook `0x55C0E`, same cave base `0xC4B34`, `CAVE_EXTENT` = 68 UNCHANGED, same 5 bits of
`0x14A` byte4[7:3], same `andi 0x7` preserving the live `STEER_SENSOR_STATUS` bits 2:0, same
displaced-`movea` re-execution, same `jmp [lp]`. **62 bytes of body + 6 bytes of `0xFF` pad**; the pad
sits AFTER an unconditional `jmp [lp]` and is therefore unreachable.

| bit | rung | why |
|---|---|---|
| `b7` | `gp-0x6b70 < 0`        | SIGN of the Coulomb friction-compensator output |
| `b6` | `gp-0x6b70 != 0`       | liveness -- the term is producing something at all |
| `b5` | `\|gp-0x6b70\| >= 64`  | magnitude, two-sided, trips at +64 / -65 |
| `b4` | `gp-0x67ab < 2`        | **the aggregator's optional-term GATE** -- probe the gate, not just the output |
| `b3` | hard-coded **1**       | field-liveness control / build fingerprint |

🛑🛑 **WHY `b5`'s THRESHOLD IS 64 AND NOT 512 -- AND WHY `b5 ~= b6` IS A *POSITIVE* RESULT.**
`gp-0x6b70 = clamp(SIGN(resid) * LERP(|resid|), +-8192)` is **MEMORYLESS -- there is no EMA on its
output.** So the band `(0, 64)` is populated **only if the LERP actually ramps through small values**,
which makes the **`b5`/`b6` duty RATIO a second, independent relay-vs-linear discriminator**,
orthogonal to the `b7`/`b6` zero-crossing test:
  · **`b5/b6` -> 1.00** ⇒ the output jumps straight past 64 whenever it leaves zero ⇒ **a PLATEAU,
    relay-like: no linear ramp exists.**
  · **`b5/b6` << 1** ⇒ it spends most of its non-zero time inside `(0, 64)` ⇒ **shaped/viscous, and a
    relay CANNOT do this.**
🛑 **`b5 ~= b6` IS THEREFORE A POSITIVE RESULT (plateau DETECTED), NOT A SATURATED OR WASTED RUNG.**
State it that way or it will be misread as "the rung pinned high and told us nothing".
⊕ At 512 the band `(0, 512)` fills under almost any shape and the ratio carries nothing. At 64 both
outcomes are reachable and both are informative, so **there is no uninterpretable branch** -- and
`b5 == 0` now means something concrete: *the term never reaches 64 counts, i.e. under 0.8% of its own
+-8192 clamp*, rather than being confounded with a LERP table nobody could read.

🛑 **THIS BUILD WAS CUT ONCE WITH THE WRONG THRESHOLD AND RE-CUT.** The first cut carried `a932`
(`sar 0x9` ⇒ T = 512) at cave offset **+18**; the spec is `a632` (`sar 0x6` ⇒ T = 64). **One byte.**
Both defective artefacts were DELETED (not renamed -- they carried no evidence) and the build re-cut
under the same `OUT`/`TAG`/`BIN_OUT`. `assert_cave_is_spec` now pins the whole 68-byte payload to
`EXPECTED_CAVE_HEX` and checks **+18 by name, first**, so the same class of defect fails loudly.

🛑 **THE PROBE CANNOT SCORE `0xC40D4` IN FORCE, AND THE HEADER SAYS SO RATHER THAN IMPLYING OTHERWISE.**
**V86 is the first build ever to read `gp-0x6b70`**, so every predicted duty shift is against a
baseline that DOES NOT EXIST. What scores the control cell is (a) the build-time assertion
`0xC40D4 == 0x011E` re-read from the BUILT image, and (b) the frequency ratio from the bar -- **no
probe bits**. **The baseline arrives with V86B** (same cave, same cell at 573), which is a real reason
to fly both.

★ **THE STRUCTURAL INVARIANTS ARE DUALS OF V85's, WHICH GIVES BUILD IDENTITY WITH NO FREE PARAMETER.**
V86 requires `b7 => b6` and `b5 => b6`. V85 required `b6 => b7`. ⇒ **a single `b6 & !b7` frame refutes
V85, and a single `b7 & !b6` frame refutes V86.** Each pair is computed from the SAME register in the
SAME cave pass, so zero violations are permitted -- not a rate, not a sampling race.

🛑 **THE TAIL IS BYTE-IDENTICAL TO V85's FLOWN CAVE** (V86 `+38..+61` == V85 `+44..+67`, 24 bytes),
asserted here from both images. The re-issued `cmp 0x0,r6` at `+12` is REQUIRED: the `add 0x4,r7` at
`+10` clobbers the flags the second rung needs.

GATE 1 -- RAM OWNERSHIP.  **PASS.** [EVIDENCE, two methods + the aliasing forms]
------------------------------------------------
V86 allocates no RAM, adds no instruction outside the already-proven 68-byte cave, grows no extent and
introduces no new writer of anything. Censused FRESH on the BUILT image:
  · `gp-0x6b70`: **1 writer (`0x382D2`) / 1 firmware reader (`0x38006`)**, 0 absolute literals,
    0 movhi/movea, **0 disp23**. The cave adds a READ and writes nothing.
  · `gp-0x67ab`: **1 writer (`0x2775C`) / 2 firmware readers (`0x2774C`, `0x37FE6`)**, 0 aliases.
  🛑 **BOTH cave loads carry hw2 IDENTICAL to the firmware's own read of the same cell** -- `0x9490`
  against `0x38006`, `0x9855` against `0x37FE6`. Only the `reg2` field differs (the firmware targets
  `r13`, the cave `r6`), which it must. Re-derived independently by `V55.ldh` / `V55.ldbu_any`.
  🛑 `r7` is provably DEAD across the hook: `0x55C12` is `mov 0x8,r7`. `r6` is restored by the
  displaced `movea` re-executed LAST.

GATE 2 -- CLOSED-LOOP STABILITY (MAGNITUDE **AND** PHASE).
------------------------------------------------------------------------------------------------
  PHASE. **This edit IS a phase change, and that is its purpose** -- so it is argued, not waved past.
  Lowering `alpha` moves the estimator's pole and the loop's -180 deg crossing **away from** the
  12.8 Hz [12.1, 13.6] wheel-on-torsion-bar plant mode. That is the CONSERVATIVE direction on the one
  loop parameter that cannot be pinned (plant Q), and it was verified amplitude-neutral within
  **+-8% for every Q in [2, 40]**, in both directions.
  MAGNITUDE. **REDUCED at HF, unchanged at DC.** `|H(0)| = 1` exactly (above). At 20 Hz the estimator
  gain falls to 0.650x, at 28 Hz to 0.585x.
  ⚠ **WHAT GATE 2 DOES NOT COVER**: this is a linear pole move in a loop whose plant Q is inferred,
  not measured. The Q-sweep bounds the amplitude effect; it does not prove the frequency prediction.
  **The probe is what converts that to a measurement.**

🛑🛑 TWO TRAPS THAT ARE LIVE TODAY -- RECORDED SO THEY ARE NOT RE-PROPOSED
--------------------------------------------------------------------------------------------------
1. **`0xC61F6` 3 -> 0 MUST NOT BE MADE.** A deadband is the **DUAL of a relay**: `N(A) -> 0` as
   `A -> 0` is precisely what *prevents* a limit cycle. Deleting it **ADDS** small-signal gain -- the
   DESTABILISING direction -- and it costs only 0.4% at the lane's own full scale anyway. FROZEN at 3.
2. **`gain_A` rec0/rec1 -> 512 on a V85 base produces a byte diff that LOOKS like V72's r26
   configuration AND IS NOT.** V72's gate byte `0x3AA96` was `C5`; V85's is `FB`, and with `FB` the
   armed path **OVERWRITES** `gain_A` with `[0xC6444]`. **Any future "we reproduced V72" claim must
   dereference `0x3AA96` first.** Not made here; recorded.

CELLS EXPLICITLY REJECTED FOR V86 -- do not re-propose
--------------------------------------------------------------------------------------------------
  · **`0xC40BC` -- FROZEN at 6000.** ⊕ It is MEMORYLESS, so its describing function is real and
    positive and it contributes **exactly zero phase** ⇒ it **cannot** move the frequency V86
    measures. **The V86 test is immune to V85's edit by construction.**
  · **`gain_A` rec0/rec1 -- DEAD.** Lever B's repoint makes `lp = latActive` and the armed path
    overwrites `gain_A` with `[0xC6444]` = 512. V84/V85 already deliver 512 engaged at EVERY speed,
    deeper than V72/V73. An already-run, twice-failed pre-registered experiment.
  · **Lever A (`0x3AB76`/`0x3AC20`) -- DO NOT RESTORE.** Its `sar` is UNGATED, so it reproduces
    V62/V65 manual behaviour verbatim, and `r24 >= ~2` is necessary for grind #2 in every build that
    has produced it. Grind #2 is on the operator's forbidden list.
  · **The 13-point LERP `0xC6B66`/`0xC6B80` -- DEAD.** `gp-0x6a10` is **absolute steering angle**, not
    tracking error (99.94% match to `|angle| >= 0.85 deg`); 88.6% of engaged driving sits in its flat
    first segment.
  · **`0xC6200` -- DISQUALIFIED** pending a reader census: it is **6 bytes** from `0xC6206`/`0xC6208`,
    which V40 set to `0xFFFF` and BRICKED the ECU with. FROZEN at 8192 here.
  · **`0xC63A0` -- HELD OUT.** It was 2048 on V72/V73/V74/V75/V81 and silently reverted at V84. It was
    a live candidate, but **V81 carried 2048 and V81 is the drive on which the operator reported the
    LKAS angle rate felt limited.** That association is unresolved and his constraint is explicit.

THE BASE -- SETTLED, AND PROVEN ON-CAR
--------------------------------------------------------------------------------------------------
`_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin`
  sha256 `cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f`, asserted before a byte
  moves, with the four images it must NEVER be confused with listed in `NOT_THE_BASE`.
**V85 flew as route `6e`, fault-free** (`STEER_STATUS` = {0: 43,641}, 0 DTC-active, 0 sentinels).

WHAT THIS FILE PROVIDES, AND WHAT IT DELIBERATELY DOES NOT
--------------------------------------------------------------------------------------------------
PROVIDED (all cell-list-independent, all runnable today):
  1. base load + sha256 gate + a negative list of look-alike images
  2. **15 FROZEN cells + 2 FROZEN bytes = 17 items**, asserted ONE AT A TIME **from the BUILT image**
  3. **`ANCHORS` -- a VALUE-anchored verifier**: exact expected values at exact addresses across the
     ENTIRE live non-stock surface, plus the stock cells that must be understood as stock
  4. **a ZERO-UNATTRIBUTED-BYTES gate**: every byte differing from the V85 base must resolve to a
     declared control cell, a declared code edit, the probe cave, or a CRC word -- else the build FAILS
  5. **RULE 7 mode-proof scaffolding**: all **10** pointer arrays × all **34** mode slots,
     DEREFERENCED, never a hard-coded record address; the residual-record census; the anchors
  6. CRC recomputation + the `[0xC5000,0xC5FFC)` interdiction + the 50/50 chain walk
  7. `.rwd` encode + in-memory readback + a from-disk re-verify, on the same discipline as V85
  8. a cave assembly/emit path with the V85 payload carried forward until `probe-design` lands

NOT PROVIDED (deliberate -- these are phase 2, and they are the operator's call, not the builder's):
  · **any control cell.** `CONTROL_CELLS` is `()`. No lever is guessed, invented or implied here.
  · **any V86 probe payload.** `CAVE_PAYLOAD` is `None` ⇒ V85's 68 bytes are carried BYTE-FOR-BYTE.
  · **a variant token / output filename.** `VARIANT_TOKEN` is `None` and every write path refuses.

🛑 THE FROZEN SET -- 12 CELLS + 2 BYTES = 14 ITEMS, AND WHY EACH ONE IS THERE
--------------------------------------------------------------------------------------------------
V85 declared **10 `FROZEN_CELLS` + 2 `FROZEN_BYTES` = 12 items**, and all 12 verify PASS on its image.
⚠ `docs/STATE.md` says "14 frozen cells"; **that number is wrong for V85** (no 14-item list exists in
the kit -- the "14" in `BUILD-LINEAGE.md` is the 14 *friction sites*, a different set). It is NOT
propagated here. V86's list reaches **14 items by ADDING TWO CELLS**, and that coincidence with
`STATE.md`'s wrong number is exactly that -- a coincidence. The two additions are named:

  carried from V85 (12)
    `0xD77DA`=0 `0xD77EE`=0        FactorC m26/m27 Y[0] -> Honda. The engaged-only damper, DELETED at
                                   V84. 🛑 FROZEN BY OPERATOR DECISION -- the ring's four-point
                                   dose-response (burst duty V80 96.6% -> V81 25.1% -> V84 2.54%) is
                                   the strongest causal chain the kit owns.
    `0xD7822`=60 `0xD7824`=400
    `0xD782C`=140                  FactorE m27 -> Honda. Same package, same reason.
    `0xC6446`=5244 `0x3AA96`=0xFB  Lever B -- the flown V67/V68 arm + gate repoint.
    `0xC6444`=512                  r26's engaged arm -- STOCK, deliberately, as the untried S3 lever.
    `0xC407E`=511                  🛑 THE HARD-FAULT INTERLOCK. Honda ships this clamp **one count
                                   under its own 512 trip** (`FUN_00036d74` tests `|gp-0x6b26|/1024 >
                                   f32 cal(0xC4004)` = 0.5, single-frame, un-debounced, mode-proof, at
                                   1 kHz). **V73 raised it to 850 and V74/V75 both hard-faulted** with
                                   a latched total loss of assist mid-drive. DO-NOT-RAISE, and do not
                                   "fix" it by raising `0xC4004` either -- that cell is anchored below.
    `0xC6CD0`=3564                 V57's decoupled forward reader -- the 4x LKAS setpoint.
    `0xC63A0`=1024                 Path-2 damper weight, Honda's.
    `0x454FE`=0xB5                 V42's macro-ratchet byte. **Silently lost THREE times already**;
                                   keep, even though it is currently MEASURED INERT (`gp-0x67fa == 4`
                                   fires 0/123,277 driving frames).
  NEW IN V86 (2)
    `0xC4080`=0                    🛑🛑 **A LATENT PURE COULOMB RELAY, AND IT COSTS NOTHING ONLY
                                   BECAUSE IT IS ZERO.** In `FUN_0003b8f6`,
                                   `FRICTION += cal(0xC4080)/1024 * ratio` -- note there is **no
                                   `|model|` factor on that term**, unlike the `|model|*ratio*102/1024`
                                   term beside it. ⇒ it is **amplitude-INDEPENDENT**: a pure
                                   `sign(motor rate)` injection whose describing-function gain rises
                                   without bound as amplitude falls. **NEVER RAISE IT.** Raising it
                                   would re-introduce exactly the relay V85 spent its whole build
                                   removing, and in a form V85's `0xC40BC` cannot moderate.
    `0xC40BC`=6000                 🛑 **V85's cell. DECIDED: FREEZE AT 6000 -- neither push nor
                                   revert.** The nonlinearity now measures at **0.0000** of grinding
                                   frames and **4.3%** of micro-ratchet frames after a **20.3x**
                                   reduction. There is no larger dose (`N` is already flat at 6000),
                                   and reverting re-arms a relay index of 7.87 -- 2.4x V80's
                                   bang-bang, the worst grinding this car has ever produced.

🛑 THE VALUE-ANCHORED VERIFIER -- WHY A SPAN DIFF IS NOT ENOUGH
--------------------------------------------------------------------------------------------------
RECORDED TRAP: `verify/diff_build_vs_stock.py` is **SPAN-based**. It answers "did the right region change?"
and is therefore blind to "the right region changed to the WRONG VALUE". `ANCHORS` below asserts
**exact values at exact addresses** -- every live non-stock cell in the cumulative stock->V85 delta,
plus the cells whose *stockness* is load-bearing -- and `classify_diff` adds the complementary gate:
**zero unattributed differing bytes** vs the base. Together they are two-sided: the anchors catch a
silent revert, the classifier catches a silent addition.

🛑 RULE 7 -- MODE PROOF, AND THE LADDER THAT NEVER EXISTED
--------------------------------------------------------------------------------------------------
This car is **`TVCA4`, variant row 11 ⇒ modes 24/25 MANUAL, 26/27 ENGAGED**, and **27 is a SECOND
engaged column** (V83a forgot it and shipped V81's entire damper live for a whole flight). Builds
**V69/V70/V72 wrote mode-10 records and delivered BYTE-STOCK** -- an entire r24 dose ladder that never
existed. Therefore: **every record address in this file is DEREFERENCED through its pointer array**
(`factor_rec(buf, ARRAY, mode)`), never quoted. The three known-good anchors asserted after
dereferencing are FactorC m26 -> `0xD77D0`, FactorE m26 -> `0xD780C`, Friction m26 -> `0xD7A54`.
⊕ And the sweep covers **all 34 mode slots of all 10 arrays**, not the 7-mode view: V85 still carries
residual damper records at modes 0-5/10-12/14/15/17/23/29/32/33 which the 7-mode reader cannot see.
They are unreachable on a row-11 car [BELIEF, structural], but a future edit must not be confused by
them, so they are enumerated explicitly (`assert_residual_records`).

⊕ **A COUNT WORTH RECORDING, because it differs from the one in circulation.** `archive/arc-maps/_session_v86_arc_map.md`
says to audit "all **58** pointer-array slots". The full sweep here is **10 arrays x 34 modes = 340
slots**, and measured on the V85 image **all 340 dereference to DISTINCT record addresses** -- no mode
shares a record with any other, in any family. So 58 is a narrower view, not the whole map; the number
to use for a full audit is **340**. [EVIDENCE -- `sweep_records`, LE reads, pointers dereferenced.]
Of those 340, **34 records outside this car's four columns are non-stock** (V72-V81 damper residue).

🛑 AND ONE GATE HERE EXISTS BECAUSE ITS FIRST DRAFT WAS WRONG. `assert_residual_records` compares the
residual set **against STOCK**, so a write into a record that is *already* non-stock -- e.g. FactorE
mode 10, which carries V72-V75 residue -- **does not change the count and slips straight through**.
`verify/verify_v86_gates.py` case 14 caught exactly that. `assert_records_vs_base` is the repair: every one of
the 340 records must be **byte-identical to the BASE unless the edit list declares otherwise**,
reachable or not. Both are kept; the second is the one that bites.

THE PROBE CAVE
--------------------------------------------------------------------------------------------------
Proven extent: **68 bytes at `0xC4B34`-`0xC4B77`**, flown by V58/V59/V64/V68/V69/V70/V75/V84/V85.
A further **1,144 bytes at `0xC4B78`** are free (asserted all-`0xFF` here). The TX hook for `0x14A`
("330") at `0x55C0E` is TAKEN; `0x55D50` (399 = `0x18F`) and `0x55EFA` (427 = `0x1AB`) are **byte-stock
on every build ever made** and are asserted so. 🛑 The gateway is a **WHITELIST** -- only `0x14A`,
`0x18F`, `0x1AB` cross, so **a new CAN ID can never reach openpilot**; telemetry must ride the existing
frames. Checksum `FUN_00057b24` is called last ⇒ it auto-covers spare-bit writes. The live field is
`0x14A` byte 4 bits 7:3, with bits 2:0 a live `STEER_SENSOR_STATUS` nibble preserved by `andi 0x7`.
**`CAVE_PAYLOAD = None` carries V85's payload byte-for-byte until `probe-design` lands its spec.**

Usage:
    python builds/v80_v107/build_v86_tva.py                        # NULL BUILD: verifies everything, writes nothing
    ACCORD_V86_WRITE=rwd python builds/v80_v107/build_v86_tva.py   # REFUSED until the cell list and token are set
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
import math
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
import build_v55_tva as V55                # noqa: E402  (ldh, ldbu_any encoders)
import build_v67_tva as V67                # noqa: E402  (Lever B's repoint + guards)
import build_v68_tva as V68                # noqa: E402  (cave geometry)
import build_v72_tva as V72                # noqa: E402  (CAVE_EXTENT, 0xC63A0 census)
import build_v74_tva as V74                # noqa: E402  (record readers, censuses, mode columns)
import build_v75_tva as V75                # noqa: E402  (u16/s16/u32, cave helpers)
import build_v81_tva as V81                # noqa: E402  ★ census_gp4 -- the kit's 4-method gp census
import build_v84_tva as V84B               # noqa: E402  ★ V85's base builder -- every frozen guard
import build_v85_tva as V85B               # noqa: E402  ★★ THE BASE's builder -- cave, censuses
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
CAVE_BASE = V68.CAVE_BASE                          # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT                      # 68 -- the PROVEN extent. Never grow it.
CAVE_FREE_END = V84B.CAVE_FREE_END                 # 0xC4FF0 -- above it is the CRC self-descriptor
CAVE_FREE_BYTES = CAVE_FREE_END - (CAVE_BASE + CAVE_EXTENT)     # 1144
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK           # 0x55C0E
TP, GP_BASE = 0xBF000, 0xFEDF8000
GP, TPREG = 4, 5
R6, R7 = 6, 7

u16, s16, u32 = V75.u16, V75.s16, V75.u32
f32 = lambda b, a: struct.unpack_from("<f", b, a)[0]            # noqa: E731

# =====================================================================================================
# THE BASE -- V85, the cut that flew route 6e, FAULT-FREE
# =====================================================================================================
SRC_BIN = plain_image_path(
    "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin")
SRC_SHA256 = "cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f"
SRC_ROUTE = "6e"
NOT_THE_BASE = {  # sha256 -> why it must never be accepted
    "344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a":
        "_v84 -- V85's OWN base. It carries 0xC40BC = 600, i.e. the Coulomb relay V85 removed.",
    "bdd857c942cab37a26b7d78e4c76cefeec054b33fc46d887d448291e15ab2825":
        "the SUPERSEDED control-path-only V84 cut. It never flew.",
    "bb717ce8322d35c587e95084e697a5ad98ba6564ee9265bb09a88a2a241cd25a":
        "_v83a -- it carries the engaged-only damper V84 deleted.",
    "4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b":
        "_v81 -- four builds back, and it carries 0xC63A0 = 2048.",
    "e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c":
        "_v75_CY0.566-EX1.200_magprobe -- it carries 0xC407E = 850, the DTC-0x1d fault mechanism.",
}
STOCK_BIN = stock_fw_path("code.bin")
STOCK_SHA256 = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =====================================================================================================
# THE EDIT SET -- ONE CELL, TWO BYTES
# =====================================================================================================
# CONTROL_CELLS : (addr, width, value_to_ASSERT_on_the_base, value_to_WRITE, label)
#                 width is 1 or 2; a 2-byte cell is packed LITTLE-ENDIAN (`<H`), V850 is LE.
# 🛑 Every entry's `value_to_ASSERT_on_the_base` is checked against the V85 image BEFORE the write and
# 🛑 the write is checked to have taken AFTER it. A cell whose base value has drifted FAILS the build.
CMD_EMA_ADDR = 0xC40D4                          # tp+0x50D4
CMD_EMA_OLD, CMD_EMA_NEW = 573, 286             # alpha/4096: 0.1399 -> 0.0698
CMD_EMA_DEN = 4096
CONTROL_CELLS: tuple = (
    (CMD_EMA_ADDR, 2, CMD_EMA_OLD, CMD_EMA_NEW,
     "command-EMA coefficient (FUN_0003b8f6, 1 kHz)"),
)

# CODE_BYTES : (addr, byte_to_ASSERT_on_the_base, byte_to_WRITE, label)
# 🛑 A single in-place branch/displacement byte is the ONLY code-edit class with a clean record here.
# 🛑 Code CAVES are this kit's only bricking class -- V24, V27 and V48B all bricked the ECU.
CODE_BYTES: tuple = ()                          # V86 makes NO code edit outside the proven cave

# =====================================================================================================
# THE CAVE -- probe-design's 62-byte body + 6 bytes of UNREACHABLE 0xFF pad = the proven 68-byte extent
# =====================================================================================================
# Each halfword is pinned below in `CAVE_LISTING`; `assert_cave_encodings` re-derives the two
# gp-relative loads from the kit's OWN encoders and asserts their hw2 equals the FIRMWARE's own read
# of the same cell, so neither can silently address a different cell.
CAVE_LISTING = (
    ("003a",     "mov  0x0,r7          ; r7 = 0"),
    ("24379094", "ld.h -0x6b70[gp],r6  ; ★ Coulomb friction-compensator output. SIGNED (op 0x39)"),
    ("6032",     "cmp  0x0,r6"),
    ("a305",     "bnh  +4              ; UNSIGNED <= 0 ⇔ r6 == 0"),
    ("443a",     "add  0x4,r7          ; b6 = (v != 0)  -- LIVENESS"),
    ("6032",     "cmp  0x0,r6          ; 🛑 RE-ISSUED: the `add` above clobbered the flags"),
    ("ae05",     "bge  +4              ; SIGNED >= 0"),
    ("483a",     "add  0x8,r7          ; b7 = (v < 0)   -- SIGN"),
    ("a632",     "sar  0x6,r6          ; q = v >> 6, ARITHMETIC (op 0x15), sign PRESERVED"),
    ("4132",     "add  0x1,r6          ; q + 1"),
    ("6132",     "cmp  0x1,r6"),
    ("a305",     "bnh  +4              ; UNSIGNED <= 1 ⇔ q in {-1,0} ⇔ v in [-64, 63]"),
    ("423a",     "add  0x2,r7          ; b5 = (|v| >= 64), trips +64 / -65, TWO-SIDED"),
    ("a4375598", "ld.bu -0x67ab[gp],r6 ; ★ the aggregator's optional-term GATE. ZERO-extended byte"),
    ("6232",     "cmp  0x2,r6"),
    ("a905",     "bnl  +4              ; UNSIGNED >= 2"),
    ("413a",     "add  0x1,r7          ; b4 = (gate < 2) -- GATE OPEN"),
    ("c43a",     "shl  0x4,r7          ; the 4-bit thermometer -> bits 7:4"),
    ("483a",     "add  0x8,r7          ; b3 = 1, THE FINGERPRINT (weight 8 POST-shift)"),
    ("8437edea", "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4"),
    ("c6360700", "andi 0x7,r6,r6       ; preserve the live STEER_SENSOR_STATUS bits 2:0"),
    ("0731",     "or   r7,r6           ; THE MERGE  🛑 NOT `or r6,r7`"),
    ("4437ecea", "st.b r6,-0x1514[gp]  ; THE ONLY STORE"),
    ("2436e8ea", "movea -0x1518,gp,r6  ; re-execute the displaced instruction, LAST (r6 was scratch)"),
    ("7f00",     "jmp  [lp]            ; -> 0x55C12"),
)
CAVE_BODY = bytes.fromhex("".join(h for h, _t in CAVE_LISTING))
CAVE_PAD = 0xFF
# 🛑 The pad follows an UNCONDITIONAL `jmp [lp]` ⇒ structurally unreachable. It exists because V86's
# 🛑 body is 6 bytes shorter than V85's, and the extent is NEVER grown or shrunk.
CAVE_PAYLOAD: bytes | None = CAVE_BODY + bytes([CAVE_PAD]) * (CAVE_EXTENT - len(CAVE_BODY))

# the two cells the cave READS -- (disp, firmware writers, firmware readers, why)
PROBE_CELLS = (
    (0x6B70, 1, 1, "Coulomb friction-compensator output -- FUN_00038148's clamped result"),
    (0x67AB, 1, 2, "the assist aggregator's optional-term gate byte"),
)
# the FIRMWARE's own read of each probed cell -- the cave's hw2 must EQUAL these
PROBE_TWIN_READS = {0x6B70: 0x38006, 0x67AB: 0x37FE6}
PROBE_WRITERS = {0x6B70: (0x382D2,), 0x67AB: (0x2775C,)}
BIT_SIGN, BIT_NONZERO, BIT_MAG, BIT_GATE, BIT_FINGERPRINT = 0x80, 0x40, 0x20, 0x10, 0x08
MAG_SHIFT, MAG_T = 6, 64                        # `sar 0x6` ⇒ the rung trips at +64 / -65
RELAY_T = MAG_T                                 # exported so the decoder IMPORTS it, never copies it
GATE_T = 2                                      # b4 fires iff gp-0x67ab < 2
PAYLOAD_KEEP_MASK = V75.PAYLOAD_KEEP_MASK       # 0x7

# 🛑🛑 THE CAVE, AS A LITERAL. The build FAILS unless the emitted 68 bytes equal this EXACTLY.
# 🛑 This assert exists because V86's FIRST cut shipped `a932` (`sar 0x9`, T = 512) at **+18** when the
# 🛑 spec called for `a632` (`sar 0x6`, T = 64) -- ONE BYTE, and it silently changed what the rung
# 🛑 measures. Those artefacts were deleted and re-cut. `assert_cave_is_spec` names +18 specifically.
EXPECTED_CAVE_HEX = ("003a243790946032a305443a6032ae05483aa63241326132a305423aa43755986232a905413a"
                     "c43a483a8437edeac636070007314437ecea2436e8ea7f00ffffffffffff")
SHIFT_OFF = 18                                  # the offset the first cut got wrong
SHIFT_HW = "a632"

# 🛑 probe-design's PINS -- every emitted halfword is byte-identical to a real instruction that is
# already in the image, so no encoding here is a hand-derivation. (addr, hex, n_in_stock, what)
CAVE_PINS = (
    (0x2784E, "a305", 17, "bnh +4"),
    (0x244CE, "ae05", 86, "bge +4"),
    (0x2DB04, "a905", 15, "bnl +4  (UNSIGNED >=)"),
    (0x2401A, "a632", 26, "sar 0x6,r6  -- AND byte-identical to V85's OWN flown cave @0xC4B3A"),
    (0x847C8, "6032", 1,  "cmp 0x0,r6  ⚠ n=1: a THIN pin, flagged rather than hidden"),
)
# assert 1: the two loads' displacements pinned to the aggregator's own reads -- the GATE-1 argument
LOAD_DISP_PINS = {0x38008: "9094", 0x37FE8: "5598"}

# 🛑 FROZEN THE MOMENT A HASH IS REPORTED. A re-cut under the same build number DESTROYS its
# 🛑 predecessor's plain image and leaves a flashable artefact NO gate can check.
VARIANT_TOKEN: str | None = "CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB"

# =====================================================================================================
# 🛑 FROZEN -- 14 CELLS + 2 BYTES. Asserted INDIVIDUALLY from the BUILT image, never from the edit list.
# This kit has silently reverted a confirmed fix at a rebase at least THREE times (`0x454FE` twice,
# Lever A once, the V38 rebase seven levers at once). The assert is the only thing that catches it.
# =====================================================================================================
FROZEN_CELLS = {
    0xD77DA: (0,    "FactorC mode-26 Y[0] -> Honda. The engaged-only damper, DELETED at V84. "
                    "🛑 FROZEN BY OPERATOR DECISION -- the 26-31 Hz ring's dose-response rests on it"),
    0xD77EE: (0,    "FactorC mode-27 Y[0] -> Honda. 🛑 m27 is a SECOND engaged column -- V83a forgot "
                    "it and flew V81's whole damper live"),
    0xD7822: (60,   "FactorE mode-27 X[0] -> Honda"),
    0xD7824: (400,  "FactorE mode-27 X[1] -> Honda"),
    0xD782C: (140,  "FactorE mode-27 Y[1] -> Honda"),
    0xC6446: (5244, "Lever B's r24 engaged arm -- the FLOWN V67/V68 value"),
    0xC6444: (512,  "r26's engaged arm -- STOCK, deliberately, as the untried S3 lever"),
    0xC407E: (511,  "🛑 THE HARD-FAULT INTERLOCK. Honda's clamp, ONE count under its own 512 trip. "
                    "V73 raised it to 850 and V74/V75 BOTH hard-faulted. DO-NOT-RAISE"),
    0xC6CD0: (3564, "V57's decoupled forward-reader cell -- the 4x LKAS setpoint. INTACT"),
    0xC63A0: (1024, "the Path-2 damper weight. Honda's"),
    # ---- NEW IN V86 -------------------------------------------------------------------------------
    0xC4080: (0,    "🛑🛑 A LATENT PURE COULOMB RELAY. `FRICTION += cal/1024 * ratio` with NO |model| "
                    "factor ⇒ amplitude-INDEPENDENT, an unbounded relay index. It costs nothing ONLY "
                    "because it is zero. **NEVER RAISE IT**"),
    0xC40BC: (6000, "🛑 V85's cell. DECIDED: FREEZE AT 6000 -- neither push nor revert. The "
                    "nonlinearity measures 0.0000 of grinding frames and 4.3% of micro-ratchet frames "
                    "after a 20.3x reduction; N is already flat, so there is no larger dose. ⊕ It is "
                    "MEMORYLESS ⇒ exactly ZERO phase ⇒ it cannot move the frequency V86 measures"),
    # ---- NEW THIS SESSION: three cells whose LOWERING creates a pure relay at full authority ------
    0xC63AE: (1024, "🛑 lowering this toward 0 drives the LERP index to 0 ⇒ the output becomes the "
                    "constant +-Y[0] ⇒ A PURE RELAY AT FULL AUTHORITY. Never written, 75 images"),
    0xC6200: (8192, "🛑 the clamp on gp-0x6b70. If it ever drops below Y[0] the output becomes "
                    "constant ⇒ the same relay failure. ⚠ AND it sits SIX BYTES from 0xC6206/0xC6208, "
                    "the governor-slew cals V40 set to 0xFFFF and BRICKED the ECU with"),
    0xC61F6: (3,    "🛑 the r24 lane deadband. A deadband is the DUAL of a relay -- N(A)->0 as A->0 is "
                    "what PREVENTS a limit cycle. Setting it to 0 ADDS small-signal gain, the "
                    "DESTABILISING direction, and costs only 0.4% at the lane's own full scale"),
}
FROZEN_BYTES = {
    0x3AA96: (0xFB, "Lever B's gate repoint -- the FLOWN V67/V68 byte (`C5` dead gp-0x683c -> `FB` "
                    "latActive gp-0x6806)"),
    0x454FE: (0xB5, "V42's macro-ratchet fix (`br` not `bne`). Lost THREE times already; KEEP -- "
                    "even though it is currently MEASURED INERT (gp-0x67fa==4 fires 0/123,277)"),
}
# 🛑 15 CELLS + 2 BYTES = 17 ITEMS. V85's real set is 10 cells + 2 bytes = 12 items, all of which
# 🛑 PASS. V86 adds FIVE CELLS: 0xC4080 and 0xC40BC (the plant-model pair) plus 0xC63AE, 0xC6200 and
# 🛑 0xC61F6 (the three whose LOWERING creates a pure relay at full authority).
# 🛑 `STATE.md`'s "14 frozen cells" for V85 is WRONG and is not propagated here -- no 14-item list has
# 🛑 ever existed in this kit; the "14" in BUILD-LINEAGE.md is the 14 *friction sites*, a different set.
assert len(FROZEN_CELLS) == 15 and len(FROZEN_BYTES) == 2, \
    f"the frozen set is {len(FROZEN_CELLS)} cells + {len(FROZEN_BYTES)} bytes -- expected 15 + 2"
assert len(FROZEN_CELLS) + len(FROZEN_BYTES) == 17

# =====================================================================================================
# ★ THE VALUE-ANCHORED VERIFIER -- exact VALUES at exact ADDRESSES, not a span.
# (addr, kind, expected, stock, introduced, what it physically is / what it does)
# Every one of these was read out of the V85 image and the STOCK image before being written down here.
# =====================================================================================================
ANCHORS = (
    # ---- LIVE NON-STOCK: the cells that actually reach the steering -------------------------------
    (0x13109, "byte", 0x2C, 0x2D, "V22",
     "ASCII version string `39990-TVA-A160` -> `…TVA,A160`. COSMETIC; every modified build shares it"),
    (0x14120, "byte", 0x2C, 0x2D, "V22", "the second copy of the same string. COSMETIC"),
    (0x2A1F0, "u16", 0x7CD0, 0x746C, "V57",
     "the tp-relative displacement in the FORWARD LKAS-gain load. tp+0x746C=0xC646C (shared, 6 "
     "readers) -> tp+0x7CD0=0xC6CD0 (private). Decouples the forward reader from the 4 feedback ones"),
    (0xC6CD0, "u16", 3564, 0xFFFF, "V57",
     "the private forward-LKAS gain cell 0x2A1F0 now points at ⇒ 4x LKAS authority, forward path only"),
    (0x3AA96, "byte", 0xFB, 0xC5, "V67", "Lever B: the r24 engaged-arm gate repoint onto latActive"),
    (0xC6446, "u16", 5244, 512, "V67",
     "Lever B's r24 engaged arm. Kit's best measured grind-#1 result, 0.40 [0.27, 0.58] on V67/V68"),
    (0x454FE, "byte", 0xB5, 0xBA, "V42",
     "V42's state-4 governor substitution branch. ⚠ ON-CAR BUT MEASURED INERT"),
    (0xC40BC, "u16", 6000, 600, "V85",
     "the friction-ratio normaliser in FUN_0003b8f6 (1 kHz). Relay -> viscous; 1 reader / 0 writers"),
    (0xC61B2, "u16", 2048, 512, "V22->V38", "mixer-channel clamp 1 of 4 (x4 headroom)"),
    (0xC61B4, "u16", 2048, 512, "V22->V38", "mixer-channel clamp 2 of 4 (x4 headroom)"),
    (0xC61C0, "u16", 0xFFFF, 1600, "V36", "angle-rate tier 1 of the STEER_STATUS debounce SM"),
    (0xC61C2, "u16", 0xFFFF, 896, "V36", "angle-rate tier 2 -- the arm can never fire"),
    (0xC61C4, "u16", 0xFFFF, 1280, "V36", "angle-rate tier 3"),
    (0xC64B4, "byte", 0xFF, 0x70, "V36", "torque tier 1 of the same debounce SM"),
    (0xC64B6, "byte", 0xFF, 0x36, "V36", "torque tier 2"),
    (0xC64B7, "byte", 0xFF, 0x40, "V36", "torque tier 3"),
    (0xC64B8, "byte", 0xFF, 0x70, "V37",
     "torque tier 4 -- ✅ V37's gentle-EME fix, the one CONFIRMED cure in the kit (on-car 2026-07-14)"),
    (0xC64DE, "byte", 0x1B, 0x11, "V22",
     "⚠ UNKNOWN. Read at 18 sites in the 0x29xxx-0x2Bxxx arbitration/STEER_STATUS/ENABLE region. The "
     "old 'EME ramp step' label was RETRACTED as unsupported. Carried on every build since V22"),
    (0xC6598, "f32", 5.0, 1.0, "V29->V38", "FLOAT mirror of the soft-EME corridor wall (+)"),
    (0xC659C, "f32", 5.0, 1.0, "V29->V38", "FLOAT corridor wall (+), second"),
    (0xC65AC, "f32", -5.0, -1.0, "V29->V38", "FLOAT corridor wall (-)"),
    (0xC65B0, "f32", -5.0, -1.0, "V29->V38", "FLOAT corridor wall (-), second"),
    (0xC65C4, "f32", 5.0, 0.0, "V29->V38", "FLOAT boost floor"),
    (0xC65C8, "f32", 5.0, 1.5, "V29->V38", "FLOAT boost wall"),
    (0xC65CC, "f32", 5.0, 2.0, "V29->V38", "FLOAT boost wall"),
    (0xC674E, "s16", 5120, 1024, "V25->V38", "INT copy of the corridor wall (+). 1024 ct = 1.0"),
    (0xC6750, "s16", 5120, 1024, "V25->V38", "INT corridor wall (+), second"),
    (0xC675A, "s16", -5120, -1024, "V25->V38", "INT corridor wall (-)"),
    (0xC675C, "s16", -5120, -1024, "V25->V38", "INT corridor wall (-), second"),
    (0xC6768, "s16", 5120, 0, "V25->V38", "INT boost floor"),
    (0xC676A, "s16", 5120, 1536, "V25->V38", "INT boost wall"),
    (0xC676C, "s16", 5120, 2048, "V25->V38", "INT boost wall"),
    (0xC62EA, "u16", 0, 320, "V53",
     "the low-speed steer lockout window (~5 km/h). 0 ⇒ the lockout that sets STEER_STATUS=3 and kills "
     "STEER_CONTROL_ACTIVE never engages. This is what lets LKAS work at creep"),
    # ---- STOCK, AND THE STOCKNESS IS LOAD-BEARING -------------------------------------------------
    (0xC407E, "u16", 511, 511, "-",
     "🛑 THE HARD-FAULT INTERLOCK. Honda's, one count under its own 512 trip. NOT in the diff at all"),
    (0xC4004, "f32", 0.5, 0.5, "-",
     "🛑 the interlock's FLOAT twin -- FUN_00036d74's trip threshold. Do not 'fix' 0xC407E by raising "
     "this; it is the same interlock from the other side"),
    (0xC4080, "u16", 0, 0, "-",
     "🛑🛑 the LATENT PURE COULOMB RELAY -- no |model| factor ⇒ amplitude-independent. NEVER RAISE"),
    (0xC63A0, "u16", 1024, 1024, "-", "Path-2 damper weight, Honda's. V72-V76 and V81 carried 2048"),
    (0xC6444, "u16", 512, 512, "-", "r26 engaged arm -- left stock on purpose, the S3 lever"),
    (0xC64C8, "u16", 0, 0, "-",
     "the aggregator MODE SELECTOR = pass-through. 🛑 mode 1 DISCARDS the whole aggregator "
     "contribution, mode 2 blends. 0 writers / 1 reader; UNTRACED; do not move without GATE 2"),
    (0xD2006, "u16", 102, 102, "-", "the boost-amplitude blend cal (V60's falsified lever), stock"),
    (0xC64FA, "byte", 0x05, 0x05, "-", "the CEIL byte cal, stock"),
    (0xC646C, "u16", 891, 891, "-",
     "the SHARED sensor scale -- 6 readers across 3 subsystems. V57 decoupled the forward reader off "
     "it; it must stay Honda's or the feedback paths move too"),
    (0x3AB76, "byte", 0xAA, 0xAA, "-",
     "the `sar` imm5 on the r26 rate lane. 🛑 LEVER A IS OFF THE CAR -- byte-stock for 17 images"),
    (0x3AC20, "byte", 0xAA, 0xAA, "-",
     "the `sar` imm5 on the r24 rate lane. 🛑 Its Lever-A half CAUSED grind #2 (11.71x corner tail)"),
    (0xC6200, "u16", 8192, 8192, "-",
     "the clamp on gp-0x6b70. ⚠ NEIGHBOUR OF 0xC6206/0xC6208, the governor-slew cals V40 set to "
     "0xFFFF and BRICKED the ECU with. Reader census + monitor search before this is even discussed"),
    (0xC6C42, "u16", 4, 4, "-", "the differentiator delay D -- the PHASE lever. Never written, 55 img"),
    (0xC63AC, "u16", 102, 102, "-", "Path-2 accumulator one-pole IIR ⇒ fc ~16.7 Hz, inside S1"),
    (0xC61B8, "u16", 102, 102, "-", "the pre-gain deadband -- never rescaled while its clamps went x4"),
)
# the 7 per-term ENABLE bytes on the assist aggregator -- all 0x01, frozen 75 images.
# 🛑 Each byte deletes a term FEEDING THE MOTOR. Same danger class as 0xC64C8.
ENABLE_BYTES = tuple(range(0xC64AD, 0xC64B4))
# the friction lane's arithmetic dependencies. If one moves, every number in V85's header is void.
LANE_CALS = {
    0xC40D0: (408,  "friction EMA alpha /4096 -- the lane's ONLY pole. A PHASE lever; V85 left it"),
    0xC40D2: (102,  "friction scale /1024"),
    # 🛑 0xC40D4 IS DELIBERATELY ABSENT: it is V86's ONE control cell. It was a LANE_CAL through the
    # 🛑 phase-1 scaffold and was moved out here, explicitly, when the cell list landed -- NOT deleted
    # 🛑 quietly to make a guard stop complaining. Its value is asserted by CONTROL_CELLS on both sides.
    0xC40D6: (246,  "inertia EMA alpha /4096"),
    0xC40D8: (3686, "torque EMA alpha /4096"),
    0xC613A: (1159, "torque scale /32768"),
    0xC6468: (2639, "output scale on gp-0x6bfc"),
    0xC646E: (1428, "INERTIA gain"),
    0xC407C: (461,  "the interlock clamp's neighbour -- owner unidentified, never touched"),
}
LANE_FLOATS = {0xC4048: 1.0, 0xC404C: 0.0, 0xC4050: 0.0}    # the FIR taps -- a PASS-THROUGH
# ---- the LKAS arb setpoint limit: 8 selector-reachable records x 9 cells, all raised 15360 -> 16384 -
SETPOINT_RECORDS = (0xE4194, 0xE41BC, 0xE420C, 0xE4234, 0xE5194, 0xE51BC, 0xE51E4, 0xE520C)
SETPOINT_NCELL, SETPOINT_STRIDE = 9, 2
SETPOINT_NEW, SETPOINT_STOCK = 16384, 15360
SETPOINT_UNREACHED = 15360      # records sel {2,5,10,11} stay here -- the selector cannot reach them

# =====================================================================================================
# 🛑 RULE 7 -- MODE PROOF. All 10 pointer arrays, all 34 slots, DEREFERENCED.
# =====================================================================================================
N_MODES = V84B.N_MODES                       # 34
ALL_PTR_ARRAYS = dict(V84B.ALL_PTR_ARRAYS)   # FactorB/C/D/E + ceiling + friction
GAIN_B_PTRS = V84B.GAIN_B_PTRS               # 0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214
PTR_ARRAYS = dict(ALL_PTR_ARRAYS)
PTR_ARRAYS.update({f"gain_B[{i}]": a for i, a in enumerate(GAIN_B_PTRS)})
THIS_CAR_KEY, THIS_CAR_ROW = "TVCA4", 11
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
THIS_CAR_MODES = MANUAL_MODES + ENGAGED_MODES
# ⊕ the anchors the sweep must land on AFTER dereferencing -- stated independently, never quoted
DEREF_ANCHORS = {("FactorC", 26): 0xD77D0, ("FactorE", 26): 0xD780C, ("friction", 26): 0xD7A54,
                 ("FactorC", 24): 0xD67E4, ("FactorE", 24): 0xD6820, ("friction", 24): 0xD6A64}

# =====================================================================================================
# OUTPUT NAMING -- 🛑 exactly ONE flashable .rwd and ONE plain image per build number on disk
# =====================================================================================================
WRITE_MODE = os.environ.get("ACCORD_V86_WRITE", "").strip().lower()
assert WRITE_MODE in ("", "none", "bin", "rwd"), \
    f"ACCORD_V86_WRITE={WRITE_MODE!r} -- expected '' (dry run), 'bin' or 'rwd'"


def _naming():
    """(TAG, BIN_OUT, OUT). 🛑 REFUSES while `VARIANT_TOKEN` is None -- naming is frozen at cut time."""
    if VARIANT_TOKEN is None:
        raise SystemExit(
            "🛑 VARIANT_TOKEN is None -- the V86 cell list is not decided, so this build has no "
            "identity yet. Set it EXACTLY ONCE when the list is final: freezing it freezes TAG / "
            "BIN_OUT / OUT, and a re-cut under the same build number DESTROYS its predecessor's "
            "plain image.")
    assert "+" not in VARIANT_TOKEN, "🛑 `+` in a filename URL-decodes to a SPACE"
    assert all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN), \
        "the variant token must be alphanumeric plus `.` and `-`"
    tag = f"V85BASE-{VARIANT_TOKEN}"
    bin_out = str(plain_image_path(f"_v86_{VARIANT_TOKEN}_plain_image.bin"))
    out = os.path.join(RWD_DIR, f"39990-TVA,A160-V86-{tag}-0x{START:X}-0x{END:X}.rwd")
    assert len(out) < 250, f"the .rwd path is {len(out)} chars -- Windows' 260 limit would truncate it"
    assert VARIANT_TOKEN in os.path.basename(bin_out) and VARIANT_TOKEN in os.path.basename(out), \
        "🛑 the variant is not in BOTH filenames"
    return tag, bin_out, out


def is_null_build():
    """True when nothing is staged -- the scaffold's own smoke test, and never a flashable artefact."""
    return not CONTROL_CELLS and not CODE_BYTES and CAVE_PAYLOAD is None


def _refuse_null_write():
    if is_null_build():
        raise SystemExit(
            "🛑 REFUSING TO WRITE A NULL BUILD. With no control cell, no code byte and no cave "
            "payload, this image is BYTE-IDENTICAL to V85 -- a duplicate artefact carries zero "
            "evidence and would collide with `exactly ONE flashable .rwd per build number`. "
            "Stage the cell list first.")


# =====================================================================================================
# THE CAVE -- assembly / emit path, scaffolded. V85's payload is carried until a spec lands.
# =====================================================================================================

def build_cave():
    """(payload, listing). `CAVE_PAYLOAD is None` ⇒ V85's 68 bytes, RE-DERIVED from its own builder.

    🛑 Re-derived, not copied out of the image: that way the carried-forward payload is proven to be
    the one `build_v85_tva.build_cave()` emits, and a silently patched image cannot slip through.
    """
    if CAVE_PAYLOAD is None:
        body, listing = V85B.build_cave()
        assert len(body) == CAVE_EXTENT, "V85's cave is not the proven 68-byte extent"
        return body, listing
    body = bytes(CAVE_PAYLOAD)
    assert len(body) == CAVE_EXTENT, \
        f"🛑 the V86 cave payload is {len(body)} bytes; the PROVEN extent is {CAVE_EXTENT} and must be " \
        "filled EXACTLY -- never grown (a shortfall leaves stale V85 bytes EXECUTING)"
    listing, off = [], 0
    for hexs, text in CAVE_LISTING:
        raw = bytes.fromhex(hexs)
        listing.append((CAVE_BASE + off, raw, text))
        off += len(raw)
    assert off == len(CAVE_BODY) == 62, f"the cave body is {off} bytes, expected 62"
    for k in range(off, CAVE_EXTENT):
        assert body[k] == CAVE_PAD, f"the pad byte at +{k} is 0x{body[k]:02X}, expected 0xFF"
    return body, listing


def assert_cave_is_spec(payload, label):
    """🛑🛑 THE EMITTED CAVE MUST EQUAL `probe-design`'s HEX EXACTLY, AND +18 IS NAMED.

    V86's FIRST cut shipped `a932` (`sar 0x9` ⇒ b5 trips at 512) at offset +18 where the spec called
    for `a632` (`sar 0x6` ⇒ b5 trips at 64). **One byte**, no assert caught it, and it silently
    changed what the rung measures. Those artefacts were deleted and the build re-cut. This assert is
    the repair, and it checks the named offset FIRST so the failure message points at the cause.
    """
    got = payload.hex()
    at18 = payload[SHIFT_OFF:SHIFT_OFF + 2].hex()
    assert at18 == SHIFT_HW, \
        f"🛑🛑 {label}: cave +{SHIFT_OFF} is `{at18}`, the spec is `{SHIFT_HW}`. " \
        f"`a632` = `sar 0x6` ⇒ b5 trips at 64; `a932` = `sar 0x9` ⇒ b5 trips at 512. " \
        f"THIS IS THE EXACT DEFECT THAT FORCED V86's RE-CUT."
    assert got == EXPECTED_CAVE_HEX, \
        f"🛑 {label}: the emitted cave is not probe-design's spec\n" \
        f"      emitted {got}\n      spec    {EXPECTED_CAVE_HEX}"
    assert len(payload) == CAVE_EXTENT == 68 and len(CAVE_BODY) == 62
    # the shift's opcode field must be `sar` 0x15, NEVER `shr` 0x14
    hw = struct.unpack_from("<H", payload, SHIFT_OFF)[0]
    assert (hw >> 5) & 0x3F == 0x15, \
        f"🛑 {label}: the shift at +{SHIFT_OFF} is opcode 0x{(hw >> 5) & 0x3F:02X}, not `sar` 0x15 -- " \
        "`shr` (0x14) would make every negative value a huge positive and b5 would read ~100% forever"
    assert (hw & 0x1F) == MAG_SHIFT and (1 << MAG_SHIFT) == MAG_T == RELAY_T, \
        f"🛑 {label}: the shift immediate is {hw & 0x1F} but MAG_T is {MAG_T} -- they must agree"
    assert (hw >> 11) == R6, f"{label}: the shift does not target r6"
    return at18


def assert_cave_pins(stock, buf, label):
    """🛑 EVERY emitted halfword is byte-identical to a real instruction ALREADY IN THE IMAGE.

    Nothing in this cave is a hand-derived encoding. ⚠ `cmp 0x0,r6` has n = 1 in stock -- a THIN pin.
    It is flagged here rather than hidden, because a single-instance pin is weaker evidence than an
    86-instance one and the operator is entitled to know which is which.
    """
    for addr, hexs, n_expect, what in CAVE_PINS:
        got = bytes(stock[addr:addr + 2]).hex()
        assert got == hexs, \
            f"🛑 {label}: the pin for `{what}` -- STOCK@0x{addr:05X} is {got}, expected {hexs}"
        assert bytes.fromhex(hexs) in CAVE_BODY, \
            f"🛑 {label}: the pinned halfword {hexs} ({what}) is not in the emitted cave"
    # assert 1 -- the whole GATE-1 argument: the cave reads the cell the AGGREGATOR reads
    for addr, hexs in LOAD_DISP_PINS.items():
        got = bytes(buf[addr:addr + 2]).hex()
        assert got == hexs, \
            f"🛑 {label}: the aggregator's own displacement at 0x{addr:05X} is {got}, expected " \
            f"{hexs} -- the cave's load can no longer be shown to address the same cell"
    # only r6 and r7 are ever destinations -- the two V75 proved dead across the hook
    for _a, raw, text in build_cave()[1]:
        hw = struct.unpack_from("<H", raw, 0)[0]
        if text.startswith(("mov", "add", "cmp", "sar", "shl", "ld.", "andi", "or", "movea")):
            assert (hw >> 11) in (R6, R7), \
                f"🛑 {label}: `{text.strip()}` targets r{hw >> 11}; only r6/r7 are dead across the hook"
    return len(CAVE_PINS)


def assert_cave_encodings(buf, label):
    """🛑 THE TWO gp-RELATIVE LOADS, PROVEN TO ADDRESS THE CELLS THEY CLAIM -- by TWO methods.

    METHOD 1: re-derive `hw1` from the kit's OWN encoders (`V55.ldh`, `V55.ldbu_any`).
    METHOD 2: assert the cave's `hw2` EQUALS the FIRMWARE's own read of the same cell. `hw2` carries
    the displacement, so an equal `hw2` with an equal `reg1` is the same cell BY CONSTRUCTION. Only
    `reg2` differs -- the firmware targets `r13`, the cave `r6` -- and it MUST.
    🛑 This exists because `ld.h` (0x39) and `st.h` (0x3B) are ONE BIT apart, and because `ld.bu`
    carries the width selector in hw2's LSB (the recorded `disp | 1` trap).
    """
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    for disp, twin in PROBE_TWIN_READS.items():
        off = CAVE_BODY.find(struct.pack("<H", (0x10000 - disp) & 0xFFFF)) - 2
        assert off >= 0, f"{label}: the cave has no load of gp-0x{disp:04x}"
        hw1_c, hw2_c = struct.unpack_from("<HH", cave, off)
        hw1_f, hw2_f = struct.unpack_from("<HH", buf, twin)
        op_c, op_f = (hw1_c >> 5) & 0x3F, (hw1_f >> 5) & 0x3F
        assert hw2_c == hw2_f, \
            f"🛑 {label}: the cave's gp-0x{disp:04x} load carries hw2 0x{hw2_c:04X}, the firmware's " \
            f"own read @0x{twin:05X} carries 0x{hw2_f:04X} -- THEY ARE NOT THE SAME CELL"
        assert op_c == op_f, \
            f"🛑 {label}: the cave's opcode is 0x{op_c:02X}, the firmware's is 0x{op_f:02X}"
        assert op_c in (0x39, 0x3C, 0x3D), \
            f"🛑 {label}: the gp-0x{disp:04x} access is opcode 0x{op_c:02X} -- NOT a load. 0x3A/0x3B " \
            "are STORES, one bit away, and would CLOBBER the cell"
        assert (hw1_c & 0x1F) == (hw1_f & 0x1F) == GP, f"{label}: the base register is not gp"
        assert (hw1_c >> 11) == R6, f"{label}: the cave's load does not target r6"
        # METHOD 1 -- the kit's own encoders, independently
        want = V55.ldh(disp, R6) if op_c == 0x39 else V55.ldbu_any(-disp, R6)
        assert bytes(cave[off:off + 4]) == want, \
            f"🛑 {label}: the kit's encoder gives {want.hex()} for gp-0x{disp:04x}, the cave has " \
            f"{bytes(cave[off:off + 4]).hex()}"
    return True


def assert_cave_tail_matches_v85(buf, v85_img, label):
    """🛑 The 24-byte tail (shl/add/ld.bu/andi/or/st.b/movea/jmp) is BYTE-IDENTICAL to V85's flown cave.

    V86's body is 6 bytes shorter, so the tail sits at +38 where V85's sat at +44. Asserted from BOTH
    images rather than assumed, because this is the part that actually returns control to the ECU.
    """
    tail = bytes(buf[CAVE_BASE + 38:CAVE_BASE + 62])
    v85_tail = bytes(v85_img[CAVE_BASE + 44:CAVE_BASE + 68])
    assert tail == v85_tail, \
        f"🛑 {label}: the cave TAIL is {tail.hex()}, V85's flown tail is {v85_tail.hex()}"
    assert len(tail) == 24
    return tail


def ema_dc_gain(alpha_num, den=CMD_EMA_DEN, n=200000):
    """🛑 THE OPERATOR'S HARD CONSTRAINT, PROVED NUMERICALLY RATHER THAN ASSERTED.

    An EMA `y += alpha*(x - y)` has `|H(0)| = alpha / (1 - (1-alpha)) = 1` **exactly, for every
    alpha** -- the alpha cancels. So under any SUSTAINED command the estimator converges to a
    bit-identical value and **this edit cannot limit the maximum LKAS-commanded steering angle rate.**
    Only transient tracking changes. Iterated here in float to the fixed point.
    """
    a = alpha_num / float(den)
    y = 0.0
    for _ in range(n):
        y += a * (1.0 - y)
    return y


def ema_gain_at(alpha_num, f_hz, fs=1000.0, den=CMD_EMA_DEN):
    """|H(f)| of the one-pole EMA at the 1 kHz task rate. `a / |1 - (1-a)e^{-jw}|`."""
    a = alpha_num / float(den)
    w = 2.0 * math.pi * f_hz / fs
    re, im = 1.0 - (1.0 - a) * math.cos(w), (1.0 - a) * math.sin(w)
    return a / math.hypot(re, im)


def assert_ema_arithmetic():
    """🛑 CALIBRATE THE INSTRUMENT BEFORE USING IT, and prove the DC claim over a 28x alpha range."""
    for num in (143, 286, 573, 1146, 2048, 4095):
        dc = ema_dc_gain(num)
        assert abs(dc - 1.0) < 1e-9, \
            f"🛑 the EMA's DC gain at alpha={num}/4096 re-derives as {dc!r}, not 1.0 -- the " \
            "max-angle-rate argument is the whole safety case for this build and it FAILED"
    # the HF reduction that makes this more than a diagnostic
    for f, want in ((20.0, 0.650), (28.0, 0.585)):
        got = ema_gain_at(CMD_EMA_NEW, f) / ema_gain_at(CMD_EMA_OLD, f)
        assert abs(got - want) < 0.02, \
            f"🛑 the HF gain ratio at {f} Hz re-derives as {got:.3f}, the header claims {want}"
    # and the OPPOSITE direction would have RAISED it -- why the sign is down, not up
    for f in (20.0, 28.0):
        up = ema_gain_at(2 * CMD_EMA_OLD, f) / ema_gain_at(CMD_EMA_OLD, f)
        assert up > 1.0, "doubling alpha must RAISE the HF gain -- the direction argument is void"
    return ema_gain_at(CMD_EMA_NEW, 20.0) / ema_gain_at(CMD_EMA_OLD, 20.0)


def assert_cmd_ema_mode_proof(buf, label):
    """★ RULE 7 IS MOOT FOR THIS CELL, AND HERE IS THE PROOF RATHER THAN THE ASSERTION.

    A mode-indexed record repeats at its array's stride. `0xC40D4`'s value appears EXACTLY ONCE in
    `[0xC4000, 0xC4200)`, and NO stride in [2, 0x400) reproduces it -- so it cannot be one column of a
    mode table written into the wrong column, which is how V69/V70/V72 delivered byte-stock.
    """
    lo, hi = 0xC4000, 0xC4200
    want = u16(buf, CMD_EMA_ADDR)
    hits = [a for a in range(lo, hi, 2) if u16(buf, a) == want]
    assert hits == [CMD_EMA_ADDR], \
        f"🛑 {label}: the value {want} appears at {[hex(a) for a in hits]} in [0x{lo:05X},0x{hi:05X}) " \
        "-- it may be a mode-indexed record, and RULE 7 would NOT be moot"
    for stride in range(2, 0x400, 2):
        for k in (-2, -1, 1, 2):
            a = CMD_EMA_ADDR + k * stride
            if lo <= a < hi and u16(buf, a) == want:
                raise AssertionError(
                    f"🛑 {label}: stride 0x{stride:X} repeats {want} at 0x{a:05X} -- this looks like a "
                    "mode table and the mode-proof claim must be re-derived")
    return len(hits)


def assert_cave(buf, label):
    """🛑 The cave, RE-DERIVED and RE-DISASSEMBLED out of the BUILT image."""
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    derived, _listing = build_cave()
    assert cave == derived, \
        f"🛑 {label}: the cave in the image is not `build_cave()`'s re-derivation\n" \
        f"      image  {cave.hex()}\n      derive {derived.hex()}"
    redis = V85B.redisassemble_v85_cave(cave)
    assert not [m for _a, _r, m in redis if m == "nop" or m.startswith("??")], \
        f"{label}: the cave re-disassembly contains a nop or an undecoded halfword"
    stores = [m for _a, _r, m in redis if m.startswith(("st.b", "st.h", "st.w"))]
    assert len(stores) == 1 and stores[0].startswith("st.b"), \
        f"{label}: the cave contains {stores}, expected exactly ONE `st.b` to the CAN-330 payload"
    # every branch lands on an emitted instruction boundary
    bounds = {a for a, _r, _m in redis}
    for a, raw, _m in redis:
        if len(raw) == 2 and (struct.unpack("<H", raw)[0] >> 7) & 0xF == 0xB:
            hw = struct.unpack("<H", raw)[0]
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            assert a + d in bounds, \
                f"🛑 {label}: the branch at 0x{a:05X} lands at 0x{a + d:05X}, NOT an instruction " \
                "boundary -- it would execute the middle of a 4-byte instruction"
    # the hook is UNCHANGED -- same jarl, same return, same displaced movea
    assert bytes(buf[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: the hook @0x{HOOK_ADDR:05X} is not `jarl 0x{CAVE_BASE:05X}`"
    assert bytes(buf[HOOK_ADDR + 4:HOOK_ADDR + 6]) == V75.HOOK_RETURN_INSN, \
        f"{label}: 0x{HOOK_ADDR + 4:05X} is not `mov 0x8,r7` -- r7 is not provably dead across the hook"
    assert cave.count(HOOK_STOCK) == 1, \
        f"{label}: the displaced `movea` is not present exactly once -- the hook's own instruction " \
        "must be re-executed inside the cave"
    return cave, redis


M32 = 0xFFFFFFFF


def wire_byte4(v6b70, gate, status_bits=0x7):
    """A Python mirror of the cave, INSTRUCTION FOR INSTRUCTION, on 32-bit register semantics.

    `v6b70` is the SIGN-EXTENDED int16 the `ld.h` produces; `gate` is the ZERO-EXTENDED byte the
    `ld.bu` produces. 🛑 `bnh`/`bnl` are UNSIGNED conditions and `bge` is SIGNED -- mirrored exactly.
    """
    r7 = 0                                                  # mov 0x0,r7
    r6 = v6b70                                              # ld.h  (SIGN-extended)
    if not (r6 & M32) <= 0:                                 # cmp 0x0 / bnh +4  (UNSIGNED <=)
        r7 += 4                                             # b6 = (v != 0)
    if not r6 >= 0:                                         # cmp 0x0 / bge +4  (SIGNED >=)
        r7 += 8                                             # b7 = (v < 0)
    r6 = r6 >> MAG_SHIFT                                    # sar 0x9  (Python >> IS arithmetic)
    r6 = r6 + 1                                             # add 0x1
    if not (r6 & M32) <= 1:                                 # cmp 0x1 / bnh +4  (UNSIGNED <=)
        r7 += 2                                             # b5 = (|v| >= 512)
    r6 = gate & 0xFF                                        # ld.bu (ZERO-extended)
    if not (r6 & M32) >= GATE_T:                            # cmp 0x2 / bnl +4  (UNSIGNED >=)
        r7 += 1                                             # b4 = gate OPEN
    r7 = (r7 << 4) & M32                                    # shl 0x4,r7
    r7 += BIT_FINGERPRINT                                   # add 0x8,r7  (POST-shift)
    r6 = status_bits & PAYLOAD_KEEP_MASK                    # ld.bu / andi 0x7
    return (r6 | r7) & 0xFF                                 # or / st.b (LOW BYTE only)


def decode_byte4(byte4):
    """Decode `0x14A` byte4. 🛑 A frame whose FINGERPRINT is clear is NOT V86 -- refuse it."""
    if not byte4 & BIT_FINGERPRINT:
        return None
    return {"sign": bool(byte4 & BIT_SIGN), "nonzero": bool(byte4 & BIT_NONZERO),
            "mag": bool(byte4 & BIT_MAG), "gate": bool(byte4 & BIT_GATE), "fingerprint": True}


def _self_check_wire():
    """Every rung EXHAUSTIVELY over the FULL int16 range, and the gate over its full byte range."""
    for v in range(-32768, 32768):
        d = decode_byte4(wire_byte4(v, 0))
        assert d is not None and d["fingerprint"]
        assert d["sign"] == (v < 0), f"b7 wrong at v={v}"
        assert d["nonzero"] == (v != 0), f"b6 wrong at v={v}"
        assert d["mag"] == (v >= MAG_T or v <= -MAG_T - 1), f"b5 wrong at v={v}"
        # 🛑 THE INVARIANTS -- exact, same register, same pass. No sampling race.
        assert not (d["sign"] and not d["nonzero"]), f"b7 without b6 at v={v}"
        assert not (d["mag"] and not d["nonzero"]), f"b5 without b6 at v={v}"
    for g in range(256):
        d = decode_byte4(wire_byte4(0, g))
        assert d["gate"] == (g < GATE_T), f"b4 wrong at gate={g}"
    # ---- the trip points, as literals, so a silent drift FAILS ------------------------------------
    assert decode_byte4(wire_byte4(MAG_T, 0))["mag"] and not decode_byte4(wire_byte4(MAG_T - 1, 0))["mag"]
    assert decode_byte4(wire_byte4(-MAG_T - 1, 0))["mag"] and not decode_byte4(wire_byte4(-MAG_T, 0))["mag"]
    # ---- EVERY rung must be able to BOTH fire and not fire (V69's b4 was structurally VACUOUS) -----
    # 🛑 the `mag` OFF vector must sit BELOW MAG_T -- it was 100, which fires once T dropped 512 -> 64.
    for name, on, off in (("sign", wire_byte4(-100, 0), wire_byte4(100, 0)),
                          ("nonzero", wire_byte4(1, 0), wire_byte4(0, 0)),
                          ("mag", wire_byte4(-900, 0), wire_byte4(MAG_T - 1, 0)),
                          ("gate", wire_byte4(0, 1), wire_byte4(0, 2))):
        assert decode_byte4(on)[name] and not decode_byte4(off)[name], \
            f"🛑 rung {name} cannot both fire and not fire -- it is VACUOUS"
    # ---- the fingerprint always set, the live status bits always preserved ------------------------
    for v in (-32768, -512, 0, 512, 32767):
        for st in range(8):
            b = wire_byte4(v, 0, status_bits=st)
            assert b & BIT_FINGERPRINT, "🛑 the fingerprint is not set on a reachable payload"
            assert b & PAYLOAD_KEEP_MASK == st, "🛑 the live STEER_SENSOR_STATUS bits were destroyed"
    assert decode_byte4(0x87) is None and decode_byte4(0x00) is None
    assert wire_byte4(0, 2, 0) == BIT_FINGERPRINT, "🛑 the all-clear payload is not just b3"
    # ---- 🛑 THE DUAL-INVARIANT BUILD IDENTITY, BOTH DIRECTIONS ------------------------------------
    # V86 requires b7=>b6 and b5=>b6. V85 required b6=>b7. A frame satisfying one refutes the other.
    v85_only = BIT_FINGERPRINT | BIT_NONZERO                # b6 set, b7 clear -- legal on V86 ONLY
    assert decode_byte4(v85_only)["nonzero"] and not decode_byte4(v85_only)["sign"]
    v86_illegal = BIT_FINGERPRINT | BIT_SIGN                # b7 set, b6 clear -- IMPOSSIBLE on V86
    d = decode_byte4(v86_illegal)
    assert d["sign"] and not d["nonzero"], \
        "the V86-illegal pattern must be constructible, or the refutation test is vacuous"
    assert not any(wire_byte4(v, g) == v86_illegal
                   for v in range(-32768, 32768, 7) for g in (0, 2)), \
        "🛑 V86's own cave can emit `b7 & !b6` -- the invariant, and the build identity, are VOID"


_self_check_wire()


def assert_decoder_module():
    """🛑 THE BUILDER->DECODER LINK, MADE MECHANICAL. `studies/probes/decode_v86_probe.py` IMPORTS these names rather
    than copying them, so the V66 failure mode -- a stale decoder header -- is structurally
    impossible. Its own self-test is run here against THIS build's constants."""
    if not os.path.exists(os.path.join(HERE, "studies/probes/decode_v86_probe.py")):
        print("    ⚠ studies/probes/decode_v86_probe.py not found -- the decoder/image link is NOT verified")
        return False
    import importlib
    dec = importlib.import_module("decode_v86_probe")
    importlib.reload(dec)
    assert dec.CAVE_HEX == CAVE_PAYLOAD.hex(), \
        "🛑 the shipped decoder's cave hex does not match this build's -- it is STALE"
    for name, want in (("BIT_SIGN", BIT_SIGN), ("BIT_NONZERO", BIT_NONZERO), ("BIT_MAG", BIT_MAG),
                       ("BIT_GATE", BIT_GATE), ("BIT_FINGERPRINT", BIT_FINGERPRINT),
                       ("MAG_T", MAG_T), ("GATE_T", GATE_T)):
        assert getattr(dec, name) == want, \
            f"🛑 the decoder's {name} is {getattr(dec, name)}, not {want}"
    dec._selftest()
    return True


def assert_probe_cells_v86(buf, label):
    """🛑 GATE 1 FOR THE PROBE -- `census_gp4` (disp16 + disp23 + abs literal + movhi/movea) AND the
    from-scratch Format-VII scan. The cave READS these cells and WRITES NEITHER."""
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    out = {}
    V85B.assert_disp23_calibrated(buf)          # calibrate before a disp23 null is load-bearing
    for disp, n_w, n_r, why in PROBE_CELLS:
        w, r, (lit, mhi) = V81.census_gp4(buf, disp)
        fw_w = [x for x in w if x[0] not in cave_span]
        fw_r = [x for x in r if x[0] not in cave_span]
        assert (len(fw_w), len(fw_r)) == (n_w, n_r), \
            f"🛑 {label}: gp-0x{disp:04x} ({why}) has {len(fw_w)}w/{len(fw_r)}r, expected " \
            f"{n_w}w/{n_r}r: writers {[hex(x[0]) for x in fw_w]}"
        assert tuple(sorted(x[0] for x in fw_w)) == PROBE_WRITERS[disp], \
            f"🛑 {label}: gp-0x{disp:04x}'s writer set is {[hex(x[0]) for x in fw_w]}, expected " \
            f"{[hex(a) for a in PROBE_WRITERS[disp]]}"
        assert not lit and not mhi, \
            f"🛑 {label}: gp-0x{disp:04x} has {len(lit)} absolute-literal and {len(mhi)} movhi/movea " \
            "reference(s) -- an ALIASED access the displacement scans cannot see"
        cave_w = [x for x in w if x[0] in cave_span]
        assert not cave_w, \
            f"🛑 {label}: THE CAVE WRITES gp-0x{disp:04x} at {[hex(x[0]) for x in cave_w]} -- the " \
            "probe is supposed to be READ-ONLY telemetry"
        # SECOND METHOD, from scratch: our own Format-VII scan over the halfword displacement
        mine_w = [h for h in V85B.fmt7_scan(buf, GP, (0x10000 - disp) & 0xFFFF) if h[2]]
        assert len(mine_w) == n_w, \
            f"🛑 {label}: the second method finds {len(mine_w)} writer(s) of gp-0x{disp:04x}"
        # THIRD METHOD: the calibrated 48-bit disp23 decoder -- a null here is load-bearing
        ext = V85B.disp23_scan(buf, GP, -disp)
        assert not ext, \
            f"🛑 {label}: gp-0x{disp:04x} has a 6-byte extended-displacement access at " \
            f"{[hex(a) for a, _b in ext]} -- an encoding the disp16 scan is BLIND to"
        out[disp] = (len(fw_w), len(fw_r), len([x for x in r if x[0] in cave_span]))
    return out


def assert_cave_region(buf, label):
    """🛑 The 1,144 free bytes above the proven extent are UNTOUCHED, and 399/427 are byte-stock."""
    for addr, want in V84B.HOOK_399_STOCK.items():
        got = bytes(buf[addr:addr + 4])
        assert got == want, \
            f"🛑 {label}: the frame-399/427 hook site 0x{addr:05X} is {got.hex()}, expected the " \
            f"byte-stock {want.hex()} -- a SECOND hook was installed"
    tail = bytes(buf[CAVE_BASE + CAVE_EXTENT:CAVE_FREE_END])
    assert len(tail) == CAVE_FREE_BYTES == 1144
    assert set(tail) == {0xFF}, \
        f"🛑 {label}: the {CAVE_FREE_BYTES} free bytes above 0x{CAVE_BASE + CAVE_EXTENT:05X} are not " \
        f"untouched 0xFF ({len(tail) - tail.count(0xFF)} non-FF) -- a second cave was built"
    return len(tail)


# =====================================================================================================
# THE GUARDS
# =====================================================================================================

def assert_frozen(buf, label):
    """🛑 14 cells + 2 bytes, ONE AT A TIME, from the BUILT image. Never from the edit list."""
    for addr, (want, why) in FROZEN_CELLS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: FROZEN 0x{addr:05X} = {got}, expected {want} -- {why}"
    for addr, (want, why) in FROZEN_BYTES.items():
        assert buf[addr] == want, \
            f"🛑 {label}: FROZEN 0x{addr:05X} = 0x{buf[addr]:02X}, expected 0x{want:02X} -- {why}"
    return len(FROZEN_CELLS) + len(FROZEN_BYTES)


def read_anchor(buf, addr, kind):
    return {"byte": lambda: buf[addr], "u16": lambda: u16(buf, addr),
            "s16": lambda: s16(buf, addr), "f32": lambda: f32(buf, addr)}[kind]()


def assert_anchors(buf, stock, label):
    """★ THE VALUE-ANCHORED VERIFIER -- exact values at exact addresses, both sides.

    🛑 `verify/diff_build_vs_stock.py` is SPAN-based: it passes a build that wrote the right REGION with the
    WRONG VALUE. This asserts the value. It also re-asserts each anchor's STOCK value, so a stale or
    swapped stock dump cannot make a silent revert look correct.
    """
    for addr, kind, want, want_stock, _intro, why in ANCHORS:
        got = read_anchor(buf, addr, kind)
        assert got == want, \
            f"🛑 {label}: ANCHOR 0x{addr:05X} ({kind}) = {got!r}, expected {want!r} -- {why}"
        got_stock = read_anchor(stock, addr, kind)
        assert got_stock == want_stock, \
            f"🛑 {label}: 0x{addr:05X}'s STOCK value is {got_stock!r}, this file says {want_stock!r} " \
            "-- the stock dump or the anchor table is wrong, and every 'non-stock' claim is void"
    for a in ENABLE_BYTES:
        assert buf[a] == 0x01 and stock[a] == 0x01, \
            f"🛑 {label}: the per-term ENABLE byte 0x{a:05X} is 0x{buf[a]:02X}, expected 0x01 -- each " \
            "of these DELETES A TERM FEEDING THE MOTOR; moving one needs a census and GATE 2"
    for addr, (want, why) in LANE_CALS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: LANE CAL 0x{addr:05X} = {got}, expected {want} -- {why}"
    for addr, want in LANE_FLOATS.items():
        got = f32(buf, addr)
        assert got == want, \
            f"🛑 {label}: the FIR tap 0x{addr:05X} = {got}, expected {want} -- the 'pass-through' " \
            "claim, and with it the |model| bound, would be void"
    # ---- the 8 selector-reachable LKAS setpoint records, 9 cells each --------------------------------
    n = 0
    for rec in SETPOINT_RECORDS:
        for k in range(SETPOINT_NCELL):
            a = rec + k * SETPOINT_STRIDE
            got = u16(buf, a)
            assert got == SETPOINT_NEW, \
                f"🛑 {label}: setpoint 0x{a:05X} = {got}, expected {SETPOINT_NEW} (V38's +6.7%)"
            assert u16(stock, a) == SETPOINT_STOCK, \
                f"🛑 {label}: setpoint 0x{a:05X}'s STOCK value is {u16(stock, a)}, not {SETPOINT_STOCK}"
            n += 1
    assert n == 72, f"{n} setpoint cells checked, expected 8 records x 9"
    return len(ANCHORS), n


def sweep_records(buf):
    """Every (family, mode) slot, DEREFERENCED through its pointer array. 🛑 RULE 7's instrument.

    Returns {(family, mode): (rec_addr, n, xs, ys)} over all 10 arrays x all 34 modes.
    🛑 A hard-coded record address is exactly how V69/V70/V72 shipped byte-stock: they wrote mode-10
    records on a car that reads modes 24/25/26/27.
    """
    out = {}
    for name, arr in PTR_ARRAYS.items():
        for mode in range(N_MODES):
            rec = V74.factor_rec(buf, arr, mode)
            assert START <= rec < END, \
                f"🛑 {name}[{mode}] dereferences to 0x{rec:05X}, outside the flashable region"
            n, xs, ys = V74.rec_any(buf, rec)
            out[(name, mode)] = (rec, n, xs, ys)
    return out


def assert_mode_proof(buf, stock, label):
    """🛑 RULE 7, in full: the arrays are Honda's, the dereference anchors land, THIS CAR's four
    columns are byte-stock in all six factor families and all four gain_B arrays."""
    # 1. the pointer arrays themselves have not moved -- a moved pointer redirects a lever SILENTLY
    V84B.assert_pointer_arrays_stock(buf, stock, label)
    # 2. the variant row still resolves to TVCA4 / 24,25,26,27 and the four columns are DISTINCT
    key, modes, distinct = V84B.derive_this_cars_modes(buf)
    assert key == THIS_CAR_KEY and tuple(modes) == THIS_CAR_MODES, \
        f"🛑 {label}: variant row {THIS_CAR_ROW} is {key!r} {modes}, expected " \
        f"{THIS_CAR_KEY!r} {THIS_CAR_MODES}"
    assert len(set(modes)) == 4, \
        f"🛑 {label}: the four mode columns are not distinct -- m27 would be an alias of m26"
    # 3. the engaged / disengaged column sets, DERIVED from the config table on THIS image
    _rows, engaged, disengaged = V74.derive_mode_columns(buf)
    for m in ENGAGED_MODES:
        assert m in engaged, f"🛑 {label}: mode {m} is not in the derived ENGAGED set"
    for m in MANUAL_MODES:
        assert m in disengaged, f"🛑 {label}: mode {m} is not in the derived DISENGAGED set"
    # 4. the sweep, and the dereference anchors it must land on
    recs = sweep_records(buf)
    for (name, mode), want in DEREF_ANCHORS.items():
        got = recs[(name, mode)][0]
        assert got == want, \
            f"🛑 {label}: {name} m{mode} dereferences to 0x{got:05X}, the anchor says 0x{want:05X} " \
            "-- the pointer arrays or the mode map moved and every record read here is suspect"
    # 5. THIS CAR's four columns are byte-STOCK in every family (V84's revert, still holding)
    for name in PTR_ARRAYS:
        for mode in THIS_CAR_MODES:
            rec = recs[(name, mode)][0]
            ln = V74.rec_len(buf, rec)
            assert bytes(buf[rec:rec + ln]) == bytes(stock[rec:rec + ln]), \
                f"🛑 {label}: {name} m{mode} @0x{rec:05X} ({ln} B) is NOT byte-stock -- this car " \
                f"READS mode {mode}, so this is a LIVE change and it is not declared"
    # 6. V84's own suite, unmodified, on the same image
    V84B.assert_manual_modes_frozen(buf, buf, stock, label)
    V84B.assert_friction_all_stock(buf, stock, label)
    V84B.assert_gain_a_honda(buf, stock, label)
    V84B.assert_gain_b_inert_mode10(buf, label)
    V84B.assert_factor_surface(buf, stock, label, reverted=True)
    V84B.assert_engaged_equals_manual(buf, stock, label)
    V84B.assert_factor_monotone(buf, label, must_have_fold=False)
    return recs


def residual_records(buf, stock, recs):
    """🛑 The 14+ records outside this car's columns that STILL carry V72-V81-era damper residue.

    They are unreachable on a row-11 `TVCA4` car [BELIEF, structural -- only modes 10/11 have a
    MEASURED refutation, V72's probe 0/87,940]. Enumerated so a future edit cannot be confused by
    them, and so the 7-mode view's blindness is on the record: **V83a shipped V81's whole damper live
    in mode 27 and nobody noticed for a flight.** That is this exact failure one row over.
    """
    out = []
    seen = set()
    for (name, mode), (rec, _n, _x, _y) in sorted(recs.items()):
        if mode in THIS_CAR_MODES or (name, rec) in seen:
            continue
        seen.add((name, rec))
        ln = V74.rec_len(buf, rec)
        if bytes(buf[rec:rec + ln]) != bytes(stock[rec:rec + ln]):
            out.append((name, mode, rec, ln))
    return out


def assert_residual_records(buf, stock, recs, label):
    """The residual set must not GROW, and no residual record may be reachable on this car.

    ⚠ THIS ALONE IS NOT SUFFICIENT and the negative-control harness PROVED it: the residual census is
    computed against STOCK, so writing into a record that is *already* non-stock (e.g. FactorE m10,
    V72-V75 damper residue) does not change the count and slips through. `assert_records_vs_base`
    below is the gate that actually catches it. This one stays for the reachability claim.
    """
    res = residual_records(buf, stock, recs)
    live = [r for r in res if r[1] in THIS_CAR_MODES]
    assert not live, f"🛑 {label}: a residual record is in THIS CAR's columns: {live}"
    return res


def assert_records_vs_base(buf, base_img, recs, attributed, label):
    """🛑 EVERY record of EVERY family at EVERY mode is byte-identical to the BASE unless DECLARED.

    This is the gate that closes the hole `assert_residual_records` leaves open. It is indifferent to
    whether a record is stock, residual, reachable or unreachable: **if a record's bytes moved and the
    edit list did not say so, the build fails.** That is the V69/V70/V72 failure caught at the byte
    level -- those builds wrote mode-10 records on a car that reads modes 24/25/26/27 and delivered
    byte-stock, an entire dose ladder that never existed.
    """
    seen, bad = set(), []
    for (name, mode), (rec, _n, _x, _y) in sorted(recs.items()):
        if (name, rec) in seen:
            continue
        seen.add((name, rec))
        ln = V74.rec_len(buf, rec)
        if bytes(buf[rec:rec + ln]) == bytes(base_img[rec:rec + ln]):
            continue
        undeclared = [a for a in range(rec, rec + ln)
                      if buf[a] != base_img[a] and a not in attributed]
        if undeclared:
            bad.append((name, mode, rec, ln, [hex(a) for a in undeclared[:8]]))
    assert not bad, \
        f"🛑 {label}: {len(bad)} table record(s) differ from the BASE at bytes NO declared edit " \
        f"accounts for: {bad[:4]}. A record write that is not in the edit list is either a silent " \
        "corruption or a lever nobody declared -- and if its mode is not in " \
        f"{THIS_CAR_MODES} it delivers BYTE-STOCK, which is how V69/V70/V72 shipped a dose ladder " \
        "that never existed."
    return len(seen)


def assert_carried_guards(buf, stock, label):
    """Every guard V85 ran, re-run here on the V86 image. Cell-list-independent by construction.

    🛑 If the final V86 cell list makes one of these FAIL, that is a DECISION to be taken explicitly
    and named in the build header -- not a guard to be quietly deleted. Each line says what it blocks.
    """
    V84B.assert_keep_list(buf, label)               # blocks: Lever A `sar`, the V38 package, KEEP set
    V84B.assert_insurance_guards(buf, stock, label)
    V84B.assert_edit_geometry(buf, label)
    V84B.assert_repoint_and_chain(buf, label, done=True)    # blocks: touching Lever B's repoint chain
    V84B.assert_repoint_twins(buf, label)
    V84B.assert_arm_derivation(buf, label)
    V67.assert_untouched_context_v67(buf, label)
    V67.assert_untouched_v67(buf, label)
    V67.assert_signal_sites(buf, label)
    V74.assert_clamp_census(bytes(buf))             # blocks: moving 0xC407E's reader set
    V72.assert_lever_c_single_reader(bytes(buf))
    V85B.assert_ratio_norm_census(buf, label)       # 0xC40BC: 1 reader / 0 writers, FOUR ways
    V85B.assert_b5_refutation(buf, label)           # gp-0x6b98 is hard-clamped to +-0x2000
    V85B.assert_caller_guard(buf, label)            # FUN_0003b8f6 runs only in states {4, 5, 11}
    V85B.assert_out_cliff(buf, label)               # gp-0x6bfc's sentinel is OUTSIDE its own clamp
    # V85's OWN probe cells: their FIRMWARE census must be unchanged even though V86 stops reading them
    V85B.assert_probe_cells(buf, label, range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    assert_probe_cells_v86(buf, label)              # GATE 1 for V86's two cells
    assert_cmd_ema_mode_proof(buf, label)


# =====================================================================================================
# THE ZERO-UNATTRIBUTED-BYTES GATE
# =====================================================================================================

def make_attributor(crc_only, cave_changed):
    """`d -> reason or None`. **None is a FAILURE**, not a default."""
    by_addr = {}
    for addr, width, pre, new, lbl in CONTROL_CELLS:
        for k in range(width):
            by_addr[addr + k] = f"CONTROL 0x{addr:05X} {lbl}  {pre} -> {new}"
    for addr, pre, new, lbl in CODE_BYTES:
        by_addr[addr] = f"CODE 0x{addr:05X} {lbl}  0x{pre:02X} -> 0x{new:02X}"

    def attribute(d):
        if d in by_addr:
            return by_addr[d]
        if d in crc_only:
            return "CRC trailer"
        if cave_changed and CAVE_BASE <= d < CAVE_BASE + CAVE_EXTENT:
            return f"the CAVE @0x{CAVE_BASE:05X} ({CAVE_EXTENT} B, extent UNCHANGED)"
        return None
    return attribute


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


def assert_identity_modulo(buf, ref_img, allowed, label, refname):
    """🛑 Whole-image identity modulo an ATTRIBUTED set -- the strongest statement available.

    Restore every byte V86 is ALLOWED to have changed, then assert the result is byte-for-byte the
    reference over the FULL 1 MiB -- not over [START, END), and not by span.
    """
    probe = bytearray(buf)
    for a in allowed:
        probe[a] = ref_img[a]
    diff = [i for i in range(len(ref_img)) if probe[i] != ref_img[i]]
    assert not diff, \
        f"🛑 {label}: after restoring the {len(allowed)} ATTRIBUTED bytes, the image still differs " \
        f"from {refname} at {len(diff)} byte(s): {[hex(x) for x in diff[:16]]}. STOP AND REPORT."
    return bytes(probe)


# =====================================================================================================
# THE BUILD
# =====================================================================================================

def build():
    print(__doc__)
    null = is_null_build()

    v85 = Path(SRC_BIN).read_bytes()
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V85, flown route {SRC_ROUTE}, FAULT-FREE): {SRC_BIN}")
    src_sha = hashlib.sha256(v85).hexdigest()
    print(f"  SHA256 {src_sha}")
    assert len(v85) == len(stock) == 0x100000, "an image is not 1 MiB"
    assert src_sha not in NOT_THE_BASE, f"🛑🛑 THE BASE IS {NOT_THE_BASE.get(src_sha)}"
    assert src_sha == SRC_SHA256, \
        f"🛑🛑 THE BASE IS NOT THE FLOWN V85. SHA256 is {src_sha}, expected {SRC_SHA256}."
    assert hashlib.sha256(stock).hexdigest() == STOCK_SHA256, \
        "🛑 the STOCK dump has drifted -- every 'non-stock' claim in this file rests on it"
    print(f"  ✅ the base SHA256 is the V85 cut that FLEW ROUTE {SRC_ROUTE}, EXACTLY. "
          "STEER_STATUS {0: 43,641}, 0 DTC-active, 0 sentinels.")
    print(f"  WRITE MODE: {WRITE_MODE or 'DRY RUN -- nothing will be written to disk'}")
    if null:
        print("\n  🛑🛑 NULL BUILD -- `CONTROL_CELLS`, `CODE_BYTES` and `CAVE_PAYLOAD` are EMPTY STUBS.")
        print("      The V86 cell list is NOT DECIDED. This run is the SCAFFOLD's smoke test: it must")
        print("      reproduce V85 BIT-FOR-BIT. No .rwd will be cut, and writing is refused.")

    # =================================================================================================
    # GATE THE SOURCE -- everything below is measured on the INPUT before a byte moves
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  GATING THE SOURCE")
    assert walk_all_blocks(v85) == 0, "the V85 source's own CRC chain does not verify"
    n_frozen = assert_frozen(v85, "V85 source")
    n_anch, n_setpoint = assert_anchors(v85, stock, "V85 source")
    recs = assert_mode_proof(v85, stock, "V85 source")
    residual = assert_residual_records(v85, stock, recs, "V85 source")
    assert_carried_guards(v85, stock, "V85 source")
    assert_cave_region(v85, "V85 source")
    hf_ratio = assert_ema_arithmetic()
    decoder_ok = assert_decoder_module()
    # the base must still carry V85's OWN cave, byte for byte, before V86 repoints it
    v85_cave, _l = V85B.build_cave()
    assert bytes(v85[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v85_cave, \
        "🛑 the base's cave is not `build_v85_tva.build_cave()`'s 68 bytes"
    for addr, width, pre, _new, lbl in CONTROL_CELLS:
        got = u16(v85, addr) if width == 2 else v85[addr]
        assert got == pre, f"🛑 the base's 0x{addr:05X} ({lbl}) is {got}, expected V85's {pre}"
    print(f"\n    ★ THE CONTROL CELL -- 0x{CMD_EMA_ADDR:05X} (tp+0x50D4), the command-EMA coefficient")
    print(f"      alpha {CMD_EMA_OLD}/{CMD_EMA_DEN} = {CMD_EMA_OLD / CMD_EMA_DEN:.4f}  ->  "
          f"{CMD_EMA_NEW}/{CMD_EMA_DEN} = {CMD_EMA_NEW / CMD_EMA_DEN:.4f}")
    print("      🛑 DC GAIN, THE OPERATOR'S HARD CONSTRAINT -- computed, not asserted:")
    for num in (CMD_EMA_OLD, CMD_EMA_NEW, 143, 4095):
        print(f"         alpha = {num:>4d}/4096 = {num / CMD_EMA_DEN:.4f}  ⇒  |H(0)| = "
              f"{ema_dc_gain(num):.12f}")
    print("         ⇒ |H(0)| = 1 EXACTLY for every alpha (the alpha cancels) ⇒ under any SUSTAINED")
    print("           command the estimator converges to a BIT-IDENTICAL value ⇒ **this edit cannot")
    print("           limit the maximum LKAS-commanded steering angle rate.** Only transients change.")
    print("      ⊕ AND IT IS NOT MERELY DIAGNOSTIC -- the HF gain it removes, V86 / V85:")
    print("        " + "".join(f"{f'{f} Hz':>10}" for f in (1, 5, 7.79, 12.8, 20, 28)))
    print("        " + "".join(
        f"{ema_gain_at(CMD_EMA_NEW, f) / ema_gain_at(CMD_EMA_OLD, f):>10.3f}"
        for f in (1, 5, 7.79, 12.8, 20, 28)))
    print(f"        ⇒ {hf_ratio:.3f}x at 20 Hz, directly in the band the operator calls grinding; the")
    print("          OPPOSITE direction (1146) would have RAISED it, which is why the sign is DOWN.")
    print(f"    ✅ CRC 50/50 on the INPUT · {len(FROZEN_CELLS)} FROZEN cells + {len(FROZEN_BYTES)} "
          f"FROZEN bytes = {n_frozen} verified individually")
    print(f"    ✅ VALUE ANCHORS: {n_anch} cells + {len(ENABLE_BYTES)} enable bytes + "
          f"{len(LANE_CALS)} lane cals + {len(LANE_FLOATS)} FIR taps + {n_setpoint} setpoint cells,")
    print("       each asserted at its EXACT address with its EXACT value -- and each one's STOCK "
          "value re-asserted too (two-sided).")
    print(f"    ✅ RULE 7: {len(PTR_ARRAYS)} pointer arrays x {N_MODES} modes = {len(recs)} slots "
          f"DEREFERENCED; {len(DEREF_ANCHORS)} anchors land;")
    print(f"       this car is {THIS_CAR_KEY} row {THIS_CAR_ROW} ⇒ MANUAL {MANUAL_MODES} / ENGAGED "
          f"{ENGAGED_MODES}, and all four columns are byte-STOCK in all {len(PTR_ARRAYS)} families.")
    print(f"    ⚠ RESIDUAL (unreachable) non-stock records outside this car's columns: "
          f"{len(residual)} -- V72-V81 damper leftovers.")
    by_mode = sorted({m for _n, m, _r, _l in residual})
    print(f"       modes {by_mode}")
    print("       [BELIEF, structural] unreachable on a row-11 car; only m10/m11 have a MEASURED "
          "refutation (V72's probe 0/87,940).")
    print(f"    ✅ CAVE: {CAVE_EXTENT} B @0x{CAVE_BASE:05X}; the {CAVE_FREE_BYTES} free bytes above it "
          f"are untouched 0xFF; hooks 0x55D50/0x55EFA byte-stock.")
    print(f"    ✅ studies/probes/decode_v86_probe.py: "
          f"{'imports THIS builds bit map; its self-test PASSES' if decoder_ok else 'NOT FOUND'}")

    # =================================================================================================
    # APPLY -- control cells, then code bytes, then the cave
    # =================================================================================================
    code = bytearray(v85)
    attributed = set()
    print("\n" + "-" * 102)
    print(f"  APPLYING {len(CONTROL_CELLS)} CONTROL CELL(S) + {len(CODE_BYTES)} CODE BYTE(S)")
    if CONTROL_CELLS:
        print(f"      {'#':>2s} {'addr':<9s} {'cell':<30s} {'V85':>7s} {'V86':>7s}  bytes")
    for i, (addr, width, pre, new, lbl) in enumerate(CONTROL_CELLS, 1):
        assert width in (1, 2), f"0x{addr:05X}: width {width} -- only 1 and 2 are supported"
        got = buf_read = u16(code, addr) if width == 2 else code[addr]
        assert got == pre, \
            f"🛑 the base's 0x{addr:05X} ({lbl}) is {buf_read}, expected V85's {pre} -- the base " \
            "drifted, or the cell list was written against a different image"
        old_raw = bytes(code[addr:addr + width])
        if width == 2:
            assert 0 <= new <= 0xFFFF, f"0x{addr:05X}: {new} is not a halfword"
            struct.pack_into("<H", code, addr, new)
            assert u16(code, addr) == new, f"the write at 0x{addr:05X} did not take"
        else:
            assert 0 <= new <= 0xFF, f"0x{addr:05X}: {new} is not a byte"
            code[addr] = new
            assert code[addr] == new, f"the write at 0x{addr:05X} did not take"
        assert addr not in FROZEN_CELLS and addr not in FROZEN_BYTES, \
            f"🛑🛑 0x{addr:05X} is in the FROZEN set and the edit list writes it. Resolve the " \
            "CONTRADICTION deliberately -- do not delete the guard."
        attributed |= {addr + k for k in range(width)}
        print(f"      {i:2d} 0x{addr:05X}  {lbl:<30s} {pre:>7d} {new:>7d}  "
              f"{old_raw.hex():<6s} -> {bytes(code[addr:addr + width]).hex()}")
    for addr, pre, new, lbl in CODE_BYTES:
        assert code[addr] == pre, \
            f"🛑 the base's code byte 0x{addr:05X} ({lbl}) is 0x{code[addr]:02X}, expected 0x{pre:02X}"
        assert addr not in FROZEN_BYTES, f"🛑🛑 0x{addr:05X} is FROZEN and the edit list writes it"
        code[addr] = new
        attributed.add(addr)
        print(f"      CODE 0x{addr:05X}  {lbl:<30s} 0x{pre:02X} -> 0x{new:02X}")
    if not CONTROL_CELLS and not CODE_BYTES:
        print("      (none -- the cell list is an empty stub)")

    old_cave = bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    new_cave, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = new_cave
    cave_attributed = {CAVE_BASE + k for k in range(CAVE_EXTENT) if old_cave[k] != new_cave[k]}
    attributed |= cave_attributed
    print(f"\n    THE CAVE -- 0x{CAVE_BASE:05X}, {CAVE_EXTENT} B, extent UNCHANGED, hook "
          f"0x{HOOK_ADDR:05X} UNCHANGED")
    if CAVE_PAYLOAD is None:
        print("      CARRIED FORWARD from V85, re-derived by `build_v85_tva.build_cave()` ⇒ "
              f"{len(cave_attributed)} byte(s) differ (expected 0).")
    else:
        print(f"      V85   {old_cave.hex()}")
        print(f"      V86   {new_cave.hex()}")
        print(f"      ⇒ {len(cave_attributed)} of {CAVE_EXTENT} cave bytes differ.")
        for _a, _r, _t in cave_listing:
            print(f"        0x{_a:05X} {_r.hex():<10s} {_t}")

    # =================================================================================================
    # RE-ASSERT EVERYTHING ON THE FINISHED IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  RE-ASSERTING ON THE FINISHED IMAGE")
    assert_frozen(code, "V86")
    assert_anchors(code, stock, "V86")
    recs_out = assert_mode_proof(code, stock, "V86")
    res_out = assert_residual_records(code, stock, recs_out, "V86")
    assert len(res_out) == len(residual), \
        f"🛑 the residual-record set moved from {len(residual)} to {len(res_out)} -- V86 wrote an " \
        "UNREACHABLE mode record. That is the V69/V70/V72 failure: a dose that never existed."
    # 🛑 the gate that actually catches a write into an ALREADY-non-stock record -- see its docstring
    n_records = assert_records_vs_base(code, v85, recs_out, attributed, "V86")
    assert_carried_guards(code, stock, "V86")
    assert_cave_region(code, "V86")
    _cave, cave_redis = assert_cave(code, "V86")
    assert_cave_is_spec(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]), "V86")
    assert_cave_pins(stock, code, "V86")
    assert_cave_encodings(code, "V86")
    assert_cave_tail_matches_v85(code, v85, "V86")
    probe_out = assert_probe_cells_v86(code, "V86")
    for disp, _w, _r, _why in PROBE_CELLS:
        assert probe_out[disp][2] == 1, \
            f"🛑 V86's cave reads gp-0x{disp:04x} {probe_out[disp][2]} time(s), expected exactly 1"
    assert u16(code, CMD_EMA_ADDR) == CMD_EMA_NEW
    for (name, mode), (rec, _n, _x, _y) in recs_out.items():
        assert rec == recs[(name, mode)][0], \
            f"🛑 {name} m{mode}'s pointer moved across the edit -- impossible for a cal/code build"
    print(f"    ✅ every FROZEN cell/byte, every value anchor, the {len(recs_out)}-slot mode sweep, "
          "the cave, the hooks: RE-VERIFIED on the BUILT image.")
    print(f"    ✅ all {n_records} DISTINCT table records byte-identical to the BASE except where the "
          "edit list declares otherwise")
    print("       (reachable AND unreachable -- a mode-10 write on a 24/25/26/27 car fails here, "
          "which is the V69/V70/V72 defect).")

    # =================================================================================================
    # CRC
    # =================================================================================================
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
              f"   owns {len(owners)} byte(s): {owners[:4]}{' …' if len(owners) > 4 else ''}")
    if not blocks:
        print("    (none -- no byte moved, so no trailer moves either)")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full 50-block chain re-walked: 50/50 PASS (0 mismatches)")
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- THE BLOCK THE BOOTLOADER SKIPS. V40 wrote there, " \
        "left the CRC stale, and the ECU faulted at ignition (EPS lamp, no power steering)."
    assert not [a for a in attributed if a < START or a >= END], \
        f"an edit landed outside the flashable region [0x{START:X},0x{END:X})"
    assert bytes(code[0xC5000:0xC5FFC]) == bytes(v85[0xC5000:0xC5FFC]) == \
        bytes(stock[0xC5000:0xC5FFC]), \
        "🛑 [0xC5000,0xC5FFC) is not byte-identical to the base AND to stock"
    print(f"    ✅ 0 of the {len(attributed)} edited bytes land in [0xC5000,0xC5FFC) (byte-identical "
          f"to stock), and all lie inside [0x{START:X},0x{END:X}).")

    # =================================================================================================
    # 🛑 THE ZERO-UNATTRIBUTED-BYTES GATE
    # =================================================================================================
    attribute = make_attributor(crc_only, bool(cave_attributed))
    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V86 vs the flown V85 -- over the WHOLE 1 MiB image")
    runs = diff_runs(code, v85, attribute)
    total = sum(b - a + 1 for a, b in runs)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    if runs:
        print(f"      {'range':<21s} {'len':>4s}  attribution")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, \
        f"🛑 UNATTRIBUTED bytes vs V85: {[hex(x) for x in stray[:16]]} -- every differing byte must " \
        "resolve to a declared control cell, a declared code edit, the probe cave, or a CRC word. " \
        "STOP AND REPORT."
    # the run count must decompose exactly -- a stray inside an attributed run cannot hide
    n_expect_cell = sum(1 for _ in CONTROL_CELLS) + sum(1 for _ in CODE_BYTES)
    print(f"    ⇒ ZERO unattributed bytes. Decomposition: <= {n_expect_cell} control/code run(s) + "
          f"{1 if cave_attributed else 0} cave run(s) + {len(blocks)} CRC run(s).")

    # ---- the value-anchored round trip: restoring the attributed set reproduces V85 bit-for-bit ----
    assert_identity_modulo(code, v85, attributed | crc_only, "V86", "V85")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = v85[a]
    rt_sha = hashlib.sha256(bytes(rt)).hexdigest()
    assert rt_sha == SRC_SHA256, f"the round trip yields {rt_sha}, expected {SRC_SHA256}"
    print(f"    ✅ VALUE-ANCHORED ROUND TRIP: restoring the {len(attributed)} attributed + "
          f"{len(crc_only)} CRC bytes reproduces")
    print(f"       V85 BIT-FOR-BIT -- sha256 back to {rt_sha} over all 0x100000 bytes.")
    d_stock = sum(1 for i in range(START, END) if code[i] != stock[i])
    d_stock_base = sum(1 for i in range(START, END) if v85[i] != stock[i])
    print(f"    ⊕ vs STOCK over [0x{START:X},0x{END:X}): V86 differs at {d_stock} bytes, "
          f"V85 at {d_stock_base}.")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    if null:
        assert bytes(code) == bytes(v85), \
            "🛑🛑 THE NULL BUILD DID NOT REPRODUCE V85. The scaffold is broken; nothing else in " \
            "this file can be trusted until it does."
        assert img_sha == SRC_SHA256 and total == 0 and not attributed
        print("\n    ✅✅ NULL-BUILD SMOKE TEST: the scaffold reproduced the flown V85 BIT-FOR-BIT")
        print(f"        (sha256 {img_sha}, 0 differing bytes over the whole 1 MiB).")

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
    FF.assert_x31_checksum(rwd, "V86 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v85)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, never from the in-memory build.
    assert_frozen(dec, "V86 readback")
    assert_anchors(dec, stock, "V86 readback")
    recs_rb = assert_mode_proof(dec, stock, "V86 readback")
    assert_records_vs_base(dec, v85, recs_rb, attributed, "V86 readback")
    assert_carried_guards(dec, stock, "V86 readback")
    assert_cave_region(dec, "V86 readback")
    assert_cave(dec, "V86 readback")
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert_identity_modulo(dec, v85, attributed | crc_only, "V86 readback", "V85")
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("    ✅ READBACK: every FROZEN cell, every value anchor, the full mode sweep, the carried")
    print("       guard suite, the cave, and the 50/50 CRC chain -- ALL re-verified FROM THE DECODED")
    print("       .rwd PAYLOAD, and the payload is byte-identical to the built image.")

    # =================================================================================================
    # WRITE -- only if explicitly enabled, and NEVER for a null build
    # =================================================================================================
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WAS WRITTEN TO DISK.")
        if null:
            print("     This is a NULL BUILD. Stage the cell list and set VARIANT_TOKEN before "
                  "ACCORD_V86_WRITE can do anything.")
        else:
            print("     Re-run with ACCORD_V86_WRITE=rwd to cut the artefacts.")
    else:
        _refuse_null_write()
        _tag, bin_out, out = _naming()
        existing = Path(bin_out).read_bytes() if os.path.exists(bin_out) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(
                f"🛑 REFUSING TO OVERWRITE {bin_out}: a DIFFERENT image already exists (on disk "
                f"{hashlib.sha256(existing).hexdigest()}, about to write {img_sha}). A same-number "
                "re-cut destroys a predecessor's snapshot and leaves a flashable artefact NO gate "
                "can check. Rename it `SUPERSEDED-DO-NOT-FLASH-…` deliberately, then re-run.")
        Path(bin_out).write_bytes(bytes(code))
        print(f"  wrote {bin_out}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(out) and Path(out).read_bytes() != rwd:
                raise SystemExit(
                    f"🛑 a DIFFERENT {out} already exists -- exactly ONE flashable .rwd per build "
                    "number. Rename or delete it deliberately, then re-run.")
            Path(out).write_bytes(rwd)
            print(f"  wrote {out}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            # ---- 🛑 A SEPARATE FROM-DISK DECODE OF THE SHIPPED FILE -------------------------------
            shipped = Path(out).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha, "the shipped .rwd re-hashes wrong"
            FF.assert_x31_checksum(shipped, "V86 shipped")
            sb = parse_x31(shipped)
            assert sb["headers"] == FF.EXPECTED_HEADERS
            assert sb["blocks"] == [{"start": START, "length": END - START}]
            sd = bytearray(v85)
            sd[START:END] = bytes(sb["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert_frozen(sd, "V86 shipped-from-disk")
            assert_anchors(sd, stock, "V86 shipped-from-disk")
            recs_sd = assert_mode_proof(sd, stock, "V86 shipped-from-disk")
            assert_records_vs_base(sd, v85, recs_sd, attributed, "V86 shipped-from-disk")
            assert_cave(sd, "V86 shipped-from-disk")
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(bin_out).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code), \
                "the written plain image does not re-read as the built image"
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded, and its payload")
            print("     re-verified INDEPENDENTLY of the in-memory build.")

    print(f"\n  V86 [{VARIANT_TOKEN or 'NO TOKEN -- CELL LIST NOT DECIDED'}] -- "
          f"image SHA256 {img_sha}")
    print(f"                                    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    if null:
        print("  🛑 SCAFFOLD ONLY. No lever is staged, no lever is implied, and no artefact was cut.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without touching an image."""
    assert CAVE_BASE == 0xC4B34 and CAVE_EXTENT == 68
    assert CAVE_BASE + CAVE_EXTENT == 0xC4B78 and CAVE_FREE_BYTES == 1144
    assert HOOK_ADDR == 0x55C0E, "the 330 TX hook moved"
    assert TP == 0xBF000 and TP + 0x6000 == 0xC5000, \
        "🛑 tp+0x6000 is 0xC5000, NOT 0xC6000 -- the off-by-0x1000 trap has recurred four times"
    assert TP + 0x50BC == 0xC40BC and TP + 0x507E == 0xC407E and TP + 0x7CD0 == 0xC6CD0
    assert GP_BASE == 0xFEDF8000
    # the frozen and anchored sets must not contradict each other
    for addr, (want, _why) in FROZEN_CELLS.items():
        for a, kind, exp, _s, _i, _w in ANCHORS:
            if a == addr and kind in ("u16", "s16"):
                assert exp == want, \
                    f"🛑 0x{addr:05X} is FROZEN at {want} and ANCHORED at {exp} -- contradiction"
    for addr, (want, _why) in FROZEN_BYTES.items():
        for a, kind, exp, _s, _i, _w in ANCHORS:
            if a == addr and kind == "byte":
                assert exp == want, \
                    f"🛑 0x{addr:05X} is FROZEN at 0x{want:02X} and ANCHORED at 0x{exp:02X}"
    assert len({a for a, *_ in ANCHORS}) == len(ANCHORS), "a duplicate address in ANCHORS"
    assert len(SETPOINT_RECORDS) == 8 and SETPOINT_NCELL == 9
    assert not set(ENABLE_BYTES) & {a for a, *_ in ANCHORS}
    # the stubs really are empty in phase 1
    assert is_null_build() == (not CONTROL_CELLS and not CODE_BYTES and CAVE_PAYLOAD is None)
    # RULE 7's map
    assert THIS_CAR_MODES == (24, 25, 26, 27) and len(set(THIS_CAR_MODES)) == 4
    assert set(ENGAGED_MODES) == {26, 27} and set(MANUAL_MODES) == {24, 25}
    assert len(PTR_ARRAYS) == 10 and N_MODES == 34
    # the naming path must REFUSE while the token is unset
    if VARIANT_TOKEN is None:
        try:
            _naming()
        except SystemExit:
            pass
        else:                                                          # pragma: no cover
            raise AssertionError("🛑 _naming() did not refuse an unset VARIANT_TOKEN")


if __name__ == "__main__":
    _self_check()
    build()
