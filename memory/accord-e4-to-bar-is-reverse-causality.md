---
name: accord-e4-to-bar-is-reverse-causality
description: "gamma^2(0xE4, torsion bar) at 6-9 Hz reaches 0.28 and looks like a clean actuation transfer. It is REVERSE CAUSALITY - openpilot's controller reads steering angle at 100 Hz and feeds it back out. Retracted before use; recorded so nobody rediscovers it as a result."
metadata:
  type: reference
---

# 🛑★★★★ A RESULT THAT LOOKED EXCELLENT AND WAS KILLED BY ITS OWN AUTHOR

2026-08-21. `gamma^2(e4tq, torsion bar)` at 6–9 Hz, engaged hands-off:
**0.085 / 0.138 / 0.280** on routes 73/75/76 — **67–538× the shuffled null**, with the 20–24 Hz control
band clean. It reads as a clean actuation transfer. **It is not.**

## The kills
1. **`gamma^2(e4tq, STEERING ANGLE)` at 6–9 Hz = 0.399 / 0.526 / 0.709 — HIGHER than e4~bar.**
   openpilot's torque controller reads the measured angle at 100 Hz and its P/D term feeds straight
   back out. `ang` is a **current-frame `0x14A` field with no staleness**, so this kill is clean.
2. **The bar channel's band ratio 6-9 / 0.5-3 is 5.9–11.3× with NEAR-ZERO PHASE**
   (−1.8 / −6.6 / −9.2 deg). A gain rising 6–11× across two octaves with no phase lag is **not a
   physical actuation transfer** — it is a same-frame algebraic relationship, i.e. feedback.
3. The bar ratio **tracks `gamma^2(e4, ang)` across routes**: r76 has both the highest e4~ang (0.709)
   and the highest bar coherence (0.280); r73 has the lowest of each.

⚠ A fourth kill originally offered — *"the bandpassed cross-correlation peaks at lag +0 ms exactly"* —
was **WITHDRAWN by its author**: `tq` IS `0x18F` byte0-1 **held-last** onto the `0x14A` grid
(`rlog-tools/extract_r67_v81.py:85-108`), and `e4tq` is held-last too, so lag-0 bounds the true lag to
roughly ±10 ms rather than proving it is zero. **Kills 1–3 stand on their own.**

## 🛑 THE STANDING CONSEQUENCE
**openpilot's command is NOT EXOGENOUS at 6–9 Hz. This is a closed loop.** Partial coherence on `ang`
does not rescue it — with 55 windows the partial estimator is upward-biased (it returns H = 1.04 in the
20–24 Hz control band where the raw estimate is 0.26).

⇒ **Never pre-register column torque as a co-primary endpoint against an 0xE4-derived quantity.** It
has a feedback path that an injected tone will not break, and a null or a win there is uninterpretable.
Use it as a descriptive secondary only.
⇒ Corollary: **a deliberately injected tone at a chosen frequency is the only exogenous input
available** — which is an argument FOR injection, not against it.

⚠ **Do not cite the kit precedent where 427 and column torque agreed** (2.30× vs 1.97×) as licence to
treat the channels as interchangeable here. That compared **incoherent band power**; this asks for a
**directed transfer**, and only the column channel carries the feedback path.

Related: [[accord-lkas-lane-passes-8hz-nearly-unattenuated]] ·
[[feedback-run-the-control-before-the-measurement]] · [[accord-a-caveat-can-mutate-into-a-result]]
