# THE SHELF — what is built, what to flash, what it changes

**Updated 2026-08-29.** Two flashable builds. Everything else from this arc is renamed
`SUPERSEDED-DO-NOT-FLASH-GATE2-…` and must not be sent.

🛑 **Nothing here has been flashed and no CAN or UDS message has been sent.** Flashing requires you to
name the file and the bus, and they will be read back to you first.

---

## ⭐ V199 — THE FIX. Flash this one.

```
39990-TVA,A160-V199-V196BASE-NOTCH.POLES.BELOW.ZEROS-0x13000-0x100000.rwd
  image c86646ab48c4a62546b4e7bafa59f8097d3bdd99ffdcd3aeabd9f93c7252dc10
  rwd   8df71f5db9f51e3cccf2d14c27aa580869434125112271115cfaddeddface708
```

A notch on the grind at **19.75 Hz**, plus the engaged inertia half-dose, built so the filter **cannot
add loop gain at any frequency**.

## V200 — the same car, plus one measurement

```
39990-TVA,A160-V200-V199BASE-PROBE-THE-R24-RATE-LANE-0x13000-0x100000.rwd
  image db0b613aad11e67822528251b66790386635a59e9584e87d352bf294d5bf460e
  rwd   95cf26bd43cb7352a24133536c509468f5f8247aa859de1cfb31529c1c26cfc9
```

Byte-identical control cells to V199. It adds **2 payload bytes** so CAN 427 carries `gp-0x6ada`, the
**r24 rate lane** — the biggest 8 Hz exciter (8192 clamp, 8× the inertia term V199 halves). Flash this
instead of V199 if you are willing to trade nothing at all for an answer to *"is the ratchet lever even
aimed at the dominant term?"*

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

## WHAT V199 CHANGES vs V122 — 11 cells, 30 payload bytes

| addr | V122 → V199 | what it physically is | introduced |
|---|---|---|---|
| `0xC60A8` | `−1.5372` → `−1.9233811` | biquad pole angle → **17.45 Hz** | V199 |
| `0xC60AC` | `0.63462` → `0.9360563` | biquad pole radius → **0.9675** | V199 |
| `0xC60B0` | `−1.8808` → `−1.9846207` | **the notch centre, 55.23 → 19.75 Hz** | V195, kept |
| `0xC60B4` | `0.81731` → `0.8241721` | overall gain — forced by unity DC | V199 |
| `0xC40D2` | 1020 → **102** | K1, modelled Coulomb friction → **Honda** | V177 |
| `0xC40DC` | 8 → **22** | acceleration EMA alpha → **Honda** | V179 |
| `0xC63A6` | 1024 → **512** | w[3], the inertia term's weight, halved | V181 |
| `0xD7A5C` | (−29490,−17202,−16000) → **(−4915,−2867,−983)** | **engaged** inertia curve, **half Honda** | V196, kept |
| `0xD7A6C` | (−29490,−17202,−16000) → (−9830,−5734,−1966) | m27 inertia curve → **Honda** | V175 |
| `0x55DF2` | −27324 → −27328 | CAN 427 probe source → `gp-0x6ac0` | V183 |
| `0x55E10` | 12963 → 12964 | the probe's pack shift, `sar 4` | V183 |

**Measured on-car:** none of the four biquad cells — this filter geometry has never flown.
**Reverts to Honda:** `0xC40D2`, `0xC40DC`, `0xD7A6C`.
**Unverified doses:** `0xC63A6`, `0xD7A5C` (the inertia sign has not been confirmed on-car).
**The cave is byte-identical** to V196 — no code-cave change, so this is not the bricking class.

🛑 **Manual driving is unaffected by the biquad either way.** The section is engagement-gated by V103's
three-site patch on `gp-0x6806`, so every notch cell is inert with LKAS off.

---

## BEFORE YOU FLASH

```
python flashing-2020accord/preflight.py "<the .rwd filename>"     # V199 passes 8/8
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
python rlog-tools/probe/decode_v198_r24_lane.py <tag> --v198     # V200 only
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
| 15–25 Hz excess on `cs_rate` | **31.6× → ~3.1×** (10.1× attenuation) | the grind is not in the assist section's path |
| 6–9 Hz excess on `cs_tq` | unchanged | the notch was never aimed there |
| LKAS command 0.5–3 Hz | unchanged, ±10 % | if it moves, the notch is eating command authority |
| `gp-0x6ada` 8 Hz content (V200) | if ≫ the inertia term, V199's ratchet lever is aimed at a minor exciter | the rate lanes are where a bigger lever belongs |
