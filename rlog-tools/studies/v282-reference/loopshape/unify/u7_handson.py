# -*- coding: utf-8 -*-
"""THE STRONGEST CONTROL THAT EXISTS HERE: hands-ON frames -- and the sensor floor.

u0_census settled that there are ZERO seconds of longitudinal-only engaged driving at 8-22 m/s, so a
lateral-loop-OPEN control does not exist in this corpus.  Hands-on frames are the fallback: the
driver's arms add mechanical impedance at the wheel (and the fork freezes the integrator and the
observer while steeringPressed).  They are SHORT -- the census found not one run of 10 s at 8-22 m/s
outside route 39 -- so this uses 2.56 s blocks and a block bootstrap, and reports how much time each
cell actually has.

Also measured here: the steering-angle QUANTISATION floor, because the V282 family's uncommanded
wheel motion above ~2.5 Hz sits on a flat floor and the comparison must know whether that floor is
the car or the sensor.

out: U7-OUT.txt, u7.json
"""
import json
import numpy as np
from scipy import signal
import ulib as U

FS = 100.0
BLK = 128
BANDS = [(0.6, 1.2), (1.2, 2.4), (1.8, 3.5), (2.4, 4.0)]
VB = [(5, 15), (15, 22), (22, 32)]


def band_rms_blocks(x, i0, i1, f1, f2):
    sos = signal.butter(4, [f1, f2], btype="band", fs=FS, output="sos")
    seg = np.nan_to_num(x[i0:i1])
    if len(seg) < BLK + 64:
        return []
    y = signal.sosfiltfilt(sos, seg)
    n = len(y) // BLK
    return [float(np.sqrt(np.mean(y[k * BLK:(k + 1) * BLK] ** 2))) for k in range(n)]


rows = {}
quant = {}
for rt in U.FAMILY:
    S = U.load(rt)
    # --- quantisation floor of steeringAngleDeg: the smallest non-zero step actually seen
    import v282cmp as V
    RAW = np.load(V.CACHE / f"{rt}.npz", allow_pickle=True)["sa_deg"]   # RAW carState, un-interpolated
    d = np.diff(RAW)
    nz = np.abs(d[np.abs(d) > 1e-9])
    q = float(np.percentile(nz, 1)) if len(nz) else float("nan")
    qmin = float(np.min(nz)) if len(nz) else float("nan")
    # floor an ideal uniform quantiser would leave in a band, RMS = q/sqrt(12) spread over 0-50 Hz
    quant[rt] = dict(step_min=qmin, step_p1=q,
                     floor_full=float(qmin / np.sqrt(12.0)),
                     floor_1p2_2p4=float(qmin / np.sqrt(12.0) * np.sqrt(1.2 / 50.0)))
    r = {}
    for hands in ("off", "on"):
        m = U.usable(S, 0, 99, hands=hands)
        for lo, hi in VB:
            mm = m & (S["v"] >= lo) & (S["v"] < hi)
            segs = U.segments(S, mm, BLK / FS + 0.6)
            for f1, f2 in BANDS:
                vals = []
                for a, b in segs:
                    vals += band_rms_blocks(S["sa"], a, b, f1, f2)
                r[f"{hands}_{lo}_{f1}"] = vals
    rows[rt] = dict(fam=S["fam"], data={k: v for k, v in r.items()})
    print(f"{U.SHORT[rt]:<9} {S['fam']:<8} q_min {qmin:.4f} deg  "
          + "  ".join(f"{lo}: on {len(r[f'on_{lo}_1.2'])} blk / off {len(r[f'off_{lo}_1.2'])} blk" for lo, _ in VB),
          flush=True)
    del S

rng = np.random.default_rng(7)


def boot_ratio(on, off, n=2000):
    if len(on) < 5 or len(off) < 5:
        return (np.nan, np.nan, np.nan)
    r = np.median(on) / np.median(off)
    bs = [np.median(rng.choice(on, len(on))) / np.median(rng.choice(off, len(off))) for _ in range(n)]
    return (r, float(np.percentile(bs, 5)), float(np.percentile(bs, 95)))


L = ["HANDS-ON vs HANDS-OFF, same route, same speed bin: median 2.56 s block RMS of the steering",
     "angle in band (deg).  A ratio below 1 means the driver's hands REMOVED wheel motion.",
     "CONFOUNDS, stated: hands-on also freezes the PID integrator and the disturbance observer, and",
     "the driver is himself injecting torque -- so a ratio below 1 is a lower bound on the damping",
     "effect and a ratio above 1 does not cleanly refute it.", ""]
for f1, f2 in BANDS:
    L.append(f"--- band {f1}-{f2} Hz")
    L.append(f"{'route':<9}{'fam':<8}" + "".join(f"{f'{lo}-{hi} m/s':>26}" for lo, hi in VB))
    for rt, d in rows.items():
        cells = []
        for lo, hi in VB:
            on = d["data"].get(f"on_{lo}_{f1}", [])
            off = d["data"].get(f"off_{lo}_{f1}", [])
            r, a, b = boot_ratio(np.array(on), np.array(off))
            cells.append(f"{r:>8.2f}[{a:.2f},{b:.2f}]n{len(on):<3d}" if np.isfinite(r) else f"{'-':>26}")
        L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}" + "".join(cells))
    # family pool
    for FM in ("V282", "V282old", "TORQ"):
        cells = []
        for lo, hi in VB:
            on = np.concatenate([d["data"].get(f"on_{lo}_{f1}", []) for d in rows.values() if d["fam"] == FM] or [[]])
            off = np.concatenate([d["data"].get(f"off_{lo}_{f1}", []) for d in rows.values() if d["fam"] == FM] or [[]])
            r, a, b = boot_ratio(np.asarray(on), np.asarray(off))
            cells.append(f"{r:>8.2f}[{a:.2f},{b:.2f}]n{len(on):<3d}" if np.isfinite(r) else f"{'-':>26}")
        L.append(f"{'POOLED':<9}{FM:<8}" + "".join(cells))
    L.append("")

L.append("STEERING-ANGLE QUANTISATION -- is the V282 family's flat high-frequency floor the car or")
L.append("the sensor?  q_min is the smallest non-zero frame-to-frame step in the whole route.")
L.append(f"{'route':<9}{'fam':<8}{'q_min deg':>11}{'q_p1':>9}{'ideal floor 1.2-2.4 Hz deg':>28}")
for rt, q in quant.items():
    L.append(f"{U.SHORT[rt]:<9}{U.FAMILY[rt]:<8}{q['step_min']:>11.4f}{q['step_p1']:>9.4f}"
             f"{q['floor_1p2_2p4']:>28.4f}")
json.dump(dict(quant=quant, rows={k: {kk: (vv if kk != 'data' else {a: len(b) for a, b in vv.items()})
                                     for kk, vv in v.items()} for k, v in rows.items()}),
          open("u7.json", "w"), indent=1, default=float)
txt = "\n".join(L)
open("U7-OUT.txt", "w").write(txt)
print(txt)
