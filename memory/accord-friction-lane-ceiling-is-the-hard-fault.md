---
name: accord-friction-lane-ceiling-is-the-hard-fault
description: The two mid-drive hard faults are the friction lane gp-0x6b26 crossing a flat 512-count monitor ceiling — V73 raised its clamp from 511 (one count under, an interlock) to 850.
metadata:
  type: reference
---

★★★★★ **THE HARD-FAULT MECHANISM, FOUND AND ORCHESTRATOR-VERIFIED 2026-08-07.** Two mid-drive total
losses of power steering (V74 and V75) are explained by a **flat magnitude ceiling on the FRICTION
lane** — not the damper, not a race, not a timing skew.

## The monitor [EVIDENCE, decompiled by the orchestrator directly]
`FUN_00036d74`, called **UNCONDITIONALLY** from `FUN_0002214a` @`0x2290a` — the kit's established
**1 kHz** control task (`get_xrefs_to` returns exactly that one `UNCONDITIONAL_CALL`):

```c
fVar3 = (float)(int)*(short *)(gp - 0x6b26) * 0.0009765625;   // /1024, Q10
fVar2 = *(float *)(tp + 0x5004) * -1.0;
if ((*(float *)(tp + 0x5004) < fVar3) || (fVar3 < fVar2))
    FUN_000462e6(0x39bc, fVar3, 0, CEIL, -CEIL);              // -> FUN_00016de6(0x1d) -> HARD FAULT
```
It then writes mirrors `gp-0x6b20` (the value ×1024), `gp-0x6b1e` (+CEIL×1024), `gp-0x6b24` (−CEIL×1024),
all **unconditionally, after the `if`** — usable telemetry.

**`tp+0x5004` = `0xC4004` = float `0.5` = 512 raw counts** — raw bytes `0000003f`, **byte-identical in
stock / V38 / V72 / V73 / V74 / V75**. ⚠ Watch the tp trap: `0xBF000 + 0x5004 = 0xC4004`.

🛑 **This is a flat, symmetric, unconditional magnitude check. There is NO re-sampled comparator, no
race, no timing escape.** If `|gp-0x6b26|` ever exceeds 512, it faults, period. That is what makes it
different from the damper's Surface A, which needs a ceiling *shrink* between two samplings and is
effectively unreachable.

## The breach — a one-count interlock, removed at V73 [EVIDENCE, orchestrator byte reads, all images]
`gp-0x6b26` is clamped to ±`0xC407E`:

| build | `0xC4004` ceiling | `0xC407E` clamp | relationship | on-car |
|---|---|---|---|---|
| stock / V38 / V72 | 512 | **511** | **1 count UNDER — structurally untrippable** | clean, always |
| **V73** | 512 | **850** | **338 counts OVER** | clean (needs a big event) |
| **V74 / V75** | 512 | 850 | 338 over, **friction table ×1.5** | **BOTH HARD-FAULTED** |

🛑 **CORRECTION 2026-08-07: the ×1.5 friction table was introduced by V73, NOT V74.** Verified across the
lineage — stock/V70/V71c/V72 carry Honda's row; **V73, V74 and V75 all carry ×1.5**, and V73 raised
`0xC407E` in the same build. The table above understates V73's exposure by one build; V73 carried *both*
legs and simply never met a big enough event.

★★ **Honda set the clamp to exactly one count below the monitor's own trip threshold.** That is an
interlock: a clamped signal cannot trip its own fault check. **V73 raised it to 850 and removed the
interlock without knowing it was one.** V74 then multiplied the mode-26 friction table by 1.5
(`0xD7A54` `Y = [−9830,−5734,−1966] → [−14745,−8601,−2949]`), dropping the motor-rate magnitude needed
to cross 512 from `gp-0x6c2c` ≈ **6258** to ≈ **4180**. Both V74 and V75 faulted.

## Why this fits when nothing else did
- **Mode-proof.** `0xC407E` is a bare cal with no mode index ⇒ live in MANUAL. **This is the only
  candidate that explains V74 faulting with LKAS disengaged.** (Note the fault was actually 2.509 s
  post-disengage, still on mode 26 — see [[accord-v74-fault-damper-WAS-in-force-mode-lag]] — but the
  clamp breach is live in either mode.)
- **Single-frame latch.** Flat check, threshold-0 dwell on fid 28/29 ⇒ trips on the first qualifying
  call. Matches the observed one-transmission latch.
- **Explains the build history exactly.** V38–V72 could not fault (clamp < ceiling). V73 could but
  needed a large event. V74/V75 needed a third less. Faults are new at V74.
- **Explains why every damper theory came up empty** — wrong lane entirely.
- **Torque magnitude never unified the two faults** (V75 was 86th percentile); `|d(angle rate)/dt|` did,
  n=1 each. The lane's multiplier is `gp-0x6c2c` — 🛑 **CORRECTED 2026-08-08: filtered motor
  ACCELERATION, not a "filtered motor rate."** `FUN_00041464` runs two cascaded IIRs on the **one-cycle
  delta** of the filtered rate, so the lane is **DC-blind: `gp-0x6b26` ≈ 0 under steady motion at any
  speed or torque, and responds only to oscillation.** That is why `|d(angle rate)/dt|` unified the
  faults and magnitude did not — the lane is *literally* a jerk detector.
  ⇒ **"Remove the friction lane to fix steady-state heaviness" is NOT supported by this structure.**
  See [[accord-gp6c2c-is-the-detector-input]].
  ⚠ Its index is `gp-0x6a5e` (**vehicle speed**), and **bar torque appears nowhere in the arithmetic**;
  an earlier "route-max bar torque maximises it" framing was wrong at the code level.
  ⚠ There is **no bare `sign()` flip**: the output's sign tracks `gp-0x6c2c`'s own EMA-filtered value
  × an always-negative speed coefficient. **A monotonic rise in `|gp-0x6c2c|` trips it just as well as
  a reversal** — it is a magnitude-ceiling crossing, not a step-at-reversal.

## The fix
**`0xC407E` → 511.** One cell. Mode-proof, restores the one-count margin, closes the manual-mode
exposure, and **loosens no monitor**. ⇒ **A V38 base gets this for free** — V38 predates V73.
🛑 **`0xC407E` is now a DO-NOT-RAISE cell.** V73's edit is the single most consequential unreviewed
change in this kit's history. Raising `0xC4004` instead would loosen the monitor itself and must not be
done casually.

✅ **CLOSED 2026-08-08 — `gp-0x6c2c`'s scale is ≈ 0.3016 counts per °/s²** (it is an **acceleration**,
so the units are °/s² per count, not °/s). Cross-validated: solving this chain for the V74/V75 trip
demands **7,076 °/s²** against an **independently measured 7,154 °/s² peak jerk** on that drive — 1.1%.
⇒ ~4180 is an **extreme** value, and the mechanism's sizing now stands on two independent numbers.

⚠ **(superseded) OPEN:** `gp-0x6c2c`'s physical scale (deg/s per raw count) is not derived, so it is unknown whether
~4180 is an ordinary or an extreme motor-rate value. Closing it needs `FUN_00041464`'s
`gp-0x35a0 → gp-0x6c2c` EMA chain (α = 22/64 on `gp-0x4f50<<5`, final `>>9`) anchored against a
known-scale sibling — **or the V76 probe's `|gp-0x6b26| ≥ 448` margin bit, which answers it by
telemetry.** ⇒ the mechanism and the interlock breach are **[EVIDENCE]**; *"this caused both faults"*
is a strong **[BELIEF]** resting on the build history lining up exactly.

---

## ✅ 2026-08-07 — CONFIRMED IN GHIDRA BY THE ORCHESTRATOR, and the blast radius is now CLOSED

- **Sole writer of `gp-0x6b26`**: `st.h r6,-0x6b26[gp]` @`0x36CF0` in `FUN_00036c12` — **exactly ONE
  writer image-wide**, confirmed by Ghidra **plus** a raw Python LE scan covering disp16, the 6-byte
  disp23 form, LE32 address literals and `movhi`/`movea` pairs (**0 hits on all three alternatives**).
  The stored value is **already clamped** to ±`0xC407E` (clamp arms `0x36CCC`–`0x36CE2`).
- **`0xC407E` itself**: **0 writers, 3 readers, all `ld.h` SIGNED, all three inside `FUN_00036c12`** ⇒
  the cell's entire blast radius is one lane's clamp magnitude.
- **The monitor's gate is unconditional *relative to the producer*.** `FUN_00036d74`'s caller gate
  `gp-0x67fa ∈ {4,5,11}` is the **same** gate that wraps the producer's call ⇒ **no path writes
  `gp-0x6b26` without the monitor checking it that cycle.**
- **Margins**: stock/V38/**V76/V78/V79/V80** and **V81** = **511 ⇒ +1, UNTRIPPABLE BY CONSTRUCTION**
  (the only value that can reach the cell is already clamped below the trip, whatever the plant, mode or
  lever set does); **V73/V74/V75 = 850 ⇒ −338, TRIPPABLE.** [EVIDENCE]
- **★ V75's fault was NOT the damper.** In the last 5 s before the trip the damper was identically
  **zero for 4.98 s** and reached only level 2 (128–288) **19 ms** before the fault. The car was
  stationary T−5 → T−1 s then launched (0 → 7.6 km/h); column rate reversed sign twice in the final
  150 ms (+55, +31, −38 °/s) and **peak jerk hit 7,154 °/s² = 4.3× that route's own p99.9 (1,664) and
  the route maximum** — exactly what this mechanism predicts. [EVIDENCE]
- 🛑 **`0xC63A0` is EXONERATED** — there is **no firmware data path** from it to `gp-0x6b26`. The
  standing directive *"do not double `0xC63A0`, that caused the hard faults"* rests on a false premise.
  See [[accord-c63a0-exonerated-of-the-hard-faults]].
- ✅ **V81 closes both legs** (`0xC407E` → 511 **and** the friction table → stock):
  [[accord-v81-built-c407e511-friction-stock]].

⚠ Unchanged: *"`0xC407E`=850 caused BOTH faults"* is still **[BELIEF]** — **the DTC number was never
confirmed on-car.** What is **[EVIDENCE]** is that the mechanism exists, is single-frame, is mode-proof,
and the build history lines up exactly. V81 closes it whether or not it fired.

Related: [[accord-v74-fault-damper-WAS-in-force-mode-lag]] · [[accord-both-faults-fired-at-max-angle-rate-slew]] ·
[[accord-v77-cannot-reach-the-monitors]] · [[accord-check-build-lineage-before-proposing-lever]] ·
[[accord-c63a0-exonerated-of-the-hard-faults]] · [[accord-v81-built-c407e511-friction-stock]]
