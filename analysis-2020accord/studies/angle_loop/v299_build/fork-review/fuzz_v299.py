"""Independent reviewer fuzz of the V299 fork _update_angle (commit 66780911)."""
import math, sys, time
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, r"C:\Users\dudei\Desktop\Projects\openpilots\raayyymond-StarPilot\StarPilot\opendbc_repo")
from opendbc.car.honda.tests.test_angle_v299 import make_cp, make_controller, FW_A16A, FW_A16B, FW_A160
from opendbc.car.honda.values import CarControllerParams as P, is_accord_eps_angle_loop_fw
from opendbc.car.lateral import get_max_angle_delta_vm

t0 = time.time()
# ---- is_angle_fw literal table
lits = {b"39990-TVA,A16A": True, b"39990-TVA,A16B": True, b"39990-TVA,A16A\x00\x00": True, b"39990-TVA,A16B\x00\x00": True,
        b"39990-TVA,A160": False, b"39990-TVA,A160\x00\x00": False, b"39990-TVA-A160\x00\x00": False, b"39990-TVA,A16a": False,
        b"39990-TVA,A16AB": False, b"39990-TVA,A16": False, b"39990-TVA,A16\x00\x00": False, b"39990-TVA,A16A ": False,
        b"\x0039990-TVA,A16A": False, b"39990-TVA,A16Z": True, b"39990-TVA,A16A\x00X": False}
for k, want in lits.items():
  got = is_accord_eps_angle_loop_fw(k)
  print("fw", k, got, "OK" if got == want else "MISMATCH")

def run(values, seed, n=60000):
  rng = np.random.default_rng(seed)
  with pytest.MonkeyPatch.context() as mp:
    CP = make_cp(mp, FW_A16B, True)
    cc = make_controller(mp, CP, values)
  p = cc.params
  theta = 0.0; des = 0.0; lat = False; prev_lat = False; prev_theta = 0.0
  viol = 0; worst = 0.0; edge_bad = 0; hold_bad = 0; maxdelta_bad = 0; statusset = set(); nan_crash = 0
  for i in range(n):
    v = float(rng.choice([0.0, 0.5, 3.0, 8.0, 11.75, 14.0, 17.5, 26.9, 40.0, rng.uniform(0, 40)]))
    if rng.random() < 0.02: lat = not lat
    # driver/wheel: random walk, with occasional large hand jumps (driver fighting), clamp to +-480
    theta = float(np.clip(theta + rng.normal(0, 2.0) + (rng.normal(0, 60) if rng.random() < 0.01 else 0), -480, 480))
    theta_q = math.floor(theta * 10) / 10.0  # 0.1 deg CAN quantum
    des = float(des + rng.normal(0, 5)) if rng.random() > 0.01 else float(rng.uniform(-600, 600))
    CC = SimpleNamespace(latActive=lat, enabled=bool(rng.random() < 0.9), actuators=SimpleNamespace(steeringAngleDeg=des))
    CS = SimpleNamespace(out=SimpleNamespace(steeringAngleDeg=theta_q, steeringRateDeg=float(rng.normal(0, 50)),
                         steeringTorque=float(rng.normal(0, 2000)), vEgoRaw=v,
                         cruiseState=SimpleNamespace(available=bool(rng.random() < 0.95))))
    last_before = cc.apply_angle_last
    ang, raw, st = cc._update_angle(CC, CS)
    statusset.add(st)
    if lat:
      em = float(np.interp(v, p.ANGLE_ERROR_MAX_BP, p.ANGLE_ERROR_MAX_V))
      e = abs(ang - theta_q)
      if e > em + 1e-9:
        if abs(theta_q) <= P.ANGLE_LIMITS.STEER_ANGLE_MAX:  # outside the 400-deg rail is a separate class
          viol += 1
        worst = max(worst, e - em)
      if abs(theta_q) <= 400 and raw != int(np.clip(math.floor(-10 * ang + 0.5), -4000, 4000)): hold_bad += 1
      if not prev_lat:  # rising edge: limiter must start from the wheel (previous frame's theta)
        md = min(get_max_angle_delta_vm(max(v, 1), cc.VM, p), p.ANGLE_LIMITS.MAX_ANGLE_RATE)
        if abs(prev_theta) <= 400 and abs(last_before - prev_theta) > 1e-9: edge_bad += 1
    else:
      if abs(theta_q) <= 400 and cc.apply_angle_last != theta_q: hold_bad += 1
      if raw not in (0, int(np.clip(math.floor(-10 * theta_q + 0.5), -4000, 4000))): hold_bad += 1
    prev_lat, prev_theta = lat, theta_q
  return dict(values=values, rate=p.ANGLE_LIMITS.MAX_ANGLE_RATE, clipV=p.ANGLE_ERROR_MAX_V, viol=viol, worst_beyond_clip=round(worst, 3),
              edge_bad=edge_bad, hold_bad=hold_bad, status=sorted(statusset),
              class_V=P.ANGLE_ERROR_MAX_V, class_rate=P.ANGLE_LIMITS.MAX_ANGLE_RATE)

for vals in ({}, {"AccordAngleMaxRate": 250.0, "AccordAngleClipScale": 1.6}):
  print(run(vals, 1))

# second controller in the same process must not inherit the first's mutated params (class leak)
with pytest.MonkeyPatch.context() as mp:
  CP = make_cp(mp, FW_A16B, True)
  a = make_controller(mp, CP, {"AccordAngleMaxRate": 250.0, "AccordAngleClipScale": 1.6})
  b = make_controller(mp, CP, {})
print("leak check: a", a.params.ANGLE_LIMITS.MAX_ANGLE_RATE, a.params.ANGLE_ERROR_MAX_V, "b", b.params.ANGLE_LIMITS.MAX_ANGLE_RATE, b.params.ANGLE_ERROR_MAX_V)
print("clip at 14 m/s s=1.0/1.6:", np.interp(14, P.ANGLE_ERROR_MAX_BP, P.ANGLE_ERROR_MAX_V), np.interp(14, a.params.ANGLE_ERROR_MAX_BP, a.params.ANGLE_ERROR_MAX_V))

# NaN desired (pre-existing class check)
with pytest.MonkeyPatch.context() as mp:
  CP = make_cp(mp, FW_A16B, True); c = make_controller(mp, CP, {})
CSn = SimpleNamespace(out=SimpleNamespace(steeringAngleDeg=1.0, steeringRateDeg=0.0, steeringTorque=0.0, vEgoRaw=10.0, cruiseState=SimpleNamespace(available=True)))
try:
  r = c._update_angle(SimpleNamespace(latActive=True, enabled=True, actuators=SimpleNamespace(steeringAngleDeg=float("nan"))), CSn)
  print("nan desired ->", r)
except Exception as ex:
  print("nan desired raises", type(ex).__name__, ex)
print("elapsed", round(time.time() - t0, 1))
