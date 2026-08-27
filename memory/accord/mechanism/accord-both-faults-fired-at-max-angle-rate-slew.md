---
name: accord-both-faults-fired-at-max-angle-rate-slew
description: Both hard faults fired at their drive's single largest |d(angle rate)/dt| (n=1 each) while torque magnitude does NOT unify them — a static un-debounced monitor corridor, not a dose problem.
metadata:
  type: reference
---

★★★★★ **The variable that unifies both ECU hard faults is ANGLE-RATE SLEW, not magnitude, not dose.**
One metric applied to both fault drives, sentinel-free:

| | \|driver torque\| peak, 100 ms pre | its pct | **\|d(angle rate)/dt\|** | its pct |
|---|---|---|---|---|
| **V74** (route 61, t=732.3872) | 3,676 | 99.999 | **5,400 /s** | **route MAX, n = 1** |
| **V75** (route 5e, t=284.7947) | 922 | **86.3** | **6,900 /s** | **route MAX, n = 1** |

**Magnitude does not unify them; slew does** — each fault fired at its own drive's single largest
value, n = 1 in both. ⇒ **This dissolves V75's "mildest of four launches" paradox**: the relevant
quantity was never dose, it was the single-cycle rate of change.

**Corroborated independently on V74:**
- **The bump was ORDINARY.** IMU at 101.03 Hz (vertical axis = **`ax`**, 0.9884 g). A real bump exists
  — `ax` deviation **−1.494 m/s² at −15 ms**, rebound **+1.559 at +34 ms**, so the operator's "over a
  bump" is correct — but it ranks **#84 of 388** isolated excursions, **78.6th percentile**, with the
  route max **2.94×** larger.
- V74 **survived 8 earlier damper-live episodes** above 3,000 counts of bar torque, and **502 frames**
  at ≥3,000 counts with the damper live.
- At the fault the rate was 20–78 ct — inside FactorE's **ramp** (`X[0..1]` = 12..400), **not** the
  flat band ⇒ **the V74/V75 bang-bang relay is cleanly ELIMINATED for this fault.**

★★★★ **THE ROM STRUCTURE CONVERGES ON THE SAME ANSWER, INDEPENDENTLY.** There are **FOUR** monitor
trip surfaces feeding fault_id 28/29:

| surface | int leg (fid 28) | float leg (fid 29) | compares |
|---|---|---|---|
| **A** damper ceiling-clamp | `FUN_00034350` → `FUN_0004613e(0x4179,…)` | `FUN_000347b8` → `FUN_000462e6(0x417a,…)` | **`gp-0x6bd0` itself**, ±5/1024 |
| **B** comp-envelope | `FUN_000456a4` → `FUN_0004613e(0x3c35,…)` | `FUN_00045a20` → `FUN_000462e6(0x3a09,…)` | `gp-0x6acc` vs `gp-0x6ace` |

**Neither surface computes a derivative** — both are **per-cycle STATIC consistency checks** between
int and float representations of the same quantity, computed by two independent code paths.
★ **And the DTC-manager dwell is a structural NO-OP for these two IDs**: `FUN_00018738`'s trip test is
`increment + gp-0x42ec[fid] + 1 < threshold`, where `threshold` is the record's own offset+2 field —
and it reads **`0x0000` for both fid 28 (`0xB8054`) and fid 29 (`0xB8070`)** (both descriptors
`0x3D01`). Any accumulator ≥ 0 already fails `< 0` ⇒ **it trips on the FIRST qualifying call.** The
only real debounce is the ~**0.1 s** accumulator inside each monitor (`gp-0x3564` / `gp-0x3550`).
⇒ **A static, effectively un-debounced window on two independently-computed representations is
EXACTLY what a large single-cycle transient trips.** Two unrelated lines of evidence — the on-car slew
statistics and the ROM's monitor structure — land on the same mechanism.

🛑 **SENTINEL TRAP — this bit me before I caught it.** At the fault frame the `0x14A` angle fields
latch to `0x7FFF`. A derivative window that *touches* that frame imports a ~16,000-count spike and
inflates `|d(rate)/dt|` **~300×**. Use a strict pre-fault prefix and **assert it is sentinel-free**.
This is the same trap that contaminated `v75fault_{timeline,analysis,followups,oscillation}.py`.

⇒ **THE LEVER THIS IMPLIES HAS NEVER BEEN PROPOSED IN THIS KIT: something that limits `gp-0x6bd0`'s
SLEW, not its magnitude.** Every damper lever tried (`C_Y0`, `E_X0`, `E_X1`, `E_Y1`, `0xC63A0`) moves
gain or shape, not rate of change.

⚠ Not exhaustive: 5–8 further `FUN_0004613e`/`FUN_000462e6` callers (`FUN_00027b0a`, `FUN_00027802`,
`FUN_00036388`, `FUN_00036c12`, `FUN_00041464`, `FUN_000365d2`, `FUN_00036d74`, `FUN_00041b8e`) were
not traced; none is in the Path-2 dataflow by name, but a fifth surface is not formally excluded.
⚠ ROM statics **cannot** discriminate fid 28 from fid 29 — both eligible, both `0x3D01`. Only a
runtime probe on `gp-0x42ec[28]`/`gp-0x42ec[29]` or `gp-0x3564`/`gp-0x3550` can.

Related: [[accord-v74-fault-damper-WAS-in-force-mode-lag]] · [[accord-v77-cannot-reach-the-monitors]] ·
[[accord-descriptor-bit13-is-the-fault-fingerprint]] · [[feedback-episodes-not-windows]]
