---
name: reference-starpilot-fork-updater-has-no-allowlist-and-the-16-33-steerratio-trap
description: 2026-09-04, verified by the orchestrator in the operator's own StarPilot checkout (branch Dom, C:/Users/dudei/Desktop/Projects/openpilots/StarPilot). THE FORK QUESTION IS ANSWERED YES - system/updated/updated.py reads the target branch from the UpdaterTargetBranch param (:282/:316), builds the branch picker from `git ls-remote --heads` on whatever origin is (:396), fetches `git fetch origin <branch>` (:433) and sets upstream (:439); a grep for allowlist/whitelist/signature/verify/commaai/firestar returns ZERO matches - no URL allowlist, no owner check, no signature verification. So pointing origin at a personal fork and setting Target Branch makes the Galaxy software-update button track that fork. Params live in /data/params, OUTSIDE the repo, so every param change survives the updater's reset --hard + clean -xdff and needs no fork at all. THE TRAP: never set SteerRatio to 16.33. controlsd.py:471 computes accord_ratio_is_explicit = use_custom_steerRatio AND abs(param - CP.steerRatio) > 0.01, and the Accord's platform steerRatio IS 16.33 (opendbc honda/values.py:188) - so at 16.33 the flag goes FALSE and sr *= HONDA_ACCORD_STEER_RATIO_SCALE = 14.0/16.33, giving an EFFECTIVE ratio of 14.0. The operator's own backup shows he was at 16.33 with ForceAutoTune ON on 2026-09-02 18:50, i.e. silently running 14.0. Safe values 16.1 / 16.5; avoid 16.32-16.34.
metadata:
  type: reference
---

# The StarPilot fork/updater question, answered — and the 16.33 SteerRatio trap — 2026-09-04

All of this was verified by the orchestrator directly in the operator's checkout
(`C:/Users/dudei/Desktop/Projects/openpilots/StarPilot`, branch `Dom`), not relayed from an agent.

## 1. Will the software-update button follow a personal fork? YES [EVIDENCE]

`system/updated/updated.py`:

| line | behaviour |
|---|---|
| `:282` / `:316` | reads / writes the target branch from the **`UpdaterTargetBranch`** param |
| `:396` | builds the branch picker from **`git ls-remote --heads`** on whatever `origin` is |
| `:433` | `git fetch origin <branch>` |
| `:439` | `git branch --set-upstream-to origin/<branch>` |

A grep for `allowlist|whitelist|signature|verify|commaai|firestar` over that file returns **zero matches**.
**There is no URL allowlist, no owner check and no signature verification.**

⇒ Fork the repo, branch `Dom` from upstream `Dom`, then on the device
`git remote set-url origin https://github.com/<user>/StarPilot.git` and pick the branch under
Settings → Software → Target Branch. Keep current with GitHub's **Sync fork → "Update branch"**
(never *"Discard N commits"*), then the update button.

**BELIEF, not verifiable from the repo:** that GitHub offers "Update branch" on an ahead-and-behind
branch, and that the Galaxy backend does not gate on the origin URL (`the_galaxy.py` only *reports* it
as `forkMaintainer` telemetry). Both settle by simply doing it once.

**Params need no fork at all.** `SteerRatio`, `SteerKP`, `SteerLatAccel`, `SteerFriction` live in
`/data/params`, outside the repo, so they survive the updater's `reset --hard` + `clean -xdff`. Only a
*code* change needs the fork — and a purely local edit is wiped, while a local *commit* silently stops
updates. Churn is low: the Accord constants block took **4** commits since June against 84 for the
file; never put structural changes in `latcontrol_torque.py` (92 commits).

## 2. 🛑 THE 16.33 TRAP — never set SteerRatio to the platform value

```python
# controlsd.py:469-478
custom_accord_ratio     = toggles.steerRatio (default CP.steerRatio)
accord_ratio_is_explicit = use_custom_steerRatio and abs(custom_accord_ratio - CP.steerRatio) > 0.01
...
elif carFingerprint == HONDA_ACCORD and not accord_ratio_is_explicit:
    sr *= get_honda_accord_steer_ratio_scale(CS.vEgo)   # = HONDA_ACCORD_STEER_RATIO_SCALE = 14.0/16.33
```
and `opendbc/car/honda/values.py:188` gives the Accord **`steerRatio = 16.33`**.

⇒ Set the param to 16.33 and the explicit flag goes **False**, so the 0.8573 scale applies and the
**effective ratio becomes 14.0** — worse than most settings anyone would choose deliberately.
**Safe: 16.1, 16.5. Avoid 16.32–16.34.** Clamp is 0.5–1.5 × 16.33 = 8.17–24.50
(`starpilot_variables.py:760`).

**The operator hit this.** His decoded backups by mtime: 2026-09-02 18:50 → SteerRatio **16.33** with
`ForceAutoTune` True / `ForceAutoTuneOff` False — **both gates false, so he was silently running an
effective 14.0**. Since 2026-09-03 00:02 he is at 12.5 with `ForceAutoTuneOff` True, so the explicit
flag is genuinely on and 12.5 is really 12.5.

## 3. The levers, and their true directions [EVIDENCE]

- **`SteerKP` 0.6 → 0.8** — free, no fork. `latcontrol_vehicle_tunes.py:77` already sets
  `HONDA_ACCORD_TORQUE_KP = 0.8`, but the param overwrites it every frame with 0.6.
- **`SteerLatAccel`** — free. `opendbc/car/interfaces.py:326`:
  `return lateral_acceleration / float(torque_params.latAccelFactor)`. It is a **DIVISOR**, so
  **lowering it RAISES delivered torque** (2.11 → 1.689 is ×1.25). ⚠ It also scales the friction term
  the *other* way (`friction * latAccelFactor`, `lateral.py:196`), and it conflicts with the
  2026-09-02 back-calc that wanted it *raised* to 2.53 for the 3.9 Hz oscillation.
- **`HONDA_ACCORD_TORQUE_KI` 0.15 → 0.35** (`latcontrol_vehicle_tunes.py:78`) — **the one line worth
  forking for**. The module default at `latcontrol_torque.py:29` **is already 0.35**; the Accord
  override is what lowered it. 🛑 **Must fly on a Ki-0 EPS image (V282), never on V283** — two
  integrators on the same error at the same operating point.
- **`SteerRatio`** — see the trap above. Raising it is correct **only on a Ki-0 image**; on V283 the
  EPS integrator over-delivers and a lower SR is holding it down.

Related: [[feedback-openpilot-means-starpilot-dom-branch]],
[[accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps]],
[[project-operator-starpilot-toggles-decoded-2026-09-03]],
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]].
