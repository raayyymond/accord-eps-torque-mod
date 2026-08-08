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
