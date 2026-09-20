"""Extract the message/CAN timing chain for the delay decomposition (one route at a time, one segment at a time).

Per route writes cache/<counter>--<hash>.npz with, all times = logMonoTime in seconds:
  can batches   : cb_t (one per 'can' event)
  EPS frames    : f14_t f14_bi f14_pos ang14 rate14     (0x14A src 1; batch index, position in batch)
                  f18_t f18_bi f18_pos tq18 rate18 sca18 (0x18F src 1)
                  fab_t fab_bi fab_pos tap               (0x1AB src 1; signed tap in firmware counts, 8 per LSB)
  TX echoes     : fe4_t fe4_bi fe4_pos fe4_raw           (0xE4 src 129 -- panda TX confirmation on bus 1)
  sendcan       : sc_t sc_raw sc_cmd sc_req              (0xE4 bus 1)
  carState      : cs_t cs_ang cs_rate cs_v cs_press
  controlsState : ct_t ct_out ct_act ct_des ct_active
  carControl    : cc_t cc_lat cc_tq
  carOutput     : co_t co_tq co_can
Kit schema; unknown union members skipped.  Usage: python extract_chain.py <counter--hash> [...]
"""
import sys, glob, os, gc
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
import rlog_parse

RLOGS = KIT / "analysis-2020accord" / "rlogs"
OUT = HERE / "cache"; OUT.mkdir(exist_ok=True)


def i16(d, o):
    v = (d[o] << 8) | d[o + 1]
    return v - 65536 if v >= 32768 else v


def extract(route):
    maxs = int(os.environ.get("MAXSEGS", "999"))
    segs = sorted(glob.glob(str(RLOGS / f"75604b0a432fdc89_{route}--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))[:maxs]
    K = {k: [] for k in ("cb_t", "f14_t", "f14_bi", "f14_pos", "ang14", "rate14", "f18_t", "f18_bi", "f18_pos", "tq18",
                         "rate18", "sca18", "fab_t", "fab_bi", "fab_pos", "tap", "fe4_t", "fe4_bi", "fe4_pos", "fe4_raw",
                         "sc_t", "sc_raw", "sc_cmd", "sc_req", "cs_t", "cs_ang", "cs_rate", "cs_v", "cs_press",
                         "ct_t", "ct_out", "ct_act", "ct_des", "ct_active", "cc_t", "cc_lat", "cc_tq",
                         "co_t", "co_tq", "co_can")}
    bi = -1
    for p in segs:
        n0 = len(K["cs_t"])
        try:
            for e in rlog_parse.read_messages(p):
                try:
                    w = e.which()
                except Exception:
                    continue
                if w == "can":
                    t = e.logMonoTime * 1e-9
                    bi += 1
                    K["cb_t"].append(t)
                    for pos, m in enumerate(e.can):
                        a, s = int(m.address), int(m.src)
                        if s == 1 and a in (0x14A, 0x18F, 0x1AB):
                            d = bytes(m.dat)
                            if a == 0x14A:
                                K["f14_t"].append(t); K["f14_bi"].append(bi); K["f14_pos"].append(pos)
                                K["ang14"].append(-0.1 * i16(d, 0)); K["rate14"].append(-1.0 * i16(d, 2))
                            elif a == 0x18F:
                                K["f18_t"].append(t); K["f18_bi"].append(bi); K["f18_pos"].append(pos)
                                K["tq18"].append(-i16(d, 0)); K["rate18"].append(-0.1 * i16(d, 2))
                                K["sca18"].append((d[4] >> 3) & 1)
                            else:
                                v = ((d[0] & 3) << 8) | d[1]
                                mag = (v & 0x1FF) * 8
                                K["fab_t"].append(t); K["fab_bi"].append(bi); K["fab_pos"].append(pos)
                                K["tap"].append(-mag if (v & 0x200) else mag)
                        elif s == 129 and a == 0xE4:
                            d = bytes(m.dat)
                            K["fe4_t"].append(t); K["fe4_bi"].append(bi); K["fe4_pos"].append(pos)
                            K["fe4_raw"].append(int.from_bytes(d[:5], "big"))
                elif w == "sendcan":
                    t = e.logMonoTime * 1e-9
                    for m in e.sendcan:
                        if int(m.address) == 0xE4:
                            d = bytes(m.dat)
                            K["sc_t"].append(t); K["sc_raw"].append(int.from_bytes(d[:5], "big"))
                            K["sc_cmd"].append(i16(d, 0)); K["sc_req"].append((d[2] >> 7) & 1)
                elif w == "carState":
                    c = e.carState
                    K["cs_t"].append(e.logMonoTime * 1e-9); K["cs_ang"].append(c.steeringAngleDeg)
                    K["cs_rate"].append(c.steeringRateDeg); K["cs_v"].append(c.vEgo); K["cs_press"].append(int(c.steeringPressed))
                elif w == "controlsState":
                    c = e.controlsState
                    try:
                        ts = c.lateralControlState.torqueState
                        o, a_, d_, ac = ts.output, ts.actualLateralAccel, ts.desiredLateralAccel, int(ts.active)
                    except Exception:
                        o = a_ = d_ = np.nan; ac = 0
                    K["ct_t"].append(e.logMonoTime * 1e-9); K["ct_out"].append(o); K["ct_act"].append(a_)
                    K["ct_des"].append(d_); K["ct_active"].append(ac)
                elif w == "carControl":
                    c = e.carControl
                    K["cc_t"].append(e.logMonoTime * 1e-9); K["cc_lat"].append(int(c.latActive)); K["cc_tq"].append(c.actuators.torque)
                elif w == "carOutput":
                    c = e.carOutput
                    K["co_t"].append(e.logMonoTime * 1e-9); K["co_tq"].append(c.actuatorsOutput.torque)
                    K["co_can"].append(c.actuatorsOutput.torqueOutputCan)
        except Exception as ex:
            print("  seg read stopped:", os.path.basename(p), str(ex)[:100])
        print(f"  {os.path.basename(p)}  carState {len(K['cs_t']) - n0}", flush=True)
        gc.collect()
    A = {}
    for k, v in K.items():
        if k in ("fe4_raw", "sc_raw"):
            A[k] = np.asarray(v, dtype=np.uint64)
        elif k.endswith("_bi") or k.endswith("_pos") or k in ("sc_cmd", "sc_req", "cs_press", "ct_active", "cc_lat", "sca18", "tq18"):
            A[k] = np.asarray(v, dtype=np.int64)
        else:
            A[k] = np.asarray(v, dtype=np.float64)
    np.savez_compressed(OUT / f"{route}.npz", **A)
    print(route, {k: len(v) for k, v in A.items() if k.endswith("_t")})


if __name__ == "__main__":
    for r in sys.argv[1:]:
        extract(r); gc.collect()
