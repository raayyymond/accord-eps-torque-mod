---
name: accord-v62-fixed-the-grinding
description: "★★★★ V62 flashed and driven 2026-07-31/08-01 (route 37) — the 20.9 Hz grinding is FIXED 8–42×, the kit's first measured fix. The reported \"new grinding\" is NOT an established regression."
metadata: 
  node_type: memory
  type: project
  originSessionId: 9d7a82e7-3e41-4e6c-8c21-5e0df8ff0133
  modified: 2026-08-04T14:57:57.430Z
---

**V62** (`sar 0xa`→`sar 0x9` at `0x3AC20` + `0x3AB76`, `FUN_0003aa2c`) flew on route
`00000037--6231e33f3d`, 86,278 frames. Operator: *"Original grinding at 2–5 mph is gone!"*

**Measured** — engaged creep, speed-standardised, **episode-clustered** bootstrap:
18–22 Hz V62/V59 = **0.124 [0.036, 0.387]** (8×), **0.024 [0.016, 0.234] at |rate| 16–32 deg/s (42×)**,
with a **30–40 Hz negative control at ~1.0** ⇒ band-specific. Transient rates **0.793/0.486/0.338** at
>200/>500/>1000 counts per 10 ms — monotonically cleaner; **lowest p90/p99/>1000-rate of any build**.
FLIGHT-CLEAN: `ST==4` 0/86,278 (zero-EME streak >229,278).

🛑 **The reported "new grinding at 10–20 mph" is NOT an established regression.** The 43 excursions
>2000 are **ONE 0.92 s burst ⇒ n = 1**. Burst rate: V62 **0.00142 [0.00004, 0.00793]** vs V59
**0 [0, 0.00986]** — **V62's CI is inside V59's**; V61 is **72×** V62. Exposure-matched (16.14 s vs
15.75 s, one event) ⇒ **p = 0.51**. Instant #2 is an ordinary burst **V59 produces ~3× more often**;
instant #1 is a 38–46 Hz singleton at **5.4 mph, not 10–20**.
⇒ **NO NEW BUILD. Fly V62 again and count bursts** — the question is the *rate of a rare event*, which
needs exposure, not firmware.

🛑🛑 ~~**r26 is STRUCTURALLY INERT** — `avg`'s cal base `0xC6564` byte-reads as **40 bytes of exact zero**
(bounded by non-zero data both sides), no writer for the RAM adjustment ⇒ `stage1 ≈ 0` regardless of
dtorque. **`0x3AB76` was a NO-OP; r24 carries the whole lane.** Re-attributes V42/V61/V62 and supersedes
*"killing either alone leaves the other transmitting."*~~
**SPLIT 2026-08-04 — one leg reversed, one downgraded. NOT a flat reversal.**
**LEG 1 (the GATE) is REVERSED [EVIDENCE]**: it kills r26 only at `|gp-0x6bda| ≥ 384`, and hands-off
`gp-0x6bda` ≈ 9262 = **24×** that ⇒ the gate does **not** kill r26 in ordinary driving.
**LEG 2 (the MAGNITUDE) is DOWNGRADED to BELIEF**: `0xC6564` **is** 40 zero bytes with no writer found
for the RAM adjustment, but **its link to `gp-0x69a4` was never verified**, and the real producer is a
**live runtime 10-segment LERP at `0x355C6` in `FUN_000352b4`**.
⇒ *"`0x3AB76` was a no-op / r24 carries the whole lane"* now rests on **LEG 2 alone**, and the
V42/V61/V62 re-attribution is **contingent on it** — the on-car *results* stand either way. ★ The
indirect argument that LEG 2 holds: at `a ≈ 1`, V67/V68's 6.00× gain_A cut would put them at ~0.94×
total, essentially stock, **yet they measured the best grind #1 result in the kit.** ✅ V70's
`gp-0x6adc`/`gp-0x6ada` sign pair settles it. Full chain:
[[accord-r26-is-structurally-inert]].

★ **AND V62's DOSE IS NEAR THE OPTIMUM, NOT ON A RAMP.** V69 flew 4× on 2026-08-04 and grind #1 came
back: median `e_18-22` engaged creep **2501 (0×) · 879 (1×) · 168 (2×) · 109 (2× gated) · 746 (4×)** ⇒
**non-monotone, minimum near 2×.** Do not read the 8–42× above as *"more would be better"* —
[[accord-v69-flew-dose-response-non-monotone]].

⚠ Trigger sits outside the firmware: instant #1 has openpilot's command **railed at ±4096** for 0.64 s
with the driver turning against it (engaged-creep rail duty V62 42.4% vs V59 25.3% — itself a confound).
🛑 No openpilot-side modifications is standing; recorded as observation only.

See [[accord-ratchet-is-a-saturated-resonance]], [[feedback-episodes-not-windows]].
