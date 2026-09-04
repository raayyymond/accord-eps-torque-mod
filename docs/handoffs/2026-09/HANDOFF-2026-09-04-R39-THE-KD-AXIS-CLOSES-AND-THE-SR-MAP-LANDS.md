# HANDOFF — 2026-09-04 (late): r39 flies V282 + the SR map, the over-steer is EQUILIBRIUM, and the Kd axis CLOSES

**Read `docs/STATE.md`'s decision box first — it is fully rewritten and carries every number.** This
handoff is the narrative: what was asked, what was done, what changed my mind, and what is left.

---

## 0. The one-paragraph version

The operator flew **route r39** on **V282** with two openpilot-side changes: the variable steer-ratio
map (his fork) and `SteerKP` 0.6 → 0.8. He reported *"various grinding moments … worst-case over-steer
on turn at 20+ mph … general over-steer on curves … solid, stable lane keep on straights … amazing
authority"*, and asked whether Ziegler–Nichols tuning would improve smoothness. **Four subagents later:
the map is confirmed live and correct and explains 100 % of the over-steer; the over-steer is an
EQUILIBRIUM change, not transient overshoot; his "grinding" is the 7.3 Hz ring rather than the 20 Hz
creep grind, and his stronger outer loop is driving that ring ~4× harder; ZN is structurally the wrong
recipe for this loop AND points the wrong way; and the Kd axis it points away from turns out to be
CLOSED anyway, because the r24 arm is measured at 0.40–0.52 of the modelled magnitude.** **No firmware
was cut.** The single recommendation is `SteerLatAccel` 2.11 → **4.0**, which treats both symptoms.

---

## 1. What the operator asked

> *"New route on V282 again. Using the new custom StarPilot fork (my version with custom SR)… various
> grinding moments, I generally created a bookmark at these instances a little bit after they happen;
> worst-case over-steer on turn at 20+ mph; general over-steer on curves at medium and at high speed;
> solid, stable lane keep on straights; amazing authority."*
> `/goal Updated firmware and accompanying custom StarPilot lateral tuning settings … which fixes
> V282's issues.` … *"I think we should try ZN tuning if you think it will help improve the autonomous
> steering smoothness (remove stuttering)."*

Then two rulings mid-session that reshaped the whole analysis:
> *"Oversteer is probably outerloop responsibility"*
> *"Innerloop is merely responsible for accelerating the steering angle as demanded by outerloop."*

**That second sentence is a SPECIFICATION.** It makes the EPS rate PID an **actuator judged on
fidelity**, not a regulator judged on disturbance rejection — and it is what disqualifies ZN.

---

## 2. How the session was run

Orchestrator + four subagents on disjoint surfaces, all briefed as subagents reporting to `main`:

| agent | surface | outcome |
|---|---|---|
| `dec39` | decode both cache families; build attribution; SR-map liveness; exposure census | map live (slope 0.99997); found the route-counter reset and the V64 byte-4 decode trap |
| `over39` | the outer loop / over-steer | **equilibrium, not transient**; the identifying split; LAF 2.11 → 4.0 |
| `grind39` | the bookmarks, the V282 pre-registration, the deadband, the ring | **both bookmarks are 7.3 Hz**; prereg scored as written; ring pinned to n = 8 |
| `zn39` | inner-loop sizing, ZN, the Kd/Kp trade | ZN rejected structurally; **the Kd axis closes**; withdrew its own recommendation twice |

**Every one of the four self-corrected at least once**, and three of the four corrections came from the
orchestrator verifying a crux rather than relaying it. That is the process working; it is also the
reason this handoff is long.

---

## 3. What changed my mind, in order

1. **I predicted transient overshoot. It is equilibrium.** `over39` falsified it: `R` climbs from 0.90,
   crosses 1.00 at ~0.8 s, and stays 5–25 % over for the whole curve, with **quasi-static excess
   exceeding transient**. Confirmed by a ratio-free statistic I proposed for exactly this reason —
   peak÷settled is **1.173 (r35) vs 1.171 (r39)** while their levels differ by ΔR = +0.192. **Same
   shape, displaced level.**
2. **I assumed the map and `SteerKP` were confounded. They are not.** SR enters `latcontrol_torque` in
   one place, so it moves the measurement scale `1/ρ` only; `SteerKP` can only move `R_m`. Measured:
   `1/ρ` 0.784 → 0.988 (×1.26, the map's design), `R_m` 1.178 → 1.123 with **overlapping CIs**.
   ⇒ **the map explains the whole delta.**
3. **I recommended a Kd raise. Then the measurement inverted it.** `zn39`'s forced-geometry test (fix
   the measured complex sum, scale `|Lr|`, let `Ls` be forced — no free parameter) shows the Kd axis
   flips sign as the r24 arm shrinks. `grind39` then measured that arm at **0.41/0.52**, and the duty
   ladder renormalised on r39's own `|T|` gives **0.46**. **Kd 160 lands at `|L| = 0.997`.**
4. **I said the 27–32 Hz mode rested on one estimator family. It rests on two of three.** The table
   scans 2–24 Hz only; cmd-IV's "none" is a **window artefact**. `Ku = 227` is the conservative
   worst-family bound, never MEASURED-grade.
5. **I claimed the equilibrium verdict was instrument-independent.** Two of three discriminators are;
   the quasi-static-vs-transient split **reverses** under the specific-force array (by 0.011 m/s²).
   `over39` downgraded that section against itself.

---

## 4. The ZN answer, since it was the operator's explicit question

**No, and for three independent reasons** (detail in `docs/research/ZN-BACKWARDS-NO-OVERSHOOT-2026-09-04.md`):

1. **ZN designs IN a closed-loop peak of 1.3–1.5** — precisely what an actuator must not have.
2. **ZN's only reachable form here is a Kd CUT** (`Td` has no cell), while the fidelity optimum wanted
   Kd RAISED. It points the wrong way on the axis that sets peaking. Its one right answer (Kd 162 ≈ the
   loop-shape study's 160) is an arithmetic accident.
3. **The no-overshoot family is structurally forbidden.** Kd 90 / Kd 54 both put `|L(7.3)| ≥ 1.01`,
   because only the servo arm carries Kp/Kd — turning the controller down **withdraws the cancellation**
   that keeps the two-arm sum sub-unity. **This loop has no "quiet it down" regime.**

⭐ And the target it was aimed at is gone anyway: **at the measured r24 arm, the best Kd anywhere is
worth 1–2 % on the ring** (against 26 % under the modelled arm). **Kd is not a weak lever — it is not a
lever.**

---

## 5. Deliverable

**openpilot, and it is the whole recommendation:**
> **`SteerLatAccel` 2.11 → 4.0, flown alone.** Keep `SteerKP` 0.8, `SteerFriction` 0.03, keep the map.
> Firmware stays **V282**. The Galaxy ceiling is already 16.893 (device verified on `8a28dcef`).

Sized from r39's own f/i balance — the feedforward over-commands **1.86×** and the integrator spends
**46 % of itself** cancelling it. It cuts the over-command that produces the equilibrium over-steer
**and** the drive into the 7 Hz ring, on two independent instruments. A second estimator puts the
endpoint at 9.5; the two disagree 2.4×, so 4.0 now.

**firmware: nothing.** `accord-firmwares` has no new artifact this session, deliberately.

---

## 6. Open, for the next session

1. ⭐ **The plant-magnitude identification drive** — 427 `T` tap + 0x18F rate simultaneously, swept
   excitation. **Two agents independently ranked it above any further dose.** The plant's magnitude
   above ~5 Hz has **never** been measured, which is why `|T(f)|`, `f_-3dB` and `max|T|` are all
   model-composed — and this session's arithmetic **inverted twice on that one unmeasured number**.
2. **Score the LAF-4.0 drive** on `R_m` (does it fall toward 1.00?) and the 6–10 Hz loaded-turn bar.
3. **The ~11 % `R_m` residual** — present on every arm, unmasked by the map, unreachable by any gain
   knob. Three candidate mechanisms, all BELIEF, not separable on one drive.
4. **Five recorded defects** (route-counter reset, the V64 byte-4 decode, `backcalc_extract.py`'s
   src-128/129 mix, the `r39_1ab.json` tap descriptor, and a discarded Kp discriminator) — all in
   `STATE.md`, none fixed.
5. **`docs/STATE.md` is 194 KB** (down from 200.9). Under the 256 KB cap, over its own ~150 KB target.
6. **A louder grinding episode the operator did NOT bookmark**, at route t 883.2 (idx 83, 116°,
   30.6 deg/s) — worth showing him.

---

## 7. Artifacts written

`docs/research/ZN-BACKWARDS-NO-OVERSHOOT-2026-09-04.md` (Parts I–IV, close box at top) ·
`docs/research/LOOP-MODEL-CONVENTION-DEFECT-2026-09-04.md` ·
`rlog-tools/studies/osc-highangle/OVERSTEER-V282-r39-2026-09-04.md` ·
`rlog-tools/studies/grind/V282-READ-r39-2026-09-04.md` ·
`analysis-2020accord/extract/extract_r39_cache.py` · caches at `_scratch/cache/r39/` and
`analysis-2020accord/_scratch/cache/r39/` · two new memories under `memory/accord/mechanism/`.
