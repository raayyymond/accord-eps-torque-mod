# STATE — living current state of the kit

**Last updated: 2026-08-06 (V74 flight + V75 build).** This file is the single current-state record.
Update it in place at every close-out; do not append new dated blocks (that is what made `CLAUDE.md`
unreadable). The narrative of how each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` — 🛑 **start with `RULE 3` at the top of that file: a
"CONFIRMED" result is about a LEVER, not about the car you are driving. Byte-check the current image
before reasoning from any recorded result.** 🛑 **Then `RULE 6` — a lever is only in force if the car
reads the TABLE you edited.** Then the latest handoff,
`docs/HANDOFF-2026-08-05-v72-flew-the-damper-was-never-in-force.md` (spec: `docs/V73-DESIGN.md`),
then `docs/HANDOFF-2026-08-04-both-confirmed-fixes-were-off-the-car.md`
(predecessors: `HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md`, then
`HANDOFF-2026-08-04-v69-recut-4x-and-ratchet-probe.md`, then
`HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md`, then
`HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`, then `HANDOFF-2026-08-03-the-detector-was-always-there.md`, then
`HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md`, then
`HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md`, then
`HANDOFF-2026-08-01-v62-flew-and-the-grinding-is-fixed.md`, then
`HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md`, then
`HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md`, then
`HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md`, then
`HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`).

---

★★★★★ **THE HEADLINE, 2026-08-07 (LATEST, late): THE HARD-FAULT MECHANISM IS FOUND. IT IS THE **FRICTION**
LANE CROSSING A FLAT 512-COUNT MONITOR CEILING — AN INTERLOCK V73 REMOVED WITHOUT KNOWING IT WAS ONE.
**V76 IS BUILT ON A V38 BASE AND CLOSES IT BY CONSTRUCTION.** NOT FLASHED.**

`FUN_00036d74` — called **UNCONDITIONALLY** from the 1 kHz task `FUN_0002214a` @`0x2290a` (`get_xrefs_to`
returns exactly that one call) — tests `|gp-0x6b26| / 1024 > cal(tp+0x5004 = 0xC4004)`, where `0xC4004`
= float **0.5 = 512 raw counts** (bytes `0000003f`, byte-identical in every image), and faults straight to
DTC `0x1d`. 🛑 **Flat, symmetric, unconditional — no re-sampled comparator, no race, no timing escape.**

| build | ceiling | clamp `0xC407E` | relationship | on-car |
|---|---|---|---|---|
| stock / V38 / V72 | 512 | **511** | **1 count UNDER — structurally untrippable** | clean, always |
| **V73** | 512 | **850** | **338 counts OVER** | clean (needed a big event) |
| **V74 / V75** | 512 | 850 | 338 over + friction m26 **×1.5** (`0xD7A54`) | **BOTH HARD-FAULTED** |

★★ **Honda set the clamp exactly one count below the monitor's own trip threshold — an interlock.**
V73 raised it to 850; V74's ×1.5 friction then dropped the `gp-0x6c2c` needed to cross from ≈6258 to
≈4180. **Mode-proof ⇒ live in MANUAL — the only candidate that explains V74 faulting disengaged.**
Explains the single-frame latch (threshold-0 dwell) and the exact build history. **It was never the damper.**
✅ **FIX = `0xC407E` → 511**, one cell, loosens no monitor — **a V38 base gets it free.**
🛑 **RULE 11** added to `BUILD-LINEAGE.md`: *a clamp may be an interlock — never raise one without finding
its monitor.* **`0xC407E` is a DO-NOT-RAISE cell.**
⚠ OPEN: `gp-0x6c2c`'s physical scale undetermined ⇒ mechanism **[EVIDENCE]**, "it caused both faults"
strong **[BELIEF]**.

## ✅ BUILT, VERIFIED, **UNFLASHED** — V76 on a V38 base
`39990-TVA,A160-V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd-0x13000-0x100000.rwd`
rwd `1fba57b243534538a7d533436387a98c673bf038dc579f9a3c6796d4c6030c89` ·
image `_v76_v38base_relu_damper_plain_image.bin` `54a212a269623ef3d674fe7711eefdf7db32ebc3f25bf3e20c7bc5a14c830f33`
Base `_v38_plain_image.bin` `a7391972…afa8`. **V38→V76 = 8 runs / 91 bytes**, all attributed; **CRC 50/50 PASS**.
Damper, mode 26 only (mode 24 byte-stock): **FactorC `Y=[566,566,566,908]`** (flat/ReLU) ·
**FactorE `X=[0,119,2500,4000] Y=[0,300,539,927]`** (plateau removed). `k`=1.3866.
**Dose 137 flat 0–80 km/h** = V75's creep peak, **2.45× V75 at 60 km/h**, at **12% lower loop gain than the
build that faulted**. **Grind #2: 0.57× / 0.61× / 0.76× vs V75** at 42/85/255 °/s.
Probe (64 B of 68): **bit7 `|gp-0x6b26| > 448`** (live band 449–511 — margin on the fault lane) ·
**bit4 `gp+0x63fd & 2`** (mode index, closes the mode-lag question) · **bit3 `gp-0x67fa == 5`** (positive
control). Bits 6/5 constant 0 — **must not be read as a measurement.**
🛑 **NOT CLEARED TO FLY.** Residual risk: **3.10× V74's time-weighted `k` across 47.3% of engaged driving**
(286.4 s at 35–80 km/h, clean evidence only at the lower gain). Driven by dose, not by flatness.
🛑 **V76B / 8× LKAS NOT BUILT** — never built, no on-car data, GATE 2 unquantified (~21 ms to full torque
inside a 100 ms `steerActuatorDelay`), and on a V38 base it needs V57's decouple carried forward
(`0xC6CD0` reads `0xFFFF`). Fly V76 first; one variable at a time.

Full narrative: `docs/HANDOFF-2026-08-07-v76-v38base-and-the-friction-ceiling.md`.

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-07 (earlier): THE V74 BUMP-FAULT RLOGS ARRIVED. THE DAMPER EDITS *WERE* IN
FORCE, AND THE VARIABLE THAT UNIFIES BOTH HARD FAULTS IS ANGLE-RATE **SLEW**, NOT DOSE.**
🛑 **The "damper edits were in force" refutation and the mode-lag finding STAND.** The *slew* framing is
**superseded** — the trip is a flat magnitude ceiling on the **friction** lane, not a rate limit on the
damper. `|d(angle rate)/dt|` remains the empirical correlate (route max on both faults, n=1 each) but is
**not** the mechanism.

Route `75604b0a432fdc89_00000061--3b8f2f9278`, segs 0–12, 75,901 frames / 760.7 s. **Fault pinned to
t = 732.3872 s, seg 12** — `gp-0x67fa` **5 → 8**, `0x1AB` DTC-active 0→1, all three `0x14A` angle fields
→ `0x7FFF`, STEER_SENSOR_STATUS 7→4, bus STEER_STATUS 0→7, **all in ONE 100 Hz transmission**. Exactly
**one** state transition in the whole route; state 8 never exits. `0x14A` holds **99.97 Hz** for the
28.3 s tail ⇒ **authority/motor-off latch, not a reset.** Same class as V75's fault.

🛑🛑 **[EVIDENCE] "THE FACTOR C/E EDITS WERE NOT IN FORCE" IS REFUTED — AND WITH IT, `k*` IS NOT VOID.**
The byte facts stand (mode 24 *is* byte-stock); the **inference** from them was wrong. "Disengaged" was
taken from the operator's verbal report and silently equated with "mode 24". The car says otherwise:
`bit7` (`gp-0x6bd0 != 0`) = **1 at the fault frame** and continuously for **560 ms** before, at
**33.29 km/h** — *below* stock mode-24 FactorC `X[0]` = 2240 ct = 35.00 km/h, where the evaluator
**hard-clamps to `Y[0]` = 0** (disasm `0x3451e`→`0x34522`) and the factor chain is **purely
multiplicative** — four back-to-back `mulu`+`shr 0xa` at `0x34684`–`0x3469c`, **zero `add`/`or`** ⇒
FactorC = 0 forces the damper to 0, with **no additive rescue path**. openpilot had dropped lateral
control only **2.509 s** earlier. ⇒ **the ECU was still on the ENGAGED column** (mode 26: `C_Y0`=429).
★ **Negative control, replicated on two routes of the same build:** manual `bit7` fires **only** inside
a ~4 s post-disengage tail and is **hard zero beyond it — 0 of 9,286 (route 61) and 0 of 39,794
(route 5d)**, i.e. **49,080 true-manual frames with zero damper activity.** The three manual episodes
that looked like they disagreed agree once ordered by time-since-disengage: the one reading **0.00%**
(and it *crosses* the knee) had **never been engaged at all**.
⚠ **HONEST GAP:** the ~2.5 s hold is empirical; its ROM mechanism is **not** pinned. Mode cell is
**`gp+0x63fd`**; the only real debounce found is `0xC624E` = **40 ms** (~150 ms with ramp-settle), not
2.5 s. The `gp-0x6733 = −1` sentinel (`FUN_000527da`) blocks reselect entirely but its caller is
register-indirect and **unresolved**. The conclusion follows from the arithmetic regardless of *why*
the mode was held.

★★★★ **THE UNIFYING VARIABLE IS SLEW.** One metric, both fault drives, sentinel-free:
| | \|torque\| peak, 100 ms pre | pct | **\|d(angle rate)/dt\|** | pct |
|---|---|---|---|---|
| **V74** (r61) | 3,676 | 99.999 | **5,400 /s** | **route MAX, n=1** |
| **V75** (r5e) | 922 | **86.3** | **6,900 /s** | **route MAX, n=1** |
Magnitude does **not** unify them; slew does — each fault at its drive's single largest value.
**This dissolves V75's "mildest of four launches" paradox.** Corroborated on V74: the bump was **real
but ORDINARY** — IMU (101.03 Hz, vertical axis = **`ax`**) shows −1.494 m/s² at −15 ms, ranking **#84
of 388**, **78.6th pct**, route max **2.94×** larger; and V74 **survived 8 earlier damper-live episodes
above 3,000 counts.** ⇒ **a fast-transient sensitivity, not a dose problem.**
⚠ At the fault the rate was 20–78 ct — inside FactorE's **ramp**, *not* the flat band ⇒ **the V74/V75
bang-bang relay is cleanly ELIMINATED for this fault.**
🛑 **SENTINEL TRAP:** a derivative window touching the fault frame imports the `0x7FFF` spike and
inflates `|d(rate)/dt|` **~300×**. All numbers above use a strict pre-fault prefix with an assertion.

★★★★ **`gp-0x685c` CLOSED, and the fid-28/29 "debounce" is a STRUCTURAL NO-OP.** 4 writers / 1 reader
(the state-8 trap block's leg 2). **fid 28 @`0xB8054` and fid 29 @`0xB8070` are BOTH `0x3D01`** ⇒ both
eligible, both able to set it — **ROM statics cannot discriminate them.** ★ The trip test's threshold
field reads **`0x0000` for both** ⇒ `FUN_00018738` **trips on the FIRST qualifying call**; the only real
debounce is the ~**0.1 s** accumulator inside each monitor (`gp-0x3564` / `gp-0x3550`). **One stage, not
two** — the best structural match yet to the slew result. The `gp-0x6b98 == 0` leg is the **weakest**
(it is a *sum* including an additive driver term, `FUN_00042af8`).

🛑🛑🛑 **V77 IS A NULL EXPERIMENT FOR THIS FAULT CLASS — RESOLVED. DO NOT FLY IT EXPECTING A SAFETY
RESULT.** **ALL THREE** monitor trip surfaces are structurally blind to `0xC63A0`, verified along three
independent lines (see "THE THIRD SURFACE" below for the one that took three attempts to settle).

[EVIDENCE, **orchestrator-verified in Ghidra**, not relayed.] Surfaces **A and B** feed fid 28/29 and
**`0xC63A0` reaches neither**:
| surface | int leg (fid 28) | float leg (fid 29) | compares |
|---|---|---|---|
| **A** damper ceiling-clamp | `FUN_00034350` → `FUN_0004613e(0x4179,…)` | `FUN_000347b8` → `FUN_000462e6(0x417a,…)` | **`gp-0x6bd0` ITSELF**, ±5/1024 |
| **B** comp-envelope (NEW) | `FUN_000456a4` → `FUN_0004613e(0x3c35,…)` | `FUN_00045a20` → `FUN_000462e6(0x3a09,…)` | `gp-0x6acc` vs `gp-0x6ace` |
- `FUN_000347b8`: `fVar5 = (float)(int)*(short *)(gp - 0x6bd0) * 0.0009765625` — reads the damper cell
  **directly by value**, tests against `0x3ba00000` (= 5/1024), reports `0x417a`.
- `FUN_00038148`: `gp-0x6bd0` appears **exactly once**, a read-only summand weighted by `tp+0x73a0`
  (=`0xC63A0`) behind a `|x| ≤ 2048` zeroing gate; the function's **only store is `gp-0x6b70`**.
  **No write to `gp-0x6bd0` exists anywhere in it.**
⇒ **`0xC63A0` is strictly DOWNSTREAM of what the monitors read. Reverting it changes not one bit they
see.** Surface B is a parallel pipeline (`FUN_000456a4`'s comp term uses only `gp-0x6a10`/`gp-0x6ac0`/
`gp-0x6abe` — **zero** references to `gp-0x6b98`/`gp-0x6bd0`/`gp-0x6b70`).
★ **Both surfaces are per-cycle STATIC int-vs-float consistency checks — neither computes a
derivative.** With the threshold-`0x0000` no-op above, a static un-debounced window is *exactly* what a
large single-cycle transient trips ⇒ **the on-car slew statistics and the ROM's monitor structure
converge independently.**
🛑🛑 **THE THIRD SURFACE — and it is the whole flash decision.** The *original* Monitor 1/Monitor 2
pair (`gp-0x3564`/`gp-0x3550`) does **not** compare `gp-0x6bd0` at all. It compares **`gp-0x6b98`, the
merged command itself**, against a float envelope `gp-0x6dbc`/`fVar23` at ±5/1024:
`fVar12 = −((float)*(short*)(gp-0x6b98) * 0.0009765625 − fVar23)`, else flag **32.0** (the "torque arm"
weight) → `gp-0x3540`/`gp-0x3550` → `FUN_000462e6(0x3f1b,…)` → **fid 29**; the same check recurs one
cycle later in `FUN_00042af8` (`gp-0x3564`, +10/cycle, thr 100) → `FUN_0004613e` @`0x43D42` → **fid 28**.
`fVar23` is built from `gp-0x4f64` + corridor tables `tp+0x71d4`/`tp+0x71d8`, **no Path-2 terms** ⇒ only
the left side could move. **IF `0xC63A0` reaches `gp-0x6b98`, V77 has a real mechanism.**
✅ **RESOLVED — THE PREMISE IS FALSE, AND SURFACE C IS BLIND TOO.** It had been justified by *"Path 2
closes through `gp-0x6b98`"* — **the wrong direction**: `FUN_0003b8f6` *reads* `gp-0x6b98` back **into**
Path 2, making it an **input**, not an output. The forward trace:
- **`gp-0x6afe` has exactly ONE writer program-wide** — `FUN_00042ac6` @`0x42ad6` (`st.h r15,-0x6afe,gp`),
  a 6-line clamp/store: `gp-0x6afe = (param_1 + 0x2800 > 0x5000) ? 0x7fff : param_1`
  [**orchestrator-verified** — decompiled directly; it reads nothing else]. Its sole caller is
  `FUN_00026c80` @`0x277f6`, passing `sVar38 = clamp(iVar14, ±0x2800)`, accumulated **entirely inside
  that function** from local stack buffers filled from mode-table constants.
- `search_instructions` scoped to `FUN_00026c80`: **989 instructions, ZERO hits** for `6ad4`, `6b94`,
  `6ad6`, `6b70`. Same scan over `FUN_00042af8` (1,769 instructions) for `uVar34`: **zero hits**,
  independently reproducing the second tracer's full decompile.
⊕ Real but non-decisive: `sVar38` is *also* stored to **`gp-0x6b4e`**, one of `FUN_00038148`'s six
weighted inputs and a **sibling** of `gp-0x6bd0` ⇒ `gp-0x6afe` and the damper's Path-2 term share a
common ancestor but run in **PARALLEL, not series**; `gp-0x6afe` bypasses `FUN_00038148` entirely.
⇒ `gp-0x6b98 = clamp(clamp(gate(gp-0x6afe) + uVar34))` — **neither term carries anything downstream of
`0x381AC`.** **ALL THREE SURFACES ARE BLIND. V77 cannot structurally prevent a Monitor-1/2 trip.**
⚠ Not exhaustive: 8 further `FUN_0004613e`/`FUN_000462e6` callers (`FUN_00027b0a`, `FUN_00027802`,
`FUN_00036388`, `FUN_00036c12`, `FUN_00041464`, `FUN_000365d2`, `FUN_00036d74`, `FUN_00041b8e`)
untraced; none is in the Path-2 dataflow by name, but a fourth surface is not formally excluded.
⚠ **This answer took the tracer three attempts** (structural NO → conditional YES → final NO). The
YES rested on an unverified directional premise. Recorded because the *pattern* matters: a subagent
reversing itself reads as diligence and is easy to accept unchallenged.
⚠ `0xC63A0`'s effect was in any case **confounded with damper liveness** across V72/V73/V74/V75 —
V72/V73 carried 2048 without a manual fault, but their damper was structurally **zero**, so it was inert.

🛑🛑🛑 **SAFETY UNCHANGED: V74 IS ON THE CAR AND HAS HARD-FAULTED. Two hard faults in two days, both
total loss of power steering. NO BUILD IN THIS LINEAGE HAS DEMONSTRATED SAFETY. Nothing here is
clearance to fly.**

Full narrative: `docs/HANDOFF-2026-08-07-v74-fault-rlogs-the-damper-WAS-in-force.md`.

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-06 (late): V74 ALSO HARD-FAULTED — IN MANUAL, OVER A BUMP, WITH THE
FACTOR C/E EDITS BYTE-STOCK IN THE ACTIVE MODE. THE FAULT CLASS IS NOT A DAMPER-DOSE PROBLEM, `k*` IS VOID,
AND NO BUILD IN THIS LINEAGE HAS DEMONSTRATED SAFETY.**
🛑 **SUPERSEDED 2026-08-07 — the "edits not in force" conclusion and the `k*`-is-void consequence are
REFUTED by the fault drive's own telemetry (above). The fault characterisation, the bit13 fingerprint,
and the eight refuted mechanisms all STAND. The safety statement stands and is unchanged.**

🛑🛑🛑 **SAFETY: TWO HARD FAULTS IN TWO DAYS, ON TWO DIFFERENT BUILDS.** V75 faulted engaged at a stoplight
launch; **V74 faulted DISENGAGED, driving over a bump** — latched total loss of power steering, EPS lamp on
continuously, still on after an engine restart, extinguished only after ~30 s of driving (textbook DTC
maturation, and it matches the `gp-0x3ee8` state-8 force latch, which is **set once and never cleared anywhere
in ROM**). V74 is on the car. **There is currently no build known to be safe.**

★★★★★ **[EVIDENCE, verified two ways] THE FACTOR C/E EDITS WERE NOT IN FORCE WHEN V74 FAULTED.** Disengaged
= **mode 24**, and all five mode-24 damper records are **byte-identical to stock** on V74 and V75 — FactorC
`0xD67E4` `X=[2240,3840,5120,8960] Y=[0,234,429,908]`, FactorE `0xD6820` `X=[60,400,2500,4000] Y=[0,140,539,927]`,
FactorB `0xD6760`, FactorD `0xD67A4`, Ceiling `0xD60B4`. Independently, **0 of the 54 non-CRC V73→V74 diff runs
land inside any mode-24 record.**
🛑🛑 ⇒ **`k* ∈ (0.580, 1.580]` IS VOID** and *"V74 flew 1,011 s clean"* is no longer a safety anchor. Every
gain-margin argument below inherited from it and must be read with that in mind.

★★★★ **THE ONE MECHANISM THAT CAN EXPLAIN A MANUAL FAULT: `0xC63A0`.** `tp+0x73a0 = 0xBF000+0x73A0`, u16 Q10,
one of **six sibling weights** at `0xC63A0..0xC63AA` in `FUN_00038148`'s stage-1 sum — **all stock 1024, and it
is the ONLY one any build has ever moved** (V72 → **2048**, never reverted until V77). It is a **bare `tp`
scalar, mode-proof, live in manual AND engaged**, with 1 reader (`0x381AC`), 0 writers, **no monitor and no
float mirror** (two-method null). It weights the damper output `gp-0x6bd0` into **Path 2**, which is a **closed
feedback loop inside the FIRMWARE** — `gp-0x6b98` re-enters one sample later via **`FUN_0003b8f6`** (`0x2240e`,
before the governor at `0x229ce`). Reverting it is **−6.02 dB, zero phase, and costs nothing on Path 1**
(`FUN_0003aa2c`, unity weight — the lane that actually delivers the damping).
⚠ It was only *functionally* armed at V74, when the damper it weights first became non-zero at creep.
⚠ **n = 1**: V72/V73 carried the same value and manual configuration without a manual fault.
🛑 **`0xC63A0` does NOT touch the `gp-0x6b98` re-entry term, which may dominate. OPEN, highest-value next trace.**

✅ **BUILT: V77 = V74 base + `0xC63A0` 2048→1024, single variable.** `V74→V77 = 2 runs / 5 bytes`
(`0xC63A1` `08`→`04` + `0xC6FFC` CRC). rwd `fd8db4e2ed140035782a55b2e6808bcf87a0ea85692cbe547960a13de1cfc8c5`,
image `a0f7c09c038931cabc419ccf79d4bb9819e647e88c0fb817ebc23cd44d102782`. **V77B** = same revert on the V75 base
(rwd `f2c2dc0b…`, image `acbc2187…`) — **UNFLASHED, NOT RECOMMENDED.** 🛑 **Neither is clearance to fly. V77 is a
hypothesis test, not a known-good.**

★★★★ **V75's FAULT IS PINNED TO ONE 100 Hz FRAME** — route `5e`, **t = 284.7947 s**. STEER_STATUS→7,
STEER_CONTROL_ACTIVE→0, `gp-0x6880`→1, the `0x1AB` DTC-active flag→1, all three `0x14A` angle fields→`0x7FFF`,
STEER_SENSOR_STATUS 7→4 — all latched, all in one transmission. **Three facts kill every magnitude-based
mechanism:** the faulting launch was the **MILDEST of four** (an earlier one sat on the ±4096 rail **76%** of
its window without faulting; this one had **0.00%** rail contact); the damper **never reached the `≥448` probe
rung (0/39,961 frames)**; and 300 ms pre-fault there was a **20.0 Hz oscillation absent from openpilot's
command**. ⇒ **a fast-transient sensitivity, not a dose problem.** Post-fault the control task and CAN stack are
both alive with MOTOR_TORQUE frozen ⇒ **motor-off latch, not a reset.**

★★★★ **THE bit13 FINGERPRINT [orchestrator-verified in Ghidra].** `FUN_00040a50` forces the angle sentinel on
`FUN_00046ea6(0xd)` — **bit13 of the OR-aggregate `(gp-0x18d0|gp-0x18d4)`** over descriptor words at
`tp-0x72bc = 0xB7D44`, stride `0x1c`. ⇒ **the angle invalidation is a CONSEQUENCE, not a cause**, and bit13
**rules out** fid 4, fid 80 (`0xC41668`) and fid 72 (`0xD48394`), and **rules in fid 28 (Monitor 1)** and
**fid 29 (Monitor 2 / `FUN_00045a20`)** — both `0x00003D01`, both **un-debounced single-cycle latches on the
damper's own chain**. This is the operator's "plausibility window" in its true form: a **±0.001 consistency
corridor between two representations of the same signal**, sized when the creep damper was structurally zero.

🛑 **THE DTC READ IS STRUCTURALLY BLIND HERE.** `0xF00049` is a **catch-all shared by ~42 fault_ids**; a
multi-member group's UDS status is **not an OR** — the display picks a winner from a **live RAM** log
(`tp-0x7fcc`) cleared by the power cycle, defaulting to fid 4. Today's read is byte-identical to a **stock,
pre-V21** capture except two bits (`0xC41668` +pending, `0xD48394` +confirmed). **`0x23` is not implemented on
this ECU** (NRC 0x11, three captures, three eras). ⇒ **catch it on-car, not over UDS.**

★★★★ **THE DAMPER FIXES THE GRIND AND CANNOT FIX THE MICRO-RATCHET.** Dose-response over the four builds that
differ only in the damper cells: **18–22 Hz slope −0.599 [−0.856, −0.348] = −5.20 dB/unit k (CI excludes zero)**;
**6–9 Hz slope −0.089 [−0.350, +0.163] (CI includes zero — FLAT)**. V75/V74 grind **0.349 [0.192, 0.784]**,
limit-cycle duty **0.034 — lowest of 13 builds**, ratio **0.067 [0.000, 0.283]**, negative controls flat.
🛑 **k required for the ratchet = 4.2–13.5 vs the 1.5798 that faulted** ⇒ **it needs a different lever.**
★ V75 is the first build where the bands decoupled: `(6-9)/(18-22)` 1.40 → **2.75 [2.09, 3.72]**.

🛑 **REFUTED THIS SESSION:** the cadence watchdog (**DTC `0x18` is a boot-time reset-cause report, not
live-trippable**); the probe cave's 45→68 B growth (**+17 cycles ≈ 212 ns — EXONERATED, keep the probe**); the
soft-EME boost-floor margin (**SM1/2/3 cannot latch** — the recovery ramp has no bypass); the angle domain as a
cause; a second consumer of the FactorC/E tables (`FUN_00034350` is the **sole reader** at all 40 modes).

Full narrative: `docs/HANDOFF-2026-08-06-v74-also-faulted-and-the-damper-was-not-in-force.md`.

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-06 (earlier): V75 FLEW, FIXED THE AUDIBLE GRIND #1 — AND HARD-FAULTED THE
ECU. LATCHED TOTAL LOSS OF POWER STEERING AT A STOPLIGHT LAUNCH. THE CAUSE IS A GATE-2 LOOP-GAIN
OVERSHOOT WE INTRODUCED, AND `k*` IS NOW BRACKETED BY OUR OWN TWO FLIGHTS.**
🛑 **SUPERSEDED — the loop-gain-overshoot framing does NOT survive V74's manual fault, and `k*` is VOID.**
The V75 symptom result and the fault characterisation below both stand; the *causal attribution to the damper
dose* does not.

🛑🛑🛑 **SAFETY FIRST: V75 IS ON THE CAR AND PRODUCED A MID-DRIVE LOSS OF ASSIST.** Operator report: after
stopping at a stoplight and pulling away normally with openpilot engaged, the EPS lamp lit, comma reported
an LKAS fault, and **all power steering was lost — the wheel went to manual effort and stayed there.**
This is a **more dangerous failure class than anything in this kit's history**: V24/V27/V48B bricked at
flash or at ignition, V40 bricked at ignition. **This is the first fault that fired mid-drive.** ⚠ n = 1;
no rlogs. ✅ Operator also reports V75 **fixed the audible grind #1 and strongly attenuated the micro
ratchet** — the best symptom result the kit has had. **Both facts are real and they are the whole trade.**

★★★★★ **THE MECHANISM — and it is the one number that survives.** The damper's **ramp-regime incremental
gain** `k = (C_Y0·Y[1]>>10)/(X[1]−X[0])` is a **FREQUENCY-INDEPENDENT SCALAR** on the whole damper path,
so it scales loop gain equally at every frequency and **no plant model is needed to compare builds**:

| build | `C_Y0` | `E_X1` | plateau M | **k** | **vs V74** | on-car |
|---|---|---|---|---|---|---|
| stock | 0 | 400 | 0 | **0.0000** | **−∞ dB** | damper **identically zero below 35 km/h** |
| **V74** | 429 | 400 | 225 | **0.5799** | **0 dB** | **1,011 s CLEAN** |
| **V75** | 566 | **200** | 297 | **1.5798** | **+8.70 dB** | **FAULTED** |
| **new cut** | 566 | 400 | 297 | **0.7655** | **+2.41 dB** | built, unflashed |

⇒ **`k* ∈ (0.580, 1.580]` — V74's gain margin through this path is >0 dB and <8.70 dB.** The first
quantitative statement this kit has about it, and it says the margin was **thin before V75 spent 8.7 dB of
it.** Firmware-side phase is only **−20.9°@7.79 Hz / −55.4°@21 Hz** (PID + 16 Hz IIR + rate EMA + 100 Hz
ZOH, all byte-extracted) ⇒ **the firmware alone cannot invert the damping; the instability is in the
plant** (measured Q ≈ 13.6). ⚠ No absolute Nyquist/gain-margin exists — the plant transfer function is not
measured, and one was deliberately **not invented**. The *relative* answer does not need it.

⊕ **What V74/V75 also did, undocumented until now: `FactorE Y[1] := Y[2]` created a BANG-BANG RELAY.**
Stock `Y = [0,140,539,927]` is a monotone ramp with **no flat segment**; V74/V75 `[0,539,539,927]` is
**constant** across `X[1]→X[2]` with the sign taken from `gp-0x6abe` ⇒ relay band **85–531 °/s (V74)** →
**42–531 °/s (V75)**. 🛑 **This is exactly V72's error, which this file claimed the design avoided** —
*"`Y[0]=0` is preserved ⇒ no chatter mechanism"* is true only **below `X[1]`**. ★ It is a **100 Hz
sampled-data artifact**, not a table discontinuity. **But the relay is NOT the fault**: at a gentle
stoplight launch the car sits in the **ramp** (engaged creep is above 200 ct only 21.8% of the time), and
a 5,224-point search shows that at matched peak gain a no-flat surface damps the symptom band the same
⇒ **the plateau is not what buys the damping; the gain is.**

🛑 **EIGHT MECHANISMS WERE REFUTED, ALL ON THE SAME CONSTRAINT — V74 FLEW CLEAN.** Surface arithmetic ·
`FUN_000347b8` (215-count margin) · int/float lockstep (**no float mirror of FactorC/E exists in the
ROM**) · governor slew-step · `FUN_00045a20` (`gp-0x6bd0` **cancels** in its subtraction) · duty ·
dwell (**V74 sits 210 consecutive 1 kHz cycles = 21× the trip requirement, 35×, and never faulted**) ·
per-event/at-rail transitions (**V74 is MORE rail-coincident per transition than V75**). ⇒ **the
proximate monitor is NOT identified.** Prime suspect remains **Monitor 2** (`FUN_00043e44`, ±5/1024,
charge:leak 2:1, break-even duty 1/3, **10 consecutive cycles = 10 ms → DTC 0x1c/0x1d → `0xF00049`,
latched**) — its corridor compares `gp-0x6b04` (PRE-clamp) vs `gp-0x6b98` (POST) and **can only open when
a clamp BINDS.** ✅ **That binding path is now CLOSED as impossible**: the bus→`gp-0x6b98` scale is exactly
**`k = 891/2048 = 0.4351`**, so a **rail-pinned openpilot command delivers only 1782 of the 4762 governor
ceiling (37.4%)** and even the damper's loosest aggregator bound leaves `1782+2048 = 3830 < 4762`. **And
the scale is byte-identical on V74 and V75, so it could never have discriminated them.**

✅ **THE DECISIVE MEASUREMENT NOT YET TAKEN: read the stored DTC.** `flashing-2020accord/eps-read-dtcs.py`
(source-asserted read-only) — UDS **`19 02 FF`**, **bus 1**, `0x18DA30F1`/`0x18DAF130`; proven on THIS ECU
(a real `0xF00049 status=0x48 confirmedDTC` capture exists from the V24 era). Fallback `22 48 01`.
🛑 **Requires the operator's explicit confirmation of payload and bus. Not sent.**

Full narrative: `docs/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md`.

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-06 (earlier): V74 FLEW, ROUTE `5d` — THE DAMPER IS REAL ON THIS CAR FOR THE
FIRST TIME EVER MEASURED. THE ABORT GATE READ AMBIGUOUS ON FIRST PASS, WAS INVESTIGATED PROPERLY, AND
RESOLVES CLEAR — NOT A RELAY, A PRE-EXISTING HARMONIC. V75 (2.74× THE DOSE) IS BUILT.**
🛑 **The abort-gate conclusion stands; the SAFETY conclusion did not.** The gate asked only about a relay
harmonic. Nothing in it, or in the no-clip rule, tests loop gain or phase — see the V75 headline above.

`bit7 = (gp-0x6bd0 != 0)`, the damper's OWN output — **the kit's first positive control on this cell** —
fires **67.44% duty engaged at creep vs 0.29% disengaged (230.7× contrast)**; engaged overall **39.93%**,
manual **2.13%**; **23,603 of 101,118 frames = 234.2 s of live damping.** V72's IDENTICAL probe on the
SAME cell fired **0 of 87,940**. ⇒ **[EVIDENCE] LEVER E′ IS IN FORCE** — the two-dead-zone diagnosis
below is now confirmed fixed on-car, not just argued from bytes.
★ **Negative control holds**: 100% of the 943 manual `bit7` frames are within 5 s of a disengagement
(the mode-lag hysteresis band), **0 of 40,398 beyond 5 s** ⇒ the engaged-column-only design is confirmed
**on-car** — manual and parking steering really is byte-stock, not merely asserted from the build.
★ **Probe validated in both directions**: 157 disengaged frames clearing *both* stock breakpoints read
**100.000%** — the STOCK damper working correctly whenever its own (narrower) dead zones are met. (🛑
corrected 2026-08-06: an earlier "183 / 99.45%" reading used the superseded 10.0 rate scale — the
settled scale is 4.7121, see `memory/reference-accord-rate-scale-4p7121-stands.md`.)

🛑 **`gp-0x67fa` = CONSTANT 5** (101,117 of 101,118 frames; state 4 on exactly one frame, the LAST of
the route, at vEgo −0.0, in PARK). State 5 clears every assist-chain mask (`0x830`/`0x930`/`0xc30`).
⇒ **`0x454FE` / the state-4 governor is DEFINITIVELY DEAD — retire it as a candidate for good.** (Carried
inertly by every build since V71; this closes the two-session-old [OPEN] for real.)

📋 **THE PRE-REGISTERED ABORT GATE — THE FULL PICTURE, NOT JUST THE FAVOURABLE NUMBER.**
🛑 **First pass (route-wide averaged-spectrum point estimate) understated the concern and was
corrected same-session.** `5×f0` prominence **2.227** (NFFT 2048) / **1.719** (NFFT 512) vs the **3.0**
threshold reads clear on its own point estimate, but its own CI is **[1.247, 5.293]** — crosses 3.0.
**Two things the first pass omitted, both real:** (1) the **K-free per-window method** (the script's own
comment calls it "the safer number" when the two disagree) puts V74 at **2.884 [2.301, 3.575]** — the
**HIGHEST median of any build in the corpus**, CI crossing 3.0. (2) The **creep-only arm** — the exact
regime V75's dose lands hardest, `FactorC Y[0]` is the creep cell — reads **5.844** at **K=2**
(pooled-corpus creep baseline **0.632** at K=24): nearly 2× the abort threshold, uninterpretable alone
at K=2 but not dismissible either.
✅ **Investigated properly, not waved off — TWO independent, unconfounded checks, both against the
hypothesis "V74 excited a new relay harmonic":**
1. **The tracking test** [EVIDENCE]: both anchored searches above are constrained to hunt within a few
   bins of that build's OWN predicted `5×f0`, so they cannot tell "peak moves with f0" from "peak is
   fixed and 5×f0 happened to land near it." An UN-anchored wideband (33–47 Hz) peak search, regressed
   across all 11 corpus builds, resolves it: peak location correlates with **2×grind-#1's own frequency**
   (r = **0.759**, p = **0.0068**, slope 1.478 [0.477, 2.255] — CI excludes 0, includes 1) and does
   **NOT** correlate with `5×f0` (r = **0.144**, p = **0.673**, slope 0.165 [−0.461, 0.913] — CI
   includes 0). V74's own independently-found peak sits at **40.20 Hz**, **0.01 Hz** from `2×grind-1`
   (40.19 Hz) and **2.11 Hz** from its own `5×f0` (42.31 Hz) — a gap far larger than the 0.049 Hz NFFT
   bin width. **Mechanism**: V74 has the **highest measured f0 (8.46 Hz) of all 11 corpus builds**, which
   places its `5×f0` closer to the pre-existing ~40–42 Hz grind-#1-2nd-harmonic zone (documented since
   V59, `memory/accord-v59-parametric-pump-marginal.md`, 42.19 Hz = 2×21.09 Hz) than any other build's —
   a coincidental proximity, not a causal one.
2. **The odd-harmonic-series check** [EVIDENCE]: a genuine relay excites the WHOLE odd series, not just
   the 5th. V74's `3×f0` prominence is **1.374 [1.05, 2.56] — rank 5 of 11 builds, unremarkable**
   (corpus range 0.47–18.34). The series is **incomplete** — independent evidence against a relay. ⚠ `3×f0`
   is itself confounded for TWO OTHER builds (V62, V71B — their `3×f0` lands within 0.6 Hz of their own
   grind-#1 fundamental, producing spuriously huge readings of 15.8 / 18.3) but **not for V74**, whose
   high f0 gives it the **largest gap to its own grind-1 fundamental of any build (5.29 Hz)** — the same
   property that confounds V74 at `5×f0` makes it the *cleanest* reading at `3×f0`, and that clean
   reading is ordinary.
⇒ **VERDICT: the gate resolves CLEAR, but as a checked conclusion, not a first-pass reading.** The
elevated readings on both anchored statistics are explained, mechanistically and with two independent
confirmations, by V74 happening to have the corpus's highest ratchet frequency — not by a new relay
cycle. **Falsifier A does not fire** (duty ratio **0.797**, wrong side of 1.2). **Falsifier C, raw**, is
clean vs V73 (Δf0 = **−0.035 Hz**) and fires only vs V72 (**+0.780 Hz**, discounted — corpus f0 spans
8.01–9.79 Hz build-to-build and the CIs overlap); **speed-matched** it is worse than the raw figure
(**+0.481 Hz** vs V73, **+0.543 Hz** vs V72 — the latter crosses the 0.5 Hz abort line), which the raw
number should not be read as having cleared. ⚠ **A single secondary check (does the ~42 Hz elevation
appear in V74's byte-stock manual creep arm too) came back mixed** — different peak location (46.99 Hz
vs 40.20 Hz), but both arms are thin (manual K=10 at a different f0=8.93; engaged creep K=2) — **not
load-bearing**, the tracking test and the odd-harmonic check are both better-powered and already
decisive. Scripts: `analysis-2020accord/r5d_falsifiers.py`, `r5d_tracking_test.py`, `r5d_3xf0_check.py`.
📋 **SUCCESS: UNDERPOWERED, DIRECTION FAVOURABLE.** duty **0.797** [0.544, 1.045] · duration **0.934**
[0.804, 1.152] · envp99 **0.835** [0.492, 1.197] — all trend down, none clears its own CI. MDE ≈
**2.0–2.9×** on **9 episodes** (route 5d delivered 9 against a planned ~40). V74's absolute ratchet
`duty_rel` **0.1036** is the LOWEST in the whole 12-build inventory. **Both symptoms remain active**:
6-9 Hz sits at **3.27×** and 18-22 Hz at **2.72×** over the 24-28 Hz control in the clean 9.4-12.5 m/s
window — the damper did not eliminate either mode, consistent with a real, correctly-signed but
partial effect that this route lacked the power to size cleanly.
⚠ **The shortfall is EXPOSURE, not the lever**: only **78 s** of engaged creep and **200.3 s** of engaged
time sat inside tyre order 1's contaminated speed band. **V75's flight needs genuine stop-and-go
congestion**, not a repeat of route 5d's shape — see the flight instruction below.

⊕ **Three structural corrections, this session:**
1. ★ **`gp-0x6ac2` is a SIGN-GATED BACK-DRIVE DETECTOR, not a rate signal** [EVIDENCE, decompile
   `FUN_00041464`]: `|state| >> 10` when `sign(rate) != sign(gp-0x6b98)`, else **0**. ⇒ the damper's own
   ceiling (`0xC77A0`, `X=[300,800] Y=[512,1024]`) sits **pinned at its 512 floor in ordinary driving**
   and only lifts during genuine kickback. All 26 modes byte-identical here. Corrects a prior memory:
   the `0x41852` bypass writes a **0xFFFF sentinel** at `0x41b44` — it does NOT hold the previous value.
2. **`gp-0x6ac0` = 30 counts per Hz of electrical frequency**, `column_deg/s = counts / 4.7121` — the
   firmware chain re-verified byte-for-byte this session. An on-car fit of **5.80** is explained by the
   estimator's column-vs-motor-rate bias, **not** a firmware error — do not revise 4.7121 from that fit.
3. **openpilot has TWO hard rails, both measured**: amplitude **4096** (`FUN_00052676` =
   `clamp(req × -4, ±0x4000)`, so **4096 × 4 = 0x4000 EXACTLY** — zero upstream headroom,
   orchestrator-verified in Ghidra) and a slew cap at **123 counts/frame** = `0.03 × STEER_MAX`, zero
   frames exceeding. **16.07% of engaged time sits against one rail or the other.**

Full narrative: `docs/HANDOFF-2026-08-06-v74-flew-and-v75-is-built.md`.

---

★★★★★ **THE HEADLINE, 2026-08-05 (confirmed and now flown, see above): THE CAR IS CONFIG ROW 11 `TVCA4`,
MODES 24 (MANUAL) / 26 (ENGAGED) — NOT `TVAA1`/10/11. EVERY MODE-INDEXED LEVER THIS KIT EVER FLEW WAS
INERT. AND THE DAMPER HAS **TWO** DEAD ZONES — SPEED *AND* RATE — WHICH IS WHY THIS CAR HAS NEVER HAD
CREEP DAMPING, STOCK INCLUDED (until V74 — see above).**

V73's probe read `*(byte)(gp+0x63fd)` over **104,061 frames** through a **4-bit** field that drops bit 4.
**[EVIDENCE, orchestrator-verified from `stock_fw_dump/code.bin`, table `0xCD000` stride `0x24`]** an
observed *v* means true ∈ {*v*, *v*+16}; observed **8** ⇒ {8,24}, and **raw 8 appears in NO row** ⇒
manual = **24**, forced. Only row 11 `TVCA4` contains 24 ⇒ engaged = **26**, forced. ★ **It is the MANUAL
arm that closes it** — observed 10 alone never would have (rows 2/3/6/7 carry raw 10), which is exactly
why the `TVAA1` assumption survived a dozen builds. ⚠ The part number is `TVA` but the ECU is coded to a
`TVC` chassis row; `build_v73_tva.py`'s assertion that every `TVA*`-reachable mode is < 16 is **void**.
⇒ **Inert by table selection: V44, V47, V72's Levers B/C, BOTH of V73's levers, and the ENTIRE r24 dose of
V69/V70/V72/V73.** See `BUILD-LINEAGE.md` **RULE 7**.

★★ **The mode TOGGLES with engagement** — 18 transitions, all engagement edges, **1.0209 s** rise lag
(sd 4.9 ms) / **2.0798 s** fall lag (sd 0.8 ms), 99.09% lag-matched, **zero exceptions**. ⚠ But it is a
**RELABELING, not a RETUNING**: of 21 mode-indexed records diffed 24-vs-26, **19 are byte-identical** ⇒
**it does NOT explain engagement-conditionality.**

★★ **THE TWO DEAD ZONES.** `dose = (FactorC × FactorE) >> 10` (seed `gp-0x698a` structurally pinned at
1024; FactorB/D flat unity). **FactorC** is speed-indexed and dead below `X[0]` = 2240 = **35 km/h**;
**FactorE** is rate-indexed and dead below `X[0]` = **60 counts**. **Both have `Y[0] = 0` in all 34 modes.**
Measured `gp-0x6ac0` in-burst = **98.9** [94.2, 113.0]. ⇒ **stock dose 0 · FactorC alone 6 · FactorC at
maximum 14 · both dead zones opened 50** against a ~43 requirement — **neither factor alone can reach it.**
⊕ **This retires V72's `bit4` null with no exotic explanation**: **98.72%** of engaged-highway frames sit
below `FactorE X[0]` ⇒ output zero, stock dose mean **0.10**. The damper runs and produces nothing.

🛑 **The symptom is ONE lightly-damped resonance, Q ≈ 14, ring-down 4.4 cycles, NO trigger in any recorded
channel, and f0 FALLS 9.0 → 7.7 Hz with load** ⇒ **not stick-slip** (a stick-slip rate rises with drive
velocity). The operator's *"same frequency, one audible"* is right: the hand feels **rim motion**, which
6-9 Hz dominates at every speed; the 21 Hz ring only decides audibility. Supersedes the recorded Q ≈ 40.

**Struck this session, with arithmetic:** saturation/headroom (0/127 in-burst frames at rail, and the four
summed mixer channels are **base assist**, not LKAS) · a 7.8 Hz firmware divider (mod-100 scheduler) ·
stick-slip · state 8 (`0x830 ⊂ 0xc30`) · `gp-0x67fa` aliasing (all 33 writers store literals ≤ 11).

Full narrative: `docs/HANDOFF-2026-08-05-the-car-is-tvca4-and-both-dead-zones.md`.

---

★★★★★ **THE HEADLINE, 2026-08-05 (⚠ SUPERSEDED — the mode is 24/26, not "not 10/11"; the `bit4` null is
explained by the RATE dead zone, not by table selection): V72's DAMPING LEVERS WERE NEVER IN FORCE. `FUN_00034350`
SELECTS ALL FIVE DAMPING FACTORS THROUGH A 13-VARIANT MODE TABLE; V72 EDITED MODES 10/11 ONLY; AND THE
PROBE PROVES THE CAR IS NOT IN THEM. ⇒ THE DAMPING APPROACH TO THE RATCHET HAS NEVER BEEN TESTED.**

`mode = *(byte)(gp + 0x63fd)`, selected by a config lookup (`FUN_00057f8e`) matching a 5-byte ASCII key at
`gp+0x6408..0x640C` against 16 records at `0xCD000`. On V72, modes 10/11 give `|gp-0x6bd0| = 389`
**unconditionally** (FactorC ≥ 430 at every speed, FactorE = 927 at every rate) ⇒ `bit4` would fire on
**100%** of frames. **It fired on 0 of 87,940, including 0 of 34,275 above 35 km/h.**
⇒ **[EVIDENCE] Not mode 10/11. Levers B and C were INERT BY TABLE SELECTION** — not a broken probe, not a
vacuous seed, not a missing factor; all three were independently eliminated first.
★ It hid for a dozen builds because `39990-TVA-A160` *reads as* row 2 `'TVAA1'` ⇒ modes 10/11 — **an
assumption in `BUILD-LINEAGE.md`, never a measurement.** `build_v44_tva.py` has patched 10 **and** 11
since V44 because of it.
⚠ **Which mode IS live is open.** Graded on route 59's own telemetry: **modes 4/5 and 12 fully
consistent** (highway `gp-0x6ac0` peaked at **329.8** vs their 330–335 thresholds), **0–3 marginally
disfavoured** (11/34,277 frames), **10/11 excluded.** V73's probe settles it.

Full narrative: `docs/HANDOFF-2026-08-05-v72-flew-the-damper-was-never-in-force.md`.
Spec and every risk: `docs/V73-DESIGN.md`.

## 🛑🛑 ON THE CAR: **V74 — AND IT HARD-FAULTED TOO (manual, over a bump, 2026-08-06 late).**

**Updated 2026-08-06 (late).** After V75's stoplight-launch fault the operator pulled over, **reflashed V74**,
and drove on it. **V74 then hard-faulted as well** — disengaged, over a bump, latched total loss of power
steering, recovered only by an engine restart. **[EVIDENCE] The FactorC/E edits were byte-stock in the active
mode (24).** ⇒ **`k*` is VOID and there is currently NO build known to be safe.** See the top-of-file headline.
**V77** (V74 + `0xC63A0` 2048→1024, single variable) is **built and unflashed** — a hypothesis test, not a
known-good. **V77B** (same revert on the V75 base) is built, unflashed and **NOT recommended.**
🛑 **The V75 section below is retained as the fault's primary record. Its causal attribution to the damper dose
does not survive V74's manual fault; the characterisation does.**

### Retained record — the V75 cut that faulted

🛑🛑 **THE TWO V75 CUTS DIFFER BY ONE SUBSTRING (`-EX1.200`) AND THE PROBE CANNOT TELL THEM APART.**
`build_v75_tva.py` emits a **byte-identical cave for every lever set**, so no payload, no log and no
on-car reading distinguishes them — **the filename is the only discriminator, for a build that cost the
operator power steering.** Unrenamed they sorted adjacent in `ls`. ✅ **The faulted cut is therefore
renamed with the reason IN THE NAME**, per the V70 precedent:
`SUPERSEDED-DO-NOT-FLASH-HARDFAULT-LOSS-OF-ASSIST-2026-08-06-V75-CY0.566-EX1.200.rwd`.
⚠ **Deliberate asymmetry: its PLAIN IMAGE keeps its original name** (`_v75_CY0.566-EX1.200_…bin`).
It is not flashable, and it is the fault's own primary evidence — every `v75_fault_*.py` and
`v75_step_*.py` script reads it by that path. **Renaming it would break the analysis and protect
nothing.** The hazard is the `.rwd`; that is what was renamed.

| | value |
|---|---|
| **ON THE CAR (faulted)** | `SUPERSEDED-DO-NOT-FLASH-HARDFAULT-LOSS-OF-ASSIST-2026-08-06-V75-CY0.566-EX1.200.rwd` |
| **BUILT THIS SESSION, UNFLASHED** | `…-levers-**CY0.566**-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd` |
| new-cut rwd SHA256 | `b245e1d17ed1ca4ec51a06a0a17a41afe37ba369b819eb0e2db02d2d49781765` |
| new-cut image SHA256 | `9a96b7fe0cb5263f9cbc528cb0a0a67744048f439373f326f5a7c966ff37f3d1` |
| new-cut image | `_v75_CY0.566_magprobe_plain_image.bin` |

**The new cut = `LEVERS = {"CY0": True, "EX1": False}`** — keeps V75's `FactorC Y[0] = 566`, reverts
`FactorE X[1]` to **400**. ★ **Single-variable against BOTH flown builds** (V74 + CY0 ; V75 − EX1) — no
other candidate is. Keeps **~99%** of V75's grind-band and **~88%** of its ratchet damping (plateau
untouched at M = 297), restores V74's plateau-entry statistics (~0.53/s at creep vs V75's 7.25), and
spends **2.41 of the ≤8.70 dB** margin V74 empirically demonstrated.
**Verified:** 50/50 CRC PASS · full readback re-verification · **mode 24 (manual/parking) byte-stock across
all six mode-indexed record types, resolved through the pointer arrays** (orchestrator-checked; a first
spot-check using a guessed byte range read "False" and was wrong — the same record-length trap V73 hit).
🛑 **NOT CLEARANCE TO FLY.** Built per the standing "build without asking" instruction; the flash decision
is the operator's and needs the file and bus named back.
⊕ `build_v75_tva.py` now takes **`ACCORD_V75_LEVERS`** (env) so it still reproduces the flown V75
byte-for-byte. `rlog-tools/decode_v75_probe.py`'s `RWD_NAME` now names the new cut — and the faulted cut's
full basename is **deliberately absent** from that file, because the build guard is a substring test and
naming both would make it vacuous for both.

⚠ **Fallback if you want to drive before any of this is settled: V74** (`d1c2671f…`), 1,011 s flown clean.
**It is the empirical choice, not a proven-safe one** — it carries the same relay at a higher entry rate
(85 °/s) and the same 2× weight at `0xC63A0`. The only *structurally* clean option for this lever is
stock FactorC/FactorE, which gives up the damper entirely.

### ⚠ SUPERSEDED — V74 was on the car until V75 (flown, route `5d`, 101,118 frames / 1,011.2 s) ⚠ **The abort gate for V75 was flagged ambiguous mid-session
(K-free/creep-arm numbers omitted from the first pass), investigated with a tracking test + an
odd-harmonic check, and resolved CLEAR — see the headline for the full picture, not just this line.**

| | value |
|---|---|
| V74 image SHA256 | `8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959` |
| V74 rwd SHA256 | `d1c2671f5a830897496cba51d8f7af53e178101e0a6018608be17caf70d02daf` |
| V74 image | `_v74_engagedcols_x0_12_addonly_plain_image.bin` |
| V74 rwd | `39990-TVA,A160-V74-V73BASE-ENGCOLS13-x12-addonly-FactorCY0eqY2-FactorEX0to12-Y1eqY2-frictionx1p5-C407E850-probe-67fa-6bd0nz-0x13000-0x100000.rwd` |
| V75 image | TODO (`build75`) |
| V75 rwd | TODO (`build75`) |

**Verified 232/232 on the plain image AND the decoded `.rwd`** · 50/50 CRC · 10 trailers, each confirmed
moved · **nothing in `[0xC5000,0xC5FFC)`** · 179 functional bytes all attributable (cave 42 · FactorC 24 ·
FactorE `X[0]` 13 · FactorE `Y[1]` 22 · friction 78) · keep-list byte-identical to V73 · **all 13
disengaged modes × 6 records byte-identical to V73.**
🛑 **Orchestrator-verified TWO WAYS** (standing instruction — `memory/feedback-verify-with-ghidra-and-bytes-both.md`):
**Ghidra**, fresh import of the *built* image — cave decodes as `ld.h -0x6bd0` → `cmp r0` → `be` (correct
polarity at the `b205` trap) → `movea 0x10` → `ld.bu -0x67fa` → `andi 0xf` → `or` → `shl 3` → merge with
`andi 0x7` of the payload → **a single `st.b` to the CAN staging byte and nothing else** (GATE 1);
**and bytes** — mode 26 records, mode 24 identical to V73, keep-list, `sar` = stock, 0 bytes in the CRC gap,
219-byte total diff.

🛑 **THREE V74 CUTS EXIST. Two are renamed `SUPERSEDED-DO-NOT-FLASH-…` with the reason in the name**
(`…x0_6_staleX0…` `70dcfca5`, built from a stale spec; `…x0_12_hybridD2A7E…` `00a06480`, carried a
withdrawn revert). ★ **All three share a byte-identical cave** — no probe payload distinguishes them, and
the hybrid cut differs from the live one by **8 bytes**. **The filename is the only pre-drive discriminator.**

⊕ **Three durable findings from the build**, recorded in `build_v74_tva.py`'s header:
**(1)** V73's flat `0x18` guard window **spills 4 bytes past a 4-point record** (`0x14`) into the *next*
mode's record — it false-positived here. Fix: `rec_len = 4 + 4n`. Anything reusing V73's idiom across
adjacent modes will false-positive. **(2)** `gp-0x67fa` is **lockstep-shadowed at `gp-0x4c39`**; the probe
reads only, and since 0 is unreachable in its value set, **a constant ZERO `bits 6:3` is a VOID drive, not
a null result** (🛑 fixed 2026-08-06 — the prior wording dropped the "== 0" and misled a reader this
session; a non-zero constant, e.g. the observed constant 5, is a normal, informative reading).
**(3)** Modes 2/3 carry a different FactorE record entirely (`X=[70,450,1000,4000]`,
`Y=[115,115,177,253]`) — the only engaged modes whose dose is unchanged by the 6→12 revision.

⚠ **THE SIZING'S HONEST LIMIT:** the ~43-count requirement is in **torsion-bar** counts and the ~50-count
delivery is in **aggregator** counts. **Nobody could convert between them** (the attempted transfer
estimate had coherence 0.072 and was correctly refused). ⇒ **the direction is solid — correct phase,
dissipative, opening a dead zone where there was none — but the magnitude could be off by a factor of a
few either way.** That is what the ladder and the pre-registered abort criterion are for.

### V74's FLIGHT (route `5d`, 101,118 frames / 1,011.2 s) — what it actually tested, and what it proved
| lever | in force? | result |
|---|---|---|
| **Lever E′** (damper, `FactorC`/`FactorE`, engaged column) | ✅ **LIVE — 23,603/101,118 frames (23.3%)**, 67.44% duty engaged-creep vs 0.29% disengaged | **THE FIRST TIME THIS CAR HAS MEASURED DAMPER OUTPUT** — V72's identical probe on the same cell read 0/87,940 |
| **Lever D′** (friction ×1.5, engaged column) | ✅ live on the same 13 modes as Lever E′ (shares the `0x830` gate) | not independently probed this build; rides the damper's liveness evidence |
| **`gp-0x67fa` state gate** | ✅ constant **5** ∈ {4,5,11}/{4,5,8,11}/{4,5,10,11} — every mask open | `0x454FE` proven definitively dead (state 4 = 1/101,118 frame, in PARK) |
| **pre-registered abort gate** | ✅ **CLEAR, ON INVESTIGATION** — first-pass point estimate looked clear but omitted the K-free (2.884, corpus MAX) and creep-only (5.844 @ K=2) numbers; tracking test + odd-harmonic check then showed the elevation is grind #1's pre-existing 2nd harmonic, not a relay | see headline for the full chain — this cell is a summary, not the record |
| **pre-registered success** | ⚠ **UNDERPOWERED** — duty/duration/envp99 all trend down, none clears its CI | MDE 2.0–2.9× on 9 episodes (planned ~40); **not** a null result, an exposure shortfall |
| probe (`bit7`/`bits 6:3`) | ✅ both validated — positive control fires (157/100.000%), negative control holds (0/40,398 manual frames past the 5 s hysteresis band) | the kit's cleanest probe result to date |

**Both symptoms remain measurably active** — 6-9 Hz at **3.27×** and 18-22 Hz at **2.72×** over the
24-28 Hz control in the clean 9.4-12.5 m/s window — but V74's absolute ratchet `duty_rel` (**0.1036**) is
the LOWEST of the whole 12-build inventory, and every trend (duty, duration, envp99 vs V73) points the
right way without clearing its own CI on 9 episodes. ⇒ **the honest read is "real, correctly-signed,
partial effect that this route lacked the power to size" — not "no effect" and not "fixed."**
🛑 **This is a genuinely different situation from V73's flight below**: V73 flew with BOTH levers at
**zero exposure** (wrong mode, per RULE 7); V74 is the first build where the exposure question is
answered and the remaining question is purely statistical power.

### V75 — 2.74× THE DOSE, SAME ENGAGED-COLUMN DESIGN. **BUILT, VERIFIED, UNFLASHED.**
`FactorC Y[0]` 429→**566** and `FactorE X[1]` 400→**200**, on the same engaged column of all 16 rows as
V74 (13-mode disjoint design, unchanged). **2.74×** V74's dose at the symptom's own measured rate
(**50 → 137** counts at rate 99). 🛑 **`FactorE Y[]` has ZERO headroom — do not touch it.**
✅ **Verified clip-free TWO WAYS** (see `BUILD-LINEAGE.md` **RULE 8** — this is exactly the rule it
records): 0 new clips on the 98,988-point rectangular-grid rule (`new > old AND new > 512`), **and** 0
clips on the 101,118 frames actually driven (observed peak **354** = 69% of the 512 ceiling). The grid's
worst corner assumes 849°/s; route 5d's actual maximum was 330°/s and zero frames exceeded 2000 counts —
both checks were run and agree, not just the permissive one.
★ **`FactorE X[1]` is a free lever**: it steepens the low-rate ramp without raising the plateau that sets
the surface maximum, so it costs nothing under either the grid rule or the dose ladder — neither found it
by construction; the probe-5d telemetry did.
**PROBE redesigned to a magnitude thermometer**, not a liveness bit (V74's `bit7` already answered
liveness; asking it again wastes a bit): `bit7` = nonzero · `bit6/5/4` = `|output| ≥ 128/288/448` ·
`bit3` = `(gp-0x6ac2 != 0)` (the back-drive detector — see the structural correction above).
⏳ **Image/rwd SHA256: TODO, pending `build75`.**

### ⚠ SUPERSEDED — WAS ON THE CAR (before V74): V73's FLIGHT (route `5a`, 104,061 frames / 1,040.6 s)
| lever | in force? | result |
|---|---|---|
| **Lever E** (damping, modes 0-5/12/14) | ❌ **0 / 104,061 frames** | zero exposure — **not** an under-dose |
| **Lever D LERP** (friction ×1.5 at `0xD2A44` = mode **10**) | ❌ **inert** | null by construction |
| **`0xC407E` 511→850** (not mode-indexed) | ✅ **live**, ~80% of burst frames | **no** band change ⇒ weak but real falsification, bounded at +339 counts |
| probe | ✅ 100% liveness, `bits 2:0` preserved | **the mode** |

Operator: grind #2 **resolved** · macro ratchet **still fixed** · **grind #1 and micro ratchet both
present**, *"the same vibration frequency; grind #1 is audible, the micro ratcheting is not."*
🛑 **And his reframing, which the byte evidence independently confirms: "grind #2 was never an independent
issue — it only ever came to be through proposed fixes for grind #1."** V62's `sar` (mode-proof code)
governs it; V72/V73 do not carry it. **The fix is an ABSENCE** ⇒ V74/V75 retain it by leaving the lanes
alone.

### V74/V75 — the design principle, earned twice over: **write the ENGAGED COLUMN OF EVERY ROW**
Engaged set {2,3,5,11,14,15,17,23,26,27,29,32,33} and the disengaged set are **disjoint across all 16
rows** ⇒ delivers whatever row is live **while leaving manual/parking steering byte-stock**.
- **LEVER E′** — `FactorC Y[0] := Y[2]` · **`FactorE X[0]: 60 → 12`** · `FactorE Y[1] := Y[2]`.
  ★ **Opens the RATE dead zone rather than raising a gain** ⇒ genuinely rate-proportional in the symptom's
  range. 🛑 **The OPPOSITE of V72's error, not a larger version:** V72 raised `FactorE`'s floor, giving a
  *constant* (near-bang-bang relay). Here **`Y[0] = 0` is preserved**, so magnitude vanishes with rate and
  the bare `sign()` relay multiplies a vanishing quantity ⇒ **no discontinuity, no chatter mechanism.**
- **LEVER D′** — friction ×1.5 on the same 13 modes; `0xC407E` = 850. ⚠ **not** mode-indexed ⇒ applies in
  manual too (disclosed). 🛑 **Hard cap 1000, never 1024** — the aggregator's ±0x400 window is a
  **zero-reject**, so a lane on the cliff contributes *nothing*.
- **UNTOUCHED** — the whole r24/r26 lane incl. V72's r26 cut (`0xC6A68`/`0xC6A7C` flat 512), the `sar`
  sites, the gate, both scalar arms. ⚠ That cut is **PARTIAL** — `rec2 0xC6A90` / `rec3 0xC6AA4` are stock.
- **PROBE** — `bits 6:3 = gp-0x67fa` (lossless; 0 impossible ⇒ liveness structural) · **`bit7 =
  (gp-0x6bd0 != 0)`** — the damper's own output, **the positive control the last five probes lacked.**
- **GATE 2 [EVIDENCE]** — both lanes dissipative at both frequencies; both phasors have positive real part
  ⇒ **their sum does too, by construction.** DTC-0x18 cost **zero** (cal-only).

📋 **V74's PRE-REGISTRATION, CHECKED 2026-08-06 — see the headline for the full chain, this is a summary.**
success = 6-9 Hz duty **and** duration fall with **f0 unchanged** (|Δf0| ≤ 0.3 Hz) ⇒ **UNDERPOWERED**
(trends favourable, none clears its CI on 9 episodes). **ABORT if 5×f0 prominence > 3.0** (baseline 0.80)
⇒ **CLEAR, but only after investigation** — the route-wide point estimate (2.227/1.719) looked clear on
its own, but omitted the K-free per-window number (corpus MAXIMUM, 2.884, CI crossing 3.0) and the
creep-only arm (5.844 at K=2). A tracking test (peak location vs 5×f0 across 11 builds: r=0.144, p=0.673,
NOT significant) and an odd-harmonic check (V74's 3×f0 prominence 1.374, rank 5/11, unremarkable — the
series is incomplete) both independently showed the elevation is grind #1's pre-existing 2nd harmonic
(peak vs 2×grind-1: r=0.759, p=0.0068), not a new relay cycle, and explained WHY V74 specifically reads
high on the anchored statistics (it has the corpus's highest f0, so its 5×f0 sits closest to that
pre-existing line — a coincidence of this build's own frequency, not a causal effect of the dose).
Also checked and clear: duty ratio > 1.2 with prominence ratio > 1.3 (duty ratio 0.797, wrong side); raw
|Δf0| > 0.5 Hz (clean vs V73 at −0.035 Hz, fires only vs V72 at +0.780 Hz, discounted). ⚠ **Speed-matched
Δf0 is worse than the raw figure** — +0.481 Hz vs V73, +0.543 Hz vs V72 (crosses the 0.5 Hz line) — do
not cite the raw number as though it were the more rigorous one. **Honest read:** the lever is real,
correctly signed, did not extinguish either mode on this route's exposure, and the gate genuinely holds
once investigated — not a rubber stamp on the first favourable number.

### V76 — V75's SIBLING (SAME V74 BASE). **BUILT, VERIFIED, UNFLASHED — and UN-DERISKED, not superseded.**
`_v76_gate_fb_arm5244_gateprobe_plain_image.bin`. Restores V67/V68's rate lane on the V74 base: gate
`0x3AA96` `0xC5 → 0xFB`, `0xC6446` = 5244, `0xC6444` = 512 (already equal — asserted, never written),
**both `sar` sites left stock**. 🛑 **Do NOT rename or supersede this artifact.** It is a live candidate.

**[EVIDENCE, byte-read 2026-08-06]** V76's **engaged** rate lane is **byte-identical to V67/V68**, and
therefore delivers `(r24, r26)` = **(3.414, 0.250)** at 0 km/h / rateKey 3000. ⚠ Its r24 dose is
**rate-dependent, 1.707× → 3.414× across the creep rate axis** — a flat arm replacing a rolling-off LERP,
so quoting "≈1.71×" alone understates it. ⊕ V76's **manual** r26 is also cut to 0.167× (V74's ungated
`0xC6A68`/`0xC6A7C` = 512), where V67/V68's manual is stock — a further cut, in the safe direction.
⊕ **The masking risk is already closed by existing data**: V67's own probe read `gp-0x671d != 0` in
**0 of 150,327 frames**, so `0xC6442` never outranks the arm.

🛑🛑 **GRIND-#2 RISK: NOT ESTABLISHED.** V76 sits in the cell whose only occupants are V67/V68, and that
cell's evidence is:

| cell | V67+V68 exposure | P(0) at V71C's own rate | power | MDE @ 80% |
|---|---|---|---|---|
| non-highway 0.3–14 m/s | 224.0 s | 0.063 | 94% | 0.58× ref |
| creep 0.3–4 m/s | 42.2 s | 0.510 | 49% | 2.39× ref |
| **engaged creep CORNER** | **11.5 s** | **0.607** | **39%** | **3.22× ref** |
| **engaged HIGH-RATE creep** | **0.0 s** | — | **0%** | — |

⇒ **It is un-derisked, not de-risked.** The powered r26-cut evidence (V72/V73/V74, 212.5 s, P(0) = 0.016)
is at **r24 = 1.000×** and does **not** transfer to a build that raises r24. Combined with the
collinearity above, **no build has ever moved grind #1 and been well-powered against grind #2.**
✅ **THE RESOLUTION IS CHEAP AND COSTS NO BYTES: ~90 s of deliberate ENGAGED hard cornering at creep**
(< 4 m/s, |ang| ≥ 100°, openpilot engaged) moves P(0) below 0.05 **on a single drive**, whichever way it
falls. Fly it with that instruction or do not fly it.

### V75's PRE-REGISTRATION — Falsifier B and C RETIRED in their anchored form, not re-sized
🛑🛑 **`memory/reference-accord-falsifier-b-anchored-search-presupposes-answer.md` — read before
scoring V75.** Falsifier B (anchored `5×f0` prominence, ±4/±2 bins) and Falsifier C (raw `Δf0`) are not
being loosened or tightened for V75 — they are **RETIRED**, because they are structurally incapable of
separating "genuine relay harmonic" from "a fixed pre-existing line the prediction happened to land
near" (proven on real data: V74's true peak sat 43 NFFT-2048 bins outside the anchored search's reach).
**Replacement instrument for V75 and every future gate check:**
1. The **un-anchored wideband peak search + cross-build tracking regression**
   (`analysis-2020accord/r5d_tracking_test.py` — the reference instrument, run it as a matter of course,
   not only when a number looks concerning) — peak-vs-`5×f0` slope near 1 with a significant correlation
   is what a genuine relay looks like; near 0 is what a fixed pre-existing line looks like.
2. The **`3×f0` odd-harmonic-completeness check** (`r5d_3xf0_check.py`) — a real relay excites the WHOLE
   odd series, so `3×f0` should be elevated roughly in proportion to `5×f0`, not merely unremarkable.
3. Before trusting EITHER harmonic for a given build, **check its gap to that build's own grind-1
   fundamental / `2×grind-1` first** — whichever harmonic sits closer to that fixed line is the one at
   confound risk, and this varies build to build (V74 was confounded at `5×f0`, clean at `3×f0`; V62 and
   V71B are the reverse).
Score against **both** V73 and V74 as comparators (V74 gives the cleaner same-mechanism baseline now that
Lever E′ is confirmed live). Score BOTH 6-9 Hz and 18-22 Hz, clean-window first, exactly as done for V74.

### FLIGHT INSTRUCTION FOR V75 — 🛑 route 5d under-delivered on EXPOSURE, not on the lever
Route 5d gave **9 episodes** against the ~40 planned, and only **78 s** of engaged creep — the MDE
(2.0–2.9×) was set by this shortfall, not by the lever being small. **Repeating route 5d's shape will
under-power V75 the same way.** **(1) ESSENTIAL: genuine stop-and-go congestion** — a congested
lane-marked arterial, engaged, ~15-20 min, targeting **≥ 30 episodes** and **≥ 200 s of engaged creep**
(2.5× route 5d's creep exposure). **(2) ESSENTIAL:** steady **≥ 20 m/s** cruise, 8-10 min — route 5d's
own clean high-speed arm was only 3 episodes/97 s, the thinnest in this report. (3) opportunistic:
mid-motion disengagements, any speed.
⚠ Tyre order 1 is in-band at **12.5-18.7 m/s**, order 2 at 6.2-9.4, order 3 at 4.2-6.2 ⇒ **clean windows
9.4-12.5 m/s and ≥ 20 m/s** — route 5d put 200.3 s of engaged time inside the dirty order-1 band vs only
158.7 s clean; weight the drive toward the clean bands if the route allows a choice.
⚠ **Read the probe first** — V75's probe is a magnitude thermometer, not a liveness bit (V74 already
settled liveness); a constant ZERO across `bit7`/`bits 6:3` means the cave never fired and nothing else
is interpretable, but a non-zero constant is a normal, informative reading, not a void drive.

## ⚠ SUPERSEDED — WAS ON THE CAR: **V72** (route `59`)

| | value |
|---|---|
| V73 image SHA256 | `918a37151876a1a321103fbd7252684d944773109ff454a08a41fe2c191ee63a` |
| V73 rwd SHA256 | `d15e848f86f11245db16822bb06dadde39d5112aa6ce0444d3219aa5dee7c7d5` |
| V73 rwd | `39990-TVA,A160-V73-V72BASE-frictionx1.5-C407E850-ratchet-modes0_5_12_14-Y0eqY1-probe-MODEBYTE-0x13000-0x100000.rwd` |

**V73 verified:** 50/50 CRC PASS · exactly 6 trailers · **nothing in `[0xC5000,0xC5FFC)`** · 89 functional
bytes all attributable (cave 61, ratchet 20, friction 6, clamp 2) · V72's levers byte-identical.
⚠ An earlier V73 cut targeting modes 0/2 only is renamed `SUPERSEDED-DO-NOT-FLASH-…`.

### V72's FLIGHT (route `59`) — one fix real, one not
| symptom | verdict |
|---|---|
| **creep grind #2** | ✅ **ESTABLISHED.** Routes 58/59 identical **691.2 s** exposure, r59 more in every burst cell, **7 vs 0 (ALL-SPEED windows)**, exact Poisson **p = 0.0078**; pooled two-lane row **0 in 2,656 s vs 31, p = 6e-5** — 🛑 **BOTH FIGURES ARE *WINDOW* COUNTS AT 50% OVERLAP**, so a single 2 s burst contributes 2–3 of them (~3× inflation). **Restated on MERGED EVENTS: 0 vs 13, and the p-value moves ~2 orders.** ⊕ V72's own zero is **genuine but is a `(1.000, 0.250)` result, not `(3.414, 0.250)`** — see the corrected two-lane table |
| **highway grind #2** | ❌ **STRUCK.** 0 in 253.4 s ⇒ **P(0) = 0.456**; no build ever produced a highway burst. Real result is a **non-regression** (0.448 vs V71C, outside null, 91 counts) |
| **micro ratchet (7.79 Hz)** | ❌ **NOT FIXED — attenuation 1.0**, three instruments. Column moves **2.1–2.5× FURTHER** |
| **macro ratchet** | ⚠ fixed per operator, **UNMEASURABLE** — 64/65 comparisons inside null and both instruments **fail their own positive control** |
| **grind #1** | ❌ **614 [311, 1187] — the STOCK band** (P = 0.985 vs stock; excluded HIGHER than V62/V65/V67/V68/V71C at P < 0.0001) |

🛑 **THERE ARE TWO RATCHETS, per the operator.** **MACRO** = the large one he reports fixed. **MICRO ==
the 7.79 Hz line** — *"not audible, felt in the column"* is exactly right, **7.7 Hz is below the ~20 Hz
hearing threshold.** All three data agents measured MICRO; nobody measured MACRO.

### ★★★★ GRIND #1 IS A LIMIT CYCLE — [EVIDENCE, 8 routes]
**duty spans 0.015 → 0.958 (64×) while in-burst amplitude spans 1232 → 1533 (1.24×)** against a **5.62×**
dose ladder; two-moded on exactly the arms that have it, one-moded on the arms that suppress it.
⇒ **successful builds stop the cycle STARTING, they never shrink it.** Excess over its own 24-28 Hz
control floors at **2.21** (V67/V68) and **reaches 1.0 on no build.**
⊕ And sweeping `a` (`gp-0x69a4`) 0→32.0, summed and differential, **no value makes the ladder monotone**
(best |τ| = 0.429) ⇒ **not a scalar-gain phenomenon.**
~~★★ **At ≤10 km/h V72's delivered gain is BIT-IDENTICAL to V67/V68's and it scored stock's grind**
(dose-matched: consistent with stock P = 0.874, excluded higher than V67+V68 P < 0.0001).
⇒ **the rate lane is exhausted as a grind-#1 lever.**~~

🛑🛑 **RETRACTED 2026-08-06 — THE PREMISE IS FALSE AND THE CONCLUSION DOES NOT FOLLOW.** [EVIDENCE,
byte-read] At ≤10 km/h **V72 delivers r24 = 1.000× and V67/V68 deliver 1.707–2.048×.** They are
identical on **r26 only** (both 0.167×). ⇒ **not bit-identical, and not dose-matched.**
★ **This is RULE 7 wearing a disguise, and it is the most dangerous form of it seen so far:** both
builds carry the literal value **5244** — V72 in the **mode-10 `gain_B` surface** (inert on a mode-24/26
car) and V67/V68 in the **`0xC6446` gated arm** (live, mode-proof). *Same number, same lane, opposite
delivery.* Any comparison keyed on the cal value rather than on the delivered gain will make this
mistake. **Compare DELIVERED gains, never cal values.**
⊕ The measurements agree with the correction, not with the retracted claim: on one instrument with the
split-half null computed first, **V72's grind #1 did not move (ratio 0.953) while V67 = 0.430 and
V68 = 0.229 did.** If the two configurations really delivered the same gain, that split could not exist.
⇒ 🛑 **"The rate lane is exhausted as a grind-#1 lever" is WITHDRAWN.** It rested entirely on the false
equality. The r24 arm remains the only lever that has ever produced the kit's best grind-#1 numbers, and
**V76 is the build that carries it** — see the V76 section. What *is* still true, and is the real
constraint, is [[accord-grind1-fix-and-grind2-are-collinear]]: the trade against grind #2 has never been
separated at usable power.

### The two symptoms share a driver but are DISTINCT MODES
Partial `r(6-9, 18-22 | 24-28)` = **0.460**, circular-shift null [−0.102, +0.023], **p = 0.0002**,
build-independent — **but opposite-signed dependence on steering position** (Spearman **+0.23/+0.32** vs
**+0.05/+0.06**, two pipelines). **Two amplitudes of one oscillation cannot do that.**
⇒ 🛑 **Score BOTH bands on every future build.** ⚠ The angle result is **diagnostic, not a lever** —
no firmware structure of adequate magnitude found, and **nothing separates firmware from plant.**

---

★★★★★ **THE HEADLINE, 2026-08-05 (SUPERSEDED — still valid as the grind-#2 rule): THE TWO-LANE RULE.
CREEP GRIND #2 REQUIRES **BOTH** LANES ELEVATED — CUTTING EITHER KILLS IT, SIX BUILDS, NO EXCEPTIONS.**
⇒ V72 occupied the safe row and **grind #2 is confirmed fixed on-car.**
⚠ Its companion claim — that V72 would deliver "the first real damping at creep" — is **REFUTED**: see
the headline above. Narrative: `docs/HANDOFF-2026-08-05-grind2-is-grind1s-harmonic-and-both-lanes-must-move.md`.

🛑🛑 **CORRECTED 2026-08-06 — THE RULE'S *SHAPE* SURVIVES, ITS *NUMBERS* DO NOT.** The original wording
was "r24 high-rate ≳**3.4×** AND r26 high-rate ≳1.5×". **The 3.4× threshold is WRONG: V62/V65 burst at a
delivered r24 of 2.000×.** The table below is rebuilt on **DELIVERED** multipliers, byte-read from every
shipped image on a **mode-24/26** car (`analysis-2020accord/_grind2_delivered_lib.py`,
`grind2_delivered_table.py`). Do not quote a numeric r24 threshold; quote the shape.

## 🛑 SUPERSEDED — WAS ON THE CAR: **V71C** (route `58`)

| | value |
|---|---|
| image SHA256 | `466b5f2983167ed1599969eaf1165b570c34ff900012853c6fdb050deebaca58` |
| rwd SHA256 | `2751ffa60499b7a5969c47feaf67caedf43eeaf215ae0bc9297abe66fef7e7a4` |
| rwd name | `39990-TVA,A160-V72-A-WHOLEAXIS-r24_5244-r26_512-V67CREEP-hwy1x-B-FactorCE-430_927-C-63A0x2-454FE-probe-a512-a1024-damp-rate512-…rwd` |

⚠ **An earlier V72 cut was the SUPERSEDED plateau-only spec** and is renamed
`SUPERSEDED-DO-NOT-FLASH-…`. **Exactly one flashable V72 exists.** ★ It was caught by **byte-checking the
image, not the filename** — the superseded artifact's own name read `…-PLATEAU-…-LEVERB-V47damp-…`, i.e.
it described itself correctly and was still the wrong build.

**Verified:** 50/50 CRC blocks PASS · exactly the MAIN/CAL/`0xD2000` trailers moved · nothing in
`[0xC5000,0xC5FFC)` · all 85 functional bytes attributable · **V67/V68's engaged multipliers reproduced
with 0 mismatches at 0 and 10 km/h at rate 0/400/1400/3000** · **0 deviations from 1.000× at ≥50 km/h.**

### THE TWO-LANE RULE — REBUILT ON **DELIVERED** MULTIPLIERS, 2026-08-06 [EVIDENCE, byte-read]
🛑 The r24 column below is **DELIVERED**, not nominal. It is computed by mirroring the decompiled ladder
(`0x3AB56` r26 / `0x3ABFA` r24, both `sar` sites) against the **mode-24/26** `gain_B` records, from each
shipped image. Exposure is the **engaged creep CORNER** cell — |ang| ≥ 100°, 0.3–4 m/s — because **18 of
21 creep burst windows live there**; only **DOSED** arms are counted (a gated build's manual arm runs
byte-stock and does not test the lever). Events are **merged bursts**, not overlapping windows.

| group | build(s) | **DELIVERED r24** | **DELIVERED r26** | *(old nominal r24)* | dosed corner-creep | events |
|---|---|---|---|---|---|---|
| stock lane | V58·V59·V61·V64·**V69·V70** | 1.000 | 1.000 | 1.000 | 346.9 s | **0** · P(0)=0.0012 |
| r26 cut only | **V72·V73·V74** | **1.000** ⚠ | 0.250 | ~~3.414~~ | 212.5 s | **0** · P(0)=0.016 |
| r26 up only | **V71B/`r54`** | 1.000 | 2.000 | 1.000 | 102.4 s | **0** · P(0)=0.136 |
| **both up (`sar`)** | **V62 · V65** | **2.000** ⚠ | 2.000 | ~~3.414~~ | 387.8 s | **7 — worst in corpus** |
| **both up (gate)** | **V71C/`r58`** | 3.414 | 1.500 | 3.414 | 23.0 s | **1** (3 windows, max 1742) |
| **r24 up, r26 cut** | **V67/V68** → **V76** | 3.414 | 0.250 | 3.414 | **11.5 s** | 0 ⚠ **P(0)=0.80** |

⚠ **TWO CELLS WERE WRONG AND ARE CORRECTED ABOVE.**
- **V62/V65 delivered r24 = 2.000×, not 3.414×.** Their lever is `sar 0xa → 0x9` at `0x3AC20`/`0x3AB76` —
  a **flat doubling of both lanes at every speed and rate**, not the arm. 3.414× was the *arm* figure
  copied across the whole column.
- **V72/V73/V74 delivered r24 = 1.000×, not 3.414×** — **RULE 7.** Their `0xD2A74`/`0xD2AB0` = 5244 sits
  at **mode 10** and is **inert** on a mode-24/26 car. Byte-read: `gain_B` m24 and m26 are **stock** on
  every one of them. ⇒ **V72 never occupied V67/V68's row** — it occupied `(1.000, 0.250)`.
- ⊕ The **V67/V68** and **V71C** rows were already correct: 3.414 / 0.250 and 3.414 / 1.500 are the true
  delivered values at 0 km/h, rateKey 3000, engaged.

🛑 **A THIRD DEFECT, IN CODE, WITH ITS BLAST RADIUS AUDITED.** `analysis-2020accord/_r58_lib.py` computed
route 58's "delivered dose surface" **against `_v70_plain_image.bin` at mode 10**, so its docstring
asserted — emphatically, as *"the single most load-bearing arithmetic fact on this route"* — that
**V71C's creep r24 is a CUT (0.854×)**. It is a **BOOST (1.707× at low rate → 3.414× at rateKey 3000)**.
The signature is unambiguous: its "stock r24" row `6144 5633 5122 …` **is** V70's doubled mode-10 rec0/rec1
(`Y[0]` 3072→6144, 2561→5122, byte-read), while its ≥50 km/h entries are the undoubled rec2/rec3 — because
V70 edited only rec0/rec1.
✅ **Audited, and the blast radius is CONTAINED:** the "cut at creep" framing **never propagated into
`STATE.md` or `BUILD-LINEAGE.md`** (grepped), and **no script consumed `V71C_R24_DOSE`** — it is defined,
re-exported once by `_r59_lib.py`, and read by nothing. The damage was to *readers* of the docstring.
⊕ The **2.438× at 100 km/h** figures used in the highway argument below are **unaffected and correct** —
they sit above 50 km/h where V70's mode-10 edit never reached. **Do not revise them.**
⊕ `V71B_R26_DOSE` / `V71C_R26_DOSE` were also always right: `gain_A` is not mode-indexed and V70 never
touched it, so neither cause could reach them (re-derived, agree to ≤ 0.03).
**Fixed in place 2026-08-06** with the wrong text quoted rather than deleted; the memory
`memory/accord-two-lane-rule-grind2.md` carried the same "0.93× cut" line and is corrected.

★ **What survives:** every bursting build has **both** lanes elevated, and each single-lane arm is clean —
r26 = 2.000× alone (V71B) and r26 = 0.250× with r24 stock (V72/V73/V74) both produce zero.
🛑 **What does NOT survive:** the numeric threshold, and the *necessity* of the r26 cut — see the power
row above. **V67/V68's cell rests on 11.5 s and P(0) = 0.80.**

🛑🛑 **THE V67/V68 CELL NEVER SAID "none" — THE TABLE FLATTENED THE OPERATOR'S HEDGE INTO A RESULT.**
His verbatim report on V67 (`docs/HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md:23`):

> *"Grind #2 seems **mostly** gone. However, and maybe this is a grind #3 or #2.5, on the way, when doing
> somewhat significant turns, there is sometimes a resonance that I can feel is similar to grind #2. …
> Grind #2 **might still be there somewhat** during LKAS-disengaged or **more so LKAS-engaged at
> low-speed, I am not sure. Might just be dampened.**"*

⇒ He named **engaged low-speed** — the exact cell with 11.5 s of exposure — as where he was unsure. That
hedge was recorded as **"none"**, and a later session then cited the "none" as evidence for a build
recommendation. **The correct entry for that cell is UNMEASURED, never a null.** Rule:
`memory/feedback-never-log-a-hedge-as-a-null.md`.

### ★★★★★ THE COLLINEARITY — 2026-08-06, [EVIDENCE], and it is the strategic fact in this corpus
**Split-half null computed FIRST inside the stock-lane pool with the identical estimator = [0.663, 1.502];
grind #1 = p90 of the 18–22 Hz envelope over engaged-creep windows, episodes resampled.**

**The builds that measurably moved grind #1 are EXACTLY {V62, V65, V67, V68, V71C}.**

| moved grind #1? | build | grind-#2 events | engaged creep-CORNER s | engaged HIGH-RATE creep s |
|---|---|---|---|---|
| **YES** | V62 · V65 · V71C | **present** | 74.2 · 189.4 · 23.0 | 21.8 · 120.3 · 6.4 |
| **YES** | **V67 · V68** | not observed | **11.5 · 0.0** | **0.0 · 0.0** |
| no | V58·V59·V61·V64·V69·V70·V71B·V72·V73·V74 | none | 3.8 – 56.3 | 0.0 – 21.8 |

⇒ 🛑🛑 **EVERY BUILD WITH ADEQUATE GRIND-#2 EXPOSURE FAILED TO MOVE GRIND #1, AND EVERY BUILD THAT MOVED
GRIND #1 EITHER SHOWS GRIND #2 OR HAS ESSENTIALLY NO EXPOSURE IN THE BURST REGIME.** The two are
**perfectly collinear** — **no build has ever demonstrated one without the other at usable power.**
★ Corpus-wide, all **13** merged events fall in the **29.4%** of dosed non-highway exposure held by the
two "both lanes up" groups: **p = 1.2e-7**. V71C alone holds **3 of 13** in **5.28%** of exposure,
**P(≥3) = 0.028**.
🛑 **DO NOT PROPOSE A RATE-LANE GRIND-#1 FIX AS IF THE TRADE WERE SOLVED.** It has never been separated.
The cheapest way to break the collinearity costs no bytes: **~90 s of deliberate ENGAGED hard cornering
at creep** on the next rate-lane build. Scripts: `analysis-2020accord/grind2_collinearity.py`,
`grind2_delivered_verdict.py`.

### (A) THE `sar` vs (B) THE MULTIPLIERS — **(A) IS DEAD** [EVIDENCE, 2026-08-06]
`sar 0x9` is carried by **V62, V65, V71A ONLY** (byte-read; the `BUILD-LINEAGE` ledger correction holds).
**V71C has both `sar` sites STOCK at `0x3AB76`/`0x3AC20` and produced a grind-#2 event**, so "V62's `sar`
is what causes grind #2 ⇒ a `sar`-stock build is safe" is **refuted**:
- one merged event, `r58s1` t = 11.6–16.7 s, v 1.77–2.05 m/s, |ang| 392°, engaged
- p99 = **1741.9** vs a max of **142.2** on *any* non-bursting build's engaged creep ⇒ **12.2×**
- **spectrally identical** — peak **44.31 Hz** at 0.198 Hz resolution, P = 106,227 against a
  same-segment non-burst floor of **25.5** (V65 43.29 Hz, V62 41.81 Hz).
  ⚠ A coarse 0.396 Hz pass reads 46.29 Hz; **the fine pass is the correct one.**
- V71C's own **manual arm is byte-stock** on the same drive, same day, same road: max 70.6, zero events
⚠ **It is n = 1.** Enough to refute (A); **not** enough to size the effect.

### THE FLIGHTS — the operator was right on all six calls
**V71B/`r54`:** grind #1 **545** (inside the stock pool; indistinguishable from V69 P=0.84 / V70 P=0.22);
grind #2 **ABSENT and powered** (0 bursts, P(0)=0.0002 engaged / 0.0098 manual); ratchet present, 171.5 s.
**V71C/`r58`:** grind #1 **223** (excluded lower than stock P=0.0006; excluded **higher** than V67
P=0.0215); grind #2 **PRESENT engaged**, **7 burst windows in the ALL-SPEED cell / 3 in the CREEP cell**
(🛑 **LABEL THE CELL** — the same instrument gives 7 and 3 for the two cells, and quoting the bare "7"
next to a creep claim reads as 7 creep bursts, which it is not. On **merged events** the same route is
**3 events non-highway / 1 event at creep**); ratchet present, **8,521 counts p-p = corpus record**.
**V71C better than V71B at P < 1e-4 — exactly his ranking.**
★ The only functional difference between V71C and V67/V68 is `0xC6444` (3072 vs 512) ⇒ **the r26 cut is
load-bearing.** ★ **Grind #2 follows the GATE, not the hands** (ungated V62/V65 burst in both arms
equally; gated V71C only engaged) ⚠ contradicting the operator's *"worse without openpilot"* recollection.

### 🛑 FIVE RETRACTIONS THIS SESSION, FOUR OF THEM THE ORCHESTRATOR'S OWN
1. **"Grind #2 IS grind #1's 2nd harmonic"** — published as the session headline, **retracted the same
   session**. A ratio of two narrow lines is a property of their marginals; **shuffling the pairing
   reproduced it**, and every tracking SLOPE contains 0 and excludes 2.0 on four routes. The corpus's
   original *"slope 0.173, NOT a harmonic"* is **CONFIRMED**. Method rule:
   `memory/feedback-a-ratio-is-not-a-tracking-test.md`.
2. **"`0x454FE` is falsified for the ratchet"** — the test was **VACUOUS**. `gp-0x67fa == 4` reads
   **0/123,277** and **8/92,826** (all eight in PARK) ⇒ state 4 never occurs while driving ⇒ the
   substitution never ran. ★ What survives is stronger: it never runs on **stock** either ⇒ structurally
   eliminated. ⚠ **[OPEN]** V42's confirmed hard-turn fix could not have acted either.
3. **"V69/V70 dosed the wrong part of the curve"** — refuted; measured operating point is **p50 = 104
   counts** and they delivered 2.000×/3.999× there.
4. **"Modulation depth ranks the corpus"** — refuted on measured data (within-cycle depth 1.002/1.004).
5. **"V67/V68 showed zero creep grind #2" is a SHARED zero** — every non-V62 build reads 0.0, incl. stock.
   **Only V62/V65 *and V71C* have ever produced bursts.**
   🛑 **THE CLAUSE IN BOLD WAS DROPPED WHEN THIS LINE WAS TRANSCRIBED INTO `STATE.md`, and without it the
   sentence asserts the opposite of what the corpus shows** — it reads as "V71C has no bursts either",
   contradicting the table 30 lines above. Restored 2026-08-06. The original is intact at
   `docs/HANDOFF-2026-08-05-grind2-is-grind1s-harmonic-and-both-lanes-must-move.md:93` and
   `docs/V72-DESIGN.md:355`. **There was never a measurement conflict — only a lost clause.**

### OTHER DURABLE RESULTS
- ★★★★ **The engagement question is ANSWERED and the operator's objection was right:** the rate lanes read
  **ZERO** LKAS signals; `gp-0x67fa` is a **fault** state machine (33 writers decompiled); `gp-0x683c` has
  1 read / 0 writers. ⇒ the dependence is **PHYSICAL** — base damping is **exactly zero below 35.0 km/h**,
  so at creep the driver's hand is the only damping in the system.
- ✅ **`gp-0x67ac` is PROVABLY always 0** — the reduced-sum branch that would zero r24, r26 *and* damping
  is unreachable (`0xC4124` = `00 00 05 00 05 05 00 00 00 05 00`, identical across all 65 images).
- 🛑 **PWM carrier corrected 8 kHz → 4.000 kHz** (PCLK is 40 MHz). ⇒ `gp-0x6ac0` = 30 × f_electrical.
- ✅ **Axis scale settled at 4.7121 counts/column-deg-s**, three ways; **P × G = 56.5**. The 0.58901
  candidate is the right factor on the **wrong CAN copy** (`0x14A` packs `(-gp-0x6a56)>>3`).
- 🛑 **The ratchet's Q is NOT measurable at any window length** — Q(2N)/Q(N) = **2.06**. The recorded
  Q ≈ 40 is a window artefact. ⚠ *"A hand on the wheel kills it"* does **not** generalise (p = 0.31/0.39),
  though engagement-conditionality replicates at **p = 6.3e-13** with manual hands-off **1/150**.
- ⚠ **Two `BUILD-LINEAGE.md` ledger errors:** `0xC6442`/`0xC61F6` attributed to V39 were **never written
  by any build**; and **V71B/V71C carry NEITHER of V62's `sar` bytes** (those are V62/V65/V71A only).

### ⇒ ★★★ THE FLIGHT INSTRUCTION — load-bearing, and it costs nothing
**Drive deliberate ENGAGED hard cornering at creep** — < 4 m/s, sustained driver torque ≥ 1200,
|angle| ≥ 100°, **openpilot engaged**, ~**90 s**. The corpus has **essentially no unprovoked engaged
corner exposure**: V67 and V70 have **2 engaged corner blocks each, P(0) ≈ 0.69**. Ninety seconds takes
the power from ~25% to ~80% and settles grind #2 on one drive, whichever way it falls.

---

★★★★ **THE HEADLINE, 2026-08-04 (LATEST): THE CAR WAS MISSING BOTH OF ITS CONFIRMED FIXES. V70 FLEW AND
GRIND #1 IS BACK AT THE STOCK LEVEL. THE DOSE AXIS THIS KIT HAS USED SINCE V62 IS THE WRONG LANE — r24
IS NEAR-INERT AND r26 IS LIVE. AND THE RATCHET IS ENGAGEMENT-***REQUIRED***, WITH NO BUILD IN THIS KIT
HAVING EVER MOVED IT. ⇒ V71 IS BUILT: BOTH FIXES RESTORED, PLUS A PROBE THAT READS THE GAIN IN FORCE.**

🛑🛑 **Read `RULE 3` at the top of `docs/BUILD-LINEAGE.md` before anything else in this file.**
Full narrative: `docs/HANDOFF-2026-08-04-both-confirmed-fixes-were-off-the-car.md`.

---

## 🛑🛑 1. BOTH CONFIRMED FIXES HAD FALLEN OFF THE CAR

**[EVIDENCE — byte-read across all 60 `_v*_plain_image.bin` in `../accord-firmwares/analysis-2020accord/`.]**

| lever | what it did | recorded as | actually carried by | how it was lost |
|---|---|---|---|---|
| **`0x454FE`** `65BA`(`bne`) → `65B5`(`br`) | V42's **state-4 governor ratchet** kill | *"CONFIRMED ROOT CAUSE, carry forward"* | **V42–V52C only**; **stock in V53 → V70** | 🛑 **silent rebase loss** — V53+ descends from the V38/FOURFRAME branch point, which is *before* V42. **Nobody decided this** |
| **`0x3AB76` + `0x3AC20`** `sar 0xa` → `0x9` | V62's **×2 on BOTH rate lanes** — the kit's only measured grind-#1 fix (8× at creep, 42× at \|rate\| 16–32) | the reference "2×" rung of the dose ladder | **V62 and V65 only** | ⚠ removed as **V66's confirmatory control**, **never restored**; the effect was then re-created twice in encodings that dose **r24 only**, and the ladder kept calling those "2×" |

⇒ **From V66 to V70 the car carried NEITHER.** 🛑 **The `0x454FE` case is worse than bookkeeping:** the
argument that later retired it as a cause of the *current* ratchet — *"`STEER_STATUS == 4` fires
0/37,922"* — was **voided** when bus `STEER_STATUS` was shown not to be `gp-0x67fa`. **It was never
actually eliminated.** ★ **And the second case is the more dangerous general form:** a lever removed
*on purpose* as a control is, six builds later, indistinguishable from a lever that was never needed.
**When you remove a confirmed fix to run a control, write the restore into the next build's spec.**

---

## 🛠 2. ON THE CAR RIGHT NOW: **V70** (flown, route `50`). **V71 IS BUILT AND UNFLASHED.**

### THREE V71 SIBLINGS ARE BUILT AND UNFLASHED. **All three restore `0x454FE`.**

**All orchestrator-verified from the image bytes.** 🛑 **They are NOT separable on the wire** — A and C
carry a byte-identical cave, and B differs by one cave byte that never reaches the CAN payload.
**THE FILENAME IS THE ONLY PRE-DRIVE DISCRIMINATOR.**

| | image SHA256 | rwd SHA256 | rate-lane levers | probe watches |
|---|---|---|---|---|
| **V71A** | `acc62e0930c9fa8f5176e22d1751f3f9544b1228c90d0b1e09188c67448c78e5` | `5c5138d960192d7d0a4e37301a0c82ad29e02ccff0cc116b62d6ac1cb0337e9e` | both `sar` → `0x9`; **flat 2.000× at every speed** | `gp-0x6ada` (**r24**) |
| **V71B** ← **RECOMMENDED** | `d4543d02b2fa113df7ab394ba0131859e3193a8c75604ddf3165768b6e5dd3f4` | `3bc9347aa54449b2ccfe7896b076f57bf0b932ed1de3d41ae45be838ceaa8157` | `gain_A` rec0/rec1 Y[0..3] ×2; **2.000× ≤10 km/h → EXACTLY 1.000× ≥50**; r24 stock | `gp-0x6adc` (**r26**) |
| **V71C** | `30b63fdd59bdf9221fec0942d9ccdbc6f0582d2e8c3acbc4d30b0acd89ff1607` | `4ce568b6fd85ad0ad2a5a6159ede09276f705a1e00d66ac129b8f60679c4e609` | gate `0x3AA96`→`fb`; `0xC6446`=5244; **`0xC6444` 512→3072 (r26 CUT REMOVED)**; `sar` stock | `gp-0x6ada` (**r24**) |

**Which constraint each satisfies** — the four are not jointly satisfiable by any build in the set:

| | grind #1 | creep grind #2 | **highway grind #2** | ratchet |
|---|---|---|---|---|
| V71A | ✓ V62's lane (168) | ✗ **V62 caused it** | ✗ flat 2× | ✓ |
| **V71B** | ✓ r26 moved | **? UNTESTED** | **✓ STRUCTURAL 1.000×** | ✓ |
| V71C | ~ V67/V68's arm | ✓ gated ⇒ manual stock | ✗ **r24 stays 2.438×** | ✓ |

★ **Why V71B is recommended:** it is the **minimal change from V70**, the configuration the operator
reports as having grind #2 gone. It keeps V70's exact highway property (**both lanes byte-identical to
stock at ≥3200 counts, 12,221 sweep points**) and adds the one thing V70 lacks — **r26 movement**, which
every build that fixed grind #1 had (§3). Its probe watches the lane it doses.
**V71C is the fallback** if V71B does not move grind #1: it carries V67/V68's best-in-kit creep numbers
(grind #1 **109**, creep grind #2 **0 bursts**), 71 bytes off V67 = cave + `0x454FE` + `0xC6445` + CRC.

🛑🛑 **A SCALAR GATED ARM CAN NEVER BE HIGHWAY-CLEAN WHILE DOSING AT CREEP.** [EVIDENCE] The arm
**replaces** a LERP that rolls off with speed, so `arm/LERP` necessarily **rises** toward highway:
V67/V68 and V71C both deliver **r24 2.438× at 100 km/h** against V69/V70's 1.000×. No value of
`0xC6446` fixes it — lowering it enough for highway puts creep **below** stock. ⇒ **only the ungated
speed-shaped surface (V71B's route) can be structurally stock at highway.** ⚠ This also corrects a
premise used to justify V71C: V67/V68 differs from the highway-clean builds in **BOTH** lanes (r26 cut
~5× **and** r24 raised 2.438×), so **V71C removes only one of two candidate causes.** Named follow-up
if r24 proves to be the highway culprit: `0xC6446` 5244 → ~2151–2400.

★★ **On V71A, `0x3AB76` — the r26 `sar` — IS THE LOAD-BEARING HALF.** `0x3AC20` (r24) is restored **for
exact V62 parity, NOT because r24's dose is expected to matter**: the clean single-variable r24 series is
flat across a 4:1 range (§3). State it that way in any pre-flight note, so a null on r24 is not later
read as a null on the build.

⚠ **INT32 headroom at `mul r8,r6` @`0x3AB72`** (structural worst case, % of INT32_MAX): stock / **V71A**
/ **V71C** = **46.87%**; **V71B = 93.75%** — the band V62's own build note rejected. **No overflow is
reachable** (`ld.hu` bounds `avg` at 65535), but V71B has half the margin. Ceiling `0xC6444` ≤ **6553**,
re-derived as `2³¹ / ((5120 × 65535) >> 10)`; V71C's 3072 asserted inside it.

🛑🛑 **V71C's HIGHWAY r26 IS 1.15–2.31× STOCK, NOT 1.000× — "remove the cut" is EXACT ONLY AT CREEP.**
[EVIDENCE — independent audit, image re-derived bit-identically from scratch.] `0xC6444` is a **scalar
arm**; `gain_A` is a **SURFACE**. 3072 equals gain_A's value only at **0–10 km/h low rate** (grind #1's
and the ratchet's own region). gain_A rolls to **2560** at 100 km/h and lower at high rate, so the arm
**overshoots**: engaged r26 vs stock runs **1.000× → 2.308×** across the grid.
⇒ **at highway V71C has BOTH lanes elevated** (r24 **2.438×**, r26 up to **2.31×**) — nearer V62's
direction than the highway-clean builds. **This further weakens V71C as a highway fix**, on top of the
scalar-arm problem above. ⚠ No single-cal encoding is speed-shaped: a lower arm (e.g. 2560, ≤1.0× at
100 km/h) would cost **0.833× at creep**, re-cutting the region where V67/V68's 109 was measured.
⇒ **V71C's honest scope is grind #1 + creep grind #2. Do not fly it expecting a highway fix.**
★ Confirmed by the same audit: the **ONLY** row that moves vs V67/V68 is **engaged r26** (a flat
**6.000×** un-cut); r24 moves at **0 of 24,321** grid points, engaged and manual, and manual differs
from stock at **0 of 24,321** points on both lanes.
⚠ r26 saturation crosses the recorded `|dtorque|` max 839 at **avg ≈ 3333 (3.25× unity)** on V71C vs
19,997 on V67/V68 — **plausible in normal driving**, but it is a **saturation, not a wrap** (it costs
describing-function gain, it cannot produce garbage), and it is **stock's own crossing at creep**.

⚠ **V71C's probe watches `gp-0x6ada` (r24), and that is a known divergence, not an oversight.** The
audit's judgement — which I accept as reasonable and did **not** act on — is that `gp-0x6adc` (r26)
would have been the better cell, because **V71C's r24 configuration is byte-identical to V67/V68, which
flew twice**, so an r24 magnitude rung measures nothing new about *this* build, while the r26 arm is
V71C's **only** novel byte. The counter-case: r24 is the four-in-a-row zero and V71C is its most
sensitive test yet (**25.0 counts** of `|dtorque|` on the engaged arm, vs V70's 85–241 which read
0/18,010 and 0/47,990). **Left as built** because V71A already covers r24-dosed and V71B covers
r26-dosed, and V71C is the fallback, not the recommended flight. **A one-byte re-cut is available**
(cave `+0x1A`, `0x26` → `0x24`) and needs a new filename **and** a decoder entry.

🛑 **`0xC6444` IS LIVE ON V71C AND NULL ON V71A/V71B.** It is read at `0x3AB5E` **only when `lp != 0`**,
and `lp` derives from `gp-0x683c` (**zero writers**) unless `0x3AA96` is repointed. The record's STRIKE
of this cell is correct for gateless builds and **WRONG for V71C — do not strike the lever that makes
that build work.** It is a property of the **gate byte**, not of the calibration.

**Probe (all three, 68/68 cave bytes, zero spare):** bit7 liveness (seed `movea 0x10,r0,r7`, which
becomes bit7 via one `shl 0x3,r7` — 🛑 **NOT V67's `0x80`; this has already tripped one careful reader**)
· **bit6 `gp-0x671d != 0`** — ★★ **THE MASK: which gain is actually in force** · **bit5 `gp-0x67fa == 4`**
— 📋 **pre-registered BIMODAL ~100%/~0%**, a **complete** discriminator now that states 5 and 10 are
excluded · **bit4 `|mirror| >= 128`, TWO-SIDED** (⚠ the negative arm trips at **−129**: `sar` floors, so
the mismatch set against `|x| >= 128` is exactly `{−128}`, proven over all 65,536 patterns) ·
**bit3 `mirror >= 0`** — the SIGN. ⚠ `gp-0x671a` was dropped to fund the two-sided test: `bit6 = 0` can
no longer separate arm3 (2048) from the LERP (3072) — a 1.5× gain ambiguity that cannot flip a null,
since bit4 trips at 8.0 vs 5.3 counts on those branches. **`decode_v71_probe.py` refuses to run without
`--v71a` / `--v71b` / `--v71c`.**

🛑 **THE `0x454FE` JUSTIFICATION, STATED HONESTLY AND KEPT STATED:** it is restored because it is a
**confirmed fix lost by accident** — **NOT** because it is established to cause the current ratchet.
§6's symmetry tension is evidence *against* that mechanism, and V71 does not resolve it.
⚠ **KNOWN RISK, disclosed: V62 is also the build that introduced creep grind #2.** Restoring its lane
may bring it back. Given r26 is now known live, that may have been **r26's** doubling rather than
r24's — **untested.**

---

## ★★★★ 3. THE DOSE AXIS THIS KIT HAS USED SINCE V62 IS THE WRONG LANE

### 3.0 🛑 THERE **IS** A CLEAN SINGLE-VARIABLE r24 SERIES, AND IT SAYS r24 IS NEAR-INERT

**[EVIDENCE — medians recomputed from `_grind2_lib.wrecs`, not quoted from the record.]**
**stock → V70 → V69 is a PURE r24 dose series with r26 held at ×1:**

| build | r24 | r26 | median `e_18-22` (engaged creep) |
|---|---|---|---|
| stock | **×1** | ×1 | **879** |
| **V70** | **×2** | ×1 | **729** |
| **V69** | **×4** | ×1 | **746** |

**All three CIs mutually overlapping** ⇒ 🛑 **r24 is close to INERT for grind #1 across a 4:1 dose
range.** And the converse holds across the whole corpus: **every build that FIXED grind #1 changed
r26** (V62 ×2; V67/V68 ÷6.00), and **every build that changed only r24 did not.**

⇒ **The headline is NOT "nothing is single-variable".** It is: **the dose axis this kit has used since
V62 is the wrong lane.** Correct any text that says otherwise.

### 3.1 The structure — two selectors, one gate

**[EVIDENCE — orchestrator-disassembled, both selectors read out of the image.]** r24 and r26 have
**separate gain selectors** sharing **one** gate `lp`:

**`r26 → gain_A`** — `0x3AB5E ld.hu 0x7444[tp],r8` (`0xC6444` = 512, taken when `lp != 0`) ▸
`0x3AB68` `0xC643E` ▸ else **gain_A's own LERP (3072 at creep)**.
**`r24 → gain_B`** — `0x3ABFE` `0xC6442` = 1024 (the `gp-0x671d` mask arm, **outranks all**) ▸
`0x3AC08` `0xC6446` (when `lp != 0`) ▸ `0x3AC12` `0xC6440` = 2048 ▸ else **the mode-10 surface**.

⇒ **V67/V68's ONE-BYTE gate repoint at `0x3AA96` raises r24 AND cuts r26 6.00× at once.**
Net vs stock = `(5244 + 512·a) / (3072 + 3072·a)`, with `a = gp-0x69a4/1024`:

| `a` | net vs stock |
|---|---|
| 0 | **1.707×** |
| **0.848** | **1.000× — PARITY** |
| > 0.848 | **BELOW stock** |

**V69 and V70 edited gain_B only.** ⇒ 🛑 **every published multiplier in this kit is an r24-only number
computed at `a = 0` — i.e. a number on the lane §3.0 shows to be near-inert.**

★ **Four supporting byte facts, all [EVIDENCE]:**
1. **gain_A's four records `0xC6A68` / `0xC6A7C` / `0xC6A90` / `0xC6AA4` are BYTE-IDENTICAL across all
   11 images** ⇒ **V67/V68's ÷6.00 (= 512/3072) is EXACT, and engaged-only.**
2. **The two LERPs live in separate RAM** — `gp-0x6e40`/`gp-0x6e38` for gain_B, `gp-0x6e30`/`gp-0x6e28`
   for gain_A — filled by the **two halves of `FUN_0003ad74`**.
3. **gain_B is filled from the MODE-INDEXED arrays; gain_A from FIXED, non-mode-indexed records.**
   That is why V69/V70's mode-10 surface edit could not reach r26 even in principle.
4. **There is NO `gp-0x671d` mask arm on the r26 side** — gain_A is **2 arms + default**, not 3.

### 🛑 r26 IS LIVE — existence proof, and it REFUTES the inertness claim on-car

**[EVIDENCE]** V70's probe read `gp-0x6adc` (r26's post-clamp mirror) **strictly negative on
1,644 of 18,010 frames.** **A pinned-zero cell cannot clear a `>= 0` test.**
⇒ **"r26 is inert / r24 carries the entire lane" is REFUTED** — not merely downgraded (§9.1).

★ **New asymmetry [EVIDENCE]: `bit3 ⇒ bit4` STRICTLY** — **0 of 18,010** frames with r24 ≥ 0 while
r26 < 0. **[BELIEF]** the natural reading is *"r26 is ZERO part of the time, same-signed otherwise"*,
consistent with the shared polarity load (`ld.b -0x6752[gp],r14` @`0x3AB78`, reused at `0x3AB7E` for
r26 and `0x3AC3E` for r24).

⚠⚠ **AND HERE IS THE PART TO CARRY UNEXPLAINED — do not smooth it.** **r26 ×2 (V62/V65) AND r26 ÷6.00
(V67/V68) BOTH HELPED, and ÷6 helped MORE** (median 168 vs 109 against stock's 879). **A monotone
"more r26 damping is better" story and a monotone "less is better" story are both refuted by the same
two rows. The corpus cannot say why, and that is the leading open question of this session.**
🛑 **Anyone proposing an r26 dose must state which direction they are betting on and why** — the record
does not supply it.

★ **Independent bus-side support for the r26 attribution, arrived at WITHOUT the disassembly
[EVIDENCE]:** median `e_18-22` by **bar-torque reversal count**, engaged creep — in the **rev ≥ 40**
regime (where the ratchet lives), **V62 reads 396 against 1155–1403 for V59 / V64 / V69 / V70.**
**V62 is the odd one out, and it is the only build with r26 ×2.**

✅ **V62's `sar` route is the ONLY encoding whose dose is exact independently of `a`** — it scales both
lanes identically, **2.000× on the total for every value of `a`.** That is why V71 restores this route
rather than re-deriving the dose through a cal arm.

### The ladder, re-read against what each build actually carried

Median `e_18-22`, engaged creep:

| build | r24 | r26 | median `e_18-22` |
|---|---|---|---|
| V61 | ×0 | ×0 | **2501** |
| stock | ×1 | ×1 | **879** |
| **V70** | ×2 | ×1 | **729** |
| **V69** | ×4 | ×1 | **746** |
| **V62 / V65** | **×2** | **×2** | **168** |
| **V67 / V68** | gated arm | **÷6** | **109** |

⇒ **r24's dose is FLAT from ×1 through ×4 (879 / 729 / 746 — §3.0), and both builds that fixed grind #1
changed r26.** [EVIDENCE] is the **flatness of the r24 rung** and the **co-occurrence**; ⚠ the
**direction** of the r26 effect is **not** established (see the unexplained ×2-and-÷6 result above).

---

## 4. ROUTE `50` — V70's FLIGHT

**`75604b0a432fdc89_00000050--50f2e00e8f`**, segments 0–2, **181.6 s**, **18,010 frames**.
✅ **FLIGHT-CLEAN:** `ST == 4` **0** and `ST == 3` **0**, on the gridded cache *and* the raw un-gridded
`0x18F` stream; watchlist absent (`steerUnavailable`/`canError`/`controlsMismatch`/`immediateDisable`).
⚠ **THE CENSUS MATTERS MORE THAN USUAL — this is a SMALL route.** Engaged **72.4 s**, manual
**107.8 s**, **engaged creep 28.9 s**, **highway ≥ 50 km/h 7.9 s**, and **ZERO manual highway
exposure**. **Segment 0 is PARKED — boot only.** Read every null below against that census, not `4f`'s.

### 4.1 🛑 GRIND #1 IS BACK AT THE STOCK LEVEL — [EVIDENCE]

Median `e_18-22`, engaged creep: **729.1**. Resampling **V70's exact 5-block structure** from each arm:

| arm | verdict |
|---|---|
| stock | **CONSISTENT** (P = 0.635) |
| V69 | **CONSISTENT** (P = 0.495) |
| **V62 / V65** | **EXCLUDED** (P = 0.0000) |
| **V67 / V68** | **EXCLUDED** (P = 0.0000) |

Survives **(effort, |rate|)-matching**.
⚠ **The 24–28 Hz negative control is NOT flat** — V70 reads **1.88× stock** there, because provoked
steering raises the floor. Subject-band **excess over control** vs V62 is still **2.59×**, so the
exclusion survives, but the raw ratio is inflated by a floor shift.
⚠ **On the scale-free 18-22/24-28 ratio, V70 (37.4) sits BELOW stock (76.0).** 🛑 **That view does not
rank-order the builds the way `e_18-22` does. Report both; pick neither.** The disagreement is itself
the finding.

★★ **A METHODOLOGICAL CORRECTION WORTH ITS OWN LINE: CI OVERLAP IS NOT A TEST.** The
subsample-at-matched-exposure test above (resample V70's exact 5-block structure from each arm)
**excludes V62's level at P < 5 × 10⁻⁵**, where a CI comparison called the same contrast undecided.
⇒ **"V70 is not at V62's level" IS ESTABLISHED. Where V70 sits BETWEEN stock and V62 is NOT.** Both
halves of that sentence are load-bearing; quote them together.

🛑 **AND GRIND #1 IS BLIND TO r24 GAIN — this retires a MEASUREMENT TOOL, not just a hypothesis.**
Log-log slope of median `e_18-22` on r24 gain: **−0.144 [−0.991, +0.347]** — **contains 0**; stock /
V70 / V69 pairwise **indistinguishable** (P = 0.667 / 0.610 / 0.426). ⇒ **grind #1 cannot be used as an
in-force check for the r24 lane on ANY future build.** That is a **structural** limit, not a power
limit — more exposure will not fix it. ⊕ It also means **grind #1 cannot adjudicate the bit6
(a)-vs-(b) question** (§5.1), so the bit6 zero carries that diagnostic load alone.

### 4.2 GRIND #2 — not a regression, but **"gone" is NOT established**

**0 bursts everywhere**, max **94.6** vs V62/V65's **1830.7**. But at V62's own burst rate:
**P(0) = 0.34 engaged-creep · 0.56 corner · 0.98 highway**; power **66% / 44% / 2%.**
⇒ **the highway cell says nothing at all.** And **V67 already eliminated engaged-creep grind #2**
(P(0) = 0.0005), so a clean V70 creep arm **REPLICATES an already-clean arm — it does not credit V70.**
🛑 **Do not write this up as "V70 fixed grind #2".**

### 4.3 ★★★★ THE RATCHET — ENGAGEMENT-**REQUIRED**, Q ≈ 40, AND NO BUILD HAS EVER MOVED IT

#### 4.3.1 🛑 ENGAGEMENT-**REQUIRED**, NOT ENGAGEMENT-CONDITIONAL — the grip confound is removed

**[EVIDENCE]** Both arms **hands-off** (`|lowpass(tq, 3 Hz)| ≤ 300`), **creep < 4 m/s**, pooled over
**four routes and four builds**:

| route | engaged hands-off | manual hands-off | Fisher p |
|---|---|---|---|
| V70 `r50` | 4/5 = **80%** | 0/35 = **0%** | 5.5 × 10⁻⁵ |
| V69 `r4f` | 22/27 = **81%** | 0/20 = **0%** | 9.4 × 10⁻⁹ |
| V62 `r37` | 31/39 = **79%** | 0/39 = **0%** | 2.3 × 10⁻¹⁴ |
| V59 `r2c` | 16/17 = **94%** | 0/24 = **0%** | 1.7 × 10⁻¹⁰ |
| **POOLED** | **73/88 = 83.0%** | **0/118 = 0.0%** | **3.8 × 10⁻⁴¹** |

**ZERO hits in 118 manual hands-off creep windows / 302 s across four builds.**
⇒ 🛑🛑 **AND THE RATE IS BUILD-INDEPENDENT (80 / 81 / 79 / 94%) — NO BUILD IN THIS KIT HAS EVER MOVED
THE RATCHET.** ⚠ **This SUPERSEDES the earlier "engagement-conditional, 44/46 windows" statement** —
same phenomenon, far better-controlled data, far stronger claim.
★ **And the converse: a hand on the wheel SUPPRESSES it while engaged** — V59 94% → 14%
(p = 3.5 × 10⁻⁴), V69 81% → 37% (p = 4.5 × 10⁻³).

#### 4.3.2 ★★★★ THE TRANSITION TRACE — the mechanism, second by second, at constant speed

**[EVIDENCE — 4th-order Butterworth 6–9 Hz, `sosfiltfilt`, 2.56 s windows, hop 64; seg-local `t`,
mono = t + 100.6; orchestrator-verified from `_cache_r50/r50s1.npz`.]**

| seg1 `t` | mono | `lat` | effort | **RAW p-p** | **6–9 Hz p-p** |
|---|---|---|---|---|---|
| 27.5 | 128.1 | 0.00 | 2646 | **6502** | **190** |
| 28.2 | 128.8 | 0.00 | 2235 | **6502** | 255 |
| 33.3 | 133.9 | 0.00 | 942 | 3237 | 136 |
| **33.9** | **134.5** | **0.06** | **320** | 1423 | **134** |
| **34.6** | **135.2** | **0.31** | **441** | 3182 | **1179** |
| 35.2 | 135.8 | 0.56 | 645 | 4039 | 2156 |
| 36.5 | 137.1 | 1.00 | 998 | 5070 | **2452** |
| 46.1 | 146.7 | 1.00 | 1548 | 4204 | 910 |
| 46.7 | 147.3 | 1.00 | 2129 | 3019 | **273** |

★★ **THE HEADLINE PAIR — use this one, it is the cleanest in the corpus.** `t = 33.9` (`lat` 0.06,
effort 320) → **134 counts**; `t = 34.6` (`lat` 0.31, effort 441) → **1,179 counts**. **8.8× in 0.7 s**,
with **speed FALLING (1.75 → 1.60 m/s)** and effort roughly flat — **speed moves the WRONG way for any
confound.**
**And the death is as sharp:** effort **1,548 → 2,129** over **0.6 s** collapses the band
**910 → 273.** ⇒ **it comes on tracking `latActive` and goes off when the driver grips.**

✅ **THE 6,502-vs-591 INSTRUMENT DISCREPANCY IS SETTLED, NOT OPEN.** At mono 127.5–128.1 the car is at
`lat = 0.00`, effort **2,550–2,646**, speed 0.6–0.8 m/s, and the **6–9 Hz content is 190 counts**.
⇒ **the 6,502 peak is RAW BROADBAND — the operator cranking the wheel, not the ratchet.**
★ **THE RATCHET PROPER RUNS seg1 `t` ≈ 34.6 → 46.1 (mono 135.2 → 146.7), ~11.5 s.** 🛑 **Burst #0's
ratchet onset is mono ≈ 135.2 — NOT 123.69. That is the clean-material window; correct any text using
the older figure.**

#### 4.3.3 🛑 A CORRECTION TO THE OPERATOR'S FRAMING — the causal order, not the facts

**His hard manual provocation produced NO ratchet at all** (effort 2,500–2,900; 6–9 Hz p-p only
**422–797**, prominence **1–6**). **The manoeuvres SET UP the condition** — creep, loaded wheel, LKAS
about to take over — **and the ratchet fires when LKAS ENGAGES AND HE LETS GO.**
★ **Both parts of his account are correct; the causal order is the other way round.** His report is
**corroborated, not contradicted** — he identified the setup and the event, and named the right
segments before the data did.

#### 4.3.4 ★★★ Q ≈ 40 at f0 = 7.793 Hz — [EVIDENCE], and measured on the RIGHT data

From a **12.81 s provoked episode**. ★ **The invariance test is what makes it real:** Q reads **39.0
with a window cap of 54** and **40.0 with a cap of 111** — a window-limited estimate would have
**doubled** when the cap doubled. It did not. ⇒ **ζ ≈ 0.0125, ~3× more lightly damped than the 21 Hz
mode.**
✅ **Q ≈ 40 CONFIRMS the record's Q ≈ 36.** 🛑 **The only thing SUPERSEDED is *"Q is not measurable at
NFFT 256"* — the claim that it could not be measured, not the value.**
✅ **And it is not contaminated by the driver's input** — the episode reconciles exactly with §4.3.2
(envelope-based p-p, 2 × 2,452 = 4,904 ≈ 4,894; speed span matches `t` ≈ 33–46, i.e. the
**post-engagement** window, **not** the cranking). That was the one real risk in the discrepancy and it
is closed.
⚠ **It rests on ONE episode** — a second ≥ 10 s episode would make it two. ⚠ **f0 drift inside the
window would DEFLATE Q, so 40 is a LOWER BOUND**, not a point estimate.

Also from route 50, all [EVIDENCE]:
- **10 windows / 25.6 s at ≥ 1200 counts p-p, max 4,894.** Zero-crossing f0 **7.75 Hz**.
- **Speed-invariant:** Theil-Sen **+0.068 [+0.005, +0.247]** Hz per m/s vs wheel-order-1's **0.482**.
- **In the bar (prom 59), angle-rate (22), angle (15) — and NOT in openpilot's command (1.25)**
  ⇒ **the loop closes inside the EPS + plant.** Replicates `4f`.
- **Per-engaged-window ratchet rate is identical across builds** — V70 **32.1%**, V69 **34.4%**,
  V62 **32.8%** ⇒ **V70 did not add ratchet events**, consistent with §4.3.1's build-independence.

#### 4.3.5 ⇒ WHAT THE BUILD-INDEPENDENCE BUYS

★★ **`0x454FE` is a genuinely UNTESTED lever for the ratchet** — it has **not been on the car during a
single one of the four measurements above** (V59, V62, V69, V70 are all post-V53, all stock at
`0x454FE`). ⚠ **That is a reason it is worth restoring; it is NOT evidence that it will work**, and
§6's symmetry tension still argues against the mechanism.
★★ **And four facts now fit into one picture:** *engagement-required* + *hands-off-conditional* +
*Q ≈ 40* + *base-assist damping exactly ZERO below ~35 km/h* ⇒ **at creep, the driver's hand is the
only damping in the system.** That is what makes §8's deferred FactorC/FactorE lever materially more
compelling than when it was filed.

### 4.4 "STIFFER" — no bus-side instrument sees it, and the proposed mechanism is REFUTED

**[EVIDENCE — arithmetic.]** The clamp at `0x3AC42` is **HARD** (`clamp(., ±0x2000)`), **exactly linear
below the rail**, and **V69 spent 0.0000% of engaged time at or above its 683 rail** (max **633.9**).
⇒ **there is no compression difference to feel — the saturation story is REFUTED** (§9.4).
Effort/impedance put V70 at **0.79–0.97×** every predecessor, **every CI containing 1**.
**[BELIEF]** the likeliest referent is **the ratchet itself** — 4,894 counts at Q ≈ 40 arriving 0.8 s
after engagement. No instrument separates "stiffer steering" from "a big ratchet event early".

---

## 5. THE PROBE READOUTS (V70, route 50)

### 5.1 🛑🛑 bit6 (`gp-0x6ada >= +512`) READ **ZERO — 0/18,010 — AND IT IS NOT VACUOUS**

**[EVIDENCE]** A replay through the **shipped** surface driven by **route 50's own data** predicts
**311 hits**; **stock predicts 52.** Observed **0**. And `|dtorque|` off a 100 Hz grid is a **LOWER**
bound, so **the gap cannot be closed in the safe direction.**
⇒ **delivered gain < ~1574 Q10, below stock's 3072** ⇒ 🛑 **`0xC6442` = 1024 — the `gp-0x671d` mask
arm — is the only arm in the selector that predicts exactly 0.**
✅ **The identification is NOT the problem:** the orchestrator verified first-hand that
`0x3AC42`–`0x3AC54` is `r24 = clamp(r6, ±0x2000)` and that `0x3AD5A st.h r24,-0x6ada,gp` stores exactly
that, r24 unclobbered through the add chain.
⚠⚠ **BUT THE ARM-SELECTION READING IS THE WEAKER ONE — SOFTENED 2026-08-04, and this matters.**
**The same rung read 0 / 47,990 frames on V69's route `4f`, at DOUBLE V70's dose**, where it needed only
**49 counts** of `|dtorque|` against a repo max of **839**. **That anomaly is far larger than V70's, and
it does NOT fit arm selection**: under (b) the mask arm is **1024 on every build**, so it cannot produce
a **dose-dependent** miss. And **V67's probe read `gp-0x671d` 0 / 150,327 on route 47**, so the mask
would have to be set near-continuously on `4f` *and* `50` but never on `47`.
⇒ **[BELIEF] (a) — an under-ranged or MIS-RECONSTRUCTED rung — is the better-supported reading.** The
`dtorque` figure is a **4-sample 1 kHz difference rebuilt from a 100 Hz bus copy of a different,
filtered torque cell**; polarity is the other candidate. **(b) arm selection is possible but less
parsimonious. The corpus cannot settle it** — and per §4.1, grind #1 cannot adjudicate it either.

🛑 **THE DURABLE PART IS THE LESSON, NOT THE MECHANISM: this is the FOURTH probe in a row to return an
uninterpretable zero by reading a lane OUTPUT.** ⇒ **read the GAIN IN FORCE, not a lane output.**
✅ **V71 answers it both ways** — `gp-0x671d` **directly** (bit6), plus a **two-sided, low-threshold**
r24 mirror rung so an under-ranged reconstruction cannot hide again.

### 5.2 ★★ bit5 (`gp-0x67fa == 10`) = **0.0000%** — FIVE BUILDS VINDICATED

**[EVIDENCE]**, encoding independently verified. ⇒ **the aggregator ran** ⇒ **state ∈ {4, 5, 11}** ⇒
**`FUN_00036388` and `FUN_000428d4` WERE INVOKED.**
⇒ 🛑 **the `gp-0x67df` detector nulls on V64 / V67 / V68 are GENUINE, and the state-gate explanation
for them is REFUTED.** The **pre-registered** prediction (*"bit5 reads LOW"*) held, which is what makes
this interpretable rather than a lucky null.
⚠ **It licenses "the call was made", NOT "the body ran."** `FUN_00046ea6(5)` on `gp-0x18d0` bit 5 —
the detector's second, independent entry gate — **remains OPEN.**

### 5.3 bit4 / bit3 — the r26 pair
See §3. **bit4 tracked bit3 ⇒ r26 is LIVE**, and `bit3 ⇒ bit4` holds **strictly** (0/18,010 violations).

---

## 6. THE STATE MACHINE — THE CADENCE IS REFUTED AT INSTRUCTION LEVEL

**[EVIDENCE — instruction level; gp-relative *and* absolute encodings both checked.]**

**`gp-0x68ad` can NEVER be set in the field.** Both SET paths need permanently-zero flags: `gp-0x437c`
(a UDS artifact) and — **newly closed** — `gp-0x679d`, whose sole writer `FUN_000567c0` @`0x567e2`
reads `gp-0x67ba`, and **`gp-0x67ba` has exactly ONE access image-wide and ZERO writers.**
`FUN_00019970` opens with `if (gp-0x68ad != 1) return;` ⇒ **4 → 5 NEVER FIRES; state 5 is DEAD CODE on
the road.**

**`gp-0x6d78` bit 15 is a ONE-WAY, OR-ONLY latch** — 15 sites, one writer (`FUN_000197b8` @`0x197ca`,
`|= 1<<n`), **no clear anywhere image-wide** ⇒ **4 → 10 is a ONE-SHOT DRIFT; 10 → 4 can never fire
afterwards.**

⇒ 🛑 **State 4 is STICKY once entered, then leaves permanently. There is NO periodic cadence** —
**refuted structurally, not merely unconfirmed.** With §5.2's 0.0000%, **the reachable set on a normal
drive is {4, 11}.**

⚠ **A TENSION TO CARRY, not to resolve by assertion.** The V42 substitution is **ASYMMETRIC** (it
clamps command-magnitude *increases* and passes *decreases*), so continuously active it should print a
**rectified** waveform. **Yet the ratchet measures SYMMETRIC** — skew **−0.16 … +0.06**, crest
**2.07–2.45** against a sine's 1.414. ⇒ **evidence AGAINST the state-4 substitution shaping the
CURRENT ratchet.** It is *not* evidence that restoring `0x454FE` is wrong — see §2 for how V71 states
its justification.

✅ **Safety re-verified against `_v70_plain_image.bin` [EVIDENCE]:** `FUN_0004595a` `[0x4595A,0x45A1F)`
and `FUN_000462e6` `[0x462E6,0x46360)` are **0 diff bytes vs stock**; the DTC-0x1d-no-debounce path is
unchanged. The *"the substitution only ever makes `gp-0x6ace` smaller ⇒ safe side"* argument
**transfers**, but remains **[INFERRED]**, not verified. `0x454FE` sits in the bridged main CRC block
`[0x13000, 0xC4FFC)`.

🛑 **[OPEN]** what sets `gp-0x6d78` bits 15/16 mid-drive — `FUN_000197b8` has **21 callers, untraced**.
That decides whether state 4 is sticky for a whole drive or only briefly.

---

## 7. THE AGGREGATOR IS ELIMINATED

**[EVIDENCE — every ceiling byte-read.]** **All EIGHT zero-type range gates are STRUCTURALLY VACUOUS** —
each capped by its own producer's ceiling at or inside its gate window, **on every drive, every build**:

| lane | producer ceiling | gate window |
|---|---|---|
| boost | 512 | 2048 |
| damping | **exactly 0 at creep** (FactorC `0xD27BC` Y[0] = 0, multiplicative; ≈ 35 km/h onset); ≤ 1024 at highway | 2048 |
| friction | 511 | 1024 |
| magnitude | ±0x3000 | **== window, exactly, inclusive** |
| LKAS | ±0x2800 | **== window, exactly** |
| `gp-0x6ade` | **0 writers** | — |
| resonance | max 1024 (**164–341** at the ratchet's speeds) | 2800 |
| return-centre `gp-0x6b62` | max 5786 | 8192 |

⇒ **the aggregator stage contains NO reachable hard nonlinearity**, joining the aggregator **SUM**
(V65, 120,049 frames). **The relay / limit-cycle framing for the aggregator is REFUTED** (§9.3).
★ Also [EVIDENCE]: `FUN_00036388`'s own counters give **~20–40 ms or ~1 s** periods — nowhere near
7.8 Hz ⇒ **it INHERITS the ratchet, it does not GENERATE it.**

---

## 8. ⚠ DEFERRED TO V72 — deliberately not stacked on V71

★★ **ONE LEVER, AND IT IS NOW MATERIALLY MORE COMPELLING THAN WHEN IT WAS DEFERRED: FactorC + FactorE
TOGETHER, re-read against the RATCHET.**
**Base-assist damping is EXACTLY ZERO below ~35 km/h** (FactorC `0xD27BC` Y[0] = 0, multiplicative)
while **the ratchet lives at 4.9–8.0 km/h with Q ≈ 40.** And **V47 — FactorC and FactorE raised
TOGETHER — reported *"marginally quieter at 5 mph"*** and was filed **null against the 21 Hz
vibration.** 🛑 **That positive whisper has never been evaluated against the RATCHET.**
★★ **§4.3 is what strengthens it.** *Engagement-required* + *hands-off-conditional* + *Q ≈ 40* +
*base-assist damping exactly zero below ~35 km/h* fit into a single picture:
**at creep, the driver's hand is the only damping in the system.** ⚠ **Still DEFERRED** — it is a
two-cal change on a lane V47 already touched, and it deserves its own single-variable drive.

🛑🛑 **STRUCK 2026-08-04 — `0xC6444` IS NOT A LEVER. IT IS A NULL BY CONSTRUCTION.**
**[EVIDENCE]** `0xC6444` is read **only** at `0x3AB5E`, and **only when `lp != 0`**. On **every gateless
build** — stock, V62, V65, V69, V70, **V71** — the gate `0x3AA96` is `c5`, so `lp` derives from
`gp-0x683c`, which has **0 writers image-wide** ⇒ **that load never executes.** **Raising it changes
NOTHING** unless `0x3AA96` is *also* repointed — which reintroduces **the V67/V68 control path the
operator rejected.** ⇒ **this supersedes the standing *"candidate, not a recommendation"* framing;
it is not a candidate at all on the builds this kit is flying.**

---

## 9. 🛑 RETRACTIONS THIS SESSION — recorded as retractions, with what replaced each

1. **"r26 is INERT / r24 carries the entire lane" — REFUTED ON-CAR.** LEG 2 was the last leg holding it
   up; V70's bit4 killed it (1,644/18,010 strictly negative). **Replaced by §3.**
2. **The "peak-velocity / rateKey collapse" hypothesis — DEAD ON SCALE B, ALIVE ONLY AT THE ~90th
   PERCENTILE WORST INSTANT ON SCALE A. (A sharper retraction than "refuted", and the honest one.)**
   🛑 **Its founding number was never a burst measurement.** `A_rk = 1927` is
   `v70_parametric_gain_collapse.py:132` — **the top decile of the WHOLE-DRIVE `|rate|` distribution
   (hard manoeuvres)**, not the rate index during a grind. **Measured directly over 424 burst
   windows**, the oscillation's own 18–22 Hz rate swing is **p50 140 / p90 327 counts**; even **raw**
   max `|rate_c|` in-window is **p50 542**. The monotone window needs **A_rk ≳ 1400**, reached by
   **9.20%** of windows on scale A and **0.00%** on scale B.
   Corroborating: grind #1 lives **97.8% (scale A) / 100% (scale B)** inside the flat `[0,400]` rate
   segment over **19,378 burst samples / 11 routes**; re-pricing made Spearman **worse**
   (−0.638 → −0.657). ⚠ **The two analysts disagreed and the orchestrator adjudicated — record the
   adjudication:** the outcome data (V70 excluded from V62's class at P < 5 × 10⁻⁵) is **sound**, but
   the rateKey axis is the **bus angle rate converted by an assumed scale** while `gp-0x6ac0` is the
   **motor/resolver rate** — **a proxy that cannot settle it either way.**
   **Replaced by:** §3 — r24 is near-inert and the lane was never the r24 lane, which accounts for the
   same outcomes **with no rateKey claim at all.**
3. **The aggregator zero-gate / relay hypothesis — REFUTED** (§7, all 8 vacuous).
4. **"V69 ran just under saturation, so V70 feels stiffer" — REFUTED** (§4.4; hard clamp, 0.0000% at
   the rail).
5. **"Q is not measurable at NFFT 256" — SUPERSEDED** (§4.3). 🛑 **Note the scope precisely: Q ≈ 40
   CONFIRMS the record's Q ≈ 36. The only thing superseded is the claim that Q could not be
   measured** — not the value. ⚠ one episode; lower bound.
6. **The "non-monotone dose–response with a minimum near 2×" is RETIRED.** It priced **every** build on
   r24 alone at `a = 0`; with r26 live, V62/V65's "2×" and V69/V70's "2×/4×" were never the same
   quantity. **Replaced by §3.**
7. 🛑 **"Grind #1 can be used to check whether an r24 dose is in force" — RETIRED as an INSTRUMENT**
   (§4.1). Log-log slope **−0.144 [−0.991, +0.347]**, pairwise P = 0.667 / 0.610 / 0.426. **Structural,
   not a power limit.** **Replaced by:** V71's `gp-0x671d` mask rung, which reads the gain in force.
8. ⚠ **"The ratchet is engagement-CONDITIONAL (44/46 windows)" — SUPERSEDED by a far stronger,
   better-controlled statement: it is engagement-REQUIRED** (§4.3.1; **0 of 118** manual hands-off
   creep windows across four builds, and the rate is **build-independent**).
9. ⚠ **The bit6 "arm-selection" reading is DOWNGRADED to the weaker of two candidates** (§5.1) —
   it cannot explain the **dose-dependent** miss on route `4f`. **Replaced by:** [BELIEF] an
   under-ranged or mis-reconstructed rung, with the corpus unable to settle it.
10. 🛑 **`0xC6444` is STRUCK as a lever — a NULL BY CONSTRUCTION, not "untested upward"** (§8). It is
    read only at `0x3AB5E` and only when `lp != 0`; on every gateless build `gp-0x683c` has 0 writers,
    so the load never executes. **This supersedes the standing "candidate, not a recommendation"
    framing.** ✅ **BUT A SINGLE-VARIABLE r26 TEST DOES EXIST — via `gain_A`'s RECORDS, not the arm.**
    [EVIDENCE, orchestrator byte-read] `gain_A` has the **same 4-record × 4-point layout on the same
    `0xC6010` speed cross-axis** (`[0, 640, 3200, 6400]` counts = `[0, 10, 50, 100]` km/h) as `gain_B`:
    rec0 `0xC6A68` Y=[3072,3072,2434,2048] · rec1 `0xC6A7C` Y=[3072,3072,2488,1536] · rec2 `0xC6A90` ·
    rec3 `0xC6AA4`. ⇒ **doubling rec0/rec1's WHOLE rate axis doses r26 alone, below 50 km/h, and is
    EXACTLY 1.000× at and above 50 km/h by construction** (rec2/rec3 untouched — V69/V70's proven
    structural guarantee, applied to the lane that actually matters). **That is V71B.**

---

## ⇒ ★★★ NEXT

1. **Fly V71** (operator's call; flash only on explicit instruction naming the file and the bus). It is
   the **first build since V65 whose rate lane is byte-identical to a twice-flown, flight-clean
   configuration**, plus a lever the record says was confirmed and then lost by accident.
2. **The two verdict-affecting reads V71 buys:** **bit6 `gp-0x671d != 0`** answers §5.1's four-in-a-row
   zero directly — *which gain is in force* — and **bit5 `gp-0x67fa == 4`** is a **complete**
   discriminator now that 5 and 10 are excluded, **pre-registered bimodal**.
3. 🛑 **Do not stack V72's two levers onto V71** (§8). One of them (FactorC/FactorE) is the most
   under-examined positive whisper in the archive and deserves its own single-variable drive.
4. 🛑 **Do not re-quote any pre-2026-08-04 rate-lane multiplier without saying it is r24-only at
   `a = 0`** (§3).

---

★★★ **THE PRIOR HEADLINE, 2026-08-04: V69 FLEW AND GRIND #1 CAME BACK AT CREEP.**
→ Kept for the route `4f` measurements, which stand. 🛑 **THREE of its conclusions have since
been retracted or superseded and are marked in place below:** its **dose–response ladder** priced every
build on r24 alone at `a = 0` (**RETIRED** — THE HEADLINE §3), its **§7 "r26 is inert" split** is now
**REFUTED on-car** (THE HEADLINE §3), and its **§4 "Q is not measurable"** is **SUPERSEDED**
(**Q ≈ 40**, THE HEADLINE §4.3).

**Route `4f--61171e660d`** — 8 segments, **481.7 s**, 47,990–47,996 frames. Full narrative:
`docs/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md`.
✅ **FLIGHT-CLEAN, two methods:** `ST == 4` **0** and `ST == 3` **0**, on the gridded 100 Hz cache *and*
on the raw un-gridded `0x18F` stream; watchlist absent (`steerUnavailable`/`canError`/
`controlsMismatch`/`immediateDisable` 0), `steerSaturated` **2** and `steerOverride` **667** ordinary.
✅ **BUILD IDENTITY FROM THE PROBE, NOT THE FILENAME.** byte4 = `0x87` on **100%** of frames, bit7
liveness set, **bit3 = 0 ⇒ V68 excluded absolutely.** ★ V66/V67 are excluded **empirically**, which is
stronger than the pre-flight note allowed: their bit6 is `gp-0x6806` ≈ `latActive` at 99.98%, and `4f`
is **345.7 s engaged with bit6 = 0 in every frame.** V69-×2 is excluded **structurally** (its `0xC4B54`
`61`→`60` makes bit4 constant 1). RWD `e62fcbba…` matches the record.

### 1. ★★★★ GRIND #1 IS BACK, AT CREEP — CONFIRMED

**EVIDENCE.** Engaged pooled 18–22 Hz: **f0 20.42 Hz, prominence 13.47** (criterion > 4); f0
**identical across all 8 search bands**; the manual arm reads **1.25 = no line**. Present in **6 of 8
segments**, absent on **seg 6** — the only pure-highway segment.

★ **The order veto is cleared by a contrast a tyre cannot fake** — a wheel or engine order does not know
whether LKAS is on. Engaged-vs-manual, **within route**, speed-matched: **4.726 [1.082, 18.20]** against
a null of **[0.36, 3.24]**, with the 24–28 Hz negative control and the 1–4 Hz validity check both inside
their nulls.

| contrast | ratio | null |
|---|---|---|
| V69 / Kd2 (V62 + V65) | **1.381 [1.026, 1.724]** | [0.83, 1.16] |
| V69 / Kd2-gated (V67 + V68) | **1.654 [1.244, 2.167]** | [0.88, 1.13] |
| **creep < 20 km/h, V69 / V62 (r37) — block unit** | **2.244 [1.438, 3.191]** | — |
| **creep < 20 km/h, V69 / V62 (r37) — episode unit** | **2.235 [1.533, 3.429]** | — |

⚠ **The ALL-SPEEDS headline loses its CI under the conservative episode unit ([0.870, 2.598]); THE CREEP
RESULT DOES NOT** — it holds under **both** resampling units. Quote the creep number; never quote the
all-speeds number without this caveat in the same sentence.

★ **"Lands on stock at ≥ 50 km/h" — CONFIRMED.** **1.066 [0.690, 1.677]** vs the Kd1 pool and
**0.789 [0.515, 1.252]** vs V59/r2c, both inside null, validity passes. That is the speed shaping's
structural prediction, measured. ⚠ **The other half — "elevated vs V67/V68 at highway" — is WEAK**: its
24–28 Hz negative control moves as much as the subject band. **Do not lean on it.**

★★ **SATURATION IS ELIMINATED — the dose was fully delivered.** Transfer-corrected `|dtorque|` max
**633.9**, **0.0000%** above V69's 683 rail ⇒ **≥ 99.9% of engaged time received the full 4.000×.**
The pre-flight 0.81× margin worry did not bite, and the result below **cannot** be explained as clipping.

🛑🛑 **RETIRED 2026-08-04 — READ THE HEADLINE §3 INSTEAD. The ladder below prices EVERY build on r24
alone at `a = 0`.** r26 is now known **LIVE** on-car (1,644/18,010 frames strictly negative), so
V62/V65's "2×" (both lanes, via `sar`) and V69/V70's "2×/4×" (gain_B only) **were never the same
quantity**, and *"a minimum near 2×"* was an artefact of pricing them as if they were. The **numbers**
below are measurements and stand; the **dose labels** on them do not.

★★★ **THE DOSE–RESPONSE IS NON-MONOTONE — the session's central result.** Median `e_18-22`, engaged
creep:

| dose | build | median `e_18-22` |
|---|---|---|
| 0× | V61 | **2501** |
| 1× (stock) | — | **879** |
| **2×** | **V62 / V65** | **168** |
| **2× gated** | **V67 / V68** | **109** |
| **4×** | **V69** | **746** |

**The minimum is around 2×.** ⚠ These are **cross-route medians without covariate matching** — read them
*beside* the matched contrasts above, not instead of them.

★★ **THE EFFECT IS ENGAGEMENT-CONDITIONAL THOUGH THE DOSE IS NOT.** V69's 4× applies **identically in
both arms** (the gate is reverted; the speed surface does not know about LKAS). Yet **manual at 4× is
indistinguishable from stock — 1.070 [0.383, 1.396], inside null** — while engaged is **2.244×**.
⇒ **the mechanism is inside the CLOSED LKAS LOOP, not open-loop damping quality.** A plain
"too much derivative feedback is harsh" story predicts the manual arm moves too. It does not.

🛑 **THE MECHANISM IS NOT UNIQUELY DETERMINED — record as BELIEF, with the dose–response as the
EVIDENCE.** Two candidates both fit every number above:
**(a)** a plain derivative-feedback optimum, overshot;
**(b)** a **parametric gain collapse** — `gp-0x6ac0` is loaded **`ld.hu` (UNSIGNED) @ `0x3AAC4`**, so the
gain index sweeps **0 → peak → 0 twice per cycle**, and V69 turned Honda's **2.0× rate rolloff into
8.0×**, making the damper **weakest at peak velocity**.
🛑 **PROVENANCE CORRECTION 2026-08-04 — `A_rk = 1927` WAS NEVER A BURST MEASUREMENT.** It is
`v70_parametric_gain_collapse.py:132`, the **top decile of the WHOLE-DRIVE `|rate|` distribution**
(hard manoeuvres), not the rate index during a grind. Measured directly over **424 burst windows**, the
oscillation's own 18–22 Hz rate swing is **p50 140 / p90 327 counts**, and even raw max `|rate_c|`
in-window is **p50 542**. The monotone window needs **A_rk ≳ 1400** — reached by **9.20%** of windows on
scale A and **0.00%** on scale B. ⇒ **the hypothesis survives on scale A only, at the ~90th-percentile
worst instant, and is DEAD on scale B.** See THE HEADLINE §9.2.
Modulation depth at `A_rk` 1927: **1.00×**
(V67's flat arm) / **1.49×** (V62) / **5.96×** (V69), with the effective-gain crossover at `A_rk` ≈
**1300** (orchestrator) and **1200–1330** (`RateLaneTrace`, Fourier on the integer chain) — **two
methods.** ⚠ (b) explains the engagement-conditionality more naturally, but that is not a discriminator
on its own. **Do not build as if (b) were settled.**

### 2. GRIND #2 — a replication, not a result; and one hypothesis refuted

Creep **0 bursts**, engaged **P(0) = 0.0042** — but **V67 already gave 0 bursts in 158.7 s at
P(0) = 0.0005**, so this **REPLICATES an already-clean arm.** ⚠ The corner cell is **under-powered on
`4f`**: engaged 26.9 s (P(0) = 0.128), manual 42.2 s (P(0) = 0.079).

★ **The genuine non-regressions.** V69's **4× did NOT re-introduce creep grind #2** (engaged max
**142.2** vs V62/V65's **1830.7**). And V69's manual creep is the **first DOSED manual arm since V65**:
0 bursts in 69.1 s, max **50.5** — the lowest of any pool, **29× below** V62/V65's 1469.6.
P(0) = **0.0512**, *just short*.

🛑 **THE "P-A" HYPOTHESIS IS REFUTED — a retraction.** P-A said V69's rate-axis **under-dose** at grind
#2's operating point (1.72× at `gp-0x6ac0` 1206) explains the null. **Premise CONFIRMED** — all 24
Kd = 2 bursts sit at p90-rate ≥ **400** counts, 19 of 24 at ≥ **1126**, **0 of 96** windows in the
lowest stratum. **Causal claim REFUTED** — in the `[1400, ∞)` stratum carrying **10 of 18** engaged
bursts, **V67 ran 99.8 s at 2.719× — MORE than V62's flat 2.000× — and produced ZERO**, expected
**12.00**, **P(0) = 6 × 10⁻⁶**. ⇒ **r24 dose at the operating point is NOT sufficient to cause grind
#2.** ⚠ Not a clean single-variable contrast (V67 also carries the `0xC646C` decouple, `0xC6CD0` = 3564,
mss0) — which is fine for refuting *sufficiency* and would not be fine for a positive claim.

### 3. ★★ THE LANE-CHANGE TRANSIENT IS DOSE-INDEPENDENT — V69's STATED PURPOSE FAILED

It **survived and is LARGER in p-p on V69** (**2,599** and **4,094** counts) than V68's recorded
**1,468**. ★ **It runs at full amplitude on the STOCK rate lane**: V58/r2b at dose **1.000×** gives
×floor p90 **14.93**, max **22.76**, **2,389 counts p-p @ 27.59 Hz**; **V59/r2c at 1.000× carries the
corpus's largest p-p, 3,283 @ 27.07 Hz.** Non-monotone — V62 at 2.000× is *quieter* than V58 at 1.000×.

| contrast | ratio | verdict |
|---|---|---|
| 2.000× / 1.000× (pooled, speed-matched) | **1.176 [0.641, 2.320]** | inside null |
| 2.403× / 1.000× | **2.897 [1.271, 11.439]** | does **not** clear its null |
| route-level Theil-Sen slope on dose | **+5.736 [−25.432, +34.934]** | **0 inside** |

★ **EXCITATION, NOT GAIN, IS THE LIVE CANDIDATE.** Within dose = 1.000× exactly, **ALC vs
driver-commanded = 2.389 [1.453, 4.898]** (null [0.44, 2.26], does not clear, one manual route). And
holding excitation fixed **collapsed the 2.403× contrast 2.849 → 2.013 with the CI crossing 1** —
*"an excitation contrast wearing a dose label"*, **the same class as the withdrawn 28 Hz "mode".**
⇒ 🛑 **V70 MUST NOT CHASE THE RATE LANE FOR THIS SYMPTOM.**

### 4. ★★★ THE RATCHET — first real characterisation, and a probe post-mortem

**Present and large on `4f`:** **46 windows / 118 s at ≥ 1200 counts p-p, peak 6,065 counts p-p.**
Seg 1 carries a **continuous 20 s** event (t = 20.5–40.9 s); seg 0 one at t = 50.4–60.7 s.
**The operator's "mostly segments 0 and 1" is confirmed exactly**, and he said it before the data did.

**Frequency median 7.79 Hz** by zero-crossing (FFT-free), **7.56 Hz** by the spectral estimator —
consistent with the recorded **7.56 ± 0.36**. **Order veto:** slope **+0.0358 Hz per m/s** vs wheel
order 1's **0.482** ⇒ **speed-invariant, not an order**; rpm 773–1724 with f0 static ⇒ **not an engine
order.**

★ **NEW: the ~7.5 Hz line is in the BAR and the ANGLE-RATE but NOT in openpilot's COMMAND** — `e4tq`
6–9 Hz prominence median **2.7** against a presence threshold of **10**, and it holds when restricted to
windows with command-rail duty ≤ 2%. ⇒ **the loop closes inside the EPS + plant. openpilot is not the
oscillator.**

**Engagement-conditional:** **44/46 windows engaged, 0 manual**; Fisher one-sided **p = 4.6 × 10⁻⁵**;
matched **6.65 [2.45, 12.85]** vs null [1.03, 3.96].
⚠ **SUPERSEDED 2026-08-04 — THE HEADLINE §4.3.1.** The grip confound is now removed (both arms
hands-off, creep < 4 m/s) and pooled over four routes: **73/88 = 83.0% engaged vs 0/118 = 0.0% manual,
p = 3.8 × 10⁻⁴¹**. ⇒ the ratchet is **engagement-REQUIRED, not merely conditional**, and the rate is
**build-independent (80/81/79/94%) ⇒ no build in this kit has ever moved it.**

⚠ **Widen the record's "creep only"** — one **4,843-count** episode at **12.7 m/s**.
⚠ ~~**Q is NOT measurable at NFFT 256** (the main lobe caps it at ~13.3) ⇒ the recorded **Q ≈ 36** is
**neither confirmed nor refuted** here.~~ 🛑 **SUPERSEDED 2026-08-04 — THE HEADLINE §4.3: Q ≈ 40 at
f0 = 7.793 Hz**, measured on route 50 from a 12.81 s provoked episode and confirmed by a **window-cap
invariance test** (39.0 at cap 54, 40.0 at cap 111). ⚠ **One episode; and f0 drift would DEFLATE it, so
40 is a LOWER BOUND.** The statement above was true of `4f`'s windows and is kept for that reason.
⚠ **The "amplitude-saturated / flat-topped" premise behind V69's rung choice is NOT what `4f` shows** —
crest **2.07–2.45** on a band-pass where a steady sine gives **1.414**, and **no flat-topping on any
filter**. **BELIEF-level re-framing; flag it for re-examination**, do not treat the saturation model as
dead.

**r24 dose ladder 0× → 4× on the ratchet: NULL and honestly UNDER-POWERED** — every CI inside its null,
and the 24–27 Hz negative control itself ranges **0.38–2.47**. Cross-build V69/V67 = **3.0× raw / 3.6×
selectivity**, **both CIs overlapping the split-half null** ⇒ **not established.**
⚠ **Route `4a` cannot speak to the ratchet** — its 149.2 s is engaged-*creep*, but the hands-off cell is
**13.0 s with zero episodes.**

### 5. ★★★ THE PROBE POST-MORTEM — three defects, and one transferable lesson

🛑 **bit4 WAS STRUCTURALLY VACUOUS — it could never have fired, on any build, on any drive.**
`gp-0x6ad4` is clamped to **±CEILING = MIN of three LERPs**. The binding one is `0xC67C2`/`0xC67C8`,
indexed on **voted vehicle speed**, **max 1024**, and it **starts at ZERO** — at the four ratchet
episodes' speeds (**4.9 / 6.8 / 7.8 / 8.0 km/h**) CEILING was **164–341**. bit4 tested **≥ 4096** ⇒
**12–25× above the lane's entire reachable range.**
**ROOT CAUSE: the design read the ERR *input* clamp `±0x2800` as if it were the lane's OUTPUT range.**
🛑 The *"40% of its ±0x2800 ZERO gate"* wording is **corrected wherever it appeared** here and in
`docs/V69-DESIGN.md`. ★ This also explains, retroactively, **why V56's mute of this lane changed
nothing** — there was very little there to mute at creep.

**bit5 was insensitive, not vacuous:** reachable max **5786** (`|gp-0x6b5e| ≤ 4762` from the trapezoid
`0xC66CC` X = [−384, −128, 128, 294, 384] Y = [0, 4762, 4762, 717, 0] with `0xC63C2` = 1024, plus a
latched `|sVar8| ≤ 1024`), so 4096 was **71% of full range** — the rung only saw the **top 29%.**

**bit6 had no exposure** — the replay predicts **~1** one-sided hit on `4f`; observed **0**;
**p ≈ 0.37.** **NOT** the V64 gate failure, but **not a positive control either**, so bits 5/4 cannot be
interpreted against it.

⇒ 🛑 **THE LESSON: both middle rungs were sized against a DOWNSTREAM GATE WIDTH rather than the lane's
own reachable output.** A gate's width says what the *consumer* accepts; it says nothing about what the
*producer* can emit. **Size every threshold against the producing lane's own clamp/LERP ceiling at the
operating point you care about, and state that ceiling in the build note.**

✅ `rlog-tools/decode_v69_ratchet.py` was **fixed in place** this session — a **128-sample floor
replaces a 256** that made its own null vacuous (its printed `0/9` was a tautology); `analog_line()` and
`matched_null()` fixed alongside. **Do not regress it.**

### 6. ★★★★ A STATE GATE NOBODY HAD SEEN — and state 10 SPLITS THE ASSIST CHAIN IN HALF

**[EVIDENCE — instruction level, `FUN_0002214a` `0x2214a`–`0x22a84`.]** 🛑 **The guard wraps the `jarl`
IN THE CALLER, not inside the four functions.** Each has exactly one call site, all in `FUN_0002214a`
(RTOS **task 1**, 1 kHz) ⇒ **in a masked-out state the callee is NEVER INVOKED — no stack frame, 0% of
body.** Index is a plain `1 << (gp-0x67fa & 0xf)`, **no off-by-one** (`0x2214e` `ld.bu` / `0x22172`
`andi 0xf` / `0x2217c` `shl`, recomputed identically @`0x221bc`–`0x221c6`). **THREE masks:**

| site | mask | states | what it gates |
|---|---|---|---|
| `0x221d6` | **`0x830`** | **{4, 5, 11}** | `FUN_00036388` @`0x22882` (return-to-centre) · `FUN_000428d4` @`0x22926` (**the OSCILLATION DETECTOR**) |
| `0x22518` | **`0x930`** | **{4, 5, 8, 11}** | `FUN_00028ea6` / `FUN_0002b422` / `FUN_0002b57a` (**ARBITRATION = `gp-0x6806`'s PRODUCER**) |
| `0x2269a` | **`0xc30`** | **{4, 5, 10, 11}** | `FUN_0003a382` @`0x226a0` (residual lane) · `FUN_0003aa2c` @`0x2291e` (**THE AGGREGATOR**) |

⇒ **IN STATE 10 THE AGGREGATOR AND THE RESIDUAL LANE RUN, WHILE THE DETECTOR, THE RETURN-TO-CENTRE LANE
AND ARBITRATION DO NOT. Assist is delivered from a stale `gp-0x6806`.**

★ **State 10 is REACHABLE IN NORMAL OPERATION** — written twice in `FUN_00019970` (the state-4 handler):
`0x199CC` (diagnostic, `tp+0x74d0 == 0xa`) and **`0x19A72` (the NORMAL path)**, the latter gated on
**bit 15 of `gp-0x6d78`** with bit 16 (→ state 11) taking priority. Writer set over **33 `st.b` sites**
(Ghidra and a raw LE byte scan agree exactly, no undercount): {1,3,4,5,6,7,8,9,10,11}, max 11.
⚠ **[OPEN] what bit 15 of `gp-0x6d78` means** — that decides how *often* state 10 is visited, not
whether it can be.

🛑 **THIS IS A LIVE ALTERNATIVE EXPLANATION FOR THE FIVE-BUILD DETECTOR NULL** (`gp-0x67df` 0/14,980
V64, 0/186,321 V67, 0/53,991 V68): *"`FUN_000428d4` was never CALLED"* has **never been on the table**,
and it has the **identical signature** to *"it ran and found nothing."*

⚠ **BUT V67's OWN PROBE ARGUES AGAINST IT, AND THIS MUST BE QUOTED ALONGSIDE.** State 10 is absent from
`0x930` too, so arbitration — `gp-0x6806`'s producer — is **also** skipped there and the flag would go
**STALE**. V67 measured **`gp-0x6806` == `latActive` in 150,302/150,327 = 99.983%** of frames, all **25**
disagreements single-frame transition edges. **A stale flag cannot track transitions that closely**
⇒ **the ECU is predominantly NOT in state 10 while engaged, and the detector nulls are probably
GENUINE.** [BELIEF — indirect.]
✅ **V70's bit5 rung (`gp-0x67fa == 10`) settles it directly, and is NON-VACUOUS IN BOTH DIRECTIONS:**
**bit5 ≈ 0** ⇒ state ∈ {4,5,11} ⇒ **the nulls are genuine and five builds are vindicated**;
**bit5 materially non-zero** ⇒ **the nulls were on the gate** and the detector programme needs
replanning.

⚠ **THE DETECTOR HAS A SECOND, INDEPENDENT ENTRY GATE, AND IT IS STILL OPEN.** `FUN_000428d4` is also
gated on **`FUN_00046ea6(5)`** — bit 5 of `gp-0x18d0`/`gp-0x18d4`, a fault/DTC-style bitmask, falling to
a fixed `0x8000` sentinel if set. 🛑 **The record's earlier closure established only that that FUNCTION
has one caller image-wide — NOT that the BIT is clear in operation. Those are different claims**, and
only the first was ever checked. The other three gated functions have no such secondary gate.

🛑 **AND bus `STEER_STATUS` is NOT `gp-0x67fa`** — `4f` reads `ST = 0` on 47,990/47,990 frames *while
the car steered*, and **state 0 is in no mask**. **Any reasoning that equated them** — e.g. *"ST==4
fires 0/37,922"* as evidence about `gp-0x67fa == 4` — **is invalid.** [VERIFIED] **State 4 sits inside
all three masks** and is where the V42 governor ratchet substitution used to fire.

⚠ **PROVENANCE, carry it:** decompiled against **stock `code.bin`**, with the 33 writer sites
cross-checked **byte-identical in `_v68_plain_image.bin`**. The **dispatcher itself was NOT decompiled
from a V68/V69 image** — high confidence it is unchanged (far outside any cave region), but that is
**BELIEF by adjacency, not EVIDENCE.**

### 7. ★★★ THE "r26 IS INERT" CLAIM SPLITS — one leg REVERSED, one DOWNGRADED

🛑🛑 **RESOLVED ON-CAR 2026-08-04 — LEG 2 IS NOW REFUTED, NOT MERELY BELIEF. READ THE HEADLINE §3.**
V70's bit4 read `gp-0x6adc` **strictly negative on 1,644 of 18,010 frames**, and **a pinned-zero cell
cannot clear a `>= 0` test** ⇒ **r26 is LIVE.** The prediction table at the end of this section was
**non-vacuous in both directions and it fired in the "r26 is LIVE" direction.** Everything below is
kept as the reasoning that set up that measurement; **the verdict is settled, and "r24 carries the
entire lane" is gone.**

🛑 **This is NOT a flat reversal of the whole claim** — writing it that way would be the mirror image of
the original error. The claim rested on **two independent legs** and they resolved differently.

**LEG 1 — THE GATE: REVERSED. [EVIDENCE]**
- `r26 == 0 ⟺ gp-0x6b5e != 0` (since `0xC6138` = 1 ⇒ `r22 == 1` always, and `gp-0x671a` = 0 over 240k
  frames).
- `gp-0x6b5e = ((LERP(gp-0x6bda) × 0xC63C2) >> 10) × polarity` — producer `FUN_000361c8` @`0x36256`/
  `0x36264` (shadow pair `gp-0x4cd8`), `0xC63C2` = 1024 = Q10 unity — on the trapezoid `0xC66CC`
  X = [−384, −128, 128, 294, 384], Y = [0, 4762, 4762, 717, 0] ⇒ r26 is killed **only where the LERP is
  ZERO, i.e. `|gp-0x6bda| ≥ 384`.**
- ★ **`gp-0x6bda` is a MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque `gp-0x6bf0`**
  (`FUN_00036022` @ `0x36068`–`0x3608C`; envelope `gp-0x6bd8`/`gp-0x6bd6` maintained by `FUN_00035d38`,
  half-width **never below 9390**, `0xC614A` = ±10048, margin cal `0xC614C` = 128).
  **Hands-off: `gp-0x6bda` ≈ 9262 = 24× the 384 threshold.**

⇒ **THE GATE DOES NOT KILL r26 IN ORDINARY DRIVING, and least of all hands-off at creep.** The kill
window is a **~512-count sliver at the DRIVER-OVERRIDE end** (cf. `0xC6156` = 9216). **This half is
settled, and it is a genuine reversal of how the gate was read.**

**LEG 2 — THE MAGNITUDE: STILL BELIEF, unresolved in either direction.**
`FUN_00039702` shows the RAM array `gp-0x641E`…`gp-0x6444` is an **adjustment added in Q10 float to a
fixed cal base at `tp+0x7564`**, and **`0xC6564`–`0xC658C` really is 40 bytes of EXACT ZERO** with **no
writer found for the RAM side (10 of 18 cells checked)** ⇒ `stage1 ≈ 0` — **IF that cal base is what
actually feeds `gp-0x69a4`.** 🛑 **THAT LINK WAS NEVER VERIFIED.** `gp-0x69a4`'s real producer is a
**live runtime 10-segment LERP at `0x355C6` in `FUN_000352b4`** (the local *slope* of the curve, gated
`|gp-0x4f60| ≤ 25600`) — **1 writer / 3 readers: `0x355A4`, `0x3575A`, `0x3AB3A` (= the aggregator).**

⇒ **"r24 carries the entire lane" is a BELIEF resting on LEG 2 ALONE**, and the re-attribution of
**V42 / V61 / V62 to a single lane is CONTINGENT ON LEG 2.** It may well still be right.
★ **The one indirect argument that it holds — and it is what keeps the dose–response coherent:** at
`a = gp-0x69a4/1024 ≈ 1`, V67/V68's gate (gain_A **3072 → 512**, a **6.00× cut**) would put their
engaged **TOTAL at ~0.94× stock** — essentially *on* stock — **yet V67/V68 measured the best grind #1
result in the kit (median `e_18-22` engaged creep 109 vs stock's 879).** ⇒ **the empirical record argues
`a` is small.** [BELIEF — indirect, but it is the only thing making the dose–response self-consistent.]

✅ **AND IT IS DIRECTLY MEASURABLE — V70 flies exactly the pair.** `gp-0x6adc` is r26's post-clamp
mirror (`st.h` @`0x3AD4E`, **0 readers / 1 writer** image-wide), and r24/r26 share **ONE polarity
load** — `ld.b -0x6752[gp],r14` @`0x3AB78`, reused at `0x3AB7E` (r26) and `0x3AC3E` (r24) — so **they
always carry the same sign.** Therefore `sign(gp-0x6adc)` vs `sign(gp-0x6ada)` is a **matched pair**:

| observation | verdict |
|---|---|
| **bit4 pinned at 1 while bit3 toggles** | **r26 is ZERO** ⇒ LEG 2 holds, r24 carries the lane |
| **bit4 TRACKS bit3** | **r26 is LIVE** ⇒ LEG 2 falls, and V42/V61/V62 need re-attributing again |

**Non-vacuous in both directions. Resolvable on the next drive.**

🛑🛑 **STRUCK 2026-08-04 — `0xC6444` IS A NULL BY CONSTRUCTION, NOT A CANDIDATE.** [EVIDENCE] it is read
**only** at `0x3AB5E` and **only when `lp != 0`**; on every **gateless** build (stock, V62, V65, V69,
V70, V71) the gate `0x3AA96` is `c5`, so `lp` derives from `gp-0x683c`, which has **0 writers
image-wide** ⇒ **the load never executes and raising it changes nothing**, unless `0x3AA96` is also
repointed — which reintroduces the control path the operator rejected. **THE HEADLINE §8.**
The paragraph below is the superseded framing, kept for the reasoning:
⚠ ~~**`0xC6444` — a CANDIDATE, NOT A RECOMMENDATION.**~~ Raising it is genuinely **UNTESTED**: V42 tested it
**downward** (512 → 0, FALSIFIED) — the same *"tested downward ≠ tested upward"* distinction the
V61 → V62 correction turned on. Blast radius **1 reader / 0 writers, no float mirror, same CRC block #48
as `0xC6446`**, overflow ceiling ≤ **6553**. 🛑 **V70 does not take it** — `a` is unmeasured and
V67/V68's control path is the best-measured arm **on the two instrumented symptoms** — but it carries the **high-speed grind** (scalar arm = **2.44×** at highway), which is why restoring it was overridden.
✅ **V62/V65's `sar` route is the only edit in this kit that is dose-exact independent of `a`** — 2.000×
on the total for **every** value of `a`.

### 8. INSTRUMENT AND HARNESS CORRECTIONS

1. 🛑 **`1/median(dt)` is biased by a ROUTE-DEPENDENT amount** — **100.13** (r4f) to **101.42** (r35)
   against a true grid of **100.000 Hz everywhere**. That is **1.3% spread = 0.27 Hz at 21 Hz = three
   quarters of a bin, BETWEEN THE ARMS of a cross-build contrast.** Use the **mean rate over the longest
   gap-free stretch + an index lattice.** ⚠ **`_r31_common.fs_of()` still uses the bad estimator.**
2. **The repo's `|dtorque|` figures (123–839) are ALREADY transfer-corrected** —
   `v69_surface_math.measured_dtorque()` applies `|sin(π f · 0.004)|`; a **raw** 10 ms CAN difference
   runs **3.4–5×** larger (analytic ratio 0.202 @ 7.6 Hz → 0.294 @ 50 Hz). A claim that the 0.81× rail
   margin was overstated **tenfold** was **raised and withdrawn this session** — recorded so it is not
   re-derived a third time.
3. **`FUN_0003ad74` record selection is 2-point between ADJACENT records only.** Breakpoints `0xC6010` =
   [0, 640, 3200, 6400] counts = **[0, 10, 50, 100] km/h**; **≥ 50.000 km/h reads only P2/P3.**
   ⚠ **Boundary detail:** at **3199 counts (49.984 km/h)** V69 vs stock is **1.0013×** — a **continuous
   ramp, not a step.** So *"byte-identical at and above 50.000 km/h"* is **true** and *"below 50"* is
   **not**.
4. 🛑 **`0xC618A` is a HALFWORD (= 1024)** — a byte read returns 0 and would "disprove" it.
5. **`mcp__ghidra__get_xrefs_to` returned "No references found" for an RTOS task entry** ⇒ **a null from
   that tool is never load-bearing.**
6. **A `jarl` Format-V scanner mask bug produced ZERO hits for functions Ghidra had just given callers
   for** — bits 15:11 are **reg2, not opcode**, and `disp = ((hw1 & 0x3F) << 16) | hw2` sign-extended
   from **22 bits**. **Anchor any such scanner on a known site and assert it.**

### ⇒ ★★★ NEXT: V70 IS BUILT AND UNFLASHED, WITH A REPAIRED PROBE

✅ **RESOLVED: the superseded first V70 is renamed `SUPERSEDED-DO-NOT-FLASH-…-V68CONTROLPATH-…`**
(`accord-firmwares` `9d44efc`); filesystem-verified, **exactly ONE flashable `V70` file remains.**
⚠ It mattered because that build has the **opposite control path** (gate `fb` / arm 5244 / surface stock
vs the current gateless ×2) and a **byte-identical cave** — so the probe could not have separated them
on-car. **Still confirm the filename against the operator's instruction before any flash.**

1. **The dose–response has a minimum near 2×**, so V69's 4× is past the optimum at creep. **V70 keeps
   V69's gateless speed-shaped topology and halves the dose to ×2** — creep lands at 1.84× (on the
   minimum) while highway stays **structurally** stock. 🛑 **Going back to V67/V68's scalar arm was
   tried and OVERRIDDEN**: it re-introduces the high-speed grind, because a scalar arm replaces a
   surface Honda rolls off, so `arm/LERP` **peaks at highway** — see the headline table.
2. **The probe budget is the scarce resource and all three of V69's rungs were wasted or under-exposed**
   — §5 says exactly how to size the next three, and V70's four rungs are sized that way.
3. **Two probe bits settle two verdict-affecting unknowns, and both are non-vacuous in BOTH
   directions.** **bit5 = `gp-0x67fa == 10`** (§6): ≈ 0 ⇒ the five-build detector null is genuine and
   those builds are vindicated; materially non-zero ⇒ the null was on the gate. **bit4/bit3 = the
   `gp-0x6adc`/`gp-0x6ada` sign pair** (§7): bit4 pinned at 1 while bit3 toggles ⇒ r26 is zero and
   "r24 carries the lane" holds; bit4 tracking bit3 ⇒ r26 is live and V42/V61/V62 need re-attributing.
4. ⚠ **Neither unknown is a reason to expect a different answer.** V67's own gate probe argues the ECU
   is predominantly **not** in state 10 while engaged (§6), and the dose–response argues `a` is
   **small** (§7). **The leading reading is that both current claims survive** — V70 measures them
   because they are cheap and verdict-affecting, not because they look wrong.

🛑 **Do NOT aim V70's rate lane at the lane-change transient** (§3). 🛑 **Do NOT read `4f` as evidence
about the ratchet's Q** (§4), or **route `4a` as evidence about the ratchet at all** (§4).

---

★★★ **THE PRIOR HEADLINE, 2026-08-04: V69 WAS BUILT AND RE-CUT ON TWO OPERATOR INSTRUCTIONS. THE
SURFACE DOSE WENT TO 4×, AND THE TELEMETRY WAS RE-AIMED FROM THE GRINDS TO THE RATCHET.**
⇒ **It has now FLOWN — see the headline above for what it did.** The build record below stands as
written; what has changed is the *interpretation* of two of its design arguments, both flagged in place.

**Spec: `docs/V69-DESIGN.md` §0 (the revision; the rest of that file still describes the ×2 cut).
Builder: `analysis-2020accord/build_v69_tva.py`. Verifier: `analysis-2020accord/verify_v69_image.py`.
Decoder: `rlog-tools/decode_v69_ratchet.py`.** Image SHA `48bb4192…`, RWD SHA `e62fcbba…`.
**7 edit sites / 70 changed bytes, 3 CRC blocks, cave extent UNCHANGED (66 of the proven 68 B).**

| # | addr | before → after | what |
|---|---|---|---|
| 1 | `0x3AA96` | `fb` → `c5` | gate **REVERTS** to the dead `gp-0x683c` |
| 2 | `0xC6446` | 5244 → 512 | the now-unreachable arm returns to stock |
| 3–4 | `0xD2A7E`/`0xD2A80` | 3072 → **12288** | mode-10 gain_B **0 km/h** record Y[0..1] (**×4**) |
| 5–6 | `0xD2ABA`/`0xD2ABC` | 2561 → **10244** | mode-10 gain_B **10 km/h** record Y[0..1] (**×4**) |
| 7 | `0xC4B34`–`0xC4B77` | V68's cave | **the RATCHET probe** — 3 signed-halfword rungs |

**Multiplier: 4.000× to 10 km/h → 3.658 @15 → 3.307 @20 → 2.578 @30 → 1.808 @40 → EXACTLY 1.000× at
and above 50 km/h**, in BOTH arms. ★ **That 1.000× is STRUCTURAL, not tuned**: the lane-change point
(93.35 km/h = 5980 counts) sits in the cross-axis `[3200,6400]` segment, so the interpolation there
reads **only rec2/rec3**, which this edit does not touch — proven by a **12,221-point sweep**.
★ **And it does not bet on the OPEN axis scale** (4.7121 vs 0.58901 counts/deg-s): V69 scales the
whole flat `[0,400]` segment instead of leaning on a breakpoint, so its creep dose is **4.000× on
BOTH scales**, and there is **no hump anywhere**.

🛑🛑 **WHAT 4× COSTS, AND IT IS NOT HIDDEN.** The shape is identical to the ×2 cut; only the dose
moved. **(a) THE FLOWN BRACKET IS BROKEN** — at 2.000× GATE 2's magnitude leg was an *interpolation*
between stock (1.00×) and V62/V65 (2.00×, flown flight-clean); **4.000× is an extrapolation to twice
the largest dose this kit has ever driven.** Phase is untouched (no filter, no pole, no delay, no
`sar` moved), the lane is linear, V65 measured the aggregator never railing over 120,049 frames, and
grind #1's dose–response was monotone through 2.00×. **(b) SATURATION CROSSES THE RECORD** — peak
gain 12288 rails the r24 lane at `|dtorque|` **683**, against the repo-recorded max **839** (margin
**0.81×** ⇒ *it can rail*) and the V68-route max 511 (1.34×); at ×2 it could not. ⚠ every `|dtorque|`
figure here is a **LOWER BOUND**, so the true margin is worse, not better. **(c) manual creep is
4.000×** on the pessimistic axis scale; manual highway stays byte-identical to stock. The fold step
at rateKey ≥ 13001 (2759 deg/s, fault-level, unreachable) widens to 2.00 → **8.00×**.
★ **bit6 of the new probe measures cost (b) on-car** — it is instrumented, not merely disclosed.

★★★ **THE TELEMETRY IS RE-AIMED AT THE RATCHET.** Bits 6/5/4 no longer read Honda's oscillation
detector. **That instrument is exhausted**: `gp-0x67df` has never been observed non-zero in this kit
(0/53,991 on V68, 0/186,321 on V67, straight through the captured 28 Hz burst), and with no positive
control the null cannot separate "no oscillation" from "detector disabled / input dead". ★ **And the
ratchet is the one symptom this channel can RESOLVE** — at ~7.4–7.6 Hz a 100 Hz probe gets ~13.5
samples/cycle, so each bit's own time series carries the line; at 21 Hz and 43 Hz it never could.

The ratchet's signature — **symmetric, amplitude-saturated, Q ≈ 36, creep, engaged, hands-off, NOT
the V42 state-4 governor** — is the describing-function signature of a **hard nonlinearity inside
the loop**. V65 killed the obvious one (the aggregator SUM never rails, 120,049 frames). What that
null never covered is **each lane's own nonlinearity upstream of the sum**: eight ZERO-type range
gates (out-of-window contributes **0, not clipped** — a crossing is a *step*) and two saturating lane
clips. **None has ever been measured.** `0x14A` byte4:

| bit | cell | test | its lane's hard nonlinearity | why |
|---|---|---|---|---|
| 7 | — | 1 | — | LIVENESS; field == 0 ⇒ VOID |
| **6** | `gp-0x6ada` | ≥ +4096 | ±0x2000 **saturating clip** | ★★ **r24's LANE OUTPUT** — the damping/torque-rate lane the record points at *and* the lane V69 scales. Honda mirrors it to RAM at `0x3AD5A` every 1 kHz tick. 🛑 **0 readers / 1 writer image-wide** ⇒ the strongest GATE-1 statement in the chain: nothing consumes it. +4096 = half its rail ⇒ duty is a **rail-proximity meter** |
| **5** | `gp-0x6b62` | ≥ +4096 | ±0x2000 **ZERO gate** | ★★ **THE OPERATOR'S OWN HYPOTHESIS, never probed in 69 builds.** Return-to-centre: `FUN_00036388`, a slow ±1/tick accumulator **with hysteresis** |
| **4** | `gp-0x6ad4` | ≥ +4096 | 🛑 ~~±0x2800 **ZERO gate**~~ **STRUCTURALLY VACUOUS — CORRECTED 2026-08-04** | the **unfiltered** residual lane (`FUN_0003a382`: raw derivative on the torque sensor, straight into the aggregator), whose gain is LERP-indexed by `gp-0x671a` ⇒ it **closes a loop from Honda's own detector back into assist**. 🛑🛑 **`±0x2800` IS THE ERR *INPUT* CLAMP, NOT THE LANE'S OUTPUT RANGE.** The output is clamped to ±CEILING = **MIN of three LERPs**, the binding one `0xC67C2`/`0xC67C8` indexed on **voted vehicle speed**, **max 1024**, starting at **ZERO** — at the ratchet episodes' speeds (4.9/6.8/7.8/8.0 km/h) CEILING was **164–341**. ⇒ a **≥ 4096** test is **12–25× above the lane's entire reachable range** and **could never have fired on any build, any drive**. ★ Also explains why **V56's mute of this lane changed nothing** |
| 3 | — | **0** | — | V69 BUILD CLASS. V68 emits bit3 = 1 in **100.000%** of 53,991 frames ⇒ V68 excluded absolutely |

**bit6 is freed from the LKAS gate** to buy the third rung: `gp-0x6806` agreed with `latActive` in
**99.983%** of 150,327 frames, `0x18F` b4 bit3 and `0xE4` byte2 bit7 agree 99.94–100%, and V69
*reverts* the gate so that cell no longer steers anything on this build.
**Encoding (14 B/rung):** `ld.h` · `sar 0xc` · `cmp 0x1` · `blt +6` · `movea BIT,r7,r7`. All three
lanes are **signed** halfwords; `sar` is arithmetic and `blt` signed, asserted by an **exhaustive
wire model over all 65,536 patterns**. 🛑🛑 **THE ONE-BIT TRAP IS LIVE HERE:** `ld.h` = 0x39,
`st.h` = 0x3B, and `gp-0x6ada`'s *only* real instance **is** the `st.h` form carrying **the same
displacement halfword** — one bit turns the read into a **write into a 1 kHz aggregator lane**.
Asserted by value in the builder *and* independently in the verifier.
**Provenance:** `ld.h -0x6ad4[gp],r6` is **BYTE-IDENTICAL** to the aggregator's own read @`0x3ACA8`;
`gp-0x6b62` has **eight** real instances differing only in reg2; `sar 0xc,r6`/`cmp 0x1,r6`/`blt +6`
are all byte-identical real instructions. **66 of the proven 68 cave bytes; the extent is NOT grown**
(a fourth rung needs 14 more — that arithmetic, not preference, is why there are three).

🛑🛑 **POST-FLIGHT, 2026-08-04 — ALL THREE RUNGS FAILED, AND THE RESIDUALS BELOW ARE NOT WHY.**
**bit4 structurally vacuous** (see the table note — sized against a downstream gate width instead of the
lane's own reachable output); **bit5 insensitive, not vacuous** (reachable max **5786**, so 4096 was
**71%** of full range and it only saw the top 29%); **bit6 had NO EXPOSURE** (replay predicts ~1
one-sided hit on `4f`, observed 0, **p ≈ 0.37** — a power problem, *not* the V64 gate failure, and not a
positive control either). ⇒ **the transferable lesson is in the headline §5.**

🛑 **THREE RESIDUALS ON THE PROBE.** **(1) ONE-SIDED** — each rung tests the positive side only
(two-sided costs 8 B/rung and does not fit); a symmetric limit cycle still puts 7.4 Hz in the bit's
spectrum, but **a null bounds only that lane's POSITIVE excursions.** **(2) NO POSITIVE CONTROL on
bits 5/4** — only bit6 is expected to fire on any real drive; if bit6 also reads 0.000%, check bit7
and the `.rwd` name **before** interpreting bits 5/4 (the V64 lesson). **(3) V69-vs-V66/V67 is NOT
structural** — those also emit bit3 = 0 with bits 5:4 measured 0 over 186,321 frames, so `{0x87,
0xC7}` is a *subset* of V69's payload space; discrimination rests on bit5/bit4 ever firing plus the
filename. V68 — the build on the car — **is** excluded absolutely.

⚠ **NOT taken, so it is not re-proposed:** `gp-0x6bbe` boost (±0x800, the narrowest gate on a live
lane) is indexed on **driver torque** and the ratchet is hands-off; `gp-0x6bd0` damping (±0x800) has
f5 = 0 at both operating points on a **static** claim — **first cut if a rung frees up**;
`gp-0x6b4c` is already on CAN `0xE4`; `gp-0x4f62` (r24's input) is rung 4 if the cave ever grows.

★ **NEW STRUCTURAL FINDING, folded into the golden model:** **both inline lanes are mirrored to RAM
post-clamp and nothing reads them** — `st.h r26 → gp-0x6adc` @`0x3AD4E` and `st.h r24 → gp-0x6ada`
@`0x3AD5A`, each **0 readers / 1 writer** image-wide (two decoders). They are free, blast-radius-zero
telemetry taps on exactly the quantity every rate-lane build scales.

🛑 **THE DESIGN IS FORCED.** The gate branch `0x3AC04-0x3AC0C` is `cmp`+`be`+`ld.hu`+`br` = **10
bytes, zero slack**, and it **REPLACES** the LERP rather than scaling it ⇒ speed shaping reaches the
engaged lane only if the gate is OFF. *Gated AND speed-shaped* needs a cave on the 1 kHz path — the
only bricking class (V24/V27/V48B). **Rejected.**

🛑 **~~Design A~~ (`0xD2ABC` alone → 7051) REJECTED on three counts**: hump **2.753×** (the recorded
"~2.45×" is only its value at 128 deg/s); it swings **2.00× → 1.22×** across the two axis scales; and
at **|rate| 16–32 deg/s — where V62's fix measured LARGEST (42×)** — it delivers only **1.1–1.5×**,
because its boost is a ramp starting at the axis-400 breakpoint. Region min/median **1.75/2.00**
(V69) vs **1.09/1.45** (Design A). An independent directed search over 8 edit families converged on
V69's exact four addresses and values.

⚠ **THE THREE COSTS, STATED.** (1) **Manual steering below ~50 km/h now gets the rate damping** — the
operator was shown this trade with the cave alternative priced and **chose it**; manual highway is
byte-identical to stock. (2) **Saturation margin** ~~drops 1.91× → 1.63×~~ — **at the as-built ×4 it
is 0.81×** (peak gain 12288 rails at `|dtorque|` 683 vs the recorded max 839), i.e. the lane can rail
in ordinary driving. **The one metric where V69 is WORSE than V68**, and at ×4 it crosses the record
rather than merely narrowing. (3) On the pessimistic axis scale, **manual creep and creep grind #2
are both 4.000×** — ~~exactly the dose V62/V65 flew~~ **twice it**.
🛑 The ×2 numbers in the paragraphs immediately above (Design A comparison, region min/median, the
Pareto reasoning) were computed for the 2.000× cut and are **kept as the design record**. The dose
that shipped is **4.000×** — see the headline table. The *shape* arguments (structural highway
1.000×, scale-invariance, no hump, neighbour safety) are dose-independent and carry over unchanged.

🛑🛑 **TWO TRAPS THE BUILDER ASSERTS AGAINST.** (a) **EDIT-ORDER INVARIANT**: writing `0xC6446 = 512`
while the gate stays repointed leaves the arm **LIVE at ~5× BELOW the stock LERP** — worse than stock
everywhere. (b) **NEIGHBOUR TRAP**: mode 11/12's 0 km/h records are **BYTE-IDENTICAL** to mode 10's,
so the target pattern occurs **3× within 40 bytes**; `diff_build_vs_stock.py` is **span-based** and
would not catch a stray hit. All 8 neighbours are asserted, in both builder and verifier.

✅ **NO FLOAT MIRROR** on any Y value — four encodings over the whole image; a mirror must carry ALL
the values and 2561/2247/1947/2322/1400/3000 are absent in every one. ⚠ **X values DO have f32 hits**,
which is why **V69 edits Y ONLY**. ✅ 50/50 CRC, x31 PASS, RWD decodes back to the image with every
gate re-run on the readback; `verify_v69_image.py` all anchors PASS (incl. `0xC6564`, which
`verify_v68_image.py` does not check); `diff_build_vs_stock.py v69` **0 unattributed**.

🛑 **THE MECHANISM IS SUGGESTIVE, NOT ESTABLISHED** — the 26–30 Hz maneuver dose ratio is
**3.334 [1.201, 6.492]** inside a split-half null of **[0.33, 3.36]**. The operator was offered the
drive that would settle it and **declined**; V69 is built on it by explicit decision. Six
pre-registered predictions, two of them negative controls, are in `docs/V69-DESIGN.md` §9 — **P3
(40–49 Hz does not move) and P4 (1–4 Hz does not move) are what catch this being wrong.**
⚠ **P1/P2/P6 were sized for ×2 and are NOT re-derived for ×4** — the dose–response is measured only
out to 2.00×, so quoting their intervals at 4× would be inventing precision. Read them as
*directions*. **P3/P4/P5 are dose-independent and stand. P7/P8/P9 are new and pre-registered for the
×4 cut and the ratchet probe** (§9).
⇒ ★★★ **NEXT: flash V69 on the operator's explicit instruction, then an ORDINARY 20–30 min engaged
highway commute** — route `4e` gave 18 maneuver windows in ~4 min at speed, so a commute yields
5–7× that. **No scripted drive is needed for the highway question.**
⇒ ★★★ **AND, FOR THE RATCHET, ADD PARKING-LOT CREEP: engaged, hands-off, |angle| large.** The
recorded ratchet episodes are 7.56 ± 0.36 Hz, hands-off + engaged + creep, at both 9–15° and 133°.
🛑 **Route `2b` could not speak to the ratchet in either direction and the operator said so before
the data did** — the decoder prints the episode count first and says so outright when there are none.
Decode with `rlog-tools/decode_v69_ratchet.py`.

---

★★★★ **THE PRIOR HEADLINE, 2026-08-03: V68 FLEW. THE LANE-CHANGE VIBRATION IS CAPTURED AND IT IS
A ~28 Hz TRANSIENT, NOT GRIND #2. THE CORPUS'S MISSING LKAS-OFF HIGHWAY ARM IS CLOSED, AND
"ONLY WHEN ENGAGED" IS REFUTED AT 40–49 Hz. HONDA'S 1 kHz DETECTOR STAYED AT ZERO.**

Routes **`4c`** (`d0ea3c14b4` segs 4–8, **LKAS OFF** manual highway — operator: *"no grind vibration
felt"*) and **`4e`** (`11f5b814b6` segs 31–34, **LKAS ON** — *"definitely felt the grind #2-like
vibration when changing lanes"*). Full narrative:
`docs/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`. Reproduce with
`analysis-2020accord/analyze_v68_highway_arms.py`, `_followups.py`, `_engaged_line.py`,
`_line28.py`, `_line28_identity.py`.

✅ **V68 CONFIRMED FROM THE PROBE, NOT THE FILENAME.** byte4 ∈ `{0x8F, 0xCF}`, **bit3 = 100.000%**
of 53,991 frames (V66/V67 emit bit3 = 0 ⇒ excluded absolutely); VOID 0, illegal 0, ord_viol 0.
Cave verified by hand from `_v68_plain_image.bin`: `movea 0x88,r0,r7` @`0xC4B34`,
`ld.bu -0x6806[gp],r6` @`0xC4B38`, **`ld.bu -0x67df[gp],r6` = `a4372198` @`0xC4B44` (ODD disp
`0x9821`, hw1 `a437`)**, `cmp 0x1,r6`/`blt +6`, `ld.bu -0x671a[gp],r6` @`0xC4B50`.
⚠ **NAMING TRAP:** `build_v68_tva.py` still calls bit4's constant `BIT_RATE` with `RATE_DISP =
0x6AC0` — leftovers from the SUPERSEDED rate-axis probe. **Read `CELLS`, not the constant name.**
✅ **FLIGHT-CLEAN both routes, two methods:** `ST == 4` **0**, `ST == 3` **0** gridded *and* on the
raw un-gridded `0x18F` stream; watchlist (steerUnavailable/canError/controlsMismatch/…) CLEAN.

★★★ **THE MISSING ARM IS CLOSED.** `4c` supplies **234.8 s disengaged above 20 m/s** (148.4 s above
25, 42.7 s above 28) against the entire prior corpus's **0.0 s at every cut from 12 to 28 m/s**.
🛑🛑 **BUT ARM AND DOSE ARE THE SAME VARIABLE.** V68's control path is V67's, whose rate-lane arm is
CONDITIONAL on `gp-0x6806`: **LKAS ON = gate open = Kd 2.00× ; LKAS OFF = gate closed = Kd 1
(stock)**. Every cross-arm number is "engaged AND doubled" vs "disengaged AND stock".

★★ **"ONLY WHEN ENGAGED" IS REFUTED FOR 40–49 Hz.** Maneuver-vs-control computed INSIDE each arm
against its own split-half null (road/day/tyre cancel), one absolute cut pair (|rate|pk ≥ 19.0 /
≤ 11.0 deg/s):

| band | **ON (4e)** | **OFF (4c)** | null |
|---|---|---|---|
| 1–4 (validity) | 1.182 [0.818, 1.506] | 1.592 [0.807, 1.823] | [0.78, 1.29] |
| **18–22** | **3.129 [2.408, 5.298]** | 1.780 [1.444, 1.927] | [0.66, 1.51] |
| **24–28** | **5.098 [2.798, 6.160]** | 2.056 [1.470, 2.812] | [0.79, 1.23] |
| 30–40 | 2.072 [1.550, 2.292] | 2.081 [1.667, 2.711] | [0.72, 1.42] |
| **40–49** | **2.516 [1.561, 3.701]** | **2.558 [1.469, 3.747]** | [0.77, 1.31] |

⇒ grind #2's band rises by **the same factor in both arms**; 30–40 Hz too. ⇒ ★★ **the
engagement-conditional part is at 18–28 Hz**, a different band from the one this kit has hunted.
⚠ **The raw cross-arm LEVEL contrast is uninterpretable and is kept only to be dismissed:** the 1–4
Hz exposure check fails at **0.213** (effort p50 **565** manual vs **96** engaged), the (speed,
effort, |rate|) matcher finds **zero** shared cells, and **0.0%** of manual windows fall below the
engaged arm's p90 effort. Only the within-arm contrast carries weight.

★★★★ **THE EVENT, CAPTURED — `4e` seg 33, t = 51.3 s.** `preLaneChangeRight` → ALC right lane change
at **25.93 m/s / 1566 rpm**, angle −4.8 → **−11.3°**, rate peak **38 deg/s**, engaged, `ST == 0`:
**bar 1468 counts p-p**, **26–30 Hz envelope 614** (route median 31 ⇒ **20×**), lines at
27.73 / **28.12** / **28.51** Hz at **prominence 100–107** — while **40–49 Hz reads 69** in the same
window. Identity, with the arithmetic: wheel order 2 = **24.93**, order 3 = **37.40**, engine order 1
= **26.10**, order 2 = **52.20** Hz — **it is none of them.** ✅ Positive control in the SAME window:
lines at **37.10/37.49 Hz** sit on wheel order 3, so the estimator does find orders when present.
⇒ **the felt lane-change vibration is a ~28 Hz transient and grind #2's band is quiet during it.**

🛑 **THE DETECTOR STAYED AT ZERO — bit5 `gp-0x67df != 0` fired 0/53,991 frames**, including straight
through that burst; bit4 likewise 0. With V67 (186,321 frames at `>= 5`) and V64's route 35 on the
same word, **the bottom rung is now measured and empty.** 🛑🛑 **AT FULL STRENGTH: this cell has
NEVER been observed non-zero in this kit — there is NO POSITIVE CONTROL.** It bounds amplitude only
if the detector is live; *"disabled / input dead / `FUN_000428d4` not reached"* is **not excluded**.
⇒ **`gp-0x67df`'s writer and `FUN_000428d4`'s enable condition are now VERDICT-AFFECTING and OPEN.**

⚠ **THE RATE-LANE SUGGESTION — REAL SHAPE, INSUFFICIENT POWER, AND NOT MORE THAN THAT.** Pooling all
highway windows by **arm-resolved** dose. Within-dose maneuver/control (null [0.86, 1.15]): 24–28 Hz
**6.694 → 12.874**, 26–30 Hz **3.665 → 11.822**, but 40–49 Hz **3.304 → 3.903** and 30–40 flat.
Direct dose ratio Kd2/Kd1 on maneuver windows (106 vs 39 windows, 41 vs 17 blocks): **26–30 Hz
3.334 [1.201, 6.492] against a split-half null of [0.33, 3.36] — the CI does NOT clear its own
floor.** Control windows flat (1.034 [0.904, 1.290]). ⚠ Also confounded with arm and route (Kd=1
maneuvers are driver-initiated on `4c`; Kd=2 is dominated by `r47`'s ALC).
⇒ ★★★ **RECOMMENDED, NO BUILD: ONE HIGHWAY RUN ALTERNATING LKAS ON/OFF EVERY ~60 s ON ONE STRETCH,
WITH DELIBERATE LANE CHANGES IN BOTH ARMS.** V68's gate already carries both doses, so dose, road,
tyres and time all become within-route. Power computed, not asserted — Kd=1 maneuver blocks 17
(today) → null 3.65× ; 51 → **2.42×** ; 102 → **1.96×**; the measured point is 3.334×, so a ceiling
below ~2.2× is decisive ⇒ **~150–250 s more of ACTIVE maneuvering LKAS-OFF ≈ 20–30 deliberate lane
changes**, plus a matching set engaged. ⚠ If it confirms, the lever is the **same `sar 0xa` →
`sar 0x9` site in `FUN_0003aa2c`** that V62 doubled and V67 made conditional — i.e. partially
reverting what fixed grind #1. **Price that trade before building.**

✅ **THE ORDER VETO RAN FIRST AND 30–49.5 Hz IS EMPTY ON BOTH ARMS** — averaged-periodogram
prominence **1.89–2.45** (`4c` disengaged) and **1.81–2.02** (`4e` engaged) against the **> 4**
criterion, with the 8–30 Hz control recovering wheel order 1 to 0.17 Hz. **Sixth confirmation, and
the first on a disengaged arm.**

🛑 **THREE CORRECTIONS OF MINE THIS SESSION.**
1. **"An engaged-only fixed 28 Hz line" — WITHDRAWN.** It passed the band-centre test (peak fixed as
   the search band swept 24–30 … 15–45 Hz) and I was ready to call it a mode. A **per-window**
   census killed it: 26–30 Hz appears in **133/177 = 75.1%** of MANUAL windows at median prominence
   **7.50** vs **88/121 = 72.7%** at **6.27** engaged — *more* on the manual route — and `4c`'s
   version is **wheel order 2** (Theil-Sen **+1.0352 [+1.0012, +1.0616]** vs order 2's +0.9616,
   per-bin agreement 0.1–0.35 Hz). ⇒ 🛑 **NEW RULE: an averaged spectrum compares two routes only
   if their SPEED DISTRIBUTIONS MATCH** — a moving order concentrates in a narrow-speed route and
   smears in a wide-speed one, manufacturing an "only on route X" line. **And the band-centre test
   is necessary but NOT sufficient; follow it with a per-window prominence census.**
2. **Coherence was computed against `e4req`** — the engagement BIT `(d[2]>>7)&1` — not `e4tq` =
   `i16be(d,0)`, the command. That is why every band read exactly `0.000`. **An exact 0.000 across
   every band is a wiring error, not a result.** Redone: `4e` engaged **0.343** at 26.5–29.5 Hz vs
   **0.016** at 40–49; `r47` 0.269/0.002; grind #1's recorded benchmark 0.917. ⚠ the manual
   negative-control column is **degenerate (n = 1)** and must not be quoted.
3. **The maneuver contrast was first run with per-arm decile cuts and no null.** Both fixed above.

⚠ **`4c` and `4e` are different roads 14 h apart** (02:48 vs 17:15 local) — every cross-route number
is caveated in place. ⚠ **The 28 Hz burst is n = 1 well-characterised event** plus a broader 24–30 Hz
maneuver amplification: a capture, not a rate.

---

★★★★ **THE PRIOR HEADLINE, 2026-08-03: THE >50 Hz BLINDNESS WAS OURS, NOT THE CAR'S. HONDA RUNS A
1 kHz OSCILLATION DETECTOR WHOSE INPUT IS A BAND-PASS PEAKING AT ~61 Hz — AND V67 HAS BEEN READING IT
ALL ALONG, AT THE WRONG THRESHOLD. ★★★ AND THE MICROPHONE INDEPENDENTLY PLACES GRIND #2's ENERGY IN
THAT SAME BAND — FROM DATA ALREADY ON DISK.**

★★★ **THE ACOUSTIC INVERSION — the first DATA-BASED evidence of >50 Hz content in this kit, and it
needed no transfer model.** `soundPressure` and `soundPressureWeighted` are a **two-point filter bank**:
A-weighting is **−32.4 dB at 44.6 Hz** but only **−19.1 dB at 100 Hz**, so the *ratio* of the two channels
reports where energy sits even though **neither channel can name a frequency**. On the 10 demonstrated
creep grind #2 bursts, the excess carries a mean A-weight of **4.28× [2.28, 9.86]** that of a pure
44.6 Hz excess ⇒ **the acoustic excess CANNOT be entirely at 40–49 Hz.** ⭐ Inverted against the IEC
61672 A-curve (verified −30.27 dB @ 50 Hz / −19.14 @ 100 vs the standard −30.2 / −19.1):

| mean A-weight vs W(44.6 Hz) | effective centroid |
|---|---|
| **4.28×** (point) | **63.5 Hz** |
| 2.28× (CI low) | 54.2 Hz |
| 9.86× (CI high) | 79.6 Hz |

🛑 **THE RATIO IS A POWER RATIO, NOT AN AMPLITUDE RATIO.** An orchestrator pass inverted it as amplitude
and published **95.5 Hz [66.8, 170.5]** — **WRONG, and retracted.** 95.5 Hz would require a power ratio of
**18.29×**, not 4.28×. Settled by an independent consistency check: the same data's *"16.2% of energy at
100 Hz"* decomposition gives a mean power weight of **4.277×**, reproducing 4.28 exactly, and that same
mixture is only **2.068×** in amplitude terms. **Anyone re-deriving this must square the weights.**
**The whole interval, 54–80 Hz, is still ABOVE the 50.00/50.51 Hz Nyquist ceiling** — margin **54.2 Hz**,
not 66.8 — and a pure 44.6 Hz excess would read **1.00× by construction**, excluded (CI low 2.28 > 1).
★ **And the corrected number is TIGHTER corroboration, not weaker: 63.5 Hz sits essentially ON
`gp-0x6c2c`'s band-pass peak of 61 Hz.** Robust to the burst statistic (5.64 p90 / 3.07
median / 3.31 max); the mic fires on **8 of 10** bursts and tracks torsion-bar magnitude.
🛑🛑 **THE LIMIT, AT FULL STRENGTH: this is a MEAN-WEIGHT inversion. It proves the excess is not all
sub-50 Hz; it does NOT LOCATE the energy.** Any mixture with the same mean weight fits equally well —
**63.5 Hz is an effective centroid, not a line.** ⚠ The second harmonic of 44.6 Hz is **89.2 Hz**, which a
44.6/89.2 mixture could produce; that reading (a contact nonlinearity) is **BELIEF, not measurement.**
⚠ **Tyre scrub is NOT eliminated** — controls match the exact (speed, effort, |rate|) cell and the
partial correlation survives it, but scrub intensity is driven by **rack force**, which is not among the
controlled covariates.
⇒ ★★ **THIS CORROBORATES V68 FROM A COMPLETELY DIFFERENT CHANNEL, WITH NO SHARED ASSUMPTION.** The
acoustic centroid **63.5 Hz [54, 80]** sits essentially **ON** `gp-0x6c2c`'s band-pass peak of **61 Hz**
(>90% of its 21 Hz gain out to ~180 Hz) — the detector V68's probe now reads. Firmware arithmetic and
cabin audio, independently and with no shared assumption, point at the same band.
🛑 **AND THE MICROPHONE READ 1.061 ON GRIND #1 — INSIDE ITS NULL — on a large, real, measured
oscillation.** The cleanest demonstration in the corpus that **a mic null does NOT mean "no vibration."**
⇒ **a mic POSITIVE is informative (and via the A/un-weighted contrast carries genuine spectral
information); a mic NEGATIVE on a TACTILE event carries almost nothing.** Positive control replicated at
**4.59× [2.95, 8.31]** (vs 4.14× on record) by a different estimator and control design.

★★ **GRIND #1 DOES NOT REACH THE CHASSIS; GRIND #2 DOES — settled by two independent estimators.**
Bar→chassis **coherence** (scale-free, uses no level at all): grind #2 **0.82–0.88 on EVERY axis** vs
0.30–0.61 in matched controls; **grind #1, 48 events, NO contrast on ANY axis** — every one inside its own
control. Amplitude agrees: grind #2 burst/control = bar **77.1** · `ay` **58.8** · `gz` **36.2** · `gy`
21.3 · `ax` 20.1 · `az` 19.2 · `gx` 11.4 · mic 4.59, all clearing their nulls; grind #1 = bar **12.87**
but **every IMU axis inside its null**. ⇒ **grind #1 is a TORSIONAL COLUMN MODE that does not reach the
body — which is exactly why the IMU never showed its reduction.** ⚠ BELIEF: grind #2's axis ordering
(lateral ≫ roll > pitch ≈ vertical ≈ longitudinal ≫ yaw) reads as a **lateral rack/subframe force with a
roll couple** — translational-dominant with a rotational partner; **not** wheel-hop, **not** yaw.

⚠ **THE HIGHWAY ENERGY BUDGET CANNOT BEAR THE WEIGHT — but the bound is now quantified.**
κ = (fractional acoustic excess)/(fractional mechanical excess) = **0.0091 [0.0059, 0.0159]**. The
κ-predicted acoustic signal at highway sits **2–9× BELOW the microphone's own highway floor** on every
route (r2b 6× · r37 9× · r3b 4× · r47 2×) ⇒ **a highway acoustic null is UNINFORMATIVE**, quantified
rather than asserted. 🛑 The joint detector is **MIC-LIMITED** — the mic is the minimum channel in **97%**
of burst blocks ⇒ **"joint" buys SPECIFICITY, NOT SENSITIVITY.**
⚠ **A real tri-channel coincidence DOES exist at highway** (`ay` 1.347/1.866/1.372/1.437, `gz` ~1.35–1.61,
sound 2/4 routes) **but it is DOSE-INDEPENDENT** and the stock Kd = 1.00 lane is not the lowest ⇒ it is the
already-characterised **manoeuvre-loading tail. THIS DOES NOT REVIVE THE RATE LANE.**

🛑 **TWO INSTRUMENT CONSTANTS, both new, both will bite a future session.**
1. **`1/median(dt)` IS THE WRONG CAN RATE.** Frames are timestamped **per log packet**, so on r47 **12% of
   `dt` exceed 15 ms and p10 is exactly 0**; `median(dt)` reads **100.76 Hz** on a grid that is 100.000 Hz
   to 2e-5. **Use the mean rate + an index lattice.** Recorded timestamps wander from it by up to
   **7.5–10.3 ms** — that is the CAN alignment uncertainty.
2. **The microphone pipeline delay is 115 ms** (measured against road impacts, 35 segments, peak ρ 0.512).
   `micd.py` alone predicts 75 ms; the extra **~40 ms is audio-capture buffering.** Subtract it from any
   sound↔CAN alignment.
   ⚠ Accel and gyro are **separate streams with separate hardware-timestamp offsets** ⇒ **±50 ms is the
   empirical lead/lag floor, and NO physical ordering between bar, chassis and sound is resolvable** —
   true transit is 0.2 ms structure-borne / ~3 ms airborne, **30–500× below the finest instrument step.**
   The bar→chassis discrimination is carried by **coherence**, not by timing.
Reproduce all of the above: `analysis-2020accord/grind2_trichannel.py`.

---

`FUN_000428d4` runs in **task 1 (1 kHz, by construction** — TCB table `0xbb858`, mod-100 divider
`0x14be4`, `syscall8(0)` unconditional**)**. Its input `gp-0x6c2c` (`FUN_00041464` @`0x4184E`, K1=37>>7,
K2=22>>6, out >>9) is **not** a low-pass: the EMA increment `step[n] = ema1[n]−ema1[n−1]` is a
differentiator in series with the low-pass, so the cascade is a **BAND-PASS**. Integer-exact simulation,
gain relative to 21.09 Hz:

| f (Hz) | 1 | 21.09 | 45 | **61** | 100 | 150 | 200 |
|---|---|---|---|---|---|---|---|
| rel. gain | **0.05×** | 1.00× | 1.54× | **1.61× (max)** | 1.43× | 1.15× | 0.94× |

**>90% of the 21 Hz gain out to ~180 Hz, and ~30× rejection of 1 Hz driver content for free.**
Trip amplitude on `gp-0x4f50` to reach `T` = `0xC620A` = 12800: 21.3 Hz **1683** · 45 **1104** · 60
**1056** · 80 **1092** · 100 **1186** · 150 **1478** · 200 **1735** — ⇒ **45–100 Hz needs LESS amplitude
than 21 Hz already required**, and none is near `gp-0x4f50`'s own ±13000 clamp. ✅ Validated against the
golden model's recorded pair: **1683 → 12804 trips, 1682 → 12797 does not.** ⭐ **Orchestrator
re-simulated independently and reproduced the table and the pair.** Reproduce:
`analysis-2020accord/gp6c2c_freq_response.py`.
🛑 **`gp-0x4f50`'s deg/s conversion is [OPEN]** — do **NOT** borrow `gp-0x6ac0`'s 4.7121 counts/deg-s.
Composing those two is exactly what produced the retracted "bus = 8 × deg/s".

★★ **`gp-0x671a` is the readout, and it is free.** It counts **REVERSALS** of `gp-0x6c2c` past ±T (raw
counter `gp-0x357c`, FSM state `gp-0x67df` ∈ {0,1,2}); it **passes through 1,2,3,4** before saturating at
CEIL = `0xC64FA` = 5 (⭐ verified in Ghidra at `0x429DA-0x429F2`: the pin to CEIL fires only when
already-saturated AND the fresh count lags; **every other path is `mov r14,r8`, the raw count verbatim**).
Dwell decay **50 ticks** (`0xC64DD`); the held output releases after **5000 ticks** (`0xC6270` = 5.0 s)
gated on `gp-0x6a5e` ≥ `0xC62DE` = **640 = 10.0 km/h** (64 counts/km/h) ⇒ **below ~10 km/h it never
releases; at road speed it clears 5.0 s after the last reversal.** Both cells hold ≥50 ms ⇒ **reliably
catchable by the EXISTING 100 Hz probe.** 8 accesses image-wide, 1 writer — **reading is blast-radius
free**, the same class flown 3× (V63/V64/V67).
⇒ 🛑 **V67 read this detector and got 0.000% over 186,321 frames — but at threshold 5.** "Never reached
5" is **not** "never incremented". ⇒ **NO new cave, NO code on the 1 kHz path, NO new RAM audit.** The
1 kHz-cave design priced earlier this session is **WITHDRAWN as unnecessary** — its own author retracted
it on this evidence.

★★★★ **AND ROUTE `4a` CLOSED THE LAST OPEN ARM: ENGAGED-CREEP GRIND #2 IS RESOLVED.** Route
`4a--346bf31d97` segs 20–25, **V67 confirmed from the probe** (byte4 ∈ {0x87, 0xC7}; **bit3 = 0/35,994**,
and V68 emits `movea 0x88` so `0x87` cannot occur on it). 360 s, **149.2 s engaged creep — 6.8× route
47's 22 s** — and **79.7 s of the grind-#2 corner in the armed state vs route 47's 6.9 s (11.6×)**.

| arm | secs | bursts | 40–49 MAX | expected @Kd=2 | **P(0)** |
|---|---|---|---|---|---|
| `r47`+`r4a` **ON** | **158.7** | **0** | 156.6 | 7.62 | **0.0005** |
| `r47`+`r4a` OFF | 151.0 | 0 | 96.9 | 6.50 | 0.0015 |

Corner-conditioned, pooled ON: expected 9.80, **P(0) = 0.0001**. **Zero further seconds needed in either
arm** ⇒ *"it needs a parking lot, not a build"* is **satisfied**. Observed max 156.6 vs Kd=2's 1830.7
(11.7× down) ⇒ not a threshold artefact.
★★ **GRIND #1 STILL FIXED, AND STRONGER**: `r4a` **0.38 [0.21, 0.55]**, V67 pooled **0.40 [0.27, 0.58]**
vs the Kd=1 pool (null **[0.88, 1.13]**) — statistically **on top of the Kd=2 pool (0.39)** while leaving
manual steering stock. Arm-matched: **engaged 0.321 [0.218, 0.541] vs disengaged 1.151 [0.698, 1.521]**,
replicating route 47's one-arm-only suppression more strongly (placebo row 0.96–0.99). ✅ Flight-clean:
`ST==4` **0/35,994** both ways, `ST==3` 0, zero `steerUnavailable`/`canError`/`controlsMismatch`.
⚠ Grind #1 appeared **once** (seg 21, 21.5 Hz, 3684 counts p-p, 1 window of 114) — the route was not
*incapable* of showing it. n = 1.

🛑🛑 **THE HIGHWAY SYMPTOM: A WELL-POWERED NULL, AND A PRE-REGISTERED HYPOTHESIS OF MINE REFUTED.**
I pre-registered **H1** — *"the highway resonance is grind #2's mechanism at a higher mode, so the EVENT
RATE should rise with dose"* — with its predictions stated before looking, because the prior null used
**pooled medians**, which are blind to a rare threshold event by construction. **H1 failed.**
**The veto ran first and cleared decisively: there is NO LINE AT ALL in 30–49.5 Hz at highway** —
averaged-periodogram prominence **1.32–3.83** (bar), **1.23–2.13** (`ay`), **1.26–1.76** (`gz`) against
the kit's **>4** criterion, on **every route, every build, every channel**. The same estimator resolves
**wheel order 1 at prominence up to 79** (10.94→12.61→13.66→15.40 Hz across speed bins; Theil-Sen
**+0.4836 [+0.4806, +0.4863]** vs order 1's 0.4808).

| band | 2.00/1.00 | 2.44/1.00 | split-half null | min detectable |
|---|---|---|---|---|
| **18–22 (positive control)** | **0.565 [0.329, 0.984]** | **0.319 [0.130, 0.661]** | [0.50, 2.30] | 1.51× |
| **40–49** | 0.855 [0.432, 1.702] | **1.152 [0.496, 2.690]** | [0.36, 2.50] | **1.61×** |

⇒ **Two independent statistics — pooled level and event rate — reach the same null**, with the positive
control firing on both. **The earlier null was NOT a statistic-choice artefact.** Command↔bar coherence
in event windows **0.169 vs 0.166** background (grind #1 was **0.917**).
★ **What the highway events ARE:** the **top tail of smooth maneuver loading**, not a distinct mode.
No step — P(event) rises through every decile of steering rate from the 5th up (ρ **+0.420**); trigger is
a **~1.5 s steering-rate transient** (median |rate| 1.0 → 5.0 → 6.5 → **18.0** → 5.0 deg/s at constant
speed); **hands-off confirmed 19/20**; **rail duty 0.00 on every event**; duration 0.22–0.87 s.
⇒ 🛑 **NO CONTROL-PATH CHANGE IS SUPPORTED.** Below 50 Hz there is nothing to find. Either the operator
is correctly perceiving the loading effect, or the symptom is **above 50 Hz** — and `gp-0x671a` is now the
only instrument that can tell those apart.

★★ **THE OPERATOR'S OWN CHARACTERISATION, 2026-08-03** (his answers reframed the session): **fixed pitch**
⇒ a **mode, not a wheel order**; **hands OFF for sure**; **threshold-like**; **feels it, does not hear
it**; **has never driven it LKAS-off at highway.** Data verdict: **hands-off CONFIRMED** (19/20);
**threshold-like CONTRADICTED** (smooth through every decile); **fixed pitch rules out an ORDER but NOT
>50 Hz** — aliasing preserves apparent-frequency stability.
🛑🛑 **THE CORPUS HOLDS 1,177.4 s OF ENGAGED DRIVING AT v ≥ 25 m/s AND 0.0 s OF IT LKAS-OFF** — ⚠ quote a
**threshold** with this number or it cannot be reconciled with the 2,035 s / 1,450 s figures below;
engaged seconds by threshold are 2,403.9 (≥12) · 2,006.0 (≥15) · 1,438.3 (≥20) · **1,177.4 (≥25)** ·
781.2 (≥28). ✅ **The load-bearing half needs no threshold: disengaged is 0.0 s at EVERY cut from 12 to
28 m/s** — verified two independent ways
(openpilot `carControl.latActive` **and** car-side raw CAN `0x18F STEER_CONTROL_ACTIVE`), across 6,034 s
and eleven routes; **0.0 s off above 15 m/s vs 2,035 s on; 0.0 vs 1,450 above 20 m/s.** His
*"only during LKAS-engaged"* report **has never been testable**. It is already **99.3% hands-off** at
highway, so the published analyses were not diluted. ⇒ ★★★ **ONE HIGHWAY RUN WITH LKAS OFF IS THE
HIGHEST-VALUE ACTION AVAILABLE** — no instrument, no toggle, no build.
⚠ **79.8% of all corpus exposure above 28 m/s is route 47 alone** ⇒ above 28 m/s **dose is confounded
1:1 with route.** ~4 min of engaged highway >28 m/s on another build breaks it.

🛑 **SIX CORRECTIONS THIS SESSION — read before quoting any of the affected numbers.**
1. **"At highway, 40–49 Hz IS wheel order 3 (p50 2.994)" is RETIRED** — that p50 is an **estimator
   artefact**: `order = f0·CIRC/v` returns ≈3.00 *by arithmetic* whenever a band-limited argmax sits near
   the centre of 30–49.5 Hz at ~28 m/s. **Order 1 at 10–16 Hz is real and survives** (prominence up to
   79), and the general "don't mistake a wheel order for a firmware effect" warning stands.
2. **A "fixed 42 Hz mode" was found and WITHDRAWN the same session** — a median-of-per-window-argmax
   estimator manufactures a line at band centre when none exists, and it beat the alternative at
   **ΔBIC 249–460**. Averaging the periodograms first made it vanish. ⇒ **Average periodograms, then
   peak-find.** The CVT/engine-order alternative was also tested and killed (required slope
   −0.0333 Hz/rpm vs measured **−0.00071 [−0.00251, +0.00084]**).
3. **`gp-0x6a5e` is voted VEHICLE SPEED, not driver torque** (settled 2026-07-29; two live documents still
   carried the stale label at the `gp-0x671a` release site). The downstream *"the timer reloads
   constantly"* conclusion is **SUPERSEDED** — speed does not dip at every direction change.
4. **`soundPressure` is 0–8000 Hz analysed** (one RMS over 1600 samples at 10.000 Hz), **not** the
   recorded "16–48 kHz".
5. **`diff_build_vs_stock.py` was emitting FALSE POSITIVES** — a stale table plus two latent bugs (a
   compound-label selector that silently printed nothing, and `sar imm5` shape claimed for every code
   edit). **A gate that cannot fail informatively is worse than no gate.** Fixed; `--self-test` now
   injects a stray byte and proves it still fails. All ten builds V59→V68 exit 0, zero unattributed.
6. **The retracted "bus = 8 × deg/s" was still live inside `build_v68_tva.py`** and is struck; the stale
   `assert 1.4 < headroom < 1.5` is replaced by an assert on **the contradiction itself**, so it cannot
   rot back in.

★ **THE MICROPHONE NULL BEARS VERY LITTLE WEIGHT ON A TACTILE EVENT — quantified.** It detects a **25.3%
excess in acoustic power** at highway; its only positive control is grind #2 at **4.14×**, so the one
demonstrated detection sits **64× above** the smallest event the null excludes, with nothing in between.
That control was validated at **creep** (floor 0.0193) but highway's floor is 0.0606 — **9.9× the power**.
And `soundPressure` is one RMS over **0–8 kHz**, versus the ear's ~1/3-octave critical bands (18.5 Hz at
80 Hz) ⇒ a **26.4 dB** bandwidth penalty. **The operator is the better instrument here and he reports
feeling, not hearing.** ⇒ downgrade, do not quote it as independent corroboration.
🛑 **RAISING THE COMMA IMU ODR IS DECLINED — and NOT only on the standing no-openpilot-modifications
rule.** It is **not** confined to the measurement path: `locationd` → `livePose` →
`controlsd.py:120-121` **lateral roll compensation**; and `locationd` derives its validity limits from the
**declared** service frequency, so a real-vs-declared divergence silently mis-scales them. The fork also
already shows **84 `selfdrivedLagging` / 52 `commIssue` / 24 `locationdTemporaryError`**, and `locationd`
is precisely the process whose input rate would be multiplied. **Moot regardless** — the firmware route
reaches the same band at lower cost. ⚠ Separately: `rawAudioData` (16 kHz PCM) is **already published
live** and gated only by the user-facing **RecordAudio toggle** — available with **no code change**, if
acoustic spectra are ever wanted.

⇒ ★★★ **RECOMMENDED: KEEP V67's CONTROL PATH. FLASH THE REVISED V68 AND DRIVE HIGHWAY WITH LKAS OFF.**

---

★★★★ **THE PRIOR HEADLINE, 2026-08-02: V67 FLEW AND IT IS THE BEST BUILD THIS KIT HAS MEASURED —
GRIND #1 FIXED AND THE CREEP GRIND #2 ELIMINATED. THE NEW HIGHWAY SYMPTOM IS *NOT* THE RATE LANE.**

Route **`47`** (`75604b0a432fdc89_00000047--3e0b6134c0`), 26 segments, **1,495 s**, an ordinary
street → highway → street → parking-lot commute (not a provoked test route).

✅ **The probe is live and the gate works.** 150,327 frames, decoded two ways: byte4 takes exactly two
values `{0x87, 0xC7}`; **`bit6` == `carControl.latActive` in 150,302/150,327 = 99.983%** (the 25
disagreements are single-frame transition edges); **`bit5` (`gp-0x671d`, the masking risk) = 0** and
`bit4` (`gp-0x671a`) = **0 in every frame**; `illegal` = 0; VOID = 0. ⇒ V67's arm was a **clean binary**
— stock LERP vs `0xC6446` = 5244, nothing masking it. ⚠ `bit4` is now a **wasted rung** (V64 closed it).
✅ **FLIGHT-CLEAN:** `ST == 4` = **0/150,327** (zero-EME streak now past 500k frames), `ST == 3` = 12,
zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/`immediateDisable`/
`steerSaturated`.

★★ **THE WITHIN-ROUTE GATE A/B — route 47 is the first route containing BOTH doses**, with the arm state
recorded per frame, so the contrast needs no cross-route comparison. 18–22 Hz engaged-creep, cell-
stratified, episode-clustered: **ENGAGED arm 0.524 [0.337, 0.804]** vs the Kd = 1 pool (and 1.183
[0.773, 1.617] vs Kd = 2), **DISENGAGED arm 1.055 [0.669, 1.354]** vs Kd = 1. ⇒ **suppression in ONE arm
only** — V67's conditional design, measured, and the first evidence ever to separate V66 from V67
(their probe payloads cannot). 🛑 28 windows / 11 episodes — strong, not proof; confirm the `.rwd` name.

★★ **GRIND #1 IS STILL FIXED** — engaged creep, 18–22 Hz, p90 of window envelope p99, episode-bootstrapped
against the Kd = 1.00× pool (split-half null **[0.90, 1.12]**):

| dose | route(s) | secs | 18–22 p90 | **ratio [95%]** |
|---|---|---|---|---|
| Kd = 0 | V61 `r31` | 33 | 1290.0 | **1.50 [1.40, 1.62]** |
| Kd = 1.00× | V58 `r2b` + V59 `r2c` + V64 `r35` | 173 | 860.4 | 1.00 (ref) |
| **Kd = gated (V67 `r47`)** | | **22** | **480.9** | **0.55 [0.35, 0.65]** |
| Kd = 2.00× | V62 `r37` + V65 `r3a`/`r3b` | 375 | 337.2 | **0.39 [0.32, 0.48]** |

Monotone in dose, all far outside the null. V67 ≈ V62 (CIs overlap), as the arithmetic predicts.
⚠ **V67's engaged-creep exposure is only 22 s / 17 windows** — route 47 was a commute. Read the CI.

★★ **THE CREEP GRIND #2 IS GONE.** Creep, 40–49 Hz, burst = a 2.56 s window with envelope p99 > 500
(the V62/V65 bursts ran 2000–4000):

| dose | LKAS ON secs / MAX / bursts | LKAS OFF secs / MAX / bursts |
|---|---|---|
| Kd = 1.00× | 173 / 110.6 / **0** | 137 / 89.8 / **0** |
| **Kd = 2.00×** | 375 / **1830.7** / **18** | 140 / **1469.6** / **6** |
| **V67** | 22 / **83.5** / **0** | 91 / **48.8** / **0** |

🛑 **The two arms are NOT equally supported.** Manual: expected 3.91 bursts, **P(0) = 0.020** — solid.
**Engaged: expected only 1.04, P(0) = 0.35 — UNRESOLVED**, and that is exactly the operator's own
uncertainty. **It needs a parking lot, not a build.**

🛑🛑 **AND THE HIGHWAY SYMPTOM SHOWS NO RATE-LANE DOSE RESPONSE — a prediction of mine, refuted.**
The enabler: **route `2b` (V58, Kd = 1.00×) carries 227 s of highway-engaged driving** that two sessions
had assumed did not exist. v > 20 m/s, engaged throughout:

| dose pool | blocks | secs | 40–49 p90 | **40–49 MAX** | blk>300 | **ratio vs Kd=1 [95%]** |
|---|---|---|---|---|---|---|
| Kd = 1.00× (`r2b`+`r2c`) | 27 | 276 | 117.4 | **648.4** | 2/27 | 1.00 |
| Kd = 2.00× (`r37`+`r3b`) | 41 | 420 | 127.5 | **300.0** | 0/41 | **0.970 [0.787, 1.154]** |
| Kd = 2.44× (`r47`) | 83 | 850 | 93.6 | **488.2** | 6/83 | **0.938 [0.764, 1.184]** |

**Split-half null [0.73, 1.37] — both ratios inside it. No ordering, and the corpus-maximum highway
envelope (851.5 counts, 30–49 Hz) is on V58/`r2b` at Kd = 1.00× — the STOCK rate lane.** Manoeuvre-
conditioned: 40–49 = **0.999 [0.79, 1.31]** and **0.884 [0.67, 1.28]**.
✅ **Positive control, so this is not a dead estimator: 18–22 Hz IS suppressed at highway on the Kd = 2
arms** — manoeuvre-conditioned median **0.509 [0.39, 0.92]**, outside the null.
⚠ The one band outside the null, **10–16 Hz (1.55/1.50), is WHEEL ORDER 1** (order 0.996–0.999 on all
five routes) — tyre balance between drives months apart, **not** a dose effect.
🛑 My own first pass reported *"max 341/155/267, zero windows above 500"* — **both halves wrong**, my
estimator ran 1.4–1.9× low by skipping the detrend + Hann taper that `_grind2_lib.win_env` applies. The
corrected numbers **strengthen** the null.
And the identity question is settled by amplitude: creep grind #2 runs f0 43–45 Hz at prominence
**48–1062×** and envelope **2000–4000**; the highway population runs f0 45–47 Hz at prominence **~6×**
and envelope **155–370**. ⇒ **Not grind #2.** The operator's *"maybe this is a grind #3 or #2.5"* stands.

⇒ 🛑 **I PREDICTED THE OPPOSITE FROM ARITHMETIC AND WITHDREW IT.** V67 genuinely delivers **2.44×** at
highway — its maximum, 22% above V62's 2.00× — because a flat scalar arm replaces a surface Honda
**rolls off with speed**. That is correct arithmetic and it makes a tidy story with the operator's
report. **The data does not support it.** Building V68 on it would have been this kit's recorded failure
mode — *a statistic computed correctly over the wrong population* — for the fourth time.

**What IS real at highway:** within route 47, 21 maneuvers vs 21 **matched** straight-line controls give
1–4 Hz 1.21 · **6–9 2.78** · 10–16 1.41 · 18–22 1.86 · 24–28 1.88 · 30–40 1.58 · **40–49 2.13**
(nulls ~[0.6, 1.5]) ⇒ **broadband from 6 Hz up**, with 6–9 Hz rising *more* than 40–49 Hz, at absolute
levels ~50× below the creep bursts. A maneuver loads the wheel and everything gets noisier.

⚠ **AND THE MICROPHONE ALSO SEES NOTHING — but see the headline: this null bears VERY LITTLE WEIGHT on a
TACTILE event, and the operator reports feeling rather than hearing.** 🛑 **CORRECTED 2026-08-03:
`soundPressure` is one RMS over 1600 samples of 16 kHz PCM ⇒ 0–8000 Hz ANALYSED**, published at
10.000 Hz — **not** the "16–48 kHz" this line used to claim. That correction is load-bearing in the
*other* direction: the **26.4 dB** bandwidth penalty versus the ear's ~1/3-octave critical bands, which is
what downgrades this null, **depends** on the band being 0–8 kHz. Anyone trusting the old figure will
**over-weight** the null. Highway maneuvers vs matched straight-line controls, paired: **un-weighted 1.069 [0.960, 1.184]** against a split-half null of **[0.793, 1.264]**; A-weighted 0.905 [0.647, 1.165]; dB 0.985. **All inside their nulls**, and a low-frequency event would have shown as un-weighted-up / A-weighted-flat. ⇒ **three independent instruments agree.** ⚠ Bounded power: a 10 Hz *level* under highway road noise, n = 21 pairs — it bounds the effect, it does not prove silence. `analysis-2020accord/r47_microphone_test.py`.

🛑🛑 **THE HARD LIMIT: BOTH INSTRUMENTS ARE BLIND ABOVE ~50 Hz.** CAN grid **100.000 Hz exactly** (Nyquist **50.00**);
comma IMU **101.02 Hz** (Nyquist **50.51**) — settled by a lattice fit (77 µs vs 2889 µs) and a synthetic
fold test in which **7 of 7 tones fold per 101.02 Hz**; my earlier 99.9–100.5 came from the dt *mean*,
which ~1% dropped samples inflate. So there is **0.51 Hz** of headroom — but headroom is the wrong
quantity: the alias discriminant is a **1.021 Hz apparent-peak difference** and the measured sem is
**0.856** where ≪0.34 is needed. Resolving it needs a log at a different IMU ODR (208/416 Hz). If the
felt highway vibration is above 50 Hz, nothing in this kit can see it, and every null above is silent
about it. This also re-confirms that IMU/CAN frequency agreement carries **no** information about the
44.9 vs 55.6 Hz alias.

🛑🛑 **THREE CLAIMS OF MINE, MADE AND RETRACTED THE SAME NIGHT — read this before quoting any
rate-axis number.** I published (a) *"bus counts = 8 × deg/s"*, (b) *"the rate axis is arithmetically
dead — all three populations sit in the flat `[0,400]` segment"*, and (c) *"V67's build note has a units
error; its arm delivers 1.94×"*. **All three are WRONG.** Settled two ways: regressing `rate_c` on the
differentiated ANGLE channel gives slope **0.95–1.00, r ≥ 0.985** ⇒ **the bus rate field IS deg/s**; and
at 4.7121 counts/deg-s the inner breakpoints are **85 / 297 / 637 deg/s**, which real driving reaches
(|rate| peaks at **521 deg/s** over 407,617 frames), whereas the wrong scale would put them at
679 / 2377 / 5093 where Honda's 2× rolloff could **never engage**. ⇒ **V67's build note was CORRECT**
(LERP 2622 ⇒ exactly **2.00×**), and **the rate axis IS usable**: grind #1 ~603, creep grind #2 ~1206
(both on the `[400,1400]` rolloff), highway ~141–198 (flat; X1 = `0x0190` exactly, and Y0 == Y1 in every curve **except** mode-10's 50 km/h record `0xD2AEC` (2305 vs 2304 — a +1 rounding artifact, 0.04%, behaviourally nil, but an exact equality test breaks on it)). **The error was composing two unverified structural relations into a scale instead
of measuring it against a channel already in the cache.**

★ **DESIGN A — the best-characterised alternative, ONE halfword**: `0xD2ABC` (the 10 km/h record's
`Y[1]`) **2561 → 7051**. grind #1 **2.00×** · creep grind #2 **1.22×** (vs V67's 2.18×) · highway
**1.00×** (vs V67's 2.44×). Blast radius clean two ways, no float mirror, CRC block #41 only, never
edited in any build; saturates at `|dtorque| ≥ 1190` vs a measured max of 839. 🛑 Costs: it is **not**
LKAS-gated (so unlike V67 it changes manual feel at low speed), and the multiplier **humps to ~2.45×
near 10 km/h** because `0xD2AB0` *is* the 10 km/h breakpoint record. **Not recommended while V67 already
has grind #1 fixed and creep grind #2 at zero bursts** — it would trade a measured property for margin
on quantities already at zero.

🛑🛑 **SUPERSEDED 2026-08-03 — BOTH ORDER FIGURES BELOW ARE ESTIMATOR TAUTOLOGIES. See the headline,
item 1 of the corrections block.** `order = f0·CIRC/v` returns ≈3.00 *by arithmetic* whenever a
band-limited argmax sits near the centre of 30–49.5 Hz at ~28 m/s — **and 1.995 has the same defect**
(26–32 Hz has band centre 29 Hz; at 28–30 m/s that ratio is ≈2.0 whatever the spectrum contains), so the
two do **not** corroborate each other; they are one tautology counted twice. Averaged-periodogram
prominence in 30–49.5 Hz is **1.23–3.83** against a **>4** criterion, on every route/build/channel ⇒
**there is no line there at all.** The generalised rule: a matching order is evidence only when the band
is **wide relative to the order spacing**, or when the order is **tracked across a speed sweep**.
✅ **What survives:** 10–16 Hz **order 1 is real** (prominence up to 79, order 1.00–1.02 per bin), and the
general "do not mistake a wheel order for a firmware effect" warning stands — better founded, not weaker.
Old text kept visible below rather than overwritten:
> 🛑🛑 **A TYRE TRAP THAT WOULD MANUFACTURE "GRIND #2 AT HIGHWAY":** at highway the persistent 40–49 Hz
> **line is wheel order 3** (measured per-window order p50 **2.994**; 26–32 Hz is order 2 at **1.995**,
> n > 600). At 30.8 m/s order 3 = **44.3 Hz**, one bin from grind #2. The bursts themselves are NOT the
> order (on/off-order power ratio 6.94 in quiet windows, **0.82 inside bursts**).

⚠ And `fs_of()` is
biased **+0.5–1.4% route-dependently**: the true `0x14A` rate is **100.000 Hz**, so grind #2's
"44.9 Hz" is **44.6 Hz** and the between-route frequency spread was the instrument, not the car.

🛑 **NO SPEED- OR TORQUE-CONDITIONAL BYTE EXISTS TO GATE ON**, over two independent search passes —
every candidate is multi-valued, inline-only, standstill-only, dead (`0xC62EA` = 0 since V53), or
answers the same "LKAS applying" question V67 already found insufficient. The architectural reason:
this firmware's idiom for speed is **"always LERP, never threshold-and-latch."**
🛑 **Do NOT repoint the mask arm `gp-0x671d`**: it is a rising-edge counter driving **DTC 0x5e**, read by
**8 functions** including 4 reads in the motor-off dispatcher `FUN_0003d4a2`, where an edge-detector on
the counter forces a retry path. Unlike the dead `gp-0x683c` it is a **live fault response**.
🛑🛑 **The >50 Hz probe is DEAD at the proven cave site**: hook `0x55C0E` runs at **100 Hz (task 5)**,
not 1 kHz — it is the CAN-`0x14A` frame builder reached only via handler slot 10 ← `FUN_00022ca0` — so
the cave **cannot observe 1 kHz content at all**; and **no stock writer ever clears bits 7:3** of
`gp-0x1514` (8 accesses, all masked RMW), so a sticky latch could never clear. ✅ Separately,
`gp-0x683c` **is** a free `.data` byte on V67+ (V67 removed its only reader; two boot loops zero it) —
useful cave state in future, but it does not rescue the 100 Hz problem.
✅ **`gp-0x67ac` is CLOSED as of 2026-08-03 — it is provably 0 on this car, so the lanes CANNOT drop
out.** (Was: *"OPEN and matters"*.) The mechanism is real — when it is **exactly 1** (`0x3aa3c cmp 0x1`
→ `cmovh`; a value ≥ 2 does **not** skip), `FUN_0003aa2c` routes around the branch that adds r24/r26 and
**both lanes leave the aggregate entirely**, regardless of arm. But it can never be 1 here: the per-slot
role table `tp+0x5124` = `0xC4124` reads **`[0,0,5,0,5,5,0,0,0,5,0]`** and `gp-0x617c[slot]` is set to 1
only for roles **6 or 7**, so the OR-latch never fires. ⇒ **the highway null was NOT reading a
disconnected lane** — retired analytically rather than measured.
🛑 **This is a CALIBRATION fact, re-checkable in one read — NOT a structural guarantee.** `build_v68_tva.py`
now re-reads `0xC4124` every build and **STOPS** if any slot ever carries a 6 or 7; `verify_v68_image.py`
asserts the same bytes independently. If that table ever changes, `gp-0x67ac` is live again and this
paragraph reverts. ⚠ OPEN, not verdict-affecting: `gp-0x61a0`'s writer (search the **callers** of
`FUN_00026c80`) and `gp-0x61e8`'s identity.

⇒ ★★★ **RECOMMENDED: KEEP V67 ON THE CAR. NO CONTROL-PATH CHANGE IS SUPPORTED.** The two real gaps are
**(A)** 22 s of engaged-creep exposure — closed by a 5-minute parking-lot drive, not a build — and
**(B)** the >50 Hz blindness, which needs a probe that samples inside the 1 kHz task and reports a
**sticky** HF flag. Reproduce every number above with
`analysis-2020accord/r47_orchestrator_checks.py`; the surface arithmetic is in
`analysis-2020accord/v68_design_math.py`.

🛑 **CLOSED, NEGATIVE — the highway symptom is NOT the ratchet.** I raised it as an open lead because
6–9 Hz rose most in the within-route maneuver contrast. It does not survive: highway-manoeuvre f0 is
**9.13 Hz** (parking-lot ratchet 7.46/7.69), it **moves to 11.13 Hz in cruise** (a mode does not move),
and the ratchet's 15 Hz harmonic lock is **absent** (0.294 vs 0.598). Cross-dose manoeuvre-conditioned
6–9 Hz = **1.050 [0.869, 1.546]** and **1.021 [0.683, 1.787]**, null [0.68, 1.38] — both inside.

★★★★ **THE HEADLINE, 2026-08-01 (LATEST): THE ROOT CAUSE OF "GRIND #2" IS V62's OWN FIX, AND THE
BAND TABLE SHOWS IT AS ONE KNOB DOING BOTH THINGS.**

The operator flew **V65** (= V62's control-path edits byte-identical + the saturation-ladder probe) on
two new routes — `3a` (`4e55c1e0f4`, grind #2 demonstrated **with LKAS ON**) and `3b` (`a4a7f4dbf1`,
demonstrated **with LKAS OFF**, then unrelated highway) — and reported that V62 fixed the original
grinding but **introduced a second one**: a whole-car resonance at low speed under significant *driver*
steering input, *"almost like I have a subwoofer"*, **present regardless of LKAS engagement**.

**Corner-conditioned extreme-tail maxima, Kd = 1× vs Kd = 2×, 219 blocks** (corner = creep ∧ |driver
torque| ≥ 1200 ∧ |angle| ≥ 100°):

| band | Kd=1× | Kd=2× | **ratio** | p |
|---|---|---|---|---|
| 1–4 Hz (driver) | 4709 | 4763 | **1.01** | 1.00 |
| 6–9 Hz (ratchet) | 2773 | 3335 | 1.20 | 0.037 |
| 10–16 Hz | 2520 | 2005 | **0.80** | 1.00 |
| **18–22 Hz — GRIND #1** | 3656 | 1269 | **0.35** | 1.00 |
| 24–28 Hz | 485 | 1289 | **2.66** | 0.013 |
| 30–40 Hz | 373 | 1113 | **2.98** | 0.013 |
| **40–49 Hz — GRIND #2** | 301 | **3526** | **11.71** | **0.0003** |

⇒ ★★★★ **A MONOTONE FREQUENCY RESPONSE WITH A CROSSOVER BETWEEN 22 AND 24 Hz** — `0.80 → 0.35 → 2.66
→ 2.98 → 11.71`, with **1–4 Hz flat at 1.01** as a control. **Not generic roughness.** V62 **cut grind
#1 by 2.9× and raised grind #2 by 11.7×, with one knob.**

**Why:** `gp-0x4f62` is a **4-sample finite difference at 1 kHz** (`2*(x[n]−x[n−4])/4`, delay cal
`0xC6C42` = 4). A differentiator's gain **rises** with frequency — **1.93× at 41.6 Hz vs 20.9 Hz** —
so V62's *flat* ×2 raised the high band harder, in absolute terms, than the mode it fixed. V62's build
note computed selectivity only against the **driver** (1 Hz, 14.6:1) and never against a **higher**
mode, where the ratio runs the wrong way. Arithmetic: `analysis-2020accord/rate_lane_frequency_response.py`.

🛑 **A FILTER CANNOT FIX IT — structural, not numeric.** A differentiator rises +20 dB/dec, one real
pole falls −20 dB/dec ⇒ the cascade is **flat** above the corner, so one pole drives the 41.6/20.9
selectivity toward 1.0 and never below. Two poles low enough to bite by 42 Hz cost −92° at 20.9 Hz and
**destroy the damping V62 bought**. Raising the delay cal `0xC6C42` fails identically. **Do not
re-propose either.** ⇒ the separation must come from an **operating condition**, not from frequency.

✅✅ **AND THE COMMA IMU REPRODUCES THE DOSE-RESPONSE INDEPENDENTLY.** Same corner, Kd=2×/Kd=1× on the
accelerometer/gyro — a sensor sharing **no signal path** with the EPS (first use of the IMU in this kit):
**1–4 Hz p95 0.76 · 18–22 Hz 1.20 · 24–28 Hz 0.65 · 30–40 Hz 1.25 · 40–49 Hz p95 6.27, max 6.71.**
Medians ~1 everywhere (the phenomenon is in the tail); the rise is confined to 40–49 Hz.
⚠ **The IMU does NOT show grind #1's reduction and its grind-#1 positive control is weak** — a real
limitation, but physically coherent: grind #1 is a **torsional column mode** that need not reach the
chassis, grind #2 is the one the operator says *"makes the entire car vibrate"*. **The IMU's
selectivity matches the operator's own description of which one shakes the car.**

**Grind #2 itself:** ~**44.9 Hz**, sd 5.4, n = 43, **Q ≈ 37**; **NOT a harmonic** of grind #1 (slope
0.173 [−0.92, 1.59] against the 2.0 a harmonic needs); during bursts the IMU carries **20–50× its own
baseline**, ρ 0.23–0.55 with the CAN band at p ≪ 1e-70.
🛑 **Its frequency is ALIASED and unresolved** — ⚠ *numbers superseded 2026-08-03: the grid is 100.000 Hz
exactly, `fs_of()` was biased +0.5–1.4%, so this line is really **44.6 Hz**; see the headline.* —
CAN is a ~100.5 Hz grid ⇒ 44.9 and ~55.6 Hz are the
same observation; the IMU's ~101 Hz median is only 0.5 Hz away so **IMU/CAN agreement says nothing
about the alias**. It does not block the fix.

**Gating:** grind #1's top-decile creep windows are **100% engaged** (engaged/disengaged p99 **6.63×**);
grind #2's are **84.5%** against a **54.7%** base rate (p99 **1.33×**) ⇒ **grind #1 is LKAS-gated,
grind #2 is not.** Driver torque separates them **>8×** (grind #1 hands-off; grind #2 at `tq_avg`
1600–2700, |angle| 150–265°); steering rate only ~2× at creep with overlapping p90s.

★★★ **AND V65's OWN PROBE ANSWERED ITS QUESTION: THE AGGREGATOR NEVER RAILS.** The 4-level ladder on
`gp-0x6b94`, **120,049 frames**, orchestrator-verified from the caches: liveness **100%**, zero
invariant violations, and **+RAIL 0 / −RAIL 0** — the sum never comes within 20% of its own ±10240
clip. Only **54** frames pass ±4096 (48 negative, 6 positive), and `bit6↔bit3` alternation is
**0.0000 flips/s in every arm**, not as a small number but because **no rail frame exists**.
⇒ **The loop is LINEAR at the aggregator.** No describing-function or saturation reasoning is needed
in this chain, and a linear gain change on any lane **propagates faithfully** — which is *why* V62's
flat ×2 produced the band table above.
★ **All 54 non-neutral frames sit inside grind #2 bursts**, at 36.3–106.1× the segment-median 30–49 Hz
envelope (54/54) ⇒ the aggregator's only large excursions on either route are grind #2, independent
corroboration that it is a real large-signal event **in the command path**.
🛑 **DO NOT apply V65's pre-committed "all four quiet ⇒ NOT another lane gain" clause to grind #2.**
That branch was written to test whether the **RATCHET** is a rail-to-rail limit cycle. Grind #2's
attribution rests on an **on-car dose-response on exactly a lane gain**; an intervention outranks an
inference drawn from a different hypothesis. What the null *does* close is the **ratchet's**
"amplitude-saturated at the aggregator" reading, and the *clipping* rationale for the `0xD2AEC`
breakpoint lever.
⚠ **Stroboscopic caveat:** 100 Hz sampling a ~43 Hz burst cannot claim the sum touched ±4096 only 54
times — the true count is higher and the peak under-estimated. The **route-wide ±8192 null is
unconditional**; "never rails *during a burst*" is the weaker claim. Do not quote 54 as a rate.

✅ **V65 IS FLIGHT-CLEAN AND ADDS TO THE ZERO-EME STREAK.** `ST == 4` = **0** across both routes
(36,991 + 83,058), confirmed a second way by a raw-CAN recount off the `0x18F` src-1 frames rather than
the gridded cache. `STEER_STATUS` only ever 0 or 3, every `ST == 3` in a park/reverse segment. Zero
`steerUnavailable` / `steerTempUnavailable` / `canError` / `immediateDisable`; one `controlsMismatch`
per route; three `steerSaturated` on 3b seg 5. `latActive` 88.2% / 75.4%; CAN 99.94–100.04 Hz.
⚠ **Route `3b`'s highway section starts seg 3 (t ≈ 25 s) — exclude segs 3–12** from any parking-lot
statistic. The demos: 3a LKAS-**ON** = segs 3/4 (six bursts); 3b LKAS-**OFF** = seg 2 only,
`latActive` 0.00.

⇒ **See `docs/V66-V67-DESIGN.md`** for the full design. **V66** (built this session) = V65 with both
`sar` immediates reverted to stock + a four-bit **gate probe**; it is the operator's requested stable
long-drive build **and** the confirmatory intervention. **V67** = keep the ×2 but gate it on a
hands-on/driver-torque cell by repointing the **dead `gp-0x683c` gate** — a **ONE-BYTE** code edit into
a calibration arm that already exists. 🛑 **V67 is blocked on V66's chatter measurement.**

---

★★★ **THE PRIOR HEADLINE, still standing: V62 FLEW AND THE GRINDING IS FIXED. The kit's first measured
fix.** Route `00000037--6231e33f3d`, 15 segs, 86,278 frames. Operator: *"Original grinding at 2–5 mph is
gone!"* Engaged creep, speed-standardised, **episode-clustered** bootstrap: 18–22 Hz **0.124 [0.036,
0.387]** vs V59 (8×), and **0.024 [0.016, 0.234] at |rate| 16–32 deg/s (42×)**, with a **30–40 Hz negative
control at ~1.0** ⇒ band-specific, not a route offset. Transient rates **0.793 / 0.486 / 0.338** at
>200/>500/>1000 counts per 10 ms — monotonically cleaner, and the **lowest p90/p99/>1000-rate of any
build**. ★ V61 quantified on the same statistic: p50 roughness **730** vs V59's 101, >1000 excursions
**376.7/s vs 24.3/s** — the operator's "significantly worse", at 15×.

🛑 **The reported "new grinding at 10–20 mph" is NOT an established regression.** Wall clock measured
(±0.05 s): **10:12:15 → seg 1 t=9.67 s** (5.4 mph, *not* 10–20), **10:23:24 → seg 12 t=18.63 s** (16.3 mph).
Both relocated **independently of the operator's memory**. They are **two different phenomena**:
instant #2 is an ordinary roughness burst **V59 produces ~3× MORE often** (1.042/s vs 0.354/s) — the
*unmasking*; instant #1 is a **0.92 s singleton** carried by **38–46 Hz** (8,478× median) while 18–22 Hz
sat at 1.4× median. 🛑🛑 **Its 43 excursions >2000 are ONE burst ⇒ n = 1.** By distinct bursts/engaged
second: V62 **0.00142 [0.00004, 0.00793]**, V59 **0 [0, 0.00986]** — **V62's CI is INSIDE V59's**;
V61 is **72×** V62. Exposure-matched (v 2–4 m/s ∧ |rate| ≥32 deg/s: 16.14 s vs 15.75 s, one event) ⇒
**p = 0.51, a coin flip.**
⇒ ★★★ **RECOMMENDED: NO NEW BUILD. Fly V62 again and count bursts.** The open question is the *rate of a
rare event*, which needs exposure, not firmware. See "Recommended next steps".

🛑 ~~⇒ ★★★ **AND r26 IS STRUCTURALLY INERT.**~~ **SPLIT 2026-08-04 INTO TWO LEGS — one reversed, one
downgraded. Do NOT read it as a flat reversal.** **LEG 1 (the GATE) is REVERSED [EVIDENCE]**: the gate
kills r26 only at `|gp-0x6bda| ≥ 384`, and hands-off `gp-0x6bda` ≈ **9262 = 24×** that ⇒ **it does not
kill r26 in ordinary driving**, least of all hands-off at creep. **LEG 2 (the MAGNITUDE) is DOWNGRADED
to BELIEF**: `avg`'s cal base `0xC6564` **is** 40 bytes of exact zero with no writer found for the RAM
side (10 of 18 cells) — but **its link to `gp-0x69a4` was never verified**, and `gp-0x69a4`'s real
producer is a **live runtime 10-segment LERP at `0x355C6` in `FUN_000352b4`**. Full chain in THE
HEADLINE §7.
⇒ **"r24 carries the entire lane" now rests on LEG 2 alone, and the re-attribution built on it — V42
"null because r26 was already zero", V61 "WORSE = killing r24", V62 "fix = doubling r24" — is
CONTINGENT on LEG 2, not established.** The underlying on-car *results* all stand either way.
★ The indirect argument that LEG 2 holds: at `a ≈ 1` V67/V68's 6.00× cut on gain_A would put their
engaged total at ~0.94× stock, essentially *on* stock, **yet they measured the best grind #1 result in
the kit** ⇒ `a` is probably small. ✅ **V70's `gp-0x6adc`/`gp-0x6ada` sign pair settles it directly.**

🛑 **THE PRIOR HEADLINE, still standing: V61 made the grinding WORSE, and that inverted the record.** The
torsion-bar RATE lane (`r24`/`r26` in `FUN_0003aa2c`) is the mode's **DAMPER**, not its amplifier. Every
build that touched it — V39, V42, V61 — tested it **downward**. The gradient points **up**.

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it.

---

## 🛑🛑 THE TWO SYMPTOMS ARE DIFFERENT PHENOMENA — settled by the operator 2026-07-30

Everything before this date conflated them. Read this before any other section.

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz** (Q≈36, 2nd harmonic locked at 15.0 Hz) | **FIXED ~20.9 Hz** ⚠ see below |
| where it dominates | parking-lot creep at large steering angle | ⚠ **CREEP-ONLY on V58** — see below |
| variance share, r29 burst | **33.0%** (6–9 Hz) | **5.3%** (19–24 Hz) |
| vs command saturation | **rises 8.42×** with rail duty | falls to 0.74× |
| in openpilot's command? | **no** — command's 6–9 Hz peak is 6.26 Hz, 6.4 bins away | ⚠ **YES** — see below |

🛑 **Three entries in that table were corrected by the V58 drive (route `2b`, 2026-07-30).** They are
left visible above with pointers rather than silently overwritten:

1. **The frequency law `f = 0.177·v + 20.48` does NOT reproduce.** Strict 18–26 Hz band, sub-bin peak,
   speed stable within 1.5 m/s: slope `a = −0.005 … +0.031` at every prominence cut (n = 23–75, v span
   1.13–17.5 m/s). **`a = 0` fits within 0.12–1.48σ; `a = 0.177` is rejected at 3.2–7.1σ.** Model-free
   per bin: 20.65 / 20.83 / 21.90 / 21.50 / 21.61 / 20.46 Hz over 0–20 m/s vs a predicted 20.66 → 23.49.
   ⚠ **Do not rewrite the law off one route yet** — the recorded value came from a *pooled cross-route*
   fit whose own source warned "steering angle shifts it ±2 Hz", and on route `2b`
   `spearman(v,|ang|) = −0.728`. Re-run the strict-band test over V55/V56/V57 first (step 2 below).
   ⚠ **Search-band trap:** a 15–30 Hz or 17–28 Hz band catches the **ratchet's 2nd harmonic**
   (2×8.0–8.9 = 16–17.8 Hz) at road speed; the argmax then steps down to ~15 Hz and fakes a *negative*
   slope. A creep-only window fakes a *positive* one. Use 18–26 Hz **plus a presence test**.
2. **Creep-only, not road speed.** 18–26 Hz prominence by speed (engaged): 141× / 138× / 518× at
   1–2 / 2–3 / 3–4 m/s, collapsing to 29× / 11× / 8× / 7× at 4–6 / 6–10 / 10–14 / 14–18 m/s — and above
   6 m/s the peak-frequency scatter (sd 1.5–2.2 Hz) shows there is no coherent line at all.
3. **~21 Hz IS in openpilot's command.** Verified on the **native 0xE4 grid**, so not a held-last
   resampling artifact: 20.89 Hz at prominence 34.0×, `coherence(cmd, bar) = 0.917` at 20.96 Hz (K=4,
   95% null 0.632); co-located command peak in 8/21 strong-line windows vs 1/11 weak. The bar's line is
   6–7× sharper, which reads as an echo — but **direction is unresolved.** Carrier phase cannot settle it
   (one-sample mailbox skew = 75° at 21 Hz), and the skew-robust **envelope** cross-correlation was
   **inconclusive** (2/4 runs bar-leads, 2/4 command-leads, peak corr only 0.33–0.44). ⇒ openpilot is
   inside this loop; that is a constraint on any firmware fix, not an action.

⚠ **Operator correction, authoritative:** the 7.4 Hz line is the **ratcheting**, not the grinding. An
earlier pass this session called it "the grinding" and concluded the kit had been chasing the wrong mode
for 50 builds. **That conclusion is withdrawn** — the 20–25 Hz focus was correct all along.
⚠ **Steering-angle excitation of the 7.4 Hz mode is a CORRELATION only**, related through return-to-centre.
Do not treat angle as causal.

**The ratchet is not the V42 ratchet.** `STEER_STATUS == 4` fires in **0 of 37,922 frames** across both
V57 routes, so the state-4 governor (`0x454FE`, root-caused and fixed by V42) is not producing it.
Mechanism unknown. It is a plant limit cycle gated by applied LKAS torque, not commanded: over 0.21 s the
command drifts 510 counts while the torsion bar swings **2,791 counts through 3 sign changes**.

---

## ★★ V59 FLEW 2026-07-30 (route `2c`) — the grinding mechanism is a PARAMETRIC PUMP, and it is MARGINAL

**V59 is FLIGHT-CLEAN.** 50,963 frames / 9 segments (2,5,6,7 not uploaded). `ST==4`: **0/50,963**.
No `steerUnavailable`/`steerTempUnavailable`/`canError`/`steerSaturated`. Probe **100% live, 100%
thermometer-monotonic, fault sentinel 0.000%**, stock low bits `&0x07 == 0b111` with zero exceptions.
`0x14A`/`0x18F` at 100 Hz. Two boundary transients only (a boot cluster in `wrongGear`, and one
`controlsMismatch`/`immediateDisable` at the tail of seg 12 — parked, LKAS off). ⚠ The route was NOT
the pure creep route specified: segs 4/8/9 are road speed to 23.6 m/s. It did deliver what `2b` could
not — **50.2 s of engaged + creep + SUSTAINED hands-off**.

### The mechanism
`gp-0x6ba6` is `|filtered signal|` — **rectified** — so it sweeps the boost-amplitude LERP at **2× the
mode frequency**. Measured, engaged+creep+hands-off (13 runs, K=30, periodograms averaged across
DISJOINT runs, never spliced): the thermometer's own spectrum peaks at **42.19 Hz** (= 2 × 21.09 to
within one bin), prominence 11.10×; the 18–26 Hz band shows only 1.23×. **Disengaged: bit5 NEVER
toggles — 0/4 runs, 61.2 s, K=90, prominence 0.00×.** Depth 76.93% <512 / 18.46% 512-1k / 4.57% 1k-2k
/ 0.04% ≥2048 engaged, vs **99.83% <512** disengaged. Toggle rate **25.55/s hands-off, 9.42/s
hands-ON, 0.00/s disengaged** — hands-on the index sits *pinned high*, it does not modulate.
`corr(env, lvl)` is **positive in 11/11 hands-off runs** (median +0.487, +0.485 partialling out
effort); the negative hands-ON value is pure Simpson's paradox. **0 of 33 windows have the index
sweeping with no grinding line.**

🛑 **What V59 did NOT establish.** The index is `|x|` of a bar-derived signal, so 2f coupling and
index-tracks-mode are **arithmetically forced** once the ripple exists — coherence against the bar is
circular and is not evidence. What is new is the **depth**, and that it survives hands-off.
**Causality is not settleable observationally.** Only an intervention separates drive from echo.

### ⇒ It is an AMPLITUDE-GATED BOOTSTRAP, and it is MARGINAL
A pump at 2f into a mode at f is the principal Mathieu resonance; threshold `eps_crit ≈ 2/Q = 0.147`
at the recorded Q = 13.6. Simulating the **literal integer arithmetic** with the confirmed blend
direction, across both open unknowns (task rate; series question):

| `\|tq\|` amp | 1 kHz y4-only | 1 kHz both | 500 Hz y4-only | 500 Hz both |
|---|---|---|---|---|
| 218 (median) | 0.013 | 0.020 | 0.013 | 0.020 |
| 829 (p90) | 0.072 | 0.104 | 0.055 | 0.080 |
| 1451 (p99) | 0.104 | **0.169** | 0.070 | 0.116 |

eps scales with amplitude ⇒ a **bootstrap**: a kick raises the oscillation → the index swings wider →
the modulation deepens → more pumping, until the curve flattens past index 3645 and the clamps bite.
That is why the grinding **bursts** rather than hums, and why it needs a road input to ignite.

🛑🛑 **THE THRESHOLD COMPARISON IS UNDECIDABLE FROM THIS DATA — do not quote a verdict either way.**
`eps_crit = 2/Q` needs the **PASSIVE** Q (the mode's damping when *not* being driven). That is not
measurable while the mode is active, and V59 contains no free decay to measure it from:
- **Ring-down: none exists.** 66 candidate decays, longest **0.63 cycles** — envelope wiggle, not
  damping. The mode does not ring down; it is sustained while conditions hold.
- **Autocorrelation analytic envelope** (biased-ACF triangular taper divided out, tau capped at 25%
  of record) gives apparent **Q median 102, range 22–1083** (n=8 hands-off runs). ⚠ That is the
  coherence of a *driven* oscillation, **NOT** the passive Q — a self-sustained limit cycle has
  near-infinite apparent Q. It cannot be substituted into `2/Q`.

| assumed Q | eps_crit | verdict vs measured eps (0.020 / 0.104 / 0.169) |
|---|---|---|
| 13.6 (recorded, provenance unverified) | 0.147 | marginal — crosses only at p99 |
| 22 (lowest apparent) | 0.091 | **above** at p90 and p99 |
| 102 (median apparent) | 0.020 | **above everywhere** |

⚠ **What the coherence DOES support:** a passive Q=13.6 mode kicked by broadband road noise would
show coherence ~`Q/(pi*f)` ≈ 205 ms. Observed is 0.33–17 s equivalent — **far more coherent than
random excitation of a lightly-damped mode can produce.** ⇒ there is an **active, phase-coherent
drive**. That is consistent with the parametric pump but does not prove it is the drive.

⇒ **Only an intervention decides it. V60 is the discriminator, not just a candidate fix.**

### The structure — golden model was WRONG, and there is a filter nobody had modelled
`FUN_00034a72`: the two amplitude curves do **not** multiply in series. `0xD2888` scales the final
assist term (`sar 0xe,r13` @`0x35008`); `0xD28DC` enters earlier (`shr 0xe,r28` @`0x34C26`) and is
**differenced against `gp-0x6a56`** then clamped ±12000. ⚠ **UNRESOLVED DISPUTE:** a subagent holds
`0xD28DC` is a dead end (3 image-wide refs to state cell `gp-0x69bc`, all in-function). That argument
is **structurally invalid** — a scan of the STATE CELL cannot show whether the blended value is
consumed in a REGISTER the same tick, which is what a slew-limited gain does. The decompiler shows the
blended y1 as an operand of a `>>14`, and a byte scan finds exactly two `>>14` sites in the function,
one of them at `0x34C26` inside the span the subagent claims to have traced. **Not called. It does not
change the verdict** (see the table — both columns are mostly sub-threshold).

★★ **BOTH LERP outputs are SLEW-BLENDED before use** — previously unmodelled entirely. Rate cal
`0xCA06C[10] -> 0xD2006 = 102` (Q10). **Direction CONFIRMED @`0x34be4`** (`cmp r25,r10 / ble` →
instant snap when raw ≤ old): **FALLING is instant, RISING is slowed** — a fast-attack/slow-release
gain reducer. This is what pulls eps down from the raw-LERP values.

### Levers — one clean, three closed
- ★★ **`0xD2006` = 102, the blend coefficient. THE LEVER, and GATE 1 is CLEAN.** Lowering it
  attenuates the 42 Hz pump **without moving the static gain map at all** (the blend converges to the
  same steady state ⇒ DC assist and manual feel untouched). Blast radius byte-verified: exactly one
  pointer (`0xCA094`) references it; the "three identical copies" in `0xD2000` are modes 10/11/12's
  independent entries, not an array; distinct from the ceiling (`0xD2000`) and gain scalar
  (`0xD200C`) for the same mode; not array-consumed. Only other hit is the CRC/block directory.
  ⚠ Expected benefit is **modest and uncertain** — eps is already mostly sub-threshold, so this bites
  only on the loudest bursts. The argument for it is that a *bootstrap* only needs to be kept below
  threshold at the amplitudes where it currently crosses. Feel cost: slower gain recovery after a
  sharp input (tau ≈ 10 ms now, ≈ 24 ms at cal 43 — short vs steering dynamics).
- 🛑🛑 **VOID — CORRECTED 2026-08-06.** The block below says FactorC damping was "already flashed and
  falsified." **That is wrong and was wrong when written.** V44/V47 wrote **modes 10/11** under the `TVAA1`
  assumption; **this car is config row 11 `TVCA4`, modes 24 (manual) / 26 (engaged)** — see `BUILD-LINEAGE.md`
  RULE 7. Both builds were **inert by table selection, not falsified.** The FactorC/FactorE damping approach
  was **never actually tested until V74**, and it is now measured to work on grind #1 (**−5.20 dB per unit `k`,
  CI excludes zero**) while being **flat on the micro-ratchet**. Retained below only as a record of the
  superseded reasoning. **Do not cite it as evidence against the damper.**
- ~~🛑🛑 **FactorC damping (`0xD27BC`/`0xD27C6`) — ALREADY FLASHED AND FALSIFIED. DO NOT RE-PROPOSE.**~~
  **`V44` set `0xD27C6` 0 → 235 and `0xD27DA` 0 → 234 (modes 10/11), flashed, and it was NULL** —
  because **Factor E (`0xC9F84[mode]`, the motor-rate deadzone) re-zeroes the product downstream.**
  **`V47` then attacked Factor E itself** (`0xD2802/04/06`, `0xD2816/18/1A`) → *"marginally quieter at
  5 mph, no effect in motion."* **Both were confirmed 2026-07-28 to hit the LIVE table** (PN → key
  `TVAA1` → config row 2 → INDEX 10 → `0xD27BC`). `BUILD-LINEAGE.md` states it outright: *"the
  missing-damping hypothesis was genuinely tested and IS falsified — do not resurrect it on a 'wrong
  variant' theory."*
  ⚠ **Damping IS exactly zero below 35 km/h** (`Y[0]=0`, all 34 mode tables) and that remains true and
  relevant as *context* — but the lever has been driven from **both** factors and neither moved the
  grinding. V44's *rationale* was withdrawn (it thought the axis was driver torque; it is speed), yet
  **its on-car NULL stands regardless of why it was built.**
  🛑 **This was re-proposed on 2026-07-30 by the orchestrator as "V61", after the loop hypothesis made
  it look freshly attractive — the operator caught it. The build script was written and deleted
  unexecuted.** Cause: the address was named without grepping `build_v*_tva.py` first. **That grep is
  mandatory and it is cheap. FALSIFIED ≠ untested, and a compelling new mechanism is exactly when the
  check gets skipped.**

  ✅ **Salvage — genuinely new and worth keeping regardless:** the damper's **int/float lockstep is
  SAFE for a FactorC-class edit.** `FUN_000347b8` @`0x347b8` *reads* `gp-0x6bd0` (first line,
  `(float)gp-0x6bd0 * 0.0009765625`) and only re-clamps it with an independently recomputed **ceiling**,
  faulting via `FUN_000462e6(0x417a,…)` if the two differ by more than `0.0048828125` = **5/1024**. It
  **never recomputes the four-factor product**, so FactorA/C/Ramp/MotorRate are *not* float-mirrored.
  And the two ceilings are the **same table in two number formats**, byte-verified:
  `INT 0xC77A0[10] → 0xD209C: X=[300,800] Y=[512,1024]` vs `FLOAT tp+0x7554 = 0xC6554: 300.0, 800.0,
  0.5, 1.0`. ⇒ exact agreement, tolerance never approached. **Damper authority at creep is hard-clamped
  to ±512 against the aggregator's ±10240 (≤5%)** — a firmware-enforced bound worth remembering for any
  future damper-lane work. Confirmed 4 ways (`search_instructions`, raw LE byte scan, `get_xrefs_to`,
  and a **split-encoding check** for `movhi`+`movea` construction of the address — only 2 `movhi 0xd`
  exist image-wide and neither resolves near `0xC9E9C`). Modes 8/11 byte-identical to mode 10.
  Escalation map, for any future damper work: `FUN_000347b8` → `FUN_000462e6(0x417a)` →
  `FUN_00016de6(0x1d)`; and `FUN_00034350`'s own entry-time re-check → `FUN_0004613e(0x4179)` →
  `FUN_00016de6(0x1c)` — **one tolerance in two representations** (0.0048828125 × 1024 = 5.0 exactly),
  not two independent gates.
- 🛑 **RECORD CORRECTION — `0xD2018` is not what we said.** It is **data**, one resolved pointer inside
  `FUN_00035154`'s `0xC7888[mode]` ceiling array — `search_instructions` finds zero because it scans
  instruction operands only. And `FUN_00035154` is simply the `gp-0x6bbe` **analog** of `FUN_000347b8`:
  ceiling-only, same ±0.0048828125 tolerance, same escalation, keyed on `gp-0x6a62` instead of
  `gp-0x6ac2`. The old note ("any edit to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table
  `0xD2018` or it may trip") implied a stronger, different mechanism. It is the same pattern.
- 🛑 **`gp-0x6b70` — TRACED AND CLOSED 2026-07-30. It terminates at an already-falsified lever.**
  Full chain, measured: `FUN_00038148` (1 kHz) sums **six UNITY-weighted terms** — `gp-0x6bd0` (damper)
  and `gp-0x6bbe` (boost) among them, cals `0xC63A0/A2/A4/A6/A8/AA` **all = 1024 = exactly 1.0**,
  byte-read — EMA-blended at `0xC63AC` = 102/1024, → `gp-0x6b70` → `FUN_00037fe6` (one of seven
  unity-weighted terms, cals `0xC64AD-0xC64B3` all = 1) → `gp-0x6ad6` → **`FUN_0003a382`** (the real
  PID) → `gp-0x6ad4` → `FUN_0003aa2c`'s aggregator → `gp-0x6b94` → governor → `gp-0x6b98`.
  ⇒ **So boost and damper DO re-enter a second, parallel aggregator at unity gain.** That structural
  fact is new. But **every weight in the whole chain is unity and stock — there is no hidden loop gain
  in the aggregation.**
  ★★ **And the chain's only output-shaping calibration is `0xC6AF0`** — `FUN_0003a382`'s authority
  ceiling, which **V56 already zeroed, flashed: NULL on the grinding, and it cost damping** (V57/V58
  both carry the assertion `"0xC6AF0 must stay STOCK -- V56's mute is falsified"`). Since `gp-0x6ad4`
  has only 2 accesses image-wide, that mute was equivalent to deleting this entire chain's
  contribution. ⇒ **a second independent reason not to hunt loop gain down this path.**
  ⚠ Genuinely untouched by any build (`grep`ed): `0xC63A0-0xC63AC`, `0xC64AD-0xC64B3`, `0xC6200`, and
  whatever produces `gp-0x67ab`/`gp-0x69aa`. Not proposed as levers — recorded as unexplored.
  ⚠ Open: `gp-0x67ab` / `gp-0x69aa` semantic identity (structural role only); `FUN_00026c80`, the
  11-channel mixer feeding them, only partially read.
- ★ **SECOND instance of the over-count scan trap, same session.** `search_instructions` reported
  **21 hits** for `gp-0x6b70`; **19 were false positives** — substring collision against
  `jarl 0x0006b700,lp`. A raw byte scan finds **exactly 2** (writer `0x382d2`, reader `0x38006`).
  Together with the `6bd0`/`0x00076bd0` collision this is now a **recurring** failure mode, not a
  one-off. **Always confirm a hit is a gp-relative operand, not an address literal.**
- ⚠ **The off-by-0x1000 tp trap recurred again** (a subagent computed `tp+0x73a8` as `0xC73A8`; it is
  `0xC63A8`). Self-caught. That is now **five** recorded occurrences.
- ★ **NEW SCAN TRAP — `search_instructions` can OVER-count too.** `operand_pattern="6bd0"` returned
  false positives from **substring collision against the branch-target literal `0x00076bd0`** in
  `FUN_0006bcb2`/`FUN_000757a2`. Every trap on record so far was about *undercounting*; this is the
  first over-count. **Confirm the hit is a gp-relative operand, not an address literal.**
- 🛑 **`0xC63BA` (=512) — PARTIAL ONLY.** Byte-verified 2-stage EMA, alpha 0.5 both stages, blast
  radius fully contained (2 reads, both in `FUN_0003b66a`). But it filters only the **torque** lane;
  the index is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`, via
  `FUN_00041464` ← `FUN_00068f52`'s angle-delta differentiator). Both analysts were right.
- 🛑 **Speed-keyed assist concentration — REFUTED.** `0xD2834` is nearly flat (rel 0.856 / 0.979 /
  0.987 / 0.997 / 0.903 at 0.5 / 3 / 6 / 10 / 18 m/s).

### Closed and corrected by this drive
- ✅ **The damping SIGN is no longer open.** `gp-0x6bd0` (`FUN_00034350`, sole producer, 3 writes) has
  its sign forced to `-sign(gp-0x6abe)` @`0x3469e-0x346a2` — textbook velocity-proportional damping,
  correct by construction. Joins the aggregator at `0x3ac78` in `FUN_0003aa2c`.
- ✅ **The frequency law is rejected a SECOND time.** Route 2c: `a = 0.177` rejected at **2.60σ**
  presence-tested (n=19, 9 runs), up to 7.08σ without. `a = 0` fits at every cut, ~20.4–21.1 Hz flat.
  Crucially the fitted subset is **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728).
  ⇒ **The fixed ~20.9 Hz line is now the record.**
- ✅ **V58/V59 control PASSES** — grinding statistically identical: 7 of 8 jointly speed-and-effort
  matched cells in 0.76–1.41× with no systematic direction, peak frequency within 0.7 Hz everywhere.
  Exactly what CAL-CRC-unchanged predicts; validates the comparison chain.
- ⚠ **CORRECTION to "creep-only":** that holds for the **hands-off** arm. There is a second
  population at **10–13 m/s under driver load** at large angle (prominence 174–651×), verified NOT a
  tyre order (frequency CV 2.2% vs order CV 9.8%; 3.89 is not an integer order). Correct wording:
  *strongest at creep 1–4 m/s; sampling gap at 6–10; still coherent at 10–13 under steering load;
  absent above 14 m/s* (0 of 48 windows pass presence).
- ⚠ **~21 Hz IS in openpilot's command**, confirmed again: native-`0xE4` prominence median 35× (max
  46×) hands-off, coherence **5/5 above the K-appropriate 95% null**. **Direction still NOT settled**
  — envelope cross-correlation splits 2 bar-leads / 3 command-leads, same as V58.
- ★ **Route 2c contains hands-off engaged creep RATCHET episodes** — 7.56 ± 0.36 Hz, within-run sd
  0.07–0.10 Hz, prominence median 783× (max 2142×), 15 windows / 5 runs, at both 9–15° and 133°.
  `STATE.md` previously recorded route 2b gave **zero** and that a dedicated route was required.
  Mode identity unconfirmed — the data exists, that is all.

### Open gates before V60
1. ✅✅ **RESOLVED 2026-07-31 — TASK 5 IS 100 Hz, and it invalidates the eps table above.**
   The rate divider is `FUN_00014be4`, a mod-100 counter (`gp-0x4304`) on the 1 kHz tick. Verified by
   the orchestrator: `tp-0x3814` = `0xBB7EC` byte-reads **`0x000BB920`**, and `idx*0x30 + 0xBB920`
   reproduces **all seven** TCB entry points exactly (`+0x08`), so the wake argument is a **0-based
   task-slot index**, not an abstract group ID:

   | idx | TCB entry `+0x08` | task | condition | **rate** |
   |---|---|---|---|---|
   | 0 | `0x0002214A` | task 1 — arb, `FUN_0003b66a`, aggregator, governor, shaper | every tick | **1000 Hz** |
   | 1 | `0x00022A88` | task 2 | `c & 1` | 500 Hz |
   | 3 | `0x00022B24` | task 4 | `c % 5 == 2` | 200 Hz |
   | **4** | **`0x00022CA0`** | **task 5 — boost `FUN_00034a72` + damping `FUN_00034350`** | `c % 10 == 4` | **100 Hz** |
   | 5 | `0x0002351E` | task 6 | `c == 0x10` | 10 Hz |

   ⇒ **The V59 eps table bracketed 1 kHz and 500 Hz. Both are wrong.** The boost-amplitude LERPs are
   evaluated at **100 Hz**, so a 42 Hz index modulation is sampled ~2.4×/cycle — barely above Nyquist
   and heavily ZOH-attenuated. **The pump could barely act at all**, which is an independent structural
   reason for V60's null on top of the empirical one.

   ★★ **THE BIGGER CONSEQUENCE — a 100 Hz damper cannot damp a 20.9 Hz mode.** `gp-0x6bd0` is
   velocity-proportional damping (sign forced to `-sign(gp-0x6abe)`), and damping only works when the
   force is in phase with velocity. A zero-order hold at 100 Hz costs `360 · 20.9 · T` of transport
   lag: **37.6° average (T/2), 75.2° worst case**, before any plant phase. ⇒ **a structural explanation
   for why EVERY damper lever was null (V44 FactorC, V47 FactorC+FactorE together) that does not depend
   on the FactorC speed-axis argument** — even with both deadzones fully open, the damper is too slow
   to act on this mode. It may even be anti-damping at 21 Hz.
   ⇒ 🛑 **Any fix acting through boost or damping is fighting 38–75° of architectural lag at the mode
   frequency. Prefer task 1 (1 kHz).** V61's edit is in `FUN_0003aa2c`, task 1 — on the right side of
   this. Any future task-5 change needs this in its GATE 2.
2. **`gp-0x6986` / `gp-0x6988` values unmeasured** — they scale the pump. Both are ≤1024 clamps so
   they can only pull eps *down*.

---

## ★★ V70's PROBE — design detail (**it has now FLOWN**; the readouts are in THE HEADLINE §5)

✅ **FLOWN 2026-08-04 on route `50`. Outcome in one line:** **bit6 = 0/18,010 and it is NOT vacuous**
(the replay predicts 311 hits on route 50's own data, stock predicts 52) ⇒ the delivered gain is
**below stock** and `0xC6442` = 1024 is the only arm predicting 0; **bit5 = 0.0000%** ⇒ the five-build
detector null is **GENUINE**; **bit4 tracked bit3** ⇒ **r26 is LIVE**, refuting the inertness claim.
📋 **The pre-registered prediction at the bottom of this section (bit5 reads LOW) HELD** — which is
what makes that null interpretable rather than lucky. **The design rationale below stands as written.**

🛑 **This is NOT a build-status block** — SHAs, filenames and the control path live in the
**"On the car right now — V70"** block further down. **The probe is unchanged from the superseded first
V70**, and everything below holds for any V70 cut.

✅ **DONE — the superseded first V70 is renamed `SUPERSEDED-DO-NOT-FLASH-39990-TVA,A160-V70-…-LKASGATED-
V68CONTROLPATH-…rwd`** and pushed (`accord-firmwares` **`9d44efc`**). The flash directory now holds
exactly **one** flashable `V70`-prefixed file, the ×2 re-cut. Verified from the filesystem, not assumed.
🛑 **WHY IT MATTERED, and the rule it leaves behind: its cave is BYTE-IDENTICAL to the current one**, so
**the probe cannot distinguish the two on-car** — `bit6 ⇒ bit3` gives build-**CLASS** identity, never
**FILE** identity, and it cannot tell two cuts of the same version apart. **The filename was the only
discriminator before a drive.** ⇒ **Any re-cut under the same version number MUST be renamed
`SUPERSEDED-DO-NOT-FLASH-…` the moment it is superseded**, exactly as the two stale V68 artefacts were.
🛑 **AND A SECOND HAZARD IS STILL OPEN — the rename fixed the flash risk, NOT this one.** Both cuts write
`_v70_plain_image.bin`, so the newer one **overwrote** the older image; only the superseded `.rwd`
survives, and `verify_v70_image.py` asserts the current topology so it fails on the old one **by
construction**. ⇒ **a flashable artefact exists that NO gate in this kit can check.**
**The hazard, the recommended builder fix (not yet applied) and what was not attempted are recorded in
`docs/BUILD-LINEAGE.md` Part 2.**

★★ **THE PROBE: 68 of the proven 68 cave bytes, ZERO spare** (base `0xC4B34`, hook `0x55C0E`, extent
unchanged):

| bit | cell | test | bytes |
|---|---|---|---|
| **6** | `gp-0x6ada` | ≥ **+512** (`sar 0x9`) — r24 lane out, post-clip | 14 |
| **5** | `gp-0x67fa` | **== 10** — ★★ **THE STATE GATE** | 12 |
| **4** | `gp-0x6adc` | ≥ 0 — **r26 mirror SIGN** | 12 |
| **3** | `gp-0x6ada` | ≥ 0 — **r24 mirror SIGN**, reusing the already-shifted `r6` (valid: `sar` preserves sign) | 6 |

⭐ **Re-decoded from the image bytes independently of the builder:** the loads at `0xC4B38` / `0xC4B4C` /
`0xC4B58` carry opcodes **`0x39` (`ld.h`) / `0x3C` (`ld.bu`) / `0x39` (`ld.h`)** on `gp-0x6ADA` /
`gp-0x67FA` / `gp-0x6ADC`, with the `ld.bu` displacement parity handled (`hw2 = 0x9807` encodes
`disp = 0x9806`); and **there is exactly ONE store in the cave** — `st.b` @`0xC4B6E` to the CAN payload
byte `gp-0x1514`. **No `st.h` (`0x3B`) anywhere.**
🛑 **The one-bit trap is live on THREE rungs**, including **`ld.bu` `0x3C` vs `st.b` `0x3A` on
`gp-0x67fa`, which has 128 readers** — a slipped opcode there writes the ECU state variable.
★ **V70 is structurally SAFER than V69 here:** V69's third rung read `gp-0x6ad4`, which the aggregator
*consumes* at `0x3ACA8`, so a slip would have corrupted a live lane; **V70's two `ld.h` rungs are both
on ZERO-READER mirrors**, where a slip could only produce a wrong reading.

★ **BUILD IDENTITY IS SOLVED FROM THE VALUE SET ALONE — a first for this kit.** `bit3 = sign(gp-0x6ada)`
is **guaranteed non-constant**, which creates the hard invariant **bit6 ⇒ bit3**: `bit6 = 1, bit3 = 0` is
an **impossible frame**, so only **12 of 16** payloads are reachable. That excludes **absolutely: V53,
V54, V65, V66, V67, V68, V69** — every build from V65 on, **including the one on the car.**
⚠ **Residual, and it stays on the record: V55 / V57 / V58 / V64** are independent-bit probes spanning
all 16 payloads, so they are separated by **filename only**. Six-plus builds back, and **strictly
smaller than V69's residual** (which was its immediate predecessors) — but not zero.
🛑 **Note what this does NOT do: it cannot separate two V70 cuts from each other**, because their caves
are identical. Build-class identity is not file identity.

🛑 **bit4 IS THE SIGN, NOT A MATCHED `+512` THRESHOLD — a deliberate deviation from the spec, and the
reason belongs in the record.** The cave was **exactly 2 bytes short**, and a `≥ +512` null on r26 was
the *predicted* outcome given `0xC6564` = 40 zero bytes — i.e. it would have landed straight back in the
uninterpretable-zero class that wasted all three of V69's rungs.
**COST, STATED: V70 measures r26 LIVENESS, not the quantitative `a`.**

| observation | verdict |
|---|---|
| **bit4 ≈ 1.000 while bit3 toggles** | **r26 inert** — LEG 2 holds, r24 carries the lane |
| **bit4 tracks bit3** | **r26 live** — and V67/V68's gate has been cutting damping **6×** |

★ **UNPLANNED BENEFIT, worth recording:** bit3 is **amplitude-independent**, so it carries the ~7.4 Hz
line **even when the lane never reaches +512**. ⇒ **bit6 measures the ratchet's SIZE, bit3 its
PRESENCE** — *if bit3 detects and bit6 does not, the ratchet is real and small*, which **no prior probe
could have said.**

📋 **PRE-REGISTERED PREDICTION, so the result is interpretable either way: bit5 reads LOW.** V67's
`gp-0x6806` tracked `latActive` at **99.983%**, which a flag going stale in state 10 could not do. ⇒
**bit5 ≈ 0 ⇒ the five-build detector null is GENUINE and those builds are vindicated; bit5 materially
non-zero ⇒ the nulls were on the gate** and the detector programme needs replanning. **Non-vacuous in
both directions** — the failure every V69 rung shared.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**


## On the car right now — **V70** (flashed, driven route `50--50f2e00e8f` 2026-08-04)

**V70 = V69's gateless topology at half the dose** (gate `0x3AA96` stays `c5` (dead), arm `0xC6446`
stays 512; `0xD2A7E`/`0xD2A80` 12288 → **6144**, `0xD2ABA`/`0xD2ABC` 10244 → **5122**) + the 4-bit
**sign probe**. Delivered **2.000× to 10 km/h → 1.000× at and above 50 km/h**, r24 only.
✅ **Flight-clean** (`ST==4` 0, `ST==3` 0, both methods). **See THE HEADLINE for the full route-50
result.** Summary: **grind #1 is BACK at the stock level** (median `e_18-22` engaged creep **729.1**;
CONSISTENT with stock P = 0.635 and V69 P = 0.495, **EXCLUDED** from V62/V65 and V67/V68 at
P = 0.0000); **grind #2 shows 0 bursts but "gone" is NOT established** (highway power 2%); **the
ratchet's Q is measured at ≈ 40**; **bit6 read an uninterpretable zero, bit5 read 0.0000% and
vindicated five builds, and bit4 proved r26 LIVE.**
⇒ ★★★ **V71 IS BUILT AND UNFLASHED** — both lost confirmed fixes restored (`0x454FE`, `0x3AB76`/
`0x3AC20`), the surface reverted to stock, and a probe that reads **the gain in force** rather than a
lane output. SHAs in the V71 build report.

---

## Previously on the car — **V69** (flashed, driven route `4f--61171e660d` 2026-08-04)

**V69 = the gate REVERTED + Honda's own low-speed rate-gain surface scaled ×4** (`0x3AA96` `fb`→`c5`,
`0xC6446` 5244→512, `0xD2A7E`/`0xD2A80` 3072→12288, `0xD2ABA`/`0xD2ABC` 2561→10244) + the RATCHET probe.
Image SHA `48bb4192…`, RWD SHA `e62fcbba…`. See THE HEADLINE at the top of this file for the full route
`4f` result. Summary: **flight-clean; the 4× dose was FULLY DELIVERED (0.0000% above the rail); grind #1
is BACK at creep (2.244 [1.438, 3.191] vs V62, holding under both resampling units); the dose–response is
NON-MONOTONE with a minimum near 2×; the lane-change transient — V69's stated purpose — is
DOSE-INDEPENDENT; all three probe rungs failed for the reasons in §5.**
⇒ **V70 has since flown and answered both** — `gp-0x67fa == 10` reads **0.0000%** and **r26 is LIVE**;
see THE HEADLINE. 🛑 **Two `.rwd` files carry a V70 prefix; the superseded first cut has the OPPOSITE
control path and a byte-identical cave, and is renamed `SUPERSEDED-DO-NOT-FLASH-…`** (`9d44efc`,
filesystem-verified).

---

## Previously on the car — **V67** (flashed, driven route `47--3e0b6134c0` 2026-08-02)

**V67 = V66 + the grind #1 fix gated on LKAS**: `0x3AA96` `c5`→`fb` (repoint the dead `gp-0x683c` gate to
`gp-0x6806`) + `0xC6446` 512→5244, both `sar` sites left **stock**. Route-47 result: **grind #1 fixed
(0.55 [0.35, 0.65]), creep grind #2 ELIMINATED (0 bursts in 113 s vs 24 at Kd = 2×), the gate confirmed
on-car, `gp-0x671d` never fired**, and the new highway symptom shows **no rate-lane dose response**.
⚠ **RE-READ 2026-08-04 — V67's GATE MAY ALSO CUT r26 6.00×, and this is now an OPEN question rather than
a settled harmlessness.** ⊕ **RESOLVED 2026-08-04: r26 IS live, so this IS a 6.00× cut whenever the
gate is repointed — and `0xC6444` is only reachable ON such a build** (THE HEADLINE §3, §8).
The repoint makes **both** cal arms live under LKAS, and `0xC6444` (r26's arm)
stays at **512** against r26's live LERP value of **3072**. That was recorded as harmless *because r26
was believed inert* — a justification that no longer stands on its own (THE HEADLINE §7: the GATE leg is
reversed, the MAGNITUDE leg is only BELIEF). **If r26 is live, V67/V68 is "r24 up 2×, r26 down 6×"**, and
total engaged rate-lane damping falls **below stock** once `a = gp-0x69a4/1024` > **0.848** at 0 km/h,
with **`a` unmeasured.** ⚠ **The counter-argument points the other way and is the leading reading:** the
measured dose–response is only self-consistent if `a` is **small** — else V67/V68 at ~0.94× total would
sit on stock yet measure 8× better than stock. ⇒ **V67/V68 probably is what it says it is; V70's
`gp-0x6adc`/`gp-0x6ada` sign pair confirms or refutes it directly.**

---

## Previously on the car — **V68** (a MEASUREMENT build; flashed, driven routes `4c`/`4e` 2026-08-03)

🛑 **STATUS CORRECTED 2026-08-04: V68 is no longer "built and unflashed" — it flew, and V69 has since
replaced it on the car.** The build note below is kept as written for provenance.

🛑🛑 **TWO `.rwd` FILES CARRY A `V68` PREFIX. ONLY ONE IS LIVE. THE LIVE ONE CONTAINS `fsm67df`.**
The other is renamed **`SUPERSEDED-DO-NOT-FLASH-…-rateaxisprobe-…`** and was never flashed.
**Confirm `fsm67df` in the filename before any flash.** This is exactly the confusion the `bit3`
fingerprint catches *after* a drive — prevent it before.
⚠ **CORRECTED 2026-08-04: this block previously said THREE files, naming a third, `-dropout67ac-`.
That file does not exist and never did** — `git ls-files` and a full-history search of
`accord-firmwares` return **zero** hits for `dropout67ac`, and the only tracked `V68`-prefixed
artefacts are `-fsm67df-detector671a-` (live) and `SUPERSEDED-…-rateaxisprobe-`. The four tracked
`V68`/`V70` artefacts in total are those two plus `-SPEEDSHAPED-…-x2-signprobe-` (live V70) and
`SUPERSEDED-…-V68CONTROLPATH-` (the overridden first V70). 🛑 **A phantom entry in a
DO-NOT-FLASH list is not harmless bookkeeping** — it inflates the apparent hazard, and a future
reader who cannot find the file has to decide whether it was deleted, renamed, or imagined. Verify
this list against `git ls-files` before quoting it.

**⭐ REVISED 2026-08-03. V67's control path byte-identical — V68 vs V67 is EIGHT bytes: 4 cave + 4 MAIN
CRC, zero outside the cave span.** Cave **60/68**, 8 spare. Image SHA `9106044a…`, RWD SHA `332c2cee…`
(source `_v67_plain_image.bin` `5e01bcc4…`).
`39990-TVA,A160-V68-…-LKASGATED-fsm67df-detector671a-can330byte4-0x13000-0x100000.rwd`

**Probe, re-decoded from the READBACK bytes** — a **two-stage sensitivity ladder on Honda's own 1 kHz
oscillation detector**, which the headline shows is a **band-pass peaking at ~61 Hz**:

| bit | cell | test | meaning |
|---|---|---|---|
| 7 | — | const 1 | liveness (0 ⇒ cave did not fire ⇒ VOID) |
| 6 | `gp-0x6806` | `!= 0` | **the LKAS gate — unchanged from V67** |
| 5 | **`gp-0x67df`** | **`!= 0`** | detector FSM has **left neutral** ⇒ `\|gp-0x6c2c\|` crossed ±12800 — **no reversal required** |
| 4 | **`gp-0x671a`** | **`>= 1`** | …**and then reversed** at least once |
| 3 | — | const 1 | **build fingerprint** (V67 clear by construction) |

★★★ **THIS IS THE KIT'S ONLY ABOVE-50-Hz-CAPABLE INSTRUMENT.** CAN is Nyquist 50.00 and the IMU 50.51;
`gp-0x671a`/`gp-0x67df` integrate **1 kHz** information and both hold ≥50 ms, so the **existing** 100 Hz
hook reads them. **No new cave, no code on the 1 kHz path, no new RAM audit** — the same risk class as
every flight since V55.
★ **Why `>= 1` and not `>= 5`:** V67 measured `gp-0x671a >= 5` at **0.000% over 186,321 frames on two
routes**. *"Never reached 5"* is not *"never incremented"* — and `gp-0x671a` **passes through 1,2,3,4**
(⭐ verified in Ghidra at `0x429DA-0x429F2`). The information is at the **bottom** of the ladder, so this
extends **downward**: `gp-0x67df` fires on events too brief or too one-sided to produce a reversal.
★ **`bit5` set with `bit4` clear is the new information this build buys.** ⚠ `bit4 ⇒ bit5` is an
**expectation, not an encoding guarantee** — the cells are sampled on one tick but cleared by different
rules, so `bit4 && !bit5` can occur at a clear boundary. The decoder **reports its rate** rather than
asserting it away.
⚠ **Both bits give NEITHER amplitude NOR frequency** — detectors, not spectrometers. They deliver
above-50-Hz *information*, not an above-50-Hz *waveform*.
🛑 **Latch semantics — two cases, do not collapse them.** Below **~10 km/h** (`gp-0x6a5e` < `0xC62DE` =
640, at 64 counts/km/h) the CEIL latch **never releases** and duty saturates; at road speed it clears
**5.0 s** (`0xC6270` = 5000 ticks) after the last reversal. Sub-CEIL counts clear on the **50-tick dwell**
(`0xC64DD`) ⇒ ~50 ms ⇒ ~5 frames at 100 Hz, so **brief events are under-counted**. Duty is a **hold-time**
statistic, not an event rate.
⚠ **Encoding trap, recorded because it nearly bit:** the two rungs sit on **opposite displacement
parities** — `gp-0x67df` disp16 `0x9821` **ODD** (opcode `0x3D`, hw1 `a437`), `gp-0x671a` disp16 `0x98E6`
**EVEN** (opcode `0x3C`, hw1 `8437`). An encoder or scan assuming one parity silently addresses the
**neighbouring cell** with every other field perfect. ✅ Both emitted words are **flown, not derived**:
`a4372198` is byte-identical to V64's cave word at `0xC4B4C` (route 35), `8437e798` to V67's at `0xC4B50`
(routes 47/4a). ⚠ Neither has a byte-identical instance in **stock** — every real reader targets a
different destination register; what matches in stock is **hw2**, the displacement including its parity bit.

**Verification, all green:** CAL block `[0xC6000,0xC6FFC)` **0 differing bytes** + CAL CRC trailer
unchanged ⇒ **GATE 2 UN-ENGAGED** · **GATE 1 vacuous** (cave stores = 1, the CAN payload byte; both rungs
`ld.bu` only) · **49/49 bootloader + 50/50 full CRC** on image and readback · RWD round-trips
byte-identical across `[0x13000,0x100000)` · **cave re-decoded from the readback**, 19 instructions ·
`verify_v68_image.py` **35/35** · `diff_build_vs_stock.py` v68/v67 exit 0, `--self-test` exit 1.

★ **`gp-0x67ac` was CONSIDERED AND REJECTED — it is provably 0, so there is nothing to measure.** The
per-slot role table `tp+0x5124` = `0xC4124` reads **`[0,0,5,0,5,5,0,0,0,5,0]`** (⭐ orchestrator-verified
from the image bytes, and independently by the builder); `gp-0x617c[slot]` is set to 1 only for roles
**6 or 7**, so the OR-latch never fires ⇒ `gp-0x67ac` ≡ 0 ⇒ **the r24/r26 lanes CANNOT silently drop out,
so the highway null was NOT reading a disconnected lane.** That doubt is retired **analytically**, which
is better than measuring it. 🛑 This rests on **calibration bytes, not a structural guarantee** — the
build now **re-reads the table every time and STOPS** if any slot ever carries a 6 or 7, and a second
assert forbids `gp-0x67ac` from re-entering `CELLS`, citing that probing a proven zero is the error V68's
**original** bit4 made (`gp-0x6ac0 >= 400`, pre-registered as a flat zero, measured **0.000%** over
186,321 frames — a wasted rung, now reclaimed).
⚠ **OPEN residuals:** `gp-0x61a0`'s writer (search the **callers** of `FUN_00026c80`, not the function)
and `gp-0x61e8`'s identity — neither affects the verdict.

⇒ ★★★ **RECOMMENDED NEXT FLASH: V68, then DRIVE HIGHWAY WITH LKAS OFF.** V67's control path is
untouched, so **grind #1 and the creep grind #2 keep their measured fixes**; V68 buys the one measurement
nothing else in this kit can make. Decoder `rlog-tools/decode_v68_probe.py`.

---

## Previously on the car — **V65** (flashed, driven routes `3a--4e55c1e0f4` and `3b--a4a7f4dbf1` 2026-08-01)

**V65 = V62's control-path edits byte-identical + the 4-level saturation ladder on `gp-0x6b94`.** The
operator drove two routes on it: `3a` (short — parking lot, then **grind #2 demonstrated with LKAS ON**)
and `3b` (longer — parking lot, **grind #2 demonstrated with LKAS OFF**, then unrelated highway lateral
tuning). **Grind #1 stays fixed on V65** (18–22 Hz 0.555 [0.467, 0.685] vs Kd=1×, replicating V62), and
**grind #2 is confirmed and characterised** — see THE HEADLINE at the top of this file.
⇒ ★★★ **RECOMMENDED NEXT FLASH: V66** (see "Built and UNFLASHED"). It is what the operator asked for —
a stable long-drive build with stock base assist — and it is simultaneously the confirmatory revert and
the pre-flight probe for V67's gate.

---

## Previously on the car — **V62** (flashed 2026-07-31, driven route `37--6231e33f3d`)

**See THE HEADLINE at the top of this file for the full V62 result** — it is the current state and is not
repeated here. Summary: **the 20.9 Hz grinding is FIXED (8–42×)**, the route is flight-clean
(`ST==4` 0/86,278, zero-EME streak now >229,278 frames), **no regression is established**, and the
recommended next action is **another V62 drive, not a build**. V62 carries **V59's probe unchanged** —
🛑 `0x14A` byte4 = `0x87` therefore means *"boost index ≥ 2048"* (the **deepest** thermometer reading),
**not** V64's *"detector unarmed"*. Same byte, opposite meaning; it is 9.24% of route 37.

---

## Previously on the car — **V64**

## 🛑🛑 V64 FLASHED AND DRIVEN 2026-07-31 (route `35--77808fe7ce`) → **GRINDING UNFIXED, AND THE PROBE DIAGNOSED THE NULL**

Operator: *"I drove disengaged then engaged after. The vibration/grinding at low speeds is not fixed."*

**The probe answered its question and the answer was not the one the build was hoping for.**
`0x14A` byte4 = **constant `0x87`, zero variance across 14,980 frames / 149.8 s**:

| bit | meaning | frames set |
|---|---|---|
| 7 | liveness | **14,980 / 14,980** — the cave ran, every tick |
| 6 | `gp-0x671a >= 5` — **V63/V64's raised arm selected** | **0** |
| 5 | `gp-0x671a != 0` — counter incremented at all | **0** |
| 4 | `gp-0x67df != 0` — FSM left neutral | **0** |
| 3 | `gp-0x671d != 0` — r24 override | **0** |

⇒ `|gp-0x6c2c|` **never crossed `T` = `0xC620A` = 12800**, the reversal counter never incremented once,
and **V64's two cal edits were never in force.** ⇒ **A null on the GATE, not on the damping hypothesis.**
🛑 **Do not record V64 as evidence against raising the rate lane.** It is not.

**Confirmed four ways:** raw byte histogram · `rlog-tools/decode_v64_detector.py` (run by the
orchestrator) · an independent raw-CAN rederivation · **V59's probe ruled out** (its bit5 was set
essentially always; here 0/14,981, and other routes show byte4 genuinely varying `0xBF/0x8F/0x9F/0x87`).

**Spectra confirm it independently — the car behaved exactly like V59:**

| build | n runs | peak | prominence | abs power |
|---|---|---|---|---|
| V59 route `2c` | 9 | 21.18 Hz | 227× | 5.26e8 |
| V61 route `31` | 3 | **18.25 Hz** | 486× | **4.15e9** |
| **V64 route `35`** | 2 | **21.30 Hz** | 149× | 4.31e8 |

Best-populated speed bin (2–3 m/s): **V59 20.98 Hz / env99 1811 vs V64 20.99 Hz / env99 1804** — three
significant figures on both. V61's manual/reverse spread is **gone**. FLIGHT-CLEAN: `ST==4` **0**, all six
watched events 0, `0x14A`/`0x18F` at 100.03 Hz. Route is 100% creep (vEgo max 4.58 m/s), 1,958 reverse
frames, log starts 43 s **before** first engagement.

### ✅ The build was aimed CORRECTLY — the V63 polarity dispute is closed
`0x3AA7C cmp r14,r12 / bc` sets **`r2 = 1` iff `gp-0x671a >= CEIL`**, and both `ld.hu 0x743e[tp]`
@`0x3AB68` and `ld.hu 0x7440[tp]` @`0x3AC12` are taken iff `r2 != 0`. ⚠ The golden model's
`selected_state_value` is **`r22`** (cals `0xC6138`=1 / `0xC6136`=0), a **different register** from the arm
selector `r2` — both model readings were right, describing different variables. The "dispute" dissolves.
⚠ **bit3 = 0% ⇒ r24 WAS covered**; the `gp-0x671d` override was idle throughout.

### ✅ The detector genuinely RAN — the `FUN_00046ea6(5)` gate is closed
`FUN_000428d4`'s entire body is gated on `FUN_00046ea6(5) == 0` (bit 5 of `gp-0x18d0 | gp-0x18d4`), and if
that bit were set the cells would simply never be written — **indistinguishable from "T never crossed"**.
Closed by raw byte scan of **all 47 `jarl` sites** (Ghidra found 44 — the documented undercount; the
conclusion survived the *more* complete method): **bit 5 has exactly ONE caller image-wide, the detector
itself** (`0x428DA`). The only dynamic indices are cal bytes `0xB9A14-16` = **0, 2, 6**. The mask is
DTC-driven (`tp-0x72c4` table, stride 28, u32 at +8) and **self-clearing** — `gp-0x18d4` is rebuilt by
plain assignment on each active-fault sweep. ⚠ Residual: 6 of 47 sites set `r6` further back than a
5-halfword window; all sit in clusters whose other members resolve to 0 or 7.

### 🛑 AND EVEN IF THE GATE HAD OPENED, V64 DELIVERS LITTLE — byte-read defaults
At the hands-off-creep LERP axis (X = 0):

| lane | default arm (state<5) | osc arm (state>=5) stock | V64's arm | delivered vs default |
|---|---|---|---|---|
| r24 | **2305** (`0xD2AEC`) | 2048 | 4096 | ×1.78 |
| r26 | **3072** (`gain_A` rec0/rec1) | 1536 | 3072 | **×1.00 — a no-op** |

⇒ **Honda's oscillation arms are gain REDUCTIONS, not boosts.** V63/V64 largely *cancel Honda's own
de-escalation* rather than adding damping. V62's `sar` edit gives a clean **×2 on both lanes under every
arm and every mode**.

---

## Previously on the car — **V61**

## ★★★ V61 FLASHED AND DRIVEN 2026-07-31 → **WORSE. And that is the best result this kit has had.**

**The first SIGNED on-car outcome on any vibration lever.** Every prior build was a null or a fault.
V61 made the symptom *worse*, which is strictly more informative — it measures the **gradient**, and the
gradient says every previous attempt on this lane was pushing the wrong way.

**What V61 did:** zeroed the torsion-bar torque-RATE lane at **both** taps of its shared
`r1 = clamp(gp-0x4f62, ±5120)` (`0x3AB6C mul r1,r6,r0 → mul r0,r6,r0`; `0x3AC16 mov r1,r8 → mov r0,r8`).
Two single-bit reg1 changes, no cave, no calibration moved.

**Operator, authoritative:**
- **LKAS ON, forward** — grinding still present and **significantly worse**: higher amplitude, louder.
- **LKAS OFF, forward** — grinding **newly present** in manual driving when turning.
- **LKAS OFF, reverse** — grinding **definitely newly present** in manual driving.

### ⇒ The rate lane is the mode's DAMPER, not its amplifier
Sign verified by the orchestrator from image bytes, not relayed:
- `gp-0x6752` (polarity) is **one load @`0x3AB78` reused unmodified by both lanes**, and the *same byte*
  is read by `FUN_0003a382`'s resonance lane @`0x3A71A` — the aggregator's one genuinely
  torque-**proportional** P-term. ⇒ **polarity CANCELS**; its value is not needed to answer the question.
- The combine chain `0x3ACC8`–`0x3ACDA` is **ten instructions, every lane entering with `add`**, each
  add's `reg1` threading the previous add's `reg2`. **Not one `sub`.**
- ⇒ `r24, r26 = +Kd·d(T_bar)/dt` **in phase with assist** — `Kp·x + Kd·dx/dt`, a lead compensator.

For the hands-off mode (steering-wheel inertia on the torsion bar), with motor torque on the column only:
```
phi'' + (Kd·k/J_c)·phi' + k·(1/J_w + (1+K)/J_c)·phi = T_road/J_c
```
The `phi'` coefficient is **`Kd·k/J_c > 0` — positive damping, LINEAR in Kd. At `Kd = 0` the mode has no
damping term at all.** That is V61, and that is what the car did — including in **manual** driving, where
base assist is the only loop running, and worst in **reverse**.

🛑 **A derivative term is DC-neutral** (zero at constant torque), so V61 cannot have "removed assist" — it
changed **only** dynamics. That is what makes this a clean signed measurement rather than a confound.

🛑 **This falsifies the golden model's framing.** `eps_lkas_chain_model.py:1792` called r26
*"excitation-to-amplifier: faster slew → bigger derivative → bigger r26 → more motor torque → repeat"* and
recommended the r26 kill. Both passages are **struck and corrected in place**. ⇒ **V39 (r24), V42 (r26)
and V61 (both) all tested this lane DOWNWARD.** Their results stand; they bracket the **wrong side**.

★ **Why this lane and not the dampers already tried:** `FUN_0003aa2c` is **task 1, 1000 Hz** ⇒ ~3.8° of
ZOH lag at 20.9 Hz. Boost/damping are **task 5, 100 Hz** ⇒ **37.6–75.2°** — the structural reason V44 and
V47 were null. **The rate lane is the only damping mechanism in the chain fast enough to act on this mode.**

### ✅ The rlog CONFIRMS all three of the operator's observations — and the mode MOVED

Route `00000031--0441e00d2b`, 4 segments, **22,052 frames / 222 s**, parking lot (v max 1.5–5.4 m/s),
segs 0/3 manual, segs 1/2 engaged (latActive 47.2% / 18.1%). **FLIGHT-CLEAN:** `STEER_STATUS` = 0 in
22,042/22,052, `ST==3` in 10 frames, **`ST==4`: 0** (the clean streak extends past 143,000 frames).
Zero `steerUnavailable` / `steerTempUnavailable` / `canError` / `immediateDisable` / `steerSaturated`;
one `controlsMismatch`. **2,851 frames ≈ 28 s of reverse** — a real analysable population.

🛑🛑 **THE MODE MOVED DOWN 3 Hz AND GOT 7.9× LOUDER.** Engaged creep, v ≤ 5.35 m/s, *identical method,
speed-matched, same channel*, V59's route `2c` as the control (`analyze_r31_manual_vs_engaged.py`):

| build | n runs | peak | prominence | abs power |
|---|---|---|---|---|
| **V59** route `2c` | 9 | **21.18 Hz** | 227× | 5.26e8 |
| **V61** route `31` | 3 | **18.25 Hz** | 486× | **4.15e9** |

⇒ **−2.93 Hz and ×7.9 power.** ★★ **The frequency shift is the decisive observable, and it is
structural: a pure GAIN change cannot move a resonance frequency — a PHASE change can.** Removing a lead
compensator lowers the frequency at which the loop phase reaches −180°, so the limit cycle drops. Both
observables agree, and the direction was predicted *before* the data was looked at.

**The three conditions, route 31, ordered exactly as the operator reported them:**

| condition | n | peak | prominence | abs power |
|---|---|---|---|---|
| **ENGAGED** creep | 3 | 18.25 Hz | 486× | **4.15e9** |
| **MANUAL reverse** | 2 | **17.82 Hz** | **1910×** | 5.78e8 |
| **MANUAL forward** | 5 | 18.54 Hz | **13.1×** | 3.82e6 |

⇒ **Manual reverse carries 151× the power of manual forward, at the same frequency as the engaged line.**
That is the *same mode*, unmasked by the loss of damping — not a new one.

🛑 **REFINEMENT — "manual forward is a floor" is WRONG, and the error is instructive.** The 13.1× above
is an **un-gated average** over all manual-forward driving, so it is diluted by ordinary quiet cruising.
Gated on **sustained effort ≥ 1000** it is **146×** (n=2 windows, f0 18.40 Hz) — the phenomenon *is*
present in manual forward, but **only while the driver is actually loading the wheel**, which is exactly
what the operator said (*"in some scenarios"*). A second analyst reached the same place from the other
side: the loudest manual windows are at **|v| = 0.00–0.6 m/s with the wheel cranked** (effort 2200–3300),
and a `|v| ≥ 0.3 m/s` "moving" gate **drops them entirely**, taking that arm from *"median prominence
5.3×, mostly floor"* to *"median 317×, envelope p99 median 2495"*, f0 **17.08 Hz, sd 0.76, n=7**.
⇒ **Two different gates each hid the same population.** Manual/reverse sits at **17.0–17.8 Hz**, about
0.5–1.3 Hz *below* the engaged 18.3 Hz — same mode family, frequency shifting with loading.
⇒ ★ **Adopt a near-stationary, high-effort manual arm as a standing convention.** That is where manual
EPS instability lives, and both a speed gate and a missing effort gate erase it.

★ **The ratchet stayed LKAS-gated while the grinding did not.** Engaged: 10 of 14 windows reach 10×
prominence at 6.56 Hz. Manual: **0 of 28**. Reverse: **0 of 10**. ⇒ under V61 the two symptoms
**separated further** — the grinding escaped into base assist, the ratchet did not. That is independent
support for them being different phenomena, and it is also the third exclusion of the
ratchet-2nd-harmonic reading (a harmonic cannot live where its fundamental fails a presence test; and
2 × 6.56 = 13.1 Hz, not 17.8).

⚠ **Caveats, stated:** n is small (3 engaged / 2 reverse runs) and this is one route against one control
route. The effect sizes (7.9×, 151×, −2.93 Hz) are far larger than that weakness, but a repeat on V62 is
what confirms them.

⚠ **A methodology trap caught in-flight and worth recording:** the first pass pre-restricted the search to
the strict 18–26 Hz band and the argmax **pinned to the band edge at 18.04 Hz with sd 0.00** — a
truncation artifact, because the mode had moved *below* the band. **The strict band is for
presence-testing a mode whose frequency you already know, not for locating one that has shifted.** Locate
over 12–30 Hz, then interpret. (The ratchet-2nd-harmonic trap is separately excluded here: in manual
reverse the 6–10 Hz fundamental is only 9.6× while the 17.8 Hz line is ~1900× — a "harmonic" 200× stronger
than its own fundamental is not a harmonic.)

---

## 🛑 V60 FLASHED AND DRIVEN 2026-07-31 → **NULL. The parametric pump is CLOSED.**

Operator: *"I drove on the V60 RWD. It did not fix the vibration issue."* **No rlogs** — V60 carries
V59's probe unchanged, so there was no new telemetry to upload.

**This null is a result, not a wasted drive.** V60 was built as a **discriminator** and the record
predicted the outcome: *"Expect it to be NULL… a null closes the parametric mechanism and leaves the
loop standing."* Pump causality was not settleable observationally (the index is `|x|` of a bar-derived
signal, so 2f coupling is arithmetically forced) and `eps_crit = 2/Q` needed a passive Q that V59 could
not measure. Only an intervention could separate drive from echo. It did.
⇒ **V58/V59/V60's whole arc closes. The 42.19 Hz index modulation is real, engagement-gated, and is NOT
the driver of the grinding.**

★ **Consequence — `0xC63BA` is pre-falsified by the same null and must NOT be proposed as a fix.** It
looked ideal (cal-only, 512 = 2-stage EMA α = 0.5 ≈ −0.30 dB at 21 Hz, exactly 2 readers at `0x3B7BA`/
`0x3B7D4`, never edited, explicitly reserved by `build_v59_tva.py:444` as *"a V60 candidate"*). But a
byte scan of its consumers closes it: readers of `gp-0x6b9a` (8) and `gp-0x6ba6` (7) are confined to
`FUN_00034350` (damping), `FUN_00034a72` (boost), their producer, and V59's probe cave — so the index
drives **only** the boost/damping amplitude LERPs, i.e. the mechanism V60 just falsified. Proposing it
would repeat the V44/FactorC pattern exactly.

⚠ **Two more lanes removed from the search, byte-verified:** `FUN_00036c12` (`gp-0x6b26`) and
`FUN_00036388` (`gp-0x6b62`, the return-centre lane that was the operator's own hypothesis) read **no
torque signal at all** — speed- and motor-rate-keyed only.

**V58** = V57's calibration + the angle-rate/boost-lane probe in the cave. Flashed and driven 2026-07-30,
route `2b` (normal commute, 14 segments, ~14 min, 83,959 frames, creep → highway → parking).

```
0xC646C  shared sensor scale = 891 (stock)     <- was 3564 on V38..V56
0xC6CD0  private LKAS forward gain = 3564      <- V57's new cell
0xC62EA  low-speed lockout = 0                 <- V53, unchanged
0xC64DE  re-engage ramp = 27                   <- V18, carried forward correctly
_v58_plain_image.bin  SHA 431117459a42dc2e7906446261c7175bf2d0cc35b88290f2fdeb9b779d654c48
V58 .rwd              SHA 7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7
```

**V58 is FLIGHT-CLEAN.** `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/
`immediateDisable`: **0 across all 14 segments** (raw `onroadEvents` scan, verified twice). The only
flags are `commIssue`×2 + `selfdrivedLagging`×1, all at seg 0 t≈8.5 s **in `wrongGear` before the drive
started** — a boot transient, unlike route 28's real mid-drive soft-disable. `STEER_STATUS == 0` in
**83,959/83,959** frames; **`ST==4`: 0**, extending V57's 0/37,922 to 121,881 combined clean frames.
Probe low bits `& 0x07 == 0b111`, zero exceptions. `0x14A`/`0x18F` at 100.00 Hz in every driving segment.

**V58's on-car result — see the handoff for the full numbers:**
- ★★ **The collinearity confound is BROKEN.** Seg 13 gives 60 s of *moving but disengaged* at
  0.5–4.8 m/s. Speed-matched grinding: **13.4×** [95% 3.9–19.8], **16.9×** speed+effort-matched, and
  **184×** on time-occupancy at matched creep. Better than any ratio — **the resonance is ABSENT
  disengaged**: prominence median 122.7× vs 3.6×, with the disengaged "peak" wandering 15–29.9 Hz
  (sd 2.49 Hz) i.e. the argmax of a floor. Confounds run *against* the engaged arm (disengaged has
  |ang| 167° vs 9°, effort 1638 vs 205). ⇒ **the grinding requires applied LKAS torque. Settled.**
- ✅ **bit5 = 0 in all 35,964 frames ⇒ the ceiling `0xD20C0` is ELIMINATED.** The lane never pins, so
  `K1` @`0xD200C` = 43 keeps its headroom.
- 🛑 **bit6 VOID BY CONSTRUCTION.** `gp-0x6bbe` crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s; it is
  DC-dominated. **The damping sign is STILL OPEN.** ⚠ Pooling runs to force an answer manufactures a
  splice artifact (bit6 has 5/0/0/1 transitions *within* the four engaged runs, so a concatenated
  "coherence 0.5 at 25 Hz" is step discontinuities at the joins). **A sign comparator is a phase probe
  only for a signal that crosses zero at the frequency of interest.**
- ★★ **bit4 FIRED and is the lead.** `sign(gp-0x6b9a)` at 20.93 Hz, per-run coherence
  0.649/0.970/0.769/0.881, own-spectrum peak 10.8× median, `corr(envelope, toggle rate) = +0.834`.
  At matched creep: **13.69 toggles/s engaged vs 0.61 disengaged**, 20.93 Hz line present in one arm and
  absent in the other, duty cycle barely moving ⇒ it *oscillates*, it does not merely sit elsewhere.

🛑 **Hands-off could not be conditioned on anywhere on this route** — zero fully-hands-off windows in
either arm in any qualifying speed bin. Everything above is "any hands", matched on effort instead.

## 🛑🛑 CORRECTION — `gp-0x671a` IS A ONE-WAY LATCH, so V63/V64's decoupling is NARROWER than first stated

An earlier pass this session told the operator V63 had **"zero manual-feel cost by construction"**. **That was too strong and is withdrawn.** `FUN_000428d4`'s output stage (`0x429A0`–`0x42A12`, orchestrator-verified, cals byte-read) holds the counter:
```
0x429A8  cmp r15,r12 / bh   ; cal 0xC62DE = 640 > voted VEHICLE SPEED gp-0x6a5e -> RELOAD hold timer
0x429AC  cmp r0,r14  / bne  ; revcount != 0                                     -> RELOAD hold timer
0x429CA  reload = cal 0xC6270 = 5000 ticks = 5.0 s @ 1 kHz
0x429EA  once held >= CEIL, the output is RE-PINNED TO CEIL every tick
```
🛑🛑 **LABEL CORRECTED 2026-08-03 — `gp-0x6a5e` is voted VEHICLE SPEED, not driver torque.** Settled
2026-07-29 by the voter `FUN_00041eec` (`memory/reference-accord-gp6a5e-is-speed-reclassifies-v44-v47.md`);
that is the same reclassification that invalidated V44/V47's rationale. The line above said "DRIVER
TORQUE" and was wrong. 🛑 **The label is wrong; the CONSEQUENCE is under verification** — a tracer is
re-reading the disassembly independently. Nothing below is a settled replacement.

> ⚠ **SUPERSEDED, left visible rather than overwritten (the old text, verbatim):**
> *"The only way down is **5000 consecutive ticks with driver torque ≥ 640 AND no reversals** — and
> driver torque dips below 640 on every direction change, so the timer reloads constantly.
> ⇒ **Accurate claim: a drive that never oscillates never sees the raised gain** (a real scope
> reduction against V62's always-on doubling) — **but once a single 5-reversal burst occurs, the
> raised gain latches on and carries into subsequent manual steering.** V63/V64 is "V62, but only
> after an oscillation has happened"."*
>
> **Why it does not survive the relabel:** the "dips below 640 on every direction change" step was
> load-bearing and was a claim about *driver torque*. **Speed does not dip at every direction change**,
> and 640 counts is **~10 km/h** at the kit's 64.0625 counts/km-h. So the un-latch condition reads as
> *5 s above ~10 km/h with no reversals* — a condition ordinary driving meets constantly, which would
> make the latch **far less sticky**, not more. ⇒ the stickiness conclusion, and the "carries into
> subsequent manual steering" scope argument that rests on it, are **both open**. Do not lean on
> either reading until the tracer's result lands.
✅ **And the latch is PROTECTIVE.** A gain switching per-tick with the reversals would modulate **at the mode frequency** — a parametric pump, the exact failure mode V58/V59/V60 spent three builds chasing. Honda's hold prevents that; a per-tick-gated damper would be actively dangerous.
⚠ Cell correction: the per-tick zeroing at `0x42906` is on **`gp-0x357c`** (raw count), not `gp-0x671a`.

## Built and UNFLASHED

🛑 **THE `status` COLUMN BELOW IS STALE FOR V67 AND EARLIER — READ IT AS A BUILD NOTE, NOT A FLASH
STATUS.** Every row that says "BUILT, UNFLASHED" for V62/V67 was written before those builds flew.
**`docs/BUILD-LINEAGE.md` Part 4 and "On the car right now" above are the authorities on what has been
flashed.** Flash order since: **V62 → V64 → V65 → V67 → V68 → V69 → V70 (on the car now, 2026-08-04).**
⏳ **V71 is BUILT and UNFLASHED** — V70 carrier + `0x454FE` `ba`→`b5` + `0x3AB76`/`0x3AC20` `aa`→`a9` +
the mode-10 surface reverted to stock + a **gain-in-force** probe. **SHAs in the V71 build report.**

| build | what | status |
|---|---|---|
| ★★★ **V69** | the gate REVERTED + Honda's own low-speed rate-gain surface scaled **×4** + the RATCHET probe | 🛑 **FLASHED 2026-08-04, driven route `4f--61171e660d` → grind #1 is BACK at creep and the dose–response is NON-MONOTONE.** See THE HEADLINE. Flight-clean; the dose was fully delivered; all three probe rungs failed. **Do not re-flash for grind #1.** Image `48bb4192…`, RWD `e62fcbba…` |
| ★★★★ **V67** | **V66 + the grind #1 fix, GATED ON LKAS** — `0x3AA96` `c5`→`fb` + `0xC6446` 512→5244, both `sar` sites STOCK | ✅ **BUILT 2026-08-01, UNFLASHED. ★★★★ THE OPERATOR'S CHOICE FOR THE LONG DRIVE.** ★★★★ **THE FIX, AND THE OPERATOR'S CHOICE FOR THE LONG DRIVE.** V66's calibration and reverts, plus the grind #1 fix made conditional on LKAS. **LKAS off is byte-for-byte STOCK base steering; LKAS on gets 2.00× at grind #1's operating point** (creep 7.2 km/h, 128 deg/s, LERP 2622 ⇒ arm 5244). ✅✅ **THE GATE IS VALIDATED ON-CAR BEFORE THE FLASH** — V57's own probe put `(gp-0x6806 == 0)` on `0x14A` byte4 bit6 and flew routes `28`/`29` in July, and nobody had correlated it: **99.90% / 99.94% agreement with `carControl.latActive`** over **37,914 frames** at two very different duty cycles (21.73% / 49.88%), with **0.0505 / 0.0300 transitions per second**. ⇒ `gp-0x6806 != 0` **is** "LKAS is applying"; it does **NOT** drop out during steady engaged holding (the one ambiguity static analysis could not close — it is a ramp-FSM phase flag whose "settled" phases 5/6/7 could not be ruled out); and it toggles **three orders of magnitude** below the 21/45 Hz modes, so the parametric-pump criterion passes with enormous margin. Reproduce with `analysis-2020accord/validate_gp6806_gate.py`. ⭐ **Orchestrator-verified independently from the built image.** **15 bytes off V66**, restricted to `[0x13000,0x100000)`: `0x3AA96` (1), cave `0xC4B46`/`0xC4B52`/`0xC4B54`/`0xC4B56` (4), MAIN CRC (4), `0xC6446` (2), CAL CRC (4). The repoint leaves **hw1 untouched** and the result `84 7f fb 97` differs from the real `ld.bu -0x6806[gp],r12` = `84 67 fb 97` @`0x02A1B6` **only in the reg2 field**. `0xC6444` (r26's arm on the same gate) stays **stock 512** — ~~r26 is inert~~ 🛑 **CORRECTED 2026-08-04: that justification no longer holds on its own.** The GATE leg of the inertness claim is reversed and the MAGNITUDE leg is only BELIEF (THE HEADLINE §7). **If r26 is live, leaving `0xC6444` at 512 while the gate is repointed is a 6.00× CUT on r26 whenever LKAS applies** (its live LERP value at creep is 3072) ⇒ V67/V68 would be *"r24 up 2×, r26 down 6×"*. ⚠ The dose–response argues `a` is small, i.e. that the cut is immaterial — **but that is an inference, not a measurement.** V70's `gp-0x6adc`/`gp-0x6ada` sign pair settles it. Both `sar` sites confirmed **stock `0xa`**, `0x3AB70` untouched, `0xD2000` block and **all four** mode-10 `gain_B` records byte-identical to V66. 50/50 CRC; x31 checksum PASS; **the RWD decodes exactly back to the image**. GATE 1 **vacuous** — the repoint is a read-only load displacement claiming no RAM, and the cave's sole store is the existing CAN-330 payload byte with bits 2:0 preserved. GATE 2 is **measured, not argued**: the lane is a **derivative ⇒ DC-neutral**, so a gain step at engagement is not a torque step, and the gate's toggle rate is the table above. Arithmetic `5120 × 5244 = 26.8 M` = **1.25% of INT32_MAX**; the lane saturates at \|dtorque\| ≥ 1599 against a measured 123–839. **Probe** (`0x14A` byte4): **bit7** liveness · **bit6** `gp-0x6806 != 0` (**the gate** — low duty while engaged ⇒ wrong cell and V67 is inert) · **bit5** `gp-0x671d != 0` (**the masking risk** — it OUTRANKS the arm and pins the gain to `0xC6442` = 1024, *below* stock, so if it fires V67 is worse than V66) · **bit4** `gp-0x671a >= 5` (the third arm). Cave re-decoded from the built image; the odd displacement `-0x671d` (bit 0 in **hw1 bit 5**) and the even `-0x671a` / `-0x6806` all encoded correctly. ⚠ bit4 **hardcodes 5** rather than reading cal `0xC64FA`; the cal is 5 and V67 does not move it, but a future change to `0xC64FA` would silently desync the probe from the firmware. 🛑 **GRIND #2 SURVIVES UNDER LKAS**, at **2.21×** — slightly above V62's 2.00×, because a scalar arm does not follow the LERP's own rolloff. That is the stated cost of an LKAS gate: measured gating is **98.7%** engaged for grind #1 but **84.3%** for grind #2 against a **54.7%** base rate. `0xC6446` is one halfword and is the knob for that trade. 🛑 **Do not read a V67 null without decoding the probe first** — that is the V64 lesson. Decoder `rlog-tools/decode_v67_gate.py`. Image SHA `5e01bcc4b34a52831fd524cb9af765a01a8dfa3e2c4782d81b3efcb6c94f8c96`; RWD SHA `33457613ea8635686baf94833e75688fe200c616d76cb4b38b3152d4a47a1caf` |
| ★★★★ **V66** | **V65 with BOTH `sar` immediates reverted to stock + a 3-bit GATE PROBE** — the operator's requested stable long-drive build, and the confirmatory revert | ✅ **BUILT 2026-08-01, UNFLASHED. ★ THE RECOMMENDED NEXT FLASH.** Restores **exactly stock** base assist (grind #1 returns as V38 has it; grind #2's cause is removed), carries V57's `0xC646C` decoupling + `0xC6CD0` = 3564 + `0xC62EA` = 0 + `0xC64DE` = 27 unchanged. Probe on `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6806 != 0` · **bit5** `gp-0x67f5 != 0` (**its toggle rate is V67's kill criterion**) · **bit4** `gp-0x67fe != 0` (**gate candidate C — one bit settles whether it is an LKAS flag or base assist**). **61 bytes off V65** (2 code + 52 cave + MAIN CRC); ⭐ **CAL block byte-identical to V65**, `0xD2000` block identical, all four mode-10 `gain_B` records unchanged = machine proof no calibration moved; `0x3AB70` still `sar 0xa`; **`gp-0x683c`'s load at `0x3AA94` UNCHANGED**. Same base/hook/68-byte extent as six clean flights; **62/68 used**. GATE 1 vacuous. 50/50 CRC; x31 PASS; RWD decodes exactly back to the image; ⭐ orchestrator-verified from the built image with the cave re-decoded from the bytes. 🛑 **Only three probe bits fit**, so `gp-0x671d` and `gp-0x67fe` are unmeasured. **Route:** ordinary long driving plus deliberate parking-lot creep, **and specifically reproduce grind #2** — creep with heavy manual steering, |angle| ≥ 100°, both engaged and disengaged. **Log from before the first engagement.** Decoder `rlog-tools/decode_v66_gateprobe.py`. Image SHA `0d4a0a5361e8ba91b1a24ad3298dd617ad541903070b02a58b9ae6df6709f246`; RWD SHA `41a4476ae9fb29fd2afd1b41238bf19b409b256abb8adfa3a8fb7b5569548fa9` |
| ~~**V64**~~ | V63's two cal edits + the probe repointed at the oscillation detector | 🛑 **FLASHED 2026-07-31 → GRINDING UNFIXED, DETECTOR NEVER ARMED. Do not re-flash for the damping.** See "On the car right now" above. The probe did its job — it converted an uninterpretable null into a diagnosed one. Original build note kept below for provenance. ✅ **BUILT 2026-07-31.** Operator's proposal, and it removes V63's fatal weakness: V63's probe still measured `gp-0x6ba6`, the parametric-pump index **V60 already falsified**, so a V63 null would have been uninterpretable. V64 keeps the cal edits byte-identical (**CAL block byte-identical to V63, machine-verified**) and repoints the cave: `0x14A` byte4 **bit7** liveness · **bit6** `gp-0x671a >= 5` (the arm is selected) · **bit5** `gp-0x671a != 0` · **bit4** `gp-0x67df != 0` (FSM left neutral ⇒ `\|gp-0x6c2c\|` crossed ±12800) · **bit3** `gp-0x671d != 0` (r24's override active). **Actionable in every failure mode:** bit6 never set + bit4 set ⇒ lower `CEIL` (`0xC64FA`); bit4 clear ⇒ lower `T` (`0xC620A`); bit6 live but no improvement ⇒ the rise was too small; bit3 set ⇒ also raise `0xC6442`. **60 bytes off V59** (50 cave + 2 cal + 8 CRC), **54 off V63 (cave + MAIN CRC only)**, 90 off V38. Same base `0xC4B34`, same hook `0x55C0E`, **same 68-byte extent** as V55/V57/V58/V59 — all four flown clean; **68/68 used, zero budget left.** GATE 1 vacuous (read-only; sole write is the existing CAN payload byte, bits 2:0 preserved). 50/50 CRC; RWD round-trips; cave re-decoded from the readback. ⭐ **Orchestrator-verified independently from the built image:** all three cave loads decode to `gp-0x671a`/`gp-0x67df`/`gp-0x671d` (V850 `ld.bu` carries displacement bit 0 in **hw1 bit 5**, not hw2 — a naive decode reports false mismatches), the `gp-0x671d` halfword is **byte-identical to the real firmware instance** @`0x3AB98`, and the only store is the CAN byte. Decoder `rlog-tools/decode_v64_detector.py` leads with **time-to-first-set** and **whether it ever clears** (see the latch note — occupancy saturates once set). 🛑 **Start the log BEFORE the first engagement**, or time-to-first-set is unmeasurable. Image SHA `e9dcd3b619cb35a4405861331a20807c4d0d2df074b6119a6690df728c68511e`; RWD SHA `7abbeba61ccc22852506e8747cedd12236210e93c23f8a13ad586e19914f0830` |
| ★★ **V63** | V59 + raise **only the OSCILLATION-DETECTED gain arms** of both rate lanes | ✅ **BUILT 2026-07-31, UNFLASHED — superseded by V64, which is the same cal edit plus instrumentation.** `0xC6440` 2048→4096 (r24) and `0xC643E` 1536→3072 (r26). **6 bytes off V59** (2 cal bytes + CAL CRC), 88 off V38. ⭐ **MAIN CRC UNCHANGED** = machine proof no code byte moved. V62's `sar` shifts and V61's tap kill both **asserted absent** ⇒ independent experiment, not layered. 50/50 CRC, RWD round-trips, re-verified from the built image. **Built in response to the operator's objection that V62 changes manual feel to fix an LKAS-specific symptom** — and the firmware turns out to already discriminate: both lanes' gain chains end in `assist_state gp-0x671a >= 5`, and `gp-0x671a` is a **HARD-REVERSAL COUNTER** (`FUN_000428d4`: neutral state resets it to 0 **every tick** and only exits if `\|gp-0x6c2c\| > 12800`; a reversal increments; 50 quiet ticks clear it). ⇒ it reads **0 during smooth steering** and `state>=5` means **an oscillation is happening**. Raising only those arms adds damping **only while oscillating**; both smooth-steering LERP defaults stay stock ⇒ **zero manual-feel cost by construction, and a smaller edit than V62.** ✅ **No new arithmetic risk: 3072 is already gain_A's own stock maximum**, so worst-case `stage1×gain` stays at 47% of INT32_MAX, unchanged. GATE 1 vacuous. 🛑 **Residual 1 — a NULL IS AMBIGUOUS:** whether `gp-0x6c2c` actually crosses ±12800 during the vibration is **unverified and load-bearing**; if it does not, V63 is inert. **Resolve with no probe and no cave: fly V63 first, and if null fly V62, which cannot miss.** 🛑 **Residual 2:** `gate_671d` outranks r24's arm and is live, so **expect r26 to carry this build**; r26's chain is clean (`gate_683c` dead). Image SHA `2f843bce8ff6fcab72cd3fafddcbdea926b40701e1425cabad03791f1a09019c`; RWD SHA `5e5f83d7cd9281000dcfa602a6e70b252037ad782728502d82e82d42c72b9abc` |
| ★★★ **V62** | V59 + **DOUBLE the torsion-bar RATE lane** — `sar 0xa` → `sar 0x9` on each lane's final shift | ✅ **BUILT 2026-07-31, UNFLASHED. ★★★ THE RECOMMENDED NEXT FLASH — promoted from fallback after V64's gate null.** It carries **no detector anywhere in its path**, so it is immune to the ambiguity that made V63/V64 inert. ⭐ **Re-verified from the built image 2026-07-31**: exactly 6 bytes vs V59 — `0x3AB76` `aa`→`a9`, `0x3AC20` `aa`→`a9`, MAIN CRC at `0xC4FFC`; `0x3AB70` correctly still `sar 0xa`; `0xC6440`/`0xC643E`/`0xC6442` confirmed stock. ✅ Lane clamps re-confirmed **±8192 each** (`0x3AB82`/`0x3AC42`), aggregate **±10240** ⇒ cannot produce an unbounded command. ⚠ **Pre-committed caveat:** r24 saturates once the input derivative exceeds `8192·1024/gain` — 3639 (71% of the ±5120 ceiling) at the stock 2305 default, **1820 (36%) under V62**; above that both clamp identically, so expect a **partial** improvement, not elimination. The benefit is that hitting the damping ceiling earlier in each cycle removes more energy per cycle from a limit cycle. **The matched inverse of V61.** `0x3AC20 42AA→42A9` (r24) and `0x3AB76 32AA→32A9` (r26). V61 took `Kd`→0 and the mode diverged; V62 takes `Kd`→2×, the same-sized step back. Stock sustains with **no ring-down at all** ⇒ `zeta_net ≈ 0`, so doubling should move it to `+zeta_lead`. **6 bytes off V59** (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38. ⭐ **CAL CRC unchanged** and ⭐ **`0xD2000`-block CRC unchanged** = machine proof no calibration moved and V60's falsified blend is absent. 50/50 CRC, RWD round-trips with every gate re-run on the readback; re-verified independently from the built image (taps back at `r1`, both shifts `sar 0x9`, `0x3AB70` still `sar 0xa`, exactly 2 code bytes). 🛑 **`sar` immediates chosen OVER the gain cals**, three traced reasons: the live gain arm is a **priority chain** that cannot be pinned statically (`gp-0x671a` is a bounded [0,5] *persistence ramp* that plausibly never saturates during a 21 Hz oscillation); **r24's default arm is MODE-INDEXED** via `gp+0x63fd` through four pointer arrays (`0xD2AEC`←`0xCC154` idx 10, `0xD6AEC`←`0xCC184` **idx 22** — ⚠ **a different MODE, not a redundancy twin; the "V27 desync" reading was wrong**); and `gp-0x683c` has **zero writers** ⇒ `0xC6446`/`0xC6444` are dead arms. A `sar` edit doubles the lane **under every arm and every mode**. 🛑 **`0x3AB76` not `0x3AB70`** — V850 `mul` discards the high word into `r0`, and doubling before the `×gain_A` multiply pushes the worst case to **94% of INT32_MAX** vs 47% (unchanged) after it. **Headroom is arm-dependent**: ~22× / ~11× / **~7.3× worst case**, so doubling keeps ≥3.6× margin. GATE 1 **vacuous** (no cave, no RAM, no new opcode). ⚠ **Residual:** `avg(gp-0x69a4)` magnitude is still unmeasured after three sessions — if r26 were already pinned at ±8192 doubling would deepen a saturation; bounded against by the fact that such a lane would dominate the ±10240 sum clamp and V61 would have been far more dramatic. r24 is immune. ⚠ Manual feel **will** change. Reversible by reflashing V59 or V61. Image SHA `80d9e1f721b741722a9d4b141a2d328fe8d999705765fedffab1ad23aa9264c7`; RWD SHA `1e0806a1eac69688e6d636fa02c5b1e864da40a65a4d3f8137d444d1ec5bff8e` |
| ~~V61~~ | V59 + **kill the torsion-bar RATE lane at BOTH taps of its shared value** | ★★★ **FLASHED 2026-07-31 → WORSE. Do not re-flash except as a deliberate revert.** The signed result that inverted the record — see the section above. Original build note kept below for provenance. **The one decisive subtractive test never performed.** r24 and r26 are **not independent** — both are gain-scalings of ONE value, `r1 = clamp(gp-0x4f62, ±5120)`, produced at `0x3AAAC-0x3AAC0` and tapped twice: `0x3AB6C mul r1,r6,r0` (r26) and `0x3AC16 mov r1,r8` (r24). **V39 killed only r24 — and only *conditionally*** (cave at `0x3AC78`, bypasses unless driver max torque < 320 AND \|LKAS\| ≥ 417); **V42 killed only r26** and says so outright (*"WHY r26 AND NOT r24: r24 was already zeroed by V39"*). Same sign, shared polarity load @`0x3AB78` ⇒ **killing either alone leaves the other transmitting, so each null is uninformative about the lane.** ⭐ **THE EDIT IS TWO SINGLE-BIT REGISTER-FIELD CHANGES** — `0x37E1→0x37E0` and `0x4001→0x4000`, both `reg1: r1→r0`, opcode and reg2 byte-identical (verified programmatically on the built image). **No cave** ⇒ GATE 1 vacuous, and the kit's only bricking class is avoided. r24's tail traced to zero: `mov 0x0,r6` @`0x3AC22` is the default and both deadzone arms skip. **5 bytes off V59** (2 code + 3 CRC), 88 off V38. ⭐ **CAL CRC unchanged** = machine proof no `0xC6xxx` cal moved; **`0xD2000`-block CRC unchanged** = machine proof V60's falsified blend is absent. Every r24/r26 gain cal (`0xC6440/42/46`, `0xC61F6`, `0xC6444`, `0xC643E`) and V42's `gain_A` Y rows asserted **STOCK**, so this is an independent lane test, not V39/V42 layered underneath. 50/50 CRC, RWD round-trips with every gate re-run on the readback. ⚠ **Expect a manual-feel change** — the rate lanes are a phase-lead term in **base** assist and this chain has no LKAS-only decoupling point. Reversible by reflashing V59. ⚠ V59's probe rides along but is **NOT a null control**: it reads `gp-0x6ba6`, upstream of the edit, so the edit cannot move it *directly* — but a quieter bar moves the index, making it a **secondary readout**. Image SHA `35da8600aa42584d0c5cf35bde8e9a751a0396e66f149f5fd18d07982498e23a`; RWD SHA `dd647870272aaa6342c425d25efb01a13eb540b1bd2c58fbbcbef132139f8a05` |
| ~~V60~~ | V59 + the boost-amplitude BLEND coefficient `0xD2006`: 102 → 43 | 🛑 **FLASHED 2026-07-31 → NULL on the vibration. Do not re-flash.** The discriminator fired and returned the predicted null ⇒ **the parametric pump is CLOSED**, and `0xC63BA` goes with it (the index drives only the boost/damping amplitude LERPs). Original build note kept below for provenance. **BUILT 2026-07-30.** **The intervention that settles whether the 42 Hz pump DRIVES the grinding or merely ECHOES it** — the only discriminator left, since causality is not settleable observationally and `eps_crit = 2/Q` needs a passive Q that V59 cannot measure. **5 bytes off V59**: one cal byte + the `[0xD2000,0xD2FFC)` block CRC. ⭐ **MAIN CRC and CAL CRC both UNCHANGED** = machine proof the cave/probe did not move and no `0xC6xxx` calibration moved. 91 bytes off V38. Q10 0.0996 → 0.0420; 42 Hz transmission ~0.37 → ~0.17; tau 10.0 → 23.8 ms @1 kHz. Predicted eps p99 **0.169 → 0.099**. 🛑 **The effect SATURATES** — the falling edge is instant regardless of the coefficient, so this lever buys ~1.7× and then flattens (cal 32 only reaches 0.086); 43 is the knee. **GATE 1 vacuous** (calibration halfword, no code, no RAM). **GATE 2 is the argument**: base-assist path, no LKAS-only decoupling point exists in this chain — but it is a pure *dynamics* change on a gain-**scheduling** variable, adds no gain, moves no static map, cannot change any steady-state value, and tau stays <50 ms worst case. Blast radius byte-verified: mode 10's cell is private (modes 11/12 have their own). **V59's probe is UNCHANGED and is the CONTROL** — it reads `gp-0x6ba6`, *upstream* of the blend, so the index distribution must return statistically identical (76.9/18.5/4.6/0.04). 50/50 CRC, RWD round-trips. Image SHA `6328cff064598cac8d9a7a4147626c8b55ddbad2e586ac3e1b8fca9c9459be5c`; RWD SHA `519aaab4908844d6a240d48f50d8a523b39353a3a4e3bffeb3de4bb4e1d19787` |
| **V59** | V58 + cave payload replaced by the **boost-index DEPTH probe** | ✅ **BUILT 2026-07-30, UNFLASHED.** `0x14A` byte4: bit7 liveness, bit6 = `gp-0x6ba6 < 0` (the `0xFFFF` fault sentinel), **bit5/4/3 = a THERMOMETER on `gp-0x6ba6` at 512 / 1024 / 2048** (sense is "index < T", which is what lets the whole cave run on the two pinned condition codes). **19 bytes off V58** (cave + MAIN CRC only; **CAL CRC unchanged** = machine proof no calibration moved), 86 off V38. Same base `0xC4B34`/hook `0x55C0E`/68-byte extent as V55/V57/V58, all flown clean. **No new encoder, no new condition code.** 50/50 CRC, RWD round-trip, cave re-disassembled from the built image; the build also asserts both LERPs still resolve at the same mode and `tp+0x7498/0x7499` are still 1. Decoder `rlog-tools/decode_v59_boostindex.py` (hard-stops above 1% non-monotonic rather than reporting on a surviving subset). RWD SHA `ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7`; image SHA `c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d` |
| **V55** | the pre-V56 revert target | ✅ built, driven, fault-free. SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| ~~V56~~ | the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED.** Do not re-flash |
| ~~V57~~ | the `0xC646C` decoupling + deadband probe | ✅ flashed, fault-free; its calibration is carried by V58 |

🛑 **Flash only on explicit operator instruction naming the file and the bus.** Kill openpilot/pandad first.

---

## 🛑 METHODOLOGY — three conventions that were producing wrong answers

These invalidate *reasoning* behind earlier conclusions. None changes a measured on-car outcome, but
every historical amplitude comparison needs rebuilding before it can be trusted.

1. **`carState.cruiseState.enabled` is LONGITUDINAL + LATERAL and is the WRONG engagement proxy.**
   It reads **0.00%** on V55 route `1c`, V56 route `24` seg 0, and V57 route `29` seg 1 — parking-lot
   routes where lateral was demonstrably applying. On route 28 it reads 84.0% while lateral applied 49.9%.
   **Use `carControl.latActive`, corroborated by CAN `0x18F` byte4 bit3 (`STEER_CONTROL_ACTIVE`).** The
   three agree to **99.85–99.94%**. Using cruiseState flipped V57's headline verdict from INERT to
   NOT INERT, and inflates V56's creep baseline **28×** by sweeping in hands-on parking manoeuvres at
   |ang| 89.6°.
2. **Hands-off must be SUSTAINED effort `|lowpass(tq, 3 Hz)| ≤ 200`, never raw `|tq| ≤ 200`.**
   The oscillation is ±1400 counts *on the torsion-bar channel itself*, so it trips the raw test by
   itself: 68.3% of frames scored "hands-on" have the driver doing nothing sustained. On genuinely quiet
   frames the raw test **keeps** 390 frames with oscillation rms 103.5 and **drops** 746 with rms 909.2 —
   **8.79× the amplitude.** It selects *against* the phenomenon. Switching recovers 2.5× more usable
   frames and turns subsets that had no contiguous run into computable numbers.
3. **Mean Welch power is the wrong statistic for a bursty limit cycle — use peak/p99 envelope.**
   V57/V55 grinding: median 0.419 but **p99 0.891, max 0.898**. The "halving" lived entirely in the
   median, which is dominated by quiet time between bursts. Operator called this before the data did.

✅ **A fourth problem, SOLVED 2026-07-30 by route `2b`:** engagement and motion used to be collinear —
no speed bin on any route had ≥3 windows in both arms, so the recorded ratios (877×, 786×, 14,750×,
27.7×) were moving-vs-stopped contrasts wearing an engagement label. **Route `2b` breaks it**: seg 13 is
60 s of *moving but disengaged* at 0.5–4.8 m/s against engaged creep at overlapping speeds, giving 3 of
9 speed bins with windows in both arms (18 v 18 windows, but only ~10 independent episodes per arm —
treat n as episodes, not windows). ⇒ **13.4× amplitude [95% 3.9–19.8], 16.9× speed+effort-matched.**
🛑 The old ratios stay retired; **do not resurrect 877×/786×/14,750×** — they were never engagement
contrasts. Quote the route-`2b` numbers, or absolute engaged powers.

⚠ **A fifth convention, learned the hard way this session: use a STRICT 18–26 Hz band plus a presence
test, never a wider search band.** A 15–30 Hz or 17–28 Hz argmax catches the ratchet's 2nd harmonic
(2×8.0–8.9 Hz = 16–17.8 Hz) at road speed and steps down to ~15 Hz, manufacturing a *negative* frequency
slope out of a mode switch. Two independent analysts produced two contradictory "frequency laws" this way
before the band was tightened.

⚠ **A sixth: prominence, not envelope amplitude, is what separates a mode from broadband.** The
disengaged arm's loudest 18–26 Hz moments are single-digit prominence at |ang| up to 295° — a driver
cranking a wheel. An envelope-ratio headline divides one broadband spike by another; the prominence
contrast (34× grinding vs 6.1× ratchet) and the presence/absence are the defensible statistics.

---

## Signal-identity corrections of record

- 🛑★★ **`gp-0x6c2c` — the oscillation detector's input — is a MOTOR-RATE DERIVATIVE, not torque and not
  a raw per-tick difference.** Produced in `FUN_00041464` @`0x4184E`; all cals byte-read LE:
  ```python
  K1 = 37     # cal 0xC643C, >>7        K2 = 22   # cal 0xC40DC, >>6
  x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
  if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # validity ceiling -> fault sentinel
  target = x * 1024
  step   = ((target - old) * K1) >> 7 ; old += step   # EMA #1 increment -- THE DIFFERENCE
  acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # x32, clamp +-16,384,000
  state += ((acc - state) * K2) >> 6                  # EMA #2
  gp_0x6c2c = state >> 9                              # range +-32,000; T = 40.0% of that
  ```
  ⇒ **an ACCELERATION** — differencing kills DC, so a sustained large steering input cannot drive it.
  Sibling `gp-0x6c2e` takes the same `acc` through a slower EMA (cal `0xC40DA` = 3, `>>7`).
  **Sizing:** a 21.3 Hz sinusoid needs `|gp-0x4f50|` ≈ **1683** counts @1 kHz / **1821** @100 Hz to trip
  `T` — inside that signal's own ±13000 validity ceiling, so **the detector is NOT structurally blind to
  the mode; the drive was ~1.7–2× short.** Independently reproduced in the frequency domain
  (`|1-H1|`=0.43041 × `|H2|`=0.95375 ⇒ `gp_0x6c2c = 7.5965·U` ⇒ U = **1685**) — 4 significant figures by
  a different method. The `acc` clamp bites at U ≈ 4017 ⇒ `T` is reached at ~42% of saturation, linear there.
  🛑 **Do NOT size `T` from bus torque.** A pass this session derived "T ≈ 2048–2560" and "LSB ≤3.29×
  finer" from the `0x18F` torque channel; **both are VOID** — `gp-0x6c2c` is not torque-derived and does
  not share that LSB. Also void: a "per-tick rate ⇒ effectively dead" reading that priced the chain at
  unity gain and missed the `×1024` and `×32` pre-scales, which are invisible from the bus.
  ⚠ `gp-0x4f50`'s physical units remain **untraced** (needs the ISR writing `gp-0x29c4`, or a probe), so
  1683 is in raw counts of a signal whose scale is unknown.
- 🛑★ **`gp-0x671a` is NOT private to the rate lanes — 4 external consumers.** Byte-scanned both
  encodings, whole image: 8 real hits, 6 reader functions, sole writer `0x42A12`. External:
  **`FUN_0003a382`** (a **continuous LERP index**, not a gate, shaping the live P/I/D lane `gp-0x6ad4`),
  **`FUN_00036c12`** (friction-comp `gp-0x6b26`, sums into the *same* aggregator; ⚠ its own gate uses cal
  `0xC64FD`, **not** CEIL), **`FUN_000352b4`** (gates a 2nd-order IIR update), **`FUN_00035b20`** (selects
  between two LERP-blend curves). ⇒ **lowering `T` changes five things at once.** By contrast `gp-0x67df`
  is **clean** (2 hits, both inside `FUN_000428d4`) and `T` itself has 4 readers, all inside the detector.
  `CEIL` (`0xC64FA`) is **not** private — 3 external readers.
  ✅ `gp-0x671a` is logged into a diagnostic record array each low-torque tick (`FUN_00045608(2,…)`) but
  the DTC-0x21 dispatch in that tail reads a *different* array (`gp-0x6544[2]`, producer untraced) ⇒
  "touches diagnostic logging, does not appear to gate a fault" — not chased to full closure.
- 🛑 **`0xC64FA` (CEIL) is a BYTE cal = 5, read by `ld.bu` @`0x3AA78`.** A halfword read gives **517** and
  is wrong. Lowering CEIL means writing one byte. (`T` at `0xC620A` *is* a halfword, `ld.h`, = 12800.)
- 🛑 **`gp-0x671d` is NOT "r24's override flag".** It is a **saturating rising-edge counter on a
  torque-residual/observer check** (`FUN_00041d56`, 5-tap filter combination vs `tp+0x71f8`/`0x71fa`),
  feeding DTC dispatch `FUN_00016de6(0x5e,…)`, reset only by `FUN_0003bcb2`'s resync — **not** every tick.
  8 reader functions including the motor-off dispatcher `FUN_0003d4a2`. It read **0** for all of route
  `35`, so r24 *was* covered by V64's arm. Writer/reader set confirmed exhaustive by whole-image raw byte
  scan in **both** encodings (disp16: 16 hits; disp23: 0).

- 🛑★★ **`gp-0x6ba6 == |gp-0x6b9a|`, and `gp-0x6ba6` — not `gp-0x6b9a` — is the boost amplitude index.**
  Byte-verified 2026-07-30; **`build_v58_tva.py`'s docstring was wrong on both counts** and is corrected
  in place. `FUN_0003b66a` writes both from the same r28 (`cmp r0,r28 / mov r28,r13 / bge / subr r0,r13`
  @`0x3b874-87c`, then `st.h` @`0x3b892` and `@0x3b8b0`; byte-scanned for **both** gp-relative encodings:
  exactly one writer each). `gp-0x6b9a`'s only live consumer in `FUN_00034a72` is a **five-input
  plausibility gate** (`|x| ≤ 25600` @`0x34c9c-cb4`, ANDed with `gp-0x6ba6`/`gp-0x4f68`/`gp-0x4f60`/
  `gp-0x6c2e` into r21, which zeroes r24 @`0x34fc8`) — **its sign has no effect on the output**, and two
  of its three reads there (`0x34b5e`, `0x34b68`) are **dead** (`tp+0x7499 = 1` takes the branch
  @`0x34b3c`). **`0xD28DC` hangs off pointer table `0xca4f4`, NOT `0xca23c`** (which resolves to
  `0xD2888`); resolved from image bytes across all 34 modes.
  ⇒ **THE MECHANISM:** V58 measured the *signed* sibling crossing zero at 20.93 Hz only when LKAS
  applies, so the index is that signal **full-wave rectified** — a minimum at every zero crossing,
  sweeping the boost amplitude curve (`0xD28DC` Y = 16384→8187, `0xD2888` Y = 16384→8176) at **~2× the
  mode frequency on the BASE ASSIST path**. ⚠ **INFERENCE, depth unmeasured**: a sign bit carries no
  amplitude, and the delivered swing depends on how far up the curve the index climbs —
  `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert"
  below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero.
  **V59 measures which regime. Do not move `0xD28DC`/`0xD2888` until it has flown.**
- ⚠ **`FUN_0003b66a` branch A is NOT a biquad** — a subagent claimed "a genuine floating-point 2-pole
  biquad, IIR by definition"; it is not. `tp+0x5018/501c/5020` = `0xC4018/1C/20` read **(1.0, 0.0, 0.0)**
  and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, not
  feedback. **Stateful ≠ recursive.** It is the identity 3-tap FIR already on record, so **"no biquad
  anywhere" survives and there is no new notch candidate.** Also new: `tp+0x74be = 0` (`0xC64BE`) makes
  `0x3b736–0x3b758` (the `divf.s` block) dead code.
- ⚠ **`search_instructions` undercounted again** — 8 access sites for `gp-0x6b9a` where a Python byte
  scan finds **9** (it missed V58's own cave read at `0xC4B4E`, an unanalysed region). The sole-writer
  conclusion held, but only because it was re-derived. **Never let a writer/reader set rest on it alone.**

- 🛑★★ **`gp-0x6a56` is NOT independently sensed.** `FUN_0003f776` (sole producer, 4 `st.h`, all inside it):
  `gp-0x6a56 = clamp(polarity × ((gp-0x6abe × 48 × cal(tp+0x713a)) >> 15), ±12000)` — a fixed Q15 scale of
  the **motor/resolver electrical rate**. The ±12000 is a magnitude clamp recomputed fresh each tick, not a
  rate limit; `gp-0x6a60` merely mirrors its magnitude. ⇒ **`STEER_ANGLE_RATE` is opendbc-named but is not
  an independent angle sensor**, so "996× on rate vs 877× on torque" is two EPS-internal derivations, not
  independent corroboration. And since `gp-0x6bbe`'s `baseline` is **also** `gp-0x6abe`-derived,
  `rate_error = baseline − angle_rate` may partially cancel ⇒ **the damping sign is UNRESOLVED.**
- 🛑 **`FUN_0004613e` is not a rate limiter.** It snapshots params into log cells and calls
  `FUN_00016de6(0x1c,…)`, a fault logger; **`0x3638` (13880) is a diagnostic TAG** (the same callee takes
  `0x38c7` elsewhere). The `gp-0x6bb2/4/6/8` cluster is a cross-tick **integrity watchdog** re-deriving the
  same ±512 ceiling in float, with **no forward path into any control signal**. Golden model corrected.
  ⚠ Its fault path calls `FUN_000462e6(0x39e9,…)` **ungated** — Monitor 2's hard-shutdown chain. Any edit
  to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table `0xD2018` to match, or it may trip.
- 🛑 **`0xC6372`/`0xC636E` is a DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every
  build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. Any
  GATE-2 analysis of those two cals is analysing a lever with zero effect on this firmware.
- **The FIR slots are real but cannot notch.** `FUN_0003b66a` implements a genuine **3-tap transversal FIR**
  (`y[n] = b0·x[n] + b1·x[n−1] + b2·x[n−2]`, two persisted delay states `gp-0x365c`/`gp-0x3658`) — **not a
  2-pole IIR biquad**, so it is unconditionally stable. Coefficients `0xC4018/1C/20` = floats
  **(1.0, 0.0, 0.0)** = identity; a second instance `0xC4048/4C/50` (`FUN_0003b8f6`) is also identity.
  Exactly **one consumer each**. See "closed levers" for why enabling them fails.
- 🛑 **The ±565/cycle slew in `FUN_0003b66a` is a CODE IMMEDIATE** (`mov 0x440d4000,r6` = 565.0f), not a
  calibration. Editing it is a code-patch-class change. The halfword 565 in the cal region
  (`[0,191,402,565,686,804,878]` at `0xCE43C` etc.) is an unrelated LERP entry — numeric coincidence.
- ⚠ **The two `STEER_ANGLE_RATE` copies disagree by a constant 1.25×** (`0x18F[2:4]×−0.1` reads 0.799–0.800
  of `0x14A[2:4]×−1.0`, corr +0.9997). One DBC scale factor is wrong. Frequencies, Q, prominence and ratios
  are unaffected; **absolute deg/s figures are not.**
- 🛑 **`STEER_STATUS` is `0x18F` byte4 bits 7:4**, not bits 2:0 (which are SPARE — never written anywhere in
  the image, boot-zeroed, read 0 forever). Reading bits 2:0 yields a tautological "always 0". Route 29 shows
  `ST==3` in **120 frames**, all at `vEgo == 0.000` exactly, never with LKAS applying, in two episodes
  (1.08 s at log start, 0.10 s at t=77.8 s). **Not a V57 regression** — `0xC62EA` is byte-identical across
  V55/V56/V57. Amends the record's "ST=3 never fires on V53+".
- 🛑 **The "8.69 Hz line V56 introduced" never existed — it is wheel order 1.** V56's 35 windows sat at
  v ≈ 18 m/s where `0.489·v − 0.186 = 8.69`; its own edge windows move to 7.03 and 9.77 Hz, and V57 tracks
  identically (7.03 → 8.98 → 9.38). **Its absence on V57 is NOT evidence the `0xC6AF0` mute was live** — a
  different liveness proof is needed.
- ⚠ **The recorded V56 baseline `7.66e4` is suspect** — within 5% of route 24 seg 0's *all-frames* power,
  and that segment contains **zero** LKAS-applying frames.

---

## ✅ The tyre line — CONFIRMED, firmware-independent, and actionable

Order tracking (rescale each window's frequency axis by its own wheel frequency before pooling) puts
**both** builds at **order 1.000**:

| build | K | v range | order peak | prom | implied circumference |
|---|---|---|---|---|---|
| **V57 / r28** | 9 | 4.2–20.1 m/s | **1.000** | 11.7 | **2.088 m** |
| V56 / r24 | 59 | 9.5–20.5 m/s | **1.000** | 6.2 | **2.088 m** |

Estimator calibrated on V56 first, where the answer was known. Decoys at order 0.70/1.40/1.80/2.00 all
score far below. Per-window on V57's road episode: 2.056–2.105 m, with a 715× prominence burst at
19.5 m/s. A 235/45R18 is 2.05–2.11 m ⇒ **one line per wheel revolution**.

⇒ 🛑 **Get a wheel balance / road-force check.** Firmware cannot move a road input, and it didn't.

★ Separately, a **fixed ~7.4 Hz resonance** is present on V57 (Q 36.2 at nfft=1024, prominence 40–136×) at
1.2 m/s where wheel order is only 0.59 Hz ⇒ **not the tyre**. It is the ratchet. Route 28's creep misses it
because that creep is |ang| 5.8° — **excitation, not absence** (r29 creep is 26.5°, matching the historical
set's 12.6–42.2°).

---

## Recommended next steps, in order

🛑 **NO openpilot-side modifications.** Standing operator instruction. openpilot remains a *measurement
instrument* only.

0000. 🛑🛑 **2026-08-04, STANDING: BYTE-CHECK THE CURRENT IMAGE BEFORE CITING ANY CONFIRMED RESULT.**
   `RULE 3`, `docs/BUILD-LINEAGE.md`. Both of this kit's confirmed fixes — V42's `0x454FE` and V62's
   `0x3AB76`/`0x3AC20` — **had fallen off the car and nobody noticed for ten builds.** A confirmed fix
   that is no longer carried is not evidence about the car you are driving.

000. 🛑 **NAME THE FILE BEFORE ANY FLASH.** More than one `.rwd` carries a `V70` prefix, and the
   superseded first cut has the **OPPOSITE** control path (`…LKASGATED-V68CONTROLPATH…`) with a
   **byte-identical cave**, so the probe cannot tell them apart on-car. It is renamed
   `SUPERSEDED-DO-NOT-FLASH-…` (`9d44efc`, filesystem-verified). ⚠ **The same discipline now applies to
   V70 vs V71.**

00. ★★★★ **2026-08-04: V71 IS BUILT AND UNFLASHED — restore both lost fixes, and probe the GAIN IN
   FORCE.** Its rate lane is **byte-identical to V62/V65**, which flew twice, both flight-clean. The two
   verdict-affecting reads it buys: **bit6 `gp-0x671d != 0`** (which gain is actually in force — the
   direct answer to four consecutive probes that returned uninterpretable zeros by reading a lane
   *output*) and **bit5 `gp-0x67fa == 4`** (a **complete** discriminator now that states 5 and 10 are
   excluded; **pre-registered bimodal**).
   🛑 **State the `0x454FE` justification honestly: it is restored because it is a confirmed fix lost by
   accident, NOT because it is established to cause the current ratchet** — the ratchet measures
   **symmetric** while the substitution is **asymmetric**, which is evidence against that mechanism.
   ⚠ **Known risk, disclosed: V62 is also the build that introduced creep grind #2.**
   🛑 **Do NOT stack V72's lever onto V71** — **FactorC/FactorE together, re-read against the RATCHET**
   (V47's *"marginally quieter at 5 mph"*, never evaluated against it) deserves its own single-variable
   drive. ★★ It is **materially more compelling** now: *engagement-required* + *hands-off-conditional*
   + *Q ≈ 40* + *damping exactly zero below ~35 km/h* ⇒ **at creep the driver's hand is the only damping
   in the system.**
   🛑🛑 **`0xC6444` is STRUCK — a NULL BY CONSTRUCTION on any gateless build** (THE HEADLINE §8). Do not
   re-propose it.
   🛑 **Do NOT aim any rate-lane dose at the lane-change transient** — dose-independent; excitation, not
   gain. 🛑 **Do not re-quote any pre-2026-08-04 rate-lane multiplier without saying it is r24-only at
   `a = 0`.**
   ⚠ **Everything below this line predates the V70 flight.** Read steps 0–0c as the reasoning that got
   here, not as current recommendations.

0. ★★★★ **OPERATOR'S DECISION 2026-08-01: FLASH V67 FOR THE LONG DRIVE.** V67 = V66 + the
   grind #1 fix gated on LKAS — `0x3AA96` `c5`→`fb` (repoint the dead `gp-0x683c` gate to
   `gp-0x6806`) + `0xC6446` 512→**5244**, with both `sar` sites left STOCK. **LKAS off is
   byte-for-byte stock behaviour; LKAS on gets 2.00× at grind #1's operating point.**
   ✅ **The gate is VALIDATED ON-CAR ALREADY** — V57's probe measured `gp-0x6806` at **99.90–99.94%
   agreement with `latActive`** over 37,914 frames and **0.03–0.05 toggles/s**, so it is the
   engagement flag, it does not drop out during steady holding, and it cannot parametrically pump.
   **Pre-committed interpretation:**
   - **grind #1 gone, grind #2 gone in manual, grind #2 remains under LKAS** ⇒ the expected outcome.
     Next lever is `0xC6446` itself (one halfword) to trade the two.
   - **grind #1 back** ⇒ check probe bit6 duty (gate not firing ⇒ wrong cell) then bit5
     (`gp-0x671d` firing ⇒ the arm is masked and the gain is pinned to 1024, *below* stock).
   - **grind #2 worse under LKAS** ⇒ 2.21× is too much there; lower `0xC6446`.
   🛑 Do NOT read a V67 null without decoding the probe first — that is the V64 lesson.

0a. **V66 remains built, verified and unflashed** — the pure stock-rate-lane control. It is still the
   cleanest confirmatory revert if V67's result is ambiguous.
   ~~FLASH V66 AND DRIVE IT LONG.~~ ✅ Built, verified, and it is exactly what the operator asked
   for: **V38 4× LKAS reach · steer-to-zero · stock rate lane (grind #1 left as V38 has it) · live
   telemetry.** It is simultaneously **the confirmatory revert** — the one knob that produced grind #2
   goes back to stock, so the drive tests the attribution for free — and **the pre-flight probe for
   V67's gate**, which is the fix.
   **Route:** ordinary long driving plus deliberate parking-lot creep, **and specifically reproduce
   grind #2** — creep with heavy manual steering, |angle| ≥ 100°, both engaged and disengaged.
   🛑 **Log from before the first engagement.** Decode with `rlog-tools/decode_v66_gateprobe.py`.
   **Interpretation pre-committed, so it cannot drift:**
   - **grind #2 GONE, grind #1 back** ⇒ attribution closed. Build V67 (gate the ×2 on whichever of
     `gp-0x67f5` / `gp-0x6806` the probe shows is chatter-free).
   - **grind #2 STILL THERE** ⇒ the rate lane is the wrong tree; V62 should go back on (it is a proven
     fix and would be being given up for nothing), and grind #2 becomes a ~44.9 Hz mechanical mode to
     attack in its own right.
   - **bit5 (`gp-0x67f5`) toggling anywhere near 15–60 Hz** ⇒ that gate is DEAD; a gain keyed on it
     would be a parametric pump. Fall back to `gp-0x6806`, or to V68's dose reduction.
   - **bit4 (`gp-0x683c`) ever 1** ⇒ the cell is not dead, and V67's repoint is not a clean
     substitution. Cancel it.

0-old. ~~**NO NEW BUILD. KEEP V62 ON THE CAR AND FLY IT AGAIN.**~~ — **SUPERSEDED 2026-08-01.** The
   "rare event needing exposure" framing was right to demand more data and the data arrived: the
   operator flew V65 twice and the events are **not** rare in the corner, they are **11.7× at 40–49 Hz
   with p = 0.0003**. See THE HEADLINE. ✅ V62 flew and **BETTER** was the
   pre-committed outcome — direction confirmed, and the grinding is fixed 8–42×. **There is nothing
   established to fix.** The one candidate event is a **0.92 s singleton at p = 0.51** against an
   exposure-matched control, and V62's burst-rate CI sits **inside** V59's. A fix would be aimed at a
   coin flip.
   **The open question is the RATE of a rare event, and that needs EXPOSURE, not firmware.** Two more
   V62 routes make it estimable: if it never recurs it was a one-off; if it recurs at ~1/700 s there are
   three events and a real CI.
   **Route:** ordinary driving plus deliberate creep passes, and specifically **revisit the corner the
   burst lived in — v 2–4 m/s at high steering rate (≥32 deg/s) under LKAS.** Log from before first
   engagement. 🛑 Do **not** re-run the pre-committed `sar 0x8` (4×) escalation yet — it would trade a
   confirmed fix against an unmeasured effect.

0a. **When a build does come, the target is the RATCHET — and the search space just shrank.**
   ⚠ ~~❌ NOT the r26 revert (structurally inert — see the headline).~~ **The inertness claim SPLIT on
   2026-08-04 (THE HEADLINE §7): the GATE leg is reversed, but the MAGNITUDE leg — the one this
   exclusion actually rests on — is only DOWNGRADED to BELIEF, and the dose–response argues it holds.
   So the exclusion is weakened, not withdrawn. V70's sign pair decides it.** ❌ NOT the base-assist damper
   `gp-0x6bd0` (f5 = 0 at both operating points; a **third** independent reason V44/V47 were null).
   ❌ NOT friction comp or a deadband — the ratchet waveform is **symmetric on every build**
   (skew(dx/dt) −0.16…+0.06 vs a −3.27 sawtooth calibration) ⇒ an **amplitude-saturated resonance**,
   pointing at damping/loop gain. ❌ NOT the motor-rate LERP as a discriminator — scale resolved at
   **4.7121 counts per deg/s** (`0xC613A` = 1159), so ratchet 9.4 counts and grinding 73.0 counts both
   sit inside gain_A's **flat first segment** (breakpoints 250/400).
   ✅ **STILL OPEN, the leading idea:** the modes **do** separate on motor rate, and **breakpoints are
   calibration**. r24's gain_B (mode 10, `0xD2AEC`) has X = [0, **400**, 1500, 3000], Y = [2305, 2304,
   2149, 1948]. Moving them to bracket the two operating points — e.g. X = [0, 40, 100, 3000],
   Y = [2305, 2305, 4610, 4610] — gives **stock gain where the ratchet lives and 2× where the grinding
   lives**. Arithmetic safe (5120 × 4610 = 23.6M vs 2³¹). Hold until the ratchet is worth attacking.
   ⚠ **The ratchet's trigger sits outside the firmware**: instant #1 occurs with openpilot's command
   **railed at ±4096** for 0.64 s with the driver turning against it (engaged-creep rail duty **V62 42.4%
   vs V59 25.3%** — itself a confound). 🛑 **NO openpilot-side modifications** is standing; recorded as
   observation, and the constraint is the operator's call.

0b. 🛑 **DO NOT re-propose lowering `T` (`0xC620A`) as a cheap fix.** It is *viable on sizing* — see the
   `gp-0x6c2c` section below, ~1.7–2× short, not 5× and not 30× — but `gp-0x671a` has **four external
   consumers** besides the rate lanes, one of them (`FUN_0003a382`) using it as a **continuous LERP
   index** into the live P/I/D lane `gp-0x6ad4`. Lowering `T` changes **five things at once**, four
   uncontrolled, one of them a shape parameter on a lane already known to be load-bearing. That is not a
   clean GATE 1 and not a clean experiment. It ranks **behind** V62 and behind the phase lever.

0c. ⚠ **Superseded, was step 0:** ~~FLASH V63 FIRST, THEN V62 IF NULL.~~ The reasoning was sound and the
   ordering did buy the answer it promised — V64 (V63 + the detector probe) established *for free and
   without a second flash* that the detector never trips. But the premise ("zero manual-feel cost by
   riding the firmware's own oscillation detector") turned out to be **moot**, because the arm is never
   selected, and **weak even if it were** (r24 ×1.78, r26 ×1.00 — Honda's osc arms are gain *reductions*).
   ⚠ **Operator's standing objection, and it was right:** *"we seem to be affecting manual steering feel
   even though the symptom is specific to LKAS-engaged only."* V62 did ignore that question. The answer
   is that stock `Kd` is not sufficient for manual either — **manual has `Kd` PLUS the driver's hands**,
   which damp the very mass that resonates (wheel inertia on the torsion bar). Measured 2×2: V59 manual
   9.2 / V59 engaged 1092 / V61 manual 163 / V61 engaged 3007 — removing `Kd` degraded **both** arms, so
   it was doing real work in manual all along. LKAS also *injects* energy at the mode frequency
   (command→bar transfer peaks at **21.09 Hz**, the global max, coherence 0.917).
   ⚠ V62's residual manual-feel cost is **small and computed, not hoped**: the lane is a *derivative*, so
   it is inherently frequency-selective — doubling adds **+50 counts at 1 Hz driver bandwidth (0.49% of
   the ±10240 sum clamp) vs +732 at the mode. 14.6:1 selectivity.**
1. ~~**FLASH V62 as the primary**~~ — superseded by step 0. It remains the matched inverse of the one
   build that produced a signed result: `Kd`→0 diverged, `Kd`→2× is the same-sized step back, and the
   damping coefficient is **linear in Kd**.
   **Route:** repeat the V61 route so the comparison is like-for-like — parking-lot creep, deliberate
   LKAS on/off passes at matched speed and angle, **plus the same manual-forward and manual-REVERSE
   passes**. 🛑 **Manual reverse is the highest-information single test**: V61 introduced grinding there
   from nothing, with no LKAS in the loop at all, so it reads the lane's damping with the cleanest
   possible confound structure. Probe unchanged (`rlog-tools/decode_v59_boostindex.py`) — secondary
   readout only, since `gp-0x6ba6` is upstream of the edit.
   **Interpretation set in advance, so it cannot drift:**
   - **BETTER** ⇒ the lane is the damper, the direction is confirmed, and the next question is *how much
     more* (V63 = 4×, or the phase lever below).
   - **NULL** ⇒ the lane's damping is already **phase-limited**, not gain-limited. Then the next lever is
     the lead's **PHASE**, not its gain: **`0xC6C42` (delay D) 4 → 2 halves the differentiator's transport
     lag, 15.1° → 7.6° at 20.9 Hz.** ⚠ Note the earlier objection to D — "it is half a lockstep pair" —
     is **RETRACTED**: `0xC6C42` has exactly one reader (`FUN_0007e74a`) and D feeds a single computation
     broadcast to both cells in sync. The real caveat is that D sets the differentiator's time window and
     its response at other D is uncharacterised. Characterise it before building.
   - **WORSE** ⇒ the lead has gone past optimum into noise amplification; back off to 1.5× rather than
     abandoning the lane.
1. **Analyse the V61 rlog, route `00000031--0441e00d2b`** (4 segments). Not blocking V62, but it is the
   only quantitative record of a *signed* change and it answers two things nothing else can: whether the
   newly-appearing **manual/reverse** line sits at the **same ~20.9 Hz and Q** as the engaged grinding
   (⇒ same mode, unmasked) or elsewhere (⇒ a different finding, and V62's rationale needs revisiting),
   and whether **`ST==4`** stayed at 0. Use the strict 18–26 Hz band + presence test, `latActive`,
   sustained-effort hands-off, and peak-frequency **scatter** as the mode-vs-floor discriminator.
2. 🛑🛑 **RESOLVED 2026-07-31 — AND THE ANSWER WAS THAT THERE WAS NEVER A NUMBER. V52C DID NOT HALVE
   ANYTHING.** This step used to read "re-derive V52C's halving under the corrected statistics; the
   rlogs exist." **Both halves of that were false.**
   - **"Halved the mode" is the FILTER'S OWN TRANSFER FUNCTION, relabelled as an on-car result.**
     V52C's EMA at α = 74/1024, fs = 1 kHz, gives `|H(20.9 Hz)| = 0.4963` = **−6.08 dB**. −6.1 dB **is**
     0.496× **is** "halved". The two figures in the record are the same statement written twice.
     Independently recomputed 2026-07-31 in `analysis-2020accord/eps_feedback_path_coverage.py`.
   - **Textual lineage, git-traced.** The phrase was born in `f0adb24`
     (`HANDOFF-2026-07-28-v55-...md:205`) as a **caveat explaining why V52C's NULL is weak evidence**:
     *"⚠ V52C's null is weak — only −6.1 dB at 21 Hz while adding 61° of lag. It halved the mode's
     content; it did not remove it."* By `59acdd2` (the V59 handoff) it had become *"halved the mode —
     the largest single effect any build has had"* and the word **null had vanished**.
   - **Every contemporaneous on-car record says NULL, including the operator's own words:**
     `HANDOFF-2026-07-26-route13-...md:8` — *"V52C did not fix the vibration; it clearly changed manual
     feel."* `ARCHIVE-CLAUDE-MD-2026-07-27.md:56` — *"V52C's null is MEANINGFUL: −6.1 dB at 20.9 Hz, so
     it WAS a fair test of the `gp-0x4f60` lane ⇒ real evidence AGAINST that lane."*
   - **There are no V52C rlogs and there never were.** Routes on disk: `13,1a,1b,1c,24,28,29,2b,2c`.
     The V52C window (`08`–`12`) is absent from the whole machine and was never in git.
   ⇒ **The loop hypothesis loses its retrodiction entirely.** It now rests only on the two things that
   were actually measured: the **21.09 Hz command→torsion-bar transfer peak** (global max over 3–46 Hz)
   and the **traced absence of any motor-command feedforward**. Both stand.
   ⚠ This does **not** falsify the loop: a 2× gain cut that also adds ~57–61° of lag is a poor
   stabiliser, so a null is what a real loop with <6 dB gain margin would also produce. V52C is
   **weak-to-moderate evidence against the `gp-0x4f60` VALUE path**, not against the loop.
2b. ~~**Flash V60 as a DISCRIMINATOR**~~ — ✅ **DONE 2026-07-31, null, pump closed.** Kept for provenance:
   It attacks the
   *pump*, and the pump now looks like a passenger. **A null is the informative outcome**: it would
   close the parametric mechanism this kit spent V58/V59/V60 on and leave the loop standing.
   **Route:** parking-lot creep **v ≤ 5 m/s**, LKAS applying, **sustained hands-off ≥ 3 s**
   (`|lowpass(tq,3Hz)| ≤ 200`), deliberate LKAS on/off passes at matched speed and angle, plus a pass
   at the **10–13 m/s under-load** population. Decode with `rlog-tools/decode_v59_boostindex.py` — the
   probe is **unchanged and is the CONTROL**: the index distribution must return statistically
   identical to V59 (76.9 / 18.5 / 4.6 / 0.04 at engaged+creep+hands-off). If the index matches and the
   grinding moved, the blend is the only thing that did.
3. 🛑 **Sizing any loop fix needs the phase margin, and the bus cannot give it.** One 100 Hz mailbox
   sample is **~76° at 21 Hz** — larger than any phase worth reading. Establishing loop phase needs a
   **firmware-side probe** (a V59-class thermometer on a signal that crosses zero at 21 Hz), not more
   rlog analysis. Until then, any gain reduction is empirical and iterative.
4. ⚠ **Base-assist loop gain (`0xCA154[mode]` → `0xD2834`, speed-keyed) is the untested handle** — and
   it is a **direct trade against steering weight**, so it is an operator decision, not an analyst's.
   Grep it and state its history before proposing it. The amplitude curves `0xD28DC`/`0xD2888` and
   `0xC63BA` are the other in-loop knobs; all sit on base assist, none has an LKAS-only decoupling
   point (traced and confirmed — unlike V57's `0xC646C`, this chain has no fork).
5. **Re-run the strict-band (18–26 Hz + presence test) analysis over the V55/V56/V57 routes.** Route 2c
   independently rejected `a = 0.177` (2.60σ presence-tested, up to 7.08σ raw) and its fitted subset is
   **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728), so the fixed ~20.9 Hz line is now
   the record — but the historical amplitude baselines still need re-deriving on lateral engagement +
   sustained-effort hands-off + envelope statistics. Treat `7.66e4` as provisional.
6. ★ **The ratchet: route `2c` HAS clean episodes, and the record says it shouldn't.** 7.56 ± 0.36 Hz,
   within-run sd 0.07–0.10 Hz, prominence median **783×** (max 2142×), **15 windows / 5 runs**,
   hands-off + engaged + creep, at both 9–15° and 133°. `STATE.md` previously recorded that route 2b
   gave **zero** and that a dedicated comma-commanded route would be required. **Mode identity
   unconfirmed** — this was found incidentally by an analyst outside its brief. Verify before building
   on it.
7. **The ratchet still has no cal lever and no mechanism.** All rate-limit candidates are closed (see
   `BUILD-LINEAGE.md`). Next step is measurement, not a build. The return-centre lane `gp-0x6b62`
   (aggregator, ZERO-gated ±0x2000) has never been probed and is the operator's own hypothesis.
   🛑 **Route `2b` cannot speak to the ratchet in either direction, and the operator said so before the
   data did.** Hands-off + engaged + `|e4tq| ≥ 3500` + v ≤ 3.0 m/s yields **9 runs / 139 frames (~1.4 s)**,
   all inside one 8 s window in seg 1 that overlaps a hands-on manoeuvre sweeping −24° → +302° — i.e.
   transient zero-crossings of the lowpassed effort signal *during* hands-on driving. **Zero clean
   episodes.** The driver-applied sharp turns don't show it either: 6–9 Hz sits at or below a strict
   quiet baseline in 8 of 11 long episodes, with the 5–10 Hz peak wandering 5.3–9.9 Hz rather than
   locking at 7.4 Hz with Q≈36. **A dedicated comma-commanded route is required.**
8. 🛑 **Do NOT move `0xD28DC`, `0xD2888`, or `tp+0x73ba` (`0xC63BA` = 512).** All sit on the **base
   assist** path with no LKAS-only decoupling point, so they change manual feel and all need GATE 2.
   ⚠ `0xC63BA` is **partial by construction**: byte-verified as a 2-stage EMA (α = 0.5 both stages,
   blast radius fully contained — 2 reads, both in `FUN_0003b66a`), but it filters only the **torque**
   lane, and the index is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`, via
   `FUN_00041464` ← `FUN_00068f52`'s angle-delta differentiator). It cannot touch the second lane.
9. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.
6. **The take-over beep is closed** — `commIssue`/`selfdrivedLagging` under device CPU load, clean CAN/EPS
   null. Seen again on both V57 routes (route 28's at t=126.5 s produced a real soft-disable).

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** `gp-0x6966` is wind-up-driven, not
speed-driven, and V31's boost floor makes wind-up unreachable (V54 measured this on-car under railed
command).

---

## Still-standing results worth not re-deriving

- **`gp-0x6966` authority ≡ 0 by design on V31+** — soft-EME wind-up magnitude, pinned by V31's boost
  floor; `0xC6AF0` selects unity in 100% of normal operation. Measured on-car, route `1b`, 5,989/5,989.
- **Steer-to-zero works** — `0xC62EA` = 0, `ST=3` never fires while moving, 226 frames of
  `STEER_CONTROL_ACTIVE=1` below 5 km/h on route `1a`.
- **The `0x14A` byte4 bits 7:3 piggyback is proven across FOUR flashes** (V54, V55, V56, V57). Use it for
  all future firmware telemetry; **do not build another new-mailbox channel** (FOURFRAME2 was never
  transmitted — that null remains uninterpretable).
- **No notch/biquad exists anywhere** on the arb, aggregator, r24/r26, comp-add, boost/damping/friction,
  shaper, or governor paths, nor in the three non-aggregator consumers of `gp-0x6b94`
  (`FUN_0004503c` governor, `FUN_0004595a` redundancy monitor, `FUN_0007ff08` boot interlock). Two regions
  remain unswept: the raw CAN → `gp-0x4f60` producer, and the FOC current loop below `gp-0x6b98`.
- **An rlog cannot identify the flashed build from the version string** — every build reports
  `fw='39990-TVA,A160'`. Behaviourally: `ST=3` never firing while moving ⇒ V53+; probe field semantics
  identify V54/V55/V56/V57/V58 exactly.
