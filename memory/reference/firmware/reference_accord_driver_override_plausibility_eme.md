---
name: reference-accord-driver-override-plausibility-eme
description: "⚠ CORRECTED 2026-05-27 (4-analyst Ghidra review in ../assessment/ + road test): the V16 'slew re-enable' fix is REJECTED — 0xC61D6=0 FREEZES a dormant speed×torque 2D shaping lane (it is NOT a disabled output damper); 0→14 ACTIVATES an uncalibrated map. V17 deadband-only is INERT (slew=0 pins gp-0x356c at 0). The real EME command-cut is the override state machine node gp-0x6960, NOT the shaper deadband. V18 = 2× + ramp-only (0xC64DE 17→27, cal-only, NO code patch / NO trampoline) is FLASHED + road-validated (drives well). Lever semantics: [[reference-accord-eme-lever-semantics]]. ⚠ SAFETY: the Accord 2x build (V14/V15A/V15B, arb-output gain 0xC646C 891→1782 + clamps 0xC61B2/B4 512→1024) has a recurring EPS-misbehavior event (EME) on sharp LOW-SPEED turns where the driver adds significant hand torque: LKAS abruptly zeroes (wheel snaps straight), steering degrades (heavy + jerky/ratcheting) for ~10s, then recovers — sometimes feeling over-light after. ROOT CAUSE (mechanism Ghidra-verified): the doubled arb-output gain AMPLIFIES a pre-existing driver-override / column-torque-sensor plausibility inhibition. WHERE DRIVER INPUT ENTERS: the column torque sensor (dual-coil, 5 ADC channels gp-0x6a44/40/3c/38/46) → plausibility voter FUN_00041eec → fused driver torque gp-0x6a5e (0xFEDF15A2) + converge/plausible flag gp-0x67f4 (0xFEDF180C). gp-0x6a5e is the axis of g_pArbSetpointLimitCurves (LKAS limited as a function of driver torque) AND the gates that ZERO the LKAS integrator. Delivered LKAS = clamp((integrator+term)×polarity×GAIN[0xC646C], ±[0xC61B4]) × ENABLE, ENABLE = (byte 0xFEDF195C ∈ {2,3}); gain applied AFTER the integrator so any given wind-up reaches the wheel at 2x. The exact gate that fires in the EME (override-curve collapse vs transient dual-coil disagreement vs +0x7D00=32000 one-sided ceiling) is NOT discriminated statically — needs bench RAM or CAN 0x427 + steering-torque logging."
metadata:
  node_type: memory
  type: reference
---

> ## ✅✅ CORRECTION + RESULT 2026-05-27 (LATEST) — 4-analyst Ghidra review dismantled the slew/deadband story; V18 (ramp-only) FLASHED + drives well
>
> A multi-analyst disassembly review (`../assessment/`, 11 rounds, decode-verified) overturned the V16 mechanism in the block immediately below, and the operator road-tested the survivor. Distilled:
> - **V16 REJECTED — the slew framing is INVERTED.** `0xC61D6` (`tp+0x71d6`, read once @`0x43350`) is NOT a "disabled delivered-command limiter." It is the **step size** of a rate limiter on an internal persistent state `gp-0x356c` (exactly 2 refs in the whole program: read @`0x434ce`, store @`0x43504`). step=0 ⇒ that state **freezes/pins at 0** = a dormant lane contributing nothing. Setting 0→14 **ACTIVATES an uncalibrated speed×torque 2D shaping map** (target = curve@`0xC6770` × curve@`0xC69E8`, `25·r8>>10`) onto the live command via mux byte `0xC64C9`=0 → `r28`→`r20`→add @`0x43af4`→governor→±0x2000→`gp-0x6b98`. Highest-risk lever; last/never.
> - **V17 deadband-only is INERT, not a fix.** `0xC6424` (`tp+0x7424`, read once @`0x43358`, one cmp @`0x434ca`) gates ONLY the `gp-0x356c` limiter; with slew=0 that state is pinned at 0, so 29491→20000 changes nothing. Deadband and slew are **coupled**.
> - **The real command-cut node is the OVERRIDE STATE MACHINE** `gp-0x6960` (states `gp-0x355d`; stores @`0x4362a`/`0x436c2` incl. an `ori 0x8000` sentinel), **NOT** gated by the shaper deadband. The block below conflated the two mechanisms — that conflation is the error.
> - **Ramp `0xC64DE` label was inverted too.** `tp+0x74de`=stock `0x11`=17 is the **count ceiling** of the re-engage/debounce SM in `m_steer_torque_arbitration` (read 8×; counter `gp-0x6756`, init `=(ceiling>>1)+1`; driver torque `gp-0x6a5e`, transitions `gp-0x3d36`/`gp-0x6809`). 17→27 **lengthens/softens** the re-engage span — NOT "faster." It is the one lever on the override path the EME actually traverses; it targets the **recovery ratchet**, not the initial snap.
> - **No output rate-limiter cal exists.** `gp-0x6b98` has only a ±0x2000 magnitude clamp + a ±5 change *detector*. A true down-rate limiter would need a **code patch (trampoline at the `0x43b52` store into the `0x8B218+` cave)** — **scoped in the review but NEVER built. No trampoline in any `.rwd` or in the Ghidra project** (verified: `../accord-firmware/analysis-2020accord/ghidra_project/code.bin` ≡ stock dump; cave all-`0xFF`; `0x43b52` is the stock `st.h`). The "aragon asymmetric rate-limit prior art" claim is **RETRACTED** (not in his `rwd-xray-2026`; his comma-side LPF can't fix a firmware gate tripped by physical column torque).
> - **The EME gate is UNOBSERVABLE on-car** (internal RAM, not CAN; not bench-reproducible) → no gate-specific fix can be mechanism-validated; only passive CAN `0x427` sees the outward signature. V18 was validated by road feel.
> - **RESULT — V18 = `builds/v18_v49/build_v18_tva.py`:** 2× gain `0xC646C`=1782 + clamps `0xC61B2`/`0xC61B4`=1024 + **ramp `0xC64DE` 17→27 only** (deadband stock 29491, slew stock 0). Calibration-only; decode-verified 15-byte diff (2 PN + 3 cal halfwords + 1 cal byte + 2 CRCs). **FLASHED + road-validated: drives well.** Per [[feedback-operator-lived-experience]] this is the authoritative outcome. Lever semantics record: [[reference-accord-eme-lever-semantics]].
>
> *The "V16 fix BUILT" block below is preserved for the record but its slew/deadband mechanism is wrong; do not act on it.*
>
> ## ⚠ UPDATE 2026-05-27 [⚠ SUPERSEDED — slew/deadband mechanism INVERTED; see the CORRECTION block above] — root cause REFINED (whole-assist cut, not LKAS-only) + V16 fix BUILT
>
> Operator road-report correction (overrides the LKAS-centric framing below per [[feedback-operator-lived-experience]]): the event feels like the **WHOLE power steering momentarily cuts out**, not just LKAS easing. A 4-agent program-wide inventory sweep + disasm verification this session confirmed the mechanism and located the keystone:
> - **Base power-steering assist (gp-0x6bf0) and LKAS both merge into the shaper accumulator and exit the SINGLE final command `gp-0x6b98`** — zeroing it kills both. There is no separate base-assist path to the FOC. (Verified, cluster 3.)
> - On a hard override the **net torque demand swings through zero**, and/or the dual-coil voter transiently diverges → the assist state machine does a **transient re-init (state 3→1→2→3, NOT fault-state 4)** → **no DTC latches** (persistent fault bit `gp-0x6d78` bit15 never set).
> - The shaper **deadband** (`tp+0x7424`=`0xC6424`=29491) zeroes the command via the newly-found state node **`gp-0x6960`** → `gp-0x6b98 = 0` (disasm-verified to the final store @0x43b52/0x43dfc).
> - **THE KEYSTONE: the delivered-command slew limiter is DISABLED** — `tp+0x71d6`=`0xC61D6`=**0** (NOT 14; the prior `0xC71D6`=14 was an off-by-0x1000 address error, see [[reference-accord-pointer-base-audit]]). With the rate-limiter off, any momentary drop becomes a **hard 0 → hold → jump-back** instead of a soft dip = the felt cut + ~10 s ratchet. The 2× gain only **doubled the consequence** of a normally-imperceptible event.
> - **Whichever gate momentarily drops the command** (deadband zero-crossing [verified], low-speed governor dip `gp-0x4f64` [cluster 2], plausibility re-init [cluster 1/4], or LKAS ramp-abort `gp-0x6758` via `FUN_0002a30e` [cluster 1]), the disabled slew is the common amplifier — so re-enabling it is robust to all of them (it sits on the shared post-merge trunk).
>
> **PREFERRED FIX (built as V16, keeps 2× exactly, touches no fault logic):** re-enable the slew — `0xC61D6` **0→14** (the value other Honda variants ship). Optional: narrow deadband `0xC6424` 29491→20000, faster re-engage ramp byte `0xC64DE` 17→27. All in CRC block 0xC6000. `build_v16_tva.py`; 49/49 CRC PASS, clean 18-byte diff, UNFLASHED. This **supersedes** the earlier "SAFE = reduce gain 1782→1300" suggestion (that sacrificed the 2×; the slew re-enable keeps it). Full inventory: `analysis-2020accord/reference/fw_inventory/MASTER_INVENTORY.md`. The `FUN_00041eec` plausibility threshold remains OFF-LIMITS.

The 2020 Accord (`39990-TVA-A160`, V850, code.bin) **driver-input → LKAS interaction** and the **EME (EPS misbehavior event)** observed on the 2x torque builds. Established 2026-05-26 (this session) from the open Ghidra instance: arithmetic at the arbitration OUTPUT read directly by me [VERIFIED]; channel identity by a firmware-codepath-tracer swarm [tracer-VERIFIED, high confidence]. Bases gp=0xFEDF8000, tp=0xBF000. Builds on / refines [[reference-accord-lkas-delivery-and-governor]], [[reference-accord-arbitration-limit-family]], [[project-accord-torque-mod-v0]].

## The symptom (operator road report, 3 instances)

Always op-engaged. On sharp turns at low–medium speed that openpilot cannot complete, the driver adds significant hand torque to help; at/after the apex the steering **sharply straightens, LKAS commands lose all effect**, then the power steering feels degraded — "manual but jerky," "ratchets in the turn direction when I push" — for tens of seconds, recovering after going straight / a nudge / a stoplight. Once afterward the steering felt "too easy, like 2x." Feel reported as BOTH active push-to-center AND assist dropout. No dash-light note (not confirmed either way).

## Where driver input enters the LKAS torque path [VERIFIED structure]

```
column steering-torque sensor (dual-coil, redundant)
  → ADC readers FUN_00021646/0x622/0x69e/0x672 (raw HW regs, lock/unlock), ×41/64 scale (0x29>>6)
  → FUN_00053216 / FUN_000534da (ch idx 0-3) + FUN_000522fe (5th, separate ADC bank via FUN_00021706)
  → channels gp-0x6a44(0xFEDF15BC) / -0x6a40 / -0x6a3c / -0x6a38 / -0x6a46
  → plausibility VOTER FUN_00041eec:
        abs() each; spread (max-min) < adaptive threshold uVar10 ⇒ coherent;
        fuses → gp-0x6a5e (0xFEDF15A2)   = running fused DRIVER TORQUE estimate
        sets   → gp-0x67f4 (0xFEDF180C)  = "plausible & converged" flag
        threshold relaxed by steering-angle-error gp-0x6a10 (so hard steering doesn't nuisance-trip)
        re-enable (gp-0x67f4 0→1) requires fused value within 65 counts of the running reference
```

`gp-0x6a5e` (fused driver torque) is consumed by `m_steer_torque_arbitration` (FUN_00028ea6) in **two** ways:
1. **Override blend (designed):** it is the axis into `g_pArbSetpointLimitCurves` → the LKAS setpoint limit shrinks as driver torque rises (authority handoff). [VERIFIED structure]
2. **Kill gates:** `bVar1=false` (arb decompile lines 86–94) if **any** channel > `0x7D00`=32000 (one-sided ceiling) **or** `gp-0x67f4 != 1`. `bVar1=false` drives the integrator switch (branches at 619/660) to **zero the integrator** → `iVar28=0` → request flag `gp-0x67a7=0` → delivery SM leaves the enabled state. [VERIFIED]

## Delivered-LKAS output math (where the 2x gain sits) [VERIFIED — read the instructions]

In FUN_00028ea6, ~lines 1271–1327:
```
iVar23 = (iVar34 * uVar18) >> 15                 // gated/zeroed by an anti-windup sign-guard:
         // line 1266: if (iVar34 * prev_output[gp-0x6b30] < 1) iVar23 = 0  (sign-reversal/zero-cross → drop correction term)
iVar28 = (iVar28 + iVar23) * polarity[gp-0x6752] * GAIN[tp+0x746c = 0xC646C]
uVar13 = iVar28 >> 15 ; clamp ±[tp+0x71b4 = 0xC61B4]
gp-0x6b3c (0xFEDF14C4) = clamped × ENABLE
   where ENABLE = ( *(char)(gp-0x67a4 = 0xFEDF195C) == 2 || == 3 ) ? 1 : 0   (else LKAS = 0)
```
- **GAIN = `0xC646C` = the V14/V15 doubled lever (891→1782); applied AFTER the integrator** → any wind-up reaches the wheel at ~2x.
- Sole writer of the ENABLE byte `0xFEDF195C` = `st.b r14,-0x67a4[gp]` @ `0x2b51e` in `m_steer_torque_limit_and_pack`; values **2/3 = enabled, 0/1/4/5 = LKAS zeroed**; it follows `gp-0x67a7` (integrator-nonzero / request-active) and `gp-0x67a1` (==5 = distribute_clamp motor-limit).
- A second guard skips the whole main computation (zeroes the term) if `|gp-0x6a56|≥12000` (a bounded polarity-scaled internal reference written by FUN_0003f776, lockstep-shadowed) or `|gp-0x4f60|≥25600` or polarity==0 (arb line 95–97).

## Root cause of the EME [mechanism VERIFIED; exact trigger gate INFERRED]

The 2x arb-output gain **amplifies the consequence of the firmware's normal driver-override / torque-sensor inhibition.** When the driver applies hard hand torque to finish a sharp low-speed turn:
- the override curve cuts the LKAS setpoint and/or a gate (`gp-0x67f4→0`, or the +32000 ceiling) zeroes the integrator;
- because delivered torque ran at ~2x, the loss is twice as large and abrupt → the **snap / straighten**;
- re-engagement needs the channels to re-converge (within 65) and the integrator to re-ramp **through the 2x gain** → the **jerky/ratchet ~10s recovery**;
- the "feels 2x easy after" = wound-up / re-ramped integrator at 2x (NOT steady doubled driver-assist — operator never feels it in fully manual driving, which rules out a doubled assist path).

**Why 2x makes it scary, not stock:** at stock 1x the same dropout-and-recover almost certainly happens but loses/regains only a little assist → imperceptible. At 2x it loses twice the assist instantly and returns in twice-as-big steps → a fight-the-wheel event. We did not break the mechanism; we amplified its consequences.

**Tracer nuance:** under normal hand torque all 5 channels rise TOGETHER and stay coherent (driver effort alone does not split a healthy sensor). The voter trips on disagreement (fault-like) or the one-sided ceiling. So the operative EME trigger is most likely (i) the override-curve setpoint collapse, (ii) a transient dual-coil disagreement under fast/hard input, or (iii) the +0x7D00 ceiling — **not discriminable from static analysis.** Decisive next step = bench RAM (`0xFEDF15A2` fused torque, `0xFEDF195C` enable, `0xFEDF180C` flag, integrator, delivered torque) or a CAN 0x427 motor-torque + steering-torque log through one EME (same method as [[reference-civic-steer-motor-torque-can427]] / [[dream-diagnostic-chain-reusable-method]]).

## Mitigation directions

- **SAFE lever:** reduce arb gain `0xC646C` (e.g. 1782→~1300, ~1.5x) and/or clamp `0xC61B4` — shrinks the snap + re-ramp magnitude and means the driver fights less hard (less likely to reach the override/ceiling edge). Pure calibration, touches no safety limit; same build mechanics as V15B (recompute block-48 CRC).
- **DO NOT** widen the torque-sensor plausibility/agreement threshold to stop the dropout — `FUN_00041eec` is a genuine **column-torque-sensor fault detector**; relaxing it suppresses real fault detection. (This RETRACTS my earlier "aggressive lever: raise the plausibility threshold" suggestion, made before the channels were identified.)
- Comma-side: the dropout is a plant behavior openpilot doesn't model; a controller change can't see/prevent the firmware gate.

Method per [[feedback-rigorous-validation]] (arb-output arithmetic read directly; channel identity is tracer-verified high-confidence; the exact EME gate is explicitly left as bench/CAN-data-only). Supersedes the "V14 WORKS, saga closed" optimism in [[project-accord-torque-mod-v0]] / [[reference-accord-lkas-delivery-and-governor]] — 2x delivers torque, but with this driver-override interaction hazard.
