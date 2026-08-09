---
name: accord-v84-flew-and-fixed-nothing
description: "🛑 V84 flew as route 6d and FIXED NOTHING — operator verbatim: 'None of these have been fully fixed in V84.' One BAND moved (26–31 Hz burst duty 25.1% → 2.54%). A band moving is not a symptom fixed. ⊕ V83a's ring-falsifier is retracted; V84 is byte-identical to V67/V68 at every grind cell."
metadata:
  node_type: memory
  type: project
---

**Route `6d`** = `75604b0a432fdc89_0000006d--5d03a5adb4--{0..11}`, 68,235 frames, **682.4 s**, **79.71%
engaged**, 0–31.38 m/s (113 km/h). **Fault-free**: `STEER_STATUS` {0: 68,219, 3: 17}, **0 DTC-active
frames, 0 sentinels**. Orchestrator-verified from `_cache_r6d/` independently of the scoring agent.

**Identity = V84, with no free parameter.** `0x14A` byte4 field alphabet is exactly **{0x2F, 0x3F}**:
`b3` (V84's hard-coded fingerprint) reads **1.00000**, and `b7`/`b6` read **0.00000** for all 68,236
frames. Routes 67/68 are perfect *thermometers* (V81/V83a cave family) and contain neither value.

## ★★★★★ THE RESULT — the highway ring

| build | damper relay index | engaged >80 km/h | windows with 26–31 Hz envelope >1000 | burst duty | longest ring |
|---|---|---|---|---|---|
| V80 | 3.27 (bang-bang) | 30.7 s | **24/24 (100%)** | 96.6% | 18.29 s |
| V81 | 1.45 | 44.8 s | 8/35 (22.9%) | 25.1% | 11.25 s |
| **V84** | **0.00 (Honda viscous)** | **151.0 s** | **1/118 (0.8%)** | **2.54%** | **1.34 s** |

**On 3.4–4.9× the exposure of either comparator** (orchestrator-verified: 370.8 s engaged >50 km/h,
158.1 s >80 km/h). ⇒ the operator's *"I did not notice any odd behavior at normal speed"* is **NOT an
exposure artefact.** Both adversarial checks pass: the 26–31 Hz *median* rise is a broadband floor shift
(the 32–38 Hz negative control moves with it, ratio-of-ratios 1.13) but the **tail is down 0.32×**; and
the IMU says V84's road was **1.2× rougher**, which moves *against* V84.

## 🛑🛑 THE RETRACTION THIS FORCES
V83a's pre-registered falsifier — *"if the ring is not below V76's, the damper-dose model is wrong"* —
fired, and `docs/STATE.md` recorded **"RECORD THE DAMPER-DOSE MODEL OF THE 26–31 Hz RING AS FALSIFIED."**
**That conclusion is void.** V83a reverted mode 26 but **left mode 27 carrying V81's entire damper
package** (mode 27 is a second ENGAGED column on this `TVCA4` car), and it had only **19.2 s** of >80 km/h
exposure — uninterpretable. **V84 is the first build to remove the damper in BOTH engaged columns**, and
the ring went away. **The damper-relay model of the ring is now SUPPORTED by a four-point monotone
dose–response in relay index.** ⇒ freeze `0xD77DA`/`0xD77EE`=0 and `0xD7822`/`0xD7824`/`0xD782C`=60/400/140.

## The rest, scored against V84's own pre-registration
- **S1 grind #1 (18–22 Hz): falsifier did NOT fire** — 0.509× V83a [0.396, 0.695] vs a split-half null
  of [0.60, 1.62], band-specific (negative control 0.969). **But V84/V81 = 1.10 after the control
  correction**, i.e. Lever B bought back exactly what V83a lost and nothing more.
  ⊕ **Orchestrator byte-check: V84 is byte-identical to V67/V68 at EVERY grind-relevant cell** except
  `0x454FE` (which cannot execute — `gp-0x67fa==4` fires 0/123,277 driving frames). **V84 delivered
  V67's grind-#1 performance. The rate lane is maxed out at a level the operator still calls grinding.**
- **S2 micro-ratchet (6–9 Hz): FAIL** — 1.150× V83a (inside null) but **1.548× V67, outside its null**.
- **S3 macro ratchet: FAIL** (operator: "very obviously present"; no instrument exists).
- **S4 impedance: FAIL and REVERSED** — 2.052 [1.089, 3.936] vs V81's 1.484, despite the Coulomb damper
  being deleted. ⚠ manual arm is only 4.5 s at 10–40 km/h; marginal.
- **Grind #2: both operator-reported events found.** Event 2 (t=255.9 s, 56 km/h, 18.6°, cmd 1657) is a
  clean grind #2 — 48.77 Hz, Q 20.8, 3.10× IMU excess. Event 1 may be a **folded ring harmonic**
  (2×26.6 = 53.2 Hz folds to ~47 Hz). **Neither had the blinker up**, and lane-change windows as a class
  are flat in every band ⇒ *"grind #2 on a lane change"* is not supported as lane-change-specific.
- 🛑 The §7b grind-#2 protocol was **NOT run**: 5.1 s in-regime against a 166 s floor = **3.1%**. The
  strict-regime "0 events" is uninterpretable. Four builds in a row have now missed this.

See [[accord-v83a-flew-and-r24-is-the-actor]], [[accord-v80-damper-relay-and-grind1-inert]],
[[accord-stock-mode24-equals-mode26-damper-is-ours]].
