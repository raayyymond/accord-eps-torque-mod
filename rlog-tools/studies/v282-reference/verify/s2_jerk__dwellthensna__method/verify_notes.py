"""Adversarial METHOD/ARITHMETIC verification of finding
'dwell-then-snap-stick-slip-in-events' (stream s2_jerk).

What this does: re-runs s2_jerk/s2_stickslip.py (unmodified, reads only the already-extracted
event caches in s2_jerk/_out/events_*.npz via s2_common.load_all -> the shared v282cmp.py
event definitions) and diffs its printed/json output against the numbers quoted in the finding.
Also inspects s2_common.py, s2_stickslip.py and v282cmp.py's event_metrics() for estimator
correctness (window lengths, lag alignment, sign handling, bootstrap CIs over events AND routes).

Result: see the reasoning in the caller's StructuredOutput. Summary:
- conc (angle-travel concentration) and dwell-share numbers in the finding match
  s2_jerk/_out/s2_stickslip.json to the last reported digit, for every (rev, stratum) cited,
  EXCEPT two CI bounds that are each off by 0.01 in the generous direction
  (T64B|<15 dwell ci_ev upper 0.2446 reported as +0.25 instead of +0.24; T64|lo<15
  la_pose.jerk_rough ci_ev lower 0.090 reported as +0.08 instead of +0.09) -- both are
  rounding slips, not fabrication, and neither changes whether the CI excludes zero.
- la_act.jerk_rough / la_pose.jerk_rough numbers match s2_jerk/_out/s2_analyze.txt exactly
  for the T64-only strata the finding cites (hi>=15 n=48, v8-15 n=10, lo<15 n=11).
- REF is correctly restricted to group=='V282' only (318 events, 3 routes); 'V282old' (3 more
  routes, older fork) is present in the same _out/ dir but is NOT pulled into REF by
  s2_common.load_all/s2_stickslip's `r['group']=='V282'` filter -- confirmed by inspecting
  the per-route group label stored in each events_*.npz.
- Matching (s2_common.match) uses log-space calipers on jerk, step AND speed jointly
  (cal_j=cal_s=0.35, cal_v=0.25), so the conc/dwell/jerk_rough deltas are not a speed- or
  amplitude-confound artifact of the kind flagged elsewhere this session for the ARM-B/6e A-B.
- conc_of() and the dwell window are unit-consistent with their docstrings (NPRE=100 @ 100 Hz
  -> window indices 50:300 = [-0.5,+2.0]s for conc, 70:200 = [-0.3,+1.0]s for dwell) and the
  ramp-vs-staircase positive/negative control assertion (0.25 / 0.71) reproduces exactly.
- This stream does NOT use band_H (phasor-averaged |H|) anywhere -- it is purely event/time
  domain, so the "no phasor-averaged H where phase rotates" pitfall named in the task brief
  does not apply here.
- Both event-bootstrap (ci_ev) and route-cluster-bootstrap (ci_rt) CIs are computed for every
  stratum; the finding reports both for the headline (>=15 m/s conc) row and reports ci_ev only
  for the rest, which is defensible since ci_rt is near-identical everywhere checked.
- Two known-but-symmetric estimator quirks (Dd floor of 1e-3 in the dwell normalisation for
  near-zero-step events; event_metrics' shrinking-overlap 0..0.8s forward-only lag search)
  apply identically to V282 and torque-mode events in every matched pair, so they cannot
  manufacture the reported group difference on their own.

Command used to reproduce (from s2_jerk/):  python s2_stickslip.py
Output diffed by hand against the finding's "magnitude" block and against
s2_jerk/_out/s2_analyze.txt (la_act.jerk_rough / la_pose.jerk_rough rows), using the awk
one-liner below to pair each jerk_rough row with its ##### group / -- stratum header:

  awk '/^#####/{grp=$0} /^  --/{sub(/^  -- /,"");strat=$1}
       /la_pose.jerk_rough|la_act.jerk_rough/{print grp" | "strat" | "$0}' s2_analyze.txt
"""
