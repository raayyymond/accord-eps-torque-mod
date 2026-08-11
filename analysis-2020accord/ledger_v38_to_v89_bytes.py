#!/usr/bin/env python3
"""DELIVERED-BYTES LEDGER, V38 -> V89.  Extends ledger_v38_to_v84_bytes.py through V85-V89.
Reads the PLAIN IMAGES ON DISK, not the build scripts.

Plain images are flat 1 MiB code images: file offset == firmware address (verified by anchoring
0xC646C == 891 on stock, and 0x2A1F0 halfword == 0x7CD0 on V57+).
V850 is LITTLE-ENDIAN.  Record layout: [npt:u16][X x npt][Y x npt], Y at base + 2 + 2*npt.

Written for the 2026-08-10 ARC AUDIT (docs/ARC-AUDIT-2026-08-10.md). Extends the V38->V84 reader
with: V85, V86, V86B, V87, V88, V89 build rows; the requested cell superset (0xC40BC/0xC40D2/
0xC40D4/0xC4080/0xC6200/0xC646E/0xD77DA/0xD77EE/0xC6AFC/0xC6AFE/0xC64B0 and 0xC63A0's five stock
siblings); a raw dump of the cave region 0xC4B00-0xC4B60 for every build that carries a cave; and a
"# builds frozen" column computed along the build order for every scalar site.
"""
import struct, os, sys, json
from pathlib import Path

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", r"C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
STOCK = ROOT / "stock_fw_dump" / "code.bin"

# ---- build order, V38 .. V89.  filename stem -> label
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
    ("V86",  "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V86B", "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V87",  "_v87_V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98_plain_image.bin"),
    ("V88",  "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256_plain_image.bin"),
    ("V89",  "_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin"),
]

# expected sha256 for each build image, from docs/BUILD-LINEAGE.md / team-lead brief -- cross-checked
# at load time so a stale or wrong file on disk is caught immediately, not silently read.
EXPECTED_SHA = {
    "V85": "cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f",
    "V86": "b8d81ebf9aae4ce27b489687a6d2dc1b222214accc0b128068b31ce41515d2f8",
    "V86B": "b2dfe9ffc3fd2c5a786a7adb1d281e2841143756dccf766b84f292b3f9416d8d",
    "V87": "27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034",
    "V88": "96b1e018d2058984ada1ba4add7ce42516d5ed9cab65c7be7db294c3d0ca47b8",
    "V89": "6eae6826881cb5fd737ab433919f64a556ed027126e3f056ed8f03c13206f159",
}

# ---- scalar sites: (addr, width, label).  width 1 = byte, 2 = signed halfword LE
SITES = [
    (0x3AA96, 1, "r24/r26 gate byte (C5=dead 0x683C / FB=latActive 0x6806)"),
    (0x3AB76, 1, "V62 sar r26 (AA=stock / A9=x2)"),
    (0x3AC20, 1, "V62 sar r24 (AA=stock / A9=x2)"),
    (0x454FE, 1, "V42 macro-ratchet fix (BA=stock bne / B5=br)"),
    (0xC643E, 2, "gain_A arm"),
    (0xC6440, 2, "third arm gp-0x671a"),
    (0xC6442, 2, "gp-0x671d arm (outranks gate)"),
    (0xC6444, 2, "r26 engaged arm"),
    (0xC6446, 2, "r24 engaged arm (Lever B)"),
    (0xC644A, 2, "V43 dirty-derivative pole"),
    (0xC6450, 2, "V46 lever (FUN_0003a382 Stage-A EMA)"),
    (0xC646C, 2, "SHARED sensor scale (stock 891)"),
    (0xC646E, 2, "companion cal -- kit's own 'INERTIA gain'"),
    (0xC6CD0, 2, "V57 private forward LKAS gain (3564 = 4x)"),
    (0x2A1F0, 2, "V57 decouple displacement (7CD0 => 0xC6CD0)"),
    (0xC61B2, 2, "ARBITRATION output clamp"),
    (0xC61B4, 2, "LKAS-GAIN output clamp"),
    (0xC61B8, 2, "pre-gain deadband (102)"),
    (0xC61F6, 2, "r24 lane deadzone"),
    (0xC62EA, 2, "low-speed steer lockout window"),
    (0xC63A0, 2, "Path-2 damper weight (the ODD ONE OUT of 6 siblings)"),
    (0xC63A2, 2, "Path-2 sibling (stock 1024, never moved)"),
    (0xC63A4, 2, "Path-2 sibling (stock 1024, never moved)"),
    (0xC63A6, 2, "Path-2 sibling (stock 1024, never moved)"),
    (0xC63A8, 2, "Path-2 sibling (stock 1024, never moved)"),
    (0xC63AA, 2, "Path-2 sibling (stock 1024, never moved)"),
    (0xC63AC, 2, "Path-2 accumulator IIR coeff"),
    (0xC63AE, 2, "LERP index cell -- NEVER RAISE to 0 (forbidden relay move)"),
    (0xC4080, 2, "K0 -- NEVER-RAISE pure-relay hazard (FRICTION += cal/1024, no |model| factor)"),
    (0xC407E, 2, "friction-comp clamp / DTC-0x1d interlock"),
    (0xC407C, 2, "interlock clamp neighbour"),
    (0xC40BC, 2, "Coulomb-relay normaliser in FUN_0003b8f6 (V85 lever)"),
    (0xC40D2, 2, "K1 -- |model|-proportional modelled Coulomb friction (V89 lever)"),
    (0xC40D4, 2, "command-branch EMA in FUN_0003b8f6, alpha (V86 lever)"),
    (0xC64C8, 1, "aggregator mode selector"),
    (0xC64C9, 1, "blend mux"),
    (0xC64FA, 1, "CEIL byte cal"),
    (0xC64B0, 2, "unclaimed neighbour of the CEIL/gain block -- checked, not a known lever"),
    (0xC6200, 2, "clamp -- NEVER < Y[0] (forbidden relay move); NOT governor-shared"),
    (0xC6206, 2, "speed-selector cal A (V40 brick)"),
    (0xC6208, 2, "speed-selector cal B (V40 brick)"),
    (0xC61DA, 2, "Q10 integrator scale"),
    (0xC6316, 2, "governor vehicle-speed cal ~10km/h"),
    (0xC6158, 2, "ceiling tp+0x7158 fallback"),
    (0xC6AFC, 2, "V56 mute target 1 (falsified/harmful, 6-9Hz NOT covered)"),
    (0xC6AFE, 2, "V56 mute target 2 (falsified/harmful, 6-9Hz NOT covered)"),
    (0xD77DA, 2, "FactorC m26 Y[0] via ptr array (damper zero point, engaged)"),
    (0xD77EE, 2, "FactorC m27 Y[0] via ptr array (damper zero point, engaged col 2)"),
    # gain_A records: rec0/rec1 cells named in BUILD-LINEAGE as the SEVENTH silent revert
    (0xC6A72, 2, "gain_A rec0 [0]"), (0xC6A74, 2, "gain_A rec0 [1]"),
    (0xC6A76, 2, "gain_A rec0 [2]"), (0xC6A78, 2, "gain_A rec0 [3]"),
    (0xC6A86, 2, "gain_A rec1 [0]"), (0xC6A88, 2, "gain_A rec1 [1]"),
    (0xC6A8A, 2, "gain_A rec1 [2]"), (0xC6A8C, 2, "gain_A rec1 [3]"),
    (0xC6A9A, 2, "gain_A rec2 Y[0]"), (0xC6A9C, 2, "gain_A rec2 Y[1]"),
    (0xC6A9E, 2, "gain_A rec2 Y[2]"), (0xC6AA0, 2, "gain_A rec2 Y[3]"),
    (0xC6AAE, 2, "gain_A rec3 Y[0]"), (0xC6AB0, 2, "gain_A rec3 Y[1]"),
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
    "gain_B":   None,      # 4 separate arrays, handled below
}
GAIN_B_PTRS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
MODES = [10, 11, 12, 24, 25, 26, 27]

# ---- cave region: raw byte dump, every build that has ever carried a cave here
CAVE_LO, CAVE_HI = 0xC4B00, 0xC4B60


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
    import hashlib
    imgs = {}
    missing = []
    for name, f in BUILDS:
        p = f if isinstance(f, Path) else ROOT / f
        if not p.exists():
            print(f"### MISSING {name}: {p}", file=sys.stderr)
            missing.append(name)
            continue
        b = load(p)
        imgs[name] = b
        if name in EXPECTED_SHA:
            h = hashlib.sha256(b).hexdigest()
            if h != EXPECTED_SHA[name]:
                print(f"### SHA MISMATCH {name}: got {h}, expected {EXPECTED_SHA[name]}", file=sys.stderr)
            else:
                print(f"    sha OK  {name}  {h}")
    names = [n for n, _ in BUILDS if n in imgs]
    print(f"\nMISSING FROM DISK (no image, excluded from matrix): {missing}\n")

    # sanity anchors
    st = imgs["STOCK"]
    assert len(st) == 0x100000, len(st)
    assert s16(st, 0xC646C) == 891, s16(st, 0xC646C)
    assert st[0x454FE] == 0xBA, hex(st[0x454FE])
    print("ANCHORS OK: stock 0xC646C=891, 0x454FE=0xBA, len=0x100000\n")

    out = {}
    # --- scalars, with a "# builds frozen" (consecutive unchanged run ending at the last build)
    rows = []
    for addr, w, label in SITES:
        vals = {}
        for n in names:
            b = imgs[n]
            vals[n] = b[addr] if w == 1 else s16(b, addr)
        rows.append((addr, w, label, vals))
    out["scalars"] = [{"addr": f"0x{a:05X}", "w": w, "label": l,
                       "vals": {k: v for k, v in v_.items()}} for a, w, l, v_ in rows]

    # --- factor records per mode
    fac = {}
    for fname, ptr in PTRS.items():
        if ptr is None: continue
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
    # gain_B: 4 arrays
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

    outp = Path(os.environ.get("LEDGER_OUT", "ledger_bytes_v89.json"))
    outp.write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {outp}")

    # ---- human print: scalars, only rows that ever change, plus frozen-run count
    print("\n=== SCALAR SITES (only rows that differ somewhere) ===")
    for addr, w, label, vals in rows:
        uniq = set(vals.values())
        tag = "" if len(uniq) > 1 else "  [CONSTANT -- STOCK on every build on disk]"
        print(f"\n0x{addr:05X} w{w}  {label}{tag}")
        # run-length compress along build order
        prev = None; run = []
        segs = []
        for n in names:
            v = vals[n]
            if v != prev:
                if run: segs.append((prev, run))
                run = [n]; prev = v
            else:
                run.append(n)
        if run: segs.append((prev, run))
        for v, r in segs:
            vs = f"0x{v:02X}" if w == 1 else str(v)
            print(f"    {vs:>8}  :  {r[0]}..{r[-1]}" if len(r) > 1 else f"    {vs:>8}  :  {r[0]}")
        # frozen count = length of the LAST run (i.e. how many consecutive builds up to
        # the newest on disk have sat at the current value)
        if segs:
            last_val, last_run = segs[-1]
            print(f"    # builds frozen (at current value, ending {names[-1]}): {len(last_run)}")

    # ---- human print: factor records, modes 24/25/26/27 (+10/11 to show inertness)
    print("\n\n=== FACTOR RECORDS (run-length along build order) ===")
    for fname in ("FactorC", "FactorE", "FactorB", "FactorD", "ceiling", "friction"):
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
            if len(segs) == 1:
                print(f"\n{fname} m{m}: [CONSTANT ALL BUILDS ON DISK] {segs[0][0]}")
            else:
                print(f"\n{fname} m{m}:")
                for v, r in segs:
                    rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
                    print(f"    {rng:<14} {v}")

    print("\n\n=== gain_B (4 arrays) -- only entries that CHANGE ===")
    for key in sorted(fac["gain_B"]):
        vals = fac["gain_B"][key]
        if len(set(str(v) for v in vals.values())) == 1:
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
        print(f"\ngain_B {key}:")
        for v, r in segs:
            rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
            print(f"    {rng:<14} {v}")

    # ---- cave region raw dump for builds that carry a cave (non-0xFF content present)
    print(f"\n\n=== CAVE REGION 0x{CAVE_LO:05X}-0x{CAVE_HI:05X} (hex, only builds with non-FF content) ===")
    for n in names:
        b = imgs[n]
        region = b[CAVE_LO:CAVE_HI]
        if all(x == 0xFF for x in region):
            continue
        print(f"\n{n}:")
        print("    " + region.hex())


if __name__ == "__main__":
    main()
