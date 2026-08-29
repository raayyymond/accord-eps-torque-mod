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

---

## V183 — the strongest fix, PLUS the probe that unblocks the damper family

`9f9326170e8adab1…` · 24/24 · **3 bytes on top of V181, no cave change**

Carries V181's complete fix unchanged, and repoints CAN 427 to `gp-0x6ac0` — the signal that **hard
switches the entire base-assist damper off** (`gp-0x6ac0 >= 0x32C9` = 13001 zeroes the whole
five-factor product).

```
0x55DF2  9544 -> 9540    427 source gp-0x6abc -> gp-0x6ac0
0x55E10  a3   -> a4      packer sar 3 -> sar 4
```

**The shift had to move.** The 427 field is 10 bits at >>3, so its largest representable source is
1023x8 = 8184 — *below* the 13001 gate. It would have saturated before reaching the threshold and the
probe would have been worthless. At >>4 the max is 16368, resolution 16/LSB, and the gate lands at
field value 812.

**What a null licenses, written before the drive:**

| observation | conclusion |
|---|---|
| field stays >= 812 through engaged creep | damper is **hard OFF** whenever the ratchet happens — **the entire damper family is closed**, V182's direction included |
| field < 812 for a meaningful fraction | the gate is not the blocker; FactorC/FactorE knots become worth sizing |
| field pinned at 1023 | still saturating — the shift needs to go further, said unambiguously rather than silently |

So the drive tests the strongest available fix **and** answers a question that no amount of further
desk work can, because neither `gp-0x6ac0` nor `gp-0x6a5e` is in the corpus.

⚠ Cost: 427 stops carrying `gp-0x6abc` for this drive, and the channel is rescaled 2x, so historical
427 comparisons must account for the shift.

---

## V184 — the single-variable test (FLY THIS)

`96509cc9b102e026…` · 29/29 · base V183

**The finding behind it.** Stock ships mode 24 (manual) identical to mode 26 (engaged) across all six
mode-record families. Enumerating them on the build you are actually driving finds **exactly one**
kit-created engaged/manual asymmetry:

```
L1 · L3 · FactorE · L5      m26 == m24, m27 == m24
FactorC                     m27 differs ALREADY IN STOCK -> Honda's, not ours
0xCBE74 inertia             m26/m27 Y = [-29490,-17202,-16000]  vs  m24 [-9830,-5734,-1966]
```

The ratchet is engaged-amplified ~15x. **If that amplification comes from a mode asymmetry at all, the
inertia dose is the only candidate on the car.**

**Why V184 and not V183.** V183 inherits V158's damper edits, which *create* two new engaged-only
asymmetries your car does not have — so a result would be ambiguous between them and the inertia
dose. V184 copies those back from each table's own m24 record (read at build time, never typed).

Result: **engaged is identical to manual in every family, exactly as stock ships it, except the
inertia dose is gone.** One variable.

It still carries the poles, K1→Honda, the accel filter→Honda, w[3] halved, and the 427 probe — all of
which act in both modes or are instrumentation, so none confounds the engaged/manual contrast.

| what the drive shows | conclusion |
|---|---|
| ratchet falls **and** engaged/manual ratio falls | the inertia dose carried the engaged amplification — the strongest single result available |
| ratchet falls, ratio unchanged | the broadband levers did it; mode asymmetry was not the amplifier |
| neither moves | no mode asymmetry explains it; the search leaves the mode records entirely |

Independently, the 427 probe answers whether the damper's hard OFF gate is ever open.

---

## THE FORK — V184 vs V185. This is your call, not mine.

The biquad is **engaged-gated**, so V184's poles add **+16.4 deg of engaged-only lag at 1 Hz**, in a
path that is part of the plant openpilot controls.

**I tried to measure whether openpilot can afford it, and the attempt failed its own controls:**

```
ENGAGED (loop closed)   Mp = 0.840 at 0.39 Hz
manual  (loop OPEN)     Mp = 19.59 at 1.17 Hz   <- artifact, Ang/Cmd divides by ~0
phase-shuffled command  Mp = 0.683 at 0.39 Hz
```

The engaged peak is below 1 and barely above the shuffled surrogate — command and angle are both
dominated by road curvature, so the estimate measures the road, not the loop. **openpilot's phase
margin is not estimable from this corpus. The 16.4 deg is an UNQUANTIFIED risk, not a small one.**

And you list **peak command oscillation** as a current symptom. A loop that already oscillates has
thin margin by definition.

| | **V184** | **V185** |
|---|---|---|
| image | `96509cc9b102e026…` | `54e114d172d89dcb…` |
| grind 15–25 Hz | **−16.0 dB** | ~none |
| ratchet | −8.8 dB + inertia revert | inertia revert only |
| added lag @1 Hz | **+16.4 deg** | **~0 deg** |
| spends phase margin | **yes, unquantified** | **no** |
| K1 / accel filter / w[3] / inertia → Honda | yes | yes |
| 427 probe on gp-0x6ac0 | yes | yes |

**V184** if the ratchet is driven by loop gain in the assist section — it is the only build that
attacks the grind hard.
**V185** if you want the ratchet levers with **zero risk to command oscillation** — it is phase-
identical to what you drive today.

If the ratchet is caused by the inertia lane, V185 fixes it at no phase cost. If it is caused by
assist-section loop gain, V185 does nothing and V184 is the answer. Either way the 427 probe reports,
so the drive is informative on both branches.
