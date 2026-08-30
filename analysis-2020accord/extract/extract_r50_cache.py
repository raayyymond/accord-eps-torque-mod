#!/usr/bin/env python3
"""Extract route `50` (V70, segments 0-2) to .npz caches. THE CANONICAL ROUTE-50 EXTRACTOR.

Route `75604b0a432fdc89_00000050--50f2e00e8f`, segments 0, 1, 2 -- ~181 s total, which is SHORT.
The operator drove the ratchet deliberately at the start; treat the highway exposure as thin and
say so in any result rather than pooling it with a long route.

🛑 ONE ROUTE, ONE EXTRACTOR. Two agents once wrote `extract/extract_r4f_cache.py` and `r4f_extract_cache.py`
in the same session, both writing `_scratch/cache/r4f/r4fs*.npz` with DIFFERENT field sets, and whichever
ran last silently dropped the other's channels. If you need a variant, add a flag, not a file.

Decode is byte-for-byte `extract/extract_r4f_cache.py`'s with ONE substantive change -- the byte4 decoder,
which is BUILD-SPECIFIC and now carries V70's SIGN probe rather than V69's ratchet rungs. Taken
from `rlog-tools/probe/decode_v70_probe.py`, whose CAVE_HEX `build_v70_tva.assert_decoder_matches()` links
mechanically to the built cave:

    bit7 = 1                    LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x6ada >= +512    *** THE POSITIVE CONTROL. *** r24's lane output, post its own
                                +/-0x2000 saturating clip. 0 readers / 1 writer image-wide.
    bit5 = gp-0x67fa == 10      *** THE STATE GATE. *** State 10 runs the aggregator but NOT the
                                detector (`andi 0x830` = {4,5,11}) -- the mask wraps the `jarl` in
                                the caller, so a masked-out state is never invoked at all.
    bit4 = gp-0x6adc >= 0       r26's post-clamp mirror SIGN. Read as AGREEMENT with bit3, never
                                as a standalone duty.
    bit3 = gp-0x6ada >= 0       r24's SIGN -- the keystone: build identity, the order invariant,
                                and the amplitude-independent ratchet carrier.
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved.

★ THE ORDER INVARIANT bit6 => bit3 (x >= +512 implies x >= 0) is proven in the builder over all
65,536 halfword patterns, so only 12 of 16 payloads are reachable and `bit6 = 1 with bit3 = 0` is
IMPOSSIBLE. `illegal` counts any frame outside that set; a non-zero count means the flashed image is
not this build and nothing downstream may be trusted.

🛑 IDENTIFICATION IS TWO-TIER, and the second tier is a REAL limit on THIS build in particular.
   TIER 1 (absolute, from the value set): a TOGGLING bit3 excludes V68 (constant 1, measured
   53,991/53,991) and V66/V67/V69 (constant 0, structurally) at once; bit7 excludes V53/V54; a
   `bit6 & bit3` frame excludes V65's ladder; a `bit4 & ~bit3` frame excludes V59-V63's thermometer.
   TIER 2 (NOT closeable from the wire): V55/V57/V58/V64 are four-bit probes with INDEPENDENT bits,
   so their reachable space is all 16 payloads.
   ⚠⚠ AND THE LIVE ONE: the SUPERSEDED first V70 cut carries a BYTE-IDENTICAL cave (it differs only
   in the control path -- V68's LKAS-gated arm-5244 topology instead of the shipped speed-shaped
   surface). NO probe reading can separate the two. The `.rwd` filename is the only discriminator,
   and the superseded artifact is renamed `SUPERSEDED-DO-NOT-FLASH-...` for exactly that reason.

⚠ bit6 IS ONE-SIDED; bit3 is its two-sided partner on the same cell. Never quote a bit6 null as
two-sided, and never quote bit4's duty without bit3 beside it.

RPM (0x17C bytes 2:3, big-endian, src 1) is pulled in the SAME pass -- the engine-order veto needs
it and a second walk over 3 x ~11 MB segments is pure cost.

Usage:  python extract/extract_r50_cache.py            # all 3 segments
        python extract/extract_r50_cache.py 0 1        # chosen segments
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000050--50f2e00e8f"
SEGS = [0, 1, 2]
OUT = Path(os.environ.get("R50_CACHE", ROOT / "_scratch/cache/r50"))
PFX = "r50s"

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

# V70's TWELVE legal payloads as transmitted (bit7 set, status bits = 7, and bit6 => bit3).
LEGAL_B4 = {0x80 | a | b | c | d | 0x07
            for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10) for d in (0, 0x08)
            if not (a and not d)}
# The four the invariant FORBIDS -- bit6 set with bit3 clear. 0xC7 is V66/V67's bulk payload, so a
# hit here is both an order violation AND the signature of the wrong image.
IMPOSSIBLE_B4 = {0x80 | 0x40 | b | c | 0x07 for b in (0, 0x20) for c in (0, 0x10)}
# 🛑 V68's payload space OVERLAPS V70's -- it is NOT a disjointness test, unlike V69's bit3 = 0.
# V68 pins bit3 = 1 on every frame, so its eight payloads are a SUBSET of V70's twelve and a
# bit3 = 1 frame proves nothing. The exclusion runs the OTHER way: any bit3 = 0 frame excludes V68.
# Reported below as `bit3=0 frames`, which is the statistic that actually discriminates.
V68_B4 = {0x88 | a | b | c | 0x07
          for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)}

assert len(LEGAL_B4) == 12, "the order invariant is not encoded -- expected 12 reachable payloads"
assert not (LEGAL_B4 & IMPOSSIBLE_B4), "LEGAL and IMPOSSIBLE overlap"


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def held_last(t_out, t_in, v_in, fill):
    """Zero-order hold. For CATEGORICAL channels; np.interp would fabricate intermediate codes."""
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in), t_out, side="right") - 1
    out = np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)])
    return out.astype(float)


def extract(paths, tag, t0=None):
    rows, e4hist, events = [], [], []
    last18, lastE4 = None, (0.0, 0)
    raw = {0x14A: [], 0x18F: [], 0x1FA: [], 0x0E4: []}
    # 🛑 INDEPENDENT SECOND METHOD for the STEER_STATUS census and the byte4 histogram: every
    # 0x18F / 0x14A src-1 frame exactly as it arrived, no hold, no grid.
    raw18_st, raw14_b4 = [], []
    rpm_t, rpm_v = [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    clk = {"t": [], "w": []}
    init_wall = []
    snd = {"t": [], "sp": [], "spw": []}

    for p in paths:
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
                    if src == 1 and addr in raw:
                        raw[addr].append(tm)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x17C and len(d) >= 4:
                        rpm_t.append(tm)
                        rpm_v.append((d[2] << 8) | d[3])
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
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
            elif w == "soundPressure":
                try:
                    m = evt.soundPressure
                    snd["t"].append(tm)
                    snd["sp"].append(float(m.soundPressure))
                    snd["spw"].append(float(m.soundPressureWeighted))
                except Exception:
                    for k in ("t", "sp", "spw"):
                        if len(snd[k]) > min(len(snd[j]) for j in ("t", "sp", "spw")):
                            snd[k].pop()
            elif w == "clocks":
                try:
                    wn = int(evt.clocks.wallTimeNanos)
                except Exception:
                    continue
                if wn > 0:
                    clk["t"].append(tm); clk["w"].append(wn * 1e-9)
            elif w == "initData":
                try:
                    wn = int(evt.initData.wallTimeNanos)
                except Exception:
                    wn = 0
                if wn > 0:
                    init_wall.append((tm, wn * 1e-9))
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        nm = str(e.name)
                    except Exception:
                        continue
                    events.append((tm, nm,
                                   bool(getattr(e, "enable", False)),
                                   bool(getattr(e, "softDisable", False)),
                                   bool(getattr(e, "immediateDisable", False)),
                                   bool(getattr(e, "noEntry", False))))

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    if t0 is None:
        t0 = d["t"][0]
    d["t"] = d["t"] - t0
    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V70 probe decode ---------------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & 0x80) != 0)
    b6ada_hi = ((p & 0x40) != 0)   # bit6  gp-0x6ada >= +512   POSITIVE CONTROL, one-sided
    st10 = ((p & 0x20) != 0)       # bit5  gp-0x67fa == 10     THE STATE GATE
    b6adc_sgn = ((p & 0x10) != 0)  # bit4  gp-0x6adc >= 0      r26 mirror SIGN
    b6ada_sgn = ((p & 0x08) != 0)  # bit3  gp-0x6ada >= 0      r24 mirror SIGN -- the keystone
    d["live"] = live.astype(float)
    d["b6_6ada"] = b6ada_hi.astype(float)
    d["b5_st10"] = st10.astype(float)
    d["b4_6adc"] = b6adc_sgn.astype(float)
    d["b3_6ada"] = b6ada_sgn.astype(float)
    # ★ The two decision statistics, precomputed so no downstream script re-derives them wrong.
    d["sign_agree"] = (b6adc_sgn == b6ada_sgn).astype(float)
    d["order_viol"] = (b6ada_hi & ~b6ada_sgn).astype(float)   # bit6 => bit3; must be 0 everywhere
    # 🛑 There is NO LKAS-gate bit on V70 -- the gate is reverted onto the DEAD `gp-0x683c`, so
    # gp-0x6806 no longer steers anything and no rung reads it. Engagement comes from
    # carControl.latActive (and CAN 0x18F b4 bit3 = `sca`), which agree 99.94-100%.
    d["g6806"] = np.full(len(p), np.nan)
    b4ok = np.isin(p & 0xFF, sorted(LEGAL_B4))
    d["illegal"] = (~live | ~b4ok).astype(float)

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    rawout = {f"raw{addr:03X}": (np.array(v, float) - t0) for addr, v in raw.items()}

    clk_mono = np.array(clk["t"], float) - t0
    clk_wall = np.array(clk["w"], float)
    if len(clk_wall) >= 2:
        off = float(np.median(clk_wall - clk_mono))
        off_sd = float(np.std(clk_wall - clk_mono, ddof=1))
    elif len(clk_wall) == 1:
        off, off_sd = float(clk_wall[0] - clk_mono[0]), np.nan
    else:
        off, off_sd = np.nan, np.nan
    iw = np.array(init_wall, float).reshape(-1, 2)
    if len(iw):
        iw[:, 0] -= t0
    n_snd = min(len(snd["t"]), len(snd["sp"]), len(snd["spw"]))
    snd_t = np.array(snd["t"][:n_snd], float) - t0

    # 🛑 RPM IS WRITTEN THREE WAYS ON PURPOSE, and the first one is load-bearing.
    #   `rpm`            gridded onto the 0x14A lattice -- what `_r50_lib._add_rpm` and
    #                    `avg_periodogram` look for. If this is missing they silently return NaN
    #                    and every engine-order veto reads "unknown" instead of failing loudly.
    #   `rpm_t`/`rpm_v`  the raw 0x17C stream, un-gridded, for anything that needs true timing.
    #   `{tag}_rpm.npz`  a separate file, kept because `extract/extract_v68_rpm.py`'s convention reads it.
    rpm_ts = np.array(rpm_t, float) - t0
    rpm_vs = np.array(rpm_v, float)
    d["rpm"] = (np.interp(d["t"], rpm_ts, rpm_vs) if len(rpm_ts)
                else np.full(len(d["t"]), np.nan))
    np.savez_compressed(
        OUT / f"{tag}.npz", **d, e4hist=e4, **rawout,
        rpm_t=rpm_ts, rpm_v=rpm_vs,
        clk_mono=clk_mono, clk_wall=clk_wall, init_wall=iw,
        snd_t=snd_t, snd_sp=np.array(snd["sp"][:n_snd], float),
        snd_spw=np.array(snd["spw"][:n_snd], float),
        raw18_st=np.array(raw18_st, np.int16), raw14_b4=np.array(raw14_b4, np.int16),
        t0_mono=np.array([t0]), wall_t0=np.array([off]), wall_off_sd=np.array([off_sd]))
    np.savez_compressed(OUT / f"{tag}_rpm.npz", t=rpm_ts, rpm=rpm_vs)
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    fs = 1.0 / np.median(np.diff(d["t"]))
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    void = int((d["field"] == 0).sum())
    import time as _time
    wstr = (_time.strftime("%H:%M:%S", _time.localtime(off)) if np.isfinite(off) else "??")
    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad_b4 = {int(v): int(c) for v, c in zip(b4u, b4c) if int(v) not in LEGAL_B4}
    imp_b4 = {int(v): int(c) for v, c in zip(b4u, b4c) if int(v) in IMPOSSIBLE_B4}
    # ★ THE discriminator against V68 (bit3 constant 1) and against V66/V67/V69 (bit3 constant 0).
    n_b3_lo = int(sum(int(c) for v, c in zip(b4u, b4c) if not (int(v) & 0x08)))
    n_b3_hi = int(sum(int(c) for v, c in zip(b4u, b4c) if int(v) & 0x08))
    rp = np.array(rpm_v, float)
    rok = (rp > 400) & (rp < 7000)
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** ILLEGAL-for-V70 {bad_b4}" if bad_b4 else "   (all legal V70)") +
          (f"   *** ORDER VIOLATION {imp_b4}" if imp_b4 else "") + "\n"
          f"      bit3 toggles: {n_b3_hi} set / {n_b3_lo} clear"
          + ("   => V68(const 1) AND V66/V67/V69(const 0) BOTH excluded"
             if n_b3_hi and n_b3_lo else
             "   *** CONSTANT bit3 -- V70 NOT confirmed, see the decoder") + "\n"
          f"      VOID {void}  "
          f"*** bit6 gp-0x6ada>=512 {100 * d['b6_6ada'].mean():.4f}%  "
          f"*** bit5 state10 {100 * d['b5_st10'].mean():.4f}%  "
          f"*** bit4 sgn(gp-0x6adc) {100 * d['b4_6adc'].mean():.4f}%  "
          f"*** bit3 sgn(gp-0x6ada) {100 * d['b3_6ada'].mean():.4f}%  "
          f"agree {100 * d['sign_agree'].mean():.4f}%  "
          f"illegal {int(d['illegal'].sum())}  orderviol {int(d['order_viol'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"blinker {100 * (d['cs_lchg'] > 0.5).mean():.1f}%  "
          f"ST==4 {int((d['sstat'] == 4).sum())}  ST==3 {int((d['sstat'] == 3).sum())}  "
          f"mic {n_snd}  rpm {len(rp)}"
          + (f" ({np.percentile(rp[rok], 5):.0f}..{np.percentile(rp[rok], 95):.0f})"
             if rok.any() else "") +
          f"  gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    args = [int(x) for x in sys.argv[1:]] or SEGS
    for s in args:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{PFX}{s}")
