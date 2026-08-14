---
name: reference-accord-pregain-deadband-c61b8
description: "A fixed 102-count deadband + sign-consistency gate sits immediately BEFORE the arbitration gain multiply. Quartering openpilot's PID shrank the signal into it, so it now occupies ~4x more of the working range."
metadata:
  node_type: memory
  type: reference
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-20T02:42:40.370Z
---

**Found 2026-07-20 in `FUN_00028ea6` (arbitration core), block `0x2a1ae`-`0x2a206`, stock `code.bin`. Leading FIRMWARE candidate for the ~5 mph small-command vibration.**

```
if (cal 0xC64A3 == 1 && gp-0x6806 == 0) {          # both must hold, else the block is SKIPPED
    if (|iVar34| <= L)                iVar34 = 0     # flat deadband
    else if (sign(iVar34) != sign(gp-0x6b30_prev)
             || gp-0x6b30_prev == 0)  iVar34 = 0     # sign-consistency rule
}
iVar34 = (iVar34 * ramp_gain gp-0x69b0) >> 15
st.h iVar34 -> gp-0x6b30                             # @0x2a206, feeds next cycle's sign test
```

- `L` = cal **`0xC61B8`** (`tp+0x71b8`) = **102**. ⚠ **MIXED SIGNEDNESS TRAP:** read `ld.h` **signed** @`0x2a1be` and `ld.hu` **unsigned** @`0x2a1ca`. Any edit must stay in 0..32767 to behave identically under both.
- ENABLE = cal **`0xC64A3`** (`tp+0x74a3`) = **1**, single byte, `ld.bu`, **sole reader image-wide**.
- `gp-0x6b30` has exactly 2 references image-wide, both inside this gate.

**Why it is a V38 regression:** `L` is a FIXED ABSOLUTE threshold in the **pre-gain** domain. With openpilot's PID quartered to compensate the 4× gain, the pre-gain domain operates 4× closer to zero for the same physical torque — the deadband did not move, the signal shrank into it. It now occupies ~4× more of the working range, so small low-speed commands that used to sit clear of it dither in and out: zeroed one cycle, passed the next. See [[reference-accord-gain-rescaling-invariance-partition]], which assigned the vibration to "upstream of the gain" **before** this trace ran.

✅ **RESOLVED AND ELIMINATED 2026-07-20.** The gate is enabled only while `gp-0x6806 == 0`, which the 9-state engage-ramp SM forces only after STEER_STATUS visits {3,4,7}. On V37/V38's cal set **4 and 7 are unreachable** (the torque channel saturates at 254 and the rate term at 800, against cals raised to `0xFF`/`0xFFFF`). That leaves `==3`, and **measured across 98,053 raw CAN-399 frames it is the LOW-SPEED LOCKOUT**: ~100% below 3 mph, 8.9% at 3-4 mph, **0% above 4 mph**. The operator has since confirmed the vibration is **speed-independent**, present at all speeds whenever LKAS commands torque and the wheel turns. So the gate is off wherever the symptom lives ⇒ **`0xC64A3 = 0` would be a no-op. Do not ship it.** The mechanism below remains true as a structural fact; it is simply not this bug. Original contradiction, kept for the record: Read literally the sign rule **self-latches**: once the gate stores 0, next cycle's test is `0 × x = 0`, which fails `bgt`, forcing 0 forever. The car's LKAS works, so one of these holds: **(A)** `gp-0x6806 != 0` in normal driving ⇒ gate inert and the fix is a no-op; **(B)** the latch reading is wrong ⇒ pure deadband ⇒ leading candidate; **(C)** `gp-0x6806` toggles periodically ⇒ the latch heals on a cadence ⇒ a **relaxation oscillator whose period IS the grinding**.

**Two clean negatives from the same pass, both worth a build each:**
- **Polarity `gp-0x6752` CANNOT chatter.** It is a static per-variant config byte parsed once at boot (`FUN_00048a40` record type `0x54`, shadow `gp-0x4c2d`), values `{0,+1,−1}`, re-validated only for memory integrity. The "bare unhysteretic sign multiplier near zero" hypothesis is refuted.
- **The long-running "is there an integrator before the gain?" disagreement is SETTLED — there are TWO different real variables.** `gp-0x3d3c` is a one-pole IIR filter (cals `0xC63EC`=992, `0xC63EE`=507, Q10; `iVar34 = gp-0x3d3c >> 5`); `gp-0x69b0` is a separate 0..0x8000 Q15 fade-in ramp gain driven by its own 8-state SM `gp-0x3d38`. **Neither is a torque-error integrator that winds up.** Both prior descriptions were half right.

**How to apply:** candidate mitigation is `0xC64A3` → `0x00` — single unsigned byte, sole reader, and it does **not** invent a code path: it forces the `bne 0x2a1e6` branch that already executes routinely whenever `gp-0x6806 != 0` (every re-engage ramp). Narrower alternative: `0xC61B8` → 0, removing the flat band but keeping the sign rule. **Do not build either until (A)/(B)/(C) is settled** — under (A) both are no-ops. Also still [OPEN]: the CAN-setpoint-domain equivalent of `L`=102 has not been back-propagated through the LERP cascade + IIR + `>>5`.

## 🛑🛑 CORRECTED 2026-08-14 — `gp-0x6806` IS **NOT** THE LOW-SPEED LOCKOUT. IT IS THE ENGAGEMENT FLAG.

This file's *"~100 % below 3 mph, 8.9 % at 3–4 mph, **0 % above 4 mph**"* reading is a **SPEED
CORRELATION MEASURED ON A CREEP-DOMINATED CORPUS**, not a property of the flag. On such a corpus
"engaged" and "below 4 mph" are nearly the same set, so `latActive` **reads as a lockout**.

**What `gp-0x6806` actually is [EVIDENCE, traced from the producer 2026-08-14]:**
> **The LKAS-engagement / steer-control-active flag, written ONLY by `FUN_00028ea6`'s engage-ramp state
> machine — `!= 0` when LKAS is active, `0` when it is not.**

- **16 stores image-wide: 8 live (all in `FUN_00028ea6`), 8 in the dead `[0x2a508, 0x2a939]` region.**
  Four live sites write non-zero (gate **disabled**), four write `r0` (gate **enabled**).
- At `0x293A6` the store is `mov 0x1,r6` → `st.b r6,-0x6806,gp` **in the same breath as `st.b r15,-0x3d38`
  with `r15 = 3`** — a state of the 8-state engage-ramp SM that drives the `gp-0x69b0` fade-in ramp.
  **An engage-ramp SM emits an ENGAGEMENT flag, not a speed flag.**
- **V67 measured it == `latActive` on 150,302 / 150,327 frames = 99.983 %**, all 25 disagreements
  single-frame edges. **An identity test on 150k frames beats a correlation inferred on 98k.**
- **Route `0x85` breaks the confound outright** — engaged p50 **39.6 km/h**, **45.5 s above 80 km/h**.
  No "0 % above 4 mph" flag survives that.
- ⭐ Third, independent: the symptom is **speed-INDEPENDENT** (+0.111 / +0.077 / +0.131 across
  10–30 / 30–60 / 60+ km/h). **A creep-only enable cannot host a speed-independent symptom.**
- ✅ Internal consistency: **Lever B arms on `!= 0`; this block arms on `== 0`** — exact complements.

## ⇒ THE BLOCK IS **STRUCTURALLY DEAD** FOR THIS SYMPTOM
The enable is `gp-0x6806 == 0` ⇒ **the deadband and the sign-latch run in MANUAL ONLY.** The symptom is
**engagement-required**: **73/88 = 83.0 % engaged vs 0/118 = 0.0 % MANUAL, Fisher p = 3.8×10⁻⁴¹**, zero
hits in 118 manual windows / 302 s, plus his own *"literally every bad symptom is LKAS engaged only."*
**A term that only runs in manual cannot produce a symptom that never occurs in manual.**
⇒ Both disarms (`0xC61B8` → 0, `0xC64A3` → 0) are **dead proposals**.

## ⚠ AND IT IS A **LATCHING KILLSWITCH**, NOT A HYSTERESIS — do not import backlash's describing function
The block never outputs a **lagged** input. It outputs the ramp-scaled input **or exactly zero**, and
once zero it stays zero until the enable drops. **Backlash's "phase lag that grows as amplitude falls"
does NOT transfer.** ⊕ The self-latch reading is **correct** (`0x2a1da mul r13,r6,r0` / `bgt`: `prev == 0`
⇒ product 0 ⇒ `0 > 0` false ⇒ re-zeroed and stored), **and the heal path is `0x2a1e6`** — when the enable
fails, control branches *past* the gate but *before* the state store, so `prev` refreshes. **The latch
heals whenever `gp-0x6806 != 0`.**

⚠ `0xC62EA` = 320 → 0 since ~V35 is a **byte fact that stands**; the *"we may have disarmed this block
ourselves"* inference built on it is **WITHDRAWN** — it was only ever reachable via the lockout reading.

See [[accord-verify-a-lerp-axis-before-designing-to-it]] — **verify a GATE'S ENABLE from its producer,
not from a label.**
