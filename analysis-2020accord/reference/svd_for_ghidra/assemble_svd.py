#!/usr/bin/env python3
"""Merge per-section SVD <peripheral> fragments into a single CMSIS-SVD device file.

Each subagent wrote one fragment file in reference/svd_parts/section*.svd containing one or
more <peripheral> elements (no <device> wrapper, no XML declaration). This script:
  - validates each fragment is well-formed (wrapped in a temp root)
  - collects all <peripheral> elements
  - de-duplicates peripheral names (suffix _2, _3 on collision)
  - sorts peripherals by baseAddress
  - warns on addressBlock overlaps between peripherals
  - emits a CMSIS-SVD 1.1 device for the Renesas UPD70F3508 (V850E2/Px4)
"""
import glob, io, os, sys, re, copy
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "reference/svd_parts")
OUT = os.path.join(HERE, "reference/svd_for_ghidra", "UPD70F3508_V850E2Px4.svd")

def load_fragment(path):
    raw = io.open(path, encoding="utf-8").read()
    # Wrap so multiple top-level <peripheral> elements parse, and so pure-comment files are OK.
    try:
        root = ET.fromstring("<wrap>" + raw + "</wrap>")
    except ET.ParseError as e:
        print(f"  !! PARSE ERROR in {os.path.basename(path)}: {e}", file=sys.stderr)
        return []
    return root.findall("peripheral")

def base_of(p):
    t = (p.findtext("baseAddress") or "0x0").strip()
    try:
        return int(t, 16) if t.lower().startswith("0x") else int(t)
    except ValueError:
        return 0

def span_of(p):
    """(start, end) absolute address span from baseAddress + max addressBlock size."""
    b = base_of(p)
    size = 0
    for ab in p.findall("addressBlock"):
        off = ab.findtext("offset") or "0"
        sz = ab.findtext("size") or "0"
        try:
            off = int(off, 16) if "x" in off.lower() else int(off)
            sz = int(sz, 16) if "x" in sz.lower() else int(sz)
            size = max(size, off + sz)
        except ValueError:
            pass
    return (b, b + max(size, 1))

def _int(s, default=0):
    if s is None:
        return default
    s = s.strip()
    try:
        return int(s, 16) if "x" in s.lower() else int(s)
    except ValueError:
        return default

def regen_address_blocks(p, gap=0x400):
    """Replace a peripheral's <addressBlock>(s) with tight blocks derived from its
    registers, clustering registers separated by < `gap` bytes. Avoids the giant
    sparse blocks some sections produce (e.g. a FLG register far from its base),
    which would otherwise trigger false peripheral overlaps."""
    base = base_of(p)
    spans = []  # (start_off, end_off) per register, relative to base
    for r in p.findall(".//register"):
        off = _int(r.findtext("addressOffset"))
        nbytes = max(1, _int(r.findtext("size"), 8) // 8)
        spans.append((off, off + nbytes))
    if not spans:
        return
    spans.sort()
    clusters = [[spans[0][0], spans[0][1]]]
    for s, e in spans[1:]:
        if s - clusters[-1][1] <= gap:
            clusters[-1][1] = max(clusters[-1][1], e)
        else:
            clusters.append([s, e])
    for ab in p.findall("addressBlock"):
        p.remove(ab)
    name_el = p.find("name")
    insert_at = list(p).index(name_el) + 1 if name_el is not None else 0
    for i, (s, e) in enumerate(clusters):
        ab = ET.Element("addressBlock")
        o = ET.SubElement(ab, "offset"); o.text = hex(s)
        sz = ET.SubElement(ab, "size"); sz.text = hex(e - s)
        u = ET.SubElement(ab, "usage"); u.text = "registers"
        p.insert(insert_at + i, ab)

_ORDER = {
    "peripheral": ["name", "version", "description", "alternatePeripheral", "groupName",
                   "prependToName", "appendToName", "headerStructName", "disableCondition",
                   "baseAddress", "addressBlock", "interrupt", "registers"],
    "register": ["name", "displayName", "description", "alternateGroup", "alternateRegister",
                 "addressOffset", "size", "access", "protection", "resetValue", "resetMask",
                 "dataType", "modifiedWriteValues", "writeConstraint", "readAction", "fields"],
    "field": ["name", "description", "bitOffset", "bitWidth", "lsb", "msb", "bitRange",
              "access", "modifiedWriteValues", "writeConstraint", "readAction",
              "enumeratedValues"],
}

def normalize_order(elem):
    """Stable-reorder children of peripheral/register/field elements into canonical
    CMSIS-SVD order so the file passes strict schema validators (svdconv etc.)."""
    order = _ORDER.get(elem.tag)
    if order:
        children = list(elem)
        for c in children:
            elem.remove(c)
        children.sort(key=lambda c: order.index(c.tag) if c.tag in order else len(order))
        for c in children:
            elem.append(c)
    for c in list(elem):
        normalize_order(c)

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not (elem.text or "").strip():
            elem.text = i + "  "
        for c in elem:
            indent(c, level + 1)
        if not (c.tail or "").strip():
            c.tail = i
    if level and not (elem.tail or "").strip():
        elem.tail = i

def main():
    frags = sorted(glob.glob(os.path.join(PARTS, "section*.svd")))
    print(f"Found {len(frags)} fragment files")
    peris = []
    per_file = {}
    for f in frags:
        ps = load_fragment(f)
        per_file[os.path.basename(f)] = len(ps)
        peris.extend(ps)
    print("Per-file peripheral counts:")
    for k in sorted(per_file):
        print(f"  {k}: {per_file[k]}")

    # de-dup names
    seen = {}
    for p in peris:
        n = p.findtext("name") or "UNNAMED"
        if n in seen:
            seen[n] += 1
            newn = f"{n}_{seen[n]}"
            p.find("name").text = newn
            print(f"  name collision: {n} -> {newn}")
        else:
            seen[n] = 1

    # regenerate tight addressBlock(s) from registers (skip derivedFrom shells w/o regs)
    for p in peris:
        if p.findall(".//register"):
            regen_address_blocks(p)

    def clusters_abs(p):
        b = base_of(p)
        out = []
        for ab in p.findall("addressBlock"):
            o = _int(ab.findtext("offset")); s = _int(ab.findtext("size"))
            out.append((b + o, b + o + max(s, 1)))
        return out or [(b, b + 1)]

    # union-find merge of peripherals whose register clusters actually overlap
    n = len(peris)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    tagged = []
    for i, p in enumerate(peris):
        for s, e in clusters_abs(p):
            tagged.append((s, e, i))
    tagged.sort()
    active = []  # (end, idx) of still-open intervals
    for s, e, i in tagged:
        active = [(ae, ai) for ae, ai in active if ae > s]
        for ae, ai in active:
            if find(ai) != find(i):
                union(ai, i)
        active.append((e, i))

    # group peripherals by merge-root
    groups = {}
    for i, p in enumerate(peris):
        groups.setdefault(find(i), []).append(p)

    def merged_name(names):
        names = sorted(set(names))
        if len(names) == 1:
            return names[0]
        stripped = re.sub(r"\d+", "", names[0]).replace("__", "_").strip("_")
        return stripped or names[0]

    merged = []
    collisions = []
    for root, grp in groups.items():
        grp.sort(key=base_of)
        if len(grp) == 1:
            merged.append(grp[0]); continue
        names = [g.findtext("name") for g in grp]
        newp = ET.Element("peripheral")
        nm = ET.SubElement(newp, "name"); nm.text = merged_name(names)
        desc = ET.SubElement(newp, "description")
        desc.text = (grp[0].findtext("description") or nm.text) + \
            " (merged: " + ", ".join(names) + ")"
        regs_el = ET.SubElement(newp, "registers")
        by_addr = {}
        for g in grp:
            gb = base_of(g)
            for r in g.findall(".//register"):
                addr = gb + _int(r.findtext("addressOffset"))
                if addr in by_addr:
                    prev = by_addr[addr].findtext("name")
                    cur = r.findtext("name")
                    if prev != cur:
                        collisions.append((addr, prev, cur))
                    continue
                by_addr[addr] = r
        newbase = min(by_addr)
        nb = ET.SubElement(newp, "baseAddress"); nb.text = hex(newbase)
        for addr in sorted(by_addr):
            r = copy.deepcopy(by_addr[addr])
            ao = r.find("addressOffset")
            if ao is None:
                ao = ET.SubElement(r, "addressOffset")
            ao.text = hex(addr - newbase)
            regs_el.append(r)
        regen_address_blocks(newp)
        merged.append(newp)
        print(f"  MERGED {names} -> {nm.text} ({len(by_addr)} regs, base {newbase:#x})")

    peris = merged
    peris.sort(key=base_of)

    # de-dup names again (post-merge, just in case)
    seen = {}
    for p in peris:
        nm = p.find("name"); base = nm.text
        if base in seen:
            seen[base] += 1; nm.text = f"{base}_{seen[base]}"
            print(f"  post-merge name collision: {base} -> {nm.text}")
        else:
            seen[base] = 1

    # final precise overlap check on tight clusters
    final_tagged = []
    for p in peris:
        for s, e in clusters_abs(p):
            final_tagged.append((s, e, p.findtext("name")))
    final_tagged.sort()
    overlaps = 0
    for j in range(len(final_tagged) - 1):
        s, e, nm = final_tagged[j]
        s2, e2, nm2 = final_tagged[j + 1]
        if nm != nm2 and s2 < e:
            print(f"  !! RESIDUAL OVERLAP: {nm} [{s:#x}-{e:#x}) vs {nm2} [{s2:#x}-{e2:#x})", file=sys.stderr)
            overlaps += 1
    if collisions:
        print(f"  register address collisions (different names, kept first): {len(collisions)}")
        for addr, a, b in collisions[:20]:
            print(f"    {addr:#x}: {a} vs {b}")
    print(f"  residual overlaps after merge: {overlaps}")

    nreg = sum(len(p.findall(".//register")) for p in peris)
    nfield = sum(len(p.findall(".//field")) for p in peris)
    print(f"TOTAL: {len(peris)} peripherals, {nreg} registers, {nfield} fields")

    # build device
    dev = ET.Element("device")
    dev.set("schemaVersion", "1.1")
    dev.set("{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation", "CMSIS-SVD.xsd")
    def add(parent, tag, text):
        e = ET.SubElement(parent, tag); e.text = text; return e
    add(dev, "vendor", "Renesas")
    add(dev, "name", "UPD70F3508")
    add(dev, "series", "V850E2/Px4")
    add(dev, "version", "1.0")
    add(dev, "description", "Renesas V850E2/Px4 (uPD70F3508) automotive MCU. "
        "SVD generated from R01UH0098EJ0100 hardware manual for Ghidra import.")
    cpu = ET.SubElement(dev, "cpu")
    add(cpu, "name", "other")
    add(cpu, "revision", "r0p0")
    add(cpu, "endian", "little")
    add(cpu, "mpuPresent", "false")
    add(cpu, "fpuPresent", "true")
    add(cpu, "nvicPrioBits", "4")
    add(cpu, "vendorSystickConfig", "false")
    add(dev, "addressUnitBits", "8")
    add(dev, "width", "32")
    add(dev, "size", "32")
    add(dev, "access", "read-write")
    add(dev, "resetValue", "0x00000000")
    add(dev, "resetMask", "0xFFFFFFFF")
    peris_el = ET.SubElement(dev, "peripherals")
    for p in peris:
        normalize_order(p)
        peris_el.append(p)

    indent(dev)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    xml = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(dev, encoding="unicode")
    io.open(OUT, "w", encoding="utf-8").write(xml)
    print(f"Wrote {OUT} ({len(xml)} bytes)")
    # final validation
    ET.fromstring(xml.split("?>",1)[1])
    print("Final XML validates OK")

if __name__ == "__main__":
    main()
