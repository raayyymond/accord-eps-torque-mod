---
name: accord-steerstatus3-speed-gated-but-report-only
description: "★★★★★ STEER_STATUS=3 (LOW_SPEED_LOCKOUT) IS genuinely speed-gated — speed_clamp_lo = cal 0xC62EA = 320 = 5.0 km/h. Falsifies the prior 'substate fallback, not speed-gated' claim. ⚠ ITS OWN 'report-only ⇒ the cal does not unlock assist' CONCLUSION IS FALSIFIED — see the correction header inside; lowering 0xC62EA DOES restore real authority."
metadata:
  type: reference
---

> 🛑 **CORRECTION 2026-07-25 — THE "REPORT-ONLY ⇒ CAL DOESN'T UNLOCK ASSIST" HALF OF THIS MEMORY IS
> FALSE. Lowering `0xC62EA` DOES restore real steer authority.**
> The evidence below is right: `gp-0x6807` has no torque-gating reader **outside** `FUN_00028ea6` and
> its dead twin `FUN_0002a30e`. The inference drawn from it is wrong, because **the load-bearing
> consumer is INTRA-FUNCTION**: `0x2937E ld.bu gp-0x6807` / `0x29382 cmp 0x2,r6` / `0x29384 bnh`.
> With `STEER_STATUS >= 3` control falls through to `0x2938E jr 0x29734` (the disengage path), skipping
> the engage block at `0x29392`-`0x293AC` which sets **`gp-0x6806` = 1 (= `STEER_CONTROL_ACTIVE`, packer
> `shl 3`)** and advances the authority ramp `gp-0x69b0`; the disengage arms then explicitly test
> `cmp 3,r6` @`0x29678` and store `r0`. Confirmed on-car: **zero** frames in ~305k ever have
> `STEER_CONTROL_ACTIVE=1` alongside `STEER_STATUS=3`.
> **Standing methodology rule: an "external readers" sweep CANNOT establish that a variable is
> report-only — always check intra-function reads.**
> See `docs/HANDOFF-2026-07-24-low-speed-steer-lockout.md` §6 and
> [[accord-v850-scan-traps-formatv-and-storezero]].

**FALSIFIES the prior kit claim "STEER_STATUS=3 is NOT speed-gated — it is a fallback when substate
`gp-0x67fe != 2`."** The substate term is real but it is only ONE conjunct of an AND-chain that also
contains a genuine two-sided **vehicle-speed window**.

## Complete writer enumeration for `gp-0x6807` (STEER_STATUS), BOTH encodings
`gp-0x6807 = 0xFEDF17F9` (odd ⇒ byte variable). Decoder validated by reproducing the kit's
`gp-0x4f60` figures exactly (4-byte: 64 `ld.h` + 5 `st.h` = 69; 6-byte: 7, in the 3 named functions).
- **4-byte disp16:** 20 `st.b` writers + 20 `ld.bu` readers.
- **6-byte V850E2 extended-disp:** **0 accesses of any subop** ⇒ the table is complete.
  (Ext-form decode: `hw0 ∈ {0x0784, 0x07A4}`, `disp23 = (hw2<<7) | ((hw1>>4)&0x7F)`,
  `reg3 = (hw1>>11)&0x1F`, subop = `hw1 & 0xF`.)

**10 live writers in `FUN_00028ea6`** (sole caller `FUN_0002214a` = w_steer_control_task — confirms the
kit: the debounce SM is inlined here). **10 in `FUN_0002a30e` = DEAD (0 callers).**

| live site | value | branch |
|---|---|---|
| `0x29160` | 7 | outer gate fails |
| `0x2917C` | 6 | `(gp+0x6400) & 8` set |
| **`0x29194`** | **3** | **`!speed_valid`  ← THE ONLY value-3 writer** |
| `0x291BC` | 7 | DTC-0x49 counter saturated → `FUN_00016de6(0x49,1,1,1)` |
| `0x29282` | var | debounce `cVar19` |
| `0x2928E`,`0x292AE`,`0x2930A`,`0x2931A` | 4 | debounce fire / decay |
| `0x292F8` | var | debounce `cVar19` |

## The value-3 guard = `speed_valid`, and it IS a speed window
`STEER_STATUS = 3` is the `else` of `if (bVar2)`. `bVar2` (the AND-chain) requires **all** of:
1. **`cal 0xC62EA (=320) <= gp-0x6a5e <= cal 0xC62E8 (=12800)`**, bypassable when `gp-0x68b3 != 0`.
   `gp-0x6a5e` is **VOTED VEHICLE SPEED at 64 counts/km/h** ⇒ **window = [5.0 km/h, 200.0 km/h]**.
   See [[accord-gp6a5e-is-voted-vehicle-speed]]. **`0xC62EA` IS the `speed_clamp_lo` analogue** of the
   Clarity edit.
2. `bVar1` = all five voter channels inside `[-6400, +32000]` (= `[-100,+500] km/h`) AND
   `gp-0x67f4 == 1` (voter-converged flag) AND `gp-0x6a5e < 0x7d01`.
3. **`gp-0x67fe == 2`** (assist substate engaged) — the term the earlier trace saw and stopped at.
4. `gp-0x69aa == 0x8000` — a **degenerate equality** (cal `tp+0x73f2 = 0x8000` is both bounds).
   `gp-0x69aa` = Q15 derate product, MIN-only, literal-seeded `0x8000`, written once @`0x45342` in the
   governor ⇒ the test means "**no derate of any kind active**".
5. `gp-0x69ae` (LKAS setpoint) within `±0x4000`.

**The standstill exemption:** `gp-0x68b3` is written in `FUN_0004d0d0` **only when `gp-0x6a62 == 0`**
(exactly zero = true standstill) — so 0 km/h can bypass the window, but **1..319 counts
(0 < v < 5 km/h) cannot.** That asymmetry is the signature of a deliberate low-speed lockout.

## 🛑 BUT: `gp-0x6807` IS REPORT-ONLY — this is the load-bearing caveat
Only **two** readers exist outside the producing FSM:
- `0x55C96` → `FUN_00055c42`, the **CAN 399 packer** (`STEER_STATUS` signal).
- `0x4E8EC` → `FUN_0004e82e`, a **56-byte diagnostic/UDS record builder** (`len = 0x38`); byte 9 =
  `gp-0x6807`. Also packs `gp-0x69ae*13/4`, `gp-0x4f60*125/128`, `gp-0x6a56`, `gp-0x6b38`.

**No reader gates motor torque, motor enable, or `FUN_00045608`.** The `!speed_valid` branch only sets
the status byte and resets the DTC-0x49 counters (`gp-0x6758`, `gp-0x6757`) — it zeroes no command.
⇒ **Lowering `0xC62EA` would change what the EPS REPORTS and would let the DTC-0x49 torque-plausibility
debounce run below 5 km/h; it would NOT by itself unlock low-speed assist.** openpilot already
tolerates `LOW_SPEED_LOCKOUT`, so the practical low-speed blocker is likely `minEnableSpeed`, not this.

## ✅ Completeness: the arbitration's OTHER speed reads are dead — belt AND braces
`gp-0x6a5e` (speed) is read **5×** inside `FUN_00028ea6`: `0x28F0E`/`0x28F1E` (the `bVar1`/`bVar2`
STEER_STATUS window, above) and **three deeper reads at `0x29774`, `0x298E8`, `0x299B2`**. All three
feed the *same* LERP over cal axis `tp+0x7736..0x773c` (X) / `tp+0x773e` (Y) producing `sVar27` →
`gp-0x6a7e` / `gp-0x6b2c`. Two independent reasons they cannot produce a live speed→torque effect:
1. **All three are guarded by `gp-0x6809 == 1`, and `gp-0x6809` has ZERO writers in BOTH encodings**
   (0 four-byte `st.b`, 0 extended-form; 8 readers `0x2975A, 0x29808, 0x29964, 0x29A2C, 0x2B09E,
   0x2B13E, 0x2B288, 0x2B3DE`). Confirms the kit's dead-gate finding with the validated decoder ⇒
   control always takes `goto LAB_00029974`. [[reference_accord_gp6809_zero_writers_confirmed_dead_gate]]
2. **The LERP is degenerate anyway:** record `@0xC6734` = `[count=4, X=[0,31872,31936,32000],
   Y=[0,0,0,0]]`. X/64 = `[0, 498, 499, 500] km/h` (multiples of 64 ⇒ another speed axis; top 32000
   counts = 500 km/h = the voter clamp). Y all zero ⇒ output 0 regardless.

⇒ **The ONLY live use of vehicle speed in the arbitration is the STEER_STATUS window.** Combined with
"`gp-0x6807` has no torque-gating reader", there is **no live speed→torque path in the arbitration**.

## Safety if it is ever edited
`0xC62EA`/`0xC62E8` are plain u16 cals in the `0xC6xxx` block (`ld.hu`, unsigned) — no float mirror
found on these two. **But lowering `speed_clamp_lo` ENABLES the DTC-0x49 debounce in a regime where it
currently never runs**, and V36/V37 history shows that counter reaching `FUN_00016de6(0x49)` →
`STEER_STATUS=7` → dash lights + openpilot LKAS drop. `0x49` is **not** hard-fault eligible
(`rec 0xB8538 [+8]=0x0000`), so no motor-off — but a dash-light regression is plausible. Treat as a
drivability/DTC risk, not a brick risk.
