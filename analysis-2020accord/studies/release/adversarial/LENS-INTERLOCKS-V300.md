# LENS: interlocks and downstream — release V300 (stock + angle loop), 2026-10-15

Lens: firmware-codepath-tracer (subagent). Ghidra program queried: `code.bin` (STOCK, the only program open; not switched). V300 image read by Python only (`_v300_V300-RELEASE-...A16C_plain_image.bin`). Nothing flashed, sent or edited. Scripts: scratchpad `lensint/li_scan.py` (0.9 s). Re-ran `h1_v300_built.py` (9.9 s).

## VERDICT: PASS_WITH_DEFECTS (no FAIL / do-not-flash finding)

### Pre-registered FAIL conditions (written before tracing)
- F1: a live stock check compares or ratios lane torque against a quantity that was map-scaled (x6) in V299 and is Honda-scale in V300, and the check is crossed only because of that mismatch.
- F2: a V300-changed cell is read on a path that executes while disengaged and alters delivered torque or arms a fault.
- F3: any stock monitor, clamp or governor threshold downstream of the aggregator differs from stock in V300 other than the A6/A7 cells, or the int and float EME twins disagree.
- F4: with the camera field != 2 the cave path returns a non-zero lane torque, or a stock camera can emit field == 2.
None fired.

## Q1 — EME shaper / governor / lockstep monitors (E: Python diff + Ghidra decompile)

Full stock-vs-V300 diff = 203 runs / 749 B (matches the builder). **No run lies in 0xC5000–0xC61AF or 0xC7000–0xE3FFF.** Code bodies byte-identical to stock: shaper+Monitor1+Monitor2 `0x42AF8–0x44A00`, governor+comp `0x4503C–0x45B30`, aggregator `0x3AA2C–0x3AD40`, energy budget `0x7B022–0x7C4F2`.

Chain from the aggregator (decompile `FUN_0003aa2c`): sum of lanes (each windowed) clamped +-0x2800 (code immediate) -> gp-0x6b94 (+ shadow gp-0x4ce0) -> governor `FUN_0004503c` (bound = auth * gp-0x4f64, gp-0x4f64 <= 5325 from cap table 0xC520C) -> gp-0x6ace -> comp -> gp-0x6acc -> shaper (final clamp +-0x2000 immediate) -> gp-0x6b98.

| threshold | address | stock | V300 |
|---|---|---|---|
| aggregate clamp | code imm 0x3AD0x | +-10240 | same |
| governor cap table X/Y | 0xC520C (24 B) | read | identical |
| slew 512/205 | 0xC6206/08 | | identical |
| monitor tol (FUN_00045a20) | 0xC602C | 0 | identical |
| Monitor2 gate | 0xC64A4 | 0 (armed) | identical |
| SM2 arm / int clamp / authority | 0xC6422 / 0xC61DC / 0xC61DA | 16384 / 30720 / 1092 | identical |
| final clamp | code imm +-0x2000 | | same |
| **corridor dir1/dir2 int** | 0xC674E/50, 0xC675A/5C | +-1024 | **+-5120** |
| **boost Y int** | 0xC6768/6A/6C | 0/1536/2048 | **5120 x3** |
| **float twins** | 0xC6598/9C/AC/B0, 0xC65C4/C8/CC | +-1.0, 0/1.5/2.0 | **+-5.0, 5.0 x3** |

- E: int/1024 == float for all 7 pairs on the V300 image (Python). The lockstep Monitor 1 (int) vs Monitor 2 (float) cannot diverge on these cells.
- E: the changed cells are the shaper's bound arms (max/min with the IIR arm). Raising them widens the allowed interval, so V300's soft-EME interval contains stock's at every instant. V300 cannot trip the soft-EME integrator where stock would not.
- E: the monitors compare two copies of the SAME chain (Monitor 1/2: pre- vs post-clamp copy; FUN_00045a20: gp-0x6acc vs gp-0x6ace; FUN_0004595a: |gp-0x6b94| vs |gp-0x6ace| and sign). None compares lane torque with a base-assist-derived bound. A base-assist lane returning to Honda scale does not enter any of them differently from stock.
- B: the ladder (5120) sits below governor ceiling + comp (5325 + 2560); a sum of lane 2461 + Honda assist + comp above 5120 would wind the integrator (15361 count-ticks to SM2). The same ladder with Honda banks is the V38..V267 configuration that flew; V299's banks differed (D8, V268). Not re-simulated.
- DEFECT D-2 (disclose): A7 weakens Honda's excessive-motor-effort protection about 5x (1024 -> 5120), in manual driving as well as engaged. It is the V38 package and permissive-only, but the release page must say so.

## Q2 — plausibility checks; the demand-byte crux (E: Ghidra disassembly + two scans)

**The census premise is wrong, so the V299 -> V300 scale mismatch does not exist.**
- `gp-0x682f = min(|gp-0x4f60 >> 5|, 255)`, the driver bar torque. Disassembly (dry-run) `0x28F26 ld.h -0x4f60,gp,r15`; `0x29048 mov r15,r7`, `0x2904A sar 5`, `0x29056..0x29064` saturate to 0xFF, `0x29068 st.b r8,-0x682f,gp`. r15 is not a destination in 0x28F26..0x29048 (all instructions read). The decompiler's `iVar28` is reassigned: line 68 `iVar28 = gp-0x4f60`; the map LERP uses other variables.
- Writers: exactly 0x29068 and 0x290B8 (store r0). Raw LE scan (disp16, op class, tp/gp) finds 16 gp-0x682f sites (2 W, 14 R; Ghidra `search_instructions` found 12; the other 4 are in 0x29C56/29CC8/2AB4A/2ABBE and are `gp-0x6830` neighbours by parity). Every site is byte-identical to stock in V300. Independent agreement with `LENS-SIDECHANNELS-D9-D6-D7.md`.
- `gp-0x69ae` (the E4 demand, clamp(-4*raw, +-0x4000)): V300 sites 0x29032 (LIM clamp -> uVar33, used only as `!= 0`/`== 0`), 0x29124 (range test +-0x4000), 0x29D6A (the angle loop), 0x4E840 (a diagnostic response packer, read-only, no compare), 4 writers in `FUN_00052676` (RX handler). Nothing ratios it against lane torque.
- Readers of lane torque gp-0x6b38: 0x2A23C/0x2A2EA (forward, store), 0x2A934/0x2B418 (uncalled island), 0x4E8D2/0x4E8E2 (same diagnostic packer, copy only). No compare.
- DTC 0x49 counter (`gp-0x6758`): gated by `0xC64B8 (=255) < gp-0x682f`, never true; V37 package intact. The `jr 0x29CC4` idx bypass at 0x29A7C likewise never fires.
- Other lane-torque watchers (FUN_00070a98 DTC 0x26 delivery consistency, thresholds 3000 cycles) are stock code and cells; B: unaffected (V282..V299 flew the same x6 lane with no DTC).
- Result: D9 revert is safe; the "x6 demand byte" never existed. No F1.

## Q3 — power-on / manual driving (E: reader scan of every kept cell, Python + Ghidra)

V300 is NOT byte-stock when disengaged; it is stock-equivalent on delivered torque except for A7 (below). Every kept non-stock cell:

| cell | reader(s) in V300 | disengaged effect |
|---|---|---|
| A6 gain 0xC6CD0 | 0x2A1EE only | multiplies the PID output; PID skipped when disengaged (0x29A50/56: run iff ramp != 0 and request==1; else `jr 0x2A164`) -> 0 |
| A6 clamp 0xC61B4 | 0x2A20C/1F8 (lane), 0x2A91E.. (island) | same lane output |
| 0xC61B2 | 0x2B436.. island only | dead |
| ICL 0xC61BA, Ki 0xC63E6, DB 0xC62E4 | cave region 0x29D6E..0x29DA0 (PID block) | PID block only |
| fb filter a/b/C 0xC63E8/EA, 0xC62E6 | 0x28F86..0x28FB8 | **every tick**: updates filter state gp-0x3d30/r26; no torque output when PID skipped; gp-0x6a34 only read in the gp-0x680a==1 lane (0 writers) |
| D4 0xC62EA | 0x28EBC | engagement gate only (needs a request) |
| D6 cells | 28EA6 debounce/arb SM (+ uncalled twin) | needs request; can only suppress faults |
| A2 edits | 0x28F4E every tick: x := theta; bail test +-12000 now on theta (bail zeroes gp-0x682f, same as stock bail) | state only |
| A7 ladder | 0x42F6E.., 0x43066.. and float 0x44384.. | **runs every tick in manual too**: permissive (see D-2) |
| A5 fade 0xE54FC, Kp/Kd records | taper stage / PID block | PID/lane path only |
| F181 string | diagnostic only | none |

Delivered torque while disengaged = stock base assist + 0. The only live difference in manual driving is the wider EME interval. Disengage transient (D-4): the A2 guard removes the stock 0.5 s ramp-out of the PID; the lane output goes to zero as soon as the request drops (V298 design, flown).

## Q4 — camera interlock with a stock camera (E: cave bytes, golden mirror, trace)

- E: `TRACE-2026-10-01-camera-0xE4-byte2-census`: 6,898,004 stock-camera 0xE4 frames over 95 routes, field bits 3:2 only 0 or 1, zero frames with 2 or 3. So a stock camera always takes the CAM branch (F4 not triggered). B: the census is all this car/camera; a different camera is unverified.
- E: V300 cave bytes `0xC4C5A: e0c9 e235` = `cmp r0,r25 ; be CAM`; CAM block `0xC4CC8`: `0082` mov 0,r16 (E'=0); `00d2` mov 0,r26 (fb operand = 0); `24373192` ld.w gp-0x6dd0 (I); `a632` sar 6; `8031` subr r0,r6 (r6 = -(I>>6)); `b607aa50` jr 0x29D7E. Stock code at 0x29D7E: `cmp r10,r6` with DB=0 -> I-input = -(I>>6); then `mul Ki(40)`, `>>3`, so I' = I>>3 *(1 - 40/64) = 0.375 per tick, as the lead stated (V298 docstring "0.125" is stale). P = E'*Kp = 0. D operand (0x29EE0, `mov r26,r8`) = 0. Lane torque -> 0 within a few ticks through the output lag. H1 mirror on the V300 image: camera cases 0/738 mismatches, negative controls fire (re-run, 9.9 s).
- E: the CAM branch never reads the camera's torque as a setpoint: E is replaced by 0 before the branch. The stock rate path (Honda map) is NOT entered; the E4 edit is permanent.
- DEFECT D-3: with a stock camera V300 does NOT behave as stock Honda LKAS. It behaves as LKAS-inert plus Honda base assist. This is the interlock's purpose (no E4 map path exists any more), so a stock camera cannot steer the car. The brief's expectation "must behave as stock" cannot hold. Not a safety fault; a functional statement for the release page.

## Defects (non-blocking)
- D-1: census D9 text is wrong (gp-0x682f is bar torque); correct before publishing (sidechannels lens already says so).
- D-2: EME protection widened 5x in all driving, disclose.
- D-3: stock camera = LKAS inert, not stock LKAS.
- D-4: no ramp-out of the lane on request drop.
- D-5 (B): r16/r26 forced to 0 at CAM entry and exit can give one tick of D discontinuity (D = Kd*r26); bounded by the D clamp; field flips only happen at engage/disengage.

## Not verified here
- No dynamic simulation of Honda assist + lane 2461 + comp against the 5120 ladder (B).
- Island `0x2A30E–0x2B421` dead is taken from the 2026-09-13 trace.
- Cave bytes decoded by hand around the CAM block; the whole-cave equivalence rests on the H1 interpreter result, not on my decode.
