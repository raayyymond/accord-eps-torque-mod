---
name: feedback-3node-and-process-framing
description: "Joey's two durable mental models for the tuning work: (1) model+firmware+controller are ONE coupled 3-node system; (2) optimize the PROCESS of good driving, not proxy metric degrees (Goodhart)."
source: user
metadata:
  type: feedback
---

# Joey's framing: 3-node balance + process-not-degrees

Two reframes Joey offered 2026-05-30 that reshaped the whole tuning approach.

**(1) "It's both — the model, the car's firmware, and the controller are 3 nodes in a balanced system."** The supercombo (path), the EPS firmware (plant/authority), and the PID controller are coupled — don't pin emergent behavior on a single node. This resolved the left-hug investigation: every single-node attribution (alignment → "model aims left" → controller) flip-flopped *because* it isn't one node. When a measurement reverses across framings, suspect the single-cause framing, take the systems view.

**(2) "Train it on the process of becoming a better driver, not its degrees."** Optimizing proxy metrics (over-rotation degrees) Goodharts — finds tunes that score well and still drive like a robot (the trading-bot-on-proxy-P&L failure). The real target is good-driving-ness itself. This is the objective-design north star: anchor the auto-tuner's objective to *learned good driving* (e.g. a Gemini/critic reward, or matching good human trajectories), not a hand-picked metric basket.

**Why it matters:** these are the load-bearing design lenses for the auto-tune work, and the *why* under it is accessibility — openpilot reliably carrying the driving load (see [[radar-work-accessibility-motivation]]).

**How to apply:** systems view before single-cause; felt good-driving as the objective. Related: [[feedback-operator-lived-experience-overrides-analyst-recs]].
