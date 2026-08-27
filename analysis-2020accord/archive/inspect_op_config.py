#!/usr/bin/env python3
r"""Inspect the openpilot-side config in the MANUAL drive (aa5b3e0c01) vs route b9:
openpilot version, lateral tuning, presence of a feedforward term, and the bus-command spectral
rolloff (to detect the newly-added CAN-output low-pass). The operator reports PID->PID+FF-from-model
and a low-pass on the openpilot CAN output, both NEW since V38."""
import sys, glob
from pathlib import Path
from collections import Counter
import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402


def honda_checksum(address, d):
    s = 0; a = address
    while a:
        s += a & 0xF; a >>= 4
    for i, b in enumerate(d):
        if i == len(d) - 1:
            b >>= 4
        s += (b & 0xF) + (b >> 4)
    return (8 - s) & 0xF


def s16be(b0, b1):
    v = (b0 << 8) | b1
    return v - 0x10000 if v & 0x8000 else v


def probe(paths, label, nseg_cfg=2):
    print("\n" + "=" * 78 + f"\n{label}\n" + "=" * 78)
    ver = None; latt = None
    f_terms = []; p_terms = []; i_terms = []
    e4_dlc = Counter(); e4_len_ok = 0
    for pi, p in enumerate(paths):
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            if w == "initData" and ver is None:
                try:
                    ver = evt.initData.version
                except Exception:
                    pass
            elif w == "carParams" and latt is None:
                try:
                    cp = evt.carParams
                    lt = cp.lateralTuning
                    latt = f"which={lt.which()}"
                    if lt.which() == "torque":
                        t = lt.torque
                        latt += (f" kp={t.kp:.3f} ki={t.ki:.3f} kf={t.kf:.4f} "
                                 f"friction={t.friction:.3f} useSteeringAngle={t.useSteeringAngle}")
                except Exception as e:
                    latt = f"(err {e})"
            elif w == "controlsState":
                try:
                    lcs = evt.controlsState.lateralControlState
                    if lcs.which() == "torqueState":
                        ts = lcs.torqueState
                        p_terms.append(float(ts.p)); i_terms.append(float(ts.i)); f_terms.append(float(ts.f))
                except Exception:
                    pass
            elif w == "can":
                for fr in evt.can:
                    if fr.address == 228:
                        e4_dlc[len(fr.dat)] += 1
        if pi + 1 >= nseg_cfg and ver is not None and latt is not None and len(f_terms) > 50:
            break
    print(f"  openpilot version: {ver}")
    print(f"  lateralTuning:     {latt}")
    if f_terms:
        f_terms = np.array(f_terms); p_terms = np.array(p_terms); i_terms = np.array(i_terms)
        print(f"  lateral term RMS over {len(f_terms)} samples:  "
              f"P={np.std(p_terms):.3f}  I={np.std(i_terms):.3f}  FEEDFORWARD f={np.std(f_terms):.3f} "
              f"(mean|f|={np.mean(np.abs(f_terms)):.3f})")
        print(f"  -> feedforward is {'ACTIVE (non-zero)' if np.mean(np.abs(f_terms)) > 1e-4 else '~zero'}")
    print(f"  CAN 228 (0xE4) DLC histogram: {dict(e4_dlc)}")


def bus_rolloff(paths, label, tx_src=0):
    """PSD rolloff of the 0xE4 bus STEER_TORQUE command over engaged runs -> detects an output low-pass."""
    FS = 100.0
    cmds = []
    for p in paths:
        st = []; t = []
        for evt in read_messages(p):
            try:
                if evt.which() != "can":
                    continue
            except Exception:
                continue
            for fr in evt.can:
                if fr.address == 228 and fr.src == tx_src:
                    d = bytes(fr.dat)
                    if len(d) >= 4:
                        st.append(s16be(d[0], d[1])); t.append(evt.logMonoTime)
        if len(st) > 1024:
            cmds.append(np.array(st, float))
    if not cmds:
        print(f"  [{label}] no 0xE4 command captured on src {tx_src}")
        return
    # Welch PSD, report high/low band ratio (rolloff = strong LP on output)
    win = np.hanning(512)
    acc = np.zeros(257); K = 0
    for x in cmds:
        for s0 in range(0, len(x) - 512, 256):
            seg = x[s0:s0 + 512].copy(); seg -= seg.mean(); seg *= win
            acc += np.abs(np.fft.rfft(seg)) ** 2; K += 1
    f = np.fft.rfftfreq(512, 1 / FS); P = acc / max(K, 1)
    def band(a, b):
        return P[(f >= a) & (f <= b)].sum()
    lo = band(0.5, 3); mid = band(5, 12); hi = band(15, 30)
    print(f"  [{label}] 0xE4 bus PSD bands (K={K}): 0.5-3Hz={lo:.3g}  5-12Hz={mid:.3g}  15-30Hz={hi:.3g}  "
          f"| hi/lo={hi/lo:.4f} mid/lo={mid/lo:.4f}  (lower hi/lo => stronger output low-pass)")


manual = sorted(glob.glob(str(HERE / "rlogs" / "manual" / "*" / "*" / "rlog.zst")))
b9 = sorted(glob.glob(str(HERE / "rlogs" / "807a3c21c9f405e8_000000b9--*--*--rlog.zst")))

probe(manual[:3], "MANUAL drive (aa5b3e0c01) -- V49P firmware")
probe(b9[:3], "ROUTE b9 -- V38 firmware (reference)")
print("\n" + "-" * 78 + "\nBUS-COMMAND ROLLOFF (detect the new openpilot output low-pass)\n" + "-" * 78)
bus_rolloff(manual, "manual")
bus_rolloff(b9, "b9")
