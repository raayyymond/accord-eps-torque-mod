# LENS: side channels D9 / D6 / D7 — release V300 (stock + angle loop), 2026-10-15

Lens: firmware-codepath-tracer (subagent). Program queried: `code.bin` (stock, the only program open). V299 bytes read by Python for comparison only. Nothing flashed, sent or edited.

## VERDICTS

| item | verdict | one line |
|---|---|---|
| D9 map side channels | **PASS** | The census premise is wrong. `gp-0x682f`, `gp-0x6830`, `gp-0x6a34` are NOT map-derived. Reverting the map changes none of them. |
| D6 debounce package | **PASS_WITH_DEFECTS** | 12 readers named. Keep is correct. Two census defects: mis-transcribed stock values, and an undeclared disabled protection. |
| D7 `0xC64DE` 27 -> 17 | **PASS** | Inert twice over: gate `gp-0x6809` is never written, and the amplitude table is all zeros. |

No FAIL / do-not-flash finding from this lens.

## Pre-registered FAIL conditions (set before tracing)

- D9 FAIL: any of the 17 sites takes its value from the map LERP output, and a threshold or gate on the engage/taper/interlock path is crossed only because the map is large; or the cave reads a map-derived byte.
- D6 FAIL: a live reader of `0xC61C0/C2/C4` or `0xC64B4..B8` where 0xFFFF/255 disables a protection the angle loop relies on, with nothing else covering it.
- D7 FAIL: the `gp-0x6b2c` square wave reaches the motor path with non-zero amplitude, or its half-period feeds a live consumer other than the wave itself.

## D9 — EVIDENCE

**Decisive fact: `gp-0x682f = min(|gp-0x4f60| >> 5, 255)`. That is driver bar torque, not the assist map.**

Ghidra `disassemble_bytes` (dry_run) 0x28f20–0x290e8 on stock:

```
28f26 ld.h  -0x4f60,gp,r15        ; bar torque (x1.024 CAN scale)
29048 mov r15,r7 / 2904a sar 5,r7 / 2904c bp / 2904e subr r0,r7   ; |t|>>5
29056 addi -0xff,r7,r0 / 29060 movea 0xff,r0,r16 / 29064 cmovc r16,r7,r8   ; saturate 255
29068 st.b  r8,-0x682f,gp
```

r15 is never a destination between 0x28f26 and 0x29048 (167-instruction listing read in full). The decompile's `iVar28 >> 5` stored to `gp-0x682f` is the same `iVar28 = gp-0x4f60` assigned at the top of the function. The census read a later reuse of that decompiler variable (the map LERP output) into it. An independent 2026-08-27 trace (taper-cascade memory) reached the identical formula.

- `gp-0x6830` (0x290de): `|clamp(((r15>>5)+(r6>>5)-r6)>>4, +-0x3200)| >> 6`. A one-pole lag/derivative of the same bar torque (state `gp-0x3d34`, stored 0x29080). Not the map.
- `gp-0x6a34` (0x290ca): `|r26 floored to 32| >> 5`. The filtered rate feedback. Not the map.
- The map bank `0xC9A88` is read at exactly two places in the image: LERP at 0x29cfe (live) and 0x2abf4 (uncalled twin). LE32 literal scan of `0xC9A88`: 2 hits.
- The LERP output `r13` is consumed only by `mulh r13,r16` at 0x29d6c. V299 bytes at 0x29d6a are `24875296` = `ld.h -0x69ae,gp,r16`, which replaces `mov r8,r16 ; mulh r13,r16`. Every path after 0x29d6c reloads r13 before use (0x29d8c, 0x29da0). So in the angle-loop images the map Y is dead end to end. The LERP still runs and its result is dropped. X knots are unchanged, so `divq` stays safe.
- Taps `gp-0x6a32` (old map output) and `gp-0x674b` (idx): 2 writers, 0 readers each.

**The 17 sites.** Raw scan matches Ghidra `search_instructions` (12 for 682f, `match_count 12`). `get_xrefs_to` on the RAM address returned the known false zero. The raw scan covers disp16 forms with parity-correct `ld.bu`, disp23 6-byte forms (0 hits), and LE32 literals. Every site the decompile shows was found, which is the positive control.

| site | function | role | map-dependent? |
|---|---|---|---|
| 29068 st.b | 28ea6 live | writer: bar torque >>5 | no |
| 290b8 st.b r0 | 28ea6 live | bail target zeroes it | no |
| 29206, 29218 | 28ea6 live | DTC-0x49 counter `gp-0x6758`: `0xC64B8 < 682f && uVar33 != 0` | no; dead at 255 |
| 29242, 292bc | 28ea6 live | STEER_STATUS=4 debounce rise / hold, tier 1 vs `0xC64B4`/`B5` | no; dead at 255 |
| 29a7c | 28ea6 live | `cmp r8,r1 ; bnh` vs `0xC64B8`: idx bypass `jr 0x29cc4` | no; dead at 255 |
| 2a3e8, 2a3fa, 2a424, 2a49e | 2a30e island | twin of the debounce and DTC logic | no |
| 2a97e | 2a93a island | twin of the 29a7c bypass | no |
| 290de st.b (6830) | 28ea6 live | writer | no |
| 29c56, 29cc8 (6830) | 28ea6 live | load r21: X of the spF LERP `0xC6974` (X 4,6,8,10; Y 255 x4, flat) and X of hand-fade factor A (`0xCBB54`/`0xCBC34`: 255 up to X=10, 205 at X>=20) | no |
| 2ab4a, 2abbe (6830) | 2a93a island | twin | no |
| 290ca st.h (6a34) | 28ea6 live | writer | no |
| 2a0ca (6a34) | 28ea6 live | read inside the `gp-0x680a == 1` lane, entered by `jr 0x2a0c6` at 29a70. `gp-0x680a` has 0 writers (disp16, disp23, LE32 literal, `movea gp` all empty) and boot value `0x868a6 = 00`. Unreachable. | no |
| 2afae (6a34) | 2a93a island | twin | no |

Totals: 682f = 12 sites (2 writers, 10 readers), 6830 = 5 sites (1 writer, 4 readers), giving the 17. Seven of the seventeen are in the island `0x2A30E–0x2B421` (zero direct callers per the 2026-09-13 trace). Register-indirect dispatch into it was not excluded, but that is moot: those copies are Honda logic on cells that are not map-derived.

**Sub-questions**

1. *Can the engage/arb SM fail to engage or drop the lane under Honda's map when the fork sends raw = -10*theta?* No path depends on the map. The engage gates are sensor plausibility, `gp-0x67fe == 2`, the `gp-0x69aa` band, the speed band, `(short)gp-0x69ae + 0x4000 < 0x8001`, then the `gp-0x6803/6805/6807/3d38` ramp SM. `gp-0x69ae = clamp(-4*raw, +-0x4000)`, so raw +-4096 lands exactly on +-0x4000 and passes the band. The only engage-side use of the clamped setpoint `uVar33` is `uVar33 != 0` inside the DTC-0x49 counter, which is dead at `0xC64B8 = 255`. Method: decompile of 28ea6 plus disassembly 0x29a44–0x29aa4.
2. *Does the demand byte feed the Kp/Kd X axis?* No. X = idx = `|clamp((G*r22)>>22, +-240)|`, with `G = taper*spF` and `r22 = clamp(gp-0x69ae, +-LIM)`. The only link to `gp-0x682f` is the bypass at 0x29a7c (idx := 0), unreachable at 255. The map Y is the output keyed by idx, not an input to it. Kp/Kd are flat 112/48 anyway.
3. *Hand fade / `0xCBBC4` taper?* Yes, they read `gp-0x682f` (factor B, tables `0xCBAE4` and `0xCBBC4`) and `gp-0x6830` (factor A). Both are bar torque, so Honda's map scale never touched them and the release hand fade equals stock. The arm is selected by `gp-0x6803 == 2` at 0x29a74, the same value the camera interlock uses: `==2` gives `0xCBAE4` (255 -> 51 by X 112), otherwise `0xCBBC4` (255 -> 77 by X 96). That coupling predates D9 and D9 does not change it. Worth stating on the page.
4. *Does the cave read any of these?* Scan of the V299 cave 0xC4C00–0xC4FF0: gp cells touched are `-0x6abe`, `-0x6a5e` (speed), `-0x4f68` (|tau|), `-0x6a00` (angle), `-0x6dd0`. None of the 17-site cells and none of `-0x6a32/-0x674b/-0x697a`.
5. *Was the x6 scale load-bearing?* The x6 the loop needs is A6 (`0x2A1F0` repoint to `0xC6CD0`, kept). It is a different mechanism and D9 does not touch it.

**Defects (non-blocking; correct the census text)**

- The D9 row says `gp-0x682f = min(|iVar28|>>5, 254)` of the map. Correct: driver bar torque >>5, saturating at 255. The revert recommendation stands, now because the map is dead end to end in this image.
- Release rationale item 4 says the SM "reads Honda's own numbers again". Correct: it reads the same numbers it always read, because they were never map-scaled.
- Residual BELIEF: the island is dead. Not load-bearing.

## D6 — EVIDENCE

12 readers (raw LE scan, `ld.hu` opfield 0x3F with hw2 bit 0 = 1). Two further raw hits, 0x2bd5e (opf 0x2c) and 0x82df2 (opf 0x2f), are not `ld.hu` and are rejected. Both functions carry the identical 4-tier OR envelope.

| cell (stock value) | FUN_00028ea6 rise / hold (live) | FUN_0002a30e rise / hold (no direct callers) |
|---|---|---|
| `0xC61C0` (1600) | 0x2924a / 0x292c4 | 0x2a42c / 0x2a4a6 |
| `0xC61C2` (896) | 0x2925e / 0x292d8 | 0x2a440 / 0x2a4ba |
| `0xC61C4` (1280) | 0x2926e / 0x292e8 | 0x2a450 / 0x2a4ca |

What each cell is: a threshold on `uVar37 = |clamp(lag-difference of bar torque, +-0x3200)|`, max 12800. 0xFFFF can never be exceeded, so the three rate terms are off. The torque terms use `0xC64B4..B7` (stock 112, 96, 54, 64; now 255). With `gp-0x682f` saturating at 255, `255 < 682f` is never true. Result: the trip that writes `gp-0x6807 := 4` (STEER_STATUS 4) from driver-torque transients cannot fire in the live function. That trip only ever depended on the bar-torque envelope, never on the map.

`0xC64B8` second role at 0x29a78/7c/86: `ld.bu 0x74b8` against `ld.bu gp-0x682f`, then `cmp r8,r1 ; bnh 0x29a8e`. An unsigned byte compare against 255 is false for every value, so it cannot fire at either scale. If it did, `jr 0x29cc4` sets idx := 0. The release error path reads `gp-0x69ae` directly and Kp/Kd are flat, so a firing would leave the angle loop untouched. Other readers of `0xC64B8`: 0x2920a and 0x2921c (DTC-0x49 counter, dead at 255), and the uncalled twins 0x2a3ec, 0x2a3fe, 0x2a97a. Hits at 0x4549e and 0x4556e are the odd neighbour `0xC64B9` and are rejected.

**Defects**

1. The census D6 row quotes stock `0xC64B4..B7` as "70/60/36/40". The image holds 112, 96, 54, 64. The hex bytes 0x70/0x60/0x36/0x40 were read as decimal. `0xC64B6` is 54 and `0xC64B7` is 64. `0xC64B8` = 112 is correct. Stock `0xC61C0/C2/C4` = 0x640/0x380/0x500 = 1600/896/1280 is correct.
2. The release page must state what keeping D6 costs. The driver-torque-transient STEER_STATUS=4 trip and the DTC-0x49 over-torque counter are off, as on every flown build since V37. Hand override rests on the hand-fade taper and the cave's 1229 freeze. This is not new risk for the release, but it is a disabled Honda protection and should be declared, not implied by the word "kept".

Keep is correct. Reverting D6 while A6 (x6 lane gain) stays is the unflown direction, and the V36/V37 record found the stock envelope trips with x6 authority.

## D7 — EVIDENCE

`0xC64DE` is a byte (17 stock, 27 now). Raw scan: 16 `ld.bu` sites with opf 0x3C (even displacement). Eight are live in FUN_00028ea6 (0x2976e, 0x2984e, 0x29862, 0x29874, 0x29896, 0x298a8, 0x298b0, 0x299aa). Eight are in the uncalled FUN_0002b070 (0x2b0aa, 0x2b17e, 0x2b192, 0x2b1a4, 0x2b1c4, 0x2b1d6, 0x2b1de, 0x2b2be). The odd neighbour `0xC64DF` = 100 (0x29288, 0x2a46a, debounce reseed) is a separate cell and D7 does not touch it.

Function: a three-state generator inside the arbitration function. State `gp-0x3d37` (read only at 0x29734) runs a ramp counter `gp-0x6a7e` up to `0xC6288` = 300 ticks, then a relaxation oscillator. Counter `gp-0x6756` counts to N = `0xC64DE`, then `gp-0x6b2c := -gp-0x6b2c`, and re-arms at `(N>>1)+1`. N is the half-period in ticks: 17 gives 29.4 Hz, 27 gives 18.5 Hz at 1 kHz. The cells `3d36`, `3d37`, `6756`, `6a7e` have readers only inside this block and its uncalled twin. The one consumer of the wave is `gp-0x6b2c`, which is the additive term at 0x2A1FC.

Why it is inert, by two independent routes, both byte-read:

1. Gate. The wave branch requires `gp-0x6809 == 1 && bVar1`. `gp-0x6809` has 8 raw reads and 0 writers by disp16, disp23, LE32 literal (`0xFEDF17F7`) and `movea gp` scans. Boot value: flash `0x868a7 = 00`. A prior kit record says V31P telemetry read it 0 in about 30k frames (taken from memory, not re-run).
2. Amplitude. LERP table `0xC6734`: n = 4, X = 0, 31872, 31936, 32000, Y = 0, 0, 0, 0. Identical in stock and V299. All 24 write sites of `gp-0x6b2c` are that LERP, a negation, or a zero store. A sign flip of zero is zero. The prior trace showed the 0x2A1FC addend is identically zero, so there is no bar-torque feedthrough.

Interaction with the angle loop and x6: none. A6 multiplies the PID path at 0x2A1EE and the addend is zero. Returning N to 17 changes a compare constant in an unreachable, zero-amplitude branch.

Name (BELIEF): a dormant Honda steering-wheel haptic vibration generator, meaning a square-wave torque at about 29 Hz with speed-indexed amplitude, enabled by a request flag that nothing sets in this variant. The V18 ledger label "re-engage ramp" was wrong. The safe direction is stock, and stock has the same effect as the current value.

Defect: ledger rows still quote `0xC64DE` as a halfword (25617 / 25627). It is a byte, 17 / 27.

## Method record

- Ghidra: `decompile_function(0x28ea6)` (1,309 lines, saved to scratch), `disassemble_bytes` dry_run over 0x28f20–0x290e8, 0x29a44–0x29aa4, 0x29cb4–0x29d90 and 0x29d8c–0x29f40, `search_instructions -0x682f` (12, equals raw scan), `get_xrefs_to(0xFEDF17D1)` (false zero).
- Python, scripts in `_scratch/lens_d9/` (each under 2 s): per-opcode disp16 scan, disp23 scan, LE32 literal scan, `movea gp` scan, parity-correct `ld.bu`; stock and V299 cell reads; `.data` boot values via the flash `0x86260` copy source.
- Not re-verified here: the V31P telemetry zero for `gp-0x6809`, and the "island is uncalled" claim (taken from the 2026-09-13 trace; indirect dispatch not excluded).
