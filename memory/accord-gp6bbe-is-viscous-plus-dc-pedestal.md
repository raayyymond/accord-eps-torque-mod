---
name: accord-gp6bbe-is-viscous-plus-dc-pedestal
description: "V92 telemetered the BOOST lane gp-0x6bbe for the first time. It is a VISCOUS (rate-proportional) term ~90 ct/(rad/s) riding a large ~74-count DC pedestal whose sign is 88.65% negative when engaged vs 49.9% manual. REFUTES the 'torque-reinforcing' structural flag."
metadata:
  type: reference
---

# ★★★★★ `gp-0x6bbe` IDENTIFIED — viscous + a big engagement-conditional DC pedestal

Route 79 (V92), 2026-08-11. **First measurement in the kit's history.** V92 is the first build ever
to write CAN `0x14A` byte 7, and it repointed 427 to this cell with a `sar 4` scale
(`clamp(|x|·5>>4, 0, 0x3FF)`, max observed wire 122/1023 ⇒ **never clips** — the scale fix worked).
Tools: `rlog-tools/v92_boost_lane_and_rez.py`, `v92_boost_lane_identify.py`.

## THE IDENTITY [EVIDENCE] — a flat real transfer against wheel rate

Discriminator stated before the numbers: *viscous ⇒ phase ~0°, gain flat · inertial ⇒ +90°, gain ∝ f
· stiffness ⇒ −90°, gain ∝ 1/f.*

| band | gain (ct per rad/s) | phase | coh² (shuf ≈ 0.000) |
|---|---|---|---|
| 2–4 | 100.0 | −29.0° | 0.185 |
| 4–6 | 90.1 | −12.6° | 0.261 |
| 6–9 | 92.0 | **+13.9°** | 0.315 |
| 9–12 | 93.4 | +19.6° | 0.419 |
| 12–16 | 78.7 | +26.6° | 0.320 |
| 18–22 | 58.8 | +58.1° | 0.266 |

⇒ **flat gain ≈ 90 ct/(rad/s) with phase crossing zero at ~5–6 Hz = VISCOUS / rate-derived.**

🛑 **THIS REFUTES THE STRUCTURAL FLAG THAT JUSTIFIED THE BIT.** `build_v92_tva.py` called
`gp-0x6bbe` *"the flagged best structural match for anti-damping (same-signed as the raw torque
sensor ⇒ REINFORCING)"*. Measured against column torque the phase is **+140° to +164°** at 4–12 Hz —
**opposite-signed, not same-signed** — and that value is **fully predicted by `boost ∝ rate` alone**
(`phase(boost/tq) = phase(boost/rate) − phase(Z)` = 14° − (−125°) = +139°, observed +145°).
**No independent torque-derived component is needed or evidenced.**

## ★ THE DC PEDESTAL — this is the part that matches the operator's own mechanism

`|gp-0x6bbe|` by wheel-rate bin, engaged (p50, counts): **73.6 / 73.6 / 73.6 / 92.8 / 160.0 / 214.4
/ 161.6** for 0–1 / 1–3 / 3–6 / 6–13 / 13–25 / 25–50 / >50 °/s.
⇒ **a ~74-count floor that does NOT scale with rate**, plus a rate-proportional part above ~6 °/s.
Engaged & moving: p50 **76.8**, p90 144.0, p99 268.8, max 390.4, **nonzero 99.40 %**.
Manual: p50 **0.0**, nonzero **27.32 %**.

**Sign bit (a DC claim, robust to the inter-message skew):**
`P(gp-0x6bbe < 0)` = **0.8865 engaged & moving · 0.4990 manual & moving · 0.0299 manual & parked.**

⇒ **Engaging drives this aggregator lane to a near-constant sign and a persistent ~74-count offset,
while manual leaves it a coin flip.** That is the operator's own stated mechanism in an instrument:
***"the ratchet is just on a DC LKAS command."*** [EVIDENCE for the statistics; **BELIEF** that this
pedestal causes the symptom.]

## 🛑 THE SKEW CAVEAT — and why the magnitude results are still clean

V92 splits the lane: **magnitude** on 427 @50 Hz, **sign** on `0x14A` b7 @100 Hz. Reconstructing a
SIGNED lane costs up to ~10–20 ms = **28–56° at 7.79 Hz**. Handled, not ignored: every signed
estimate was recomputed with the sign stream shifted **−2…+2** samples and the values move by
< 1.5 % (e.g. 6–9 Hz: 88.9 / 89.2 / 89.3 / 88.0 / 87.7). **Magnitude-only statistics come from one
message and carry NO skew** — they are the load-bearing ones. Distinct from
`[[accord-raw14-offbyone-in-every-cache]]`, which is a loader bug; this is real inter-message skew.
