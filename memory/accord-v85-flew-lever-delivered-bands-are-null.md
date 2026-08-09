---
name: accord-v85-flew-lever-delivered-bands-are-null
description: "V85 flew route 6e fault-free; 0xC40BC cut relay saturation 7.21x and is now SPENT (freeze at 6000), but every band is a clean null and the operator says ratcheting is still unfixed."
metadata:
  node_type: memory
  type: project
---

★★★★ **V85 FLEW AS ROUTE `6e` ON 2026-08-09** (`75604b0a432fdc89_0000006e--649c462a6e`, cache
`_cache_r6e/`). **43,641 frames · 438.2 s · 82.02% engaged.**
**FAULT-FREE, and the cleanest flight in the modern lineage: `STEER_STATUS` = {0: 43,641} — not one
non-zero frame**, 0 DTC-active, 0 sentinels. [EVIDENCE]
**Identity with no free parameter:** `b3` fingerprint 1.00000; `b7` duty **0.39481** where V84 read
**0/68,236**; nesting `b6⇒b7` and `b5⇒b4` both 0 violations.

## 🛑 THE OPERATOR'S VERDICT, IN HIS WORDS — it overrides every number below
- **grinding**: *"still barely perceptible"*, *"got a little bit better"* — still present
- **micro-ratcheting**: *"barely, perceptibly better (somewhat unsure)"* — still present
- **ratcheting**: 🛑 **"was still unfixed"**
- grind #2: *"I did not experience any"* — 🛑 **an absence of complaint is not a cure**

## THE LEVER DELIVERED, AND IS NOW SPENT
Relay saturation **39.5% → 11.1% overall, 33.3% → 4.6% engaged (7.21×)**; **both pre-registered duty
predictions hit.** [EVIDENCE]

🛑 **FREEZE `0xC40BC` AT 6000 — and the pre-registration's own reason was the WRONG ROUTE to it.**
It read *"N is already flat at 6000"*. The **single-input** describing function cannot settle this,
because **the ring rides on a bias 5–10× its own amplitude** (`|B|` p50 **35** / p90 **228** counts vs
ring amplitudes `A` p50 **4–7**). The correct instrument is the **BIASED** DF: top-decile pinning at
cal 6000 is **0.0000 (18–22 Hz)** and **0.043 (6–9 Hz)** after a delivered **20.3×** reduction.
⇒ **Do not raise it further and do not revert it — the lever is spent, not wrong.**

🛑 **REFRAME: the pathology was PARAMETRICALLY SWITCHED DAMPING, not "harmonic injection."** At cal 600
the damping switched **fully off** on **87% (6–9 Hz)** and **96% (18–22 Hz)** of symptom frames.
⊕ `gp-0x6abc` scale confirmed two independent ways: **4.923** and **4.697** ct/(°/s) bracket the
inherited **4.7121**; reachable envelope **±1,930 counts**.

## 🛑 EVERY BAND IS A CLEAN NULL vs V84
6–9 Hz **1.088 [0.746, 1.451]** · 18–22 Hz **1.347 [0.947, 1.758]** · 40–49 Hz 1.002 ·
**negative control 32–38 Hz 1.007** · 1–4 Hz validity 1.005 · IMU roughness **0.958** (V85's road
*smoother*, i.e. moving **for** V85). **Split-half nulls are [0.63, 1.50] wide — a ratio must clear
~1.5 to mean anything.**
🛑 **The instrument neither corroborates nor refutes the operator's two "a little better" reports.**
Score bands; let the operator score symptoms.
⚠ **Self-correction:** the 6–9 Hz *"V85 worse than V81"* = 1.625 was a **wheel-order artefact** —
order-cleaned it falls to **1.273 [0.853, 2.507]**. The 18–22 Hz result survives (1.957 → **1.928**).

## 🛑 EXPOSURE LIMIT — bounds what may EVER be scored on this route
Engaged **≥50 km/h: 35.6 s · ≥80 km/h: 22.4 s** (V84 had 370.8 / 158.1) ⇒ **V83a-class** ⇒
**no highway and no 26–31 Hz verdict may be scored on route `6e`, in either direction.** Its damper
abort criterion "passed" only because it **could not have fired**. Creep exposure is the **best in the
ladder** (68 windows / 15 blocks) and is what this route can carry.

## Three extraction traps
1. 🛑 **`_cache_r6e/r6e.npz` carries `probe_build = ['V80']` — a STALE EXTRACTOR HEURISTIC. WRONG.
   Never quote it.** Found independently by two agents.
2. ⊕ **"CAN 330 / 399 / 427" are DECIMAL** = hex **`0x14A` / `0x18F` / `0x1AB`**.
3. ⊕ **Route `6e` segment `--7--` is truncated mid-capnp-message**; stock `read_messages` raises and
   loses the whole route. A wrapper recovered **32,695** complete messages.

Related: [[accord-ratchet-is-a-linear-loop-oscillation]],
[[accord-plant-model-residual-aggregator-chain]], [[accord-v86-built-the-frequency-lever]],
[[accord-fun3b8f6-coulomb-relay-proportional-to-command]],
[[feedback-a-falsifier-only-fires-if-it-could-have-fired]].
