"""Extract, per route, the signals the straight-road weave study needs that the v282ref cache lacks.
modelV2 (20 Hz): near lane lines y at x = 0 / 10 / 20 m, their probs, plan position y at x = 10 m, action
desiredCurvature, laneChangeState.  starpilotLateralState (100 Hz): observer torque, frozen, ff.  initData toggles.
Parsed with the FORK schema (forkparse.py) because the kit schema's slot @137 is a different struct.
out: ./cache/<counter>--<hash>_fsr.npz
"""
import sys, glob, os, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from forkparse import read_messages
RL = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs"
OUT = HERE / "cache"; OUT.mkdir(exist_ok=True)
PK = ("Accord", "Steer", "LatSmooth", "UseAutoSteerDelay", "ForceTorqueController", "HondaLateral", "AdvancedLateralTune")

def seg(p): return int(os.path.basename(p).split("--")[2])

def extract(route):
    A = {k: [] for k in ("t_m", "lL0", "lR0", "lL10", "lR10", "lL20", "lR20", "pL", "pR", "py10", "dcurv", "lcs",
                         "t_s", "s_act", "dob", "dob_fz", "s_ff")}
    params = {}
    for p in sorted(glob.glob(f"{RL}/75604b0a432fdc89_{route}--*--rlog.zst"), key=seg):
        try:
            for e in read_messages(p):
                w = e.which()
                if w == "modelV2":
                    m = e.modelV2
                    try:
                        L1, L2 = m.laneLines[1], m.laneLines[2]
                        x1 = np.asarray(L1.x); y1 = np.asarray(L1.y); x2 = np.asarray(L2.x); y2 = np.asarray(L2.y)
                        px = np.asarray(m.position.x); py = np.asarray(m.position.y)
                        pr = list(m.laneLineProbs)
                    except Exception:
                        continue
                    if len(x1) < 5 or len(pr) < 3:
                        continue
                    A["t_m"].append(e.logMonoTime / 1e9)
                    A["lL0"].append(y1[0]); A["lR0"].append(y2[0])
                    A["lL10"].append(np.interp(10, x1, y1)); A["lR10"].append(np.interp(10, x2, y2))
                    A["lL20"].append(np.interp(20, x1, y1)); A["lR20"].append(np.interp(20, x2, y2))
                    A["pL"].append(pr[1]); A["pR"].append(pr[2])
                    A["py10"].append(np.interp(10, px, py) if len(px) > 3 and px[-1] > 10 else np.nan)
                    A["dcurv"].append(m.action.desiredCurvature)
                    try:
                        A["lcs"].append(float(int(m.meta.laneChangeState)))
                    except Exception:
                        A["lcs"].append(np.nan)
                elif w == "starpilotLateralState":
                    try:
                        s = e.starpilotLateralState
                        A["t_s"].append(e.logMonoTime / 1e9); A["s_act"].append(float(s.active))
                        A["dob"].append(s.accordObserverTorque); A["dob_fz"].append(float(s.accordObserverFrozen))
                        A["s_ff"].append(s.feedforward)
                    except Exception:
                        pass
                elif w == "initData" and not params:
                    try:
                        for x in e.initData.params.entries:
                            if x.key.startswith(PK):
                                params[x.key] = bytes(x.value).decode(errors="replace")[:200]
                    except Exception:
                        pass
        except Exception as ex:
            print(f"   seg {seg(p)} read error {ex}", flush=True)
        n = len(A["t_s"])
        if n and len(A["t_s"]) != len(A["dob"]):
            m_ = min(len(A[k]) for k in ("t_s", "s_act", "dob", "dob_fz", "s_ff"))
            for k in ("t_s", "s_act", "dob", "dob_fz", "s_ff"): A[k] = A[k][:m_]
        print(f"   {route} seg {seg(p)} model={len(A['t_m'])} slat={len(A['t_s'])}", flush=True)
    D = {k: np.asarray(v, dtype=np.float64) for k, v in A.items()}
    D["params_json"] = np.array(json.dumps(params))
    np.savez_compressed(OUT / f"{route}_fsr.npz", **D)
    print(f"{route}: wrote, params {len(params)}", flush=True)

if __name__ == "__main__":
    for r in sys.argv[1:]:
        if (OUT / f"{r}_fsr.npz").exists():
            print(r, "exists"); continue
        extract(r)
