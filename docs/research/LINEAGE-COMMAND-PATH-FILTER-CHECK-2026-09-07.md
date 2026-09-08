# Lineage check: has any build ever filtered the LKAS command/setpoint path? (2026-09-07)

**Purpose.** Before cutting a V288 code cave that interpolates/filters the LKAS setpoint (the
`0xE4`-derived reference) inside the EPS ahead of the 1 kHz rate PID's error, the whole post-V38 arc
was checked for prior attempts at filtering, slewing, rate-limiting or interpolating that specific
signal — as opposed to feedback lanes, the base-assist damper, the 55 Hz biquad, the assist-lane lag
pole `0xC6906`, or the r24 rate lane. Read-only research pass; every claim below is EVIDENCE (cited by
file + heading/grep string) unless marked BELIEF/OPEN.

Base for this check: **V282** (on the car), candidate under evaluation: a setpoint-interpolation cave
on top of V282.

---

## (a) Is a setpoint filter genuinely new to the arc, or a re-run?

**GENUINELY NEW AS CODE.** The general idea "smooth/limit the command" has been visited many times
across 250+ builds, and every prior instance acted somewhere else in the chain — none of them ever
touched the live `0xE4 → assist map → 32·sp` path that feeds the 1 kHz PID's error.

Current `docs/STATE.md` (§"THE MECHANISM BEHIND THE D CLAMP, and why the staircase cannot be softened
by calibration", 2026-09-06) is the most authoritative statement in the record and says this directly:

> "the setpoint path has NO memory anywhere from the 0xE4 byte to the error — CAN decode store
> (0x526F2) → symmetric clamp → Q16 LERP scale → ›22 → clamp 240 (0xC64F0) → assist map → `shl 5` (an
> immediate) → `sub`. Structural test: a slew needs a RAM cell both written and read; the positive
> control finds the lag filter's state (gp-0x3d3c); the setpoint region has none [EVIDENCE, tracer
> addenda 5–6]."

`docs/BUILD-LINEAGE.md`'s V287 rev 2 row ends with the same conclusion: *"Identified, not built: a
setpoint-interpolation code edit (no cal on the setpoint path has memory — the staircase reaches D
unfiltered)."*

### What HAS been tried, and why none of it is this lever

1. **V50 / V51P / V52 / V52C** (2026-07-22 → 2026-07-24) — a first-order EMA low-pass cave
   (fc ≈ 12 Hz, α = 74/1024) on **`gp-0x4f60`, the raw torque-SENSOR (feedback) signal**, not the
   command. V52C repointed all 19 command-region *readers of the sensor* to a filtered copy. **This
   is a feedback-path filter, not a setpoint filter.**
   - GATE 1 history matters here: V50's chosen state cell **`gp-0x1500` FAILED** — it is a live
     I/O-mailbox slot (the `0xb7260` array), proven non-free by an on-car probe (V50P) *before* the
     full filter build was ever flown (`memory/reference/can/reference-accord-b7260-io-mailbox-array.md`).
     The rebuild moved to `gp-0x1300` (V51P/V52/V52C).
   - **V52C WAS flashed and driven.** Operator, `docs/handoffs/2026-07/HANDOFF-2026-07-26-route13-vibration-engagement-dependence.md`:
     *"V52C did not fix the vibration; it clearly changed manual driving feel."* NULL on the symptom,
     real cost to manual feel.
   - `docs/handoffs/2026-07/HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md` separately
     retracts a fabricated claim that "V52C halved the mode" was load-bearing evidence for a loop
     hypothesis — the arithmetic (0.496× = "halved") is correct but was never a positive result; every
     contemporaneous record calls it a null.

2. **V43 "dirty derivative pole"** (`0xC644A` 1024→32) — on the **model-residual observer lane**
   (`gp-0x6ad4` / aggregator), a feedforward-vs-actual comparison path, not the command.
   FALSIFIED — fixed neither symptom (`docs/handoffs/2026-07/HANDOFF-2026-07-21-v43-dirty-derivative-pole.md`).

3. **V40 / V41 "governor slew and rate cap"** — V40's asymmetric slew lives in the **merged
   aggregator OUTPUT governor** (`FUN_0004503c`, target = `gp-0x6b94` = LKAS + base assist summed),
   i.e. *downstream* of the setpoint/PID, gating final delivered torque — not the reference entering
   the error calc. V41 then explicitly REMOVED the motor-rate cap per operator directive: *"The
   delivered LKAS command should be as true as possible to what the comma says it should be, relying
   on the comma's peer-reviewed safety measures."* Neither is a setpoint filter
   (`docs/handoffs/2026-07/HANDOFF-2026-07-19-v40-governor-slew-and-rate-cap.md`,
   `docs/handoffs/2026-07/HANDOFF-2026-07-20-v41-ratecap-flat.md`).

4. **`0xC6194` "LKAS-only rate limiter"** (inside `FUN_00026c80`, part of the 11-slot lane mixer) — a
   real, calibrated slew limiter (3 ct/tick, ≈1.37 s full scale) that looks exactly like what an
   operator might ask for. **Structurally DEAD**: its input partition `0xC4118` is all-1s so 100% of
   the request bypasses it, AND arming it is a **hard never-arm** — zeroing the partition byte to
   "arm" it drives `gp-0x3d88`→0 ⇒ `gp-0x6b4c`→0 ⇒ LKAS steering silently dies while openpilot
   believes it is steering (`docs/BUILD-LINEAGE.md`, `0xC4118` row). Additionally (2026-08-29) the
   whole 11-slot mixer's value-A path was traced end-to-end and found to deliver **zero** on this
   car's live records regardless of the limiter — moot even if armed.

5. **`0xC61D6` "shaper slew step"** — a pre-V18 (V16) dormant 2D map, rejected by an 11-round review:
   raising it from 0 does not "re-enable an anti-snap ramp," it activates an uncalibrated speed×torque
   map onto the live command. Re-proposed and re-killed at least twice since
   (`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`).

6. **Notch/pole arc** (V105 biquad retune, V172→V228 relocation, V231 liveness probe, V237 lag-pole
   k=80, V241) — all on the **feedback/observer/damper lanes**, never the setpoint.

⇒ **Net:** this kit has tried filtering (a) the torque-sensor feedback signal (flown, null + cost to
feel), (b) the model-residual lane (flown, falsified), and (c) the merged aggregator output (built,
then removed per operator instruction) — and has found and killed two *dormant* command-adjacent
rate-limiters that turn out to be either architecturally dead or unsafe to arm. **It has never
filtered the actual reference the PID compares against.** A setpoint-interpolation cave would be the
first of its kind in this arc.

---

## (b) Which RAM the builder may use

- **PROVEN POISON — do not reuse.** The whole **`gp-0x1401..0x1502` range is a subset of a 40-slot ×
  8-byte I/O-mailbox array at `0xb7260`** (`memory/reference/can/reference-accord-b7260-io-mailbox-array.md`).
  Confirmed live slots inside it: **`gp-0x1500`** (slot 5 — V50's cell, proven non-free by the V50P
  on-car probe) and **`gp-0x14E0`** (slot 9). **`gp-0x14FA` is the V48B brick cell** (aliased a live
  monitor status byte — catastrophic). Slots are written by **table-dispatched / register-indirect
  pointers**, invisible to disp16/absolute-literal static scans — exactly why static clearance passed
  for `gp-0x1500` and it still failed on-car.
- **GATE 1 sequence that caught this, and should be repeated for any new cell:**
  1. absence from the descriptor/pointer tables at `0x89c34`, `0xbbc48`, `0x89c6c`, `0xbbc80`,
     `0xbbca0`;
  2. zero `movhi` materialising the `0xFEDF` page for that address anywhere in code;
  3. an on-car live probe of the candidate cell (à la V50P) **before** committing the real filter
     logic to it — this is the sequence that caught V50's defect before the functional filter ever
     flew, and it should gate the new cell the same way.
- **Where the new state should physically live.** `docs/STATE.md` (§"NEXT — in order", item 2)
  already specs this: *"Spec the setpoint-interpolation cave: GATE 1 for a new state cell, hook site
  near `0x29D76`, instrument = 427 tap vs mirror on step ticks, dose = interpolation depth."*
  `0x29D76` sits in the same neighbourhood as the D-clamp readers V287 touches (`0x29EE8`/`EF2`/`EF8`/
  `F02`) — i.e. the hook site was chosen with the actual "staircase → 32·Δsp → D" mechanism in mind,
  not guessed.
- **Do NOT reuse `gp-0x1300` / `gp-0x1500` / any `gp-0x14xx` cell.** Pick a fresh cell and run the
  three-part GATE 1 test above (descriptor-table absence + no `movhi` + live probe) that closed out
  V52's replacement cell (`gp-0x1300`, outside the mailbox array).

---

## (c) Authority comparison — "the only thing that ever eliminated the grinding limited the max
angular acceleration and velocity heavily"

No build in the record matches this description literally. The two candidates offered as guesses
don't fit on inspection:

- **V62/V65** (the kit's only clean measured grinding fix, 8–42× reduction at 18–22 Hz,
  `memory/accord/builds/accord-v62-fixed-the-grinding.md`) is a **Kd doubling**
  (`sar 0xa`→`sar 0x9` on the r24/r26 derivative lane, `FUN_0003aa2c`) — more derivative damping, not
  a rate/accel cap. It does not touch max angular velocity or acceleration.
- **V88** ("operator says fixed" for grinding, `docs/BUILD-LINEAGE-CATCHUP-V76-V100.md` V88 row) is
  **Lever B restored** (r24 arm flat 5244 = 2.0× the derivative gain while LKAS applies) — again
  derivative feedback gain. V88 measurably HALVED 15–22 Hz command HF content as a *side effect* of
  more feedback damping, but full-demand rate/authority was not reduced by design.
- The genuine "22.3 deg/s" figure in the record is the **STOCK reference ceiling** (Kp-map top knot,
  pre-any-multiplier — `memory/accord/mechanism/accord-feedback-operand-is-a-two-sample-sum-dc-30-89.md`).
  The closest evidentiary match to the operator's framing is structural, not a specific "build":
  grinding is documented to have **first appeared when V38 raised the LKAS command target ~4× past
  the 512-count governor floor** — `docs/handoffs/2026-07/HANDOFF-2026-07-20-v41-ratecap-flat.md`:
  *"Stock V9's max LKAS demand was 417 — below the 512 floor, so stock LKAS could never be capped at
  all... V38's 4× raise is the first build to cross it. That is why the ratchet appeared with V38."*
  I.e. the record supports "less commanded authority ⇒ no grinding" as an observed correlation across
  the whole arc's *origin*, not as a specific "build X limited accel/velocity and cured it."
- The one build that DOES measurably cut authority heavily and buys stability is **V285** (Kp = 0,
  ZN P-only, 2026-09-04): authority loss −89.7 %@1 Hz / −54.2 %@5 / −40.3 %@7.3 / −30.3 %@9.64 /
  −20.2 %@13.5 / −12.1 %@20 / −5.5 %@40; ring improves to 0.861 from ~0.98; GM 2.11× vs 1.77×. **But
  V285 is explicitly bench-only / DO NOT FLY** (zero steady-state lane-keeping by construction) — it
  has never been driven, so the operator cannot have experienced it eliminating grinding on-car.

**Recommendation: ask the operator directly which build/drive they mean.** Nothing in the record
cleanly matches "a build that heavily limited max angular accel/velocity and thereby eliminated
grinding on-car."

### V282 authority today vs the two structural reference points

| | max LKAS-only target | full-demand rate | notes |
|---|---|---|---|
| stock V9 | 417 raw | ~22.3 deg/s (map ceiling) | never crosses the 512 governor floor — literally uncappable, and (per the record) never reported grinding |
| V38 (grinding's origin) | 1782 raw (4×) | — | first build to cross the 512 floor; ratchet/grinding appear here |
| V282 (car today) | 6× map, clamp 46080, Kp flat 248, Kd 128 | ~125–150 deg/s (93 % of a 133.6 ceiling per V280 rev 2 data) | 6–6.7× the stock rate ceiling |

---

## Code-cave discipline (condensed)

**Bricked (3).** V24 (pre-V18, archived — corridor `shl` desync, superseded before the current
numbering scheme). **V27** — bricked from **asymmetry, not magnitude**: the float corridor twin was
doubled wholesale while the int corridor was scaled only partially. **V48B** — bricked from two
independent causes in one build: (a) RAM collision, cave state `gp-0x14FA` aliased a live monitor
status byte, and (b) an unmodelled lightly-damped resonator dropped into the always-on base-assist
loop.

**Flown successfully since V29** (representative, not exhaustive — the `0xC4B34` cave region is
reused and grown across most of them): V39 (174 B, cave `0xC4B34-C4B5F`); V49P/V50P/V51P telemetry
probes (`0x55C0E` hook + cave, read-only); V54 (44 B cave, 5-bit authority probe); V55 (68 B, dual
probe); V67/V68/V71c/V84–V90 (Lever B repoint + growing comparator cave, 62→74→80 B); V96 (112 B,
**zero cal bytes** — pure repoint + probe); V102/V282 (154–156 B cave with the r24/aggregator
comparator ladder). All of these are either read-only probes or in-place branch/displacement edits
inside a previously-cleared footprint — the "single in-place edit, not a new trampoline + cave" class
CLAUDE.md calls a lower risk than V24/V27/V48B's class.

**RAM proven dead by a flown cave / trace:** `gp-0x683c` (Lever B mask, zero writers, confirmed two
independent ways) is a code-level dead cell, not a RAM-availability example. No RAM cell outside the
`0xC4B34` cave's own footprint has been "proven dead and reusable" as general-purpose free scratch —
that footprint is the kit's one repeatedly-reverified-free region.

**RAM proven to FAIL:** `gp-0x1500` (V50, I/O-mailbox slot 5) and `gp-0x14FA` (V48B, brick). Both sit
inside the `0xb7260` mailbox array (`gp-0x1401..0x1502`), now fully mapped and flagged as poison
territory — 40 slots at 8-byte stride, several confirmed live, written by register-indirect table
dispatch invisible to static scans.

**`build_v282_tva.py` layout** (`analysis-2020accord/builds/v108_plus/build_v282_tva.py`) — the
template a V288 builder should extend rather than reinvent:
- a `check(cond, msg, kind)` assertion helper that censuses every check as **S**ubstantive,
  **V**acuous (entailed by the base hash), or **T**autological (readback of its own write);
- `runs()` / `rec()` helpers for byte-run and LERP-record diffing;
- the CRC trailer is located **generically, content-derived via `V53.owning_block`** — never
  hardcoded to a fixed address;
- an `independent_rebuild(base)` function that re-derives the image directly (hw2-halfword patch +
  generic re-CRC) with **no shared state**, then asserts its SHA-256 equals the built image's;
- the `build()` function sequences: base-image CRC-chain + bootloader-replay verification → apply the
  cave/cal edits → locate and recompute the owning CRC block → re-verify chains → diff against base
  and assert every differing byte is inside the attributed touched-site set → x31 checksum on source
  and RWD → decode the RWD and verify readback CRC → run the independent-rebuild cross-check → print
  the S/V/T census.

A V288 builder for the setpoint-interpolation cave should follow this exact skeleton (same `check()`/
census discipline, same generic CRC-block lookup, same independent-rebuild-with-no-shared-state
cross-check) rather than a bespoke verifier.

---

## Grind history timeline (operator's words, condensed)

- **V38** (first 4× raise): grinding/ratchet appear for the first time — never possible on stock
  (417 < 512 governor floor).
- **V42/V43** (2026-07-20/21): *"Vibration is present in all steering wheel movements driven purely by
  LKAS. When I assist manually via the wheel, it goes away."* — mechanically identified as 21.4 Hz,
  Q ≈ 13.6, base-assist damper zeroed hands-off.
- **V44**: damper opened hands-off (Y[0] raised) to address the above.
- **V50–V52C** (2026-07-22 → 24): broad low-pass on the torque sensor — flown; operator: *"did not fix
  the vibration; clearly changed manual driving feel."*
- **V62/V65** (2026-07-31/08-01): *"Original grinding at 2–5 mph is gone!"* — the kit's first clean
  fix (Kd 2×), 8–42× reduction at 18–22 Hz.
- **V67** (2026-08-02): best-in-kit result — grind #1 AND grind #2 both zero on this drive (LKAS-gated
  Lever B).
- **V87–V90** (2026-08-09 → 11): rebase to V38 + measurement builds; V90 operator: *"grind #1 still
  exists, micro-ratcheting still exists, grind #2 felt on highway curves/lane changes."*
- **V99** (2026-08-13): *"I think it helped with the audible aspect of the grinding, though I'm not
  sure"* — not called fixed; later shown structurally null.
- **V107/V108** (2026-08-27): damper-is-a-relay finding; grinding shifts to *"higher pitch, several
  hundred Hz, 15–40 mph"* plus a new sub-10 Hz oscillation — a DIFFERENT symptom introduced by the
  schedule reshape, reverted in V108.
- **V276–V282** (2026-09-01 → 06, current arc): grind #1 reframed as the **18–22 Hz rate-loop
  crossover resonance** (a different, higher/narrower-band object than the V38-era 21.4 Hz base-assist
  mechanical mode) — r35's "pronounced grind" incident (23:48:21) is a 0.9 s exponential burst, not a
  standing hum. V287 rev 2 (D-clamp 7680) is a partial mitigant (~5 %), explicitly NOT a cure, and the
  record itself says the residual requires the setpoint-interpolation code edit.

⇒ **Open question, not resolved by this pass:** the record shows the *named* grind mechanism has
moved at least twice — the V38-era 21.4 Hz mechanical base-assist resonance (damper-reachable, fixed
by V62's Kd raise and V44's damper-open) versus today's 18–22 Hz rate-loop crossover resonance on V282
(a control-loop artefact of the linearised 6× reference + flat Kp, NOT damper-reachable, NOT
Kd-reachable per the V287 cal-surface-exhausted finding). These may be genuinely different objects
sharing a label, or the same physical mode attacked from different sides across 250 builds — the
record does not resolve which. Flag before concluding "today's grind is the same thing, just
attenuated."
