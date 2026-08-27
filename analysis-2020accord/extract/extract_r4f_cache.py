#!/usr/bin/env python3
"""Extract route `4f` (V69, all 8 segments) to .npz caches. THE CANONICAL ROUTE-4f EXTRACTOR.

Route `75604b0a432fdc89_0000004f--61171e660d`, segments 0-7. The operator's report after this
drive: *"Grind #2 seems to be GONE at low AND high speeds."* -- confirmed, but as a REPLICATION of
V67's already-clean creep arm, not as a V69 effect. What the same route also showed: grind #1 came
BACK, at creep. See docs/handoffs/2026-08/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md.

🛑 NAME-COLLISION HISTORY, kept because it silently cost a channel once. Two agents in one session
wrote a route-4f extractor under near-identical names -- `extract/extract_r4f_cache.py` (this file) and
`r4f_extract_cache.py` -- BOTH writing `_scratch/cache/r4f/r4fs*.npz`. Whichever ran last won, and their
field sets DIFFERED: the other carried gridded `rpm` + raw `rpm_t`/`rpm_v` and no microphone; this
one carried microphone `snd_*`, the V68-payload cross-check and `{tag}_rpm.npz`. A run of one after
the other therefore produced a cache that was missing whichever channel the loser supplied, with no
error. This file now writes the UNION of both, the shim was deleted, and a fresh run reproduces the
cache with no manual patch step. Verified after the merge: 52 fields per segment, zero missing from
an 18-channel checklist, and the rpm medians are IDENTICAL to the pre-merge values
(894/810/884/923/1435/1512/1478/1343) -- the dedupe changed no published number.
⇒ RULE: one route, one extractor. If you need a variant, add a flag, not a second file.

Decode is byte-for-byte `extract/extract_v68_cache.py`'s with ONE substantive change -- the byte4 decoder,
which is BUILD-SPECIFIC and now carries V69's RATCHET probe rather than V68's grind detector. Taken
from `rlog-tools/probe/decode_v69_ratchet.py` (which `build_v69_tva.assert_decoder_matches()` links
mechanically to the built cave):

    bit7 = 1                        LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x6ada >= +4096       r24's LANE OUTPUT, post +/-0x2000 saturating clip -- the lane
                                    V69 scales 4x below 50 km/h. 0 readers / 1 writer image-wide.
                                    +4096 is HALF its rail => duty is a rail-proximity meter.
    bit5 = gp-0x6b62 >= +4096       return-to-centre lane, half its +/-0x2000 ZERO gate.
    bit4 = gp-0x6ad4 >= +4096       unfiltered residual lane (FUN_0003a382), 40% of its +/-0x2800
                                    ZERO gate.
    bit3 = 0                        *** V69 BUILD-CLASS MARKER -- CONSTANT 0. V68 emits 1 always. ***
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved.

🛑 IDENTIFICATION IS TWO-TIER, and the second tier is a real limit.
   TIER 1 (absolute): V68 asserts bit3 == 1 on every frame it emits and measured 53,991/53,991, so
   V68 -- the build that was on the car before this one -- is excluded by any bit3 == 0 frame.
   TIER 2 (subset): V66/V67 also emit bit3 == 0 and had bits 5:4 measured 0 over 186,321 frames, so
   their reachable payloads {0x87, 0xC7} are a SUBSET of V69's eight. Discrimination from those two
   rests on bit5 or bit4 ever firing, plus the flashed .rwd filename.

⚠ THE PROBE BITS ARE ONE-SIDED. Each rung tests the POSITIVE side only. A rung reading 0 bounds
that lane's positive excursions and nothing else. Never quote a null here as two-sided.

RPM (0x17C bytes 2:3, big-endian, src 1) is pulled in the SAME pass -- the engine-order veto needs
it and a second walk over 8 x ~11 MB segments is pure cost.

Usage:  python extract/extract_r4f_cache.py            # all 8 segments
        python extract/extract_r4f_cache.py 0 1 2      # chosen segments
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_0000004f--61171e660d"
SEGS = list(range(0, 8))
OUT = Path(os.environ.get("R4F_CACHE", ROOT / "_scratch/cache/r4f"))
PFX = "r4fs"

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

# V69's eight legal payloads as transmitted (bit7 set, bit3 CLEAR, status bits = 7).
LEGAL_B4 = {0x80 | a | b | c | 0x07
            for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)}
# V68's payload space -- disjoint from V69's by bit3. Any hit here means the wrong image flew.
V68_B4 = {0x88 | a | b | c | 0x07
          for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)}


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

    # ---- V69 probe decode ---------------------------------------------------------------------
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & 0x80) != 0)
    b6ada = ((p & 0x40) != 0)      # bit6  gp-0x6ada >= +4096   r24 lane output, rail proximity
    b6b62 = ((p & 0x20) != 0)      # bit5  gp-0x6b62 >= +4096   return-to-centre lane
    b6ad4 = ((p & 0x10) != 0)      # bit4  gp-0x6ad4 >= +4096   unfiltered residual lane
    cls = ((p & 0x08) != 0)        # bit3  must be 0 in EVERY frame on V69 (V68 sets it always)
    d["live"] = live.astype(float)
    d["b6_6ada"] = b6ada.astype(float)
    d["b5_6b62"] = b6b62.astype(float)
    d["b4_6ad4"] = b6ad4.astype(float)
    d["cls"] = cls.astype(float)
    # 🛑 There is NO LKAS-gate bit on V69 -- bit6 was freed from the gate to buy the third rung, and
    # V69 REVERTS the gate so gp-0x6806 no longer steers anything. Engagement comes from
    # carControl.latActive (and CAN 0x18F b4 bit3 = `sca`), which agree 99.94-100%.
    d["g6806"] = np.full(len(p), np.nan)
    b4ok = np.isin(p & 0xFF, sorted(LEGAL_B4))
    d["illegal"] = (~live | cls | ~b4ok).astype(float)

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
    #   `rpm`            gridded onto the 0x14A lattice -- what `_r4f_lib._add_rpm` and
    #                    `avg_periodogram` look for. If this is missing they silently return NaN
    #                    and every engine-order veto reads "unknown" instead of failing loudly.
    #   `rpm_t`/`rpm_v`  the raw 0x17C stream, un-gridded, for anything that needs true timing.
    #   `{tag}_rpm.npz`  a separate file, kept because `extract/extract_v68_rpm.py`'s convention reads it.
    # A cache that loses a channel costs a future session a wrong answer -- so all three, always.
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
    v68hit = {int(v): int(c) for v, c in zip(b4u, b4c) if int(v) in V68_B4}
    rp = np.array(rpm_v, float)
    rok = (rp > 400) & (rp < 7000)
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.2f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** ILLEGAL-for-V69 {bad_b4}" if bad_b4 else "   (all legal V69)") +
          (f"   *** V68 PAYLOAD {v68hit}" if v68hit else "") + "\n"
          f"      VOID {void}  bit3 CLASS(must be 0) {100 * d['cls'].mean():.3f}%  "
          f"*** bit6 gp-0x6ada {100 * d['b6_6ada'].mean():.4f}%  "
          f"*** bit5 gp-0x6b62 {100 * d['b5_6b62'].mean():.4f}%  "
          f"*** bit4 gp-0x6ad4 {100 * d['b4_6ad4'].mean():.4f}%  "
          f"illegal {int(d['illegal'].sum())}\n"
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
