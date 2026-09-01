# HANDOFF — 2026-09-01 — V276 flew, and the loop stopped damping

**Predecessor:** `HANDOFF-2026-09-01-the-cliff-and-the-fade.md` (V277, built, unflown).
**Status: NO BUILD WAS CUT. Diagnosis only. V278 is designed, costed, and deliberately NOT built.**

---

## The report

V276 was flashed and driven. The operator, verbatim:

> "Amazing authority now on turns as I would like on 6x torque. However, there is now a large, slower
> (2-4 Hz) oscillation when LKAS engaged. This oscillation happens at all tested speeds. Does not
> happen when LKAS disengaged. This oscillation excites itself or happens by itself even on straight
> roads. Only way to stop it is to hold the steering wheel very firmly. After letting go, the
> oscillation comes back."

No rlog yet. Everything below was established without one.

---

## 🛑 THE MECHANISM — the loop stopped providing negative feedback

`E = 32*setpoint - feedback` at `0x29d78`. **E > 0 the lane PUSHES; E < 0 the lane DAMPS.**

Kp, Kd, the forward gain (`0xC6CD0`=5346) and the cap (`0xC61B4`=3072) are ALL byte-identical
V268 → V276. V276 scaled the setpoint AND the feedback clamp by 6, preserving Honda's 1.395 ratio —
so the rate at which E can go negative moved OUT OF PHYSICAL REACH.

**In raw counts** (`E<0` needs `feedback > 32*setpoint_ceiling`; slot 1, ceiling 172 — no unit factor):

| K | threshold | matching `0xC62E6` |
|---|---|---|
| 1 (stock) | 5,504 | 7,680 |
| 1.5 | 8,256 | 11,520 |
| **2** | **11,008** | **15,360** |
| 2.5 | 13,760 | 19,200 |
| 3 | 16,512 | 23,040 |
| **6 (V276, on the car)** | **33,024** | **46,080** |

Median achieved rate ~6,668 raw. **Stock crossed over routinely (that is the "backs off mid-corner"
weakness). V276 never crosses at all.** A P/D controller that can never change sign is a `sign(error)`
RELAY, and a saturated relay driving an underdamped plant is the textbook self-sustaining limit cycle —
which is exactly why a firm grip stops it and letting go restarts it.

Corroborated independently: **P now reaches its clamp in ALL 28 slots at full demand vs 97.4% on V268.**

### The fix is a WINDOW, not a dose

The crossover must sit **between normal driving and the OSCILLATION's peak rate**:

- below normal driving → the lane backs off mid-correction (stock's failure);
- above the oscillation's peak → never damps (V276's failure);
- **between → pushes normally AND damps the oscillation.**

`K=2` (11,008) and `K=2.5` (13,760) both sit inside it. **Peak torque is untouched at every K** —
`0xC61B4`, `0xC6CD0` and the map's Y-ceiling are all frozen.

---

## 🛑 2-4 Hz IS NOT OURS, AND IT IS NEW

**Not ours:** both in-loop poles (output lag 5.05 Hz, feedback lag 16.5 Hz) plus the 1-sample/1 kHz
transport delay supply only **−28.5° @ 2 Hz, −41.0° @ 3 Hz, −52.0° @ 4 Hz** — 128–152° short of −180°.
The frequency is a MECHANICAL resonance (column / torsion-bar / rack), which this kit has never
characterised. We cannot notch it; we can only stop feeding it.

**New:** the whole cached corpus was re-scored at 2-4 Hz (35 routes, V74→V122 + stock).
`excess24` (band power ÷ the power-law baseline through its own 1.0–1.6 and 5–6 Hz shoulders) has
median **0.83** — the band carries LESS than its shoulders predict, on every build ever flown.
**No build in the corpus has a 2-4 Hz mode.** Within-route bootstrap 95% CI spans 2.15×, which is what
sets the pre-registration's 2.5 threshold.

⚠ **The cached corpus stops at V122** — blind over 154 revisions. Stated, not hidden.

⭐ **The band was never a blind spot in the TRANSFORM** (100 Hz, Welch nperseg 512, 0.195 Hz bins, no
high-pass and no detrend anywhere in `score/`) — **only in the BAND SET.** ~50 scorers start at 5–6 Hz.
2-4 Hz has been the kit's normalising CONTROL band for a year (`lo_2_4`, `CTRL`), and
`studies/mixer/delivered_command_is_sensor_fed_not_commanded.py` says outright that **2-4 Hz is the
LKAS lane's own band.**

**V101 hypothesis REFUTED, cleanly.** V101 puts **83.2%** of its engaged 1–40 Hz rate energy into
22–30 Hz and is below corpus median in every other band; its 2-4 Hz fraction is among the lowest in the
corpus. The original 22–30 Hz filing was right. ⊕ But V101 has the corpus's tightest command↔rate
coupling with an ORDINARY `excess24` — so **8× gain raised coupling without creating a 2-4 Hz mode**,
and if V276 shows high coherence AND high excess, that combination is genuinely new.

---

## Corrections of record

1. 🛑 **THE LKAS CEILING IS 2505, NOT 3072. My own "correction" last session was WRONG.**
   `0xC61BE` = 15360 is a symmetric clamp at `0x2a13e-0x2a162` whose output reaches the forward gain at
   ~unity (the readout `(state_old+state_new)>>5` cancels the output lag's 15.84 state gain to 0.990):
   `15360*5346>>15 = 2505`. `0xC61B4`=3072 clamps the COMBINED base+LKAS sum, not this lane.
   **Triple-confirmed:** my own disassembly; `osc-damp` this session; and
   `reference_accord_c61be_c61b4_c61b2_diagnostic_cluster_not_lkas_ceiling` from **2026-08-26**, which
   cross-validates via stock `15360*891>>15 = 417` against the independently recorded "stock V9 max
   LKAS command was 417". **The kit already held this fact and I contradicted it —
   `feedback-search-the-kit-before-naming-a-cause`, again.**
2. **`0xC61BE` has a SIGN-EXTENSION DEFECT on its POSITIVE saturation branch.** `0x2a146` is `ld.h`
   (sign-extend) while the other three reads are `ld.hu`. **It must stay < 32768** or maximum positive
   demand inverts to maximum negative torque.
3. **Raising `0xC61BE` is a SECOND-STAGE lever, NOT this build's fix.** It raises delivered LKAS torque
   ~22.6% (2505 → the 3072 cap) INTO an active limit cycle; it does NOT restore linearity, because P's
   own clamp `0xC61BC` is ALSO 15360; and D cannot use the headroom, saturating at `|dErr|>20`/tick
   (~2.9% of the error range at 3 Hz). The agent memory asserting "costs zero authority" was corrected
   in place.
4. **`0xC9A88` is a POINTER FAMILY**, byte-identical V112→V277. V276's ×6 landed in the pointed-to
   records at `0xE4000`–`0xE8105`. And **V276 is not two cells** — it carries 4 bytes of code
   (`0x55DF2-3` / `0x55E0E` / `0x55E10`), the selector tap inherited from V273.
5. **Gate (B) (`0xCBAE4`/`0xCBBC4`) is INERT in the override case.** `r25 = (gp-0x6803 == 2)` at
   `0x29a80`; when true, both `cmovne`s select the grab-rate curves, which for slot 1 are
   `Y=[255,255,255,255,255,205]` — flat. **V277 omitting these tables was CORRECT.** Gate (A), the
   cliff, is the only live nonlinearity in this loop.
6. **`FUN_0002a30e` is UNREACHABLE** — four independent nulls (callers, xrefs, a raw `jarl disp22` scan,
   a dispatch-table word scan). It is the DTC-0x49 state machine and carries neither gate.
7. **`gp-0x4f60` is the RAW torsion-bar sensor** with NO dynamic filtering and NO motor-reaction
   compensation in its producer chain, so the operator's "LKAS drives its own torque feedback" loop is
   STRUCTURALLY CLOSED. `FUN_0007f300` is a static zero-offset bias clamped at ±0x134 — **NOT** the
   phase-correction filter inherited memory claimed. Corrected in place.
8. **The 5 Hz PID-output lag** is `y[n]=(992*y[n-1]+507*x[n])>>10` at `0xC63EC`/`0xC63EE`. ⚠ **DC-gain
   trap: the STATE's DC gain is `b/(1024-a)` = 15.84; moving the corner at constant gain requires
   holding that ratio.** Costed and ready, NOT proposed as primary — it buys ~21° at 2 Hz against a
   130–150° deficit.
9. **The variant selector fact was ALREADY KNOWN on 2026-07-18** in `build_v38_tva.py`
   (`SETPOINT_REACHABLE_SELECTORS = (0,1,3,4,6,7,8,9)`) and was lost, then re-derived as new. The
   dead-slot lineage re-check is **DONE: nothing retracts** — no build before V273 touched those banks.
10. 🛑 **DEFECT, reported not fixed: `rlog-tools/studies/impedance/rez_by_band_all_routes.py` globs only
    ONE of the TWO cache roots**, silently omitting ~12 routes (V74–V89) from its Re(Z)/f0 corpus
    statistics. Several standing findings rest on that scorer. **Worth a sweep.**

---

## What V278 is, and why it is NOT built

**Class:** a REDUCTION of a live gain. Only the third in ~240 builds, and the first in response to a
symptom the build itself created. The two prior reductions were V93/V94 — *"made the stuttering and
grinding worse, by a lot."* That is not an argument against it, but it belongs on the drive card.

**Held open deliberately, per the DO-NOT-CUT-HASTILY doctrine:**

- **K is sized by the operator's own log.** `gp-0x6a56` is already on CAN `0x18F` bytes 2–3 at 100 Hz,
  free, on the car now — so the V276 rlog contains the oscillation's actual peak rate, the window's
  upper edge MEASURED rather than assumed. The channel is magnitude-clamped at ±12000 raw, which helps
  either way: a flat-top already exceeds K=2's 11,008 crossover.
- **The discriminator decides whether V278 should exist at all.** Pre-registered in
  `rlog-tools/studies/osc-2to4/PREREG-V276-2to4Hz-READ.md`, 8 tests, thresholds fixed BEFORE the log,
  with an explicit **"do not build V278"** verdict condition:
  - `cmd_excess24 ≥ 2.5` AND `coh24 ≥ 0.8` → openpilot OUTER loop → **comma-side fix, V278 is the
    wrong lever**;
  - `cmd_excess24 ≤ 1.3` while `rate_excess24 ≥ 2.5` → EPS INNER loop → V278 exists;
  - both ≥ 2.5 with `coh24 ≤ 0.5` → ambiguous, instrument before building.
- **Telemetry is not free.** `sign(E)` (`gp-0x6cf8`) and `P-at-clamp` (`gp-0x6b32`) are both unread gp
  cells, but the CAN-427 packer calls an `abs()` helper and **RECTIFIES** — it structurally cannot carry
  a sign bit without a restructure. That is a CODE change needing GATE 1 / GATE 2, not a cal edit.

---

## Scripts that survive

- `rlog-tools/studies/osc-2to4/PREREG-V276-2to4Hz-READ.md` — the pre-registration.
- `rlog-tools/studies/osc-2to4/band_excess_2to4_speed_matched.py` — the primary instrument.
- `rlog-tools/studies/osc-2to4/rescore_2to4hz_all_routes.py` — raw levels (⚠ regime-confounded).
- `rlog-tools/studies/osc-2to4/v101_recheck_and_noise_floor.py` — V101 re-check + bootstrap floor.

## Safety

**Nothing was flashed. No CAN message and no UDS read was sent at any point.** V277 remains built and
unflown, and it does NOT address this symptom — it carries V276's ×6 forward and would inherit the
oscillation.
