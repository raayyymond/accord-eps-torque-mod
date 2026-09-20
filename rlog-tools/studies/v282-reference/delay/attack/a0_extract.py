"""ADVERSARY a0: my own raw extraction. No inherited cache, no inherited chain npz.

Per route, per segment, streamed. Keeps only what the two attacks need:
  msg streams: carState / controlsState / carControl / sendcan(0xE4 src1)
  raw can:     batch logMonoTime + per-frame (addr, src, payload) for 0x14A, 0x18F, 0x1AB, and 0xE4 echoes
usage: python a0_extract.py <route> [nseg]
out:   out/raw_<route>.npz
"""
import sys, os, glob
from pathlib import Path
import numpy as np

KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
from rlog_parse import read_messages  # noqa: E402

RLOGS = KIT / "analysis-2020accord" / "rlogs"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

WANT = {0x14A, 0x18F, 0x1AB, 0xE4}


def seg_no(p):
    return int(os.path.basename(p).split("--")[2])


def i16be(d, i=0):
    return int.from_bytes(d[i:i + 2], "big", signed=True)


def extract(route, nseg=None):
    segs = sorted(glob.glob(str(RLOGS / f"75604b0a432fdc89_{route}--*--rlog.zst")), key=seg_no)
    if nseg:
        segs = segs[:nseg]
    A = {k: [] for k in ("t_cst", "sa", "sr", "v", "spress", "storque_eps",
                         "t_cs", "cs_out", "cs_act", "cs_err",
                         "t_cc", "cc_tq", "cc_tqcan", "cc_lat",
                         "t_e4", "e4",
                         "cb", "cf_addr", "cf_src", "cf_b0", "cf_b1", "cf_cnt", "cf_bi", "cf_idx")}
    nb = 0
    for p in segs:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            t = evt.logMonoTime / 1e9
            if w == "carState":
                c = evt.carState
                A["t_cst"].append(t); A["sa"].append(c.steeringAngleDeg); A["sr"].append(c.steeringRateDeg)
                A["v"].append(c.vEgo); A["spress"].append(float(c.steeringPressed))
                A["storque_eps"].append(c.steeringTorqueEps)
            elif w == "controlsState":
                cs = evt.controlsState
                try:
                    ts = cs.lateralControlState.torqueState
                except Exception:
                    continue
                A["t_cs"].append(t); A["cs_out"].append(ts.output); A["cs_act"].append(float(ts.active))
                A["cs_err"].append(ts.error)
            elif w == "carControl":
                cc = evt.carControl
                A["t_cc"].append(t); A["cc_tq"].append(cc.actuators.torque)
                A["cc_tqcan"].append(cc.actuators.torqueOutputCan); A["cc_lat"].append(float(cc.latActive))
            elif w == "sendcan":
                for m in evt.sendcan:
                    if m.address == 0xE4 and m.src == 1:
                        d = bytes(m.dat)
                        A["t_e4"].append(t); A["e4"].append(float(i16be(d)))
            elif w == "can":
                A["cb"].append(t)
                for j, m in enumerate(evt.can):
                    if m.address in WANT:
                        d = bytes(m.dat)
                        A["cf_addr"].append(m.address); A["cf_src"].append(m.src)
                        A["cf_b0"].append(float(i16be(d, 0)))
                        A["cf_b1"].append(float(i16be(d, 2)) if len(d) >= 4 else 0.0)
                        A["cf_cnt"].append(float(d[-2] >> 4) if len(d) >= 2 else 0.0)
                        A["cf_bi"].append(nb); A["cf_idx"].append(j)
                nb += 1
        print(f"  {route} seg {seg_no(p)} cst={len(A['t_cst'])} frames={len(A['cf_addr'])}", flush=True)
    D = {k: np.asarray(v, dtype=np.float64 if k not in ("cf_addr", "cf_src", "cf_bi", "cf_idx") else np.int64)
         for k, v in A.items() if len(v)}
    f = OUT / f"raw_{route}.npz"
    np.savez_compressed(f, **D)
    print(f"{route}: {f.name} {f.stat().st_size/1e6:.1f} MB span {D['t_cst'][-1]-D['t_cst'][0]:.0f}s", flush=True)


if __name__ == "__main__":
    extract(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
