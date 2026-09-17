"""Extract a route into one npz for the V282-vs-torque-mode comparison.

Keyed on counter--hash (counters collide across device resets). Superset of rev64-goal's ident schema,
plus the signals the event analysis needs: yaw rate, IMU yaw, driver/EPS torque, the CAN command, and the
live vehicle parameters (roll / steer ratio) so angle_des can be rebuilt exactly.

usage:  python build_cache.py 0000006c--2bc842dbac [more routes...]
out:    analysis-2020accord/_scratch/cache/v282ref/<counter>--<hash>.npz
"""
import sys, os, glob
from pathlib import Path
import numpy as np

KIT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
from rlog_parse import read_messages  # noqa: E402

RLOGS = KIT / "analysis-2020accord" / "rlogs"
OUT = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"
OUT.mkdir(parents=True, exist_ok=True)

KEYS = ['t_cs', 'cs_active', 'cs_err', 'cs_p', 'cs_i', 'cs_f', 'cs_out', 'cs_sat', 'cs_la_act', 'cs_la_des',
        'cs_la_jerk', 'cs_des_curv', 'cs_curv', 'cs_errrate',
        't_cst', 'vego', 'aego', 'sa_deg', 'sr_deg', 'spress', 'storque', 'storque_eps', 'cs_yaw', 'sa_off',
        't_cc', 'lat_active', 'cc_enabled', 'cc_curv_cmd', 'cc_torque', 'cc_tq_can', 'cc_curv_now',
        't_lp', 'roll', 'sR', 'stiff', 'aoff',
        't_lt', 'laf_f', 'lao_f', 'fric_f',
        't_ld', 'ld_delay',
        't_pose', 'pose_wz',
        't_e4', 'e4_cmd', 'e4_req']


def seg_no(p):
    return int(os.path.basename(p).split("--")[2])


def extract(route):
    segs = sorted(glob.glob(str(RLOGS / f"75604b0a432fdc89_{route}--*--rlog.zst")), key=seg_no)
    if not segs:
        print(f"{route}: no segments", flush=True)
        return
    A = {k: [] for k in KEYS}
    for p in segs:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            t = evt.logMonoTime / 1e9
            if w == 'controlsState':
                cs = evt.controlsState
                try:
                    ts = cs.lateralControlState.torqueState
                except Exception:
                    continue
                A['t_cs'].append(t); A['cs_active'].append(float(ts.active))
                A['cs_err'].append(ts.error); A['cs_p'].append(ts.p); A['cs_i'].append(ts.i)
                A['cs_f'].append(ts.f); A['cs_out'].append(ts.output); A['cs_sat'].append(float(ts.saturated))
                A['cs_la_act'].append(ts.actualLateralAccel); A['cs_la_des'].append(ts.desiredLateralAccel)
                A['cs_la_jerk'].append(ts.desiredLateralJerk); A['cs_errrate'].append(ts.errorRate)
                A['cs_des_curv'].append(cs.desiredCurvature); A['cs_curv'].append(cs.curvature)
            elif w == 'carState':
                c = evt.carState
                A['t_cst'].append(t); A['vego'].append(c.vEgo); A['aego'].append(c.aEgo)
                A['sa_deg'].append(c.steeringAngleDeg); A['sr_deg'].append(c.steeringRateDeg)
                A['spress'].append(float(c.steeringPressed)); A['storque'].append(c.steeringTorque)
                A['storque_eps'].append(c.steeringTorqueEps); A['cs_yaw'].append(c.yawRate)
                A['sa_off'].append(c.steeringAngleOffsetDeg)
            elif w == 'carControl':
                cc = evt.carControl
                A['t_cc'].append(t); A['lat_active'].append(float(cc.latActive))
                A['cc_enabled'].append(float(cc.enabled)); A['cc_curv_now'].append(cc.currentCurvature)
                a = cc.actuators
                A['cc_curv_cmd'].append(a.curvature); A['cc_torque'].append(a.torque)
                A['cc_tq_can'].append(a.torqueOutputCan)
            elif w == 'liveParameters':
                d = evt.liveParameters
                A['t_lp'].append(t); A['roll'].append(d.roll); A['sR'].append(d.steerRatio)
                A['stiff'].append(d.stiffnessFactor); A['aoff'].append(d.angleOffsetDeg)
            elif w == 'liveTorqueParameters':
                d = evt.liveTorqueParameters
                A['t_lt'].append(t); A['laf_f'].append(d.latAccelFactorFiltered)
                A['lao_f'].append(d.latAccelOffsetFiltered); A['fric_f'].append(d.frictionCoefficientFiltered)
            elif w == 'liveDelay':
                try:
                    A['t_ld'].append(t); A['ld_delay'].append(evt.liveDelay.lateralDelay)
                except Exception:
                    A['t_ld'].pop()
            elif w == 'livePose':
                try:
                    A['t_pose'].append(t); A['pose_wz'].append(evt.livePose.angularVelocityDevice.z)
                except Exception:
                    A['t_pose'].pop()
            elif w == 'sendcan':
                for m in evt.sendcan:
                    if m.address == 0xE4 and m.src == 1:   # openpilot sends STEERING_CONTROL on bus 1 here
                        d = bytes(m.dat)
                        if len(d) >= 3:
                            A['t_e4'].append(t)
                            A['e4_cmd'].append(float(int.from_bytes(d[0:2], 'big', signed=True)))
                            A['e4_req'].append(float((d[2] >> 7) & 1))
        print(f"   {route} seg {seg_no(p)}  cs={len(A['t_cs'])}", flush=True)
    D = {k: np.asarray(v, dtype=np.float64) for k, v in A.items() if len(v)}
    f = OUT / f"{route}.npz"
    np.savez_compressed(f, **D)
    span = (D['t_cs'][-1] - D['t_cs'][0]) if 't_cs' in D else 0
    eng = float(D['cs_active'].sum() / 100.0) if 'cs_active' in D else 0
    print(f"{route}: wrote {f.name} {f.stat().st_size/1e6:.1f} MB, span {span:.0f} s, active ~{eng:.0f} s, "
          f"keys missing: {[k for k in KEYS if k not in D]}", flush=True)


if __name__ == "__main__":
    for r in sys.argv[1:]:
        extract(r)
