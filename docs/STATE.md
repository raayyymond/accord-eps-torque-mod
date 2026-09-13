# STATE — living current state of the kit

> 🛑 **READ THIS BOX FIRST.** Everything you need to make a decision is in this box. The superseded decision
> boxes and the 84 finding/correction blocks that used to follow it are ARCHIVED under `docs/archive/` (pointers
> at the end of this file). They are a record, not a briefing; nothing was retracted by the moves.

## ✈ THE DECISION, IN ONE PLACE — updated 2026-09-13 (**V291 (C10) BUILT — the first LOOP-OPENING build — and NOT CLEARED FOR FLASHING by the letter of its pre-registered adversarial pass: B4 + an ungated 9–18 Hz cost; B3 re-scored PASS. Nothing flashed, nothing sent.**)

**ON THE CAR: V282** — route `…0000006c` (2026-09-12, 62 segments, mostly motorway, 326 s engaged in the 8
segments read) attributed from the tap (b7 → 0.000 after disengage, b5 engaged 0.156), not the label.
**Flash target: none recommended.** V291 exists on disk and is the only V291; flying it is the operator's
decision against the verdict below.

---

### 🛑🛑 V291 (C10) — WHAT IT IS, AND WHY IT IS NOT CLEARED

**V291 = V282 + 15 bytes:** `0xC63E8/EA` 923/1560 → **962/958** (the LKAS rate-PID feedback lag pole 16.53 →
**9.94 Hz, DC 30.89 held**), `0xC6446` 5244 → **4725** (the r24 engaged arm, −9.9 %, a partial revert of
V84's Lever B), the 0x14A cave's **b3 = sign(fb state gp-0x3d30)** (displacement-only), two CRC trailers.
Forward path byte-identical (map ×6, Kp 248, Kd 128, Ki 0, clamps, ×6 gain, output lag; peak 2505).
rwd **`8ce8d5b7c7cda973a04fbe9a061090c76121b6a136d1bba18d1b67fd24530533`** · image
**`a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657`** · script
`analysis-2020accord/builds/v108_plus/build_v291_tva.py` · design `docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md`
(+ Addenda A–D) · prereg + verdicts `docs/review/ADVERSARIAL-V291-PREREG-2026-09-13.md` · lineage entry ·
page https://claude.ai/code/artifact/19038e6d-729b-4a79-ba3b-a07aeefcc067.

**CLASS — genuinely new in the V38 → V291 arc: OPEN THE RATE LOOP ABOVE ~8 Hz.** Every prior in-loop
lever (V289's notch, option C, Kd, fb pole UP, output lag, leads) shaped the loop AT the mode and returned a
null under the authority gates; V291 lowers the servo's feedback bandwidth so the loop stops acting where
the grinding object lives, and pays the 7.3 Hz gate with the r24 cut.

**Predicted (servo-side, byte-exact z-domain over the 121-fit family):** max |1/(1+L)| over 12–26 Hz
**19.4 → 3.6**, sensitivity at 20.3 Hz **×0.34**, ring **×3.24 shorter** (f −0.8 Hz, NOT relocated), PM
+39 → +57°, GM 1.15 → 1.55, 0/121 unstable, **transient authority UP** (pkR 1.026 worst), steady state
×1.000 (linear), |T(3.9)| ×1.07, 5–9 Hz bump 0.70 → 0.91. r24-folded: Ms 12–26 **4.7 (effective arm) /
12.3 (flown arm)**; folded f0 17.0–17.9 Hz.

**ADVERSARIAL PASS (four independent agents, FAIL criteria written before the image existed):**
- **A arithmetic PASS · C build audit PASS · D interlocks PASS** (one reader per cell on the built image,
  both methods; every EME/governor/lockstep/DTC cal byte-identical; the gp-0x671d latch moves the safe way).
- 🛑 **B units/stability: DO-NOT-FLASH — no instability on any fit at any scaling; after the re-score the
  basis is B4 + one ungated cost:** (1) **B3 PASS (re-scored)** — with the r24 arm settled as EFFECTIVE (κ 0.449,
  the deadband explains ≤ 15 % of the 2353-vs-5244 gap, the 5244 rung is selected, k_eff 0.895) and the 9.94–14 Hz
  band identified at nperseg 512, the r24-folded 12–26 Hz improvement is **×3.3–4.2** across the whole B(f)
  perturbation box, f0 17.45–17.95 Hz (clear of 15–17), no new ζ < 0.05 pole; (2) **B4 FAIL** — byte-exact
  steady state at tiny demand (sp = 3 counts) **×1.34–1.80** of V282's (within 3 % at sp = 33; 0.23–0.41 deg/s
  absolute): the feedback quantum b/1024 0.66 → 1.07 raw counts leaves the rate loop effectively open below
  ~0.5 deg/s — **intrinsic to any cal-only fb-pole change**, fixable only by a cave with an error-feedback
  remainder word; (3) **UNGATED** — worst-fit disturbance sensitivity worse than V282 on **121/121 fits over
  3.0–18.2 Hz, peak ×1.99 at 12.85 Hz** — a broad well-damped shoulder (no pole below ζ 0.36), not a line, in
  the band that killed V289 (whose object was a ζ 0.03 line); the byte-exact integer limit cycle's median
  frequency moves 19.8 → 15.2 Hz. B5 FAILS if the fork's `AccordCurvatureLead` is ON.
- ⇒ **ORCHESTRATOR'S VERDICT: NOT CLEARED FOR FLASHING**, by the letter of the rule written before the pass ran.
  The remaining grounds are a sub-deg/s effect the class cannot avoid and a design cost no gate priced; **whether
  a well-damped ×2 shoulder at 9–18 Hz is an acceptable price for ×3–4 at 20 Hz is the operator's decision.**

**What closed B3 (`rlog-tools/studies/grind/B-IV-AND-KAPPA-2026-09-13.md`):** the ±3 post-gain deadband was
already in the b6-inversion ladder and the measured post-gain amplitude (26–138 counts) is 5–25× too large for
it to matter; the residual ×1.95 is a constant pre-deadband scale (stratum-invariant ×1.21); the 427 tap is exact
by its packer/decoder identity; B(f) is not detectably biased at 20.3 Hz (command-IV ×1.01/×1.02); the command
has no energy at 12–13 Hz so no instrument reaches the band, but nperseg 512 identifies 9.94–14 Hz (coh ≥ 0.40)
and moves |B| ≤ 8 % / ∠B ≤ 18°. **What would close B4:** the fb filter as a cave with error feedback (V292
direction). **The 9–18 Hz shoulder needs a gate** (B proposes: sensitivity ratio vs V282 ≤ 1.25 pointwise over
3–30 Hz, worst fit; C10 reads 1.99).

**If the operator flies it anyway — pre-registered read (one ~20 s hands-off creep episode):** 18–22 Hz
envelope **half-peak** decay ≈545 → ≈183 ms (the half-peak metric is safe; a full-envelope or 10 % metric
is NOT — the tail below 0.5 deg/s is open-loop on V291); T-vs-0x18F-rate cross-spectrum phase **−14° ± 4°
at 10 Hz** (−12.5° at 7.3 Hz) over 16 s of creep — the LANDED check; 0x14A **b3 transition rate ×0.785
[0.762, 0.805]** of the mirror's V282-pole prediction on the same 0x18F trace, within-drive, conditioned on
|rate| ≥ 2 counts and mean rate ≤ ~1.5 deg/s (outside that window the bit pins). **Revert signatures, with
numbers:** the 6–9 Hz strong-turn ripple returns (F7 ≥ 2/100 s or tap ripple/level ≥ 0.25); a new 10–18 Hz
line or roughness (worst-fit sensitivity ×1.3–2.0, peak near 13 Hz; integer cycle at ~15 Hz); a 22–30 Hz
line; the grinding unchanged; a darty/loose lane-centring feel; a one-sided standing pull at rest.
**`AccordCurvatureLead` must be OFF.**

---

### ⭐⭐ THE MEASUREMENT THAT SET THE DIRECTION — with the loop OPEN there is NO 18–22 Hz object

`OPENLOOP-RING-DAMPING-2026-09-13.md`, 35 routes, 4,759 s lateral-disengaged (STEER_REQUEST = 0, which
opens the rate loop AND the engaged-only r24 lane): the pooled spectrum carries **no resonance in 16–26 Hz**
(prominence 1.00 / 1.25, below a no-mode control); a synthetic mode of **ζ ≤ 0.03 at the same energy WOULD
have been found** ⇒ **ζ_open ≥ 0.05 or non-modal**. Engaged on the same routes: ζ 0.034–0.036; **V282 alone
0.0164 [0.0126, 0.0222]** at 20.01 Hz. Load-matched amplitude OFF/engaged **0.21** (×4.5; mode-specific
×2.5–3.2 against the 26–34 Hz neighbour band). **V289's relocated 15–17 Hz ring is ALSO engagement-gated**,
and **V289's notch — an in-situ loop-opening at 20 Hz — removed the 20 Hz mode outright.** 🛑 Limit: opening
the loop also removes the LKAS excitation, so "no object" has two readings (ζ_open ≥ 0.05, or a low-ζ mode
only LKAS torque excites); both say the same thing for a build. **Estimator corrections:** the free-decay ζ
behind DESIGN-V290B §A.2 returns 0.036–0.040 for NO mode (void); coherence-time ζ is sound only for 0.02–0.05;
the 12–14 Hz "road line" is not a resolvable resonance. **Unit trap:** the ring is **~16 LSB on the 0x18F
RATE channel** (1.98 deg/s); "0.17–0.28 LSB" was the ANGLE channel — the feedback leg is LINEAR (0.879 of the
T ring; quantiser kicks 0.35 %).

### 🛑🛑 THE DESIGN LAW, AS OF 2026-09-13

> **The grinding object is a creature of the closed engaged loop. The lever is to make the LKAS rate loop
> stop acting in 12–26 Hz while keeping its action below ~8 Hz — and the price of that, in this loop, is
> paid at three places: the 7.3 Hz gate (the r24 pump arm), the 9–18 Hz sensitivity waterbed, and the
> feedback quantum at tiny rates. Score every candidate on ALL THREE, pointwise over 3–30 Hz, r24-folded,
> byte-exact — not on a band maximum.**

- **The fb-pole-down class does everything except the 7 Hz gate** (`DESIGN-V291-FBLP` body): Ms 12–26
  19.4 → 1.4–5.1, PM/GM up, pkR UP, 0/121 unstable, no new lightly damped pole — and fails gate73 at every
  dose because **94 % of the gate damage is phase lag at 7.3 Hz priced against the FIXED r24 arm**. Closed
  axes: fb × Kd (dominated; Kd ≥ 160 destabilises 77–112/121), 2nd-order fb LP (up to 70/121 unstable),
  output-lag pairing (93–109/121 unstable), the P-path-only split (passes five gates, hollows out 3–4 Hz:
  |T(3.9)| ×2.4 — parked). Readability floor ×2.43 (from the record's CI ×0.34–2.01): C12 (12 Hz) cannot
  observe its own edit; C10 and C8 can.
- **The r24 lane, traced and measured** (`TRACE-2026-09-13-r24-lane-transfer.md`, `B-OF-F-V282-2026-09-13.md`):
  r24 = −clip(deadband₃(trunc(clip(0.5·(bar[n]−bar[n−4]), ±5120)·g/1024)), ±8192), g = 0xC6446, 1 kHz, from
  the torsion-bar torque; **unit-weight sibling of the LKAS lane (gp-0x6b4c) at gp-0x6b94 ⇒ 1 : 1 at the
  motor.** On the wire: pure PUMP at 3–7 Hz (∠+170°), near-pure DAMPER at 18–22 Hz (∠+9…+15°), **73–86 % of
  the electronic 20 Hz damping**; gate73 improves monotonically with any r24 cut and the 20 Hz damping falls
  monotonically — **no sweet spot, and a high-pass on r24 is DEAD** (it adds lead where r24 already sits at
  +171°; HP 5/8 Hz re-arm the 7 Hz cycle). κ dispute open: effective ≈ 0.45× (b6 inversion, V281r3's
  cycle-gone), 0.10–0.20 (V289 bound), 1.45 (the record's pooled split). 10–14 Hz unidentified in every
  stratum. The gp-0x671d fault latch that would collapse r24 ×0.195 is UNARMED (5530 never reached on 4,653 s).
- **The LKAS lane's true path** (`TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`): T @0x2A23C →
  gated copy **@0x2A2EA** → gp-0x6b3c → clamp ±0xC61B2 → ep-relative request array → **gp-0x6b4c** (unit
  weight) → aggregator → governor → comp → shaper → gp-0x6b98. **gp-0x6ad4 is a driver-torque tracking PID**,
  not the LKAS output. **0x2A508–0x2B421 was undefined and is an uncalled TWIN of the LKAS output path** —
  analysed and SAVED (functions 2086 → 2090); the 0x2B41C "forward" the record cites is dead; 0xC646C has
  5 live readers.

### FORK (`raayyymond-StarPilot` @ Dom, HEAD 305732c85) — one patch, UNCOMMITTED, OFF by default
`ModelCurvatureLead` (`selfdrive/controls/lib/drive_helpers.py`, wired in `controlsd.py` before
`clip_curvature`; toggle `AccordCurvatureLead` default OFF, `AccordCurvatureLeadGain` 0.75; tests in
`selfdrive/controls/tests/test_model_curvature_lead.py`): slope-continuous extrapolation of the 20 Hz
modelV2 staircase. Removes 63–66 % of the camera-locked leg but cuts the 0xE4 18–22 Hz band only **−2.4 dB
(r39) / −4.2 dB (r63)** (the plan's share is the limit), adds +0.9–2.5 dB at 5–18 Hz, |H| ≥ 1 everywhere
(no authority loss), a lead vs today's hold below ~3.5 Hz and a lag above it. **Design B (trajectory-shaped,
"lag-negative") FALSIFIED** — orientationRate is a different head and a worse predictor. ~−18 % ring:
unreadable from one drive; ride it free on a drive spent on something else. The operator's own uncommitted
SR-map refit (route 6c) in `latcontrol_vehicle_tunes.py` is untouched. The rate-plant FF is bandwidth-blind
to a 10 Hz inner loop (~2 % perturbation); `AccordTorqueKi` 0.30 → 0.15 is the conservative knob;
`AccordRatePlantFF = False` is NOT conservative (×2.4–4.3 steady FF).

### CORRECTIONS OF RECORD, 2026-09-13
1. `DESIGN-V290B` §A.2's per-build free-decay ζ are NOT measurements (estimator at the no-mode floor).
2. "The ring is 0.17–0.28 LSB" is the ANGLE channel; on the rate channel it is ~16 LSB.
3. "r24 is a 4-tap FIR on gp-0x6ada" — it is a lag-4 backward difference on gp-0x4f62; gp-0x6ada is a
   write-only output mirror. `grind_loop_shape.py` §G ("5244 → 512 improves both bands") is falsified on
   the car (V70 at 512 put grind #1 back at stock).
4. The record's "×33–72 engagement gating" is a presence RATE; the amplitude ratio is ×4.5.
5. The bar-to-rate phase swing is downward ~130–150° through a ~9.4 Hz mode, not upward 210°; the
   creep-vs-loaded 7 Hz difference was a selection artefact of gating on instantaneous |bar|.
6. `reference_accord_gp671d_arm_inverts…` (tracer store) is wrong to favour gp-0x6ad4; the 2026-08-01 memory
   is right (gp-0x6b4c); the 08-26 census memory needs the word "driver-torque". Neither edited — ask first.
7. `TRACE-2026-09-13-fb-lag-filter-bytes.md` §4: "P = product >> 7 at 0x29F18" is the I accumulator; P is
   `mul` @0x29E36 then `sar 0x8` @0x29E3E.
8. Two V850 opcode-field collisions worth a scanner rule: field 0x3C/0x3D is shared by Format-V jr/jarl and
   the 6-byte extended load (hw2 bit 0 discriminates); field 0x3F by ld.hu, mul and setfcc (a real ld.hu
   has hw2 bit 0 = 1). Reject any Format-V hit whose target is ODD.

### ✈ NEXT — in order
1. **The operator decides on V291** with the narrowed basis above (B4 + the 9–18 Hz shoulder); if he flies it, the
   pre-registered read and revert signatures apply and `AccordCurvatureLead` stays OFF.
2. **V292 direction (not cut):** the fb filter in a CAVE with an error-feedback remainder word (Q15,
   DC 1.00000 at every amplitude — closes B4), at the 0x28F4C hook (runs every tick, no sentinel; 868 B
   free at 0xC4C90), scored on a pointwise 3–30 Hz sensitivity gate (≤ 1.25 vs V282 worst-fit) with the
   r24 fold at the settled arm. The operator decides whether the 9–18 Hz shoulder is an acceptable price.
3. **The IMU stays the top missing instrument** (road vs rack vs motor).
4. **The transient test** (`SPEC-COMB-TRANSIENT-TEST-2026-09-10.md`) is now second to the loop-opening
   result; keep it as the ζ_eff measurement.
5. Standing: golden model **90 symbols**, `_self_check()`+`_demo()` sha256
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d` (2,512 B) — re-verified this close-out;
   `docs/BUILD-LINEAGE.md` (229 KB) and `BUILD-LINEAGE-PART1-LEVER-INDEX.md` (193 KB) are over the 150 KB
   soft target — split at the next close-out; `0xC61C0/C2/C4` still has no lineage entry.

**Session reports:** `docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md` · `docs/review/ADVERSARIAL-V291-PREREG-2026-09-13.md`
+ `ADV-V291-{A,B,C,D}-2026-09-13.md` · `docs/traces/TRACE-2026-09-13-{fb-lag-filter-bytes,r24-lane-transfer,lkas-lane-to-aggregator-and-ghidra-gap}.md`
· `rlog-tools/studies/grind/{OPENLOOP-RING-DAMPING,B-OF-F-V282,ROUTE-6C-ATTRIBUTION}-2026-09-13.md` ·
`docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.md` · handoff `docs/handoffs/2026-09/HANDOFF-2026-09-13-V291-LOOP-OPENING-BUILT-NOT-CLEARED.md`.
**The 2026-09-10 and 2026-09-09 decision boxes are archived in `docs/archive/STATE-ARCHIVE-2026-09-13-decision-boxes-0909-0910.md`** —
their excitation-census verdict (the grinding is an excited resonance; the camera comb is real at lock
≈0.50; the estimator and ζ corrections) still stands and is folded into the paragraphs above.

---


## 📁 **THE V279-ERA REFERENCE AND 84 FINDING BLOCKS (2026-08-30 → 2026-09-11) ARCHIVED 2026-09-13**

Moved to `docs/archive/STATE-ARCHIVE-2026-09-13-v279-to-v290-blocks.md` at the V291 close-out to keep this file
under its working target. **A record, not an instruction.** Nothing was retracted by the move; the decision box
above carries every correction that was still decision-bearing.

## 📁 **EARLIER BLOCKS (24) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 🗂 INDEX TO THE BLOCKS BELOW

| what you want | look for the block titled |
|---|---|
| the flight order | *FLIGHT ORDER — A CHOICE, NOT A SINGLE BUILD* |
| why V222’s ratchet is a risk | *THE 8× IS COVERED WHERE THE OPERATOR FELT IT — BUT NOT AT THE RATCHET* |
| what V228 is | *V228 BUILT — V222 WITHOUT THE 8×* |
| the audible side effect | *"V228 CANNOT MAKE ANYTHING WORSE" IS FALSE* · *THE 40–49 Hz LIFT IS UNAVOIDABLE* |
| **my own withdrawn claims** | *SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED* · *CORRECTION TO THE BLOCK BELOW — AND TO MY OWN r24 ANCHOR* · *CORRECTION: "V62’s lever CREATED grind #2" is NOT settled* |
| what measurement can and cannot do | *THE RATCHET BAND CANNOT BE SCORED BY BAND POWER* · *RING-DOWN COMPUTED* · *CROSS-BUILD EVIDENCE HAS NEVER BEEN PRICED AGAINST ROUTE VARIATION* |
| what is closed and will not be re-proposed | *THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION* · *THE NOTCH IS NOW CLOSED* · *EXACTLY ONE BIQUAD* · *FOC CURRENT LOOP IS TRANSPARENT* · *LEVER A r26-HALF ONLY* · *r24 IS AT 94 % OF A STRUCTURAL PHASE CEILING* |
| what is still open | *THE TWO REMAINING QUESTIONS BOTH NEED A CAVE* · *OPEN OBSERVATION — an 11.4× residual* · *THE FRAME TEST IS INCONCLUSIVE* |
| the session narrative | *SESSION HANDOFF* (last block) |

---



## 📁 **EARLIER BLOCKS (22) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 📁 **EARLIER STATE (V204 → V208) IS ARCHIVED — with its closures kept here**

Split out 2026-08-30 at **138.6 KB**, against the ~150 KB soft target. The narrative, the numbers
and the retractions now live in `docs/archive/STATE-ARCHIVE-2026-08-30-v204-v208.md` — **a record,
not an instruction.** What that era CLOSED is kept below, because a closure is what stops a lever
being re-proposed:

| closed | verdict |
|---|---|
| the notch shelf | was cutting a **real 6–9 Hz damper 7.15× below the car**; fixed V214–V217 |
| the saturation census | **closed** — the last gate cannot fire; V207 retired **before** flight |
| `gp-0x6b70` saturation | **does not saturate**; V206’s best argument retracted |
| the command-gated-saturation model | **no mechanism exists** in this path — no gate rejects either |
| the 8 Hz ratchet notch | **stays rejected**; the friction lane is NOT "reverted to Honda" |
| two authority levers | **checked and closed**; a latent 18.52 Hz injector found silent |
| `0xC63AA` sensitivity | **41× understated** in the old record |
| the relay | a **SOFT** relay, curve **built at runtime** — unreadable from the image |
| `0xC63AE` sign | established **without a drive**; V206 built and priced |

🛑 **Tooling gotcha kept live, because it still bites:** `stock_fw_dump/code.bin` reads `0xFFFF`
at `0xC6CD0` because **V57 created that cell**. Do not use the stock dump as a stock reference for
post-V57 migrated cals — it hands you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and
`0xC64DE` read correctly from it.

## 📁 **EARLIER STATE (V184 → V202) IS ARCHIVED**

Split out 2026-08-30 at **173.6 KB**, past the ~150 KB soft target. Everything from the V202 notch work downward now lives in `docs/archive/STATE-ARCHIVE-2026-08-30-v184-v202.md` — **a record, not an instruction.** All of it is superseded: the candidate is **V222**, the ladder is V223–V226, and that notch was replaced at V208 and again at V217/V222.
