# HANDOFF — 2026-07-14 (later) — V36 dash-lights regression root-caused; V37 built (DTC-0x49 disabled)

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **STOCK analysis program = `code.bin`**
(Ghidra program name `code.bin`, flat base 0 → address==file-offset; `gp=0xFEDF8000`, `tp=0xBF000`).
Openpilot = operator's **StarPilot** fork on a **comma 4**.

**Builds on** `HANDOFF-2026-07-14-v36-debounce-sm-root-cause.md` (V36 = V31 + the 7 debounce-SM cals → unsigned
max, disabling `STEER_STATUS=4`). This session: operator **flashed V36**, hit a new fault, and we root-caused
it (Ghidra: own decompile + a firmware-codepath-tracer subagent, every load-bearing claim cross-checked) and
**built V37**.

---

## 0. One-line state
**V36 flashed fine but, mid-drive, throws a burst of dashboard warning lights + drops LKAS (comma) while base
power steering keeps working.** Root cause: disabling `STEER_STATUS=4` silently removed an **in-code interlock**
that was the only thing keeping a SECOND counter — the **DTC-0x49 fail counter `gp-0x6758`** — from ever
saturating. **V37 = V36 + raise `0xC64B8` (112→0xFF)** so that counter can never increment ⇒ DTC 0x49 can never
fire. Cal-only, 49/49 CRC, **UNFLASHED**.

---

## 1. The symptom (operator report)
Flashed V36. Halfway through a drive a **bunch of dashboard error lights flash** and **LKAS through the comma
stops working**; the **steering wheel (base assist) stays functional**. Did not occur on stock or any prior
flashed build (V30/V31P/V31P-V2). ⇒ a NEW regression introduced by V36. (V36's only delta vs the
flashed-and-fine V31P-V2 lineage is the 7 debounce cals → max; every V31 cal is identical.)

## 2. Root cause — V36 unmasked DTC 0x49 by removing an in-code interlock (instruction-verified)
The live debounce SM (inlined in `m_steer_torque_arbitration`) runs **two counters off the same torque channel
`gp-0x682f` on the same tick**:

| | Counter A `gp-0x6757` | Counter B `gp-0x6758` |
|---|---|---|
| Produces | `STEER_STATUS=4` (gentle EME) | `STEER_STATUS=7` + `FUN_00016de6(0x49,1,1,1)` = **DTC 0x49** |
| Increments on | torque>112 OR rate>1600 (+ combined tiers) — cals **V36 maxed** (`0xC64B4/B5/B6/B7`,`0xC61C0/C2/C4`) | torque > **112** — `cal 0xC64B8` (**V36 left stock**) |
| Trips after | **5** cycles (seed `0xC64E2`=5) | **100** cycles (`0xC64E0`+`0xC64E1` = 50+50) |
| Saturation site | `0x2928e` fire | `0x291b8` check → `0x291ca jarl 0x16de6` |

**The interlock (the bug):** every branch that sets/holds `STEER_STATUS=4` also executes `gp-0x6758 = 0` (live
stores at `0x29292`, `0x292b2`, `0x2930e`). In stock, sustained loaded-curve torque trips Counter A at cycle 5,
and the `STEER_STATUS=4` fire + its ≤100-cycle hold **zero Counter B every cycle** → Counter B never reaches 100
→ **DTC 0x49 was structurally unreachable.** V36 maxed Counter A's thresholds → `STEER_STATUS=4` never fires →
those `gp-0x6758=0` writes never run → Counter B free-runs on the untouched `torque>112` gate → 100 cycles
(~1 s @ ~100 Hz) → **DTC 0x49 + `STEER_STATUS=7`**. "Halfway through a drive" = the first hard loaded curve held
~1 s.

**Symptom mapping:** dash lights = the EPS confirmed-DTC (`FUN_00016de6` writes a per-DTC descriptor table at
`tp-0x72a8`); LKAS drop = openpilot treats `STEER_STATUS=7` as a permanent fault (`steerFaultPermanent`, repo
`HANDOFF-2x`) → zeroes `latActive`; base assist survives because 0x49 is a LKAS/assist-monitor DTC, not a
hardware shutdown. (The exact in-firmware MIL/cluster aggregator that turns a stored 0x49 into the specific
cluster lights was NOT traced — the DTC-set + `STEER_STATUS=7` broadcast are verified; the cluster mapping is the
standard downstream. Low priority.)

## 3. `0xC64B8` blast radius — why "Option A" needed vetting (operator-accepted the one live side effect)
`0xC64B8` is **NOT solely the DTC gate.** Whole-image scan (185,116 instrs): 6 direct byte reads (all `ld.bu`);
**no absolute-pointer load**; **no wide `ld.hu`/`ld.w` load spans the byte** (neighbours `0xC64B4/B5/B6/B7` are
all single-byte reads):

| Site | Live? | Role |
|---|---|---|
| `0x2920a`, `0x2921c` | ✅ live | DTC counter-B gate → **intended disable** |
| **`0x29a78`** | ✅ **live** | **torque-arb branch** `torque>112 ? high-torque cutoff : full arb-curve interp` (dead twin `FUN_0002a93a` sets the main arb term `iVar13=0` in the `>112` branch) |
| `0x2a3ec`,`0x2a3fe` (`FUN_0002a30e`), `0x2a97a` (`FUN_0002a93a`) | ☠ dead | inert |

⇒ Raising `0xC64B8`→255 also flips the **live** arb branch at `0x29a78` for torque in (112,255]: the arb no
longer takes its high-torque cutoff, it runs the full interpolation instead — a **drivability change in the
loaded-curve regime**. **Operator reviewed and accepted this** (2026-07-14). No clean cal-only lever avoids it:
the increment gate IS the shared `0xC64B8`; the saturation cals `0xC64E0/E1` only *delay* the DTC (byte counter
can still reach a raised threshold), so they can't guarantee-disable it. A side-effect-free alternative would be
a **code edit** (neutralize the counter-B saturation→DTC branch), which the operator declined in favor of the
cal-only Option A.

**Correction of record — both standalone functions are DEAD.** `FUN_0002a30e` AND `FUN_0002a93a` each have
**0 callers, 0 xrefs, 0 data-table pointers** (byte-pattern searched both LE entry pointers). Their logic is
**inlined live in `m_steer_torque_arbitration`** (called every tick by `w_steer_control_task@0x2214a`): the
debounce SM at `0x29120–0x2931e`, the arb curve around `0x29a5c–0x2a2xx`. Almost certainly a compiler inlining
artifact (out-of-line copies emitted then not dead-stripped; register-renamed but logically identical). **This
supersedes the V36 handoff / CLAUDE.md framing that `FUN_0002a30e` is "the status producer"** — that standalone
copy never executes. (`gp-0x6758` is the DTC-0x49 fail counter; an older tracer memory mislabeled it a "ramp
gain accumulator.")

## 4. V37 — BUILT, verified, UNFLASHED
**Build:** `analysis-2020accord/build_v37_tva.py` →
`../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V37-V36-DTC0x49-OFF-torqueMax255-rateMax65535-dtcGate255-0x13000-0x100000.rwd`
(+ `../accord-firmware/analysis-2020accord/_v37_plain_image.bin`). **V37 = V36 (all cals unchanged) + `0xC64B8` 112→`0xFF`.**
`gp-0x682f` is a byte ≤255, so `0xFF < gp-0x682f` is never true ⇒ Counter B never increments ⇒ never saturates ⇒
DTC 0x49 can never fire. (`STEER_STATUS=4` stays disabled from V36, so nothing re-arms the interlock; `gp-0x6758`
simply sits at 0.)

**Verification (build asserts + independent fresh diff of `../accord-firmware/analysis-2020accord/_v37_plain_image.bin` vs stock):**
- All intended cals correct: `0xC64B4/B5/B6/B7/B8` = `0xFF`; rate cals `0xC61C0/C2/C4` = `0xFFFF`.
- Left stock confirmed: `0xC6312`=320; counter-B saturation cals `0xC64E0/E1`=50/50; seeds `0xC64DF`=100,
  `0xC64E2`=5.
- **Cal-only proven:** both FSM code ranges `[0x29000,0x29400)` and `[0x2a30e,0x2a508)` byte-identical to stock
  (0 diffs); all three live `0xC64B8` reader instructions (`0x2920a`,`0x2921c`,`0x29a78`) byte-untouched.
- **Cleanest proof:** V37 vs V36 = **exactly 5 bytes** — `0xC64B8` (1B) + its CRC `0xC6FFC` (4B). (The `0xC4FFC`
  CRC is unchanged because `0xC64B8` isn't in that block, as predicted.)
- 42 total byte-diffs vs stock (V36's 41 + `0xC64B8`); **49/49 CRC OK**; round-trip `decode==patched`.

## 5. Trade-offs & open questions
- **Trade-off 1 (accepted):** genuine DTC-0x49 fault detection is now disabled — a real EPS torque-monitor fault
  would no longer set 0x49 / `STEER_STATUS=7`.
- **Trade-off 2 (accepted):** the live arb high-torque cutoff at `0x29a78` is defeated for torque in (112,255].
- **Deeper open item (unchanged from V36):** the actual **LKAS-motor-zeroing instruction** of the felt gentle
  EME (the "sharp slight wheel-straightening mid-turn") is **still unlocated**. V37, like V36, is a
  discriminating experiment on the DTC/`STEER_STATUS` side — it does not by itself prove the *felt* cut is fixed.
- Other open (low priority): the in-firmware MIL/cluster aggregator for a stored DTC; `gp-0x682f`'s source `r15`;
  `FUN_0002a30e`'s indirect caller / exact SM task rate (to convert cycle counts to ms precisely).

## 6. NEXT SESSION
1. **Flash V37** (operator names file + bus; iron rule; kill openpilot/pandad first). File:
   `39990-TVA,A160-V37-V36-DTC0x49-OFF-torqueMax255-rateMax65535-dtcGate255-0x13000-0x100000.rwd`.
2. **Drive a sustained loaded curve** (the regime that tripped V36). **Verdict A:** no dash-lights / no LKAS
   drop → the DTC-0x49 regression is fixed. **Verdict B:** watch whether the felt **wheel-straightening** (the
   original gentle EME) persists — if it does with no `STEER_STATUS=4`, the felt assist-drop is a separate path
   (→ hunt the motor-zero, open item).
3. If discriminating telemetry is wanted, log the **values** of `gp-0x682f`, `gp-0x6758`, `gp-0x6757` (not the
   old gate bits).

## 7. Iron rules (unchanged)
- **No CAN/UDS send or flash without the operator naming the exact file/payload + bus; repeat it back.** V37 is a
  STUDY ARTIFACT until then.
- Analyze STOCK `code.bin` only (never a `_v*_plain_image.bin` except to *verify a build*). r2 default `v850`
  mis-decodes V850E2 — use `v850.gnu` or Ghidra.
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`).

## 8. Artifacts this session
- `analysis-2020accord/build_v37_tva.py`, `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V37-...rwd`,
  `../accord-firmware/analysis-2020accord/_v37_plain_image.bin`.
- Memories: `v37-dtc0x49-fix-and-0xc64b8-blast-radius` (new); `v36-debounce-sm-root-cause-and-build`, `MEMORY.md`
  (updated); repo `memory/MEMORY_CONSTELLATION.md` era note extended.
