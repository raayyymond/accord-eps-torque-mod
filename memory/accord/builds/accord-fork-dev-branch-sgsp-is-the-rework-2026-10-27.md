---
name: accord-fork-dev-branch-sgsp-is-the-rework-2026-10-27
description: 2026-10-27 — upstream Dom force-pushed to StarPilot 7.0 (unrelated history); the 14 Accord commits were PORTED onto it as 4 commits on `dev` (pushed); dev-dom6 keeps the old line; idle hold now enabled-only under 7.0 AOL; tests local + device
metadata:
  type: project
---

**2026-10-27.** Operator: *"Copy accord-PTM to a new branch, dev"* → then *"Port now"* once upstream `Dom` turned out to be force-pushed to the 7.0 "Domathon" rewrite (`efe875ffd6`, 19 060 commits, NO common ancestor, tree under `openpilot/`, Honda port stock, Galaxy web app absent).
- **`dev` = new `upstream/Dom` + 4 ported commits** `e9256c574e` · `b164e6c830` · `0aebe81587` · `46dfc39dbe`, pushed `origin/dev` (force, the first `dev` was the old line). **`dev-dom6` `5ec9ae7449`** = old Dom + our 14 + the 3-file "Trick or Treat" merge, pushed. `accord-PTM` frozen. **Device switched to `dev` `7a83cd1cc2` the same night** (offroad, theme assets stashed, reboot clean, no build loop); first 7.0 drive still ahead.
- **Port deltas:** flags 32768/65536 (16384 taken); detection before the modified-EPS dashcam fallback, `EPS_MODIFIED` no longer set; no `lateralControlMode` field, turn lead already torque-only → 45a1a529c2 moot; `get_params` has no toggles; learner/brake thresholds live in `bosch_longitudinal.py`; **idle hold only when enabled + main on** (7.0 panda lateral grant under AOL is a session, invisible to the carcontroller; `AlwaysOnLateral=1` on the device) — BELIEF harmless, check AOL-idle engagement on-car.
- **Test venues:** bin_decompile 3.12 (+pyzmq, pycryptodome; PYTHONPATH `root;opendbc_repo;msgq_repo;rednose_repo;panda` in Windows form) runs opendbc + latcontrol tests; `fcntl`/compiled `msgq` block anything that imports `openpilot.common.params` → run those on the comma 4 (`ssh comma`, `/usr/local/venv/bin/python`, `PYTHONPATH=/data/tools/pytest` for pytest, side worktree `/data/dev-wt`). Fetching the 7.0 history to the device is SLOW (> 10 min). **Device run 2026-10-27: 477 passed, 0 failed**; the Galaxy `test_settings.py` aborts in messaging under the live stack (environment).
- Fork-folder Claude context set up in its own session (fork `CLAUDE.md`, skill copy, `docs/ACCORD.md`).

**How to apply:** check out `dev` on the device for the next drive; `upstream/Dom` (7.0) is now the merge source. Related: [[accord-follow-floor-0p4s-fork-0b1b09a1eb-2026-10-22]], [[feedback-openpilot-means-starpilot-dom-branch]].
