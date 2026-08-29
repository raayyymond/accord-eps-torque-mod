# THE SHELF — what is built, what to flash, what it changes

**Updated 2026-08-29.** Four flashable builds: V199, V202, V203, V204. Everything else from this arc is renamed
`SUPERSEDED-DO-NOT-FLASH-GATE2-…` and must not be sent.

🛑 **Nothing here has been flashed and no CAN or UDS message has been sent.** Flashing requires you to
name the file and the bus, and they will be read back to you first.

---

## ⭐ V203 — FLASH THIS ONE. The best fix, plus the measurement that makes a null readable.

```
39990-TVA,A160-V203-V202BASE-PROBE-THE-PEDESTAL-0x13000-0x100000.rwd
  image 0da3b7b9a4bfa9068960ed1c5afd07ff4f816376da9488df4d31946cf55b5965
  rwd   e9513d179e9336b7aa448dae03980b3a033557743a3f63a5de162553e5c20abf
```

V202 control cells byte-identical, +3 payload bytes putting `gp-0x6b7e` (the unfiltered pedestal) on
CAN 427. Preflight 8/8, 40/40 assertions.

## V202 — the same fix without the instrument

```
39990-TVA,A160-V202-V199BASE-POLES.15.25.WIDER.SHOULDER-0x13000-0x100000.rwd
  image 2c5bc569c2c5e4c66f7eaa350ddbfe87d50af9875fa75a10d927eed3a7255160
```

Same null as V199 (19.75 Hz, depth 0.00099), poles dropped 17.45 → 15.25 Hz and radius eased to
0.9600. `max|H|` = 0.999998, so it still can only remove loop gain.

| f Hz | V199 | **V202** |
|---|---|---|
| 16.33 | 1.6× | **2.3×** |
| 18.00 | 3.0× | **4.6×** |
| **20.12 (median grind peak)** | 15.6× | **24.7×** |
| 22.15 | 2.8× | **4.3×** |
| 23.00 (the gain line) | 2.2× | **3.4×** |
| 30.00 | 1.1× | **1.5×** |

Cost: **~3 ms** more group delay in the driver-assist path (+3.80→+5.52 ms vs V199’s +1.30→+2.37).
Human steering-feel thresholds are tens of ms.

🛑 **The notch is a POINT fix, not a band fix.** A joint minimax over the whole 16.3–23 Hz band
improves worst-case leakage by only 1.1× and makes the median *worse* — one biquad cannot cover
6.7 Hz. **So score the drive stratified by its own peak frequency, never pooled:** a drive peaking at
16 Hz gets 2.3×, one peaking at 20 Hz gets 24.7×.

## V204 — V202 + the probe that unblocks the kit’s best parked lever

```
39990-TVA,A160-V204-V202BASE-PROBE-GP6B4E-0x13000-0x100000.rwd
  image 30e7da9f6d20ff1335d01abe86ba03df7245c802217a4e6df54c5b93208873e6
```

V202 control cells byte-identical, +3 payload bytes putting `gp-0x6b4e` on CAN 427. Preflight 8/8.

`0xC63AA` has sat parked since 2026-08-20 as *“the best structural lever, but it needs the dilution
ratio first.”* Mirroring `FUN_00038148` closed two of its three unknowns and showed the **recorded
sensitivity is 41× understated** (2.577× `gp-0x6b4c`, not 0.0625× — the record kept a `>>4` but
dropped the `*0x10` that cancels it). The last unknown is how big `gp-0x6b4e` runs, and this measures
it. Small ⇒ the lever is dominant and worth sizing; comparable ⇒ it is genuinely diluted and should
be struck rather than left parked.

⚠ 41× more potent also means 41× more able to destabilise — `gp-0x6b70` is clamped at ±8192 and
2.577 × a `gp-0x6b4c` of 4000 already exceeds it. This is a lever to size, not a free one.

## V199 — the low-phase fallback

```
39990-TVA,A160-V199-V196BASE-NOTCH.POLES.BELOW.ZEROS-0x13000-0x100000.rwd
  image c86646ab48c4a62546b4e7bafa59f8097d3bdd99ffdcd3aeabd9f93c7252dc10
  rwd   8df71f5db9f51e3cccf2d14c27aa580869434125112271115cfaddeddface708
```

A notch on the grind at **19.75 Hz**, plus the engaged inertia half-dose, built so the filter **cannot
add loop gain at any frequency**.

---

## 🛑 WHY V194 / V195 / V196 / V198 WERE PULLED

`BUILD-LINEAGE.md`, V105 section, says it outright:

> *"THE HIDDEN ONE: fixing DC with **poles at the notch angle** (the textbook narrow notch) forces
> `max|H|` to 1.098–1.608 … Fix: **Honda's own poles-BELOW-zeros layout**. **Check `max|H|` over
> 0–500 Hz against stock's 1.0000 before shipping any biquad edit.**"*

Every notch build from V188 on put the poles at the zeros. Measured from the built images:

| build | `max|H|` 0–500 Hz | zeros | poles | radius | verdict |
|---|---|---|---|---|---|
| V122 (Honda's layout) | 1.0000 | 55.23 | 42.35 | 0.7966 | PASS |
| V188 / V189 / V194 | 1.3533 | 19.40 | 19.40 | 0.9300 | **FAIL — adds 35 % loop gain** |
| V195 / V196 / V198 | 1.7177 | 19.75 | 19.75 | 0.9000 | **FAIL — adds 72 % loop gain** |
| **V199 / V200** | **1.000000** | 19.75 | **17.45** | 0.9675 | **PASS** |

V196 amplifies **1.88× Honda at 35 Hz, 4.57× at 45 Hz, 1.72× at Nyquist**. V103's own GATE 2 — the
argument that licensed arming this filter at all — was *"|H| ≤ 1.000032 everywhere 0.1–500 Hz ⇒ the
filter can only REMOVE loop gain, never add it."* A filter that **adds** gain in the loop whose
instability we are chasing is not a fix.

**It shipped because V195's own gate was written `check(mx <= 2.0, …)`.** The gate existed and the
number in it was wrong. V199's is `<= 1.0000001`, with a control assertion that the V196 base fails it.

---

## WHAT V202/V203 CHANGE vs V122 — 11 cells, 30 payload bytes

| addr | V122 → V199 | what it physically is | introduced |
|---|---|---|---|
| `0xC60A8` | `−1.5372` → `−1.9289435` | biquad pole angle → **15.25 Hz** | V202 |
| `0xC60AC` | `0.63462` → `0.9216000` | biquad pole radius → **0.9600** | V202 |
| `0xC60B0` | `−1.8808` → `−1.9846207` | **the notch centre, 55.23 → 19.75 Hz** | V195, kept |
| `0xC60B4` | `0.81731` → (forced) | overall gain — forced by unity DC | V202 |
| `0xC40D2` | 1020 → **102** | K1, modelled Coulomb friction — Honda’s VALUE, but see below | V177 |
| `0xC40DC` | 8 → **22** | acceleration EMA alpha → **Honda** | V179 |
| `0xC63A6` | 1024 → **512** | w[3], the inertia term's weight, halved | V181 |
| `0xD7A5C` | (−29490,−17202,−16000) → **(−4915,−2867,−983)** | **engaged** inertia curve, **half Honda** | V196, kept |
| `0xD7A6C` | (−29490,−17202,−16000) → (−9830,−5734,−1966) | m27 inertia curve → **Honda** | V175 |
| `0x55DF2` | −27324 → −27328 | CAN 427 probe source → `gp-0x6ac0` | V183 |
| `0x55E10` | 12963 → 12964 | the probe's pack shift, `sar 4` | V183 |

**Measured on-car:** none of the four biquad cells — this filter geometry has never flown.
**Reverts to Honda:** `0xC40DC`, `0xD7A6C`.
🛑 **The friction lane is NOT Honda’s.** `0xC40D2` holds Honda’s K1, but the ramp knee `0xC40BC` was
never reverted (600 → 3000) and it multiplies the whole expression: `(600/3000)×(102/102)` = **0.200×**
Honda below saturation, with saturation moved from motor-rate 50 to 250. Above saturation it equals
Honda exactly. **Less friction means less ratchet and matches your low-friction directive, but the
verified polarity is more friction = more assist, so it is also an authority cut in that lane.**
**Unverified doses:** `0xC63A6`, `0xD7A5C` (the inertia sign has not been confirmed on-car).
**The cave is byte-identical** to V196 — no code-cave change, so this is not the bricking class.

🛑 **Manual driving is unaffected by the biquad either way.** The section is engagement-gated by V103's
three-site patch on `gp-0x6806`, so every notch cell is inert with LKAS off.

---

## BEFORE YOU FLASH

```
python flashing-2020accord/preflight.py "<the .rwd filename>"     # V199/V200/V201 all pass 8/8
tmux kill-server                                                  # openpilot/pandad MUST be dead
```
Name the file and the bus out loud. They will be read back to you before anything is sent.

## THE DRIVE

Two passes are enough. The design law is that one short symptomatic drive must interpret the build.

1. **~15 s engaged creep, hands off** — the grind's home ground.
2. **~15 s engaged, hands lightly on** — the corpus blind spot; `f'` compresses 6.3× when you push.

Then:
```
python rlog-tools/score/score_band_excess.py <tag>
python rlog-tools/score/cross_channel_band_excess.py <tag>
python rlog-tools/probe/decode_v201_pedestal.py <tag> --v203       # V203 only
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v204  # V204 only
```

## STOP CONDITIONS

| what you feel | what it means | what to do |
|---|---|---|
| ratcheting noticeably **worse** | the inertia sign is inverted | stop; reflash the prior build |
| wheel heavy or dead to fast inputs | the half-dose is too much | stop; quarter it |
| a **new high note while engaged** | Honda's 55 Hz null, which the notch gives up | stop; it can only appear with LKAS on |
| grinding unchanged | the notch is aimed at the wrong frequency | stop — no point continuing |

## PRE-REGISTERED — write the sentence a null will license

| endpoint | prediction | what a null means |
|---|---|---|
| **15–25 Hz excess on `cs_rate`, STRATIFIED BY THE DRIVE’S OWN PEAK** | peak near 20 Hz → **24.7×**; peak near 18 Hz → 4.6×; peak near 16.3 Hz → **2.3×** | pooling these hides the result — a low-peak drive can look like a null when the filter did exactly what it was designed to |
| 6–9 Hz excess on `cs_tq` | unchanged | the notch was never aimed there; that band is the ratchet |
| LKAS command 0.5–3 Hz | unchanged | the biquad is not in the command path at all, so any movement here is something else |
| `gp-0x6b7e` content at the drive’s peak (V203) | small vs the notch output | if it dominates, the pedestal is the bypass and the lever is `0xC6906–090C` (K = 20 at all four knots) |
| `gp-0x6b7e` duty | if identically zero, the friction-hold limiter never cuts engaged | the whole parallel path leaves the model |

## 🛑 WHAT THE NOTCH CAN AND CANNOT FIX — corrected 2026-08-29

Decompiling `FUN_000352b4` settled which signal this filter is actually on. The tp anchors check out
exactly (`tp+0x749b` = `0xC649B` the arm cell, `tp+0x70a8`–`0xb4` = the four coefficient cells), so this
is the filter we have been editing:

```
gp-0x4f60 (TORQUE SENSOR) -> clamp +-8192 -> 10-knot assist map -> gp-0x6b7a
  -> friction-hold limiter -> gp-0x6b82 -> BIQUAD -> clamp +-12.0 -> x1024
  -> + gp-0x6b7e  (UNFILTERED, added AFTER the filter)
  -> clamp +-0x3000 -> gp-0x6b86 -> aggregator
```

**`gp-0x6b86` is the base power-assist output, not the LKAS command.** An earlier note of mine called
it "the LKAS command" — that was wrong and is retracted. What follows:

| symptom | can this notch fix it? |
|---|---|
| **Grinding** | **Yes, and this is the right place.** motion → column torque → sensor → assist map → biquad → aggregator → motor → motion **is** the loop, and the notch cuts its gain at 19.75 Hz. |
| **LKAS authority** | **Not affected either way — and that is good news.** openpilot's command never passes through this filter, so **no notch dose can reduce how hard it steers.** The authority objection does not apply to this lever. |
| **Peak command oscillation** | **Not directly.** The command does not pass through the filter. It may still fall if it *tracks* the grind, which the record says it does — but that is an indirect claim, and this build is not evidence for it. |
| **Ratcheting** | Not by the notch. That is the inertia half-dose at `0xD7A5C`, carried on all three builds. |
