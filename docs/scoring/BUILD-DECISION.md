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

---

## V181 — the last lever, spent

`0xC63A6` (w[3]) **1024 → 512**, on a V180 base. One cell, image `49ca42da43e95f31…`.

It weights the **only ω²-scaled lane** in the six-term sum, so halving it removes loop gain **66.7×
harder at 8.17 Hz than at 1 Hz — with zero added lag**. That is the cleanest match to the standing
constraint (no ratcheting AND no added mass to LKAS) of anything built this session.

**Why it is safe:** GATE 1 — one writer, and the sum's gate can never close because the writer clamps
to ±511 inside a ±1024 window, so w[3] multiplies every frame. GATE 2 — the term is *positive*
acceleration feedback, i.e. destabilising, so reducing it can only increase stability margin; there is
no magnitude or phase condition to satisfy. Precedent: its sibling `0xC63A0` moved 2× on-car
fault-free at V72/V77.

⚠ **This is the only edit that goes BELOW Honda's own configuration.** Honda includes
apparent-inertia compensation deliberately, to make the wheel lighter. Halving it will feel slightly
**heavier — but at high frequency, not at the ~1 Hz where you and LKAS steer**, because of the ω²
weighting. Dose is a half, not zero, so there is headroom left if it helps but does not cure.

| | V177 | V180 | **V181** |
|---|---|---|---|
| ratchet @8.64 Hz | 0.476 | 0.339 | 0.339 **+ ω² lane halved** |
| grind @21 Hz | 0.189 | 0.127 | 0.127 |
| added lag @1 Hz | +29 ms | +43 ms | +43 ms |
| goes below Honda | no | no | **yes** |

---

## V182 — the only build that ADDS damping (strongest)

`0xD77DA` 429→700 and `0xD77EE` 426→700, on a V181 base. Image `1375f42510641e7b…`, 29/29.

Every other build this session **removes** loop gain. This one raises FactorC's below-35 km/h
fallback so **Honda's own base-assist damper works harder across the whole creep band** — which is
the textbook fix for a lightly-damped mode, and the one direction nothing else covered.

```
ch0 = (FactorC x FactorE) >> 10        below 35 km/h, FactorC = Y[0]
  now   (429 x ~310) >> 10 = 129
  V182  (700 x ~310) >> 10 = 211        ~1.63x more creep damping, ENGAGED ONLY
```

**Mode-proofed at build time.** The builder resolves the pointer table at the indices the car actually
runs (m24 manual / m26,27 engaged), asserts the records match, and asserts **manual stays stock** —
so parking and manual feel cannot change, and the drive can separate it by the engaged-vs-manual
contrast already on the card.

**Why it reaches the ratchet:** FactorE is rate-gated, and an 8 Hz oscillation of even 1° makes
~50 °/s, which already clears its knee. So the damper grows *with* the oscillation and stays small in
smooth driving — it damps the ratchet without adding steady drag.

⚠ It does add drag while engaged at creep. It is **viscous, not stiction**, so no static friction is
added, but you will feel more damping in engaged creep. Headroom remains: Y[0] could go to 908.

| | V177 | V181 | **V182** |
|---|---|---|---|
| removes loop gain | yes | yes + ω² lane halved | same |
| **adds damping** | no | no | **yes, 1.63x at creep** |
| added lag @1 Hz | +29 ms | +43 ms | +43 ms |
| manual feel changed | no | no | **no (asserted)** |
