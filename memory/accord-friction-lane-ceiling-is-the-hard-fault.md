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
  n=1 each. The lane's multiplier is `gp-0x6c2c`, a **filtered motor rate** — a rate-family signal.
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

⚠ **OPEN:** `gp-0x6c2c`'s physical scale (deg/s per raw count) is not derived, so it is unknown whether
~4180 is an ordinary or an extreme motor-rate value. Closing it needs `FUN_00041464`'s
`gp-0x35a0 → gp-0x6c2c` EMA chain (α = 22/64 on `gp-0x4f50<<5`, final `>>9`) anchored against a
known-scale sibling — **or the V76 probe's `|gp-0x6b26| ≥ 448` margin bit, which answers it by
telemetry.** ⇒ the mechanism and the interlock breach are **[EVIDENCE]**; *"this caused both faults"*
is a strong **[BELIEF]** resting on the build history lining up exactly.

Related: [[accord-v74-fault-damper-WAS-in-force-mode-lag]] · [[accord-both-faults-fired-at-max-angle-rate-slew]] ·
[[accord-v77-cannot-reach-the-monitors]] · [[accord-check-build-lineage-before-proposing-lever]]
