---
name: reference_accord_gp671a_creep_value_and_friction_lane_schedule
description: "gp-0x671a is 0 at creep -- the low-speed FLOOR branch in FUN_000428d4 is dead by CAL (0xC62DC=0, unsigned compare) and the detector needs 4x more signal than the friction rail, so the friction lane's 5.00x low-speed schedule is NOT bypassed. Independently reproduces LOWSPEED-LANE-MAP's 5.00x from the table bytes. Also DERIVES gp-0x6abc's scale."
metadata:
  type: reference
---

# `gp-0x671a` at creep — settled, and it is 0 (2026-08-09, FILTER-A-STRUCTURAL task)

Question posed by the orchestrator: `LOWSPEED-LANE-MAP` found the friction lane `gp-0x6b26` runs at
**5.00×** at 0 km/h with its ±511 rail 5× closer than at highway, and flagged that
**if `gp-0x671a` ≥ 5 at creep the schedule is bypassed** for a scalar. **It is not bypassed.**

## 1. The friction-lane branch, exactly `[EVIDENCE, decompile 0x36c12]`

```c
if ((*(byte*)(gp-0x671a) < 0xff) && (*(char*)(gp-0x67f4) == '\x01')) {
    if (*(byte*)(gp-0x671a) < *(byte*)(tp+0x74fd)) {   // 0xC64FD = 5
        ... speed LERP via pointer array 0xCBE74[gp+0x63fd], indexed on gp-0x6a5e ...
    } else  sVar7 = *(short*)(tp+0x740a);              // 0xC640A = -8192 (SIGNED, ld.h)
} else      sVar7 = *(short*)(tp+0x740c);              // 0xC640C = -3277
```
Confirms the gate as described. Second gate `gp-0x67f4 == 1` is the **vehicle-speed voter plausibility
flag** (see [[reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered]]), not an
engagement gate.

Output clamp is `tp+0x507c+2` = **`0xC407E` = 511** — the known hard-fault interlock cell
([[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]). That is the "±511 rail".

## 2. `gp-0x671a` = 0 at creep — three independent reasons `[EVIDENCE]`

Sole writer `0x42a12`, inside `FUN_000428d4` (an oscillation FSM on `gp-0x6c2c` vs `T` = `0xC620A` = 12800).

**(a) The low-speed FLOOR branch is DEAD BY CAL.** Assembly, not just decompile:
```
000429a4: ld.hu -0x6a5e[gp],r15      ; speed loaded UNSIGNED
000429f2: ld.hu 0x72dc[tp],r11       ; 0xC62DC = 0   (STOCK and V86B)
000429f6: cmp r15,r11                ; r11 - r15
000429fa: bnh 0x00042a0e             ; unsigned "not higher" -> ALWAYS taken when threshold is 0
000429fc:   ...max(count, CEIL) block, SKIPPED...
00042a12: st.b r7,-0x671a[gp]
```
An unsigned value can never be `< 0` ⇒ **`gp-0x671a` is never floored to 5 by speed.**

**(b) The latch requires the counter to reach 5 first.** At creep (speed < `0xC62DE` = 640 cts = 10 km/h)
the path is: reload hold timer `gp-0x6a88` = `0xC6270` = 5000, then
`uVar10 = count` unless `count <= prev` **and** `prev >= 5` **and** `count < 5`, in which case
`uVar10 = 5`. So it is a **one-way latch that only engages once 5 is already reached**; with `prev = 0`
it never engages. The counter `gp-0x357c` is **reset to 0** whenever the FSM sits in state 0
(`0x42906: st.b r0,-0x357c[gp]`).

**(c) The detector needs 4× more signal than the friction rail.** Both key off `gp-0x6c2c`:
- friction term ≈ `gp-0x6c2c × (Y/64) × (273/262144)`; at creep `Y = -9830` ⇒ **−0.15995 × rate**,
  so the ±511 rail is hit at **|gp-0x6c2c| ≈ 3195 counts**
- the oscillation detector needs **|gp-0x6c2c| > 12800**
⇒ **the friction relay saturates ~4× before the detector can even arm.** They are decoupled at creep.

Corroborated on-car: V64 measured that **the detector never armed**
([[accord-v64-null-is-on-the-gate]]).

🛑 **Residual risk worth stating:** the latch has **no decay path at creep** — the only decay
(`0x429b0`, decrementing `gp-0x6a88`) requires speed ≥ 10 km/h **and** count == 0. So a single genuine
oscillation burst below 10 km/h would pin `gp-0x671a` at 5 until the car exceeds 10 km/h and the 5000-tick
(≈5 s at 1 kHz) hold expires. Not reachable on current evidence, but it is a latch, not a sample.

## 3. The 5.00× reproduced from the table bytes `[EVIDENCE]`

Pointer array `0xCBE74[mode]`; **modes 22-28 all point to distinct addresses holding identical values**
(consistent with [[accord-stock-mode24-equals-mode26-damper-is-ours]]):
```
n=3, X = [0, 1280, 5760] cts = [0, 20, 90] km/h   (gp-0x6a5e at 64 cts/km/h)
      Y = [-9830, -5734, -1966]
|Y(0 km/h)| / |Y(90 km/h)| = 9830/1966 = 5.000   <-- LOWSPEED-LANE-MAP's 5.00x, independently derived
rail |gp-0x6c2c|: 3195 counts @0 km/h  vs  15975 @90 km/h  -> "5x closer at creep", confirmed
```

⚠ **The bypass is NOT a sign flip and its effect is mostly at HIGH speed.** All table Y are negative,
same sign as the scalar −8192. At creep the bypass would move −9830 → −8192, i.e. **×0.833, a 17%
reduction**; at 90 km/h it would be −1966 → −8192, i.e. **×4.17 increase**. So even if the latch ever did
engage, the creep-side consequence is modest — **LOWSPEED-LANE-MAP's low-speed conclusion is doubly safe.**

## 4. ★ Bonus, and it CLOSES an open item of mine: `gp-0x6abc`'s scale is DERIVED, not proxied

`[EVIDENCE, decompile FUN_00041464 @0x41464]` In the valid branch:
```c
*(short*)(gp-0x6abc) = sVar15;                  // = gp-0x4f50, RAW rotor speed
uVar16 = uVar8 + ((uVar18-uVar8)*cal(tp+0x743c))>>7;   // uVar18 = gp-0x4f50 * 1024, state gp-0x359c
*(short*)(gp-0x6abe) = (short)((int)uVar16>>10);       // = EMA(gp-0x4f50), SAME UNITS
*(short*)(gp-0x6ac0) = |uVar16|>>10;                   // = |gp-0x6abe|
```
⇒ **`gp-0x6abc`, `gp-0x6abe` and `gp-0x6ac0` are the same quantity in the same units**, differing only by
a first-order EMA and a rectifier. `tp+0x743c` = **`0xC643C` = 37** ⇒ α = 37/128 = 0.2891, −3 dB = 54.83 Hz.
```
|H(7.79 Hz)| = 0.9900  ->  gp-0x6abc = gp-0x6abe x 1.010
|H(21.09Hz)| = 0.9328  ->  x1.072
|H(27.40Hz)| = 0.8939  ->  x1.119
```
⇒ the confirmed **4.7121 counts per °/s** for `gp-0x6abe`
([[reference_accord_gp6abe_column_degps_scale_settled]]) **applies to `gp-0x6abc`**, and `gp-0x6abc` is
the slightly LARGER (unfiltered) one. **This closes open item 3 of
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]]**, which recorded the scale
as unconfirmed — that file should be updated (operator asked, not yet done).
It also means the `gp-0x6ac0`-based clamp figures in
[[reference_accord_c63b4_8hz_bandpass_in_fun3b66a]] §3 are **conservative under-estimates**, not a loose
proxy.

## 5. 🛑 Trap I hit and corrected — off-by-0x1000, again

I mistyped `tp+0x743c` as `tp+0x643c` in a read table and printed **14000** (from `0xC543C`) as the EMA
alpha. The true value at `0xC643C` is **37**. `tp = 0xBF000`, so `tp+0x7xxx` = `0xC6xxx` and
`tp+0x6xxx` = `0xC5xxx`. **This is the fifth recorded instance in this kit.** Anchor every tp offset
against a known value before using it.

## 6. Not answerable from disk: what index/amplitude values actually OCCUR

The six caches on disk (`_cache_r47/r4a/r4e/r4f_ratchet.npz`, `_cache_r4f_v69.npz`,
`_cache_r65_records.pkl`) carry only CAN-derived channels (`tq`, `rate`, `ang`, `v`, `csrate`, `b4`,
`st18`, `lat`, `e4`, `seg`, `press`). **`b4` takes only 2-3 distinct values per route** (135/199, 207, 135)
— build-specific probe bits, **not a thermometer**. **No cache contains `gp-0x6abc` or `gp-0x6ba6`.**
The only `gp-0x6ba6` thermometer ever flown was V59 on route `2c`
([[accord-v59-parametric-pump-marginal]], thresholds 512/1024/2048) and **that raw log is not on disk.**
⇒ closing this needs a new probe or the recovered route-`2c` log — **§4 above is the honest substitute,
and it is a derivation rather than a proxy.**

Related: [[reference_accord_c63b4_8hz_bandpass_in_fun3b66a]],
[[reference_accord_gp671a_blast_radius_not_a_free_lever]],
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]],
[[reference_accord_friction_lane_c407e_census_and_mode26_record_identity]].

---

## 🛑 EXTENDED 2026-08-22 (`mechanism` task) — the HIGHWAY case, and the bypass is BACKWARDS

Team-lead reopened this asking whether `gp-0x671a >= 5` bypasses the mode-record LERP **at highway**,
which would make V106's dose and any V107 reshape inert there. **It does not, and the asymmetry runs the
other way.**

**`gp-0x671a` is the detector's half-cycle COUNTER**, not a speed/load/temperature index: the FSM
(`gp-0x67df`, states 0/1/2) increments byte counter `gp-0x357c` on each crossing of
`|gp-0x6c2c| > T = cal 0xC620A = 12,800`, and `gp-0x671a` is that counter one-way-latched at
**CEIL = cal `0xC64FA` = 5**. ⇒ **five crossings of 12,800 are required.** The measured corpus max
`|gp-0x6c2c|` is **5,141–5,320 — 2.4× below ONE crossing**
([[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]]).

⭐ **The decay path is gated on speed being HIGH, so highway is the SAFEST case:**
```
speed <  cal 0xC62DE = 640 (10 km/h)  OR counter != 0  -> hold timer gp-0x6a88 RELOADED to 5000
speed >= 10 km/h AND counter == 0                      -> timer DECREMENTS; at 0 the latch RELEASES
```
⇒ no decay below 10 km/h, decay above it — any latch clears within ~5 s of motorway driving.
**A bypass could only ever be a CREEP phenomenon; it cannot explain a high-speed residual.**
Also: no Y edit can arm it — the detector reads `gp-0x6c2c` **upstream** of the Y multiply.

**A free proof the LERP branch is live:** `0xC640A`/`0xC640C` are **byte-identical between V105 and
V106**, so any fallback frame gives a V106/V105 ratio of exactly **1.00**. `a6-score` measured
**1.68 [1.16, 1.88]** ⇒ the LERP branch is being taken. And the shortfall from 2.00 needs no bypass:
simulating the measured distribution through the ±511 clamp gives a mean delivered ratio of
**1.591** pooled (1.476 in-burst), inside that CI.

**Census, Ghidra ≡ raw Python LE scan (`ld.bu` hw2=disp|1, `st.b` hw2=disp), exact agreement on 8:**
`0x35A06 · 0x35BEA · 0x36C1E · 0x3A4A6 · 0x3AA70 · 0x429C4 · 0x429D2 · 0x42A12 (SOLE WRITER)`.
Ghidra's `0x26758/0x66714/0x671A4/0x671A8/0xE16xx` are branch- and call-target TEXT collisions.
**`0xC640A` and `0xC640C` each have EXACTLY ONE site** (`0x36CB4`, `0x36CBA`, both in `FUN_00036c12`).

🛑 **`0xC640A`/`0xC640C` are NOT virgin.** V93 and V94 cut both ×0.75 (−8192→−6144,
−3277→−2458); image census **100/102 stock, 2 carry the cut**. **V94 FLEW route `7d` and the operator
stopped driving it.** CONFOUNDED — V93/V94 also cut the mode records ×0.25/×0.50, so the fallback edit
is not independently attributable. ⚠ `build_v93_tva.py:79` designed that flight as an explicit **branch
discriminator** (*"ratio 0.75 ⇒ a FALLBACK constant is live"*) — **the drive was aborted and the ratio
was never harvested.** A purpose-built on-car test of this exact question whose readout was never taken.

⇒ **`0xC640A` is NOT a better lever than a reshape** — it is a two-byte edit into a branch the car does
not execute. **Probe advice:** a bare `(gp-0x671a >= 5)` rung will read 0 and is the
[[accord-v68-detector-still-zero-no-positive-control]] trap verbatim; spend **3 bits on
`min(gp-0x671a,7)`** or nothing.
