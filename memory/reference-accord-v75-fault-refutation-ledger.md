---
name: reference-accord-v75-fault-refutation-ledger
description: Six candidate mechanisms for V75's latched loss of power steering, each refuted with arithmetic — do not re-propose without new evidence.
metadata:
  type: reference
---

🛑 **V75 FLASHED → LATCHED TOTAL LOSS OF POWER STEERING** (EPS lamp + openpilot LKAS fault + manual-effort
wheel) after a stoplight stop → pull-away with openpilot engaged. **V74 flew 1,011 s clean.** No rlogs.

**The entire functional delta V74→V75** (byte-diffed from the images, RULE 4): `FactorC Y[0]` 429→**566**
(11 modes), `FactorE X[1]` 400→**200** (13 modes), probe cave rewritten 45→68 B, 10 CRC words.
**Nothing else.** Friction, `0xC407E`, `sar`, r24/r26, the ceiling table, `0x454FE`, and every mode-24
(manual) record are byte-identical to V74.

★ **Anchor fact: of 17 monitor-related constants byte-read across stock/V74/V75, only TWO were ever moved
by any build** — `0xC63A0` (1024→2048) and `0xC407E` (511→850), both at V72/V73, both identical between
V74 and V75. **No build has ever moved a fault threshold.** ⇒ the fault comes from the **signal**, not a
widened limit.

## The six refuted mechanisms — each died on arithmetic

| # | mechanism | why it is dead |
|---|---|---|
| 1 | **Arithmetic fault in the surface** (non-monotone X, /0, overflow, sign discontinuity) | 0 non-monotone X in 510 records; no `divq`; 2263× s32 headroom; mode 24 byte-stock and identically zero |
| 2 | **`FUN_000347b8`** — the damper's own ceiling consistency check (±5/1024, N=1, → DTC 0x1d) | Needs `gp-0x6bd0` > ~517. **FactorE has NO headroom past its own `X[3]`** (`Y[3]=927` hard cap) and FactorC is constant at `Y[0]` below 2240 ⇒ creep supremum is exactly `(566×927)>>10 = 512`, and the ceiling's floor is a hard 512. **Margin 215 counts, 43× the tolerance.** Unreachable *independent of any `gp-0x6ac2` timing race.* Both LERPs flat-clamp — no extrapolation, no int/float twin bug |
| 3 | **Int-vs-float lockstep** (the V24–V27 brick class) | **No float mirror of FactorC or FactorE exists anywhere in the ROM** — exhaustive unaligned float search at 7 scale factors, positive control found the known ceiling mirror at `0xC6554`. The one real int/float pair (ceiling) had **neither side touched** by V74 or V75 |
| 4 | **Governor slew-step / per-cycle step trip** | Max one-cycle `\|Δgp-0x6bd0\|` = 225 (V74) / 297 (V75); `STEP_FAST`=512. `FUN_0004595a` **explicitly tolerates output LAGGING target**, faulting only on output *exceeding* it or flipping sign. ⚠ Route-wide, V75 *does* exceed 512 on 35 frames and V74 on zero — but all 35 are one 113 km/h burst, and the refutation stands on the tolerance argument, not on "both under 512" |
| 5 | **`FUN_00045a20`** (governor tracking error, N=1 single-cycle latch) | Its `comp = (gp-0x6acc − gp-0x6ace)/1024` is algebraically `FUN_000456a4`'s common-mode-rate damping term, and **both operands already include the aggregator sum identically ⇒ `gp-0x6bd0` CANCELS in the subtraction.** Also gated on `gp-0x6ac0 > 1000–5000`, far above both relay entry rates ⇒ `comp = 0` there |
| 6 | **Duty- or dwell-triggered corridor trip** | **V74 clears the 1/3 break-even duty 1,411 times engaged (2.57/s) and never faulted.** Its median plateau run is **210 consecutive 1 kHz cycles — 21× the 10-cycle trip requirement — on all 35 engaged entries**, max 151×. If dwell were the faulted condition V74 would have tripped 35 times on route 5d alone |

## What survives

**Only a TRANSITION-triggered trip on Monitor 2** — see [[reference-accord-monitor2-corridor-and-the-c64a4-trap]].
The deduction: since a dwell rule would have latched V74 repeatedly and did not, the fault condition
**cannot be co-extensive with sitting on the plateau**; it must fire on the *edge*. That is the one regime
where the builds diverge **8.1×** rather than the **1.32×** magnitude that killed mechanisms 1–5.
**Not numerically closed** — needs the aggregate command's headroom-to-clamp at a transition.

⚠ **THE VALIDATION GAP — RESTATED 2026-08-06; the original wording overclaimed.** ~~Route 5d contains
ZERO engaged stoplight stops ⇒ it structurally could not contain the faulting regime.~~ **True only for
*engaged while STOPPED*** (0.0 s — 12 full stops, 343.5 s stopped, `latActive` = 0.000 in every one).
**Route 5d DOES contain 5–6 engaged stoplight LAUNCHES** (two independent counts). ⇒ **V74 FLEW the
faulting regime and did NOT fault** — which **strengthens** the V74/V75 contrast rather than voiding it.

What survives, in its honest form: **RULE 8's observed-envelope check is only ever as good as the
envelope**, and a route's flight-instruction shortfall is a hole in the SAFETY argument, not just in the
measurement. But the specific "could not contain the regime" escape hatch is **closed** — the regime was
there.

🛑🛑 **AND THE LEDGER'S ANCHOR HAS SINCE COLLAPSED.** *"V74 flew 1,011 s clean"* is **no longer a safety
anchor** — **V74 hard-faulted in MANUAL, over a bump, on 2026-08-06**, with its FactorC/FactorE edits
**not in force** (mode 24 is byte-stock). See
[[accord-v74-hard-faulted-in-manual-over-a-bump]]. ⇒ every dwell/duty refutation below that reads *"V74
did X and never faulted"* is weakened accordingly, and **`k* ∈ (0.580, 1.580]` is VOID**.
⊕ Mechanism 6's magnitude framing is separately dead: **the faulting launch was the MILDEST of four**
([[accord-v75-fault-pinned-to-the-frame]]).

⚠ **GATE 2 was never run for this edit**, and the kit's own memory flagged it
(`reference-accord-factore-x1-is-the-free-dose-lever.md`: *"The tradeoff is PHASE, not magnitude … that is
a GATE 2 question and cannot be settled from a log"*). Same structural gap as V48B.

⚠ **n = 1.** The fault has been observed once. Correlation with the flash is strong but a single event
cannot exclude an unrelated cause.

~~✅ **The decisive outstanding measurement is a DTC read**~~ — 🛑 **WITHDRAWN 2026-08-06: the DTC read
is STRUCTURALLY BLIND here.** `0xF00049` is a catch-all shared by ~42 fault_ids, its UDS status is **not**
an OR across members (a priority pick from a **RAM** log the power cycle clears, falling back to fid 4,
a power-on self-test), and `0x23 ReadMemoryByAddress` is **not implemented** on this ECU (NRC `0x11`,
three eras). See [[accord-dtc-read-is-structurally-blind-here]]. The discriminating instrument is a
probe-cave bit on the descriptor word — [[accord-descriptor-bit13-is-the-fault-fingerprint]].
🛑 Any live CAN/UDS send still requires explicit operator confirmation of the exact payload.
