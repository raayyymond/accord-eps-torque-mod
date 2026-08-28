---
name: accord-the-78hz-mode-does-not-move-with-firmware-gain
description: "Across 16 mod routes spanning a 2x change in the forward gain 0xC6CD0 (3564 / 5346 / 7128), the 7-9 Hz mode's centre frequency does not move: Spearman(gain, f0) = -0.015, p = 0.954, and the group medians are non-monotone (7.764 / 8.008 / 7.617 Hz). That is the signature of a fixed MECHANICAL resonance rather than a relocatable closed-loop pole, which matters because firmware can then only DAMP the mode - and the damping route is measured-closed by the +-511 rail. The remaining firmware route is excitation reduction, which is what V121 does."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 THE 7.8 Hz MODE **DOES NOT MOVE** WITH FIRMWARE GAIN — it is mechanical

## THE TEST, AND WHY IT DECIDES SOMETHING
A closed-loop pole **moves** when loop gain changes; a mechanical resonance does not. The kit already
used exactly this to classify the ~23 Hz line, which **moved 20.3 → 23.0 Hz across three 4× routes**
([[accord-the-8x-gain-is-the-carrier]]). Applying it to the 7-9 Hz mode across 17 routes whose
forward gain `0xC6CD0` spans **3564 / 5346 / 7128** and whose relay knee spans **300 / 600 / 1800**:
```
   Spearman(gain 0xC6CD0, f0) = -0.015   p = 0.954      <- NO relationship
   Spearman(knee  0xC40BC, f0) = +0.332  p = 0.193      <- not significant

   f0 by forward gain:  3564 (n=6) 7.764 Hz | 5346 (n=9) 8.008 | 7128 (n=1) 7.617 | 65535 stock (n=1) 6.836
   mod routes span 7.42 - 8.40 Hz; spectral resolution +-1.3 % at 7.8 Hz
```
✅ **Across a 2× change in forward gain, `f0` does not move, and the group medians are
non-monotone.** ⇒ **the 7.8 Hz mode behaves as a FIXED MECHANICAL RESONANCE, not a relocatable
closed-loop pole.**
⊕ Consistent with [[accord-ratchet-is-a-lightly-damped-resonance]] (ring-down ζ 0.017-0.036, Q 14-29,
motor/rack-side, limit cycle excluded) and with
[[accord-the-742hz-mode-is-stocks-and-our-q-is-lower]].
⚠ **A self-correction:** my script's own verdict line said *"f0 MOVES ⇒ closed-loop pole"* because it
tested **max/min spread (22.9 %)**, which is dominated by the **single stock route** at 6.836 Hz whose
IQR [6.20, 7.86] is wide and overlaps the mods. **Spread across heterogeneous routes is not the test;
the correlation with the gain is.** The stock-vs-mod shift is itself **not established** at n = 1.

## 🛑🛑 WHAT THIS MEANS — stated plainly, because it limits what can be promised
The three things firmware could do to a resonance are: **move it, damp it, or stop exciting it.**
```
   MOVE IT   -> refuted here: f0 is invariant to a 2x forward-gain change
   DAMP IT   -> measured-CLOSED: [[accord-the-damping-route-is-closed-by-the-rail]] -- Y[1] at -24000
                rails 32.32 % at 10-25 km/h, V108 already rails <=10.45 % at 24-40 km/h where the
                symptom lives, and the +-511 clamp 0xC407E cannot be raised (V73 -> V74/V75 faulted)
   EXCITE IT LESS -> the ONLY route left.  That is V121.
```
⇒ **The 7.8 Hz peak-turn oscillation may not be fully eliminable in firmware.** A fixed, lightly
damped mechanical mode that the firmware can neither relocate nor damp further can only be *driven
less hard*. **Reducing excitation reduces its amplitude; it does not remove the mode.**
✅ **This is not a counsel of despair — it is the correct target definition.** V121 aims at exactly
the one thing left, and [[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]] says the
excitation path contains a hard nonlinearity, which is what V121 softens. ⚠ Its effect remains
**UNKNOWN** and its mechanism **[BELIEF]**.
🛑 **What should NOT be promised: that any firmware build eliminates this oscillation entirely.**
The honest claim is *"reduce how hard it is driven"*, and the pre-registered card
`docs/scoring/SCORING-V121-preregistered.md` is written to measure exactly that.
Tool: `analysis-2020accord/verify/mode_frequency_vs_gain.py`.
