# H1 — "OP is just switching between two points on that torque table; as you scale it they get further apart, so you lose resolution" — TESTED

Subagent `hyptable`, 2026-09-09. Analysis only: nothing built, nothing flashed, nothing sent.
Script: `rlog-tools/studies/grind/h1_table_resolution.py` (output `_scratch/h1_table_resolution.txt`, per-window
arrays `_scratch/h1_table_resolution_windows.npz`). Images read: stock `code.bin`, `_v112_…`, `_v282_…`, `_v289_…`
under `ACCORD_FIRMWARE_ROOT/analysis-2020accord/`. Wire: routes r39 (V282) and r5e_v288 (V288 rev 2) — the assist
map and the whole rate loop are byte-identical on V282 / V288 / V289 (checked in §A), so these caches answer for V289
too. Census yardstick = `grind1_census_v282.py`'s recipe via `wire_0xe4_20hz.episodes_of` (2 s windows / 0.5 s step,
present = 15–26 Hz prominence ≥ 8 AND bar 18–22 ≥ 40 raw).

## Verdict, first

**H1 is FALSE as a mechanism for the grinding, under every reading I could give it.** [EVIDENCE, methods below]

| reading | what it would need | what the bytes / wire say |
|---|---|---|
| (a) the EPS assist map loses resolution when scaled | steps between table points that grow with the scale and produce a 20 Hz tone | the index quantiser sits **before** the map and is **map-independent** (1 idx LSB = 16.19 raw counts on every build); the LERP is continuous at every knot; the integer truncation is ≤ 1 setpoint count on both maps and is 6× *smaller* relative to the setpoint on the 6× map; the map's whole quantisation residual, pushed through P and the gain, is **2.3–2.5 output counts** at 18–22 Hz and **does not change between grinding and baseline windows** (2.34 vs 2.38, 2.54 vs 2.39), while the measured 18–22 Hz torque on the tap is **29–30 counts** in grinding — 12× larger (3× even against the Ms = 3.8 resonance bound) |
| (b) an openpilot table dithers between two knots | a command-indexed table with a knee on the Accord path | the Accord's only command-indexed table is `torqueBP/torqueV = [0,4096]/[0,4096]`: `np.interp` is the **identity** (max error 0), then `int()` → 1 LSB = 1/4096. Every other `np.interp` in `latcontrol_torque.py` is indexed by speed or |lat-accel|. Scaling that table is a no-op |
| (c) 0xE4 alternates between two values | ±1 alternation runs, 100 ms windows on exactly two values | in grinding windows the command changes on **96–98 %** of frames; |Δcmd| is 16–63 counts on 41 % of frames and slew-capped (≥ 122) on 13–21 %; ±1 alternation fraction **0.000** (p50), longest alternating run 0–3 frames; fraction of 100 ms windows on exactly two command values **0.000**, on exactly two idx values **0.000**, on one idx value **0.000** |
| (d) the line's frequency / presence should track the map scale and the command cadence | f set by the dither cadence, absent or 6× weaker on the stock map, no Kp dependence | f0 **20.03–20.08 Hz** on map ×2 concave (V278r3) and ×6 linear (V280r2/V281r3/V282/V288); f0 uncorrelated with the idx bin-crossing rate inside grinding windows (ρ 0.00 / 0.18 while the rate spans 65–97 /s); the band was already named on the **stock map** in the V62 and V112 eras; ζ falls 0.036 → 0.019 with **Kp**, which a pre-loop quantiser cannot do; and **V288 made every setpoint step ~11× finer and the grinding did not move** (258 vs 239 ep/h, f 20.06 vs 20.03) |

What H1 gets right, in one sentence: scaling the map raises the loop gain per command count, and the record shows the 20 Hz
mode loses damping with loop gain — but that is a **gain** effect, continuous in the command, not a **resolution** effect;
making the steps finer (V288) changed nothing, and making them coarser (stock, ×2) did not remove the line.

---

## A. The bytes — the assist map and its LERP, mirrored from the disassembly [EVIDENCE]

Method: `disassemble_bytes` (dry run) on stock `code.bin` 0x29CB0–0x29D7C inside `FUN_00028ea6`, then integer Python; the
map/Kp/Kd records and cal cells read from the four images with `struct` little-endian; the four images' pointer family
`0xC9A88` is identical (28 slots, slot 7 → `0xE502C`).

```python
# 0x29032 ld.h  -0x69ae[gp]       CMD (signed); ±L clamp 0x29036-0x29044     (−4·cmd = the CAN decode stage, kit mirror v280_map_profiles.demand)
S  = clamp(-4*cmd, -16384, +16384)
r7 = (taper*speedF) & 0xFFFF      # 0x29CB4 mulu, 0x29CB8 andi   taper 254 (same-sign LERP, |bar| < 2240), speedF 255
r7 = (r7 * S) >> 16               # 0x29CBC mul,  0x29CC0 sar 0x10
r7 = r7 >> 6                      # 0x29CD6 sar 0x6
r7 = clamp(r7, -240, +240)        # 0x29CDC-0x29CF4, cal 0xC64F0 = 240 (ld.bu 0x74f0 / 0x74f1 parity pair)
idx = abs(r7)                     # 0x29CF6 cmp, 0x29CFA subr;  published st.b -0x674b[gp] @0x29D14
# 0x29CFC mov 0xc9a88,r16 ; 0x29D06 sld.w -> record ; X[0] @+2, Y[0] @+0x16
if idx <= X[0]:  sp = Y[0]        # 0x29D22 cmp r10,r9 ; bh
elif idx >= X[9]: sp = Y[9]       # 0x29D2E cmp r13,r9 ; bnc
else:                             # 0x29D36/0x29D48 knot walk while idx >= X[k+1]
    sp = Y[k] + ((idx - X[k]) * (Y[k+1] - Y[k])) // (X[k+1] - X[k])   # 0x29D58 sub, 0x29D5C sub, 0x29D5E mul, 0x29D64 divq, 0x29D68 add
sp = sign * sp                    # 0x29D6C mulh r13,r16 ; 0x29D72 st.h -0x6a32[gp]
E  = (sp << 5) - fb               # 0x29D76 shl 0x5 ; 0x29D78 sub r26
```
`divq` truncates toward zero; every operand is ≥ 0 here, so it floors. There is no other rounding, shift or width loss
between the CAN byte and `E`: the only places resolution is lost are the `>> 22` that makes the index and the floor in
the LERP.

**A0. The maps (slot 7, X knots identical on all four images):**

| image | Y at X = 0,12,20,24,32,64,96,128,160,240 | Kp knots | fb pole |
|---|---|---|---|
| stock, V112 | 0 24 42 50 62 100 126 154 166 172 | 248 512 645 696 696 | 923/1560 |
| V282, V289 | 0 52 86 103 138 275 413 550 688 1032 | 248 flat | 923/1560 (V289: 875/2301) |

V282 and V289 carry the same map bytes; V289 differs from V282 only in the fb pole and the notch cave.

**A1. Index quantisation — map-independent.** 1 idx LSB = 2^22 / (64770·4) = **16.19 raw 0xE4 counts** (0.40 % of 4096);
measured bin widths over cmd 0..4096: 16 or 17 counts, idx 240 at cmd 3886, idx = 0 for |cmd| ≤ 16. **This is the only
quantisation the command meets before the map, and no build has ever changed it** (cal `0xC64F0` = 240 on all four).

**A2. Setpoint LSB.** E = 32·sp − fb; fb DC = 2·1560/(1024−923) = 30.89 per raw rate count; 8 raw counts per deg/s ⇒
**1 sp count = 0.1295 deg/s on every build.** Through P alone (Kp 248, gain 5346>>15) one sp count is 31 P counts →
5.06 output counts (out clamp 3072, tap LSB 8).

**A3. Per-idx setpoint step, per interval (sp counts / deg/s / output counts through P):**

| interval (idx) | Δcmd (raw) | stock | V282/V289 |
|---|---|---|---|
| 0–12 | 194 | 2.000 / 0.259 / 10.1 | 4.333 / 0.561 / 21.9 |
| 12–20 | 130 | 2.250 / 0.291 / 11.4 | 4.250 / 0.550 / 21.5 |
| 24–32 | 130 | 1.500 / 0.194 / 7.6 | 4.375 / 0.567 / 22.1 |
| 32–64 | 518 | 1.188 / 0.154 / 6.0 | 4.281 / 0.554 / 21.7 |
| 64–96 | 518 | 0.812 / 0.105 / 4.1 | 4.312 / 0.558 / 21.8 |
| 128–160 | 518 | 0.375 / 0.049 / 1.9 | 4.312 / 0.558 / 21.8 |
| 160–240 | 1295 | 0.075 / 0.010 / 0.4 | 4.300 / 0.557 / 21.8 |

The 6× map's per-idx step is 2.15× stock's at low idx and up to 57× at the top — that is the map's **gain**, exactly the
thing the record calls the reference lever. The **relative** resolution (step / value) is the same on both maps by
construction (same X, Y scaled), 0.19 at idx 6, 0.04 at idx 30, 0.008 at idx 120.

**A4. Integer truncation.** sp_fw − sp_exact ∈ [−0.97, 0] sp counts on both maps (≤ 0.126 deg/s). Per-idx steps: stock
{0 ×104, 1 ×102, 2 ×32, 3 ×2}; V282 {4 ×168, 5 ×72}. So the 6× LERP "jitters" between slopes 4 and 5 per idx; the stock
LERP sits on a genuine staircase above idx 160 (a step every 13 idx). **The coarser staircase is the STOCK map's.**
A knot is a slope change, never a jump — "straddling a breakpoint" moves sp by the local slope only.

**A5. The one real cost of scale.** A 1-idx step is a one-tick E step of 32·Δsp: D = (ΔE·128)>>3 = 2202 (V282) vs 1024
(stock, low idx) for one 1 kHz tick, ×0.163 → 359 vs 167 output counts for 1 ms, then the 5.05 Hz output lag (×~0.03 for a
single tick). The D clamp (10240) binds at |ΔE| ≥ 640 = 4.6 idx per tick; a slew-capped frame is 7.6 idx. The **cap**
(openpilot's 0.03/frame), not the LSB, sets the kick — and V288 removed 97 % of those binds with no effect on the grind.

## B. The openpilot side [EVIDENCE, read from the operator's fork `openpilots/raayyymond-StarPilot/StarPilot` @ 0f98d8c7, branch Dom]

- `opendbc/car/honda/interface.py`, `elif candidate == CAR.HONDA_ACCORD:` → `torqueBP, torqueV = [[0, 4096], [0, 4096]]`.
  `values.py` `CarControllerParams.__init__` mirrors it: `STEER_MAX = 4096`, `STEER_LOOKUP_BP = [-4096, 0, 4096] = STEER_LOOKUP_V`.
- `carcontroller.py` `apply_torque = int(np.interp(-limited_torque * STEER_MAX, STEER_LOOKUP_BP, STEER_LOOKUP_V))` — the
  interpolation is the identity over the whole range (max |interp(u) − u| = 0 on 20 001 points); `int()` truncates toward
  zero: **1 LSB = 1/4096 = 0.024 %**, 16× finer than the EPS's own index quantiser.
- `rate_limit(torque_cmd, last, ±STEER_DELTA_UP·DT_CTRL)` = ±0.03/frame = **122.88 raw counts/frame** — the cap the wire
  study measured at 123.
- `latcontrol_torque.py`: every `np.interp` on the Accord path is indexed by speed (`KP_INTERP`, `LOW_SPEED`, roll-offset
  fade) or |lat-accel| (centre-chatter weight); none is indexed by the command, so none can alternate between two knots at
  100 Hz. The Accord rate-plant FF is a filter (`FirstOrderFilter`, 0.10 s), not a table.

**There is no scaled table on the openpilot side.** The "two points" the colleague may have in mind are literally the two
points of the identity table [0, 4096] — and scaling both ends together changes nothing.

## C. The wire — r39 (V282, 880 s engaged, 79 episodes) and r5e_v288 (642 s, 46 episodes) [EVIDENCE]

Raw 0xE4 on its own dejittered 100 Hz frame counter (`wire_0xe4_20hz.load_route`; resid p50 1.6 ms), per 2 s census
window; "grinding" = episode-majority windows (310 / 171), "baseline matched" = engaged, v < 12 m/s, |bar| < 400 raw (771 / 245).

| statistic (p50 over windows) | r39 grinding | r39 baseline | r5e grinding | r5e baseline |
|---|---|---|---|---|
| |Δcmd| = 0 / 1 / 2 (fraction of frames) | .044 / .022 / .021 | .059 / .090 / .075 | .018 / .016 / .016 | .042 / .051 / .049 |
| |Δcmd| 16–63 / 64–121 / ≥ 122 (cap) | .410 / .120 / .132 | .274 / .028 / .016 | .409 / .139 / .210 | .307 / .065 / .087 |
| ±1 alternation fraction (p50 / p90) | 0.000 / 0.005 | 0.005 / 0.026 | 0.000 / 0.005 | 0.005 / 0.020 |
| longest ±1 alternating run (p50 / p90 / max, frames) | 0 / 1 / 2 | 1 / 2 / 3 | 0 / 1 / 3 | 1 / 2 / 3 |
| 100 ms windows on exactly 2 cmd values / 2 idx values / 1 idx value | 0 / 0 / 0 | 0 / .053 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| idx change duty; idx bin-crossing rate p10/p50/p90 (/s) | .807; 65/80/92 | .533; 40/53/71 | .893; 71/89/97 | .675; 37/67/88 |
| cmd 18–22 Hz amp / 30–49 Hz amp (raw) | 31.3 / 19.8 | 9.2 / 9.2 | 48.2 / 21.8 | 14.0 / 12.8 |
| bar 18–22 (raw) · tap T 18–22 (counts) · rate 18–22 (raw) | 75 · 29.0 · 23.8 | 22 · 9.6 · 7.9 | 73 · 30.1 · 23.2 | 26 · 10.9 · 8.8 |
| **map quantisation residual → output counts**, V282 map: rms · 18–22 amp · 30–49 amp | 6.73 · **2.34** · 5.40 | 6.50 · **2.38** · 4.97 | 6.69 · **2.54** · 5.68 | 6.58 · **2.39** · 5.35 |
| same residual with the STOCK map on the same command: rms · 18–22 | 2.97 · 0.96 | 3.10 · 1.14 | 2.93 · 1.00 | 3.10 · 1.10 |
| **tap 18–22 ÷ residual 18–22** (p10 / p50 / p90) | 7 / **12** / 26 | — | 5 / **12** / 22 | — |

Reading:
1. **Nothing on the wire dwells.** In grinding the command moves on 96–98 % of frames, mostly by 16–63 counts (1–4 idx
   bins) and by the slew cap on 13–21 % of frames. A two-value dither would show ±1 alternation and two-value 100 ms
   windows; both are **zero** at the median in every stratum. (This reproduces the 2026-09-07 wire study's "92 % of frames
   change"; grinding windows are *more* mobile than baseline, not less.)
2. **The quantiser's own noise is small, white-ish and does not move with the symptom.** The staircase-minus-continuous
   residual of the 6× map is 6.7 output counts rms (0.2 % of the 3072 clamp) with 2.3–2.5 counts in 18–22 Hz and *more*
   in 30–49 Hz — no line, and **identical in grinding and baseline windows**. The tap's 18–22 Hz torque is 29–30 counts in
   grinding, 12× the residual (3× even if the whole Ms = 3.8 resonance peak were credited to it), and it is 3× the baseline
   while the residual is not. On the stock map the same residual is 3.0 counts rms — 2.2×, not 6×, smaller, because the
   ≤ 1-count LERP floor is the same on both and only the idx-quantiser × slope term scales.
3. **Frequency.** If a ramp through idx bins were toning, f0 would follow the bin-crossing rate; that rate spans
   65–97 /s in grinding windows while f0 sits at 19.5–20.6 Hz, Spearman ρ 0.00 (p 0.94) on r39 and 0.18 on r5e.
   (The 100 Hz command sequence *is* what the EPS receives — a white residual at 100 Hz has no hidden 80 Hz content to
   fold to 20 Hz; the TASK5 alias caveat applies to the 0x18F sensor streams, not to the command or its quantiser.)
4. **Line vs idx motion** (all engaged windows): on r39 windows with ≤ 20 idx changes in 2 s are rare (n = 9) and none is
   present; 21–60 changes → present 0.069 (n = 29, but v p50 3.4 m/s and hands-on |bar| 825 — confounded); > 60 changes →
   present 0.212 (n = 1704). Weakly consistent with "the line rides on a moving command", which is the record's echo /
   slew-cap enrichment, not evidence of quantisation: the residual amplitude is the same in those windows.

## D. The record — what H1 predicts, what is on disk [EVIDENCE for the numbers; the predictions are H1's logic]

H1 predicts: (i) excitation ∝ map scale ⇒ no line, or ~6× less, on stock-map builds; (ii) a frequency set by the
command's dwell cadence (50 Hz for a strict alternation, the bin-crossing rate for a ramp, broadband otherwise), moving
with command slope and speed; (iii) no line when the idx is frozen; (iv) no dependence on Kp, because the quantiser sits
in front of the loop.

The record (`rlog-tools/studies/grind/_scratch/loopshape20_mode_nature.txt`, 2026-09-08, 9 routes, 5 builds):

| build | map | Kp | f0 (bar line) | n | presence |
|---|---|---|---|---|---|
| V278r3 | ×2 concave | LERP 248→696 | 20.08 [19.81–20.96] | 434 | 37.7 % |
| V280r2 | ×6 linear | LERP 248→696 | 20.08 [19.72–20.89] | 1026 | 24.3 % |
| V281r3 | ×6 linear | flat 248 | 20.06 [19.91–20.20] | 293 | 16.2 % |
| V282 | ×6 linear | flat 248 | 20.03 [19.80–20.27] | 586 | 15.2 % |
| V288 | ×6 linear, setpoint pre-filter (steps ~11× finer) | flat 248 | 20.06 [19.90–20.30] | 198 | 15.6 % |

- f0 by Kp bin on the Kp-LERP routes: 20.01 → 20.05 → 20.11 → 20.24 → 20.57 Hz for Kp 240–300 … 600–700; by idx bin on the
  flat-Kp routes: 20.03 / 20.03 / 20.06 / 20.03 for idx 0–20 … 120–250. ζ 0.036 → 0.019 with Kp (§2c of that file).
- Ledger (`docs/research/GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md`, grind #1 row): the 18–22 Hz band is named in the
  **V62 era** and 21–26 Hz in the **V112 era** — both on the **stock map** — and the one stock creep sample (r97) carries
  29 raw in the band vs ~113–146 raw pooled on ×2/×6 builds.
- V288 rev 2 (`GRIND1-CENSUS-V288-R5E-2026-09-08.md`): the setpoint pre-filter made every per-tick setpoint step ~11×
  finer (ΔE 1088 → 96 sp counts per the correction of record) and cut D-clamp binds ×0.03; grinding **unchanged**
  (258 vs 239 ep/h, f 20.06 vs 20.03, envelope p50 126 vs 127).

Against H1's four predictions: (i) the line exists on the stock map and is *more* present on ×2 than ×6 (Kp confounded,
but the direction is wrong for H1); (ii) f is pinned at 20.03–20.08 Hz across map scale, Kp, idx, speed and echo
presence, and is uncorrelated with the bin-crossing rate inside episodes; (iii) untestable in the strict sense (the
command never freezes for 2 s while engaged), but the quantiser's noise does not rise in grinding windows; (iv) ζ falls
with Kp, which a pre-loop quantiser cannot produce. **Every prediction fails; the one lever that directly tested H1's
mechanism (V288: finer steps) was a null.**

## Caveats and what is BELIEF

- The −4× CAN decode and taper 254 / speedF 255 are the kit's standing mirror (`v280_map_profiles.demand`,
  `grind_incident_r35.demand_live`), consistent with the published idx byte on earlier probes; I did not re-derive the
  decode at `0x526F2` here. The 16.19-count idx LSB inherits that factor: if the decode were −2× the LSB would be 32 counts
  and the conclusion (map-independent, no dither, residual 12× below the line) is unchanged. [BELIEF for the factor, EVIDENCE for the invariance]
- The quantisation residual is pushed through **P only** (Kp 248, gain 5346>>15). Through D it is a one-tick kick per
  frame (A5) that the 5.05 Hz output lag attenuates ×~0.03; the D route was the thing V288 tested on the car.
- "Tap 18–22 ÷ residual" is open-loop; the closed loop can amplify at most by Ms (3.8 on the census fit) — applied above.

## How H1 relates to H2 — for the operator, in plain words

H1 and H2 are the same idea from two sides: both say the command openpilot sends is *lumpy* — H2 says it is lumpy in
time (a 20 Hz staircase held for four frames), H1 says it is lumpy in value (jumping between two table points that the
6× map pushes further apart) — and that the EPS is faithfully reproducing the lumps as grinding. Neither survives the
wire. The command changes on almost every 100 Hz frame, by amounts far larger than one table step, and never sits on
two values; the only quantiser it meets (16 counts per index step) is the same on every build we have flown, including
stock, and its noise is a dozen times too small and does not rise when the grinding is present. What *is* true in both
hypotheses is that the scaled map gives the loop more gain per command count, and the record shows the 20 Hz mode loses
damping as loop gain rises — but that is a smooth gain effect, not a resolution effect: V288 made the steps eleven times
finer and the grinding did not move, and the line was already there on the stock map. The 20 Hz is a mechanical mode of
the column that the rate loop de-damps; openpilot's 20 Hz content in the command is an echo of that ring, not its cause.
