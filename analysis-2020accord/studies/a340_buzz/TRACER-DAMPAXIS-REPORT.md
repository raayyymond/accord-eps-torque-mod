# TRACER REPORT - A340 DampAxis chain (T1-T5), 2026-11-17, subagent tracer-dampaxis-a340
Read-only study. GhidraMCP for all decompile/disasm (programs `A340_stock.bin`, `code.bin`=A160 stock); bytes via Python on the images.
Scripts (seconds each): `analysis-2020accord/_scratch/out/a340_buzz/{t1*.py,t4.py,scan.py,scan2.py,loop.py,loop2.py}`.
Positive controls run: tp-scanner finds the known 0xC40D4 reader at 0x421A8 (A340) and 0xC40DC reader (A160); gp scanner finds all 27 `gp+0x63fd` sites Ghidra lists.
EVIDENCE = read from image bytes / decompile / controlled scan.  BELIEF = inference.

## HEADLINE (read this first)
**The 13 "DampAxis" bytes were ported by ADDRESS ANALOGY. On A340 the pointer-table index that selects them (26/27) is chosen by DIFFERENT chassis keys than on A160.**
- EVIDENCE: the consumer (A340 FUN_00037794 @0x377CC `ld.bu gp+0x63fd`; A160 FUN_00036c12 @0x36C4A) picks its record as `ptr[mode]` from 0xCBE40 (A340) / 0xCBE74 (A160); `mode` = gp+0x63fd is written by FUN_000432c8/FUN_00043214 (A340; A160 twins 42746/42692) from the variant table at 0xCD012+row*0x24, where row = match of the 5-byte coded ID (gp+0x6408..0C) against keys at 0xCD000+row*0x24 (FUN_0005904a, 29 rows on A340). Columns e012..e015 = mode for (gp-0x67bc,gp-0x67a8) = (0,1),(0,2),(1,1),(1,2): cols 0/1 = MANUAL, cols 2/3 = ENGAGED (BUILD-LINEAGE RULE 6/1443: A160 "mode 24 = MANUAL, mode 26 = ENGAGED").
- A160 row 11 key 'TVCA4' = [24,25,26,27]  -> the operator's car (the only A160 row that contains 26/27; RULE 6 already showed the car is NOT row TVAA1/mode 10).
- A340 (image bytes): modes 26/27 are selected ONLY by rows 25,26 = keys 'TWAA0','TWAA1' = [26,26,27,27] (manual=26, engaged=27 - BOTH EDITED). A340 'TVCA4' (row 19) = [16,17,18,19]; 'TVCA3'/'TVCX0'/'TVCA6' (rows 17,18,20) = [24,24,25,25]; all 'TVAL*/TVAX*/TVAY*/TVAK*' rows = modes 4..11. **None of those touch records 26/27.**
- All 34 records in the ptr table are byte-identical on stock A340 AND A160 (-9830,-5734,-1966; X 0,1280,5760); REV 3 edits ONLY records 26 and 27 (0xD7A5C, 0xD7A6C) - checked by diffing all 34 records in the REV3 image.
=> If the third-party car is coded TWAA0/TWAA1, DampAxis is live in BOTH manual (mode 26) and engaged (mode 27) at x3.0 / x3.0 / x8.1 of stock = matches "buzzes engaged AND in manual near centre, not on stock, not on A160 car (which uses TVCA4 = 24 manual/26 engaged, and was flown)". If the car is any other key, the rows are INERT and DampAxis reduces to the single byte 0xC40D4 22->14 (which my analysis says is not the buzz maker, see T3).
- **NEXT STEP (cannot be done by tracing): learn the car's coded 5-byte ID (gp+0x6408..0C; not in the flash dump) - car model/trim (Hybrid?), or a UDS/EEPROM read, or a probe of gp+0x63fd.** This single fact decides H1.

## T1 - DampAxis chain constant by constant (A340 stock | A160 stock | A340 REV3 | A160 V300 rev2)
| item | A340 | A160 | notes |
|---|---|---|---|
| producer / consumer | FUN_00041fe6 / FUN_00037794 | FUN_00041464 / FUN_00036c12 | decompiles structurally identical (EVIDENCE); same call order in the 1 kHz task body (FUN_00022240 vs FUN_0002214A: producer slot 4 ... consumer slot 0x1f, aggregator 0x20, governor 0x21) |
| rate input | gp-0x4ea8 (writer FUN_0006a07a from gp-0x2920) | gp-0x4f50 (FUN_00068fbe from gp-0x29c4) | twin writers; plausibility limits 0xC4912/14 = 5500/5000 = A160 0xC491A/1C (same) => same units (EVIDENCE for equal limits, BELIEF same scale) |
| alpha1 (EMA of rate*1024, >>7) | tp+0x745A = 0xC645A = 37 | tp+0x743C = 0xC643C = 37 | stock, REV3 and V300 all 37; 2nd reader at 0x4271C (A340) / 0x41B1A (A160) = slot-5 sibling |
| difference | (E1new-E1old)*32, clamp +-0xFA0000 | same | acc_est = 64 * dRate_filtered per tick (EVIDENCE, derived below) |
| alpha2 (EMA of diff, >>6) -> gp-0x6bfc | 0xC40D4 = 22 (stock) -> **14 (REV3)**; sole reader 0x421A8 | 0xC40DC = 22 -> 14 (V300); sole reader | tp+0x50D4 / tp+0x50DC; controlled scan |
| sibling alpha (>>7) -> gp-0x6bfe | 0xC40D2 = 3 | 0xC40DA = 3 | unchanged both |
| rate-invalid | |rate|>13000 -> states zeroed, gp-0x6bfc/fe := 0x7FFF | same | |
| consumer gate | gp-0x66e0 < 0xFF and gp-0x67ba==1, then gp-0x66e0 < *(0xC654D)=5 | gp-0x671a, gp-0x67f4==1, < *(0xC64FD)=5 | |
| fallbacks | not-enabled: 0xC6422 = -3277 ; code>=5: 0xC6420 = -8192 (unedited) | 0xC640C=-3277 ; 0xC640A=-8192 | same values; neither image edits them |
| speed axis | gp-0x6a2e (writer FUN_00042A6E @0x42EC4) | gp-0x6a5e (FUN_00041EEC @0x42342) | twin writers (BELIEF same 64 ct/km/h); X knots 0,1280,5760 (=0,20,90 km/h) |
| Y rows (stock) | -9830,-5734,-1966 all 34 records | same all 34 | |
| Y rows edited | 0xD7A5C,0xD7A6C := -29490,-17202,-16000 (REV3) | same (V300) | x3.0, x3.0, x8.14 of stock; edited records are ptr[26]=0xD7A54, ptr[27]=0xD7A64 on BOTH (A340 ptr base 0xCBE40, A160 0xCBE74; both tables byte-identical content) |
| multiplier / clamp | out = ((acc*Y)>>6)*0x111 >>18, clamp +-*(0xC407E)=511 | same, 511 | = Y*1.6276e-5*acc = **Y*1.0417e-3 * dRate_f(counts/tick)** => -10.24 (stock Y0), -30.72 (REV3 Y0) per count/tick; Y2: -2.05 stock vs -16.67 REV3 |
| output | gp-0x6af6 | gp-0x6b26 | |
| selector writer(s) | FUN_000432C8 (4 stores), FUN_00043214 (init), FUN_0004B31A (boot/coding cmd) | FUN_00042746, 42692, 4A798 | |
Sample rate: both producer and consumer are called from the SAME task function on each firmware (A340 FUN_00022240 only caller of both; A160 FUN_0002214A) with identical statement order -> same rate on both (EVIDENCE structure; the 1 kHz figure is A160 kit knowledge, BELIEF for A340).

### Mode selection tables (A340 image bytes, rows of 0xCD000+r*0x24; mode cols = [manual,manual,engaged,engaged])
| A340 key (row) | modes | A160 key (row) | modes |
|---|---|---|---|
| TVAL0/1/2, TVAX0 (1-4) | 4,4,5,5 | TVAA0 (1) | 4,4,5,5 |
| TVAL3/4, TVAX2 (5-7) | 6,6,7,7 | TVAA1 (2) | 10,10,11,11 |
| TVAY*(8-14) | 8,8,9,9 | TVAC1 (3) | 10,10,11,11 |
| TVAY5, TVAK0 (15,16) | 10,10,11,11 | TVCA0 (9) | 16,16,17,17 |
| TVCA3 (17), TVCX0 (18), TVCA6 (20) | 24,24,25,25 | TVCA3 (10) | 22,22,23,23 |
| TVCA4 (19) | 16,17,18,19 | **TVCA4 (11) = operator car** | **24,25,26,27** |
| TVCY0 (21) | 12,12,13,13 | TWAA0/1 (13,14) | 28,28,29,29 |
| TVCY2, TVCK0/1 (22-24) | 14,14,15,15 | TWAA2 (15) | 30..33 |
| **TWAA0, TWAA1 (25,26)** | **26,26,27,27 <- EDITED** | | |
| TWAA3 (27) / TWAA4 (28) | 20..23 / 28,28,29,29 | | |
(A160 TVAA1 = mode 10 was the assumption RULE 6 falsified; A160 car engaged mode is 26.)

## T2 - Downstream of gp-0x6af6 (A340) / gp-0x6b26 (A160)
EVIDENCE: raw-scan + Ghidra search_instructions give identical reader sets (control: the producer's own ld/st found):
1. Aggregator FUN_0003B5AE (A340, slot 0x20) / FUN_0003AA2C (A160): `+(short)gp-0x6af6 * (|v+0x400| < 0x801)` summed UNSCALED (x1) with the other lane terms in the `else` branch of gp-0x6772/gp-0x67AC (<2 ==1 branch excludes it); clamp +-0x2800 (0xD800 on the low side); store gp-0x6b64 (A340) / gp-0x6b94 (A160).  Lane gain into the sum = 1.0 on both.
2. gp-0x6b64 -> FUN_0003776E (EMA x0x40, 0xC63EA..), FUN_00045BBE governor (A160 FUN_0004503C), FUN_000464DC, FUN_00080FC4 (A160 4595A, 36BEC, 7FF08 twins). Governor FUN_00045BBE/0004503C: decompiles are structurally identical (rate-limit ramps, `(sum - gp-0x4ebc*u17>>15)*u6>>15`, store gp-0x6a9e / gp-0x6ace; only gp/tp displacements differ). Gain = ratio of two ramp values (<=1, = 1 unity when both at 0x8000).
3. Other lane consumers: FUN_000378F6 (A340; A160 36D74) = lockstep copy /1024 float monitor; FUN_00038CCA (A340; A160 38148) = torque observer weight 0xC63B8 (A340) -> gp-0x6b40 (plausibility side). Neither is the motor path.
End-to-end lane gain to the governor output: **x1 on both; ratio A340/A160 = 1.0** (EVIDENCE through the governor; stages after gp-0x6a9e/0x6ace were NOT traced - I did not find an A340-only stage up to there; BELIEF that the final motor stage is the twin of A160's). So tripled rows give x3 lane torque (per acc) on A340 exactly as on A160.
Sibling lane 0xC40D2/gp-0x6bfe: unchanged by REV3; its consumers not traced (no edit, so not a REV3 differentiator).

## T3 - Sign and limit-cycle
EVIDENCE (decompile): out = -(|Y|*1.0417e-3) * dRate_f. Y<0 on every row, so the lane torque is **-d(rate)/dt: it OPPOSES acceleration (adds virtual inertia)** on both firmwares, same convention (identical code, same sign of Y). BELIEF: whether "positive command accelerates positive gp-0x4ea8 rate" (sign of the plant) - not traced; the kit calls this the damper/inertia lane.
Loop structure (BELIEF-grade modelling, EVIDENCE-grade constants): derivative of a rate that is itself the integral of the torque => L(z) = g*LP1(0.289)*LP2(alpha2/64)*z^-d, a gain with two lags and d samples of delay, NOT a damper. Numerics (loop.py, 1 kHz):
- alpha2=22 (stock): -180 deg at 130 Hz (d=2, g_crit=5.4) / 91 Hz (d=3, g_crit=3.2); d=1 never crosses.
- alpha2=14 (REV3): -180 deg at 116 Hz (d=2, g_crit=7.0) / 81 Hz (d=3, g_crit=4.0). 116 Hz aliases to 16.0 Hz and 81-83 Hz to 17-19 Hz at 100 Hz sampling: **matches the measured 16.7 Hz / 83 Hz**.
- alpha2 22->14 RAISES g_crit (more HF attenuation) but ADDS 10-30 % low-frequency anti-damping (2-20 Hz: x1.3 at 5 Hz, x1.13 at 20 Hz; loop2.py): a lagged -K*acc feedback is negative damping w*|F|*sin(lag). Rows x3 => x3 loop gain (x8.1 at 90 km/h).
- A saturating clamp (+-511) fixes the amplitude independent of speed/rows = constant-amplitude limit cycle, as observed. Unknown without a plant J: whether stock g sits between g_crit/3 and g_crit (BELIEF: it must, if the rows are live, since stock does not buzz).

## T4 - REQUEST-OFF AUDIT of V300-A340 REV3 (diff of [0x13000,0x100000): 842 bytes, 139 groups)
| group (address) | what | can it change motor cmd at request=0? |
|---|---|---|
| 0x13109-0x1310D | F181 string `39990-TVA,A34C` | no (ID) |
| 0x292F0 E1 (x := gp-0x69c8 angle) | filter input at the top of FUN_00029230, runs EVERY tick | filter state gp-0x3C8C/3C90/3C87/3C88 touched only inside FUN_00029230 (raw scan, positive-controlled): output r26 is consumed only after the gate. NO |
| 0x29E68 B2, 0x29E6E A2 | B2: r8 = request==1 ? elig : 0 ; A2 `bne`->`be`: PID path runs iff ramp!=0 AND r8!=0 else `jr 0x2A596` | gate, see below: skips, NO new output |
| 0x2A334 E4, 0x2A340 HOOK, 0x2A3D4 OPH, cave 0xC4C00 | all lie after 0x29E80 on the run path | unreachable at request 0 once the gate skips (EVIDENCE: A340 stock disasm 0x29E60-0x29E7C: `setfe r8 / bne 29E78 / ... jr 0x2A596`) |
| 0x2A622 A6 (0xC6E88=5328, clamps 0xC61C0/C2 3072) | x6 authority on r15 after 0x2A5A6 (common to skip path) | multiplies only the decaying output-lag state (below). NO sustained term |
| 0x2961E/0x29630 D6b | DTC-0x49 counter gate | fault path only |
| 0xC61C1.. 0xC61D0-D5, 0xC6504-08 | clamps / STEER_STATUS debounce (SM readers 0x2965C-0x296FA, 0x2AF86..) | LKAS status machine; not the assist path |
| 0xC62F6/F8, 0xC63F8/FA | A4 fb-lag/deadband: readers 0x29328/2C/38/3E/5A, 0x2A338.. all in FUN_00029230 | NO (b: output is a register, state private) |
| 0xC63FC/FE out-lag | readers 0x2A5A6/0x2A5AA in the skip path | decays to 0 via pole; no leak |
| 0xC40D4 | alpha2 22->14 | **YES - acts in manual** (producer runs whenever the task mask allows and rate valid) |
| 0xD7A5C/0xD7A6C | rows 26/27 | **YES in manual ONLY if mode==26 (TWAA* keys, col 0/1)**; else inert |
| 0xC679E-0xC67BD, 0xC65EA-0xC661E (A7 EME ladder, boost floor, f32 mirrors) | readers 0x43BE8/43C00/43C48/43C60/43AF0/43B08 (FUN_0004367A EME shaper) | acts on the TOTAL command (incl. manual), but only RAISES limits (+-1024 -> +-5120, floor 0 -> 5120); cannot add torque by itself (BELIEF; shaper's 54 KB decompile not read) |
| 0xC6C05-0xC6C1C | dir-2 fades (u8 tables, read via pointer at ~0x2A072) | LKAS hand fade; request-gated lane (BELIEF) |
| 0xC6E88, 0xC6FFC, 0xC4FFC, 0xD7FFC, 0xE4FFC, 0xE5FFC.. | private cell / CRC trailers | no |
| 0xE460A..0xE5D1C (36x3 records: Kp 0x20->0x30?, Kd, Ki) | LKAS PID gains scheduled by FUN_0002A740 | lane only; gated |
At request=0 the skip target 0x2A596 zeroes r23/r29/r27/r13 and the 0x7FFFFFFF sentinel, writes gp-0x6B02/04/06/FE := 0, and runs the output lag on zero input (state gp-0x3C9C decays by its pole 0xC63FC/FE, x6 stage then x0). Nothing rings or leaks after the lag decays (EVIDENCE: disasm 0x2A596-0x2A5E6; decay length not measured). Stock ran the PID while ramp!=0 even at request 0; REV3 skips it immediately - that is a difference but not a buzz source.
(d) DampAxis acts in manual: producer yes; consumer yes via gate gp-0x67ba==1 && gp-0x66e0<5 (row LERP) else the unedited fallbacks -3277/-8192.
Caveat: the two uncalled-by-me LKAS-side functions that read 0xC61C0/C2 (FUN_0002BFA4 = LKAS state machine gp-0x3C84, FUN_0002C0FC) were not traced to their outputs.

## T5 - A340 vs A160 differences affecting the loop gain near centre
- EVIDENCE: lane->aggregate->governor chain, rate source, constants (alpha1, 0xC407E, 0x111, fallbacks, plausibility limits) are identical => the damper lane gain per count is the same on both.
- EVIDENCE: the mode map differs (above). It is the decisive A340-only fact.
- NOT traced (open): A340 base-assist bank 0xCE000-0xD9FFF differs by 7487 B (the base friction/damper factor tables FUN_00034ED2 vs A160 FUN_00034350, selected by the same gp+0x63fd mode); if A340's stock base damping at TWAA modes is lower than A160's TVCA4, the same x3 inertia feedback would leave less natural damping to absorb the lag-induced anti-damping. BELIEF; needs the factor tables for modes 26/27 (A340) vs 26/27 (A160).

## RANKED HYPOTHESES for "A340 buzzes, A160 does not"
1. (BELIEF, strong, hinges on one unknown fact) The user's car is coded TWAA0/TWAA1: the ported rows 26/27 are its manual AND engaged mode => x3/x3/x8.1 inertia-feedback with lag -> 80-116 Hz saturating limit cycle (alias 16-19 Hz), constant amplitude (+-511 clamp), strongest when wheel acceleration is large (return to centre) - fits manual-only-near-centre and engaged-still. Falsifier: any other key, or gp+0x63fd observed != 26/27. EVIDENCE for every link except the car's key.
2. (BELIEF) Same cause but the car is TVC* / other: then the rows are inert and DampAxis = alpha2 only; alpha2 14 adds 10-30 % low-f anti-damping on a plant with less damping than the A160 car (T5 open). Weak: A160 V300 carries the same alpha2 and flew.
3. (BELIEF, low) A7 ladder/clamps in manual on a different A340 plant: they only raise limits; unlikely.
4. (Process) The A160 V300 DampAxis rows were exercised only in engaged mode 26/27 on a TVCA4 car; they were never validated on any car whose manual mode is an edited row (A340 TWAA is the first). The port used "same addresses" (REV2 docstring) instead of re-deriving the mode map - the RULE 6 failure class.
Suggested fix (for the orchestrator, not done): re-derive which A340 modes are the user's engaged/manual modes from the user's key, and either restore rows 26/27 to stock or edit the records that key actually selects; add the key/mode to the build docstring.
