# -*- coding: utf-8 -*-
"""build_v299_fork_fixture.py -- the route-79 fixture for the fork's V299 tests
(opendbc_repo/opendbc/car/honda/tests/data/accord_angle_r79_v299.npz).  Three parts, all RECORDED on route 79
(75604b0a432fdc89_00000079--a1f5d2a272, V298 A16A, fork Dom 2712e1336):

  lim_*   the limiter inputs and the 0xE4 field the car sent, on the fork's frame axis, with the card-loop pairing of
          v298_flight/m4_common.limiter_reconstruct (carOutput row i <- carState row i-1, carControl jc-1).  Kept: every
          latActive frame plus the one frame before each latActive run (the limiter's seed: lateral off returns the
          wheel).  Integers where the parser produced integers: steeringAngleDeg = k * -0.1 (DBC factor), rate and hand
          torque integer counts -- so the test rebuilds the float64 the controller saw, not the float32 the log kept.
  e1ab_*  segment 0's bus-1 0x1AB frames (t, 3 bytes) and the bus-1 CAN event times (the parser's clock), which hold
          the route's only two 0x1AB gaps > 100 ms (1.23 s and 0.48 s at t 29-31 s).
  bar_*   the 31,987 frames of rev_bar_sign.py's mask (latActive, not pressed, |tap| >= 10, |today's bar| >= 0.1,
          v > 3): the 0x1AB frame there (3 bytes) and the sign of today's angle-mode bar.
Inputs: _scratch/cache/v280/r79_fork.npz, r79_a1f5d2_al.npz, _scratch/v299_fork/r79_1ab.npz (extract_r79_1ab.py).
Wall printed (< 30 s)."""
import json, sys, time
from pathlib import Path
import numpy as np
T0 = time.time()
KIT = Path(__file__).resolve().parents[5]
C = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
FORK = Path(r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot")
OUT = FORK / "opendbc_repo" / "opendbc" / "car" / "honda" / "tests" / "data" / "accord_angle_r79_v299.npz"

F = dict(np.load(C / "r79_fork.npz"))
W = np.load(C / "r79_a1f5d2_al.npz")
X = np.load(KIT / "analysis-2020accord" / "_scratch" / "v299_fork" / "r79_1ab.npz")
cpj = json.loads(str(F["carparams_json"]))
meta = json.loads(str(F["meta_json"]))
assert meta["fork_commit"] == "2712e1336" and cpj["steerControlType"] == "angle"

# ---- limiter frames (m4_common.limiter_reconstruct's pairing)
t = F["t_co"]; n = len(t)
jc = np.clip(np.searchsorted(F["t_cc"], t, side="right") - 2, 0, len(F["t_cc"]) - 1)
sh = lambda x: np.r_[x[:1], x[:-1]]  # noqa: E731
lat = F["cc_latActive"][jc].astype(bool)
ena = F["cc_enabled"][jc].astype(bool)
des = F["cc_ang"][jc].astype(np.float32)
assert np.array_equal(des.astype(np.float64), F["cc_ang"][jc]), "carControl angle is not float32"
ang = sh(F["cs_ang"]); rate = sh(F["cs_rate"]); tq = sh(F["cs_tq"]); vraw = sh(F["cs_vegoraw"]).astype(np.float32)
avail = sh(F["cs_cr_avail"]).astype(bool)
k = np.round(ang / -0.1).astype(np.int64)
assert np.array_equal(np.float32(k * -0.1), ang.astype(np.float32)), "steeringAngleDeg is not raw x -0.1"
assert np.array_equal(np.round(rate), rate) and np.array_equal(np.round(tq), tq)
assert np.abs(k).max() < 32768 and np.abs(rate).max() < 32768 and np.abs(tq).max() < 32768
rec = F["co_tqcan"]
assert np.array_equal(np.round(rec), rec)
start = lat & ~np.r_[False, lat[:-1]]
keep = lat | np.r_[start[1:], False]
assert not keep[0] or not lat[0]
flags = (lat.astype(np.uint8) | (ena.astype(np.uint8) << 1) | (avail.astype(np.uint8) << 2))[keep]
# ---- the recorded 0xE4 field = the published torqueOutputCan (angle_raw as sent) on latActive frames
co_raw = np.floor(-10.0 * F["co_ang"] + 0.5)
print(f"latActive {lat.sum()}, runs {start.sum()}, kept {keep.sum()}; co_tqcan == raw(co_ang) on latActive "
      f"{np.mean(rec[lat] == co_raw[lat]) * 100:.3f} %")

# ---- segment-0 0x1AB frames and bus-1 clock
t1 = X["t_ns"]; ev = X["seg0_bus1_event_ns"]
s0 = t1 <= ev[-1]
gaps = np.diff(t1[s0]) * 1e-6
print(f"seg0 0x1AB frames {s0.sum()}, gaps > 100 ms {(gaps > 100).sum()} ({np.sort(gaps)[-2:].round(1).tolist()} ms); bus-1 events {len(ev)}")

# ---- the bar-sign frames (rev_bar_sign.py's mask, same frames)
raw10 = ((W["b0"] & 3) << 8) | W["b1"]
s10 = np.where(raw10 & 0x200, -1, 1) * (raw10 & 0x1FF)
tcs, v, press = F["t_cs"], F["cs_vego"], F["cs_press"].astype(bool)
latc = np.interp(tcs, F["t_cc"], F["cc_latActive"].astype(float)) > 0.5
idx = np.clip(np.searchsorted(W["t1ab"], tcs), 0, len(W["t1ab"]) - 1)
tap = s10[idx]
dk = np.interp(tcs, F["t_ctl"], F["ctl_dcurv"]); roll = np.interp(tcs, F["t_lp"], F["lp_roll"])
cur = np.clip((dk * v**2 - roll * 9.81 * np.interp(v, [5, 15], [0, 1])) / 0.3247, -1, 1)
m = latc & ~press & (np.abs(tap) >= 10) & (np.abs(cur) >= 0.1) & (v > 3)
assert np.allclose(W["t1ab"], t1 * 1e-9) and np.array_equal(W["b0"], X["b"][:, 0])
print(f"bar frames {m.sum()}; sign(tap) == sign(today's bar) {np.mean(np.sign(tap[m]) == np.sign(cur[m])):.3f}")

OUT.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(
  OUT,
  lim_k_ang=k[keep].astype(np.int16), lim_rate=rate[keep].astype(np.int16), lim_tq=tq[keep].astype(np.int16),
  lim_vraw=vraw[keep], lim_des=des[keep], lim_flags=flags, lim_rec_raw=rec[keep].astype(np.int16),
  e1ab_t_ns=t1[s0], e1ab_b=X["b"][s0], e1ab_bus1_ev_ns=ev,
  bar_b=X["b"][idx[m]], bar_today_sign=np.sign(cur[m]).astype(np.int8),
  cp_vm=np.array([cpj["mass"], cpj["wheelbase"], cpj["centerToFront"], cpj["tireStiffnessFront"], cpj["tireStiffnessRear"],
                  cpj["steerRatio"], cpj["rotationalInertia"]]),
  source=np.array("route 75604b0a432fdc89_00000079--a1f5d2a272 (V298 A16A, fork Dom 2712e1336); "
                  "kit analysis-2020accord/studies/angle_loop/v299_design/fork/build_v299_fork_fixture.py"),
)
print(f"wrote {OUT} {OUT.stat().st_size} bytes; wall {time.time() - T0:.2f} s")
