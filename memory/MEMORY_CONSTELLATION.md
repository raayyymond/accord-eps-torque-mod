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

**Also corrected in place:** an agent-memory verdict *"Monitor 2 PERMANENTLY GATED OFF, never needs fixing"* rested on an **off-by-`0x1000`** tp+disp slip — the gate is `tp+0x74a4` = **`0xC64A4` = `0x00` = ENABLED**, not `0xC74A4` = `0xEA`. Struck through in place; that conclusion would have told a future session to skip mirror discipline during corridor work.

### 2026-07-19 — Era: V38 on-car clean, V39 direct-rate vibration experiment

V38 moved from static candidate to **flashed and fault-free**. Remaining behavior separates into a several-Hz
hard-turn ratchet and a common tens-of-Hz high-LKAS vibration at low and high road speed. Strong driver torque
moves the wheel quickly without either symptom, contradicting an intrinsic moving-motor limit. The direct
Sensor-B torque-rate lane (`gp-0x4f62 -> r24`, up to +/-8192) is cadence-compatible with the vibration; the
independent governor remains a possible stateful ratchet participant. Revised V39 suppresses all `r24` signs
at the exact V9 full-scale equivalent (`|LKAS lane|>=417`) and low driver torque, leaves adaptive `r26`, every V38 calibration, and the governor
unchanged, and does not claim the ratchet is solved. The live golden edge map is
`analysis-2020accord/eps_lkas_chain_model.py`; update it continuously and prefer it over stale prose.
