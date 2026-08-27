#!/usr/bin/env python3
"""studies/sessions/v70/v70_bit6_threshold_sizing.py -- what `sar` immediate gives bit6 a POSITIVE CONTROL?

V69's bit6 (`gp-0x6ada >= +4096`) read 0.0000% over 47,990 frames of route 4f. The replay in
`studies/sessions/r4f/r4f_v69_readout.py` showed why: under V69's own 4x surface the route predicted ~1 one-sided hit,
so the rung had no power. V70 keeps the rung and changes ONE immediate, `sar 0xc` -> `sar 0xa`,
dropping the threshold 4096 -> 1024. This file sizes that choice against the data.

🛑 V70'S CONTROL PATH IS V67/V68's, NOT V69's. So the duty that decides the build is the one under
   the LKAS-gated arm 0xC6446 = 5244 (engaged) with the stock LERP when disengaged -- NOT under
   V69's 4x surface. All three regimes are reported; the middle one is the one to size against.

METHOD. Same replay as `studies/sessions/r4f/r4f_v69_readout.py`, which the orchestrator adjudicated as the
authoritative one: dtorque via the firmware's own 4-sample-@1kHz difference applied in frequency
(`|H(f)| = |sin(pi f 0.004)|`, the /2 folded in), gain surface read from image bytes, r24 through
its real +/-3 deadzone and +/-8192 clamp. Every |dtorque| is a LOWER BOUND (CAN Nyquist 50 Hz), so
every predicted duty below is a LOWER BOUND too -- the safe direction for "will it fire enough?".

THE METRIC THAT DECIDES IT is not duty. A rung that is high ~always carries no 7.56 Hz line, and
one that is high ~never carries none either. So this file SIMULATES THE BIT at each threshold and
measures the 6-9 Hz prominence of the simulated bit's OWN time series inside the four confirmed
ratchet episodes -- the same statistic the decoder scores on-car. Pick the threshold that maximises
THAT, subject to the route-wide duty staying out of saturation.

Usage:  python studies/sessions/v70/v70_bit6_threshold_sizing.py
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
import os
import struct
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = Path(__file__).resolve().parents[3].parent
sys.path.insert(0, str(KIT / "rlog-tools"))
sys.path.insert(0, str(KIT / "analysis-2020accord"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

from decode_v67_gate import runs_of, sustained                                # noqa: E402
from r4f_v69_readout import CACHE, dtorque_series, V69_RECS                   # noqa: E402
import v69_surface_math as S                                                  # noqa: E402

ROOT = os.environ["ACCORD_FIRMWARE_ROOT"]
V69IMG = Path(ROOT) / "analysis-2020accord" / "_v69_plain_image.bin"
CREEP_MAX_MS, HANDS_OFF_TQ = 4.0, 300
ARM_GATED = 5244                    # cal 0xC6446 under V67/V68 -- V70's control path
THRESHOLDS = (512, 1024, 2048, 4096)
SAR_FOR = {4096: 0xC, 2048: 0xB, 1024: 0xA, 512: 0x9}

# The three rungs' `sar` halfword addresses inside the 66-byte cave at 0xC4B34.
# layout per rung: ld.h(4) sar(2) cmp(2) blt(2) movea(4) = 14 bytes, after a 4-byte movea preamble.
SAR_ADDR = {"bit6 gp-0x6ada": 0xC4B3C, "bit5 gp-0x6b62": 0xC4B4A, "bit4 gp-0x6ad4": 0xC4B58}
LDH_ADDR = {"bit6 gp-0x6ada": 0xC4B38, "bit5 gp-0x6b62": 0xC4B46, "bit4 gp-0x6ad4": 0xC4B54}


# =====================================================================================================
# 1. THE ENCODING -- proved from the built image, not assumed
# =====================================================================================================
def encoding_proof():
    V = V69IMG.read_bytes()
    print("=" * 102)
    print("1. THE `sar` IMMEDIATE MAPPING, PROVED FROM THE BUILT V69 IMAGE")
    print("   V850 Format II:  [reg2:5][opcode:6][imm5:5]   -- imm5 is bits 4:0 of the HALFWORD,")
    print("   i.e. the LOW BYTE only. The threshold is 1 << imm5.")
    ok = True
    for name in SAR_ADDR:
        sa, la = SAR_ADDR[name], LDH_ADDR[name]
        hw = struct.unpack_from("<H", V, sa)[0]
        ld = struct.unpack_from("<H", V, la)[0]
        disp = struct.unpack_from("<H", V, la + 2)[0]
        op_ld, reg2_ld, reg1_ld = (ld >> 5) & 0x3F, ld >> 11, ld & 0x1F
        print(f"\n   {name}")
        print(f"     ld.h  @0x{la:05X}  bytes {V[la:la + 4].hex()}   hw1=0x{ld:04X} "
              f"op=0x{op_ld:02X} ({'ld.h ✅' if op_ld == 0x39 else 'NOT ld.h 🛑'}) "
              f"reg2=r{reg2_ld} reg1=r{reg1_ld} disp=0x{disp:04X} "
              f"(gp{-((0x10000 - disp) if disp & 0x8000 else disp):#07x})")
        print(f"     sar   @0x{sa:05X}  bytes {V[sa:sa + 2].hex()}   hw =0x{hw:04X}  "
              f"reg2=r{hw >> 11}  op=0b{(hw >> 5) & 0x3F:06b}  imm5={hw & 0x1F} "
              f"⇒ threshold {1 << (hw & 0x1F)}")
        ok &= (op_ld == 0x39)
        for T in THRESHOLDS:
            nh = (hw & ~0x1F) | SAR_FOR[T]
            print(f"       T={T:5d}  sar 0x{SAR_FOR[T]:x}  halfword 0x{nh:04X}  "
                  f"bytes {struct.pack('<H', nh).hex()}   "
                  f"({'UNCHANGED' if nh == hw else 'low byte %02x -> %02x' % (hw & 0xFF, nh & 0xFF)})")
    print(f"\n   🛑 ONE-BIT TRAP GUARD: `ld.h` = op 0x39, `st.h` = op 0x3B, and gp-0x6ada's only")
    print(f"      real instance IS the st.h form with the SAME displacement halfword. The `sar`")
    print(f"      edit changes the LOW BYTE of the halfword at 0xC4B3C ONLY -- two bytes AFTER the")
    print(f"      ld.h's opcode halfword (0xC4B38-39) and after its displacement (0xC4B3A-3B).")
    print(f"      Opcode, both register fields and the displacement are all outside the edited byte.")
    print(f"      all three loads are ld.h: {ok}")
    print(f"   ⇒ bit6 4096 -> 1024 is EXACTLY: 0xC4B3C  0xAC -> 0xAA   (one byte, one CRC block)")


# =====================================================================================================
# 2. THE REPLAY
# =====================================================================================================
def gains(v_kmh, degs, lat, regime):
    """Per-frame Q10 gain for r24, under each candidate control path."""
    cache, out = {}, np.zeros(len(v_kmh), dtype=np.int64)
    for i in range(len(v_kmh)):
        if regime == "v67v68" and lat[i]:
            out[i] = ARM_GATED                      # the LKAS arm REPLACES the LERP
            continue
        recs = V69_RECS if regime == "v69x4" else S.STOCK
        key = (int(v_kmh[i] * S.COUNTS_PER_KMH) if np.isfinite(v_kmh[i]) else 0,
               int(abs(degs[i]) * S.SCALE_A) if np.isfinite(degs[i]) else 0, regime)
        g = cache.get(key)
        if g is None:
            g = cache[key] = S.gain_q10(key[0], key[1], recs)
        out[i] = g
    return out


def shaped_lane(dt, g):
    """r24 BEFORE the polarity multiply: (dtorque*gain)>>10, +/-3 deadzone, +/-8192 clamp."""
    d = np.clip(np.rint(dt), -S.DTORQUE_CLAMP, S.DTORQUE_CLAMP).astype(np.int64)
    scaled = (d * g) >> 10                          # V850 `sar`: arithmetic, floors negatives
    sh = np.where(scaled > S.DEADZONE, scaled - S.DEADZONE,
                  np.where(scaled < -S.DEADZONE, scaled + S.DEADZONE, 0))
    return np.clip(sh, -S.LANE_CLAMP, S.LANE_CLAMP)


def prom69(mask, fs, lo=6.0, hi=9.0):
    m = np.asarray(mask, bool)
    if m.sum() in (0, len(m)) or len(m) < 128:
        return float("nan")
    x = m.astype(float) - m.mean()
    P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    b = (f >= lo) & (f <= hi)
    bg = (f >= 2.0) & (f <= 20.0) & ~b
    fl = np.median(P[bg])
    return float(P[b].max() / fl) if fl > 0 else float("nan")


def band_prom_analog(x, fs):
    x = np.asarray(x, float) - np.mean(x)
    P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    b = (f >= 6.0) & (f <= 9.0)
    bg = (f >= 2.0) & (f <= 20.0) & ~b
    fl = np.median(P[bg])
    return float(f[b][np.argmax(P[b])]), (float(P[b].max() / fl) if fl > 0 else float("nan"))


def main():
    print(__doc__)
    encoding_proof()

    z = np.load(CACHE, allow_pickle=False)
    d = {k: z[k] for k in z.files}
    b4, t, seg = d["b4"], d["t"], d["seg"]
    n = len(b4)
    fs = (n - 1) / (t[-1] - t[0])
    v_kmh = d["v"] * 3.6
    lat = d["lat"].astype(bool)
    sus = np.abs(sustained(d["tq"], fs))
    cell = lat & (d["v"] <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ)
    dt = dtorque_series(d["tq"], seg)

    # the four CONFIRMED ratchet episodes, re-derived exactly as in studies/sessions/r4f/r4f_v69_readout.py
    eps = [ab for ab in runs_of(cell) if ab[1] - ab[0] >= 256]
    mn, sn = [], []
    rng = np.random.default_rng(69)
    outside = lat & ~cell
    orr = [ab for ab in runs_of(outside) if ab[1] - ab[0] >= 128]
    lens = [b - a for a, b in eps]
    for _ in range(400):
        a, b = orr[rng.integers(len(orr))]
        L = min(lens[rng.integers(len(lens))], b - a)
        s0 = a + rng.integers(0, b - a - L + 1)
        for ch in (d["tq"], d["rate"]):
            mn.append(band_prom_analog(ch[s0:s0 + L], fs)[1])
    for a, b in eps:
        m = (a + b) // 2
        for aa, bb in ((a, m), (m, b)):
            for ch in (d["tq"], d["rate"]):
                sn.append(band_prom_analog(ch[aa:bb], fs)[1])
    floor = max(np.percentile(sn, 95), np.percentile(mn, 95))
    conf = [(a, b) for a, b in eps
            if max(band_prom_analog(d["tq"][a:b], fs)[1],
                   band_prom_analog(d["rate"][a:b], fs)[1]) > floor]
    cidx = np.concatenate([np.arange(a, b) for a, b in conf])
    print("\n" + "=" * 102)
    print(f"2. THE REPLAY   frames {n}   fs {fs:.3f} Hz   floor {floor:.1f}")
    print(f"   confirmed ratchet episodes: {len(conf)}   {len(cidx)} frames / "
          f"{len(cidx) / fs:.2f} s   median line "
          f"{np.median([band_prom_analog(d['tq'][a:b], fs)[0] for a, b in conf]):.2f} Hz")

    for regime, label in (("stock", "STOCK LERP everywhere"),
                          ("v67v68", "V67/V68 GATED ARM 5244 engaged, stock LERP manual  ⇐ V70's path"),
                          ("v69x4", "V69 4x SPEED-SHAPED surface")):
        g = gains(v_kmh, d["rate"], lat, regime)
        sh = shaped_lane(dt, g)
        print(f"\n   --- {label}")
        print(f"       max |r24| route {np.abs(sh).max():5.0f}   in ratchet episodes "
              f"{np.abs(sh[cidx]).max():5.0f}   (rail 8192)")
        print(f"       {'T':>5s} {'sar':>5s} | {'route +':>8s} {'route -':>8s} | "
              f"{'ratchet +':>10s} {'ratchet -':>10s} | {'6-9Hz prom of the SIMULATED bit':>32s}")
        for T in THRESHOLDS:
            rp = float((sh >= T).mean())
            rm = float((-sh >= T).mean())
            cp = float((sh[cidx] >= T).mean())
            cm = float((-sh[cidx] >= T).mean())
            proms = [prom69((sh[a:b] >= T), fs) for a, b in conf]
            promsm = [prom69((-sh[a:b] >= T), fs) for a, b in conf]
            good = [p for p in proms + promsm if np.isfinite(p)]
            live = sum(1 for p in proms if np.isfinite(p))
            print(f"       {T:5d} {'0x%x' % SAR_FOR[T]:>5s} | {rp:8.5f} {rm:8.5f} | "
                  f"{cp:10.5f} {cm:10.5f} | "
                  f"median {np.median(good) if good else float('nan'):7.1f}  "
                  f"toggling in {live}/{len(conf)} eps")

    print("\n" + "=" * 102)
    print("3. bit5 / bit4 REACHABILITY AT EACH THRESHOLD  (see studies/sessions/v70/v70_rung_reachability.py for the")
    print("   derivations; the trapezoid below is byte-read here as the second method)")
    B = Path(ROOT, "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    TP = 0xBF000
    xs = [struct.unpack_from("<h", B, TP + 0x76CE + 2 * i)[0] for i in range(5)]
    ys = [struct.unpack_from("<h", B, TP + 0x76D8 + 2 * i)[0] for i in range(5)]
    sc = struct.unpack_from("<H", B, TP + 0x73C2)[0]
    print(f"   FUN_000361c8 -> gp-0x6b5e:  X 0xC66CE {xs}   Y 0xC66D8 {ys}   "
          f"scale 0xC63C2 = {sc} (Q10 ⇒ identity)")
    max_6b5e = max(ys) * sc // 1024
    max_6b62 = max_6b5e + 1024          # sVar13 max + sVar8 pinned at cal 0xC618A
    ceil_6ad4_max, ceil_6ad4_creep = 1024, 341
    print(f"   ⇒ max |gp-0x6b5e| = {max_6b5e};  |sVar13| <= min({max_6b5e}, 8192) = {max_6b5e}")
    print(f"   ⇒ max |gp-0x6b62| = {max_6b5e} + 1024 = {max_6b62}   (sVar8 pinned while latched)")
    print(f"   ⇒ max |gp-0x6ad4| = {ceil_6ad4_max} anywhere, {ceil_6ad4_creep} at 8 km/h creep")
    h5 = f"bit5 % of {max_6b62}"
    h4 = f"bit4 % of {ceil_6ad4_creep} (creep)"
    print(f"\n   {'T':>5s} {'sar':>5s} | {'bit6 % of 8192 rail':>20s} {h5:>20s} {h4:>26s}")
    allT = {128: 0x7, 256: 0x8, **{t: SAR_FOR[t] for t in THRESHOLDS}}
    for T in sorted(allT):
        f6, f5, f4 = 100 * T / 8192, 100 * T / max_6b62, 100 * T / ceil_6ad4_creep
        print(f"   {T:5d} {'0x%x' % allT[T]:>5s} | {f6:19.1f}% {f5:19.1f}%"
              f"{'  UNREACHABLE' if f5 > 100 else '':<13s}"
              f"{f4:13.1f}%{'  UNREACHABLE' if f4 > 100 else ''}")
    print("\n   ⇒ PER-RUNG RECOMMENDATION -- each rung has its OWN `sar`, so they need not match:")
    print("       bit6 gp-0x6ada  @0xC4B3C  ac -> a9 (T=512)   best 6-9 Hz prominence, 4/4 episodes")
    print("                                 ac -> aa (T=1024)  also live, 4/4 episodes, prom 1.5x lower")
    print("       bit5 gp-0x6b62  @0xC4B4A  ac -> aa (T=1024)  17.7% of its 5786 max -- a real detector")
    print("       bit4 gp-0x6ad4  @0xC4B58  ac -> a7 (T=128)   the ONLY value that is reachable at")
    print("                                 creep; T=256 is 75-156% of the ceiling across 4.9-8 km/h")
    print("                                 and T>=512 is unreachable everywhere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
