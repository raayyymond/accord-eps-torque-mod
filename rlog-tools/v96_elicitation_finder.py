#!/usr/bin/env python3
r"""Find the operator's deliberate low-speed elicitation blocks in routes `7e` / `7f`, split them
into ENGAGED and DISENGAGED arms, and rank the individual events inside each one by 6-9 Hz
column-torque energy (the kit's grinding / micro-ratchet instrument).

DEFINITIONS, stated once so the plots and the timestamps mean the same thing:
  * "low speed"      |vEgo| < 20 km/h                        -- the parking regime he describes
  * "override push"  |0x18F STEER_TORQUE_SENSOR| > 1200      -- the kit's `steeringPressed` threshold
  * "block"          contiguous low-speed time with push duty > 0.15 over a 2 s window,
                     gaps < 4 s bridged, >= 6 s long
  * "event"          one contiguous push run >= 0.15 s inside a block, anchored at its |tq| peak
  * band envelope    |hilbert(bandpass 6-9 Hz, 4th-order zero-phase Butterworth)| on `tq`, 100 Hz

🛑 The 6-9 Hz envelope is an INSTRUMENT, not a symptom.  It ranks candidate windows for plotting.
Whether a given window is the grinding or the micro-ratchet is the operator's call, not the
script's.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CACHE = {r: ROOT / "analysis-2020accord" / f"_cache_r{r}" / f"r{r}.npz" for r in ("7e", "7f")}

FS = 100.0
V_LOW_KMH = 20.0
PUSH = 1200.0
BAND = (6.0, 9.0)


def band_env(x, lo=BAND[0], hi=BAND[1], fs=FS):
    sos = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return np.abs(hilbert(sosfiltfilt(sos, x - np.mean(x))))


def runs(mask):
    d = np.diff(mask.astype(np.int8))
    s = list(np.where(d == 1)[0] + 1)
    e = list(np.where(d == -1)[0] + 1)
    if mask[0]:
        s = [0] + s
    if mask[-1]:
        e = e + [len(mask)]
    return list(zip(s, e))


def load(r):
    z = np.load(CACHE[r], allow_pickle=True)
    return dict(t=np.asarray(z["t"], float),
                v=np.abs(np.asarray(z["cs_v"], float)) * 3.6,
                lat=np.asarray(z["cc_lat"], float) > 0.5,
                ang=np.asarray(z["ang"], float),
                rate_c=np.asarray(z["rate_c"], float),
                wang=np.asarray(z["wang"], float),
                cs_rate=np.asarray(z["cs_rate"], float),
                tq=np.asarray(z["tq"], float),
                cmd=np.asarray(z["e4tq"], float),
                req=np.asarray(z["e4req"], float),
                sstat=np.asarray(z["sstat"], float),
                sca=np.asarray(z["sca"], float))


def blocks(D, min_sec=6.0, bridge_sec=4.0):
    t, v, tq = D["t"], D["v"], D["tq"]
    push = np.abs(tq) > PUSH
    w = int(2.0 * FS)
    duty = np.convolve(push.astype(float), np.ones(w) / w, mode="same")
    m = (v < V_LOW_KMH) & (duty > 0.15)
    out = []
    for a, b in runs(m):
        if out and t[a] - out[-1][1] < bridge_sec:
            out[-1] = (out[-1][0], t[min(b, len(t) - 1)])
        else:
            out.append((t[a], t[min(b, len(t) - 1)]))
    return [(a, b) for a, b in out if b - a >= min_sec]


def events_in(D, t0, t1, env):
    t, tq, lat = D["t"], D["tq"], D["lat"]
    sl = (t >= t0) & (t <= t1)
    idx = np.where(sl)[0]
    push = np.abs(tq[idx]) > PUSH
    if not push.any():
        return []
    ev = []
    for a, b in runs(push):
        i0, i1 = idx[a], idx[min(b, len(idx) - 1)]
        if t[i1] - t[i0] < 0.15:
            continue
        k = i0 + int(np.argmax(np.abs(tq[i0:i1 + 1])))
        w = slice(max(0, k - 50), min(len(t), k + 50))
        ev.append(dict(t_peak=float(t[k]), t0=float(t[i0]), t1=float(t[i1]),
                       dur=float(t[i1] - t[i0]), tq_peak=float(tq[k]),
                       ang_at_peak=float(D["ang"][k]),
                       ang_span=float(D["ang"][i0:i1 + 1].max() - D["ang"][i0:i1 + 1].min()),
                       cmd_absmax=float(np.abs(D["cmd"][i0:i1 + 1]).max()),
                       cmd_rail_duty=float(np.mean(np.abs(D["cmd"][i0:i1 + 1]) >= 4090)),
                       v_mean=float(D["v"][i0:i1 + 1].mean()),
                       eng=bool(lat[i0:i1 + 1].mean() > 0.5),
                       env_p95=float(np.percentile(env[w], 95)),
                       env_med=float(np.median(env[w]))))
    return ev


def mmss(x):
    return f"{int(x)//60}:{int(x)%60:02d}.{int((x%1)*10)}"


if __name__ == "__main__":
    report = {}
    for r in ("7e", "7f"):
        D = load(r)
        env = band_env(D["tq"])
        bl = blocks(D)
        print("=" * 110)
        print(f"ROUTE {r}   elicitation blocks  (|v| < {V_LOW_KMH:.0f} km/h, "
              f"|driver torque| > {PUSH:.0f} duty > 0.15)")
        print(f"  {'#':>2} {'start':>8} {'end':>8} {'dur':>6} {'eng%':>6} {'v med':>6} "
              f"{'|ang|max':>8} {'events':>7} {'6-9Hz p95':>10}")
        recs = []
        for i, (a, b) in enumerate(bl):
            sl = (D["t"] >= a) & (D["t"] <= b)
            ev = events_in(D, a, b, env)
            rec = dict(i=i, t0=a, t1=b, dur=b - a, eng=float(D["lat"][sl].mean()),
                       v_med=float(np.median(D["v"][sl])),
                       ang_absmax=float(np.abs(D["ang"][sl]).max()),
                       n_events=len(ev), env_p95=float(np.percentile(env[sl], 95)),
                       events=ev)
            recs.append(rec)
            print(f"  {i:>2} {mmss(a):>8} {mmss(b):>8} {b-a:6.1f} {100*rec['eng']:5.0f}% "
                  f"{rec['v_med']:6.1f} {rec['ang_absmax']:8.0f} {len(ev):>7} "
                  f"{rec['env_p95']:10.0f}")
        report[r] = recs
    (ROOT / "analysis-2020accord" / "_r7e_r7f_elicitations.json").write_text(
        json.dumps(report, indent=1))
    print("\nwrote analysis-2020accord/_r7e_r7f_elicitations.json")
