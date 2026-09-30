# ADV-A: arithmetic attack on the BUILT V295 image

Subagent "ADV-A arithmetic", 2026-09-30. Adversarial pass, surface 1 of the close-out rule (arithmetic).
- **Nothing was flashed. No CAN was sent. Nothing was committed.** Not edited: STATE, CLAUDE.md, memory, BUILD-LINEAGE,
  the golden model, the build script.
- The FAIL criteria were written before any V295 number was computed: `ADV-A-CRITERIA.md` (F1–F11 block, D1–D6 report).
- Every claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF.
- Scripts and outputs: `adversarial/advA/a1_*.py … a10_*.py` and `*_out.txt` next to them.

## 0. Verdict: **PASS_WITH_DEFECTS**

**None of F1–F11 fired, so the arithmetic does not block the flash.** The dose sits exactly on one of its own caps,
and the build record understates that by one count:

1. **The restart-pulse cap is met with zero margin, not one.** The worst reachable pulse at 100 deg/s is **288 T**,
   and the cap is 288 T. The build report says 287 T and a 1 T margin.
   - Where it occurs: idx 238, demand −, rate −, with the output lag at the low end of its fixed-point interval.
   - That state is reachable: a demand that falls from idx 240 to idx 238 settles the lag there.
   - The build's cold-boot march lands at the other end of the interval, which gives 287.
   - F8 does not fire, because 288 is not greater than 288.
2. **A two-tick bail exceeds the absolute cap.** The pulse is **308 T** (V294: 192) on 224 of 964 lanes.
   - Every reading of the cap so far (designers, adversaries, builder) assumed a one-tick bail.
   - For a two-tick bail to stay at or under 288, b must be at most 970.
   - The part of the pulse that depends on b does not grow with bail length: at most **124 T** for bails of 1, 2 or
     5 ticks.
   - The per-lane ratio to V294 stays at or below ×2.0.
   - **Whether the cap covers bails longer than one tick is the orchestrator's decision. My arithmetic cannot make it.**
3. **New finding, not pre-registered: the trim rectifies at the P clamp near the rail.** A zero-mean wheel-rate
   oscillation lowers the mean delivered torque at idx ≥ ~230.
   - V295 roughly doubles V294's loss. At idx 240:
     - 2.4 Hz, 50 deg/s: 51 T (V294 23);
     - 20 Hz, 50 deg/s: 69 T (V294 33);
     - 2.4 Hz, 187 deg/s: 206 T (V294 112).
   - The loss only ever reduces torque; it never adds authority.
   - It does not reach the r71b drive: the drive's maximum |T| is 1467, far below the rail.
   - The claim "static surface unchanged" holds for a constant wheel rate. It does not hold for the mean torque under
     oscillation at the rail.
4. **D4 fired: the time with |trim| > 300 T goes from 0.042 s to 1.362 s, about ×32** (13 episodes on r71b).
   - 1.31 s of it is below 5 m/s, and 0.96 s is hands-on.
   - This follows from scaling a heavy-tailed distribution by 1.85 against a fixed threshold.
   - The brief does not state it.

## 1. Identity of the thing attacked [E: `a1_bytes.py`]

- **V295 image:** sha256 **`5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed`**, 1,048,576 B. Hashed
  with certutil before anything else, and again in Python.
- **V294 base:** `3143616d…dbdd85`.
- **rwd files:** V295 `f42a06bd…eaae87`, V294 `a2b418f0…9f706a`.
- **Whole-file diff, all 1 MiB:** exactly 6 bytes. `0xC63EA 37→1a`, `0xC63EB 02→04`, and `0xC6FFC–FF` `65 11 44 f3 → d9 2b 98 8d`.
  The code region [0x13000, 0xC0000) has **0** differing bytes.
- **CRC:** a direct `zlib.crc32` over [0xC6000, 0xC6FFC) equals the LE trailer on both images (0xF3441165 → 0x8D982BD9).
  Control: block 0xC5000 matches the same way on stock, V294 and V295.
- **b:** u16 LE at 0xC63EA = **1050**. Read as s16 it is also 1050, so there is no sign hazard. Big-endian would read
  6660.
- **Cells:** every other cell the lane reads is byte-identical to V294, read by my own reader.
  - a = 1011; C = 1024; Kp 960 on all 28 selectors; Kd 0 on all 28; D clamp 0; Ki 0.
  - P and sum clamps 15360; output lag 992/507; gain 5346; T clamp 3072; map rec 0xE502C with Y up to 1032.
  - e_shift 2 (0x29D76 `c282`); fb_op diff (0x28FA4 `89d1`, opcode field 0x0C = subr).
- **Anchor against the off-by-0x1000 trap:** stock reads 923/1560 at 0xC63E8/EA, and 992/507 at 0xC63EC/EE.
- **Ghidra (V294 program `/advC/_v294_…`, dry-run disassembly and read_memory only; nothing mutated, nothing saved):**
  - 64 instruction sites from the listing (0x28F4C…0x2A23C) are **byte-identical to the V295 file**.
  - `read_memory 0xC63E8` gives `f3 03 37 02 e0 03 fb 01`. The program is the V294 image, not a stale import.
  - So the V294 listing is the V295 code.

## 2. The arithmetic, decoded from the bytes [E: Ghidra decompile of `FUN_00028ea6`, then the listing]

I took the structure from the decompile first, then pinned each instruction from the listing. My mirror is
`advA_lane.py`, written from the listing without importing the golden model. The trim path, instruction for
instruction:

```python
# 0x28F4C ld.h -0x6a56[gp],r7 ; 0x28F50/54/58 addi 0x2ee0 / addi -0x5dc1 / bnc : -12000 <= x <= 12000 else BAIL
# 0x28F40..46 pol+1 < 3 ; 0x28F5E cmp r0,r14/bne : pol != 0 else BAIL   (and |bar gp-0x4f60| <= 25600, decompile l.69)
# BAIL (-> 0x290B0): sentinel gp-0x3d2c := 2, r26 := 0, PID skipped (S := 0, I := 0, E_prev := 0x7fffffff), s NOT stored
s_old = s if sentinel == 1 else 0            # 0x28F66 ld.bu ; 0x28F76 bne ; 0x28F7C ld.w -0x3d30 | 0x28F84 mov 0,r26
r7 = w32(x * b)                              # 0x28F86 ld.hu 0x73ea,tp (b = 1050, UNSIGNED) ; 0x28F8E mul r16,r7,r0
r9 = w32(a * s_old)                          # 0x28F8A ld.h 0x73e8,tp (a = 1011, SIGNED)  ; 0x28F92 mul r26,r9,r0
s_new = (r9 >> 10) + (r7 >> 10)              # 0x28F9A / 0x28FA0 sar 0xa (floors) ; 0x28FA2 add r7,r9
r26 = s_new - s_old                          # 0x28FA4 subr r9,r26   (V294's edit, unchanged)
s = s_new                                    # 0x28FA8 st.w r9,-0x3d30  -- stored BEFORE the clamp resolves
r26 = min(max(r26, -1024), 1024)             # 0x28FA6 cmp ; ble / 0x28FB2 subr ; bge  (signed), C = ld.hu 0x72e6
E = (sp << 2) - r26                          # 0x29D76 shl 0x2,r16 ; 0x29D78 sub r26,r16   (sp = mulh(sign, map) @0x29D6C)
P = clamp((E * 960) >> 8, +-15360)           # 0x29E32 zxh ; 0x29E36 mul ; 0x29E3E sar 8 ; clamp ld.hu 0x71bc
S = clamp((m * (0 + P + 0)) >> 8, +-15360)   # I = 0 (Ki 0), D = 0 (Kd 0, D clamp 0) ; 0x2A0BE mul ; 0x2A0C2 sar 8 ; 0x2A13E..
o2 = ((992 * o) >> 10) + ((S * 507) >> 10)   # 0x2A180 / 0x2A194 mul ; 0x2A1A0 / 0x2A1A6 sar 0xa ; 0x2A1A8 add
y = (o + o2) >> 5 ; o = o2                   # 0x2A1AA add ; 0x2A1AC sar 5 ; 0x2A1B0 st.w -0x3d3c
# 0x2A198 ld.bu 0x74a3 == 1 (ARMED on V294 and V295) AND gp-0x6806 == 0 -> yr := 0 if |y| <= 102 or y*yr_prev <= 0
yr = sxh((y * ramp) >> 15)                   # 0x2A1E6 mul r14,r9 ; sar 0xf ; sxh
T = clamp(((0 + yr) * (pol * 5346)) >> 15, +-3072)   # 0x2A1F6 mulh ; 0x2A1FC add ; 0x2A1FE mul ; 0x2A202 sar 0xf
```

**Structural facts that settle several attack lines at once:**

- **b enters only through r26, and r26 enters only through E.** Every other operand is byte-identical to V294.
  - The r26 clamp cannot wind up: s is stored before the clamp, so clamping never feeds back into the state.
  - I found one tp-relative reader of 0xC63EA, `0x28F86 ld.hu`. The scan was positive-controlled against
    `0x28F8A ld.h 0x73e8` and found no absolute or alias LE32 reference [E: `a9_reader_scan.py`].
  - The full census belongs to adversary D.
- **The output gate at 0xC64A3 = 1 / threshold 0xC61B8 = 102 is armed on both builds, and the golden model does not
  mirror it.** It is live only while gp-0x6806 == 0, which the census reads as ramp-down [B, the census's reading].
  - It can only zero the output, never raise it.
  - It is b-independent in form. How V295's larger trim interacts with it during the disengage fade is left to
    adversary D.
  - My mirror implements the gate. The golden comparison was run with the gate not live.
- **r26 is also published as gp-0x6a34 = |r26>>5|**, via `mov r26,r16; sar 5; shl 5` at 0x28FBE–C2.
  - Its range is 0…32, unchanged because C is unchanged. Its distribution scales by ×1.85.
  - Its readers are the dead damper mode (gp-0x680a has 0 writers) and the twin function `FUN_0002a93a`. That is
    adversary D's surface.

## 3. Mirror vs golden [E: `a2_mirror_vs_golden.py`]

**Setup.** My mirror was compared with the golden `lkas_fb_lag` + `lkas_rate_pid_tick` at the V295 cells read from
the image:
- 700 sequences of 200 ticks, **140,000 ticks** in all. Both sides started from identical random reachable states:
  s in ±969k, o in ±240k, sentinel 0/1/2.
- x was driven by random walks, steps, 5–30 Hz sines, 0.5–3 Hz sines, small walks, and the ±12000 edge.
- idx, sign, taper m (0–255) and polarity ±1 were random, and the ramp was partial on 136 sequences.

**Result: 0 mismatches in 1,400,000 comparisons** of r26, E, P, S, y and T, plus the states s, o, I8 and E_prev.

**Coverage:**
- 6,577 bails (|x| > 12000 and invalid polarity), and 4,004 restarts.
- 102,397 ticks with the r26 clamp binding, and 30,307 live ticks with the clamp not binding.
- 16,860 ticks with the P clamp binding.
- LERPs (map, Kp, Kd) over 241 idx: 0 mismatches.

A bail has no golden API, so for bail ticks the golden side is its own `lkas_output_lag(0)` plus its T formula.

## 4. int32 [E: `a3_int32.py`, plus product maxima logged in a2, a4, a5 and a7]

**The reachable range of s.** s′ = F(s, x) = (a·s ≫ 10) + (b·x ≫ 10) is non-decreasing in both s and x, and s starts
from 0 at boot and at every restart. So the reachable s lies in [s\*(−12000), s\*(+12000)], taking the nearest ends of
the floor-generated fixed-point intervals.
- **V295:** s\* = **+969,098 / −969,256**; max |a·s| = **979,917,816**; **margin 2.1915**.
- **V294:** 523,265 / −523,422; margin 4.058.
- Starting above +969,098 (unreachable), s settles at 969,176, and the approach passes a·s = 1.08e9 (margin 1.99).
  That start state never occurs.
- 12000 counts is ±1500.0 deg/s at 8 counts per deg/s, so the guard and the plausibility bound are the same number.

**Hostile march.** 200 × 20,000 ticks, with reversals at ±12000 and bails. The largest a·s was 979,917,816, equal to
the fixed point. Nothing exceeds it.

**Every other product (V295):**

| product | max | margin | depends on b? |
|---|---|---|---|
| b·x | 12,600,000 | 170 | yes |
| E·Kp | 4,945,920 (\|E\| ≤ 4·1032 + 1024) | 434 | no |
| taper·P | 3,916,800 | 550 | no |
| S·lb | 7,787,520 | 276 | no |
| la·o | ~241M | ≥ 8.9 | no |
| y·ramp | ≤ ~498M | ≥ 4.3 | no |
| y·gain | 80.7M | ≥ 26 | no |

**Dose limits at a = 1011:**
- The largest b with margin ≥ 2.0 is **1150**; b = 1151 gives 1.999.
- The largest b with margin ≥ 1.0, where it would wrap, is **2301**.
- b = 1050 has margin 2.1915, and b = 1051 has 2.1894.

**Sign extension.**
- b goes through `ld.hu` and is below 0x8000, so it would read the same either way.
- a goes through `ld.h` (1011), x through `ld.h`, Kp through `zxh`, the gain through `ld.h`, and pol through `ld.b`.
- None of these loads can change V295's numbers.

## 5. Surface, rail, zero command, settle, cap [E: `a5_surface_settle.py`, `a10_trim_cap.py`]

- **Golden surface march** (241 idx × pol ±1): 0 cells differ between V295 and V294. The rail is 2461 at pol +1 and
  −2462 at pol −1.
  - My mirror with demand sign ±1 at x = 0 also has 0 differences, with extremes **+2461 / −2463**.
  - Zero command gives T = 0.
- **Constant x, 2,176 lanes:**
  - x ∈ {0, ±1, ±7, ±80, ±800, ±2400, ±8000, ±11999, ±12000}, 8 idx, both signs;
  - 8 start states: cold boot, restart, s = +969,098, s = −969,256, and four random.
  - **r26 = 0 exactly on every lane**, and T is constant over the last 500 ticks.
  - This follows from F being monotone: s is a monotone integer sequence, so it reaches a fixed point, and then r26 = 0.
- **Settled T, V295 vs V294:** 31 of 2,176 lanes differ by **±1 count**, and none by more. Settled T vs the x = 0
  surface also differs by at most 1.
  - That is the output lag's fixed-point interval: which end you land on depends on the trajectory.
  - The builder's statement "equals V294 on every lane" is true for cold-boot starts only. This is D1, trivial.
- **Trim cap under a sustained wheel acceleration** (±40 counts per tick, which clamps r26 on both builds):
  - **−616 / +615** on both builds at idx 0 and 120.
  - At idx 238, when the trim pushes toward the rail, it delivers only +2 / −3, because the P clamp stops it. That is
    F10 structurally: the trim cannot add authority above the rail.
  - Where r26 binds (the cap): V295 at |α| ≥ **1585 deg/s²**, V294 at 2935. At 2.4 Hz that is a wheel-rate amplitude
    of 163 vs 301 deg/s.

## 6. DC bias under zero-mean noise [E: `a5_surface_settle.py` §3; 200,000 ticks per case]

- **r26 has no DC bias.** The sum of r26 equals s_end − s_start **exactly** (residual 0) in every case where the clamp
  never binds. The ≫10 floors bias s, not r26.
- **At idx 0 and 120:** mean T shifts by −1.0 T on both builds (floors in the output chain). This is b-independent.
- **Near the rail it is new [E], reported as D7:** P-clamp rectification. Oscillation drives P into the clamp on one
  half-cycle only, so the mean |T| falls.
  - It is confined to idx ≥ ~230. At 120 it is ≤ 0.3 T.
  - V295 roughly doubles it:

| x input (counts; 8 = 1 deg/s) | idx 238 V294 → V295 | idx 240 V294 → V295 |
|---|---|---|
| white σ 20 | −2.0 → −4.1 T | 0.0 → −0.1 T |
| white σ 200 | −25.8 → −48.5 T | −18.0 → −40.2 T |
| 20 Hz, 400 (50 deg/s) | −41.6 → −77.7 T | −33.1 → −69.1 T |
| 2.4 Hz, 400 (50 deg/s) | −31.6 → −59.3 T | −23.4 → −50.8 T |
| 2.4 Hz, 1500 (187 deg/s) | −121 → −215 T | −112 → −206 T |

  Values are shown for the + demand sign; the − sign mirrors them.
- **It only reduces torque**, which is the safe direction. On r71b it never engages, because the drive's maximum |T| is
  1467 of 2461.
- **What the verdict rests on:** "static surface unchanged" is exact at constant rate, and within ±1 count at any
  settled state. It is not exact for mean torque under oscillation at the rail.

## 7. Trim gain and phase, 0.3–30 Hz: sinusoid march vs closed form [E: `a6_trim_frf.py`]

**Setup.**
- idx 0, so P = −3.75·r26.
- Each amplitude was set so that |r26| peaks near 500: unclamped, and well above one LSB.
- The closed form is
  (b/1024)(1−z⁻¹)/(1−(a/1024)z⁻¹) · (−Kp/256) · (m/256) · (lb/1024)/(1−(la/1024)z⁻¹) · (1+z⁻¹)/32 · gain/32768.

**Agreement.** At 15 frequencies × 2 builds, the worst |P| magnitude error is **0.034 %** and the worst P phase error is
**0.013°**. T agrees within 0.1 % and 0.1°.
- **The V295/V294 ratio of |T/x| is 1.852 at every frequency (1.851–1.853), and the phase is identical.** b is a pure
  real gain until r26 clamps.
- **Trim phase vs x:** −102° at 0.3 Hz, −165° at 2.4 Hz, −177° at 3 Hz, +110° at 20 Hz. The trim opposes the wheel rate
  around 2–3 Hz on both builds. Any sign question sits with V294's wire read, not with this edit.

| quantity | V294 | V295 | brief | status |
|---|---|---|---|---|
| \|P/x\| at 20 Hz | 2.0790 | **3.8500** | 2.079 → 3.85 | ×1.852, below ×3 (6.24); **F9 does not fire** |
| T per deg/s of wheel rate, 2.4 Hz | 1.847 | **3.420** | ~1.85 → ~3.4 | confirmed |
| K_α, DC limit (T per deg/s²) | 0.2097 | **0.3884** | 0.210 → ~0.389 | confirmed |
| K_α, measured at 0.3 Hz | 0.2071 | 0.3836 | | |

## 8. Restart pulse [E: `a4_restart.py`, `a4b_restart_margin.py`, `a4c_restart_pol.py`, `a8_durations.py`]

**Protocol.**
- **Envelope:** all 964 lanes, idx 0–240 × demand sign × rate sign.
- **Settle:** constant x for 3,000 ticks. Then the output lag was placed at its **low** end, its **high** end, and where
  cold boot lands, and settled for 300 ticks.
- **Bail and restart:** one bail tick (the design's case), then 1,500 restart ticks.
- **Pulse** = max |T − T_pre|.
- **Validation:** the vector lane matched the scalar mirror tick for tick on 24 lanes × 4,801 ticks.

**Results, one-tick bail:**

| rate | V294 worst | **V295 worst** | zero command V294 → V295 | lanes > 288 | worst per-lane ratio | worst / worst |
|---|---|---|---|---|---|---|
| 10 deg/s | 76 | 77 | 15 → 28 | 0 | ×2.08 (tiny numbers) | ×1.01 |
| 30 deg/s | 77 | 104 | 44 → 81 | 0 | ×2.03 | ×1.35 |
| **100 deg/s** | **165** | **288** | **146 → 270** | **0** | **×1.932** | **×1.745** |
| 300 deg/s | 436 | 562 | 420 → 556 | 902 | ×1.35 | ×1.29 |
| 1500 deg/s (the guard) | 611 | 615 | 611 → 615 | 904 | ×1.01 | ×1.01 |

- **The 288 lane:** idx 238, demand −, rate −, output lag at the low end of [−241279 … −241248].
  - T_pre = −2461. The trough is −2173, 42 ms after the bail.
  - At the high end T_pre = −2460, which gives 287. The trough is the same.
  - **Reachable:** after the demand falls from idx 240 to 238, the lag settles at −241279, the low end. The scalar
    mirror confirms this.
  - Polarity −1 gives the same 288.
- **The builder's numbers are the cold-boot end.** My "boot" run reproduces them exactly: worst 287 at idx 227, and
  145 → 269 at zero command. The worst reachable values are **288** and **146 → 270**.
- **Largest b with the one-tick pulse ≤ 288** (both ends plus boot): **1053**. So b = 1050 passes with 3 counts of b
  headroom and 0 T of pulse headroom.
- **Two-tick bail at 100 deg/s:** V295 **308** vs V294 192. **224 lanes exceed 288.** Largest b that passes: **970**.
- **Five-tick bail:** 395 vs 360. At 20 and 100 ticks the dropout dominates and both builds read the same (~1147 and 2358).
- **The b-dependent part, max |T295 − T294| on the same lane and state:** **124 T** for bail lengths 1, 2 and 5. It is
  largest at zero command.
- **Durations, one-tick bail, ms above 50 / 150 / 300 T:**
  - zero command at 100 deg/s: V294 160/0/0 → V295 215/113/0;
  - worst lane at 300 deg/s: 257/163/89 → 305/213/142;
  - at 1500 deg/s: 382/289/218 → 428/335/265, both at the cap.
- **How reachable bails are [B, inherited from the adversaries]:** they need a bar > 25600, pol = 0, or |x| > 12000.
  The producer saturates at ±12000, and pol has no zero writer. So this is a fault path only.

## 9. r71b replay through the built cells [E: `a7_route_replay.py`, `a8_durations.py`]

**Setup.** The run was 1 kHz and byte-exact: 1,020,390 ticks, 800.8 s engaged, 91.8 s of them hands-on. Inputs were the
plant cache's idx, sign, taper m and x1k.
- There were no bails: max |x| was 2979.
- **Control 1:** the inlined march equals `advA_lane.Lane` on 30,000 ticks.
- **Control 2:** my V294 march equals the plant cache's own V294 march **tick for tick (0 differing)**, and the FF-only
  runs match too.
- **Control 3:** the tap minus quant(my V294) on 35,441 hands-off engaged frames has an rms of **3.64 T**.

**Caveat [B]:** this is **open loop**. V295 is driven with V294's recorded motion; closed-loop motion would differ.

| engaged | V294 | V295 |
|---|---|---|
| r26 clamp binds | 0 | **66 ticks (0.0082 %)**, all engaged |
| P at clamp | 461 ticks | 419 ticks |
| max \|T\| | 1467 | 1277 |
| max \|r26 raw\| | 637 | 1179 |
| p99.9 \|r26\| | 368 | 682 |
| max \|a·s\| on the route | 120.7M (margin 17.8) | 223.5M (margin 9.6) |
| V295 − V294 delivered T | — | rms 15.9, p99 81, max 247, mean +0.04 |

The unclamped r26 ratio V295/V294 has a median of **1.8519**, which is exactly b's ratio.

**Trim = T_live − T_FFonly, by speed band (rms / p99 / max, T counts):**

| band | engaged s | V294 | V295 | rms ratio | mean T295 − T294 |
|---|---|---|---|---|---|
| 0–5 m/s | 109.7 | 36.5 / 172 / 309 | 67.4 / 318 / 554 | ×1.847 | +0.45 |
| 5–10 | 228.5 | 21.1 / 100 / 165 | 39.0 / 185 / 306 | ×1.852 | −0.02 |
| 10–15 | 225.4 | 10.5 / 53 / 141 | 19.4 / 99 / 261 | ×1.851 | −0.03 |
| 15–22 | 162.8 | 6.6 / 30 / 102 | 12.3 / 55 / 189 | ×1.850 | −0.03 |
| 22+ | 74.3 | 3.6 / 14 / 55 | 6.6 / 26 / 102 | ×1.846 | +0.02 |

**Driver-override resistance (hands-on engaged ticks, 91.8 s).**
- |trim|: p50 8 → 16; **p99 166 → 307**; **max 309 → 554**.
- **The part opposing the driver's torque** (−sign(bar)·trim): **p99 68 → 125**, **max 163 → 301**. It opposes on
  36–38 % of ticks, and its mean is −9.5 → −17.6, meaning on average it slightly *aids* the driver's direction.
- This is ×1.84–1.85, so the brief's "roughly doubles" is confirmed. D4's ×2.3 bound is not reached.

**Dwell with |trim| > 300 T:**
- **V294 0.042 s (1 episode) → V295 1.362 s (13 episodes).** **D4 fires on this (×32).**
  - 1.313 s of it is below 5 m/s, and 0.963 s is hands-on. Hands-off engaged: 0 → 0.399 s.
- Above 450 T: 0 → 0.126 s.

## 10. FAIL-criteria scorecard

| id | result |
|---|---|
| F1 hash | PASS: `5c044d65…52ed`; base `3143616d…dbdd85` |
| F2 diff / b / CRC / code sites | PASS: 6 bytes; b = 1050 LE; CRC LE match; subr and shl 2 in the file |
| F3 decode differs | PASS: ld.hu b, single reader, s stored before the clamp, signed clamps |
| F4 mirror ≠ golden | PASS: 0 / 1,400,000 comparisons |
| F5 reachable wrap | PASS: max a·s 979,917,816 by the monotone reachable-set bound, and hostile marches agree |
| F6 margin < 2 | PASS: 2.1915 |
| F7 surface, rail, zero command | PASS: 0/482; +2461 / −2463; 0 |
| F8 restart > 288 at ≤ 100 deg/s | **PASS AT ZERO MARGIN: 288** (one-tick). The two-tick case is 308, outside the pre-registered definition, and reported in §0 item 2 |
| F9 \|P/x\| 20 Hz ≥ ×3 | PASS: ×1.852 (3.850) |
| F10 T above the rail | PASS: the P clamp bounds it (a10: +2 / −3 at idx 238); random ticks T_bind 0 |
| F11 no settle AND ΔT > 5 | PASS: r26 = 0 on 2176/2176; ΔT ≤ 1 |
| D1 | fired, trivial: ±1 on 31/2176 settled lanes (output-lag fixed-point interval) |
| D2 | no: march = closed form within 0.034 % and 0.013° |
| D3 | no by its wording: 300 deg/s ×1.29, 1500 ×1.01. The undisclosed two-tick absolute breach is in §0 item 2 |
| D4 | **fired**: \|trim\| > 300 dwell ×32 (0.042 → 1.362 s). Override resistance ×1.85, within bound |
| D5 | no: r26 telescopes exactly |
| D6 | **fired**: the build report's 287 / 1 T margin should be 288 / 0 T; 145 → 269 should be 146 → 270; "settled T equals V294's on every lane" holds for cold boot only (±1 otherwise) |
| D7 (new) | P-clamp rectification near the rail, ×2 of V294's, torque-reducing only |

## 11. What must be decided or corrected before the image is offered

1. **Rule on the scope of the restart cap.**
   - At b = 1050 the one-tick reading is exactly at the cap: 288 of 288.
   - A two-tick bail gives 308. If the cap is meant to cover any bail length, b must be at most 970, and V295 as built
     fails that reading.
   - The per-lane ratio to V294 stays at or below ×2.0 for every bail length. If that is what the cap means, V295 passes.
2. **Correct the build record** (`V295-BUILD.md` §3/§7, the build-script docstring):
   - worst restart pulse **288 T** (0 T margin), not 287;
   - zero command **146 → 270**;
   - settled T equal to V294's within ±1 (the fixed-point interval), not equal on every lane.
3. **Put the two undisclosed costs on the close-out page:**
   - the |trim| > 300 dwell goes 0.04 → 1.36 s on r71b, mostly below 5 m/s and hands-on;
   - the mean torque near the rail drops under wheel oscillation (the rectification), at about twice V294's size.

## 12. Files

| file | what |
|---|---|
| `adversarial/ADV-A-CRITERIA.md` | FAIL criteria, written first |
| `advA/a1_bytes.py` / `_out.txt` / `a1_cells.json` | hashes, full diff, CRC, Ghidra-vs-file bytes, every cell |
| `advA/advA_lane.py` | my scalar integer mirror, from the listing |
| `advA/advA_vec.py` | numpy lane copy, validated against the scalar mirror |
| `advA/a2_mirror_vs_golden.py` / `_out.txt` | 140,000 random ticks vs the golden model |
| `advA/a3_int32.py` / `_out.txt` | fixed points, reachable bound, hostile march, b limits |
| `advA/a4_restart.py`, `a4b_restart_margin.py`, `a4c_restart_pol.py` / `_out.txt` | restart envelope, margins, polarity −1 |
| `advA/a5_surface_settle.py` / `_out.txt` | surface, settle from 2176 lanes, DC bias and rectification |
| `advA/a6_trim_frf.py` / `_out.txt` | gain and phase, march vs closed form |
| `advA/a7_route_replay.py` / `_out.txt` | r71b replay (`_a7_traces.npz` is a scratch trace) |
| `advA/a8_durations.py` / `_out.txt` | pulse durations, dwell breakdown |
| `advA/a9_reader_scan.py` / `_out.txt` | positive-controlled reader cross-check |
| `advA/a10_trim_cap.py` / `_out.txt` | trim cap through the mirror |
