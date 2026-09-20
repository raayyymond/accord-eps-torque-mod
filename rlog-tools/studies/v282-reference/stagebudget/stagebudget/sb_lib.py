# -*- coding: utf-8 -*-
"""stagebudget: shared library.

Two jobs.

(1) EXACT REPRODUCTION of the fork's setpoint-shaping software from its OWN logged input, so that the
    two software legs can be split with no estimation error:

        X  = model desired lateral accel        = controlsState.desiredCurvature * vEgo^2
                                                 (== latcontrol_torque's future_desired_lateral_accel, :253)
        Z0 = the DELAY-CANCELLER / JERK-FILTER output, i.e. `setpoint` BEFORE the Accord ref filter
             (latcontrol_torque :303-317)
        Z  = logged desiredLateralAccel = `setpoint` AFTER the two cascaded ref filters (:319-329, :839)

    Every constant is read out of the fork AT THE COMMIT EACH ROUTE FLEW (git show), never from HEAD.
    The reproduction is VALIDATED against the logged Z on every route; nothing downstream is reported
    for a route whose validation fails.

(2) The analytic transfer of each software stage, used only as a POSITIVE CONTROL on the measured legs.

This is MEASUREMENT + exact software replay of a logged software stage.  It is NOT a plant model and
predicts nothing about the car.  ANALYSIS ONLY, read-only.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

FS = V.FS
DT = 0.01                      # DT_CTRL; latcontrol_torque's self.dt
MAX_LAT_JERK_UP = 2.5          # m/s^3, identical at every flown commit (git-checked)

# ---------------------------------------------------------------------------------------------
# per-flown-commit software configuration.  EVIDENCE: `git show <commit>:<file> | grep`, run
# 2026-09-20 over all ten flown commits (see JERK/REF columns in sb_params.txt).
#   ref_block   the `accord_ref_filter_1/2` cascade exists in latcontrol_torque at that commit
#   jerk_hz     cutoff of the lateral-jerk low-pass in the delay-compensation stage
#               HONDA_ACCORD_JERK_LP_HZ = 4.0 exists ONLY at 84766cdc5; every other flown commit
#               falls through to the generic LP_FILTER_CUTOFF_HZ = 1.2.
# ---------------------------------------------------------------------------------------------
COMMIT = {
    "8a28dcef8": dict(ref_block=False, jerk_hz=1.2),
    "ffe28378f": dict(ref_block=False, jerk_hz=1.2),
    "0f98d8c75": dict(ref_block=False, jerk_hz=1.2),
    "57410c3b4": dict(ref_block=False, jerk_hz=1.2),
    "4247cb09e": dict(ref_block=False, jerk_hz=1.2),
    "66cf4454a": dict(ref_block=False, jerk_hz=1.2),
    "e8e62f0e1": dict(ref_block=True, jerk_hz=1.2),
    "08a5a7064": dict(ref_block=True, jerk_hz=1.2),
    "e44b6cd31": dict(ref_block=True, jerk_hz=1.2),
    "84766cdc5": dict(ref_block=True, jerk_hz=4.0),
}

# route -> (group, flown commit, flown AccordRefFilter).  Group and RF come from each route's OWN
# initData (hsurface/surface/params_all.json); RF None = the code has no ref-filter stage at all.
ROUTES = {
    "00000064--ce6b0b0ebb": ("V282", "0f98d8c75", None),
    "00000065--b9f78988bd": ("V282", "0f98d8c75", None),
    "0000006c--2bc842dbac": ("V282", "57410c3b4", None),
    "00000039--f56039af87": ("V282old", "8a28dcef8", None),
    "0000003a--283a39a1d6": ("V282old", "ffe28378f", None),
    "0000003c--927965c2b4": ("V282old", "ffe28378f", None),
    "0000006c--68c6e94b17": ("T64", "84766cdc5", 0.06),
    "0000006d--05e83bb04f": ("T64", "84766cdc5", 0.06),
    "0000006e--6ca3e014fd": ("T64B", "84766cdc5", 0.06),
    "00000076--d0b7ea7e4d": ("T5", "e44b6cd31", 0.12),
    "00000075--6c8687d5bd": ("T4", "08a5a7064", 0.12),
    "00000074--2bf17ca67d": ("T4", "08a5a7064", 0.12),
    "00000072--8001fc3048": ("T3", "e8e62f0e1", 0.12),
    "00000073--79fd149dd8": ("T3", "e8e62f0e1", 0.12),
    "00000070--717f5a7866": ("T2", "4247cb09e", None),
    "00000071--f2c9d073a3": ("T2", "66cf4454a", None),
}
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
# the like-for-like comparator set: torque revs that fly the SAME 1.2 Hz jerk filter as V282
TORQ_J12 = ["T5", "T4", "T3", "T2"]

SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
SPDN = ["0-8", "8-15", "15-22", "22+"]
BANDS = [(0.06, 0.15, 40.96), (0.15, 0.30, 20.48), (0.30, 0.60, 10.24), (0.60, 1.20, 10.24)]
# fixed absolute cuts on the window's MEDIAN |model| (m/s^2), the amplitude axis the
# hsurface/amplitude stream used (its quintiles ran 0.007 -> 0.12 m/s^2)
ACUT = [(0.0, 0.012), (0.012, 0.025), (0.025, 0.050), (0.050, 0.100),
        (0.100, 0.200), (0.200, 9.9)]
ACUTN = ["a1 <.012", "a2 .012-.025", "a3 .025-.050", "a4 .050-.100",
         "a5 .100-.200", "a6 >=.200"]


# ---------------------------------------------------------------------------------------------
# the fork's first-order filter, exactly (common/filter_simple.py)
#     update_alpha(rc): alpha = dt/(rc+dt);   update(v): x = (1-alpha)x + alpha v
# ---------------------------------------------------------------------------------------------
def alpha_of(rc, dt=DT):
    return dt / (rc + dt)


def fof_H(f, rc, dt=DT):
    """Complex response of ONE discrete FirstOrderFilter with that rc, at frequency f (Hz)."""
    a = alpha_of(rc, dt)
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return a / (1.0 - (1.0 - a) * z)


def ref_filter_H(f, rc, dt=DT):
    """The Accord reference-shaping stage: TWO cascaded FirstOrderFilters at the same rc."""
    if not rc:
        return np.ones_like(np.asarray(f, float), dtype=complex)
    return fof_H(f, rc, dt) ** 2


def canceller_H(f, D, jerk_hz, dt=DT):
    """Analytic response of the delay-compensation stage IGNORING both jerk clips:
           Z0(s)/X(s) = e^{-sD} + F_j(s) * (1 - e^{-sD}) * (D_mult/D_buf)
       with the buffer delay quantised to whole frames the way the code quantises it
       (delay_frames = clip(int(D/dt),1,buflen)) and the multiply using the UNquantised D.
       Control only; the measured leg is the one that is reported."""
    f = np.asarray(f, float)
    nd = max(int(D / dt), 1)
    Db = nd * dt
    e = np.exp(-2j * np.pi * f * Db)
    Fj = fof_H(f, 1.0 / (2.0 * np.pi * jerk_hz), dt)
    return e + Fj * (1.0 - e) * (D / Db)


def group_lag_ms(H, f):
    """-d(phase)/d(omega) of an analytic response over a grid, in ms (positive = lags)."""
    ph = np.unwrap(np.angle(H))
    return -np.gradient(ph, 2 * np.pi * np.asarray(f, float)) * 1e3


# ---------------------------------------------------------------------------------------------
# (1) the reproduction
# ---------------------------------------------------------------------------------------------
def replay_setpoint(S, jerk_hz, ref_rc):
    """Re-run latcontrol_torque's setpoint chain frame by frame over the WHOLE route.

    latcontrol_torque.py, identical in structure at every flown commit:
      :253  future_desired_lateral_accel = desired_curvature * vEgo**2                     (= X)
      :303  delay_frames = int(clip(lat_delay/dt, 1, request_buffer_len))
      :304  expected_lateral_accel = curvature_request_buffer[-delay_frames] * vEgo**2
      :305  curvature_request_buffer.append(desired_curvature)      <- AFTER the read
      :313  raw_lateral_jerk   = clip((X - expected)/max(lat_delay, dt), +-MAX_LAT_JERK_UP)
      :315  desired_lateral_jerk = clip(jerk_filter.update(raw), +-MAX_LAT_JERK_UP)
      :317  setpoint = expected + desired_lateral_jerk * lat_delay                          (= Z0)
      :322  if accord_ref_rc > 0: setpoint = rf2.update(rf1.update(setpoint))                (= Z)
    inactive frames (:256-289): the buffer is STILL appended, jerk_filter.x = 0,
      accord_ref_filter_{1,2}.x = X  (primed on the live command).

    Returns Z0, Zhat, and the two clip-activity masks.  Index arithmetic is only valid inside a
    contiguous clock block, so the caller must mask on `ok_block`.
    """
    t = S["t"]
    n = len(t)
    curv = np.nan_to_num(S["_curv"])
    v = np.nan_to_num(S["v"])
    X = curv * v * v
    D = np.nan_to_num(S["lat_delay"])
    act = S["active"]
    # frame index of a clock discontinuity: restart the buffer history there
    gap = np.zeros(n, bool)
    gap[1:] = np.diff(t) > 4.0 / FS
    gap[0] = True

    aj = alpha_of(1.0 / (2.0 * np.pi * jerk_hz))
    ar = alpha_of(ref_rc) if ref_rc else None

    Z0 = np.full(n, np.nan)
    Zh = np.full(n, np.nan)
    ok = np.zeros(n, bool)
    clip_raw = np.zeros(n, bool)
    clip_flt = np.zeros(n, bool)

    buf = np.zeros(n)              # buf[j] = curvature appended at frame j  (== curv[j])
    jx = 0.0
    r1 = r2 = 0.0
    blk0 = 0
    for j in range(n):
        if gap[j]:
            blk0 = j
            jx = 0.0
            r1 = r2 = X[j]
        buf[j] = curv[j]
        nd = int(D[j] / DT)
        nd = 1 if nd < 1 else (500 if nd > 500 else nd)
        if not act[j]:
            jx = 0.0
            r1 = r2 = X[j]
            continue
        if j - nd < blk0:
            continue                # not enough contiguous history for this frame
        exp_la = buf[j - nd] * v[j] * v[j]
        raw = (X[j] - exp_la) / max(D[j], DT)
        if raw > MAX_LAT_JERK_UP:
            raw = MAX_LAT_JERK_UP; clip_raw[j] = True
        elif raw < -MAX_LAT_JERK_UP:
            raw = -MAX_LAT_JERK_UP; clip_raw[j] = True
        jx = (1.0 - aj) * jx + aj * raw
        jf = jx
        if jf > MAX_LAT_JERK_UP:
            jf = MAX_LAT_JERK_UP; clip_flt[j] = True
        elif jf < -MAX_LAT_JERK_UP:
            jf = -MAX_LAT_JERK_UP; clip_flt[j] = True
        sp = exp_la + jf * D[j]
        Z0[j] = sp
        if ar is None:
            Zh[j] = sp
        else:
            r1 = (1.0 - ar) * r1 + ar * sp
            r2 = (1.0 - ar) * r2 + ar * r1
            Zh[j] = r2
        ok[j] = True
    return Z0, Zh, ok, clip_raw, clip_flt


def load_route(rk):
    """v282cmp.load plus the raw desired curvature (the replay needs curvature, not X)."""
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    S = V.load(rk)
    S["_curv"] = D["cs_des_curv"]
    return S


def _self_test():
    """Positive controls on the analytic pieces and on the replay machinery."""
    f = np.array([0.05, 0.1, 0.2, 0.5, 1.0])
    # 1. one FOF at rc: DC gain 1, group lag at DC -> rc (+dt/2 discretisation)
    g = fof_H(1e-6, 0.12)
    assert abs(abs(g) - 1.0) < 1e-6, g
    fg = np.linspace(1e-4, 0.05, 200)
    lag = group_lag_ms(fof_H(fg, 0.12), fg)[0]
    assert 115.0 < lag < 130.0, lag                      # 0.12 s + dt/2
    lag2 = group_lag_ms(ref_filter_H(fg, 0.12), fg)[0]
    assert 235.0 < lag2 < 255.0, lag2                    # 2*RC
    assert abs(group_lag_ms(ref_filter_H(fg, 0.06), fg)[0] - lag2 / 2) < 15.0
    # 2. ref_filter_H with rc None/0 is the identity
    assert np.allclose(ref_filter_H(f, None), 1.0)
    # 3. the canceller is EXACT (H == 1 at every f) when the jerk filter is infinitely fast
    Hc = canceller_H(f, 0.30, 1e6)
    assert np.allclose(np.abs(Hc), 1.0, atol=2e-3), np.abs(Hc)
    assert np.allclose(np.degrees(np.angle(Hc)), 0.0, atol=0.6), np.degrees(np.angle(Hc))
    # 4. the replay reproduces a hand-computed 3-frame case with no clipping and no ref filter
    n = 400
    S = dict(t=np.arange(n) * DT, v=np.full(n, 20.0), active=np.ones(n, bool),
             lat_delay=np.full(n, 0.20), _curv=np.zeros(n))
    S["_curv"][200:] = 1e-4                              # a curvature step, X step = 0.04 m/s^2
    Z0, Zh, ok, c1, c2 = replay_setpoint(S, 1.2, None)
    assert not c1.any() and not c2.any()
    assert np.allclose(Z0[ok], Zh[ok])
    assert abs(Z0[150] - 0.0) < 1e-12
    # the step arrives at the buffer tap 20 frames later; before that Z0 is pure jerk-filter lead
    assert Z0[205] > 0.0 and Z0[205] < 0.04               # leading, not yet at the tap
    assert abs(Z0[-1] - 0.04) < 1e-6                      # settles on the step exactly
    # 5. the replay's steady-state gain is exactly 1 for a ramp (the canceller's whole point)
    S2 = dict(t=np.arange(3000) * DT, v=np.full(3000, 20.0), active=np.ones(3000, bool),
              lat_delay=np.full(3000, 0.30), _curv=np.linspace(0, 2e-4, 3000))
    Z0b, _, okb, cr, cf = replay_setpoint(S2, 1.2, None)
    X2 = S2["_curv"] * 400.0
    err = Z0b[2000:2900] - X2[2000:2900]
    assert np.abs(err).max() < 2e-4, np.abs(err).max()     # a ramp is tracked with ~no lag
    return ("sb_lib self-test OK: 2*RC lag recovered (%.0f ms at 0.12), canceller exact at F_j=1, "
            "replay reproduces a step and tracks a ramp lag-free" % lag2)


if __name__ == "__main__":
    print(_self_test())
