#!/usr/bin/env python3
"""Extract routes `6f` and `70` into `_scratch/cache/r6f/` and `_scratch/cache/r70/`, then ESTABLISH WHICH BUILD FLEW.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `decode/extract_r6e.py` does, this file adds rows to
`decode_v84_probe_r6d.ROUTES` and calls that module's `extract()` / `split()` -- the SAME code that
wrote `_scratch/cache/r6d/` (V84) and `_scratch/cache/r6e/` (V85).  Field names, ZOH/interp convention, IMU axis pick,
sentinel definition and `PASS_1D` are therefore bit-for-bit the ones every prior route was scored
with, so every `_r*_lib` / `_grind2_lib` / `score_*` harness loads these caches unchanged.

🛑 TRUNCATION.  Route `6e`'s last segment was torn mid-capnp-message and stock `read_messages` lost
the WHOLE route.  The tolerant wrapper from `decode/extract_r6e.py` is carried here verbatim: it yields every
COMPLETE message and stops at the tear.  `read_multiple_bytes` is strictly sequential, so nothing
partial can enter a cache.  Per-segment complete-message counts are recorded either way.

🛑 `probe_build`.  The shared extractor stamps a route label into `probe_build` from a table.  That
field is a HAND-ENTERED LABEL, not a measurement, and downstream code has quoted it as though it were
one.  Here it is written as `"UNVERIFIED"` by `extract()`, and only OVERWRITTEN once the
parameter-free identity battery in `identity()` returns a decisive verdict -- alongside
`build_identity` (the verdict) and `build_identity_basis` (the numbers behind it).

★ THE IDENTITY TEST HAS NO FREE PARAMETER.  V86 and V86B share ONE 68-byte cave; V86B swaps two
halfwords so the b6/b5 WEIGHTS trade places (`build_v86b_tva.build_cave`, asserted to differ from
V86's payload at EXACTLY two offsets).  Both caves compute `sign`, `nonzero`, `mag` from the SAME
register in the SAME pass, so the nesting is EXACT -- zero violations admitted, not "few":

    build   b7      b6        b5        b4    b3    exact laws
    V86     sign    nonzero   mag       gate  1     b7 => b6 , b5 => b6
    V86B    sign    mag       nonzero   gate  1     b7 => b5 , b6 => b5

⇒ the masked field `byte4 & 0xF8` splits into three disjoint sets:
    V86-ONLY  {0x48,0x58,0xC8,0xD8}   (b6 set, b5 clear)  -- IMPOSSIBLE on V86B
    V86B-ONLY {0x28,0x38,0xA8,0xB8}   (b5 set, b6 clear)  -- IMPOSSIBLE on V86
    SHARED    {0x08,0x18,0x68,0x78,0xE8,0xF8}
ONE frame in an exclusive set identifies the build; one frame violating a build's law refutes it.

Usage:
    python decode/extract_r6f_r70.py                # extract both, then identity + health + exposure
    python decode/extract_r6f_r70.py extract 6f 70
    python decode/extract_r6f_r70.py identity 6f 70
    python decode/extract_r6f_r70.py report 6f 70
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
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v84_probe_r6d as D  # noqa: E402  -- THE extractor that wrote _scratch/cache/r6d/ and _scratch/cache/r6e/
import rlog_parse                 # noqa: E402

import build_v86_tva as V86       # noqa: E402  -- the bit map comes from the BUILDERS, never a copy
import build_v86b_tva as V86B     # noqa: E402

# route key -> (route stem, n segs, cache dir, per-seg prefix, npz stem, label)
D.ROUTES["6f"] = ("75604b0a432fdc89_0000006f--80ca318af4", 4, "_scratch/cache/r6f", "r6fs", "r6f", "UNVERIFIED")
D.ROUTES["70"] = ("75604b0a432fdc89_00000070--66544f819d", 4, "_scratch/cache/r70", "r70s", "r70", "UNVERIFIED")
NEW = ("6f", "70")

# ---- the two candidate decodes, BOTH stamped on BOTH routes (the `decode_v84_probe_r6d` doctrine:
# ---- the identity battery needs each hypothesis's reading of the other's log side by side) --------
V86_COLS = (("v86_sign", V86.BIT_SIGN), ("v86_nonzero", V86.BIT_NONZERO),
            ("v86_mag", V86.BIT_MAG), ("v86_gate", V86.BIT_GATE),
            ("v86_fingerprint", V86.BIT_FINGERPRINT))
V86B_COLS = (("v86b_sign", V86B.BIT_SIGN), ("v86b_mag", V86B.BIT_MAG),
             ("v86b_nonzero", V86B.BIT_NONZERO), ("v86b_gate", V86B.BIT_GATE),
             ("v86b_fingerprint", V86B.BIT_FINGERPRINT))
D.PASS_1D = list(D.PASS_1D) + [c for c, _ in V86_COLS] + [c for c, _ in V86B_COLS]

# 🛑 the weights MUST differ in exactly the b6/b5 pair, or this whole file is measuring nothing
assert (V86.BIT_SIGN, V86.BIT_GATE, V86.BIT_FINGERPRINT) == \
       (V86B.BIT_SIGN, V86B.BIT_GATE, V86B.BIT_FINGERPRINT) == (0x80, 0x10, 0x08)
assert (V86.BIT_NONZERO, V86.BIT_MAG) == (0x40, 0x20)
assert (V86B.BIT_NONZERO, V86B.BIT_MAG) == (0x20, 0x40)
assert V86.MAG_T == V86B.RELAY_T == 64 and V86.GATE_T == V86B.GATE_T == 2

# the exclusive alphabets, DERIVED EXHAUSTIVELY from the two builders' own `wire_byte4` (every int16
# value of gp-0x6b70 x gate open/shut), never hand-written.  🛑 `status_bits=0`: bits 2:0 are the live
# STEER_SENSOR_STATUS and are preserved by the cave's `andi 0x7`; the discriminator is bits 7:3 ONLY.
_V86_REACH = {V86.wire_byte4(v, g, 0) for v in range(-32768, 32768) for g in (0, 2)}
_V86B_REACH = {V86B.wire_byte4(v, g, 0) for v in range(-32768, 32768) for g in (0, 2)}
V86_ONLY = _V86_REACH - _V86B_REACH
V86B_ONLY = _V86B_REACH - _V86_REACH
SHARED = _V86_REACH & _V86B_REACH
assert V86_ONLY == {0x48, 0x58, 0xC8, 0xD8}, V86_ONLY
assert V86B_ONLY == {0x28, 0x38, 0xA8, 0xB8}, V86B_ONLY
assert SHARED == {0x08, 0x18, 0x68, 0x78, 0xE8, 0xF8}, SHARED

# =====================================================================================================
# tolerant rlog reader -- carried verbatim from decode/extract_r6e.py, plus a per-segment message count
# =====================================================================================================
_ORIG_READ = rlog_parse.read_messages
TRUNCATED = {}
MSG_COUNT = {}


def _read_messages_tolerant(path):
    n = 0
    try:
        for evt in _ORIG_READ(path):
            n += 1
            yield evt
    except Exception as exc:                       # capnp KjException on a torn tail
        TRUNCATED[Path(path).name] = (n, str(exc).splitlines()[0])
        print(f"  ⚠ TRUNCATED rlog {Path(path).name}: {n:,} complete messages read, then "
              f"{str(exc).splitlines()[0]}", flush=True)
    finally:
        MSG_COUNT[Path(path).name] = n


rlog_parse.read_messages = _read_messages_tolerant


def stamp(route):
    """Add both candidate decodes to the route-global npz BEFORE `split()` copies them per segment."""
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    f = ROOT / cdir / f"{stem}.npz"
    z = dict(np.load(f))
    p = z["probe"].astype(int)
    for col, bit in V86_COLS + V86B_COLS:
        z[col] = ((p & bit) != 0).astype(float)
    np.savez_compressed(f, **z)
    print(f"  stamped {len(V86_COLS) + len(V86B_COLS)} candidate-decode columns onto {stem}.npz")


def extract_route(route):
    D.extract(route)
    stamp(route)
    D.split(route)
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    segs = {k: dict(complete_messages=v,
                    truncated=k in TRUNCATED,
                    error=TRUNCATED.get(k, (0, None))[1])
            for k, v in MSG_COUNT.items() if _pref in k}
    (ROOT / cdir / f"{stem}_segments.json").write_text(json.dumps(segs, indent=1))
    return segs


# =====================================================================================================
# 1.  BUILD IDENTITY -- no free parameter anywhere in it
# =====================================================================================================
def identity(route):
    _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz")
    b4 = z["raw14_b4"].astype(int) & 0xFF
    f = b4 & 0xF8
    n = len(b4)
    b7, b6, b5, b4b, b3 = ((f & m) != 0 for m in (0x80, 0x40, 0x20, 0x10, 0x08))
    o = dict(route=route, frames=int(n))
    o["b7_duty"], o["b6_duty"] = float(b7.mean()), float(b6.mean())
    o["b5_duty"], o["b4_duty"] = float(b5.mean()), float(b4b.mean())
    o["b3_duty_FINGERPRINT"] = float(b3.mean())
    o["fingerprint_clear_frames"] = int((~b3).sum())
    # ---- V86's two EXACT laws: b7 => b6 (sign=>nonzero), b5 => b6 (mag=>nonzero) ----
    o["v86_viol_b7_not_b6"] = int((b7 & ~b6).sum())
    o["v86_viol_b5_not_b6"] = int((b5 & ~b6).sum())
    o["v86_violations"] = o["v86_viol_b7_not_b6"] + o["v86_viol_b5_not_b6"]
    # ---- V86B's two EXACT laws: b7 => b5, b6 => b5 ----
    o["v86b_viol_b7_not_b5"] = int((b7 & ~b5).sum())
    o["v86b_viol_b6_not_b5"] = int((b6 & ~b5).sum())
    o["v86b_violations"] = o["v86b_viol_b7_not_b5"] + o["v86b_viol_b6_not_b5"]
    # ---- exclusive-alphabet counts ----
    o["v86_only_frames"] = int(sum(int(v) in V86_ONLY for v in f))
    o["v86b_only_frames"] = int(sum(int(v) in V86B_ONLY for v in f))
    o["outside_both_alphabets"] = int(sum(int(v) not in (_V86_REACH | _V86B_REACH) for v in f))
    # ---- CONTRAST: V85's laws were b6 => b7 and b5 => b4 (its rungs were two nested pairs) ----
    o["v85_viol_b6_not_b7"] = int((b6 & ~b7).sum())
    o["v85_viol_b5_not_b4"] = int((b5 & ~b4b).sum())
    fu, fc = np.unique(f, return_counts=True)
    o["field_alphabet"] = [f"0x{int(v):02X}" for v in fu]
    o["field_hist"] = {f"0x{int(v):02X}": int(c) for v, c in zip(fu, fc)}
    bu, bc = np.unique(b4, return_counts=True)
    o["raw_byte4_hist"] = {f"0x{int(v):02X}": int(c) for v, c in zip(bu, bc)}
    # ---- verdict ----
    if o["fingerprint_clear_frames"]:
        o["verdict"] = "NEITHER -- fingerprint bit3 is CLEAR on some frames"
    elif o["v86_violations"] == 0 and o["v86b_violations"] > 0:
        o["verdict"] = "V86"
    elif o["v86b_violations"] == 0 and o["v86_violations"] > 0:
        o["verdict"] = "V86B"
    elif o["v86_violations"] == 0 and o["v86b_violations"] == 0:
        o["verdict"] = "INDISTINGUISHABLE -- both law sets hold (no exclusive code was ever emitted)"
    else:
        o["verdict"] = "NEITHER -- both law sets are violated"
    return o


def identity_table(routes):
    res = [identity(r) for r in routes]
    w = 30
    hdr = "statistic".ljust(w) + "".join(f"{'route ' + r['route']:>20}" for r in res)
    rows = [("frames", "frames", "{:,}"),
            ("b7 duty  sign", "b7_duty", "{:.5f}"),
            ("b6 duty", "b6_duty", "{:.5f}"),
            ("b5 duty", "b5_duty", "{:.5f}"),
            ("b4 duty  GATE", "b4_duty", "{:.5f}"),
            ("b3 duty  FINGERPRINT", "b3_duty_FINGERPRINT", "{:.5f}"),
            ("fingerprint-clear frames", "fingerprint_clear_frames", "{:,}"),
            ("V86 law viol  b7&!b6", "v86_viol_b7_not_b6", "{:,}"),
            ("V86 law viol  b5&!b6", "v86_viol_b5_not_b6", "{:,}"),
            ("V86 VIOLATIONS (total)", "v86_violations", "{:,}"),
            ("V86B law viol b7&!b5", "v86b_viol_b7_not_b5", "{:,}"),
            ("V86B law viol b6&!b5", "v86b_viol_b6_not_b5", "{:,}"),
            ("V86B VIOLATIONS (total)", "v86b_violations", "{:,}"),
            ("V86-ONLY codes seen", "v86_only_frames", "{:,}"),
            ("V86B-ONLY codes seen", "v86b_only_frames", "{:,}"),
            ("outside BOTH alphabets", "outside_both_alphabets", "{:,}"),
            ("(V85 law viol b6&!b7)", "v85_viol_b6_not_b7", "{:,}"),
            ("(V85 law viol b5&!b4)", "v85_viol_b5_not_b4", "{:,}")]
    lines = [hdr, "-" * len(hdr)]
    for lab, key, fmt in rows:
        lines.append(lab.ljust(w) + "".join(f"{fmt.format(r[key]):>20}" for r in res))
    lines.append("")
    for r in res:
        lines.append(f"route {r['route']} VERDICT: {r['verdict']}")
        lines.append(f"  field hist: " + " ".join(f"{k}:{v}" for k, v in sorted(r["field_hist"].items())))
    lines.append("")
    lines.append(f"V86-ONLY alphabet  {sorted(hex(x) for x in V86_ONLY)}")
    lines.append(f"V86B-ONLY alphabet {sorted(hex(x) for x in V86B_ONLY)}")
    return "\n".join(lines), res


def stamp_verdict(route, verdict):
    """Overwrite the hand-entered `probe_build` label with the MEASURED verdict, everywhere."""
    _pref, _n, cdir, pfx, stem, _lab = D.ROUTES[route]
    C = ROOT / cdir
    for p in [C / f"{stem}.npz"] + sorted(C.glob(f"{pfx}*.npz")):
        d = dict(np.load(p))
        d["probe_build"] = np.array([verdict])
        d["build_identity"] = np.array([verdict])
        d["build_identity_basis"] = np.array(["byte4[7:3] exact-nesting + exclusive-alphabet; "
                                              "parameter-free; see <stem>_identity.json"])
        np.savez_compressed(p, **d)
    print(f"  route {route}: probe_build/build_identity stamped '{verdict}' on "
          f"{1 + len(list(C.glob(f'{pfx}*.npz')))} files")


# =====================================================================================================
# 2.  EXPOSURE + PER-WINDOW SPEED CENSUS -- bins IDENTICAL to score/score_v85_r6e_bands.py
# =====================================================================================================
WIN = 128                       # 1.28 s at 100 Hz -- the corpus's spectral window
VB = [(0.0, 0.5), (0.5, 1.5), (1.5, 2.78), (2.78, 5.0), (5.0, 8.0), (8.0, 11.1),
      (11.1, 16.0), (16.0, 22.2), (22.2, 40.0)]           # m/s, score_v85_r6e_bands.VB verbatim
STRATA = [("creep <10 kph", 0.0, 2.78), ("10-40 kph", 2.78, 11.1),
          ("40-80 kph", 11.1, 22.2), (">80 kph", 22.2, 1e9)]
CIRC = 2.0805                   # m, wheel order 1 = v / CIRC


def _load(route):
    if route in D.ROUTES:
        _pref, _n, cdir, _pfx, stem, _lab = D.ROUTES[route]
    else:                                       # comparison routes already on disk
        cdir, stem = {"6e": ("_scratch/cache/r6e", "r6e"), "6d": ("_scratch/cache/r6d", "r6d"),
                      "67": ("_scratch/cache/r67x", "r67"), "68": ("_scratch/cache/r68x", "r68")}[route]
    return np.load(ROOT / cdir / f"{stem}.npz")


def exposure(route):
    z = _load(route)
    t = z["t"]
    v = np.abs(z["cs_v"])
    lat = z["cc_lat"] > 0.5
    dt = float(np.median(np.diff(t)))
    o = dict(route=route, samples=int(len(t)), duration_s=float(t[-1] - t[0]), dt_s=dt,
             engaged_frac=float(lat.mean()))

    def sec(m):
        return float(m.sum() * dt)

    o["engaged_s"] = sec(lat)
    o["manual_s"] = sec(~lat)
    for tag, sel in (("engaged", lat), ("manual", ~lat), ("all", np.ones(len(t), bool))):
        o[f"{tag}_ge50kph_s"] = sec(sel & (v >= 50 / 3.6))
        o[f"{tag}_ge80kph_s"] = sec(sel & (v >= 80 / 3.6))
        o[f"{tag}_creep_2_9_s"] = sec(sel & (v >= 2.0) & (v < 9.0))
        o[f"{tag}_standstill_lt0p5_s"] = sec(sel & (v < 0.5))
        o[f"{tag}_0p5_2_s"] = sec(sel & (v >= 0.5) & (v < 2.0))
        o[f"{tag}_v_max"] = float(v[sel].max()) if sel.sum() else float("nan")
    # 🛑 REVERSE.  Both parking-lot routes spend ~30 s in R.  `cs_v` is a MAGNITUDE, so reverse creep
    # is indistinguishable from forward creep by speed alone and would silently pollute a MANUAL arm.
    g = z["cs_gear"].astype(int)
    rev = g == 4                                # GEAR.index('reverse') in compare_v75_v76_v80_grind
    o["gear_s"] = {n: sec(g == i) for i, n in enumerate(
        ("unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
         "manumatic")) if (g == i).any()}
    o["reverse_engaged_s"] = sec(rev & lat)
    o["reverse_manual_s"] = sec(rev & ~lat)
    o["manual_creep_2_9_FWD_s"] = sec(~lat & ~rev & (v >= 2.0) & (v < 9.0))
    o["manual_0p5_2_FWD_s"] = sec(~lat & ~rev & (v >= 0.5) & (v < 2.0))
    o["strata_engaged_s"] = {nm: sec(lat & (v >= lo) & (v < hi)) for nm, lo, hi in STRATA}
    o["strata_manual_s"] = {nm: sec(~lat & (v >= lo) & (v < hi)) for nm, lo, hi in STRATA}
    # ---- scoreability, on the corpus's own rule: a stratum with < 5 windows of 1.28 s is not scored
    o["scoreable"] = {nm: dict(engaged_s=o["strata_engaged_s"][nm],
                               windows=int(o["strata_engaged_s"][nm] / (WIN * dt)),
                               scoreable=bool(o["strata_engaged_s"][nm] / (WIN * dt) >= 5))
                      for nm, _, _ in STRATA}
    return o


def speed_census(route):
    """Per-WINDOW census on the 1.28 s grid -- the form `score/score_v85_r6e_bands.py` consumes."""
    z = _load(route)
    v = np.abs(z["cs_v"])
    lat = z["cc_lat"] > 0.5
    nw = len(v) // WIN
    vw = v[:nw * WIN].reshape(nw, WIN).mean(axis=1)
    lw = lat[:nw * WIN].reshape(nw, WIN).mean(axis=1) >= 0.99      # window is engaged THROUGHOUT
    out = dict(route=route, windows=int(nw), win_s=WIN / 100.0,
               engaged_windows=int(lw.sum()), manual_windows=int((~lw).sum()),
               bins=[f"{lo:.2f}-{hi:.2f}" for lo, hi in VB])
    for tag, sel in (("engaged", lw), ("manual", ~lw), ("all", np.ones(nw, bool))):
        c = [int(((vw >= lo) & (vw < hi) & sel).sum()) for lo, hi in VB]
        out[f"{tag}_counts"] = c
        out[f"{tag}_frac"] = [x / max(sel.sum(), 1) for x in c]
    ve = vw[lw]
    out["engaged_order1_hz"] = dict(
        median=float(np.median(ve / CIRC)) if len(ve) else float("nan"),
        p05=float(np.percentile(ve / CIRC, 5)) if len(ve) else float("nan"),
        p95=float(np.percentile(ve / CIRC, 95)) if len(ve) else float("nan"))
    return out


# =====================================================================================================
# 2b. WHAT THE FIELD SAYS ABOUT gp-0x6b70 -- the SAME five physical bins on both builds
# ★ The six SHARED codes mean the same thing on V86 and V86B; the exclusive ones are the mirror image
# of each other.  So the friction compensator's distribution is directly comparable ACROSS the pair.
# =====================================================================================================
PHYS = {  # field code -> (V86 meaning, V86B meaning) -- identical physics, different bit weights
    0x18: ("v == 0", "v == 0"),
    0x58: ("0 < v < 64", None), 0x38: (None, "0 < v < 64"),
    0x78: ("v >= +64", "v >= +64"),
    0xD8: ("-64 <= v <= -1", None), 0xB8: (None, "-64 <= v <= -1"),
    0xF8: ("v <= -65", "v <= -65"),
}
PHYS_BIN = {("V86", 0x18): "zero", ("V86B", 0x18): "zero",
            ("V86", 0x58): "small_pos", ("V86B", 0x38): "small_pos",
            ("V86", 0x78): "big_pos", ("V86B", 0x78): "big_pos",
            ("V86", 0xD8): "small_neg", ("V86B", 0xB8): "small_neg",
            ("V86", 0xF8): "big_neg", ("V86B", 0xF8): "big_neg"}


def friction_distribution(route, build):
    """gp-0x6b70's distribution over the five bins the 5-bit field resolves. NOT an interpretation."""
    z = _load(route)
    f = (z["raw14_b4"].astype(int) & 0xF8)
    lat_rows = z["cc_lat"] > 0.5                       # on the ROW grid, not the raw grid
    p = z["probe"].astype(int) & 0xF8
    n = len(f)
    o = dict(route=route, build=build, frames=int(n), bins={})
    for code, cnt in zip(*np.unique(f, return_counts=True)):
        k = PHYS_BIN.get((build, int(code)))
        o["bins"][k or f"UNMAPPED_0x{int(code):02X}"] = dict(code=f"0x{int(code):02X}",
                                                             n=int(cnt), frac=float(cnt) / n)
    for tag, sel in (("engaged", lat_rows), ("manual", ~lat_rows)):
        sub = p[sel]
        o[tag] = {PHYS_BIN.get((build, int(c)), f"UNMAPPED_0x{int(c):02X}"):
                  float(cnt) / max(len(sub), 1)
                  for c, cnt in zip(*np.unique(sub, return_counts=True))}
        o[f"{tag}_frames"] = int(sel.sum())
    nz = 1.0 - o["bins"].get("zero", {"frac": 0.0})["frac"]
    big = (o["bins"].get("big_pos", {"frac": 0.0})["frac"]
           + o["bins"].get("big_neg", {"frac": 0.0})["frac"])
    o["nonzero_duty"] = nz
    o["mag_ge64_duty"] = big
    o["mag_over_nonzero"] = big / nz if nz else None    # ->1 = PLATEAU/relay-like; <<1 = ramped
    return o


# =====================================================================================================
# 3.  MANOEUVRE BLOCKS -- the operator drove two parking-lot symptom tests
# =====================================================================================================
def manoeuvres(route, min_s=3.0):
    """Label 1 s bins {stopped, creep, slow, drive} x {straight, turning} and merge into blocks."""
    z = _load(route)
    t, v = z["t"], np.abs(z["cs_v"])
    lat = z["cc_lat"] > 0.5
    ang = np.abs(z["ang"])                      # column angle, deg, from 0x14A
    rate = np.abs(z["rate_c"])                  # column rate, deg/s, from 0x14A
    dt = float(np.median(np.diff(t)))
    nb = int((t[-1] - t[0]) / 1.0)
    lab, mid = [], []
    for i in range(nb):
        m = (t >= t[0] + i) & (t < t[0] + i + 1)
        if m.sum() < 10:
            continue
        vv, aa, rr = v[m].mean(), ang[m].mean(), rate[m].mean()
        sp = ("stopped" if vv < 0.5 else "creep" if vv < 2.0 else
              "slow" if vv < 9.0 else "mid" if vv < 13.9 else "fast")
        tn = "turning" if (aa > 20.0 or rr > 25.0) else "straight"
        lab.append(f"{sp}/{tn}/{'ENG' if lat[m].mean() > 0.5 else 'man'}")
        mid.append(t[0] + i)
    blocks = []
    for i, L in enumerate(lab):
        if blocks and blocks[-1][2] == L:
            blocks[-1][1] = mid[i] + 1.0
        else:
            blocks.append([mid[i], mid[i] + 1.0, L])
    blocks = [dict(t0=round(a, 1), t1=round(b, 1), dur=round(b - a, 1), label=L)
              for a, b, L in blocks if b - a >= min_s]
    # creep-band engaged/manual split, the separately-requested measurement
    creep = (v >= 2.0) & (v < 9.0)
    o = dict(route=route, blocks=blocks,
             creep_2_9_engaged_s=float((creep & lat).sum() * dt),
             creep_2_9_manual_s=float((creep & ~lat).sum() * dt),
             creep_0p5_2_engaged_s=float(((v >= 0.5) & (v < 2.0) & lat).sum() * dt),
             creep_0p5_2_manual_s=float(((v >= 0.5) & (v < 2.0) & ~lat).sum() * dt),
             stopped_engaged_s=float(((v < 0.5) & lat).sum() * dt),
             stopped_manual_s=float(((v < 0.5) & ~lat).sum() * dt))
    return o


# =====================================================================================================
def run_report(routes):
    txt, res = identity_table(routes)
    print("\n" + "=" * 100 + "\nBUILD IDENTITY\n" + "=" * 100)
    print(txt)
    for r in res:
        cdir = D.ROUTES[r["route"]][2]
        (ROOT / cdir / f"{D.ROUTES[r['route']][4]}_identity.json").write_text(json.dumps(r, indent=1))
        if r["verdict"] in ("V86", "V86B"):
            stamp_verdict(r["route"], r["verdict"])
    verdicts = {r["route"]: r["verdict"] for r in res}
    for route in routes:
        cdir, stem = D.ROUTES[route][2], D.ROUTES[route][4]
        h, e, c, m = D.health(route), exposure(route), speed_census(route), manoeuvres(route)
        fd = friction_distribution(route, verdicts[route])
        print(f"\nROUTE {route}  gp-0x6b70 DISTRIBUTION ({verdicts[route]})\n{json.dumps(fd, indent=1)}")
        for nm, obj in (("health", h), ("exposure", e), ("speed_census", c), ("manoeuvres", m),
                        ("friction_dist", fd)):
            (ROOT / cdir / f"{stem}_{nm}.json").write_text(json.dumps(obj, indent=1))
        print("\n" + "=" * 100 + f"\nROUTE {route}  HEALTH\n" + "=" * 100)
        print(json.dumps({k: v for k, v in h.items() if k != "b0_1ab_hist"}, indent=1))
        print(f"0x1AB byte0 hist: {h['b0_1ab_hist']}")
        print(f"\nROUTE {route}  EXPOSURE\n{json.dumps(e, indent=1)}")
        print(f"\nROUTE {route}  SPEED CENSUS\n{json.dumps(c, indent=1)}")
        print(f"\nROUTE {route}  CREEP SPLIT\n" + json.dumps(
            {k: v for k, v in m.items() if k != "blocks"}, indent=1))
        print(f"\nROUTE {route}  MANOEUVRE BLOCKS (>= 3 s)")
        for b in m["blocks"]:
            print(f"   {b['t0']:7.1f} .. {b['t1']:7.1f}  ({b['dur']:5.1f}s)  {b['label']}")
    # comparison-route census on the SAME bins, so a downstream agent can speed-match
    comp = {}
    for r in ("6e", "6d", "67"):
        try:
            comp[r] = dict(exposure=exposure(r), speed_census=speed_census(r))
        except Exception as exc:
            comp[r] = {"error": str(exc)}
    (ROOT / "_scratch/cache/r6f" / "comparison_routes_census.json").write_text(json.dumps(comp, indent=1))
    print("\n" + "=" * 100 + "\nCOMPARISON ROUTES (same bins) -> _scratch/cache/r6f/comparison_routes_census.json")
    for r, d in comp.items():
        if "error" in d:
            print(f"  {r}: {d['error']}")
            continue
        ex = d["exposure"]
        print(f"  {r}: engaged {ex['engaged_s']:7.1f}s  >=50kph {ex['engaged_ge50kph_s']:6.1f}s  "
              f">=80kph {ex['engaged_ge80kph_s']:6.1f}s  creep2-9 {ex['engaged_creep_2_9_s']:6.1f}s")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    args = [a for a in sys.argv[2:] if a in NEW] or list(NEW)
    if cmd in ("all", "extract"):
        for r in args:
            print(f"\n=== extracting route {r} -> {D.ROUTES[r][2]}", flush=True)
            extract_route(r)
        if TRUNCATED:
            print("\n🛑 TRUNCATED SEGMENTS (declare these in any census):")
            for k, (n, why) in TRUNCATED.items():
                print(f"   {k}: {n:,} messages then {why}")
        else:
            print("\n✓ no truncated segments on either route")
    if cmd in ("all", "report", "identity"):
        run_report(args)
