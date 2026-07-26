#!/usr/bin/env python3
"""Structural sanity + spot-check validation of the assembled UPD70F3508 SVD."""
import io, os, sys
import xml.etree.ElementTree as ET

SVD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "svd_for_ghidra", "UPD70F3508_V850E2Px4.svd")

def _int(s):
    s = (s or "").strip()
    return int(s, 16) if "x" in s.lower() else int(s or 0)

def main():
    tree = ET.parse(SVD)
    dev = tree.getroot()
    peris = dev.findall(".//peripheral")
    problems = []
    seen_names = set()
    npp = nreg = nfield = 0
    for p in peris:
        npp += 1
        name = p.findtext("name")
        if name in seen_names:
            problems.append(f"duplicate peripheral name {name}")
        seen_names.add(name)
        if p.get("derivedFrom"):
            continue
        base = _int(p.findtext("baseAddress"))
        if not p.findall("addressBlock"):
            problems.append(f"{name}: no addressBlock")
        # registers
        addrs = {}
        for r in p.findall(".//register"):
            nreg += 1
            off = _int(r.findtext("addressOffset"))
            if off < 0:
                problems.append(f"{name}.{r.findtext('name')}: negative offset")
            sz = _int(r.findtext("size"))
            if sz not in (8, 16, 32):
                problems.append(f"{name}.{r.findtext('name')}: odd size {sz}")
            a = base + off
            if a in addrs:
                problems.append(f"{name}: addr {a:#x} shared by {addrs[a]} and {r.findtext('name')}")
            addrs[a] = r.findtext("name")
            # field bounds
            for fld in r.findall(".//field"):
                nfield += 1
                br = fld.findtext("bitRange")
                if br:
                    try:
                        msb, lsb = [int(x) for x in br.strip("[]").split(":")]
                        if msb > sz - 1 or lsb < 0 or lsb > msb:
                            problems.append(f"{name}.{r.findtext('name')}.{fld.findtext('name')}: bad bitRange {br} for size {sz}")
                    except ValueError:
                        problems.append(f"{name}.{r.findtext('name')}.{fld.findtext('name')}: unparseable bitRange {br}")

    # build a global symbol->address index for spot-checks
    idx = {}
    for p in peris:
        base = _int(p.findtext("baseAddress"))
        for r in p.findall(".//register"):
            idx[r.findtext("name")] = base + _int(r.findtext("addressOffset"))

    # spot-checks: register symbol -> expected absolute address (from manual)
    expect = {
        "RESF": 0xFF420020,
        "SWRESA": 0xFF42002C,
        "WDTA0WDTE": 0xFF806000,
        "WDTA0MD": 0xFF80600C,
        "APC": 0xFF454000,
        "FCNnGMCSPRE": None,  # placeholder; FCN names are concrete below
        "OPBT0": 0xFF47000C,
    }
    print(f"peripherals={npp} registers={nreg} fields={nfield}")
    print(f"unique register symbols indexed: {len(idx)}")
    print("--- spot checks ---")
    for sym, exp in expect.items():
        if exp is None:
            continue
        got = idx.get(sym)
        ok = (got == exp)
        print(f"  {'OK ' if ok else 'BAD'} {sym}: got={got and hex(got)} expected={hex(exp)}")

    print(f"--- {len(problems)} structural problems ---")
    for pr in problems[:60]:
        print("  " + pr)
    if len(problems) > 60:
        print(f"  ... and {len(problems)-60} more")

if __name__ == "__main__":
    main()
