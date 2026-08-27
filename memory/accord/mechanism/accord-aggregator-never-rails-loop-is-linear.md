---
name: accord-aggregator-never-rails-loop-is-linear
description: ★★★ V65's saturation ladder answered its question - gp-0x6b94 NEVER reaches ±8192 in 120,049 frames and passes ±4096 in only 54. The aggregator is NOT clipped, so the loop is LINEAR there. That makes a lane-gain change propagate faithfully; it does NOT close lane gains as levers, and reading it that way contradicts the r24 dose-response.
metadata:
  type: reference
---

# ★★★ THE AGGREGATOR NEVER RAILS — the loop is linear at `gp-0x6b94`

V65's 4-level symmetric ladder on the aggregator output, routes `3a` + `3b`, **120,049 frames**.
Orchestrator-verified independently from the caches (`field` is `byte4 >> 3`, so the legal payloads
appear as 16 / 18 / 20 = NEUTRAL / −HALF / +HALF).

| | 3a | 3b |
|---|---|---|
| frames | 36,991 | 83,058 |
| liveness fail (`field == 0`) | **0** | **0** |
| NEUTRAL | 36,951 (99.892%) | 83,044 (99.983%) |
| −HALF (≤ −4097) | 34 | 14 |
| +HALF (≥ +4096) | 6 | 0 |
| **+RAIL (≥ +8192)** | **0** | **0** |
| **−RAIL (≤ −8193)** | **0** | **0** |
| invariant violations (`bit6⇒bit5`, `bit3⇒bit4`, never-both-sides) | **0** | **0** |

**`gp-0x6b94` never comes within 20% of its own ±10240 clip.** `bit6↔bit3` alternation is **0.0000
flips/s in every arm** — engaged-creep, manual-creep, corner-engaged, corner-manual — and not as a small
number: **no rail frame exists**, so no flip sequence exists and no flip frequency is computable.

## ✅ What this establishes

**The loop is operating in its LINEAR regime at the aggregator.** No describing-function or
saturation reasoning is needed anywhere in this chain, and a **linear gain change on any lane
propagates faithfully** to `gp-0x6b94`.

⇒ That is *support* for the r24 mechanism, not a problem for it: V62's flat ×2 produced the measured
band table (18–22 Hz **0.35**, 40–49 Hz **11.71**) precisely because nothing between the lane and the
sum was clipping it.

★ **All 54 non-neutral frames sit inside grind #2 bursts**, at **36.3–106.1×** the segment-median
30–49 Hz envelope — 54 of 54. The aggregator's only excursions past ±4096 anywhere on either route
happen during grind #2. Independent corroboration that grind #2 is a genuine large-signal event **in
the command path**, not only a sensor-side resonance.

## 🛑 What it does NOT establish — an over-reach to avoid

V65's pre-committed reading said *"all four quiet ⇒ the nonlinearity is downstream; next target is
`gp-0x6b98` and the FOC loop — **NOT another lane gain**."* **Do not apply that clause to grind #2.**
It was written to test whether the **RATCHET** is a rail-to-rail limit cycle in the sum. Grind #2's
attribution rests on an **on-car dose-response on exactly a lane gain** (Kd = 0 / 1× / 2× → 40–49 Hz
11.71×, p = 0.0003, replicated on three routes and on the comma IMU). **An intervention outranks an
inference drawn from a different hypothesis.**

What the null *does* close:
- The **ratchet** cannot be an amplitude-saturated resonance *at the aggregator*. If it saturates
  anywhere, it is further downstream. See [[accord-ratchet-is-a-saturated-resonance]], whose
  "amplitude-saturated" framing now needs a location.
- The `0xD2AEC` **gain_B breakpoint** lever loses its *clipping* rationale (it was attractive partly as
  a way to act before a clip). It remains available on its own merits, and it was already ranked behind
  gating for a different reason — steering rate separates the symptoms only ~2×.

## ⚠ The one caveat, and it is real

The probe is **100 Hz sampling a ~43 Hz burst** — stroboscopic. It **cannot** claim the sum touched
±4096 only 54 times; the true crossing count is higher and the peak is under-estimated. The **±8192
null is unconditional over the whole route**, but over the *bursts specifically* the sample count is
small, so "never rails during a burst" is the weaker of the two claims. **Quote the route-wide null;
do not quote the 54 as a rate.**

⚠ `probe/decode_v65_saturation.py` still prints its constant-`0x87` STOP text because its guard is a
>99%-fraction test rather than a distinct-value test. byte4 is **not** literally constant here (three
distinct legal payloads), so this is not V64's frozen null — but **confirming the flashed `.rwd`
filename is cheap and should be done before this carries a build decision.**

## Flight-clean — V65 ADDS TO THE ZERO-EME STREAK
`ST == 4` is **0** on both routes (36,991 + 83,058 frames), confirmed a second way by a raw-CAN
recount off the `0x18F` src-1 frames rather than the gridded cache. `STEER_STATUS` is only ever 0 or 3,
and every `ST == 3` sits in a park/reverse segment. Zero `steerUnavailable` / `steerTempUnavailable` /
`canError` / `immediateDisable`; one `controlsMismatch` per route; three `steerSaturated` on 3b seg 5.
`latActive` 88.2% / 75.4%. CAN 99.94–100.04 Hz. Reverse: 1,248 / 2,694 frames.

## 🛑🛑 A COLLISION WITH `accord-c6200-clamps-the-pid-reference` — SAME ±8192, DIFFERENT CELL, NO CONTRADICTION

Added 2026-08-13 (later still), record-repair pass, because a careless read of both memories together
draws the wrong inference. `[[accord-c6200-clamps-the-pid-reference]]` reports that `gp-0x6ad6` (the
**PID's reference**, upstream of the PID) can saturate at the same magnitude, ±8192, that this memory
proves `gp-0x6b94` (the **aggregator output**, downstream of the PID) never reaches. **Read fast,
V65's null looks like it has already answered whether that OTHER clamp binds — it has not.**

**The reconciliation is arithmetic, not assertion:**
- `gp-0x6b94` and `gp-0x6ad6` are different cells at different points in the chain — one is upstream
  of the PID, the other is its output, summed with nine other terms.
- A **fully railed** `gp-0x6ad6` contributes only `8192 × 0.2565 ≈ 2,101` counts at `gp-0x6b94` —
  comfortably inside THIS memory's own NEUTRAL band (`|·| < 4096`). ⇒ **V65's null is silent about
  whether the PID-reference clamp binds; the two nulls are COMPATIBLE, not redundant, and this memory
  does NOT close that question.**
- [BELIEF, stated in the safe direction only — the step uses `0.2565`, the *unsaturated* small-signal
  derivative, so it is a linearisation. It is enough to show this memory does not preclude a high duty
  on the other clamp; it is not enough to predict one.]

⇒ **Do not cite this memory as having closed the `gp-0x6ad6` question.** That clamp's duty remains
unmeasured and is V100's content — see the linked memory for the instrument.

See also [[accord-grind2-is-a-45hz-mode-under-driver-load]],
[[accord-gp683c-dead-gate-is-a-free-lkas-arm]], [[accord-r24-gain-b-four-pointer-arrays]],
[[accord-c6200-clamps-the-pid-reference]].
