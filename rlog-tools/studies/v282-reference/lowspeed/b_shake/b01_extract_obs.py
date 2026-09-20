"""b01: extract the LOGGED observer (starpilotLateralState.accordObserverTorque / Frozen, fork schema) per torque route.
Saved raw (logged sign). latcontrol_torque.py:850 logs -accord_dob_torque."""
import sys, glob, os
from pathlib import Path
import numpy as np
BASE = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, str(BASE / 'fill_straightroad'))
import forkparse
RL = BASE.parents[2] / 'analysis-2020accord' / 'rlogs'
OUT = Path(__file__).parent / 'out'
for rk in sys.argv[1:]:
    segs = sorted(glob.glob(str(RL / f"75604b0a432fdc89_{rk}--*--rlog.zst")), key=lambda p: int(os.path.basename(p).split("--")[2]))
    t, o, fz = [], [], []
    for p in segs:
        for e in forkparse.read_messages(p):
            try:
                if e.which() != 'starpilotLateralState':
                    continue
            except Exception:
                continue
            s = e.starpilotLateralState
            t.append(e.logMonoTime / 1e9); o.append(s.accordObserverTorque); fz.append(float(s.accordObserverFrozen))
    np.savez_compressed(OUT / f'obs_{rk}.npz', t=np.array(t), obs_logged=np.array(o), frozen=np.array(fz))
    print(rk, len(segs), len(t), flush=True)
