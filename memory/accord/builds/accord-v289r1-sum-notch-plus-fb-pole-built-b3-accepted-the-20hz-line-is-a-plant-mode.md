---
name: accord-v289r1-sum-notch-plus-fb-pole-built-b3-accepted-the-20hz-line-is-a-plant-mode
description: "V289 rev 1 (2026-09-08) = V282 + a Q14 notch code cave (20.036 Hz, Q 3.0, DC exactly 1) on the clamped LKAS loop OUTPUT (hook 0x2A174 → 0xC4C00, before the 5 Hz output lag) + fb lag pole 0xC63E8/EA 923/1560 → 875/2301 (16.5 → 25 Hz, DC held); 185 B / 10 runs / TWO CRC pages; telemetry b4.5 = sign(S−y), b4.7 = |S−y| ≥ |y|. Adversarial: A/C/D PASS, B FAIL on B3 (capped-step peak rate ×0.91, accel ×0.93; steady ×1.00) — the OPERATOR ACCEPTED rev 1. Basis: the 20 Hz line is a PLANT MODE the loop de-damps (f pinned across Kp 248–696, +0.4 Hz with gain, ζ falls with gain). Expected: rings decay ~1.7× faster, not a cure."
metadata:
  type: project
---

# V289 rev 1 — notch on the loop output + fb pole 25 Hz, built and accepted (2026-09-08/09)

| claim | status | method |
|---|---|---|
| the 20 Hz line is a plant mode the loop de-damps, not the loop crossover | EVIDENCE | 9 routes / 5 builds / 529 episodes: f 20.03–20.08 Hz on every build; Kp 287→696 moves it +0.4 Hz (crossover predicts −2..−4 Hz); ζ 0.036→0.019 with gain, stable; plant rate/T bump ×1.7 at 18–21 Hz with flat phase |
| the record's PM 35–60° was a 3.9 ms stream-offset artefact | EVIDENCE | loopshape20_loop_model re-derivation; the loop sits at |L| 0.8–0.95, −170..−185° at 20.3 Hz |
| both Honda lag filters (5.05 Hz output lag 0xC63EC/EE; 16.5 Hz fb lag 0xC63E8/EA) are INSIDE the rate loop and had never been touched | EVIDENCE | TRACE-2026-09-08 (decompile + bytes; my own read of 0x2A170–0x2A1F8) |
| 0x2A1E6 multiplies y × the engagement ramp gp-0x69b0 (not |fb|) | EVIDENCE | decompile + register census; corrects the V287 design doc |
| hook 0x2A174 is the convergence point of every route; scratch r6/r7/r9/r13; live r11/r14/r15/r16/r22/r24/r27/r29/lp | EVIDENCE | tracer + adversary A (61/61 vs Ghidra on the imported image) |
| state run gp-0x6c44..gp-0x6c39 has zero accessors, boots to 0 | EVIDENCE | raw scan incl. ld.b/st.b/bit ops + Ghidra (adversary D); the earlier halfword-only census was wrong on 2 of 3 runs |
| realised notch 20.036 Hz, Q 3.007, −47.6 dB, DC 254/254; fb DC 30.891→30.886 | EVIDENCE | coefficients decoded from the image immediates by three independent decoders |
| GATE 2: |L|<5 Hz +2 %, 3.9 Hz +0.56°, 7 Hz gate 1.005, Ms 3.8→2.0, step-ring ζ 0.016→0.038 | EVIDENCE on the census plant (BELIEF on the plant itself) | adversary B, bytes-derived elements |
| B3: capped-step peak rate ×0.909, accel ×0.929; steady ×1.00; open-loop peak torque identical | EVIDENCE | byte-exact closed-loop mirror; the design's "×1.00" was the fb-operand notch topology |
| a bare notch re-arms the 7 Hz strong-turn ring (gate 1.079); fb pole alone is a blind dose | BELIEF (model) | design §5 |

**Why it matters:** first in-loop filter on the rate loop's own output and first move of the fb pole in 285 images; the class
that the V288 null pointed at. Two CRC pages change (the fb cells live in [0xC6000,0xC6FFC)).

**How to apply:** read the first V289 route with b4.5 (duty ≈ 0.50 = alive; cross-spectrum with the 0x18F rate) and b4.7
(engaged-only — it reads 1.000 disengaged); revert on a new 14–17 Hz or 22–24 Hz line or a sustained ~16 Hz grind. If null,
the next candidate is the notch alone at Q4, not a re-cut. Never census "free" RAM without byte forms and bit ops.
See [[accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted]], [[accord-feedback-operand-is-a-two-sample-sum-dc-30-89]],
[[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]] (now superseded on the mechanism).
