# PROBE SPEC — a zero-crossing rate counter, to break the aliasing tie

**Status: SPEC ONLY. Not built, not scheduled. V217 is the flight candidate and this must not churn it.**
Written 2026-08-29.

---

## The problem it exists to solve

Every rlog cache in this kit samples at **fs = 101.01–101.26 Hz**. Nyquist is **~50.5 Hz**. Therefore
**anything real in 52–71 Hz folds into the 30–49 Hz band the kit scores** — a real 71 Hz line lands on
30 Hz, indistinguishable from a real 30 Hz line.

This is not hypothetical. It bears directly on the single largest signal in the corpus: r7d's ~31 Hz
line, 63× background in `cs_rate`, engagement-gated, present in the firmware's own `probe` byte, and
**absent from the LKAS command**. That line is either a ~30 Hz closed-loop mode or a ~71 Hz one, and
**no amount of further analysis on the existing caches can tell them apart**:

- the fold source (52–71 Hz) sits **entirely above Nyquist**, so it can be neither observed nor
  filtered out after the fact;
- no channel escapes it — `probe`, `raw14` and `raw18` all ride the same 101 Hz frame rate, and the
  ~50 Hz channels (`raw1ab`, `ws`) fold 30 Hz and 70 Hz onto the **same** ~20 Hz;
- the spread in fs across routes is 0.25 Hz, far too small to separate the alias by its shift.

The distinction matters for what gets built. A ~30 Hz mode is in the band the notch and the assist
biquad can shape. A ~71 Hz mode is above everything the cal surface reaches and would mean the kit has
been scoring a mechanical or FOC-side phenomenon as if it were a control-loop one.

## The instrument

**Count zero crossings inside the 1000 Hz control task; report the count on the 100 Hz CAN frame.**
The count accumulates at the task rate, so it measures the *true* crossing rate of the internal signal
**regardless of the transmit rate**. Aliasing is impossible by construction — there is no sampling of
the waveform to fold.

```
  per control tick (1000 Hz), on the internal signal S:
      if sign(S) != sign(S_prev):  ctr += 1
      S_prev = S
  every 4th CAN frame boundary (40 ms):
      field = min(ctr, 15)          # 4 bits
      ctr   = 0
```

A 40 ms accumulation window rather than a 10 ms one buys resolution without over-ranging:

| true tone | crossings/s | count per 40 ms window |
|---|---|---|
| 7.8 Hz — the established ratchet | 15.6 | **0.62** |
| 21 Hz — the known engaged mode | 42 | **1.68** |
| 30 Hz | 60 | **2.40** |
| **71 Hz — the alias hypothesis** | 142 | **5.68** |
| 187 Hz | 374 | 15 — the 4-bit ceiling |

⇒ **the three live hypotheses are 2.4 vs 5.7 vs 0.6 — separated by more than 2× each, on a channel
whose ceiling is 187 Hz.** Not under-ranged, not over-ranged, and the ceiling is stated rather than
guessed. Pair the counter with the **raw sign bit** at full frame rate, giving the sign/magnitude
pairing the design law requires: **4 bits counter + 1 sign bit = 5 bits**, which is exactly the free
channel this kit already owns (`0x14A` byte 4, bits 7:3 — see `accord-can-tx-gateway-whitelist-and-20-free-bits`).

## Why this satisfies the design law

The law, from all 45 probe builds V53→V97: *every probe that DECIDED something was a sign bit paired
with a magnitude channel, or a deliberately-designed control; every uninterpretable null was a single
threshold rung on a quantity with no measured distribution and no positive control.*

- **It is not a threshold rung.** It reports a count, and the count's mapping to frequency is exact.
- **It is scale-free.** Like a comparator, it never quantises an amplitude, so it cannot be
  under- or over-ranged by a wrong guess about the signal's size. The one scale assumption it does
  make — where zero is — is the one quantity in this chain that is known exactly.
- **Its positive control is free and already established.** The ~7.8 Hz ratchet must read ~0.62
  counts/window during a ratchet episode. If it does not, the instrument is wrong and the drive is
  still interpretable — as an instrument failure, named, rather than an uninterpretable null.
- **It reads out within the symptom**, from one short engaged episode. No matched pair, no
  cross-build contrast, no minutes of exposure.

## Pre-registered readout

Mean count per 40 ms window over engaged frames, during a symptomatic episode:

| observed | conclusion |
|---|---|
| **~0.6** | the dominant internal content is the ratchet band; the 30–49 Hz scoring band is picking up something not dominant in this signal |
| **~2.4** | the line is genuinely ~30 Hz — in the band the notch and the assist biquad reach, and the loop-gain reading of r7d stands |
| **~5.7** | **the line is ~71 Hz and every 30–49 Hz claim in this kit is an alias.** Re-open the 30–49 Hz control band, `SCORING-V217-preregistered.md`, and the r7d study |
| ceiling 15, sustained | something is chattering above ~187 Hz — an FOC/PWM-side effect, not a steering-loop one |

Anything between two rows is **UNRESOLVED and must be reported as such**, not rounded to the nearest
hypothesis.

## What it costs and what it risks

⚠ **This is a code cave, and caves are this kit's only bricking class** (V24, V27, V48B). It is not a
cal edit. It must clear **GATE 1 RAM ownership** (the counter and `S_prev` need two owned scratch
cells, with writers and register-indirect access checked — static clearance is not sufficient, as
`gp-0x1500` proved) and **GATE 2 closed-loop stability** is trivially satisfied only if the rung is
genuinely read-only on the control path, which must be shown rather than assumed.

The cheaper predecessor exists: V87's flown cave already reads `gp-0x6b98` and its structure is
proven. This rung is an increment and a compare bolted onto that pattern, plus one extra scratch cell
for `S_prev`. **Prefer extending the proven cave over cutting a new one.**

## Where it sits in the queue

**Behind V217.** V217 is a cal-only build whose whole purpose is restoring a damper the shelf was
cutting; adding a cave to it would confound the one thing it is meant to settle and would move it out
of the safest build class. This spec is what to build **after** V217 flies, if the 30–49 Hz band is
still load-bearing at that point.

Related: `analysis-2020accord/studies/mixer/r7d_31hz_what_it_is_and_isnt.py`.
