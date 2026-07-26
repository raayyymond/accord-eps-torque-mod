"""Decode the 'gentle EME' (LKAS-only cut) events from rlog.zst directly off CAN + carState.

msg 399 STEER_STATUS (EPS frame, hand-decoded Motorola):
  STEER_STATUS(39|4+), STEER_CONTROL_ACTIVE(35|1+), STEER_TORQUE_SENSOR(7|16- x-1),
  STEER_ANGLE_RATE(23|16- x-0.1 deg/s)
carState: vEgo, steeringTorqueEps(motor), steeringTorque(driver), steeringAngleDeg, steeringRateDeg
carControl: latActive, actuators.torque(cmd -1..1), actuators.torqueOutputCan(EPS input int)

Locate event by STEER_STATUS->4 (no_torque_alert_2); print signals in a window around it.
"""
import io, sys
from pathlib import Path
import zstandard as zstd
import capnp

KIT = Path(__file__).resolve().parent.parent
CEREAL = KIT / "rlog-tools" / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL / "log.capnp"))

def be_bits(data, start, length):
    """DBC Motorola (@0) big-endian extraction, MSB-first."""
    val = 0; bit = start
    for _ in range(length):
        byte, b_in = bit // 8, bit % 8
        val = (val << 1) | ((data[byte] >> b_in) & 1)
        bit = bit + 15 if b_in == 0 else bit - 1
    return val

def s16(u):  # signed 16-bit
    return u - 0x10000 if u & 0x8000 else u

def dec399(d):
    if len(d) < 7: return None
    return {
        "status": be_bits(d, 39, 4),
        "active": be_bits(d, 35, 1),
        "tbar":   -s16(be_bits(d, 7, 16)),          # scale -1
        "rate":   -0.1 * s16(be_bits(d, 23, 16)),   # scale -0.1 deg/s
    }

def events(path):
    raw = Path(path).read_bytes()
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read()
    it = log_capnp.Event.read_multiple_bytes(data)
    while True:
        try: yield next(it)
        except StopIteration: break
        except capnp.KjException: break

def analyze(path):
    print("\n" + "="*112 + f"\n{Path(path).name}\n" + "="*112)
    rows = []; t0 = None
    st = {"status":None,"active":None,"tbar":None,"rate":None,
          "veg":None,"mot":None,"drv":None,"ang":None,"csrate":None,
          "lat":None,"cmd":None,"cmdcan":None}
    for evt in events(path):
        t = evt.logMonoTime
        if t0 is None: t0 = t
        ts = (t - t0)/1e9
        w = evt.which()
        if w == "can":
            for c in evt.can:
                if c.address == 399 and c.src == 1:
                    dd = dec399(bytes(c.dat))
                    if dd:
                        st.update(dd); rows.append((ts, dict(st)))
        elif w == "carState":
            cs = evt.carState
            st["veg"]=cs.vEgo; st["mot"]=cs.steeringTorqueEps; st["drv"]=cs.steeringTorque
            st["ang"]=cs.steeringAngleDeg; st["csrate"]=cs.steeringRateDeg
        elif w == "carControl":
            a = evt.carControl.actuators
            st["lat"]=bool(evt.carControl.latActive); st["cmd"]=a.torque; st["cmdcan"]=a.torqueOutputCan
    idx4 = next((i for i,(ts,d) in enumerate(rows) if d["status"]==4), None)
    if idx4 is None:
        from collections import Counter
        print("  no STEER_STATUS==4. histogram:", Counter(d["status"] for _,d in rows))
        return
    tcut = rows[idx4][0]
    # window
    print(f"  *** STEER_STATUS->4 (no_torque_alert_2) first at t={tcut:.3f}s, vEgo~"
          f"{next((d['veg'] for ts,d in rows if abs(ts-tcut)<0.2 and d['veg']),0):.1f} m/s ***")
    hdr = (f"  {'t_s':>7} {'STAT':>4} {'ctrlA':>5} | {'EPSmot':>7} {'cmd':>6} {'cmdcan':>7} {'lat':>3} | "
           f"{'angle':>7} {'rate399':>7} {'csrate':>7} | {'tbar399':>7} {'drvCS':>6}")
    print(hdr); print("  " + "-"*(len(hdr)-2))
    for ts,d in rows:
        if tcut-1.0 <= ts <= tcut+1.0:
            g = lambda k,f,dflt="   -": (f % d[k]) if d[k] is not None else dflt
            mark = " <==4" if d["status"]==4 else ""
            print(f"  {ts:7.3f} {str(d['status']):>4} {str(d['active']):>5} | "
                  f"{g('mot','%7.0f')} {g('cmd','%6.2f')} {g('cmdcan','%7.0f')} {str(d['lat'])[0]:>3} | "
                  f"{g('ang','%7.1f')} {g('rate','%7.1f')} {g('csrate','%7.1f')} | "
                  f"{g('tbar','%7.0f')} {g('drv','%6.0f')}{mark}")

for p in sys.argv[1:]:
    analyze(p)
