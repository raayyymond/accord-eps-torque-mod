---
name: reference_accord_rate_lane_v62_to_v69_gain_arc
description: Cross-build byte-verified map of the r24 rate lane V62->V69 -- V66 REVERTED V62's sar doubling and V67/V68/V69 all carry stock `sar 0xa`, so V69's speed-shaped surface is NOT the same mechanism; includes the exact speed x rate gain table vs stock, the rail thresholds per build, the region where V69 is WEAKER than V62, and gp-0x683c's zero-writer status confirmed four ways.
metadata:
  type: reference
---

# The r24 rate lane, V62 -> V69: what each build actually does. Traced 2026-08-04.

Reproduce with `analysis-2020accord/studies/sessions/v70/v70_rate_lane_gain_model.py` and
`analysis-2020accord/studies/sessions/v70/v70_gp683c_writer_census.py` (both mirror the decompiled integer arithmetic and
byte-read every constant LE).

## 1. THE `sar` HISTORY -- V69 does NOT carry V62's doubling [EVIDENCE: Python LE read, all images]
`0x3AC20` `sar 0xa,r8` hw `0x42AA`; V62's edit is `0x42A9` (`sar 0x9`). Sibling r26 site `0x3AB76`
`0x32AA`->`0x32A9`. `0x3AB70` never moved in any build.

| | 0x3AB76 | 0x3AC20 | 0x3AA96 gate byte | 0xC6446 arm |
|---|---|---|---|---|
| stock/V38/V61 | 32AA | 42AA | C5 = gp-0x683c | 512 |
| **V62, V65** | **32A9** | **42A9** | C5 | 512 |
| V66, V67*, V68*, **V69** | 32AA | 42AA | C5 / **FB on V67,V68** | 512 / **5244 on V67,V68** |

**V66 reverted it** (`builds/v50_v79/build_v66_tva.py:9-10`); V67 kept the revert; V68/V69 assert it
(`builds/v50_v79/build_v68_tva.py:477 SAR_SITES_STOCK`). ⇒ **V62's mechanism and V69's are different in kind**:
V62 was a constant factor immune to speed, rate and arm selection; V69 moves only the LERP *default*
arm's Y[0]/Y[1] at the 0 and 10 km/h records.

## 2. gp-0x683c HAS ZERO WRITERS -- confirmed FOUR ways, stock and V69 [EVIDENCE]
disp16 scan (per-opcode disp rules, store-zero INCLUDED) = **1 hit, and it is the read at 0x3AA94**;
disp23 6-byte extended form = 0; LE32 literal of `0xFEDF17C4` = 0; movhi/movea pair = 0; GhidraMCP
`get_xrefs_to` = none. Control: **gp-0x6806 = 16 writers / 13 readers.** ⇒ on stock/V62/V65/V66/V69 the
`0xC6446` arm never executes. See [[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]].
Gate decode: `0x3AA94` = `847f c597`; `0x97C4`->gp-0x683C, `0x97FA`->gp-0x6806. Both displacements are
EVEN, so the ld.bu hw1-bit5 parity trap does not bite at this site.

## 3. GAIN vs STOCK, rateKey = 0 (the flat [0,400] segment) [EVIDENCE]
```
km/h            0     5    10    15    20    30    40    50    60    80   100
V62 / V65   2.000 2.000 2.000 2.000 2.000 2.000 2.000 2.000 2.000 2.000 2.000
V67/68 eng  1.707 1.862 2.048 2.074 2.100 2.155 2.214 2.275 2.305 2.370 2.438
V67/68 man  1.000 ......................... all 1.000 .........................
V69 (eng == man)
            4.000 3.999 4.000 3.658 3.308 2.579 1.811 1.000 1.000 1.000 1.000
stock abs   3.000 2.751 2.501 2.470 2.438 2.376 2.313 2.251 2.222 2.161 2.101
```
V69's >=50 km/h 1.000x is **structural**: P2/P3 (`0xD2AEC`/`0xD2B28`) are untouched and the speed
interpolation reads only them there. V69 engaged == V69 manual **bit-identically**, because the gate is
dead and the edit is on the default arm -- so V69 is 4.000x in MANUAL creep, where V67/V68 were exactly
stock.

## 4. 🛑 THE RATE AXIS IS NOT BENIGN -- V69's boost decays along it, V62's did not [EVIDENCE]
```
V69 xstock @0 km/h: rateKey 0-400 4.000 | 500 3.768 | 700 3.266 | 900 2.709 | 1100 2.086 | 1300 1.385 | >=1400 1.000
V62 xstock: 2.000 at every speed and every rateKey.
```
STATE.md's measured operating points: **grind #1 ~603, creep grind #2 ~1206, highway ~141-198**
(`gp-0x6ac0` at 4.7121 counts/deg-s). **Where V69 is WEAKER than V62** (ratio < 1): every speed
>= 50 km/h at every rate (exactly 0.500 = stock); >= 40 km/h at rateKey >= ~0; and rateKey >= ~1200 at
any speed. **At grind #1's own index (603) at creep V69 is 1.75x of V62 -- MORE, not less.**

## 5. RAIL THRESHOLDS -- smallest |gp-0x4f62| that hits the +/-0x2000 clip (rateKey 0)
```
km/h        0    5   10   20   40   50  100
stock    2732 2979 3277 3361 3543 3641 3902
V62/V65  1366 1490 1639 1681 1772 1821 1951
V67/68   1601 (flat -- the arm is speed-independent)
V69       683  745  820 1016 1957 3641 3902
```
Repo max |dtorque| **839** ⇒ **V69 is the first build that rails this lane in ordinary driving.**
🛑 **But saturation ALONE cannot make V69 weaker than V62.** For a symmetric saturation
`N(A) = (L/A)*u*f(1/u)`, `u = K*A/L`, which is **strictly increasing in K** -- so at equal amplitude
V69's describing-function gain is always >= V62's (2.000x down to 1.009x at A = 5120, converging to the
shared `4L/(pi*A)` asymptote). The destabilising quantity is the **rate-axis rolloff**, which makes the
gain fall as the oscillation grows: with the index in phase with the input, V69/V62 crosses 1.0 at
rateKey amplitude ~1200 and reaches 0.51 by 5000.

## 6. 🛑 RESOLVED 2026-08-04 -- **r26 IS LIVE. The kit's "structurally INERT" memory is WRONG.**
`0xC6564` **is** 40 zero bytes (byte-verified) **but it does not feed r26's `avg`.** `gp-0x69a4`'s real
producer is a live 10-point runtime LERP at **0x355C6** in `FUN_000352b4`. Census: 1 writer / 3 readers
(0x355A4, 0x3575A, **0x3AB3A** = the aggregator).
Kill condition @0x3AB2A-0x3AB34 = `(gp-0x6b5e != 0) AND (r22 == 1)`; `[0xC6138]`=1 and `gp-0x671a<5`
always ⇒ **r26 = 0 iff `gp-0x6b5e` != 0**.
`gp-0x6b5e` (writers 0x36256/0x36264 in `FUN_000361c8`, shadow `gp-0x4cd8`) =
`polarity * ((LERP_0xC66CC(gp-0x6bda) * [0xC63C2]=1024) >> 10)`; table `0xC66CC` n=5,
X=[-384,-128,128,294,384], Y=[0,4762,4762,717,0] ⇒ **zero only at and outside ±384**.
★ **`gp-0x6bda` is a MARGIN TO A PEAK-HOLD ENVELOPE, not a raw signal** [`FUN_00036022` 0x36068-0x3608C]:
`gp-0x6bda = (x>0 ? UPPER-x : x-LOWER) - ([0xC614C]=128 unless gp-0x67fe==2)`, where `x = gp-0x6bf0 =
DRIVER ASSIST TORQUE` (kit memory `reference_accord_lerp_envelope_gating`; hands-off = |x| <= 9216,
cal `0xC6156` byte-verified) and UPPER/LOWER are a **rising peak-hold** maintained by `FUN_00035d38`,
clamped ±`[0xC614A]`=10048, **half-width >= `[0xC6150]>>1` = 9390 in every branch** including the
`gp-0x37ba` recentre.
⇒ **hands-off (x≈0): `gp-0x6bda` ≈ 9262 = 24x the 384 threshold ⇒ r26 LIVE.** r26 dies only when
`|driver assist|` comes within ~512 counts of its own envelope edge (≈ the documented 9216
driver-override condition) -- a ~5% sliver at the far end of the axis.
🛑 **CONSEQUENCE: V62's fix was carried by BOTH lanes; V69 restores neither.** And `lp` at 0x3AB56 is
the SAME register as r24's gate (set once at 0x3AAA8 from the single `ld.bu` @0x3AA94), so V67/V68's
one-byte repoint forced **r26's gain to `[0xC6444]`=512 against a stock gain_A of 3072 = a 6.00x CUT,
engaged only**, while raising r24 to 5244. Total slope = `[gain_B + a*gain_A]/2^sar`, `a = gp-0x69a4/1024`:
**V67/V68 engaged falls BELOW STOCK for a > 0.848 (creep) .. 1.510 (100 km/h)**; V62/V65 = 2.000x for
**every** a (the `sar` route is dose-exact independent of `avg`); V69 = (4+a)/(1+a) at creep, equal to
V62 at a=2. ⇒ **`a` is the one number that decides all of it — measure it with a cave rung on
`gp-0x6adc`** (r26's post-clamp mirror @0x3AD4E, 0 readers / 1 writer).
`0xC6444` blast radius: **1 reader (0x3AB5E), disp23 0, LE32 literal 0, no float mirror**, CRC block #48
(same as 0xC6446). History: **only ever tested DOWNWARD** (V42 set it 0 with 0xC643E→0 and all gain_A
Y→0, flashed→FALSIFIED; V61 zeroed both lanes, WORSE). **Raising it is untested.** 🛑 Overflow ceiling
**6553** (two chained multiplies: worst-case `stage1 = (5120*65535)>>10 = 327,675`).
See [[reference_accord_aggregator_lane_mirrors_6ada_6adc]],
[[reference_accord_r26_adaptive_lane_full_trace_and_sign]],
[[reference_accord_lerp_envelope_gating]].

## 7. ★ FUN_0003ad74 REBUILDS BOTH TABLES -- there is NO separate gain_B rebuilder [EVIDENCE]
Body 0x3AD74-0x3AFF3. **First half 0x3AD74-0x3AECC = gain_B / r24**: writes `gp-0x6e40` (X) /
`gp-0x6e38` (Y) from the mode-indexed ROM records. **Second half 0x3AECC-0x3AFEE = gain_A / r26**:
writes `gp-0x6e30` / `gp-0x6e28` from `tp+0x7a68/7a7c/7a90/7aa4` = 0xC6A68/7C/90/A4 (V42's
0xC6A72/86/9A/AE are those records' Y[0]). Speed at 0x3AD7E `ld.hu -0x6a5e[gp]`, fallback
`[0xC6314]` = 5120. P0/P1/P2 via LE32-literal pointer arrays 0xCBF5C/0xCC044/0xCC12C at mode*4;
**P3 via `ld.w 0xd214[r16]` (tp+0xD214 = 0xCC214) at 0x3ADC2 -- tp-relative, so an LE32 literal scan
for 0xCC214 returns ZERO and can look like a missing 4th record.**

**THE BLEND IS STRICT 2-POINT.** `0x3ADF8 ld.w -0x4[ep],r16` = LOW record, `0x3AE00 sld.w 0x0[ep],r6`
= HIGH record; exactly two pointers are dereferenced, no accumulator, no loop over records.
`k` = first index with `Xcross[k] > speed`; k==0 copies P0, k==4 copies P3.
⇒ **at speed >= 3200 counts = 50.000 km/h the RAM table reads ONLY P2/P3** -- machine-asserted
bit-identical stock-vs-V69 over a 0..6500 sweep. ⚠ At 3199 counts (49.984 km/h) there is a
**1.0013x** residual (stock Y=[2306,2305,...] vs V69 [2309,2308,...]); it is a continuous ramp, not a
step, so "byte-identical BELOW 50" is false while "at and above 50.000" is true.
Blast radius: `movea -0x6e40,gp` exists at exactly **2 sites image-wide** (0x3ABA4 reader / 0x3AE42
writer); same for -0x6e30 (0x3AAD8 / 0x3AF64). One producer, one consumer.
⚠ Sole caller `FUN_00022ca0` is an **RTOS task** (LE32 literal at 0xBB9E8 in the 0xBB9B8 table), not
inline in the 1 kHz aggregator -- **rate UNRESOLVED**; the table lags speed by up to one task period.

## 8. ★★ THE TWO-KNOB PROPERTY: with the gate LIVE the arm and the surface are INDEPENDENT [EVIDENCE]
Each arm at 0x3ABFE/0x3AC08/0x3AC12 is an unconditional **overwrite** of r10 followed by
`br 0x3AC16`; the LERP runs first into r10. So with `0x3AA96` = `0xfb`:
- **engaged** (gp-0x6806 != 0), gp-0x671d == 0 -> gain = `[0xC6446]`, **LERP discarded, surface INERT**
- **manual** -> arm2 skipped, arm3 dead (gp-0x671a >= 5 is 0/186,321 + 0/53,991) -> gain = **the surface**
- gp-0x671d != 0 -> `[0xC6442]` = 1024, outranks both (2 writers: 0x3BD2A store-zero, 0x41EC6)
Machine proof: V69-surface+gate=fb vs stock-surface+gate=fb, **engaged**, 121 speeds x 6 rates ->
identical in all 726 cells. ⇒ a **cave-free** design giving a flat engaged knob and a speed-shaped
manual knob. 🛑 **V69's edit-order invariant INVERTS**: `gate == 0xfb` REQUIRES `0xC6446` re-raised
from 512, or the engaged lane sits ~5x BELOW stock everywhere (worse than V61, which was worse on-car).

Related: [[reference_accord_r24_gainb_table_structure_and_priority_gate]] (the pointer chain and the
4-way gate), [[reference_accord_v61_taps_gain_priority_and_sign_apples_to_apples]],
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]].
