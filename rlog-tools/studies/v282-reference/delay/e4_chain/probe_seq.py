"""Print the event ORDER and timestamps around an engaged stretch: can(EPS frames), carState, controlsState, carControl, carOutput, sendcan."""
import sys
from pathlib import Path
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
import rlog_parse
p = KIT / "analysis-2020accord" / "rlogs" / sys.argv[1]
start = int(sys.argv[2]); n = 0; shown = 0; t0 = None
dump = {}
for e in rlog_parse.read_messages(p):
    try: w = e.which()
    except Exception: continue
    if w not in ("can", "carState", "controlsState", "carControl", "carOutput", "sendcan"): continue
    n += 1
    if n < start: continue
    t = e.logMonoTime
    if t0 is None: t0 = t
    dt = (t - t0) / 1e6
    if w == "can":
        s = [(hex(m.address), m.src, bytes(m.dat).hex()) for m in e.can if m.address in (0xE4, 0x14A, 0x18F, 0x1AB) and m.src in (1, 129)]
    elif w == "sendcan":
        s = [(hex(m.address), m.src, bytes(m.dat).hex()) for m in e.sendcan if m.address == 0xE4]
    elif w == "carState":
        c = e.carState; s = (c.steeringAngleDeg, c.steeringRateDeg, c.vEgo, c.steeringPressed)
    elif w == "controlsState":
        c = e.controlsState; ts = c.lateralControlState.torqueState
        s = (ts.output, ts.actualLateralAccel, ts.desiredLateralAccel, c.curvature)
    elif w == "carControl":
        c = e.carControl; s = (c.latActive, c.actuators.torque, c.actuators.curvature)
        if "cc" not in dump: dump["cc"] = str(c)[:1500]
    elif w == "carOutput":
        c = e.carOutput; s = (c.actuatorsOutput.torque, c.actuatorsOutput.torqueOutputCan)
    print(f"{dt:9.3f} {w:14s} {s}")
    shown += 1
    if shown > int(sys.argv[3]): break
for k, v in dump.items(): print(v)
