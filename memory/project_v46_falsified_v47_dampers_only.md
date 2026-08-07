---
name: project_v46_falsified_v47_dampers_only
description: V46 (lever A / Stage A carrier low-pass) FLASHED and did NOT move the vibration -> falsified. V47 = ratchet + dampers-only (Factor C + Factor E aggressive), BUILT + verified, UNFLASHED.
metadata:
  type: project
---

> 🛑 **BANNER 2026-08-06 — the DAMPER half of this record is VOID under RULE 7.** V44 and V47 wrote
> **modes 10/11** on a **modes-24/26** car ⇒ the Factor C / Factor E edits were **never in force**; any
> V47-derived damper null is **UNINTERPRETABLE, not a falsification**. The damper approach was **not
> actually tested until V74**, which measured a real 18–22 Hz dose-response
> ([[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]],
> [[accord-damper-is-mode-table-selected]], [[feedback-rule7-mode-proof-or-a-bet]]).
> The **V46 / lever-A** half of this record is unaffected — `0xC6450` was mode-proof and is validly
> falsified.

In-flight build state as of 2026-07-21 (supersedes the V44/V45 candidate state).

- **V46 FLASHED → vibration unchanged → LEVER A FALSIFIED.** V46 = V38 + ratchet + Stage A carrier
  low-pass (`0xC6450` 1024→32, corner ~4.8 Hz on the exact-unity residual passthrough of
  `FUN_0003a382`). The structural case (reinforcing positive-feedback carrier, −12 dB at 21 Hz) was
  clean but produced no noticeable on-car change. Joins r24/r26/Stage-C-pole/damping-floor/slew as a
  falsified vibration lever. Builder `analysis-2020accord/build_v46_tva.py` retained as the record.

- **V47 = ratchet + DAMPING RESTORE ONLY, BUILT + verified, UNFLASHED.** The current candidate. Opens
  BOTH damper deadzones the operator's manual-rotation cure implicates: Factor C (`0xD27C6`→235,
  `0xD27DA`→234, V44's cells) AND Factor E (`0xD2802/04/06` & `0xD2816/18/1A` → 700/750/800, aggressive).
  See [[reference-accord-damper-two-deadzones-factorC-factorE]] for why both are needed. Sizing is
  aggressive (conservative Y0-only ≈ V44's failed magnitude); trade-off is low-speed steering heaviness,
  middle-ground Y0≈350 on standby. Clamp bound left stock (see [[reference-accord-damping-clamp-dtc1d-trap]]).
  Builder `analysis-2020accord/build_v47_tva.py`. RWD SHA `1421ca1b…afb7bc34`; 23 bytes vs V38 in 2 CRC
  blocks (MAIN + DAMP), 50/50 + 49/49 verified.

Next: flash V47, evaluate ring + steering-feel. If it works but feels heavy → middle-ground Factor E.
If null → damping hypothesis falsified; the mode may be primarily the mechanical dual-pinion rack
resonance ([[reference-accord-dualpinion-arch-one-torsion-sensor]]) with firmware only enabling it.
Handoff: `docs/HANDOFF-2026-07-21-v46-v47-vibration.md`.
