# -*- coding: utf-8 -*-
"""Extract per-window cross-spectra for the loop identification.  One route at a time (RAM).

WINDOWS: laterally engaged, hands OFF, speed in [vmin,vmax), contiguous (no clock gap), at least
`WIN` seconds long.  Each window contributes Hann/Welch blocks of `NPS` samples at 50% overlap.

SIGNALS (all on the controlsState clock):
  r   = torqueState.desiredLateralAccel   -- the SHAPED setpoint the loop actually chases [m/s^2]
  y   = torqueState.actualLateralAccel    -- the loop's OWN measurement                   [m/s^2]
  e   = r - y                             -- the fork's `error` BEFORE lsf inflation/notch
  el  = torqueState.error                 -- the logged (inflated, notched) error
  ufb = (p+i)/LAF                         -- the PID's contribution to the command        [torque]
  uff = f/LAF                             -- the feedforward term (plant FF + friction + the
                                             torque builds' inner rate loop and observer) [torque]
  u   = ufb+uff                           -- the command before the +/-1 clip             [torque]
  sa  = carState.steeringAngleDeg, sr = carState.steeringRateDeg
  yp  = livePose yaw * v                  -- an INDEPENDENT achieved lateral accel
  x   = desiredCurvature * v^2            -- the MODEL's desired lateral accel (the goal's X)

usage: python u1_extract.py [vmin vmax winlen nps tag]
out:   spec_<tag>.npz
"""
import sys
import numpy as np
import ulib as U
import uspec as SP

VMIN = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
VMAX = float(sys.argv[2]) if len(sys.argv) > 2 else 99.0
WIN = float(sys.argv[3]) if len(sys.argv) > 3 else 41.0
NPS = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
TAG = sys.argv[5] if len(sys.argv) > 5 else "hi"
HANDS = sys.argv[6] if len(sys.argv) > 6 else "off"

NAMES = ["r", "y", "e", "el", "ufb", "uff", "u", "sa", "sr", "yp", "x"]
rec = {"f": None, "route": [], "fam": [], "nblk": [], "sec": [], "v": [], "rrms": [], "arms": [],
       "spec": [], "satfrac": []}

for rt in U.FAMILY:
    S = U.load(rt)
    m = U.usable(S, VMIN, VMAX, hands=HANDS)
    segs = U.segments(S, m, WIN)
    n_ok = 0
    for a, b in segs:
        sl = slice(a, b)
        sig = dict(r=S["r"][sl], y=S["y"][sl], e=(S["r"] - S["y"])[sl], el=S["e"][sl],
                   ufb=S["ufb"][sl], uff=S["uff"][sl], u=S["u"][sl],
                   sa=S["sa"][sl], sr=S["sr"][sl], yp=S["la_pose"][sl], x=S["model"][sl])
        out = SP.window_spectra(sig, NPS)
        if out is None:
            continue
        f, sp, nb = out
        rec["f"] = f
        rec["route"].append(rt); rec["fam"].append(S["fam"])
        rec["nblk"].append(nb); rec["sec"].append((b - a) / U.FS)
        rec["v"].append(float(np.median(S["v"][sl])))
        # per-window reference amplitude in the two analysis bands (for amplitude matching)
        df = f[1] - f[0]
        for nm, (f1, f2) in (("rrms", (0.15, 0.30)), ("arms", (0.60, 1.20))):
            s = (f >= f1) & (f < f2)
            rec[nm].append(float(np.sqrt(max(np.real(sp[("r", "r")][s]).sum() * df, 0.0))))
        rec["satfrac"].append(float(S["sat"][sl].mean()))
        rec["spec"].append(sp)
        n_ok += 1
    print(f"{U.SHORT[rt]:<10} {S['fam']:<8} windows {n_ok:3d} / segs {len(segs):3d}", flush=True)
    del S

keys = sorted({k for sp in rec["spec"] for k in sp})
arr = {f"S_{a}_{b}": np.array([sp[(a, b)] for sp in rec["spec"]]) for a, b in keys}
np.savez_compressed(f"spec_{TAG}.npz", f=rec["f"], route=np.array(rec["route"]), fam=np.array(rec["fam"]),
                    nblk=np.array(rec["nblk"]), sec=np.array(rec["sec"]), v=np.array(rec["v"]),
                    rrms=np.array(rec["rrms"]), arms=np.array(rec["arms"]),
                    satfrac=np.array(rec["satfrac"]), names=np.array(NAMES), **arr)
print(f"wrote spec_{TAG}.npz  windows={len(rec['spec'])}  df={rec['f'][1]-rec['f'][0]:.4f} Hz  nps={NPS}")
