# HANDOFF - 2026-07-20 - SESSION: V40 ignition fault investigation

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2.
**Session scope:** diagnose why V40 disabled power steering, and build the next candidate.
**Outcome:** V41 BUILT + VERIFIED (NOT FLASHED). **V40's fault is NOT root-caused.** Three of the
lead's own hypotheses were retracted during the session; a kit tooling defect was found and fixed.

> Companion build doc: `docs/HANDOFF-2026-07-20-v41-ratecap-flat.md`. Read that for V41's contents.
> This document is the session narrative, the state of knowledge, and the do-not-re-walk list.

## 1. The presenting problem

V40 was FLASHED. The car came up with an **immediate EPS warning lamp and power steering completely
disabled** — operator-confirmed as occurring **with the car stationary and completely untouched**, at
every start. The operator also raised sensor noise (torque sensor or electrical-angle-rate estimate)
as a candidate.

V40 made two calibration-only changes, both of which **remove a protection**:
- merged-governor slew steps `0xC6206`/`0xC6208`: 512/205 → **65535** (rate limiter defeated)
- motor-rate cap table flattened to `Y = 5325 × 5`, Q13 slopes zeroed (taper removed)

## 2. ⚠ Three retractions — read these before trusting anything else

This session produced three confident-but-wrong conclusions from the lead. All are corrected in place
in the memory files, but the pattern matters more than any one of them.

**R1 — "The `0xC6000` CRC bridge is bogus; the chain is 50 blocks."**
Claimed the kit's `verify_bootloader_crc.walk()` invented a bridge and that V40's stale `0xC5FFC` CRC
failed a startup check. **The bridge is REAL.** `FUN_0000b006` genuinely hard-codes it — byte-verified:
`0xB070`/`0xB072` encode the literal `0xC6000` compared against, `0xB07A`/`0xB07C` → `0x13000`,
`0xB080`/`0xB082` → `0xB1FFC`. The walker was faithful. A subagent overturned this with raw bytes.

**R2 — "The cap flatten is the prime suspect, because `MIN(4762, cap)` differs at rest."**
The `MIN` was mislocated: cal `0xC6202`=4762 has **exactly one reader image-wide, `0x7B06A`, inside
`FUN_0007b022`** — not in the governor. And once the axis was established, stock and flat are
**identical at rest**. The argument did not survive its own premises.

**R3 — "`0xC6194` is the correct place to loosen LKAS slew."**
It is **architecturally inert**: gain cal `0xC63CC` = `0x0000` multiplies out the entire rate-limited
term. The zero was visible in a u16 read early on, was dismissed as a probable reporting error rather
than chased, and a build was written on top of it before it was checked.

**Also retracted:** extrapolation-based cap numbers (rate 0 → 8137, rate 10000 → −15348). The LERP
**clamps**; those values are never computed.

**And an over-correction:** the lead cast blanket doubt on the prior "motor resolver electrical-angle
rate" identification purely because it shared a session with R1's error. It was **correct**, and was
re-derived independently. Guilt by association is not evidence.

**Process lesson of record:** *a verifier and the assertion that checks the verifier must not share an
assumption.* V40's `assert_crc_gap_is_real()` passed precisely because it re-derived the "gap" from the
same walker it was meant to check. That is how a stale CRC reached a car with a green build log.

## 3. Tooling defect found and fixed

`analysis-2020accord/verify_bootloader_crc.py` now exposes **two** walks, because they answer different
questions and conflating them cost a build:

```text
walk()             faithful bootloader replay, 49 blocks, bridge INCLUDED -> predicts UDS NRC 0x72
walk_all_blocks()  stored linked list, 50 blocks -> HYGIENE only, NOT a bootloader replay
```

`[0xC5000, 0xC5FFC)` is a real, self-describing block whose CRC is correct in stock/V31/V37/V38 — but
**nothing in the firmware reads it** (§4). Keep it consistent anyway; it costs four bytes.

Builders now assert the **inverse** of V40's assertion: every written address must be provably *inside*
a CRC-covered block, and every dirtied block must be recomputed. Uncovered is build-stopping.

## 4. Established this session (VERIFIED, with citations)

**Integrity / boot**
- `FUN_0000b006` = UDS CheckProgrammingDependencies. Reachable **only** via a diagnostic session; on
  failure sets `DAT_fedf20ba = 0x72` (UDS NRC). **No DTC, no motor-off.**
- Boot path: reset `0x6: jr 0x8000` → **blank/presence check only** on four addresses (`0x13010`,
  `0x14000`, `0x9060`, `0xA6000`) compared against `0xFFFFFFFF` → `jr 0x14010`. **No CRC at boot.**
- App range: **no CRC32 polynomial present**; **zero xrefs to `0xC5FFC`/`0xC5FF8`/`0xC5FFA`** image-wide.
- ⇒ **The stale `0xC5FFC` CRC has no consumer. It cannot have caused the fault.**

**Governor `FUN_0004503c`**
- Step selector: `gp-0x67f5 == 0` → `0xC6206` (512, "fast"); else → `0xC6208` (205, "slow").
  `gp-0x67f5` is set by the driver-torque voter `FUN_00041eec` — forced `0xFF` when raw torque diverges
  from the vote by ≥65, debounced to 1 while voted `|torque|` ≥ 640. **At rest/hands-off the FAST step
  is active; the SLOW step governs hard turns.**
- Effective step = `(cal × r23) >> 15`, `r23` provably ≤ 32768 (two chained `FUN_00049a78` MINs seeded
  at literal `0x8000`). **No overflow at any cal value up to 65535.**
- **Sign-crossing reset has NO hysteresis and NO minimum-magnitude qualifier** — any sign flip, however
  small, zeroes the accumulator `gp-0x138a`.
- **Target is `gp-0x6b94`, the AGGREGATOR output (LKAS + base assist)** — read at `0x453E0`. The cap
  `gp-0x4f64` is read at `0x453F0`. ⇒ **this governor is NOT LKAS-specific.**

**Motor-rate cap**
- Table `0xC520C` (mirror `0xC5224`): count 5, X `(1050,1700,2500,3700,4100)`, Y
  `(5325,3584,2406,1587,512)`. Slopes at `0xC5030`/`0xC5038` are the **exact Q13 finite differences**.
- **The LERP CLAMPS at both ends** (`0x7b658`-`0x7b67a`; both clamp branches are unconditional jumps to
  `0x7b71a`, displacements confirmed). Below `X[0]` → `Y[0]`=5325; at/above `X[4]` → `Y[4]`=512.
- **`0xC5224` is a redundant MIRROR, not a composed stage**: the query lands in `r24` once at
  `0x7b642`, and `r24` is untouched between `0x7b656 mov r24,r7` and `0x7b722 mov r24,r7`.
- **Index = `clamp(gp-0x6ac0, 0, 10000)`** on the dominant path — `MIN` not `MAX` (`0x7b3fe`/`0x7b40a`
  against cal `0xC559C` = `10000.0f`), gain cal `0xC5648` = **1.0f exactly** whenever the
  `gp-0x4f0c`-derived channel ≥ cal `0xC5598` = `42.0f`.
- **`gp-0x6ac0` IS motor resolver/FOC electrical-angle rate** — re-derived, 5 hops, sole writer at each:
  `FUN_00041464` → `gp-0x4f50` → `FUN_00068fbe` (IRQ snapshot) → `gp-0x29c4` → `FUN_00068f52` (14-bit
  wraparound delta, ×120000>>14, 2-sample avg, clamped ±13000) → `FUN_00065afe` (sin/cos ADC pair,
  atan2/CORDIC, `&0x3fff`). **Mechanically coupled to steering angle**, per the operator.

**LKAS lane**
- `FUN_00026c80` writes `gp-0x6b4c`, the LKAS lane the aggregator reads at `0x3AA3E`. It contains a
  complete rate limiter (`0xC6194`=3, bounds `0xC6192`=2048/`0xC6198`=3072) that is **INERT**: gain cal
  `0xC63CC` = `0x0000` (verified `0x276c2 ld.hu 0x73CC[tp],r8`) zeroes the whole term. `gp-0x6b4c`
  reduces to `gp-0x3d88`, an **unlimited per-mode passthrough**.
- `gp-0x3d6c`/`gp-0x3d84`/`gp-0x3d88`: 2 sites each, **all inside `FUN_00026c80`**. No other consumer.
- ⇒ **There is no live LKAS-specific slew limit.** The LKAS command already reaches the aggregator
  unfiltered.

**Fault machinery**
- **`FUN_000462e6`'s first argument is DTC *data*, not an index** — it unconditionally calls
  `FUN_00016de6(0x1d, param_1, 1, 1)`. So `0x3a09`/`0x3f8e`/`0x3f1b` all feed the same `0x1d`
  hard-shutdown class. Partially closes the kit's open `0x1D`↔`0x49` mapping question.
- **`FUN_00016de6(0x1d, …, 1, 1)` reaches the motor-off escalation with NO debounce counter.** A single
  out-of-bounds cycle in `FUN_0004595a` or `FUN_00045a20` suffices. Standing fact, not specific to this bug.
- New monitor `FUN_00045a20`: checks `gp-0x6acc − gp-0x6ace` against a float band LERP'd from
  `0xC6610..0xC661C` (350/410/5000/400, stock in both builds).

**Correction of record:** the limp-path cals are `tp+0x7c3c` = **`0xC6C3C` = 1** (identity) and
`tp+0x7c22` = **`0xC6C22` = 25** — *not* `0xC7C3C`=424. ⚠ **The `+0x1000` tp slip occurred THREE times
from three different agents in one session.** Always re-verify tp-relative addresses against raw bytes.

## 5. Dead ends — do NOT re-walk

| Candidate | Verdict |
|---|---|
| Stale `0xC5FFC` CRC | **Dead.** No consumer anywhere (§4) |
| Slew `65535` overflow/truncation | **Dead.** `r23 ≤ 32768` bounds the product; effect is snap-to-target, not wraparound |
| Four shadow lockstep pairs | **Dead.** `gp-0x6ace`↔`gp-0x4cca`, `gp-0x6b94`↔`gp-0x4ce0`, `gp-0x6acc`↔`gp-0x4cc8`, `gp-0x4f64`↔`gp-0x448a` — both halves written in the same branch, atomic w.r.t. the check |
| `FUN_0004595a` / `FUN_00045a20` as chatter triggers | **Unlikely.** Same-cycle stage-consistency checks; defeating the limiter makes output track target exactly, satisfying them *more* easily |
| Rate-limit limit cycle on the LKAS lane (vibration) | **Dead.** No live rate limiter there (`0xC6194` inert) |
| Cap flatten as the ignition-fault cause | **Weak.** Provably identical to stock at rest (both clamp to `Y[0]`) unless a startup transient lifts the rate above ~1050 |

## 6. Leading hypothesis for V40's fault (UNCONFIRMED)

**Removal of the merged-command slew limit.** A slew limiter is a low-pass filter on the torque
command. At rest the target is sensor noise around zero; the sign-crossing reset fires on every noise
sign flip (no hysteresis, no minimum magnitude — verified); with the step at 65535 the command snaps to
the full noisy target every cycle. Maximum chatter at zero command, stationary — matching the symptom.

**Secondary: a startup transient in `gp-0x6ac0`.** `gp-0x29c2`, `gp-0x4f4e`, `gp-0x359c` have **no
writers except their own read-modify-write**. First-sample guards exist but are gated on exact sentinels
(`0x8000`, `0x7FFFFFFF`) that **nothing writes** — "primed by luck, if at all." Worst case cycle 1 can
reach the ±13000 clamp; IIR gain `0xC643C`=37/128 settles in ~9-14 cycles. At high rate stock clamps to
512 while V40 gives 5325. ⚠ **Not provable from this image** — the crt0 trace terminates at
`0x8bea: jr 0xFEDF0048`, a RAM address whose contents are not in `code.bin`. Also weakened by: if the
ECU retains standby power, RAM holds the previous angle and no transient occurs.

## 7. Artifacts

- **`V41` — BUILT + VERIFIED, NOT FLASHED.** V38 + 36 bytes: cap flattened (both mirrors), slopes
  zeroed, `0xC5FFC` CRC. **The `0xC6000` block is byte-identical to V38.**
  RWD `77fbd6aa695d63c3bdd69fd4db4be36dc879ae7fc423e0934951933ea38c60e5`.
- **`V42` and `V43` were DELETED** at operator direction (builders, images, RWDs, handoff). Version
  numbering does not advance past V41 until V41 is superseded.
- `V40` retained as the flashed-and-faulted reference.

## 8. Open threads, in priority order

1. **The vibration mechanism is unknown again.** If a rate limit shapes the LKAS lane it must be
   upstream of the `gp-0x62b0` mode-value array (computed base — a gp-relative displacement sweep will
   not find it) or in whatever sets the `tp+0x5118` mode flags. Untraced.
2. **V40's fault mechanism.** §6 is the leading candidate; neither branch is confirmed.
3. **Aggregator deadband.** `FUN_0003aa2c`'s own body has no near-zero deadband (only wide
   range-validity gates). Its **seven upstream lanes were not checked** — any one could pin near zero,
   which would kill the noise-chatter hypothesis outright.
4. `gp-0x4f0c`'s physical identity (the channel gating the cap's `42.0f` branch). No longer load-bearing.
5. `gp-0x6ac0`'s sibling `gp-0x6ac2` carries the sign-gate against `gp-0x6b98`; `gp-0x6ac0` does not.
   Fix wherever the old note claims otherwise.

## 9. Memory files written or corrected

- `reference-crc-chain-is-50-blocks-c5000-not-a-gap.md` — **corrected twice**; now records that the
  bridge is real and that nothing reads the block.
- `reference-accord-c520c-cap-table-axis-provenance.md` — **corrected**; clamp behavior, settled index,
  mirror-not-composition.
- `reference-accord-lkas-only-rate-limiter-c6194.md` — **corrected**; now records the zero gain.
- `reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs.md` — new.
- `feedback-delegate-firmware-tracing-to-subagents.md` — strengthened to a default, plus a `CLAUDE.md`
  entry: **RE/decompilation goes to subagents; the lead verifies at the end.**
