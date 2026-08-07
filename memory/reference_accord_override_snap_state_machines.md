---
name: reference-accord-override-snap-state-machines
description: "[EXTENDED 2026-05-30 — Trace A: SM1 arm tp+0x71de=0xC61DE=2048 + SM3 arm tp+0x71dc=0xC61DC=30720 PINNED; all 3 SMs are COMMAND-driven via integrator gp-0x3570 (NOT column velocity — a swarm agent's velocity-seed claim was a misread, corrected by reading L663-720); SM1 'scale puzzle' RESOLVED (the |cmd| compare operand uVar19 = cal tp+0x71de, NOT the Q15 node); gp-0x4f60 identity UPGRADED to [STRONG]=angular velocity; cal-dump 0x741c/0x741e was mis-slotted (real: 0x741c=32440, 0x741e=16384, 0x7420=0=SM3 cut value); V19 high-end-2× BUILT = proportional rescale 0xC6422 16384→32768 + 0xC61DC 30720→61440, 49/49 CRC, UNFLASHED.] VERIFIED 2026-05-29 (3 firmware-codepath-tracer subagents, instruction-level): the Accord EME snap is THREE redundant authority-gate state machines inside s_motor_torque_rate_shaper (FUN_00042af8), OR-linked by a 3-way MIN. SM1 (state gp-0x355d, node gp-0x6960, phase gp-0x6786, counters gp-0x6a74[ceiling=12 immediate @0x43626]/gp-0x6711), SM2 (state gp-0x355e, node gp-0x6962, phase gp-0x6785, counters gp-0x6710/gp-0x6a72, substates gp-0x3560/gp-0x3561[±1 dir latch]), SM3 (state gp-0x355f, node gp-0x6787, accum gp-0x3568). Cut math: authority=min(node1,node2,node3) @0x439c0; demand = blend × authority >>15 @0x43a3a; nodes ∈ {0,0x8000} Q15 (0x8000=unity, 0=cut → gp-0x6b98=0). node=0 BYPASSES slew @0x439d8 → INSTANT snap; recovery RAMPS via slew step sp+0x38 (~10s ratchet). SM2 magnitude ARMING threshold = tp+0x7422=0xC6422=16384=exactly 50% of Q15 0x8000 (read @0x436f4/0x43746, bytes 00 40); stock full LKAS authority ~15360 sits JUST BELOW 16384 → SM ~never arms at 1×, 2× sails past → arms (this is why EME is 2×-only). Fight ref gp-0x6af8 (0xFEDF1508) written once @0x42c3a = gated gp-0x4f60 (gate ±0x6400). SM1 trigger (decompile L883-885): velocity-arm (tp+0x71e0=0xC61E0 < |gp-0x4f68|) AND |cmd|>current-node AND (cmd×dir×gp-0x6af8<0 = cmd OPPOSES gp-0x6af8) AND polarity. SM is LOCAL: all 6 SM vars accessed ONLY in the shaper (program-wide search + get_xrefs_to = zero external), sets NO local DTC/inhibit, NOT lockstep-shadowed — but the TRIP is broadcast to another core: post-SM block 0x43d0c-0x43de8 reads phase bytes, on phase==3 sends CSIG msg 0x2a via FUN_00016de6 EVERY cycle. Re-confirmed: dual-path int/float monitor (gp-0x3564 +10/-5/thr100; fault 0x3f1b via FUN_000462e6→FUN_00056518) is REPORT-ONLY (does NOT gate torque). Non-verified companions (semantics of gp-0x4f60, the safety purpose, the minimum-edit) live in analysis-2020accord/EME_OVERRIDE_SM_NONVERIFIED.md. tp=0xBF000, gp=0xFEDF8000."
metadata:
  node_type: memory
  type: reference
---

The mechanism behind the 2020 Accord (`39990-TVA-A160`, V850E2, code.bin) EME snap, established 2026-05-29 by three `firmware-codepath-tracer` subagents reading the disassembly instruction-by-instruction. This supersedes the loose "override SM `gp-0x6960` is the cut node" framing in [[reference-accord-eme-lever-semantics]] / [[reference-accord-driver-override-plausibility-eme]] with the full structure. Bases `tp=0xBF000`, `gp=0xFEDF8000` (see [[reference-accord-pointer-base-audit]]). All claims here are [V] instruction-grounded; interpretive/unverified claims are NOT here — they live in `analysis-2020accord/EME_OVERRIDE_SM_NONVERIFIED.md`.

## The snap is THREE redundant authority-gate state machines, OR-linked [V]

All inside `s_motor_torque_rate_shaper` (`FUN_00042af8`):

| | State byte | Node (Q15 gate) | Phase byte | Counters | Substates |
|---|---|---|---|---|---|
| SM1 | `gp-0x355d` | `gp-0x6960` | `gp-0x6786` | `gp-0x6a74` (ceiling **12**, immediate @`0x43626`), `gp-0x6711` | — |
| SM2 | `gp-0x355e` | `gp-0x6962` | `gp-0x6785` | `gp-0x6710`, `gp-0x6a72` | `gp-0x3560` (phase-A), `gp-0x3561` (**±1 direction latch**) |
| SM3 | `gp-0x355f` | `gp-0x6787` | — | accum `gp-0x3568` | — |

Each node holds **`0x8000` (Q15 unity = full LKAS authority) or `0` (cut)**.

## Cut math [V — Agent B, instruction addresses]

```
0x439c0:  authority = min(gp-0x6960, gp-0x6962, gp-0x6787)        ; 3-way MIN (OR-link: any node=0 wins)
0x43a3a:  demand    = blend(shaped, command) × authority >> 15    ; Q15 multiply
          → demand → ±0x2000 clamp → gp-0x6b98 → FOC
```
authority=0 → demand=0 → `gp-0x6b98`=0 → motor torque removed → self-aligning torque returns wheel to center = **the snap**. **Any single SM** zeroing its node is sufficient.

## Cut is INSTANT, recovery is RAMPED — and 🛑 **IT CANNOT LATCH** [V — Agent B @0x439d8-0x439ea; recovery branch re-decompiled 2026-08-06]

At the slew stage, a node value of 0 is **detected and BYPASSES the slew** → the gate snaps to 0 in one tick (the abrupt cut). The opposite direction (re-engage) ramps back up through slew step **`sp+0x38`** — this is the ~10 s ratchet recovery. (`sp+0x38` is a caller-passed stack value, not yet mapped to a cal address — see TODO.)

> 🛑 **CORRECTION 2026-08-06 — THE SM1/SM2/SM3 CUT CANNOT LATCH.** [EVIDENCE, fresh decompile] the
> authority-node **recovery branch is a single fixed-step rise with NO bypass condition**, regardless of
> which SM caused the cut ⇒ **it self-clears, always.** Any claim that this mechanism produces a
> *latched* loss of power steering — including as a candidate for V74's or V75's hard fault — is
> **wrong**; a latch requires the DTC-eligibility chain
> ([[reference-accord-monitor2-corridor-and-the-c64a4-trap]],
> [[accord-descriptor-bit13-is-the-fault-fingerprint]]).
>
> ⊕ **`gp-0x3570` is a PURE UNATTENUATED INTEGRATOR** — it adds the **entire** `(cmd − bound)` every
> 1 kHz cycle, **not** ¼ per cycle. A sustained **100-count excess arms SM2 in 153 ms**. Any dwell-time
> reasoning built on a ¼-per-cycle tracker is void.
>
> ⊕ **Measured near-inert on-car:** V54 read authority **≤ 119 over 5,989 frames** against a **3,073**
> knee — see [[reference-accord-v54-flashed-authority-is-zero-by-design]]. And **boost-floor margin
> erosion is REFUTED as the V75 cause** (margin **+215** clamp-sum / **+481** realized, never crossing
> zero).

## The arming threshold is the whole story for "why 2×-only" [V — Agent C]

SM2 only arms when LKAS demand magnitude reaches **`tp+0x7422` = `0xC6422` = 16384 (`0x4000`) = exactly 50% of Q15 full-scale (`0x8000`)** (read @`0x436f4`/`0x43746`; `read_memory` = bytes `00 40`). **Stock full LKAS authority ≈ 15360 — just below 16384** → the SM essentially never arms at 1×. The 2× build pushes demand to ~30720, sailing past 16384 → the SM arms during normal strong-LKAS operation. This single fact explains why the EME is a 2×-only phenomenon.

## The "fight" reference and SM1 trigger [V — Agent A disasm of the writer]

`gp-0x6af8` (abs `0xFEDF1508`) is written **once** @`0x42c3a` (`st.h r14`) = **gated `gp-0x4f60`** (zeroed if `|gp-0x4f60| > 0x6400`=25600). SM1's cut-arming boolean (decompile L883-885):
```
(velocity arm: cal tp+0x71e0=0xC61E0 < |gp-0x4f68|)   // column moving fast enough
 AND (|command| > current node value)                  // LKAS pushing past its gate
 AND (command × direction × gp-0x6af8 < 0)             // command OPPOSES gp-0x6af8
 AND (command polarity term)
```
i.e. the trip fires when a high-magnitude LKAS command **opposes `gp-0x6af8`** while the column is moving and the condition is sustained (the counters). *What `gp-0x4f60`/`gp-0x6af8` physically is (column angular velocity per Agent A vs torque per Agents B/C) is NOT settled — see the non-verified doc.*

## The SM is LOCAL but reports its trip to another core [V — Agent C]

- All six SM variables (`gp-0x6960`/`6962`, `gp-0x355d`/`355e`, `gp-0x6785`/`6786`) are accessed **only inside the shaper** — program-wide `search_instructions` per offset + `get_xrefs_to` on every absolute address returned nothing external.
- The SM sets **no local DTC/inhibit** and calls **no fault reporter** within the SM region (no `jarl` between `0x4353c`-`0x439c0`).
- It is **NOT lockstep-shadowed** (no `FUN_0006b9fa` on SM vars); the three copies are independent redundant channels, **not cross-checked against each other**.
- BUT the post-SM block (`0x43d0c`-`0x43de8`) reads the phase bytes and, on **phase==3 (tripped)**, broadcasts a **CSIG frame msg `0x2a`** via `FUN_00016de6` **every cycle** to another core. So suppressing the local cut would NOT hide the event from that core (nor from the CAN `0x427` motor-torque bus).

## Cal constants read in the SM region [V — Agent C, read_memory]

`tp+0x7418`=10 (`0xC6418`), `0x741a`=0, `0x741c`=0, `0x741e`=32440 (`0x7EB8`), `0x7420`=0, `0x7422`=**16384** (arming gate), `0x7424`=29491 (`0xC6424` — the "deadband" of [[reference-accord-eme-lever-semantics]], reused here as a **dwell timeout** for `gp-0x6a74`). Counter ceilings `gp-0x6711`/`0x6710`/`0x6a72` and slew steps are caller-passed **stack** values (`sp+0x9`/`0xc`/`0x2c`/`0x34`/`0x36`/`0x38`), not yet traced to cal addresses.

## Two re-confirmations this session [V]

- The **dual-path int/float consistency monitor** (`gp-0x3564` leaky integrator +10/−5/threshold 100; `gp-0x3550`; flags from `FUN_00043e44`; fault code `0x3f1b` via `FUN_000462e6` → telemetry packer `FUN_00056518`) is **REPORT-ONLY — it does NOT gate torque.** It has the same ~10-tick sustained signature but is not the cut.

  > # 🛑 **THIS BULLET IS WRONG — RETRACTED 2026-07-18. Do not rely on "REPORT-ONLY".**
  >
  > It conflates **two** monitors, and the one it names by accumulator (`gp-0x3564`) is the **hard-shutdown** one.
  >
  > - **Monitor 1** = `FUN_00042af8` (shaper), accumulator **`gp-0x3564`** (int, +10/cycle, thr 100) → `+0x400` → sum ≥128 → `FUN_0004613e` → `FUN_00016de6(0x1c, …)`.
  > - **Monitor 2** = `FUN_00043e44` (watchdog), accumulator **`gp-0x3550`** (float, +0.001/cycle, thr 0.01 ≈10 cycles) → `+1024.0` → sum >128 → `FUN_000462e6` → `FUN_00016de6(0x1d, 0x3f1b, 1, 1)`.
  >
  > `gp-0x3564` is traced at instruction level **all the way to motor-off**: `FUN_00016de6` → `FUN_0001611e` (bits `0x41` gate) → `FUN_00018738` → `gp-0x685c`=1 → `FUN_00018bc0` (`gp-0x3ef8`=1) → `FUN_00019f7c` → `gp-0x67fa`=8 → `FUN_0001a16a` → `FUN_00045608(3,0,0x8000,0x8000)` **motor off** → `gp-0x3ee8`=1 latch, **power-cycle to recover**. This is the V25/V26 brick mechanism. It unambiguously *does* gate torque.
  >
  > Monitor 2's trip is also **reachable**: its fault-SM enable gate is `0xC64A4` = `0x00` = **ENABLED** (verified on stock bytes). A prior pass misread it as `0xC74A4` = `0xEA` — an off-by-`0x1000` tp+disp slip — and wrongly declared Monitor 2 permanently gated off.
  >
  > Still **[UNVERIFIED]**: whether index `0x1d` is hard-fault-eligible (bits `0x41`), and the `0x1d` ↔ `0x49` ↔ `0xF00049` mapping. Full model: [[reference-accord-watchdog-fault-sm-fun43e44]].
- In `m_steer_torque_arbitration`, the **setpoint magnitude limit** (`g_pArbSetpointLimitCurves` ≈15360 @`0xE4180`, mode-indexed by `gp-0x674e`) is applied **before** the output gain `tp+0x746c`=`0xC646C` (decompile L127-208 vs L1271-1288). The current V14/V18 2× (gain at arb OUTPUT) therefore sits **after** the authority limit → it re-inflates LKAS past the envelope the SMs guard. A setpoint-stage gain that leaves the 15360 limit stock keeps demand **below the 16384 arming threshold** at full command. See [[reference-accord-arbitration-limit-family]], [[project-accord-torque-mod-v0]].
- `gp-0x6b98` is the **MERGED** command (base driver assist `gp-0x6bf0` + LKAS summed) → a gain downstream of it (FOC q-ref) would double **driver assist** too. The LKAS-specific gain must stay at the setpoint/arb, upstream of the merge. (Confirms [[reference-accord-lkas-delivery-and-governor]].)

## Implication for the 2× goal

Full-command 2× **authority** and the EME are the same lever seen two ways: the SMs exist to catch sustained high LKAS authority opposing the steering, and full-command 2× *is* that. Safe path = setpoint-gain that self-caps at stock authority under the 16384 gate ([[project-accord-torque-mod-v0]], the V12A `shl3` lever @`0x526d2`). High-end 2× would require rescaling the SM arming thresholds (lead candidate `tp+0x7422` `0x4000`→`0x8000`, plus un-pinned SM1/SM3 companions) — a genuine loosening; details + open traces in the non-verified doc and `20260529-11pm-TODO.md`.

## Trace A resolution — SM1+SM3 arming pinned, command-driven seed confirmed, V19 built [V 2026-05-30]

4-agent `firmware-codepath-tracer` swarm + operator-directed re-verification (decompile `FUN_00042af8` L615–1196 read instruction-level). Closes the open SM1/SM3 traces from the non-verified doc §4.

- **All three SMs arm off the COMMAND-magnitude path, NOT column velocity.** The integrator `gp-0x3570` slews toward `uVar25 × 0x8000`, where `uVar25` = the LKAS command (`gp-0x6acc`, mode-gated at L651). Then `uVar53 = |gp-0x3570 >> 15|` and `uVar34 = uVar53 × (tp+0x71da=1092) / 1024`. (A swarm agent claimed a `gp-0x4f60` column-velocity seed "at L219" — that is the `gp-0x6af8` *writer*, a **misread**; corrected by reading L663–720.) This is the mechanism behind "2×-only": 2× command drives the integrator higher → crosses the gates that 1× sits under.
- **SM1 "scale puzzle" RESOLVED.** The arming compare `uVar19 < |uVar25|` (L884) uses `uVar19 = cal[tp+0x71de] = 0xC61DE = 2048` (loaded at L756), **not** the Q15 node `0x8000`. The node reassignment `uVar19 = *gp-0x6960` happens only *afterward*, inside the action branches. SM1 magnitude arm = `|cmd| > 2048` AND col-velocity > `tp+0x71e0`(7168) AND command opposes `gp-0x6af8`. (SM1 is therefore NOT the 2×-only culprit — its 2048 floor is already crossed at 1×; it is velocity+opposition-gated.)
- **SM3 arming PINNED.** SM3 cuts when the integrator **saturates** (`uVar53 ≥ cal[tp+0x71dc] = 0xC61DC = 30720`, = its own clamp ceiling) for `tp+0x7298`(20) cycles. `30720 = 2 × 15360` (stock full authority) — a designed-at-2× guard. `tp+0x71dc` is simultaneously the integrator clamp AND SM3's trip.
- **Complete arming-threshold set (cal-addressable):** SM1 `tp+0x71de`=2048 · SM2 `tp+0x7422`=16384 · SM3 `tp+0x71dc`=30720.
- **`gp-0x4f60`/`gp-0x6af8` identity UPGRADED to [STRONG] = column/motor ANGULAR VELOCITY** (Q10; the recurring `0x6400`=25600=25×1024 clamp + the `<25.0` float gate after ×(1/1024)). So the SMs are **anti-oscillation / fight-on-motion** monitors. (Residual [OPEN]: `gp-0x6b50` ultimate source is a register-indirect/HW write not statically resolved.)
- **Cal-dump correction (minor):** the 2026-05-29 dump mis-slotted by one halfword. Actual: `tp+0x741c`=32440, `tp+0x741e`=16384, `tp+0x7420`=**0** (= the value `uVar54`/SM3 node takes when SM3 trips → cut), `tp+0x7422`=16384, `tp+0x7424`=29491. The load-bearing 0x7422/0x7420 are confirmed correct.
- **Recovery cals (shaper single caller `w_steer_control_task` @0x2214a):** `sp+0x38` rise/recovery step ← LERP `tp+0x7a28`(=6); `sp+0x36` fall step ← `tp+0x7a18`(=197); counter ceilings `tp+0x74fe`/`0x74ff`(=5), `tp+0x729a`/`0x729c`(=200); dwell `tp+0x7298`(=20).
- **High-end-2× minimum edit, BUILT as V19 (`build_v19_tva.py`), UNFLASHED:** proportional rescale `0xC6422` 16384→32768 (SM2) + `0xC61DC` 30720→61440 (SM3 + integrator clamp; arithmetic-safe: `0xF000×0x8000 = 0x78000000 < INT32_MAX`). SM1 left stock. Preserves each monitor's RELATIVE trip point at 2× (rescale, not defeat). 49/49 CRC, ECU-decode==patched, 17-byte diff. See [[project-accord-torque-mod-v0]].
- **Residual [OPEN] (do not over-claim):** the command full-scale is ambiguous (mode gate at L651 caps `uVar25` to ±0x2000/0x3000 in modes 0/2; the ~15360 reading that makes the SM3 edit *necessary* needs the active mode to bypass it — `FUN_000074c4[tp+4]` UNVERIFIED). If full-scale ≈8192, only 0xC6422 is needed and the 0xC61DC edit is harmless-but-inert. WHICH SM fires in the real EME is still undiscriminated on-car — CAN `0x427` capture remains the discriminator and would pin the scale. Working doc: `analysis-2020accord/EME_OVERRIDE_SM_NONVERIFIED.md` §0.


## 2026-05-30 — drive-data resolution + corrections (see analysis-2020accord/SESSION-2026-05-30-EME-RESOLUTION.md)
Full detail in `analysis-2020accord/SESSION-2026-05-30-EME-RESOLUTION.md`. Headline corrections
to the records above:
- **Mode-0 integrator gp-0x3570 is an ACCUMULATOR of (command − envelope), not a tracker** →
  SM2 AND SM3 ARE reachable; **V19 edits are LIVE** (prior "V19 inert" reasoning was wrong;
  operator's V18-vs-V19 difference was the correct disproof).
- **Shaper runs at 1000 Hz (1 ms/cycle)** [STRONG], not 100 Hz. Dwell cals: SM2 `tp+0x74ff`
  (0xC64FF)=5 (~5–6 ms, counter gp-0x6710); SM3 `tp+0x7298`(0xC6298)=20 (~20 ms). Dwell is a
  near-useless lever vs a ~1.2 s (1200-cycle) event.
- **SM3 genuinely cuts to 0**: cal `tp+0x7420`(0xC6420)=0 is the node value on SM3 trip
  (a prior tracer's "SM3 only reduces authority" was wrong).
- **SM3 arm `tp+0x71dc`(0xC61DC) max = 0xFFFF** (16-bit field; clamp=cal<<15 stays positive
  int32). SM2's uVar34=(uVar53*1092)>>10 truncates 16-bit → wraps at uVar53~61454; only affects
  SM2, which arms far below in all builds. SM2 practical ceiling for "3×" = 49152.
- **Envelope is LIVE during turns**: bounds = LERP tables `tp+0x7748`/`tp+0x7754` (plateau
  ±1024, X=gated col velocity gp-0x4f60) × polarity gp-0x6752 (±1, never 0). The "inert in
  mode 0" claim conflated gp-0x6752 with command-mode byte tp+0x74c8=0.
- **The logged EME** (sustained ~1.2 s opposing command, column stationary at the cut, trips on
  V19) = SM2/SM3 wind-up. SM1 ruled out (needs live column velocity). All OFF-shaper instant
  cuts ruled out for the hands-off case (observer-edge=jerk detector; fault-bit-8=dwell;
  gp-0x67f4=sensor-loss→rate not cut; gp-0x67a4=torque-blind handshake). **gp-0x4e65 is NOT on
  the LKAS path** (resolver cluster) — the EME-doc suspect is mislocated.
- Builds: V20A (SM3 max), V20B (SM3 max + SM2 3×) — see project memory.

## 2026-06-03 — the integrator BOUND that arms these SMs is a gated 3-way max/min; V30 EME = bound collapse; V31 = boost floor
The SM2/SM3 arming integrator `gp-0x3570` winds up on `(command − bound)`, where **bound = MAX/MIN(corridor,
IIR gp-0x3574, boost)** (the same 3-way wall, built `0x43136–0x43156`). Each arm is conditionally gated, and
**both the corridor's authority-gate (`0x43114`) and a boost-zeroing SM (`gp-0x3562`, `0x42fb8–0x43016`, latch
at authority > cal `0xC641E`=16384 for ~`0xC64E3`=20 cyc) key off `r13 = gp-0x6966 = (|gp-0x3570>>15|×cal
0xC61DA[1092])>>10` = the authority magnitude** (= the same uVar34 that arms SM2 at `0xC6422`). The corridor is
ALSO the DRIVER-OVERRIDE arm (off when `|gp-0x6bf0|≤9216` = hands-off). On a hands-off held turn all three arms
collapse (corridor off, boost≈0 no rate, IIR decays) → the 2× command winds the integrator → SM2/SM3 cut =
**the V30 residual soft EME** (FLASHED, drove well otherwise). **V31** floors the boost arm (ON at authority≈0)
so the bound stays ≥4096 > command 3584 → integrator can't wind up → these SMs never arm (self-stable). Full
model: [[reference-accord-soft-eme-bound-arm-gating]]; build `build_v31_tva.py`, handoff
`docs/HANDOFF-2026-06-03-v31.md`.
