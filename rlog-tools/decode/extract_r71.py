#!/usr/bin/env python3
r"""Extract route `71` (the V87 drive) into `_scratch/cache/r71/`, and tap the FULL 0x1AB payload.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `decode/extract_r6e.py` and `decode/extract_r6f_r70.py` do,
this file adds a row to `decode_v84_probe_r6d.ROUTES` and calls that module's `extract()` / `split()`
-- the SAME code that wrote `_scratch/cache/r6d/`.. `_scratch/cache/r70/`.  Field names, ZOH/interp convention, IMU
axis pick, sentinel definition and `PASS_1D` are therefore bit-for-bit the ones every prior route was
scored with.

★ WHAT IS NEW: V87's probe is a DISPLACEMENT EDIT on the 427 (`0x1AB`) transmit packer
(`0x55DF2` `e893` -> `6894`), so `MOTOR_TORQUE` now carries

    wire = clamp( (|gp-0x6b98| * 5) >> 3 , 0, 0x3FF )        # Honda's own abs / x5/8 / 10-bit clamp

The shared extractor keeps only `0x1AB` **byte 0** (for the DTC-active bit).  A generator TAP around
`rlog_parse.read_messages` records all three bytes and the `src` during the extractor's OWN single
pass -- no second decompression, and the extractor sees a byte-identical event stream.

DBC layout (Motorola bit numbering), verbatim from `studies/loop-causality/r67_1ab_census.py`:
    MOTOR_TORQUE     1|10@0+  -> byte0 bits[1:0] are the two MSBs, byte1 is the low 8
    CONFIG_VALID     7|1      -> byte0 bit 7
    CHECKSUM        19|4      -> byte2 bits[3:0]
    COUNTER         21|2      -> byte2 bits[5:4]
    OUTPUT_DISABLED 22|1      -> byte2 bit 6

Usage:
    python decode/extract_r71.py                # extract 71, tap 70 + 6f for the cross-build comparison
    python decode/extract_r71.py extract 71
    python decode/extract_r71.py tap 70 6f
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

# route key -> (route stem, n segs, cache dir, per-seg prefix, npz stem, label)
D.ROUTES["71"] = ("75604b0a432fdc89_00000071--ac50da2a6a", 4, "_scratch/cache/r71", "r71s", "r71",
                  "UNVERIFIED")
D.ROUTES.setdefault("70", ("75604b0a432fdc89_00000070--66544f819d", 4, "_scratch/cache/r70", "r70s", "r70",
                           "V86B"))
D.ROUTES.setdefault("6f", ("75604b0a432fdc89_0000006f--80ca318af4", 4, "_scratch/cache/r6f", "r6fs", "r6f",
                           "V86"))

# V87 carries V86B's 62-byte cave BYTE-FOR-BYTE, so the 0x14A byte-4 alphabet must read V86B.
# (build_v87_tva.CAVE_PAYLOAD is asserted equal to build_v86b_tva's payload below.)
V86_ONLY = {0x48, 0x58, 0xC8, 0xD8}
V86B_ONLY = {0x28, 0x38, 0xA8, 0xB8}
SHARED_B4 = {0x08, 0x18, 0x68, 0x78, 0xE8, 0xF8}

# ======================================================================================
# 0x1AB TAP -- a pass-through generator, so the extractor's event stream is unchanged
# ======================================================================================
_ORIG_READ = rlog_parse.read_messages
TAP = {"t": [], "b0": [], "b1": [], "b2": [], "src": [], "dlc": []}
TRUNCATED, MSG_COUNT = {}, {}
_TAP_ON = False


def _read_messages_tapped(path):
    """Tolerant reader (carried verbatim from `decode/extract_r6e.py`) + the 0x1AB tap."""
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


def tap_only(route):
    """0x1AB-only pass over an ALREADY-EXTRACTED route, for the cross-build comparison."""
    global _TAP_ON
    pref, nseg, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    t0 = float(z["t0_mono"][0])
    _tap_reset()
    _TAP_ON = True
    for s in range(nseg):
        p = RLOGDIR / f"{pref}--{s}--rlog.zst"
        if not p.exists():
            continue
        for _ in rlog_parse.read_messages(str(p)):
            pass
        print(f"  seg {s} done, 0x1AB frames so far {len(TAP['t'])}", flush=True)
    _TAP_ON = False
    A = _tap_arrays(t0)
    rep = _tap_report(f"r{route}", A)
    np.savez_compressed(ROOT / cdir / f"{stem}_1ab.npz", **A)
    (ROOT / cdir / f"{stem}_1ab.json").write_text(json.dumps(rep, indent=1))
    return rep


def identity(route):
    """0x14A byte-4 alphabet -- V87 must read V86B, because it carries V86B's cave verbatim."""
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
    return dict(frames=n, v86_only=v86, v86b_only=v86b, outside=other,
                hist={f"0x{int(v):02X}": int(c) for v, c in zip(fu, fc)})


if __name__ == "__main__":
    # the cave payload assertion -- V87 must be V86B's cave byte-for-byte, or the alphabet is wrong
    import build_v86b_tva as V86B
    import build_v87_tva as V87
    import build_v86_tva as V86
    _b = V86B.CAVE_PAYLOAD
    assert len(V87.CAVE_PAYLOAD) == 62 and _b[62:] == b"\xff" * 6, "cave pad shape changed"
    assert V87.CAVE_PAYLOAD == _b[:62], \
        "V87's cave is NOT V86B's payload -- the 0x14A identity alphabet below does not apply"
    assert V87.CAVE_PAYLOAD != V86.CAVE_PAYLOAD[:62] and V87.CAVE_BASE == V86B.CAVE_BASE
    assert (V86B.BIT_SIGN, V86B.BIT_MAG, V86B.BIT_NONZERO) == (0x80, 0x40, 0x20)
    assert (V86.BIT_SIGN, V86.BIT_MAG, V86.BIT_NONZERO) == (0x80, 0x20, 0x40)
    print("  ✅ V87.CAVE_PAYLOAD == build_v86b_tva.CAVE_PAYLOAD[:62]  (the 6-byte 0xFF pad aside),"
          "\n     and it DIFFERS from V86's ⇒ the V86B byte-4 alphabet applies to route 71.")

    args = sys.argv[1:]
    if not args:
        rep = extract_route("71")
        ident = identity("71")
        json.dump({"1ab": rep, "b4": ident},
                  open(ROOT / "_scratch/cache/r71" / "r71_identity.json", "w"), indent=1)
    elif args[0] == "extract":
        for r in args[1:]:
            extract_route(r)
    elif args[0] == "tap":
        for r in args[1:]:
            tap_only(r)
    elif args[0] == "identity":
        for r in args[1:]:
            identity(r)
