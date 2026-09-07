---
name: reference_accord_lkas_pid_filter_form_two_sample_sum_and_oscillation_detector
description: The exact integer form of BOTH LKAS-rate-PID filters (output lag 0xC63EC/EE and feedback EMA 0xC63E8/EA) -- a one-pole IIR on an INCREMENT whose output is the two-sample sum, with `a` ADDED not subtracted; the output lag has a >>5 and DC 0.990, the feedback EMA has NO >>5 and DC 30.89. No overflow on any candidate (>=8.9x headroom). Plus: Honda's oscillation-reversal detector FUN_000428d4 is LIVE at 1 kHz and is a genuine HIGH-PASS (>10 Hz) frequency-selective 40% assist cut -- the one downstream monitor a faster lag pole can move toward.
metadata:
  type: reference
---

# The two LKAS rate-PID filters, exactly; and the frequency-selective monitor downstream

Measured 2026-09-06 on V282 (`_v282_..._plain_image.bin`) for bytes, stock `code.bin` for Ghidra.
Admissible because a full byte diff of `FUN_00028ea6` `[0x28EA6,0x2A2A0)` V282-vs-stock is **exactly 2
bytes**, at `0x2A1F0/F1` (`ld.h 0x746c` -> `ld.h 0x7cd0`, the V282 gain repoint). **Both filter blocks
are byte-identical.**

## 🛑 THE FILTER FORM — neither of the two obvious candidates

Both filters are a one-pole IIR **on an internal increment `s`**, output = the **two-sample sum**
`s[n-1] + s[n]`, with **`a` ADDED** (pole is `a/1024` directly, no minus sign).

```python
# OUTPUT LAG   0x2A174-0x2A1B0 ; state gp-0x3d3c (32-bit) ; a=0xC63EC=992 b=0xC63EE=507 ; |x|<=15360
s_new = ((992*s) >> 10) + ((507*x) >> 10);  y = (s + s_new) >> 5;  s = s_new   # st.w stores s_new, NOT y

# FEEDBACK EMA 0x28F86-0x28FA8 ; state gp-0x3d30 (32-bit) ; a=0xC63E8=923 b=0xC63EA=1560 ; |x|<=12000
s_new = ((923*s) >> 10) + ((1560*x) >> 10); y = s + s_new;         s = s_new   # NO >>5
y = clamp(y, -cal(0xC62E6), +cal(0xC62E6))   # V282 46080 ; stock 7680
```

**⇒ DC = 2b / ((1024-a) * 2^shift)**, shift=5 for the lag, **shift=0 for the EMA**.
- lag 992/507 -> **DC 0.99023** (the record's 0.990 CONFIRMED), pole 5.05 Hz.
- EMA 923/1560 -> **DC 30.891** (two-sample sum), pole 16.53 Hz. 🛑 **The `/32` does NOT apply here** —
  a brief that quotes `2b/(1024-a)/32` for the EMA is wrong. This is why two earlier agents read 15.45;
  see [[accord-feedback-operand-is-a-two-sample-sum-dc-30-89]].

Verified by a 4000-tick step response of the integer mirror: lag y=15208 vs closed-form 15210;
EMA y=30862 vs 30891 (the deficit is the `sar` floor).

**Widths / loads:** states are **32-bit** `ld.w`/`st.w`. `a` is **`ld.h` (SIGNED)**, `b` is
**`ld.hu` (UNSIGNED)** — so **any future `a` >= 32768 loads NEGATIVE and gives a sign-flipping unstable
filter.** `mul` keeps the low 32 only; the high half goes to r0.
**Neither internal state is clamped** — `s` is bounded only by the INPUT bound. The EMA's input guard
is `0x28F50 addi 0x2ee0` / `0x28F54 addi -0x5dc1` / `bnc`, i.e. **|x| <= 12000** or the function bails.

## Overflow: NONE, on every candidate. Worst intermediate `a*s` = 241 M vs 2^31 = 2147 M (8.9x).

| a/b | f | DC | \|H\|20Hz | \|H\|40Hz | max a*s | headroom |
|---|---|---|---|---|---|---|
| 992/507 (lag today) | 5.05 | 0.9902 | 0.2422 | 0.1235 | 241,413,120 | 8.9x |
| 963/986 | 9.78 | **1.0102 ⚠** | 0.4430 | 0.2386 | 239,091,746 | 9.0x |
| 963/**966** | 9.78 | 0.9898 | 0.4340 | 0.2337 | 234,242,014 | 9.2x |
| 932/1457 | 14.98 | 0.9898 | 0.5927 | 0.3454 | 226,714,268 | 9.5x |
| 923/1560 (EMA today) | 16.53 | 30.891 | | | 171,074,851 | 12.6x |
| 842/2814 | **31.15** | 30.923 | | | 156,223,385 | 13.7x |
| 832/**2966** | 33.05 | 30.896 | | | 154,232,000 | 13.9x |

⚠ **`963/986` is NOT DC-neutral (+2.0%)** — use `963/966`. ⚠ **`842/2814` is 31.1 Hz, not 33** on the
matched-z convention (`f = -ln(a/1024)*fs/2pi`) that the kit uses elsewhere; `832/2966` is a true 33 Hz.
The "x2.5-x2.9" for a 5->15 Hz lag move is the 20-40 Hz magnitude ratio: **2.45x @20, 2.80x @40.**
The EMA clamp 0xC62E6=46080 saturates at |x| = **1492** of 12000, because DC is 30.89. DC-matched pole
moves do not shift that point.

## 🛑🛑 THE DOWNSTREAM MONITOR THAT IS FREQUENCY-SELECTIVE: `FUN_000428d4`

**LIVE at 1 kHz** — called from `FUN_0002214a` under `uVar2 & 0x830`; state 11 sets bit 0x800.
Its own top gate `FUN_00046ea6(5)` runs the FSM when DTC bit 5 is **CLEAR**, i.e. normally.

- Input `gp-0x6c2c` (the FUN_00041464 rate estimate, EMA corner ~67 Hz, so it passes 20-40 Hz intact).
- Reversal test: alternate crossings past **+/-cal(0xC620A) = 12800** (amplitude threshold).
- 🛑 **Dwell `cal(0xC64DD) = 50` ticks = 50 ms resets the FSM ⇒ it only accepts oscillations with a
  half-period under 50 ms, i.e. frequency ABOVE 10 Hz. A genuine HIGH-PASS acceptance window.**
  **20-40 Hz is inside it; the 7-9 Hz ratchet is outside it.**
- Counter `gp-0x357c` -> level `gp-0x671a` (held against `cal(0xC64FA)=5`).
- **The cut**: LERP x knots at **`0xC694A`** = {0,15,20,25}, y = {32768,32768,19661,19661}
  ⇒ flat 1.000 to level 15, ramp to **flat 0.600 at level 20 — a 40% ASSIST CUT** -> `gp-0x6994`
  -> `FUN_00045608(2,..)`/`FUN_00045668(2)` -> `FUN_00016de6(0x21,..)` monitor report.
- Speed gate: LERP runs only if `gp-0x6a5e <= cal(0xC62E0)=960`; `0xC62DE=640`; `0xC62DC=0` makes the
  second floor block unreachable. All V282 = stock.
- **15 reversals for any cut, 20 for the full 40%.** At 20 Hz that is 375 ms / 500 ms of sustained
  oscillation; at 40 Hz, 187 / 250 ms. The measured grind is a sustained 20.3-21 Hz line and r35 had a
  0.9 s burst — **long enough, if the +/-12800 amplitude threshold is met.**
- **[BELIEF]** it is not firing today (no 40% assist drop in the symptom record), so today's amplitude
  is under 12800. **A 2.45-2.80x rise in that band moves toward it. Gate on an inert tap of
  `gp-0x6c2c` (0xFEDF13D4) before flying the 15 Hz lag pole.**

⚠ **OFF-BY-0x1000 CAUGHT HERE:** Ghidra renders this LERP base as `DAT_0000794a + unaff_tp`. At
0xC794A it gives nonsense (13/61464/13/61508); the correct anchor is **0xC694A**. Same for
`tp+0x72dc/de/e0` = **0xC62DC/DE/E0**, not 0xC72xx.

## The three monitors that are NOT at risk
- **Governor slew `FUN_0004503c`** (`0xC6206`=512 fast / `0xC6208`=**205** slow): IS a per-tick
  asymmetric rate limit (binds above A=1631 @20 Hz, A=816 @40 Hz) but it is a **SHAPER, not a cut** —
  `FUN_0004595a` only checks |out|<=|target| with matching sign, guaranteed structurally. It will
  **blunt and rectify** the extra HF, so delivered HF is less than the raw 2.45-2.80x.
- **Soft-EME shaper `FUN_00042af8`**: CANNOT FIRE. `gp-0x6ace <= cal(0xC6202)=4762` + comp <= 2560 =
  7322 vs the +/-8192 reject; margin 870. Amplitude-bounded by cals downstream of the governor clamp.
- **Lockstep `FUN_00043e44`**: checks the recomputed *bound* (0xC6598/0xC65C4 arms), not the signal.
  A pole cal edit touches neither arm.

## The tick: 1 kHz is EVIDENCE, but on ONE method only
The task descriptor at **0xBB920** (48-byte stride, pointer array at 0xBB864) is an RTOS TCB:
`+0x00` stack ptr 0xFEDF70C8, `+0x04` attr 0x00010607, `+0x08` **entry 0x0002214A**, `+0x0C` stack base
0xFEDEC000. **NO period field.** `FUN_0002214a` has no `jarl` callers and ends in `FUN_000861f2`, a
**SCBP/SCCFG syscall-table dispatch** (wait-for-next-activation). So the period is not statically here.
🛑 **The OSTM0 route is REFUTED (PCLK is 40 MHz, not 80 — it would give 500 Hz).** The surviving
evidence is the on-car measurement: `0xC64DF` = 100 (byte-verified V282) measured as a **100.00 ms**
STEER_STATUS=4 dwell ⇒ 1 tick = 1.000 ms. **⇒ ONE method, not the "two independent methods" the record
claims.** The golden model's `motor_torque_governor` docstring and
`memory/misc/control-task-tick-confirmed-1khz.md` both still repeat the refuted half — flagged, not
edited (ask the operator first).

⭐ **The robust part:** `FUN_00028ea6` and `FUN_0003aa2c` are called **in the same task body, same
pass**, under masks 0x930 and 0xc30 which both contain bit 11. **Zero ticks of skew between them**, so
every relative-phase result is safe regardless of the absolute-rate question; only absolute-Hz claims
depend on it.

## Related
[[reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader]] — the reader census this
re-confirmed (6 sites, 0 stores, halfword-only, positive control 0xC646C -> 5 sites).
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] · [[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]]
