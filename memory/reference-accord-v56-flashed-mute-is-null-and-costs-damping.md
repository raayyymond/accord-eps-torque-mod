# ★★ V56 FLASHED — the `0xC6AF0` mute is NULL for the 21 Hz and COSTS damping ⇒ REVERT to V55

**Route `24`, 2026-07-29** — 16 segments, **15:43**, the kit's **first road drive with a firmware probe**
(every prior vibration route was parking-lot creep). V56 = V55 + `0xC6AFC`/`0xC6AFE` 32768→0, which
zeroes the output bound of `gp-0x6ad4` unconditionally, i.e. **mutes the whole `FUN_0003a382` residual
lane, all three branches at once**.

## 1. The 21 Hz is UNCHANGED — the lane is eliminated as a class

Speed-matched creep (vEgo ≤ 1.6 m/s), engaged + hands-off, **full 16-bit** CAN `0x18F` bytes 0-1:

| build | P[15-26 Hz] engaged | disengaged | ratio |
|---|---|---|---|
| **V56 / route 24** | **1.28e8** | 1.63e5 | **786×** |
| V55 / route 1c | — | — | 877× (recorded) |

And the command still carries it: probe field P[15-26] = **182** on V56 vs **22** on V55 at matched creep
(peak 23.24 Hz), i.e. **not reduced**. Transition rate 23.9/s (V56) vs 21.9/s (V55) — the command is just
as active.

⇒ This is pre-registered **outcome (iii)**: neither the vibration nor the command's 21 Hz moved.
🛑 **`gp-0x6ad4` / `FUN_0003a382` is ELIMINATED as the 21 Hz source.** V43, V46 and V48A each attenuated
one branch; V56 killed all three via the output bound. That whole thread is closed — see
[[reference-accord-gp6ad4-lane-and-c6af0-output-gate]].

## 2. ★ The mute COST damping — GATE 2 answered in the unfavourable direction

The operator reports steering feels like **damping was removed**, with a **new resonance at a few Hz in
some instances**, absent before V56. That is exactly the risk `build_v56_tva.py` flagged as its one open
gate (*"if the lane is a DAMPING term, muting it could make the vibration worse"*).

It reproduces in the data. Welch, NFFT=1024 (0.0977 Hz), windows entirely engaged + hands-off +
CAN-contiguous, split on `steeringPressed` (avoiding the known spurious-7.42 Hz mixing trap):

| speed bin | n windows | top peak | vs next neighbour |
|---|---|---|---|
| 15-20 m/s | 82 | **8.69 Hz at 1.18e8** | **6.7×** (10.06 Hz @1.76e7) |
| 20-30 m/s | 15 | 9.67 Hz @4.72e7 | — |
| 10-15 m/s | 49 | 10.94 Hz @1.44e7 | no 8.69 line |

**Intermittent** — a handful of windows dominate (worst 09:23.21 and 09:21.94, vEgo ~18 m/s,
P[2-9] = 8.17e7 / 5.22e7), matching "in some few instances". **No disengaged spectrum at any speed shows
it**; disengaged is dominated by 1.2-3.3 Hz driver input.

⚠ **Two control gaps, stated rather than papered over:** there are **zero disengaged windows above
15 m/s**, so the 8.69 Hz bin has no matched-speed disengaged control; and **there is no pre-V56 road
baseline in the archive** — route `13`'s surviving segments (12-15 only) are creep, vEgo max 2.73 m/s.
The operator's felt comparison is the primary evidence that the mode is *new*.

## 3. 🛑 A partial restore (`Y = 16384`) is NOT a candidate

The lane at **100%** authority (V55) and at **0%** (V56) produced the same 21 Hz. Intermediate authority
is bounded between two measurements that already agree, so it can only deliver a fraction of an effect
that was zero. It has no experimental value — it is a partial revert wearing a candidate's clothes.

## How to apply

- **Revert to V55.** `39990-TVA,A160-V55-...rwd`, SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf`.
  Already built, already driven, known-good, and it keeps the probe.
- Do **not** re-propose any `FUN_0003a382` lever for the vibration — the branch-agnostic test is done.
- The 21 Hz must enter `gp-0x6b98` through a **different summand**. The aggregator has **9 lanes**, all
  plain `add` — enumerate the others. See [[reference-accord-fun3a382-is-a-real-pid]] for the confirmed
  lane list.
- ⚠ Every amplitude figure derived from the probe is suspect — see
  [[reference-accord-probe-underranges-to-a-one-bit-comparator]].
