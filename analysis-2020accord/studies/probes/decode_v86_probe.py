#!/usr/bin/env python3
"""studies/probes/decode_v86_probe.py -- decode V86's `0x14A` byte-4 probe field, and REFUSE anything that is not V86.

🛑 THE REFUSAL IS THE POINT. A decoder will happily accept the WRONG build's log with full confidence,
because nothing in the frame says which build wrote it. V68 fixed that with a hard-coded fingerprint
bit; V84 and V85 carried the same device at `byte4[3]`; V86 carries it too **and its two structural
invariants are the DUALS of V85's**, which makes the two builds mutually refutable with no fitted
parameter.

THE FIELD -- `0x14A` byte 4, bits 7:3. Bits 2:0 are the live `STEER_SENSOR_STATUS` and are preserved
by the cave's `andi 0x7`.

    bit7  gp-0x6b70 < 0         SIGN of the Coulomb friction-compensator output
    bit6  gp-0x6b70 != 0        LIVENESS -- the term is producing anything at all
    bit5  |gp-0x6b70| >= 64     MAGNITUDE, TWO-SIDED, trips at +64 / -65
    bit4  gp-0x67ab < 2         ★ THE AGGREGATOR'S OPTIONAL-TERM GATE -- probe the gate, not just
                                  the output. V64/V68 each returned an uninterpretable null because
                                  the gate was never measured and the detector had never armed.
    bit3  1                     BUILD FINGERPRINT -- constant.

★★ TWO STRUCTURAL INVARIANTS, AND THEY ARE **EXACT** -- NOT A RATE, NOT A RACE.
`bit7 => bit6` and `bit5 => bit6`. Both are computed from the **same register in the same pass of the
same cave**, so they admit **ZERO** violations. `classify_log` raises `NotV86` on the first one.

★ WHY V85 CANNOT PRODUCE A V86-SHAPED LOG, AND VICE VERSA -- THE DUAL INVARIANTS.
V85's cave required `b6 => b7` (its b6 was `|rate| >= 512`, nested inside b7's `|rate| >= 64`).
V86 requires `b7 => b6`. These are duals, so:
  · **a single `b6 & !b7` frame is LEGAL on V86 and IMPOSSIBLE on V85** ⇒ it refutes V85;
  · **a single `b7 & !b6` frame is IMPOSSIBLE on V86** ⇒ it refutes V86.
Together with the fingerprint that is **two independent discriminators and no free parameter.**

🛑 WHAT A NULL WOULD AND WOULD NOT MEAN -- READ THIS BEFORE SCORING.
  · `b6` duty ~ 0 ⇒ the friction compensator is producing NOTHING. The lane is idle and **no
    conclusion about V86's control cell may be drawn from the other rungs.**
  · `b4` duty ~ 0 ⇒ the aggregator's optional term is GATED OFF. Same: the lane is not in circuit.
    🛑 **This is the rung V64/V68 did not have.** Both returned nulls that could not be told apart
    from "the lever did nothing", because nobody measured whether the gate had armed.
  · `b5` duty ~ 0 with `b6` high ⇒ the term is live but small -- a real measurement, not a null.

🛑 SAMPLING. The cave runs in the CAN-TX packer at **100 Hz**. That is ~12.8 samples/cycle at 7.79 Hz
but it is **UNDER-SAMPLED at 27.75 Hz**, so every number here is a **DUTY CYCLE, never a peak.**

🛑 WHAT THIS PROBE DOES NOT MEASURE. V86's control cell is a **FREQUENCY** lever (the command-EMA
pole). These four rungs measure the friction compensator's sign, liveness, magnitude and gate -- they
do **not** measure the -180 deg crossing. **The frequency claim is scored from the rlog spectra, not
from this field.** This probe exists to tell you whether the lane was in circuit at all.

Usage:
    python studies/probes/decode_v86_probe.py --selftest
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
import sys

# 🛑 the cave's own bit map, imported from the BUILDER so the decoder cannot drift from the image.
try:
    from build_v86_tva import (BIT_FINGERPRINT, BIT_GATE, BIT_MAG, BIT_NONZERO, BIT_SIGN,
                               CAVE_PAYLOAD, GATE_T, MAG_T, PAYLOAD_KEEP_MASK, RELAY_T,
                               decode_byte4)
except ImportError as exc:                                             # pragma: no cover
    raise SystemExit(f"decode_v86_probe must sit beside builds/v80_v107/build_v86_tva.py: {exc}")

PROBE_ID = 0x14A
PROBE_BYTE = 4
RUNGS = ("sign", "nonzero", "mag", "gate")
CAVE_HEX = CAVE_PAYLOAD.hex()


class NotV86(Exception):
    """Raised when a log cannot be shown to have been produced by V86."""


def decode_frame(byte4):
    """One frame. Returns None when the FINGERPRINT is clear ⇒ the frame is NOT V86."""
    return decode_byte4(byte4)


def classify_log(byte4_stream, latactive=None, min_frames=500):
    """Whole-log decode. 🛑 REFUSES unless the fingerprint AND both nesting invariants hold."""
    vals = list(byte4_stream)
    if len(vals) < min_frames:
        raise NotV86(f"only {len(vals)} frames -- too few to establish the fingerprint "
                     f"(need >= {min_frames}). Report NOTHING rather than a weak claim.")
    bad = [v for v in vals if not v & BIT_FINGERPRINT]
    if bad:
        raise NotV86(
            f"🛑 {len(bad)} of {len(vals)} frames ({100 * len(bad) / len(vals):.2f}%) have byte4 "
            f"bit3 CLEAR. V86 hard-codes it to 1 on every pass, so this log was NOT produced by V86. "
            f"REFUSING to decode.")
    dec = [decode_frame(v) for v in vals]
    for name, hi, lo in (("sign", "sign", "nonzero"), ("magnitude", "mag", "nonzero")):
        viol = sum(1 for d in dec if d[hi] and not d[lo])
        if viol:
            raise NotV86(
                f"🛑 {viol} of {len(vals)} frames have the {name} rung set with the LIVENESS rung "
                f"clear. Both are computed from the SAME register in the SAME cave pass, so this is "
                f"STRUCTURALLY IMPOSSIBLE on V86 -- the log is from another build, or this decoder "
                f"does not match the image. Do not report numbers from it. "
                f"(V85's invariant was the DUAL, `b6 => b7`, and a V85 log lands here.)")
    out = {"frames": len(vals), "fingerprint_ok": True, "nesting_ok": True}
    for r in RUNGS:
        out[r] = sum(1 for d in dec if d[r]) / len(vals)
    # ---- 🛑 THE TWO NULL-INTERPRETING FLAGS. Set ⇒ the lane was not in circuit ⇒ NO conclusion. ----
    # ★ THE SECOND DISCRIMINATOR: gp-0x6b70 is MEMORYLESS, so the band (0, RELAY_T) is populated
    # ONLY if the LERP ramps through small values. ratio -> 1 = PLATEAU (relay-like); << 1 = ramped.
    out["b5_over_b6"] = (out["mag"] / out["nonzero"]) if out["nonzero"] else None
    out["lane_idle"] = out["nonzero"] < 0.01
    out["gate_shut"] = out["gate"] < 0.01
    out["interpretable"] = not (out["lane_idle"] or out["gate_shut"])
    if latactive is not None:
        la = list(latactive)
        if len(la) != len(vals):
            raise NotV86(f"latActive has {len(la)} samples against {len(vals)} frames -- unaligned")
        for tag, want in (("engaged", True), ("manual", False)):
            sel = [d for d, a in zip(dec, la) if bool(a) is want]
            out[f"{tag}_frames"] = len(sel)
            for r in RUNGS:
                out[f"{tag}_{r}"] = (sum(1 for d in sel if d[r]) / len(sel)) if sel else None
    return out


def report(res):
    lines = [f"frames {res['frames']:,} · fingerprint OK on 100% · both nesting invariants HOLD "
             f"⇒ this log IS V86", ""]
    lines.append(f"  gp-0x6b70 <  0      (bit7)  duty {res['sign']:.4f}   SIGN of the friction "
                 "compensator")
    lines.append(f"  gp-0x6b70 != 0      (bit6)  duty {res['nonzero']:.4f}   LIVENESS 🛑 near zero "
                 "⇒ the lane is IDLE and nothing else here means anything")
    lines.append(f"  |gp-0x6b70| >= {MAG_T:<4d} (bit5)  duty {res['mag']:.4f}   MAGNITUDE, two-sided "
                 f"(trips +{MAG_T} / -{MAG_T + 1})")
    lines.append(f"  gp-0x67ab <  {GATE_T:<4d} (bit4)  duty {res['gate']:.4f}   ★ THE AGGREGATOR "
                 "GATE 🛑 near zero ⇒ the term is OUT OF CIRCUIT")
    if res.get("b5_over_b6") is not None:
        r = res["b5_over_b6"]
        lines += ["", f"  ★ SHAPE DISCRIMINATOR  b5/b6 = {r:.3f}   (memoryless term ⇒ the band "
                      f"(0,{RELAY_T}) fills ONLY if the LERP ramps)"]
        lines.append("    🛑 b5/b6 -> 1.00 is a POSITIVE RESULT: a PLATEAU, relay-like -- NOT a "
                     "saturated or wasted rung.")
        lines.append("    🛑 b5/b6 << 1 ⇒ it ramps through small values ⇒ shaped/viscous, which a "
                     "relay CANNOT do.")
    lines += ["", "  🛑 INTERPRETABILITY -- check this BEFORE reading any number above:"]
    lines.append(f"    lane idle (b6 < 1%)  : {res['lane_idle']}")
    lines.append(f"    gate shut (b4 < 1%)  : {res['gate_shut']}")
    lines.append(f"    ⇒ INTERPRETABLE      : {res['interpretable']}")
    if not res["interpretable"]:
        lines.append("    🛑🛑 A NULL HERE IS A NULL ON THE GATE, NOT ON THE HYPOTHESIS. This is the "
                     "V64/V68 failure and it is now DETECTED rather than inferred afterwards.")
    if "engaged_sign" in res:
        lines += ["", "  WITHIN-ROUTE A/B (the control cell is MODE-PROOF ⇒ both arms carry it):"]
        for r in RUNGS:
            m, e = res.get(f"manual_{r}"), res.get(f"engaged_{r}")
            if m is not None and e is not None:
                lines.append(f"    {r:<8s} manual {m:.4f} -> engaged {e:.4f}")
    lines += ["", "  🛑 100 Hz sampling ⇒ these are DUTY CYCLES, never peaks. Under-sampled at "
                  "27.75 Hz.",
              "  🛑 V86's control cell is a FREQUENCY lever. These rungs do NOT measure the -180 deg "
              "crossing;",
              "     the frequency claim is scored from the rlog SPECTRA. This field tells you only "
              "whether the lane was live."]
    return "\n".join(lines)


def _selftest():
    from build_v86_tva import wire_byte4
    good = [wire_byte4(v, g, status_bits=s)
            for v in (-900, -100, -1, 0, 1, 100, 900)
            for g in (0, 1, 2, 3)
            for s in range(8)]
    res = classify_log(good, min_frames=100)
    assert res["fingerprint_ok"] and res["nesting_ok"] and res["frames"] == len(good)
    assert abs(res["sign"] - 3 / 7) < 1e-9, res["sign"]        # -900,-100,-1 of 7
    assert abs(res["nonzero"] - 6 / 7) < 1e-9, res["nonzero"]  # all but 0
    # 🛑 with T = 64 (not 512) the vector -900,-100,100,900 all fire: 4/7, not 2/7.
    assert abs(res["mag"] - 4 / 7) < 1e-9, res["mag"]          # -900, -100, 100, 900
    assert abs(res["gate"] - 2 / 4) < 1e-9, res["gate"]        # g in {0,1} of {0,1,2,3}
    assert res["interpretable"]
    # 🛑 a bit3-clear log MUST be refused
    try:
        classify_log([0x87] * 1000, min_frames=100)
    except NotV86 as e:
        assert "bit3 CLEAR" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a bit3-clear log was NOT refused -- the whole point of this file")
    # 🛑 a V85-SHAPED log must be refused: V85 could emit b7 set with b6 clear (its b7 was the OUTER
    # 🛑 nesting level), which is structurally impossible on V86.
    v85_like = [BIT_FINGERPRINT | BIT_SIGN] * 300 + [BIT_FINGERPRINT] * 700
    try:
        classify_log(v85_like, min_frames=100)
    except NotV86 as e:
        assert "STRUCTURALLY IMPOSSIBLE" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a V85-shaped log was NOT refused")
    # the magnitude nesting is policed too
    mag_bad = [BIT_FINGERPRINT | BIT_MAG] * 200 + [BIT_FINGERPRINT] * 800
    try:
        classify_log(mag_bad, min_frames=100)
    except NotV86 as e:
        assert "magnitude rung" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a magnitude-nesting violation was NOT refused")
    # 🛑 the two null-interpreting flags must actually fire
    idle = [BIT_FINGERPRINT | BIT_GATE] * 1000
    r = classify_log(idle, min_frames=100)
    assert r["lane_idle"] and not r["interpretable"], "the lane-idle detector did not fire"
    shut = [wire_byte4(100, 2)] * 1000
    r = classify_log(shut, min_frames=100)
    assert r["gate_shut"] and not r["interpretable"], "the gate-shut detector did not fire"
    assert "NULL ON THE GATE" in report(r)
    # a single all-clear frame decodes as None, never as "everything false"
    assert decode_frame(0x00) is None and decode_frame(0x87) is None
    assert decode_frame(BIT_FINGERPRINT) is not None
    for s in range(8):
        assert decode_frame(BIT_FINGERPRINT | s) == decode_frame(BIT_FINGERPRINT)
    assert PAYLOAD_KEEP_MASK == 0x7
    try:
        classify_log([BIT_FINGERPRINT] * 10)
    except NotV86 as e:
        assert "too few" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("a short log was not refused")
    # the bit map is the BUILDER's, not a copy
    assert (BIT_SIGN, BIT_NONZERO, BIT_MAG, BIT_GATE, BIT_FINGERPRINT) == \
        (0x80, 0x40, 0x20, 0x10, 0x08)
    assert (MAG_T, GATE_T, RELAY_T) == (64, 2, 64)
    assert isinstance(CAVE_HEX, str) and len(CAVE_HEX) == 136
    assert "this log IS V86" in report(res)
    print("decode_v86_probe self-test: PASS")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        _selftest()
    else:                                                              # pragma: no cover
        raise SystemExit("point this at an rlog reader; `classify_log` is the entry point and it "
                         "REFUSES any log that fails the fingerprint or either nesting invariant.")
