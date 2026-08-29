# BUILD DECISION — two real choices

Everything else on the shelf is a control or a step on the way to these two.

| | V177 — **conservative** | V180 — **maximum** |
|---|---|---|
| image | `fc93255645014a0f…` | `31505dc64def54da…` |
| assist poles | 0.970 | **0.980** |
| K1 Coulomb → Honda | yes | yes |
| engaged inertia → Honda | yes | yes |
| accel filter → Honda | no | **yes** |
| ratchet @8.64 Hz | 0.476 | **0.339** |
| grind @21 Hz | 0.189 | **0.127** |
| **added lag @1 Hz** | **+29 ms** | **+43 ms** |
| cells vs the flying build | 6 | 10 |
| attributable from one drive | **yes** | no |

## Which to fly

**V177 if you want to know *why* it worked.** One cell separates it from V175, so the drive can
attribute the result. Its case is the strongest quantitative one on the shelf: K1 was 10x Honda's.

**V180 if you just want the ratcheting gone.** It carries every Honda revert plus the strongest
attenuation inside the lag guardrail. The cost is 43 ms of lag at 1 Hz instead of 29 — you will feel
that as steering weight, and it is the thing you said must not be the price. If it is too heavy, that
is a real result and V177 is the fallback.

🛑 Both keep Honda's 55.23 Hz notch, the V31/V38 authority ladder, the V37 EME debounce fix, the
hard-fault interlock at 511, and `0xC63A6` unspent. GATE 2 magnitude passes on both (max |H| < 1).

## The drive is the same either way

Stage 1: **one continuous 15-second engaged creep pass, 1–24 km/h, real curvature. Then stop.**
If the ratcheting is still obviously there, say so and we are done with that build.

Stage 2, only if Stage 1 shows a win: three short alternating engaged / LKAS-off passes (~90 s).

```
python rlog-tools/score/score_band_excess.py <route-tag>
python rlog-tools/score/grind_engaged_vs_manual.py <route-tag>
```

⚠ Expect creep to feel **lighter** (inertia + K1 reverts) but **slightly laggier** (poles).
🛑 LKAS authority is **not measurable** on this drive — your impression is the instrument.
