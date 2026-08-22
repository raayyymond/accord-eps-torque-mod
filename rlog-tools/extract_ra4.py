#!/usr/bin/env python3
r"""Extract route `a4` (**V104**) into `analysis-2020accord/_cache_ra4/`.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly the `extract_r9e.py` pattern: add a row to
`decode_v84_probe_r6d.ROUTES`, then call `extract_r7d.extract_route()` -- the SAME code that wrote
every cache since `_cache_r6d/`.

===================================================================================================
ROUTE a4 == V104.  V103 BASE + `c4` x1.85 + Lever B restored + 427 repointed to `gp-0x6b86`.
===================================================================================================
Byte diff V103 -> V104, re-verified from the two plain images THIS SESSION (16 B in 7 runs):
    0x03AA96  c5 -> fb        Lever B: `ld.bu` displacement, r24 arm gates on gp-0x6806
    0x055DF2  b4 -> 7a        CAN 427 source  gp-0x6b4c -> **gp-0x6b86**
    0x055E10  a6 -> a4        CAN 427 shift   sar 6 -> **sar 4**
    0x0C4FFC  CRC trailer (main app block)
    0x0C60B4  3a3b51 -> fc89c1   `c4` 0.81731 -> 1.51202  (x1.8500000)
    0x0C6446  0002 -> 7c14      Lever B dose 512 -> 5244
    0x0C6FFC  CRC trailer (cal block)
✅ **THE CAVE REGION [0xC4A00, 0xC4FFB] IS BYTE-IDENTICAL: 0 differing bytes.** [EVIDENCE]

===================================================================================================
🛑🛑 THE TRAP THIS CACHE MUST NOT WALK INTO -- THERE IS NO SIGN BIT FOR THE NEW 427 CELL
===================================================================================================
V104 moved the 427 SOURCE but left the CAVE byte-identical.  So `0x14A` byte4 **b7 is still the
sign of `gp-0x6b4c`** -- the OLD cell -- while 427 now carries `|gp-0x6b86|`.

⇒ **`sgn427` DOES NOT BELONG TO THE 427 MAGNITUDE ON THIS ROUTE.**  Applying it would multiply the
biquad output by the LKAS command lane's sign: a random +-1 at ~4 sign flips/s, which destroys any
directed cross-spectrum and manufactures broadband noise.
⇒ This cache therefore emits **`x6b86_mag` -- UNSIGNED COUNTS, RECTIFIED** -- and emits the sign bit
   only under its true name `sgn_6b4c`.  **NO `x6b86` (signed) key exists.  Do not create one.**
   Rectification is recoverable ONLY for band statistics; a directed cross-spectrum against `tq` or
   `rate_f` is NOT available on this route.  [see `accord-427-source-cell-changes-by-build`]

🛑 **NO `x6b94` AND NO `x6b4c` KEY IS WRITTEN.**  Every previous extractor wrote both regardless of
   which cell was on the wire, which is the alias defect audited into
   `accord-427-alias-x6b94-is-the-lane-on-three-routes`.  `check_427_alias.py` is extended for
   `ra4` in the same commit so the guard knows this route by name.

🛑 **`damp_nz` / `g6ac2` ARE STALE DECODES ON V100+ ROUTES** and are DELETED from this cache after
   the shared extractor emits them, rather than left to look plausible.

🛑 **`raw14` OFF-BY-ONE: REPRODUCED, NOT FIXED -- deliberately.**  `t == raw14_t[1:]` and
   `probe == raw14_b4[1:]` in all 13 existing caches.  Diverging here would silently break every
   downstream script that assumes the convention, and the machinery already ships the correct
   index map as `row2raw14`.  **SAFE PAIRS ON `ra4`, unchanged: `(t, probe)` or
   `(raw14_t, raw14_b4)`.  NEVER `(t, raw14_b4)`.**  The `row2raw14` report is printed and the
   lead is asserted to match the other caches.

===================================================================================================
THE CAVE BIT MAP -- V103's, verbatim, because the cave is byte-identical
===================================================================================================
    byte4 b7 0x80 = gp-0x6b4c < 0                 *** NOT the sign of the 427 cell on V104 ***
    byte4 b6 0x40 = |gp-0x6ada| >= |gp-0x6adc|    COMPARATOR: r24 vs r26
    byte4 b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|    COMPARATOR: friction vs inertia
    byte4 b4 0x10 = gp-0x6ada < 0                 sign of r24
    byte4 b3 0x08 = gp-0x3680 < 0                 D_state (PID D-term) SIGN
    byte7[7:6]    = 3                             SAME CODE as V101/V102/V103

    427 (0x1AB) = clamp(|gp-0x6b86| * 5 >> 4, 0, 0x3FF)   => counts = wire * 16/5 = **3.2**

🛑 **IDENTITY.  THE CAVE CANNOT DISTINGUISH V104 FROM V103 -- IT IS THE SAME 164 BYTES.**
   V103's own rule (byte7[7:6]==3 AND b3 varies) separates V103/V104 from V101/V102 but NOT from
   each other.  **The only categorical V104 witness is the 427 CHANNEL:**
     * V103's packer is `|gp-0x6b4c| * 5 >> 6` and `gp-0x6b4c`'s own writer clamps at +-10240,
       so V103's MAXIMUM REACHABLE wire code is (10240*5)>>6 = **800**.  Observed max on `0x9e`
       was **117**.
     * V104's packer is `|gp-0x6b86| * 5 >> 4`; the field saturates at 1023 for |cell| >= 3273.6,
       and |gp-0x6b86| ~ 1.85 x |gp-0x6b82| whose observed max on `0x9e` was 1996 -> ~3693.
   ⇒ **ANY frame with wire code >= 801 is STRUCTURALLY IMPOSSIBLE on V103/V102 and is a
     single-frame V104 witness.**  Reported as `n_above_v103_ceiling`.
   ⚠ If it is ZERO the route is NOT thereby refuted -- it just means the lane never went loud
     enough -- so a second, softer leg is reported too: the wire-code DISTRIBUTION.

Usage:
    python extract_ra4.py                 # full pipeline
    python extract_ra4.py extract
    python extract_ra4.py derive
    python extract_ra4.py identity
    python extract_ra4.py lane427
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402
import rlog_parse        # noqa: E402

D = X.D

NEW = {
    "a4": ("75604b0a432fdc89_000000a4--bdd0c0aa4e", 16,
           "analysis-2020accord/_cache_ra4", "ra4s", "ra4", "V104"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v

# ---- V104 427 spec: NEW source (gp-0x6b86, the biquad output) and NEW shift (sar 4).
X.WIRE_SCALE["a4"] = 16.0 / 5.0                       # 3.2 counts per wire LSB
X.WIRE_SOURCE["a4"] = ("gp-0x6b86 (BIQUAD OUTPUT -- THE DOSED LANE), sar 4  "
                       "[V104 repoint; this cell has NEVER been on the wire before]")

M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES["a4"] = {
    "b7_sign_6b4c_neg__NOT_THE_427_CELL": M_B7,
    "b6_CMP_absr24_ge_absr26": M_B6,
    "b5_CMP_absfriction_ge_absinertia": M_B5,
    "b4_sign_r24_neg": M_B4,
    "b3_sign_Dstate_neg": M_B3,
}

IDENT_MASK = 0xC0
COUNTS_PER_LSB = 16.0 / 5.0            # sar 4
WIRE_SAT_FIELD = 1023                  # the 10-bit CAN field
V103_MAX_REACHABLE_WIRE = 800          # (10240*5)>>6 -- V103/V102's structural ceiling
SAT_CELL_COUNTS = WIRE_SAT_FIELD * COUNTS_PER_LSB      # 3273.6 counts of gp-0x6b86

DERIVED = ["v104_b7", "v104_b6", "v104_b5", "v104_b4", "v104_b3",
           "mag427", "sgn_6b4c", "x6b86_mag", "v_rear", "lp_yaw"]
# 🛑 keys deliberately ABSENT: x6b94, x6b4c (wrong cell), sgn427 (wrong cell's sign),
#    damp_nz / g6ac2 (stale decodes on V100+).

_TAPPED_READ = rlog_parse.read_messages
MISSING_SEGMENTS = []
LP = {"t": [], "z": []}


def _read_guarded(path):
    p = Path(path)
    if not p.exists():
        MISSING_SEGMENTS.append(p.name)
        print("  segment file ABSENT, skipped: %s" % p.name, flush=True)
        return
    for evt in _TAPPED_READ(path):
        try:
            if evt.which() == "livePose":
                LP["t"].append(evt.logMonoTime * 1e-9)
                LP["z"].append(float(evt.livePose.angularVelocityDevice.z))
        except Exception:
            pass
        yield evt


rlog_parse.read_messages = _read_guarded


def extract_route(route="a4"):
    MISSING_SEGMENTS.clear()
    LP["t"].clear()
    LP["z"].clear()
    rep = X.extract_route(route)
    rep["segments_absent"] = list(MISSING_SEGMENTS)
    rep["livePose_samples"] = len(LP["t"])
    print("\n  segments absent from disk: %d   livePose samples: %d"
          % (len(MISSING_SEGMENTS), len(LP["t"])))
    cdir = ROOT / D.ROUTES[route][2]
    np.savez_compressed(cdir / (D.ROUTES[route][4] + "_lp.npz"),
                        t=np.array(LP["t"], float), z=np.array(LP["z"], float))
    return rep


def derive(route="a4"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / (stem + ".npz")
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the pairing contract is broken"
    for nm, m in (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3)):
        z["v104_" + nm] = ((p & m) != 0).astype(float)

    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    z["mag427"] = mag
    # 🛑 b7 is gp-0x6b4c's sign, NOT gp-0x6b86's.  Named for what it is; never applied to mag427.
    z["sgn_6b4c"] = np.where(z["v104_b7"] > 0.5, -1.0, 1.0)
    z["x6b86_mag"] = mag * COUNTS_PER_LSB          # UNSIGNED counts of |gp-0x6b86|

    for dead in ("x6b94", "x6b4c", "sgn427", "damp_nz", "g6ac2"):
        if dead in z:
            del z[dead]
            print("  removed stale/mislabelled key: %s" % dead)

    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    z["v_rear"] = 0.5 * (rl + rr)

    lpf = ROOT / cdir / (stem + "_lp.npz")
    z["lp_yaw"] = np.full(n, np.nan)
    if lpf.exists():
        L = np.load(lpf)
        lt, lz = np.asarray(L["t"], float), np.asarray(L["z"], float)
        if len(lt) > 1:
            t0 = float(z["t0_mono"][0])
            rel = lt - t0
            o = np.argsort(rel)
            z["lp_yaw"] = np.interp(t, rel[o], lz[o])

    np.savez_compressed(f, **z)
    for k in DERIVED:
        if k not in D.PASS_1D:
            D.PASS_1D.append(k)
    for dead in ("x6b94", "x6b4c", "sgn427", "damp_nz", "g6ac2"):
        while dead in D.PASS_1D:
            D.PASS_1D.remove(dead)
    D.split(route)

    print("\n  === DERIVED COLUMNS, route %s (%s) ===" % (route, lab))
    print("    v104_b7..b3 decoded from `probe` (%d rows, SAFE pairing with `t`)" % n)
    print("    mag427  nonzero %.2f %%  distinct %d  max %.0f   sat@1023 %.4f %%  "
          "ABOVE V103 CEILING (>=801) %.4f %%"
          % (100 * np.mean(mag > 0), len(np.unique(mag)), mag.max(),
             100 * np.mean(mag >= WIRE_SAT_FIELD),
             100 * np.mean(mag > V103_MAX_REACHABLE_WIRE)))
    print("    x6b86_mag (UNSIGNED counts)  p50 %.1f  p95 %.1f  p99 %.1f  max %.1f"
          % (np.percentile(z["x6b86_mag"], 50), np.percentile(z["x6b86_mag"], 95),
             np.percentile(z["x6b86_mag"], 99), z["x6b86_mag"].max()))
    print("    v_rear  median %.2f km/h   lp_yaw finite %.1f %%"
          % (np.nanmedian(z["v_rear"]), 100 * np.mean(np.isfinite(z["lp_yaw"]))))
    return z


def identity(route="a4"):
    """V104 witness.  The cave is V103's byte-for-byte, so the CAVE cannot separate them.
    LEG 1 (inherited, separates V104/V103 from V101/V102): byte7[7:6]==3 AND b3 VARIES.
    LEG 2 (the only V104-specific one): a 427 wire code > 800 is structurally impossible on
           V103/V102, whose packer ceiling is (10240*5)>>6 = 800.
    """
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)
    bits = {k: ((b4 & m) != 0) for k, m in
            (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3))}
    duty3 = float((code == 3).mean())
    live = {k: float(bits[k].mean()) for k in bits}
    b3_varies = bool(0.0005 < live["b3"] < 0.9995)
    nlive = sum(1 for k in ("b6", "b5", "b4") if 0.001 < live[k] < 0.999)

    mt = np.asarray(z["ab_mt"], int)
    n_above = int((mt > V103_MAX_REACHABLE_WIRE).sum())
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code3_duty=duty3, b3_duty=live["b3"], b3_varies=b3_varies,
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               bit_duties=live, n_nonconstant_of_b6b5b4=int(nlive),
               wire_n_frames=int(len(mt)), wire_max=int(mt.max()),
               wire_p50=float(np.percentile(mt, 50)), wire_p99=float(np.percentile(mt, 99)),
               n_above_v103_ceiling=n_above,
               frac_above_v103_ceiling=float(n_above / len(mt)) if len(mt) else float("nan"),
               leg1_pass=bool(duty3 >= 0.9999 and b3_varies and nlive >= 1),
               leg2_pass=bool(n_above > 0),
               rule=("LEG1 byte7[7:6]==3 AND b3 varies (V103/V104 vs V101/V102);  "
                     "LEG2 any 427 wire code > 800 is impossible on V103/V102 (V104-specific).  "
                     "LEG2 failing is NOT a refutation -- it only means the lane never went loud."))
    out["identity_pass"] = bool(out["leg1_pass"])
    print("\n  === IDENTITY, route %s (expected %s): %d 0x14A frames ===" % (route, lab, n))
    print("    byte7[7:6] code histogram: " +
          "  ".join("%d:%d" % (int(v), int(c)) for v, c in zip(cu, cc)))
    print("    byte7[7:6]==3 duty %.6f   b3 duty %.6f  VARIES=%s" %
          (duty3, live["b3"], b3_varies))
    print("    byte4 field hist: " + "  ".join("%d:%d" % (int(v), int(c))
                                               for v, c in zip(fu, fc)))
    print("    bit duties: " + "  ".join("%s=%.4f" % (k, v)
                                         for k, v in sorted(live.items(), reverse=True)))
    print("    LEG 1 (V103/V104 vs V101/V102): %s" % ("PASS" if out["leg1_pass"] else "FAIL"))
    print("    LEG 2 (V104-SPECIFIC, 427 wire > 800): %d of %d frames (%.4f %%)  =>  %s"
          % (n_above, len(mt), 100 * out["frac_above_v103_ceiling"],
             "PASS -- structurally impossible on V103" if out["leg2_pass"]
             else "no evidence (lane never went loud enough); NOT a refutation"))
    print("    427 wire: p50 %.0f  p99 %.0f  max %d   (V103's observed max on 0x9e was 117)"
          % (out["wire_p50"], out["wire_p99"], out["wire_max"]))
    (ROOT / cdir / (stem + "_identity.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


def lane427(route="a4"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    mt = np.asarray(z["ab_mt"], int)
    n = len(mt)
    out = dict(route=route, build=lab, frames=int(n), source=X.WIRE_SOURCE[route],
               counts_per_lsb=COUNTS_PER_LSB, rectified=True, sign_bit_available=False,
               nonzero_frac=float(np.mean(mt > 0)), distinct=int(len(np.unique(mt))),
               p50=float(np.percentile(mt, 50)), p90=float(np.percentile(mt, 90)),
               p99=float(np.percentile(mt, 99)), max=int(mt.max()),
               sat_field_1023_frac=float(np.mean(mt >= WIRE_SAT_FIELD)),
               cell_counts_at_saturation=SAT_CELL_COUNTS)
    print("\n  === CAN 427 LANE, route %s (%s) ===" % (route, lab))
    print("    source: %s" % out["source"])
    print("    🛑 RECTIFIED AND UNSIGNED on this route -- byte4 b7 is gp-0x6b4c's sign, not this")
    print("       cell's.  Band statistics only; NO directed cross-spectrum is available.")
    print("    %d frames  nonzero %.2f %%  distinct %d  p50 %.0f  p90 %.0f  p99 %.0f  max %d"
          % (n, 100 * out["nonzero_frac"], out["distinct"], out["p50"], out["p90"],
             out["p99"], out["max"]))
    print("    sat@1023 %.4f %%   (field saturates at |gp-0x6b86| >= %.1f counts)"
          % (100 * out["sat_field_1023_frac"], SAT_CELL_COUNTS))
    (ROOT / cdir / (stem + "_lane427.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    fns = {"extract": extract_route, "derive": derive, "identity": identity,
           "lane427": lane427, "health": X.health, "census": X.census}
    if not args:
        extract_route("a4")
        derive("a4")
        identity("a4")
        lane427("a4")
        X.health("a4")
        X.census("a4")
    else:
        for r in (args[1:] or ["a4"]):
            fns[args[0]](r)
