# HANDOFF 2026-08-30 — the gain ladder, and what the measurement session found

## The deliverable

The operator's brief, mid-session: *"the safest, highest probability of working firmware with 6x torque
(or higher …) up to 16x torque with no grinding, vibration, or oscillation, best firmware for
autonomous driving."*

**Answer: a three-rung ladder, all on identical grinding work, four bytes per rung. And 16× does not
exist.**

```
  V241   6x   image 2ef7eb8eb2417905…  rwd 57d240d77f568aac…   same gain as the car
  V242   8x   image 424249b0c7d89fad…  rwd a94962b4240613c8…   RECOMMENDED
  V243  10x   image 5fb9ad74f104de46…  rwd 43a32ac352508557…   the ceiling
```

All three re-verified from disk at close-out; exactly one flashable `.rwd` each, 986,042 bytes.
Card: `docs/scoring/DRIVE-CARD-GAIN-LADDER.md`.

## Why the ceiling is real

The forward clamps must stay below the soft-EME floor `0xC674E`, and track the gain as
`gain × 512 // 891`: 6× → 3072, 8× → 4096, 10× → 5120 (= the floor; V219/V225 used 4608),
12× → 6144 FAILS, 16× → 8192 FAILS.

⚠ **`0xC674E` is not Honda's value on the car.** Honda ships **1024**; the car carries **5120**, raised
5× by an earlier build. Reaching 16× would mean raising it again to above 8192. **Left untouched in all
three builds and asserted so.** That is a decision for the operator, not for the kit.

## The risk, and why it is not V101 again

8× flew as V101 and was rejected — *"grinding/vibration at all speeds, only while LKAS commands"*. The
operator reverted to 6× himself. Measured: peak **moved 20.3 → 23.0 Hz**, de-confounded gain
**2.7–3.9× at 22–26 Hz**.

That band is what this lineage's notch attacks, and the notch is aimed by the **comma IMU** —
independent of the EPS. V101 raised the gain with no grinding treatment at all. **Safety is separate
from comfort here: V101 flew fault-free, EME audit passed. 10× has never flown at all.**

## What the measurement session established

**Positive.**
- The ratchet is **real chassis motion**, confirmed off-EPS for the first time (9/10 speed-matched
  routes, p 0.02, median 1.34 over a road control).
- The **grinding metric is valid** — V88, the one measured grinding fix, ranks near-best for grinding
  and near-worst for ratchet on the IMU. Prediction written before the answer was read.
- **22–30 Hz is the largest engagement-created motion band** (2.481, peak 25–26 Hz), and the alias-free
  audio confirms it is real, not folded from 71–79 Hz.
- **V241's notch beats V235's by 28%** on that objective, survives leave-one-route-out on all ten
  routes and five of six weightings, and cuts *less* of the damping band than V235 did.

**Negative, and each one closed an avenue.**
- Every cal in the assist-map path is measured: only `gp-0x69a0` moves the ratchet band without taking
  assist away, and it is broadband. Four cals are completely inert.
- `0xC6384` is **inert** — it only reaches above 2844 torque counts, 1.65% of frames. V236/V239 withdrawn.
- The **loop-delay hypothesis is refuted** by its own control.
- **No build has ever moved the ratchet**, confirmed on an instrument no build could game.
- **Torque and chassis name different bands** (ρ +0.040). The notch acts on torque, where its band is
  nearly the weakest — that is the honest ceiling on V241/V242's grinding claim.

**The one live thread.** The rule forbidding a 6–15 Hz notch — the band torque says matters — may rest
on a **rectified channel**: ra4/ra5/ra6 carry `mag427` without `sgn427`, and the field is a magnitude,
not two's complement. **Neither verifiable nor refutable from existing data.** Settling it needs a build
that puts the lane's sign bit on 427, plus a drive. If the rule falls, a 6–10 Hz notch is the strongest
lever the kit has had.

## Infrastructure fixed along the way

- **The whole `extract/` toolchain was dead** since the 2026-08-26 reorg (`rlog_parse` moved to
  `rlog-tools/lib/`). 51 files fixed. Invisible because the caches were already on disk.
- **`extract_imu_cache.py` had a hardcoded 6-route table** that rejected every route holding the
  speed-matched exposure. Now globs. **225 IMU caches, up from 109.**
- STATE.md archived 176 → 156 KB against the 256 KB cap.

## Corrections made to my own work this session

V237 built backwards and withdrawn · V240 promoted then found to cut a measured damper · "largest
measured ratchet lever" retracted as broadband · an arbitrary 0.97 threshold that rejected stock itself,
replaced by the car's own value · a claimed IMU null reversed when tested rather than eyeballed.

## Next

1. **A drive.** Nothing in this lineage has flown. V242 first, V241 if it grinds.
2. **The sign probe** — put `gp-0x6b86`'s sign bit on 427 and settle the 6–15 Hz rule.
3. If the rule falls, build the 6–10 Hz notch: it is the only untried lever with a measured case.
