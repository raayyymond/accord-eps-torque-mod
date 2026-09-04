# StarPilot-side fix and fork maintenance — investigation, 2026-09-04

**Scope.** Can the measured steering problems be fixed on the openpilot side instead of in the EPS
firmware, and stay maintainable (GitHub fork syncable from upstream, Galaxy software-update button
still working)?

**Method.** Read-only inspection of the checkout at `C:\Users\dudei\Desktop\Projects\openpilots\StarPilot`
(remote `https://github.com/firestar5683/StarPilot.git`, branch `Dom`, HEAD `3d4c625de`), plus the
operator's decoded toggle backups in `analysis-2020accord/reference/`. Nothing in the StarPilot
checkout was modified. Every claim below is marked **EVIDENCE** (I read the code path) or **BELIEF**.

---

## 0. RETRACTED — an earlier revision of this file claimed SteerRatio was already 16.1

**That claim was wrong and is withdrawn.** I ordered the three decoded toggle backups by filename
instead of by mtime. Corrected, with `ls --time-style=full-iso`:

| file | mtime | SteerRatio | note |
|---|---|---|---|
| `toggle-backup(2).decoded.json` | 2026-09-02 18:50 | 16.33 (stock) | pre-tune, ForceAutoTune True |
| `toggle-backup_20260902.decoded.json` | 2026-09-02 21:27 | **16.1** | the r34 drive |
| `toggle-backup_V281R3.decoded.json` | **2026-09-03 00:02** | **12.5** | the r35 drive — **newest** |

**`SteerRatio = 12.5` is the current value.** Independently confirmed on the wire by the orchestrator:
`liveParameters.steerRatio` reads 12.50 at the first and last sample of all three V283 routes
(r36/r37/r38), with latAccelFactor 2.110 and kp 0.600. The operator also chose it deliberately —
*"Going to keep SteerRatio at 12.5 for now. Dont want to confound it with the Ki update."*

The other params are unchanged across both tuned backups: `AdvancedLateralTune True`,
`SteerLatAccel 2.11`, `SteerFriction 0.03`, `SteerKP 0.6`, `ForceTorqueController True`,
`ForceAutoTune False`, `ForceAutoTuneOff True`, `SteerDelay 0.2`, `AutomaticUpdates False`.

**The SteerRatio lever is NOT spent.** See §4 for what that means — it does not become "so set it to
16.1", it becomes the opposite.

---

## 1. Levers on the lateral torque path

### 1a. Already exposed as a toggle/param — zero maintenance

**EVIDENCE**, `common/params_keys.h` (grep `SteerFriction`, `SteerKP`, `SteerLatAccel`, `SteerRatio`,
`ForceTorqueController`, `ForceAutoTune`, `ForceAutoTuneOff`) and
`starpilot/common/starpilot_variables.py` (grep `advanced_lateral_tuning = self.get_value("AdvancedLateralTune")`):

| Param | Where it lands | Clamp enforced in `starpilot_variables.get_value` | Operator's value |
|---|---|---|---|
| `SteerRatio` | `liveParameters.steerRatio` → `VM.update_params` → `VM.calc_curvature` (the **measurement**) | `0.5 x CP.steerRatio` … `1.5 x CP.steerRatio` = **8.17 … 24.50** (Accord `CP.steerRatio = 16.33`) | 16.1 |
| `SteerLatAccel` | `torque_params.latAccelFactor`; scales FF, friction magnitude, PID output→torque conversion, **and the PID limits** | `0.5 x 1.689` … `1.5 x 1.689` ≈ **0.84 … 2.53** | 2.11 |
| `SteerFriction` | `torque_params.friction` → `get_friction()` centre-crossing boost | `0 … 1` | 0.03 |
| `SteerKP` | overwrites `LaC.pid._k_p` **every control frame** | `0.5 x 0.6` … `1.5 x 0.6` = **0.30 … 0.90** | 0.6 |
| `SteerDelay` | `lat_delay` — the setpoint lookahead / jerk lookahead | `0.01 … 1.0` | 0.2 |
| `ForceTorqueController` | converts the Accord's PID lateral tune to a torque tune | bool | on |
| `ForceAutoTuneOff` | pins `liveParameters.steerRatio` to the `SteerRatio` param and `stiffnessFactor` to 1.0 | bool | on |

**There is no `SteerKI` param. EVIDENCE:** a repo-wide grep for `SteerKI`, `SteerKi`, `steer_ki` and
`SteerIntegral` across every file returns zero hits. The orchestrator's suspicion is **confirmed**.
The FLM ("Galaxy" auto-tune workspace) cannot reach it either — `starpilot/system/the_galaxy/flm_workspace.py`
`TRIAL_PARAM_SPECS` / `GENERIC_PARAM_METADATA` enumerate exactly `SteerDelay`, `SteerFriction`,
`SteerKP`, `SteerLatAccel`, `SteerRatio` and the two auto-tune booleans. No integral term anywhere.

**Two things worth knowing about the already-exposed set:**

1. **`SteerKP` is applied unconditionally and destroys two upstream behaviours. EVIDENCE:**
   `selfdrive/controls/controlsd.py`, in `Controls.update()`:

   ```python
   if hasattr(self.LaC, "pid") and self.CP.lateralTuning.which() != "pid":
     self.LaC.pid._k_p = self.starpilot_toggles.steerKp
   ```

   and `starpilot_variables.py`: `toggle.steerKp = [[0], [ …SteerKP… ]]` — a **single-breakpoint** curve.
   This overwrites (a) the whole low-speed `KP_INTERP = [250, 120, 65, 30, 11.5, 5.5, 3.5, 2.0, 0.6]`
   ramp from `latcontrol_torque.py`, and (b) the Accord's own `HONDA_ACCORD_TORQUE_KP = 0.8` set in
   `LatControlTorque.__init__`. With `SteerKP = 0.6` the car runs a flat kp of 0.6 at every speed.
   This matches the kit's measured "kp = 0.600 on all 60 routes".
   ⇒ **`SteerKP` 0.6 → 0.8 is a free, zero-maintenance step that restores the value StarPilot itself
   chose for this car.** It is +33 % proportional gain, well inside the 0.30–0.90 clamp.

2. **`SteerLatAccel` is a whole-loop gain, not just a feedforward gain. EVIDENCE:**
   `opendbc_repo/opendbc/car/interfaces.py` — `torque_from_lateral_accel_linear` is
   `lateral_acceleration / latAccelFactor` and `lateral_accel_from_torque_linear` is
   `torque * latAccelFactor`; `latcontrol_torque.update_limits()` sets the PID limits to
   `lateral_accel_from_torque(±1.0)`. So lowering `SteerLatAccel` multiplies P, I, D **and** FF by
   `1/latAccelFactor` on the way to CAN — it is the outer loop-gain knob. He is at 2.11 of a 0.84–2.53
   range, i.e. there is only ~20 % of *reduction* headroom left before the clamp; going **down** to
   e.g. 1.7 would raise total loop gain by 24 %.

### 1b. Needs a code change

**The torque controller's KI.** EVIDENCE, the full chain:

- `selfdrive/controls/lib/latcontrol_torque.py`: `KI = 0.35`, then
  `self.pid = PIDController([INTERP_SPEEDS, KP_INTERP], KI, rate=1/self.dt)`.
- Then, in `LatControlTorque.__init__`:

  ```python
  if self.is_honda_accord:
    self.pid._k_p = [self.pid._k_p[0], [*self.pid._k_p[1][:-1], HONDA_ACCORD_TORQUE_KP]]
    self.pid._k_i = [self.pid._k_i[0], [HONDA_ACCORD_TORQUE_KI] * len(self.pid._k_i[1])]
  ```

- `selfdrive/controls/lib/latcontrol_vehicle_tunes.py`, constants block:

  ```
  HONDA_ACCORD_STEER_RATIO_SCALE = 14.0 / 16.33
  HONDA_ACCORD_TORQUE_KP = 0.8
  HONDA_ACCORD_TORQUE_KI = 0.15
  ```

- `git log -S HONDA_ACCORD_TORQUE_KI` returns exactly one commit: **`50e1c1d37` "what a mornin",
  2026-08-18**. Same for `..._KP`. So the Accord special-case *is* the 2026-08-18 change the kit
  measured: before it, the Accord ran the generic `KI = 0.35`; after it, 0.15. **The kit's "ki went
  0.35 → 0.15 by an upstream commit on 2026-08-18" is confirmed, and this is the line that did it.**
- The `HONDA_ACCORD_TORQUE_KP = 0.8` set on the same line is **inert in practice**, because
  `controlsd` overwrites `_k_p` with `SteerKP` every frame (see 1a.1).

**There is no other route to KI.** `torque_ki_mult` exists but is gated on `self.use_bolt_ki_multiplier`
(Bolt only) and is driven by the deprecated `kd` field of the torque tune, which no param writes.

**Where the integrator sits, mechanically. EVIDENCE** (`common/pid.py`, `latcontrol_torque.py`):

```python
output_lataccel = self.pid.update(pid_log.error, error_rate=-measurement_rate,
                                  speed=CS.vEgo, feedforward=ff,
                                  freeze_integrator=freeze_integrator)
output_torque = self.torque_from_lateral_accel(output_lataccel, self.torque_params)
```

- error is in **lateral-accel units**: `error = setpoint - measurement`, `measurement = measured_curvature * vEgo**2`.
- integration is `i += k_i * 0.01 * error` at 100 Hz.
- anti-windup is conditional integration against `pos_limit/neg_limit`, which are
  `lateral_accel_from_torque(±1.0) = ±latAccelFactor` — i.e. **the integrator alone is allowed to reach
  full ±1.0 normalized steering torque**.
- `freeze_integrator = steer_limited_by_safety or CS.steeringPressed or CS.vEgo < threshold or unwind_detected`.
- on disengage, `if not active: output_torque = 0.0 … self.pid.reset()`.
- on driver-hands-off transition, `self.pid.i *= 0.8`.

**The structural argument for moving the integrator here is sound. EVIDENCE for the operator's specific
objection:** `self.pid.reset()` in the `not active` branch means openpilot's integral state is zeroed
the instant lateral disengages, and `output_torque = 0.0` is what goes to CAN. openpilot's integrator
therefore **cannot** produce the 139–383 counts x 0.5–1.0 s post-disengage residual that firmware Ki 50
produced. It is also visible on the wire (`controlsState.lateralControlState.torqueState`) and frozen
whenever the driver touches the wheel. All three of the operator's structural complaints about the
in-EPS integrator are answered by moving it up one loop.

**What KI is worth. BELIEF, arithmetic from the code:** with `KI = 0.15` and a persistent error of
0.2 m/s², the integrator supplies 0.03 m/s²/s — it takes **13 s** to build 0.4 m/s² of correction.
Highway lane-keeping corrections live on a 1–3 s timescale, so at 0.15 the integral term does
essentially nothing within a correction. `KI = 0.35` → 5.7 s; `KI = 0.6` → 3.3 s; `KI = 1.0` → 2.0 s.
The first value where the integrator acts *within* one correction is around 0.5–0.6.

**Minimal patch: one line, one file.**

```diff
--- a/selfdrive/controls/lib/latcontrol_vehicle_tunes.py
+++ b/selfdrive/controls/lib/latcontrol_vehicle_tunes.py
@@
-HONDA_ACCORD_TORQUE_KI = 0.15
+HONDA_ACCORD_TORQUE_KI = 0.35   # 2020 Accord on modified EPS: EPS command->rate DC gain is
+                                # 0.11-0.36 at demand index 5-40; 0.15 cannot close that droop
+                                # inside a lane-keeping correction. 0.35 = the generic upstream
+                                # value this car ran until 2026-08-18 (commit 50e1c1d37).
```

That is the entire change. No new param, no UI, no cereal field, no `params_keys.h` edit.

### Risks of raising KI — be explicit about these

1. 🛑 **The anti-windup cannot see the EPS stalling. EVIDENCE:**
   `controlsd.py`: `self.steer_limited_by_safety = abs(CC.actuators.torque - CO.actuatorsOutput.torque) > 1e-2`
   — that compares openpilot's request against the **carcontroller's own** rate-limited output
   (`rate_limit(..., ±STEER_DELTA * DT_CTRL)`, `STEER_DELTA_UP = STEER_DELTA_DOWN = 3`). It says nothing
   about the EPS's internal assist-map clamp. When the EPS is stalled at 0.36 of the request, openpilot
   sees no limiting, does not freeze, and winds toward the ±1.0 rail. The ceiling is full authority,
   not "the point where the ECU stopped responding".
2. **The plant gain varies ~8x along the demand axis** (0.11 → 0.86). As the integrator raises the
   command it drags the EPS up its own gain curve, so the loop is self-limiting — but one KI cannot be
   right for both ends, and the wind-up-then-release transition at the knee is exactly the oversteer
   signature the firmware Ki produced. **The oversteer risk is not removed by moving the integrator; it
   is made observable and resettable.**
3. **Interaction with the friction term is small at his settings.** `get_friction` returns at most
   `±friction x latAccelFactor = ±0.03 x 2.11 = ±0.063 m/s²` (≈ ±0.03 normalized torque). With
   `SteerFriction = 0.03` the friction/deadzone term is far too small to mask or fight a growing
   integrator. `steeringAngleDeadzoneDeg` is 0 for the Accord (`configure_torque_tune` passes 0.0), so
   `lateral_accel_deadzone` is 0 too.
4. **The lateral jerk limiter shapes the setpoint, not the integrator.** `MAX_LAT_JERK_UP = 2.5 m/s³`
   and the 1.2 Hz `jerk_filter` act on `desired_lateral_jerk`, which enters `setpoint`. A larger
   integrator can therefore out-run the jerk-limited setpoint on release; the CAN-side
   `STEER_DELTA = 3 counts/frame` (0.33 s full-scale slew) is the only backstop.
5. **The `unwind_detected` and `steeringPressed` freezes are the safe parts** and stay intact.

### Variable steering ratio — not worth it

**EVIDENCE:** `selfdrive/controls/controlsd.py` already has the hook —

```python
elif self.CP.carFingerprint == HONDA_CAR.HONDA_ACCORD and not accord_ratio_is_explicit:
  sr *= get_honda_accord_steer_ratio_scale(CS.vEgo)
```

and `get_honda_accord_steer_ratio_scale(_v_ego)` **ignores its argument** and returns the constant
`14.0/16.33`. So a speed-varying SR would be a two-line change to that function. But:

- **It is currently disabled for him.** `accord_ratio_is_explicit` is true whenever the `SteerRatio`
  param differs from `CP.steerRatio` by more than 0.01 — which it does (16.1 vs 16.33) — so the
  built-in 0.857 scale never applies. **EVIDENCE**, same block.
- The kit's own measurement is that the rack ratio varies with **steering angle** (16.1 → 13.1 from
  centre to lock), not with speed. openpilot's hook is speed-indexed. An angle-indexed variable ratio
  would need `VM.update_params` called with an angle-dependent `sr` — which changes the measurement
  gain of the very loop that is closing on it, i.e. a state-dependent loop gain. **BELIEF: that is a
  worse-conditioned control problem than the one it fixes.**
- Highway lane-keeping lives inside ±50° of centre, where the ratio is ~16.1 and flat. **The scalar 16.1
  he already has is the truthful value over the operating range.** A curve buys nothing on the highway
  and risks the loop in the one regime (large angles) where the 7 Hz ring already lives.

⇒ **Recommendation: no variable SR. The scalar, set truthfully, is the same effect where it matters.**

### The boundary — what openpilot cannot touch

**Confirmed, EVIDENCE:**

- openpilot's command reaches the car as a normalized torque, rate-limited to
  `STEER_DELTA_UP/DOWN = 3` counts per 10 ms frame (`opendbc/car/honda/values.py`,
  `carcontroller.py: rate_limit(torque_cmd, self.last_torque, -3*DT_CTRL, 3*DT_CTRL)`), i.e. **0.33 s
  minimum for a full-scale swing** — a hard ~1.5 Hz ceiling on large-amplitude command motion.
- The setpoint is filtered by `jerk_filter` at **1.2 Hz** and limited to 2.5 m/s³; the D term's
  `measurement_rate_filter` cuts at 2.0 Hz. The desired curvature itself comes from the model/planner
  at 20 Hz.
- `create_steering_control` is appended every frame (100 Hz), so the *sample* rate is 100 Hz, but the
  *authority* above ~2 Hz is negligible.

⇒ **The 7 Hz strong-turn ring and the ~20 Hz creep grind are outside openpilot's reach**, in both
directions: it cannot excite them deliberately and it cannot damp them. They are closed inside the
EPS's own rate loop. **An openpilot change is a candidate substitute for the deadband / understeer /
oversteer work ONLY.** The orchestrator's understanding is correct.

One refinement to the brief: SteerRatio enters the torque controller in **two** places, not one —
`latcontrol_torque.py` `measured_curvature = -VM.calc_curvature(...)` (the control-bearing one) and
`curvature_deadzone = abs(VM.calc_curvature(math.radians(effective_deadband_deg), ...))` a few lines
below. The second is inert here because `steeringAngleDeadzoneDeg = 0` for the Accord. `controlsd` also
computes `self.curvature` from `VM` for the turn-hold/blinker heuristics and publishes it as
`CC.currentCurvature`. None of that changes the conclusion: **lower SR ⇒ over-read curvature ⇒
under-turn.**

---

## 2. Maintainability mechanics

### 2a. What the Galaxy update button fetches

**EVIDENCE**, `system/updated/updated.py`:

- **Remote:** literally whatever `origin` is in `/data/openpilot/.git/config`. The updater runs
  `git ls-remote --heads` and `git fetch origin <branch>` inside the overlay. **There is no URL
  allowlist, no owner check, and no signature verification anywhere in `updated.py`.** An arbitrary
  fork remote works.
- **Branch:** the `UpdaterTargetBranch` param. If unset it defaults to `get_branch(BASEDIR)` — the
  branch currently checked out. `set_params()` writes it back every cycle.
- **Branch list in the UI:** `UpdaterAvailableBranches`, built from `git ls-remote --heads` on `origin`
  (excluding `release2`, `release2-staging`). `selfdrive/ui/layouts/settings/software.py` renders it as
  the "Target Branch" → SELECT picker. **So the picker shows whatever branches exist on the configured
  origin** — his fork's branches, if origin points at his fork.
- **Nothing in the update path would break if `origin` points at his fork**, provided the fork has a
  branch with the same name he is on (`Dom`) and the submodule URLs still resolve (they are absolute
  GitHub URLs in `.gitmodules`, unaffected by a fork of the superproject).
- **Not settled by the code:** whether `comma connect` / the Galaxy backend does anything server-side
  with the origin URL (`starpilot/system/the_galaxy/the_galaxy.py` reads
  `git config --get remote.origin.url` and reports `forkMaintainer` telemetry). That is *reporting*, not
  gating, as far as the code shows. To settle it: point `origin` at the fork on the device and watch
  whether the Galaxy software page still lists branches and offers the update.

### 2b. The actual on-device update flow — and whether a local patch survives

**EVIDENCE**, `updated.py` + `launch_chffrplus.sh`:

1. `init_overlay()` mounts an OverlayFS with `lowerdir=/data/openpilot`, upper/work in `/data/safe_staging`.
2. `fetch_update()` runs, **inside the overlay**:
   `git fetch origin <branch>` → `git checkout --force -B <branch> FETCH_HEAD` →
   `git reset --hard` → **`git clean -xdff`** → submodule sync/update/reset.
3. `finalize_update()` `copytree`s the merged view to `/data/safe_staging/finalized`, runs
   **another `git reset --hard`**, `git gc`, and sets `.overlay_consistent`.
4. At next boot `launch_chffrplus.sh` swaps `finalized` into place as `/data/openpilot`.

⇒ **A local uncommitted patch is destroyed.** `git reset --hard` reverts a modified tracked file and
`git clean -xdff` deletes an untracked one; the finalized tree that replaces `/data/openpilot` is a
clean checkout of the remote branch. There is also a "Fast Update" path (long-press the Download
button, `software.py::_execute_fast_update`) that is even blunter: `git fetch --depth=1 origin <branch>`
then **`git reset --hard FETCH_HEAD` directly in `/data/openpilot`**, then reboot.

⚠ **One nuance that is easy to get wrong.** `launch_chffrplus.sh` has a guard:

```sh
find ${DIR}/.git -newer ${DIR}/.overlay_init | grep -q '.'
# → "has been modified, skipping overlay update installation"
```

It tests **`.git`, not the working tree.** So a bare `sed` on a `.py` file does *not* trip it — the
update installs and wipes the edit. A `git commit` (which writes `.git`) *does* trip it, and then the
update silently stops installing. Neither is a workable "local patch" story.

⇒ **A code change requires a fork. Params do not: params live in `/data/params`, outside the repo,
and are untouched by every path above.**

### 2c. The lowest-maintenance shapes, compared honestly

| Shape | What it costs | What it can reach |
|---|---|---|
| **(i) Params only, no fork** | **Zero.** Survives every update, the Galaxy button is untouched, no git at all. | `SteerRatio`, `SteerLatAccel`, `SteerFriction`, `SteerKP` (0.30–0.90), `SteerDelay`. **Not KI.** |
| **(ii) Fork = upstream + one commit** | `git remote set-url origin <his fork>` once on the device; then a fork sync **before every device update**. | Anything, including KI. |
| **(iii) New param + UI + plumbing** | Touches `params_keys.h` (96 commits/3 mo), `starpilot_variables.py`, `lateral.py`, `controlsd.py`. | Same as (ii), with ~4x the conflict surface. **Not worth it.** |

**How often the target file changes upstream — the honest answer to "is this easy to maintain".
EVIDENCE**, `git rev-list --count --since=2026-06-01`:

| file | commits in ~3 months |
|---|---|
| `selfdrive/controls/lib/latcontrol_torque.py` | **92** |
| `selfdrive/controls/lib/latcontrol_vehicle_tunes.py` | **84** |
| `selfdrive/controls/controlsd.py` | 31 |
| `common/params_keys.h` | 96 |
| *(whole repo)* | *1113* |

That looks brutal — roughly a commit a day on the file. **But the number that matters is the churn on
the lines the patch touches.** `git log -L 76,82:selfdrive/controls/lib/latcontrol_vehicle_tunes.py`
returns **4 commits since 2026-06-01** (2026-06-26, 08-17, 08-18, 08-23) — the Accord constants block
has been touched roughly **once every three weeks**, and every touch was a constant-value edit.

⇒ **BELIEF, from those two numbers:** a one-line patch to `HONDA_ACCORD_TORQUE_KI` will rebase cleanly
on most syncs and will conflict perhaps once a month, as a trivial "both changed this constant" hunk
that takes seconds to resolve. That is a genuinely low maintenance burden — **but only because the patch
is one constant.** Any patch that adds *structure* to `latcontrol_torque.py` inherits the 92-commit
churn and will conflict constantly.

### 2d. GitHub "Sync fork" with an extra commit — what actually happens

**BELIEF** (GitHub product behaviour, not readable from this repo; stated with the reasoning):
GitHub's **Sync fork** button fast-forwards when the fork branch is only *behind*. When the branch is
*ahead and behind* (his case — one patch commit on top), the button offers **"Update branch"**, which
performs a **merge** of upstream into his branch and creates a merge commit; if the merge conflicts it
refuses and tells him to resolve locally. The dropdown also offers **"Discard N commits"**, which hard
resets to upstream and **would silently delete his patch** — that is the button to never press.

**Recommendation: merge, not rebase, and use the web button.** Rebasing needs a local clone and force
push; merging is what the web button does and it never rewrites history, so the device — which only ever
`fetch`es and `reset --hard`s to the remote branch — is perfectly happy either way. The one cost of
merging is a noisy history, which does not matter here.

**To settle 2d for real:** create the fork, add the one-line commit, click Sync fork once, and observe.
Five minutes, and it removes the only BELIEF in the maintainability answer.

### 2e. Concrete fork setup

1. Fork `firestar5683/StarPilot` on GitHub. Create branch `Dom` from upstream `Dom`.
2. Commit the one-line KI change on his fork's `Dom`.
3. On the device (SSH): `cd /data/openpilot && git remote set-url origin https://github.com/<him>/StarPilot.git`
4. Settings → Software → Target Branch → `Dom` (it will now list his fork's branches), then Download/Install.
5. Each time upstream moves: GitHub → Sync fork → **Update branch** (never "Discard commits"), then the
   Galaxy update button on the device as usual.

`AutomaticUpdates` is already `False` in his params, so nothing updates behind his back.

---

## 3. Recommendation

> ⚠ **Superseded by §4.** §3 was written on the retracted premise that SteerRatio was already 16.1 and
> that the car under-delivered. It does not. Read §4 instead; only the fork mechanics below survive
> unchanged.

**Step 2 — the one-line fork.**
`HONDA_ACCORD_TORQUE_KI: 0.15 → 0.35` in `selfdrive/controls/lib/latcontrol_vehicle_tunes.py`.
Maintenance cost in plain terms: **one fork, one commit, one "Sync fork" click before each device
update, and a trivial one-line conflict roughly once a month.** The Galaxy update button keeps working
exactly as it does now — the updater does not validate the remote at all.

Start at **0.35** (the value this car ran until 2026-08-18), not at 0.6+. It is a 2.3x step, it is a
value the codebase itself shipped for this platform, and it bounds the first drive's risk. Watch
`controlsState.lateralControlState.torqueState.i` on the wire before considering a second dose.

**Step 3 — do not do:** a variable steering-ratio curve, a new `SteerKI` param with UI plumbing, or any
structural patch to `latcontrol_torque.py`. Each costs far more maintenance than it returns.

**What none of this fixes.** The **7 Hz strong-turn ring** and the **~20 Hz creep grind** are inside the
EPS's own rate loop, an order of magnitude above openpilot's ~1.5–2 Hz command authority. No openpilot
change — param or code — can touch them. Those remain firmware work.

**What it does fix, and why it is structurally better than firmware Ki 50.** The steady-state droop
(deadband/understeer) gets integral compensation from a loop that (a) models its own output as a torque,
(b) zeroes its integral state on lateral disengage, so it cannot leave residual torque on the wire, and
(c) exposes that state in `controlsState` where it can be scored from an rlog. The oversteer risk does
not disappear — the 8x plant-gain variation along the demand axis is still there, and openpilot's
anti-windup **cannot see the EPS saturating** — but the failure becomes observable and resettable
instead of hidden in ECU state.

---

## 4. Re-based recommendation — SteerRatio 12.5, V283 over-delivering

Supersedes §3. Inputs from the orchestrator, treated as given: SR 12.5 measured on the wire on
r36/r37/r38; V283 over-delivers **+0.334 m/s²** on matched frames; tight-curve PID decomposition
**f +0.800, p −0.300, i −0.392, net +0.108**, median signed output **+0.009**.

### 4a. SteerRatio 12.5 is currently a BRAKE on the oversteer — do not raise it

**EVIDENCE**, `opendbc_repo/opendbc/car/vehicle_model.py`:
`calc_curvature(sa, u, roll) = curvature_factor(u) * sa / self.sR + roll_compensation(roll, u)`.
`sR` is a **pure divisor** on the steering-angle term; `curvature_factor` depends on the slip factor,
not on SR; and `stiffnessFactor` is pinned to 1.0 by `ForceAutoTuneOff`
(`paramsd.resolve_vehicle_model_params`). So the measurement is inflated by exactly
**16.1 / 12.5 = 1.288x** relative to a truthful ratio, with no second-order term.

The loop closes on that inflated measurement. Consequences, in order:

1. **Raising SR 12.5 → 16.1 shrinks `measurement` by 22 %**, which makes `error = setpoint − measurement`
   **more positive**, which makes P and I push **harder**. On a car that is already over-delivering,
   **that makes the oversteer worse.** The understeer logic in the brief is correct in isolation but
   has the wrong sign for the current situation: with V283's firmware integrator in the loop, SR 12.5
   is subtracting ~29 % of demand and partially cancelling it.
2. The operator's instinct is right for a reason beyond confounding: 12.5 is doing load-bearing work
   right now. **Do not touch SteerRatio while V283's Ki is in the car.**

### 4b. ~~Open crux~~ **RESOLVED by the orchestrator, 2026-09-04: the +0.334 is REAL — the metric is SteerRatio-free**

🛑 **RESOLUTION (EVIDENCE, method: read the metric's own definition in the script that produces it).**
`rlog-tools/studies/osc-highangle/oversteer_v283.py` documents its curve metric at the head of the curve block:
**"pose = livePose yaw*v - g sin(roll) [the road] ; vyaw = yaw*v [no roll term]"**, and the reported columns are
`os_pose` / `os_vyaw`. The overshoot is therefore computed from the car's MEASURED YAW RATE times speed, with the
roll term removed — **not** from `VM.calc_curvature`, and **not** from openpilot's `measurement`. **SteerRatio does
not enter the metric at all**, so the 1.288x deflation below does NOT apply and the table is void as a correction.
The over-delivery stands at +0.334 m/s² on matched frames.

**A real loose end that survives, and anyone sizing a dose must quote which stratum they mean:** a second agent, on a
different SR-free instrument (yaw/v ÷ desiredCurvature, tight curves above 0.02 /m), reads achieved-over-asked at
**1.03–1.13x** on r36/r37/r38 where this matched-cohort metric reads **1.278**. Both are SR-free and both say
over-delivery, so the DIRECTION is not in doubt; the MAGNITUDE differs by about a factor of two between strata.

The original reasoning is kept below as a record of the question, which was the right one to ask.

---

**(Superseded reasoning.)** If "+0.334 on matched frames" had been computed from openpilot's own `measurement`
(i.e. `VM.calc_curvature(...)·v²` with SR 12.5), it would have sat in a frame inflated 1.288x. Converting
to true lateral accel, `true = (setpoint + 0.334)/1.288 − setpoint`:

| tight-curve setpoint | apparent | **true** over-delivery |
|---|---|---|
| 0.60 m/s² | +0.334 | +0.125 |
| 0.80 | +0.334 | +0.080 |
| 1.00 | +0.334 | +0.036 |
| **1.16** | +0.334 | **0.000** |
| 1.50 | +0.334 | −0.076 |
| 2.00 | +0.334 | −0.188 |

**At a tight-curve setpoint of ~1.16 m/s², +0.334 apparent over-delivery is exactly what a
perfectly-tracking car looks like through SR 12.5.** Above that setpoint the car is genuinely
*under*-delivering.

**What settled it:** (b) — the instrument. It is `livePose` yaw-rate × v with roll removed, i.e. SR-independent,
so the deflation never applied. (a), the median tight-curve setpoint, is therefore moot for this question.
**The +0.334 IS usable for sizing**, subject only to the stratum caveat recorded in the resolution above.

### 4c. SteerKP 0.6 → 0.8 — I agree on direction; the size is smaller than it looks

**Agreed:** with `p = −0.300` the proportional term is already pulling against the turn, so +33 % on it
acts to **reduce** over-delivery. It remains the best free lever I found.

**But the naive "+33 % of −0.300 = −0.100" overstates it. EVIDENCE**, `latcontrol_torque.py`:

```python
error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))
...
self.p = self.k_p * float(error)      # in PIDController, on error_with_lsf
```
so `p = kp·error_with_lsf = kp·error + low_speed_factor·error`. **The low-speed term is
kp-independent**, so raising kp by 0.2 adds only `0.2 · error` (raw error), not 33 % of `p`.
Back-solving `error` from `p = −0.300 = error·(0.6 + lsf)` with
`lsf = (interp(v, [0,10,20,30], [12,10.5,8,5]) / v)²`:

| v (m/s) | lsf | implied error | Δp at kp 0.8 | share of +0.334 | Δp at kp 0.9 (clamp) | share |
|---|---|---|---|---|---|---|
| 10 | 1.103 | −0.176 | −0.035 | 11 % | −0.053 | 16 % |
| 15 | 0.380 | −0.306 | −0.061 | 18 % | −0.092 | 27 % |
| 20 | 0.160 | −0.395 | −0.079 | 24 % | −0.118 | 35 % |
| 25 | 0.068 | −0.449 | −0.090 | 27 % | −0.135 | 40 % |
| 30 | 0.028 | −0.478 | −0.096 | 29 % | −0.143 | 43 % |

⇒ **SteerKP 0.8 buys roughly 11–29 % of the +0.334, rising with speed; the entire remaining range to
the 0.90 clamp buys 16–43 %.** It is a real, free, correctly-signed trim — and it is **not** enough to
cancel the over-delivery on its own.

⚠ **A caveat on those percentages, corrected after §4b resolved.** An earlier revision justified the
comparison as "like-for-like, both in the SR-12.5 frame". That justification is void now that the
+0.334 is known to be SR-free road-side lateral accel (`livePose` yaw·v, roll removed): **Δp is a change
in openpilot's *commanded* lateral accel, while +0.334 is *delivered* road lateral accel** — opposite
sides of the plant. The percentages are exact only if the plant's local gain is 1.0 m/s² delivered per
m/s² commanded. Since the car is over-delivering, the local gain is **above** 1, so removing 0.06–0.10
of command removes **at least** that much delivered accel. ⇒ **Read 11–29 % as a lower bound on the
effect, not a point estimate** — and note it is a share of the 1.278 stratum; against the other SR-free
stratum (1.03–1.13x) the same change covers a much larger fraction of a much smaller excess.

Two safety notes on raising kp: it is a feedback term, so it is self-limiting (as the over-turn shrinks
the increment shrinks with it); and +33 % of P does **not** approach the 7 Hz ring, because openpilot's
authority is already dead above ~1.5–2 Hz from the `STEER_DELTA` slew ceiling and the 1.2 Hz jerk filter
(§1, boundary).

### 4d. Can params-only reach this at all? — Partly, and only one half of it

**Plainly: no, params cannot substitute for the integrator.** There is no `SteerKI`, so params cannot
add integral action, so **params cannot touch the low-demand droop that V283's firmware Ki exists to
fix.** That half is reachable only by the KI fork or by firmware.

**But the objection "net command is ~0 in a steady curve so params can do nothing" does not hold.** The
net is small because the components cancel (f +0.800 against p −0.300 and i −0.392), not because the
components are small. `SteerKP` scales `p` alone and moves the net; `SteerLatAccel` scales f, p, i, d
*and* the PID limits together (§1a.2) and so scales the net roughly proportionally. Both are live.
So params **can** trim V283's over-delivery — by ~11–29 % of it via SteerKP — they just cannot create
the integral term.

**Is it worth a drive?** Yes, but not that drive. A param change needs no flash, and the instrument
already exists — the f/p/i decomposition the orchestrator just computed is exactly the readout. But the
operator has explicitly said he does not want to confound SteerRatio with the Ki evaluation, and the
same argument applies with equal force to SteerKP. **Do not bundle SteerKP 0.8 into a drive whose
purpose is to score V283's Ki.** Change it on its own, on a fixed image, and read the same decomposition.

### 4e. 🛑 The KI fork must NOT be flown on top of V283

`i = −0.392` means openpilot's integrator is already winding **against** the turn — it is fighting the
EPS's internal integrator. Raising `HONDA_ACCORD_TORQUE_KI` on a V283 image puts **two integrators in
cascade on the same error signal**, with no separation of timescales and with the inner one invisible to
the outer one's anti-windup. That is a recipe for a slow limit cycle, and it would be uninterpretable
besides — a null could mean either integrator.

⇒ 🛑 **HARD CONSTRAINT. The openpilot-KI patch belongs on a Ki-0 image, as a SUBSTITUTE for firmware Ki,
NEVER on top of it. The two routes are mutually exclusive experiments.**

### 4f. Revised order

1. **Nothing to SteerRatio** while V283 is in the car. 12.5 is currently cancelling ~29 % of demand and
   is holding the oversteer down.
2. **§4b is settled: the +0.334 is real and SR-free** — no deflation applies. The one thing still open
   is the **stratum**: the matched-cohort metric reads 1.278 while yaw/v ÷ `desiredCurvature` on tight
   curves reads 1.03–1.13x. Both SR-free, both over-delivery; **state which stratum any dose is sized
   against.**
3. **`SteerKP` 0.6 → 0.8** is the one free, correctly-signed lever — ≥11–29 % of the 1.278-stratum
   excess (a lower bound, see §4c). Fly it alone, not inside a Ki-scoring drive.
4. **The KI fork (0.15 → 0.35) is still the right structural move for the droop** — but on a Ki-0
   firmware image, never on V283, per the hard constraint in §4e.

### 4g. The disengage contrast — the strongest argument for the KI-up-a-loop route

Put side by side, these are the two halves of the same claim, from two independent methods:

| | EPS integrator (firmware Ki 50, V283) | openpilot integrator (`LatControlTorque`) |
|---|---|---|
| **State at lateral disengage** | **Does not clear.** 139–383 tap counts still delivered **0.5–1.0 s after `STEER_REQUEST` drops**; both integrator-free builds are at zero within 0.5 s. *(EVIDENCE — independent firmware trace, 2026-09-04, relayed by the orchestrator.)* | **Zeroed on the same frame.** `if not active: output_torque = 0.0 … self.pid.reset()`. *(EVIDENCE — `selfdrive/controls/lib/latcontrol_torque.py`, the `not active` branch.)* |
| **Driver-touch behaviour** | No hands-off gate on the accumulator found in the firmware. | `freeze_integrator` on `CS.steeringPressed`; `self.pid.i *= 0.8` on release. |
| **Observability** | Invisible without a probe — the accumulator is ECU-internal state. | Published every frame as `controlsState.lateralControlState.torqueState.i`. |

**This is the operator's structural objection, confirmed from both sides.** The residual torque after
disengage is not a tuning artefact of the dose — it is what an integrator with no reset path does, and
the same function moved one loop up has an explicit reset path, an explicit driver-touch freeze, and a
telemetry channel. **It is the strongest argument in this document for the KI route**, and it is
independent of whether the KI dose itself turns out to be the right size.

⚠ It does **not** cancel §4h. Both things are true: openpilot's integrator resets cleanly, *and* it can
still wind to full authority while engaged because it cannot see the EPS saturating.

### 4h. Headline risk of the KI route, restated as asked

**Moving the integrator up a loop makes the oversteer observable and resettable. It does not make it go
away.** `steer_limited_by_safety = abs(CC.actuators.torque − CO.actuatorsOutput.torque) > 1e-2` compares
openpilot's request against the **carcontroller's own** rate limit (`STEER_DELTA = 3` counts/frame) —
it can see nothing about the EPS's internal assist-map clamp. With the EPS stalled at 0.36 of the
request, openpilot registers no limiting, does not set `freeze_integrator`, and winds toward the
`±latAccelFactor` bound, which is **full ±1.0 normalized steering torque from the integrator alone**.
Combined with the ~8x plant-gain variation along the demand axis, one KI cannot be correct at both ends
of that curve, and the wind-up-then-release transition at the knee is the same oversteer signature the
firmware Ki produced. What is genuinely gained is that the state resets at disengage (`self.pid.reset()`
in the `not active` branch), freezes on `steeringPressed`, and is published in `controlsState` where it
can be scored — not that the failure mode is eliminated.

---

## 5. Straight-road understeer — MEASURED, 2026-09-04 (subagent `opfork2`)

Answering the operator's V282 line: *"understeer on straight roads (I think this should be a StarPilot
change, where are we with this?)"*

**Scripts (new, this session):**
`rlog-tools/studies/osc-highangle/straight_understeer_v282.py` (A–E) ·
`…/straight_understeer_sr.py` (F–H) · `…/straight_understeer_road.py` (I–L).
Outputs in `rlog-tools/studies/osc-highangle/_scratch/straight_understeer_*.txt`.

**Arms.** r34 = V280 rev 2, SteerRatio 16.1, EPS Ki 0 (the SR control) · r35 = V281 rev 3, SR 12.5,
EPS Ki 0 — **this is V282 for every purpose here, since V282 adds only the read-only r24 comparator
cave** · r36/r37/r38 = V283, SR 12.5, EPS Ki 50.
**Straight mask:** lateral engaged, not `steeringPressed`, calibrated, v > 15 m/s,
|`desiredCurvature`| < 0.0020 /m (radius > 500 m). 170–358 s per route.

### 5a. 🛑 EVIDENCE — the truthful steering ratio near centre is ~16.5. SteerRatio 12.5 is a 1.30–1.33x measurement inflation.

**Method.** Invert openpilot's own vehicle model against a measurement that contains no steering ratio.
`latcontrol_torque.py:232` computes `measured_curvature = -VM.calc_curvature(radians(ang - aoff), v, roll)`
(the leading minus verified in source), and `vehicle_model.py:77` is
`calc_curvature = curvature_factor(u)*sa/sR + roll_compensation(roll, u)`. Therefore

```
sR_true = curvature_factor(v) * sa  /  ( -yaw_cal/v  -  roll_compensation(roll, v) )
```

with `yaw_cal` the calibration-rotated `livePose.angularVelocityDevice.z` — **locationd does not use the
steering ratio, so the right-hand side is SR-free.** `stiffnessFactor` is pinned to 1.0 by the operator's
`ForceAutoTuneOff`, so the slip factor is a constant read from `carParams`. Frames: engaged, not pressed,
calibrated, v > 15 m/s, |sa| > 1.5 deg, quasi-static (|`steeringRateDeg`| < 10 deg/s).

| route | SteerRatio param | **sR_true** (TLS through origin) | sR_true (affine refit) | \|sa\| < 5 deg | 5–15 deg | n |
|---|---|---|---|---|---|---|
| **r34** (the control) | **16.1** | **16.83** | 16.56 | 16.93 | 16.71 | 77 s |
| r35 (= V282) | 12.5 | **16.60** | 16.52 | 16.41 | 16.54 | 126 s |
| r36 | 12.5 | 16.43 | 15.62 | 16.41 | 16.44 | 77 s |
| r37 | 12.5 | 14.93 | 15.02 | 15.48 | 14.80 | 35 s ⚠ least data |
| r38 | 12.5 | 16.76 | 16.15 | 16.47 | 16.97 | 73 s |

**Why this is trustworthy:** (i) **r34 is a built-in control** — its param is 16.1 and the instrument
returns 16.8/16.6, a bias of 1.03–1.05, i.e. the method reproduces a known-good ratio; (ii) the affine
refit (slope + intercept) agrees within 0.3–0.8, so a mis-learned `angleOffsetDeg` cannot be driving it
(the fitted intercepts are ~1e-4 /m); (iii) the |sa| < 5 deg and 5–15 deg strata agree, so it is not a
large-angle rack-ratio artefact; (iv) it replicates across **two firmware builds and four routes**.

⇒ **`SteerRatio = 12.5` makes openpilot over-read its own curvature by 16.5/12.5 = 1.32x.**

### 5b. EVIDENCE — the loop is AT its own equilibrium on straights, and the integrator is what puts it there

Section G, the signed PID decomposition on straight frames, expressed in the feedforward's own sign
(`med(x*sign(f))`; positive = adds to `f`, negative = cancels it):

| route | \|f\| | p*sgn(f) | **i*sgn(f)** | d*sgn(f) | out*sgn(f) | out/f | sec |
|---|---|---|---|---|---|---|---|
| r34 | 0.216 | −0.053 | **−0.166** | 0.000 | −0.011 | −0.048 | 152 |
| **r35 (=V282)** | **0.292** | −0.040 | **−0.251** | 0.000 | **−0.009** | **−0.029** | 183 |
| r36 | 0.338 | −0.012 | −0.323 | 0.000 | −0.004 | −0.012 | 327 |
| r38 | 0.326 | −0.018 | −0.292 | 0.000 | −0.004 | −0.011 | 345 |

**The integrator cancels 86 % of the feedforward on r35 (96 % on r36/r38), and the net output is ~0.**
Median *signed* `error` on straights is +0.017 (r35), +0.022 (r38) — **openpilot believes it is
tracking.** That is exactly what an inflated measurement forces: `error = setpoint − measurement`, the
measurement reads 1.32x high, so the integrator winds against the feedforward until the loop settles at
`measurement = setpoint`, i.e. at **road accel = asked / 1.32 = 0.76 of asked**.

⇒ **"openpilot barely commands in steady state" (measured earlier this session: f +0.800, p −0.300,
i −0.392, net +0.108) is not an independent fact. It is the SIGNATURE of the SteerRatio bias.**

### 5c. EVIDENCE — what actually reaches the wire during a persistent lateral error

Section E/L'. Runs >= 1.0 s of one-signed |`error`| > 0.10 m/s2 inside the straight mask
(`pid_log.error` is `error_with_lsf`, ~1.11x the raw error at 25 m/s):

| route | runs | total | % of straight time | median run | median \|error\| | median \|actuatorsOutput.torque\| | median \|0xE4 cmd\| | demand idx |
|---|---|---|---|---|---|---|---|---|
| r34 | 28 | 53.1 s | 31 % | 1.58 s | 0.181 | **0.025** | 111 | 6 |
| **r35 (=V282)** | 27 | **95.5 s** | **49 %** | **2.12 s** | 0.252 | **0.025** | 106 | 6 |
| r36 | 45 | 95.6 s | 28 % | 1.65 s | 0.224 | 0.025 | 103 | 6 |
| r38 | 39 | 80.2 s | 22 % | 1.81 s | 0.227 | 0.022 | 91 | 5 |

**Half of straight-road engaged time on V282-equivalent firmware is spent inside a 2-second one-signed
lateral error of 0.25 m/s2, during which openpilot commits 2.5 % of its steering authority.**

⚠ **Defect found in a shared module — reported, not fixed.** `backcalc_laf_friction.grid()`'s `cmd`
channel is **diluted**: 0xE4 arrives in the rlog at **199.5 Hz** as two interleaved streams, and the
`STEER_REQUEST = 0` copy carries 0 in 56–58 % of samples (`frac(cmd==0 | req==1) = 0.004`). A `hold()`
over the unfiltered stream therefore reports a median |cmd| of 0–12 counts where the true
request-gated median is 66–104. Anything quoting `g["cmd"]` (e.g. `oversteer_v283_gain.py` section B)
is biased low. **Gate on `e4_req > 0.5` before gridding.** The `V.Route` idx path is unaffected.

### 5d. EVIDENCE — the EPS droop is real at this operating point, but it is NOT the binding constraint

Section D — measured column rate / the inner loop's own map reference, command held >= 0.4 s, hands light:

| route | idx 1–6 | idx 6–12 | idx 12–20 | idx 20–40 |
|---|---|---|---|---|
| r34 | 0.30 (22 s) | 0.17 (21 s) | 0.25 (6 s) | 0.52 (4 s) |
| **r35 (=V282)** | **0.30** (48 s) | **0.15** (27 s) | 0.08 (12 s) | 0.15 (7 s) |
| r36/r37/r38 (Ki 50) | 0.26–0.29 | 0.37–0.40 | 0.53–0.56 | 0.66 |

The inner rate loop delivers **15–30 % of its own reference at the straight-road demand indices** on
V282-class firmware — the droop is unambiguous, and EPS Ki 50 more than doubles it at idx 6–12
(0.15 -> 0.37–0.40). **But it sits INSIDE the outer loop, at demand index 4–6 of a 0–240 range, while
openpilot is committing 2.5 % of its authority.** A droop cannot be what defeats a controller that is
not pushing. It costs *bandwidth* (a slower correction), not the *equilibrium*.

### 5e. Road-side corroboration — consistent, and honestly underpowered

Sections I/J: `lat_torqued` (= v*yaw_cal − g*sin roll, SR-free) against `desiredLateralAccel` (also
SR-free), delay-matched, on straights after a 0.2 Hz low-pass:

| route | predicted road/asked | TLS | OLS bracket |
|---|---|---|---|
| r34 | 0.97 | **0.94** | 0.51 – 1.84 |
| r35 (=V282) | 0.75 | **0.81** | 0.51 – 1.52 |
| r36/r38 (Ki 50) | 0.76 | 2.98 / 1.33 | wide |

r34 and r35 land where 5a predicts. The OLS brackets are wide because straight-road yaw is near the
noise floor, and r36/r38 are confounded by the EPS integrator (the over-delivery already on record).
**BELIEF, not EVIDENCE, on its own — it corroborates 5a, it does not carry it.**

### 5f. 🛑 THE TRAP: never set `SteerRatio` to 16.33

**EVIDENCE**, `selfdrive/controls/controlsd.py:470-478`:

```python
custom_accord_ratio = getattr(self.starpilot_toggles, "steerRatio", self.CP.steerRatio)
accord_ratio_is_explicit = getattr(self.starpilot_toggles, "use_custom_steerRatio", False) and \
  abs(custom_accord_ratio - self.CP.steerRatio) > 0.01
...
elif self.CP.carFingerprint == HONDA_CAR.HONDA_ACCORD and not accord_ratio_is_explicit:
  sr *= get_honda_accord_steer_ratio_scale(CS.vEgo)     # returns HONDA_ACCORD_STEER_RATIO_SCALE = 14.0/16.33
```

Setting the param within **0.01 of `CP.steerRatio = 16.33`** flips `accord_ratio_is_explicit` to False
and StarPilot silently multiplies by 0.857 — **effective ratio 14.0**, i.e. still a 1.18x inflation.
**16.1 and 16.5 are both safe; 16.33 is the one value to avoid.** Clamp is `0.5…1.5 x 16.33` =
8.17…24.50 (`starpilot_variables.py:760`), so anything in that band is reachable.

### 5g. The ordered change list

| # | change | fork? | expected effect and sign | how we measure it |
|---|---|---|---|---|
| **1** | **`SteerRatio` 12.5 -> 16.1** (Settings -> Lateral) | **FREE** | removes a 1.32x measurement inflation ⇒ **+28.8 % of commanded lateral accel at the loop's own equilibrium**; sign = MORE turn. Largest single lever found. | rerun `straight_understeer_sr.py` F/G: bias 1.33 -> ~1.03, and `i*sgn(f)` should shrink from −0.25 toward 0 |
| **2** | **`SteerKP` 0.6 -> 0.8** (`KP = 0.6` verified at `latcontrol_torque.py:28`, clamp 0.30–0.90) | **FREE** | restores the `HONDA_ACCORD_TORQUE_KP = 0.8` that `controlsd.py:444` overwrites every frame. Adds `0.2 * error_raw` ~ **+0.045 m/s2** during the measured persistent-error runs — roughly **doubles** the present net output of 0.025 | `straight_understeer_road.py` L: \|actuatorsOutput.torque\| in-run; and E's run count / total seconds |
| **3** | `ForceAutoTune` | **FREE** | **already OFF.** Newest backup (`toggle-backup_V281R3.decoded.json`, mtime 2026-09-03 00:02) has `ForceAutoTune False`, `ForceAutoTuneOff True`. **No action.** The "it is ON" premise came from the OLDEST backup (2026-09-02 18:50) | n/a |
| **4** | `SteerFriction` 0.03 | **FREE** | leave. Whole authority is +-friction * latAccelFactor = **+-0.063 m/s2**; the back-calc's 0.025 moves it by 0.01 — below everything else here | n/a |
| **4b** | `SteerLatAccel` 2.11 | **FREE** | ⚠ **CONFLICT, do not bundle.** `output_torque = output_lataccel / latAccelFactor` (`interfaces.py`), so 2.11 vs the stock 1.689 costs **~20 % of delivered torque** — lowering it is a correctly-signed understeer lever. But the 2026-09-02 back-calc prescribed moving it **UP to 2.53** to cut loop gain for the 3.9 Hz oscillation. **Both cannot be right; resolve after 1 and 2 are measured.** | the same L/E readout, on its own drive |
| **5** | **`HONDA_ACCORD_TORQUE_KI` 0.15 -> 0.35** (`latcontrol_vehicle_tunes.py:78`) | **FORKED** | `common/pid.py:53` is `i += k_i * 0.01 * error` at 100 Hz = **0.15 * error per second**. Over the measured median **2.1 s** run at error 0.25 that is **0.079 m/s2** now vs **0.184** at KI 0.35. This is the only lever that closes the DC error *inside* a correction | `controlsState.lateralControlState.torqueState.i` on the wire; E's run count and total seconds |

**Order matters:** 1 changes the error that 2 multiplies, so **fly them separately**, one param per
drive, each read out with the same L/E decomposition.

### 5h. The KI-fork constraint — CONFIRMED, and now with a number

The hard constraint holds and 5d strengthens it: EPS Ki 50 raises the inner loop's DC gain **at exactly
the straight-road demand index** (idx 6–12: 0.15 -> 0.37–0.40, a 2.5x change), so an openpilot KI patch
flown on V283 would put two integrators on the same error at the same operating point with **no
separation of timescales** and with the inner one invisible to the outer one's anti-windup. Add the
disengage asymmetry already on record (firmware Ki leaves 139–383 tap counts 0.5–1.0 s after
`STEER_REQUEST` drops; `latcontrol_torque`'s `not active` branch calls `self.pid.reset()` on the same
frame).

⇒ 🛑 **V282 (Ki 0) + the KI fork is the legal pairing. V283 + the KI fork is not.** Unchanged from §4e.

### 5i. Verdict on the operator's question

**Yes — straight-road understeer is an openpilot-side problem, and it is a PARAM, not a fork.**
The dominant cause is `SteerRatio = 12.5`: it inflates openpilot's own curvature measurement by 1.32x,
which drives the integrator to cancel 86 % of the feedforward, which is why the car commits 2.5 % of its
steering authority through half of every straight-road minute. The EPS low-demand droop is real
(15–30 % of reference at idx 1–12) but cannot be the binding constraint at a demand index of 4–6.

**One caveat, stated plainly.** §4a of this document argued *against* raising `SteerRatio` — correctly,
**for V283**, where the EPS integrator is over-delivering in curves and SR 12.5 is holding it down.
**V282 is Ki-0 and under-delivers** (r35's curve-stratum road/asked TLS 0.66–0.68 at |des| > 0.5), so on
V282 the 28.8 % restoration lands well short of 1.0 and the §4a objection does not apply. **The
recommendation is conditional on the flown image being Ki-0.**
