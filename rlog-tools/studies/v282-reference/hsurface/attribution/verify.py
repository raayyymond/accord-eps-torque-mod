"""Two independent second methods for the load-bearing numbers, because a spectral estimator that is
wrong is wrong in every cell at once.

A  IS THE LOOP DELAY REALLY COMMON TO BOTH BUILDS?  The attribution's (a)=0 rests on it.  Measured here
   on the one leg I can see end to end in the cache: controlsState.output -> the 0xE4 command on the bus
   (e4 ~= -4089*output), by cross-correlation on the raw 100 Hz clocks, per route.  If this leg differed
   between V282 and V293 the 'common' claim would already be in trouble.

B  THE H_dwn GAP, BY A TIME-DOMAIN METHOD.  Band-pass both setpoint and achieved, scan the lag, take the
   regression slope at the best lag, per run, median over runs.  No Welch, no coherence, no cross-spectrum.
   It must reproduce the spectral H_dwn to within the split-half floor or the spectral number is not safe.
"""
import sys, math
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import SPD

GR = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
      "TON": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d"],
      "TOFF": ["00000075--6c8687d5bd"]}


def _self_test():
    """The time-domain estimator must recover a known gain and lag on a band-passed synthetic pair."""
    t = np.arange(0, 120, 1 / V.FS)
    rng = np.random.default_rng(5)
    x = V.lowpass(rng.standard_normal(len(t)), 0.9)
    L, g = 9, 1.35
    y = g * np.concatenate([np.zeros(L), x[:-L]])
    sos = signal.butter(4, [0.25, 0.50], btype="band", fs=V.FS, output="sos")
    xb = signal.sosfiltfilt(sos, x)[1000:-1000]     # trim the filter's edge transient, as the real pass does
    yb = signal.sosfiltfilt(sos, y)[1000:-1000]
    gg, ll = td_gain(xb, yb, 60)
    assert abs(gg - g) < 0.03 and abs(ll - L) <= 1, (gg, ll)
    return f"verify self-test OK: time-domain method recovers gain {gg:.3f} (true {g}) and lag {ll} samples (true {L})"


def td_gain(xb, yb, maxlag):
    best, lag = -np.inf, 0
    for k in range(0, maxlag + 1):
        a, b = xb[:len(xb) - k], yb[k:]
        c = float(np.dot(a, b)) / math.sqrt(float(np.dot(a, a) * np.dot(b, b)) + 1e-30)
        if c > best:
            best, lag = c, k
    a, b = xb[:len(xb) - lag], yb[lag:]
    return float(np.dot(a, b) / max(np.dot(a, a), 1e-30)), lag


def main():
    print(_self_test())
    print("\n" + "=" * 128)
    print("A  controlsState.output -> 0xE4 on the bus, per route (1-10 Hz band, xcorr peak).  Same leg,")
    print("   both builds?  The (a)=0 attribution needs this to be flat across builds.")
    print("=" * 128)
    sosA = signal.butter(4, [1.0, 10.0], btype="band", fs=V.FS, output="sos")
    sosB = {f"{f1:.2f}-{f2:.2f}": signal.butter(4, [f1, f2], btype="band", fs=V.FS, output="sos")
            for f1, f2 in [(0.10, 0.25), (0.25, 0.50), (0.50, 1.00)]}
    Bres = {}
    for g, rks in GR.items():
        for rk in rks:
            S = V.load(rk)
            u = V.usable(S)
            out = np.nan_to_num(S["out"]); e4 = np.nan_to_num(S["e4"])
            num = {}
            n = 0
            for a, b in V.runs(u, S["t"], min_s=20.0):
                c = signal.sosfiltfilt(sosA, -out[a:b]); y = signal.sosfiltfilt(sosA, e4[a:b])
                for L in range(-5, 16):
                    ca, ya = (c[:len(c) - L], y[L:]) if L >= 0 else (c[-L:], y[:len(y) + L])
                    num[L] = num.get(L, 0.0) + float(np.dot(ca, ya)) / math.sqrt(float(np.dot(ca, ca) * np.dot(ya, ya)) + 1e-30)
                n += 1
            if n:
                Ls = sorted(num); vals = np.array([num[L] / n for L in Ls])
                ib = int(np.argmax(vals))

                m = u & (np.abs(out) > 0.05)
                scale = float(np.median(e4[m] / (-out[m]))) if m.sum() > 100 else float("nan")
                print(f"   {g:5s} {rk:24s} lag {Ls[ib]*10:4d} ms  peak corr {vals[ib]:+.3f}  runs {n:3d}  "
                      f"e4/(-out) = {scale:8.1f}")
            # B: time-domain H_dwn
            for bn, sos in sosB.items():
                xb = signal.sosfiltfilt(sos, np.nan_to_num(S["setpoint"]))
                yb = signal.sosfiltfilt(sos, np.nan_to_num(S["la_pose"]))
                for lo, hi in SPD:
                    m = V.usable(S, lo, hi)
                    rs = V.runs(m, S["t"], min_s=40.0)
                    gs = []
                    for a, b in rs:
                        if b - a < 4000:
                            continue
                        # trim 5 s of filter edge transient each side -- the self-test shows 1 s is NOT enough
                        gg, ll = td_gain(xb[a + 500:b - 500], yb[a + 500:b - 500], 80)
                        gs.append((gg, ll * 10))
                    for gg2, ll2 in gs:      # pool RUNS across routes within the group; the route id is kept
                        Bres.setdefault((bn, lo, g), []).append((gg2, ll2, rk))
            del S
    print("\n" + "=" * 128)
    print("B  H_dwn (setpoint -> achieved) by the TIME-DOMAIN method, vs the spectral H_dwn from decomp.py.")
    print("   gain = regression slope at the best lag, per >=40 s run (5 s of each end trimmed), median over runs.")
    print("=" * 128)
    print(f"{'band':11s} {'v':7s} {'group':6s} {'td gain':>8s} {'td lag ms':>10s} {'routes':>7s} {'runs':>6s}")
    for bn in sorted(set(k[0] for k in Bres)):
        for lo in [0, 8, 15, 22]:
            for g in ("V282", "TON", "TOFF"):
                v = Bres.get((bn, lo, g))
                if not v:
                    continue
                print(f"{bn:11s} {lo:<7d} {g:6s} {np.median([x[0] for x in v]):8.3f} "
                      f"{np.median([x[1] for x in v]):10.0f} {len(set(x[2] for x in v)):7d} {len(v):6d}")


if __name__ == "__main__":
    main()
