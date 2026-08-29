# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔⛔ **V162/V163 SUPERSEDED — `gp-0x6ad4` IS STIFFNESS, NOT DAMPING. STRUCTURALLY ELIMINATED AT 6–9 Hz.**
Built, then killed by its own GATE 2 before it ever flew. **The rationale was FALSE.**

### ✅ THE PID'S TRANSFER FUNCTION, COMPUTED FROM THE BYTES
Structure (model, `FUN_0003a382`): `err = clamp(gp-0x4f60 - clamp(gp-0x6ad6), ±0x2800)`, then
`P: IIR((err*Kp)>>10 * 0x20, pole tp+0x7450)` · `I: ((Ki*err)>>10)+state` · `D: ((err-state)*Kd)>>10`,
summed as `gp-0x6ad4 = (((I+D+P)>>5) * LERP_out)>>10 * polarity`.
Gains at the ratchet's own operating point `gp-0x6ac0 = 99`, all three LERPs flat there:
```
   D  0xC6B1E  Y=256   => Kd = 0.2500
   I  0xC6B0A  Y=98    => Ki = 0.0957
   P  0xC6ADE  Y=2048  => Kp = 2.0, then x32 = 64.0
   🛑 IIR pole 0xC6450 = 1024 => a = 1.000000 => THE "IIR" IS A PASS-THROUGH. No smoothing at all.
```
```
   at 7.8 Hz, fs = 1 kHz:        |H|        phase      share of |sum|
       P                        64.000       0.0 deg      99.88 %
       I                         1.953     -88.6 deg       3.05 %
       D                         0.012     +88.6 deg       0.02 %
       SUM                      64.08       -1.7 deg
```
✅ **[EVIDENCE] `gp-0x6ad4` IS A NEARLY PURE PROPORTIONAL TERM AT THE RATCHET FREQUENCY** — phase
**−1.7°**, derivative contributing **0.02 %**. A 0°-phase term is **STIFFNESS, NOT DAMPING**.

### ⛔ WHY THAT KILLS THE BUILD
Raising the ceiling raises **loop gain with no phase lead** into a resonance the kit has measured at
**Q 14–29 (ζ 0.017–0.036)**. Raising proportional gain around a lightly-damped resonant plant
**reduces stability margin and increases resonant peaking** ⇒ V162/V163 would most likely make the
ratchet **WORSE**. Both are **SUPERSEDED**, artifacts renamed `SUPERSEDED-DO-NOT-FLASH-PSTIFFNESS-*`.

### ⭐ AND THE LANE IS ELIMINATED ON STRUCTURE, NOT ON A NULL
For D to matter at 7.8 Hz it needs `Kd · 2sin(ω/2) ≈ |P|`; with `2sin(ω/2) = 0.049` that demands
`Kd ≈ 1306`, i.e. a Q10 Y of ~1.34 MILLION. **The cell is a u16 — max 65535 gives Kd = 64, |D| = 3.14
against P's 64.0, a net phase of only +1.06°.** => **the derivative path is ~1300x too weak BY DESIGN
and the register width cannot close the gap.**
✅ **`gp-0x6ad4` IS STRUCTURALLY INCAPABLE OF DAMPING AT 6–9 Hz.** This properly closes one of the
model's five sensor-fed survivors — the model was right that V56's ~21 Hz null did not settle it, but
**structure settles it now.** Survivors remaining: **{r24/r26, gp-0x6b26, gp-0x6bbe, V89 plant-model}**.

### ⚠ THE MISREADING TO NOT REPEAT
The model calls it *"the most reachable **AUTHORITY** of any gated lane"* — **authority, not damping.**
It never claimed the lane damps at 6–9 Hz; it said the lane had never been **scored** there. I read
"resonance PID" and supplied "therefore it damps." ⭐ **A LANE'S NAME IS NOT ITS TRANSFER FUNCTION.**
Compute magnitude AND phase at the symptom's own frequency **before** building — which is exactly what
CLAUDE.md's GATE 2 requires, and it took ~20 lines of Python once the gains were located.
⊕ **V160/V161/V158 are UNAFFECTED** — independent lanes, and Lever B's rationale is a *measured*
single-variable result (6–9 Hz 0.859, 15–22 Hz 0.549, LF null), not a structural inference.

