#!/usr/bin/env python3
r"""Extract routes `75` and `76` (believed the V89 drive) into `_cache_r75/` and `_cache_r76/`,
tap the FULL 0x1AB payload, and run the PRE-REGISTERED build-identity test whose control is the
already-flown route 73 (V88).

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `extract_r6e.py`, `extract_r6f_r70.py`,
`extract_r71.py` and `extract_r73.py` do, this file adds rows to `decode_v84_probe_r6d.ROUTES` and
calls that module's `extract()` / `split()` -- the SAME code that wrote `_cache_r6d/` .. `_cache_r73/`.
Field names, ZOH/interp convention, IMU axis pick, sentinel definition and `PASS_1D` are therefore
bit-for-bit the ones every prior route was scored with.

★ THE IDENTITY TEST -- PARAMETER-FREE, AND ITS CONTROL IS A FLOWN ROUTE
    V88's cave read `gp-0x6b98`, the SAME cell the 427 (`0x1AB`) packer reads:
        wire = clamp( (|gp-0x6b98| * 5) >> 3 , 0, 0x3FF )   and   (256 * 5) >> 3 == 160
    so on V88, and only on V88,   b6 == (wire >= 160)   frame by frame.  Measured 0.9654 on r73.

    V89 repoints the cave to `gp-0x6ae2` (the modelled Coulomb friction x 1024) and changes the
    rung to `sar 0x6`.  The cave and the 427 wire are then TWO DIFFERENT CELLS, so that agreement
    MUST COLLAPSE TOWARD CHANCE, where chance is computed from each route's OWN marginals.
        ~chance  => V89 flew        ~0.97  => the car is still on V88.

    🛑 The 0x14A byte-4 ALPHABET cannot decide this: V89 carries V86B's cave structurally (same
    five bit weights, same fingerprint), so its reachable alphabet is identical to V86B/V87/V88's.
    The alphabet is reported as a HEALTH statistic, never as the verdict.

★ V89's CAVE BIT LAYOUT (`build_v89_tva.py`, structurally V86B's with a new source + `sar 0x6`)
        b7 = gp-0x6ae2 <  0            sign of the modelled friction term
        b6 = |gp-0x6ae2| >= 64         friction magnitude >= 0.0625        <- H2's rung
        b5 = gp-0x6ae2 != 0            THE PROBE FIRED                     <- H1's liveness
        b4 = gp-0x67ab < 2             the gate
        b3 = 1                         fingerprint
    bits 2:0 are stock STEER_SENSOR_STATUS, preserved.

Usage:
    python extract_r75_r76.py                    # extract 75 and 76, then identity + census
    python extract_r75_r76.py extract 75 76
    python extract_r75_r76.py identity 75 73
    python extract_r75_r76.py census 75 76
    python extract_r75_r76.py h1 75 76           # H1: the cave rung duties
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v84_probe_r6d as D  # noqa: E402  -- THE extractor that wrote every cache since r6d
import rlog_parse                 # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"

# route key -> (route stem, n segs, cache dir, per-seg prefix, npz stem, label)
D.ROUTES["75"] = ("75604b0a432fdc89_00000075--9bbcb3f7da", 16, "_cache_r75", "r75s", "r75",
                  "UNVERIFIED")
D.ROUTES["76"] = ("75604b0a432fdc89_00000076--c81e964e05", 13, "_cache_r76", "r76s", "r76",
                  "UNVERIFIED")
D.ROUTES.setdefault("73", ("75604b0a432fdc89_00000073--9380c74d52", 11, "_cache_r73", "r73s", "r73",
                           "V88"))
D.ROUTES.setdefault("71", ("75604b0a432fdc89_00000071--ac50da2a6a", 4, "_cache_r71", "r71s", "r71",
                           "V87"))

# byte-4 alphabets, carried verbatim from `extract_r73.py`
V86_ONLY = {0x48, 0x58, 0xC8, 0xD8}
V86B_ONLY = {0x28, 0x38, 0xA8, 0xB8}
SHARED_B4 = {0x08, 0x18, 0x68, 0x78, 0xE8, 0xF8}

# the identity test's constants -- taken from the build scripts, never re-typed here
BIT_SIGN = 0x80                  # b7
BIT_MAG = 0x40                   # b6
BIT_NONZERO = 0x20               # b5  ★ H1's liveness rung
BIT_GATE = 0x10                  # b4
BIT_FINGERPRINT = 0x08           # b3
WIRE_T = 160                     # (256 * 5) >> 3 -- V88's predicate, the one that must COLLAPSE
NEAR_TOL = 0.010                 # nearest-sample pairing tolerance, one 100 Hz 0x14A period
ZOH_TOL = 0.020                  # ZOH pairing tolerance, one 427 period

# ======================================================================================
# 0x1AB TAP -- a pass-through generator, so the extractor's event stream is unchanged
# ======================================================================================
_ORIG_READ = rlog_parse.read_messages
TAP = {"t": [], "b0": [], "b1": [], "b2": [], "src": [], "dlc": []}
TRUNCATED, MSG_COUNT = {}, {}
_TAP_ON = False


def _read_messages_tapped(path):
    """Tolerant reader (carried verbatim from `extract_r73.py`) + the 0x1AB tap."""
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
def extract_route(route):
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
    np.savez_compressed(f, **z)
    (ROOT / cdir / f"{stem}_1ab.json").write_text(json.dumps(rep, indent=1))
    D.split(route)
    segs = {k: dict(complete_messages=v, truncated=k in TRUNCATED,
                    error=TRUNCATED.get(k, (0, None))[1]) for k, v in sorted(MSG_COUNT.items())}
    (ROOT / cdir / f"{stem}_segments.json").write_text(json.dumps(segs, indent=1))
    return rep


# ======================================================================================
#  IDENTITY, PART A -- the 0x14A byte-4 alphabet (HEALTH, not the verdict)
# ======================================================================================
def identity(route):
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    f = z["raw14_b4"].astype(int) & 0xF8
    n = len(f)
    v86 = int(sum(int(x) in V86_ONLY for x in f))
    v86b = int(sum(int(x) in V86B_ONLY for x in f))
    other = int(sum(int(x) not in (V86_ONLY | V86B_ONLY | SHARED_B4) for x in f))
    fu, fc = np.unique(f, return_counts=True)
    print(f"\n  0x14A byte4 alphabet, route {route}: {n:,} frames")
    print("    " + " ".join(f"0x{int(v):02X}:{c}" for v, c in zip(fu, fc)))
    print(f"    V86-only {v86}   V86B-only {v86b}   outside both alphabets {other}")
    print("    ⚠ V89 carries V86B's cave STRUCTURALLY ⇒ this alphabet is the SAME set on V86B, V87,")
    print("      V88 and V89.  It is health, NOT the discriminator.")
    return dict(frames=n, v86_only=v86, v86b_only=v86b, outside=other,
                hist={f"0x{int(v):02X}": int(c) for v, c in zip(fu, fc)})


# ======================================================================================
#  IDENTITY, PART B -- THE LOAD-BEARING TEST:  b6  ==  (427 wire >= 160)
# ======================================================================================
def _pair_nearest(t_ref, t_src, tol):
    """For each `t_ref`, index of the NEAREST `t_src` sample, and a validity mask at `tol`."""
    j = np.searchsorted(t_src, t_ref)
    jl = np.clip(j - 1, 0, len(t_src) - 1)
    jr = np.clip(j, 0, len(t_src) - 1)
    dl = np.abs(t_ref - t_src[jl])
    dr = np.abs(t_ref - t_src[jr])
    idx = np.where(dl <= dr, jl, jr)
    dt = np.minimum(dl, dr)
    return idx, dt <= tol, dt


def _pair_zoh(t_ref, t_src, tol):
    """Last `t_src` sample at or before each `t_ref` (the kit's `held_last` convention)."""
    j = np.searchsorted(t_src, t_ref, side="right") - 1
    ok = j >= 0
    idx = np.clip(j, 0, len(t_src) - 1)
    dt = np.where(ok, t_ref - t_src[idx], np.inf)
    return idx, ok & (dt <= tol) & (dt >= 0), dt


def b6_vs_427(route, verbose=True):
    """The pre-registered V88-vs-V89 discriminator.  No free parameter in the predicate itself."""
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    if "ab_mt" not in z.files:
        raise SystemExit(f"route {route}: the 0x1AB tap is not in {stem}.npz -- re-run `extract`")
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    o = np.argsort(t14, kind="stable")
    t14, b4 = t14[o], b4[o]
    b6 = ((b4 & BIT_MAG) != 0)

    t427 = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    o = np.argsort(t427, kind="stable")
    t427, wire = t427[o], wire[o]
    pred = wire >= WIRE_T

    # engagement, brought to the 427 timestamps on the extractor's own row grid
    rt = np.asarray(z["t"], float)
    lat = np.interp(t427, rt, np.asarray(z["cc_lat"], float)) > 0.5

    out = {"route": route, "n_14a": int(len(t14)), "n_427": int(len(t427)),
           "wire_threshold": WIRE_T, "bit": "b6 = 0x40",
           "pairing": f"nearest 0x14A sample, |dt| <= {NEAR_TOL*1000:.0f} ms"}

    idx, ok, dt = _pair_nearest(t427, t14, NEAR_TOL)
    agree = (b6[idx] == pred)
    out["nearest"] = dict(
        tol_ms=NEAR_TOL * 1e3, paired=int(ok.sum()), paired_frac=float(ok.mean()),
        agreement=float(agree[ok].mean()),
        agreement_engaged=float(agree[ok & lat].mean()) if (ok & lat).sum() else float("nan"),
        agreement_manual=float(agree[ok & ~lat].mean()) if (ok & ~lat).sum() else float("nan"),
        n_engaged=int((ok & lat).sum()), n_manual=int((ok & ~lat).sum()),
        dt_median_ms=float(np.median(dt[ok]) * 1e3))
    # chance level from the two marginals -- what "no relationship" would score
    pb, pw = float(b6[idx][ok].mean()), float(pred[ok].mean())
    out["nearest"]["duty_b6"] = pb
    out["nearest"]["duty_wire_ge_160"] = pw
    out["nearest"]["chance"] = float(pb * pw + (1 - pb) * (1 - pw))
    far = ok & (np.abs(wire - WIRE_T) > 40)
    out["nearest"]["agreement_far_from_threshold"] = (float(agree[far].mean()) if far.sum()
                                                      else float("nan"))
    out["nearest"]["n_far"] = int(far.sum())

    idx2, ok2, _ = _pair_zoh(t427, t14, ZOH_TOL)
    ag2 = (b6[idx2] == pred)
    out["zoh"] = dict(tol_ms=ZOH_TOL * 1e3, paired=int(ok2.sum()),
                      agreement=float(ag2[ok2].mean()) if ok2.sum() else float("nan"))

    lags, best = [], (-1.0, 0.0)
    for lag_ms in range(-60, 61, 10):
        i3, o3, _ = _pair_nearest(t427 + lag_ms * 1e-3, t14, NEAR_TOL)
        a3 = float((b6[i3] == pred)[o3].mean()) if o3.sum() else float("nan")
        lags.append({"lag_ms": lag_ms, "agreement": a3, "paired": int(o3.sum())})
        if np.isfinite(a3) and a3 > best[0]:
            best = (a3, lag_ms)
    out["lag_sweep"] = lags
    out["best_lag_ms"] = best[1]
    out["best_lag_agreement"] = best[0]

    if verbose:
        n = out["nearest"]
        print(f"\n  === IDENTITY TEST  b6 == (427 wire >= {WIRE_T})  --  route {route} ===")
        print(f"    0x14A frames {out['n_14a']:,}   427 frames {out['n_427']:,}   "
              f"paired {n['paired']:,} ({100*n['paired_frac']:.2f}%)  median |dt| "
              f"{n['dt_median_ms']:.2f} ms")
        print(f"    AGREEMENT (nearest, <= {NEAR_TOL*1e3:.0f} ms) : {n['agreement']:.4f}")
        print(f"      engaged {n['agreement_engaged']:.4f} (n={n['n_engaged']:,})   "
              f"manual {n['agreement_manual']:.4f} (n={n['n_manual']:,})")
        print(f"      duty b6 {n['duty_b6']:.4f}   duty wire>=160 {n['duty_wire_ge_160']:.4f}   "
              f"⇒ chance level {n['chance']:.4f}")
        print(f"      away from the edge (|wire-160|>40): "
              f"{n['agreement_far_from_threshold']:.4f} (n={n['n_far']:,})")
        print(f"    ZOH variant (<= {ZOH_TOL*1e3:.0f} ms): {out['zoh']['agreement']:.4f}")
        print(f"    best lag {out['best_lag_ms']:+d} ms -> {out['best_lag_agreement']:.4f}")
    return out


def identity_verdict(route="75", control="73"):
    a = b6_vs_427(route)
    b = b6_vs_427(control)
    va, vb = a["nearest"]["agreement"], b["nearest"]["agreement"]
    ca = a["nearest"]["chance"]
    print("\n  ---------------------------------------------------------------------------")
    print(f"    route {route}: {va:.4f} (its own chance {ca:.4f})      "
          f"control route {control} (V88 flew): {vb:.4f}")
    if va >= 0.90:
        v = f"🛑 route {route} reads like V88 -- V89 did NOT fly"
    elif abs(va - ca) <= 0.06:
        v = f"V89 FLEW on route {route} -- agreement collapsed to its own chance level"
    else:
        v = f"🛑 AMBIGUOUS ({va:.4f} vs chance {ca:.4f})"
    print(f"    VERDICT: {v}")
    print("  ---------------------------------------------------------------------------")
    return dict(test=a, control=b, verdict=v)


# ======================================================================================
#  H1 -- THE PROBE MUST FIRE.  Duties of every cave rung, engaged and manual.
# ======================================================================================
def h1_rungs(route):
    """b5 = friction != 0 (liveness) · b6 = |friction*1024| >= 64 (the rung) · b7 = sign."""
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    # 🛑 SAFE PAIRING ONLY: (raw14_t, raw14_b4).  Never (t, raw14_b4) -- the kit-wide off-by-one.
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    rt = np.asarray(z["t"], float)
    lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
    v = np.abs(np.interp(t14, rt, np.asarray(z["cs_v"], float)))

    out = {"route": route, "n": int(len(b4))}
    bits = {"b7_sign": BIT_SIGN, "b6_mag64": BIT_MAG, "b5_nonzero": BIT_NONZERO,
            "b4_gate": BIT_GATE, "b3_fingerprint": BIT_FINGERPRINT}
    print(f"\n  === H1 CAVE RUNG DUTIES, route {route} ({len(b4):,} 0x14A frames) ===")
    print(f"    engaged {100*lat.mean():.2f}%")
    for name, m in bits.items():
        s = (b4 & m) != 0
        d = dict(all=float(s.mean()),
                 engaged=float(s[lat].mean()) if lat.sum() else float("nan"),
                 manual=float(s[~lat].mean()) if (~lat).sum() else float("nan"),
                 engaged_moving=float(s[lat & (v > 0.5)].mean()) if (lat & (v > 0.5)).sum()
                 else float("nan"))
        out[name] = d
        print(f"    {name:16s} duty all {d['all']:.4f}   engaged {d['engaged']:.4f}   "
              f"manual {d['manual']:.4f}   engaged&moving {d['engaged_moving']:.4f}")
    fu, fc = np.unique(b4 & 0xF8, return_counts=True)
    out["byte4_hist"] = {f"0x{int(a):02X}": int(c) for a, c in zip(fu, fc)}
    (ROOT / cdir / f"{stem}_h1.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  EXPOSURE CENSUS -- verbatim from extract_r73.py, plus the operator's RATE regimes
# ======================================================================================
SPEED_BANDS = [(0, 5), (5, 20), (20, 50), (50, 80), (80, 1e9)]
DT = 0.01                             # the kit's per-frame second, on the 100 Hz 0x14A row grid


def _bands(vk, sel):
    return {f"{lo}-{hi if hi < 1e9 else '+'} km/h":
            dict(frames=int((sel & (vk >= lo) & (vk < hi)).sum()),
                 sec=float((sel & (vk >= lo) & (vk < hi)).sum() * DT))
            for lo, hi in SPEED_BANDS}


def census(route):
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    C = ROOT / cdir
    z = np.load(C / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    seg = np.asarray(z["seg"], int)
    v = np.abs(np.asarray(z["cs_v"], float))            # m/s
    vk = v * 3.6                                        # km/h
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

    # ★ THE OPERATOR'S OWN REGIMES, on |steering rate| (deg/s), engaged
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
    # ---- the build-constant assertions, read from the build script, never re-typed here
    import build_v86b_tva as V86B
    import build_v88_tva as V88
    import build_v89_tva as V89
    assert V89.CAVE_BASE == V86B.CAVE_BASE and V89.CAVE_LEN == 62
    assert (V89.OLD_DISP, V89.NEW_DISP) == (0x6B98, 0x6AE2)
    assert (V89.OLD_SHIFT, V89.NEW_SHIFT) == (8, 6) and V89.NEW_MAG_T == 64
    assert (V89.K1_ADDR, V89.K1_OLD, V89.K1_NEW) == (0xC40D2, 102, 204)
    assert (V88.BIT_MAG, V86B.BIT_NONZERO, V86B.BIT_SIGN) == (BIT_MAG, BIT_NONZERO, BIT_SIGN)
    assert V88.WIRE_OF(256) == WIRE_T, "the 427 threshold V88 matched is not 160"
    print("  ✅ V89 = V88's cave with the source repointed gp-0x6b98 -> gp-0x6ae2 and sar 0x8 -> "
          "0x6.\n     ⇒ the cave and the 427 packer now read DIFFERENT cells, so V88's "
          f"`b6 == (wire >= {WIRE_T})` MUST collapse to chance.")

    args = sys.argv[1:]
    if not args:
        for r in ("75", "76"):
            extract_route(r)
        res = {}
        for r in ("75", "76"):
            res[r] = {"b4_alphabet": identity(r), "h1": h1_rungs(r),
                      "b6_vs_427": identity_verdict(r, "73"), "census": census(r)}
            json.dump(res[r], open(ROOT / f"_cache_r{r}" / f"r{r}_identity.json", "w"),
                      indent=1, default=float)
    elif args[0] == "extract":
        for r in args[1:]:
            extract_route(r)
    elif args[0] == "alphabet":
        for r in args[1:]:
            identity(r)
    elif args[0] == "h1":
        for r in args[1:]:
            h1_rungs(r)
    elif args[0] == "identity":
        identity_verdict(args[1] if len(args) > 1 else "75",
                         args[2] if len(args) > 2 else "73")
    elif args[0] == "census":
        for r in args[1:]:
            census(r)
    else:
        raise SystemExit(__doc__)
