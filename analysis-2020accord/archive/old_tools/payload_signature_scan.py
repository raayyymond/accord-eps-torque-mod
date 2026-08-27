#!/usr/bin/env python
"""
payload_signature_scan.py  -- entropy + structure signatures of every V850 .bin
payload in the configured miscellaneous-bin directory, cross-referenced against code.bin.

Read-only. Nothing flashed, no CAN/UDS. Generated for the 2020 Accord (TVA-A160)
"which section of code.bin is the rwd payload" question.

For each payload:
  - implied flash range [load_addr, load_addr+size)  (load_addr from filename .payload_0xNNNN.bin)
  - Shannon entropy: whole, head window, tail window (over PROGRAMMED content, FF-trimmed)
  - leading / trailing 0xFF fill
  - V850 `jr` density: count of 0x8007 halfword (bytes 07 80 LE) on even alignment, per KB
  - descriptor head word + footer word
  - rough "looks like decoded V850 code" verdict

code.bin is scanned over the candidate carve windows {0x1800,0x4000,0xC000,0x10000}
plus the MEASURED app body [0x14000,0x8B218].
"""
import os, glob, math, re, struct, sys

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import OTHER_BINS, STOCK_FW_DUMP

BINDIR = str(OTHER_BINS)
CODEBIN = str(STOCK_FW_DUMP / "code.bin")
WIN = 0x1000  # head/tail window for entropy

def entropy(b):
    if not b: return 0.0
    from collections import Counter
    c = Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def jr_density(b):
    # 0x8007 little-endian halfword = bytes 07 80 at even offset
    cnt = 0
    for i in range(0, len(b)-1, 2):
        if b[i] == 0x07 and b[i+1] == 0x80:
            cnt += 1
    kb = len(b)/1024.0
    return cnt, (cnt/kb if kb else 0)

def fedf_count(b):
    # LE pointer into V850E2 RAM 0xFEDFxxxx -> bytes .. .. df fe ; count 'df fe' pairs
    return len(re.findall(rb'\xdf\xfe', b))

def trim_ff(b):
    lead = 0
    while lead < len(b) and b[lead] == 0xFF: lead += 1
    tail = 0
    while tail < len(b) and b[len(b)-1-tail] == 0xFF: tail += 1
    return lead, tail

def load_addr_from_name(name):
    m = re.search(r'payload_0x([0-9A-Fa-f]+)\.bin$', name)
    return int(m.group(1), 16) if m else None

def report_region(label, b, base):
    """b = bytes of the region; base = its flash load address."""
    lead, tail = trim_ff(b)
    content = b[lead: len(b)-tail] if (lead+tail) < len(b) else b
    head = content[:WIN]
    tailw = content[-WIN:]
    jc, jd = jr_density(content)
    e_all = entropy(content)
    e_head = entropy(head)
    e_tail = entropy(tailw)
    fd = fedf_count(content)
    head_word = struct.unpack('<I', b[lead:lead+4])[0] if len(b)-lead >= 4 else None
    foot_word_le = struct.unpack('<I', b[-4:])[0] if len(b) >= 4 else None
    foot_word_be = struct.unpack('>I', b[-4:])[0] if len(b) >= 4 else None
    print(f"  {label}")
    print(f"    flash range      : 0x{base:X} .. 0x{base+len(b):X}  (size 0x{len(b):X})")
    print(f"    leadFF/tailFF    : 0x{lead:X} / 0x{tail:X}   content=0x{len(content):X}")
    print(f"    entropy all/head/tail: {e_all:.3f} / {e_head:.3f} / {e_tail:.3f}")
    print(f"    jr(8007) count/dens: {jc} / {jd:.2f} per KB")
    print(f"    FEDFxxxx ptrs    : {fd}")
    hw = f"0x{head_word:08X}" if head_word is not None else "n/a"
    print(f"    head word(LE)    : {hw}   first16: {b[lead:lead+16].hex(' ')}")
    print(f"    foot word LE/BE  : 0x{foot_word_le:08X} / 0x{foot_word_be:08X}   last16: {b[-16:].hex(' ')}")
    return dict(label=label, base=base, size=len(b), lead=lead, tail=tail,
                e_all=e_all, e_head=e_head, e_tail=e_tail, jd=jd, fd=fd,
                head_word=head_word, foot_le=foot_word_le)

print("="*100)
print("PART 1 -- V850 payload signatures (configured miscellaneous-bin directory)")
print("="*100)

# group by load addr / size family
files = sorted(glob.glob(os.path.join(BINDIR, "*.bin")))
fams = {}
for f in files:
    name = os.path.basename(f)
    la = load_addr_from_name(name)
    b = open(f,'rb').read()
    key = (la, len(b))
    fams.setdefault(key, []).append((name, b))

for (la, sz) in sorted(fams.keys()):
    members = fams[(la,sz)]
    print(f"\n--- FAMILY load=0x{la:X} size=0x{sz:X}  ({len(members)} files) ---")
    # show signature of first member in detail, summary metrics for the rest
    rep = report_region(members[0][0], members[0][1], la)
    if len(members) > 1:
        print(f"    other members ({len(members)-1}): entropy_all / jr_dens / fedf:")
        for name, b in members[1:]:
            lead, tail = trim_ff(b)
            content = b[lead:len(b)-tail] if (lead+tail)<len(b) else b
            jc, jd = jr_density(content)
            print(f"       {name:<48} e={entropy(content):.3f}  jr={jd:.2f}/KB  fedf={fedf_count(content)}")

print("\n"+"="*100)
print("PART 2 -- code.bin windows at candidate carve offsets")
print("="*100)
cb = open(CODEBIN,'rb').read()
print(f"code.bin size = 0x{len(cb):X}")
# candidate windows: (start, end) -- end derived from each family's block end
candidates = [
    ("x31 0x1800 conv  [0x1800,0x38000)", 0x1800, 0x38000),
    ("T9A   0x4000 conv [0x4000,0x7A000)", 0x4000, 0x7A000),
    ("TY3   0xC000 conv [0xC000,0x78000)", 0xC000, 0x78000),
    ("Pilot 0x10000 conv[0x10000,0x60000)",0x10000,0x60000),
    ("MEASURED app body [0x14000,0x8B218)",0x14000,0x8B218),
    ("app->content end  [0x14000,0x8C000)",0x14000,0x8C000),
]
for label, s, e in candidates:
    report_region(label, cb[s:e], s)

print("\n"+"="*100)
print("PART 3 -- code.bin head structure at each candidate start (raw 32 bytes)")
print("="*100)
for off in [0x1800,0x4000,0x9000,0xC000,0x10000,0x12FF0,0x13000,0x14000,0x14080]:
    print(f"  0x{off:6X}: {cb[off:off+32].hex(' ')}")
