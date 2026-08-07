#!/usr/bin/env python3
"""Head-to-head grinding quantification across V75 / V76 / V80 -- the DAMPER dose ladder.

    build   route                                      k (loop gain)   delivered damper @ r=99
    V75     75604b0a432fdc89_0000005e--857d0bd164       1.5798         137 creep -> 56 @ 60 km/h
    V76     75604b0a432fdc89_00000065--ae43aa0f27       1.3866         137 flat to 80 km/h
    V80     75604b0a432fdc89_00000066--276b942769       4.1597         412 at EVERY speed

Operator verdicts: V75 BEST EVER (pre-fault portion only, faults at t=284.805 s);
V76 "still grind #1 + micro-ratchet at creep"; V80 WORST EVER (loud, whole-car, ~90% of engaged
time, low AND high speed).

🛑 EVERY number here comes out of the kit's EXISTING harness (`_grind2_lib` + `_r47_lib` +
`_r4f_lib`'s lattice-fs fix), so a ratio computed here is computed with the identical instrument
as every prior route this kit has scored.  What this file adds:
  * the V80/route-66 extract (its OWN cache `_cache_r66x/`, never `_cache_r66/` -- a sibling agent
    owns that);
  * a fourth band `26-31` for the ~28 Hz lane-change transient (`G.BANDS` tops out at 28.0, which
    pins a 28.1-28.5 Hz line to the band edge);
  * speed-STRATIFIED band tables with episode-bootstrap CIs and a per-route SPLIT-HALF NULL;
  * the relay/limit-cycle falsifier for V80 (peak f0, bandwidth/Q, crest factor, speed slope).

🛑 Run with an interpreter that has numpy + scipy + pycapnp + zstandard. On this machine that is
`C:/Users/dudei/anaconda3/envs/bin_decompile/python.exe` -- the anaconda BASE env has a broken
numpy DLL load and no capnp.

Usage:
    python compare_v75_v76_v80_grind.py extract   # route 66 -> _cache_r66x/  (~6 min, 15 segments)
    python compare_v75_v76_v80_grind.py analyze   # S0-S7: exposure, band table, split-half null,
                                                  #        ratios, dose-response, identity, duty
    python compare_v75_v76_v80_grind.py deep      # D1-D5: line-or-floor spectra, control channels
                                                  #        (angle / IMU / command), the 100 km/h
                                                  #        event, 30-49 Hz duty, creep cell census
    python compare_v75_v76_v80_grind.py deep2     # E1-E5: duty at three thresholds, the FFT-free
                                                  #        near-Nyquist test, event uniqueness,
                                                  #        raw waveform + aliasing, dose table
    python compare_v75_v76_v80_grind.py deep3     # F1-F3: the V80 limit-cycle event class, f0 vs
                                                  #        speed and amplitude, per-segment map
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE66 = "75604b0a432fdc89_00000066--276b942769"
SEGS66 = list(range(15))
CACHE66 = ROOT / "_cache_r66x"            # ★ MY cache. `_cache_r66/` belongs to a sibling agent.
PFX66 = "r66xs"

KMH = 1.0 / 3.6
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]


# =================================================================================================
#  PART 1 -- the V80 / route-66 extract.  Field names are v77sizing_extract.py's, verbatim, so the
#  per-segment files drop straight into `_grind2_lib.wrecs` / `_r31_common.load`.
# =================================================================================================
def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


def u16be(d, i):
    return (d[i] << 8) | d[i + 1]


def wheel_speeds_kph(d):
    fl = (d[0] << 7) | (d[1] >> 1)
    fr = ((d[1] & 0x01) << 14) | (d[2] << 6) | (d[3] >> 2)
    rl = ((d[3] & 0x03) << 13) | (d[4] << 5) | (d[5] >> 3)
    rr = ((d[5] & 0x07) << 12) | (d[6] << 4) | (d[7] >> 4)
    return fl * 0.01, fr * 0.01, rl * 0.01, rr * 0.01


def held_last(t_out, t_in, v_in, fill):
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in), t_out, side="right") - 1
    return np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)]).astype(float)


def _grid(t_out, t_in, v_in):
    t_in = np.asarray(t_in, float)
    if not len(t_in):
        return np.full(len(t_out), np.nan)
    return np.interp(t_out, t_in, np.asarray(v_in, float))


def extract66(paths):
    from rlog_parse import read_messages

    rows, seg_of_row = [], []
    last18, lastE4 = None, (0.0, 0)
    raw14_b4, raw14_t = [], []
    raw18_st, raw18_b4, raw18_t = [], [], []
    raw1ab_t, raw1ab_b0 = [], []
    ws_t, ws_v = [], []
    sc_t, sc_tq, sc_rq = [], [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    co = {"t": [], "req": [], "can": []}
    a_hw, a_mono, a_v, a_st = [], [], [], []
    events = []

    for si, p in enumerate(paths):
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    src, addr = int(m.src), int(m.address)
                    d = bytes(m.dat)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_t.append(tm)
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        raw18_b4.append(d[4])
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 1 and addr == 0x1AB and len(d) >= 1:
                        raw1ab_t.append(tm)
                        raw1ab_b0.append(d[0])
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                    elif src == 1 and addr == 0x1D0 and len(d) >= 8:
                        ws_t.append(tm)
                        ws_v.append(wheel_speeds_kph(d))
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_t.append(tm)
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
                        seg_of_row.append(si)
            elif w == "sendcan":
                for m in evt.sendcan:
                    if int(m.src) == 1 and int(m.address) == 0x0E4:
                        d = bytes(m.dat)
                        if len(d) >= 3:
                            sc_t.append(tm)
                            sc_tq.append(float(i16be(d, 0)))
                            sc_rq.append(float((d[2] >> 7) & 1))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                for k, attr in (("press", "steeringPressed"), ("std", "standstill"),
                                ("lblink", "leftBlinker"), ("rblink", "rightBlinker")):
                    try:
                        cs[k].append(float(bool(getattr(c, attr))))
                    except Exception:
                        cs[k].append(0.0)
                try:
                    cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
                except Exception:
                    cs["gear"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                try:
                    cc["req"].append(float(evt.carControl.actuators.torque))
                except Exception:
                    cc["req"].append(np.nan)
            elif w == "carOutput":
                try:
                    a = evt.carOutput.actuatorsOutput
                    co["t"].append(tm); co["req"].append(float(a.torque))
                    try:
                        co["can"].append(float(a.torqueOutputCan))
                    except Exception:
                        co["can"].append(np.nan)
                except Exception:
                    pass
            elif w == "accelerometer":
                try:
                    m = evt.accelerometer
                    a_hw.append(int(m.timestamp) * 1e-9); a_mono.append(tm)
                    a_v.append(list(m.acceleration.v)); a_st.append(int(m.acceleration.status))
                except Exception:
                    pass
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        events.append((tm, str(e.name), bool(getattr(e, "enable", False)),
                                       bool(getattr(e, "softDisable", False)),
                                       bool(getattr(e, "immediateDisable", False)),
                                       bool(getattr(e, "noEntry", False))))
                    except Exception:
                        continue
        print(f"  seg {si} done, rows so far {len(rows)}", flush=True)

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    t0 = d["t"][0]
    d["t"] = d["t"] - t0
    d["seg"] = np.array(seg_of_row, float)

    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))
    cot = np.array(co["t"], float) - t0
    d["co_req"] = _grid(d["t"], cot, co["req"])
    d["co_tqcan"] = _grid(d["t"], cot, co["can"])
    sct = np.array(sc_t, float) - t0
    d["sc_tq"] = _grid(d["t"], sct, sc_tq)
    d["sc_req"] = held_last(d["t"], sct, sc_rq, 0.0) if len(sct) else np.full(len(d["t"]), np.nan)

    wst = np.array(ws_t, float) - t0
    wsv = np.array(ws_v, float).reshape(-1, 4)
    for i, k in enumerate(("fl", "fr", "rl", "rr")):
        d["ws_" + k] = (_grid(d["t"], wst, wsv[:, i] * KMH) if len(wst)
                        else np.full(len(d["t"]), np.nan))

    # The probe byte is kept RAW (`probe`) plus the two slices every build shares. V80's bit
    # semantics belong to the sibling agent's decoder; nothing here depends on them.
    p = d["probe"].astype(int)
    d["field"] = (p & 0xF8).astype(float)
    d["status"] = (p & 0x07).astype(float)
    r1ab_t = np.array(raw1ab_t, float) - t0
    r1ab_b0 = np.array(raw1ab_b0, int)
    d["dtc_active"] = (held_last(d["t"], r1ab_t, ((r1ab_b0 >> 2) & 1).astype(float), np.nan)
                       if len(r1ab_t) else np.full(len(d["t"]), np.nan))

    A = np.array(a_v, float).reshape(-1, 3) if len(a_v) else np.zeros((0, 3))
    if len(A):
        off_a = float(np.median(np.array(a_mono, float) - np.array(a_hw, float)))
        at = np.array(a_hw, float) + off_a - t0
        means = np.array([A[:, i].mean() for i in range(3)])
        vi = int(np.argmin(np.abs(np.abs(means) - 9.807)))
        d["imu_vert"] = _grid(d["t"], at, A[:, vi])
        print(f"  IMU gravity means {means} -> vertical = {'xyz'[vi]}")
    else:
        d["imu_vert"] = np.full(len(d["t"]), np.nan)

    CACHE66.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE66 / "r66.npz", **d,
        raw14_t=np.array(raw14_t, float) - t0, raw14_b4=np.array(raw14_b4, np.int16),
        raw18_t=np.array(raw18_t, float) - t0, raw18_st=np.array(raw18_st, np.int16),
        raw18_b4=np.array(raw18_b4, np.int16),
        raw1ab_t=r1ab_t, raw1ab_b0=r1ab_b0.astype(np.int16),
        ws_t=wst, ws_kph=wsv, sc_t=sct, sc_tq_raw=np.array(sc_tq, float),
        cs_t=cst, cs_v_raw=np.array(cs["v"], float),
        seg_bounds=np.array([[s, float(d["t"][d["seg"] == s].min()),
                              float(d["t"][d["seg"] == s].max())]
                             for s in np.unique(d["seg"])], float),
        t0_mono=np.array([t0]), probe_build=np.array(["V80"]))
    (CACHE66 / "r66_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    print(f"\nroute 66: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  "
          f"vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f}")
    print("  RAW 0x14A byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)))
    print(f"  sstat values: {dict(zip(*[x.tolist() for x in np.unique(d['sstat'], return_counts=True)]))}")
    print(f"  latActive {100 * np.mean(d['cc_lat'] > 0.5):.1f}% of {d['t'][-1]:.0f} s")
    print(f"  dtc_active max {np.nanmax(d['dtc_active']) if len(r1ab_t) else float('nan')}")
    return d


PASS_1D = ["t", "ang", "rate_c", "wang", "tq", "rate_f", "sca", "sstat", "slow3", "e4tq", "e4req",
           "cs_v", "cs_eng", "cs_ang", "cs_tq", "cs_press", "cs_gear", "cs_std", "cs_lblink",
           "cs_rblink", "cs_lchg", "cc_lat", "cc_en", "cc_req", "co_req", "co_tqcan", "sc_tq",
           "sc_req", "ws_fl", "ws_fr", "ws_rl", "ws_rr", "dtc_active", "imu_vert",
           "probe", "field", "status"]


def split66():
    """Split the route-global extract into per-segment files, `t` RESET to 0 -- the schema every
    `_r*_lib.py` assumes."""
    d = np.load(CACHE66 / "r66.npz")
    seg = d["seg"]
    census = {}
    for s in np.unique(seg.astype(int)):
        m = seg == s
        if m.sum() < 256:
            print(f"  seg{s}: {int(m.sum())} frames -- SKIPPED")
            continue
        out = {k: d[k][m] for k in PASS_1D if k in d.files}
        out["t"] = out["t"] - out["t"][0]
        out["probe_build"] = np.array(["V80"])
        np.savez_compressed(CACHE66 / f"{PFX66}{s}.npz", **out)
        tt, vv, ll = out["t"], np.abs(out["cs_v"]), out["cc_lat"] > 0.5
        census[int(s)] = dict(n=int(m.sum()), sec=float(tt[-1] - tt[0]),
                              v_mean=float(vv.mean()), v_max=float(vv.max()),
                              lat_frac=float(ll.mean()), eng_sec=float(ll.sum() * 0.01))
        print(f"  seg{s}: n={int(m.sum()):6d} {tt[-1] - tt[0]:6.1f}s  v_mean {vv.mean():5.2f} "
              f"(max {vv.max():5.2f})  engaged {ll.mean() * 100:5.1f}% ({ll.sum() * .01:5.1f}s)")
    (CACHE66 / "r66_census_seg.json").write_text(json.dumps(census, indent=1))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "extract":
    argv = [int(x) for x in sys.argv[2:] if x.isdigit()]
    extract66([RLOGDIR / f"{ROUTE66}--{s}--rlog.zst" for s in (argv or SEGS66)])
    split66()
    raise SystemExit(0)


# =================================================================================================
#  PART 2 -- the analysis.  Everything numeric comes from the kit's own harness.
# =================================================================================================
import pickle  # noqa: E402

import _grind2_lib as G  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r31_common as C31  # noqa: E402
import v77sizing_lib as V76LIB  # noqa: E402  -- registers V76/r65 (and asserts its own k)
import v78_symptom_lib as V75LIB  # noqa: E402  -- registers V75/r5e (pre-fault) + V59..V74

# ---- the damper dose ladder ---------------------------------------------------------------------
# k = ramp-regime incremental loop gain, counts of damper per count of motor rate. V74/V75 from
# `v78_symptom_lib.K_RAMP`; V76 re-derived by `v77sizing_lib`; V80 supplied by the orchestrator.
K = {"V74/r5d": 0.5799, "V76/r65": 1.3866, "V75/r5e": 1.5798, "V80/r66": 4.1597}
# Delivered damper counts at the 18-22 Hz burst-median motor rate r = 99 counts, per speed.
DELIVERED = {"V74/r5d": "?", "V76/r65": "137 flat to 80 km/h",
             "V75/r5e": "137 creep -> 56 @ 60 km/h", "V80/r66": "412 at EVERY speed"}
LADDER = ["V74/r5d", "V76/r65", "V75/r5e", "V80/r66"]
TRIO = ["V75/r5e", "V76/r65", "V80/r66"]
PARKED = {"V74/r5d": [2, 3, 9], "V75/r5e": [0], "V76/r65": [0, 10], "V80/r66": []}

# ---- bands ---------------------------------------------------------------------------------------
# G.BANDS tops out at 28.0, which PINS a 28.1-28.5 Hz lane-change line to the band edge, so a
# dedicated 26-31 band is added. 32-38 is a second pre-declared NEGATIVE CONTROL that (unlike
# 24-28) does not overlap the lane-change band.
BANDS_EXT = dict(G.BANDS)
BANDS_EXT["26-31"] = (26.0, 31.0)
BANDS_EXT["32-38"] = (32.0, 38.0)
BANDS_EXT["35-39"] = (35.0, 39.0)      # where a 3rd harmonic of ~21 Hz FOLDS (3*21=63 -> ~37 Hz)
BANDS_EXT["17-23"] = (17.0, 23.0)      # grind #1, widened for crest/Q so the peak is not on an edge
G.BANDS = BANDS_EXT

BAND4 = [("micro-ratchet ~7.8 Hz", "6-9"), ("GRIND #1 18-22 Hz", "18-22"),
         ("lane-change ~28 Hz", "26-31"), ("GRIND #2 40-49 Hz", "40-49")]
NEGCTRL = "32-38"

STRATA = [("creep <10 kph", 0.0, 10 * KMH), ("10-40 kph", 10 * KMH, 40 * KMH),
          ("40-80 kph", 40 * KMH, 80 * KMH), (">80 kph", 80 * KMH, 1e9)]

MYPKL = CACHE66 / "records_4build_extbands.pkl"


def register():
    G.BUILDS["V80/r66"] = dict(cache=CACHE66, pfx=PFX66, segs=SEGS66, kd=K["V80/r66"])
    R4F.install_fs()          # lattice fs for ALL builds -- never one arm of a contrast


def bandpass(x, fs, lo, hi):
    x = np.asarray(x, float)
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    y = x - (c[0] * r + c[1])
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(y))


def augment2(recs):
    """Crest factor, band RMS and the relay falsifiers, computed by re-slicing each window's own
    cache at its own `t0` -- the `_r47_lib.augment` pattern, so no second window loop can drift."""
    by = {}
    for r in recs:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    for (build, seg), rs in by.items():
        B = G.BUILDS[build]
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            continue
        d = C31.load(seg, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        t = np.asarray(d["t"], float)
        tq = np.asarray(d["tq"], float)
        n = G.NFFT
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            xw = tq[i0:i0 + n]
            if len(xw) < n or not np.all(np.isfinite(xw)):
                for k in ("crest18", "rms18", "crest40", "rms40", "crest6", "rms6", "pp18"):
                    r[k] = np.nan
                continue
            for tag, (lo, hi) in (("18", (17.0, 23.0)), ("40", (40.0, 49.0)), ("6", (6.0, 9.0))):
                b = bandpass(xw, fs, lo, hi)
                cw = b[int(0.15 * n):int(0.85 * n)]        # drop the filter's edge transients
                rms = float(np.sqrt(np.mean(cw ** 2)))
                r["rms" + tag] = rms
                r["crest" + tag] = float(np.max(np.abs(cw)) / rms) if rms > 0 else np.nan
            r["pp18"] = 2.0 * r["e_18-22"]                 # envelope AMPLITUDE -> peak-to-peak
    return recs


def build_records(rebuild=False):
    register()
    if MYPKL.exists() and not rebuild:
        with open(MYPKL, "rb") as fh:
            st = pickle.load(fh)
        if st.get("__bands__") == sorted(BANDS_EXT) and all(b in st for b in LADDER):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    st = {"__bands__": sorted(BANDS_EXT)}
    for b in LADDER:
        print(f"  wrecs {b} ...", flush=True)
        rs = R47.augment(G.wrecs(b))
        rs = augment2(rs)
        for r in rs:
            r["k"] = K[b]
        st[b] = rs
        print(f"    {len(rs)} windows", flush=True)
    CACHE66.mkdir(exist_ok=True)
    with open(MYPKL, "wb") as fh:
        pickle.dump(st, fh)
    return {k: v for k, v in st.items() if not k.startswith("__")}


def eng(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 1 and r["seg"] not in PARKED.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def nunits(rs, key=None):
    key = key or G.EPKEY
    return len({r[key] for r in rs})



# =================================================================================================
#  PART 3 -- the report
# =================================================================================================
RNG = np.random.default_rng(80_75_76)
OUT = {}


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100, flush=True)


def frac_ci(rs, key, thr, rng, nboot=3000, unit=None):
    """(fraction of windows with key > thr, lo, hi, n) resampling `unit` (default G.EPKEY)."""
    unit = unit or G.EPKEY
    grp = {}
    for r in rs:
        grp.setdefault(r[unit], []).append(r)
    per = [np.array([1.0 if (np.isfinite(r[key]) and r[key] > thr) else 0.0 for r in v])
           for v in grp.values()]
    per = [p for p in per if len(p)]
    if not per:
        return np.nan, np.nan, np.nan, 0
    allv = np.concatenate(per)
    dr = np.empty(nboot)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        dr[b] = np.mean(np.concatenate([per[j] for j in i]))
    return (float(allv.mean()), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5)),
            len(allv))


def theil_sen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 3:
        return np.nan
    sl = []
    for i in range(len(x)):
        dx = x[i + 1:] - x[i]
        dy = y[i + 1:] - y[i]
        ok = dx != 0
        sl.append(dy[ok] / dx[ok])
    sl = np.concatenate(sl) if sl else np.array([])
    return float(np.median(sl)) if len(sl) else np.nan


def theil_sen_boot(rs, xk, yk, rng, nboot=1200, unit=None):
    unit = unit or G.EPKEY
    grp = {}
    for r in rs:
        grp.setdefault(r[unit], []).append(r)
    per = list(grp.values())
    pt = theil_sen(G.col(rs, xk), G.col(rs, yk))
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        rr = [r for j in i for r in per[j]]
        dr[b] = theil_sen(G.col(rr, xk), G.col(rr, yk))
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def main():
    G.EPKEY = "blk"                       # ~10.2 s blocks nested in engagement runs
    R = build_records()

    # ---------------------------------------------------------------- S0 EXPOSURE ---------------
    hdr("S0  EXPOSURE CENSUS -- engaged only, parked segments dropped")
    print(f"{'build':10s} {'k':>7s}  {'wins':>5s} {'sec':>7s} {'blk':>4s} {'run':>4s} | "
          + " ".join(f"{nm:>13s}" for nm, _, _ in STRATA))
    OUT["exposure"] = {}
    for b in LADDER:
        e = eng(R[b], b)
        row = [f"{b:10s} {K[b]:7.4f}  {len(e):5d} {len(e) * 1.28:7.1f} "
               f"{nunits(e,'blk'):4d} {nunits(e,'ep'):4d} |"]
        st = {}
        for nm, lo, hi in STRATA:
            s = eng(R[b], b, lo, hi)
            row.append(f"  {len(s):4d}w/{nunits(s,'blk'):2d}b ")
            st[nm] = dict(n=len(s), blk=nunits(s, "blk"), ep=nunits(s, "ep"),
                          v_med=float(np.median(G.col(s, "v"))) if s else float("nan"),
                          v_iqr=[float(np.percentile(G.col(s, "v"), 25)),
                                 float(np.percentile(G.col(s, "v"), 75))] if s else None,
                          eff_med=float(np.median(G.col(s, "eff"))) if s else float("nan"),
                          rate_med=float(np.median(G.col(s, "rate"))) if s else float("nan"))
        print("".join(row))
        OUT["exposure"][b] = dict(k=K[b], n=len(e), sec=len(e) * 1.28, strata=st)
    print("\n  per-stratum MEDIAN SPEED v (m/s) / sustained EFFORT e (counts) / |angle rate| r:")
    for nm, lo, hi in STRATA:
        print(f"  {nm:14s} " + "  ".join(
            "%s: v=%5.2f e=%6.0f r=%5.1f" % (
                b.split('/')[0],
                OUT['exposure'][b]['strata'][nm]['v_med'],
                OUT['exposure'][b]['strata'][nm]['eff_med'],
                OUT['exposure'][b]['strata'][nm]['rate_med']) for b in LADDER))

    # ---------------------------------------------------------------- S1 BAND TABLE -------------
    hdr("S1  SPEED-STRATIFIED BAND TABLE -- engaged only.  median [2.5%, 97.5%] episode-bootstrap\n"
        "    p_band = spectral PROMINENCE = peak power / local median floor  (the band's EXCESS\n"
        "             over its own local noise floor; dimensionless, exposure-free)\n"
        "    e_band = p99 analytic band-envelope AMPLITUDE of the torsion bar, in counts\n"
        "             (peak-to-peak = 2x this)")
    OUT["bands"] = {}
    for label, bd in BAND4:
        print(f"\n---- {label}   [{bd} Hz] ----")
        print(f"{'stratum':14s} {'build':10s} {'n':>4s} {'blk':>4s} | "
              f"{'prominence p':>26s} | {'envelope e (counts)':>28s}")
        for nm, lo, hi in STRATA:
            for b in LADDER:
                s = eng(R[b], b, lo, hi)
                if len(s) < 5:
                    print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                          f"{'-- no sample --':>26s} |")
                    continue
                pp = G.boot_median_ci(s, "p_" + bd, RNG, nboot=2000)
                ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=2000)
                print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                      f"{pp[0]:8.2f} [{pp[1]:6.2f},{pp[2]:6.2f}] |"
                      f"{ee[0]:9.1f} [{ee[1]:7.1f},{ee[2]:7.1f}]")
                OUT["bands"].setdefault(bd, {}).setdefault(nm, {})[b] = dict(
                    n=len(s), blk=nunits(s, "blk"), p=list(pp), e=list(ee))

    # ---------------------------------------------------------------- S2 SPLIT-HALF NULL --------
    hdr("S2  SPLIT-HALF NULL -- each route halved against ITSELF, IDENTICAL estimator.\n"
        "    Any between-route ratio inside its own null interval is NOT distinguishable from\n"
        "    route/exposure noise.  300 random halvings, cell-stratified, blocks resampled.")
    OUT["null"] = {}
    print(f"{'band':8s} {'build':10s} {'key':3s} {'null median':>12s} {'null 95% interval':>26s}")
    for _, bd in BAND4:
        for b in LADDER:
            e = eng(R[b], b)
            for key, tag in (("e_" + bd, "e"), ("p_" + bd, "p")):
                n = G.split_half_null(e, key, RNG, nrep=300, min_ep=2, min_win=4)
                print(f"{bd:8s} {b:10s} {tag:3s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]")
                OUT["null"].setdefault(bd, {}).setdefault(b, {})[tag] = list(n)
        print()

    # ---------------------------------------------------------------- S3 RATIOS -----------------
    hdr("S3  BETWEEN-ROUTE RATIOS -- cell-stratified (speed x effort x |rate| cells occupied by\n"
        "    BOTH routes), blocks resampled.  Read every ratio against S2's null for the same band.")
    OUT["ratios"] = {}
    PAIRS = [("V80/r66", "V76/r65"), ("V80/r66", "V75/r5e"), ("V75/r5e", "V76/r65"),
             ("V76/r65", "V74/r5d"), ("V75/r5e", "V74/r5d"), ("V80/r66", "V74/r5d")]
    for _, bd in BAND4:
        print(f"\n---- {bd} Hz ----")
        print(f"{'pair':16s} {'key':4s} {'ratio':>8s} {'95% CI':>20s} {'cells':>6s} "
              f"{'nA':>4s} {'nB':>4s}   verdict-vs-null")
        for A, B in PAIRS:
            for key, tag in (("e_" + bd, "e"), ("p_" + bd, "p")):
                rA, rB = eng(R[A], A), eng(R[B], B)
                res = G.boot_cellwise(rA, rB, key, RNG, nboot=1500, min_ep=2, min_win=4)
                nl = OUT["null"][bd][A][tag]
                nlB = OUT["null"][bd][B][tag]
                lo = min(nl[1], nlB[1]); hi = max(nl[2], nlB[2])
                out = "OUTSIDE null" if (res[0] < lo or res[0] > hi) else "inside null "
                ci = "CI excl 1" if (np.isfinite(res[1]) and (res[1] > 1 or res[2] < 1)) \
                    else "CI incl 1"
                print(f"{A.split('/')[0]+'/'+B.split('/')[0]:16s} {tag:4s} {res[0]:8.3f} "
                      f"[{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d} {res[4]:4d} {res[5]:4d}   "
                      f"{out}; {ci}")
                OUT["ratios"].setdefault(bd, {})[f"{A}|{B}|{tag}"] = dict(
                    ratio=res[0], lo=res[1], hi=res[2], cells=res[3], nA=res[4], nB=res[5],
                    null=[lo, hi])

    for bd in ("18-22", "40-49", "6-9"):
        print(f"\n---- {bd} Hz, PER STRATUM (V80 vs each), key = e ----")
        for nm, lo_, hi_ in STRATA:
            for B in ("V76/r65", "V75/r5e"):
                a = eng(R["V80/r66"], "V80/r66", lo_, hi_)
                b_ = eng(R[B], B, lo_, hi_)
                if len(a) < 8 or len(b_) < 8:
                    print(f"  {nm:14s} V80/{B.split('/')[0]:4s}  -- insufficient "
                          f"(nA={len(a)}, nB={len(b_)})")
                    continue
                res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1500, min_ep=1, min_win=3)
                print(f"  {nm:14s} V80/{B.split('/')[0]:4s}  {res[0]:7.3f} "
                      f"[{res[1]:7.3f},{res[2]:7.3f}]  cells={res[3]}  nblk {res[4]}/{res[5]}")
                OUT.setdefault("strat_ratio", {}).setdefault(bd, {})[f"{nm}|{B}"] = \
                    dict(ratio=res[0], lo=res[1], hi=res[2], cells=res[3])

    # ---------------------------------------------------------------- S4 DOSE RESPONSE ----------
    hdr("S4  DOSE-RESPONSE vs the damper loop gain k.  Point = cell-stratified ratio of each build\n"
        "    to the SAME reference build (V76, k=1.3866), so all four points share one instrument.")
    OUT["dose"] = {}
    REF = "V76/r65"
    for _, bd in BAND4:
        print(f"\n---- {bd} Hz ----   (ratio of e_band to V76; 1.000 by construction for V76)")
        pts = []
        for b in LADDER:
            if b == REF:
                pts.append((K[b], 1.0, 1.0, 1.0, b))
                print(f"  k={K[b]:6.4f}  {b:10s}   1.000 (reference)")
                continue
            res = G.boot_cellwise(eng(R[b], b), eng(R[REF], REF), "e_" + bd, RNG,
                                  nboot=1500, min_ep=2, min_win=4)
            pts.append((K[b], res[0], res[1], res[2], b))
            print(f"  k={K[b]:6.4f}  {b:10s}   {res[0]:6.3f} [{res[1]:6.3f}, {res[2]:6.3f}]"
                  f"   cells={res[3]}")
        pts.sort()
        v = [p[1] for p in pts]
        mono_up = all(v[i] <= v[i + 1] for i in range(len(v) - 1))
        mono_dn = all(v[i] >= v[i + 1] for i in range(len(v) - 1))
        arg = int(np.argmin(v))
        print(f"  monotone increasing: {mono_up}   monotone decreasing: {mono_dn}   "
              f"MINIMUM at k={pts[arg][0]:.4f} ({pts[arg][4]})")
        OUT["dose"][bd] = dict(points=[[p[0], p[1], p[2], p[3], p[4]] for p in pts],
                               mono_up=mono_up, mono_dn=mono_dn, argmin_k=pts[arg][0],
                               argmin_build=pts[arg][4])

    # ---------------------------------------------------------------- S5 IDENTITY ---------------
    hdr("S5  IS V80's GRINDING THE SAME LINE?  f0 / spread / crest / speed- and amplitude-slope.\n"
        "    f0 located by a FREE 12-30 Hz prominence argmax (a strict band pins f0 to its edge).")
    OUT["identity"] = {}
    print(f"{'build':10s} {'n':>4s} | {'f0 12-30 Hz med [CI]':>26s} | {'sd':>5s} | "
          f"{'crest 17-23':>22s} | {'crest 40-49':>22s}")
    for b in LADDER:
        e = [r for r in eng(R[b], b) if np.isfinite(r["f_12-30"])]
        f0 = G.boot_median_ci(e, "f_12-30", RNG, nboot=2000)
        c1 = G.boot_median_ci(e, "crest18", RNG, nboot=1500)
        c4 = G.boot_median_ci(e, "crest40", RNG, nboot=1500)
        sd = float(np.std(G.col(e, "f_12-30")))
        print(f"{b:10s} {len(e):4d} | {f0[0]:7.3f} [{f0[1]:6.3f},{f0[2]:6.3f}] | {sd:5.2f} | "
              f"{c1[0]:6.3f} [{c1[1]:6.3f},{c1[2]:6.3f}] | "
              f"{c4[0]:6.3f} [{c4[1]:6.3f},{c4[2]:6.3f}]")
        OUT["identity"][b] = dict(f0=list(f0), f0_sd=sd, crest18=list(c1), crest40=list(c4),
                                  n=len(e))

    print("\n  f0 vs SPEED (Theil-Sen, Hz per m/s) and vs AMPLITUDE (Hz per 100 counts of e_18-22)")
    print("  -- a Coulomb-relay limit cycle predicts BOTH slopes ~ 0; a tyre order predicts")
    print("     +1/circ = +0.48 Hz per m/s; a speed-dependent plant predicts a nonzero speed slope.")
    for b in LADDER:
        e = [r for r in eng(R[b], b) if np.isfinite(r["f_12-30"])]
        sv = theil_sen_boot(e, "v", "f_12-30", RNG)
        for r in e:
            r["_amp100"] = r["e_18-22"] / 100.0
        sa = theil_sen_boot(e, "_amp100", "f_12-30", RNG)
        print(f"  {b:10s} d f0/d v = {sv[0]:+7.4f} [{sv[1]:+7.4f},{sv[2]:+7.4f}] Hz/(m/s)   "
              f"d f0/d amp = {sa[0]:+7.4f} [{sa[1]:+7.4f},{sa[2]:+7.4f}] Hz/100ct")
        OUT["identity"][b]["slope_v"] = list(sv)
        OUT["identity"][b]["slope_amp"] = list(sa)

    print("\n  HARMONIC STRUCTURE (median prominence, engaged): a RELAY drives ODD harmonics.")
    print("  3 x 21.1 = 63.3 Hz FOLDS to ~36.7 Hz at fs~100 Hz, so 35-39 is the odd-harmonic probe;")
    print("  40-49 carries the 2nd harmonic (grind #2). 32-38 is the pre-declared negative control.")
    KEYS = ("6-9", "18-22", "26-31", "32-38", "35-39", "40-49")
    print(f"{'build':10s} " + " ".join(f"{k:>10s}" for k in KEYS))
    for b in LADDER:
        e = eng(R[b], b)
        print(f"{b:10s} " + " ".join(
            f"{np.nanmedian(G.col(e, 'p_' + k)):10.2f}" for k in KEYS))
    print("\n  ENVELOPE amplitude (counts, median):")
    print(f"{'build':10s} " + " ".join(f"{k:>10s}" for k in KEYS))
    for b in LADDER:
        e = eng(R[b], b)
        print(f"{b:10s} " + " ".join(
            f"{np.nanmedian(G.col(e, 'e_' + k)):10.1f}" for k in KEYS))

    print("\n  AMPLITUDE SPREAD -- a relay CLAMPS the amplitude (low CV); an excited resonance is")
    print("  bursty (high CV).  CV of e_18-22 over engaged windows + its percentiles.")
    for b in LADDER:
        v = G.col(eng(R[b], b), "e_18-22")
        v = v[np.isfinite(v)]
        print(f"  {b:10s} CV={np.std(v)/np.mean(v):5.3f}  p50={np.percentile(v,50):7.1f} "
              f"p95={np.percentile(v,95):7.1f} p99={np.percentile(v,99):7.1f} max={v.max():7.1f}")
        OUT["identity"][b]["cv18"] = float(np.std(v) / np.mean(v))

    # ---------------------------------------------------------------- S6 DUTY CYCLE -------------
    hdr("S6  'GRINDING ~90% OF ENGAGED TIME' -- fraction of ENGAGED windows above a stated\n"
        "    18-22 Hz threshold, blocks resampled.  pp = peak-to-peak counts on the torsion bar.")
    OUT["duty"] = {}
    for thr in (200.0, 400.0, 600.0, 1000.0):
        print(f"\n  e_18-22 > {thr:.0f} counts amplitude  (pp >= {2*thr:.0f} counts)")
        for b in LADDER:
            e = eng(R[b], b)
            f = frac_ci(e, "e_18-22", thr, RNG)
            print(f"    {b:10s} {100*f[0]:6.1f}% [{100*f[1]:5.1f}, {100*f[2]:5.1f}]  "
                  f"of {f[3]} engaged windows ({f[3]*1.28:.0f} s)")
            OUT["duty"].setdefault(f"{thr:.0f}", {})[b] = list(f)
    print("\n  Same, threshold = the 90th percentile of V76's engaged e_18-22 (V76 reads 10.0%")
    print("  by construction).")
    ref = float(np.percentile(G.col(eng(R["V76/r65"], "V76/r65"), "e_18-22"), 90))
    print(f"  reference threshold = {ref:.1f} counts amplitude ({2*ref:.0f} ct p-p)")
    for b in LADDER:
        f = frac_ci(eng(R[b], b), "e_18-22", ref, RNG)
        print(f"    {b:10s} {100*f[0]:6.1f}% [{100*f[1]:5.1f}, {100*f[2]:5.1f}]")
        OUT["duty"].setdefault("v76p90", {})[b] = list(f)
    OUT["duty"]["v76p90_thr"] = ref

    print("\n  Per-stratum duty at pp>=1200 ct (e_18-22 > 600):")
    for nm, lo_, hi_ in STRATA:
        row = []
        for b in LADDER:
            s = eng(R[b], b, lo_, hi_)
            if len(s) < 5:
                row.append(f"{b.split('/')[0]}:  n/a")
                continue
            f = frac_ci(s, "e_18-22", 600.0, RNG, nboot=1500)
            row.append(f"{b.split('/')[0]}:{100*f[0]:5.1f}%")
        print(f"  {nm:14s} " + "   ".join(row))

    # ---------------------------------------------------------------- S7 VALIDITY ---------------
    hdr("S7  VALIDITY CHECKS")
    print("  (a) 1-4 Hz driver-input band -- the exposure-matching check. If cell matching worked")
    print("      the routes should not differ much here.")
    for A, B in [("V80/r66", "V76/r65"), ("V80/r66", "V75/r5e"), ("V75/r5e", "V76/r65")]:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_1-4", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"    {A.split('/')[0]}/{B.split('/')[0]:6s}   {res[0]:6.3f} "
              f"[{res[1]:6.3f}, {res[2]:6.3f}]   cells={res[3]}")
        OUT.setdefault("validity", {})[f"1-4|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    print("\n  (b) 32-38 Hz negative control (between the modes, no known line).")
    for A, B in [("V80/r66", "V76/r65"), ("V80/r66", "V75/r5e"), ("V75/r5e", "V76/r65")]:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_32-38", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"    {A.split('/')[0]}/{B.split('/')[0]:6s}   {res[0]:6.3f} "
              f"[{res[1]:6.3f}, {res[2]:6.3f}]   cells={res[3]}")
        OUT.setdefault("validity", {})[f"32-38|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    print("\n  (c) wheel order 1 (v/2.0805 Hz) inside each stratum -- if it lands in a band of")
    print("      record that band is contaminated by a TYRE line, not firmware.")
    for nm, lo_, hi_ in STRATA:
        f1 = (lo_ / 2.0805, min(hi_, 35.0) / 2.0805)
        print(f"    {nm:14s} order1 {f1[0]:5.2f}-{f1[1]:5.2f} Hz | order2 "
              f"{2*f1[0]:5.2f}-{2*f1[1]:5.2f} | order3 {3*f1[0]:5.2f}-{3*f1[1]:5.2f}")
    print("\n  (d) EPKEY sensitivity: headline 18-22 ratios with ENGAGEMENT-RUN episodes ('ep')")
    print("      instead of ~10.2 s blocks ('blk').")
    G.EPKEY = "ep"
    for A, B in [("V80/r66", "V76/r65"), ("V80/r66", "V75/r5e"), ("V75/r5e", "V76/r65")]:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_18-22", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"    {A.split('/')[0]}/{B.split('/')[0]:6s}   {res[0]:6.3f} "
              f"[{res[1]:6.3f}, {res[2]:6.3f}]   cells={res[3]}  runs {res[4]}/{res[5]}")
        OUT.setdefault("validity", {})[f"ep|18-22|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "blk"

    def _san(o):
        try:
            return None if not np.isfinite(o) else float(o)
        except Exception:
            return str(o)
    (CACHE66 / "compare_v75_v76_v80.json").write_text(json.dumps(OUT, indent=1, default=_san))
    print(f"\nwrote {CACHE66 / 'compare_v75_v76_v80.json'}")




# =================================================================================================
#  PART 4 -- `deep`:  is V80's HF elevation a LINE or a broadband FLOOR, and what is the 100 km/h
#  event?  Run after `analyze`.
# =================================================================================================
def medspec(build, lo, hi, eng_only=True, nfft=G.NFFT):
    """Median periodogram + median prominence spectrum over engaged windows in a speed stratum.
    Uses G.wrecs' OWN window cut (keep_P=True), so it cannot drift from the band table."""
    rs = G.wrecs(build, keep_P=True)
    f = None
    Ps, Rs, vs = [], [], []
    for r in rs:
        if r["eng"] != 1 or r["seg"] in PARKED.get(build, []):
            continue
        if not (lo <= r["v"] < hi):
            continue
        f = r["f"]
        Ps.append(r["P"])
        Rs.append(G.prom_spectrum(f, r["P"]))
        vs.append(r["v"])
    if not Ps:
        return None, None, None, 0
    return f, np.median(np.array(Ps), 0), np.nanmedian(np.array(Rs), 0), len(Ps)


def deep():
    G.EPKEY = "blk"
    R = build_records()
    O = {}

    hdr("D1  IS IT A LINE OR A FLOOR?  Median periodogram over ENGAGED windows, per speed\n"
        "    stratum, in dB relative to V76 bin-for-bin.  A LINE shows a narrow bump; a broadband\n"
        "    floor lift shows a flat offset across the whole HF region.")
    for nm, lo, hi in STRATA[1:3]:
        cur = {}
        for b in TRIO:
            f, P, Rp, n = medspec(b, lo, hi)
            cur[b] = (f, P, Rp, n)
        print(f"\n---- {nm} ----   n windows: " + ", ".join(
            f"{b.split('/')[0]}={cur[b][3]}" for b in TRIO))
        f = cur["V76/r65"][0]
        print(f"{'Hz':>6s} | {'V76 dB':>8s} {'V75 dB':>8s} {'V80 dB':>8s} | "
              f"{'V75-V76':>8s} {'V80-V76':>8s} | prominence  V76   V75   V80")
        for fc in np.arange(2.0, 50.0, 2.0):
            j = int(np.argmin(np.abs(f - fc)))
            d = {b: 10 * np.log10(cur[b][1][j] + 1e-30) for b in TRIO}
            pr = {b: cur[b][2][j] for b in TRIO}
            print(f"{f[j]:6.2f} | {d['V76/r65']:8.2f} {d['V75/r5e']:8.2f} {d['V80/r66']:8.2f} | "
                  f"{d['V75/r5e']-d['V76/r65']:+8.2f} {d['V80/r66']-d['V76/r65']:+8.2f} |"
                  f"  {pr['V76/r65']:8.2f} {pr['V75/r5e']:6.2f} {pr['V80/r66']:6.2f}")
        O.setdefault("spec", {})[nm] = {
            b: dict(f=[float(x) for x in cur[b][0]], P=[float(x) for x in cur[b][1]],
                    n=cur[b][3]) for b in TRIO}

    hdr("D2  CONTROL CHANNELS -- if V80's HF lift is REAL MOTION it must appear on the steering\n"
        "    ANGLE too; if it is ROAD it must appear on the IMU; if it is COMMANDED it must appear\n"
        "    on openpilot's own 0x0E4 torque.  All cell-stratified V80/V76, blocks resampled.")
    # IMU HF, computed per window by re-slicing (imu_vert is in all three caches).
    for b in LADDER:
        by = {}
        for r in R[b]:
            by.setdefault(r["seg"], []).append(r)
        for seg, rs in by.items():
            B = G.BUILDS[b]
            p = B["cache"] / f"{B['pfx']}{seg}.npz"
            if not p.exists():
                continue
            d = C31.load(seg, B["cache"], B["pfx"])
            fs = G.fs_of(d)
            t = np.asarray(d["t"], float)
            iv = np.asarray(d.get("imu_vert", np.full(len(t), np.nan)), float)
            taper = np.hanning(G.NFFT) + 1e-3
            cw = slice(int(0.2 * G.NFFT), int(0.8 * G.NFFT))
            for r in rs:
                i0 = int(np.argmin(np.abs(t - r["t0"])))
                w = iv[i0:i0 + G.NFFT]
                r["imu_hf"] = (G.win_env(w, fs, 20.0, 49.0, taper, cw)
                               if len(w) == G.NFFT and np.all(np.isfinite(w)) else np.nan)
                r["imu_lf"] = (G.win_env(w, fs, 1.0, 10.0, taper, cw)
                               if len(w) == G.NFFT and np.all(np.isfinite(w)) else np.nan)
    print(f"{'channel':34s} {'V80/V76':>22s} {'V80/V75':>22s} {'V75/V76':>22s}")
    CH = [("tq   30-49 Hz  (torsion bar)", "e_30-49"),
          ("tq   32-38 Hz  (neg control) ", "e_32-38"),
          ("tq   18-22 Hz  (grind #1)    ", "e_18-22"),
          ("tq   1-4  Hz   (driver input)", "e_1-4"),
          ("ang  30-49 Hz  (wheel angle) ", "ang_hf"),
          ("ang  1-10 Hz                 ", "ang_lf"),
          ("IMU  20-49 Hz  (road/plant)  ", "imu_hf"),
          ("IMU  1-10 Hz                 ", "imu_lf"),
          ("0x0E4 30-49 Hz (op command)  ", "e4hf"),
          ("zigzag |d| > 300 ct count    ", "zig"),
          ("zigzag |d| > 800 ct count    ", "zig800")]
    for lab, key in CH:
        row = []
        for A, B in (("V80/r66", "V76/r65"), ("V80/r66", "V75/r5e"), ("V75/r5e", "V76/r65")):
            try:
                res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), key, RNG, nboot=1200,
                                      min_ep=2, min_win=4)
                row.append(f"{res[0]:6.3f} [{res[1]:5.2f},{res[2]:5.2f}]")
            except Exception as ex:
                row.append(f"  n/a ({type(ex).__name__})     ")
        print(f"{lab:34s} " + " ".join(f"{x:>22s}" for x in row))
        O.setdefault("channels", {})[key] = row
    print("\n  raw medians (engaged), for scale:")
    print(f"{'channel':34s} " + " ".join(f"{b.split('/')[0]:>10s}" for b in LADDER))
    for lab, key in CH:
        print(f"{lab:34s} " + " ".join(
            f"{np.nanmedian(G.col(eng(R[b], b), key)):10.3f}" for b in LADDER))

    hdr("D3  THE 100 km/h EVENT ON V80 -- where, how long, what frequency, is it contiguous?")
    ev = sorted([r for r in eng(R["V80/r66"], "V80/r66") if r["v"] >= 80 * KMH],
                key=lambda r: (r["seg"], r["t0"]))
    print(f"  {len(ev)} engaged windows above 80 km/h, segments "
          f"{sorted({r['seg'] for r in ev})}, engagement runs {len({r['ep'] for r in ev})}")
    print(f"  {'seg':>3s} {'t0':>7s} {'v':>6s} {'rate':>6s} {'eff':>7s} | "
          f"{'e18-22':>8s} {'e26-31':>8s} {'e32-38':>8s} {'e40-49':>8s} | "
          f"{'f12-30':>7s} {'p26-31':>8s} {'crest':>6s}")
    for r in ev:
        print(f"  {r['seg']:3d} {r['t0']:7.1f} {r['v']:6.2f} {r['rate']:6.1f} {r['eff']:7.0f} | "
              f"{r['e_18-22']:8.1f} {r['e_26-31']:8.1f} {r['e_32-38']:8.1f} {r['e_40-49']:8.1f} | "
              f"{r['f_12-30']:7.2f} {r['p_26-31']:8.1f} {r['crest18']:6.2f}")
    O["event"] = [{k: float(r[k]) for k in ("seg", "t0", "v", "rate", "eff", "e_18-22", "e_26-31",
                                            "e_32-38", "e_40-49", "f_12-30", "p_26-31", "crest18")}
                  for r in ev]

    # the event's own high-resolution spectrum, from the raw cache
    if ev:
        seg = int(ev[0]["seg"])
        B = G.BUILDS["V80/r66"]
        d = C31.load(seg, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        t = np.asarray(d["t"], float)
        a = int(np.argmin(np.abs(t - ev[0]["t0"])))
        b_ = int(np.argmin(np.abs(t - ev[-1]["t0"]))) + G.NFFT
        x = np.asarray(d["tq"], float)[a:b_]
        n = 1024 if len(x) >= 1024 else 512
        acc = []
        for i in range(0, len(x) - n + 1, n // 2):
            P = G.periodogram(x[i:i + n], fs, n, True)
            if P is not None:
                acc.append(P)
        if acc:
            f = np.fft.rfftfreq(n, 1 / fs)
            P = np.median(np.array(acc), 0)
            Rp = G.prom_spectrum(f, P)
            j = int(np.argmax(np.where((f > 5) & (f < 49), Rp, -np.inf)))
            print(f"\n  event high-res spectrum: seg{seg} t {t[a]:.1f}-{t[min(b_,len(t)-1)]:.1f} s, "
                  f"nfft={n} ({n/fs:.2f} s bins, {fs/n:.3f} Hz), {len(acc)} blocks")
            print(f"  MOST PROMINENT line 5-49 Hz: {f[j]:.3f} Hz, prominence {Rp[j]:.1f}, "
                  f"Q={G.q_of(f, P, f[j]):.1f}")
            print(f"  {'Hz':>7s} {'dB':>8s} {'prom':>8s}   (top 14 bins by prominence)")
            order = np.argsort(np.where((f > 3) & (f < 49.5), Rp, -np.inf))[::-1][:14]
            for k in sorted(order):
                print(f"  {f[k]:7.3f} {10*np.log10(P[k]+1e-30):8.2f} {Rp[k]:8.1f}")
            O["event_spec"] = dict(f0=float(f[j]), prom=float(Rp[j]),
                                   q=float(G.q_of(f, P, f[j])), fs=float(fs), n=n)
        # is the event contiguous, and what is engagement/speed doing?
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        print(f"\n  seg{seg}: engaged {100*lat.mean():.1f}%, v {v.min():.1f}-{v.max():.1f} m/s; "
              f"engaged runs {[ (round(float(t[s]),1), round(float(t[e_-1]),1)) for s, e_ in G.runs_of(lat, t, 64) ]}")
        # envelope over the whole segment, 1 s steps
        env = C31.band_envelope(np.asarray(d["tq"], float), fs, 18.0, 31.0)
        step = int(fs)
        print("  18-31 Hz envelope over seg (1 s steps, counts):")
        line = []
        for i in range(0, len(env) - step, step):
            line.append(f"{np.percentile(env[i:i+step], 95):5.0f}")
        for i in range(0, len(line), 15):
            print("    t=%3d  " % i + " ".join(line[i:i + 15]))

    hdr("D4  DUTY CYCLE ON THE BAND THAT ACTUALLY MOVED (30-49 Hz broadband roughness).\n"
        "    Threshold = the 90th percentile of V76's engaged e_30-49, so V76 reads 10.0%.")
    ref = float(np.percentile(G.col(eng(R["V76/r65"], "V76/r65"), "e_30-49"), 90))
    print(f"  threshold = {ref:.1f} counts amplitude")
    for b in LADDER:
        f = frac_ci(eng(R[b], b), "e_30-49", ref, RNG)
        print(f"    {b:10s} {100*f[0]:6.1f}% [{100*f[1]:5.1f}, {100*f[2]:5.1f}]  of {f[3]} windows")
        O.setdefault("duty3049", {})[b] = list(f)
    print("\n  per stratum:")
    for nm, lo_, hi_ in STRATA:
        row = []
        for b in LADDER:
            s = eng(R[b], b, lo_, hi_)
            if len(s) < 5:
                row.append(f"{b.split('/')[0]}:  n/a")
                continue
            f = frac_ci(s, "e_30-49", ref, RNG, nboot=1500)
            row.append(f"{b.split('/')[0]}:{100*f[0]:5.1f}%")
        print(f"  {nm:14s} " + "   ".join(row))
    print("\n  and the median e_30-49 per stratum (counts):")
    for nm, lo_, hi_ in STRATA:
        row = []
        for b in LADDER:
            s = eng(R[b], b, lo_, hi_)
            row.append(f"{b.split('/')[0]}:" + ("  n/a" if len(s) < 5 else
                       f"{np.nanmedian(G.col(s, 'e_30-49')):6.1f}"))
        print(f"  {nm:14s} " + "   ".join(row))

    hdr("D5  WHY THE CREEP CELLS DID NOT MATCH -- the effort/rate census inside creep.")
    print(f"  {'build':10s} {'n':>4s} {'eff p10/50/90':>24s} {'|rate| p10/50/90':>24s} "
          f"{'cells':>28s}")
    for b in LADDER:
        s = eng(R[b], b, 0.0, 10 * KMH)
        if not s:
            continue
        e_ = G.col(s, "eff"); r_ = G.col(s, "rate")
        cells = sorted({r["cell"] for r in s})
        print(f"  {b:10s} {len(s):4d} "
              f"{np.percentile(e_,10):7.0f}/{np.percentile(e_,50):6.0f}/{np.percentile(e_,90):7.0f} "
              f"{np.percentile(r_,10):7.1f}/{np.percentile(r_,50):6.1f}/{np.percentile(r_,90):7.1f} "
              f"  {cells}")
    print("\n  cell = (eng, speed bin, effort bin, |rate| bin) with G's own edges:")
    print(f"    V_BINS  {G.V_BINS}\n    E_BINS  {G.E_BINS}\n    R_BINS  {G.R_BINS}")

    def _san(o):
        try:
            return None if not np.isfinite(o) else float(o)
        except Exception:
            return str(o)
    (CACHE66 / "deep_v75_v76_v80.json").write_text(json.dumps(O, indent=1, default=_san))
    print(f"\nwrote {CACHE66 / 'deep_v75_v76_v80.json'}")




# =================================================================================================
#  PART 5 -- `deep2`: nail the duty cycle, the near-Nyquist confirmation, and the 27.3 Hz event.
# =================================================================================================
def deep2():
    G.EPKEY = "blk"
    R = build_records()
    O = {}

    hdr("E1  DUTY CYCLE, THREE ROUTE-INDEPENDENT THRESHOLDS taken from V76's OWN engaged\n"
        "    distribution (so V76 reads 50 / 25 / 10 % by construction).  Band = 30-49 Hz, the\n"
        "    band that actually moved.")
    base = G.col(eng(R["V76/r65"], "V76/r65"), "e_30-49")
    for q in (50, 75, 90):
        thr = float(np.percentile(base, q))
        print(f"\n  threshold = V76 p{q} = {thr:.1f} counts amplitude")
        for b in LADDER:
            f = frac_ci(eng(R[b], b), "e_30-49", thr, RNG)
            print(f"    {b:10s} {100*f[0]:6.1f}% [{100*f[1]:5.1f}, {100*f[2]:5.1f}]")
            O.setdefault(f"duty_p{q}", {})[b] = list(f)
        print("    per stratum (V80 only):  " + "  ".join(
            f"{nm}:{100*frac_ci(eng(R['V80/r66'],'V80/r66',lo,hi),'e_30-49',thr,RNG,1500)[0]:5.1f}%"
            for nm, lo, hi in STRATA if len(eng(R["V80/r66"], "V80/r66", lo, hi)) >= 5))

    hdr("E2  NEAR-NYQUIST, FFT-FREE CONFIRMATION.  `zigzag` counts sample-to-sample sign\n"
        "    reversals whose smaller leg exceeds a threshold -- immune to spectral leakage.\n"
        "    A 45 Hz oscillation reverses almost every sample; an 18 Hz one does not.")
    for thr_key, lab in (("zig", "|step| > 300 counts"), ("zig800", "|step| > 800 counts")):
        print(f"\n  {lab}")
        for b in LADDER:
            e = eng(R[b], b)
            v = G.col(e, thr_key)
            fr = frac_ci(e, thr_key, 0.0, RNG)
            print(f"    {b:10s} windows with >=1 reversal: {100*fr[0]:6.1f}% "
                  f"[{100*fr[1]:5.1f}, {100*fr[2]:5.1f}]   median count {np.median(v):5.1f}  "
                  f"p95 {np.percentile(v, 95):6.1f}  max {v.max():6.0f}")
            O.setdefault(thr_key, {})[b] = dict(frac=list(fr), med=float(np.median(v)),
                                                p95=float(np.percentile(v, 95)))

    hdr("E3  IS THE 27.3 Hz EVENT UNIQUE TO V80?  Every ENGAGED window in the corpus whose\n"
        "    26-31 Hz envelope exceeds 500 counts.")
    tot = {}
    for b in LADDER:
        e = eng(R[b], b)
        hits = [r for r in e if r["e_26-31"] > 500]
        tot[b] = (len(hits), len(e))
        print(f"  {b:10s} {len(hits):4d} / {len(e):4d} engaged windows "
              f"({100*len(hits)/max(len(e),1):5.1f}%)   "
              f"segs {sorted({r['seg'] for r in hits})}  "
              f"speeds {('%.1f-%.1f m/s' % (min(r['v'] for r in hits), max(r['v'] for r in hits))) if hits else '-'}")
    O["e2631_gt500"] = {b: list(v) for b, v in tot.items()}
    print("\n  same at 26-31 > 1000 counts:")
    for b in LADDER:
        e = eng(R[b], b)
        hits = [r for r in e if r["e_26-31"] > 1000]
        print(f"  {b:10s} {len(hits):4d} / {len(e):4d}   segs {sorted({r['seg'] for r in hits})}")

    hdr("E4  THE EVENT ITSELF -- raw waveform, the COMMAND, and the aliasing caveat.")
    B = G.BUILDS["V80/r66"]
    d = C31.load(8, B["cache"], B["pfx"])
    fs = G.fs_of(d)
    t = np.asarray(d["t"], float)
    m = (t >= 21.0) & (t <= 50.0)
    for nm, key, unit in (("torsion bar tq", "tq", "counts"), ("steer angle ang", "ang", "deg"),
                          ("angle rate rate_c", "rate_c", "deg/s"),
                          ("op cmd cc_req", "cc_req", "-"), ("EPS 0x0E4 e4tq", "e4tq", "counts"),
                          ("sendcan sc_tq", "sc_tq", "counts")):
        x = np.asarray(d[key], float)[m]
        bp = bandpass(x, fs, 25.0, 30.0)
        c = bp[int(0.1 * len(bp)):int(0.9 * len(bp))]
        rms = float(np.sqrt(np.mean(c ** 2)))
        print(f"  {nm:20s} raw p-p {np.nanmax(x)-np.nanmin(x):10.3f} {unit:7s} | "
              f"25-30 Hz rms {rms:9.4f}  p-p {np.max(c)-np.min(c):10.4f}  "
              f"crest {np.max(np.abs(c))/rms if rms > 0 else float('nan'):5.2f}")
        O.setdefault("event_chan", {})[key] = dict(rms=rms, pp=float(np.max(c) - np.min(c)))
    print("\n  STEER_STATUS / STEER_CONTROL_ACTIVE during the event:")
    for key in ("sstat", "sca", "cc_lat", "cs_press"):
        x = np.asarray(d[key], float)[m]
        u, c = np.unique(np.round(x, 3), return_counts=True)
        print(f"    {key:10s} " + "  ".join(f"{uu:g}:{cc}" for uu, cc in zip(u, c))[:110])
    print("\n  ALIASING: fs = %.3f Hz -> a measured 27.344 Hz line is indistinguishable from"
          % fs)
    print("    " + ", ".join(f"{x:.2f}" for x in R47.alias_family(27.344, fs, 2)) + " Hz.")
    print("    This is COMMON MODE across all four routes (same logger, same 100 Hz CAN tick),")
    print("    so it cannot affect the between-build contrast -- only the identification.")

    # the phase relationship: does the command lead or follow the bar at 27.3 Hz?
    x = bandpass(np.asarray(d["tq"], float)[m], fs, 26.0, 29.0)
    y = bandpass(np.asarray(d["e4tq"], float)[m], fs, 26.0, 29.0)
    z = bandpass(np.asarray(d["ang"], float)[m], fs, 26.0, 29.0)
    def coh(a, b_):
        a = a - a.mean(); b_ = b_ - b_.mean()
        den = np.sqrt(np.sum(a ** 2) * np.sum(b_ ** 2))
        return float(np.sum(a * b_) / den) if den > 0 else np.nan
    print(f"\n  26-29 Hz normalised cross-correlation at lag 0:  tq.ang = {coh(x, z):+.3f}   "
          f"tq.e4tq = {coh(x, y):+.3f}   ang.e4tq = {coh(z, y):+.3f}")
    print(f"  26-29 Hz rms: tq {np.std(x):.1f} counts | ang {np.std(z):.4f} deg | "
          f"e4tq {np.std(y):.2f} counts")

    hdr("E5  DOSE-RESPONSE SUMMARY TABLE -- e_band ratio to V76, all four ladder points.")
    print(f"  {'band':10s} " + "  ".join(f"{b.split('/')[0]}(k={K[b]:.2f})" for b in
                                         sorted(LADDER, key=lambda x: K[x])))
    for _, bd in BAND4 + [("hf floor", "30-49"), ("neg ctrl", "32-38")]:
        row = []
        for b in sorted(LADDER, key=lambda x: K[x]):
            if b == "V76/r65":
                row.append("  1.000 (ref)  ")
                continue
            res = G.boot_cellwise(eng(R[b], b), eng(R["V76/r65"], "V76/r65"), "e_" + bd, RNG,
                                  nboot=1500, min_ep=2, min_win=4)
            row.append(f"{res[0]:6.3f}[{res[1]:5.2f},{res[2]:5.2f}]")
        print(f"  {bd:10s} " + "  ".join(row))
        O.setdefault("dose_table", {})[bd] = row

    def _san(o):
        try:
            return None if not np.isfinite(o) else float(o)
        except Exception:
            return str(o)
    (CACHE66 / "deep2_v75_v76_v80.json").write_text(json.dumps(O, indent=1, default=_san))
    print(f"\nwrote {CACHE66 / 'deep2_v75_v76_v80.json'}")




# =================================================================================================
#  PART 6 -- `deep3`: the V80 limit-cycle event class.  Is f0 the same at 8 km/h and 103 km/h?
#  A Coulomb-relay limit cycle predicts f0 independent of BOTH amplitude and speed.
# =================================================================================================
def deep3():
    G.EPKEY = "blk"
    R = build_records()
    O = {}

    hdr("F1  EVERY V80 ENGAGED WINDOW WITH e_26-31 > 1000 COUNTS -- f0 re-located by a free\n"
        "    20-35 Hz prominence argmax on that window's OWN periodogram.")
    B = G.BUILDS["V80/r66"]
    caches = {}
    rows = []
    for r in sorted(eng(R["V80/r66"], "V80/r66"), key=lambda r: (r["seg"], r["t0"])):
        if r["e_26-31"] <= 1000:
            continue
        seg = int(r["seg"])
        if seg not in caches:
            caches[seg] = C31.load(seg, B["cache"], B["pfx"])
        d = caches[seg]
        fs = G.fs_of(d)
        t = np.asarray(d["t"], float)
        i0 = int(np.argmin(np.abs(t - r["t0"])))
        x = np.asarray(d["tq"], float)[i0:i0 + G.NFFT]
        if len(x) < G.NFFT:
            continue
        P = G.periodogram(x, fs, G.NFFT, True)
        f = np.fft.rfftfreq(G.NFFT, 1 / fs)
        f0, pr = G.locate(f, P, 20.0, 35.0)
        q = G.q_of(f, P, f0)
        bp = bandpass(x, fs, f0 - 3, f0 + 3)
        cw = bp[int(0.15 * len(bp)):int(0.85 * len(bp))]
        rms = float(np.sqrt(np.mean(cw ** 2)))
        rows.append(dict(seg=seg, t0=float(r["t0"]), v=float(r["v"]), rate=float(r["rate"]),
                         eff=float(r["eff"]), e2631=float(r["e_26-31"]), f0=float(f0),
                         prom=float(pr), q=float(q),
                         crest=float(np.max(np.abs(cw)) / rms) if rms > 0 else np.nan,
                         rms=rms))
    print(f"  {len(rows)} windows")
    print(f"  {'seg':>3s} {'t0':>7s} {'v m/s':>6s} {'kph':>5s} {'rate':>6s} {'eff':>6s} | "
          f"{'e26-31':>8s} {'f0 Hz':>7s} {'prom':>8s} {'Q':>6s} {'crest':>6s}")
    for w in rows:
        print(f"  {w['seg']:3d} {w['t0']:7.1f} {w['v']:6.2f} {3.6*w['v']:5.1f} {w['rate']:6.1f} "
              f"{w['eff']:6.0f} | {w['e2631']:8.1f} {w['f0']:7.3f} {w['prom']:8.1f} {w['q']:6.1f} "
              f"{w['crest']:6.2f}")
    O["events"] = rows
    if rows:
        f0s = np.array([w["f0"] for w in rows])
        vs = np.array([w["v"] for w in rows])
        am = np.array([w["e2631"] for w in rows])
        lo_, hi_ = vs < 15, vs >= 15
        print(f"\n  f0 overall: median {np.median(f0s):.3f} Hz, sd {np.std(f0s):.3f}, "
              f"range {f0s.min():.3f}-{f0s.max():.3f}")
        for lab, msk in (("v < 15 m/s (<54 kph)", lo_), ("v >= 15 m/s (>=54 kph)", hi_)):
            if msk.sum():
                print(f"    {lab:24s} n={int(msk.sum()):3d}  f0 median {np.median(f0s[msk]):.3f} "
                      f"sd {np.std(f0s[msk]):.3f}  speed {vs[msk].min():.1f}-{vs[msk].max():.1f} m/s"
                      f"  e26-31 median {np.median(am[msk]):.0f}")
        print(f"  Theil-Sen d f0/d v   = {theil_sen(vs, f0s):+.5f} Hz/(m/s)   "
              f"(a tyre order would be +0.481; a relay limit cycle 0)")
        print(f"  Theil-Sen d f0/d amp = {theil_sen(am/1000.0, f0s):+.5f} Hz per 1000 counts   "
              f"(a relay limit cycle 0)")
        print(f"  median Q = {np.median([w['q'] for w in rows]):.1f}   "
              f"median crest = {np.median([w['crest'] for w in rows]):.3f}  "
              f"(pure sine 1.414; square 1.000; bursty > 2)")
        O["f0_med"] = float(np.median(f0s))
        O["f0_sd"] = float(np.std(f0s))
        O["slope_v"] = float(theil_sen(vs, f0s))
        O["slope_amp"] = float(theil_sen(am / 1000.0, f0s))

    hdr("F2  THE SAME SEARCH ON V75 / V76 / V74 -- their strongest 20-35 Hz windows, for scale.")
    for b in ("V74/r5d", "V76/r65", "V75/r5e"):
        Bb = G.BUILDS[b]
        e = sorted(eng(R[b], b), key=lambda r: -r["e_26-31"])[:5]
        print(f"\n  {b}: top 5 windows by e_26-31")
        cache = {}
        for r in e:
            seg = int(r["seg"])
            if seg not in cache:
                cache[seg] = C31.load(seg, Bb["cache"], Bb["pfx"])
            d = cache[seg]
            fs = G.fs_of(d)
            t = np.asarray(d["t"], float)
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            x = np.asarray(d["tq"], float)[i0:i0 + G.NFFT]
            if len(x) < G.NFFT:
                continue
            P = G.periodogram(x, fs, G.NFFT, True)
            f = np.fft.rfftfreq(G.NFFT, 1 / fs)
            f0, pr = G.locate(f, P, 20.0, 35.0)
            print(f"    seg{seg:2d} t={r['t0']:7.1f} v={3.6*r['v']:5.1f} kph  "
                  f"e26-31={r['e_26-31']:7.1f}  f0={f0:6.3f} Hz  prom={pr:7.1f}  "
                  f"Q={G.q_of(f, P, f0):6.1f}")

    hdr("F3  SEGMENT-BY-SEGMENT V80 -- where the limit cycle lives, and what the car was doing.")
    print(f"  {'seg':>3s} {'sec':>6s} {'eng%':>6s} {'v mean':>7s} {'v max':>6s} | "
          f"{'n eng win':>9s} {'e26-31>1000':>12s} {'med e30-49':>11s} {'med e18-22':>11s}")
    for s in SEGS66:
        p = CACHE66 / f"{PFX66}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, CACHE66, PFX66)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ws = [r for r in eng(R["V80/r66"], "V80/r66") if r["seg"] == s]
        nb = sum(1 for r in ws if r["e_26-31"] > 1000)
        print(f"  {s:3d} {d['t'][-1]:6.1f} {100*lat.mean():6.1f} {v.mean():7.2f} {v.max():6.2f} | "
              f"{len(ws):9d} {nb:12d} "
              f"{(np.nanmedian(G.col(ws,'e_30-49')) if ws else float('nan')):11.1f} "
              f"{(np.nanmedian(G.col(ws,'e_18-22')) if ws else float('nan')):11.1f}")

    def _san(o):
        try:
            return None if not np.isfinite(o) else float(o)
        except Exception:
            return str(o)
    (CACHE66 / "deep3_v80_limitcycle.json").write_text(json.dumps(O, indent=1, default=_san))
    print(f"\nwrote {CACHE66 / 'deep3_v80_limitcycle.json'}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        main()
    elif len(sys.argv) > 1 and sys.argv[1] == "deep":
        deep()
    elif len(sys.argv) > 1 and sys.argv[1] == "deep2":
        deep2()
    elif len(sys.argv) > 1 and sys.argv[1] == "deep3":
        deep3()
    else:
        print(__doc__)
