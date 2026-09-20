"""ADJUDICATION, part C -- is the disturbance observer still an ENERGY SOURCE in 1.5-3.5 Hz at the MEASURED
D_loop (55-75 ms), and is it also true BELOW 8 m/s (the band the ARM-D decision is about)?

Re-derived independently of orch_observer_work.py, with the sign convention re-checked against the fork source:
  latcontrol_torque.py:667-670   inner_torque = -(z + gain*(des_rate - rate_meas));  inner_torque += -dob_torque
                                 => inner_torque is the TORQUE frame (= -left);  dob_torque is +left
  latcontrol_torque.py:850       accordObserverTorque = -dob_torque   == the term's TORQUE-frame contribution
  => the observer's contribution IN THE +LEFT FRAME (the frame of carState.steeringRateDeg) = -(logged value).
A damper in the +left frame is T = -b*rate, so with T_left(t - tau) the energy coefficient is
      b_eq(tau) = -<T_left(t-tau), rate(t)> / <rate(t), rate(t)>,   b_eq > 0 = damps, b_eq < 0 = FEEDS.

b_eq is evaluated for CONTINUOUS tau from the band-limited cross-spectrum, which is algebraically the same
lagged inner product:  <T(t-tau), rate(t)> = sum_f  T*(f) R(f) e^{j 2 pi f tau}.
Positive controls, run through the same code path on the same data:
  P1 synthetic pure damper   T_left = -rate          -> b_eq(0) must be +1.000 and b_eq(tau) = weighted cos(w tau)
  P2 synthetic pure spring   T_left = -angle         -> b_eq(0) must be ~0 (quadrature with rate)
  P3 synthetic delayed damper T_left = -rate(t - 25 ms) -> the b_eq(tau) zero crossing must move by -25 ms
"""
import glob
import json
import os
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
V282REF = HERE.parents[1]
sys.path.insert(0, str(V282REF / "fill_straightroad"))
import forkparse  # noqa: E402

RLOGS = V282REF.parents[2] / "analysis-2020accord" / "rlogs"
FS = 100.0
BAND = (1.5, 3.5)
TAUS = [0.0, 20.0, 30.0, 40.0, 55.0, 60.0, 65.0, 75.0, 90.0, 120.0]   # ms
ROUTES = {"0000006c--68c6e94b17": "rev6.4", "0000006d--05e83bb04f": "rev6.4",
          "0000006e--6ca3e014fd": "rev6.4B", "00000076--d0b7ea7e4d": "rev5"}
BINS = [("<8", 0.0, 8.0), ("3-8", 3.0, 8.0), ("8-15", 8.0, 15.0), (">=15", 15.0, 40.0)]
sos = signal.butter(4, list(BAND), btype="band", fs=FS, output="sos")


class Acc:
    """Accumulate the 1.5-3.5 Hz cross-spectrum <T, rate> and <rate, rate> over chunks."""

    def __init__(self):
        self.num = None
        self.den = 0.0
        self.f = None
        self.secs = 0.0
        self.n = 0

    W = 384          # fixed window so every chunk lands on the SAME frequency grid (3.84 s, df 0.26 Hz)

    def add(self, T, r):
        f = np.fft.rfftfreq(self.W, 1.0 / FS)
        m = (f >= BAND[0]) & (f <= BAND[1])
        for a in range(0, len(r) - self.W + 1, self.W // 2):
            tw, rw = T[a:a + self.W], r[a:a + self.W]
            Tf = np.fft.rfft(tw)[m]
            Rf = np.fft.rfft(rw)[m]
            # sum_t T(t) r(t+tau) = (1/W) sum_f conj(T) R e^{j2pi f tau}; x2 for the negative-frequency half
            c = np.conj(Tf) * Rf * 2.0 / self.W
            self.num = c if self.num is None else self.num + c
            self.den += float(np.dot(rw, rw))
            self.secs += self.W / FS
            self.n += 1
        self.f = f[m]

    def beq(self, tau_ms):
        if self.num is None or self.den == 0:
            return float("nan")
        ph = np.exp(1j * 2 * np.pi * self.f * tau_ms / 1000.0)
        return float(-np.real(np.sum(self.num * ph)) / self.den)


def chunks_of(mask, minlen=700):
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    return [c for c in np.split(idx, np.where(np.diff(idx) > 3)[0] + 1) if len(c) >= minlen]


results = {}
for rk, rev in ROUTES.items():
    segs = sorted(glob.glob(str(RLOGS / f"75604b0a432fdc89_{rk}--*--rlog.zst")),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    T = {k: [] for k in ("obs", "st", "cs")}
    V = {k: [] for k in ("obs", "frz", "v", "rate", "ang", "press", "out", "act")}
    for p in segs:
        for e in forkparse.read_messages(p):
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
                T["st"].append(t); V["v"].append(c.vEgo); V["rate"].append(c.steeringRateDeg)
                V["ang"].append(c.steeringAngleDeg); V["press"].append(float(c.steeringPressed))
            elif w == "controlsState":
                try:
                    ts = e.controlsState.lateralControlState.torqueState
                except Exception:
                    continue
                T["cs"].append(t); V["out"].append(ts.output); V["act"].append(float(ts.active))
    if not T["obs"]:
        print(f"{rk}: no starpilotLateralState"); continue
    t = np.asarray(T["cs"])
    I = lambda tk, vk: np.interp(t, np.asarray(T[tk]), np.asarray(V[vk]))
    obs_left = -I("obs", "obs")                      # +left-frame contribution (see docstring)
    frz = I("obs", "frz") > 0.5
    v = I("st", "v"); rate = I("st", "rate"); ang = I("st", "ang"); press = I("st", "press") > 0.5
    act = np.asarray(V["act"]) > 0.5
    res = {}
    for tag, lo, hi in BINS:
        m = act & ~press & ~frz & (v >= lo) & (v < hi)
        ch = chunks_of(m)
        if not ch:
            continue
        A = {k: Acc() for k in ("obs", "P1", "P2", "P3")}
        for c in ch:
            a, b = c[0], c[-1] + 1
            r = signal.sosfiltfilt(sos, rate[a:b])
            o = signal.sosfiltfilt(sos, obs_left[a:b])
            an = signal.sosfiltfilt(sos, ang[a:b])
            e = 150
            r, o, an = r[e:-e], o[e:-e], an[e:-e]
            if len(r) < 400:
                continue
            A["obs"].add(o, r)
            A["P1"].add(-r, r)
            A["P2"].add(-an, r)
            A["P3"].add(-np.concatenate([np.zeros(3), r[:-3]]), r)   # damper delayed 30 ms
        if A["obs"].n == 0:
            continue
        res[tag] = {"secs": round(A["obs"].secs, 1), "chunks": A["obs"].n,
                    "beq_obs": {f"{x:.0f}": round(A["obs"].beq(x) * 1e4, 2) for x in TAUS},
                    "P1_damper": {f"{x:.0f}": round(A["P1"].beq(x), 3) for x in (0.0, 30.0, 100.0)},
                    "P2_spring0": round(A["P2"].beq(0.0), 3),
                    "P3_delayed_damper": {f"{x:.0f}": round(A["P3"].beq(x), 3) for x in (0.0, 30.0)}}
    results[rk] = {"rev": rev, "bins": res}
    del T, V, obs_left, frz, v, rate, ang, press, act, t

print("b_eq x 1e4 (torque per deg/s).  POSITIVE = the observer's term opposes wheel rate after tau = DAMPS.")
print("NEGATIVE = it pushes with the wheel rate = FEEDS the 1.5-3.5 Hz shake.")
print()
hdr = " ".join(f"{x:>6.0f}" for x in TAUS)
print(f"{'route':22s} {'rev':8s} {'bin':5s} {'secs':>6s} {'nch':>4s} | tau ms = {hdr}")
for rk, r in results.items():
    for tag, c in r["bins"].items():
        row = " ".join(f"{c['beq_obs'][f'{x:.0f}']:+6.2f}" for x in TAUS)
        print(f"{rk:22s} {r['rev']:8s} {tag:5s} {c['secs']:6.0f} {c['chunks']:4d} |          {row}")
print()
print("POSITIVE CONTROLS (same code path, same chunks)")
print(f"{'route':22s} {'bin':5s} | {'P1 damper b_eq(0)':>17s} {'P1(30ms)':>9s} {'P1(100ms)':>10s} "
      f"{'P2 spring b_eq(0)':>17s} {'P3 delayed(0)':>13s} {'P3(30ms)':>9s}")
for rk, r in results.items():
    for tag, c in r["bins"].items():
        print(f"{rk:22s} {tag:5s} | {c['P1_damper']['0']:17.3f} {c['P1_damper']['30']:9.3f} "
              f"{c['P1_damper']['100']:10.3f} {c['P2_spring0']:17.3f} "
              f"{c['P3_delayed_damper']['0']:13.3f} {c['P3_delayed_damper']['30']:9.3f}")
json.dump(results, open(HERE / "out" / "adj_observer.json", "w"), indent=1)
