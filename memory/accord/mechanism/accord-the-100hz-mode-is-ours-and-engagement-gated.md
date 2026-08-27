---
name: accord-the-100hz-mode-is-ours-and-engagement-gated
description: The operator's reported ~100 Hz and ~200 Hz low-speed grinding modes are measurable in the audio third-octave bands and are OURS - engaged adds +1.3 to +5.6 dB at 100 Hz below 10 mph on every gain-modified build and -0.03 dB on STOCK. But unlike the 6-9 and 20-26 Hz bands they are NOT clearly command-gated, so they are probably a separate mechanism.
metadata:
  node_type: memory
  type: reference
---

# THE ~100 Hz MODE IS **OURS**, ENGAGEMENT-GATED — BUT **NOT** COMMAND-GATED

★★★★ **EVIDENCE for the engagement contrast; the command result is a weak null.** 2026-08-27.
The operator on V108: *"low speed below ten miles an hour, grinding is still there… it seems like
it's made up of two modes. One… maybe around a hundred hertz. And there's another which seems like
it's around a hundred or two hundred hertz."*

## 🛑 NO CAN CHANNEL CAN SEE THESE MODES
Steering angle samples at 100 Hz (**Nyquist 50 Hz**) and CAN-427 at 49.8 Hz (**Nyquist 24.9 Hz**).
**Both of the operator's reported modes are above every CAN Nyquist on this car.** ⇒ **audio is the
only instrument that can observe them**, and six routes carry third-octave audio (`tob`, 20 bands,
100 Hz–8 kHz) alongside the CAN caches.

## ✅ THE RESULT — AND STOCK IS A BUILT-IN CONTROL THAT PASSES
Within-drive engaged-minus-manual, **matched speed**, below 10 mph. ⚠ Within-drive only: the cabin's
acoustic gain differs **3–12× between drives**, so cross-drive dB is structurally uncomputable and
the parked reference clip (drive-card manoeuvre 0) has never been collected.
```
  route  build        gain   100 Hz    200 Hz     n eng / n man
  r97    V9b-STOCK      1x   -0.03 dB  +0.53 dB   4425 / 3993   <- THE CONTROL
  r96    V102           6x   +1.30     +1.65      4420 / 3305
  ra4    V104           6x   +2.47     +1.85      7254 / 3436
  r85    V100           4x   +3.05     +1.41      1811 / 2222
  r9e    V103           6x   +4.90     +3.70      4325 / 2378
  r95    V101           8x   +5.62     +3.28      3196 / 1380
```
⭐ **STOCK shows NO engaged excess at 100 Hz. Every gain-modified build shows +1.3 to +5.6 dB.**
⇒ **The mode the operator hears at low speed is OURS, not Honda's** — the same conclusion the kit
reached for the 6–9 Hz band by a completely different route
([[accord-the-antidamping-is-hondas]] is the contrast: that one IS Honda's).
⊕ Ordering by gain is suggestive but not clean: 1× −0.03 · 4× +3.05 · 6× {+1.30,+2.47,+4.90} ·
8× +5.62. **Stock separates clearly; 4/6/8 overlap.** n = 1 route for stock and for 8×.

## ⚠ BUT IT IS **NOT** COMMAND-GATED — and that separates it from the ratchet
Same audio, engaged only, <15 mph, hands-off, dB against **that drive's own** `<512`-command median
(so acoustic gain cancels inside each drive):
```
  route   0.5-1k        1-2k          2-3k          3k+        (dB at 100 Hz)
  r85      +1.2          +2.1          -0.5          +0.9
  r95      +0.8          +3.0          +2.5          +0.1
  r96      +1.7          +0.7          +6.0          +4.3
  r97      -2.0          -0.1          +1.7          -0.8      <- STOCK, scattered the same way
  r9e      +0.5          +2.1          +3.0          +1.8
  ra4      +0.4          +0.2          +1.0          +0.6
```
**No monotone rise, no consistency across routes, and stock scatters like the rest.** Contrast the
steering-rate bands, where 6–9 Hz rises **3.0× → 4.7× → 52×** with command while two control bands
FALL ([[accord-ratchet-and-grind-are-command-gated-saturation]]).
⇒ 🛑 **[BELIEF] the ~100 Hz mode is a DIFFERENT mechanism from the 7.8 Hz ratchet and the 20–26 Hz
grind.** It is engagement-gated; they are command-gated. **Do not assume one fix covers both.**

## WHAT THIS MEANS FOR THE HUNT
- The operator's low-speed complaint is **at least two separate things**: a command-gated pair at
  7.8 / 20–26 Hz, and an engagement-gated mode near 100 Hz that no CAN channel can see.
- **V109's α2 cut targets 61–300 Hz** ([[accord-c40dc-is-the-band-limit-lever]]: −34 % at 100 Hz,
  −39 % at 200 Hz) — ⭐ **which is aimed squarely at this mode, and at nothing else the kit has
  measured.** That makes V109 the right next build for a reason independent of why it was designed.
- Any future audio work needs **drive-card manoeuvre 0** (30 parked seconds, engine on, HVAC off):
  it makes every acoustic number comparable across drives retroactively, and without it the
  between-build question stays uncomputable.

## ⚠ LIMITS
- **n = 1 route for stock and 1 for 8×.** The stock control is a single drive.
- The 100 Hz third-octave spans roughly **89–112 Hz**; the operator's "a hundred or two hundred" is
  not resolved more finely than that.
- Engaged and manual segments within a drive are matched on **speed only** — not on road surface,
  steering effort or what the driver was doing.
- ⚠ `r97`'s build tag is `V9b-STOCK` from its own cache; it is treated as the 1× baseline on that
  basis and on `0xC6CD0` = 891 in the stock image. **Not independently re-verified this session.**

Related: [[accord-c40dc-is-the-band-limit-lever]] · [[accord-the-8x-gain-is-the-carrier]] ·
[[accord-ratchet-and-grind-are-command-gated-saturation]]
