# EPS torque mode — the checklist for the REV-2 drive (fork tables + toggle config), and for reverting

**Updated 2026-09-13 night, after the first V293 drive (route 70).** The firmware **stays V293**; nothing is flashed.
What changes is the FORK: its Accord plant tables (code) and a rev-2 toggle config. Rev 1 of this checklist (flash
V293, restore the rev-1 config) is what route 70 flew; it is kept below as the fork-side revert.

| file | what it is |
|---|---|
| fork `Dom` **`8c4051ce6`** (two commits: `9622aee9f` "EPS plant tables re-identified on the V293 torque-mode firmware" + `8c4051ce6` "low-speed hold knots bounded by route 70's own hands-off data") | `HONDA_ACCORD_EPS_G_V` / `K_V` re-identified for the spring plant V293 left; old tables in the comment |
| `analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.json` | **the rev-2 config** (15 keys, a delta) — Galaxy → Settings → toggle backup → Restore |
| `…/toggle-config_V293_torque_mode_r2.decoded.json` | the same, readable; the scorer's `--config` argument |
| `…/toggle-config_V293_torque_mode.json` | **rev 1** (flown on route 70): the fork-side revert |
| `…/toggle-config_V282_rate_servo_REVERT.json` | the installed rate-servo tune — only with a V282-class image AND the old tables (fork revert of `8c4051ce6`) |
| `tools/make_galaxy_toggle_config.py` | regenerates all of them; `--decode <file>` prints any Galaxy backup |
| `rlog-tools/studies/grind/v293_flight_read.py` (v2) | the scorer for the drive; `V293-FLIGHT-READ-HOWTO.md` explains every row |

## 🛑 THE ONE RULE

**The rev-2 config presumes the rev-2 tables.** `AccordRatePlantFF` 1 on the OLD tables under-holds ×2.1 above
12 m/s (the integrator would carry half the turn); on the new tables it is the identified plant. So the ORDER is:
**fork first, config second, restart third.** And, unchanged from rev 1: a torque-mode config on a **rate-servo**
image (V282/V292) is over-delivery that nothing downstream catches — never create that state.

## A. Going to REV 2 (V293 stays in the ECU)

1. **Update the fork on the device to `Dom` ≥ `8c4051ce6`** (his usual pull/install). Confirm on the device:
   `git -C /data/openpilot log -1 --oneline` shows `8c4051ce6` or later, and
   `grep HONDA_ACCORD_EPS_G_V /data/openpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py` shows `550.0`.
2. **Galaxy → Settings → toggle backup → Restore → `toggle-config_V293_torque_mode_r2.json`.** It applies exactly
   these 15 keys and touches nothing else:
   `AccordRatePlantFF` 1 · `AccordEpsSpringScale` 1.0 · `AccordEpsGainScale` 1.0 · `AccordFFRateGain` 0.5 ·
   `SteerFriction` 0.011 · `SteerLatAccel` 14.0 · `SteerKP` 0.85 · `AccordTorqueKi` 0.30 ·
   `KeepLearnedLatAccelOffset` 0 · `SteerDelay` 0.2 · `UseAutoSteerDelay` 0 · `ForceAutoTuneOff` 1 ·
   `ForceAutoTune` 0 · `AdvancedLateralTune` 1 · `AccordTurnFFTaper` 0.
3. **Restart openpilot** (most keys broadcast at ~1 Hz, but the restart is what makes `initData.params` — the
   scorer's attribution — carry the config from segment 0).
4. Drive. **Watch the first 30 s at low speed** — the least-known band (the tables' 4–5 m/s knots are conservative
   guesses; the loop there is marginal by design of the fork's low-speed factor, not of this config).

## B. Fork-side revert (V293 stays)

Restore **`toggle-config_V293_torque_mode.json`** (rev 1) and restart — the state route 70 flew (loose, ratchety,
not unsafe). The tables commit can stay; rev 1 has `AccordRatePlantFF` 0, so they are inert.

## C. Reverting the EPS to V282/V292 (rate servo)

1. Restore `toggle-config_V282_rate_servo_REVERT.json` **and** put the fork back on the old tables
   (`git revert 8c4051ce6` on `Dom`, or check out `4247cb09e`) — the REVERT config has `AccordRatePlantFF` 1 and
   the rate-servo tune wants the rate-loop tables. Restart.
2. Kill openpilot (`tmux kill-server`), flash the V282 rwd (the operator names file + bus; nothing here does it).

## D. Verifying the state — from the wire

`python rlog-tools/studies/grind/v293_flight_read.py <route id> --config analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.decoded.json`

Section 0 must show: every config key matching in `initData.params`; `GitCommit` ≠ `4247cb09e` (the tables commit
or later); **Kp at 100 Hz = 0.85** (`torqueState.p/error`, the read that survives a mid-route change); the **branch
identity LIVE** (`torqueState.f` ≠ `starpilotLateralState.feedforward` on active frames — they are equal only in
the lat-accel branch); `latAccelOffset` effectively 0. Section 1 must still HOLD (the EPS map is on the wire: the
firmware did not change). Then §7 — the four symptom rows against route 70 and the V282 references.

## E. What this drive decides, and the revert triggers

- **Ratchety snapping** → dwells/min at th 0.25 deg/s (route 70: 15.2/7.7/4.6/1.2 by band; r6c 0.39/0.64/0.44/0.20)
  and the rate-magnitude concentration (0.468 → ≤ 0.40). If they do not fall: rung 2 of
  `docs/research/DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md` (a 100 Hz rate-feedback term in the fork).
- **Loose** → controller hold stiffness vs the plant's spring (kept ≈ as flown by `SteerKP` 0.85 at LAF 14).
- **Oversteer** → turn-hold actual/desired at >20 m/s (1.09 → ≤ 1.04) and the tracking gain 0.88/1.02/1.12 → 1.00.
- **Overshoot-then-correct** → step overshoot (0.44 relative at 10–20 m/s → ≤ 0.20).
- Plus: integrator share 0.38 → ≪; straight-line delivery 80 % → 90–110 %; 1–4 Hz prominence 6.5–11.8 dB → < 3 dB.
- **Revert triggers (his):** darty or loose feel worse than route 70, a one-sided pull, any oscillation, grinding,
  any EME warning or DTC. **Scorer's:** the 1–4 Hz outer-loop line; "ratchet worse than route 70".

## F. Standing fork facts that shape the numbers

- In the `AccordRatePlantFF` branch the output is `(P + I)/SteerLatAccel + plant_ff_torque + friction_torque`:
  **`SteerLatAccel` scales P and I only** — the one lever on the low-speed loop gain, because the hard-coded
  low-speed factor `[12, 10.5, 8, 5]` is ADDED to `SteerKP`. As flown (LAF 6) the loop at 4.5 m/s had PM −11° /
  Ms 12; at LAF 14 with Kp 0.85 it has PM 68° / Ms 2.16. **Every config still fails the bound at 3 m/s** — a
  direction, not a magnitude (the plant there is the study's weakest cell).
- The friction compensator is fed the LSF-inflated error (`(friction/0.30)·(1 + lsf/Kp)`); at Kp 0.85 the inflation
  at 4.5 m/s is 8.4, and the describing-function check finds no relay limit cycle at 0.011 (first sustaining value
  0.0235). The rule **friction > 0 requires Kp ≤ 1.0** holds.
- `SteerDelay` 0.2 (+0.1 software) = a 0.30 s lookahead; measured τ_eq 0.19–0.34 s. Not a lever worth a drive.
- The learner (`torqued`) keeps running; with `KeepLearnedLatAccelOffset` 0 nothing consumes its offset.
- **Safe Mode resets these keys** (`SAFE_MODE_MANAGED_KEYS`) — a route out of the config, never into it; on V293
  that lands on the fork's defaults (`AccordRatePlantFF` 1 with the new tables, the platform tune) — recoverable.
