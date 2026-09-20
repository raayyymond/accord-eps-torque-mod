import sys
from pathlib import Path
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
from rlog_parse import read_messages
p = KIT / "analysis-2020accord" / "rlogs" / f"75604b0a432fdc89_{sys.argv[1]}--{sys.argv[2]}--rlog.zst"
n0 = int(sys.argv[3]) if len(sys.argv) > 3 else 20000
out = []; k = 0
t0 = None
for e in read_messages(p):
    try:
        w = e.which()
    except Exception:
        continue
    t = e.logMonoTime
    if t0 is None: t0 = t
    if w == 'can':
        s = []
        for m in e.can:
            if m.address in (0x156, 0xE4, 0x18F):
                d = bytes(m.dat)
                s.append(f"{m.address:x}/{m.src}:{d.hex()}")
        if s: out.append((t, 'can', ' '.join(s)))
    elif w == 'sendcan':
        s = [f"{m.address:x}/{m.src}:{bytes(m.dat).hex()}" for m in e.sendcan if m.address == 0xE4]
        out.append((t, 'sendcan', ' '.join(s)))
    elif w == 'carState':
        out.append((t, 'carState', f"sa {e.carState.steeringAngleDeg:.1f} sr {e.carState.steeringRateDeg:.0f}"))
    elif w == 'controlsState':
        cs = e.controlsState
        out.append((t, 'controlsState', f"curv {cs.curvature:.6f} out {cs.lateralControlState.torqueState.output:.4f}"))
    elif w == 'carControl':
        out.append((t, 'carControl', f"tq {e.carControl.actuators.torque:.4f} lat {e.carControl.latActive}"))
    k += 1
print(len(out))
for t, w, s in out[n0:n0 + 90]:
    print(f"{(t - t0)/1e6:10.2f} {w:14s} {s}")
