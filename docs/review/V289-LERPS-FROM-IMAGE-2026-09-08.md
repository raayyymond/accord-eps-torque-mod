# V289 rev 1 — LERPs, filters and cumulative delta, read from the images — 2026-09-08

Subagent `lerps`, reporting to the orchestrator. **Method**: raw little-endian byte reads of
`stock_fw_dump/code.bin`, the `_v282_..._plain_image.bin` (V289's unchanged calibration surface for
everything except two cells) and the `_v289_..._plain_image.bin`, plus an **independent V850E2
instruction decoder written fresh for this pass** (standard opcode fields, not imported from
`build_v289_tva.py`) to recover the notch cave's coefficients from bytes. Script:
`analysis-2020accord/_scratch/out/_v289_lerp_reader.py`. Full data: `v289_lerps.json` (73 KB),
plotting-ready subset: `v289_page_data.json` (56 KB), both in the same `_scratch/out/` directory.

**Hashes, verified this pass**: stock `3f1d55a9…`, V282 `0ea98d06…`, V289 `f0c10c29…` — all match the
brief. EVIDENCE.

---

## 1. LERPs — V289 == V282 everywhere except the fb-pole cells (EVIDENCE)

Assist map (slot 7), Kp/Kd (slot 7), the four override/fade taper records, and every clamp cell in
`CLAMP_CELLS` (23 cells: T/D/P/sum clamps, deadband, I anti-windup, Ki, output-lag pole, ipath cal,
feedback clamp, r24 arms, carrier gain) were read from stock, V282 and V289 and diffed programmatically.

**Result: `lerp_diff_check.clamp_cells_differing` contains exactly two entries — `0xC63E8` and
`0xC63EA` — and nothing else.** `expected_only_fb_pole: True`. Map, Kp, Kd and all four tapers are
byte-identical V282 vs V289. **No cell differs that is outside the declared list.**

| cell | addr | V282 | V289 |
|---|---|---|---|
| fb pole a | `0xC63E8` (signed) | 923 | **875** |
| fb pole b | `0xC63EA` (unsigned) | 1560 | **2301** |
| output-lag pole a/b | `0xC63EC`/`EE` | 992 / 507 | 992 / 507 (unchanged) |
| Kp, slot 7 | `0xE5378` | 248 flat | 248 flat |
| Kd, slot 7 | `0xE511C` | 128 flat | 128 flat |
| assist map, slot 7 top | `0xE502C` | Y=1032 @ X=240 | unchanged |

## 2. The two in-loop filters

### 2a. Feedback lag (`0xC63E8`/`EA`) — EDIT 2, cal-only

Topology (confirmed by decompile in `docs/traces/TRACE-2026-09-08-...md` Q1, re-used not re-derived
here): a "two-sample-sum" one-pole, `s[n] = (a·s[n-1])>>10 + (b·x[n])>>10`, `y[n] = s[n-1] + s[n]`.
`H(z) = (b/1024)(1+z⁻¹) / (1 − (a/1024)z⁻¹)`.

| | V282 (a=923, b=1560) | V289 (a=875, b=2301) |
|---|---|---|
| pole | 16.53 Hz | **25.03 Hz** |
| DC gain | 30.891 | 30.886 (**−0.017 %, essentially unchanged**) |

`\|H\|` normalized to DC, and phase, at the requested frequencies (EVIDENCE, computed from the decoded
cells):

| f (Hz) | V282 \|H\|/DC | V282 phase | V289 \|H\|/DC | V289 phase | Δphase |
|---|---|---|---|---|---|
| 3.9 | 0.973 | −13.29° | 0.988 | −8.88° | **+4.41°** |
| 7.3 | 0.915 | −23.85° | 0.960 | −16.30° | **+7.56°** |
| 13.5 | 0.774 | −39.29° | 0.880 | −28.41° | **+10.88°** |
| 20.05 | 0.635 | −50.56° | 0.779 | −38.79° | **+11.77°** |
| 30.0 | 0.481 | −61.24° | 0.639 | −50.31° | **+10.94°** |
| 50.0 | 0.311 | −71.87° | 0.444 | −63.65° | +8.22° |

Moving the pole 16.5→25 Hz returns 10–12° of phase across the 3.9–30 Hz band and raises `\|H\|` (i.e.
raises the loop's effective feedback strength — note this is a **feedback**-path filter, so more gain
here narrows loop error, not "more assist"). DC gain is unchanged to 4 s.f., matching the build
script's own claim, confirmed independently here.

### 2b. Output lag (`0xC63EC`/`EE`) — unchanged, confirmed

`0xC63EC`=992, `0xC63EE`=507 on **both** V282 and V289 (`output_lag_cells.unchanged: True`). Same
two-sample-sum topology plus a static `>>5`. DC gain 0.9902 (matches the trace's independent figure).
At 20.05 Hz: `\|H\|`/DC = 0.244, phase −75.87° — **identical on both builds**, so it contributes zero
delta to the phase budget below.

### 2c. The notch (V289 only) — coefficients recovered independently from the image bytes

**Decoder positive control**: reproduced 14/17 of Ghidra's own captured stock-listing entries exactly;
the 3 "mismatches" are naming-only (`movi`/`cmpi` vs Ghidra's `mov`/`cmp` for the same Format-II
immediate opcodes — same encoding, same immediate value, confirmed by direct comparison) plus the
expected divergence at `0x2A174` itself, which is V289's own hook and correctly decodes as
`jr 0xC4C00` on the V289 image. Decoder trusted.

Walking the cave from the hook target (`0x2A174 → jr 0xC4C00`) to its own return (`jr 0x2A178`) found
**52 instructions, 140 bytes, `[0xC4C00, 0xC4C8C)`** — matches the build script's stated extent
independently. Three `movea imm,r0,rX` constant loads were found, assigned by instruction-sequence
role alone (which register each immediate is multiplied against next):

| decoded constant | value | assigned from structure |
|---|---|---|
| 1st movea (`0xC4C0E`) → mul'd by r12 (=x, the cave input) | **16048** | b0 |
| 2nd movea (`0xC4C26`) → mul'd by r6 (=y) | **15712** | a2 |
| 3rd movea (`0xC4C3C`) → mul'd by r9 (=n=x−y) | **−31842** | b1 (= a1 by construction: the identical multiply pattern computes `b1·n` where `a1·y` would appear in a canonical TDF-II — the code collapses them into one `mul` because `b1 == a1`) |
| `andi` immediate (×2) | `0x3fff` | E_MASK (14-bit remainder) |
| `sar` immediate | 14 | QSH (shift = Q14) |
| `b2 = b0`, `a0 = 1<<14` | 16048, 16384 | by construction (single `mul r12,r13` reused for both the accumulator term and `s2' = b0·x − a2·y`) |

**These decoded values are bit-for-bit identical to the build script's declared design constants** —
independent confirmation, not a copy: b0=16048, b1=a1=−31842, b2=16048, a0=16384, a2=15712.

Realised filter (from the decoded integers): centre **20.036 Hz** (exact numerator zero, since
b0=b2 places it on the unit circle), −3 dB edges **16.98 / 23.64 Hz**, Q **3.007**, DC gain **1.000000**
exactly (`254/254`), Nyquist gain 1.000000 exactly. At the centre the notch is an **exact zero**
(`\|H\|=0`, depth = −∞ dB in the strict mathematical sense); at the design/measurement frequencies:

| f (Hz) | \|H\| | dB | phase |
|---|---|---|---|
| 3.9 | 0.9977 | −0.020 | −3.85° |
| 7.3 | 0.9904 | −0.084 | −7.96° |
| 13.5 | 0.9250 | −0.677 | −22.33° |
| 20.05 | **0.00417** | **−47.6** | +89.76° |
| 30.0 | 0.9284 | −0.646 | +21.82° |
| 50.0 | 0.9878 | −0.107 | +8.96° |

Matches the build script's own docstring claims (−47.6 dB at 20.05, 0.998/−3.85° at 3.9 Hz, etc.)
exactly — **independently re-derived, not copied.**

200-point log-spaced (1–100 Hz) curves for fb-lag V282, fb-lag V289, notch V289, and their product
(the net in-loop change) are in `v289_lerps.json` → `curves_1_100hz` and `v289_page_data.json`.

## 3. Loop phase budget at 20.05 Hz (small table; EVIDENCE except the D-lead row)

| element | V282 phase | V289 phase | Δ |
|---|---|---|---|
| fb one-pole (two-sample sum) | −50.56° | −38.79° | **+11.77°** |
| output lag (two-sample sum, `>>5`) | −75.87° | −75.87° | 0° |
| D lead (Kp=248, Kd=128 flat, both images) | +3.70° (modelled) | +3.70° | 0° |
| one 1 kHz tick | −7.22° | −7.22° | 0° |
| notch | 0° (absent) | **+89.76°** | +89.76° |
| **sum of deltas** | | | **+101.5°** |

The D-lead row is **BELIEF** — modelled as a single-tick backward-difference lead scaled by Kp/Kd; the
exact bit-level PID summing arithmetic (P/I/D combination with the D clamp) was not re-disassembled
this pass, and the golden model explicitly does not implement this stage (`eps_chain_control.py`
SECTION 5B gap note, cited not re-derived). Kp/Kd themselves ARE read fresh from the image (EVIDENCE)
and are unchanged V282→V289. This table is a **linear, element-wise phase sum**, not a closed-loop
stability re-derivation — it says where each edit's phase contribution sits, not a verified net
margin.

## 4. Delivered-surface consequence

**Steady state (DC) is unchanged**: notch DC gain is exactly 1 (`254/254`, proven from the decoded
integer coefficients, not asserted); output-lag DC is byte-identical; fb-lag DC changes by only
**−0.017 %** (30.891→30.886), i.e. essentially unchanged. Assist map, Kp and Kd are byte-identical.
**Torque vs command at steady state is the same curve as V282.**

**Transient**: byte-exact integer mirror of the decoded notch on a 0→15360 step (the sum-clamp rail,
the largest S the loop can present), assuming the 1 kHz tick rate (BELIEF, per the build script's own
`TICK_HZ` note — not independently re-measured this pass):

- peak = **15,360 (1.00× input)** at t = 25 ms
- settles within a 2 % band by t = **120 ms**

This is smaller than the build script's own worst-case linear bound (1.155× / ~17,735, quoted in the
docstring for adversarial sign sequences) — the step response for a *constant* step is milder than the
adversarial worst case, consistent with the docstring's own framing (the 1.155× figure is a driven
worst case, not the plain-step response). Both numbers come from my own integer mirror of the
*decoded* coefficients (not copied from the script's `notch_tick` mirror), and agree with it in
structure.

## 5. Cumulative non-stock delta — V289 vs stock, new/changed rows only

Rows 1–28 are exactly `docs/review/V288-CUMULATIVE-NONSTOCK-DELTA-2026-09-07.md`'s rows 1–28 (the
V282 baseline every subsequent build inherits) — **unchanged, still MEASURED/CARRIED/INERT as there,
not re-verified byte-for-byte again this pass except where noted below.** V288's rows 29–33 (its own
setpoint-prefilter hook/cave) do **not** apply to V289 — V289 branches from **V282**, not V288.
Replacing them, verified from stock and the V289 image directly this pass:

| # | address(es) | stock | V289 | what it physically is | what it does | status |
|---|---|---|---|---|---|---|
| 29 | `0x2A174`–`0x2A177` | `e5 3f ef 73` (`ld.hu 0x73ee,tp,r7`) | `89 07 8c aa` (`jr 0xC4C00`) | hook at the ONE convergence point of the clamped PID-sum `S` (all three clip branches + the reset path land here) | diverts the clamped loop output into the notch cave, replicates the displaced load, returns | new, V289 |
| 30 | `0xC4BD6`–`0xC4BD9` | `ff ff ff ff` | `80 07 06 00` (`7f 00`→`jr 0xC4BDC`, 2 B consumed of the pre-existing `0x14A` cave's own `jmp[lp]`) | exit of the existing V280-era `0x14A` telemetry cave (row 7 in the V288 table), re-repointed a second time | diverts that cave's own tail into a new 28-byte telemetry rung | edited, V289 (address coincides with V288's identical repoint, but this is a fresh edit off the V282 base, not inherited) |
| 31 | `0xC4BDC`–`0xC4BF7` (28 B) | `ff`×28 | `e4 3f c7 93 c7 3e a0 00 84 37 ed ea c6 36 5f 00 07 31 44 37 7e ca 24 36 e8 ea 7f 00` | telemetry tail: reads the notch's FLAG halfword, keeps only bits 5/7, clears those two bits in CAN `0x14A` byte 4, ORs them back, re-issues the relocated `movea`+`jmp[lp]` epilogue | publishes `sign(n)` on bit 5 and `\|n\|≥\|y\|` on bit 7 (read-only instrumentation; bits 0–2 stock, 3/4/6 kept from V282's rungs) | new, V289 |
| 32 | `0xC4C00`–`0xC4C8B` (140 B, 52 instr.) | `ff`×140 | (decoded above — the RBJ notch with error feedback) | the notch cave itself: filters the clamped PID sum `S` in place | takes the loop's own action to ≈0 in a ±3 Hz band around 20.04 Hz; unity DC; output clamped to the same `0xC61BE` cell Honda's sum clamp uses | new, V289 |
| 33 | `0xC63E8` | 923 (stock=V282) | **875** | fb-lag pole coefficient `a` | moves the feedback filter's pole 16.5→25 Hz | new, V289, cal-only |
| 34 | `0xC63EA` | 1560 (stock=V282) | **2301** | fb-lag pole coefficient `b` | keeps DC gain at ≈30.89 while moving the pole | new, V289, cal-only |
| 35 | `0xC4FFC` | `75 49 f2 48` | `a7 61 1f 82` | page-CRC trailer, code block `[0x13000,0xC4FFC)` | recomputed for rows 29–32 | bookkeeping |
| 36 | `0xC6FFC` | `0c 9e 3c ef` | `77 04 78 fe` | page-CRC trailer, cal block `[0xC6000,0xC6FFC)` | recomputed for rows 33–34 (the fb-pole cal edit; **V288 never touched this page, so V288 never needed this trailer** — this is a genuinely new consequence of V289 being cal+cave, not cave-only) | bookkeeping |

All eight stock/V289 byte values above were read directly from both images this pass, not taken from
the build script's docstring.

## 6. V289 vs V282 diff (byte runs) and CRC check

Full-window diff `[0x13000, 0x100000)`: **185 bytes in 10 runs** — matches the build script's own
claim ("185 bytes in 10 runs (188 touched; three notch-cave bytes equal the 0xFF they replaced)")
exactly, independently reproduced:

| run | len | content |
|---|---|---|
| `0x2A174`–`0x2A178` | 4 | the hook |
| `0xC4BD6`–`0xC4BDA` | 4 | 0x14A cave's re-repointed exit |
| `0xC4BDC`–`0xC4BF8` | 28 | telemetry tail |
| `0xC4C00`–`0xC4C0A` | 10 | notch cave, part 1 |
| `0xC4C0B`–`0xC4C20` | 21 | notch cave, part 2 (1 byte at `0xC4C0A` coincidentally equals the `0xFF` it replaced) |
| `0xC4C21`–`0xC4C8C` | 107 | notch cave, part 3 (1 byte at `0xC4C20` likewise coincidental) |
| `0xC4FFC`–`0xC5000` | 4 | code-page CRC |
| `0xC63E8`–`0xC63E9` | 1 | fb pole `a` |
| `0xC63EA`–`0xC63EC` | 2 | fb pole `b` |
| `0xC6FFC`–`0xC7000` | 4 | cal-page CRC |

Sum = 185 bytes, 10 runs — **confirms the build script's own diff claim independently.** No cell
differs outside this list (cross-checked against the full `CLAMP_CELLS`/map/Kp/Kd/taper sweep in §1).
CRC trailer *values* were read and compared for identity/difference only — no generic CRC algorithm
was re-implemented and verified this pass (the build tool's own recompute is trusted for the
bookkeeping claim; re-deriving the exact CRC polynomial/seed was out of scope for this task).

---

## Open items for the orchestrator

1. §3's D-lead phase contribution is **BELIEF** (modelled, not disassembled) — if the exact PID
   summing arithmetic matters for a stability claim, it needs a dedicated decompile pass.
2. §6's CRC check confirms trailer *values changed* and *where*, but does not independently recompute
   the CRC algorithm — treat "recomputed correctly" as carried from the build script's own self-check,
   not re-verified here.
3. No cell outside `{0xC63E8, 0xC63EA}` plus the five new-code regions differs between V282 and V289 —
   confirmed by both the targeted LERP/clamp sweep (§1) and the full-window byte diff (§6), which agree.
