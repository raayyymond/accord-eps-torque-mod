"""fill_lagbudgetand: the fork's model->setpoint chain, per flown commit, as code-exact simulation and transfer function.

Source (read from each commit with `git show <c>:<path>`, cite by name):
  modeld.py              lat_delay = liveDelay.lateralDelay + lat_smooth_seconds (LAT_SMOOTH_SECONDS 0.1, Honda: not speed-scheduled)
                         lat_action_t = lat_delay + frame_delay (DT_MDL) + action_delay (DT_MDL/2)
                         desiredCurvature = smooth_value(get_curvature_from_plan(..., lat_action_t), prev, tau=0.1) at 20 Hz
  controlsd.py           lat_delay = liveDelay.lateralDelay + get_control_lateral_smooth_seconds(...)  (= +0.1 for Honda)
                         self.desired_curvature = clip_curvature(...)  -> controlsState.desiredCurvature  (the 'model' here)
  latcontrol_torque.py   LatControlTorque.update:
      delay_frames = int(clip(lat_delay/dt, 1, 100)); expected = curvature_request_buffer[-delay_frames] * vEgo^2 (read BEFORE append)
      raw_jerk = clip((u - expected)/max(lat_delay, dt), +-2.5);  jerk = clip(jerk_filter.update(raw_jerk), +-2.5)
      jerk_filter rc = 1/(2 pi fc): fc = LP_FILTER_CUTOFF_HZ 1.2 (all commits) EXCEPT 84766cdc: HONDA_ACCORD_JERK_LP_HZ 4.0
      setpoint = expected + jerk * lat_delay
      84766cdc/e44b6cd3/08a5a706 only (AccordRefFilter): setpoint = F2(F1(setpoint)), FirstOrderFilter rc = toggle, alpha = dt/(rc+dt)
      pid_log.desiredLateralAccel = setpoint;  Accord plant FF: curv_des = (setpoint - latAccelOffset*fade)/v^2 -> angle_des -> FF
  inactive branch: buffer keeps appending desired_curvature, jerk_filter.x = 0, ref filters primed to u.
"""
import numpy as np

DT = 0.01
COMMITS = {  # jerk LP cutoff Hz, AccordRefFilter code present
    "0f98d8c7": dict(jerk_fc=1.2, ref=False), "57410c3b": dict(jerk_fc=1.2, ref=False),
    "8a28dcef": dict(jerk_fc=1.2, ref=False), "ffe28378": dict(jerk_fc=1.2, ref=False),
    "08a5a706": dict(jerk_fc=1.2, ref=True), "e44b6cd3": dict(jerk_fc=1.2, ref=True),
    "84766cdc": dict(jerk_fc=4.0, ref=True),
}
# per-route flown config (census_params.json, EVIDENCE from initData): ref rc, logged liveDelay.lateralDelay
ROUTE_CFG = {
    "00000064--ce6b0b0ebb": dict(commit="0f98d8c7", ref_rc=0.0),
    "00000065--b9f78988bd": dict(commit="0f98d8c7", ref_rc=0.0),
    "0000006c--2bc842dbac": dict(commit="57410c3b", ref_rc=0.0),
    "00000039--f56039af87": dict(commit="8a28dcef", ref_rc=0.0),
    "0000003a--283a39a1d6": dict(commit="ffe28378", ref_rc=0.0),
    "0000003c--927965c2b4": dict(commit="ffe28378", ref_rc=0.0),
    "0000006c--68c6e94b17": dict(commit="84766cdc", ref_rc=0.06),
    "0000006d--05e83bb04f": dict(commit="84766cdc", ref_rc=0.06),
    "0000006e--6ca3e014fd": dict(commit="84766cdc", ref_rc=0.06),
    "00000076--d0b7ea7e4d": dict(commit="e44b6cd3", ref_rc=0.12),
    "00000075--6c8687d5bd": dict(commit="08a5a706", ref_rc=0.12),
}
MODEL_LEAD_EXTRA = 0.1 + 0.05 + 0.025   # lat_smooth + frame_delay + action_delay (modeld), added to liveDelay


def simulate_setpoint(curv, v, active, ld, jerk_fc, ref_rc, jerk_clip=2.5):
    """Frame-exact replay of LatControlTorque.update's setpoint on the controlsState clock (one call per frame)."""
    n = len(curv)
    buf = np.zeros(100)  # deque maxlen 100, index -1 = newest
    bi = 0               # ring pointer: next write position
    a_j = DT / (1 / (2 * np.pi * jerk_fc) + DT)
    a_r = DT / (ref_rc + DT) if ref_rc > 0 else 1.0
    xj = 0.0; r1 = r2 = 0.0
    out = np.full(n, np.nan)
    for k in range(n):
        u = curv[k] * v[k] ** 2
        D = ld[k] + 0.1
        if not active[k]:
            buf[bi] = curv[k]; bi = (bi + 1) % 100
            xj = 0.0; r1 = r2 = u
            continue
        N = int(np.clip(D / DT, 1, 100))
        expected = buf[(bi - N) % 100] * v[k] ** 2
        buf[bi] = curv[k]; bi = (bi + 1) % 100
        rj = np.clip((u - expected) / max(D, DT), -jerk_clip, jerk_clip)
        xj = (1 - a_j) * xj + a_j * rj
        jj = np.clip(xj, -jerk_clip, jerk_clip)
        sp = expected + jj * D
        if ref_rc > 0:
            r1 = (1 - a_r) * r1 + a_r * sp
            r2 = (1 - a_r) * r2 + a_r * r1
            sp = r2
        out[k] = sp
    return out


def chain_H(f, ld, jerk_fc, ref_rc):
    """Linear (unclipped) discrete transfer function model->setpoint at frequencies f (Hz), constant v."""
    z = np.exp(1j * 2 * np.pi * np.asarray(f) * DT)
    D = ld + 0.1
    N = int(np.clip(D / DT, 1, 100))
    a_j = DT / (1 / (2 * np.pi * jerk_fc) + DT)
    Fj = a_j / (1 - (1 - a_j) / z)
    H = z ** (-N) + Fj * (1 - z ** (-N))
    if ref_rc > 0:
        a_r = DT / (ref_rc + DT)
        R = a_r / (1 - (1 - a_r) / z)
        H = H * R * R
    return H


def phase_lag(H, f):
    return -np.unwrap(np.angle(H)) / (2 * np.pi * np.asarray(f))


if __name__ == "__main__":
    f = np.array([0.1, 0.225, 0.45, 0.85, 1.77])
    for nm, ld, fc, rc in (("V282 (ld .20, 1.2 Hz, no ref)", 0.20, 1.2, 0.0), ("T64 (ld .30, 4 Hz, ref .06)", 0.30, 4.0, 0.06),
                           ("T5/T4 (ld .28, 1.2 Hz, ref .12)", 0.285, 1.2, 0.12)):
        H = chain_H(f, ld, fc, rc)
        print(nm, "lag s", np.round(phase_lag(H, f), 3), "|H|", np.round(np.abs(H), 3))
    # positive control: pure EMA rc=0.06 x2 -> DC group delay 0.12 s
    H = chain_H(np.array([0.02]), 0.2, 1e6, 0.06) / chain_H(np.array([0.02]), 0.2, 1e6, 0.0)
    print("control: 2x EMA rc .06 low-f lag", phase_lag(H, [0.02]))
