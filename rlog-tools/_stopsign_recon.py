"""Reconstruct the stop-sign roll-through SAFETY event in seg 3.
Merges carState / carControl / controlsState / selfdriveState / drivingModelData /
modelV2 / longitudinalPlan / radarState into a single time-ordered timeline.
"""
import io
from pathlib import Path
import zstandard as zstd, capnp

CER = Path(__file__).parent / "cereal"
capnp.remove_import_hook()
L = capnp.load(str(CER / "log.capnp"))
P = "D:/drivedata/00000002--a6fcb0a223--3/rlog.zst"

def gen(p):
    d = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    it = L.Event.read_multiple_bytes(d)
    while True:
        try: yield next(it)
        except StopIteration: return
        except capnp.KjException: return

PLAN_SRC = {0:"cruise",1:"lead0",2:"lead1",3:"lead2",4:"e2e"}

# latched signal state
st = dict(vEgo=0.0, aEgo=0.0, brake=False, gas=False,
          en=False, lo=False, cmd=0.0,
          dCurv=0.0, sdState="?",
          ss=None, dAcc=None,            # drivingModelData.action
          lpSS=None, lpSrc=None, lpHasLead=None, lpFcw=None, aTarget=None, allowThrottle=None,
          leadProb=None, leadX=None, leadV=None, leadA=None,  # radarState leadOne
          mLeadProb=None, mLeadX=None, mLeadV=None,           # modelV2 leadsV3[0]
          modelPosEndX=None)

t0 = None
rows = []  # snapshot per carState frame

WIN_LO, WIN_HI = 205.0, 227.0

for e in gen(P):
    w = e.which(); t = e.logMonoTime
    if t0 is None: t0 = t
    ts = (t - t0)/1e9
    if w == "carState":
        cs = e.carState
        st["vEgo"]=cs.vEgo; st["aEgo"]=cs.aEgo; st["brake"]=cs.brakePressed; st["gas"]=cs.gasPressed
        if WIN_LO <= ts <= WIN_HI:
            rows.append((ts, dict(st)))
    elif w == "carControl":
        cc=e.carControl; st["en"]=cc.enabled; st["lo"]=cc.longActive; st["cmd"]=cc.actuators.accel
    elif w == "controlsState":
        st["dCurv"]=e.controlsState.desiredCurvature
    elif w == "selfdriveState":
        st["sdState"]=str(e.selfdriveState.state)
    elif w == "drivingModelData":
        try:
            a=e.drivingModelData.action
            st["ss"]=a.shouldStop; st["dAcc"]=a.desiredAcceleration
        except Exception: pass
    elif w == "longitudinalPlan":
        lp=e.longitudinalPlan
        try: st["lpSS"]=lp.shouldStop
        except Exception: pass
        try: st["lpSrc"]=PLAN_SRC.get(int(lp.longitudinalPlanSource), str(lp.longitudinalPlanSource))
        except Exception: pass
        try: st["lpHasLead"]=lp.hasLead
        except Exception: pass
        try: st["lpFcw"]=lp.fcw
        except Exception: pass
        try: st["aTarget"]=lp.aTarget
        except Exception: pass
        try: st["allowThrottle"]=lp.allowThrottle
        except Exception: pass
    elif w == "radarState":
        try:
            lo1=e.radarState.leadOne
            st["leadProb"]=lo1.prob if hasattr(lo1,"prob") else lo1.status
            st["leadX"]=lo1.dRel; st["leadV"]=lo1.vRel; st["leadA"]=lo1.aLeadK
            st["leadStatus"]=lo1.status
        except Exception: pass
    elif w == "modelV2":
        m=e.modelV2
        try:
            if len(m.leadsV3)>0:
                l0=m.leadsV3[0]
                st["mLeadProb"]=l0.prob
                st["mLeadX"]=l0.x[0] if len(l0.x)>0 else None
                st["mLeadV"]=l0.v[0] if len(l0.v)>0 else None
        except Exception: pass
        try:
            if len(m.position.x)>0:
                st["modelPosEndX"]=m.position.x[-1]  # furthest predicted longitudinal point
        except Exception: pass

# ---- print high-rate timeline (every carState frame ~ 100Hz -> downsample to ~10Hz) ----
print(f"# Stop-sign roll-through reconstruction  seg3  (window {WIN_LO}-{WIN_HI}s)")
print(f"# experimentalMode=True  openpilotLongitudinalControl=True  HONDA_CIVIC_BOSCH")
print()
hdr=("t","mph","aEgo","cmd","aTgt","dAcc","ss","lpSS","lpSrc","hasLd","ldX","ldV","ldProb","mLdProb","dCurv","OP","long","brk","gas","sdState")
print("  ".join(f"{h}" for h in hdr))
last=-1
for ts,s in rows:
    if int(ts*10)==last:  # ~10Hz
        continue
    last=int(ts*10)
    def f(x,fmt="{:.2f}"):
        return "-" if x is None else (fmt.format(x) if isinstance(x,(int,float)) else str(x))
    print(f"{ts:6.2f} {s['vEgo']*2.237:5.1f} {s['aEgo']:+5.2f} {s['cmd']:+5.2f} "
          f"{f(s['aTarget']):>5} {f(s['dAcc']):>5} {str(s['ss']):>5} {str(s['lpSS']):>5} "
          f"{str(s['lpSrc']):>6} {str(s['lpHasLead']):>5} {f(s['leadX'],'{:.0f}'):>4} {f(s['leadV']):>5} "
          f"{f(s['leadStatus'] if 'leadStatus' in s else None):>5} {f(s['mLeadProb']):>5} "
          f"{s['dCurv']:+.4f} {str(s['en']):>5} {str(s['lo']):>5} {str(s['brake']):>5} {str(s['gas']):>5} {s['sdState']}")
