---
name: reference-accord-fun43e44-report-only-and-gp6acc-slew-limiter
description: FUN_00043e44 is a REPORT-ONLY float-vs-int redundancy monitor (gp-0x6906 has ZERO readers, exhaustively verified); its 8.0 compare is a sanitize-to-zero not a trip; the real per-cycle slew limiter on the command path lives in m_motor_torque_governor writing gp-0x6ace (cals 0xC6206=512 / 0xC6208=205), NOT cal 0xC64DE.
metadata:
  type: reference
---

Traced 2026-07-18 on `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`
(sha256 `3f1d55a98aac6e73631d94d583065c57...`, byte-identical to the Ghidra `code.bin`).

## FUN_00043e44 is report-only — `gp-0x6906` has ZERO readers

`gp-0x6906` (= `0xFEDF16FA`, the float monitor's fault word) is written once at
`0x449fa` (`st.h r11,-0x6906[gp]`, w0=`5f64` w1=`96fa`) and **read nowhere in the
1 MB image**. Verified exhaustively across four addressing modes:
gp-relative loads (0 hits), absolute literal word `0xFEDF16FA` (0 occurrences),
`movhi 0xfedf` + `movea 0x16fa` pair reconstruction (667 movhi sites scanned,
0 followed by the matching movea within 12 halfwords), and
`movea -0x6906,gp,rX` address materialization (0 sites).
Residual gap: a struct/table base+offset walk could still reach it — not excluded.

Confirms the REPORT-ONLY framing in `analysis-2020accord/notes/FUN_00043e44_FLOAT_MONITOR.md`
with much stronger evidence than that doc carried.

## The tolerance is a float-vs-integer redundancy check, not a predictor

The `+/-5/1024` immediates (`movhi 0x3ba0`/`0xbba0` = exactly `+/-0.0048828125`)
appear at `0x4463e`, `0x44666`, `0x44788`, `0x448e2`. Each compares this function's
**float re-derivation** against the **integer shaper's stored result**:

| flag | weight | site | compares |
|---|---|---|---|
| 1 | 1.0 `0x4464e` | `0x4463a` | float `bound_final` vs `gp-0x6af6`/1024 |
| 2 | 2.0 `0x44672` | `0x44662` | `polarity x bound` vs `gp-0x6b00`/1024 |
| 3 | 4.0 `0x44794` | `0x44784` | float integrator vs `gp-0x6b0a`/1024 |
| 4 | 8.0 `0x447da` | inline | `gp-0x6b04` range check |
| 5 | 16.0 `0x44866` | inline | `tp+0x71d8` command-offset check |
| 6 | 32.0 `0x448ee` | `0x448de` | float `cmd_final` vs `gp-0x6b98`/1024 |
| 7 | 64.0 `0x4491e` | `0x4490a` | time-signal decay |

`gp-0x6af6` is written by `s_motor_torque_rate_shaper` (body `0x42af8-0x43e43`) at
`0x43a7e` / `0x43e38` — the latter is 12 bytes before this function's entry, so the
two are structurally adjacent and co-temporal.

## Max flag sum is 127 — only the SM's +1024 can reach the 128 report gate

Report gate is `movhi 0x4300` = `128.0` at `0x44a26`; flags 1..7 sum to at most
`1+2+4+8+16+32+64 = 127`. The **only** path to >=128 is the fault SM reaching state 3
and adding `movhi 0x4480` = `1024.0` (`0x449b6` / `0x449d2`), which requires the
`gp-0x3550` timer to reach `0x3c23d70b` = `0.01` s while incrementing by
`0x3a83126f` = `0.001` per call. So: **any flag must be continuously set for ~10 ms
(10 cycles at 1 kHz) before DTC 0x3f1b is raised.** A single-cycle mismatch is inert.

`0x3f1b` -> `FUN_000462e6` (`jarl` @ `0x44a4c`) -> `FUN_00016de6(0x1d, 0x3f1b, 1, 1)`.
`FUN_00016de6` is the generic DTC status-table manager (table at `tp-0x72a8`, stride
`0x1c`); it sets status bits and stores an event. **Whether DTC index 0x1d gates
assist is UNVERIFIED** — no consumer traced.

## The 8.0 compare is a sanitize-to-zero, NOT a trip

At `0x4467a` the monitor loads `gp-0x6acc` (the merged command) and at
`0x44696`/`0x446a4` compares it as a **double** against `+/-8.0`
(`movhi 0x4020`/`0xc020`). Branch polarity verified against the known
`+/-25.0` velocity gate at `0x43ef6` (`trfsr` sets Z = condition true; `be` takes
the zeroing branch). Result: `|gp-0x6acc/1024| > 8.0` replaces the value with `0.0`.
It is an input conditioner, not a bound check that faults.
A second `+/-8.0` (`movhi 0x4100`/`0xc100`, `0x448c2`/`0x448ce`) clamps `cmd_final`.

## The real slew limiter is in m_motor_torque_governor, on gp-0x6ace

`gp-0x6acc` (`0xFEDF1534`) has exactly two writers, both in
`m_post_governor_torque_comp_add` (`FUN_000456a4`): `0x45942` (normal path,
`st.h r12,-0x6acc[gp]`, `r12 = gp-0x6ace + comp` from `0x458bc`/`0x458c8`) and
`0x45932` (debug path, gated by magic `0x49d6b173` AND cal `tp+0x74ba`; that cal
reads **0x00** in stock, so the debug path is dead). **No rate limit here.**

The per-cycle slew limit is one stage upstream, in `m_motor_torque_governor`
writing `gp-0x6ace` at `0x454d2`/`0x454e0`/`0x4559c`/`0x455ae`:
- held previous value in `gp-0x138a`
- step `= (cal x Q15_scale) >> 15` where cal = `tp+0x7206` (**0xC6206 = 512**) when
  `gp-0x67f5 == 0`, else `tp+0x7208` (**0xC6208 = 205**)
- governor binder `s_clamp_i32(gp-0x6b94, +/-(gp-0x4f64 x scale) >> 15)`,
  `gp-0x4f64` from cal **0xC6202 = 4762** — the dominant high-end binder,
  well below the static `+/-0x2000`.

**Cal `0xC64DE` (= 25617) is NOT in this path.** Its 18 read sites are all in the
`0x29xxx`/`0x2axxx`/`0x2bxxx` arbitration / STEER_STATUS / ENABLE region, mostly
`ld.bu`. Do not treat it as a command-path ramp step.

## Residual scaling: V27's mechanism is CATEGORICALLY different from a gain change

The int/float residual checked against the 5/1024 window is a **fixed quantization
floor, not a proportional error term.** Error sources in the duplicated computation:

| source | site | error | scales with magnitude? |
|---|---|---|---|
| `divq` int LERP division | `0x42d80` | <1 LSB of output | **NO** — fixed |
| `sar 0xa` IIR alpha shift | `0x42dbc` | <1 LSB of Q8 state = 2^-8 count | **NO** — fixed |
| Q8 state storage (`shl 0x8`) | `0x42dae`/`0x42dca` | 2^-8 count (finer than the wall's 1-count LSB) | NO |
| float32 rounding | throughout | relative 2^-24 | yes, but negligible |
| `gp-0x6acc` int->float | `0x446ae`/`0x446b2` | **ZERO** | n/a |

`0x446ae`/`0x446b2` is `cvtf.ws` then `mulf.s` by `0x3A800000` = 2^-10: an s16 fits
exactly in float32's 24-bit mantissa and the scale is a power of two, so the
conversion is **exact**. The only proportional term is float32 rounding — at a bound
of ~5120 counts (5.0 normalized) that is 5.0 x 6e-8 = 3e-7 against a 4.88e-3 window,
**~16,000x of headroom.**

**Why V27 bricked, and why a gain change is not the same failure.** V21/V27-style
patches changed `shl 0x8 -> shl 0x9` at `0x42dae`/`0x42dca` (stock bytes verified
`c84a` / `c85a`) — **inside the integer twin**, while `FUN_00043e44` kept computing the
stock envelope. `notes/FUN_00043e44_FLOAT_MONITOR.md` states this directly: "The float path
has no analogous shift instruction to patch." That is not residual *scaling* — it is a
**structural divergence** where the residual becomes the full size of the modification
(thousands of LSB), instantly blowing a 5-LSB window.

Cal `0xC646C` (LKAS Q15 gain) is read at exactly **two** tp-relative sites: `0x2a1ee`
(inside LIVE `m_steer_torque_arbitration`, body `0x28ea6-0x2a30d`) and `0x2a904`.
**Neither is inside `FUN_00042af8` (`0x42af8-0x43e43`) nor `FUN_00043e44`
(`0x43e44-0x44a88`).** The gain multiply happens ONCE, in the int domain, upstream of
both twins; neither re-derives it. **A gain change cannot create an int/float
divergence — there is no duplicated computation of it to diverge.**

Rule of thumb this establishes: **editing a cal upstream of both twins is safe;
editing code inside one twin is what breaks lockstep.**

## The IIR arm cannot exceed its own LERP3 input

`gp-0x3574` (int IIR arm) has exactly 2 accesses, both in `FUN_00042af8`:
`ld.w` `0x42daa`, `st.w` `0x42dcc`. Mechanics: state held **Q8** (`shl 0x8`), EMA
`state += (alpha x (target<<8 - state)) >> 10` with alpha = cal `0xC6418` = **10**,
plus a `cmovle` overshoot snap at `0x42dc2`. **An EMA cannot exceed its input**, so
the arm is bounded by max(LERP3 output).

That LERP3 reads runtime arrays `gp-0x6430` (X) and `gp-0x6444` (Y), each with exactly
**one writer** (`0x38fd0` / `0x38fee`). The float twin reads the **same** runtime
arrays (`0x44002`/`0x44062` for X, `0x4402e`/`0x4406c` for Y). So what protects the IIR
arm is **not** "flat tables make it exact by construction" — it is that both twins
interpolate the same runtime data, which holds whatever values that array contains.

[UNVERIFIED] whether max(`gp-0x6444`) can exceed 5120 and win the three-way MAX —
the array is runtime-populated and I did not trace its source.
[UNVERIFIED] the LERP1 asymmetry flagged in `notes/FUN_00043e44_FLOAT_MONITOR.md`: the int
path applies an additive Y-shift to `gp-0x6444` before building its array, the float
path adds `lerp_a x lerp_b` in-loop. Algebraically equivalent for linear tables, but
the doc names a real saturation risk if the int LERP1 shift pushes past the u16
ceiling — and that risk IS magnitude-dependent.

## Consequence for a setpoint-clamp raise

`FUN_00043e44` never reads the LKAS setpoint `gp-0x69ae` nor the gain cal
`0xC646C` (tp offset `0x746c` absent from its read set). It consumes `gp-0x6acc`
as an **input**. Both sides of every tolerance therefore move together when the
clamp is raised — a raise does not open a lockstep gap. See
[[reference-accord-setpoint-limit-15360-lerp]] and
[[reference-accord-base-assist-lane-architecture]].
