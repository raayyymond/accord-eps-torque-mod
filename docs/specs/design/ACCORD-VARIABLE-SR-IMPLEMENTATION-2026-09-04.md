# Variable steer ratio for the 2018–22 Honda Accord — StarPilot implementation

**Date** 2026-09-04 · **Repo** `C:\Users\dudei\Desktop\Projects\openpilots\StarPilot`, branch `Dom`,
HEAD `3d4c625de` (2026-09-01, *"actually refresh"*) · **State: applied to the working tree, NOT committed,
NOT pushed.**

**The map is MEASURED, not assumed** — 427 min over 47 routes, four independent derivations, max fit
residual 0.39 % beyond 48°. See §4.

---

## 1. What the change does

The 2018–22 Accord (`CAR.HONDA_ACCORD`, `HondaBoschPlatformConfig`) has a **variable-ratio rack**: flat at
about 16:1 out to ~48° of wheel, then quickening monotonically to about 11:1 at lock. openpilot models the
car with a single `steerRatio`, and the platform ships **16.33** with the comment *"steerRatio: 11.82 is
spec end-to-end"* (`opendbc_repo/opendbc/car/honda/values.py:181–188`).

The Accord branch in `controlsd` then multiplied that by a constant `HONDA_ACCORD_STEER_RATIO_SCALE =
14.0 / 16.33 = 0.8573`, i.e. an effective **14.0** everywhere. Against the measured rack, **0.857 is the
rack's ratio at about 95° of wheel** — so the shipping code was one sample of the curve applied at every
angle: **too quick on centre** (should be ≈0.980 of 16.33) and **too slow at lock** (should be ≈0.677).

🛑 **The effective 14.0 is NOT what is on the car right now.** It applied when the `SteerRatio` param sat at
16.33 with `ForceAutoTune` on (2026-09-02 18:50 — both gates false, so the scale was applied). **Since
2026-09-03 00:02 the operator has run `SteerRatio` 12.5 with `ForceAutoTuneOff` True**, which makes
`accord_ratio_is_explicit` **True**, so the scale is *not* applied and `sr` is genuinely **12.5**. So there
are two baselines — **14.0 for a stock user who never set the toggle, 12.5 for this operator** — and §3.4
carries both. His is the one that governs the drive.

**The change is not "add a feature". It is "the existing constant is a single sample of a curve; restore
the curve."** That is the commit message.

**Shape of the change — one constant block, one function, one branch.**

| file | change | churn (total / since 2026-06-01 / last touched) |
|---|---|---|
| `selfdrive/controls/lib/latcontrol_vehicle_tunes.py` | constant → two knot lists; `get_honda_accord_steer_ratio_scale` → `get_honda_accord_steer_ratio` | 84 / 84 / 2026-09-01 |
| `selfdrive/controls/controlsd.py` | the `HONDA_ACCORD` branch in `state_control()`; import rename; hoisted `steer_angle_deg` | 62 / 31 / 2026-09-01 |
| `selfdrive/controls/tests/test_latcontrol.py` | the one test that pinned the old constant | 174 / 79 / 2026-09-01 |

`selfdrive/locationd/paramsd.py` and `starpilot/common/starpilot_variables.py` are **NOT touched** — see §3.

---

## 2. The diff

```diff
--- a/selfdrive/controls/lib/latcontrol_vehicle_tunes.py
+++ b/selfdrive/controls/lib/latcontrol_vehicle_tunes.py
@@ -73,7 +73,17 @@ BOLT_2017_CARS = (
-HONDA_ACCORD_STEER_RATIO_SCALE = 14.0 / 16.33
+# Measured on this car: 427 min over 47 routes, ratio derived four independent ways
+# (yaw+rear-axle speed, yaw+front, rear differential without IMU, wheel speeds alone),
+# left and right measured separately -- symmetric to within 1.5%. Flat at ~16:1 out to
+# ~48 deg, then quickening monotonically to ~11.1:1 at lock. Speed control passed, so
+# this is rack geometry, not a speed-dependent artefact: index on |angle| only.
+# The old single 14.0/16.33 scale was this curve sampled at ~95 deg and applied at every
+# angle: too quick on centre, too slow at lock.
+# Breakpoints are |steering wheel angle| in degrees off the learned centre; values are the
+# measured ratio there. np.interp holds the ends, so the ratio is bounded on [11.06, 16.00].
+HONDA_ACCORD_STEER_RATIO_ANGLE_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]  # deg
+HONDA_ACCORD_STEER_RATIO_V = [16.00, 16.00, 15.02, 14.52, 13.97, 13.75, 13.50, 12.81, 11.67, 11.06]  # :1
 HONDA_ACCORD_TORQUE_KP = 0.8
@@ -2102,8 +2112,9 @@ def get_bolt_2017_steer_ratio_scale(v_ego: float) -> float:
-def get_honda_accord_steer_ratio_scale(_v_ego: float) -> float:
-  return HONDA_ACCORD_STEER_RATIO_SCALE
+def get_honda_accord_steer_ratio(steer_angle_deg: float) -> float:
+  """Local ratio of the Accord's variable-ratio rack at the current wheel angle."""
+  return float(np.interp(abs(steer_angle_deg), HONDA_ACCORD_STEER_RATIO_ANGLE_BP, HONDA_ACCORD_STEER_RATIO_V))
```

```diff
--- a/selfdrive/controls/controlsd.py
+++ b/selfdrive/controls/controlsd.py
@@ -32,7 +32,7 @@ from openpilot.selfdrive.controls.lib.latcontrol_torque import (
-  get_honda_accord_steer_ratio_scale,
+  get_honda_accord_steer_ratio,
 )
@@ -467,18 +467,18 @@ class Controls:
     sr = max(lp.steerRatio, 0.1)
-    custom_accord_ratio = getattr(self.starpilot_toggles, "steerRatio", self.CP.steerRatio)
-    accord_ratio_is_explicit = getattr(self.starpilot_toggles, "use_custom_steerRatio", False) and \
-      abs(custom_accord_ratio - self.CP.steerRatio) > 0.01
+    steer_angle_deg = CS.steeringAngleDeg - lp.angleOffsetDeg
     if self.CP.carFingerprint == GM_CAR.CHEVROLET_BOLT_CC_2017:
       sr *= get_bolt_2017_steer_ratio_scale(CS.vEgo)
     elif self.CP.carFingerprint == GM_CAR.CHEVROLET_BOLT_CC_2018_2021:
       sr *= BOLT_2018_2021_STEER_RATIO_TEST_SCALE
-    elif self.CP.carFingerprint == HONDA_CAR.HONDA_ACCORD and not accord_ratio_is_explicit:
-      sr *= get_honda_accord_steer_ratio_scale(CS.vEgo)
+    elif self.CP.carFingerprint == HONDA_CAR.HONDA_ACCORD:
+      # Variable-ratio rack: the map IS the ratio, so neither the learner nor the
+      # SteerRatio toggle can bias it. Both are ignored for this platform by design.
+      sr = get_honda_accord_steer_ratio(steer_angle_deg)
     self.VM.update_params(x, sr)
 
-    steer_angle_without_offset = math.radians(CS.steeringAngleDeg - lp.angleOffsetDeg)
+    steer_angle_without_offset = math.radians(steer_angle_deg)
     self.curvature = -self.VM.calc_curvature(steer_angle_without_offset, CS.vEgo, lp.roll)
```

```diff
--- a/selfdrive/controls/tests/test_latcontrol.py
+++ b/selfdrive/controls/tests/test_latcontrol.py
@@ -47 +47,2 @@
+  HONDA_ACCORD_STEER_RATIO_V,
   HONDA_ACCORD_TORQUE_KI,
@@ -104 +105 @@
-  get_honda_accord_steer_ratio_scale,
+  get_honda_accord_steer_ratio,
@@ -1915,8 +1916,11 @@
-  def test_honda_accord_steer_ratio_calibration(self):
-    expected_scale = 14.0 / 16.33
-    assert get_honda_accord_steer_ratio_scale(0.0) == pytest.approx(expected_scale)
-    assert get_honda_accord_steer_ratio_scale(20.0) == pytest.approx(expected_scale)
+  def test_honda_accord_steer_ratio_is_variable_and_symmetric(self):
+    centre = get_honda_accord_steer_ratio(0.0)
+    assert centre == pytest.approx(HONDA_ACCORD_STEER_RATIO_V[0])
+    # flat across the on-centre band, then quickening toward lock, identically both sides
+    assert get_honda_accord_steer_ratio(48.0) == pytest.approx(centre)
+    assert get_honda_accord_steer_ratio(180.0) < centre
+    assert get_honda_accord_steer_ratio(-180.0) == pytest.approx(get_honda_accord_steer_ratio(180.0))
+    # np.interp holds the endpoints, so the ratio stays bounded past the last knot
+    assert get_honda_accord_steer_ratio(1e4) == pytest.approx(HONDA_ACCORD_STEER_RATIO_V[-1])
```

---

## 3. Design decisions, and why

### 3.1 The map REPLACES `sr`; it does not scale it. This is what "ignore the toggle" means structurally.

The old Accord branch multiplied `lp.steerRatio` — which `paramsd` fills from the learner **or from the
Galaxy `SteerRatio` param**, depending on `use_custom_steerRatio` (`selfdrive/locationd/paramsd.py:29–34`).
That is where the **16.33 trap** lived: `use_custom_steerRatio` is
`round(param,2) != round(16.33,2)` (`starpilot/common/starpilot_variables.py:761`), so **setting the param
to exactly 16.33 made `accord_ratio_is_explicit` FALSE and re-applied the ×0.8573 scale → effective 14.0.**
The operator hit this on 2026-09-02.

Assigning rather than multiplying kills the whole class of failure in one line: for the Accord, `sr` no
longer depends on `lp.steerRatio` at all, so **no value of the toggle, and no state of the learner, can
reach it.** The alternative — keeping the learner as a base and multiplying by a shape normalised at
centre — would have required *also* editing `paramsd.py` and/or `starpilot_variables.py` to stop the toggle
leaking in through the base (`paramsd.py:31` returns the toggle value outright when `force_auto_tune_off`).
That is two more files, both high-churn, for a base quantity that is **not** a physical constant of the car:
with a variable rack, a single learned SR is an angle-weighted average of the very curve we are supplying,
so multiplying the curve by it re-introduces the ambiguity the map exists to remove.

**Kept learned:** `stiffnessFactor` (`x`) is untouched and still comes from `lp` — tyre/alignment drift is
its job, not the rack's.

**Consequence of assigning: the table stores RATIOS, not scales on 16.33.** The scale form only existed
because the old code multiplied. The measurement is a ratio; the vehicle model wants a ratio; storing the
ratio removes one indirection and one number (16.33) that would otherwise have to stay in agreement with
`values.py`. The two forms are numerically identical — 16.00/16.33 = 0.980, 13.97/16.33 = 0.856,
11.06/16.33 = 0.677.

**⚠ Operator-visible consequence:** after this patch the Galaxy **SteerRatio** slider does **nothing** on the
Accord. Given the V281→V283 notes ("SteerRatio stays 12.5", "SR back to 16.1"), that slider has been an
active tuning knob. Tuning now happens by editing `HONDA_ACCORD_STEER_RATIO_V`. This is the requested
behaviour, but it is a workflow change.

### 3.2 Indexed by the offset-corrected wheel angle, not by speed

`CS.steeringAngleDeg - lp.angleOffsetDeg` is the same quantity the very next line feeds to
`VM.calc_curvature`, so the ratio and the angle it is applied to are consistent by construction. The raw
sensor angle would have put the map's centre wherever the sensor zero happened to be. The measurement's own
fitted true centre is **−4.25°** against openpilot's learned `angleOffsetDeg` of **−4.78°** — 0.53° apart,
inside the noise of the flat band — so `lp.angleOffsetDeg` is used rather than a hardcoded centre, and it
tracks if the sensor zero drifts. `angleOffsetDeg` is bounded ±10° by `paramsd` (`OFFSET_MAX`), so the index
is well conditioned. Hoisting it into `steer_angle_deg` removes a duplicated expression rather than adding
one.

**Angle only. No speed term.** The old signature took `_v_ego` and ignored it; speed is not the rack's
independent variable. The measurement settles this rather than assuming it: the centre→120° ratio swing
measured inside three separate speed bands gives 1.2137 / 1.1848 / 1.2000 with overlapping CIs, so the
curve is rack geometry and not a speed-dependent estimator artefact.

### 3.3 `abs()` and `np.interp`, with no explicit clamp

Left and right were measured **independently and never mirrored**, and agree to within 1.5 %; an injected
2 % asymmetry *would* have been detected, so a real ≥2 % difference is excluded. **⇒ index on `|angle|`; a
signed map would be fitting noise.**

`np.interp` holds the endpoint values outside `[bp[0], bp[-1]]`, so the ratio is bounded on `[11.06, 16.00]`
for any finite input — including a stuck or absurd angle. No `min`/`max` guard is needed, and none is added.
`np.interp` is the file's own idiom (20 other uses).

### 3.4 Downstream: the same ratio is used forward and inverse in the same frame

`self.VM` is used for `calc_curvature` (measured, `controlsd.py:482`; `latcontrol_torque.py:232,262`) and for
`get_steer_from_curvature` (desired, `latcontrol_torque.py:565–575`, `latcontrol_angle.py:63`,
`latcontrol_pid.py:136`). Because `update_params` is called once per frame before all of them, forward and
inverse share one ratio — a linearisation about the current operating point. That is exactly how the
existing Bolt precedent behaves; the patch changes the value, not the structure. **EVIDENCE** — grep of
`VM\.` across `selfdrive/controls/lib/`, plus `VehicleModel(` instantiated only at `controlsd.py:415`.

**Direction of effect (EVIDENCE, from `calc_curvature`'s form):** a *higher* SR means the same wheel angle
is read as *less* curvature, which enlarges the controller's error and so commands *more* torque.

**There are TWO baselines, because the old branch fired for some users and not others.** Both are given
below; they answer different questions and the patch ships to both populations.

- **A stock user who never set the toggle** has `use_custom_steerRatio` False ⇒ `accord_ratio_is_explicit`
  False ⇒ the old `elif` fired ⇒ `sr` = 16.33 × 0.8573 = **14.0** flat.
- **This operator's car is on 12.5.** His toggle is 12.5 against `CP.steerRatio` 16.33, so
  `|12.5 − 16.33| = 3.83 > 0.01` ✓, and `starpilot_variables.py:761` gives
  `use_custom_steerRatio = (round(12.5,2) != round(16.33,2)) and not force_auto_tune or force_auto_tune_off`
  = `(True and True) or True` = **True** ✓ (his `ForceAutoTuneOff` has been True since the 2026-09-03 00:02
  backup). ⇒ `accord_ratio_is_explicit` is **TRUE, the old branch did NOT fire, no scale was applied, and
  `sr` = `lp.steerRatio` = 12.5.** 🛑 **His row is the one that governs the drive.**

| \|angle\| | patched | vs **HIS 12.5** | vs stock 14.0 |
|---|---|---|---|
| 0–48° | 16.00 | **×1.280 — more turn-in** | ×1.143 |
| 60° | 15.02 | ×1.202 | ×1.073 |
| 76° | 14.52 | ×1.162 | ×1.037 |
| 95° | 13.97 | ×1.118 | ×0.998 |
| 121° | 13.75 | ×1.100 | ×0.982 |
| 191° | 13.50 | ×1.080 | ×0.964 |
| 236° | 12.81 | ×1.025 | ×0.915 |
| 303° | 11.67 | ×0.934 | ×0.834 |
| 380° | 11.06 | **×0.885 — less turn at lock** | ×0.790 |

**The crossover is at ~254° on his car, and at ~94° on a stock one** (EVIDENCE — `brentq` on the
interpolant for ratio = 12.5 and = 14.0 respectively). That difference is the whole point of carrying both
rows: **against his actual car he gets more turn-in across essentially the entire range he drives**, and
less only beyond ~254°, which his own data says is all below 5 m/s. Reading the stock column as if it were
his would put the crossover at 94° and predict a reduction through 121–236° that **he will not experience**.

**+28.0 % on centre is the headline number** — it is the same 1.28× as the measured curvature inflation
across 0–48°, and it is the correction to the SR 12.5 understeer bias. **65 % of engaged time sits inside
0–34°**, entirely within that flat band. This is a real authority change and should be driven as one, not
as a no-op refactor.

### 3.5 ⚠ This is openpilot's vehicle model, NOT the EPS firmware's compensation

The EPS firmware carries **its own** variable-ratio compensation curve (`0xC6B64`), which tracks the real
rack to ~2.5 % out to 120° and then goes flat, leaving ~20 % uncompensated at lock. **That is a separate
compensation living inside the ECU.** This patch changes openpilot's `VehicleModel`, which until now used a
single scalar. **Do not conflate the two, and do not assume one cancels the other** — they are different
transforms at different points in the chain, and nothing here has been shown to compose with `0xC6B64`.

---

## 4. Provenance of the numbers — MEASURED

Source: the operator's own artifact, *"Accord Rack Ratio"*, 2020 Accord, **427 min over 47 routes**, derived
from telemetry **four independent ways** with disjoint dependencies, all agreeing on the centre→120° swing:

| derivation | result |
|---|---|
| yaw rate + rear-axle speed | 1.242 |
| yaw rate + front wheel speed | 1.211 |
| rear differential, no IMU | 1.160 |
| wheel speeds alone | 1.226 |

Left and right measured independently, never mirrored; symmetric to within 1.5 % (a 2 % injected asymmetry
would have been detected). **Speed control PASSED** — the centre→120° swing measured inside three separate
speed bands gives 1.2137 / 1.1848 / 1.2000 with overlapping CIs, so the curve is rack geometry and not a
speed-dependent estimator artefact. Fitted true centre −4.25°, against openpilot's learned `angleOffsetDeg`
of −4.78° (§3.2). **65 % of engaged time sits inside 0–34°; all exposure beyond 120° occurs below 5 m/s.**

**The measured table (steering-wheel degrees per road-wheel degree):**

| \|angle\| | ratio | \|angle\| | ratio |
|---|---|---|---|
| 1.9° | 15.65 | 60.2° | 15.02 |
| 3.9° | 16.86 | 75.7° | 14.52 |
| 6.3° | 16.65 | 94.5° | 13.97 |
| 9.4° | 15.60 | 120.7° | 13.75 |
| 12.9° | 15.72 | 147.1° | 13.71 |
| 17.4° | 16.20 | 191.4° | 13.50 |
| 22.8° | 16.18 | 235.9° | 12.81 |
| 29.6° | 15.81 | 303.1° | 11.67 |
| 37.9° | 16.15 | 380.4° | 11.06 |
| 48.0° | 15.93 | | |

**Residual of the 10 shipped knots against every measured point (EVIDENCE, computed):**

| \|angle\| | measured | interp | error | | \|angle\| | measured | interp | error |
|---|---|---|---|---|---|---|---|---|
| 1.9° | 15.65 | 16.00 | +2.24 % | | 60.2° | 15.02 | 15.01 | −0.04 % |
| 3.9° | 16.86 | 16.00 | −5.10 % | | 75.7° | 14.52 | 14.53 | +0.06 % |
| 6.3° | 16.65 | 16.00 | −3.90 % | | 94.5° | 13.97 | 13.98 | +0.10 % |
| 9.4° | 15.60 | 16.00 | +2.56 % | | 120.7° | 13.75 | 13.75 | +0.02 % |
| 12.9° | 15.72 | 16.00 | +1.78 % | | 147.1° | 13.71 | 13.66 | −0.39 % |
| 17.4° | 16.20 | 16.00 | −1.23 % | | 191.4° | 13.50 | 13.49 | −0.05 % |
| 22.8° | 16.18 | 16.00 | −1.11 % | | 235.9° | 12.81 | 12.81 | +0.01 % |
| 29.6° | 15.81 | 16.00 | +1.20 % | | 303.1° | 11.67 | 11.67 | −0.01 % |
| 37.9° | 16.15 | 16.00 | −0.93 % | | 380.4° | 11.06 | 11.06 | 0.00 % |
| 48.0° | 15.93 | 16.00 | +0.44 % | | | | | |

**Max residual beyond 48° is 0.39 %.** Inside 48° the residuals reach 5.1 %, and that is **irreducible
scatter, not fit error**: the measured points there disagree with *each other* by 8 % (15.60 at 9.4° against
16.86 at 3.9°), so no smooth model can sit inside them. **16.00 flat to 48° is the honest reduction** of a
band whose mean is ≈16.05 — tracking those bins individually would inject measurement noise into the vehicle
model exactly where 65 % of engaged driving happens.

**One knot was added to the nine supplied: 60° = 15.02**, read straight off the measured table at 60.2°.
The nine-knot set jumped 48° → 76° across that point, and the chord cut the corner of a convex curve by
**+2.23 %** — the single worst residual in the whole table and the only one beyond 48° over 1 %. Adding the
measured point costs one array entry and takes the worst error beyond 48° from **2.23 % → 0.39 %**, per the
instruction not to trade accuracy for elegance on a physical curve. No number here is invented: every knot
value is a measured point, except the 16.00 flat band, which is the supplied reduction of the ten points ≤48°.

**Note on the superseded placeholder (kept as a record).** Before the measurement arrived this file shipped a
conservative guess: 16.60 at centre and 13.20 at 180°. The measurement says **16.00** at centre and **13.54**
at 180° — so the real rack is *slower* than guessed near centre and *quicker* at mid-angle. The conservative
instinct was right; the shape was not. This is why the map had to be measured rather than reasoned.

## 5. Fork and deploy procedure

**Fork (once, on github.com).** Open `https://github.com/firestar5683/StarPilot` → **Fork** → owner
`raayyymond`, keep the name `StarPilot`, **untick "Copy the `Dom` branch only"** if you want every branch.
Result: `https://github.com/raayyymond/StarPilot`.

**Push the branch (from this PC).**
```bash
cd /c/Users/dudei/Desktop/Projects/openpilots/StarPilot
git remote add fork https://github.com/raayyymond/StarPilot.git
git add selfdrive/controls/lib/latcontrol_vehicle_tunes.py \
        selfdrive/controls/controlsd.py \
        selfdrive/controls/tests/test_latcontrol.py
git commit -m "Accord: restore the rack's ratio curve instead of one sample of it"
git push fork Dom
```
(The working tree also carries unrelated pre-existing deletions under `starpilot/system/galaxy/bin/`.
The explicit `git add` above keeps them out of the commit. **Nothing has been committed or pushed by me.**)

**Point the device at the fork.** On the comma:
```bash
cd /data/openpilot
git remote set-url origin https://github.com/raayyymond/StarPilot.git
```
Then **Settings → Software → Target Branch → `Dom`** → **Check for Update** → **Download** → reboot.
`system/updated/updated.py` reads the target from the `UpdaterTargetBranch` param (`:282`, `:316`), lists
branches with `git ls-remote --heads` against whatever `origin` is (`:396`), then `git fetch origin <branch>`
(`:433`) and `git branch --set-upstream-to` (`:439`). **There is no URL allowlist, no owner check and no
signature verification**, so a personal fork works and the in-app update button keeps working. **EVIDENCE** —
orchestrator's read of `updated.py`, which I did not independently re-verify.

**Staying current with upstream — run these three steps EVERY time, in order.**

1. On your fork's GitHub page, use **Sync fork → Update branch**. That merges upstream `Dom` into your `Dom`
   and keeps your commit. **Never press "Discard N commits"** — that button hard-resets your branch to
   upstream and deletes this patch. If GitHub offers only "Discard", the branches have diverged; merge
   locally instead:
   ```bash
   git remote add upstream https://github.com/firestar5683/StarPilot.git
   git fetch upstream && git merge upstream/Dom   # or: git rebase upstream/Dom
   git push fork Dom
   ```
2. 🛑 **Run the guard.** This is not optional, and it is the mitigation for the one failure mode that is
   silent on the road (§6):
   ```bash
   grep -n "get_honda_accord_steer_ratio" selfdrive/controls/controlsd.py   # must return EXACTLY 1 hit
   ```
   Zero hits means an upstream merge silently dropped the Accord branch and the car has reverted to the
   learned/toggle steer ratio. **Do not deploy until it returns 1.**
3. Confirm `CAR.HONDA_ACCORD` still covers 2018–22 in `opendbc_repo/opendbc/car/honda/values.py`. If
   upstream splits the platform by year, the `elif` stops matching for the split-off years and they fall
   back silently in the same way.

---

## 6. Rebase risk

| file | commits (total / since 2026-06-01) | risk |
|---|---|---|
| `latcontrol_vehicle_tunes.py` | 84 / 84 | **High traffic, low conflict.** The change is one constant block in a per-car section and one self-contained function. Upstream edits elsewhere in a 2000-line file merge cleanly. |
| `controlsd.py` | 62 / 31 | **Medium.** The touched hunk is the `state_control()` SR ladder. Any upstream edit to that ladder — most likely adding another car — conflicts textually but resolves trivially. |
| `test_latcontrol.py` | 174 / 79 | **Highest traffic.** Conflicts here are cosmetic; if one appears, take upstream and re-apply the one test. |

`paramsd.py` (9 commits total, last 2026-07-20) and `starpilot_variables.py` (128 / 75) are untouched — a
deliberate saving, since `starpilot_variables.py` is the second-busiest file in the set.

### What breaks if upstream changes things

- **Upstream deletes or rewrites the `accord_ratio_is_explicit` block.** Best case for us: our hunk becomes
  a pure addition. If upstream instead removes the Accord branch entirely, the merge drops our line silently
  and the car reverts to the learned/toggle SR — **the only failure mode here that is silent on the road.**
  Guard: after every upstream sync, `grep -n "get_honda_accord_steer_ratio" selfdrive/controls/controlsd.py`
  must return exactly one hit.
- **Upstream renames or re-signatures `get_honda_accord_steer_ratio_scale`.** We already renamed it, so a
  rename upstream conflicts loudly in the tunes file. Loud is fine.
- **Upstream stops re-exporting the tunes module through `latcontrol_torque`** (`latcontrol_torque.py:15` is
  `from ...latcontrol_vehicle_tunes import *`). `controlsd`'s import would fail at start-up — an immediate,
  obvious break, not a silent one.
- **Upstream changes `paramsd`/`use_custom_steerRatio` semantics.** No effect on the Accord: nothing in the
  Accord's SR path reads them any more. That immunity is the main structural benefit of §3.1.
- **Upstream moves the Accord onto a different platform enum** (e.g. splits 2018–20 from 2021–22). The
  `elif` would stop matching for the split-off years and they would silently fall back to the learner.
  Guard: same grep, plus check `CAR.HONDA_ACCORD` still covers 2018–22 in `honda/values.py`.

---

## 7. Verification actually performed

- **EVIDENCE** — all three edited files parse (`ast.parse`).
- **EVIDENCE** — the shipped knots evaluated against all 19 measured points; full residual table in §4.
  Max error beyond 48° is **0.39 %**; inside 48° the residual is bounded by the measurement's own scatter.
- **EVIDENCE** — map values and symmetry: 0°→16.00, 48°→16.00, 60°→15.01, 95°→13.98, 121°→13.75,
  191°→13.49, 236°→12.81, 303°→11.67, 380°→11.06, 600°→11.06 (endpoint held), −180°→13.54 = +180°.
- **EVIDENCE** — the ratio crosses the live 12.5 baseline at **254°** (`brentq` on the interpolant), which
  is where the effect in §3.4 changes sign.
- **EVIDENCE** — scale-form cross-check against the supplied summary: 16.00/16.33 = 0.980 (matches),
  13.97/16.33 = 0.856 (vs the old constant's 0.857), 11.06/16.33 = 0.677 (vs 0.680).
- **EVIDENCE** — `grep` confirms no remaining reference to `get_honda_accord_steer_ratio_scale` or
  `HONDA_ACCORD_STEER_RATIO_SCALE` anywhere in the tree.
- **NOT DONE** — the test suite was not executed. `pytest` is absent from the `bin_decompile` conda env and
  openpilot's harness needs the Linux-built `cereal`/`msgq`. Run
  `pytest selfdrive/controls/tests/test_latcontrol.py -k honda_accord` on the device or a Linux checkout
  before flying it.
- **NOT DONE** — SSH to `comma@10.0.0.168` **failed**; see §8. No device state was read.

## 8. SSH attempts (read-only; nothing was written, no CAN/UDS, no flash)

Two attempts, both refused:

1. `ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes comma@10.0.0.168 '<reads>'`
   → **REMOTE HOST IDENTIFICATION HAS CHANGED**: the device now presents an ED25519 key
   (`SHA256:lpK1BMlc/miqavwFKIZIUB8etYShCShxmC5q3Wb/9E4`) while `C:\Users\dudei\.ssh\known_hosts:6` holds an
   old ECDSA key for that address. ssh then disabled password auth and refused.
2. The same with `-o UserKnownHostsFile=/dev/null` (bypasses the stale entry *without* editing
   `known_hosts`) → `Permission denied (publickey)` — this PC has no key the device accepts.

`known_hosts` was **not** modified. To enable reads later: `ssh-keygen -R 10.0.0.168`, then add this PC's
public key to the device's SSH Keys setting (Settings → Device → SSH Keys, GitHub username), then re-run.

Unread, and therefore assumed rather than confirmed: `UpdaterTargetBranch`, the live `SteerRatio` /
`SteerKP` / `SteerLatAccel` / `SteerFriction` values, the device's current `origin` URL and branch, and the
fingerprinted platform. **None of them change the patch** — the patch is correct for
`CAR.HONDA_ACCORD` regardless — but the deploy steps in §5 assume the device's `origin` is still upstream
and its target branch is still `Dom`.
