# -*- coding: utf-8 -*-
"""Planner-vs-actuator split of the following oscillation, from the long_pingpong_read.py caches (run that first).

usage: python long_pingpong_planner_vs_actuator.py <route> [<route> ...] [--trace]

For lead-following (engaged, lead tracked, v > 2 m/s), in the 2-8 s ping-pong band (0.125-0.5 Hz):
  * rms of the planner's longitudinalPlan.aTarget, of carControl.actuators.accel (what is sent), of carState.aEgo
  * rms of the TRACKING error aEgo - accel(t - lag) with the cross-correlation lag: if the band energy lives in aTarget
    itself the PLANNER oscillates; if aTarget is quiet and only aEgo / the tracking error carry it, the ACTUATOR does.
  * coherence-like correlation between aTarget and aEgo in the band
  * gas<->brake request switches per minute (ACC_CONTROL BRAKE_REQUEST), and gas-on share
  * the accelerationJerk value split by aEgo sign (confirms the 125/375 switch acts on the band)
--trace prints a 2 Hz trace of every slow/stopped-lead episode (vLead < 3 m/s, dRel < 40 m).
"""
import os, sys, json, time
import numpy as np
from scipy.signal import butter, sosfiltfilt

T0 = time.time()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import long_pingpong_read as R  # noqa: E402


def band(x, fs, lo=1 / 8.0, hi=1 / 2.0):
  return sosfiltfilt(butter(2, [lo, hi], btype="band", fs=fs, output="sos"), x - np.mean(x))


def analyse(route, trace):
  D, _, _ = R.load_route(route)
  cs, cc, sd, rs, sp, gas, lp = (D[k] for k in ("cs", "cc", "sd", "rs", "sp", "gas", "lp"))
  t = cs[:, 0]                                           # 100 Hz grid
  v, a = cs[:, 1], cs[:, 2]
  long_ = R.hold(cc[:, 0], cc[:, 1], t) == 1
  cmd = R.hold(cc[:, 0], cc[:, 2], t)
  exp = R.hold(sd[:, 0], sd[:, 1], t)
  lead = R.hold(rs[:, 0], rs[:, 1], t) == 1
  dRel, vLead = R.hold(rs[:, 0], rs[:, 2], t), R.hold(rs[:, 0], rs[:, 3], t)
  trk = R.hold(sp[:, 0], sp[:, 4], t) == 1
  aj = R.hold(sp[:, 0], sp[:, 5], t)
  aT = R.hold(lp[:, 0], lp[:, 1], t)
  brk = R.hold(gas[:, 0], gas[:, 3], t) if len(gas) else np.full(len(t), np.nan)
  gcmd = R.hold(gas[:, 0], gas[:, 1], t) if len(gas) else np.full(len(t), np.nan)
  out = {"route": route}
  fol = long_ & lead & trk & (v > 2.0) & np.isfinite(aT) & np.isfinite(cmd)
  segs = R.runs(fol & (exp == 0), 2000)                  # chill, >= 20 s
  if segs:
    bt, bc, ba, be = [], [], [], []
    for s, e in segs:
      bt.append(band(aT[s:e], 100.0)); bc.append(band(cmd[s:e], 100.0)); ba.append(band(a[s:e], 100.0))
    T, C, A = (np.concatenate(x) for x in (bt, bc, ba))
    # lag cmd -> aEgo in the band
    lags = np.arange(0, 151)
    num = np.zeros(len(lags))
    for c_, a_ in zip(bc, ba):
      num += np.array([np.dot(c_[:len(c_) - k], a_[k:]) for k in lags])
    k = int(np.argmax(num))
    E = np.concatenate([a_[k:] - c_[:len(c_) - k] for c_, a_ in zip(bc, ba)])
    rms = lambda x: float(np.sqrt(np.mean(x * x)))
    out.update(chill_follow_min=round(sum(e - s for s, e in segs) / 6000, 2),
               band_rms_aTarget=round(rms(T), 3), band_rms_cmd=round(rms(C), 3), band_rms_aEgo=round(rms(A), 3),
               band_rms_track_err=round(rms(E), 3), lag_ms=int(lags[k] * 10),
               corr_aTarget_aEgo=round(float(np.corrcoef(T, A)[0, 1]), 2),
               corr_cmd_aEgo_lagged=round(float(np.corrcoef(np.concatenate([c_[:len(c_) - k] for c_ in bc]),
                                                           np.concatenate([a_[k:] for a_ in ba]))[0, 1]), 2))
    V = np.concatenate([band(v[s:e], 100.0) for s, e in segs])
    DR = np.concatenate([band(dRel[s:e], 100.0) for s, e in segs])
    VL = np.concatenate([band(vLead[s:e], 100.0) for s, e in segs])
    out.update(band_rms_vEgo=round(rms(V), 3), band_rms_dRel=round(rms(DR), 2), band_rms_vLead=round(rms(VL), 3))
    m = fol & (exp == 0)
    mins = m.sum() / 6000
    # brake pulses inside chill following: duration of each BRAKE_REQUEST=1 run, and the commanded accel during them
    bk = (brk == 1) & m
    pulses = R.runs(bk, 1)
    if pulses:
      d = np.array([(e - s) / 100 for s, e in pulses])
      cm = np.array([np.median(cmd[s:e]) for s, e in pulses])
      out.update(brake_pulses=len(pulses), brake_pulse_s_p50=round(float(np.median(d)), 1),
                 brake_pulse_s_p90=round(float(np.percentile(d, 90)), 1),
                 brake_pulse_cmd_p50=round(float(np.median(cm)), 2),
                 brake_pulses_cmd_above_m03=round(float(np.mean(cm > -0.3)), 2))
    sw = np.count_nonzero((np.diff(brk) != 0) & m[1:] & m[:-1])
    out.update(gas_brake_switch_pm=round(sw / mins, 1), brake_share=round(float(np.nanmean(brk[m])), 2),
               gas_on_share=round(float(np.nanmean(gcmd[m] > 0)), 2),
               aj_when_aEgo_pos=float(np.nanmedian(aj[m & (a >= 0)])), aj_when_aEgo_neg=float(np.nanmedian(aj[m & (a < 0)])))
  # slow / stopped lead traces
  slow = long_ & lead & (vLead < 3.0) & (dRel < 40.0)
  eps = R.runs(slow, 500)
  out["slow_lead_s"] = round(slow.sum() / 100, 1)
  out["slow_lead_blended_share"] = round(float(np.nanmean(exp[slow])), 2) if slow.sum() else None
  if trace:
    for s, e in eps:
      print(f"--- {route} slow-lead episode at {(t[s]-t[0])/60:.2f} min, {(t[e-1]-t[s]):.1f} s")
      print("   t_s   v    aEgo  aTgt  cmd   dRel  vLead blended brake gas")
      for i in range(s, e, 50):
        print(f"  {t[i]-t[s]:5.1f} {v[i]:4.1f} {a[i]:+5.2f} {aT[i]:+5.2f} {cmd[i]:+5.2f} {dRel[i]:5.1f} {vLead[i]:5.2f}"
              f"   {int(exp[i])}      {int(brk[i]) if np.isfinite(brk[i]) else -1}  {int(gcmd[i]) if np.isfinite(gcmd[i]) else -1}")
  return out


if __name__ == "__main__":
  routes = [x for x in sys.argv[1:] if not x.startswith("--")]
  res = [analyse(r, "--trace" in sys.argv) for r in routes]
  for r in res:
    print(json.dumps(r))
  print(f"wall {time.time()-T0:.1f} s")
