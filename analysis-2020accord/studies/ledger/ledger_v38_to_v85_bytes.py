#!/usr/bin/env python3
"""DELIVERED-BYTES LEDGER, V38 -> V85.  Reads the PLAIN IMAGES ON DISK, not the build scripts.

Supersedes studies/ledger/ledger_v38_to_v84_bytes.py: adds V85, adds the V85/V86-relevant sites (the Coulomb-relay
cal 0xC40BC, the V38 authority package, the V56 mute pair, the V61 rate taps, the phase lever 0xC6C42),
and adds a SILENT-LOSS AUDIT that scores the CURRENT candidate image against every historically
confirmed fix.

Plain images are flat 1 MiB code images: file offset == firmware address (verified by anchoring
0xC646C == 891 on stock, and 0x2A1F0 halfword == 0x7CD0 on V57+).
V850 is LITTLE-ENDIAN.  Record layout: [npt:u16][X x npt][Y x npt], Y at base + 2 + 2*npt.

Env: ACCORD_FIRMWARE_ROOT (default C:/Users/dudei/Desktop/Projects/accord-firmwares)
"""
import struct, os, sys, json
from pathlib import Path

FWROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                             r"C:/Users/dudei/Desktop/Projects/accord-firmwares"))
ROOT = FWROOT / "analysis-2020accord"
STOCK = ROOT / "stock_fw_dump" / "code.bin"

# ---- build order, V38 .. V85.  filename stem -> label
BUILDS = [
    ("STOCK", STOCK),
    ("V38",  "_v38_plain_image.bin"),
    ("V39",  "_v39_plain_image.bin"),
    ("V40",  "_v40_plain_image.bin"),
    ("V41",  "_v41_plain_image.bin"),
    ("V42",  "_v42_plain_image.bin"),
    ("V43",  "_v43_plain_image.bin"),
    ("V44",  "_v44_plain_image.bin"),
    ("V45",  "_v45_plain_image.bin"),
    ("V46",  "_v46_plain_image.bin"),
    ("V47",  "_v47_plain_image.bin"),
    ("V48a", "_v48a_plain_image.bin"),
    ("V48b", "_v48b_plain_image.bin"),
    ("V49",  "_v49_plain_image.bin"),
    ("V49p", "_v49p_plain_image.bin"),
    ("V50",  "_v50_plain_image.bin"),
    ("V50probe", "_v50probe_plain_image.bin"),
    ("V51probe", "_v51probe_plain_image.bin"),
    ("V52",  "_v52_plain_image.bin"),
    ("V52c", "_v52c_plain_image.bin"),
    ("V53",  "_v53_plain_image.bin"),
    ("V54",  "_v54_plain_image.bin"),
    ("V55",  "_v55_plain_image.bin"),
    ("V56",  "_v56_plain_image.bin"),
    ("V57",  "_v57_plain_image.bin"),
    ("V58",  "_v58_plain_image.bin"),
    ("V59",  "_v59_plain_image.bin"),
    ("V60",  "_v60_plain_image.bin"),
    ("V61",  "_v61_plain_image.bin"),
    ("V62",  "_v62_plain_image.bin"),
    ("V63",  "_v63_plain_image.bin"),
    ("V64",  "_v64_plain_image.bin"),
    ("V65",  "_v65_plain_image.bin"),
    ("V66",  "_v66_plain_image.bin"),
    ("V67",  "_v67_plain_image.bin"),
    ("V68",  "_v68_plain_image.bin"),
    ("V69",  "_v69_plain_image.bin"),
    ("V70",  "_v70_plain_image.bin"),
    ("V71a", "_v71a_plain_image.bin"),
    ("V71b", "_v71b_plain_image.bin"),
    ("V71c", "_v71c_plain_image.bin"),
    ("V72",  "_v72_plain_image.bin"),
    ("V73",  "_v73_plain_image.bin"),
    ("V74",  "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
    ("V75",  "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
    ("V76",  "_v76_v38base_relu_damper_plain_image.bin"),
    ("V76g", "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"),
    ("V77",  "_v77_C63A0.1024_v74base_plain_image.bin"),
    ("V77b", "_v77b_C63A0.1024_v75base_plain_image.bin"),
    ("V78",  "_v78_v76base_ey1_449_dose206_plain_image.bin"),
    ("V79",  "_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin"),
    ("V80",  "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin"),
    ("V81",  "_v81_C407E.511-FRICTION.STOCK_plain_image.bin"),
    ("V83a", "_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin"),
    ("V84",  "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin"),
    ("V85",  "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin"),
]

CURRENT = "V85"          # the build on the car / the V86 base

# ---- scalar sites: (addr, width, label).  width 1 = byte, 2 = signed halfword LE
SITES = [
    # --- code bytes (mode-proof by construction)
    (0x3AA96, 1, "Lever B gate byte (C5=dead 0x683C / FB=latActive 0x6806)"),
    (0x3AB76, 1, "Lever A sar r26 (AA=stock / A9=x2 / A8=x4)"),
    (0x3AC20, 1, "Lever A sar r24 (AA=stock / A9=x2 / A8=x4)"),
    (0x454FE, 1, "V42 macro-ratchet fix (BA=stock bne / B5=br)  [ELIMINATED: state 4 never runs]"),
    # --- rate lane arms
    (0xC643E, 2, "gain_A arm"),
    (0xC6440, 2, "third arm gp-0x671a"),
    (0xC6442, 2, "gp-0x671d arm (outranks gate) [NEVER WRITTEN]"),
    (0xC6444, 2, "r26 engaged arm"),
    (0xC6446, 2, "r24 engaged arm (Lever B arm)"),
    (0xC644A, 2, "V43 dirty-derivative pole"),
    (0xC6450, 2, "V46 Stage-A EMA pole"),
    # --- LKAS authority package (V38)
    (0xC646C, 2, "SHARED sensor scale (stock 891)"),
    (0xC6CD0, 2, "V57 PRIVATE forward LKAS gain (3564 = 4x)"),
    (0x2A1F0, 2, "V57 decouple displacement (746C=shared / 7CD0=private)"),
    (0xC61B2, 2, "ARBITRATION output clamp (stock 512)"),
    (0xC61B4, 2, "LKAS-GAIN output clamp (stock 512)"),
    (0xC674E, 2, "soft-EME corridor +A"), (0xC6750, 2, "soft-EME corridor +B"),
    (0xC675A, 2, "soft-EME corridor -A"), (0xC675C, 2, "soft-EME corridor -B"),
    (0xC6768, 2, "V31 boost floor [0]"), (0xC676A, 2, "V31 boost floor [1]"),
    (0xC676C, 2, "V31 boost floor [2]"),
    (0xE41BC, 2, "setpoint limit Y row @0xE41A8 (stock 15360)"),
    (0xE51A8, 2, "setpoint limit record 0xE5180+0x28 (live record per V74)"),
    # --- V36/V37 debounce SM + DTC-0x49 (confirmed gentle-EME fix)
    (0xC61C0, 2, "V36 debounce SM cal A (stock 1600, defeated=0xFFFF)"),
    (0xC61C2, 2, "V36 debounce SM cal B (stock 896)"),
    (0xC61C4, 2, "V36 debounce SM cal C (stock 1280)"),
    (0xC64B4, 1, "V36 debounce counter gate A (stock 112, defeated=0xFF)"),
    (0xC64B6, 1, "V36 debounce counter gate B (stock 54)"),
    (0xC64B8, 1, "V37 DTC-0x49 counter gate (stock 112, defeated=0xFF)"),
    # --- deadbands / lockouts
    (0xC61B8, 2, "pre-gain deadband (102) [NEVER WRITTEN]"),
    (0xC61F6, 2, "r24 lane deadzone (3) [NEVER WRITTEN]"),
    (0xC62EA, 2, "low-speed steer lockout window (V53 steer-to-zero)"),
    # --- Path-2 damper
    (0xC63A0, 2, "Path-2 damper weight"),
    (0xC63AA, 2, "w_LKAS (1 reader, 0 writers) [NEVER WRITTEN]"),
    (0xC63AC, 2, "Path-2 accumulator IIR coeff (102 => fc ~16.7 Hz) [NEVER WRITTEN]"),
    # --- friction / interlock lane
    (0xC407C, 2, "interlock clamp neighbour [NEVER WRITTEN]"),
    (0xC407E, 2, "friction-comp clamp / DTC-0x1d HARD-FAULT INTERLOCK (Honda 511)"),
    (0xC40BC, 2, "V85 Coulomb-relay linearisation cal (stock 600; V85=6000)"),
    # --- aggregator
    (0xC64C8, 1, "AGGREGATOR MODE SELECTOR (0=passthru,1=discard,2=blend) [NEVER WRITTEN]"),
    (0xC64C9, 1, "blend mux [NEVER WRITTEN]"),
    (0xC64FA, 1, "CEIL byte cal (5) [NEVER WRITTEN]"),
    # --- misc
    (0xC6206, 2, "speed-selector cal A (V40 brick)"),
    (0xC6208, 2, "speed-selector cal B (V40 brick)"),
    (0xC61DA, 2, "Q10 integrator scale [NEVER WRITTEN]"),
    (0xC6316, 2, "governor vehicle-speed cal ~10km/h [NEVER WRITTEN]"),
    (0xC6158, 2, "ceiling tp+0x7158 fallback [NEVER WRITTEN]"),
    (0xC6C42, 2, "differentiator delay D (THE PHASE LEVER) [NEVER WRITTEN]"),
    (0xC6AFC, 2, "V56 mute cell A (gp-0x6ad4 lane)"),
    (0xC6AFE, 2, "V56 mute cell B"),
    (0xD2006, 2, "V60 boost-amplitude blend"),
    (0x3AB6C, 1, "V61 r26 rate tap byte"),
    (0x3AC16, 1, "V61 r24 rate tap byte"),
    # gain_A records
    (0xC6A72, 2, "gain_A rec0 Y[0]"), (0xC6A74, 2, "gain_A rec0 Y[1]"),
    (0xC6A76, 2, "gain_A rec0 Y[2]"), (0xC6A78, 2, "gain_A rec0 Y[3]"),
    (0xC6A86, 2, "gain_A rec1 Y[0]"), (0xC6A88, 2, "gain_A rec1 Y[1]"),
    (0xC6A8A, 2, "gain_A rec1 Y[2]"), (0xC6A8C, 2, "gain_A rec1 Y[3]"),
    (0xC6A9A, 2, "gain_A rec2 Y[0] (>=50 km/h)"), (0xC6A9C, 2, "gain_A rec2 Y[1]"),
    (0xC6A9E, 2, "gain_A rec2 Y[2]"), (0xC6AA0, 2, "gain_A rec2 Y[3]"),
    (0xC6AAE, 2, "gain_A rec3 Y[0] (>=50 km/h)"), (0xC6AB0, 2, "gain_A rec3 Y[1]"),
    (0xC6AB2, 2, "gain_A rec3 Y[2]"), (0xC6AB4, 2, "gain_A rec3 Y[3]"),
]

# ---- pointer arrays for the mode-indexed factor tables
PTRS = {
    "FactorB":  0xC9CCC,
    "FactorC":  0xC9E9C,
    "FactorD":  0xC9DB4,
    "FactorE":  0xC9F84,
    "ceiling":  0xC77A0,
    "friction": 0xCBE74,
}
GAIN_B_PTRS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
MODES = [10, 11, 12, 24, 25, 26, 27]
ENGAGED_MODES = [26, 27]
MANUAL_MODES = [24, 25]

# ---- THE SILENT-LOSS AUDIT.
# (label, [(addr, width, value_that_means_FIX_PRESENT), ...], builds_that_carried_it, on-car status)
CONFIRMED_FIXES = [
    ("V37 gentle-EME debounce/DTC-0x49 defeat",
     [(0xC61C0, 2, -1), (0xC61C2, 2, -1), (0xC61C4, 2, -1),
      (0xC64B4, 1, 0xFF), (0xC64B6, 1, 0xFF), (0xC64B8, 1, 0xFF)],
     "V37+", "CONFIRMED on-car 2026-07-14 (gentle EME resolved)"),
    ("V42 macro-ratchet byte 0x454FE",
     [(0x454FE, 1, 0xB5)],
     "V42-V49,V50,V52-V52c,V71a-V75,V76g-V77b,V80-V85?",
     "ELIMINATED structurally (gp-0x67fa==4 fires 0/123,277) - carry it, but it cannot act"),
    ("V53 steer-to-zero (low-speed lockout removed)",
     [(0xC62EA, 2, 0)],
     "V53-V75,V76g-V77b,V81+", "CONFIRMED on-car (feature works)"),
    ("V57 LKAS-gain decouple (private forward cell)",
     [(0x2A1F0, 2, 0x7CD0), (0xC6CD0, 2, 3564), (0xC646C, 2, 891)],
     "V57-V75,V76g,V77,V77b,V81+", "Null for symptoms; structural hygiene (feedback readers at stock)"),
    ("LEVER A - V62 sar x2 on BOTH rate lanes",
     [(0x3AB76, 1, 0xA9), (0x3AC20, 1, 0xA9)],
     "V62,V65,V71a ONLY", "MEASURED S1 FIX 0.39 [0.32,0.48]; r24 half CAUSED grind #2"),
    ("LEVER B - V67/V68 LKAS-gated r24 arm",
     [(0x3AA96, 1, 0xFB), (0xC6446, 2, 5244)],
     "V67,V68,V71c,V76g,V84,V85?", "BEST S1 IN KIT 0.40 [0.27,0.58]; FALSIFIED for the highway grind"),
    ("V81 hard-fault interlock reverted to Honda",
     [(0xC407E, 2, 511)],
     "all except V73,V74,V75,V76g,V77,V77b", "CONFIRMED: V81/V83a/V84/V85 fault-free; 850 => V74/V75 faulted"),
    ("V83a Path-2 damper weight back to Honda",
     [(0xC63A0, 2, 1024)],
     "V83a+", "0xC63A0 EXONERATED for faults; 2048 never showed a benefit"),
    ("V38 LKAS authority package (NOT a fix - the suspected CAUSE)",
     [(0xC61B2, 2, 2048), (0xC61B4, 2, 2048), (0xC6768, 2, 5120)],
     "V38-V85, ALL", "FROZEN for 47 builds; never once lowered or even built lower"),
]


def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]


def rec_any(b, base):
    n = u16(b, base)
    if not (1 <= n <= 16):
        return None
    xs = list(struct.unpack_from(f"<{n}h", b, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n))
    return n, xs, ys


def load(p):
    p = Path(p) if isinstance(p, Path) else ROOT / p
    return p.read_bytes()


def main():
    imgs = {}
    for name, f in BUILDS:
        p = f if isinstance(f, Path) else ROOT / f
        if not p.exists():
            print(f"### MISSING {name}: {p}", file=sys.stderr); continue
        imgs[name] = load(p)
    names = [n for n, _ in BUILDS if n in imgs]

    # sanity anchors
    st = imgs["STOCK"]
    assert len(st) == 0x100000, len(st)
    assert s16(st, 0xC646C) == 891, s16(st, 0xC646C)
    assert st[0x454FE] == 0xBA, hex(st[0x454FE])
    assert s16(st, 0xC407E) == 511, s16(st, 0xC407E)
    assert s16(st, 0xC40BC) == 600, s16(st, 0xC40BC)
    assert u16(st, 0x2A1F0) == 0x746C, hex(u16(st, 0x2A1F0))
    print("ANCHORS OK: stock 0xC646C=891, 0x454FE=0xBA, 0xC407E=511, 0xC40BC=600, "
          "0x2A1F0=0x746C, len=0x100000")
    print(f"BUILDS LOADED: {len(names)}  (current candidate = {CURRENT})\n")

    out = {}
    rows = []
    for addr, w, label in SITES:
        vals = {}
        for n in names:
            b = imgs[n]
            vals[n] = b[addr] if w == 1 else s16(b, addr)
        rows.append((addr, w, label, vals))
    out["scalars"] = [{"addr": f"0x{a:05X}", "w": w, "label": l, "vals": v_}
                      for a, w, l, v_ in rows]

    # --- factor records per mode
    fac = {}
    for fname, ptr in PTRS.items():
        fac[fname] = {}
        for m in MODES:
            fac[fname][m] = {}
            for n in names:
                b = imgs[n]
                base = u32(b, ptr + m * 4)
                if base >= 0x100000:
                    fac[fname][m][n] = f"PTR_OOR 0x{base:08X}"; continue
                r = rec_any(b, base)
                fac[fname][m][n] = (f"@0x{base:05X}", r[0], r[1], r[2]) if r else f"BAD@0x{base:05X}"
    fac["gain_B"] = {}
    for i, ptr in enumerate(GAIN_B_PTRS):
        for m in MODES:
            key = f"arr{i}_m{m}"
            fac["gain_B"][key] = {}
            for n in names:
                b = imgs[n]
                base = u32(b, ptr + m * 4)
                if base >= 0x100000:
                    fac["gain_B"][key][n] = f"PTR_OOR 0x{base:08X}"; continue
                r = rec_any(b, base)
                fac["gain_B"][key][n] = (f"@0x{base:05X}", r[0], r[1], r[2]) if r else f"BAD@0x{base:05X}"
    out["factors"] = fac

    outp = Path(os.environ.get("LEDGER_OUT", "ledger_v85_bytes.json"))
    outp.write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {outp}\n")

    # =====================================================================
    # SECTION C — THE SILENT-LOSS AUDIT against the CURRENT candidate
    # =====================================================================
    print("=" * 100)
    print(f"SILENT-LOSS AUDIT — is each historically confirmed fix PRESENT on {CURRENT}?")
    print("=" * 100)
    cur = imgs[CURRENT]
    for label, cells, carried, status in CONFIRMED_FIXES:
        ok = []
        for addr, w, want in cells:
            got = cur[addr] if w == 1 else s16(cur, addr)
            stockv = st[addr] if w == 1 else s16(st, addr)
            ok.append((addr, w, want, got, stockv, got == want))
        allok = all(o[5] for o in ok)
        anystock = all(o[3] == o[4] for o in ok)
        verdict = "PRESENT" if allok else ("BYTE-STOCK (ABSENT)" if anystock else "PARTIAL/OTHER")
        print(f"\n[{verdict:>19}]  {label}")
        print(f"      carried by: {carried}")
        print(f"      on-car     : {status}")
        for addr, w, want, got, stockv, good in ok:
            f = (lambda v: f"0x{v:02X}") if w == 1 else str
            mark = "ok " if good else "!! "
            print(f"      {mark}0x{addr:05X} w{w}  want={f(want):>8}  {CURRENT}={f(got):>8}  stock={f(stockv):>8}")

    # =====================================================================
    # SECTION A — CROSS-BUILD SCALAR MATRIX, with FROZEN-FOR-N
    # =====================================================================
    print("\n\n" + "=" * 100)
    print("SCALAR SITES — run-length along build order; FROZEN-N counted back from the current build")
    print("=" * 100)
    for addr, w, label, vals in rows:
        uniq = set(vals.values())
        segs = []
        prev = None; run = []
        for n in names:
            v = vals[n]
            if v != prev:
                if run: segs.append((prev, run))
                run = [n]; prev = v
            else:
                run.append(n)
        if run: segs.append((prev, run))
        # frozen-N: how many builds (excluding STOCK) back from CURRENT hold the current value
        curv = vals[CURRENT]
        bi = names.index(CURRENT)
        n_frozen = 0
        for j in range(bi, 0, -1):     # stop before STOCK
            if vals[names[j]] == curv: n_frozen += 1
            else: break
        f = (lambda v: f"0x{v:02X}") if w == 1 else str
        stockv = st[addr] if w == 1 else s16(st, addr)
        tag = "  [CONSTANT ALL BUILDS]" if len(uniq) == 1 else ""
        eq = "== STOCK" if curv == stockv else f"!= stock({f(stockv)})"
        print(f"\n0x{addr:05X} w{w}  {label}{tag}")
        print(f"    {CURRENT} = {f(curv)}  {eq}   FROZEN for the last {n_frozen} build image(s)")
        if len(uniq) > 1:
            for v, r in segs:
                rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
                print(f"        {f(v):>8}  :  {rng}")

    # =====================================================================
    # FACTOR RECORDS
    # =====================================================================
    print("\n\n" + "=" * 100)
    print("FACTOR RECORDS (run-length along build order)")
    print("=" * 100)
    for fname in ("FactorC", "FactorE", "FactorD", "FactorB", "ceiling", "friction"):
        for m in MODES:
            vals = fac[fname][m]
            prev = None; run = []; segs = []
            for n in names:
                v = str(vals[n])
                if v != prev:
                    if run: segs.append((prev, run))
                    run = [n]; prev = v
                else:
                    run.append(n)
            if run: segs.append((prev, run))
            mtag = " [ENGAGED]" if m in ENGAGED_MODES else (" [MANUAL]" if m in MANUAL_MODES else " [INERT-mode]")
            if len(segs) == 1:
                print(f"\n{fname} m{m}{mtag}: [CONSTANT ALL BUILDS] {segs[0][0]}")
            else:
                print(f"\n{fname} m{m}{mtag}:   {CURRENT} = {vals[CURRENT]}")
                for v, r in segs:
                    rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
                    print(f"    {rng:<16} {v}")

    print("\n\n" + "=" * 100)
    print("gain_B (4 arrays x 7 modes) — CHANGED entries only; engaged columns flagged")
    print("=" * 100)
    never = []
    for key in sorted(fac["gain_B"]):
        vals = fac["gain_B"][key]
        if len(set(str(v) for v in vals.values())) == 1:
            if key.endswith(("m24", "m25", "m26", "m27")):
                never.append(key)
            continue
        prev = None; run = []; segs = []
        for n in names:
            v = str(vals[n])
            if v != prev:
                if run: segs.append((prev, run))
                run = [n]; prev = v
            else:
                run.append(n)
        if run: segs.append((prev, run))
        print(f"\ngain_B {key}:   {CURRENT} = {vals[CURRENT]}")
        for v, r in segs:
            rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
            print(f"    {rng:<16} {v}")
    print(f"\ngain_B NEVER WRITTEN in modes 24/25/26/27, any build: {len(never)} of 16 records")
    for k in never:
        b = imgs[CURRENT]
        i = int(k[3]); m = int(k.split("_m")[1])
        base = u32(b, GAIN_B_PTRS[i] + m * 4)
        print(f"    {k:<12} @0x{base:05X}  {rec_any(b, base)}")


if __name__ == "__main__":
    main()
