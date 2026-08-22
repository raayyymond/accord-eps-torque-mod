---
name: reference_accord_gp6ac0_rectify_after_iir_and_governor_bound_census
description: "DECISIVE: gp-0x6ac0's rectifier is AFTER the IIR (0x4166e), not before, and the IIR corner is 54.83 Hz -- so a 21-26 Hz oscillation passes ~intact and gp-0x6ac0 is a PEAK-FOLLOWER modulating 0->peak at 2x the carrier, NOT a steady DC lift. Plus: governor bound is symmetric +/-((gp-0x4f64*Q15_authority)>>15), the ceiling swing is 9.30x NOT 10.4x, 0xC6202=4762 is a MIN not a gain, FUN_0007b022 is the SOLE writer of gp-0x4f64, and the governor output slew is ASYMMETRIC (instant toward zero, 8.3-20.7 ms away)."
metadata:
  type: reference
---

# `gp-0x6ac0`: rectify AFTER the filter — and the governor bound, censused

Traced 2026-08-22 on stock `code.bin`, GhidraMCP + raw Python LE byte scans. Decompile-first throughout.

## 1. 🛑 THE RECTIFIER IS **AFTER** THE IIR — EVIDENCE, instruction level
`FUN_00041464`, sole caller `FUN_0002214a` @`0x22200` (`get_xrefs_to` = UNCONDITIONAL_CALL), gate
`andi 0xd30` @`0x221f8` — fires every tick ⇒ **1 kHz**.

```
0x415be  addi 0x32c8,r15,r11    x + 13000        x = gp-0x4f50, SIGNED (two-sided +/-13000 range check)
0x415c2  addi -0x6591,r11,r0    range test; bc -> invalid path (sentinel 0x7fffffff)
0x415d4  shl 0xa,r28            u[n] = x << 10
0x415da  ld.hu 0x743c[tp],r10   K = cal 0xC643C = 37      (raw bytes `2500`)
0x415de  sub r7,r28             u[n] - y[n-1]
0x415e0  mul r10,r28,r0         * 37                      (max |prod| 985,088,000 < 2^31 -- no overflow)
0x415e6  sar 0x7,r28            >> 7
0x415e8  add r28,r24            y[n] = y[n-1] + ...
0x4166e  subr r0,r20            r20 = |y[n]|              <-- RECTIFIER, AFTER THE FILTER
0x41830  shr 0xa,r20
0x41832  st.h r20,-0x6ac0[gp]   gp-0x6ac0 = |y[n]| >> 10
```
**There is NO `| |` anywhere upstream of `0x415d4`.** State is `gp-0x359c` (32-bit, `st.w` @`0x41b74`).

```python
# exact integer mirror
K, SH = 37, 7                      # cal 0xC643C, sar 0x7 @0x415e6
y = y_prev + (((x << 10) - y_prev) * K >> SH)     # 0x415d4/0x415e0/0x415e6/0x415e8
gp_6ac0 = abs(y) >> 10                            # 0x4166e / 0x41830 / 0x41832
```
**alpha = 37/128 = 0.2890625, unity DC gain, f_-3dB = 54.83 Hz, tau = 2.93 ms** (63% of a step in 3 ticks;
90% in 7, 99% in 14). Cross-validates the carried phase table exactly: 0.9894<-7.02deg @8Hz,
0.9390<-16.82deg @20Hz, 0.9216<-19.05deg @23Hz, 0.9029<-21.17deg @26Hz.

### Why this is decisive
A 21-26 Hz oscillation passes at |H| = **0.92-0.90** — essentially intact — and is *then* rectified with
**no post-filter**. So `gp-0x6ac0` is **NOT a sustained DC lift**; it is a full-wave-rectified sinusoid
**modulating 0 -> peak at 42-52 Hz**, touching zero twice per carrier cycle. ⇒ the table index is a
**PEAK-FOLLOWER, not an averager**. Any model in which the HF gets *averaged* into a steady index is
wrong. (Because the ceiling drops fast and recovers slowly, it still cannot fully recover between
half-cycles ⇒ sustained dropout while the oscillation persists.)

⚠ `gp-0x6ac0 ~= |gp-0x4f50|` at DC — the `<<10` / `>>10` are internal precision only, so the
`0xC520C` axis is the rate **essentially unscaled**. Column conversion (rate-independent, re-derived
2026-08-22): **`column_degps = gp-0x6ac0 / 4.71211`** ⇒ X=1050 -> **223 deg/s**, X=4100 -> **870 deg/s**.

## 2. The governor bound — symmetric, and it binds EVERYWHERE
`FUN_0004503c` (1 kHz, called @`0x2293a`):
```
0x453e0  ld.h  -0x6b94,gp,r6     r6 = aggregator sum (SIGNED)
0x453f0  ld.hu -0x4f64,gp,r8     r8 = rate-scheduled ceiling (UNSIGNED)
0x453f4  mul   r26,r8,r0         * r26 = the Q15 AUTHORITY RAMP (a RAM cell, NOT a cal, NOT a constant)
0x453f8  sar   0xf,r8            >> 15                     -> +bound
0x453fa  mov   r8,r7
0x453fc  subr  r0,r7             0 - bound                 -> -bound
0x453fe  jarl  0x00049a90,lp     clamp(r6, r7, r8)
```
`FUN_00049a90(x,a,b)` **sorts a,b then clamps x into [min,max]** ⇒ **symmetric +/-bound CONFIRMED**.
Ghidra renders the call with only 2 args (it misses r8) — **read the assembly for the third.**
At full authority (Q15 = 0x8000) **`bound = gp-0x4f64` exactly.**

🛑 **`gp-0x4f64 = clamp(table_Y, 0, 4762)`** — see the cancellation proof in
[[reference_v850_ghidra_cal_read_rendered_as_function_symbol_trap]]. `0xC6202`=4762 is a **MIN/CEILING**,
**not** a "Q10 scale x4.650390625" (that reading is in `docs/STATE.md` and is WRONG).

| table Y (0xC520C) | gp-0x4f64 | bound | vs `gp-0x6b94`'s own +/-10240 |
|---|---|---|---|
| 5325 (rate<=1050) | **4762** | +/-4762 | **BINDS** (2.15x smaller) |
| 3584 | 3584 | +/-3584 | BINDS |
| 2406 (rate 2500) | 2406 | +/-2406 | BINDS |
| 1587 | 1587 | +/-1587 | BINDS |
| 512 (rate>=4100) | **512** | +/-512 | **BINDS** |

🛑 **Swing is 9.30x (4762->512), NOT 10.4x (5325->512)** — the 5325 top is itself capped. The clamp binds
at **every** point on the table. Consistent with V101's measured **13.0% clamp duty** at 8x.
Table re-verified by raw read: X 1050/1700/2500/3700/4100, Y 5325/3584/2406/1587/512; mirror `0xC5224`
**byte-identical**; the LERP **clamps at both ends, does not extrapolate**.

## 3. Sole-writer census of `gp-0x4f64` — two methods
Raw LE scan, both gp encodings (6-byte disp23 form: **0 hits**): **11 accesses = 8 reads + exactly 3
writes** at `0x7C2E2` / `0x7C3B4` / `0x7C47C`, each paired with its lockstep-mirror store to `gp-0x448a`
4 bytes later (`0x7C2E6`/`0x7C3B8`/`0x7C480`). All three appear in `FUN_0007b022`'s decompiled body
(one per `uVar26` branch 0/1/2 — see [[reference_accord_governor_gp0x184_chain]]).
⇒ **`FUN_0007b022` is the SOLE writer. EVIDENCE.**
`tp+0x7202` (=`0xC6202`) has **exactly ONE reader image-wide, `0x7B06A`**.

**`FUN_0007b022`'s caller:** `get_xrefs_to(0x7b022)` returned **"No references found" — a FALSE NULL**.
A self-validated raw Format-V scan (reproduced `0x453fe->0x49a90`, `0x414c4->0x4613e`, and
`0x22200->0x41464` before being trusted) found **exactly one `jarl`, at `0x6BC9C`**, inside
`FUN_0006bb08`, which `FUN_0002214a` calls @`0x221e0` ⇒ **the ceiling is recomputed at 1 kHz**, gated on
the same state mask family.

## 4. The governor OUTPUT slew is ASYMMETRIC — instant cut, slow recovery
Cals `0xC6206` = **512** and `0xC6208` = **205** (selected by `gp-0x67f5`), read @`0x45410`/`0x45416`,
step = `(cal * authority) >> 15` per 1 kHz tick, previous output in `gp-0x138a`.
Branch structure `0x4543a`-`0x4545a`: **the limit applies ONLY to motion AWAY from zero; motion toward
zero is unlimited.** Full 512->4762 recovery = **8.3 ms** (512/tick) or **20.7 ms** (205/tick).
⚠ **`0xC6206`/`0xC6208` are STAY-AWAY** — V40 set both to `0xFFFF`: EPS lamp, no power steering.

## 5. The authority ramp behind the bound
`r26`/`uVar17` is a Q15 multiplier (0x8000 = unity) from a 3-lane min-chain
(`FUN_00049a90`/`FUN_00049a70`/`FUN_00049a78` over `gp-0x6950`/`0x694e`/`0x694c`), then **rising-only**
rate-limited by cal **`0xC6492` = 33 ct/tick**, gated on `gp-0x6a64 >= cal 0xC6316` (640 ct ~ 10 km/h),
previous value in `gp-0x6946`. **32768/33 = 993 ticks = 993 ms.** Instant drop, ~1 s recovery.
⚠ **Ruled out as the operator's percept** (2026-08-22: *"1 Hz is too slow to match my observation"*) —
the finding stands, the symptom link does not. See
[[reference_accord_tau_env_fills_the_2to13hz_gap_amplitude_modulation]] for what does fill 2-13 Hz.

🛑 **The lane TARGETS `gp-0x693c`/`0x693a`/`0x6938` scan as ZERO WRITERS — that is a
`movea`+indexed-store BLINDSPOT, not a fact.** They are written through a base pointer established by a
family of slot-setters (`0x45608`/`0x45628`/`0x45648`/`0x45668`/`0x4567c`/`0x45690`), e.g.
`0x45650 movea -0x693c,gp,r30`. **Always check for a `movea` of the array base before believing a
zero-writer result on a contiguous RAM array.**

## 🛑 DRIVE-CARD RULE: `b6` UNDER-REPORTS CLIPPING while the authority ramp is still rising
V105's cave rung is **`b6 = |gp-0x6b94| >= |gp-0x4f64|`** — aggregator sum vs the RAW ceiling `G`.
But the **true** clip condition is `|sum| >= bound = (G * chanA) >> 15`. With `chanA` below unity,
`bound < G`, so real clipping starts at a **lower** threshold than `b6` fires at.
⇒ **`b6` under-reports, and the blind window is `bound <= |sum| < G`, a fraction `1 - chanA/32768` of the
ceiling.** At `chanA` = 50 % it is blind to everything between 0.5 G and G.

**Verified constants (raw LE read of the V104 image, independently confirmed by the orchestrator):**
| cal | bytes | value | meaning |
|---|---|---|---|
| `0xC6492` | `2100` | **33** ct/tick | rising-only rate limit on the Q15 authority ⇒ **32768/33 = 993 ms** for a full 0→unity traverse at 1 kHz |
| `0xC6316` | `8002` | **640** ct | speed gate = 640 / 64.0625 ct-per-km/h = **9.99 km/h** |

🛑 **The gate is the way round that matters: the slow ramp is ACTIVE at/above ~10 km/h** (`if cal <= speed`),
so it bites on exactly the highway drive this instrument is for.

⇒ **RULE: discard the first ~1 s of each engaged episode when scoring `b6` duty, and treat an
early-episode `b6` = 0 as UNINFORMATIVE, not as headroom.**

⚠ **BELIEF, and it is the load-bearing half:** that `chanA` actually *starts near zero* on engagement is
**unverified** — the three lane targets `gp-0x693c`/`0x693a`/`0x6938` are written through the
`movea`+indexed-store blindspot by the setter family at `0x45608`/`0x45628`/`0x45648`, and closing it needs
Ghidra to define `0x44600-0x45700` (mutating). **993 ms is a WORST-CASE BOUND, not a prediction** — if
`chanA` persists across engagements the ramp may be much shorter or absent.

