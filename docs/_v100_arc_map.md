# V100 arc map — cross-build cell matrix, V99 cumulative delta, and the V85→V99 classification

Written by the 2026-08-13 record-repair pass. **All numbers below are read from the
`_*_plain_image.bin` snapshots on disk** via `analysis-2020accord/ledger_v38_to_v99_bytes.py`
(new file this session, extends `ledger_v38_to_v98_bytes.py` by exactly one build, V99), **never
from the build scripts.** Reproduce with:
```
ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares
python analysis-2020accord/ledger_v38_to_v99_bytes.py            # everything
python analysis-2020accord/ledger_v38_to_v99_bytes.py frozen     # the matrix below (B2)
python analysis-2020accord/ledger_v38_to_v99_bytes.py delta      # the V99 cumulative table below (C)
```
89 build images load cleanly (V22..V99, V95 deliberately excluded as a burned number). Anchors pass:
stock `0xC646C == 891`, `code.bin[0x454FE] == 0xBA`, every image `len == 0x100000`.

---

## 1. CROSS-BUILD MATRIX — every load-bearing cell, frozen-count since V38

"N frozen" = how many consecutive build images (V22..V99, 89 total) have held V99's current value.
**N == 89 means the cell has never moved on any build.** Full 114-cell table is the `frozen` command's
output; the rows below are the ones that matter for a lever decision (moved at least once, or sit
right next to something that has).

| addr | N frozen | since | moves | stock | V99 | state | what |
|---|---|---|---|---|---|---|---|
| `0xC40BC` | **1** | V99 | 3 | 600 | **300** | NON-STOCK | Coulomb relay breakpoint (V85 first moved it 600→6000; **V99 is the first move in the other direction, into virgin range — only 600 and 6000 existed before**) |
| `0xC63AC` | 1 | V99 | 2 | 102 | 102 | **STOCK** | Stage-1 IIR alpha, ACTUAL arm (V97 moved 102→150; **V99 reverts it exactly to stock**) |
| `0x55DF2`/`0x55E10` | 4 | V96 | 5/4 | — | — | NON-STOCK | CAN-427 packer source + shift (telemetry only, not a control edit) |
| `0xD7A5C/5E/60` (m26 Y) | 4 | V96 | 7 | −9830/−5734/−1966 | −14745/−8601/−2949 | NON-STOCK | `0xCBE74` friction/damper dose, **frozen at ×1.5 since V96's revert-by-construction of V94's ×0.25/×0.5 cut** |
| `0xD7A6C/6E/70` (m27 Y) | 4 | V96 | 7 | same | same | NON-STOCK | same dose, mode 27 |
| `0xC40D2` | **10** | V89 | 1 | 102 | **204** | NON-STOCK | K1, modelled Coulomb friction (MODEL arm) — **frozen 10 builds, V89's own lever, never touched since** |
| `0x3AA96` / `0xC6446` | **11** | V88 | 9 | 0xC5 / 512 | 0xFB / **5244** | NON-STOCK | **Lever B** — the r24 engaged arm, frozen 11 builds since V88 restored it |
| `0xC40D4` | 13 | V86b | 2 | 573 | 573 | STOCK | observer torque IIR (V86 moved it 573→286, **reverted to stock by V87's V38 rebase, frozen there since**) |
| `0xC63A0` | 17 | V83a | 6 | 1024 | 1024 | STOCK | Path-2 lane weight w[0] (the damper lane) |
| `0x2A1F0` / `0xC6CD0` | 18 | V81 | 5 | −1 | **3564** | NON-STOCK | V57's private 4.000× forward LKAS gain — **frozen 18 builds, the excitation-scale lever, never revisited since V81 re-planted it** |
| `0xC62EA` | 18 | V81 | 5 | 320 | **0** | NON-STOCK | low-speed steer lockout window — **frozen at 0 (steer-to-zero) for 18 builds** |
| `0x454FE` | 19 | V80 | 11 | 0xBA | **0xB5** | NON-STOCK | V42's macro-ratchet fix (branch, not clamp) — frozen 19 builds |
| `0xC407E` | 21 | V78 | 4 | 511 | 511 | STOCK | hard-fault interlock clamp — **frozen at Honda's 511 for 21 builds**, the fix that let V91/V92/V96+ carry a ×1.5 friction dose without the V74/V75 hard-fault |
| `0xC6444` | 29 | V72 | 4 | 512 | 512 | STOCK | r26 engaged arm — Honda's value, **frozen 29 builds** (raising it flew once, as V71c, and is FALSIFIED — grind #2 came back) |

**Everything else in the SITES table (66 of 114 cells) sits at N = 89 — never moved on any build,
STOCK value.** That includes `0xC4080` (K0, the NEVER-RAISE relay hazard), `0xC63AE` (Stage-2 input
scale), `0xC6200` (the residual's output clamp), `0xC6468`/`0xC646C`/`0xC646E` (the model's shared
gains), and all four PID cells `0xC6AE6`/`0xC6B12`/`0xC6B26`. **These are the untouched perimeter of
the observer/PID structure — every V85→V99 edit has been inside it, never to it.**

⚠ **Known reader gaps, checked this session:**
- `_v67_plain_image.bin` and `_v70_plain_image.bin` **both exist on disk and both load** — the
  previously-recorded "misses `_v67_plain_image.bin`" loader bug did not reproduce against the
  current file set. Not re-litigated further; flagging that the bug as described did not fire here.
- **V70 was re-cut** (recorded, open, not re-verified this session) — its SHA is not trustworthy as
  an identity anchor. The image on disk loads and diffs cleanly, but **do not cite a V70 hash as
  proof of anything** without re-deriving it.
- No missing images in the V22..V99 chain; `packaging_mask` audit returns the same 12 "real edit, not
  packaging" bytes recorded before (`0x55C0F`, `0xC61C0..C5`, `0xC64B4..B8`).

---

## 2. V99's COMPLETE CUMULATIVE NON-STOCK DELTA — read from the image, not the build script

`image sha256 a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726` (independently
re-derived this session; matches the build handoff's stated hash). **313 differing bytes vs STOCK in
113 runs, ZERO unattributed** (every differing byte traces to a build present in the on-disk chain).

### CAVE / telemetry (does not change the control law) — 153 bytes
`0xC4B34-0xC4BCD` (153 B, first written V31p, carries every telemetry probe cave through V98's
comparator + V99's one identity byte). **Not a lever.**

### CRC / packaging — 20 bytes
5 per-4KiB block checksums (`0xC4FFC`, `0xC6FFC`, `0xD7FFC`, `0xE4FFC`, `0xE5FFC`) — a mechanical
consequence of the control-law and cave edits in those blocks, not a lever.

### CONTROL-LAW cells — 140 bytes, 39 named cells (composite table below)

| addr | width | stock | V99 | first build | what it physically is | what the change does | status |
|---|---|---|---|---|---|---|---|
| `0x13109`/`0x14120` | 1+1 | 0x2D | 0x2C | V22 | part-number ASCII (`-`→`,`) | cosmetic build marker, no control effect | inert |
| `0x2A1F0` | 2 | 29804 | 31952 | V57 | LKAS-forward displacement | repoints a load to read `0xC6CD0` (the private 4× gain below) | measured — scales EXCITATION, not loop gain ([[accord-4x-lkas-gain-is-the-frozen-variable]]) |
| `0xC6CD0` | 2 | −1 (unset) | **3564** | V57 | V57's private forward LKAS gain | **4.000× the LKAS command amplitude reaching the loop** (feedback path un-boosted) | measured on multiple flights; NEVER recommend lowering — it is not the culprit ([[accord-4x-lkas-gain-is-the-frozen-variable]]) |
| `0x3AA96` | 1 | 0xC5 | **0xFB** | V67/V88 | Lever B gate byte | switches the gate source from a dead cell to `latActive` (`gp-0x6806`) | **measured FIX component** — V88 flight: grinding operator-reported fixed, 15–22 Hz command down to 0.549× |
| `0xC6446` | 2 | 512 | **5244** | V67/V88 | r24 engaged arm — Lever B's dose | 2.000× the LERP while LKAS applies | same as above, the other half of Lever B |
| `0x454FE` | 1 | 0xBA | **0xB5** | V42/V80 | branch opcode (bne→br) | V42's macro-ratchet fix; unconditional restore | measured fix for the macro-ratchet symptom, carried since V42, currently frozen at V80's re-plant |
| `0x55C0E` | 4 | (hook absent) | jarl to cave | V31p | the `0x14A` cave call site | invokes the telemetry cave every 100 Hz frame | instrument infrastructure |
| `0x55DF2` | 2 | 37864 | 38032 | V87 | CAN-427 packer source | which `gp` cell CAN ID `0x1AB` reports | telemetry only |
| `0x55E10` | 1 | 0xA3 | 0xA6 | V92 | CAN-427 packer shift | `sar` amount on the 427 payload (no-clip fix) | telemetry only |
| `0xC40BC` | 2 | 600 | **300** | V85/**V99** | Coulomb relay breakpoint, `FUN_0003b8f6` | halves the friction relay's rate knee (10.61→5.31 °/s); compounds with K1 to a 4.00× Honda dose below 5.31 °/s | **THE V99 LEVER — retracted as a fix same-session, before it flew (see §3 below)** |
| `0xC40D2` | 2 | 102 | **204** | V89 | K1, modelled Coulomb friction (MODEL arm) | 2.000× the plant-model's modelled friction | measured direction (more modelled friction = lighter wheel, [[accord-friction-polarity-more-friction-is-more-assist]]); gate-role is BELIEF |
| `0xC61B2`/`0xC61B4` | 2+2 | 512/512 | **2048/2048** | V22 | arbitration / LKAS-gain output clamps | widens the pre-boost ceiling | frozen since V22, carried unexamined this arc |
| `0xC61C0-C4` | 6 | 1600/896/1280 | **65535×3** | V36 | gentle-EME debounce RATE thresholds | effectively disables the rate-based debounce leg | frozen since V36 (pre-V38) |
| `0xC62EA` | 2 | 320 | **0** | V53/V81 | low-speed steer lockout window | steer-to-zero instead of a ~5 km/h lockout | frozen since V81 |
| `0xC64B4`/`B6` | 2+2 | 24688/16438 | **65535/65535** | V36 | gentle-EME debounce TORQUE thresholds | disables the torque-based debounce leg | frozen since V36 |
| `0xC64B8` | 1 | 0x70 | **0xFF** | V37 | DTC-0x49 fail-counter gate | the V37 DTC-0x49 fix | frozen since V37, resolved on-car 2026-07-14 |
| `0xC64DE` | 2 | 25617 | 25627 | V22 | legacy re-engage ramp (label disputed) | small offset, unexamined | frozen since V22 |
| `0xC6598-C65CC` (7 floats) | 4×7 | various | **5f throughout** | V25/V29/V31 | corridor-wall / boost-floor FLOAT constants | authority-curve widening, pre-V38 | frozen, unexamined this arc |
| `0xC674E-C676C` (7 ints) | 2×7 | various | **5120 throughout** | V25/V31 | corridor-wall / boost-floor INT constants | same family, integer mirror | frozen, unexamined this arc |
| `0xD7A5C/5E/60`, `0xD7A6C/6E/70` (6 cells) | 2×6 | −9830/−5734/−1966 (×2) | **−14745/−8601/−2949 (×2)** | V74 | `0xCBE74` friction/damper LERP, modes 26/27 Y-rows | ×1.5 the dose, engaged modes only | **carried since V96's revert-by-construction; the row's own history is the friction/damper family's most-fought lever (V74/V75 hard-faulted at this dose with the old `0xC407E`=850 clamp; V91/V92/V96+ carry it safely under `0xC407E`=511)** |
| `0xE4194..0xE521C` (72 cells, identical value) | 2×72 | 15360 | **16384** | V38 | ARB setpoint limit records, all selectors | authority ceiling widening from V38 | frozen since V38, the kit's oldest still-active lever family |

**`0xC63AC` does NOT appear in this table** — V99 reverted it to exactly STOCK's value (102), so
V97's pole-shift lever is fully undone and the cell reads byte-identical to a factory ECU.

---

## 3. WHAT V99 IS, MEASURED VS BELIEF, AND WHY IT WAS FLOWN ANYWAY

**MEASURED (EVIDENCE, from the same-session retraction the build's own handoff records):**
- `0xC40BC`'s dose delivers only **0.5–1.2%** against Path-2's own **~9%** perceptual floor.
- **93.1%** of the operator's hands-on engaged frames sit ABOVE the 10.61 °/s knee, where 300 and 600
  are arithmetically identical (measured ramp ratio 1.050, not the intended 2.00×).
- After V99, the ACTUAL arm of the observer residual is byte-for-byte Honda; the only two non-Honda
  cells left anywhere on the observer structure are `0xC40D2` (V89, MODEL arm) and `0xC40BC` (V99,
  also MODEL arm).

**BELIEF / open:**
- GATE 2 (closed-loop stability) is not closed for `0xC40BC` — describing-function gain at the new
  knee is unmeasured; V80 is the cited precedent for what a harder relay ramp can do.
- `0xC40BC` is not engagement-gated (acts in MANUAL too) — an honest cost, not evaluated on-car yet.

**Why it flew anyway:** the operator's explicit decision, after the retraction was in front of him —
consistent with the V91 precedent (*"we are flying regardless, so the instrument is free"*). His
report afterward: ***"I think it helped with the audible aspect of the grinding, though I'm not
sure."*** Not a symptom he has called fixed. **Detailed flight scoring (route `0x82`, 2 segments) is
a separate, parallel pass this session (`rlog-tools/extract_r82.py`, `rlog-tools/v99_r82_score.py`
were in progress at the time this map was written) and is deliberately NOT summarized here — this
document is the record-repair and arc-classification deliverable, not the flight score.**

---

## 4. ARC CLASSIFICATION — V85 → V99, against the whole arc since V38

Standing classification through V84: **V38–V52 authority/filters/poles/caves · V53–V61 telemetry
probes and lane mutes · V62–V73 the rate lane (r24/r26) · V74–V83a the base-assist damper · V84
damper reverted to Honda.**

**V85 → V99 is a new era: it moves off the LANE/COMMAND side of the chain and onto the PLANT-MODEL /
OBSERVER side.** Every build from V38 through V84 edited something that sums into, gates, or shapes
the delivered LKAS command. Starting at V85, the target becomes `FUN_0003b8f6`'s plant model and the
`residual = MODEL − ACTUAL` disturbance observer that reads it — a structure no build before V85 had
ever touched.

| build(s) | what moved | genuinely NEW, or the same lever re-run? | flew? | result |
|---|---|---|---|---|
| **V85** | `0xC40BC` 600→**6000** (Coulomb relay knee, UP) | **NEW** — first edit ever to the plant-model relay knee | ✅ route `6e`, clean | relay saturation cut 7.21×; bands NULL; operator "a little better" |
| **V86** | `0xC40D4` 573→286 (observer torque IIR pole) | **NEW** — first phase/lag lever since V38 | ✅ route `6f`, clean | pre-registered frequency-shift test FALSIFIED (line stayed 7.79 Hz) — closed the linear-loop hypothesis |
| **V86b** | FactorC `Y[0]` 0→908/875 (damper-at-creep) | re-run of the V74-V80 damper family, narrowed single-variable | ✅ route `70`, clean | operator: extra dampening felt at slow speed; ring-free by construction |
| **V87** | rebase to V38 + V57 gain + V42 fix + 427 probe, NO new lever | **NEW CLASS — first SUBTRACTIVE build ever** (strips 49 builds of levers) | ✅ route `71`, clean | measurement-only; established the ~7.8 Hz mode is real (later: Q 14-29 resonance) |
| **V88** | Lever B restored (`0x3AA96`/`0xC6446`) + sign-fixed probe | Lever B itself is a **re-run** (7th flight of the same r24 arm); the sign-fix probe is **NEW** | ✅ route `73`, clean | **grinding operator-reported FIXED**; 15–22 Hz command down to 0.549×; best result in the kit to date |
| **V89** | `0xC40D2` 102→**204** (K1, modelled friction) | **NEW CLASS — first build to edit the PLANT MODEL itself**, not a command/lane term | flew (routes `75`/`76`, per record correction) | direction measured (more modelled friction = lighter wheel); gate role BELIEF |
| **V90** | zero cal cells — probe only | pure instrument | ✅ route `77` | `gp-0x6b26` measured live for first time; `Re(Z)<0` replicated 2-26 Hz |
| **V91/V92** | `0xCBE74` ×1.5 on modes 26/27 (friction/damper LERP dose) | **re-run** of V74/V75's identical dose, now protected by `0xC407E`=511 | V92 ✅ route `79` (V91's route `78` ambiguous — see BUILD-LINEAGE correction) | fault-free this time; later shown DOSE-INERT at its own output (route 78/79 stratified ratio 0.99 vs pre-registered 1.50) |
| **V93/V94** | `0xCBE74` ×0.5/×0.25 (SAME cells, opposite direction) | **same lever, pushed the OTHER way** — first-ever lowering of this dose | V94 ✅ route `7d`, aborted | operator: made it much worse, vibrated the whole car; later shown the rationale (apparent inertia) was BACKWARDS — this is why UP was later re-tried |
| **V96** | zero cal (reverted V94's cut by construction) + new residual-pair probe | **NEW** measurement pair (`gp-0x6b70`/`gp-0x374c`), first ever on the wire | ✅ routes `7e`/`7f` | instrument under-ranged 34× (S1/S2 void) — later closed analytically |
| **V97** | `0xC63AC` 102→150 (Stage-1 pole, ACTUAL arm) | **NEW** — first edit to this specific pole | ✅ route `0x80` | uninterpretable (DC-gain-1 pole, no amplitude statistic could see it, no instrument pre-registered) |
| **V98** | zero cal — first COMPARATOR probe | **NEW CLASS** — first comparator-based (not threshold) instrument in the kit | ✅ route `0x81` | ANSWERED: REQUEST is the smallest arm (duty 0.0000), MODEL≈ACTUAL (0.4235) — refutes "arms are wildly unequal"; V89/V97 nulls reframed as dose/direction, not reach |
| **V99** | `0xC40BC` 600→**300** (same cell as V85, opposite direction) + `0xC63AC` 150→**102** (revert of V97, not a new push) | **`0xC40BC`: same lever pushed the OTHER way** (V85 went up, V99 goes down, into virgin range) · **`0xC63AC`: a REVERT, not a new lever** | ✅ route `0x82`, 2026-08-13 | retracted as a fix same-session before flying (dose 0.5-1.2% vs 9% floor, 93.1% of frames above the now-irrelevant knee); operator: "helped with the audible aspect... though I'm not sure" |

**Summary of what's genuinely new in V85→V99 vs. what's a re-run:**
- **Genuinely new mechanism classes:** V85 (plant-model relay knee), V86 (phase/pole lever), V87
  (subtractive rebase), V89 (plant-model K1 — the first non-command-side lever with a positive
  measured result direction), V96/V98 (residual-pair and comparator instrumentation).
- **Re-runs of an existing lever:** V86b and V91/V92 (both re-test the pre-V85 damper/friction-dose
  families with a safety fix, not a new mechanism); V88's Lever B (a restoration, its NEW part is the
  sign-fixed probe alongside it).
- **The same lever pushed the other way — a different claim from "a new lever," flagged per standing
  instruction:** V93/V94 lowered `0xCBE74` after V91/V92 raised it; V99 lowered `0xC40BC` after V85
  raised it; V99's `0xC63AC` edit is a straight revert of V97, not a push in any direction.
- ⭐ **The load-bearing structural finding of the whole V85→V99 era**: the target moved from the
  LKAS-command side (V38-V84, everything sums into or gates the delivered command) to the
  PLANT-MODEL/OBSERVER side (`FUN_0003b8f6` → `residual = MODEL − ACTUAL` → `gp-0x6b70` → PID). Every
  build in this era edits one of exactly two arms of that residual (MODEL: `0xC40D2`/`0xC40BC`, or the
  Stage-1/Stage-2 poles/scales around the ACTUAL arm: `0xC63AC`/`0xC63AE`) or instruments it
  (V87/V90/V96/V98) — none has gone back to the command/lane side since V84.
