#!/usr/bin/env python3
r"""Extract route `77` (the V90 flight) into `analysis-2020accord/_scratch/cache/r77/`, tap the FULL
0x1AB payload, and run the SINGLE-FRAME V90 identity test from `docs/specs/SPEC-2026-08-10-v90-cave.md` §4.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `decode/extract_r6e.py` .. `decode/extract_r75_r76.py` do,
this file adds a row to `decode_v84_probe_r6d.ROUTES` and calls that module's `extract()`/`split()`
-- the SAME code that wrote every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention,
IMU axis pick, sentinel definition and `PASS_1D` are therefore bit-for-bit the ones every prior
route was scored with.

★ V90'S CAVE BIT LAYOUT (`docs/specs/SPEC-2026-08-10-v90-cave.md` §2, four INDEPENDENT signals)
        b7 0x80 = gp-0x6b26 <  0        SIGN of the damping-lane output
        b6 0x40 = |gp-0x6bf6| >= 512    |MODEL|
        b5 0x20 = gp-0x6ae2 != 0        friction relay active   (V89's rung, UNCHANGED)
        b4 0x10 = gp-0x6c00 <  0        the observer gate FAILED
        b3 0x08 = 1                     fingerprint  =>  every field value must be ODD
    bits 2:0 are stock STEER_SENSOR_STATUS, preserved.

★ IDENTITY -- single-frame, parameter-free.  `b4 == 0` is IMPOSSIBLE on V86B/V87/V88/V89 (b4
    railed at exactly 1.0000 over 254,085 measured frames) and is the ~100 % case on V90.
    ⇒ ANY frame with b4 == 0 proves V90 is on the car.

★ CAN 427 (`0x1AB`) MOTOR_TORQUE is repointed to gp-0x6b26:
        wire = clamp( (|gp-0x6b26| * 5) >> 3 , 0, 0x3FF )   at 50 Hz
    ⇒ |gp-0x6b26| = wire * 8 / 5 (~1.6 ct/LSB), and it NEVER clips (the lane is clamped to
    +-511 by `0xC407E`, and 511*5>>3 = 319 < 1023).

🛑 THE `raw14` OFF-BY-ONE IS FIXED HERE, NOT WORKED AROUND.
    `D.extract` appends to `raw14_t`/`raw14_b4` on EVERY 0x14A frame but appends a ROW only once
    `last18` is non-None, so the raw arrays lead the row grid by however many 0x14A frames arrive
    before the first 0x18F.  This module derives the exact index map by an EXACT timestamp match
    and stores it as `row2raw14`, asserting `raw14_t[row2raw14] == t` and
    `raw14_b4[row2raw14] == probe` elementwise.  Safe pairings remain `(t, probe)` and
    `(raw14_t, raw14_b4)`; `row2raw14` makes the third pairing legal and CHECKED.

Usage:
    python decode/extract_r77.py                  # extract, identity, health, census
    python decode/extract_r77.py extract
    python decode/extract_r77.py identity
    python decode/extract_r77.py health
    python decode/extract_r77.py census
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v84_probe_r6d as D  # noqa: E402  -- THE extractor that wrote every cache since r6d
import rlog_parse                 # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "77"
NSEG = 21                                    # segments 0..20 on disk
CDIR = "analysis-2020accord/_scratch/cache/r77"

D.ROUTES[ROUTE] = ("75604b0a432fdc89_00000077--7411859c54", NSEG, CDIR, "r77s", "r77", "V90")
D.ROUTES.setdefault("76", ("75604b0a432fdc89_00000076--c81e964e05", 13, "_scratch/cache/r76", "r76s",
                           "r76", "V89"))
D.ROUTES.setdefault("75", ("75604b0a432fdc89_00000075--9bbcb3f7da", 16, "_scratch/cache/r75", "r75s",
                           "r75", "V89"))
D.ROUTES.setdefault("73", ("75604b0a432fdc89_00000073--9380c74d52", 11, "_scratch/cache/r73", "r73s",
                           "r73", "V88"))

# ---- V90 rung masks, per SPEC §2.  Named for what they MEAN on V90, not for V86B's meanings.
B7_SIGN_6B26 = 0x80
B6_MODEL_GE512 = 0x40
B5_FRICTION_NZ = 0x20
B4_GATE_FAILED = 0x10
B3_FINGERPRINT = 0x08
FIELD_MASK = 0xF8

V90_ONLY = {1, 5, 9, 11, 13, 17, 19, 21, 25, 27, 29}      # field = (byte4 >> 3) & 0x1F
PRE_V90_ALPHABET = {3, 7, 15, 23, 31}                     # V86B/V87/V88/V89, measured

WIRE_SCALE = 8.0 / 5.0            # |gp-0x6b26| = wire * 8/5
LANE_CLAMP = 511                  # `0xC407E`


# ======================================================================================
# 0x1AB TAP -- a pass-through generator, so the extractor's event stream is unchanged.
# Carried VERBATIM from `decode/extract_r75_r76.py`.
# ======================================================================================
_ORIG_READ = rlog_parse.read_messages
TAP = {"t": [], "b0": [], "b1": [], "b2": [], "src": [], "dlc": []}
TRUNCATED, MSG_COUNT = {}, {}
_TAP_ON = False


def _read_messages_tapped(path):
    n = 0
    try:
        for evt in _ORIG_READ(path):
            n += 1
            if _TAP_ON:
                try:
                    if evt.which() == "can":
                        tm = evt.logMonoTime * 1e-9
                        for m in evt.can:
                            if int(m.address) == 0x1AB:
                                d = bytes(m.dat)
                                TAP["t"].append(tm)
                                TAP["b0"].append(d[0] if len(d) > 0 else 0)
                                TAP["b1"].append(d[1] if len(d) > 1 else 0)
                                TAP["b2"].append(d[2] if len(d) > 2 else 0)
                                TAP["src"].append(int(m.src))
                                TAP["dlc"].append(len(d))
                except Exception:
                    pass
            yield evt
    except Exception as exc:                       # capnp KjException on a torn tail
        TRUNCATED[Path(path).name] = (n, str(exc).splitlines()[0])
        print(f"  ⚠ TRUNCATED rlog {Path(path).name}: {n:,} complete messages read, then "
              f"{str(exc).splitlines()[0]}", flush=True)
    finally:
        MSG_COUNT[Path(path).name] = n


rlog_parse.read_messages = _read_messages_tapped


def _tap_reset():
    for k in TAP:
        TAP[k].clear()
    TRUNCATED.clear()
    MSG_COUNT.clear()


def _tap_arrays(t0):
    t = np.array(TAP["t"], float) - t0
    b0 = np.array(TAP["b0"], int)
    b1 = np.array(TAP["b1"], int)
    b2 = np.array(TAP["b2"], int)
    mt = ((b0 & 0x03) << 8) | b1                       # MOTOR_TORQUE 1|10@0+
    return dict(t1ab=t, b0=b0.astype(np.uint8), b1=b1.astype(np.uint8), b2=b2.astype(np.uint8),
                src=np.array(TAP["src"], np.int16), dlc=np.array(TAP["dlc"], np.int16),
                mt=mt.astype(np.int16),
                config_valid=((b0 >> 7) & 1).astype(np.uint8),
                dtc_bit2=((b0 >> 2) & 1).astype(np.uint8),
                checksum=(b2 & 0x0F).astype(np.uint8),
                counter=((b2 >> 4) & 0x03).astype(np.uint8),
                output_disabled=((b2 >> 6) & 1).astype(np.uint8))


def _tap_report(tag, A):
    n = len(A["t1ab"])
    if not n:
        print(f"  {tag}: 🛑 ZERO 0x1AB frames")
        return {}
    src = Counter(int(s) for s in A["src"])
    mt = A["mt"].astype(int)
    dt = np.diff(A["t1ab"])
    dt = dt[(dt > 0) & (dt < 1.0)]
    hz = 1.0 / np.median(dt) if len(dt) else float("nan")
    ctr = A["counter"].astype(int)
    step = np.diff(ctr) % 4
    out = dict(frames=n, src=dict(src), rate_hz=float(hz),
               dlc=dict(Counter(int(x) for x in A["dlc"])),
               mt_nonzero_frac=float(np.mean(mt != 0)), mt_distinct=int(len(np.unique(mt))),
               mt_min=int(mt.min()), mt_max=int(mt.max()),
               mt_p50=float(np.percentile(mt, 50)), mt_p95=float(np.percentile(mt, 95)),
               mt_p99=float(np.percentile(mt, 99)),
               mt_sat_frac=float(np.mean(mt >= 1023)),
               counter_step1_frac=float(np.mean(step == 1)) if len(step) else float("nan"),
               checksum_distinct=int(len(np.unique(A["checksum"]))),
               config_valid_duty=float(A["config_valid"].mean()),
               output_disabled_duty=float(A["output_disabled"].mean()))
    print(f"  {tag}: {n:,} frames  src={dict(src)}  {hz:.2f} Hz  dlc={out['dlc']}")
    print(f"      MOTOR_TORQUE  nonzero {100*out['mt_nonzero_frac']:.2f}%  distinct "
          f"{out['mt_distinct']}  range [{out['mt_min']},{out['mt_max']}]  "
          f"p50/p95/p99 {out['mt_p50']:.0f}/{out['mt_p95']:.0f}/{out['mt_p99']:.0f}  "
          f"saturated {100*out['mt_sat_frac']:.3f}%")
    print(f"      COUNTER +1 {100*out['counter_step1_frac']:.2f}%  CHECKSUM distinct "
          f"{out['checksum_distinct']}/16  CONFIG_VALID duty {out['config_valid_duty']:.4f}  "
          f"OUTPUT_DISABLED duty {out['output_disabled_duty']:.4f}")
    return out


# ======================================================================================
#  THE raw14 OFF-BY-ONE FIX -- derived and ASSERTED, never assumed
# ======================================================================================
def _row2raw14(z):
    """Index into `raw14_*` for each row of the extractor's grid.  Asserts an EXACT match.

    Structure of the defect: `D.extract` appends to `raw14_*` on EVERY 0x14A frame but appends a
    ROW only once `last18` is non-None, and that is the ONLY skip -- so the map is a CONSTANT LEAD
    equal to the number of 0x14A frames arriving before the first 0x18F.

    🛑 A `searchsorted` map on the timestamps is WRONG and this route proves it: `evt.can` can carry
    two 0x14A frames in one event, which share `logMonoTime` exactly (3,018 duplicate raw14
    timestamps on r77), so `searchsorted` collapses onto the first of each tie and mispairs 1,604
    rows.  The timestamp check still PASSES on that map -- only the byte check catches it.  Both
    are therefore asserted, and the constant-lead map is the one used.
    """
    t = np.asarray(z["t"], float)
    r14t = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    probe = np.asarray(z["probe"], int) & 0xFF
    lead = int(len(r14t) - len(t))
    ok_lead = bool(lead >= 0 and np.all(r14t[lead:] == t) and np.all(b4[lead:] == probe))
    ss = np.clip(np.searchsorted(r14t, t), 0, len(r14t) - 1)
    rep = dict(n_rows=int(len(t)), n_raw14=int(len(r14t)), lead=lead,
               constant_lead_holds=ok_lead,
               dup_raw14_timestamps=int(np.sum(np.diff(r14t) == 0)),
               searchsorted_would_mispair=int(np.sum(b4[ss] != probe)))
    # 🛑 assert a BOOLEAN -- a check that prints nothing is not a check that passed
    assert ok_lead, ("row2raw14: the constant-lead map does NOT reproduce (t, probe) exactly -- "
                     "the extractor's append logic has changed")
    idx = np.arange(len(t), dtype=np.int32) + lead
    assert bool(np.all(r14t[idx] == t)), "row2raw14: timestamp check failed on the final map"
    assert bool(np.all(b4[idx] == probe)), "row2raw14: byte4 check failed on the final map"
    return idx, rep


# ======================================================================================
def extract_route(route=ROUTE):
    global _TAP_ON
    _tap_reset()
    _TAP_ON = True
    D.extract(route)
    _TAP_ON = False
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    f = ROOT / cdir / f"{stem}.npz"
    z = dict(np.load(f, allow_pickle=True))
    t0 = float(z["t0_mono"][0])
    A = _tap_arrays(t0)
    print(f"\n  0x1AB FULL TAP, route {route}")
    rep = _tap_report(f"r{route}", A)
    for k, v in A.items():
        z["ab_" + k] = v
    idx, r14rep = _row2raw14(z)
    z["row2raw14"] = idx
    print(f"  raw14 index map: rows {r14rep['n_rows']:,}  raw14 {r14rep['n_raw14']:,}  "
          f"lead {r14rep['lead']}  constant_lead_holds={r14rep['constant_lead_holds']}  "
          f"dup 0x14A timestamps {r14rep['dup_raw14_timestamps']:,}  "
          f"a searchsorted map would mispair {r14rep['searchsorted_would_mispair']:,} rows")
    np.savez_compressed(f, **z)
    rep["row2raw14"] = r14rep
    (ROOT / cdir / f"{stem}_1ab.json").write_text(json.dumps(rep, indent=1, default=float))
    D.split(route)
    segs = {k: dict(complete_messages=v, truncated=k in TRUNCATED,
                    error=TRUNCATED.get(k, (0, None))[1]) for k, v in sorted(MSG_COUNT.items())}
    (ROOT / cdir / f"{stem}_segments.json").write_text(json.dumps(segs, indent=1))
    return rep


# ======================================================================================
#  IDENTITY -- SPEC §4.  Single frame, parameter-free.
# ======================================================================================
def identity(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    field = (b4 >> 3) & 0x1F
    n = len(field)
    odd = (field & 1) == 1
    gate_ok = (b4 & B4_GATE_FAILED) == 0
    v90_only = np.isin(field, sorted(V90_ONLY))
    pre = np.isin(field, sorted(PRE_V90_ALPHABET))
    fu, fc = np.unique(field, return_counts=True)
    out = dict(route=route, frames=int(n),
               n_b4_zero=int(gate_ok.sum()), frac_b4_zero=float(gate_ok.mean()),
               n_v90_only_value=int(v90_only.sum()), frac_v90_only_value=float(v90_only.mean()),
               n_pre_v90_alphabet=int(pre.sum()), frac_pre_v90_alphabet=float(pre.mean()),
               all_odd=bool(odd.all()), n_even=int((~odd).sum()),
               field_hist={int(v): int(c) for v, c in zip(fu, fc)})
    out["verdict"] = ("V90 IS ON THE CAR" if out["n_b4_zero"] > 0 else
                      "🛑 NO b4==0 FRAME -- V90 identity FAILS; everything downstream is "
                      "uninterpretable")
    print(f"\n  === V90 IDENTITY (SPEC §4), route {route}: {n:,} 0x14A frames ===")
    print("    field = (byte4>>3)&0x1F histogram:")
    print("      " + "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(fu, fc)))
    print(f"    MAP VALIDATOR  b3 == 1 on every frame (all field values ODD): {out['all_odd']}"
          f"   even values: {out['n_even']:,}")
    print(f"    b4 == 0 (observer gate OK)     : {out['n_b4_zero']:,} frames "
          f"({100*out['frac_b4_zero']:.4f} %)   <-- IMPOSSIBLE on V86B/V87/V88/V89")
    print(f"    field in the V90-ONLY set      : {out['n_v90_only_value']:,} "
          f"({100*out['frac_v90_only_value']:.4f} %)")
    print(f"    field in the pre-V90 alphabet  : {out['n_pre_v90_alphabet']:,} "
          f"({100*out['frac_pre_v90_alphabet']:.4f} %)")
    print(f"    VERDICT: {out['verdict']}")
    (ROOT / cdir / f"{stem}_identity.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  PROBE HEALTH -- every rung's duty, engaged/manual, and by wheel rate
# ======================================================================================
RATE_BINS = [(0.0, 0.35), (0.35, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0),
             (13.0, 25.0), (25.0, 50.0), (50.0, 1e9)]


def health(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    # 🛑 SAFE PAIRING: (raw14_t, raw14_b4).  Never (t, raw14_b4).
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    rt = np.asarray(z["t"], float)
    lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
    v = np.abs(np.interp(t14, rt, np.asarray(z["cs_v"], float)))
    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(rt)
    dt[dt <= 0] = np.median(dt[dt > 0]) if (dt > 0).any() else 0.01
    rate_row = np.abs(np.gradient(ang) / dt)
    rate = np.interp(t14, rt, rate_row)

    bits = {"b7_sign_6b26": B7_SIGN_6B26, "b6_model_ge512": B6_MODEL_GE512,
            "b5_friction_nz": B5_FRICTION_NZ, "b4_gate_failed": B4_GATE_FAILED,
            "b3_fingerprint": B3_FINGERPRINT}
    out = {"route": route, "n": int(len(b4)), "engaged_frac": float(lat.mean())}
    print(f"\n  === V90 RUNG HEALTH, route {route} ({len(b4):,} 0x14A frames, "
          f"{100*lat.mean():.2f} % engaged) ===")
    for name, m in bits.items():
        s = (b4 & m) != 0
        d = dict(all=float(s.mean()),
                 engaged=float(s[lat].mean()) if lat.sum() else float("nan"),
                 manual=float(s[~lat].mean()) if (~lat).sum() else float("nan"),
                 engaged_moving=float(s[lat & (v > 0.5)].mean())
                 if (lat & (v > 0.5)).sum() else float("nan"))
        d["interpretable"] = bool(0.0 < d["all"] < 1.0)
        by = {}
        for lo, hi in RATE_BINS:
            sel = lat & (rate >= lo) & (rate < hi)
            by[f"{lo}-{hi if hi < 1e9 else '+'}"] = dict(
                n=int(sel.sum()), duty=float(s[sel].mean()) if sel.sum() else float("nan"))
        d["by_rate_engaged"] = by
        out[name] = d
        flag = "" if d["interpretable"] else "   🛑 DEAD/RAILED -- NOT INTERPRETABLE"
        print(f"    {name:16s} all {d['all']:.4f}  engaged {d['engaged']:.4f}  "
              f"manual {d['manual']:.4f}  eng&moving {d['engaged_moving']:.4f}{flag}")
        print("        by |wheel rate| (engaged): " +
              "  ".join(f"{k}:{vv['duty']:.3f}(n={vv['n']:,})" for k, vv in by.items()))

    # ---- the (b6, b5) 2x2, engaged
    b6 = (b4 & B6_MODEL_GE512) != 0
    b5 = (b4 & B5_FRICTION_NZ) != 0
    tab = {}
    for i in (0, 1):
        for j in (0, 1):
            sel = lat & (b6 == bool(i)) & (b5 == bool(j))
            tab[f"b6={i},b5={j}"] = dict(n=int(sel.sum()),
                                         frac=float(sel.sum() / max(1, lat.sum())))
    out["b6_b5_2x2_engaged"] = tab
    print("    (b6,b5) 2x2, ENGAGED: " + "  ".join(f"{k} {v['frac']:.4f}" for k, v in tab.items()))
    (ROOT / cdir / f"{stem}_health.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  EXPOSURE CENSUS -- verbatim from `decode/extract_r75_r76.py`
# ======================================================================================
SPEED_BANDS = [(0, 5), (5, 20), (20, 50), (50, 80), (80, 1e9)]
DT = 0.01


def _bands(vk, sel):
    return {f"{lo}-{hi if hi < 1e9 else '+'} km/h":
            dict(frames=int((sel & (vk >= lo) & (vk < hi)).sum()),
                 sec=float((sel & (vk >= lo) & (vk < hi)).sum() * DT))
            for lo, hi in SPEED_BANDS}


def census(route=ROUTE):
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    C = ROOT / cdir
    z = np.load(C / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    seg = np.asarray(z["seg"], int)
    v = np.abs(np.asarray(z["cs_v"], float))
    vk = v * 3.6
    lat = np.asarray(z["cc_lat"], float) > 0.5
    n = len(t)
    dur = float(t[-1] - t[0])
    rate = (n - 1) / dur if dur > 0 else float("nan")

    out = {"route": route, "frames": n, "duration_s": dur, "row_rate_hz": float(rate),
           "engaged_frames": int(lat.sum()), "engaged_frac": float(lat.mean()),
           "engaged_sec": float(lat.sum() * DT), "engaged_min": float(lat.sum() * DT / 60.0),
           "manual_frames": int((~lat).sum()), "manual_sec": float((~lat).sum() * DT)}
    print(f"\n  === EXPOSURE CENSUS, route {route} ===")
    print(f"    {n:,} frames   {dur:.1f} s ({dur/60:.2f} min)   row grid {rate:.2f} Hz")
    print(f"    ENGAGED {out['engaged_frac']*100:.2f}%  =  {out['engaged_sec']:.1f} s "
          f"({out['engaged_min']:.2f} min)      MANUAL {out['manual_sec']:.1f} s")

    for tag, sel in (("all", np.ones(n, bool)), ("engaged", lat), ("manual", ~lat)):
        if not sel.sum():
            continue
        q = {p: float(np.percentile(vk[sel], p)) for p in (50, 90, 99)}
        out[f"speed_{tag}"] = dict(n=int(sel.sum()), median_kmh=q[50], p90_kmh=q[90],
                                   p99_kmh=q[99], max_kmh=float(vk[sel].max()))
        out[f"bands_{tag}"] = _bands(vk, sel)
        print(f"    {tag:8s} v median {q[50]:6.2f}  p90 {q[90]:6.2f}  p99 {q[99]:6.2f}  "
              f"max {vk[sel].max():6.2f} km/h")
        print("             " + "  ".join(f"{k}: {d['sec']:7.1f}s"
                                          for k, d in out[f"bands_{tag}"].items()))

    hi = lat & (vk >= 50)
    out["engaged_sec_ge_50kmh"] = float(hi.sum() * DT)
    out["engaged_sec_ge_80kmh"] = float((lat & (vk >= 80)).sum() * DT)
    print(f"    🛑 ENGAGED >= 50 km/h : {out['engaged_sec_ge_50kmh']:.1f} s   "
          f">= 80 km/h : {out['engaged_sec_ge_80kmh']:.1f} s")

    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(t)
    dt[dt <= 0] = np.median(dt[dt > 0]) if (dt > 0).any() else 0.01
    rate_dps = np.abs(np.gradient(ang) / dt)
    for lo, hi_, tag in ((1.0, 13.0, "micro_ratchet_1_13dps"),
                         (13.0, 50.0, "ratchet_13_50dps"),
                         (50.0, 1e9, "macro_gt50dps")):
        m = lat & (rate_dps >= lo) & (rate_dps < hi_)
        out[f"rate_{tag}_sec"] = float(m.sum() * DT)
    print(f"    RATE REGIMES engaged: micro (1-13 °/s) {out['rate_micro_ratchet_1_13dps_sec']:.1f} s"
          f"   ratchet (13-50) {out['rate_ratchet_13_50dps_sec']:.1f} s"
          f"   macro (>50) {out['rate_macro_gt50dps_sec']:.1f} s")

    man = ~lat
    for thr in (0.1, 0.2, 0.5):
        out[f"manual_parked_frac_lt_{thr}"] = (float((man & (v < thr)).mean() / man.mean())
                                               if man.sum() else float("nan"))
    print(f"    manual frames PARKED: v<0.1 {100*out['manual_parked_frac_lt_0.1']:.1f}%   "
          f"v<0.2 {100*out['manual_parked_frac_lt_0.2']:.1f}%   "
          f"v<0.5 {100*out['manual_parked_frac_lt_0.5']:.1f}%")

    ep, cur = [], 0
    for x in lat:
        if x:
            cur += 1
        else:
            if cur:
                ep.append(cur)
            cur = 0
    if cur:
        ep.append(cur)
    eps = np.array(ep, float) * DT
    out["episodes"] = dict(n=int(len(eps)), n_ge_2s=int((eps >= 2).sum()),
                           n_ge_10s=int((eps >= 10).sum()),
                           longest_s=float(eps.max()) if len(eps) else 0.0,
                           median_s=float(np.median(eps)) if len(eps) else 0.0)
    print(f"    engagement episodes: {out['episodes']['n']} total, "
          f"{out['episodes']['n_ge_2s']} >=2 s, {out['episodes']['n_ge_10s']} >=10 s, "
          f"longest {out['episodes']['longest_s']:.1f} s")

    persec = {}
    print(f"\n    {'seg':>4} {'frames':>8} {'sec':>7} {'v med':>7} {'v p90':>7} {'v max':>7} "
          f"{'eng%':>6} {'eng s':>7} {'eng>=50':>8} {'park%':>6}")
    for s in sorted(set(seg.tolist())):
        m = seg == s
        e = m & lat
        d = dict(frames=int(m.sum()), sec=float(m.sum() * DT),
                 v_median_kmh=float(np.median(vk[m])), v_p90_kmh=float(np.percentile(vk[m], 90)),
                 v_max_kmh=float(vk[m].max()),
                 engaged_frac=float(lat[m].mean()), engaged_sec=float(e.sum() * DT),
                 engaged_sec_ge_50=float((e & (vk >= 50)).sum() * DT),
                 engaged_sec_ge_80=float((e & (vk >= 80)).sum() * DT),
                 parked_frac=float((v[m] < 0.2).mean()))
        d["bands_engaged"] = _bands(vk, e)
        persec[int(s)] = d
        print(f"    {s:>4} {d['frames']:>8,} {d['sec']:>7.1f} {d['v_median_kmh']:>7.2f} "
              f"{d['v_p90_kmh']:>7.2f} {d['v_max_kmh']:>7.2f} {100*d['engaged_frac']:>5.1f}% "
              f"{d['engaged_sec']:>7.1f} {d['engaged_sec_ge_50']:>8.1f} "
              f"{100*d['parked_frac']:>5.1f}%")
    out["per_segment"] = persec

    ev = json.loads((C / f"{stem}_events.json").read_text())
    cnt = Counter(e["name"] for e in ev)
    out["events"] = dict(cnt)
    out["events_immediate"] = dict(Counter(e["name"] for e in ev if e.get("immediate")))
    out["events_soft"] = dict(Counter(e["name"] for e in ev if e.get("soft")))
    out["sentinels"] = dict(a14=int(z["sentinels"][0]), a18=int(z["sentinels"][1]))
    b0 = np.asarray(z["raw1ab_b0"], int)
    dtc = (b0 >> 2) & 1
    out["dtc_bit2_duty"] = float(dtc.mean()) if len(dtc) else float("nan")
    out["dtc_bit2_transitions"] = int(np.sum(np.diff(dtc) != 0)) if len(dtc) > 1 else 0
    if "ab_output_disabled" in z.files:
        out["output_disabled_duty"] = float(np.asarray(z["ab_output_disabled"], int).mean())
        out["config_valid_duty"] = float(np.asarray(z["ab_config_valid"], int).mean())
    st = np.asarray(z["raw18_st"], int)
    out["steer_status_hist"] = {int(k): int(c) for k, c in zip(*np.unique(st, return_counts=True))}
    print(f"\n    onroadEvents ({len(ev)} total): " +
          ", ".join(f"{k}:{c}" for k, c in cnt.most_common()))
    print(f"    sentinels 0x14A {out['sentinels']['a14']}  0x18F {out['sentinels']['a18']}   "
          f"DTC bit2 duty {out['dtc_bit2_duty']:.5f} ({out['dtc_bit2_transitions']} transitions)")
    print(f"    STEER_STATUS hist {out['steer_status_hist']}")
    if "output_disabled_duty" in out:
        print(f"    OUTPUT_DISABLED duty {out['output_disabled_duty']:.5f}   "
              f"CONFIG_VALID duty {out['config_valid_duty']:.5f}")
    (C / f"{stem}_census.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        extract_route()
        identity()
        health()
        census()
    elif args[0] == "extract":
        extract_route()
    elif args[0] == "identity":
        identity()
    elif args[0] == "health":
        health()
    elif args[0] == "census":
        census()
    else:
        raise SystemExit(__doc__)
