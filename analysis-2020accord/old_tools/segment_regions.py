#!/usr/bin/env python
"""
segment_regions.py -- FIRST-PASS region segmenter for V850 EPS firmware blobs.

Window-based content classifier; coalesces adjacent like-windows into regions and
emits sample offsets for MANUAL r2/hexdump review. The labels here are a starting
hypothesis only -- they get corrected by hand (the whole point: don't trust the
machine's pattern-match, use it to find boundaries then verify).

Window = 0x200 bytes. Read-only.
"""
import os, math, struct, re, sys
from collections import Counter

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import OTHER_BINS, STOCK_FW_DUMP

W = 0x200

def winstats(b):
    n = len(b)
    c = Counter(b)
    H = -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0
    top_byte, top_n = c.most_common(1)[0]
    ff = c.get(0xFF, 0); z = c.get(0x00, 0)
    printable = sum(c.get(x,0) for x in range(0x20,0x7F))
    jr = sum(1 for i in range(0, n-1, 2) if b[i]==0x07 and b[i+1]==0x80)
    fedf = len(re.findall(rb'\xdf\xfe', b))
    return dict(H=H, top=top_byte, topf=top_n/n, ff=ff/n, z=z/n,
                printable=printable/n, distinct=len(c), jr=jr, fedf=fedf)

def classify(s):
    if s['ff'] > 0.95:                      return 'EMPTY(FF)'
    if s['z']  > 0.95:                      return 'EMPTY(00)'
    if s['topf'] > 0.85:                    return f"FILL(0x{s['top']:02X})"
    if s['printable'] > 0.60:               return 'STRINGS'
    if s['distinct'] < 24 and s['H'] < 3.5: return 'SPARSE/TABLE'
    if s['fedf'] >= 3 or s['jr'] >= 2:      return 'CODE?'      # V850 markers present
    if s['H'] >= 7.0:                       return 'DATA-HIGH'  # packed/ciphered/dense tables
    if s['H'] >= 5.0:                       return 'CODE/DATA?' # ambiguous -> verify by disasm
    return 'DATA-LOW'

MACRO = {  # collapse fine labels into coarse region classes for a readable map
    'EMPTY(FF)':'ERASED', 'EMPTY(00)':'ERASED',
    'STRINGS':'STRINGS',
    'DATA-HIGH':'DATA/PACKED',
    'SPARSE/TABLE':'TABLE/SPARSE',
    'CODE?':'CODEISH', 'CODE/DATA?':'CODEISH', 'DATA-LOW':'CODEISH',
}
def macro(cls):
    if cls.startswith('FILL'): return 'FILL'
    return MACRO.get(cls, cls)

def segment(path, base):
    b = open(path,'rb').read()
    rows = []
    for off in range(0, len(b), W):
        w = b[off:off+W]
        if len(w) < 16: break
        s = winstats(w); s['cls'] = macro(classify(s)); s['fine'] = classify(s); s['off'] = off
        rows.append(s)
    # coalesce adjacent same-macro-class
    regions = []
    for r in rows:
        if regions and regions[-1]['cls'] == r['cls']:
            regions[-1]['end'] = r['off']+W
            regions[-1]['n'] += 1
            regions[-1]['Hs'] += r['H']; regions[-1]['jr'] += r['jr']; regions[-1]['fedf'] += r['fedf']
        else:
            regions.append(dict(cls=r['cls'], start=r['off'], end=r['off']+W, n=1,
                                Hs=r['H'], jr=r['jr'], fedf=r['fedf']))
    # absorb tiny (<0x600) non-ERASED fragments into the previous region
    merged = []
    for rg in regions:
        if (merged and (rg['end']-rg['start']) < 0x600 and not rg['cls'].startswith('ERASED')
                and merged[-1]['cls'] != 'ERASED'):
            merged[-1]['end'] = rg['end']; merged[-1]['n'] += rg['n']
            merged[-1]['Hs'] += rg['Hs']; merged[-1]['jr'] += rg['jr']; merged[-1]['fedf'] += rg['fedf']
        else:
            merged.append(rg)
    # second pass: re-coalesce now-adjacent same-class
    regions = []
    for rg in merged:
        if regions and regions[-1]['cls'] == rg['cls']:
            regions[-1]['end'] = rg['end']; regions[-1]['n'] += rg['n']
            regions[-1]['Hs'] += rg['Hs']; regions[-1]['jr'] += rg['jr']; regions[-1]['fedf'] += rg['fedf']
        else:
            regions.append(rg)
    print(f"\n{'='*96}\n{os.path.basename(path)}   base=0x{base:X}  size=0x{len(b):X}\n{'='*96}")
    print(f"{'flash start':>12} {'flash end':>12} {'size':>9}  {'class':<14} {'Havg':>5} {'jr':>4} {'fedf':>5}  sample@")
    for rg in regions:
        if rg['end']-rg['start'] < W and rg['cls'].startswith('EMPTY'):
            pass
        sz = rg['end']-rg['start']
        Havg = rg['Hs']/rg['n']
        smp = rg['start'] + (sz//2 & ~1)   # even-aligned midpoint for disasm sample
        print(f"  0x{base+rg['start']:08X}  0x{base+rg['end']:08X} 0x{sz:7X}  {rg['cls']:<14} {Havg:5.2f} {rg['jr']:4d} {rg['fedf']:5d}  file@0x{smp:X}")
    return regions

if __name__ == '__main__':
    D = str(OTHER_BINS)
    targets = [
        (STOCK_FW_DUMP / "code.bin", 0x0),
        (os.path.join(D,"39990-TG7-A030-M1.payload_0x10000.bin"), 0x10000),
        (os.path.join(D,"39990-T9A-P040-M1.payload_0x4000.bin"),  0x4000),
        (os.path.join(D,"39990TY3_J040M1__A1701003.payload_0xC000.bin"), 0xC000),
        (os.path.join(D,"39990-T2F-A210.payload_0x1800.bin"),     0x1800),
    ]
    for path, base in targets:
        segment(path, base)
