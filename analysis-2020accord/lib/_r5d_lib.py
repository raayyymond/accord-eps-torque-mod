#!/usr/bin/env python3
"""Route `5d` (**V74**) additions to the grind harness. Import this; do not re-implement.

Everything numeric is `_grind2_lib` + `_r47_lib` + `_r4f_lib` + `_r50_lib` + `_r58_lib` +
`_r59_lib` + `_r5a_lib` unchanged, so a ratio computed on route 5d is computed with the IDENTICAL
instrument as every prior route. This file adds the build entry, the probe channels, and nothing
else. Cache written by `extract/extract_r5d_cache.py`; exposure census in `_scratch/out/_r5d_extract_summary.json`.

★★★★ THE NEW CHANNEL IS A POSITIVE CONTROL, WHICH THIS KIT HAS NOT HAD. `damp` is CAN 0x14A byte4
bit7 = `(gp-0x6BD0 != 0)`, the base-assist damper's OWN OUTPUT. Route-wide it fires on **23.34%** of
frames (0.0% on the two parked segments, 67.4% on engaged creep, 0.29% on manual creep). Every
previous "the lever did nothing" on this kit was ambiguous between *the lever is wrong* and *the
lever was never in force*; on this route that ambiguity is resolved per frame.

★★ `state` is CAN 0x14A byte4 bits 6:3 = `(gp-0x67FA) & 0xF`, the assist-chain fault state.
Measured on this route: **5 on 101,101 of 101,102 frames, 4 on one frame.** It is effectively a
CONSTANT, so it is NOT a usable covariate here -- do not build an arm out of it. Its job on this
route was liveness (0 is structurally unreachable ⇒ the cave fired), and it did that job.

🛑 ENGAGEMENT IS A LEVER CONTRAST ON THIS ROUTE, WHICH IT WAS NOT ON 59/5a.
V74 writes the ENGAGED COLUMN of all 16 config rows -- mode 26 on this car -- and leaves the
disengaged column (mode 24) byte-stock. The mode selector toggles with LKAS engagement. ⇒ unlike
V72/V73, where the manual arm carried the full (ungated) rate-lane dose and an engaged/manual split
was PURELY an engagement test, here the manual arm is a genuine **byte-stock control for LEVERS E'
and D'**.
⚠ Two things that must ride with every such contrast:
  1. The rate lane is UNCHANGED from V72/V73 and is still **UNGATED** (`0x3AA96` = 0xC5, the dead
     `gp-0x683c` cell), so the r24/r26 dose is present in BOTH arms. An engaged/manual ratio on
     route 5d is (LEVER E'/D' effect x engagement effect), never a rate-lane dose test.
  2. **THE MODE LAGS ENGAGEMENT.** V73 measured 1.0209 s on the rise (sd 4.9 ms) and 2.0798 s on the
     fall (sd 0.8 ms), 18 transitions, zero exceptions. `lever_mask()` applies those lags.
     ⚠ **[BELIEF, not EVIDENCE]** -- the lag was measured on V73, whose probe carried the mode byte.
     V74's probe spends its field on the damper and the state, so **the mode is NOT observable on
     this route** and the lag cannot be re-measured here. The writer (`FUN_00042746`) is byte-stock
     in V74, which is why the lag is expected to carry; that is an argument, not a measurement.

🛑 `d["mode"]` AND `d["m_63fd"]` ARE NaN IN THIS CACHE, ON PURPOSE. `_r5a_lib._add_mode` reads
`d["mode"]` by name; V74's probe does not carry the mode, and a number there would label every
window with `gp-0x67FA`'s state. NaN fails loudly.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r4f_lib as R4F  # noqa: E402  -- owns `fs_lattice`
import _r50_lib as R50  # noqa: E402
import _r5a_lib as R5A  # noqa: E402  -- registers V73/r5a and, transitively, everything before it

PKL = ROOT / "_scratch/data/_cache_r5d_records.pkl"

fs_lattice = R4F.fs_lattice
install_fs = R4F.install_fs
USE_LATTICE_FS = R4F.USE_LATTICE_FS

# ------------------------------------------------------------------ the build entry --------------
# `kd` is a LABEL only, and on this car a historical one: V74 carries V72's rate-lane surface
# byte-identically, and BUILD-LINEAGE RULE 7 records that the mode-indexed r24 dose of V69/V70/V72/
# V73 was INERT BY TABLE SELECTION on a mode-24/26 car. Kept at V72/V73's value so the label is
# comparable across the three routes, NOT because 2.44x was ever delivered.
G.BUILDS["V74/r5d"] = dict(cache=ROOT / "_scratch/cache/r5d", pfx="r5ds", segs=list(range(17)), kd=2.44)

ORDER_5D = R5A.ORDER_5A + ["V74/r5d"]

POOL_KD2 = R5A.POOL_KD2
POOL_KD1 = R5A.POOL_KD1
POOL_GATED = R5A.POOL_GATED
POOL_V72, POOL_V73 = R5A.POOL_V72, R5A.POOL_V73
POOL_V74 = ["V74/r5d"]

V74_MANUAL_IS_STOCK_RATE_LANE = False   # UNGATED, same as V72/V73 -- see the docstring
V74_MANUAL_IS_STOCK_DAMPER = True       # ★ mode 24 is byte-stock ⇒ LEVERS E'/D' are engaged-only
V74_R24_DOSE, V74_R26_DOSE = R5A.V73_R24_DOSE, R5A.V73_R26_DOSE   # byte-identical to V72/V73

# V73's measured mode-selector lags, in seconds. See the docstring -- [BELIEF] on this route.
MODE_LAG_RISE_S = 1.0209
MODE_LAG_FALL_S = 2.0798

KMH = 1.0 / 3.6
VBINS = R50.VBINS_V70
VBIN_NAMES = R50.VBIN_NAMES
vbin = R50.vbin

CIRC_LO, CIRC_HI, CIRC = R4F.CIRC_LO, R4F.CIRC_HI, R4F.CIRC
wheel_order, engine_order = R4F.wheel_order, R4F.engine_order

# ⚠ Route 5d segments 2, 3 and 9 are effectively PARKED (vEgo <= 2.2 m/s, latActive 0%, gear park
# for most of the span) and 0 and 9 carry no engagement at all. `driving()` cuts them; the census in
# `_scratch/out/_r5d_extract_summary.json` reports every segment separately.
PARKED = dict(R5A.PARKED)


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V74/r5d, with the probe per window."""
    install_fs()
    order = order or ORDER_5D
    stamp = ("lattice" if USE_LATTICE_FS else "legacy")
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            store = pickle.load(fh)
        if store.get("__fs__") == stamp and all(b in store for b in order):
            return {k: v for k, v in store.items() if not k.startswith("__")}
    store = {"__fs__": stamp}
    for b in order:
        rs = G.wrecs(b)
        store[b] = R47.augment(rs)
        R4F._add_rpm(b, store[b])
        for r in store[b]:
            r["vb"] = vbin(r["v"])
        R5A._add_mode(b, store[b])          # NaN on route 5d, by construction -- see the docstring
        _add_probe(b, store[b])
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return {k: v for k, v in store.items() if not k.startswith("__")}


def _add_probe(build, recs):
    """Per-window damper duty, and the modal assist-chain state with its purity.

    `damp` is a DUTY (a fraction of the window), not a magnitude: bit7 is `!= 0`, so it says the
    damper produced SOMETHING, never how much. 🛑 Do not read a duty as a dose.
    `state` is CATEGORICAL -- modal value plus purity, so an impure window can be dropped rather
    than silently mislabelled. On this route it is ~constant 5 and carries no contrast.
    """
    B = G.BUILDS[build]
    by = {}
    for r in recs:
        by.setdefault(r["seg"], []).append(r)
    for seg, rs in by.items():
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        d = np.load(p) if p.exists() else None
        if d is None or "damp_nz" not in d.files:
            for r in rs:
                r["damp"], r["state"], r["state_pure"] = np.nan, np.nan, np.nan
            continue
        t = np.asarray(d["t"], float)
        dz = np.asarray(d["damp_nz"], float)
        st = np.asarray(d["state"], float)
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            wd, ws = dz[i0:i0 + G.NFFT], st[i0:i0 + G.NFFT]
            if not len(wd):
                r["damp"], r["state"], r["state_pure"] = np.nan, np.nan, np.nan
                continue
            r["damp"] = float(np.nanmean(wd))
            vals, cnt = np.unique(ws, return_counts=True)
            j = int(np.argmax(cnt))
            r["state"] = float(vals[j])
            r["state_pure"] = float(cnt[j] / len(ws))


def lever_mask(lat, t):
    """Where LEVERS E'/D' are in force, i.e. where the mode selector is at 26 -- lat, LAGGED.

    ⚠ [BELIEF] the 1.02 s rise / 2.08 s fall lags are V73's measurement; V74's probe cannot see the
    mode. Frames inside the hysteresis band are returned as a separate mask so they can be DROPPED
    rather than assigned to an arm -- that band is ~3.1 s per engagement edge, i.e. ~28 s over this
    route's 9 episodes, and misassigning it pollutes both arms of the only contrast that matters.

    Returns (in_force, byte_stock, ambiguous), three disjoint boolean masks.
    """
    lat = np.asarray(lat, bool)
    t = np.asarray(t, float)
    on = np.interp(t - MODE_LAG_RISE_S, t, lat.astype(float)) > 0.5     # engaged >= 1.02 s ago
    off = np.interp(t - MODE_LAG_FALL_S, t, lat.astype(float)) > 0.5    # engaged >= 2.08 s ago
    in_force = on & off & lat
    byte_stock = (~on) & (~off) & (~lat)
    return in_force, byte_stock, ~(in_force | byte_stock)


# ------------------------------------------------------------------ the rail channels -------------
RAIL_CHANNELS = {
    "damp": ("CAN 0x14A byte4 bit7 -- ★★★★ (gp-0x6BD0 != 0), THE BASE-ASSIST DAMPER'S OWN OUTPUT. "
             "The positive control. A DUTY, not a magnitude."),
    "state": ("CAN 0x14A byte4 bits 6:3 -- (gp-0x67FA)&0xF, the assist-chain fault state. ~constant "
              "5 on this route; liveness only. 🛑 NOT the bus STEER_STATUS."),
    "e4tq": ("CAN 0x0E4 bytes 0:1, `can` src 129 (the panda's TX echo) -- OPENPILOT'S STEER_TORQUE "
             "REQUEST. TWO limiters act on it, both measured on this route:\n"
             "  · AMPLITUDE: a hard clamp at exactly 4096. Max |e4tq| = 4096, ZERO frames above, "
             "3,853 distinct values with a continuous tail into the wall ⇒ a clamp, not a "
             "distribution edge. 8.06% of engaged frames; 36.9% at creep, 0.000% at 12.5-25 m/s.\n"
             "  · SLEW: a hard cap at exactly 123 counts/frame (= 0.03 x STEER_MAX, the "
             "`0.03*STEER_MAX` term at model/eps_lkas_chain_model.py:2238). ZERO frames exceed it; the "
             "command SITS on it for 8.01% of engaged frames, at EVERY speed (9.8% at >=25 m/s, "
             "where the amplitude rail is 2.3%). ⇒ 0 -> full scale takes >= 0.33 s.\n"
             "🛑 DO NOT read 4096 as 'openpilot self-limiting at 50% of the firmware's range'. The "
             "+-0x2000 figure in the kit's record is `FUN_00042af8`'s SHAPER OUTPUT clamp "
             "(0x43b0e-0x43b20), far downstream and in different units. The INTAKE clamp is "
             "`FUN_00052676` -- `x * -4` then clamp(+-0x4000) -- and 4096 x 4 = 0x4000 EXACTLY. "
             "openpilot's rail is MATCHED to the firmware's intake, with zero headroom; a larger "
             "STEER_MAX would be clipped straight back. See eps_lkas_chain_model.lkas_process_steer_cmd."),
    "sc_tq": ("The SAME quantity read out of the `sendcan` MESSAGE on src 1, i.e. at emission "
              "rather than at TX echo. Median |sc_tq - e4tq| = 0.75 counts, r = 0.9991 -- use "
              "either; the pair exists so a timing question can be answered without a re-extract."),
    "cc_req": "carControl.actuators.torque -- openpilot's NORMALISED request, -1..+1.",
    "co_req": "carOutput.actuatorsOutput.torque -- the APPLIED actuator output, -1..+1.",
    "tq":   ("CAN 0x18F bytes 0:1 x -1 -- STEER_TORQUE_SENSOR, the TORSION BAR. A plant sensor: it "
             "cannot clip at a firmware mixer rail, and it is the kit's standard analysis channel."),
    "sca":  ("CAN 0x18F byte4 bit3 -- STEER_CONTROL_ACTIVE. Agrees with latActive 99.947%."),
    "sstat": ("CAN 0x18F byte4 bits 7:4 -- STEER_STATUS. 🛑 NOT `gp-0x67fa`."),
    "ws_fl/fr/rl/rr": ("RAW CAN 0x1D0 src 1, per-corner wheel speed in m/s. 🛑 "
                       "`carState.wheelSpeeds` is IDENTICALLY ZERO on this fork -- this is the only "
                       "wheel-speed source. Validated against vEgo at 0.009-0.035 m/s median "
                       "absolute error per segment."),
}
NOT_OBSERVABLE = ("gp-0x6b98 (the shaped LKAS command the +-0x2000 mixer rail acts on), gp-0x6c2c "
                  "(the differentiator input), gp-0x6ac0 (motor rate), the four mixer channel "
                  "outputs, and -- new on this route -- gp+0x63FD, THE MODE SELECTOR: V74 spent its "
                  "field on the damper and the state, so the 24/26 toggle is inferred from "
                  "engagement plus V73's lags, never measured here.")

avg_periodogram = R50.avg_periodogram
eng_mask, man_mask, all_mask, hdr = R50.eng_mask, R50.man_mask, R50.all_mask, R50.hdr


def load_seg(seg):
    B = G.BUILDS["V74/r5d"]
    return C.load(seg, B["cache"], B["pfx"])


def load_imu(seg):
    """`{pfx}{seg}_imu.npz` -- the comma's LSM6DS3TR-C on its OWN hardware lattice.

    🛑 NOT the CAN grid. Accel 100.18 Hz / gyro 99.06 Hz measured over this route; `_r47_imu_lib`'s
    alias caveat applies unchanged (Nyquist ~50 Hz, so a 45 Hz line is indistinguishable from ~56).
    """
    return dict(np.load(ROOT / "_scratch/cache/r5d" / f"r5ds{seg}_imu.npz"))


def load_snd(seg):
    return dict(np.load(ROOT / "_scratch/cache/r5d" / f"r5ds{seg}_snd.npz"))
