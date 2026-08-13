# Memory Constellation — 2020 Accord EPS Firmware Project

**Companion to `MEMORY.md`.** Where MEMORY.md is the index (*what is known*), this is the synapse map (*how the known things relate*). Read after MEMORY.md, before substantive work, on session resume. Update incrementally; never redraw freehand.

> **2026-07-17 cleanup note:** this file was trimmed to Accord-only content — the project's earlier Civic (`39990-TBA-C120`), radar (`36802-TBA-A160`), and Acura RDX (`39990-TJB`) work (and their memory nodes) were removed from the repo. Most of what's below predates that split and was written when this constellation covered all four platforms; the surviving eras and clusters are the ones whose memory nodes are still on disk. `MEMORY_CONSTELLATION.svg` (the old multi-platform colored diagram) was deleted rather than hand-patched — regenerate a new one from the tables below if a visual is wanted.

---

## ASCII abstract

```
                ┌─ PROJECT STATE ─────────────────────────────┐
                │ ★ accord-torque-mod-v0 — V39 latest,        │
                │   V38 FLASHED fault-free; V39 UNFLASHED     │
                └─────┬────────────────────────────────────────┘
                      │ informs all build decisions ↓
    ┌─────────────────┼─────────────────┬───────────────────┐
    ▼                 ▼                 ▼                   ▼
┌─ ACCORD TVA/V850 ┐┌─ ACCORD EME/  ─┐┌─ FEEDBACK ──────┐┌─ V850 TOOLING ─┐
│★v850-sa-algorithm││  TORQUE-MOD    ││  rigorous-      ││ tva-cipher-    │
│★sa-secret-per-   ││  MECHANISM     ││   validation    ││   operand-     │
│   mcu-family      ││★corridor-      ││★operator-lived  ││   order        │
│  rizin-ghidra-    ││   lockstep     ││   experience    ││ tva-bootloader-│
│   v850-quirks     ││★override-snap- ││ (overrides      ││   crc-scheme   │
└──┬────────────────┘│   sm           ││   analyst recs) │└──────┬─────────┘
   │                 │★soft-eme-bound-││ dont-kill-long- │       │
   │                 │   arm-gating   ││   agents-early  │       │
   │                 │★lkas-delivery- ││ tight-agent-    │       │
   │                 │   and-governor ││   briefs        │       │
   │                 │★pointer-base-  │└─────────────────┘       │
   │                 │   audit        │                          │
   │                 │  eme-lever-    │                          │
   │                 │   semantics    │                          │
   │                 └────────┬───────┘                          │
   │                          │                                  │
   └──── pre-req for ─────────┴──── depends on ──────────────────┘
         all Accord firmware-level analysis
```

## Legend

| Marker | Meaning |
|---|---|
| `★` | Load-bearing node — drives downstream decisions or closes whole question classes |
| `○` | Supporting/confirmed node — true and useful but not structural |
| `→` | Derivation / influence (directional) |
| `↔` | Bidirectional relationship |
| `╌╌→` | Tentative / inferred edge |

## Cluster definitions

| Cluster | Members | Role |
|---|---|---|
| **PROJECT STATE** | accord-torque-mod-v0 ★ (the rolling V0→V39 build log) | Current Accord car state; what's flashed; what's pending |
| **ACCORD TVA / V850 PLATFORM** | v850-sa-algorithm-tva ★, sa-secret-per-mcu-family ★, rizin-ghidra-v850-quirks | SecurityAccess + tooling facts for the V850E2 platform (Era 4) |
| **ACCORD EME / TORQUE-MOD MECHANISM** | corridor-lockstep ★, override-snap-state-machines ★, soft-eme-bound-arm-gating ★, lkas-delivery-and-governor ★, pointer-base-audit ★, driver-override-plausibility-eme ★, eme-lever-semantics, corridor-vs-envelope, lerp-envelope-gating, lerp3-gp3574-chain, arbitration-limit-family, lkas-window-ceiling, demand-aggregator-pipeline, lkas-torque-path, databin-tp-base, gp-base-fedf8000, v22-float-monitor-2x-cave, can-single-fcn0-external-gateway, uds-did-read-surface-a160, sub3mph-lkas-openpilot-gate | The full body of disasm-verified findings about how the Accord EPS arbitrates, gates, and delivers LKAS torque — built up build-by-build from V11 through V39 |
| **V850 TOOLING / INFRASTRUCTURE** | tva-cipher-operand-order ★, tva-bootloader-crc-scheme | The .rwd container cipher + bootloader CRC scheme that every Accord build/flash script depends on |
| **FEEDBACK** | rigorous-validation, operator-lived-experience-overrides-analyst-recs ★, three-senses-of-rebuilt, dont-kill-long-agents-early, tight-agent-briefs, direct-no-hedging, verify-subagent-claims, short-installer-branch-names, rwd-output-dir, rwd-output-beside-script, svd-grounding | How to work with the operator + how to run multi-agent sessions on this project |

## Load-bearing tier (★)

These nodes change how the workspace is thought about. Adding/removing/reframing any of them propagates.

1. **v850-sa-algorithm-tva** — verified SecurityAccess algorithm + Group C constants for the V850 platform; unblocks any V850 TVA work
2. **sa-secret-per-mcu-family** — Honda's per-MCU-family SA secret structure; tells you what to expect for any new Honda EPS chassis at the SA layer
3. **accord-torque-mod-v0** — current Accord project state; gates every flash decision (V38 flashed fault-free; V39 built/unflashed)
4. **operator-lived-experience-overrides-analyst-recs** — generalizable agent-collaboration pattern; when the operator reports how the car feels, that overrides abstract analyst concerns
5. **tva-cipher-operand-order** — the on-ECU decryptor formula (`((c^0xBF)^0x10)-0x9E`), proven by the V9b flash; every `.rwd` build/decode depends on getting this right
6. **corridor-lockstep** — the wall = 3-way max(corridor, IIR, boost) lockstep model that every soft-EME build since V26 has to respect
7. **override-snap-state-machines** — the 3 authority-gated SMs that produce the hard-override EME snap; arming gate `0xC6422`
8. **soft-eme-bound-arm-gating** — per-arm gating model (corridor=driver-override arm, boost=authority-gated arm) that explains why V30 still soft-EME'd and why V31's boost floor fixes it
9. **lkas-delivery-and-governor** — the full delivery chain from arbitration output to the motor, closing the "does 2x actually reach the wheel" question (V14 confirmed it does)
10. **pointer-base-audit** — resolves `tp(app)=0xBF000` (not `0xF8000`) via all three build instructions; every `0xC6xxx` cal address depends on this being right
11. **driver-override-plausibility-eme** — the 2x-gain-amplified column-torque-sensor plausibility dropout; safety-relevant for any gain-only build

## Cross-cluster edges (the synapses)

| Edge | Direction | Rationale |
|---|---|---|
| v850-sa-algorithm-tva ↔ sa-secret-per-mcu-family | bidirectional | Same finding from different angles: V850 uses Group C; the per-family pattern is the framing, the TVA constants are the instance |
| accord-torque-mod-v0 ← v850-sa-algorithm-tva | depends on | The whole build program requires the flashable SA handshake first |
| accord-torque-mod-v0 ← rizin-ghidra-v850-quirks | depends on | Tooling-bug awareness was load-bearing for arriving at the verified SA algorithm correctly |
| accord-torque-mod-v0 ← tva-cipher-operand-order | depends on | Every `.rwd` the build scripts produce depends on the correct cipher |
| accord-torque-mod-v0 ← pointer-base-audit | depends on | Every cal address referenced by every build (V11 onward) resolves through `tp=0xBF000` |
| accord-torque-mod-v0 ↔ operator-lived-experience-overrides-analyst-recs | bidirectional | Road tests validate/falsify each build; on-car results repeatedly overturned analyst-side models (V25→V26→V27→V28→V29 ladder) |
| corridor-lockstep ↔ soft-eme-bound-arm-gating | bidirectional | soft-eme-bound-arm-gating is the per-arm refinement of corridor-lockstep's 3-way max/min wall |
| corridor-lockstep ↔ override-snap-state-machines | bidirectional | Two distinct EME mechanisms on the same command path — soft (integrator wind-up, no DTC) vs hard (authority-gated SM snap) |
| lkas-delivery-and-governor ↔ pointer-base-audit | bidirectional | The delivery chain's cal addresses only resolve correctly once tp=0xBF000 is established |
| driver-override-plausibility-eme ↔ eme-lever-semantics | bidirectional | eme-lever-semantics is the disasm-grounded vocabulary (slew/deadband/ramp/override-SM) that explains which lever actually causes the plausibility-dropout EME |
| {dont-kill-long-agents-early, tight-agent-briefs} | bidirectional | Two sides of multi-agent operation — prevention (tight briefs) and mid-flight (refine not kill) |
| three-senses-of-rebuilt ╌╌ rigorous-validation | complementary | Framing-side equivalent of build-side rigor; different layer, same discipline |

Most other edges between ACCORD EME / TORQUE-MOD MECHANISM nodes are called out inline within each era entry below (the temporal log doubles as the edge log for that cluster — it was never promoted to this table).

## Temporal layers

- **Era — TWO HARD FAULTS, AND THE DAMPER WAS NOT IN FORCE FOR ONE OF THEM (2026-08-06, late)** — V75 faulted
  engaged at a stoplight launch; **V74 then faulted DISENGAGED, over a bump, with the FactorC/FactorE edits
  byte-stock in the active mode (24)**. ⇒ `k* ∈ (0.580, 1.580]` is **VOID** and no build in this lineage has
  demonstrated safety. The surviving causal thread is `0xC63A0` — a mode-proof weight raised at V72, armed by
  V74, sitting inside a loop that closes *inside the firmware*. **V77 reverts it, single variable.**
  🛑 **Full chain, evidence and refutations: see the dated section "2026-08-06 — Era: the LOOP-GAIN chain, and
  BOTH hard faults" at the end of this file.** Key memories: [[accord-v74-hard-faulted-in-manual-over-a-bump]],
  [[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]], [[accord-descriptor-bit13-is-the-fault-fingerprint]],
  [[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]], [[accord-v77-built-c63a0-revert]].

- **Era — V37 FLASHED: GENTLE EME RESOLVED ON-CAR + full CAN→MOTOR PSEUDOCODE MODEL (2026-07-14, later)** — the operator **flashed V37 and reports the gentle EME is RESOLVED** (the felt sharp wheel-straightening mid-turn is gone). This is the decisive outcome of the V36→V37 discriminating experiment: since disabling the `STEER_STATUS` debounce SM (the `gp-0x682f` torque / `param_1` rate condition) eliminated the felt cut, the gentle EME **is** driven by that same debounce condition. New artifact: **`analysis-2020accord/eps_lkas_chain_model.py`** — a runnable, address-free Python pseudocode of the entire LKAS chain (CAN 0xE4 → setpoint → arbitration+inlined SMs → limit/distribute/mixer/gate → soft-EME shaper → FOC → TSG20 PWM), parameterized for **V9 (stock) / V31 (soft-EME fix) / V37 (gentle-EME fix)**; memory addresses live only in per-function comment blocks, cals are named constants. Built + verified this session by 3 `firmware-codepath-tracer` subagents against stock `code.bin`.
  - **Execution model corrected/confirmed (Ghidra):** the firmware runs a small **RTOS** — steering/decider tasks are dispatched indirectly off a TCB-like table (~`0xbb900`), returning via `FUN_000847be` (`eiret`), NOT from a main loop. **Base tick = OSTM0** (`FUN_00014c5c` compare `0x1387F`=79999 → ~80000-cycle period → *likely* 1 kHz/1 ms, but the OSTM0 input clock is unconfirmed). **`m_steer_torque_arbitration` (+ its inlined debounce/DTC SMs) is PHASE-GATED** — call @`0x22522` guarded by `andi 0x930` on a 16-phase counter → runs on 4 of 16 phases, **refuting "runs every tick"** (so the debounce "5 cycles" / DTC "100 cycles" tick at a divided sub-rate). Decider/deliver run from sibling RTOS task `FUN_00022ca0` (`jarl 0x413ae`/`0x3d4a2`). **FOC + PWM share ONE EI trampoline `FUN_0001492a`** dispatching on EIIC: `0x600`→`FUN_0006404c` (ADC-complete → Park/Clarke/PI/SVPWM `0x71272`), `0x970`→`FUN_00061614`→`FUN_0006c5ce` (writes TSG20 CMPU/V/W `0xFFFFCCB0/B4/B8` = MOTOR, byte-exact). PWM carrier Hz + CAN-RX EIIC entry remain OPEN.
  - **`gp-0x67a4` ENABLE gate CORRECTED — likely a second dead gate.** It is a *producer* FSM (writes `gp-0x67a4`∈{0..5} @`0x2b51e`) with **zero found readers** of `0xFEDF185C`; the long-assumed "ENABLE∈{2,3} else LKAS=0" *consumer* gate is unsubstantiated — the same dead-gate pattern as `gp-0x6809`. Do NOT anchor an ENABLE cut on it.
  - **Steering-torque sensor identity refined:** the physical wheel-torque is read via **hardware Timer Array Unit TAUA0 capture regs (`0xFFFFC400`)** → `FUN_00061ca0`→`FUN_0006195e` (float-scale from an option-reg trim) → 3 channels `gp-0x4e8c/8a/88` — **NOT raw ADC coils**. Plausibility `FUN_00062948` (3 raw vs 3 ref, fault bits `0x20/40/80`), voter `FUN_00041eec` (MAX `gp-0x6a62`, AVG `gp-0x6a5e`) and rate `FUN_0003f776` (`gp-0x6a60` = |clamp(angle-rate,±12000)|, confirmed a RATE not a torque) all byte-confirmed; the `0xFFFF` invalid-sensor sentinel is consumed live by the decider.
  - **Command chain byte-reconfirmed:** setpoint `×−4` + `±0x4000` clamp + `0x1f4`=500-tick timeout (`FUN_00052676`); mode/gear LERP pointer arrays `0xCB844`→`0xE4180..`; gain `0xC646C`=891, clamps `0xC61B2/B4`=512; distribute/mixer/gate cascade (±0x4000/±0x2800/±0x384/±0x4E20, gate `|x|≤0x2800?x:0x7FFF`→`gp-0x6afe`=`0xFEDF1502`); soft-EME shaper `s_motor_torque_rate_shaper` (integrator `gp-0x3570`, 3-way bound, corridor gate `0xC6156`=9216, authority `0xC61DA`=1092, SM2 `0xC6422`, SM3 `0xC61DC`, ±0x2000 out `gp-0x6b98`) all address-exact.
  - **Two CONFIRMED anchors (operator calibration):** only the CAN-0xE4 LKAS torque input and the steering-wheel torque sensing are ground-truth; everything else is Ghidra-static (VERIFIED) or INFERRED/OPEN, labelled as such in the model.
  - **Last updated: 2026-07-14 (V37 flashed — gentle EME resolved).**

- **Era — GENTLE-EME ROOT CAUSE RE-LOCATED / V36 (2026-07-14)** — the V31P-V2 telemetry drive (route 7f) falsified the gate-telemetry approach and a self-verified Ghidra re-trace relocated the root cause.
  - **The gentle EME is a DEBOUNCE STATE MACHINE, not a decider gate.** `STEER_STATUS=4` is set by `FUN_0002a30e` (+ an inline twin in `m_steer_torque_arbitration`) after **5 sustained cycles** (cal `0xC64E2`, counter `gp-0x6757`) of a multi-tier envelope: `torque gp-0x682f>0xC64B4(112) OR rate param_1>0xC61C0(1600)` + two combined torque∧rate tiers (7 cals total). This unifies the torque-vs-rate debate — both feed one debounced machine.
  - **Three corrections of record (self-verified):** `gp-0x6809` (the prior "deliver-flag cut anchor") is **dead code — 0 writers**; the decider `0xC6312`=320 torque-MAX gate fires **~10 Hz benign** and is NOT the trigger (V33 disabled the wrong gate); V31P-V2's 5 gate flags are **non-discriminating** (steady 10 Hz, nothing rises at the cut). `STEER_STATUS=4` is a lagging REPORT; the actual motor-zeroing instruction is **still unlocated** (top open question).
  - **V36 BUILT = V31 + those 7 debounce cals → unsigned max (0xFF/0xFFFF)** → the debounce can never advance. Cal-only, 0 code edits (both FSM byte-identical, independently diffed), 49/49 CRC, UNFLASHED. A **discriminating experiment**: flash → drive the 5:27 section → if the wheel-straightening is gone, root cause confirmed+fixed; if it persists with no STEER_STATUS=4, the assist-drop is a separate path.
  - **Operator anchor:** the felt gentle EME is at **route 5:27** (trigger ~5:26), a **sharp slight wheel-straightening mid-turn** — NOT the STEER_STATUS=4 at 5:31 (a lag / separate event, below CAN angle resolution).
  - **V36 FLASHED → DTC-0x49 dash-lights regression → V37 built (later 2026-07-14).** V36 disabling STEER_STATUS=4 silently removed an **in-code interlock** (`gp-0x6758=0`, executed by every STEER_STATUS=4 branch) that was the ONLY thing keeping a SECOND counter — the **DTC-0x49 fail counter `gp-0x6758`** (saturates at `cal 0xC64E0+0xC64E1`=100 cyc, gate `cal 0xC64B8`=112) — from saturating. With STEER_STATUS=4 gone, sustained `torque>112` free-runs it → **DTC 0x49 + STEER_STATUS=7** → dashboard lights + openpilot LKAS drop (base assist survives). **V37 = V36 + `0xC64B8`112→0xFF** (counter B never increments); cal-only, 49/49 CRC, V37-vs-V36 = exactly `0xC64B8`+CRC (⚠ V37 FLASHED 2026-07-14 → gentle EME RESOLVED on-car; see the newest era note above). **Two corrections:** `FUN_0002a30e` AND `FUN_0002a93a` are BOTH **dead** (0 refs) — the live logic is inlined in `m_steer_torque_arbitration@w_steer_control_task 0x2214a`; and `0xC64B8` is **also a LIVE torque-arb branch @0x29a78** (`torque>112 ? cutoff : full-interp`), a drivability side effect the operator **accepted**. Handoff: `docs/HANDOFF-2026-07-14-v37-dtc0x49-fix.md`.
  - **Last updated: 2026-07-14 (V37).**

- **Era 4 — 2026-05-23 SA-key chain shipped** (Accord TVA / V850 platform opened):
  - New ACCORD TVA / V850 PLATFORM cluster, 4 nodes
  - 3 new feedback nodes: three-senses-of-rebuilt, dont-kill-long-agents-early, tight-agent-briefs
  - 1 new project state node: accord-sa-solved (Accord's project-state node, later folded into accord-torque-mod-v0)
  - rayy's 2020accord branch reached commit `4cf5d3b`: verified V850 SA algorithm + stock TVA-A160 v2 .rwd + adversarially-QA'd eps-update-tva.py flasher
  - Next concrete action: rayy's dry-run validates the SA algorithm on real hardware (no brick risk)

- **Era 23 — 2026-06-03 (latest at the time) — Accord V29/V30 BUILT (cal-only matched corridor) → V30 FLASHED → drove well but residual soft EME on a hard sustained HANDS-OFF turn → V31 BUILT (boost floor)**:
  - **V30 (corridor ×4) was flashed and drives well** — far better than V18, no hard EME (DTC lockstep intact), every previously-EME'ing turn fixed — **except ONE very hard SUSTAINED turn LKAS held hands-off**, which still threw a soft EME. The operator's question ("L+C ≤ 4096, so how?") was right about the arithmetic, wrong about what the command is compared to.
  - **Root cause (walked `FUN_00042af8` on STOCK `code.bin` myself; the V30 build-comment premise "command − corridor" was wrong).** The soft-EME integrator `gp-0x3570` winds up on `(command − bound)`, and the bound is the SAME gated 3-way max/min as the lockstep wall: `r29=MAX(corridor, IIR gp-0x3574>>8, boost)`, `r27=MIN(...)`. **Each arm is conditionally gated:** the **corridor is the DRIVER-OVERRIDE arm** — zeroed when `|gp-0x6bf0 driver-assist| ≤ 9216` (cal `0xC6156`, hands-off) AND when authority `r13≠0` (`0x43114`); **boost** is latched 0 by an SM (`gp-0x3562`, `0x42fb8–0x43016`) once authority > `0xC641E`=16384 for ~20 cyc; **IIR** decays when column velocity ≈ 0. **`r13 = gp-0x6966 = (|gp-0x3570>>15| × 1092[cal 0xC61DA]) >> 10` = the AUTHORITY magnitude** (gates BOTH the corridor and the boost SM). On a hands-off held turn all three collapse (corridor off, boost≈0 no rate, IIR decays) → the 2× command (~1024) winds up the integrator → SM2/SM3 cut. **V30 widened the one arm (corridor) that is gated off in exactly that hands-off regime.** Resolves the contested IIR input identity → **column velocity** (small on a held wheel).
  - **V31 = `build_v31_tva.py` = V30 + a matched FLAT BOOST FLOOR 4096** (int `0xC6768`/`0xC676A`/`0xC676C` 0/1536/2048→4096; float mirror `0xC65C4`/`0xC65C8`/`0xC65CC` 0.0/1.5/2.0→4.0, exact ÷1024). Boost is gated only by AUTHORITY, so at the initiation instant (authority≈0) it's ON and floors the bound to 4096 > worst-case command 3584 → integrator can't wind up → authority never climbs → the boost-zeroing SM never fires → **SELF-STABLE FIXPOINT**. **Lockstep-safe** (the float twin `FUN_00043e44` is a 3-way max/min that INCLUDES boost via float table `0xC65B8` → matched edit keeps monitor delta 0, incl. at rest). **49/49 CRC**, ECU-decode==patched, **31-byte diff / 22 runs, 0 executable code edits**. UNFLASHED (at time of this era; V31's later status is recorded upstream in `project_accord_torque_mod_v0.md`).
  - **★ Method:** sub-agent traces were pinned to STOCK `code.bin` on every call; a tracer flip-flopped + mis-computed on the authority/gate chain, so the load-bearing `r13`=authority and the boost-SM were **walked directly**. The operator's edge-case question ("can corridor AND boost both be off?") surfaced the boost-zeroing SM and forced the fixpoint proof.
  - **Docs:** `docs/HANDOFF-2026-06-03-v31.md`.

- **Era 22 — 2026-06-03 — Accord V27 FLASHED → FAULTED WHEN TURNING → V28 BUILT then ANALYSIS-FALSIFIED → V29 proposed (cal-only matched corridor), UNFLASHED**:
  - **Era 21's V27 prediction was falsified on-car.** Operator flashed V27; it **hard-faulted the instant the wheel was turned** (wheel un-turnable). Same *class* as V26 (a near-t=0 divergence), different quantity.
  - **Root cause (decomp `FUN_00043e44`/`FUN_00042af8` + 4 `firmware-codepath-tracer` passes + algebra + the real stock table bytes) = RESIDUAL-DOUBLING.** V27 doubles the float **twin** (`gp-0x6db0/db8`, trampoline) AND the int **wall** (`gp-0x6af6/b00`, cal `0xC674E`). Both reach **exactly 2×**, and the primary float corridor tables (`0xC6590`/`0xC65A4`) are exact mirrors of the int corridor — so by steady-state math V27 should pass. BUT the watchdog twin is `polarity × max(corridor_mirror, SECONDARY tables)`; secondary `0xC65B8` = X[700,800,1100] Y[0,1.5,**2.0**] lets the twin exceed the corridor by a small **residual R ≤ 5/1024**. The divergence collapses to `R = polarity×max(0, secondary−corridor)`, and 2× **doubles it**: `divergence_V27 = 2R ≤ 10/1024` > the ±5/1024 monitor window the moment `polarity ≠ 0` (any steering) → `FUN_000462e6(0x3f1b)` hard shutdown.
  - **V28 = `build_v28_tva.py` = V27 + a PROPORTIONAL 2× widen of BOTH corridor consistency monitors** so `2R` fits. 49/49 CRC, cipher round-trips, all readbacks pass, UNFLASHED.
  - **★ Tooling lesson:** `search_instructions` (Ghidra parsed-instruction search) **MISSED** the negative-tolerance `movhi 0xbba0` @`0x44646`; a raw **byte scan** of `code.bin` found all 5 ±5/1024 constants. **For exhaustive constant enumeration, trust a byte scan over `search_instructions`.**
  - **★★ CORRECTION (later same day) — V28 falsified-by-analysis; the wall is `max(driver-torque, corridor)`.** Operator asked "is the command compared to the envelope or the corridor?" Settling it overturned the V28 model: `gp-0x6af6 = max(driver-column-torque IIR gp-0x3574 [×256, sar-8 @0x43136], corridor LERP r23 [cal 0x774e])` via `cmovgt r11,r23,r10 @0x4313c → r29 → st.h gp-0x6af6`. So the two monitors are an **INT-vs-FLOAT LOCKSTEP on `max(driver-torque, corridor)`**, NOT a corridor twin. **⇒ V28 is LIKELY BROKEN (do not flash):** demand-dominated turning → twin `2×torque` vs wall `torque` → divergence ≈ FULL torque, not a 5/1024 residual → the tolerance widen CANNOT cover it → faults like V27. **This model finally explains ALL three flashes:** V25 full-lock (corridor-dominated), V26 rest (`0xC6664` envelope offset), V27 turning (demand-dominated). **V29 (proposed, NOT built):** DROP the trampoline AND the tolerance widen; keep V18's GAIN (sits in BOTH lockstep paths); widen the corridor FLOOR by doubling BOTH the int cal `0xC674E` AND the float corridor mirror `0xC6590`/`0xC65A4` (matched, cal-only, monitor intact) = "V26 done right."
  - **Doc:** `docs/HANDOFF-2026-06-03-v28.md` (correction banner at top).

- **Era 21 — 2026-06-02 — Accord V26 FLASHED → HARD-FAULTED AT REST → V27 BUILT (first Accord CODE patch; corrected corridor-twin model), UNFLASHED**:
  - **Era 20's V26 prediction was falsified on-car.** Operator flashed V26; it **hard-faulted immediately on startup, wheel un-turnable** (worse than V25's drive-then-full-lock fault). The V26 premise — "double cal `0xC6664` to match the float corridor twin" — was **wrong on the table identity**: `0xC6664` is **LERP_B**, a velocity *envelope* multiplier, NOT the corridor twin. At rest `lerp_a = 2.0`, so doubling `lerp_b` ADDED a constant **+2.0 envelope offset at every operating point including parked/centered** → watchdog desync from t=0 → DTC `0xF00049` + latched motor-off in ~10 cycles.
  - **The CORRECTED model:** the corridor IS lockstep-monitored, but the **float twins are RAM `lp` (dir1 →`gp-0x6db0`) and `r20` (dir2 →`gp-0x6db8`)**, computed in `FUN_00043e44` as `corridor_mag × float(polarity gp-0x6752)`. BOTH monitors compare twin vs `wall/1024`.
  - **The V24/V25/V26/V27 ladder** (each had only part of the fix): **V24** doubled the float twins only (fault); **V25** widened int corridor only (fault at lock); **V26** widened int + doubled `0xC6664` (wrong table, fault at rest); **V27 = BOTH halves.**
  - **V27 = `build_v27_tva.py`** = V18 GAIN/clamps/ramp + INT corridor ×2 + a **CODE TRAMPOLINE** at the free `0xC4E00` cave doubling the real float twins. `0xC6664` **LEFT STOCK**. **First Accord build to ship a code-section patch.** 49/49 CRC, cipher round-trips; built `../accord-firmware/analysis-2020accord/_v27_plain_image.bin` imported into Ghidra and the trampoline disassembles exactly as designed. UNFLASHED (at time of this era — later flashed and faulted when turning, see Era 22).
  - **★ .bin-discipline lesson (tooling):** stock analysis MUST use `code.bin` — the open `_v22/_v23/_v24` images carry V21–V24 **experimental code edits**. Analyzing the wrong image produced a wrong model AND a confidently-wrong NO-GO. Always `switch_program("code.bin")` + sanity-check `0xC4E00==0xFF`, pin every subagent to it.
  - **Doc:** `docs/HANDOFF-2026-06-02-v27.md`.

- **Era 20 — 2026-06-02 (later) — Accord V25 FLASHED → HARD-FAULTED at full lock → V26 corridor-lockstep fix BUILT, UNFLASHED**:
  - **Era 19's prediction was falsified on-car.** Operator flashed V25, drove ~5–10 ft, hard-right turn out of a parking spot, and the instant the wheel hit full RIGHT lock the EPS shut down + threw a dash fault (DTC 0xF00049).
  - **The load-bearing correction:** the **DIRECTION CORRIDOR IS LOCKSTEP-MONITORED** — computed in BOTH fixed-point integer (walls `gp-0x6af6`/`gp-0x6b00`, fed by cal `0xC674E`/`0xC675A`) AND float (a velocity-indexed LERP over a SEPARATE cal table). A redundancy monitor cross-checks them. V25 doubled ONLY the integer corridor and left the float twin stock → constant desync → DTC, accumulating fastest at full lock.
  - **V26 = `build_v26_tva.py` = V25 + the float-corridor twin ×2** (seven f32 `1.0→2.0`). Restores lockstep exactly. 33 bytes / 19 runs, 49/49 CRC, zero code edits. UNFLASHED (at time of this era — later flashed and hard-faulted at rest, see Era 21).
  - **SM2/SM3 threshold raises are dead as a lever** (operator gold data): V19 raised SM2 and the soft EME still triggered; V20 raised SM3 further and threw HARD EMEs requiring restart. So the soft EME is the integrator accumulation itself, not a threshold event → the fix must PREVENT accumulation (widen the corridor), which V25/V26 do.
  - **Method note:** sequential single-question `firmware-codepath-tracer` passes beat a kitchen-sink brief (which overflowed at 68 tool calls). Two agents returned confidently-wrong verdicts, both caught by cross-checking against the stock-never-faults constraint.
  - **Doc:** `docs/HANDOFF-2026-06-02-v26.md`.

- **Era 19 — 2026-06-02 — Accord V24→V25 CLEAN: the corrected "corridor vs envelope" model; the shl/envelope thread was mis-scoped; V25 = GAIN + direction-corridor ×2, UNFLASHED [⚠ V25 later flashed → HARD-FAULTED; see Era 20 — the corridor IS lockstep-monitored]**:
  - **The load-bearing correction.** Four builds (V21–V24) doubled the INTEGER ENVELOPE (`shl 0x8→0x9` on `gp-0x3574`/`gp-0x3578`). That envelope is a WATCHDOG REFERENCE ONLY — delivered torque `gp-0x6b98` = clamp(min(lanes `gp-0x6afe`+r20, governor `gp-0x4f64`), ±0x2000) with the envelope ABSENT, and it does NOT feed the soft-EME integrator. Doubling it changed no torque and no EME headroom — it only DESYNCED the int-vs-float consistency monitors, which IS the V19–V24 hard fault (DTC 0xF00049).
  - **Three distinct 2× levers (do not conflate):** (1) GAIN `tp+0x746c`=`0xC646C` 891→1782 — the only real torque 2×; (2) shl IIR envelope — watchdog-only; (3) DIRECTION CORRIDOR `tp+0x7748`/`tp+0x7754` — the soft-EME integrator reference. Soft EME = command exits corridor → integrator `gp-0x3570` wind-up → SM2/SM3 cutback (no DTC, recoverable). The GAIN doubled the command past the stock ±1024 corridor → V18's soft EME.
  - **V25 CLEAN BUILT** (`build_v25_tva.py`) = GAIN + clamps + ramp (V18) + **corridor ×2** + PN. The entire shl / FP-twin-cave / widen / weight-8-exclude cleanup is DROPPED. 19 bytes / 12 runs, 49/49 CRC, zero code edits, UNFLASHED (at time of this era; later flashed and hard-faulted at full lock, see Era 20).
  - **MODE resolved:** A160 command mode `tp+0x74c8`=0 (MODE 0), distinct from variant mode `gp-0x674e`=1.
  - **Doc:** `docs/HANDOFF-2026-06-02-v25-clean.md`.

- **Era 18 — 2026-05-30 — Accord HIGH-END 2×: Trace A complete (3 override-SMs fully pinned, command-driven) → V19 built (proportional gate rescale), UNFLASHED**:
  - **Goal:** enable full 2× LKAS torque to SURVIVE the hard mid-turn driver-override regime (where the EME snap lives) — by understanding the snap exactly and rescaling its trigger proportionally, not defeating it. Operator-authorized subagent swarm; operator signed off on the safety trade before the build; flash deferred to a later explicit file+bus naming.
  - **Trace A — the EME snap is fully characterized.** The three OR-linked authority-gate SMs **all arm off the COMMAND-magnitude path** (command → integrator `gp-0x3570` → `uVar53`/`uVar34`), **NOT column velocity** — which is *why* the EME is 2×-only.
  - **Complete arming-threshold set PINNED (cal-addressable):** SM1 `tp+0x71de`=`0xC61DE`=2048 (+ velocity > `0xC61E0`=7168 + command-opposes-motion) · SM2 `tp+0x7422`=`0xC6422`=16384 · SM3 `tp+0x71dc`=`0xC61DC`=30720 (= integrator saturation clamp; `30720 = 2×15360`). `gp-0x4f60`/`gp-0x6af8` UPGRADED to [STRONG] = column/motor **angular velocity** → the SMs are **anti-oscillation / fight-on-motion** monitors. ⚠ **CORRECTED 2026-07-18: `gp-0x4f60` is SENSOR-B (TAS) DRIVER COLUMN TORQUE, not angular velocity** — proven by CAN-399 packer `FUN_00055c42` (`STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`). The "[STRONG] angular velocity" upgrade recorded here was wrong; it generalized from a downstream *use* (`gp-0x4f68 = |gp-0x4f60|` feeding a rate-like gate) to the signal's *identity*. This same correction was made once on 2026-07-07 (`docs/HANDOFF-2026-07-07`, "Gate 5 is |column torque|, not angular velocity") and then **failed to propagate** — see [[reference-accord-gp4f60-is-sensor-b-column-torque]], which is now the single node of record. `gp-0x6af8`'s identity is untouched by this correction.
  - **V19 BUILT** (`build_v19_tva.py`) = V18 base + TWO cal halfwords: `0xC6422` 16384→32768 (SM2) + `0xC61DC` 30720→61440 (SM3 + integrator clamp; arithmetic-safe). **SM1 left stock** (not the 2×-only culprit). 49/49 CRC, clean 17-byte diff. UNFLASHED. The rescale preserves each monitor's RELATIVE trip point at 2× (loosen-proportionally ≠ defeat).
  - **Residual [OPEN]:** command full-scale ambiguity → SM3 edit may be inert if full-scale≈8192; WHICH SM fires on-car is undiscriminated.

- **Era 17 — 2026-05-27 (later) — Accord EME: 4-analyst Ghidra review DISMANTLED the V16/V17 mechanism; V18 (2× + ramp-only) FLASHED + road-validated (drives well)**:
  - **The Era-16 slew story was INVERTED.** A multi-analyst disassembly review (11 rounds, decode-verified) proved `0xC61D6`=0 is the **step size** of a rate limiter on a dormant internal state `gp-0x356c` — step=0 **FREEZES** the lane (it is NOT a "disabled delivered-command damper"). Setting 0→14 **ACTIVATES an uncalibrated speed×torque 2D shaping map** onto the live command. **V16 REJECTED** (highest-risk lever).
  - **V17 deadband-only is INERT.** `0xC6424` gates ONLY the `gp-0x356c` limiter; with slew=0 that state is pinned at 0. Deadband and slew are **coupled**. The **real EME command-cut is the override state machine** node `gp-0x6960`, NOT the shaper deadband.
  - **Ramp `0xC64DE` re-labeled.** `tp+0x74de`=17 is the **count ceiling** of the re-engage/debounce SM (counter `gp-0x6756`); 17→27 **LENGTHENS/softens** the re-engage, targeting the **recovery ratchet**, not the initial snap.
  - **No output rate-limiter exists as cal.** A snap-killing asymmetric down-rate limiter would need a **trampoline code patch** — scoped on paper, never built. The "aragon asymmetric rate-limit prior art" claim is **RETRACTED** (not applicable to this chassis/mechanism).
  - **RESULT (operator road test, authoritative):** **V18 = 2× gain/clamps + ramp-only (`0xC64DE` 17→27), calibration-only, drives well.** It is the current good Accord build at this point in the log.
  - **New node:** reference-accord-eme-lever-semantics (the disasm-grounded lever vocabulary).

- **Era 16 — 2026-05-27 — [⚠ CORRECTED by Era 17 — the "disabled slew limiter / re-enable 0→14" mechanism below is INVERTED; V16 was REJECTED, V18 ramp-only is the flashed fix] — Accord EME root cause LOCATED (disabled slew limiter) + V16 fix built + full torque-path inventory + complete pointer-base audit**:
  - **Operator reframe:** the EME isn't LKAS easing off — the **WHOLE power steering momentarily cuts out**, no DTC. Redirected the hunt from the LKAS-only arb-kill to the shared post-merge trunk.
  - **4-agent program-wide inventory sweep** (`search_instructions` over all 185,116 instructions) → base driver-assist (gp-0x6bf0) + LKAS both merge into the shaper accumulator and exit the SINGLE final command **gp-0x6b98** → zeroing it kills BOTH.
  - **Root cause (disasm-verified end-to-end):** hard override → net-demand zero-crossing → assist state machine transient re-init (no DTC) → shaper **deadband** (`0xC6424`=29491) zeroes the command via node **gp-0x6960** → gp-0x6b98=0. **KEYSTONE: the delivered-command slew limiter is DISABLED (`0xC61D6`=0)** — any momentary drop is a hard cut+hold+jump (felt cut + ratchet) not a soft dip.
  - **Pointer-base audit COMPLETE**: app **tp=0xBF000** built in THREE instrs (movhi 0xb + movea 0x7000 + **add r1=0x8000 @0x140d6**); the missed third instr was the source of an earlier off-by-0x1000 address error. Bootloader tp=0xF8000; gp=0xFEDF8000.
  - **V16 BUILT** (`build_v16_tva.py`): V15B 2× + slew `0xC61D6` 0→14 + deadband `0xC6424`→20000 + ramp `0xC64DE` 17→27; 49/49 CRC PASS, clean 18-byte diff, UNFLASHED (at time of this era — REJECTED by the Era 17 review below).

- **Era 15 — 2026-05-26 (late) — Accord 2× EME: the driver-override / torque-sensor PLAUSIBILITY DROPOUT (reopens Era 14's "saga closed")**:
  - **Trigger:** operator road-reported a recurring, scary EPS-misbehavior event (EME) on V15B. Always op-engaged; on sharp low-speed turns where op falls short and the driver adds significant hand torque, **LKAS abruptly zeroes (wheel snaps straight), steering degrades (heavy + jerky/ratcheting) ~10s, then recovers**.
  - **Where driver input enters the LKAS path (Ghidra-verified):** the dual-coil **column torque sensor** (5 ADC channels) → plausibility voter `FUN_00041eec` → fused driver torque `gp-0x6a5e` + converge/plausible flag `gp-0x67f4`. `gp-0x6a5e` is the axis of the LKAS arb-limit curve AND feeds gates that ZERO the LKAS integrator. Delivered LKAS = `clamp((integ+term)×pol×GAIN[0xC646C],±[0xC61B4]) × ENABLE`.
  - **Root cause:** the V14/V15 **2× arb-output gain (applied AFTER the integrator) amplifies a pre-existing, normally-imperceptible driver-override / torque-sensor plausibility inhibition** into a violent mid-turn assist loss. We didn't break the mechanism; we doubled its consequence.
  - **Mitigation:** SAFE = reduce gain `0xC646C` / clamp `0xC61B4`. **DO NOT widen the torque-sensor plausibility threshold** — `FUN_00041eec` is a genuine column-torque-sensor fault detector.
  - **New memory:** reference-accord-driver-override-plausibility-eme (load-bearing for any future Accord 2× build).

- **Era 14 — 2026-05-26 (Accord V14 FLASHED + ROAD-TESTED — IT WORKS; the multi-session torque-mod saga is CLOSED)**:
  - **Result:** operator flashed V14 (`build_v14_tva.py`: arb gain `tp+0x746c`=`0xC646C` 891→1782 + clamps `tp+0x71b2`/`tp+0x71b4`=`0xC61B2`/`0xC61B4` 512→1024) and confirmed it delivers the intended **~2× LKAS torque at the wheel**. The **first** Accord torque-mod that delivers.
  - **The open MAGNITUDE question is CLOSED affirmatively (Case A).** The LKAS path is REQUEST-LIMITED by the arb output gain + clamps, **far below the 4762 governor** — stock full-command arb output ≈ **418**; V14 ≈ **835**, uncut by the governor. **V15 / governor `0xC6202` edit is NOT needed for 2×** — contingency only.
  - **Independent disasm re-verification this session** (operator asked to verify before declaring victory): arb math, `limit_and_pack`/distribute_clamp path, governor clamp all confirmed by direct read.
  - **Residual = comma-side only:** openpilot lateral PID/feedforward should be rescaled for the ~2× plant gain.

- **Era 13 — 2026-05-26 late (Accord LKAS DELIVERY chain verified — the arb output reaches the motor; V14 rehabilitated; binder relocated to the governor 0xC6202)**:
  - **The arb output is NOT a monitor dead-end — an intra-session wrong turn, corrected.** Disassembly proves `limit_and_pack` (FUN_0x2b422) packs the clamped arb torque into the struct and calls the distributor. **Verified chain to the motor:** arb→limit_and_pack→distribute_clamp(idx1)→`gp-0x62f8[1]`→mixer→`gp-0x3d88`→`gp-0x6b4c`→FUN_0003aa2c→`gp-0x6b94`→FUN_0004503c(governor)→`gp-0x6ace`→FUN_000456a4→`gp-0x6acc`→shaper FUN_00042af8→`gp-0x6b98`→FOC (45 readers).
  - **V14 (build_v14_tva.py) is on a LIVE path, not inert.** gain `tp+0x746c` 891→1782 + clamps `tp+0x71b2`/`tp+0x71b4` 512→1024; 49/49 CRC, clean 8-byte diff.
  - **Dominant high-end binder = runtime governor `gp-0x4f64`** = cal `tp+0x7202`=`0xC6202`=`0x129A`=**4762**. ⚠ **CORRECTED 2026-07-17:** the governor's LERP axis is the **MOTOR resolver electrical-angle RATE, NOT vehicle road speed**; the governor tapers under fast steering motion, not highway speed. gp-0x4f64 has **3 consumers** (see reference-accord-gp4f64-three-consumers).
  - **Two distinct levers:** (a) V14 arb-source scaling (raises LKAS's *share*); (b) governor cal `0xC6202` (raises the *combined* ceiling; lockstep-shadowed — safety-sensitive).
  - **Variant mode `gp-0x674e`:** 16-entry ECU-ID table @`0xCD000`; A160→key `TVAA1`→entry 2→**mode 1**. Selects arb/driver-assist LERP curve SETS — NOT the delivered LKAS gain (that's a separate per-channel mixer mode array).
  - **Method lessons:** the decompiler can hide a live data path by rendering a populated argument struct as constants — verify struct-passing call sites in DISASSEMBLY, not just decompile.

- **Era 12 — 2026-05-26 eve (THE `tp` base fix — Era 11's whole premise was wrong)**:
  - **Root cause of every Accord "high-end won't move" dead end: a wrong pointer base.** `0x9152` sets the *bootloader* `tp=0xF8000`; the EPS **application re-sets `tp=0xBF000`** at `FUN_00014084` (`0x140ce`: `movhi 0xb / movea 0x7000 / add r1(0x8000)`; the same routine derives `gp=0xFEDF8000`). Every `tp+offset` cal is at **`0xBF000+off`** — the **programmed** `0xBF000–0xC6FFF` region.
  - **There is NO absent `0xF8000+` calibration partition.** Era 11's "absent-partition cal" framing is **RETRACTED**.
  - **Real binder = arb OUTPUT GAIN** `tp+0x746c` = **`0xC646C` = 891**. Full-command output ≈ **±418**, below the clamps. **2× = gain 891→1782 + clamps 512→1024 — three flashable `.rwd` cal halfword edits.**
  - **Method lesson:** resolve a global pointer at its *application* definition site — not a bootloader startup or a negative search. The bootloader `tp` silently poisoned ~6 memories across multiple sessions.

- **Era 11 — 2026-05-26 (Accord LKAS high-end torque binder relocated to arbitration output) [SUPERSEDED BY Era 12 — wrong `tp` base; the arb-output relocation was right, but "absent-partition cal / gain=−1" is retracted]**:
  - **Trigger:** V12A/V13A flashed → low/mid 2× confirmed but MAX commandable torque stayed at stock at ALL speeds, no EPS fault.
  - **The load-bearing correction — a LOGICAL error, not just a tracing error:** "no fault ⇒ demand reached the raised ceiling ⇒ binder is downstream/unreachable" was invalid. A clamp biting both int/float paths agrees → no fault → top stays stock while the demand never rose.
  - **The binder is the ARBITRATION OUTPUT (FUN_00028ea6):** `uVar13 = (combined_torque × polarity × gain[tp+0x746c]) >> 15`, then `clamp(±tp+0x71b4)` → `gp-0x6b3c`. (Later corrected in Era 12: `tp=0xBF000`, not the "absent `0xF8000+` partition" claimed here.)
  - **Verdict:** low/mid 2× is the usable win; the framing of the high-end ceiling as "absent calibration" was wrong (see Era 12).

- **Era 9-and-earlier note:** the Accord platform's activation-path/control-plane verification work (whether LKAS-gated levers can affect manual driving) and the initial V0–V10 build history predate the eras captured in detail here; see `project_accord_torque_mod_v0.md` for the full rolling log back to V0.

## Key relationships (narrative)

**The Accord TVA / V850 cluster is its own MCU family, distinct from the kit's earlier SH-2A (Civic) work.** Accord TVA = V850E2/Px4, little-endian, 1 MB code flash. Code/byte patterns don't transfer across MCU families. But the *conceptual structure* does: cipher → container → calibration region → SA handshake → flash workflow. The sa-secret-per-mcu-family node captures the cross-family invariant: same algorithm structure, different constants per family. `accord-torque-mod-v0` is the project-state node — it gates flash decisions the same way an equivalent node would for any platform.

**Tooling-bug-as-firmware-bug failure mode.** Two compounding rizin/Ghidra V850 decode bugs (sld.hu disp scaling + divq dst==src remainder) made the universal Honda SA algorithm look like a novel variant on first read. The reflex to suspect "Honda changed the algorithm" was wrong; the correct default is to suspect the tooling first when V850/E2 analysis produces "this looks novel." This generalizes: whenever a disassembler output suggests an unexpected divergence, verify the disassembler's encoding against the silicon's ISA reference before claiming algorithmic novelty. See `reference-rizin-ghidra-v850-quirks`.

**The operator-vs-analyst tension is now an explicit feedback rule.** When the operator reports lived driving experience, that's ground truth over abstract analyst recommendations. This pattern generalizes beyond any single build: human-in-the-loop observational data (the V25→V26→V27→V28→V29 correction ladder, each falsified or refined by an actual road test / on-car fault) beats sandboxed static-analysis predictions when they conflict.

## Last updated

### 2026-05-24 — Era 4 update (Accord TVA / V850 platform opened)
- Added new ACCORD TVA / V850 PLATFORM cluster with 3 reference nodes + 1 project node
- Added 3 new feedback nodes (three-senses-of-rebuilt, dont-kill-long-agents-early, tight-agent-briefs)
- Trigger: Joey approved a dream-pass constellation update after 7 new memories landed in the Era 4 session

### 2026-06-08 — INFRA layer: comma 4 / Konik device access (reconnect-after-wipe)
- **Why this matters relationally:** device access is the **substrate the whole on-car empirical program depends on** — every drive-log pull that feeds road-test validation of a build flows through this node. When it breaks, no on-car empirical work can land.
- **Node updated:** `reference-operator-flash-hardware-topology`/device-access notes — a reconnect-after-wipe recipe: canonical dongle `d5779336554ff2d2` (a wipe can pin a phantom ID — fix = `rm /data/params/d/DongleId` + `python -m system.athena.konik`, no QR needed); SSH key `comma4_claude` (not `id_ed25519`); `/persist/comma/id_ecdsa` must survive wipes (identity anchor).
- **Standing lesson promoted:** a FULL wipe destroys local rlogs → pull-or-confirm-uploaded before any wipe is a hard pre-wipe gate, sibling to the pre-flash "kill openpilot/pandad" rule.

### 2026-07-17 — Accord-only cleanup pass
- Repo-wide cleanup removed all Civic (`39990-TBA-C120`), radar (`36802-TBA-A160`), and Acura RDX (`39990-TJB`) work per operator request — this constellation was rewritten to match: Civic clusters (CIVIC ARCH / MECHANISM / ACTIVATION PATHS / DEPTH MAPPING / DRIVE-DATA DIAGNOSIS), the DOMAIN EXPERTS cluster (Aragon/vfn, Civic-specific), the FOUNDATION cluster (Civic `eps-cipher` + `clarity-civic+28`, both gone with `rwd-xray/`), the SPECULATIVE THREADS/DREAMS cluster (all Civic), and every radar/RDX-era temporal-layer entry were removed.
- Renamed/reframed surviving clusters: PROJECT STATE trimmed to the Accord node only; introduced ACCORD EME / TORQUE-MOD MECHANISM (the large body of V11–V38 findings, previously folded into prose only) and V850 TOOLING / INFRASTRUCTURE (replaces FOUNDATION) as explicit clusters so the surviving ~20 `reference-accord-*` nodes have a home in the cluster table.
- Redrew the ASCII abstract for the 4 surviving clusters.
- `MEMORY_CONSTELLATION.svg` deleted (depicted the old 4-platform diagram; not hand-patchable safely — regenerate fresh if wanted).
- Cross-cluster edge table trimmed to Accord/Feedback edges only; the large historical Civic edge list was dropped rather than kept dead.

### 2026-07-18 — Era: V38 setpoint raise + the FAULT-ELIGIBILITY layer (and three retracted alarms)

**Why this matters relationally:** this session added a *layer* the constellation was missing — not another cal finding, but the **machinery that decides whether any given fault is survivable**. That layer retroactively explains prior on-car outcomes and is now the first thing to consult before trusting any new fault claim.

**New nodes:**
- `reference-accord-watchdog-fault-sm-fun43e44` — the trip structure: 7 weighted flags (1..64, **max 127**) vs threshold **128** (unreachable in one cycle *by design*), escalated by a ~10-cycle debounce adding 1024.0. Two monitors: M1 `FUN_00042af8`/`gp-0x3564` → `FUN_00016de6(0x1c,…)`, M2 `FUN_00043e44`/`gp-0x3550` → `(0x1d,…)`.
- `reference-accord-v31-to-v38-scaling-audit` — what V31's 2× fix teaches V38's 4×, and the three alarms that didn't survive contact with the disassembly.

**The load-bearing chain this session established:**

```
cal edit  ->  int/float mirror divergence  ->  flag (weight 1/2/32)
          ->  ~10-cycle debounce (gp-0x3550 / gp-0x3564)
          ->  FUN_00016de6(idx)  ->  FUN_0001611e: record[+0x8] & 0x41 ?
                 |                        (record = 0xB7D58 + (idx-1)*0x1c)
                 +-- eligible -> FUN_00018738 -> gp-0x685c=1 -> gp-0x3ef8=1
                                 -> FUN_00019f7c -> gp-0x67fa=8
                                 -> FUN_00045608(3,0,0x8000,0x8000) = MOTOR OFF
                                 -> gp-0x3ee8=1  (POWER-CYCLE to recover)
                 +-- not eligible -> DTC + dash lights only, base assist SURVIVES
```

**This chain is now the kit's fault-severity oracle.** `0x1c`/`0x1d` (monitors) and `0x17` (`gp-0x4f64` shadow mismatch) are **hard-eligible**; **`0x49` is NOT** — which *retrodicts V36's exact on-car signature* (dash lights + LKAS drop, steering survived). A model reproducing a known road outcome is the strongest validation available here.

**Edges redrawn:**
- `corridor-lockstep` ↔ `override-snap-state-machines`: a **live contradiction resolved** — `corridor_lockstep`'s "hard shutdown" is RIGHT; `override_snap`'s "REPORT-ONLY" is WRONG and retracted in place. They described *two different monitors* and `override_snap` named the hard one by its accumulator.
- `setpoint-limit-15360-lerp` → `watchdog-fault-sm`: the `[OPEN]` slew concern is **closed by refutation** — its "actual lags predicted" premise mischaracterized an int-vs-float redundancy check.
- `v31-to-v38-audit` → `override-snap`: the `~15360` in `override_snap` is `16384×1024/1092 = 15363.8`, the **integrator-domain** equivalent of the SM2 threshold — *not* the setpoint clamp. A units conflation that propagated into a false flash-blocker before being caught.

**Three alarms raised and retracted in one session — the meta-lesson.** (1) residual-scaling-at-4× (refuted by the kit's own falsified-V28 record); (2) "V38 spent all its SM margin" (cross-domain comparison; `r13` traced to authority, SM1's 2048 sits inside a driver-opposition AND); (3) "governor headroom collapsed 7.6×" (true observation, wrong implication — the governor doesn't bind at nominal, and the taper *is* the thermal protection). **Overstating a risk is as much a calibration failure as understating one**, and it is the more insidious failure here because it can talk the operator out of a sound build. Before escalating anything to "top risk," check whether this kit's own falsified-hypothesis record already answers it.

**Also corrected in place:** an agent-memory verdict *"Monitor 2 PERMANENTLY GATED OFF, never needs fixing"* rested on an **off-by-`0x1000`** tp+disp slip — the gate is `tp+0x74a4` = **`0xC64A4` = `0x00` = ENABLED**, not `0xC74A4` = `0xEA`. Struck through in place; that conclusion would have told a future session to skip mirror discipline during corridor work. ⚠ **The same slip has now been made THREE times (2026-07-18, 2026-08-06 ×2)** and re-verified each time: **`0xC64A4 = 0x00` on stock, V74 and V75 ⇒ Monitor 2 is ARMED in every build.** See [[reference-accord-monitor2-corridor-and-the-c64a4-trap]] and [[feedback-verify-the-crux-yourself-it-caught-four-errors]].

### 2026-07-19 — Era: V38 on-car clean, V39 direct-rate vibration experiment

V38 moved from static candidate to **flashed and fault-free**. Remaining behavior separates into a several-Hz
hard-turn ratchet and a common tens-of-Hz high-LKAS vibration at low and high road speed. Strong driver torque
moves the wheel quickly without either symptom, contradicting an intrinsic moving-motor limit. The direct
Sensor-B torque-rate lane (`gp-0x4f62 -> r24`, up to +/-8192) is cadence-compatible with the vibration; the
independent governor remains a possible stateful ratchet participant. Revised V39 suppresses all `r24` signs
at the exact V9 full-scale equivalent (`|LKAS lane|>=417`) and low driver torque, leaves adaptive `r26`, every V38 calibration, and the governor
unchanged, and does not claim the ratchet is solved. The live golden edge map is
`analysis-2020accord/eps_lkas_chain_model.py`; update it continuously and prefer it over stale prose.

### 2026-07-27 — Era: V53 built (FOURFRAME2 + min steer speed 0), and the no-speed-gate claim collapses

**New node:** `project-v53-fourframe2-plus-minsteerspeed0` — V53 = FOURFRAME2 byte-for-byte **+ six bytes**
(`0xC62EA` 320→0, plus the CAL CRC). BUILT, UNFLASHED. Supersedes FOURFRAME2 as the flash candidate.

**The load-bearing edge this session established is a RETRACTION chain, not a discovery:**

```
"a dedicated trace found NO speed threshold in the command chain"   (golden model, pre-07-24)
   |  trace required  compare -> BOOLEAN STORE
   |  bVar2 is never stored: register-only, consumed by the AND-chain
   v  FALSE NEGATIVE
0xC62EA IS the gate, in FUN_00028ea6, in the command chain      [SOLVED 07-24]
   |
   +-> "the firmware low-speed threshold is unquantified"   -> 320 = 4.995 km/h = 3.104 mph
   +-> "NO VEHICLE-SPEED INPUT ANYWHERE" (07-21 pass)       -> falsified TWICE (the window; and the
   |                                                            G1 governor vs cal 0xC6316=640)
   +-> "the ~5 mph vibration peak is NOT a firmware speed gate, none exists"
            -> retired; three effects (firmware window / OP engage floor / plant physics) are
               COLLINEAR on every route so far and have never been separated
```

⇒ **Method rule, now in the model itself: never require "compare → boolean store"; search for the compare
alone.** The same false-negative shape has now produced wrong answers twice in this kit (cf.
`accord-v850-scan-traps-formatv-and-storezero`, `accord-gp4f60-two-encodings-enumeration-trap`). All three
retracted claims had survived because the golden model asserted them in prose while the falsifying result
sat in a handoff — the same failure mode that created `docs/BUILD-LINEAGE.md`.

**Edges redrawn:**
- `accord-low-speed-lockout-window-c62ea` → `reference-accord-vibration-needs-applied-torque`: **promoted
  from "related" to LOAD-BEARING.** Route 13's A/B/C split cannot separate applied-torque from speed
  because `STEER_CONTROL_ACTIVE` *is* the sub-5 km/h gate there — cells B and C have zero speed overlap and
  the engaged-at-low-speed cell is structurally empty. The lockout edit is the *only* way to fill it, so
  the lockout workstream and the vibration workstream are one experiment, not two.
- `project-v53…` → `reference-accord-fourframe-strb-ssam-defect`: V53 inherits the STRB fix by **byte
  equality with the verified image**, not by re-derivation — `build_v53_tva.py` imports the cave from
  `build_vfourframe_tva.py` and asserts a 6-byte diff. ⇒ **new reusable pattern: "existing cave + one cal"
  should always import, never re-type.** Zero transcription surface beats any re-disassembly gate.

**A design intent recovered, not just a value read.** `gp-0x68b3` (the window bypass) is written only when
`gp-0x6a62 == 0` — *exactly* true standstill. So stock **permits 0 km/h and forbids 1–319 counts**: the
discontinuity is deliberate. That is why V53 uses 0 rather than the previously-recorded suggestion of 64 —
0 removes the discontinuity, 64 would merely move it. **Reading a cal's value is not reading its intent;**
the neighbouring bypass flag carried the intent and the value alone would have led to the worse edit.

**Open, and honestly unresolved:** an on-car `STEER_STATUS=3` **cannot** distinguish "speed window failed"
from "a derate is active" — `gp-0x69aa == 0x8000` is a second conjunct of the same AND sharing the same
ST=3 write. Any drive analysis keying on ST=3 must state which it means.

---

## 2026-08-04 — V69 flew: two REVERSALS, one new gate, and a probe that failed arithmetically

**Three edges changed direction this session, and two of them changed the meaning of builds already
flown.** Read this before quoting anything about r26, the rate-lane dose, or the detector nulls.

### Chain 1 — the dose–response is a CURVE, and the kit had only ever seen one side of it

```
V39 / V42 / V61   rate lane tested DOWNWARD          -> null, null, WORSE
   |  "the gradient points UP"                          [accord-rate-lane-is-the-damper-not-the-amplifier]
   v
V62 / V65   2.00x                                    -> grind #1 FIXED 8-42x   [first measured fix]
V67 / V68   2.00x, GATED on LKAS                     -> best-measured arm in the corpus
   |
   |  extrapolate the same direction, on the operator's explicit call
   v
V69   4.00x, speed-shaped                            -> GRIND #1 IS BACK  (2.244 [1.438, 3.191] at creep)
   |
   +-> median e_18-22 engaged creep: 2501 (0x) . 879 (1x) . 168 (2x) . 109 (2x gated) . 746 (4x)
   +-> NON-MONOTONE, minimum near 2x
   +-> and the dose was FULLY DELIVERED (0.0000% above the rail) => not a clipping artefact
```

⇒ **Method rule: a monotone dose–response measured over [1x, 2x] is not evidence about 4x.** V69's
GATE 2 magnitude leg said exactly this in advance (*"the flown bracket is BROKEN — this extrapolates to
twice the largest dose ever driven"*) and it was right. **The caveat was recorded, stated and correct;
what was missing was any positive reason to expect the curve to keep going the same way.**

**New edge, and it is the interesting one:** the effect is **engagement-conditional though the dose is
not** — manual at 4x is inside the null vs stock (1.070 [0.383, 1.396]) while engaged is 2.244x.
⇒ the mechanism lives **inside the closed LKAS loop**, which no open-loop damping story reaches.
Two candidates, neither settled: a plain derivative optimum overshot, or a **parametric gain collapse**
(`gp-0x6ac0` is `ld.hu` UNSIGNED @`0x3AAC4`, so the gain index sweeps 0→peak→0 **twice per cycle**, and
V69 turned a 2.0x rolloff into 8.0x — the damper weakest exactly at peak velocity).

- `accord-v69-flew-dose-response-non-monotone` → `accord-v62-flashed-grinding-is-fixed`: **new edge,
  CORRECTIVE.** V62's 8-42x sits near an optimum, not on a ramp. Any future "double it again" proposal
  must cite this.
- `accord-v69-flew-dose-response-non-monotone` → `accord-lane-change-transient-is-dose-independent`:
  V69's *stated purpose* failed independently of the grind-#1 result. **Two separate verdicts, one drive
  — do not let either carry the other.**

### Chain 2 — the r26 claim SPLITS: one leg reversed, one downgraded

🛑 **Do not read this as a flat reversal — that would be the mirror image of the original error.** The
claim rested on two **independent** legs and they resolved differently.

```
LEG 1 — THE GATE                                                        [REVERSED, EVIDENCE]
   r26 == 0  <=>  gp-0x6b5e != 0  <=>  the trapezoid LERP is ZERO  <=>  |gp-0x6bda| >= 384
   gp-0x6bda = MARGIN to a peak-hold envelope of driver assist torque gp-0x6bf0
   hands-off the margin is ~9262 = 24x the threshold
   => the gate does NOT kill r26 in ordinary driving, least of all hands-off at creep
   => the kill window is a ~512-count sliver at the DRIVER-OVERRIDE end (cf. 0xC6156 = 9216)

LEG 2 — THE MAGNITUDE                                            [DOWNGRADED to BELIEF]
   0xC6564 byte-reads as 40 bytes of exact zero            [TRUE, re-verified, still true]
   no writer found for the RAM adjustment gp-0x641E..gp-0x6444 (10 of 18 cells checked)
      |  assumed: this cal base IS what feeds gp-0x69a4
      |  NEVER VERIFIED  <-- the whole error lives on this one edge
      v
   gp-0x69a4's real producer is a LIVE runtime 10-segment LERP @0x355C6 in FUN_000352b4
      (1 writer / 3 readers: 0x355A4, 0x3575A, 0x3AB3A = the aggregator)
   => "r24 carries the entire lane" rests on LEG 2 ALONE, and it may still be right
   => the V42/V61/V62 single-lane re-attribution is CONTINGENT on LEG 2
```

★ **The one indirect argument that LEG 2 holds — and it is what keeps the dose–response coherent:**
at `a = gp-0x69a4/1024 ≈ 1`, V67/V68's gate (gain_A 3072 → 512, a **6.00x cut**) would put their engaged
**total at ~0.94x stock** — essentially *on* stock — **yet V67/V68 measured the best grind #1 result in
the kit (109 vs stock's 879).** ⇒ **the empirical record argues `a` is small.** [BELIEF, indirect.]

✅ **AND IT IS DIRECTLY MEASURABLE, which is why this stops being an argument.** r24 and r26 share
**ONE** polarity load — `ld.b -0x6752[gp],r14` @`0x3AB78`, reused at `0x3AB7E` (r26) and `0x3AC3E`
(r24) — so **they always carry the same sign**. With r26's post-clamp mirror `gp-0x6adc` (`st.h`
@`0x3AD4E`, 0 readers / 1 writer) on one bit and r24's `gp-0x6ada` on another:
**bit4 pinned at 1 while bit3 toggles ⇒ r26 is zero; bit4 tracking bit3 ⇒ r26 is live.**
**V70 flies exactly that pair. Non-vacuous in both directions.**

⇒ **Method rule, and it is the same shape as the `0xC62EA` false negative in the 2026-07-24 chain
above: a verified PREMISE does not make a verified INFERENCE.** Both errors survived because the
premise was byte-checkable and satisfying, and the step from premise to conclusion was prose.
**When a memory's evidence line is a byte read, ask what the byte read does NOT establish.**

**Edges redrawn:**
- `accord-r26-is-structurally-inert` → `accord-aggregator-lane-mirrors-6ada-6adc`: **INVERTED.**
  `gp-0x6adc` was written off as *"a rung spent on a known constant"*; it is now **the instrument that
  settles the question**, not a wasted rung.
- `accord-r26-is-structurally-inert` → `accord-v67-flew-both-grinds-fixed`: **NEW and unresolved.**
  If LEG 2 falls, V67/V68 is "r24 up 2x, **r26 down 6x**", not "r24 up 2x", and total engaged damping
  falls **below stock** once `a > 0.848` at 0 km/h. **`a` is unmeasured**, and the counter-argument
  above says it is probably small.
- **`0xC6444` is a CANDIDATE, not a recommendation.** Raising it is genuinely untested — V42 tested it
  **downward** (512 → 0, falsified), the same *"tested downward ≠ tested upward"* distinction the
  V61 → V62 correction turned on. 1 reader / 0 writers, no float mirror, CRC block #48, ceiling ≤ 6553.
  **V70 does not take it**: `a` is unmeasured, and while V67/V68's control path is the best-measured arm
  on the two instrumented symptoms, it carries the **high-speed grind** (scalar arm = 2.44x at highway),
  so restoring it was overridden.
- **A property nobody had credited:** V62/V65's `sar` route is the **only** edit in this kit whose dose
  is exact **independent of `a`** (2.000x on the total for every `a`). Every cal-arm edit is
  `a`-dependent. That is an argument for the `sar` family that has nothing to do with byte count.

### Chain 3 — `gp-0x67fa`: a gate above five builds' nulls, and the probe that argues against it

```
FUN_0002214a (RTOS task 1, 1 kHz) calls the assist chain; the guard wraps the jarl IN THE CALLER,
and each callee has exactly ONE call site => a masked-out state means it is NEVER INVOKED
(no stack frame, 0% of body).  Index = plain 1 << (gp-0x67fa & 0xf), no off-by-one.

   0x221d6  andi 0x830 -> {4,5,11}     FUN_00036388  AND  FUN_000428d4   (the OSC DETECTOR)
   0x22518  andi 0x930 -> {4,5,8,11}   FUN_00028ea6 / 0002b422 / 0002b57a
                                       (ARBITRATION = gp-0x6806's PRODUCER)
   0x2269a  andi 0xc30 -> {4,5,10,11}  FUN_0003a382  AND  FUN_0003aa2c   (THE AGGREGATOR)
                          ^^
                          state 10 is in the AGGREGATOR mask and NEITHER of the other two

=> IN STATE 10: the aggregator and the residual lane RUN, while the detector, return-to-centre
   AND arbitration DO NOT.  Assist is delivered from a STALE gp-0x6806.        [EVIDENCE]

State 10 is REACHABLE in normal operation: FUN_00019970 (the state-4 handler) writes it at
0x199CC (diagnostic) and 0x19A72 (NORMAL, on bit 15 of gp-0x6d78, bit 16 -> state 11 wins).
[OPEN] what bit 15 means -- that decides how OFTEN, not whether.
```

⇒ **This is the THIRD time the same failure shape has appeared** — V63's null was ambiguous, V64 fixed
that and created a new ambiguity one layer up (`feedback-probe-the-gate-not-just-the-output`), and now a
layer above *that* turns up in the RTOS dispatcher. *"`FUN_000428d4` was never CALLED"* has **never been
on the table**, and it has the identical signature to *"it ran and found nothing."*

🛑 **BUT THE COUNTER-ARGUMENT IS STRONG AND MUST TRAVEL WITH THE CLAIM.** State 10 is absent from
`0x930` too, so arbitration — `gp-0x6806`'s producer — is skipped there as well and the flag would go
**stale**. V67 measured `gp-0x6806` == `latActive` in **150,302/150,327 = 99.983%** of frames, all 25
disagreements single-frame transition edges. **A stale flag cannot track transitions that closely**
⇒ **the ECU is predominantly NOT in state 10 while engaged, and the detector nulls are probably
GENUINE.** [BELIEF — indirect.]
**Never write "five builds of detector nulls are in play" without this attached.**

✅ **V70's bit5 rung (`gp-0x67fa == 10`) settles it directly, and is non-vacuous both ways:**
bit5 ≈ 0 ⇒ state ∈ {4,5,11} ⇒ **the nulls are genuine and five builds are vindicated**;
bit5 materially non-zero ⇒ **the nulls were on the gate** and the detector programme needs replanning.

⚠ **A second, independent entry gate on the detector is STILL OPEN** — `FUN_00046ea6(5)`, bit 5 of
`gp-0x18d0`/`gp-0x18d4`, a fault/DTC-style bitmask falling to a `0x8000` sentinel if set. The record's
earlier closure established only that that **function** has one caller image-wide — **not** that the
**bit** is clear in operation. **Those are different claims**, and only the first was ever checked.
🛑 **And `STEER_STATUS` on the bus is NOT `gp-0x67fa`** — `4f` reads ST=0 on 47,990/47,990 while state 0
is in no mask, so the car could not have steered. Any earlier equation of the two is void.
⚠ **Provenance:** decompiled against stock `code.bin`, 33 writer sites byte-identical in
`_v68_plain_image.bin`; the **dispatcher itself was not decompiled from a V68/V69 image** — high
confidence (far outside any cave region) but **BELIEF by adjacency, not EVIDENCE.**

### Chain 4 — the probe failed for a reason that generalises

```
"gp-0x6ad4 is clamped to +/-0x2800"     <- TRUE of the ERR *INPUT*
   |  read as if it were the lane's OUTPUT range
   v
bit4 threshold set at +4096 (= "40% of the gate")
   |
   v
actual output ceiling = MIN of three LERPs; the binding one indexed on VOTED VEHICLE SPEED,
   max 1024, starting at ZERO; at the ratchet's 4.9-8.0 km/h it was 164-341
   => the test sat 12-25x above the lane's entire reachable range
   => STRUCTURALLY VACUOUS on every build, every drive
   => and it retroactively explains why V56's mute of this same lane changed nothing
```

⇒ **New standing rule: size a rung against the PRODUCING lane's own reachable output at the operating
point, never against a downstream gate's width**
(`feedback-size-probe-rungs-against-lane-reachable-output`). A gate's width says what the consumer
accepts; it says nothing about what the producer emits. This is the **companion** to
`feedback-probe-the-gate-not-just-the-output`: that node is about *which signal*, this one about
*what value*.
**All three rungs failed at once** — bit5 insensitive (4096 = 71% of a 5786 range), bit6 no exposure
(~1 predicted hit, 0 observed, p ≈ 0.37). One drive, one channel, **zero bits of information.**

### Chain 5 — "an excitation contrast wearing a dose label"

The 2.403x lane-change contrast looked real (2.849x) until **excitation was held fixed**, and then it
collapsed to 2.013 with the CI crossing 1. Within dose = 1.000x exactly, **ALC vs driver-commanded is
2.389 [1.453, 4.898]**.

⇒ **Same class as the withdrawn "engaged-only 28 Hz mode"** — a variable correlated with the arm under
test, doing the work the arm was credited with.
`accord-averaged-spectrum-needs-matched-speed-distributions` is the speed version of this;
`accord-a-caveat-can-mutate-into-a-result` is the provenance version.
**The general node: before attributing to dose, ask what else differs between the arms — and hold it.**

### What is honestly unresolved after this session

- **`gp-0x67fa`'s runtime value.** Structural finding only. Verdict-affecting for five builds — but
  V67's own gate probe argues the ECU is predominantly *not* in state 10 while engaged, so the leading
  reading is that the detector nulls are genuine. **V70's bit5 decides it.**
- **What bit 15 of `gp-0x6d78` means** — it governs how often state 10 is entered on the normal path.
- **Whether bit 5 of `gp-0x18d0`/`gp-0x18d4` is clear in operation** — the detector's *second* entry
  gate. Only the caller-count of `FUN_00046ea6` was ever checked, which is a different claim.
- **`a = gp-0x69a4 / 1024`.** Decides whether V67/V68's gate is a 6x cut on r26 or a no-op, and whether
  "r24 carries the entire lane" survives. The dose–response only coheres if `a` is small — an argument,
  not a measurement. **V70's bit4/bit3 sign pair decides it.**
- **Which mechanism produces the non-monotonicity** — derivative optimum vs parametric gain collapse.
  The dose–response is EVIDENCE; both mechanisms are BELIEF.
- **The ratchet's Q.** Not measurable at NFFT 256 (main lobe caps it at ~13.3), so the recorded Q ≈ 36
  is neither confirmed nor refuted — and the "flat-topped / saturated" premise behind V69's rung choice
  is contradicted by crest **2.07-2.45** (a steady sine gives 1.414).
- **What excites the lane-change transient**, now that gain is excluded. One manual route, CI not
  cleared: a direction, not a finding.


---

## 2026-08-04 (later) — V70 flew: both confirmed fixes were OFF THE CAR, and the dose axis was the WRONG LANE

**This session closed four of the five unresolved items listed above, and it closed them by finding
that the record's own chain had two broken links.** Read this before quoting anything about the rate
lane, the detector nulls, or the ratchet's Q.

### Chain 1 — the record described a car that did not exist

```
V42  0x454FE bne->br      "CONFIRMED ROOT CAUSE, carry forward"
       |                   carried V42..V52C only -- STOCK in V53 -> V70
       |                   lost at the V38/FOURFRAME rebase; NOBODY DECIDED IT
V62  0x3AB76/0x3AC20      "the kit's first measured fix" (grind #1, 8x at creep)
       |                   carried V62 and V65 only
       |                   removed as V66's CONTROL and never restored
       v
V66 .. V70                the car carried NEITHER, for ten builds
```

**New edge:** `accord-both-confirmed-fixes-were-off-the-car` -> **every** build-result node after V66.
It does not falsify those results; it re-labels the arm they were measured on.
**The rule that falls out is RULE 3** (`docs/BUILD-LINEAGE.md`): a "CONFIRMED" result is about a
*lever*, not about the car you are driving. And: **when you remove a confirmed fix to run a control,
write the restore into the next build's spec.**

### Chain 2 — one gate, two selectors: the ladder's rungs were never the same quantity

```
                 lp (ONE gate, 0x3AA96)
                   /                     \
     r26 -> gain_A                         r24 -> gain_B
     0xC6444=512 | 0xC643E | LERP 3072     0xC6442=1024 (gp-0x671d mask, outranks all)
                                           | 0xC6446 | 0xC6440=2048 | mode-10 surface

V67/V68  repoint lp  ==>  r24 UP and r26 DOWN 6.00x, in ONE byte
V69/V70  edit gain_B only ==> r24-only dose
V62/V65  sar on BOTH lanes ==> the ONLY dose-exact encoding, for every a
```

★★★★ **AND THERE IS A CLEAN SINGLE-VARIABLE r24 SERIES HIDING IN THE CORPUS — the strongest result of
the session.** `stock -> V70 -> V69` holds r26 at x1 and steps r24 **x1 -> x2 -> x4**, reading
**879 / 729 / 746, all three CIs overlapping** ⇒ **r24 is NEAR-INERT for grind #1 across a 4:1 range.**
**Every build that FIXED grind #1 changed r26; every build that changed only r24 did not.**
⇒ **the edge to draw is not "nothing is single-variable" — it is `dose axis -> WRONG LANE`.**
⚠⚠ **And carry the part nobody can explain: r26 x2 AND r26 /6.00 BOTH helped, /6 more.** Both monotone
stories die on the same two rows. **Leading open question.**

**`a = gp-0x69a4/1024` is no longer the open question it was** — V70's bit4 read `gp-0x6adc` **strictly
negative on 1,644/18,010 frames**, and a pinned-zero cell cannot clear a `>= 0` test.
⇒ **`accord-r26-is-structurally-inert` LEG 2 is REFUTED**, and the node is superseded in place by
`accord-r24-r26-two-selectors-one-gate`.
⇒ **`accord-v69-flew-dose-response-non-monotone`'s "minimum near 2x" edge is CUT** — it priced every
build on r24 alone at `a = 0`.

### Chain 3 — the detector nulls are vindicated, and the state machine has no cadence

```
V64 / V67 / V68   gp-0x67df null   --(was)-->  "maybe the callee was never invoked" (state 10)
V70 bit5          gp-0x67fa == 10 : 0.0000% --> state in {4,5,11} --> IT WAS INVOKED
                                              --> the nulls are GENUINE. Five builds vindicated.
gp-0x68ad never settable in the field  --> 4->5 never fires; state 5 is DEAD CODE
gp-0x6d78 bit15 one-way OR-only latch  --> 4->10 one-shot; 10->4 never
                                       --> reachable set on a normal drive = {4, 11}
                                       --> "the state-4 cadence sets the ratchet period" REFUTED
```

⚠ **The edge that survives as a tension, not a conclusion:** the V42 substitution is **asymmetric**
while the ratchet measures **symmetric** (skew −0.16…+0.06, crest 2.07–2.45). That is evidence
*against* `0x454FE` shaping the *current* ratchet — which is why V71 justifies restoring it as
**a confirmed fix lost by accident, and nothing more**.

### Chain 3b — the RATCHET separates from every build in the kit

```
grip confound REMOVED (both arms hands-off, creep < 4 m/s), 4 routes / 4 builds
   engaged hands-off  73/88 = 83.0%      manual hands-off  0/118 = 0.0%   p = 3.8e-41
   per-build rate     80 / 81 / 79 / 94%  (V70 / V69 / V62 / V59)
      => BUILD-INDEPENDENT => NO BUILD IN THIS KIT HAS EVER MOVED THE RATCHET
   converse: a hand on the wheel SUPPRESSES it while engaged (V59 94->14%, V69 81->37%)
```

**New node:** `accord-ratchet-is-engagement-required`. It **supersedes** the
`engagement-conditional 44/46` edge in `accord-ratchet-characterised-on-route-4f`.
★ **The transition trace is the mechanism, second by second, at constant speed:** `lat` 0.06 -> 0.31
takes 6-9 Hz p-p **134 -> 1,179 in 0.7 s with speed FALLING**; a grip takes it **910 -> 273 in 0.6 s**.
🛑 **And it corrects the operator's causal order without contradicting him** — his hard *manual*
provocation produced no ratchet; the manoeuvres **set up** the condition and it fires **when LKAS
engages and he lets go**. `feedback_operator_lived_experience_overrides_analyst_recs` gains a
corroborating instance, not a counterexample.
★★ **Two consequences that reach the build programme:** `0x454FE` is a **genuinely untested** lever for
the ratchet (absent from all four measurements), and *engagement-required + hands-off + Q ~= 40 +
base-assist damping exactly zero below ~35 km/h* fuse into **"at creep the driver's hand is the only
damping in the system"** — which is what promotes the deferred FactorC/FactorE lever.

### Chain 4 — four probes in a row died the same death

```
V64, V67, V68  read a lane OUTPUT (gp-0x67df)        -> uninterpretable zero
V70 bit6       read a lane OUTPUT (gp-0x6ada>=+512)  -> zero, but NOT vacuous:
                 replay on route 50's own data predicts 311 hits; stock predicts 52
                 => delivered gain < ~1574 Q10, BELOW stock
                 => 0xC6442=1024 (the gp-0x671d mask arm) is the only arm predicting 0
```

⚠⚠ **The arm-selection reading is the WEAKER one, and the edge must be drawn dashed:** the same rung
read **0/47,990 on V69's `4f` at DOUBLE the dose**, needing only **49 counts** — which arm selection
cannot produce, since the mask arm is 1024 on *every* build; and V67 read `gp-0x671d` **0/150,327** on
route 47. ⇒ **[BELIEF] an under-ranged or mis-reconstructed rung is better-supported. The corpus cannot
settle it** — and `grind #1` cannot adjudicate, being **blind to r24 gain**.

**New feedback node:** `feedback-probe-the-gain-in-force-not-a-lane-output` (**GATE 4**). It sits
beside `feedback-size-probe-rungs-against-lane-reachable-output` (**GATE 3**, which *threshold*) and
`feedback-probe-the-gate-not-just-the-output`. GATE 4 answers **which cell**. 🛑 **The durable part is
the rule, not the mechanism.**

### Chain 5 — the search space shrinks: the aggregator is out, and the ratchet is characterised

`accord-aggregator-zero-gates-all-vacuous` joins `accord-aggregator-never-rails-loop-is-linear`:
**all eight zero-type range gates are capped by their own producers**, so **the aggregator stage
contains no reachable hard nonlinearity** and the relay/limit-cycle framing for it is **REFUTED**.
`FUN_00036388`'s own counters (~20–40 ms, ~1 s) mean **it inherits the ratchet, it does not generate
it.**
`accord-ratchet-q-measured-40` **confirms** the record's **Q ≈ 36** and supersedes only the
*"Q is not measurable at NFFT 256"* edge: **Q ≈ 40 at f0 = 7.793 Hz**, with a **window-cap invariance
test** (39.0 at 54, 40.0 at 111). ⚠ **One episode; a lower bound.** ✅ **Measured on the right data** —
the 6,502-vs-591 discrepancy resolved to *raw broadband = the operator cranking*, and the Q episode sits
**after** engagement, not in it.
★ **It re-opens a dormant node:** damping is **exactly zero below ~35 km/h** while the ratchet lives at
**4.9–8.0 km/h**, and **V47's FactorC+FactorE *"marginally quieter at 5 mph"* has never been evaluated
against the ratchet** — `project_v46_falsified_v47_dampers_only` gets a new outgoing edge.

### What is honestly unresolved after this session

- **`FUN_00046ea6(5)` / bit 5 of `gp-0x18d0`** — the detector's *second* entry gate. V70's bit5
  licenses *"the call was made"*, **not** *"the body ran"*. Still the same claim it always was.
- **What sets `gp-0x6d78` bits 15/16 mid-drive** — `FUN_000197b8` has **21 untraced callers**. Decides
  whether state 4 is sticky for a whole drive or only briefly.
- **WHICH DIRECTION the r26 effect runs.** r24 is near-inert across ×1→×4, so the authority is r26's —
  but **r26 ×2 AND r26 ÷6.00 both helped, and ÷6 helped more.** **The leading open question**, and the
  corpus cannot answer it. 🛑 **`0xC6444` is NOT the test** — it is a **null by construction** on every
  gateless build (read only at `0x3AB5E`, only when `lp != 0`; `gp-0x683c` has 0 writers).
  ✅ **But the single-variable r26 test EXISTS via `gain_A`'s records** — rec0 `0xC6A68` / rec1
  `0xC6A7C`, same 4×4 layout on the same `0xC6010` speed cross-axis as `gain_B`; doubling their whole
  rate axis doses r26 alone below 50 km/h and is exactly 1.000× above it (rec2/rec3 stock). **That is
  V71B**, and it is the test the ×2-vs-÷6 question needs.
- **What produced four consecutive probe zeros** — arm selection is the weaker reading; an under-ranged
  or mis-reconstructed `dtorque` is better-supported; neither is settled.
- **Whether restoring V62's lane brings back creep grind #2**, which V62 introduced. Given r26 is now
  known live, that may have been r26's doubling rather than r24's — **untested**.
- **What "stiffer" refers to.** No bus-side instrument detects it; the saturation mechanism is refuted.
  [BELIEF] the ratchet itself (4,894 counts at Q ≈ 40, 0.8 s after engagement).
- **What excites the lane-change transient** — unchanged from the previous session.

---

## 2026-08-06 — Era: the LOOP-GAIN chain, and BOTH hard faults

**Why this matters relationally:** this session added the *edge nobody had drawn* — a **loop-gain weight
raised four builds ago** sitting **inside a closed firmware loop**, which the damper builds then **armed**.
It reframes V74 and V75 not as two damper doses but as **two points on one loop-gain ramp**, and it is the
first chain in this kit that runs **through** a lever rather than **from** it.

### THE CHAIN

```
V72:  0xC63A0  1024 -> 2048   (mode-proof, tp+0x73a0, 1 reader, 0 writers,
      |                        no monitor, no float mirror)  = +6.02 dB on PATH 2
      |                        -- and PATH 2 is a CLOSED loop: gp-0x6b98 re-enters
      |                        one sample later via FUN_0003b8f6 @0x2240e
      |                        [[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]]
      |  nothing consumed it -- gp-0x6bd0 was ZERO at creep on V72/V73
      v                         (both dead zones shut)
V74:  the damper is ARMED for the first time  (k = 0.5799)
      |  [[accord-v74-flew-damper-is-in-force]] -- bit7 fires 67.443% engaged creep
      |  the raised weight now has a live signal to multiply
      v
V75:  k = 1.5798  =>  +8.70 dB into the same loop
      |  grind #1 responds: d ln(y)/dk = -0.599 [-0.856, -0.348], CI excludes zero
      |  [[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]]
      v
TWO HARD FAULTS
      |  V75 -- engaged, one frame, route 5e t=284.7947 s
      |         [[accord-v75-fault-pinned-to-the-frame]]
      |  V74 -- MANUAL, over a bump, with its damper edits NOT in force
      |         [[accord-v74-hard-faulted-in-manual-over-a-bump]]
      |  the common factor across BOTH arms is the MODE-PROOF cell, not the damper
      v
V77:  0xC63A0  2048 -> 1024   single variable, ONE cell, 5 bytes
      [[accord-v77-built-c63a0-revert]] -- a HYPOTHESIS TEST, not a known-good
```

### The load-bearing edges this session created

| edge | direction | rationale |
|---|---|---|
| `path2-closed-loop-c63a0` → `v74-hard-faulted-in-manual` | explains | `0xC63A0` is the only **mode-proof** non-stock loop weight ⇒ the only lever live in the manual arm where V74 faulted |
| `path2-closed-loop-c63a0` → `v77-built-c63a0-revert` | motivates | −6.02 dB at **zero phase**, costing Path 1 nothing |
| `v74-flew-damper-is-in-force` → `damper-fixes-the-grind…` | enables | V74 is what made a **dose** exist at all; V44/V47/V72 had none |
| `damper-fixes-the-grind…` → `collocation-motor-rate-damper-dead` | **CONTRADICTS** | the collocation theorem said "cannot damp at any gain"; the measured 18–22 Hz slope **excludes zero** |
| `v75-fault-pinned-to-the-frame` → `monitor2-corridor-and-the-c64a4-trap` | **refutes its sizing** | the faulting launch was the **mildest of four** ⇒ magnitude/rail-contact mechanisms are dead |
| `descriptor-bit13…` → `v75-fault-pinned-to-the-frame` | **re-reads** | the `0x7FFF` angle sentinel is a **consequence** of a bit13 fault, not an angle-sensor cause |
| `dtc-read-is-structurally-blind` → `v75-fault-refutation-ledger` | **closes its last action item** | the ledger's "decisive DTC read" is withdrawn — the group is a ~42-member catch-all and the RAM log is cleared by the power cycle |

### Edges REDRAWN (retractions)

- **`collocation-motor-rate-damper-dead` loses its empirical leg.** Its evidence was *"V44/V47 nulls are
  the theorem confirmed on-car."* Both were **mode-inert** (modes 10/11 on a **TVCA4** modes-24/26 car,
  [[reference-accord-car-is-tvca4-mode-24-26]], [[accord-damper-is-mode-table-selected]]) ⇒
  **UNINTERPRETABLE, not falsifications.** The theory may still explain why the required gain is large;
  it can no longer close the direction.
- **`override-snap-state-machines` / `soft-eme-bound-arm-gating`: the cut CANNOT LATCH.** The recovery
  branch is a single fixed-step rise with **no bypass condition** ⇒ it self-clears. A latched loss of
  assist requires the **DTC-eligibility chain**, which is now the only surviving latch mechanism in the
  model. Companion fix: `gp-0x3570` is a **pure unattenuated integrator**, not a ¼-per-cycle tracker.
- **`v75-fault-refutation-ledger`'s anchor is gone.** *"V74 flew 1,011 s clean"* was the reference point
  for every gain-margin argument, and **`k* ∈ (0.580, 1.580]` is VOID.** ⚠ Its route-5d escape hatch is
  also closed: 5d has **5–6 engaged stoplight LAUNCHES** (only *engaged-while-stopped* is 0.0 s) ⇒ V74
  **flew** the faulting regime and did not fault, which **strengthens** the contrast.
- **`dtc-0x18-hard-eligible-cadence-watchdog` is boot-only.** It never was a live per-task deadline
  monitor ⇒ **no cave in this kit has ever had a `0x18` timing budget**, and V75's 45→68 B cave
  (+17 cycles ≈ 212 ns) is **EXONERATED**.

### The method node this session promoted

[[feedback-verify-the-crux-yourself-it-caught-four-errors]] — **four** decision-bearing errors caught by
the orchestrator's own byte reads and decompiles in one session (the `tp+0x74a4` off-by-`0x1000` for the
**third** time, a reversed DTC-map byte order, a fault_id off-by-one, and a `0x1AB` flag mis-scoped as
narrow when **bit10 covers 75 fault_ids**). It joins [[feedback-verify-subagent-conclusions]] and
[[feedback-verify-with-ghidra-and-bytes-both]] as the third node saying the same thing from a different
angle — and it adds the direction the others do not: **verify the SAFE answer too.**

### What is honestly unresolved after this session

- **The `gp-0x6b98` RE-ENTRY term in Path 2.** `0xC63A0` does not touch it, and it may dominate the loop
  gain ⇒ **a V77 null does NOT exonerate the loop.** Highest-value next trace.
- **Why V74 faulted in MANUAL.** Its manual-mode config (`0xC63A0`, `0xC407E`, `0xC61B2/B4`, boost floor,
  `0xC62EA`) is **unchanged since V73**, which did not fault ⇒ **n = 1** and "first sufficient bump" is
  still live.
- **What actually latches.** bit13 rules in the `0x3D01` monitors (fid 28/29) and rules out fid 4/72/80 —
  but **which** monitor, and on what edge, is not closed. UDS cannot answer it.
- **The micro-ratchet needs a different lever.** The damper is flat on 6–9 Hz and the required
  `k = 4.2–13.5` is 3–9× past a dose that hard-faulted.

---

## 2026-08-07 — Era: V80 flew, the damper is a RELAY, and the fault interlock is `0xC407E`

**Why this matters relationally:** this session **cut two edges the whole post-V72 record was hanging
from** — "grind #1 responds to damper dose" and "`0xC63A0` caused the hard faults" — and replaced them
with one mechanism (**a shape, not a level**) and one cell (**`0xC407E`, not `0xC63A0`**). It is the first
era in this kit where the *headline lever* and the *headline cause* were both wrong at the same time, and
both were caught by the orchestrator's own reads rather than by a new drive.

### THE CHAIN

```
V72..V75:  "grind #1 is DOSE-LIMITED"   (slope -0.599, then -0.614, CI excludes zero)
      |    [[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]]
      |    [[accord-grind1-dose-limited-ratchet-dose-independent]]
      v
V80:  k = 4.1597 -- a FOURTH dose point, 2.63x V75
      |  re-scored with V74/V75/V76 on ONE instrument, split-half null [0.63, 1.60]
      v
  🛑 EVERY grind-#1 point is INSIDE its own noise floor across k = 0.58 -> 4.16
      |  [[accord-grind1-is-inert-to-the-damper-dose]]
      |  => there was never an optimum in k to overshoot
      v
  BUT V80 IS THE WORST GRINDING THE CAR HAS EVER MADE -- and it did NOT fault
      |  the lever that moved was the SHAPE: dose flat at 495 ct (97% of the ceiling)
      |  over a 34x rate range, at EVERY speed  =>  a COULOMB RELAY
      |  [[accord-v80-flew-the-damper-is-a-relay]]
      |  every build gate tested `product > ceiling`; V80 clips 0.00% and passed
      v
  27.4 Hz LIMIT CYCLE + a 2.09x broadband HF floor lift (neg control fails identically)

IN PARALLEL, THE FAULT:
  "do not double 0xC63A0, that caused the hard faults"   <- operator directive, 6 builds old
      |  traced: 0xC63A0 has ONE reader; that reader writes only gp-0x374c and gp-0x6b70
      v
  🛑 NO firmware path to gp-0x6b26. THE FOURTH monitor surface is blind too.
      |  [[accord-c63a0-exonerated-of-the-hard-faults]]  closes the last caveat in
      |  [[accord-v77-cannot-reach-the-monitors]]
      v
  0xC407E = 850 IS the mechanism: sole writer @0x36CF0, value pre-clamped, 511 = +1 = untrippable
      |  [[accord-friction-lane-ceiling-is-the-hard-fault]]
      v
V81:  0xC407E -> 511 AND the x1.5 friction row -> stock, on the FLOWN V75 base. 126 bytes, cal-only.
      [[accord-v81-built-c407e511-friction-stock]]
```

### The load-bearing edges this session created

| edge | direction | rationale |
|---|---|---|
| `v80-flew-the-damper-is-a-relay` → `relu-plan-inverts-at-the-ceiling` | **confirms, and widens** | the ReLU node predicted a rail-formed relay; V80 built a relay **with 0.00% clipping** ⇒ the hazard is the **knee**, not the rail |
| `v80-flew-the-damper-is-a-relay` → `v74-v75-damper-is-a-sampled-relay` | **completes it** | that node modelled the relay from a replay; V80's own probe **measures** it (L4 duty 19.4% vs V75's 0.000%) |
| `grind1-is-inert-to-the-damper-dose` → `damper-fixes-the-grind…` | **RETRACTS its title half** | one instrument + a split-half null over four builds |
| `grind1-is-inert-to-the-damper-dose` → `grind1-dose-limited-ratchet-dose-independent` | **RETRACTS "dose-limited"**, **EXTENDS "dose-independent"** | the ratchet *does* move, but only at `k` = 4.16 — which **vindicates** the older `k` = 4.2–13.5 estimate |
| `c63a0-exonerated…` → `v77-cannot-reach-the-monitors` | **closes its open caveat** | "a fourth surface is not formally excluded" — it is excluded now |
| `c63a0-exonerated…` → `friction-lane-ceiling-is-the-hard-fault` | **transfers causation** | the directive named the wrong cell; `0xC407E` is the whole story |
| `fun3a382-is-a-torque-tracking-pid` → `v80-flew-the-damper-is-a-relay` | **resolves its `[OPEN]`, and shows the answer is not enough** | net sign is **dissipative** and Path 2 is **non-inverting** — and V80 is dissipative *and* unstable |
| `v38-rebase-silently-reverted-three-levers` → every V76-lineage contrast | **confounds them** | V80 vs V75 carried four differences, not one |

### Edges REDRAWN (retractions)

- **"Grind #1 is dose-limited" is WITHDRAWN.** It was the kit's cleanest-looking dose-response (a point
  prediction held to 0.19 dB) and it does not survive a fourth point plus a split-half null on one
  instrument. ⇒ 📋 the standing rule from [[feedback-episodes-not-windows-and-the-noise-floor]] now has a
  second, more expensive instance: **re-score every build on ONE instrument before fitting an axis across
  them, and get the null first.**
- **"V80 is 3–30× quieter than V76 at creep"** — asserted earlier in the *same session* and **RETRACTED**:
  V80's engaged creep windows carry median effort 173 ct / 1.3 °/s against 588–1113 ct / 33–48 °/s.
  **Zero matched cells.** An exposure artefact, not a result.
- **"`0xC63A0` caused the hard faults" is REFUTED at the code level**, and with it the *reason* behind a
  standing operator directive that had propagated into two build scripts. The directive may still be a
  sound caution; **its stated cause is not a fact.**
- **"the ×1.5 friction table came from V74"** is off by one build — **V73** introduced it, and V73 also
  raised `0xC407E`, so V73 carried **both** legs of the fault mechanism and simply never met a big enough
  event.
- **V57's `0xC646C` decouple has been off the car since the V38 rebase**, and reader #3 loses its
  "feedback" label entirely (**no torque path**). Neither changes the 27 Hz verdict; both change the
  headroom ledger.

### The method node this session promoted

**Gate the SHAPE, not the rail.** Every damper gate this kit has ever written tests `product > ceiling`.
V80 passed all of them at 0.00% clipping and flew as a near-bang-bang relay, because the relay lives at
**FactorE's knee, 17 counts under the rail**. The cheap invariant that would have caught it is
`dose(2r)/dose(r)` — or the describing-function ratio `N(50)/N(500)`, which reads **1.45× on V75 and
3.27× on V80**. ⇒ **"does not clip" and "is not a relay" are different statements.**

### What is honestly unresolved after this session

- **Where in `k ∈ (1.58, 4.16]` the HF cost switches on.** Flat at/below baseline up to 1.58, 2.09× at
  4.16, and **nothing in between**. The data's own recommendation is *restore the ramp*, not merely lower
  `k`.
- **`gp-0x6b94` → the motor.** Narrowed, not closed: `gp-0x6ace` is the governor-clamped form and its only
  readers are hard-shutdown monitors; `gp-0x6afe` and `gp-0x6b08` are **ruled out** as bridges. **A
  missing link, not a discovered inversion.**
- **Whether the 27 Hz line is commanded or plant.** `0x0E4` correlates +0.93 at lag 0, but the bar is
  **15.8×** the command there and the LKAS lane is a ~1–5 Hz low-pass. Needs a **phase-resolved
  coherence**, not a lag-0 correlation.
- **Reader #5's `±0x200` clamp margin is 22%** on a scale that is not proven identical to the CAN
  sensor's. "Did not fire on this drive" ≠ "cannot fire".
- **Whether V81's friction revert is the right variant.** The probe **could not discriminate**: ×1.5 pins
  at 76% of the rung's threshold, so the whole decision lives inside the comparator's first cell.

---

## 2026-08-08 — Era: V83a flew, the dose axis moves to r24, and a SECOND engaged column is found

**Why this matters relationally:** the two nodes that carried the most weight in the post-V60 record —
*"the damper dose is the axis"* and *"r26 is the lane"* — **both moved off their anchors on the same
day, and for the same underlying reason: a build that was believed to test one variable was testing
another.** V83a's falsifier fired on the ring; RULE 7's mode-proof deletion of the mode-10 ladder
re-priced the r24/r26 attribution; and a **second engaged mode column (27)** turned up carrying the very
damper V83a thought it had removed. ⊕ A **stale memory snapshot** was the proximate cause of six
already-corrected conclusions being re-derived inside this session — a tooling edge, not an analysis one.

### THE CHAIN

```
V81 flew route 67 (grinding, no fix on the car)
  |    [[accord-v81-carries-neither-grind1-fix]]
  v
V83a: revert the engaged damper, predict the 26-31 Hz ring moves  <- PRE-REGISTERED falsifier
  |
  v  route 68, fault-free, cell-stratified vs V81
  18-22 Hz  2.674 [1.956, 3.885]   null [0.63, 1.55], 10/10 cells > 1   -- WORSE
   6-9  Hz  1.526 [1.174, 2.019]                                        -- WORSE
  26-31 Hz  1.021                                                       -- FLAT
      |    [[accord-v83a-flew-worst-modern-build]]
      v
  🛑 THE DAMPER-DOSE MODEL OF THE 26-31 Hz RING IS FALSIFIED (by its own falsifier)
      |
      +--> and it was never a clean test anyway:
           mode 27 is a SECOND ENGAGED COLUMN, still carrying V81's relay damper
           (539 FactorE plateau, N(50)/N(500) = 1.45 vs Honda 0.00, 9.5x m26 at 200 ct)
           Honda's own pairing is 24<->26 and 25<->27
           [[accord-mode-27-is-a-second-engaged-column]]
           v
      V84: FactorC m26+m27 Y[0] -> 0, FactorE m27 -> Honda, lever B restored
           => engaged == manual EXHAUSTIVELY, 0..14000 speed counts, BOTH pairs
           => damper surface byte-identical to V67/V68 (the measured best)
           [[accord-v84-built-engaged-equals-manual]]

IN PARALLEL, THE DOSE AXIS:
  RULE 7 deletes the mode-10 ladder as byte-stock   [[reference-accord-car-is-tvca4-mode-24-26]]
      |
      v  re-price every build at 7 km/h / 128 deg/s engaged
  r24 MONOTONE 0 -> 1 -> 2x   (2501 -> ~790 -> 109-168)
  r26 swings 11.3x at fixed r24 and grind #1 moves ~5%   (V72: 0.953; V71B: 545)
      |    [[accord-r24-is-the-grind1-actor-r26-nearly-blind]]
      v
  🛑 "r26 x2 AND r26 /6 BOTH helped" -- the tension is GONE. Neither did.
```

### The load-bearing edges this session created

| edge | direction | rationale |
|---|---|---|
| `r24-is-the-grind1-actor…` → `r26-is-structurally-inert` | **VOIDS its follow-on leg** | the "r24 is near-inert" reading rested on the mode-10 ladder RULE 7 deleted; **LEG 1 (the gate) stays reversed, r26 is still LIVE** |
| `r24-is-the-grind1-actor…` → `v42-fix-was-the-r26-kill` | **weakens its pattern table** | the ratchet column is untouched; the **grind** column now points at r24 |
| `r24-is-the-grind1-actor…` → `rate-lane-builds-were-never-single-variable` | **completes it** | that node said the lanes were confounded; this one says **which lane won** |
| `v83a-flew-worst-modern-build` → `grind1-is-inert-to-the-damper-dose` | **extends it to a second band** | the ring joins grind #1 as dose-independent — and this time the null was **pre-registered** |
| `mode-27-is-a-second-engaged-column` → `stock-mode24-equals-mode26-damper-is-ours` | **generalises it** | Honda ships **two** manual/engaged pairs; the "engaged damper is ours" finding holds on both |
| `mode-27-is-a-second-engaged-column` → every engaged-column edit ever made | **confounds the half-applied ones** | V83a is the caught instance; **assert both pairs or the edit is half applied** |
| `can-telemetry-surface-census…` → `can-tx-gateway-whitelist-and-20-free-bits` | **confirms the ledger, adds the transport proof** | 16 clean bits by a completely different method, **plus** byte-transparency for `0x14A` — which that node assumed and never proved |
| `gp6c2c-is-the-detector-input` → `friction-lane-ceiling-is-the-hard-fault` | **closes its `[OPEN]` scale caveat** | ≈0.3016 ct per °/s², cross-validated 7,076 vs a measured 7,154 °/s² peak jerk |
| `task5-is-100hz…` → `factord-is-the-angle-error-lever` | **bounds where FactorD is worth anything** | FactorD rides the 100 Hz evaluator ⇒ its value is at **7.79 Hz**, not at the 27.7 Hz ring |
| `feedback-read-the-repo-memory-not-the-stale-snapshot` → the whole constellation | **gates access to all of it** | six corrections were re-derived from a snapshot; the map is only as current as the copy being read |

### Edges REDRAWN (retractions)

- **"The damper dose moves the 26–31 Hz ring" is FALSIFIED**, by V83a's own pre-registered test. Combined
  with [[accord-grind1-is-inert-to-the-damper-dose]], **the damper dose now has no measured effect on any
  band the kit scores** — its only demonstrated effect is the **shape** hazard (the V80 relay).
- **"r26 is the lane the symptom follows" is VOID.** Not a reversal back to the original "r26 is inert" —
  r26 is LIVE — but **grind #1 follows r24**, and the two builds that "proved" r26 both moved r24 too.
- **"The V38 rebase reverted THREE levers" is SEVEN**, and the seventh (`gain_A` rec0/rec1,
  `0xC6A72`–`0xC6A8E`) **had never been logged anywhere** ⇒ every V80-vs-V75 contrast carries **five**
  confounds. Same family as the three silent fix losses already on record.
- **"V42 killed the r26 lane completely" narrows**: `0xC643E`/`0xC6444` are **unreachable**
  (`gp-0x671a` ← one writer @`0x42A12` ← `gp-0x67df`, never non-zero) ⇒ **`gain_A` → 0 was V42's only
  live change vs stock.**
- **"`gp-0x6c2c` is a filtered motor rate" → ACCELERATION.** The differencing stage is load-bearing:
  the friction lane is **DC-blind**, so *"remove friction to fix steady-state heaviness"* has **no
  structural support** and must not be proposed again on that reasoning.
- **"The damper runs at 1 kHz" vs "at 100 Hz" was never a contradiction** — it is a **naming collision**
  between `FUN_00034350` (task 5, 100 Hz) and `FUN_0003aa2c`/`FUN_0003a382` (task 1, 1 kHz).

### The method node this session promoted

**An empirical zero is not a free bit.** `0x18F byte5[4]` reads flat zero on **28 of 30 routes** and is a
**live `STEER_STATUS`→7 indicator** on the other two. The only thing that settles "free" is the
**instruction census** — who writes the cell, and what every read-modify-write preserves.
⊕ Its mirror image, from the same census: `0x14A`'s byte-transparency was proved by a **counterfactual**
(85.5% of frames would have carried a wrong checksum under the competing model) rather than by an
absence. **Design the observation so the two hypotheses predict different data.**
⊕ And the build-time corollary: **enumerate a comparator's whole input range** — the `sar`-floor
asymmetry (16,385 values checked) and the `ld.h`/`st.h` one-bit trap were both caught by gates, not by
review. See [[accord-two-cave-encoding-traps-sar-floor-and-opcode-bit]].

### What is honestly unresolved after this session

- **What DOES move the 26–31 Hz ring.** Dose is out; shape is untested as a separate axis; the
  100 Hz ZOH says a table damper is **anti**-damping up there at all.
- **The seventh V38-rebase lever is named but the audit's count implies one more is not itemised.**
  The lever list is not proven exhaustive.
- **`0x18F`'s end-to-end transparency** — [BELIEF] only. Settle it with one non-stock pattern in
  `0x18F byte4[2:0]` flown alongside a live `0x14A` write as an in-flight positive control.
- **The macro ratchet is still uninstrumented.** Two detectors, 64/65 comparisons inside their own
  nulls, both failing their own positive control. Nothing this session changes that.
- **V84 is UNFLASHED**, and lever B is known **not** to be the highway answer — V67/V68 flew it and the
  highway grind persisted.
  🛑 **STALE — V84 FLEW as route `6d` on 2026-08-09, and V85 flew as route `6e` the same day.** See below.

---

## 2026-08-09 (late) — V85 FLEW, THE LEVER DELIVERED INTO A NULL, AND THE RATCHET CHANGED CLASS

```
V85 flies route 6e, fault-free, STEER_STATUS = {0: 43,641}
  |    [[accord-v85-flew-lever-delivered-bands-are-null]]
  |
  +--> THE LEVER DELIVERED:  relay saturation 33.3% -> 4.6% engaged (7.21x)
  |     both pre-registered duty predictions hit
  |         |
  |         v
  |    ...INTO A CLEAN NULL IN EVERY BAND
  |     6-9 Hz 1.088 [0.746, 1.451] · 18-22 Hz 1.347 [0.947, 1.758]
  |     negative control 32-38 Hz 1.007 · IMU roughness 0.958 (V85's road SMOOTHER)
  |     split-half null [0.63, 1.50] wide
  |         |
  |         v
  |    OPERATOR: "ratcheting was still unfixed"     <- THE VERDICT THAT OVERRIDES
  |
  +--> so: is the mechanism a RELAY at all?
        |
        v  odd/even comb 0.858 [0.739, 1.000]  vs a positive control at 1.204 on 15% injection
           PLV z <= 1.05 · time-locking -0.0375 · no 3rd harmonic (2nd method)
        |
        +--> NOT A RELAY  =>  refutes FUN_00038148 / gp-0x6b70 as the ~8 Hz generator
        |
        v  the wheel-on-torsion-bar mode is 12.8 Hz [12.1, 13.6] -- ABOVE the ratchet
        |
        +--> NOT A PLANT RESONANCE (7.79 Hz unreachable through the plant, 12.65 Hz floor)
        |
        v
   *** A LINEAR LOOP OSCILLATION set by accumulated estimator lag ***
        [[accord-ratchet-is-a-linear-loop-oscillation]]
        |
        v
   THE LEVER CLASS IS PHASE / LAG -- and NOTHING since V38 has ever moved it
        |
        v
   V86 = ONE cell 0xC40D4 573 -> 286, pre-registered as a FREQUENCY RATIO [0.797, 0.875]
        [[accord-v86-built-the-frequency-lever]]
```

### The load-bearing edges this session created

| edge | direction | rationale |
|---|---|---|
| `ratchet-is-a-linear-loop-oscillation` → `fun3b8f6-coulomb-relay-proportional-to-command` | **BOUNDS it** | the relay was real and worth fixing, but it is **not** the ~8 Hz generator; the lever delivered into a null |
| `ratchet-is-a-linear-loop-oscillation` → **every magnitude lever in the kit** | **RE-AIMS the whole search** | a magnitude lever on a linear loop mode changes amplitude at best and raises loop gain at worst. **What moves a loop mode is phase.** |
| `ratchet-is-a-linear-loop-oscillation` → `ratchet-characterised-on-route-4f` | **COMPLETES it** | that node had the frequency, the speed-invariance and the "not in the command" fact but no mechanism; this one supplies it |
| `v85-flew-lever-delivered-bands-are-null` → `v84-flew-and-fixed-the-highway-ring` | **CANNOT test it** | route `6e` has **22.4 s** engaged ≥80 km/h ⇒ the ring result neither replicates nor regresses. **UNMEASURED, not confirmed** |
| `plant-model-residual-aggregator-chain` → `aggregator-reaches-motor-via-gp6acc-bridge` | **EXTENDS it upstream** | the bridge closed the *output* half; this closes the *input* half — where `gp-0x6ad6` comes from |
| `levers-killed-2026-08-09` → `factord-is-the-angle-error-lever` | 🛑 **REFUTES its headline** | `gp-0x6a10` is **absolute steering angle**; FactorC's zero dead zone precedes FactorD ⇒ **this firmware has NO frequency-selective lever**, which also removes the argument that FactorE cannot do what FactorD can |
| `levers-killed-2026-08-09` → `c407e-is-the-fault-interlock-c63a0-exonerated` | **completes the `0xC63A0` story** | exonerated of the faults there; **shown INERT here** (`ch₀` = 0 on 98.8% of engaged frames) ⇒ V84's own revert of it was inert too |
| `falsifier-only-fires-if-it-could-have-fired` → `size-probe-rungs-against-lane-reachable-output` | **GENERALISES it** | that node was about rungs; this one extends the same rule to **abort criteria and exposure**, including ones that come back **clear** |
| `smoke-test-ghidra-tools-at-agent-spawn` → every tracer brief | **gates their nulls** | a blind tracer emits output shaped exactly like a genuine negative, and in this kit nulls are load-bearing |

### Edges REDRAWN (retractions and corrections)

- **`0xC40BC`: "revert if it does not help" → FREEZE.** The disposition flipped when the mechanism was
  corrected: the single-input describing function does not apply because **the ring rides on a bias
  5–10× its own amplitude**. **Spent ≠ wrong.** [[feedback-right-answer-wrong-reason-is-a-coincidence]]
- **"Harmonic injection" → PARAMETRICALLY SWITCHED DAMPING.** At cal 600 the damping switched **fully
  off** on 87% (6–9 Hz) / 96% (18–22 Hz) of symptom frames. Different mechanism, same cell.
- **"V85 is 1.625× worse than V81 at 6–9 Hz" is a WHEEL-ORDER ARTEFACT** — order-cleaned it is
  **1.273 [0.853, 2.507]**, inside the null. The 18–22 Hz result survives (1.957 → 1.928).
  ⊕ Reinforces [[accord-averaged-spectrum-needs-matched-speed-distributions]].
- **"V85's ~8 Hz line is 3.2× more prominent" is a FLOOR EFFECT**, not an amplitude increase.
- **Lever A's int16-overflow ceiling is WITHDRAWN** — the intermediate is 32-bit
  (`5120 × 5244 >> 9 = 52,440` fits). **Do not cite an r24 overflow ceiling.** The
  do-not-restore verdict survives **on the manual-arm leg alone**.
- **`0xC61F6` 3 → 0 flips from candidate to forbidden.** A deadband is the **dual** of a relay;
  deleting it **adds** small-signal gain — the destabilising direction.
- **`gp-0x67fa`'s reachable set is {11} alone** ⇒ **`0x454FE` is MEASURED INERT**, not merely
  unexercised. Keep the byte; never justify a build on it.
- **`0xC63A0` ledger:** reverted at **V83a** not V84; **V76g also carried 2048**; **V76/V80 are 1024**.

### What is honestly unresolved after this session

- **Ratcheting is unfixed** and still has no instrumented history beyond the frequency line itself.
  V86's frequency test is the first probe aimed at it since V72.
- **`Y[0]` of the `FUN_00038148` RAM LERP** is `ep`-relative and unresolved — anything that clamps or
  scales that LERP is un-sizable until it is closed.
- **3 of `0xC6200`'s 15 readers are unidentified** ⇒ **RULE 11 is not satisfied on it.**
- **The ~20.90 Hz creep line** rests on **n = 6** windows on V84 — suggestive, not measured.
- **Micro- vs macro-ratcheting are not separated**, and this session could not separate them.
- **V86B's damper creep hypothesis** is `[BELIEF]`; what settles it is a **drive protocol, not a build**.
- **The 26–31 Hz band and the highway regime have NO V85 measurement** — route `6e` lacked the exposure,
  and no verdict on them may be carried forward from this flight in either direction.

---

## 2026-08-13 (later still) — record-repair edge: the `0xC6200` collision, defused

### Edge added

| edge | direction | rationale |
|---|---|---|
| `accord-c6200-clamps-the-pid-reference` ↔ `accord-aggregator-never-rails-loop-is-linear` | **same number, different cell, both nulls stand** | both measure whether a signal reaches ±8192, at two DIFFERENT points in the chain (`gp-0x6ad6`, the PID's reference, upstream · `gp-0x6b94`, the aggregator output, downstream). Read together carelessly, V65's confirmed null ("never rails") reads as having already answered V100's open question ("does the PID-reference clamp bind?") in the negative — **it has not.** A fully railed `gp-0x6ad6` contributes only ≈2,101 counts at `gp-0x6b94`, well inside V65's own NEUTRAL band, so the two nulls are **compatible, not redundant**. [BELIEF, safe direction only — uses the unsaturated 0.2565 as a linearisation to show non-preclusion, not to predict a duty.] |

Full reconciliation written into both memory files directly (`accord-c6200-clamps-the-pid-reference.md`
carried it from the start; `accord-aggregator-never-rails-loop-is-linear.md` got it added this pass so
a reader landing at either file first sees the same defusal).

### RESOLVED from "What is honestly unresolved after this session" (2026-08-09 entry, above)
> *"3 of `0xC6200`'s 15 readers are unidentified ⇒ RULE 11 is not satisfied on it."*

**RULE 11 on `0xC6200` is now COMPLETE** — `tracer-6ad6` identified the three as `0x3a7a2`/`0x3a7b2`/
`0x3a7c4`, the PID's own clamp on `gp-0x6ad6` (crux verified by the team lead in Ghidra). The cell
is now known to be **FOUR distinct things** (friction lane, `gp-0x6b70`'s output clamp, Stage-2 LERP
`Y[9]`, and the PID reference clamp) plus one still-unchased reader at `0x39ff6`.

### 🛑 THE GENERALISABLE ROOT CAUSE — not about this cell
Every build script since V90 labels `0xC6200` as *"gp-0x6b70's clamp"* (`build_v96_tva.py:701`,
`v97:164`, `v98:677`, `v99:438`) — **one of its four roles, presented as if it were the only one.**
That single mislabel is what kept the PID-reference role invisible for **ten builds**, even though the
cell was read/discussed in every one of them.

⇒ **A cal cell with multiple roles, labelled by only one of them, is a latent wrong answer.** The
label reads as complete because it IS accurate for the role the labeller was thinking about — the
failure is silent, not a visible gap. **Before naming any multi-reader cell in a build script or a
lever proposal, check ALL of its readers, not just the one the current task cares about**, and if the
label only covers one role, say so in the label itself (`"gp-0x6b70's clamp (1 of ≥4 roles)"` rather
than `"gp-0x6b70's clamp"`). See [[accord-check-build-lineage-before-proposing-lever]] for the sibling
discipline (grep the lineage before naming any cal address) this one completes.
