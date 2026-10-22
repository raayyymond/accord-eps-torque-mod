# runs ON THE DEVICE: python - <route>--<seg>  ; writes a compressed npz (cruise_seg schema, CV=1) to stdout
import io, sys, os
import numpy as np, zstandard as zstd
from cereal import log as L
seg = sys.argv[1]
path = "/data/media/0/realdata/%s/rlog.zst" % seg
data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(open(path, "rb").read())).read()
ACC_CONTROL = 479
def _s16(hi, lo):
  v = (hi << 8) | lo
  return v - 65536 if v & 0x8000 else v
cs, cc, lp, sp, rs, gas, co = [], [], [], [], [], [], []
for e in L.Event.read_multiple_bytes(data):
  w = e.which()
  t = e.logMonoTime * 1e-9
  if w == "carState":
    c = e.carState
    cs.append((t, c.vEgo, c.aEgo, c.cruiseState.speed, c.gasPressed, c.brakePressed, c.standstill, c.vCruise))
  elif w == "carControl":
    c = e.carControl
    o = c.orientationNED
    cc.append((t, c.longActive, c.actuators.accel, o[1] if len(o) == 3 else np.nan, c.actuators.longControlState.raw))
  elif w == "carOutput":
    co.append((t, e.carOutput.actuatorsOutput.accel))
  elif w == "longitudinalPlan":
    q = e.longitudinalPlan
    sp0 = q.speeds; ac = q.accels
    lp.append((t, q.aTarget, q.hasLead, sp0[0] if len(sp0) else np.nan, ac[0] if len(ac) else np.nan,
               sp0[-1] if len(sp0) else np.nan, q.shouldStop))
  elif w == "starpilotPlan":
    p = e.starpilotPlan
    sp.append((t, p.vCruise, p.experimentalMode, p.maxAcceleration, p.minAcceleration))
  elif w == "radarState":
    l = e.radarState.leadOne
    rs.append((t, l.status, l.dRel))
  elif w == "sendcan":
    for m in e.sendcan:
      if m.address == ACC_CONTROL:
        d = m.dat
        if len(d) >= 5:
          acc = ((d[3] << 3) | (d[4] >> 5))
          acc = acc - 2048 if acc & 0x400 else acc
          gas.append((t, _s16(d[0], d[1]), acc * 0.01, (d[4] >> 2) & 1))
        break
f = lambda x, n: np.array(x, dtype=float) if x else np.zeros((0, n))
buf = io.BytesIO()
np.savez_compressed(buf, v=1, cs=f(cs, 8), cc=f(cc, 5), lp=f(lp, 7), sp=f(sp, 5), rs=f(rs, 3), gas=f(gas, 4), co=f(co, 2))
sys.stdout.buffer.write(buf.getvalue())
