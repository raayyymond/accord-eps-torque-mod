#!/usr/bin/env python3
"""decode_v85_probe.py -- decode V85's `0x14A` byte-4 probe field, and REFUSE anything that is not V85.

🛑 THE REFUSAL IS THE POINT. Every `decode_v7*_probe.py` in this kit has the same exposure: a decoder
will happily accept the WRONG build's log, with full confidence, because nothing in the frame says
which build wrote it. V68 fixed that with a hard-coded fingerprint bit; V84 carried the same device at
`byte4[3]`; V85 carries it too **and adds two structural invariants V84 cannot satisfy.**

THE FIELD -- `0x14A` byte 4, bits 7:3. Bits 2:0 are the live `STEER_SENSOR_STATUS` and are preserved
by the cave's `andi 0x7`. **All four rungs are TWO-SIDED**, symmetric within ONE count.

    bit7  |gp-0x6abc| >= 64    motor RATE. trips at +64 / -65.
                               ★ 64 is above the OLD saturation point (600/12 = 50) ⇒ **bit7 set
                                 IMPLIES V84's friction relay was saturated at that instant.**
    bit6  |gp-0x6abc| >= 512   motor RATE. trips at +512 / -513.
                               ★ 512 is above the NEW saturation point (6000/12 = 500) ⇒ **bit6 set
                                 IMPLIES V85's relay is STILL saturated.** 🛑 HIGH bit6 duty means the
                                 edit under-delivered -- this is what makes a null interpretable.
    bit5  |gp-0x6ae2| >= 8     FRICTION x 1024, HIGH rung. trips at +8 / -9.
    bit4  |gp-0x6ae2| >= 2     FRICTION x 1024, LOW rung.  trips at +2 / -3. The liveness anchor.
    bit3  1                    BUILD FINGERPRINT -- constant.

★★ TWO STRUCTURAL INVARIANTS, AND THEY ARE **EXACT** -- NOT A RATE, NOT A RACE.
`bit6 => bit7` and `bit5 => bit4`. Each pair is computed from the **same register in the same pass of
the same cave**, so unlike V84's `bit4 => bit5` (two different cells sampled a task period apart)
these admit **ZERO** violations. **A single violating frame means the decoder or the image is wrong**
and no numbers may be reported from that log. `classify_log` raises `NotV85` on the first one.

★ WHY V84 CANNOT PRODUCE A V85-SHAPED LOG (three independent tests, no fitted parameter):
  1. **b3.** V85 hard-codes it to 1 on every pass. A log with any bit3-clear carrying frame is refused.
  2. **b7.** V84's observed alphabet on route `6d` was exactly `{0x2F, 0x3F}`: `b7` and `b6` were
     identically **0 across all 68,236 frames** (they read `gp-0x6ada >= +1024` / `<= -1025`, and the
     delivered r24 never got there). V85's `b7` fires at `|motor rate| >= 64` counts = 13.6 deg/s,
     which occurs constantly in motion. **A b7 duty above 1% is impossible for V84.**
  3. **The nesting.** V84's `b7`/`b6` were MUTUALLY EXCLUSIVE (a positive and a negative excursion of
     the same cell); they can never nest. V85's must nest, always. A log satisfying `bit6 => bit7`
     on 100% of frames *and* carrying non-zero bit6 duty cannot be V84.

★ THE MEASUREMENT THIS EXISTS FOR -- `|model|`, the one quantity in this lane never measured usably.
`|gp-0x6ae2| = 102 * |model| * min(|rate|/500, 1)`, so `b4` fires above `|rate| = 9.80/|model|` and
`b5` above `39.2/|model|`, while `b7` fires at 64 and `b6` at 512. Equating them brackets `|model|`:

    b5 duty > b6 duty   ⇒  |model| > 0.077
    b4 duty > b7 duty   ⇒  |model| > 0.153
    b5 duty > b7 duty   ⇒  |model| > 0.613

⚠ `|rate|` and `|model|` are CORRELATED, so this is a **ranking, not a point estimate.** State it that
way. (V55's flown 4-bit probe put `|gp-0x6b98|` inside +-512 on 99.2% of engaged frames ⇒ the command
term of `|model|` is below 0.5 there; the working prior is ~0.2.)

★ PREDICTED DUTIES, recorded BEFORE the drive so they are falsifiable [BELIEF]:
    b4  35-70% on V85   (~85-95% had V84 carried this rung)
    b5  10-25% on V85   (~55-80% had V84 carried this rung)
⇒ **the friction tap should read LOW relative to the rate rungs.** If `b4`/`b5` are as high as the
rate rungs, the edit is not in force -- check `b6` first.

🛑 STALENESS, STATED EXACTLY. `gp-0x6ae2` is written **only on `FUN_0003b8f6`'s success path**, and the
caller's guard (`andi 0x830,r25,r28` @`0x221D6` + `cmp r0,r28` / `be` @`0x2240C`) **skips the whole
function outside states {4, 5, 11}**. In those states `bit5`/`bit4` HOLD their last value while
`bit7`/`bit6` stay live (`gp-0x6abc` has 4 writers, none inside `FUN_0003b8f6`). ⇒ **a friction rung
that is flat for a long run is a state-gate artefact, not a measurement.** `frozen_fric_runs` reports
the longest run over which bits 5:4 do not change while bits 7:6 do, which is the cheap detector.

🛑 SAMPLING. The cave runs in the CAN-TX packer at **100 Hz**. That is ~12.8 samples/cycle at 7.79 Hz
but it is **UNDER-SAMPLED at 27.75 Hz**, so every number here is a **DUTY CYCLE, never a peak.**

Usage:
    python decode_v85_probe.py --selftest
"""
import sys

# 🛑 the cave's own bit map, imported from the BUILDER so the decoder cannot drift from the image.
try:
    from build_v85_tva import (BIT_FINGERPRINT, BIT_FRIC_HI, BIT_FRIC_LO, BIT_RATE_HI, BIT_RATE_LO,
                               CAVE_HEX, FRIC_T_HI, FRIC_T_LO, NEW_SAT, OLD_SAT, PAYLOAD_KEEP_MASK,
                               RATE_COUNTS_PER_DEG_S, RATE_T_HI, RATE_T_LO, decode_byte4)
except ImportError as exc:                                             # pragma: no cover
    raise SystemExit(f"decode_v85_probe must sit beside build_v85_tva.py: {exc}")

PROBE_ID = 0x14A
PROBE_BYTE = 4
RUNGS = ("rate_lo", "rate_hi", "fric_lo", "fric_hi")
# |gp-0x6ae2| = FRIC_SCALE * |model| * min(|rate|/NEW_SAT, 1)   -- cal 0xC40D2, asserted by the builder
FRIC_SCALE = 102


class NotV85(Exception):
    """Raised when a log cannot be shown to have been produced by V85."""


def decode_frame(byte4):
    """One frame. Returns None when the FINGERPRINT is clear ⇒ the frame is NOT V85."""
    return decode_byte4(byte4)


def model_threshold(fric_t, rate_t):
    """The `|model|` at which a friction rung and a rate rung fire at the same `|rate|`."""
    return NEW_SAT * fric_t / float(FRIC_SCALE * rate_t)


def classify_log(byte4_stream, latactive=None, min_frames=500):
    """Whole-log decode. 🛑 REFUSES unless the fingerprint AND both nesting invariants hold.

    `byte4_stream` is an iterable of raw `0x14A` byte-4 values; `latactive` is an optional aligned
    iterable of booleans, which turns this from a duty report into a within-route A/B.
    """
    vals = list(byte4_stream)
    if len(vals) < min_frames:
        raise NotV85(f"only {len(vals)} frames -- too few to establish the fingerprint "
                     f"(need >= {min_frames}). Report NOTHING rather than a weak claim.")
    bad = [v for v in vals if not v & BIT_FINGERPRINT]
    if bad:
        raise NotV85(
            f"🛑 {len(bad)} of {len(vals)} frames ({100 * len(bad) / len(vals):.2f}%) have byte4 "
            f"bit3 CLEAR. V85 hard-codes it to 1 on every pass, so this log was NOT produced by V85. "
            f"REFUSING to decode.")
    dec = [decode_frame(v) for v in vals]
    # 🛑 THE EXACT INVARIANTS. Same register, same pass ⇒ zero violations are permitted.
    for name, hi, lo in (("rate", "rate_hi", "rate_lo"), ("friction", "fric_hi", "fric_lo")):
        viol = sum(1 for d in dec if d[hi] and not d[lo])
        if viol:
            raise NotV85(
                f"🛑 {viol} of {len(vals)} frames have the {name} HIGH rung set with the LOW rung "
                f"clear. Both are computed from the SAME register in the SAME cave pass, so this is "
                f"STRUCTURALLY IMPOSSIBLE on V85 -- the log is from another build, or this decoder "
                f"does not match the image. Do not report numbers from it. "
                f"(V84's b7/b6 were MUTUALLY EXCLUSIVE and would land here.)")
    out = {"frames": len(vals), "fingerprint_ok": True, "nesting_ok": True}
    for r in RUNGS:
        out[r] = sum(1 for d in dec if d[r]) / len(vals)
    # ---- the staleness detector: bits 5:4 frozen while bits 7:6 move ------------------------------
    best = run = 0
    prev = None
    for d in dec:
        key = (d["fric_lo"], d["fric_hi"])
        rate_key = (d["rate_lo"], d["rate_hi"])
        if prev is not None and key == prev[0] and rate_key != prev[1]:
            run += 1
            best = max(best, run)
        else:
            run = 0
        prev = (key, rate_key)
    out["frozen_fric_run"] = best
    out["frozen_fric_s"] = best / 100.0
    # ---- the |model| bracket ----------------------------------------------------------------------
    out["model_gt_lo"] = out["fric_lo"] > out["rate_lo"]           # |model| > 0.153
    out["model_gt_hi"] = out["fric_hi"] > out["rate_lo"]           # |model| > 0.613
    out["model_gt_vlo"] = out["fric_hi"] > out["rate_hi"]          # |model| > 0.077
    if latactive is not None:
        la = list(latactive)
        if len(la) != len(vals):
            raise NotV85(f"latActive has {len(la)} samples against {len(vals)} frames -- unaligned")
        for tag, want in (("engaged", True), ("manual", False)):
            sel = [d for d, a in zip(dec, la) if bool(a) is want]
            out[f"{tag}_frames"] = len(sel)
            for r in RUNGS:
                out[f"{tag}_{r}"] = (sum(1 for d in sel if d[r]) / len(sel)) if sel else None
    return out


def report(res):
    lines = [f"frames {res['frames']:,} · fingerprint OK on 100% · both nesting invariants HOLD "
             f"⇒ this log IS V85", ""]
    lines.append(f"  |gp-0x6abc| >= {RATE_T_LO:<4d} (bit7)  duty {res['rate_lo']:.4f}"
                 f"   MOTOR RATE. {RATE_T_LO} > the OLD saturation {OLD_SAT}"
                 f" ⇒ set IMPLIES V84's relay saturated")
    lines.append(f"  |gp-0x6abc| >= {RATE_T_HI:<4d} (bit6)  duty {res['rate_hi']:.4f}"
                 f"   {RATE_T_HI} > the NEW saturation {NEW_SAT}"
                 f" ⇒ 🛑 HIGH DUTY = THE EDIT UNDER-DELIVERED")
    lines.append(f"  |gp-0x6ae2| >= {FRIC_T_HI:<4d} (bit5)  duty {res['fric_hi']:.4f}"
                 f"   FRICTION x 1024, HIGH   (predicted 0.10-0.25)")
    lines.append(f"  |gp-0x6ae2| >= {FRIC_T_LO:<4d} (bit4)  duty {res['fric_lo']:.4f}"
                 f"   FRICTION x 1024, LOW    (predicted 0.35-0.70)")
    lines += ["", "  |model| BRACKET (⚠ a RANKING, not a point estimate -- rate and model are "
                  "correlated):"]
    for flag, thr, why in (("model_gt_vlo", model_threshold(FRIC_T_HI, RATE_T_HI), "b5 > b6"),
                           ("model_gt_lo", model_threshold(FRIC_T_LO, RATE_T_LO), "b4 > b7"),
                           ("model_gt_hi", model_threshold(FRIC_T_HI, RATE_T_LO), "b5 > b7")):
        lines.append(f"    {why:<8s} ⇒ |model| > {thr:.3f} : {res[flag]}")
    if "engaged_rate_lo" in res:
        lines += ["", "  WITHIN-ROUTE A/B (the cell is MODE-PROOF, so both arms carry the edit):"]
        for r in RUNGS:
            m, e = res.get(f"manual_{r}"), res.get(f"engaged_{r}")
            if m is not None and e is not None:
                lines.append(f"    {r:<8s} manual {m:.4f} -> engaged {e:.4f}")
    lines += ["", f"  STALENESS: longest run with bits 5:4 frozen while 7:6 moved = "
                  f"{res['frozen_fric_run']:,} frames ({res['frozen_fric_s']:.2f} s)."]
    lines.append("    FUN_0003b8f6 runs only in states {4, 5, 11} (caller guard `andi 0x830` "
                 "@0x221D6); elsewhere gp-0x6ae2 HOLDS.")
    lines.append("    A long frozen run is a STATE-GATE artefact, not a measurement.")
    lines += ["", "  🛑 100 Hz sampling ⇒ these are DUTY CYCLES, never peaks. Under-sampled at "
                  "27.75 Hz.",
              f"  ⊕ scale: {RATE_T_LO} counts = {RATE_T_LO / RATE_COUNTS_PER_DEG_S:.1f} deg/s · "
              f"{RATE_T_HI} counts = {RATE_T_HI / RATE_COUNTS_PER_DEG_S:.1f} deg/s"]
    return "\n".join(lines)


def _selftest():
    from build_v85_tva import wire_byte4
    # a V85 log: every frame carries the fingerprint and both nestings
    good = [wire_byte4(r, f, status_bits=s)
            for r in (-900, -100, -10, 0, 10, 100, 900)
            for f in (-40, -4, -1, 0, 1, 4, 40)
            for s in range(8)]
    res = classify_log(good, min_frames=100)
    assert res["fingerprint_ok"] and res["nesting_ok"] and res["frames"] == len(good)
    # rate rungs: |r| >= 64 on 4/7 of the r values, |r| >= 512 on 2/7
    assert abs(res["rate_lo"] - 4 / 7) < 1e-9, res["rate_lo"]
    assert abs(res["rate_hi"] - 2 / 7) < 1e-9, res["rate_hi"]
    assert abs(res["fric_lo"] - 4 / 7) < 1e-9, res["fric_lo"]
    assert abs(res["fric_hi"] - 2 / 7) < 1e-9, res["fric_hi"]
    # 🛑 a bit3-clear log MUST be refused
    try:
        classify_log([0x87] * 500 + [0x8F] * 500, min_frames=100)
    except NotV85 as e:
        assert "bit3 CLEAR" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a bit3-clear log was NOT refused -- the whole point of this file")
    # 🛑 a V84-SHAPED log (b7 and b6 mutually exclusive) MUST be refused by the nesting invariant
    v84_like = [BIT_FINGERPRINT | BIT_RATE_HI] * 300 + [BIT_FINGERPRINT | BIT_RATE_LO] * 700
    try:
        classify_log(v84_like, min_frames=100)
    except NotV85 as e:
        assert "STRUCTURALLY IMPOSSIBLE" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a mutually-exclusive (V84-shaped) log was NOT refused")
    # and the friction nesting is policed too
    fric_bad = [BIT_FINGERPRINT | BIT_FRIC_HI] * 200 + [BIT_FINGERPRINT] * 800
    try:
        classify_log(fric_bad, min_frames=100)
    except NotV85 as e:
        assert "friction HIGH rung" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("🛑 a friction-nesting violation was NOT refused")
    # the staleness detector must SEE a frozen friction field and NOT flag a moving one
    frozen = [wire_byte4(r, 0) for r in (0, 100, 0, 900, 0, 100)] * 200
    assert classify_log(frozen, min_frames=100)["frozen_fric_run"] > 100
    moving = [wire_byte4(r, f) for r, f in ((0, 0), (100, 4), (900, 40), (100, 4))] * 300
    assert classify_log(moving, min_frames=100)["frozen_fric_run"] == 0
    # the |model| brackets, as arithmetic
    assert abs(model_threshold(FRIC_T_LO, RATE_T_LO) - 0.15318) < 1e-4
    assert abs(model_threshold(FRIC_T_HI, RATE_T_LO) - 0.61274) < 1e-4
    assert abs(model_threshold(FRIC_T_HI, RATE_T_HI) - 0.07659) < 1e-4
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
    except NotV85 as e:
        assert "too few" in str(e)
    else:                                                              # pragma: no cover
        raise AssertionError("a short log was not refused")
    # the bit map is the BUILDER's, not a copy
    assert (BIT_RATE_LO, BIT_RATE_HI, BIT_FRIC_HI, BIT_FRIC_LO, BIT_FINGERPRINT) == \
        (0x80, 0x40, 0x20, 0x10, 0x08)
    assert (RATE_T_LO, RATE_T_HI, FRIC_T_HI, FRIC_T_LO) == (64, 512, 8, 2)
    assert RATE_T_LO > OLD_SAT and RATE_T_HI > NEW_SAT
    assert isinstance(CAVE_HEX, str) and len(CAVE_HEX) == 136
    # report() must run on a real result without raising
    assert "this log IS V85" in report(res)
    print("decode_v85_probe self-test: PASS")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        _selftest()
    else:                                                              # pragma: no cover
        raise SystemExit("point this at an rlog reader; `classify_log` is the entry point and it "
                         "REFUSES any log that fails the fingerprint or either nesting invariant.")
