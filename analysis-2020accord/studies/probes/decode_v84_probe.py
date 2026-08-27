#!/usr/bin/env python3
"""studies/probes/decode_v84_probe.py -- decode V84's `0x14A` byte-4 probe field, and REFUSE anything that is not V84.

🛑 THE REFUSAL IS THE POINT. Every `decode_v7*_probe.py` in this kit has the same exposure: V73's
decoder would happily accept a V73 log as V74, with full confidence, because nothing in the frame
said which build wrote it. V68 fixed that with a hard-coded fingerprint bit and it is why V68 can be
excluded ABSOLUTELY from later logs. V84 carries the same device at `byte4[3]`, and this decoder
**refuses a log in which that bit is ever clear on a decoded frame.**

⚠ AND THE AMBIGUITY THIS CLOSES, STATED EXACTLY. V83a's cave writes the SAME five bits of the SAME
byte, but its `bit3` is `gp-0x6ac2 != 0` -- a VARIABLE, not a constant. So:
  · a V83a frame with `gp-0x6ac2 == 0` has bit3 CLEAR and is refused outright;
  · a V83a frame with `gp-0x6ac2 != 0` has bit3 SET and is individually indistinguishable from V84.
⇒ **the fingerprint is a WHOLE-LOG test, not a per-frame one.** `classify_log()` therefore requires
bit3 set on **every** frame that carries a non-zero field, and reports the duty of each rung so a
V83a log (whose bit7 is `|gp-0x6bd0| != 0`, i.e. the DAMPER, which V84 drives to zero at creep)
stands out. **If you cannot show bit3 set on 100% of frames, do not report V84 numbers.**

THE FIELD -- `0x14A` byte 4, bits 7:3. Bits 2:0 are the live `STEER_SENSOR_STATUS` and are preserved
by the cave's `andi 0x7`.

    bit7  gp-0x6ada >= +1024      delivered r24, POSITIVE excursion
    bit6  gp-0x6ada <= -1025      delivered r24, NEGATIVE excursion
          ⇒ bit7 OR bit6  ==  |r24| >= ~1024, at FULL duty. THE LEVER-B CONFIRMATION.
    bit5  gp-0x67fe in {1,2}      FactorD's LIVENESS GATE.  🛑 if this is ~0, every FactorD number
                                  in the kit is void, and V84's own FactorD reasoning with it.
    bit4  gp-0x6a10 >= 8          FactorD's angle-error axis, 0.1 deg/count ⇒ >= 0.8 deg
    bit3  1                       BUILD FINGERPRINT -- constant

🛑 SAMPLING. The cave runs in the CAN-TX packer at **100 Hz**. That is ~12.8 samples/cycle at
7.79 Hz but it is **UNDER-SAMPLED at 27.75 Hz**, so every number here is a **DUTY CYCLE, never a
peak**, and the ring's row must be read that way.

★ THE MEASUREMENT THIS EXISTS FOR. The manual arm is byte-for-byte stock by construction and the
engaged arm carries Lever B, so **the drive contains its own within-route A/B**: split the `r24_mag`
duty by `latActive` and the predicted step is **0.24 manual -> 0.64 engaged (~2.6x)**. If that step
is absent, Lever B is not in force and no S1 verdict may be drawn from the flight.

★ A FREE STRUCTURAL SELF-CHECK -- `bit4 ⇒ bit5`, reported as a RATE, not a pass/fail.
`FUN_0003fc16`'s `else` branch writes `gp-0x6a10 = 0` EXPLICITLY whenever the gate is shut, so the
axis rung cannot fire while the gate rung is clear -- **except within one task period of a gate
transition**, because the cave samples asynchronously at the 100 Hz CAN tick. So:
  · a RARE violation rate is that race, and is expected;
  · a SYSTEMATIC one means the build or this decoder is wrong, and the log must not be reported.
This costs nothing and converts an unmeasurable race into a measured number. `axis_without_gate`.

🛑 TWO LOCKSTEP SHADOWS ON THE PROBED CELLS -- not a defect here, a warning for the next build.
  · `gp-0x67fe` <-> **`gp-0x4c3a`**  (paired `st.b` at every writer; escalates via `FUN_0006b9fa`
    @`0x3BE68`)
  · `gp-0x6a10` <-> **`gp-0x4c90`**  (`FUN_0003fc16`)
V84's cave only READS both cells and touches neither shadow -- verified from the emitted bytes. But
**anyone who WRITES either cell must write the matched shadow in the same sequence**, or the
lockstep monitor escalates.
⊕ `gp-0x67fe`'s value domain is exactly **{0, 1, 2}** across all five writers (`mov 0x2,r6`
@`0x3BE4C`, `mov 0x1,r15` @`0x3BE58`, three `st.b r0`). So `!= 0` and `in {1,2}` are equivalent on
this image, and a `bit5 == 0` reading **cannot** be explained away as "the cell held 3".

Usage:
    python studies/probes/decode_v84_probe.py <route-dir-or-rlog> [...]
    python studies/probes/decode_v84_probe.py --selftest
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
import sys

# 🛑 the cave's own bit map, imported from the BUILDER so the decoder cannot drift from the image.
# This is the mechanical link `assert_decoder_matches` exists to enforce; V66's decoder header was
# stale for one revision and said bit4 = gp-0x683c when the image read gp-0x67fe.
try:
    from build_v84_tva import (BIT_FD_AXIS, BIT_FD_GATE, BIT_FINGERPRINT, BIT_R24_NEG, BIT_R24_POS,
                               CAVE_HEX, FD_AXIS_THRESH, FD_GATE_HI, FD_GATE_LO, PAYLOAD_KEEP_MASK,
                               R24_COUNTS_NEG, R24_COUNTS_POS, decode_byte4)
except ImportError as exc:                                             # pragma: no cover
    raise SystemExit(f"decode_v84_probe must sit beside builds/v80_v107/build_v84_tva.py: {exc}")

PROBE_ID = 0x14A
PROBE_BYTE = 4
RUNGS = ("r24_pos", "r24_neg", "r24_mag", "fd_gate", "fd_axis")


class NotV84(Exception):
    """Raised when a log cannot be shown to have been produced by V84."""


def decode_frame(byte4):
    """One frame. Returns None when the FINGERPRINT is clear ⇒ the frame is NOT V84."""
    return decode_byte4(byte4)


def classify_log(byte4_stream, latactive=None, min_frames=500):
    """Whole-log decode. 🛑 REFUSES unless the fingerprint holds on EVERY carrying frame.

    `byte4_stream` is an iterable of raw `0x14A` byte-4 values; `latactive` is an optional aligned
    iterable of booleans, which is what turns this from a duty report into the within-route A/B.
    """
    vals = list(byte4_stream)
    if len(vals) < min_frames:
        raise NotV84(f"only {len(vals)} frames -- too few to establish the fingerprint "
                     f"(need >= {min_frames}). Report NOTHING rather than a weak claim.")
    bad = [v for v in vals if not v & BIT_FINGERPRINT]
    if bad:
        raise NotV84(
            f"🛑 {len(bad)} of {len(vals)} frames ({100 * len(bad) / len(vals):.2f}%) have byte4 "
            f"bit3 CLEAR. V84 hard-codes it to 1 on every pass, so this log was NOT produced by "
            f"V84 -- V83a's bit3 is `gp-0x6ac2 != 0`, a variable, and goes clear whenever the "
            f"back-drive index is zero. REFUSING to decode. Do not report V84 numbers from it.")
    out = {"frames": len(vals), "fingerprint_ok": True}
    for r in RUNGS:
        out[r] = sum(1 for v in vals if decode_frame(v)[r]) / len(vals)
    # 🛑 STRUCTURAL SELF-CHECK. FUN_0003fc16 zeroes gp-0x6a10 whenever the gate is shut, so
    # bit4 ⇒ bit5. Violations can only be the 100 Hz sampling race across a gate transition.
    # Reported as a RATE: rare = the race; systematic = the build or this decoder is wrong.
    viol = sum(1 for v in vals if (d := decode_frame(v))["fd_axis"] and not d["fd_gate"])
    out["axis_without_gate"] = viol / len(vals)
    out["axis_without_gate_n"] = viol
    if latactive is not None:
        la = list(latactive)
        if len(la) != len(vals):
            raise NotV84(f"latActive has {len(la)} samples against {len(vals)} frames -- unaligned")
        for tag, want in (("engaged", True), ("manual", False)):
            sel = [v for v, a in zip(vals, la) if bool(a) is want]
            out[f"{tag}_frames"] = len(sel)
            for r in RUNGS:
                out[f"{tag}_{r}"] = (sum(1 for v in sel if decode_frame(v)[r]) / len(sel)
                                     if sel else None)
        if out.get("manual_r24_mag"):
            out["leverB_step"] = out["engaged_r24_mag"] / out["manual_r24_mag"]
    return out


def report(res):
    lines = [f"frames {res['frames']:,} · fingerprint OK on 100% ⇒ this log IS V84", ""]
    lines.append(f"  r24 >= +{R24_COUNTS_POS:<6d} (bit7)   duty {res['r24_pos']:.3f}")
    lines.append(f"  r24 <= -{R24_COUNTS_NEG:<6d} (bit6)   duty {res['r24_neg']:.3f}")
    lines.append(f"  |r24| >= ~{R24_COUNTS_POS:<4d} (b7|b6)  duty {res['r24_mag']:.3f}"
                 "   <-- THE LEVER-B CONFIRMATION")
    lines.append(f"  gp-0x67fe in {{{FD_GATE_LO},{FD_GATE_HI}}} (bit5) duty {res['fd_gate']:.3f}"
                 "   <-- FactorD LIVENESS; if ~0, every FactorD number is VOID")
    lines.append(f"  gp-0x6a10 >= {FD_AXIS_THRESH:<3d}  (bit4)   duty {res['fd_axis']:.3f}"
                 "   <-- the angle-error axis, 0.1 deg/count")
    if "leverB_step" in res:
        lines += ["", f"  WITHIN-ROUTE A/B  manual {res['manual_r24_mag']:.3f} -> engaged "
                      f"{res['engaged_r24_mag']:.3f}  =  {res['leverB_step']:.2f}x",
                  "  (predicted ~0.24 -> ~0.64 = 2.6x. **A step near 1.0x means LEVER B IS NOT IN "
                  "FORCE** and no S1 verdict may be drawn.)"]
    awg = res["axis_without_gate"]
    verdict = ("consistent with the 100 Hz sampling race across gate transitions"
               if awg < 0.005 else
               "🛑 SYSTEMATIC -- bit4 fires with bit5 clear far too often. FUN_0003fc16 zeroes "
               "gp-0x6a10 when the gate is shut, so this cannot happen by design. The build or "
               "this decoder is WRONG. Do not report FactorD numbers from this log.")
    lines += ["", f"  bit4 & !bit5  {awg:.5f}  ({res['axis_without_gate_n']:,} frames)   {verdict}"]
    lines += ["", "  🛑 100 Hz sampling ⇒ these are DUTY CYCLES, never peaks. Under-sampled at "
                  "27.75 Hz."]
    return "\n".join(lines)


def _selftest():
    from build_v84_tva import wire_byte4
    # a V84 log: every frame carries the fingerprint
    good = [wire_byte4(r, 1, 12, status_bits=s) for r in (-2000, -500, 0, 500, 2000) for s in range(8)
            for _ in range(20)]
    res = classify_log(good, min_frames=100)
    assert res["fingerprint_ok"] and res["frames"] == len(good)
    assert abs(res["r24_mag"] - 0.4) < 1e-9, res["r24_mag"]
    assert res["fd_gate"] == 1.0 and res["fd_axis"] == 1.0
    # gate always set in `good` ⇒ the implication can never be violated there
    assert res["axis_without_gate"] == 0.0 and res["axis_without_gate_n"] == 0
    # and a hand-built violation IS counted, so the check is not vacuous
    viol_log = [wire_byte4(0, 0, 12, status_bits=0)] * 100 + [wire_byte4(0, 1, 12)] * 900
    vres = classify_log(viol_log, min_frames=100)
    assert abs(vres["axis_without_gate"] - 0.1) < 1e-9, vres["axis_without_gate"]
    # 🛑 a V83a-shaped log (bit3 variable) MUST be refused
    v83a_like = [0x87] * 500 + [0x8F] * 500
    try:
        classify_log(v83a_like, min_frames=100)
    except NotV84 as e:
        assert "bit3 CLEAR" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a bit3-clear log was NOT refused -- the whole point of this file")
    # a single all-clear frame decodes as None, never as "everything false"
    assert decode_frame(0x00) is None and decode_frame(0x87) is None
    assert decode_frame(BIT_FINGERPRINT) is not None
    # the live status bits are never consulted
    for s in range(8):
        assert decode_frame(BIT_FINGERPRINT | s) == decode_frame(BIT_FINGERPRINT)
    assert PAYLOAD_KEEP_MASK == 0x7
    # too-few-frames is a refusal, not a weak answer
    try:
        classify_log([BIT_FINGERPRINT] * 10)
    except NotV84 as e:
        assert "too few" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("a short log was not refused")
    # the bit map is the BUILDER's, not a copy
    assert (BIT_R24_POS, BIT_R24_NEG, BIT_FD_GATE, BIT_FD_AXIS, BIT_FINGERPRINT) == \
        (0x80, 0x40, 0x20, 0x10, 0x08)
    assert isinstance(CAVE_HEX, str) and len(CAVE_HEX) == 136
    print("decode_v84_probe self-test: PASS")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        _selftest()
    else:                                                              # pragma: no cover
        raise SystemExit("point this at an rlog reader; `classify_log` is the entry point and it "
                         "REFUSES any log whose byte4 bit3 is ever clear.")
