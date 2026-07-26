# HANDOFF — 2026-07-21 — V48 session: vibration loop-gain characterization, V48A (failed), V48B notch

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** V38 on-car.
**Headline:** A six-stream evidence audit re-diagnosed the ~21 Hz vibration as a **positive-feedback-
amplified two-inertia torsional mode** and produced a **quantitative loop-gain model**. Two builds were
designed: **V48A (cal-only, BUILT + VERIFIED, then FLASHED → did NOT fix the vibration)** and **V48B
(the 21.4 Hz notch — biquad DESIGNED + numerically validated; code-cave engineering IN PROGRESS,
unbuilt).** The master reference for the whole issue is now **`docs/VIBRATION-DOSSIER.md`** — read it first.

---

## 0. The one result that lands this session
**V48A did NOT fix the vibration (operator, on-car, 2026-07-21).** V48A muted the **two strongest
identified 21 Hz feedback carriers** — the "type-8" command-derivative carrier (`0xC4120`) AND the
`FUN_0003a382` reinforcing residual lane (`uVar27` ×0.25) — and the vibration was unchanged. Partial
effect (if any) was not reported.

**What that means (per the loop-gain model, `analysis-2020accord/eps_loop_gain_model.py`):** each single
carrier only cures the ring if it is ≥~50% of the loop gain; muting both was predicted to give 10–12 dB
margin **IF those two dominate.** A null says they do **not** dominate — the anti-damping is
**distributed** across more lanes (boost `FUN_00034a72`, magnitude `FUN_000352b4`, damper, r24/r26), or
the type-8 latch was inactive and `a382` alone at ×0.25 was insufficient. This is exactly the model's
"→ go to the split-independent notch" branch. **It strengthens the case for V48B (the notch), which
attenuates the shared torsion-bar input ahead of ALL sensor-reading carriers at once.** ⚠ Caveat the
notch does not cover: the type-8 command-delta carrier (already muted in V48A, no effect → likely not the
culprit) and r24/r26 (read `gp-0x4f62`; road-proven minor via V39/V42).

**NOT iterated this session per operator instruction — recorded only.**

---

## 1. The converged diagnosis (six-stream audit)
Full detail + citations in `docs/VIBRATION-DOSSIER.md`. In brief:
- The vibration is a **two-inertia torsional resonance** — motor/rack inertia vs wheel/column inertia,
  **torsion bar (= the torque sensor) as the compliance.** Literature: a complex pole at ~20.9 Hz;
  measured 21.4 Hz, Q≈13.6.
- **The bare plant is only mildly resonant (Q≈1.7); ~88% of the felt Q=13.6 is FEEDBACK-INDUCED
  peaking.** The loop at 21 Hz is real-positive (~0°) = **direct anti-damping**, because the carriers are
  command/torque-**rate** (derivative) feedbacks and the plant is −90° at its peak.
- **|L(21Hz)|: stock 0.22 → 2× 0.44 → 4× 0.875** (1.16 dB margin, 8× peaking). Self-excitation edge
  **4.57×**, palpable onset **~3×** — matches "2× fine, 4× vibrates."
- **★ Collocation keystone (why every damper build failed):** the driver's grip cures it because it adds
  damping **at the wheel/column antinode** (collocated). The firmware damper senses **motor-resolver
  rate** — the far side of the torsion bar, **non-collocated** — so it cannot reach the wheel-side mode
  at any gain, and can anti-damp it. V44/V47 nulls are that theorem confirmed. **Stop tuning the
  motor-rate damper.**
- **Route B ("achieve 4× via setpoint, stock gain") is HYGIENE-ONLY, ΔL(21Hz)=0.000** — by
  gain-rescaling invariance the delivered command is identical, so every unfiltered 21 Hz carrier is
  unchanged. (Confirmed after correcting that the type-8 carrier `gp-0x6b12` is a delivered-command
  delta, not a `0xC646C`-scaled term.)

---

## 2. Builds

### V48A — cal-only combined carrier mute — BUILT, VERIFIED, FLASHED, **FAILED**
`analysis-2020accord/build_v48a_tva.py`. V38 + ratchet (`0x454FE`) + **two carrier mutes:**
- **type-8 mute:** mixer slot-8 SUM gate `0xC4120` `0x01→0x00` (MAIN block).
- **`FUN_0003a382` attenuation:** `uVar27` `0xC67B8/BA/BC` `1024→256` (−12 dB on the lane; CAL block).
- Cut from V38 (stock damper; V47's opening NOT carried). 4× forward gain `0xC646C=3564` untouched.
- **Verified:** 12 changed bytes, 50/50 full-chain + 49/50 bootloader-walk CRC on image + RWD readback.
  RWD `39990-TVA,A160-V48A-...-uVar27x256-...rwd`, RWD SHA-256 `77574f9e…c5bc80`, image `d9451a91…b12d2e`.
- **Adversarial safety (GhidraMCP, GO):** `FUN_00027b0a` is an int/float LOCKSTEP MONITOR of the mixer
  sum that reads the SAME `0xC4120` byte → muting is matched-symmetric, monitor can't trip. Shadow pair
  `gp-0x62b0[8]`/`gp-0x4b40[8]` written gate-independently. `uVar27`/`gp-0x6ad4` pure-leaf, single-reader,
  no float mirror. Clamp trap (`0xD209C`/`0xC6554`) byte-stock.
- **ON-CAR: did NOT fix the vibration** (§0).

### V48B — the 21.4 Hz notch — DESIGNED + VALIDATED; cave engineering IN PROGRESS (unbuilt)
- **Biquad (validated, `analysis-2020accord/eps_v48b_notch_design.py`):** RBJ peaking-dip, f0=21.4 Hz,
  Q=5, −8 dB, fs=1000 Hz. **Direct-Form I, Q12, int16 coeffs `b0=4045 b1=-7949 b2=3977 a1=-7949
  a2=3926`.** Measured: −7.9 dB at 21.4 Hz, +0.000 dB at 1 Hz (feel preserved), pole r=0.979 stable,
  int32 accumulator peaks 92M (23× margin), states fit int16, clean impulse ring-down. ⚠ DF-II was
  rejected — its recursive intermediate overflows int32 (the sim caught it).
- **Feasibility (CONDITIONAL GO, filtered-copy design):** source-filtering `gp-0x4f60` is NO-GO — it's a
  shadow-lockstep var (fault `0x17`) feeding 2 no-debounce hard-shutdown monitors (`FUN_00042af8` 0x1c /
  `FUN_00043e44` 0x1d) + 2 CAN broadcasts + diagnostics. So: biquad → a NEW RAM cell; repoint only the
  carrier reads (`FUN_0003a382`, `FUN_0002c478`, `FUN_00034a72`, `FUN_000352b4`, `FUN_00034350`).
  Cave `0xC4B34–0xC4FEF` (all-0xFF, MAIN block). See
  `.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp4f60_notch_filter_feasibility_v48b.md`.
- **Reader resolution — DONE (agent, `.../firmware-codepath-tracer/reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass.md`).**
  ★ Design-changing finding: **two of the five original "carriers" are DORMANT in stock cal** —
  `FUN_00034350` (damping, mode byte `0xC6498`=1) and `FUN_00034a72` (boost, `0xC6499`=1) read
  `gp-0x4f60` but a mode gate BYPASSES that read to `gp-0x6ba6`/`gp-0x6b9a`. The **live** producers are
  **`FUN_0003b66a`@`0x3b672`** (feeds damping+boost Factor-A; two-stage IIR gain `0xC63BA`=512, barely
  touches 21 Hz) and **`FUN_0003b49a`@`0x3b4a8`** (unity IIR `0xC6408`=1024 → `gp-0x6ad6`, read only by
  `FUN_0003a382`) — **both must be ADDED to the repoint set.** Repointing only the original 7 sites would
  be a partial no-op. **Corrected repoint set:** `FUN_0003a382`@`0x3a6ca/0x3a7ca`, `FUN_0002c478`@`0x2c480`,
  `FUN_000352b4`@`0x354d2/0x35aa4`, **+`FUN_0003b66a`@`0x3b672`, +`FUN_0003b49a`@`0x3b4a8`** (and the two
  dormant sites `0x34392`/`0x34ace` as harmless defense-in-depth). All are uniform `ld.h -0x4f60[gp],rX`
  (16-bit disp, `-0x1500` in range). **Corrected hook:** the universal convergence point is **`0x7feac`**
  (`cmp r0,r8`+`mov r8,r14`, 4 bytes = one `jarl`), not the prior `0x7fce6`.
- **STILL OPEN before V48B can be built:** (1) **RAM: DF-I needs 5 free halfwords; only 3 confirmed
  (`gp-0x1500`+`gp-0x14E0`)** — find 2 more or accept a compact Q10 DF-II (detune risk); (2) classify the
  6 flagged BLOCKER readers (`FUN_0002b62c`, `FUN_0002db94` [friction-lane candidate], `FUN_00033d10`,
  `FUN_0003f884`, `FUN_0004c780`, `FUN_0004fbde`) — some are on the ~100 Hz assist task and read
  `gp-0x4f60` directly; (3) write + adversarially review the V850 cave assembly (trampoline + biquad +
  the corrected repoints); (4) `build_v48b_tva.py`. **A code cave is the kit's only class that has bricked
  (V24/V27) — do not rush it.**

---

## 3. Forward options (recorded, NOT pursued this session)
- **V48B notch** remains the model's guaranteed, split-independent, least-feel-affecting lever, and the
  V48A null makes it the logical next real attempt. It is a code cave — finish the open items in §2 and
  run a full adversarial review before any build/flash.
- **Reconsider the carrier set:** V48A muting the two "strongest" carriers with no effect is a data point
  that the dominant anti-damping may be in boost/magnitude/damper (all read `gp-0x4f60`, all covered by
  the notch) — or that the loop model's carrier attribution is off. The notch sidesteps this by being
  split-independent.
- **Tier-3 fallback (guaranteed, rejected by constraint):** reduce the LKAS gain toward the ~2.6–3×
  stability ceiling. Off the table while keeping 4×.

---

## 4. Artifacts produced this session
- `docs/VIBRATION-DOSSIER.md` — **master reference for the vibration** (phenomenology, physical model,
  firmware model, full theory ledger + why each lever failed, evidence sources, quantified loop-gain
  table, V48 menu). Read first.
- `analysis-2020accord/eps_loop_gain_model.py` — runnable loop-gain/margin model + notch design +
  per-lever prediction.
- `analysis-2020accord/eps_v48b_notch_design.py` — runnable biquad design + fixed-point validation.
- `analysis-2020accord/build_v48a_tva.py` — V48A builder (flashed, failed).
- Memories (see `memory/MEMORY.md`): collocation keystone, loop-gain characterization, V48A result.

⚠ **Latest correction of record:** the "type-8" carrier `gp-0x6b12` is an envelope-shaped delta of the
DELIVERED command (`gp-0x6b98`), NOT `gp-0x4f60 × 0xC646C` (that term feeds the dead `gp-0x6b10`). Its
`0xC646C` dependence is weak/nonlinear (a saturating LERP index). This is why Route B can't move it and
why the clean lever was the direct slot-8 mute.
