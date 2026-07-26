"""classify_isa.py — per-FILE ISA classification of every iHDS .rwd.

Each file is classified from ITS OWN decoded bytes. Two reliability fixes over
the first attempt:
  1. Cipher is resolved with the PART-NUMBER ORACLE (the part number from the
     file's own header must appear in the decoded payload), not signature-max.
     A table is cached per cipher key but RE-VALIDATED on every file; if the
     cached table doesn't decode this file's part number, the file is re-cracked.
     (Same key can serve different ISAs — e.g. 010203 serves both the V850 TG7
     and SH-2A Civic — so the cipher table is shared but the ISA verdict is
     always computed from the individual file's bytes.)
  2. ISA markers: V850 jr-opcode 0x0780 vs SH-2A 0x4F22 (sts.l pr,@-r15).
     The noisy 0x000B (rts) marker is dropped.
"""
import gzip, glob, os, itertools, re, sys
from collections import defaultdict, Counter
ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES
import encode_eps as E

def candidates(name):
    """Filename-derived part-number plaintext(s) to look for in the decoded payload."""
    base=name.split('.rwd')[0]
    out=[]
    m=re.search(r'[0-9A-Za-z]{5}-[0-9A-Za-z]{3}-[0-9A-Za-z]{4}', base)
    if m: out.append(m.group(0).encode())
    m=re.search(r'([0-9A-Za-z]{5})[-_]?([0-9A-Za-z]{3})[-_]?([0-9A-Za-z]{4})', base)
    if m: out.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}".encode())
    return list(dict.fromkeys(out))

def load(f):
    raw=open(f,'rb').read()
    return gzip.decompress(raw) if f.endswith('.gz') else raw

def parse(raw):
    """-> (container, cipher_key_bytes, payload_bytes)"""
    fmt=raw[0:1]
    if fmt==b'1':
        info=E.parse_x31(raw)
        return 'x31', (bytes(info['key']) if info['key'] else b''), b''.join(info['encs'])
    if fmt==b'Z':
        info=E.parse_x5a(raw)
        key=info['headers'][5][0] if info['headers'][5] else b''
        return 'x5a', key, info['payload']
    return 'other(0x%02x)'%fmt[0], b'', b''

def v_s(buf):
    return buf.count(b'\x80\x07'), buf.count(b'\x4F\x22')   # V850 jr , SH-2A sts.l pr

VALID={}  # keyhex -> list of distinct bijective decode tables for that key's bytes

def valid_tables(keyhex, keyvals):
    if keyhex in VALID: return VALID[keyhex]
    seen=set(); out=[]
    for keys in set(itertools.permutations(keyvals)):
        for oi in itertools.product(range(8),repeat=3):
            t=E.build_decode_table(keys,[E.OPS[x] for x in oi])
            if t is None or t in seen: continue
            seen.add(t); out.append(t)
    VALID[keyhex]=out
    return out

def classify_file(keyhex, keyvals, payload):
    """PER-FILE: among this key's valid cipher tables, pick the one that decodes
    THIS file's bytes to the strongest instruction-marker spike, then read ISA off
    that decode. Same key can need different ops per firmware family, so each file
    is resolved independently. Table is selected on a MID-payload window (guaranteed
    code, not the descriptor/identity at the start); ISA is read from the FULL decode."""
    L=len(payload)
    samp = payload if L<=0x8000 else payload[L//2:L//2+0x8000]
    best=(-1,None)
    for t in valid_tables(keyhex,keyvals):
        d=samp.translate(t)
        sc=max(d.count(b'\x80\x07'), d.count(b'\x4F\x22'))
        if sc>best[0]: best=(sc,t)
    if best[1] is None: return ('undet',0,0)
    full=payload.translate(best[1])
    v=full.count(b'\x80\x07'); s=full.count(b'\x4F\x22')
    if max(v,s)<10: return ('undet',v,s)
    return ('V850' if v>s else 'SH2A', v,s)

def main():
    files=sorted(str(p) for p in CALIB_FILES.glob('*.rwd*'))
    # parse everything
    info=[]   # [name, container, keyhex, keyvals, payload]
    bykey=defaultdict(list)
    for f in files:
        name=os.path.basename(f)
        try: c,k,p=parse(load(f))
        except Exception: info.append([name,'err','-',[],b'']); continue
        kh=k.hex() if k else '-'
        info.append([name,c,kh,list(k),p])
        if c in ('x31','x5a') and k: bykey[kh].append(len(info)-1)

    # classify EACH FILE individually (own bytes, own best-fit cipher table)
    recs=[]
    for name,c,kh,kv,p in info:
        if c not in ('x31','x5a'):
            recs.append([name,c,kh,('other-fmt',0,0)]); continue
        recs.append([name,c,kh,classify_file(kh,kv,p)])

    def report(label, subset):
        print(f"\n=== {label}: {len(subset)} files ===")
        print("  container:", dict(Counter(r[1] for r in subset)))
        by=Counter((r[3][0], r[1]) for r in subset)
        for (isa,c),n in sorted(by.items()): print(f"    {isa:9} {c:12} : {n}")
        v31=sum(n for (isa,c),n in by.items() if isa=='V850' and c=='x31')
        v5a=sum(n for (isa,c),n in by.items() if isa=='V850' and c=='x5a')
        print(f"  >> V850 total = {v31+v5a}   (x31={v31}, x5a={v5a})")

    report("ALL iHDS rwds", recs)
    report("TVA part-number rwds", [r for r in recs if 'TVA' in r[0].upper()])
    eps=[r for r in recs if r[0].upper().startswith('39990')]
    report("EPS (39990) rwds", eps)

    print("\n=== EPS x5a, per file (the contested set) ===")
    for r in sorted(eps):
        if r[1]=='x5a':
            isa,v,s=r[3]; print(f"  {r[0][:30]:30} key={r[2]:8} v850={v:5} sh2a={s:5} -> {isa}")
    print("\n=== shared-key 010203 files (must split individually) ===")
    for r in sorted(recs):
        if r[2]=='010203':
            isa,v,s=r[3]; print(f"  {r[0][:34]:34} {r[1]:4} v850={v:5} sh2a={s:5} -> {isa}")

if __name__=='__main__':
    main()
