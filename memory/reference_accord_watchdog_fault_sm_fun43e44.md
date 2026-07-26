---
name: reference-accord-watchdog-fault-sm-fun43e44
description: "FUN_00043e44's 7-flag weighted trip is escalated by a debounce to DTC index 0x1D. gp-0x6acc is sanitized at +/-8192 (out-of-range -> zero); assist-inclusive envelope is 7322, not the old 4342 estimate. Wall checks compare same-cycle float/int re-derivations, so symmetric wall edits preserve lockstep."
metadata:
  node_type: memory
  type: reference
---

Structure of the fault trip in `FUN_00043e44` (the float watchdog), disassembled and constant-verified 2026-07-18 against stock `code.bin` while closing the V38 setpoint-slew question. Every claim below is from directly quoted disassembly plus numeric decode of the `movhi` immediates.

## The trip is a weighted flag sum with a debounce escalator

Seven independent plausibility checks each set a float flag, at these addresses and weights:

| addr | weight | what it checks |
|---|---:|---|
| `0x4464e` | 1 | `\|float twin lp − gp-0x6af6/1024\| > 5/1024` — **dir1 int/float corridor lockstep** |
| `0x44672` | 2 | same for `r20` vs `gp-0x6b00` — **dir2 int/float corridor lockstep** |
| `0x44794` | 4 | integrator arm |
| `0x447da` | 8 | — |
| `0x44866` | 16 | — |
| `0x448ee` | 32 | torque arm |
| `0x4491e` | 64 | — |

Summed at `0x44926`–`0x4493a` → **max possible 127**. The trip compares against **128.0** (`movhi 0x4300` @`0x44a26`, `cmp`/`bgt` @`0x44a2e`).

**127 < 128 by design: no single-cycle combination of all seven flags can trip.** The trip only happens via the debounce state machine.

## The debounce escalator (gp-0x3540 / gp-0x3550)

State machine at `0x4493e`–`0x449e8`:

- any flag set → integrate `0.001`/cycle (`mov 0x3a83126f`) into `gp-0x3550`
- accumulator ≥ `0.01` (`mov 0x3c23d70b`) → advance to state 3
- state 3 (and the default branch) → `r7 = sum + 1024.0` (`movhi 0x4480`) → **1151 > 128 → TRIP**
- flags clear → decay `0.0005`/cycle (`mov 0x3a03126f`)

`0.01 / 0.001` = **10 cycles ≈ 0.1 s at 100 Hz** of sustained flag before trip. The SM enable gate is cal `0xC64A4` (checked `@0x44950`).

## The trip DOES reach the DTC setter — "report-only" is wrong or imprecise

```
00044a4c: jarl 0x000462e6,lp      ; r6 = 0x3f1b, r9 = 128.0

FUN_000462e6:
0004631e: movea 0x1d,r0,r6        ; DTC index 0x1D
0004631c: mov   r26,r7            ; = 0x3f1b (zxh of the passed code)
00046322: mov 0x1,r8
00046324: mov 0x1,r9
00046326: jarl 0x00016de6,lp      ; FUN_00016de6(0x1D, 0x3f1b, 1, 1)
```

`FUN_00016de6` is the **same DTC-setting routine** that the V37 saga's DTC 0x49 went through (`FUN_00016de6(0x49,1,1,1)`). So this monitor invokes DTC machinery.

⚠ **This bears on a pre-existing CONTRADICTION between two memories:**

- [[reference-accord-corridor-lockstep]] says: "Accumulator ≥128.0 → `FUN_000462e6(0x3f1b)` **hard shutdown** (DTC `0xF00049`)"
- [[reference-accord-override-snap-state-machines]] says: the dual-path int/float monitor "is **REPORT-ONLY — it does NOT gate torque**"

**Resolved 2026-07-18 — `corridor_lockstep` is right, `override_snap` is WRONG.** There are **two** monitors, and both reach the DTC manager:

| | Monitor 1 | Monitor 2 |
|---|---|---|
| function | `FUN_00042af8` (shaper) | `FUN_00043e44` (this one) |
| accumulator | `gp-0x3564`, **int**, +10/cycle, thr **100** | `gp-0x3550`, **float**, +0.001/cycle, thr **0.01** |
| escalation | `+0x400` → sum ≥128 | `+1024.0` → sum >128 |
| trip call | `FUN_0004613e` → `FUN_00016de6(**0x1c**, …)` | `FUN_000462e6` → `FUN_00016de6(**0x1d**, 0x3f1b, 1, 1)` |

⚠ An earlier draft of this note guessed "report-only may be true of Monitor 1." **That guess was backwards.** `gp-0x3564` (Monitor 1) is traced at instruction level to a **hard shutdown with power-cycle recovery** — it is the V25/V26 brick mechanism:

```
FUN_00016de6(idx,…,1,1)
  -> FUN_0001611e(record)   ; only escalates if bits 0x41 set ("hard fault eligible")
  -> FUN_00018738           ; trip counter >= threshold
     -> gp-0x685c = 1       ; DTC latch byte
     -> FUN_00018bc0        ; gp-0x3ef8 = 1  (single-opcode latch write)
  -> FUN_00019f7c (per cycle from main loop) sees gp-0x685c != 0
     -> gp-0x67fa = 8 (shutdown state)
     -> FUN_0001a16a -> FUN_00045608(3,0,0x8000,0x8000)   ; MOTOR OFF
     -> gp-0x3ee8 = 1       ; latches; no re-entry until POWER CYCLE
```

So `override_snap`'s *"gp-0x3564 … REPORT-ONLY (does NOT gate torque)"* is **contradicted by a full trace of gp-0x3564 to motor-off**. Do not rely on it.

**Monitor 2's trip is REACHABLE — verified on stock bytes 2026-07-18.** The fault-SM enable gate read at `0x44950` (`ld.bu 0x74a4[tp]`, tp=`0xBF000`) is **`0xC64A4` = `0x00` = ENABLED** (gate==0 → `bne` not taken → SM advances). A prior tracer pass misread this as `0xC74A4` = `0xEA` — an **off-by-`0x1000` tp+disp slip** — and wrongly concluded "Monitor 2 permanently gated off, never needs fixing." That conclusion is **unsafe and retracted**; the stale sections in `.claude/agent-memory/firmware-codepath-tracer/reference_accord_consistency_monitor_hardshutdown.md` are now struck through in place. **V38 does not touch `0xC64A4`.**

What remains **[UNVERIFIED]**: whether index `0x1d` specifically is *hard-fault-eligible* (i.e. whether its record carries bits `0x41`, the condition `FUN_0001611e` gates escalation on). The agent-memory doc infers `0x1c` and `0x1d` both map to DTC `0xF00049` but marks that `[I]`, pending a `FUN_00047d06` / index→DTC-binding trace. **Do not assert the `0x1d` ↔ `0x49` ↔ `0xF00049` mapping without that trace.**

Separately: the monitor's **output word `gp-0x6906`** (written once @`0x449fa`) has **zero readers** — verified across four addressing modes (gp-relative loads, absolute literal `0xFEDF16FA`, `movhi`+`movea` reconstruction over 667 sites, `movea -0x6906,gp,rX`). That word alone is inert; the DTC call is independent of it.

**Consequence for V38:** these monitors are **hard-shutdown capable**, not advisory. The matched int/float mirror discipline is not merely good practice — it is what stands between a corridor/boost cal edit and a roadside motor-off requiring a power cycle. That is exactly how V25/V26/V27 bricked.

## Why the LKAS setpoint raise cannot touch this — CLOSES the [OPEN] slew question

The `±5/1024` compare at `0x4463a`:

```
0004462a: ld.h  -0x6af6[gp],r7    ; INT wall
00044636: mulf.s r9,r1,r2         ; r1 = 0x3A800000 = 1/1024 -> r2 = wall/1024
0004463a: subf.s r2,lp,r10        ; r10 = float_twin - wall/1024
0004463e: movhi 0x3ba0,r0,r7      ; +5/1024 = +0.0048828125
00044646: movhi -0x4460,r0,r14    ; -5/1024
```

**Both operands are same-cycle redundant computations of the SAME bound in two datatypes:**

- `gp-0x6af6` (int wall) is written by `s_motor_torque_rate_shaper` at `0x43a7e`/`0x43e38` (only writers; `search_instructions` on `-0x6af6` returns exactly 5 sites: 2 writes there, 2 reads there, 1 read here).
- `lp` (float twin) is built inside `FUN_00043e44` from the float corridor/boost mirrors `tp+0x7598/0x75a4/0x75ac/0x75c4` = `0xC6598/A4/AC/C4`.

So it is an **int-vs-float lockstep**, *not* a predicted-vs-lagging-actual check. **The "actual lags predicted" framing that generated the `[OPEN]` slew concern in [[reference-accord-setpoint-limit-15360-lerp]] was a mischaracterization** — the correct model was already recorded in [[reference-accord-corridor-lockstep]].

The LKAS setpoint's **only** entry into this function is the merged command `gp-0x6acc` @`0x4467a`, and the `±8.0` compare there is a **sanitize-to-zero, NOT a gate that excludes the command from the math**:

```
0004467a: ld.h  -0x6acc[gp],r16
00044686: movhi 0x3f50 (double 2^-10)  ; value = gp-0x6acc / 1024
00044692: movhi 0x4020 (double  8.0)
00044696: cmpf.d lt,r10r11,r12r13,0x1  ; is 8.0 < value?
0004469e: be 0x000446b8                ; TRUE (out of range) -> mov r0,r16 = ZERO
000446ae: cvtf.ws r16,r13 / mulf.s     ; fallthrough (in range) -> KEEP the value
```

⚠ **POLARITY CORRECTION — an earlier draft of this note had this exactly backwards.** `trfsr` sets Z when the condition is TRUE, so `be` takes the branch on TRUE, and the TRUE case is the **out-of-range** one, which **zeroes**. Verified against the unambiguous reference case at `0x43eda`–`0x43f1e`: the same shape applied to `gp-0x4f60` (driver column torque) with a `±25.0` (`movhi 0x4039`) threshold — a plausibility sanitize at ±25600 counts. Out-of-range → zero; in-range → keep.

The old **4342** estimate omitted assist lanes that join before the first governor. The conservative envelope is `4762 + 2560 = 7322` counts = 7.15 normalized, still below 8.0, so it is **KEPT** with 870 counts of sanitize headroom.

**⇒ The correct reason the raise is safe is NOT "the setpoint is gated out."** It is:

1. `FUN_00043e44` never reads the setpoint `gp-0x69ae` nor the gain cal `0xC646C` (tp offset `0x746c` absent from its read set). It consumes `gp-0x6acc` as an **input**, and **every tolerance compares this function's float re-derivation against the integer shaper's stored result for the same quantity** — so both sides move together when the clamp is raised. A raise translates both, it does not open a gap.
2. Independently, movement **away from zero** is slew-bounded upstream: `gp-0x6acc` has exactly two writers (both in `FUN_000456a4`) with no rate limit, but `gp-0x6ace` uses step `(cal × Q15)>>15`, cal `0xC6206`=512 or `0xC6208`=205. Movement toward zero is immediate. The away-from-zero step is independent of the setpoint clamp value.

**[RESIDUAL RISK — assessed LOW; an earlier draft of this note OVERSTATED it]** A first pass flagged "the int/float residual scales with command magnitude, as it did in V27" as the top open risk. That was wrong on all three legs:

1. **The scaling theory is already falsified in this kit.** [[reference-accord-corridor-lockstep]]: *"The 'divergence=2×residual' premise was a **mis-ID** of the max's secondary arm (the large driver-torque demand, not a small fixed table)."*
2. **V27 failed from ASYMMETRY, not magnitude.** Its trampoline doubled the whole float twin (incl. the driver-torque arm) while the cal doubled only the int corridor arm → *"divergence ≈ FULL torque, not a 5/1024 residual."* V38 makes no asymmetric edit — corridor and boost move on **both** sides, exactly mirrored.
3. **The gain `0xC646C` is monitor-independent.** `search_instructions` on tp offset `0x746c` → exactly 5 readers (`0x2a1ee` in `m_steer_torque_arbitration`, plus `0x2b656`/`0x2c488`/`0x36686`/`0x3684a`), **none** inside `FUN_00043e44` (`0x43e44`–`0x44a88`) or `s_motor_torque_rate_shaper` (`0x42af8`–`0x43e43`). Confirms the kit's *"GAIN 0xC646C monitor-INDEPENDENT, flashed+road-validated."* The 4× gain reaches the monitors only through the command value, where both sides derive from the same number.

V29's principle — matched-symmetric int+float edits leave *"the stock ±5/1024 float-vs-int residual UNTOUCHED"* — is precisely V38's shape (corridor **and** boost, both flat, exact at 1/1024). V38 extends the pattern to boost where V29 left it stock, but V31/V37 already flashed matched boost edits at 4096/4.0 and drive clean.

**Calibration note for future sessions:** overstating a risk is as much a calibration failure as understating one. Before escalating a concern to "top risk", check whether this kit's own falsified-hypothesis record already answers it — the V28 entry in [[reference-accord-corridor-lockstep]] answered this one.

## Why V38's corridor/boost edits are safe against flags 1 & 2

Flags 1 and 2 *are* fed by cals V38 changes. V38 sets **all four** tables FLAT and exactly mirrored:

| | int | float | int/1024 |
|---|---:|---:|---:|
| corridor dir1 Y[0..1] | +5120 | +5.0 | +5.0 ✓ |
| corridor dir2 Y[0..1] | −5120 | −5.0 | −5.0 ✓ |
| boost Y[0..2] | 5120 | 5.0 | 5.0 ✓ |

Because every Y row is **flat**, both LERPs return their constant regardless of axis position — so int/float agreement is **exact by construction**, independent of axis scaling or interpolation rounding. This is the discipline V25/V26/V27 violated (and bricked on) and V29 onward respected. See [[reference-accord-corridor-lockstep]] for that lineage.

**[UNVERIFIED / residual]** the wall is a **three-way MAX** that also includes an **IIR arm** (`gp-0x3574`, column velocity) which is *not* a table. If that arm can exceed 5120 and win the MAX, int/float agreement there is not guaranteed by V38's flattening. Raising the flat arm to 5120 makes the flat arm win *more* often than stock (a margin improvement), but whether the IIR arm can ever exceed 5120 was **not** determined. This is the remaining open edge on flags 1–2.

## Where the real per-cycle slew limiter lives (and where it does NOT)

Traced independently by a `firmware-codepath-tracer` pass while answering "is there a rate limiter between the clamped setpoint and `gp-0x6acc`?":

- `gp-0x6acc` (`0xFEDF1534`) has **exactly two writers**, both in `m_post_governor_torque_comp_add` (`FUN_000456a4`): `0x45942` (normal, `r12 = gp-0x6ace + comp`) and `0x45932` (debug, gated by magic `0x49d6b173` **and** cal `tp+0x74ba`, which reads **0x00** in stock → **dead path**). **No rate limit at this stage.**
- The per-cycle slew limit is **one stage upstream**, in `m_motor_torque_governor` writing `gp-0x6ace` at `0x454d2`/`0x454e0`/`0x4559c`/`0x455ae`: previous value held in `gp-0x138a`; step `= (cal × Q15_scale) >> 15` with cal = `tp+0x7206` (**`0xC6206` = 512**) when `gp-0x67f5 == 0`, else `tp+0x7208` (**`0xC6208` = 205**).
- Governor binder: `s_clamp_i32(gp-0x6b94, ±(gp-0x4f64 × scale) >> 15)` with `gp-0x4f64` from cal **`0xC6202` = 4762** — the dominant high-end binder, well below the static `±0x2000`.

**Consequence:** the per-cycle step is a function of cals `0xC6206`/`0xC6208`, **not of the setpoint clamp value**. Raising the clamp cannot increase the rate of change of `gp-0x6acc`; it only extends how many cycles the ramp runs before settling. This is the clean, independent closure of the "fast setpoint slew" concern.

⚠ **CORRECTION — cal `0xC64DE` is NOT a command-path ramp step.** `build_v18..v38_tva.py` label it `"RAMPSTEP tp+0x74de re-engage ramp step 17->27 (V18 EME ramp)"`. Its 18 read sites are **all** in the `0x29xxx`/`0x2axxx`/`0x2bxxx` arbitration / `STEER_STATUS` / ENABLE region, mostly `ld.bu` — none in the command/governor path. The V18-era "EME ramp" label is **not supported**. (Note the builders patch it as a **byte** `0x11`→`0x1B`; a `u16` read at that address yields 25617 = `0x6411`, so the byte framing is the right one — the dispute is about *which subsystem it belongs to*, not its width.) This is a **labeling** correction; the edit has ridden along since V18 on flashed, road-validated builds, so it is not a new safety concern — but do not reason about it as a command ramp.

Related: [[reference-accord-corridor-lockstep]], [[reference-accord-override-snap-state-machines]], [[reference-accord-setpoint-limit-15360-lerp]], [[reference-accord-lkas-delivery-and-governor]]
