---
name: accord-v288-null-is-void-filter-was-transparent-at-the-ring
description: "🛑🛑⭐⭐⭐⭐⭐ V288 rev 2's null is VOID -- its cave is amplitude-dependent and passed the ring at gain 0.95-0.99, attenuating the grinding band by 1-5%, not 54%. The command path was never tested. 'The reference-side class is EXHAUSTED' does not hold."
metadata:
  node_type: memory
  type: project
---

🛑🛑 **V288 rev 2 NEVER TESTED THE COMMAND PATH IN THE RING BAND. Its null is VOID, and every
conclusion built on it falls with it.** Established 2026-09-10, verified by the orchestrator's own
arithmetic, not relayed.

## The mechanism

V288's setpoint pre-filter cave (`0xC4C00–0xC4C2C`, hook `0x29D72`) is **not LTI**. Its whole body is:

```python
delta = sp - y_prev
step  = delta >> 4              # integer floor -- K=4, nominal corner 10.27 Hz
if step == 0 and delta != 0:
    step = 1                    # ANTI-STICK -- this is what breaks linearity
y_new = y_prev + step
```

The anti-stick branch fires for every `0 < delta < 16`, so **small signals are followed at full rate**
and the filter is transparent to them. Measured fundamental gain at 20.3 Hz
(`docs/review/ADV-V288-A-ARITHMETIC-2026-09-07.md` lines 285–287, 459–461):

| setpoint amplitude A | gain @ 20.3 Hz |
|---|---|
| 4 | **0.99** |
| 8 | **0.95** |
| 16 | 0.61 |
| ≥ 40 | 0.45 |

## The arithmetic that voids it

```
measured 20 Hz command line      = 15–40 raw 0xE4 counts   [STATE.md, demand-gated census]
÷ idx LSB 16.125736 raw/idx      = 0.93 – 2.48 idx
× 6× map slope 4.30 sp/idx       = 4.0 – 10.7 sp counts    ← THE RING, in the filter's own units
a slew-capped frame (123 raw)    = 32.8 sp counts          ← where the filter DOES work
```

⇒ **V288 passed the ring at gain 0.95–0.99 — it removed 1–5 % of the grinding band, not 54 %.**
Its genuine ×0.03 D-clamp-bind result is the A ≈ 33 regime. **It attenuated large steps and was
invisible to the ring.** [EVIDENCE]

## What falls with it

- 🛑 **"The reference-side class is EXHAUSTED" does not hold.** The command path is **untested** in the
  ring band. This verdict drove V289, the whole V290 design round, and the "the lever is in-loop
  damping" framing.
- The V288 flight record's "grinding unchanged" is **silent**, not negative.
- Any argument of the form "we already made the setpoint steps 11× finer and nothing happened" — the
  11× applies to large steps only.

## The process failure, and it is the transferable part

⭐ **The caveat was written down THREE DAYS BEFORE V288 FLEW** — ADV-V288-A said in terms *"below ~8
counts the filter is essentially transparent"* — **and nobody applied it when reading the drive.** The
adversarial pass did its job; the reading of the result did not.

**A null from a filter that was transparent at the amplitude of interest is not a null**, exactly as
*a null from the wrong image is not a null*. ⇒ **Before reading any null, convert the SYMPTOM into the
lever's own units and check the lever was actually active there.** An integer IIR with a `>>k` floor is
the standard offender: to be non-transparent at small amplitudes it needs a **fractional accumulator /
error-feedback remainder word**, as V289's notch cave used to hold DC at exactly 1.

Surfaced by the `fwpath` subagent correcting **its own** headline claim after re-deriving it.

Related: [[accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted]] (**now superseded — read
this note first**) · [[accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed]] ·
[[accord-kp-kd-schedule-x-axis-is-demand-index-16-125736-per-lsb]] ·
[[feedback-a-check-that-condemns-the-flown-build-is-broken]]
