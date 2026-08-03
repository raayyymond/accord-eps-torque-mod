#!/usr/bin/env python3
"""audit_rlog_channels.py -- INSTRUMENT AUDIT: every service in an rlog and its TRUE sample rate.

WHY. The operator feels a highway vibration the kit cannot see. Every instrument used so far is
bandwidth-limited to ~50 Hz (CAN 100.000 Hz, comma IMU 101.02 Hz). If the symptom is above 50 Hz,
every published null about it is SILENCE, NOT ABSENCE. Before paying for a firmware code cave
(this kit's only bricking class) we must know whether ANY logged channel exceeds 100 Hz.

🛑 THE dt-MEAN TRAP. `1/mean(dt)` is biased low by dropped samples: a 1% drop rate drags a 104 Hz
stream to ~103 Hz and has already given this kit a wrong Nyquist. Three estimators are printed:

    med    1/median(dt)                    robust to drops, quantised by the log clock
    latt   LATTICE fit                     dt_i -> k_i = round(dt_i/p), p' = sum(dt)/sum(k)
                                           iterated; the only estimator that is UNBIASED under drops
    mean   1/mean(dt)                      shown ONLY so the bias is visible

The lattice estimator is the load-bearing one. `k_hist` shows the multiplicity histogram: k=1 is a
delivered sample, k>=2 is a gap of that many periods (a drop), which is reported as drop_frac.

Usage:  python audit_rlog_channels.py 4a 20 21          # route tag + segments
        python audit_rlog_channels.py 4a                # default segments
        python audit_rlog_channels.py 47 5
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {"4a": "75604b0a432fdc89_0000004a--346bf31d97",
          "47": "75604b0a432fdc89_00000047--3e0b6134c0",
          "2b": "75604b0a432fdc89_0000002b--7926e8f7e5"}
DEFSEG = {"4a": [20, 21, 22, 23, 24, 25], "47": [5, 6], "2b": [5]}

# services.py's DECLARED frequency, for a declared-vs-measured column
try:
    from cereal.services import SERVICE_LIST
    DECL = {k: v.frequency for k, v in SERVICE_LIST.items()}
except Exception:                                              # pragma: no cover
    DECL = {}


def lattice_rate(t, p0=None, iters=6):
    """Drop-unbiased period estimate.

    Every arrival is assumed to sit on a lattice of period p. dt_i is then k_i*p for integer k_i
    (k_i = 1 normally, k_i = 2 when one sample was dropped, ...). Fitting p = sum(dt)/sum(k) over
    only the dt that snap cleanly to the lattice removes the drop bias that 1/mean(dt) suffers.
    """
    t = np.asarray(t, float)
    dt = np.diff(t)
    dt = dt[dt > 0]
    if len(dt) < 8:
        return np.nan, np.nan, np.nan, {}
    p = float(np.median(dt)) if p0 is None else float(p0)
    for _ in range(iters):
        k = np.round(dt / p)
        ok = (k >= 1) & (k <= 20) & (np.abs(dt / p - k) < 0.35)   # snap tolerance 35% of a period
        if ok.sum() < 8:
            break
        p = float(dt[ok].sum() / k[ok].sum())
    k = np.round(dt / p)
    ok = (k >= 1) & (k <= 20) & (np.abs(dt / p - k) < 0.35)
    resid = float(np.std((dt[ok] / p - k[ok]) * p)) if ok.sum() else np.nan
    kh = {int(v): int(c) for v, c in zip(*np.unique(k[ok].astype(int), return_counts=True))}
    n_lat = k[ok].sum()
    drop = float((n_lat - ok.sum()) / n_lat) if n_lat else np.nan
    return 1.0 / p, resid, drop, kh


# vibration relevance: does the channel carry a mechanical/rotational quantity at all
RELEVANT = {
    "can": "CAN frames: EPS angle/rate/torque, wheel speeds, ABS -- the primary vibration grid",
    "sendcan": "openpilot TX only (LKAS command); not a measurement",
    "accelerometer": "3-axis linear accel -- DIRECT vibration measurement",
    "gyroscope": "3-axis rate -- DIRECT vibration measurement",
    "magnetometer": "magnetic field; no mechanical content",
    "soundPressure": "acoustic LEVEL scalar -- no frequency ceiling, but level-only",
    "rawAudioData": "RAW PCM -- would be the ideal instrument IF logged",
    "audioFeedback": "raw PCM feedback capture -- would be ideal IF logged",
    "carState": "vEgo/angle/torque, resampled from CAN; no new bandwidth",
    "livePose": "kalman-filtered pose; HEAVILY smoothed, no new bandwidth",
    "controlsState": "controller internals; no new bandwidth",
    "lightSensor": "ambient light @100 Hz -- no mechanical content",
    "deviceState": "thermals/CPU; no mechanical content",
}


def audit(tag, segs):
    paths = [RLOGDIR / f"{ROUTES[tag]}--{s}--rlog.zst" for s in segs]
    paths = [p for p in paths if p.exists()]
    print(f"=== route {tag}  segments {segs}  ({len(paths)} rlogs) ===")

    T = defaultdict(list)                 # service -> logMonoTime list
    HW = defaultdict(list)                # service -> hardware timestamp list (sensors)
    can_frames = 0
    can_per_addr = defaultdict(list)      # (src,addr) -> logMonoTime of the CONTAINING can event
    can_intra = []                        # frames per can event
    bustime_seen = {}                     # (src,addr) -> first busTime, or -1 if absent
    audio_info = []

    unknown = 0
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                # union discriminant not in THIS cereal copy => a service the device logs that
                # rlog-tools' log.capnp does not know. Counted, and identified by audit_unknown().
                unknown += 1
                continue
            tm = evt.logMonoTime * 1e-9
            T[w].append(tm)
            if w == "can":
                fl = evt.can
                can_intra.append(len(fl))
                for m in fl:
                    can_frames += 1
                    key = (int(m.src), int(m.address))
                    can_per_addr[key].append(tm)
                    # 🛑 Probe busTime ONCE per address, then never again. A pycapnp attribute miss
                    # raises, and re-raising it on all 283k frames cost >600 s (measured) -- the
                    # exception, not the parse, was the whole runtime.
                    if key not in bustime_seen:
                        try:
                            bustime_seen[key] = int(m.busTime)
                        except Exception:
                            bustime_seen[key] = -1
            elif w in ("accelerometer", "gyroscope", "magnetometer"):
                try:
                    HW[w].append(int(getattr(evt, w).timestamp) * 1e-9)
                except Exception:
                    pass
            elif w in ("rawAudioData", "audioFeedback"):
                try:
                    a = evt.rawAudioData if w == "rawAudioData" else evt.audioFeedback.audio
                    audio_info.append((len(bytes(a.data)), int(a.sampleRate)))
                except Exception:
                    audio_info.append((-1, -1))

    print(f"\n--- SERVICE INVENTORY ({len(T)} services present, "
          f"{unknown} messages on an UNKNOWN union discriminant) ---")
    hdr = (f"{'service':28s} {'n':>7s} {'span_s':>8s} {'med_Hz':>9s} {'latt_Hz':>9s} "
           f"{'mean_Hz':>9s} {'jit_ms':>7s} {'drop%':>6s} {'decl':>7s}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for w in sorted(T, key=lambda k: -len(T[k])):
        t = np.array(sorted(T[w]))
        span = t[-1] - t[0] if len(t) > 1 else 0.0
        if len(t) < 3:
            print(f"{w:28s} {len(t):7d} {span:8.2f} {'-':>9s} {'-':>9s} {'-':>9s} "
                  f"{'-':>7s} {'-':>6s} {DECL.get(w, float('nan')):7.2f}")
            rows.append((w, len(t), span, np.nan, np.nan))
            continue
        dt = np.diff(t)
        f_med = 1 / np.median(dt)
        f_lat, resid, drop, kh = lattice_rate(t)
        f_mean = 1 / dt.mean()
        # ⚠ BURST GUARD. The lattice fit assumes a periodic emitter. androidLog/logMessage are
        # event-driven bursts, and fitting a lattice to a burst returns a meaningless kHz figure.
        # A channel is called PERIODIC only if it actually covers its own span at that rate.
        periodic = np.isfinite(f_lat) and (len(t) / max(span, 1e-9)) > 0.5 * f_lat
        print(f"{w:28s} {len(t):7d} {span:8.2f} {f_med:9.4f} {f_lat:9.4f} {f_mean:9.4f} "
              f"{1e3 * resid:7.3f} {100 * drop:6.2f} {DECL.get(w, float('nan')):7.2f}"
              f"{'' if periodic else '   <- BURSTY, rate meaningless'}")
        rows.append((w, len(t), span, f_med, f_lat if periodic else np.nan))

    print("\n--- ANYTHING ABOVE 100 Hz? (the whole point) ---")
    fast = [(w, n, f) for w, n, s, fm, f in rows if np.isfinite(f) and f > 100.5]
    for w, n, f in fast:
        print(f"  ** {w:26s} {f:9.4f} Hz  (n={n})  Nyquist {f / 2:.2f} Hz")
    top = max((r for r in rows if np.isfinite(r[4])), key=lambda r: r[4])
    print(f"  HIGHEST periodic service: {top[0]} at {top[4]:.4f} Hz => NYQUIST {top[4] / 2:.4f} Hz")
    print("  (accelerometer/gyroscope logMonoTime rates are inflated by scheduler jitter; the "
          "HARDWARE clock below is authoritative)")

    print("\n--- IMU: hardware clock vs logMonoTime (the hw clock is the real sample clock) ---")
    for w in ("accelerometer", "gyroscope", "magnetometer"):
        if not HW[w]:
            continue
        hw = np.array(sorted(HW[w]))
        f_lat, resid, drop, kh = lattice_rate(hw)
        f_med = 1 / np.median(np.diff(hw))
        print(f"  {w:14s} hw n={len(hw):6d}  med {f_med:9.4f} Hz  LATTICE {f_lat:9.4f} Hz  "
              f"jit {1e3 * resid:.4f} ms  drop {100 * drop:.2f}%  k_hist {kh}")
        print(f"  {'':14s} => NYQUIST {f_lat / 2:.4f} Hz")

    print("\n--- CAN: is there a finer clock than the 100 Hz aggregation grid? ---")
    ce = np.array(sorted(T["can"]))
    f_lat, resid, drop, kh = lattice_rate(ce)
    print(f"  can EVENTS: n={len(ce)}  lattice {f_lat:.4f} Hz  jitter {1e3 * resid:.3f} ms  "
          f"k_hist {kh}")
    ci = np.array(can_intra)
    print(f"  frames per can event: n={len(ci)}  mean {ci.mean():.2f}  "
          f"min {ci.min()}  max {ci.max()}  total frames {can_frames}")
    nz = sum(1 for v in bustime_seen.values() if v not in (0, -1))
    absent = sum(1 for v in bustime_seen.values() if v == -1)
    print(f"  busTime (deprecated panda hw timestamp): {nz}/{len(bustime_seen)} addresses have any "
          f"NON-ZERO value ({absent} raised on access) "
          f"=> {'USABLE' if nz else 'ALL ZERO / ABSENT -- no sub-grid CAN clock'}")

    print("\n--- per-address CAN rates (top 30 by count) ---")
    print(f"  {'src:addr':>12s} {'n':>7s} {'med_Hz':>9s} {'latt_Hz':>9s} {'drop%':>6s}")
    for (src, addr), tl in sorted(can_per_addr.items(), key=lambda kv: -len(kv[1]))[:30]:
        t = np.array(tl)
        if len(t) < 8:
            continue
        f_lat, resid, drop, kh = lattice_rate(t)
        print(f"  {src:3d}:0x{addr:03X} {len(t):10d} {1 / np.median(np.diff(t)):9.4f} "
              f"{f_lat:9.4f} {100 * drop:6.2f}")

    print("\n--- RAW AUDIO ---")
    if audio_info:
        n = np.array([a for a, b in audio_info])
        sr = np.array([b for a, b in audio_info])
        print(f"  {len(audio_info)} raw-audio messages  bytes/msg {n.min()}..{n.max()}  "
              f"sampleRate {sorted(set(sr.tolist()))}")
    else:
        print("  ZERO rawAudioData / audioFeedback messages in these segments.")
        print("  services.py declares rawAudioData should_log="
              f"{SERVICE_LIST['rawAudioData'].should_log if DECL else '?'} "
              f"=> NEVER written to rlog by design.")
    return T, can_per_addr


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "4a"
    segs = [int(x) for x in sys.argv[2:]] or DEFSEG[tag]
    audit(tag, segs)
