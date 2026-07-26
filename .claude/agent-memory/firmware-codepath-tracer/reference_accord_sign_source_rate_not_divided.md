---
name: reference-accord-sign-source-rate-not-divided
description: "CORRECTED SCOPE (2026-07-21): FUN_00041464 (sign filter) is CONFIRMED 1kHz -- single caller in the confirmed-1kHz task FUN_0002214a, undivided, three independent ways. FUN_00034350 (damping magnitude) is only proven undivided WITHIN its host task FUN_00022ca0 -- that host task's own per-invocation rate is NOT independently proven, only strongly indicated ~1kHz by coefficient plausibility. Do not cite both functions as equally 'confirmed 1kHz' -- an earlier version of this memory's headline over-claimed this and was corrected after team-lead review."
metadata:
  type: reference
---

Traced 2026-07-21, independent cross-check (deliberately not coordinated with trace-36682's TCB-walker
route) on whether `FUN_00041464` (sign filter, produces `gp-0x6abe`) and `FUN_00034350` (damping
magnitude producer) run at the full ~1kHz control rate or are divided down through the newly-found
`FUN_00014be4` sub-scheduler.

## FUN_00014be4 decompiled — it's a self-contained dispatcher, not a gate consumers check [VERIFIED]

```c
void FUN_00014be4(void)
{
  if (99 < gp-0x4304) { gp-0x4304 = 0; }        // free-running 0-99 counter
  FUN_000861e0(0);                                // every call (1-in-1)
  if ((gp-0x4304 & 1) != 0) FUN_000861e0(1);      // odd counts (1-in-2)
  if (gp-0x4304 % 5 == 2) FUN_000861e0(3);        // 1-in-5
  if (gp-0x4304 % 10 == 4) FUN_000861e0(4,10,gp-0x4304/10);   // 1-in-10
  if (gp-0x4304 == 0x10) FUN_000861e0(5);          // one-shot at count 0x10
  gp-0x4304 += 1;
  FUN_000861e6();
}
```
Matches trace-36682's description exactly (100-count wraparound, `FUN_000861e0` sub-rate dispatch). **Key
fact for this check**: `FUN_00014be4` takes **no arguments** and **returns nothing its caller branches
on** — it unconditionally does its own internal dispatch of `FUN_000861e0` (an entirely separate
subsystem) and returns. **It cannot be gating any other function's execution rate** — there is no return
value or output flag for a caller to consume.

## Call-site check — both functions are state-gated only, no FUN_00014be4 in the chain [VERIFIED]

**`FUN_00041464`** (`FUN_0002214a`, `0x221e0-0x22204`):
```
0x221e6-0x221f4: CAXI claim on gp-0x42fc -> if won, call FUN_00014be4 (unconditional fallthrough after)
0x221f8: andi 0xD30,r25,r23   ; r25 = 1<<state (gp-0x67fa)
0x221fc: be [skip]             ; skip FUN_00041464 unless state in {4,5,8,10,11}
0x22200: jarl FUN_00041464
```
The `FUN_00014be4` call and the `FUN_00041464` call are **two independent, sequential pieces of code** —
the state check at `0x221f8` does not depend on anything `FUN_00014be4` did, and `FUN_00014be4`'s call is
itself gated by an unrelated CAXI mutex-claim (ensuring only one of the two cooperating tasks services it
per outer pass, not a rate divider). **No path from `FUN_00014be4` to `FUN_00041464`'s execution exists.**

**`FUN_00034350`** (`FUN_00022ca0`, `0x23252-0x23276`):
```
0x22db2 (earlier in the function): r28 = r25 & 0x830    ; states {4,5,11}
0x23252: cmp r0,r28 ; be 0x2326e     ; skip the CAXI+FUN_00014be4 block if r28==0
0x2325c-0x2326a: [same CAXI-claim + FUN_00014be4 call pattern as above]
0x2326e: cmp r0,r28 ; be 0x2327a     ; skip FUN_00034350 if r28==0 (SAME r28, re-checked, not consumed
                                        from FUN_00014be4 in any way)
0x23272-0x23276: mov 0x11,r0,r6 ; jarl FUN_00034350
```
Same structure: the state-gate (`r28`, states `{4,5,11}`) independently controls both the
`FUN_00014be4` housekeeping call and the `FUN_00034350` call — they are parallel, not chained.
**`FUN_00034350` is not divided through `FUN_00014be4` either.**

**Conclusion: both functions run at the FULL rate of their HOST TASK whenever the ECU is in a qualifying
operating state — no 1-in-N sub-rate divider sits between either function and its host task.** This is
as far as this check alone can take either function — the remaining question is each host task's own
per-invocation rate, and **the two functions do NOT share the same answer to that question**:

- `FUN_00041464`'s host task is `FUN_0002214a`, which IS independently established at ~1kHz
  ([[reference-accord-steerstatus4-dwell-constant-D]], a control-path telemetry-tied cycle count, plus
  [[reference-accord-ostm0-master-tick-rate-derivation]]). **So `FUN_00041464` is CONFIRMED ~1kHz.**
- `FUN_00034350`'s host task is `FUN_00022ca0` — a DIFFERENT task. Neither of the two rate-derivation
  routes above measured `FUN_00022ca0` directly (the D=100 dwell counter lives in `FUN_0002214a`'s
  arbitration body; the OSTM0 route establishes only the shared hardware timer, not which task services
  which interrupt at what sub-rate). A separate tracer independently confirmed `FUN_00022ca0` has no
  self-tick-counter comparable to `gp-0x3e54` to diff against. **`FUN_00034350`'s host-task rate is NOT
  independently proven from this check — only the "no divider within the task" half is.**

## Cross-check via the filter coefficient — independent evidence for 1kHz [VERIFIED arithmetic]

`alpha = 37/128 = 0.2891` (`0xC643C`, byte-confirmed earlier this session). Exact discrete-to-continuous
corner frequency `fc = -fs * ln(1-alpha) / (2*pi)`:

| candidate `fs` | -3dB corner | time constant |
|---|---|---|
| 10 Hz | 0.543 Hz | 293 ms |
| 100 Hz | 5.43 Hz | 29.3 ms |
| **1000 Hz** | **54.3 Hz** | **2.93 ms** |

A **54Hz corner is a textbook-sensible design point for a motor-resolver-rate noise filter** — fast
enough to pass real mechanical/electrical dynamics, slow enough to reject switching/quantization noise.
A 5.4Hz corner (100Hz candidate) would make this an unusually sluggish filter for a real-time rate
feedback/damping signal (nearly 30ms time constant against dynamics that matter at tens of Hz). A 0.54Hz
corner (10Hz candidate) is not physically sensible for a spinning motor's rate signal at all — it would
reject virtually all real dynamics, leaving only a near-DC average. **This independently favors the
1kHz hypothesis**, consistent with (not derived from) the call-site finding above.

## Verdict [scope corrected 2026-07-21 after team-lead review]

**Sign source `FUN_00041464`: CONFIRMED ~1kHz, undivided — the damper stays net-damping at 21Hz** (per
the already-established `-21.8°` / `cos≈0.93` phase figure at this rate). Three independent lines agree:
direct call-site tracing (no divider in the path), filter-coefficient plausibility (54Hz corner is the
only physically sensible one of the three candidates), and its host task `FUN_0002214a` being
independently confirmed 1kHz by the D=100 dwell-counter route. This is solid.

**Damping magnitude producer `FUN_00034350`: runs undivided within its host task `FUN_00022ca0`, but
that host task's OWN per-invocation rate is strongly indicated ~1kHz, NOT proven.** No
`FUN_00014be4`-mediated division was found for either function — that half of the check is equally solid
for both. What differs is which task each one lives in, and only one of those two tasks has an
independent rate measurement. Do not read this memory's earlier "both run at ~1kHz" framing as a closed
fact for `FUN_00034350` — it should read "no in-task divider found; host task rate strongly indicated,
not proven."

## Related
[[reference-accord-steerstatus4-dwell-constant-D]] — the D=100 control-task-rate finding this confirms
[[reference-accord-fun41464-sign-filter-phase-response]] — the phase analysis this rate applies to
[[reference-accord-gp67ac-aggregator-lane-suppression-gate]] — the LKAS mixer FUN_00026c80, unrelated to this dispatcher

## Addendum 2026-07-21 — boost lane EMA (0xC6372) corner-frequency plausibility, for FUN_00022ca0's OWN rate

Team-lead asked for one more coefficient-plausibility data point, this time for a function firmly inside
`FUN_00022ca0`'s tree (not `FUN_0002214a`, already confirmed 1kHz) as an independent read on the
still-open `FUN_00022ca0` execution rate.

**Cal `0xC6372` = 205** [VERIFIED, byte read]. Sole reader [VERIFIED, exhaustive `search_instructions`,
186,069 instructions, 1 hit]: `FUN_00034a72` (the boost curve, called from `FUN_00022ca0`), at
`0x34ade: ld.hu 0x7372,tp,r16`, feeding the exact same EMA idiom documented earlier this session:
`state = state + ((target - state) * 205) >> 10`, i.e. `alpha = 205/1024 = 0.2002`.

Corner frequency `fc = -fs*ln(1-alpha)/(2*pi)`:

| candidate `fs` | -3dB corner | time constant |
|---|---|---|
| 100 Hz | 3.56 Hz | 44.8 ms |
| 500 Hz | 17.8 Hz | 8.95 ms |
| 1000 Hz | 35.6 Hz | 4.48 ms |

**My read: this one does NOT disambiguate as cleanly as the sign filter's coefficient did — I'm reporting
all three rather than picking one with false confidence.** Unlike a motor-rate safety filter (where a
sub-Hz corner is obviously wrong), a driver-torque ASSIST smoothing filter has a plausible design range
spanning roughly this whole table:
- **100Hz's 3.56Hz corner** is the cleanest fit for a *smoothing* design intent — human hand-torque input
  bandwidth is generally well under ~10Hz (voluntary motor control, with physiological tremor topping out
  around 8-12Hz), and a ~3.5Hz corner is a textbook choice for rejecting road-noise/vibration content
  from a torque-sensor input feeding a boost curve — arguably the MORE natural design goal here, since a
  twitchy/noisy assist curve is exactly the kind of felt artifact this whole investigation is chasing.
- **1000Hz's 35.6Hz corner** is wide enough to pass nearly all plausible human-torque content
  essentially unfiltered — defensible only if this stage is meant as a near-transparent anti-alias
  pre-filter with the REAL smoothing done downstream (this function does have its own separate output
  rate-limiter later in the chain, `ASSIST_RATE_STEP`, established in an earlier session), but that's a
  different design philosophy than "this EMA is the smoothing stage," and I can't confirm which was
  intended from the coefficient alone.
- 500Hz sits in between, plausible either way.

**[INFERRED, moderate confidence, not a proof]: 100Hz reads as the more natural single answer for THIS
specific filter's likely purpose, but I would not treat this coefficient alone as settling
`FUN_00022ca0`'s rate the way the sign filter's 0.54Hz-vs-54Hz gap settled `FUN_0002214a`'s.** If
`FUN_00022ca0` does run at 100Hz while `FUN_0002214a` is confirmed 1kHz, that's architecturally
unremarkable (a fast motor-control loop plus a slower driver-input-processing loop is a common RTOS
pattern) and wouldn't contradict anything established so far — it would just mean the two tasks run at
different rates, which is worth stating plainly rather than assuming they match.

### Suggestive (not proof-grade) same-rate corroboration, added per team-lead 2026-07-21

Comparing this filter's corner against the sign filter's CONFIRMED corner (54.3Hz at the proven 1kHz
rate of `FUN_0002214a`, a related assist/rate filter one hop away in the same aggregator's input tree):
if the two tasks share a clock regime, `FUN_00022ca0` at 1kHz puts the boost filter's corner at 35.6Hz —
the same ballpark as its confirmed 54Hz sibling (within ~1.5x). `FUN_00022ca0` at 100Hz would put it at
3.56Hz — roughly **15x slower** than the confirmed sign filter, which would be an unusual design
mismatch between two torque/rate filters feeding the same aggregator if they were meant to behave
similarly. **This is suggestive of same-rate (favoring 1kHz for `FUN_00022ca0`), not proof** — two
filters in the same firmware are allowed to be tuned very differently on purpose (one is a safety-
relevant motor-rate signal, the other a comfort-oriented driver-torque smoother, and this memory's own
reasoning above argued FOR a slower corner on the latter for exactly that reason). Flagging the tension
explicitly rather than picking a side: the "physically plausible for an assist filter" argument (above)
points toward 100Hz; the "matches its confirmed sibling's ballpark" argument points toward 1kHz. Neither
resolves `FUN_00022ca0`'s rate on its own.
