# TRACE 2026-09-09 — the Kp / Kd schedule X axis: what it is, where its knots fall, what an edit costs

Agent `reqaxis` (subagent of `main`). GhidraMCP only (`code.bin` @ `/code.bin`, plus raw-byte reads of the
stock and V280r2/V281r3/V282/V284/V288r2/V289 images). `gp = 0xFEDF8000`, `tp = 0xBF000`.
Script: `rlog-tools/studies/grind/kpkd_axis_r62_r63.py` → `rlog-tools/studies/grind/_scratch/kpkd_axis_r62_r63.txt`.

---

## 0. Entry point and goal

**Entry point.** The two LERP records the brief names — Kp `0xE5378`, Kd `0xE511C` — reached backwards
through their pointer banks, and the index register that walks them, traced backwards to the CAN wire.

**Goal.** Name the X axis in physical units, place its knots on the measured wire, prove the record is the
live one, price an edit in bytes, and recover the history of the two records.

---

## 1. BYTE FACTS — all four confirmed, one correction to how they are *addressed*

**[EVIDENCE — raw LE byte read of six images; `dump3.py`/`kpkd_axis_r62_r63.py` `rec()`]**

The record layout is **`n` (u16) · `X[0..n-1]` (u16) · `Y[0..n-1]` (u16) · 2-byte pad**, i.e.
`X[0]` at `rec+0x02` and `Y[0]` at `rec+0x02+2n`. This is not inferred from the byte pattern (which is
ambiguous — the naive "u32 header then X then Y" split also fits and gives a *different, wrong* answer);
it is read from the instructions:

```
0x29DDE  sld.hu 0x2, ep, r9      X[0] at rec+0x02   (ep = record base)
0x29DE2  add    0xc, r10         &Y[0] = rec+0x0C   (= rec+0x02+2*5, so n = 5 is compiled in here)
0x29DF4  sld.hu 0x8, ep, r6      X[4] (ep = rec+0x02 by then)  -> the high clamp
```

So the brief's numbers are right as given:

| record | bank | slot 7 base | n | X | Y (stock) | Y (V281r3 → V289) |
|---|---|---|---|---|---|---|
| **Kp** | `0xCB994` | `0xE5378` | 5 | `0, 68, 112, 136, 208` | `248, 512, 645, 696, 696` | `248 ×5` |
| **Kd** | `0xCB7D4` | `0xE511C` | 4 | `0, 11, 22, 32` | `128 ×4` | `128 ×4` (never edited on a flown build) |
| assist map | `0xC9A88` | `0xE502C` | 10 | `0,12,20,24,32,64,96,128,160,240` | `0,24,42,50,62,100,126,154,166,172` | `0,52,86,103,138,275,413,550,688,1032` |

Record strides: Kp 24 B, Kd 20 B, map 44 B. Slot-7 pointers resolved by `*(u32)(bank + 4*7)`.

**The four banks the brief asked about are a DIFFERENT axis and must not be confused with these.**
[EVIDENCE — decompile `FUN_00028ea6` lines 850/901/1054, plus slot-7 record dumps]

| bank | slot-7 record | X | Y | key | role |
|---|---|---|---|---|---|
| `0xCBAE4` | `0xE54FC` | 24,45,64,80,96,112 | 255,205,164,125,90,51 | `gp-0x682f` = \|driver torque\|>>5 | post-PID fade A (driver-torque axis) |
| `0xCBBC4` | `0xE564C` | 16,26,38,48,64,96 | 255,243,218,179,77,77 | `gp-0x682f` | **post-PID fade B — the LIVE override fade** |
| `0xCBB54` | `0xE55A4` | 0,3,6,8,10,20 | 255,255,255,255,255,205 | `gp-0x6830` = grab-rate | post-PID fade (grab axis) |
| `0xCBC34` | `0xE56F4` | 0,3,6,8,10,20 | 255,255,255,255,255,205 | `gp-0x6830` | post-PID fade (grab axis) |

They multiply the **PID sum** (each `>>8`, then the `0xC61BE` = 15360 sum clamp) and are indexed by
**driver torque / grab rate**, never by demand. Two more banks sit *upstream* of the index and DO shape it:
`0xCB924` (same-sign) / `0xCB8B4` (opposite-sign) — the setpoint taper, X `32,42/38,80,112`, Y `255,255,255,0`,
also on the driver-torque axis. `0xCB844` (`0xE51A8`) is the flat command envelope: 15360 stock, **16384 on
V280r2 and later**.

---

## 2. Q1 — WHAT IS THE X AXIS, IN PHYSICAL UNITS?

### 2.1 The path, hop by hop

Every hop below is from `disassemble_bytes` (dry_run) on `code.bin`; the whole span `0x29CA8–0x29EC0` and
`0x29000–0x29060` is **byte-identical in the V289 image** (sha256 of each span compared, `dump4.py`).

| address | instruction | effect on the traced value |
|---|---|---|
| `0x29032` | `ld.h -0x69ae, gp, r13` | `cmd` ← `gp-0x69ae`. Its sole producer is the 0xE4 RX handler `FUN_00052676`, which writes `clamp(wire STEER_TORQUE × −4, ±0x4000)`. **[EVIDENCE — prior tracer memory `reference_accord_fun28ea6_lkas_rate_pid_full_decode.md`, `reference_accord_can_rx_descriptor_table_and_vehicle_speed.md`; not re-disassembled this session — see §7]** |
| `0x29030` | `add r13, r16` | `LIM` = LERP(`0xCB844[7]`) — flat, so LIM = 15360 (stock) / **16384 (V280r2→V289)** |
| `0x29036` | `andi 0xffff, r16, r22` | `LIM &= 0xFFFF` |
| `0x2903A–0x29044` | `cmp/bgt/subr/cmovle` | `r22 = clamp(cmd, −LIM, +LIM)` |
| `0x29A80–0x29CB2` | 4-way bank select + LERP | `taper` = LERP(same-sign `0xCB924[7]` \| opposite-sign `0xCB8B4[7]`) at index `gp-0x682f` = `min(\|driver torque\|>>5, 255)`. Arm chosen by `sign(cmd)` vs `sign(gp-0x4f60)`; the second-level select `gp-0x6803 == 2` picks the **cliff** arms `0xCBA04/0xCBA74` instead, and openpilot sends that field 0, so the cliff arm is not selected. |
| (same block) | LERP on `tp+0x7974` = `0xC6974` | `spF` = grab-rate taper — **X `4,6,8,10` / Y `255,255,255,255`, FLAT, so spF ≡ 255** |
| `0x29CB4` | `mulu r6, r10, r0` | `taper × spF` |
| `0x29CB8` | `andi 0xffff, r10, r7` | `G = (taper × spF) & 0xFFFF` — max **65025** |
| `0x29CBC` | `mul r22, r7, r0` | `G × r22` (32-bit signed) |
| `0x29CC0` | `sar 0x10, r7` | `v = (G × r22) >> 16`, **arithmetic** |
| `0x29CD6` | `sar 0x6, r7` | `v >>= 6` |
| `0x29CD4/0x29CD8` | `mov 0x1,r8` / `cmovn -0x1,r8,r8` | `r8 = sign(v)` — saved, later multiplies the map output at `0x29D6C mulh` |
| `0x29CDC–0x29CF4` | `cmp/ble/bge` + `ld.bu tp+0x74f0 / 0x74f1` | `v = clamp(v, −cal(0xC64F1)=240, +cal(0xC64F0)=240)` |
| `0x29CFA` | `subr r0, r7` | **`idx = |v|`** |
| `0x29D12/0x29D14` | `zxb r22` / `st.b r22,-0x674b,gp` | `idx & 0xFF` published to `gp-0x674B` — **the ASSIST-MAP key** and the V277 wire tap |
| `0x29DDA` | `st.h r7,-0x697a,gp` | `idx` published as a halfword to `gp-0x697a` |
| `0x29DC6` | `mov 0xcb994, r10` | Kp pointer bank |
| `0x29DD0` | `sld.w 0x0, ep, ep` | record base = `*(0xCB994 + slot*4)` (slot from `ld.bu -0x674e,gp,r12` @`0x29CC4`, `shl 0x2` @`0x29CCE`) |
| `0x29DE8` | `zxh r7` | **Kp LERP key = `idx & 0xFFFF`** |
| `0x29E76` | `mov 0xcb7d4, r7` | Kd pointer bank |
| `0x29E92` | `mov r22, r13` | **Kd LERP key = `idx & 0xFF`** (the same `r22` written to `gp-0x674B`) |

**Bypass branch:** `0x29CC4` is entered when `gp-0x682f > cal(0xC64B8) = 112` (driver-torque LKAS kill) and
sets `r7 = 0` → `idx = 0`, so an override drives the schedule to knot 0 rather than freezing it.

### 2.2 The answer

> **The X axis of BOTH tables is the demand index `idx` — the rectified, taper-scaled, ±240-clamped
> openpilot 0xE4 STEER_TORQUE command. It is the SAME axis the assist map is indexed by (the map uses
> `idx & 0xFF`, Kp uses `idx & 0xFFFF`, Kd uses `idx & 0xFF`; the ±240 clamp makes all three identical).
> It is an ABSOLUTE VALUE (the sign is split off at `0x29CD8` and re-applied to the map output only).
> It is NOT the post-map setpoint, NOT |E|, NOT the feedback, NOT speed.**

Integer Python mirror, annotated (this is the code in `kpkd_axis_r62_r63.py::demand`, and it reproduces
the kit's independent `GI.demand_live` to **1.0000 frame agreement** on all three routes):

```python
S     = clip(-4 * round(wire_0xE4_STEER_TORQUE), -LIM, LIM)   # 0x52676 handler; 0x2903A..0x29044
tx    = abs(driver_torque) // 32                              # gp-0x682f
taper = lerp(taperS if sign(S)==sign(bar) else taperO, tx)    # 0x29A80..0x29CB2   (255 when hands-off)
G     = int(taper * 255) & 0xFFFF                             # 0x29CB4 mulu ; 0x29CB8 andi 0xffff
v     = floor(G * S / 65536)                                  # 0x29CC0 sar 0x10
v     = floor(v / 64)                                         # 0x29CD6 sar 0x6
v     = clip(v, -240, 240)                                    # 0x29CDC..0x29CF4  (cals 0xC64F1/0xC64F0)
idx   = abs(v)                                                # 0x29CFA subr r0,r7
Kp    = lerp(kp_X, kp_Y, idx)      # 0x29DE8..0x29E32, then P = clip(E*Kp>>8, +-15360)  [0xC61BC]
Kd    = lerp(kd_X, kd_Y, idx)      # 0x29E8C..0x29EDE, then D = clip(dE*Kd>>3, +-10240) [0xC61B6]
```

**Scale.** The total right-shift is 22 bits and the wire is pre-multiplied by −4, so

> **1 idx LSB = 2²² / G / 4 wire counts of 0xE4 STEER_TORQUE = 16.1257 counts at G = 255×255 = 65025.**

That is the origin of the kit's 16.126: it is exact, not empirical. `idx = 240` is reached at 3870 wire
counts, i.e. **just past the 0xE4 field's own ±3840 saturation** — the ±240 clamp is a hair above full
scale and effectively never binds before the wire does. openpilot's 123-count/frame slew cap is
**7.63 idx per 100 Hz frame**.

**G is 65025 on essentially all engaged driving** — measured p10/p50/p90 = 65025/65025/65025 on all three
routes; `taper < 255` on only 1.4 % / 2.1 % / 2.9 % of engaged frames (r62 / r63 / r5e). So on the wire the
axis is simply `idx = min(round(|cmd|)/16.1257, 240)`.

---

## 3. Q2 — THE KNOTS ON THE WIRE

### 3.1 Knots in wire units (live V289 cals)

| table | knot | idx | 0xE4 counts | rate setpoint (map Y, V289's LINEAR.TO6X) |
|---|---|---|---|---|
| Kp | X[0] | 0 | 0 | 0 |
| Kp | X[1] | **68** | 1097 | 292 |
| Kp | X[2] | 112 | 1806 | 482 |
| Kp | X[3] | 136 | 2193 | 584 |
| Kp | X[4] | 208 | 3354 | 894 |
| Kd | X[0] | 0 | 0 | 0 |
| Kd | X[1] | **11** | 177 | 48 |
| Kd | X[2] | 22 | 355 | 94 |
| Kd | X[3] | **32** | 516 | 138 |

Above `idx = 32` the Kd lookup takes its **high-clamp branch** (`0x29EA0 sld.hu 0x6,ep,r10` = X[3];
`0x29EB0 ld.hu 0x6,r8,r7` = Y[3]) — **Kd is unschedulable above idx 32 without moving an X knot.**

### 3.2 Time-in-interval, engaged, by regime

Routes `r62_v289` (619 s engaged), `r63_v289` (588 s), `r5e_v288` (642 s, V288 reference).
Regimes: (a) `|Δcmd| ≥ 122` counts/frame; (b) `2 ≤ v ≤ 5 m/s` and `70 ≤ |wheel angle| ≤ 140°`;
(c) `v ≥ 22 m/s` and `|angle| < 5°`; (d) `idx ≥ 20`; (d′) the census's own grinding episodes
(from `_scratch/grind1_census_v289_r62_r63_cache.pkl`, the same detector the V282/V288 censuses used).

**POOLED V289 (r62+r63), engaged — 1207 s:**

| Kp interval | share | seconds |
|---|---|---|
| `[0, 68)` | **91.1 %** | 1100 |
| `[68, 112)` | 3.5 % | 43 |
| `[112, 136)` | 1.3 % | 15 |
| `[136, 208)` | 2.5 % | 30 |
| `[208, →]` | 1.6 % | 19 |

| Kd interval | share | seconds |
|---|---|---|
| `[0, 11)` | **67.9 %** | 820 |
| `[11, 22)` | 11.7 % | 141 |
| `[22, 32)` | 4.6 % | 55 |
| `[32, →]` (clamped) | 15.8 % | 191 |

idx percentiles engaged: p5 = 0 · p10 = 1 · p25 = 2 · **p50 = 5** · p75 = 15 · **p90 = 58** · p95 = 118 · p99 = 239.

**By regime (r62 / r63 / r5e_v288), idx p10 / p50 / p90:**

| regime | seconds (r62/r63/r5e) | idx p50 | Kp `[0,68)` share | Kd `[32,→]` share |
|---|---|---|---|---|
| all engaged | 619 / 588 / 642 | 5 / 5 / 6 | 90.6 / 91.6 / 88.4 % | 15.0 / 16.6 / 18.9 % |
| **(a) capped step** | 27.4 / 26.2 / 29.0 | **110 / 86 / 88** | 27.9 / 39.5 / 37.6 % | 88.6 / 81.0 / 84.0 % |
| **(b) low-speed full-lock turn** | 16.5 / 6.5 / 11.4 | **123 / 74 / 98** | 26.7 / 47.3 / 31.3 % | 88.2 / 76.4 / 86.5 % |
| **(c) 25 m/s cruise** | 233 / 146 / 144 | **3 / 3 / 3** | **100 / 100 / 100 %** | 0.0 / 0.1 / 0.0 % |
| (d) idx ≥ 20 | 127 / 133 / 161 | 59 / 51 / 60 | 54.3 / 63.0 / 54.1 % | 73.1 / 73.5 / 75.3 % |
| **(d′) census grind episodes** | 12.5 / 13.0 / 97.5 | **8 / 46 / 37** | 74.9 / 69.3 / 69.9 % | 31.4 / 66.8 / 55.7 % |

Census episode line frequency on the V289 routes: p10/p50/p90 = 15.0 / **15.8** / 23.1 Hz (r62) and
16.0 / **16.7** / 19.1 Hz (r63), vs 15.6 / **20.0** / 20.9 Hz on r5e_v288 — the independent confirmation,
inside this analysis, that the line moved down on V289.

### 3.3 What this means for the lever

**[EVIDENCE for the numbers; BELIEF for the reading]**

1. **The Kp table as shipped has essentially no resolution where the car lives.** All four of its non-zero
   knots (68, 112, 136, 208) sit at or above the **p90** of engaged demand. 91 % of engaged time — and
   **100 %** of highway cruise — falls in the single segment `[0, 68)`, where the shipped Y values are
   `248 → 248`. A Y-only edit on this record therefore acts almost exclusively through **Y[0] and Y[1]**,
   and any Y[2..4] change touches < 5 % of engaged time. **A low-demand gain cut is not reachable by Y
   alone at usable resolution — it requires moving X[1] down**, exactly as V284 did (and V281 rev 2 before it).
2. **The Kd table is the opposite** — its knots 0/11/22/32 straddle the busy zone, splitting engaged time
   68 / 12 / 5 / 16 %. **Kd is the table with usable low-demand resolution as shipped**, and it has been
   `128` flat on every flown build in the arc. Given that V290's class is *phase margin at crossover*, and
   D is the lead term, this is the more directly relevant of the two records.
3. **The regimes separate cleanly.** Cruise (c) is entirely idx < 68 (p50 = 3); the capped step (a) and the
   full-lock turn (b) are entirely different populations (p50 86–123). **A schedule that cuts gain below
   idx ≈ 30 and returns to 248 by idx ≈ 68 would touch ~85 % of engaged time and ~100 % of cruise while
   leaving the pkR capped-step operating point (p50 idx 86–123) and the operator's full-lock bookmarks
   (p50 idx 74–123) almost untouched** — i.e. the authority floors in the standing V290 requirement are
   structurally protected by the axis itself.
4. **But the grinding episodes are NOT a high-demand population.** Their idx p50 is 8 (r62) / 46 (r63) /
   37 (r5e) and 70–75 % of their time is in `[0, 68)`. **The symptom the operator reports and the
   transient-authority operating point sit in DIFFERENT parts of the axis** — which is what makes the
   schedule a real degree of freedom rather than a disguised flat change. ⚠ r62's episodes skew much lower
   than r63's (p50 8 vs 46); with only 12 and 15 episodes this split is not resolved, and a design should
   not lean on either number alone.

---

## 4. Q3 — IS THE SCHEDULE LIVE?

**a) Slot 7 is the live slot.** [EVIDENCE, three independent routes]
- `gp-0x674e` is loaded at `0x29CC4` (`ld.bu`) and `shl 0x2` at `0x29CCE` — the same `r12` indexes the map
  bank at `0x29D02`, the Kp bank at `0x29DCC` and the Kd bank at `0x29E6E`. **One selector, all three banks.**
- The kit measured the live selector as **7** on the V276 wire (memory `accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire`).
- **The strongest evidence is behavioural:** slot 7's *map* record `0xE502C` is the one the V280r2+ builds
  rewrote to LINEAR.TO6X (`Y[9] 172 → 1032`), and the on-car result was the measured ×6 authority change.
  A firmware reading a different slot could not have produced that. Read back here from the V289 image:
  slot 7 map Y = `0,52,86,103,138,275,413,550,688,1032` — the edited curve.

**b) The LERP is executed every engaged tick.** `FUN_00028ea6`'s only caller is `FUN_0002214a`
(`get_function_callers`), which prior tracing established by two independent methods as the **1 kHz task**
(memories `reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget`,
`reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz`). The Kp/Kd block sits inside the
engagement gate at decompile line 761 (`(uVar18 != 0 || cVar15 == 1) && bVar3`); when the gate is false the
outputs are zeroed and the LERP is skipped. So: **1 kHz while laterally engaged, not at all otherwise.**
[EVIDENCE on the caller and the gate; the 1 kHz period itself is INHERITED from prior sessions, not re-derived here.]

**c) Nothing overrides the looked-up value.** Kp lives only in a register between `0x29E32 zxh r9` and
`0x29E36 mul r9,r8,r0` — there is no RAM cell for another writer to touch. The *only* thing downstream that
can mask it is the **P clamp `0xC61BC` = 15360** (`P = clip(E·Kp>>8, ±15360)`), which binds at
`|E| ≥ 15360·256/Kp` = 15 857 at Kp 248. The kit measured the P rail at **0.3 % of strong frames at Kp 248**
(V281 rev 3, r35) — so at today's gain the clamp is not hiding Kp. ⚠ **This is the mechanism that would make
a Kp *increase* read as "pinned"**, and it is the explanation the restart addendum offers for the 2026-09-08
"f pinned across Kp 248–696" evidence. Kd's own clamp is `0xC61B6` = 10240 (`D = clip(dE·Kd>>3, ±10240)`);
V287 rev 2 lowered it to 7680 and was never flown.

**d) The tp trap did bite once, and was caught.** I first read the P/D/sum clamps at `0xC71BC`/`0xC71B6`/etc.
— the documented off-by-0x1000. `tp = 0xBF000`, so `tp+0x71BC = 0xC61BC` (15360), `tp+0x71B6 = 0xC61B6`
(10240), `tp+0x71BE = 0xC61BE` (15360), `tp+0x73E6 = 0xC63E6` (Ki = 0). All match the kit's known constants
at the corrected base. **No conclusion in this trace rests on the wrong base** — the record addresses came
from pointer banks, not tp arithmetic. Recorded here because it is the fifth-plus recurrence.

**e) `search_instructions` was not used for any load-bearing null in this trace.** Every claim is either a
`disassemble_bytes` read, a decompile line, or a raw Python byte scan.

---

## 5. Q4 — WHAT WOULD A SCHEDULED EDIT COST IN BYTES?

**X and Y are SEPARATE arrays inside one record** (not interleaved): `X[0..n-1]` contiguous, then
`Y[0..n-1]` contiguous.

**Kp, record `0xE5378`, 24-byte stride:**

| field | offset | field | offset |
|---|---|---|---|
| n = 5 | `0xE5378` | — | — |
| X[0] | `0xE537A` | Y[0] | `0xE5384` |
| X[1] | `0xE537C` | Y[1] | `0xE5386` |
| X[2] | `0xE537E` | Y[2] | `0xE5388` |
| X[3] | `0xE5380` | Y[3] | `0xE538A` |
| X[4] | `0xE5382` | Y[4] | `0xE538C` |
| pad `0x0000` | `0xE538E` | | |

**Kd, record `0xE511C`, 20-byte stride:**

| field | offset | field | offset |
|---|---|---|---|
| n = 4 | `0xE511C` | — | — |
| X[0] | `0xE511E` | Y[0] | `0xE5126` |
| X[1] | `0xE5120` | Y[1] | `0xE5128` |
| X[2] | `0xE5122` | Y[2] | `0xE512A` |
| X[3] | `0xE5124` | Y[3] | `0xE512C` |
| pad `0x0000` | `0xE512E` | | |

**Cost.** One Y knot = **2 bytes** (often 1 changed byte in practice — V285's five Y writes of 248 → 0
moved only the five low bytes, since 248 = `0x00F8`). Plus **one 4-byte page CRC**.

**CRC page.** [EVIDENCE — `build_v284_tva.py` `KP_PAGES`/`EDIT_PAGE` + `V53.owning_block`, and V285's
byte diff in `docs/BUILD-LINEAGE.md`] The 28 records of each family are spread over five separately-CRC'd
4 KB pages: `0xE4000` slots 0–5 · **`0xE5000` slots 6–11** · `0xE6000` 12–17 · `0xE7000` 18–23 ·
`0xE8000` 24–27. Trailer at `page + 0xFFC`.

> 🛑 **Both slot-7 records — Kp `0xE5378` AND Kd `0xE511C` — are in the SAME page `[0xE5000, 0xE5FFC)`.
> A combined Kp+Kd slot-7 edit costs ONE CRC trailer (`0xE5FFC`), not two.** A slot-7-only edit leaves the
> other four page CRCs bit-unchanged.

Worked example (V284, the precedent): 4 X knots + 2 Y knots = 12 payload bytes / 6 runs + `0xE5FFC` = 16 B total.

> 🛑 **HARD GATE, inherited and re-confirmed here: `0x29E2C divq r6,r9` (Kp) and the matching `divq` in the
> Kd walk divide by the SEGMENT WIDTH `X[i] − X[i−1]`. X MUST be strictly increasing** — a duplicate knot is
> a divide-by-zero in the 1 kHz task. V285's audit found all 17 `divq` in `FUN_00028ea6` divide by an X-axis
> segment width and **no Y value is ever a divisor**, so a Y-only edit cannot create one.

---

## 6. Q5 — HISTORY OF THE TWO RECORDS

**`0xE5378` (Kp slot 7)**

| build | what | flown? | on-car |
|---|---|---|---|
| stock … V280 rev 2 | X `0,68,112,136,208` · Y `248,512,645,696,696` | **FLOWN** (r32/r33/r34) | best authority; slight oscillation on strong turns; highway lane change oscillates; 7 Hz ring present, F7 4.3–8.1/100 s; zero stalls |
| **V281 rev 2** | X → `0,24,68,136,208` · Y → `248,341,341,341,341`, **all 28 records** | BUILT, SUPERSEDED, **never flown** | — |
| **V281 rev 3** | **Y = Y[0] ×5 (flat 248)**, X untouched, all 28 records | **FLOWN** (r35) | oversteering largely gone · **prolific understeer** · stuttering and rare attenuated grinding still present · a pronounced grind at 23:48:21. Measured: **the self-sustained 7 Hz cycle GONE (F7 0.0/100 s)**; P rail 0.3 % of strong frames (vs 31 %) |
| V282 / V283 | untouched (cave repoint / Ki 50) | flown | — |
| **V284** | X → `0,32,36,44,88` · Y → `248,248,512,512,248`, **slot 7 only** | BUILT, four-way adversarial pass, **🛑 SHELVED — DO NOT FLASH** | never driven |
| **V285** | Y → `0 ×5` (Kp = 0) | BUILT, **bench / system-ID config, DO NOT FLY** | never driven |
| V287–V289 | untouched (flat 248) | V288/V289 flown | — |

**The recorded reason V281 rev 3 flattened it** [EVIDENCE — `docs/BUILD-LINEAGE.md` §V281 rev 3]:
operator instruction *"I want Kp on the LKAS PID completely flat, flattened to demand index 0's value"*,
sized in `analysis-2020accord/studies/v280/KPFLAT-SIZING-2026-09-03.md` against the **6–8 Hz strong-turn
ripple** (18 episodes on r32/r33/r34), identified as the inner loop's crossover with P linear 60–80 % and
no clamp. **It was flattened to kill a 7 Hz oscillation, and it did — F7 went to 0.0.**

> 🛑 **THE ANSWER TO "would re-introducing a schedule re-introduce that": YES, if the schedule RAISES gain
> at the demand indices where the 7 Hz ring lives — and that is where the stock schedule's rise is.**
> Stock rises 248 → 696 across idx 68–208, and the 7 Hz strong-turn ring's index mass is spread 40–112
> (V284's A11.2 tabulation). The lineage's own verdict, from V284's shelving, is blunt:
> **"GAIN IS SPENT AS A LEVER ON THIS LOOP. Do not raise Kp anywhere without a fresh margin measurement."**
> Measured ring loop gain at flat Kp 248 = **0.976 [0.944–0.990]** at the 7.3 Hz strong-turn ring —
> **2.5 % of headroom**.
>
> The *converse* — CUTTING gain below idx ≈ 30 and returning to 248 by idx ≈ 68 — is a **different, never-flown
> direction**. It spends no margin (it only removes gain), it does not re-arm the 7 Hz ring (it moves the
> wrong way), and by §3.2 it lands on ~85 % of engaged time and ~100 % of cruise while leaving the capped-step
> and full-lock operating points alone. **[BELIEF — this is a reading of the measured distributions plus the
> recorded margin, not a stability calculation. A cut still lowers crossover frequency, and V281 rev 3's own
> on-car cost of a Kp cut was "prolific understeer" and a P-only deadband. Nobody has measured what a cut
> confined to idx < 68 costs in lane keeping.]**

**`0xE511C` (Kd slot 7)**

- 🛑 **NOT virgin, but never flown edited.** V279 / V279 rev 1 set it to **0** — confounded and unflown, so
  it carries no on-car evidence. **Kd has been 128 on every FLOWN build in the arc.**
- **V286** (spec written 2026-09-04, **never built**) proposed `0xE511C` Y `128 → 160` at
  `0xE5126/28/2A/2C` — 8 payload bytes + the `0xE5FFC` page CRC = 10 bytes total. That spec is the closest
  existing precedent for a Kd edit and already carries its own byte plan.
- Ziegler–Nichols work on V285 estimated **`Ku` ≈ 227 as an `0xE511C` cell value, [217–270], `Tu` ≈ 36 ms**
  — i.e. today's 128 is ~0.56 `Ku`. **[reported from `build_v285_tva.py`'s docstring; not re-derived here.]**
- **No build has ever put a non-flat shape on the Kd record.** Its X knots (0, 11, 22, 32) are already where
  the demand lives, so a Kd *shape* is reachable by a Y-only, 2-bytes-per-knot edit — unlike Kp.

---

## 7. Open questions / verification needed

1. **`gp-0x69ae = clamp(cmd × −4, ±0x4000)` was NOT re-disassembled this session.** It is taken from prior
   tracer memory (`FUN_00052676`, the 0xE4 RX handler). Everything in §2.2's scale (the 16.1257 counts per
   LSB) depends on that `×4`. **Next step:** `decompile_function 0x52676` and confirm the `shl 0x2` /
   `subr` and the `±0x4000` clamp against the bytes. The independent corroboration I do have is that
   `idx = 240` then lands at 3870 wire counts, within 1 % of the 0xE4 field's own ±3840 saturation — a
   coincidence that would not hold with any other factor.
2. **The 1 kHz tick rate of `FUN_0002214a` is inherited, not re-derived here.** Confirming it means finding
   the timer ISR/OS task that calls `FUN_0002214a` and reading its reload from the SVD-named timer.
3. **P-rail duty per knot interval is not measured in this trace.** The kit's 0.3 %-of-strong-frames figure
   is a whole-population number at flat Kp 248. Before sizing any Kp Y change, the duty should be computed
   **inside each knot interval** (the sizing script would need the simulated `E`, i.e. the 1 kHz feedback
   mirror already in `grind_incident_r35.simulate`).
4. **The grind-episode idx distribution disagrees between the two V289 routes** (p50 8 vs 46, n = 12 and 15).
   Resolving that needs more V289 episodes, or the r5e_v288 population (n = 46, p50 37) treated as the
   better-powered estimate of where grinding sits on the axis.
5. **The second-level taper select `gp-0x6803 == 2`** (cliff arms `0xCBA04/0xCBA74` vs soft arms
   `0xCB8B4/0xCB924`) is taken from memory as "openpilot sends that field 0". I read the branch structure
   this session but did not trace `gp-0x6803`'s writer. It only matters at the ~2 % of engaged frames where
   the driver is on the wheel hard enough for the taper to leave 255.

---

## 8. Files

- Script: `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\rlog-tools\studies\grind\kpkd_axis_r62_r63.py`
- Output: `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\rlog-tools\studies\grind\_scratch\kpkd_axis_r62_r63.txt`
- This trace: `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\docs\traces\TRACE-2026-09-09-kp-kd-schedule-axis.md`

---
---

# VERIFICATION SECTION — agent `scalecheck`, 2026-09-09

Added by agent `scalecheck` (subagent of `main`) **after `reqaxis` closed out.** `reqaxis`'s text above is
left exactly as written; anything I correct is marked **CORRECTION** below. GhidraMCP only (`code.bin`,
confirmed the active program via `list_open_programs`), raw-byte second method in Python.

**Job:** close `reqaxis`'s own open question §7.1 — the `×(−4)` on `gp-0x69ae` was taken from prior tracer
memory and never re-disassembled, and the whole 16.1257 counts-per-index-LSB scale rests on it.

## V.0 VERDICT

> 🛑 **THE `×(−4)` IS CONFIRMED FROM THE BYTES. The scale `16.125736` wire counts per index LSB STANDS
> EXACTLY. `reqaxis`'s §2.2, §3.1 and §3.2 need no correction and no knot moves.**

## V.1 The 0xE4 handler, re-derived from the bytes

`decompile_function 0x52676` → `disassemble_function 0x52676` (decompile first, then assembly, per the
standing rule). The producing block, verbatim from Ghidra:

```
000526c6: jarl 0x00021724,lp        ; r10 = raw 16-bit STEER_TORQUE  (see V.2)
000526ca: mov r10,r6
000526cc: sxh r6                    ; SIGN-EXTEND 16 -> 32   <- STEER_TORQUE is SIGNED
000526ce: movea -0x4000,r0,r7       ; lo = -16384
000526d2: shl 0x2,r6                ; r6 = raw << 2                      <- the "4"
000526d4: subr r0,r6                ; r6 = 0 - r6  =>  -4 * raw          <- the "-"
000526d6: movea 0x4000,r0,r8        ; hi = +16384
000526da: jarl 0x00049a90,lp        ; r10 = clamp(r6, lo, hi)
...
000526f2: st.h r10,-0x69ae[gp]      ; gp-0x69ae = clamp(-4 * raw, +-16384)
```

**[EVIDENCE]** `gp-0x69ae = clamp(−4 · wire STEER_TORQUE, ±0x4000)`. The factor is **−4**, built as
`shl 0x2` + `subr r0` — *not* a multiply, which is why an operand-text search for a `mul` would have
missed it. `reqaxis`'s inherited value was right.

**No overflow anywhere in the chain:** `|raw| ≤ 32768` (after `sxh`) → `|−4·raw| ≤ 131072`, computed in
32 bits before the clamp; then `|S| ≤ 16384` and `G ≤ 65025`, so the `0x29CBC mul` product
`|G·S| ≤ 1 065 369 600 < 2³¹` — the discarded high word of the V850 `mul` is provably sign-only, and the
`sar 0x10` at `0x29CC0` operates on an exact signed value. **[EVIDENCE — arithmetic on byte-read bounds]**

### The clamp helper is a real 3-argument clamp

```
00049a90: cmp r8,r7            00049a9e: cmp r7,r6            00049aa6: cmp r6,r8
00049a92: cmovgt r8,r10,r10    00049aa0: cmovlt r7,r10,r10    00049aa8: cmovge r6,r8,r10
00049a96: cmovgt r7,r8,r8      00049aa4: blt 0x00049aac       00049aac: jmp [lp]
00049a9a: cmovgt r10,r7,r7
```

The first three `cmovgt` order `(r7, r8)` into `(min, max)`; the rest return `clamp(r6, min, max)`.
**[EVIDENCE]** So `FUN_00049a90(v, lo, hi) = clamp(v, lo, hi)`, and the incoming `r10` that Ghidra's
decompile surfaces as a phantom `in_r10` parameter is a cmov staging artefact whose value is always
overwritten — consistent with memory `reference-accord-clamp-helpers-and-packer-scratch`.

## V.2 What is read out of the frame — width, order, sign

```
00021724: prepare { r28,lp },0x0
00021728: jarl 0x0001fa42,lp        ; (critical-section enter)
0002172c: ld.bu -0x1428[gp],r14     ; frame byte 0
00021730: ld.bu -0x1427[gp],r28     ; frame byte 1
00021734: shl 0x8,r14
00021736: or r14,r28                ; value = (byte0 << 8) | byte1   -- BIG-ENDIAN
00021738: jarl 0x0001fa72,lp        ; (critical-section exit)
0002173c: mov r28,r10
```

Two **unsigned byte** loads assembled **big-endian**, then sign-extended by the caller's `sxh`.
**[EVIDENCE]**

**Independent confirmation that this is the 0xE4 STEERING_CONTROL buffer and that the field is signed
16-bit**, from the fork's own DBC
(`.../StarPilot/opendbc_repo/opendbc/dbc/honda_accord_2017_can_ext_generated.dbc`):

```
BO_ 228 STEERING_CONTROL: 5 ADAS
 SG_ STEER_TORQUE         : 7|16@0- (1,0) [-3840|3840]
 SG_ STEER_TORQUE_REQUEST : 23|1@0+
 SG_ SET_ME_X00           : 22|7@0+
```

`7|16@0-` = bytes 0–1, big-endian, **signed** — bit-for-bit what `FUN_00021724` + `sxh` build. And
`STEER_TORQUE_REQUEST` at bit 23 = **byte 2, bit 7**, which the handler stores as
`*(gp-0x6805) = u8[gp-0x1426] >> 7` (`0x526F0 shl 0x18` / `0x52702 shr 0x1f`) — the kit's known
STEER_REQUEST cell. So `gp-0x1428` is 0xE4 byte 0, and the buffer mapping is confirmed from two
directions. **[EVIDENCE]**

### ⭐ This also CLOSES `reqaxis`'s open question §7.5 (`gp-0x6803`)

From the same handler block:

| cell | firmware expression | 0xE4 bit-field |
|---|---|---|
| `gp-0x6805` | `byte2 >> 7` | `STEER_TORQUE_REQUEST` |
| `gp-0x6804` | `(byte2 << 0x19) >> 0x1f` = bit 6 | `SET_ME_X00` bit 6 |
| **`gp-0x6803`** | `(byte2 << 0x1c) >> 0x1e` = **bits 3:2** | **`SET_ME_X00` bits 3:2** |
| `gp-0x6802` | `byte2 & 3` | `SET_ME_X00` bits 1:0 |

`create_steering_control` in `opendbc/car/honda/hondacan.py` packs **only** `STEER_TORQUE` and
`STEER_TORQUE_REQUEST` (`STEER_DOWN_TO_ZERO` is `tja_control`-only and absent from this car's DBC), so
`SET_ME_X00` is packed as 0 and **`gp-0x6803` is 0 on every frame openpilot sends.** The cliff taper arms
`0xCBA04`/`0xCBA74` (selected on `gp-0x6803 == 2`) are therefore **unreachable under openpilot** — now
EVIDENCE on both halves, firmware and fork, rather than memory. This independently re-confirms memory
`accord-the-override-taper-arm-is-selected-by-a-0xe4-field-openpilot-sends-0`.

## V.3 The rest of the chain, re-read from the bytes

`disassemble_bytes` (dry_run) over `0x29020–0x29060` and `0x29CA8–0x29D20`; every claim from the
instruction bytes:

| address | bytes | instruction | effect |
|---|---|---|---|
| `0x29032` | `246f5296` | `ld.h -0x69ae,gp,r13` | `cmd` ← signed halfword (`ld.h` sign-extends) |
| `0x29036` | `d0b6ffff` | `andi 0xffff,r16,r22` | `LIM &= 0xFFFF` |
| `0x2903A–44` | — | `cmp/mov/bgt/subr/cmp/cmovle` | `r22 = clamp(cmd, −LIM, +LIM)` — re-read, confirmed |
| `0x29CB4` | `e6572202` | `mulu r6,r10,r0` | `taper × spF` |
| `0x29CB8` | `ca3effff` | `andi 0xffff,r10,r7` | `G = … & 0xFFFF` |
| `0x29CBC` | `f63f2002` | `mul r22,r7,r0` | low 32 bits of `G × S` (high word discarded, provably unused) |
| `0x29CC0` | `b03a` | `sar 0x10,r7` | arithmetic `>> 16` |
| `0x29CD6` | `a63a` | `sar 0x6,r7` | arithmetic `>> 6` |
| `0x29CD0` | `8587f174` | `ld.bu 0x74f0,tp,r16` | `+cal(0xC64F0)` — **tp = 0xBF000, so `0xC64F0`, not `0xC74F0`** |
| `0x29CE6` | `a587f174` | `ld.bu 0x74f1,tp,r16` | `−cal(0xC64F1)` |
| `0x29CFA` | `8039` | `subr r0,r7` | `idx = abs(v)` |

`sar 16` then `sar 6` composes to exactly `floor(x / 2²²)` for negative `x` as well
(`floor(floor(x/2¹⁶)/2⁶) = floor(x/2²²)`), so the total is a clean 22-bit arithmetic right shift.

**Cal values, raw LE byte reads of the stock, V288r2 and V289 images**
(`rlog-tools/studies/grind/scalecheck_x4_r62_r63.py`):

| cal | stock | V288r2 | V289 | note |
|---|---|---|---|---|
| `LIM` = `0xCB844[7]` → `0xE51A8` | Y **flat 15360** (n = 9) | flat **16384** | flat **16384** | flat ⇒ its own key is irrelevant |
| `spF` = `0xC6974` | X `4,6,8,10` / Y **flat 255** | same | same | confirms `spF ≡ 255` |
| `0xC64F0` / `0xC64F1` | **240 / 240** | 240 / 240 | 240 / 240 | the ±240 index clamp |

**Every code span is byte-identical stock vs V289** — `0x526C6–0x526F6`, `FUN_00049a90`, `FUN_00021724`,
`0x29020–0x29060`, `0x29CA8–0x29D20`. **[EVIDENCE — Python `bytes ==`]**

## V.4 The scale, and the two cross-checks

> **1 idx LSB = 2²² / G / 4 = 4194304 / 65025 / 4 = `16.125736` wire counts of 0xE4 STEER_TORQUE.**
> `reqaxis`'s **16.1257 is CONFIRMED**, exactly, not empirically.

**Cross-check (a) — the firmware's own constants are 4× wire-domain limits.** Stronger than `reqaxis`'s
version of this argument, because it does not depend on the ±240 clamp:

- handler clamp `±0x4000` = **16384 = 4 × 4096** — 4 × the 12-bit natural range of the field;
- **stock** `LIM` cal = **15360 = 4 × 3840** — 4 × the DBC's own declared `STEER_TORQUE` limit `[-3840|3840]`;
- and the `LIM` record's own X axis contains **`X[3] = 3840`**, the wire limit a third time.

Independent constants, in two different functions, each **exactly** 4× a wire-domain bound. No other
factor reproduces them. And the ±240 clamp lands at `|raw| = 3870.2`, 0.8 % past the wire's ±3840 —
`reqaxis`'s own check, reproduced.

Worked, from the images: at the wire maximum `|raw| = 3840`, `idx = 238` on **both** stock and V289
(V289's looser `LIM = 16384` only matters for `|raw| > 3840`, which openpilot never sends). **The ±240
clamp never binds on the wire; the wire saturates first.**

**Cross-check (b) — exact integer mirror vs the kit's `GI.demand_live`, on the caches.**

> ⚠ **METHOD CAVEAT, stated because the brief asked for this as an "independent" check and it is not one:**
> `grind_incident_r35.demand_live` hard-codes `S = clip(-4.0 * round(cmd), ±LIMIT)` — **the same `−4`.**
> Its 1.0000 agreement with `reqaxis`'s mirror could never have falsified the factor. It checks the
> clamps, shifts, taper arms and 16-bit masks; the factor is confirmed by V.1 and by cross-check (a).

Running a bit-exact integer mirror of the disassembly (`idx_exact()` in the script, one line per
instruction address) against `GI.demand_live` on the three route caches:

| route | engaged | exact-int vs `GI.demand_live` | max abs diff | empirical counts/LSB (hands-off, p50) | G p10/p50/p90 |
|---|---|---|---|---|---|
| `r62_v289` | 619 s | 0.9985 | **1** | 16.102 | 65025/65025/65025 |
| `r63_v289` | 588 s | 0.9965 | **1** | 16.148 | 65025/65025/65025 |
| `r5e_v288` | 642 s | 0.9920 | **1** | 16.153 | 65025/65025/65025 |

The 0.2–0.8 % of frames that differ do so by **at most one index unit** — `GI.demand_live` LERPs the
taper in float where the firmware truncates through `divq`. Immaterial at every knot. The empirical
counts-per-LSB read off the measured wire (16.10–16.15) matches the derived **16.126** to 0.2 %.

Engaged-time shares, knot positions and regime splits in `reqaxis` §3.1–§3.3 therefore **stand unchanged**.

## V.5 Corrections and residual caveats

1. **CORRECTION (cosmetic, §2.1 table).** `reqaxis`'s hop table lists `0x29032` before `0x29030`; the
   real order is `0x29030 add r13,r16` (the LIM LERP tail) *then* `0x29032 ld.h -0x69ae,gp,r13`, which
   reuses `r13`. No consequence.
2. **CORRECTION (§2.1, `0x29030` row).** The `0xCB844[7]` record `0xE51A8` is **n = 9**, X
   `3200,3413,3627,3840,4736,5632,6528,7424,8320`, not a scalar. Its Y is **flat**, so `LIM` is a
   constant and its key never mattered — `reqaxis`'s conclusion is unaffected, but "flat" was asserted
   without the shape being shown.
3. **NOT re-traced, and immaterial here:** which sign the taper-arm select compares. `reqaxis` writes
   "`sign(cmd)` vs `sign(gp-0x4f60)`"; `GI.demand_live` and my mirror both use `sign(S) = −sign(cmd)`.
   The two arms (`0xCB924` X `32,42,80,112` / `0xCB8B4` X `32,38,80,112`, Y identical `255,255,255,0`)
   differ at **one knot**, and `taper < 255` on only 1.4–2.9 % of engaged frames, so the arm choice
   cannot move any conclusion in this trace. **[BELIEF that it is immaterial; EVIDENCE for the two
   records' contents.]** Resolving it needs the writer of `gp-0x4f60` and the branch at `0x29A80`.
4. **A latent, currently-harmless mismatch in the kit's model.** `v280_map_profiles.LIMIT` is the module
   constant **16384**, and `GI.demand_live` uses it for every build. That is the **V280r2-and-later**
   cal; **stock / pre-V280 `LIM` is 15360.** It is harmless today because the handler's own ±16384 clamp
   plus openpilot's ±3840 send limit mean the two only differ for `|raw| ∈ (3840, 4096]`, which is never
   sent. **Flagged, not fixed** — a future study replaying a pre-V280 route with a command source that
   can exceed 3840 would over-read `idx` at the top of the range.
5. `search_instructions` was not used for any load-bearing claim in this verification.

## V.6 Files

- Script: `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\rlog-tools\studies\grind\scalecheck_x4_r62_r63.py`
- Output: `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\rlog-tools\studies\grind\_scratch\scalecheck_x4_r62_r63.txt`
