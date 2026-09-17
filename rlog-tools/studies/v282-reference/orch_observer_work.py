"""Does the disturbance observer FEED the 1.5-3.5 Hz wheel shake at the car's real loop delay?

Uses the observer torque the fork LOGGED (starpilotLateralState.accordObserverTorque, decoded with the FORK's cereal
schema -- the kit schema's slot @137 is a different struct), not a replica.

Energy test per term T in the command: b_eq(tau) = -<T(t - tau), rate(t)> / <rate, rate>, both band-passed 1.5-3.5 Hz.
Convention: b_eq > 0 means the term opposes wheel rate after the delay (damps); b_eq < 0 means it pushes with it (feeds).
Delay tau = command->wheel-acceleration latency (measured 30 ms) + controls latency (carState -> sendcan, measured here).
Positive control: the fork's rate-loop term is a damper by construction (-(gain*(des_rate - meas_rate))) at tau = 0.
"""
import sys, glob, os, io
from pathlib import Path
import numpy as np
import zstandard as zstd
import capnp
from scipy import signal

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
FORK = Path("C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot")
sys.path.insert(0, str(HERE / "fill_straightroad"))
import forkparse  # fork cereal schema; the fork's car.capnp is a git symlink on Windows, so a copied schema is used
RLOGS = KIT / "analysis-2020accord" / "rlogs"
FS = 100.0
ROUTES = {"0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
          "00000076--d0b7ea7e4d": "T5"}


def read(p):
    return forkparse.read_messages(p)


sos = signal.butter(4, [1.5, 3.5], btype="band", fs=FS, output="sos")
print(f"{'route':24s} {'grp':5s} {'spd':6s} {'s':>5s} {'ctl lat ms':>10s} | b_eq x1e4 at tau = 0 / 30 / 40 / 60 / 90 / 120 ms"
      f"  [observer]  [rate-loop term: P+I+F minus hold/hyst not available, so total command]")
for rk, grp in ROUTES.items():
    segs = sorted(glob.glob(str(RLOGS / f"75604b0a432fdc89_{rk}--*--rlog.zst")), key=lambda p: int(os.path.basename(p).split("--")[2]))
    T = {"cs": [], "obs": [], "st": [], "e4": []}
    V = {"cs": [], "obs": [], "frz": [], "v": [], "rate": [], "out": [], "act": [], "press": [], "e4": []}
    for p in segs:
        for e in read(p):
            try:
                w = e.which()
            except Exception:
                continue
            t = e.logMonoTime / 1e9
            if w == "starpilotLateralState":
                s = e.starpilotLateralState
                T["obs"].append(t); V["obs"].append(s.accordObserverTorque); V["frz"].append(float(s.accordObserverFrozen))
            elif w == "carState":
                c = e.carState
                T["st"].append(t); V["v"].append(c.vEgo); V["rate"].append(c.steeringRateDeg); V["press"].append(float(c.steeringPressed))
            elif w == "controlsState":
                try:
                    ts = e.controlsState.lateralControlState.torqueState
                except Exception:
                    continue
                T["cs"].append(t); V["out"].append(ts.output); V["act"].append(float(ts.active))
            elif w == "sendcan":
                for m in e.sendcan:
                    if m.address == 0xE4 and m.src == 1:
                        T["e4"].append(t); V["e4"].append(float(int.from_bytes(bytes(m.dat)[0:2], "big", signed=True)))
    if not T["obs"]:
        print(f"{rk} {grp}: no starpilotLateralState"); continue
    t = np.asarray(T["cs"])
    I = lambda tk, vk: np.interp(t, np.asarray(T[tk]), np.asarray(V[vk]))
    # latcontrol_torque.py:850 logs accordObserverTorque = -accord_dob_torque; its contribution to cs_out is +accord_dob_torque
    obs = -I("obs", "obs"); frz = I("obs", "frz") > 0.5; v = I("st", "v"); rate = I("st", "rate"); press = I("st", "press") > 0.5
    out = np.asarray(V["out"]); act = np.asarray(V["act"]) > 0.5
    # controls latency: carState arrival -> next sendcan 0xE4
    tst = np.asarray(T["st"]); te4 = np.asarray(T["e4"])
    j = np.searchsorted(te4, tst)
    ok = j < len(te4)
    ctl_ms = float(np.median((te4[j[ok]] - tst[ok]) * 1000))
    # observer contribution to cs_out is +obs (torque frame; cs_out = -output_torque, output has -obs). Total command = cs_out.
    for lo, hi, tag in [(8, 15, "8-15"), (15, 40, ">=15")]:
        m = act & ~press & ~frz & (v >= lo) & (v < hi)
        idx = np.where(m)[0]
        if len(idx) < 500:
            continue
        br = np.where(np.diff(idx) > 3)[0]
        chunks = [c for c in np.split(idx, br + 1) if len(c) > 600]
        res_o, res_c = {}, {}
        secs = 0
        for c in chunks:
            a, b = c[0], c[-1] + 1
            r = signal.sosfiltfilt(sos, rate[a:b]); o = signal.sosfiltfilt(sos, obs[a:b]); u = signal.sosfiltfilt(sos, out[a:b])
            e = 150; r, o, u = r[e:-e], o[e:-e], u[e:-e]
            secs += len(r) / FS
            for tau in (0, 3, 4, 6, 9, 12):
                rr = r[tau:]; oo = o[:len(o) - tau] if tau else o; uu = u[:len(u) - tau] if tau else u
                res_o.setdefault(tau, [0.0, 0.0]); res_c.setdefault(tau, [0.0, 0.0])
                res_o[tau][0] += float(np.dot(oo, rr)); res_o[tau][1] += float(np.dot(rr, rr))
                res_c[tau][0] += float(np.dot(uu, rr)); res_c[tau][1] += float(np.dot(rr, rr))
        # sign of the rate-in-torque-frame relation: rate is +left deg/s, cs_out positive = the controller's +output.
        bo = " ".join(f"{-res_o[k][0]/res_o[k][1]*1e4:+6.2f}" for k in (0, 3, 4, 6, 9, 12))
        bc = " ".join(f"{-res_c[k][0]/res_c[k][1]*1e4:+6.2f}" for k in (0, 3, 4, 6, 9, 12))
        print(f"{rk:24s} {grp:5s} {tag:6s} {secs:5.0f} {ctl_ms:10.1f} | obs {bo} | total cmd {bc}")

