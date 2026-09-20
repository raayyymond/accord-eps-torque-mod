"""Extract the per-message timing chain of one route from raw rlogs (streamed, one segment at a time).

Per route npz in _cache/<route>_chain.npz:
  can batches carrying 0x14A (src 1): t, angle(raw int16), rate(raw int16)
  can batches carrying our 0xE4 TX echo (src 129): t, int16 torque
  carState: t, angle, rate, vEgo, pressed
  controlsState: t, curvature, torque output, active
  carControl: t, actuators.torque, latActive
  sendcan 0xE4 bus 1: t, int16 torque
usage: python s01_chain_extract.py <counter--hash> [max_segs]
"""
import sys, glob, os
from pathlib import Path
import numpy as np
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
from rlog_parse import read_messages

route = sys.argv[1]; maxs = int(sys.argv[2]) if len(sys.argv) > 2 else 999
segs = sorted(glob.glob(str(KIT / "analysis-2020accord" / "rlogs" / f"75604b0a432fdc89_{route}--*--rlog.zst")),
              key=lambda p: int(os.path.basename(p).split("--")[2]))[:maxs]
A = {k: [] for k in ["t14a", "a14a", "r14a", "tech", "vech", "tcst", "sa", "sr", "v", "pr",
                     "tcs", "curv", "out", "act", "tcc", "tq", "lat", "tsc", "vsc"]}
i16 = lambda d, o: int.from_bytes(d[o:o + 2], "big", signed=True)
for p in segs:
    for e in read_messages(p):
        try:
            w = e.which()
        except Exception:
            continue
        t = e.logMonoTime / 1e9
        if w == "can":
            for m in e.can:
                if m.address == 0x14A and m.src == 1:
                    d = bytes(m.dat); A["t14a"].append(t); A["a14a"].append(i16(d, 0)); A["r14a"].append(i16(d, 2))
                elif m.address == 0xE4 and m.src == 129:
                    d = bytes(m.dat); A["tech"].append(t); A["vech"].append(i16(d, 0))
        elif w == "sendcan":
            for m in e.sendcan:
                if m.address == 0xE4 and m.src == 1:
                    d = bytes(m.dat); A["tsc"].append(t); A["vsc"].append(i16(d, 0))
        elif w == "carState":
            c = e.carState
            A["tcst"].append(t); A["sa"].append(c.steeringAngleDeg); A["sr"].append(c.steeringRateDeg)
            A["v"].append(c.vEgo); A["pr"].append(float(c.steeringPressed))
        elif w == "controlsState":
            cs = e.controlsState
            try:
                ts = cs.lateralControlState.torqueState; o = ts.output; a = float(ts.active)
            except Exception:
                o, a = np.nan, 0.0
            A["tcs"].append(t); A["curv"].append(cs.curvature); A["out"].append(o); A["act"].append(a)
        elif w == "carControl":
            cc = e.carControl
            A["tcc"].append(t); A["tq"].append(cc.actuators.torque); A["lat"].append(float(cc.latActive))
    print(route, os.path.basename(p), len(A["tcst"]), flush=True)
D = {k: np.asarray(v, dtype=np.float64) for k, v in A.items()}
# rlog is not strictly time-ordered: sort every stream by its own time
for tk, ks in [("t14a", ["a14a", "r14a"]), ("tech", ["vech"]), ("tcst", ["sa", "sr", "v", "pr"]),
               ("tcs", ["curv", "out", "act"]), ("tcc", ["tq", "lat"]), ("tsc", ["vsc"])]:
    o = np.argsort(D[tk], kind="stable")
    for k in [tk] + ks:
        D[k] = D[k][o]
np.savez_compressed(Path(__file__).resolve().parent / "_cache" / f"{route}_chain.npz", **D)
print("done", route)
