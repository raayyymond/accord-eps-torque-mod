---
name: accord-lkas-lane-passes-8hz-nearly-unattenuated
description: "Measured 6-9 Hz attenuation from openpilot's 0xE4 command to the delivered motor command gp-0x6b98 is 0.71-1.06x - essentially NONE. Scopes reference-accord-lkas-lane-is-a-lowpass: 'a fast vibration cannot be COMMANDED via LKAS' is too strong at 8 Hz, though it stands at tens of Hz."
metadata:
  type: reference
---

# ★★★★ THE LKAS LANE IS ESSENTIALLY TRANSPARENT AT 8 Hz

Route 73 (V88), engaged, **HANDS-OFF**, signed lane, 224 s / 21 blocks / 55 windows, 5.12 s Hann
windows, 20 s blocks as the bootstrap unit. 2026-08-21.
Only route 73 can measure this — see [[accord-427-source-cell-changes-by-build]].

| band | gamma^2 [block-boot 95 %] | shuffled null p50 / p95 | H1 (ct 6b98 per ct 0xE4) |
|---|---|---|---|
| 0.5–3 Hz | **0.5304** [0.385, 0.680] | 0.0043 / 0.0234 | **1.027** [0.798, 1.285] |
| 4.5–6 Hz | 0.0625 | — / 0.0312 | 0.664 [0.307, 0.913] |
| **6–9 Hz** | **0.0225** [0.0084, 0.0485] | 0.0016 / **0.0060** | **0.72–1.07** (skew sweep) |
| 20–24 Hz (control) | **0.0007** [0.0001, 0.0143] | 0.0009 / 0.0039 | — |

🛑 **The 20–24 Hz control band sits AT the shuffled null ⇒ the instrument is clean.** 6–9 Hz sits at
3.8× the shuffled p95 — real but weak. Selecting the top-25 % of windows by 6–9 Hz excitation raises
gamma^2 to **0.0643** with the control band still dead (0.0021).

⇒ **BAND RATIO 6-9 / 0.5-3 = 0.71–1.06.** Median across four estimators (NPS 256/512/1024 and the
top-excitation selection): **0.98 at 0.5–3 Hz vs 0.75 at 6–9 Hz.**

## Corroborated from the firmware, independently of the telemetry
The arbitration IIR is `s[n] = 507/1024*x[n] + 992/1024*s[n-1]`, `out = (s[n-1]+s[n])/32`,
tau = 31.5 cycles. **At the confirmed 1 kHz control-task rate the corner is 5.05 Hz and the model gain
at 8 Hz is 0.534** — inside the measured bracket.

## 🛑 WHAT THIS SCOPES
`[[reference-accord-lkas-lane-is-a-lowpass]]`'s blanket claim that a fast vibration cannot be
COMMANDED via LKAS is **TOO STRONG AT 8 Hz**. It is a decade of attenuation only if the arbitration
runs near 100 Hz, which the data do not support. At 1 kHz the lane passes 8 Hz at −5.4 dB.
⚠ **This SCOPES the memory to roughly ≥10 Hz; it does not overturn it.** At tens of Hz it stands.

## Confidence
[EVIDENCE] for the direction and order of magnitude — corroborated two independent ways (telemetry
and the firmware IIR), with a clean control band and a shuffled null.
⚠ [BELIEF] for the exact figure: at gamma^2 ≈ 0.02 the H1 estimate is only ~1.5× its own shuffled-H1
null and the two could not be separated cleanly.

⊕ **UNRECONCILED:** engaged `abs(gp-0x6b98)` p50 measures **664 ct** here against the kit record's
**208 ct** — a 3.2× gap. Someone should chase which mask produced the 208. It does not affect this
result, which used measured band rms rather than p50.

Related: [[accord-honda-steer-slew-is-12288-not-300]] · [[accord-e4-to-bar-is-reverse-causality]] ·
[[accord-v87-flew-the-probe-fired-and-6b98-is-broadband]]
